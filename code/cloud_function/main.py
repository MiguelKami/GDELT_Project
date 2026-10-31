import os
import requests
import functions_framework

@functions_framework.http
def ingest_gdelt(request):

    base_url = "https://data.gdeltproject.org/gdeltv2"

    response = requests.get(
        f"{base_url}/lastupdate.txt",
        timeout=30
    )

    response.raise_for_status()

    return response.text, 200, {
        "Content-Type": "text/plain"
    }
