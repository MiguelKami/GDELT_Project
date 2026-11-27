"""Ingest the latest GDELT Events, Mentions, and GKG batches as Parquet.

GCS layout: <type>/hour_bucket=YYYYMMDDHH/<type>_YYYYMMDDHHMMSS.parquet
Timestamps in this module are UTC.
"""

import csv
import os
import tempfile
import zipfile
from datetime import datetime, timezone

import functions_framework
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage

BASE_URL = os.environ.get(
    "GDELT_BASE_URL", "https://data.gdeltproject.org/gdeltv2"
).rstrip("/")
BUCKET_NAME = os.environ["RAW_BUCKET"]

FILE_TYPES = {
    "events": ".export.CSV.zip",
    "mentions": ".mentions.CSV.zip",
    "gkg": ".gkg.csv.zip",
}

# Column order matches the source columns in terraform/schema/*.json.
# 'ingested_at' and 'hour_time' are derived metadata, not source CSV columns.
EVENT_COLUMNS = [
    "GlobalEventID", "Day", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
    "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
    "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
    "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
    "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code", "IsRootEvent",
    "EventCode", "EventBaseCode", "EventRootCode", "QuadClass",
    "GoldsteinScale", "NumMentions", "NumSources", "NumArticles", "AvgTone",
    "Actor1Geo_Type", "Actor1Geo_Fullname", "Actor1Geo_CountryCode",
    "Actor1Geo_ADM1Code", "Actor1Geo_ADM2Code", "Actor1Geo_Lat",
    "Actor1Geo_Long", "Actor1Geo_FeatureID", "Actor2Geo_Type",
    "Actor2Geo_Fullname", "Actor2Geo_CountryCode", "Actor2Geo_ADM1Code",
    "Actor2Geo_ADM2Code", "Actor2Geo_Lat", "Actor2Geo_Long",
    "Actor2Geo_FeatureID", "ActionGeo_Type", "ActionGeo_Fullname",
    "ActionGeo_CountryCode", "ActionGeo_ADM1Code", "ActionGeo_ADM2Code",
    "ActionGeo_Lat", "ActionGeo_Long", "ActionGeo_FeatureID", "DATEADDED",
    "SOURCEURL",
]

MENTION_COLUMNS = [
    "GlobalEventID", "EventTimeDate", "MentionTimeDate", "MentionType",
    "MentionSourceName", "MentionIdentifier", "SentenceID", "Actor1CharOffset",
    "Actor2CharOffset", "ActionCharOffset", "InRawText", "Confidence",
    "MentionDocLen", "MentionDocTone", "MentionDocTranslationInfo", "Extras",
]

GKG_COLUMNS = [
    "GKGRECORDID", "DATE", "SourceCollectionIdentifier", "SourceCommonName",
    "DocumentIdentifier", "Counts", "V2Counts", "Themes", "V2Themes",
    "Locations", "V2Locations", "Persons", "V2Persons", "Organizations",
    "V2Organizations", "V2Tone", "Dates", "GCAM", "SharingImage",
    "RelatedImages", "SocialImageEmbeds", "SocialVideoEmbeds", "Quotations",
    "AllNames", "Amounts", "TranslationInfo", "Extras",
]

COLUMNS = {
    "events": EVENT_COLUMNS,
    "mentions": MENTION_COLUMNS,
    "gkg": GKG_COLUMNS,
}

INTEGER_COLUMNS = {
    "events": {
        "GlobalEventID", "Day", "MonthYear", "Year", "IsRootEvent",
        "QuadClass", "NumMentions", "NumSources", "NumArticles",
        "Actor1Geo_Type", "Actor2Geo_Type", "ActionGeo_Type", "DATEADDED",
    },
    "mentions": {
        "GlobalEventID", "EventTimeDate", "MentionTimeDate", "MentionType",
        "SentenceID", "Actor1CharOffset", "Actor2CharOffset",
        "ActionCharOffset", "InRawText", "Confidence", "MentionDocLen",
    },
    "gkg": {"DATE", "SourceCollectionIdentifier"},
}

FLOAT_COLUMNS = {
    "events": {
        "FractionDate", "GoldsteinScale", "AvgTone",
        "Actor1Geo_Lat", "Actor1Geo_Long", "Actor2Geo_Lat",
        "Actor2Geo_Long", "ActionGeo_Lat", "ActionGeo_Long",
    },
    "mentions": {"MentionDocTone"},
    "gkg": set(),
}

REQUIRED_COLUMNS = {
    "events": {"GlobalEventID"},
    "mentions": {"GlobalEventID"},
    "gkg": {"GKGRECORDID"},
}


def make_parquet_schema(data_type):
    fields = []
    for name in COLUMNS[data_type]:
        if name in INTEGER_COLUMNS[data_type]:
            field_type = pa.int64()
        elif name in FLOAT_COLUMNS[data_type]:
            field_type = pa.float64()
        else:
            field_type = pa.string()
        fields.append(pa.field(name, field_type))
    fields.extend([
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
        pa.field("hour_time", pa.timestamp("us", tz="UTC")),
    ])
    return pa.schema(fields)


