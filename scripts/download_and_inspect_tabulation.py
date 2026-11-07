import urllib.request
import zipfile
import os

os.makedirs("data/downloads", exist_ok=True)
zip_path = "data/downloads/SimpleTabulation-ICD-11-MMS-en.zip"

if not os.path.exists(zip_path):
    print("Downloading SimpleTabulation-ICD-11-MMS-en.zip...")
    req = urllib.request.Request(
        "https://icdcdn.who.int/static/releasefiles/2026-01/SimpleTabulation-ICD-11-MMS-en.zip",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as f:
        f.write(resp.read())
    print("Downloaded successfully.")

with zipfile.ZipFile(zip_path) as z:
    names = z.namelist()
    print("Files in zip:", names)
    z.extractall("data/downloads")

# Inspect the extracted text file
txt_files = [f for f in names if f.endswith(".txt")]
if txt_files:
    target = os.path.join("data/downloads", txt_files[0])
    print(f"\nInspecting {target}:")
    with open(target, encoding="utf-8") as f:
        headers = [f.readline().strip() for _ in range(1)]
        first_lines = [f.readline().strip() for _ in range(5)]
    print("Header:", headers)
    print("First rows:")
    for r in first_lines:
        print(r[:200])

