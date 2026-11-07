import json
import csv
import os

print("Building enriched ICD-11 MMS database...")

# 1. Load original mms-2026-01.json
with open("data/mms-2026-01.json", encoding="utf-8") as f:
    mms_list = json.load(f)
mms_dict = {item["code"]: item for item in mms_list}

# Helper to clean titles
def clean_title(t):
    if not t:
        return ""
    t = t.strip().strip('\"')
    return t.lstrip('- ').strip()

# 2. Parse English blocks and details
blocks_en = {}
details_en = {}
with open("data/downloads/SimpleTabulation-ICD-11-MMS-en.txt", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for r in reader:
        bid = (r.get("BlockId") or "").strip()
        code = (r.get("Code") or "").strip()
        title = clean_title(r.get("Title"))
        kind = (r.get("ClassKind") or "").strip()
        ch = (r.get("ChapterNo") or "").strip()
        if kind == "chapter" and ch:
            blocks_en[ch] = title
        elif bid:
            blocks_en[bid] = title
        if code:
            details_en[code] = r

# 3. Parse Spanish blocks and details
blocks_es = {}
details_es = {}
with open("data/downloads/SimpleTabulation-ICD-11-MMS-es.txt", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for r in reader:
        bid = (r.get("BlockId") or "").strip()
        code = (r.get("Code") or "").strip()
        title = clean_title(r.get("Title"))
        kind = (r.get("ClassKind") or "").strip()
        ch = (r.get("ChapterNo") or "").strip()
        if kind == "chapter" and ch:
            blocks_es[ch] = title
        elif bid:
            blocks_es[bid] = title
        if code:
            details_es[code] = r

# 4. Parse French blocks and details
blocks_fr = {}
details_fr = {}
with open("data/downloads/SimpleTabulation-ICD-11-MMS-fr.txt", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for r in reader:
        bid = (r.get("BlockId") or "").strip()
        code = (r.get("Code") or "").strip()
        title = clean_title(r.get("Title"))
        kind = (r.get("ClassKind") or "").strip()
        ch = (r.get("ChapterNo") or "").strip()
        if kind == "chapter" and ch:
            blocks_fr[ch] = title
        elif bid:
            blocks_fr[bid] = title
        if code:
            details_fr[code] = r

# 5. Build enriched records for each code
enriched = []
for code, orig in mms_dict.items():
    r_en = details_en.get(code, {})
    r_es = details_es.get(code, {})
    r_fr = details_fr.get(code, {})
    
    ch = orig.get("chapter", r_en.get("ChapterNo", ""))
    ch_title_en = blocks_en.get(ch, "")
    ch_title_es = blocks_es.get(ch, "")
    ch_title_fr = blocks_fr.get(ch, "")
    
    # Hierarchy path English
    path_en = []
    if ch_title_en:
        path_en.append(ch_title_en)
    for g in ["Grouping1", "Grouping2", "Grouping3", "Grouping4", "Grouping5"]:
        gid = (r_en.get(g) or "").strip()
        if gid and gid in blocks_en:
            t = blocks_en[gid]
            if t not in path_en:
                path_en.append(t)

    # Hierarchy path Spanish
    path_es = []
    if ch_title_es:
        path_es.append(ch_title_es)
    for g in ["Grouping1", "Grouping2", "Grouping3", "Grouping4", "Grouping5"]:
        gid = (r_es.get(g) or "").strip()
        if gid and gid in blocks_es:
            t = blocks_es[gid]
            if t not in path_es:
                path_es.append(t)

    # Hierarchy path French
    path_fr = []
    if ch_title_fr:
        path_fr.append(ch_title_fr)
    for g in ["Grouping1", "Grouping2", "Grouping3", "Grouping4", "Grouping5"]:
        gid = (r_fr.get(g) or "").strip()
        if gid and gid in blocks_fr:
            t = blocks_fr[gid]
            if t not in path_fr:
                path_fr.append(t)

    title_en = clean_title(orig.get("title") or r_en.get("Title"))
    title_es = clean_title(r_es.get("Title")) or title_en
    title_fr = clean_title(r_fr.get("Title")) or title_en
    
    is_leaf = orig.get("leaf", (r_en.get("isLeaf") == "True"))
    is_residual = orig.get("residual", (r_en.get("IsResidual") == "True"))
    coding_note = (r_en.get("CodingNote") or "").strip()

    # Search text combines title, hierarchy, and translations
    search_parts = [
        f"Code {code}: {title_en}",
        f"Hierarchy: {' > '.join(path_en)}"
    ]
    if title_es and title_es != title_en:
        search_parts.append(f"ES: {title_es}")
    if title_fr and title_fr != title_en:
        search_parts.append(f"FR: {title_fr}")
    if coding_note:
        search_parts.append(f"Note: {coding_note}")

    search_text = " | ".join(search_parts)

    entry = {
        "code": code,
        "title": title_en,
        "title_es": title_es,
        "title_fr": title_fr,
        "chapter": ch,
        "chapter_title": ch_title_en,
        "hierarchy": path_en,
        "hierarchy_es": path_es,
        "hierarchy_fr": path_fr,
        "leaf": is_leaf,
        "residual": is_residual,
        "coding_note": coding_note,
        "search_text": search_text
    }
    enriched.append(entry)

out_path = "data/enriched_mms.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(enriched, f, indent=2, ensure_ascii=False)

print(f"Enriched database written to {out_path} with {len(enriched)} entries.")
print(f"Sample entry (1F40.Z):\n{json.dumps([x for x in enriched if x['code'] == '1F40.Z'][0], indent=2)}")
