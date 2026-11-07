import urllib.request

candidates = [
    "Index-en.zip",
    "ICD11-Index-en.zip",
    "ICD-11-MMS-Index-en.zip",
    "Index-ICD-11-MMS-en.zip",
    "Index-ICD11-MMS-en.zip",
    "ComprehensiveTabulation-ICD-11-MMS-en.zip",
    "Linearization-ICD-11-MMS-en.zip",
    "LinearizationPrint-ICD-11-MMS-en.zip",
    "LinearizationPrint-ICD-11-en.zip",
    "LinearizationPrint-ICD11-en.zip",
    "SimpleTabulation-ICD-11-MMS-es.zip",
    "SimpleTabulation-ICD-11-MMS-fr.zip",
]

base_url = "https://icdcdn.who.int/static/releasefiles/2026-01/"

for c in candidates:
    url = base_url + c
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = urllib.request.urlopen(req, timeout=4)
        print(f"FOUND: {c} (size: {res.headers.get('Content-Length')})")
    except Exception:
        pass

