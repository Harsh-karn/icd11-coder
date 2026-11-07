import json
import csv

with open("data/mms-2026-01.json", encoding="utf-8") as f:
    mms = json.load(f)
mms_codes = {x["code"] for x in mms}

tab_en = {}
with open("data/downloads/SimpleTabulation-ICD-11-MMS-en.txt", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for r in reader:
        c = (r.get("Code") or "").strip()
        if c:
            tab_en[c] = r

tab_es = {}
with open("data/downloads/SimpleTabulation-ICD-11-MMS-es.txt", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for r in reader:
        c = (r.get("Code") or "").strip()
        if c:
            tab_es[c] = r

tab_fr = {}
with open("data/downloads/SimpleTabulation-ICD-11-MMS-fr.txt", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for r in reader:
        c = (r.get("Code") or "").strip()
        if c:
            tab_fr[c] = r

print(f"Total MMS codes: {len(mms_codes)}")
print(f"EN SimpleTabulation matched: {len(mms_codes.intersection(tab_en.keys()))} / {len(mms_codes)}")
print(f"ES SimpleTabulation matched: {len(mms_codes.intersection(tab_es.keys()))} / {len(mms_codes)}")
print(f"FR SimpleTabulation matched: {len(mms_codes.intersection(tab_fr.keys()))} / {len(mms_codes)}")

missing = mms_codes - tab_en.keys()
if missing:
    print(f"Sample missing: {list(missing)[:5]}")

