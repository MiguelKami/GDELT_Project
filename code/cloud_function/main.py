import io
import zipfile
import requests
import pandas as pd

BASE_URL = "http://data.gdeltproject.org/gdeltv2"
MANIFEST_URL = f"{BASE_URL}/lastupdate.txt"

response = requests.get(MANIFEST_URL, timeout=30)
response.raise_for_status()

arquivos = response.text.strip().splitlines()

url_eventos = next(
    linha.split()[-1]
    for linha in arquivos
    if linha.split()[-1].endswith(".export.CSV.zip")
)

print(f"Arquivo encontrado: {url_eventos}")

response = requests.get(url_eventos, timeout=120)
response.raise_for_status()

with zipfile.ZipFile(io.BytesIO(response.content)) as arquivo_zip:
    nome_csv = arquivo_zip.namelist()[0]

    with arquivo_zip.open(nome_csv) as arquivo:
        df = pd.read_csv(
            arquivo,
            sep="\t",
            header=None,
            low_memory=False
        )

print(df.head())

df.to_csv("gdelt_events.csv", index=False, header=False)