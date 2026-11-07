import urllib.request
import re

url = "https://icd.who.int/browse/ect/icd11ect-1.8.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
        print("ect.js length:", len(content))
        urls = re.findall(r'https?://[a-zA-Z0-9_\-\./]+', content)
        print("HTTP URLs:", set(urls))
        paths = re.findall(r'["\'](/[a-zA-Z0-9_\-\./]+)["\']', content)
        interesting = [p for p in set(paths) if any(w in p.lower() for w in ["search", "concept", "detail", "mms", "icd"])]
        print("Paths:", interesting[:10])
except Exception as e:
    print("Error:", e)

