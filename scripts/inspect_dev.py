import json

with open("data/mms-2026-01.json", encoding="utf-8") as f:
    mms = {x["code"]: x for x in json.load(f)}

with open("data/dev_notes.jsonl", encoding="utf-8") as f:
    notes = [json.loads(line) for line in f]

print(f"Total dev notes: {len(notes)}")
leaf_count = 0
res_count = 0
total_gold = 0

for i, n in enumerate(notes[:15]):
    gold_descs = []
    for c in n["gold"]:
        total_gold += 1
        item = mms.get(c, {})
        is_leaf = item.get("leaf", False)
        is_res = item.get("residual", False)
        if is_leaf:
            leaf_count += 1
        if is_res:
            res_count += 1
        gold_descs.append(f"{c}: '{item.get('title')}' [leaf={is_leaf}, res={is_res}]")
    print(f"\n[{n['id']}] ({n['style']})")
    snippet = n['text'].replace('\n', ' ')[:120]
    print(f"Text snippet: {snippet}...")
    print(f"Gold: {gold_descs}")

for n in notes[15:]:
    for c in n["gold"]:
        total_gold += 1
        item = mms.get(c, {})
        if item.get("leaf"):
            leaf_count += 1
        if item.get("residual"):
            res_count += 1

print(f"\nGold stats across all {len(notes)} notes:")
print(f"Total gold codes: {total_gold}")
print(f"Leaf codes: {leaf_count}/{total_gold} ({leaf_count/total_gold*100:.1f}%)")
print(f"Residual codes (.Z/.X): {res_count}/{total_gold} ({res_count/total_gold*100:.1f}%)")

