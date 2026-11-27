
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

# Source column order from terraform/schema/gkg.json.
GKG_COLUMNS = [
    "GKGRECORDID", "DATE", "SourceCollectionIdentifier", "SourceCommonName",
    "DocumentIdentifier", "Counts", "V2Counts", "Themes", "V2Themes",
    "Locations", "V2Locations", "Persons", "V2Persons", "Organizations",
    "V2Organizations", "V2Tone", "Dates", "GCAM", "SharingImage",
    "RelatedImages", "SocialImageEmbeds", "SocialVideoEmbeds", "Quotations",
    "AllNames", "Amounts", "TranslationInfo", "Extras",
]
INTEGER_COLUMNS = {"DATE", "SourceCollectionIdentifier"}
GKG_PARQUET_SCHEMA = pa.schema(
    [
        pa.field(name, pa.int64() if name in INTEGER_COLUMNS else pa.string())
        for name in GKG_COLUMNS
    ]
    + [
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
        pa.field("hour_time", pa.timestamp("us", tz="UTC")),
    ]
)


def build_object_name(data_type, filename):
    """Return a stable GCS object key and the UTC batch hour."""
    batch_id = filename.split(".", 1)[0]
    batch_time = datetime.strptime(batch_id, "%Y%m%d%H%M%S").replace(
        tzinfo=timezone.utc
    )
    batch_hour = batch_time.replace(minute=0, second=0, microsecond=0)
    hour_bucket = batch_hour.strftime("%Y%m%d%H")
    extension = "parquet" if data_type == "gkg" else "csv.zip"
    return (
        f"{data_type}/hour_bucket={hour_bucket}/"
        f"{data_type}_{batch_id}.{extension}",
        batch_hour,
    )


def write_gkg_parquet(zip_path, parquet_path, batch_hour):
    """Convert the tab separated GKG CSV inside a ZIP into Snappy Parquet."""
    row_count = 0
    ingestion_time = pd.Timestamp.now(tz="UTC")

    with zipfile.ZipFile(zip_path) as archive:
        csv_name = next(
            (name for name in archive.namelist() if name.lower().endswith(".csv")),
            None,
        )
        if csv_name is None:
            raise ValueError("GKG ZIP contains no CSV file")

        with archive.open(csv_name) as csv_file:
            chunks = pd.read_csv(
                csv_file,
                sep="\t",
                header=None,
                names=GKG_COLUMNS,
                dtype="string",
                keep_default_na=False,
                quoting=csv.QUOTE_NONE,
                chunksize=10000,
                encoding="utf-8",
                on_bad_lines="error",
            )
            with pq.ParquetWriter(
                parquet_path, GKG_PARQUET_SCHEMA, compression="snappy"
            ) as writer:
                for frame in chunks:
                    for name in INTEGER_COLUMNS:
                        frame[name] = pd.to_numeric(
                            frame[name].replace("", pd.NA), errors="raise"
                        ).astype("Int64")
                    frame["ingested_at"] = ingestion_time
                    frame["hour_time"] = pd.Timestamp(batch_hour)
                    table = pa.Table.from_pandas(
                        frame, schema=GKG_PARQUET_SCHEMA, preserve_index=False
                    )
                    writer.write_table(table)
                    row_count += len(frame)

    if row_count == 0:
        raise ValueError("No rows found in GKG batch")
    return row_count


def download_to_file(session, source_url, zip_path):
    """Stream a source ZIP to a temporary file without buffering it in RAM."""
    with session.get(source_url, timeout=(10, 180), stream=True) as response:
        response.raise_for_status()
        with open(zip_path, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


@functions_framework.http
def ingest_gdelt(request):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    results = {}

    with requests.Session() as session:
        response = session.get(f"{BASE_URL}/lastupdate.txt", timeout=30)
        response.raise_for_status()
        manifest_urls = [
            line.split()[-1] for line in response.text.splitlines() if line.split()
        ]

        # Check all three URLs before processing any batch.
        files = {}
        for data_type, suffix in FILE_TYPES.items():
            source = next((u for u in manifest_urls if u.endswith(suffix)), None)
            if source is None:
                raise ValueError(f"Latest {data_type} file not found in GDELT manifest")
            files[data_type] = source

        for data_type, source_url in files.items():
            filename = source_url.rsplit("/", 1)[-1]
            object_name, batch_hour = build_object_name(data_type, filename)
            blob = bucket.blob(object_name)

            if blob.exists():
                results[data_type] = {
                    "status": "already_exists",
                    "object": object_name,
                }
                continue

            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "batch.zip")
                download_to_file(
                    session, f"{BASE_URL}/{filename}", zip_path
                )

                if data_type == "gkg":
                    upload_path = os.path.join(temp_dir, "batch.parquet")
                    row_count = write_gkg_parquet(zip_path, upload_path, batch_hour)
                    content_type = "application/vnd.apache.parquet"
                else:
                    # TODO: Convert Events and Mentions CSV to Parquet next.
                    upload_path = zip_path
                    row_count = None
                    content_type = "application/zip"

                try:
                    blob.upload_from_filename(
                        upload_path,
                        content_type=content_type,
                        if_generation_match=0,
                    )
                    status = "uploaded"
                except PreconditionFailed:
                    status = "already_exists"

                results[data_type] = {
                    "status": status,
                    "object": object_name,
                    "format": "parquet" if data_type == "gkg" else "zip",
                }
                if data_type == "gkg":
                    results[data_type]["row_count"] = row_count

    return {"status": "success", "bucket": BUCKET_NAME, "files": results}, 200
