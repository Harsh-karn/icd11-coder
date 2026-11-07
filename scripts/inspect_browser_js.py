import urllib.request
import re

url = "https://icd.who.int/browse/js/browser.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
        print("browser.js length:", len(content))
        # Look for ajax or fetch calls
        ajax = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', content)
        print("Ajax URLs:", set(ajax))
        fetches = re.findall(r'fetch\(["\']([^"\']+)["\']', content)
        print("Fetch URLs:", set(fetches))
        # Look for words like getConcept, details, concept
        keywords = re.findall(r'/[a-zA-Z0-9_\-\./]*(?:concept|detail|search|node)[a-zA-Z0-9_\-\./]*', content, re.IGNORECASE)
        print("Keywords:", sorted(set(keywords))[:15])
except Exception as e:
    print("Error:", e)

