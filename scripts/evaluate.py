"""Evaluate candidate coverage and predictions without changing the official scorer."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.retriever import ICD11Retriever

p=argparse.ArgumentParser()
p.add_argument('--notes',default='data/dev_notes.jsonl')
p.add_argument('--output',required=True)
p.add_argument('--bm25-only',action='store_true')
a=p.parse_args()
r=ICD11Retriever(emb_path='/nonexistent' if a.bm25_only else 'data/icd11_embeddings.npy')
notes=[json.loads(l) for l in Path(a.notes).read_text().splitlines() if l.strip()]
hits={k:0 for k in [1,3,5,10,20]}
Path(a.output).parent.mkdir(parents=True,exist_ok=True)
with open(a.output,'w') as out:
    for n in notes:
        c=r.retrieve(n['text'],20)
        for k in hits: hits[k]+=bool(set(n['gold']).intersection(x['code'] for x in c[:k]))
        out.write(json.dumps({'id':n['id'],'codes':r.select_offline(c)})+'\n')
print('Candidate recall', {k:round(v/len(notes),3) for k,v in hits.items()})
subprocess.run([sys.executable,'score.py','--gold',a.notes,'--pred',a.output,'--mms','data/mms-2026-01.json'],check=True)
