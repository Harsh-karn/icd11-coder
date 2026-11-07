import urllib.request
import json

urls = [
    "https://id.who.int/icd/release/11/mms/257068234",
    "https://icd.who.int/browse/latestrelease/mms/en/json?id=257068234",
    "https://icd.who.int/browse/latestrelease/mms/en/GetConceptDetails?id=257068234",
    "https://icd.who.int/browse/latestrelease/mms/en/GetConceptDetails?conceptId=257068234",
    "https://icd.who.int/browse2026-01/mms/en/GetConceptDetails?id=257068234"
]

for url in urls:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "API-Version": "v2"
            }
        )
        res = urllib.request.urlopen(req, timeout=4)
        data = res.read()
        print(f"URL: {url} -> Status {res.status}, Len {len(data)}")
        try:
            parsed = json.loads(data)
            print("  Keys:", list(parsed.keys())[:10])
        except Exception:
            print("  Sample:", data[:150])
    except Exception as e:
        print(f"URL: {url} -> {e}")

