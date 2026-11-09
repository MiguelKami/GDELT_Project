
import os
import requests
import functions_framework

from google.cloud import storage
from google.api_core.exceptions import PreconditionFailed

BASE_URL = os.environ.get(
    "GDELT_BASE_URL",
    "https://data.gdeltproject.org/gdeltv2"
).rstrip("/")

BUCKET_NAME = os.environ["RAW_BUCKET"]

FILE_TYPES = {
#    "events": ".export.CSV.zip",
#    "mentions": ".mentions.CSV.zip",
    "gkg": ".gkg.csv.zip"
}


@functions_framework.http
def ingest_gdelt(request):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    response = requests.get(
        f"{BASE_URL}/lastupdate.txt",
        timeout=30
    )
    response.raise_for_status()

    lines = response.text.strip().splitlines()

    results = {}

    for data_type, suffix in FILE_TYPES.items():
        matching_urls = [
            line.split()[-1]
            for line in lines
            if line.split()[-1].endswith(suffix)
        ]

        if not matching_urls:
            raise ValueError(
                f"No GDELT file found for {data_type}"
            )

        filename = matching_urls[0].split("/")[-1]
        source_url = f"{BASE_URL}/{filename}"
        object_name = f"{data_type}/{filename}"

        blob = bucket.blob(object_name)

        if blob.exists():
            results[data_type] = "already_exists"
            continue

        file_response = requests.get(
            source_url,
            timeout=(10, 180)
        )
        file_response.raise_for_status()

        try:
            blob.upload_from_string(
                file_response.content,
                content_type="application/zip",
                if_generation_match=0
            )
            results[data_type] = "uploaded"

        except PreconditionFailed:
            results[data_type] = "already_exists"

    return {
        "status": "success",
        "bucket": BUCKET_NAME,
        "files": results
    }, 200
