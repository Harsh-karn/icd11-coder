import urllib.request
import zipfile
import os

os.makedirs("data/downloads", exist_ok=True)

for lang in ["es", "fr"]:
    zip_name = f"SimpleTabulation-ICD-11-MMS-{lang}.zip"
    zip_path = os.path.join("data/downloads", zip_name)
    if not os.path.exists(zip_path):
        print(f"Downloading {zip_name}...")
        url = f"https://icdcdn.who.int/static/releasefiles/2026-01/{zip_name}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())
        print(f"Downloaded {zip_name}.")

    with zipfile.ZipFile(zip_path) as z:
        z.extractall("data/downloads")
        print(f"Extracted {zip_name}.")