PARQUET_SCHEMAS = {name: make_parquet_schema(name) for name in FILE_TYPES}



def build_object_name(data_type, filename):
    """Build GCS object path using UTC batch timestamp."""

    batch_id = filename.split(".", 1)[0]

    batch_time = datetime.strptime(
        batch_id, "%Y%m%d%H%M%S"
    ).replace(tzinfo=timezone.utc)

    batch_hour = batch_time.replace(
        minute=0,
        second=0,
        microsecond=0
    )

    hour_bucket = batch_hour.strftime("%Y%m%d%H")

    object_name = (
        f"data/{data_type}/"
        f"hour_bucket={hour_bucket}/"
        f"{data_type}_{batch_id}.parquet"
    )

    return object_name, batch_hour

def download_to_file(session, source_url, target_path):
    """Stream the ZIP to disk to limit memory consumption."""
    with session.get(source_url, timeout=(10, 180), stream=True) as response:
        response.raise_for_status()
        with open(target_path, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


def write_parquet(data_type, zip_path, parquet_path, batch_hour):
    """Read a tab separated GDELT CSV and write typed Snappy Parquet."""
    row_count = 0
    schema = PARQUET_SCHEMAS[data_type]
    ingested_at = pd.Timestamp.now(tz="UTC")

    with zipfile.ZipFile(zip_path) as archive:
        csv_name = next(
            (name for name in archive.namelist() if name.lower().endswith(".csv")),
            None,
        )
        if csv_name is None:
            raise ValueError(f"{data_type} ZIP does not contain a CSV file")

        with archive.open(csv_name) as csv_file:
            chunks = pd.read_csv(
                csv_file,
                sep="\t",
                header=None,
                names=COLUMNS[data_type],
                dtype="string",  # Prevent loss of leading zeros in string codes.
                keep_default_na=False,
                quoting=csv.QUOTE_NONE,
                chunksize=3000,
                encoding="utf-8",
                on_bad_lines="error",
            )

            with pq.ParquetWriter(
                parquet_path, schema, compression="snappy"
            ) as writer:
                for frame in chunks:
                    for name in INTEGER_COLUMNS[data_type]:
                        frame[name] = pd.to_numeric(
                            frame[name].replace("", pd.NA), errors="raise"
                        ).astype("Int64")
                    for name in FLOAT_COLUMNS[data_type]:
                        frame[name] = pd.to_numeric(
                            frame[name].replace("", pd.NA), errors="raise"
                        ).astype("Float64")

                    for name in REQUIRED_COLUMNS[data_type]:
                        if frame[name].isna().any() or (frame[name] == "").any():
                            raise ValueError(
                                f"{data_type} has empty values in required column {name}"
                            )

                    frame["ingested_at"] = ingested_at
                    frame["hour_time"] = pd.Timestamp(batch_hour)
                    arrow_table = pa.Table.from_pandas(
                        frame, schema=schema, preserve_index=False
                    )
                    writer.write_table(arrow_table)
                    row_count += len(frame)

    if row_count == 0:
        raise ValueError(f"{data_type} file contained no data rows")
    return row_count


@functions_framework.http
def ingest_gdelt(request):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    results = {}

    with requests.Session() as session:
        response = session.get(f"{BASE_URL}/lastupdate.txt", timeout=30)
        response.raise_for_status()
        manifest_urls = [
            line.split()[-1] for line in response.text.splitlines() if line.split()
        ]

        # Check that the manifest includes each feed before downloading.
        source_files = {}
        for data_type, suffix in FILE_TYPES.items():
            source = next((u for u in manifest_urls if u.endswith(suffix)), None)
            if source is None:
                raise ValueError(f"No {data_type} URL in GDELT manifest")
            source_files[data_type] = source

        for data_type, source_url in source_files.items():
            filename = source_url.rsplit("/", 1)[-1]
            object_name, batch_hour = build_object_name(data_type, filename)
            blob = bucket.blob(object_name)

            if blob.exists():
                results[data_type] = {
                    "status": "already_exists",
                    "object": object_name,
                    "format": "parquet",
                }
                continue

            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "source.zip")
                parquet_path = os.path.join(temp_dir, "data.parquet")
                download_to_file(
                    session, f"{BASE_URL}/{filename}", zip_path
                )
                row_count = write_parquet(
                    data_type, zip_path, parquet_path, batch_hour
                )

                try:
                    blob.upload_from_filename(
                        parquet_path,
                        content_type="application/vnd.apache.parquet",
                        if_generation_match=0,
                    )
                    status = "uploaded"
                except PreconditionFailed:
                    status = "already_exists"

                results[data_type] = {
                    "status": status,
                    "object": object_name,
                    "format": "parquet",
                    "row_count": row_count,
                }

    return {"status": "success", "bucket": BUCKET_NAME, "files": results}, 200
