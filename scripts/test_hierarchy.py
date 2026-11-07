import csv

blocks = {}
categories = {}
with open('data/downloads/SimpleTabulation-ICD-11-MMS-en.txt', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for row in reader:
        bid = (row.get('BlockId') or '').strip()
        code = (row.get('Code') or '').strip()
        title = (row.get('Title') or '').strip().strip('\"').lstrip('- ')
        kind = (row.get('ClassKind') or '').strip()
        if kind == 'chapter':
            blocks[row.get('ChapterNo', '')] = title
        elif bid:
            blocks[bid] = title
        if code:
            categories[code] = row

print(f'Total blocks/chapters: {len(blocks)}')
print(f'Total categories: {len(categories)}')

# Let's inspect category 1A00, CA23.30, 1F40.Z
for sample in ['1A00', 'CA23.30', '1F40.Z', 'CA40.Z', '1A07.Z', 'CA07.0']:
    r = categories.get(sample, {})
    ancestors = []
    ch = r.get('ChapterNo')
    if ch in blocks:
        ancestors.append(f"Chapter {ch}: {blocks[ch]}")
    for g in ['Grouping1', 'Grouping2', 'Grouping3', 'Grouping4', 'Grouping5']:
        gid = r.get(g, '')
        if gid and gid in blocks:
            ancestors.append(blocks[gid])
    print(f"\nCode {sample}:")
    print(f"  Title: {r.get('Title', '').strip('\"').lstrip('- ')}")
    print(f"  Hierarchy: {' -> '.join(ancestors)}")
    print(f"  isLeaf: {r.get('isLeaf')}, IsResidual: {r.get('IsResidual')}")
