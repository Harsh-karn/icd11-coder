import urllib.request
import re

url = "https://icd.who.int/browse/2026-01/mms/en"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        print("Status 200, HTML length:", len(html))
        # Look for script urls or endpoints in the html
        scripts = re.findall(r'src=["\']([^"\']+)["\']', html)
        print("Scripts:", scripts[:5])
        # Find any javascript ajax or url patterns
        urls = re.findall(r'["\'](/[a-zA-Z0-9_\-\/]+)["\']', html)
        print("Internal URLs:", [u for u in set(urls) if "json" in u or "mms" in u or "api" in u or "get" in u.lower()][:10])
except Exception as e:
    print("Error:", e)
