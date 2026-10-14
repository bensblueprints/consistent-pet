"""Export real human labels for a future local vision-judge fine-tuning pilot.

This creates a private dataset, not trained weights. It never substitutes AI
scores for human labels. All versions/photos of one dog stay in the same split.
"""
import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from portrait_reviews import ROOT,attach,digest
from portrait_autorefine import dog_splits
from portrait_input_registry import identity_crop


def export(destination):
    destination=destination.resolve();destination.mkdir(parents=True,exist_ok=True)
    selected=json.loads((ROOT/'selected-dogs.json').read_text())['dogs']
    dogs={d['id']:d for d in selected}
    # Group by source identity hash, not output, workflow, or a random artwork split.
    identities=sorted({d['source_sha256'] for d in selected},key=lambda s:hashlib.sha256(('fpg-judge-split-v1/'+s).encode()).hexdigest())
    split_by_identity={identity:('test' if i<2 else 'validation' if i<4 else 'train') for i,identity in enumerate(identities)}
    catalog=ROOT/'input-catalog.json'
    if catalog.exists():
        additional=json.loads(catalog.read_text())['dogs'];groups=dog_splits(additional)
        for dog in additional:
            identity=dog.get('identity_group',dog['source_sha256'])
            split=next(k for k,v in groups.items() if dog['id'] in v)
            if identity in split_by_identity and split_by_identity[identity]!=split:raise ValueError('Historical dog split changed')
            split_by_identity[identity]=split
            if dog['id'] not in dogs:dogs[dog['id']]=dog
    rows={}
    for file in ('dog-baseline.json','dog-batch.json','dog-library-batch.json','dog-revisions.json'):
        if (ROOT/file).exists():
            rows.update({r['id']:r for r in json.loads((ROOT/file).read_text())['rows']})
    records=[]
    for row in attach(list(rows.values())):
        human=row.get('human_review');dog=dogs.get(row.get('dog_id'))
        if not human or not dog:continue
        assets={key:str(ROOT/'media'/row[key]) for key in ('input','reference','output')}
        assets['identity_crop']=str(ROOT/'media'/identity_crop(row,list(dogs.values())))
        if row.get('prepared'):assets['prepared']=str(ROOT/'media'/row['prepared'])
        group=dog.get('identity_group',dog['source_sha256'])
        records.append(dict(id=row['id'],dog_id=dog['id'],identity_group=group,
                            split=split_by_identity[group],images=assets,
                            image_hashes={key:digest(Path(p)) for key,p in assets.items()},
                            workflow_id=row.get('workflow_id'),workflow_sha256=row.get('workflow_sha256'),
                            human_score=human['score'],human_notes=human['notes'],review_id=human['id'],
                            reviewed_at=human['created_at'],ai_estimate=row.get('ai_review')))
    counts=Counter(r['split'] for r in records);rated_dogs={r['dog_id'] for r in records}
    reasons=[]
    if len(records)<40:reasons.append(f'Need at least 40 reviewed outputs for a small pilot; have {len(records)}')
    if len(rated_dogs)<10:reasons.append(f'Need reviews across all 10 evaluation dogs; have {len(rated_dogs)}')
    if not any(r['human_score']<=5 for r in records):reasons.append('Need genuinely poor examples rated by a human')
    if not any(r['human_score']>=8 for r in records):reasons.append('Need genuinely strong examples rated by a human')
    for split in ('train','validation','test'):
        if not counts[split]:reasons.append('No reviewed '+split+' examples')
    for split in ('train','validation','test'):
        path=destination/(split+'.jsonl')
        path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records if r['split']==split),encoding='utf-8')
    report=dict(kind='Human-rated vision judge dataset; no training run',reviewed_outputs=len(records),
                rated_dogs=len(rated_dogs),split_counts=dict(counts),pilot_data_ready=not reasons,
                pending=reasons,training_complete=False,
                note='Pilot readiness is not proof of adequate data or generalization. Keep held-out dog identities out of training and deploy adapted weights only after a measured improvement on untouched test labels.')
    (destination/'readiness.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


def watch(destination):
    """Refresh private labels and agreement metrics as genuine feedback arrives."""
    import fcntl
    import runpy
    reporter=runpy.run_path(str(Path(__file__).with_name('report-portrait-judge-agreement.py')))
    with (ROOT/'feedback-export.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        previous=None
        while True:
            paths=[ROOT/name for name in ('reviews.sqlite3','reviews.sqlite3-wal','dog-batch.json','dog-library-batch.json','dog-revisions.json')]
            fingerprint=[]
            for path in paths:
                try:
                    stat=path.stat();fingerprint.append((stat.st_mtime_ns,stat.st_size))
                except FileNotFoundError:fingerprint.append(None)
            if fingerprint!=previous:
                export(destination);reporter['report'](destination);previous=fingerprint
            time.sleep(15)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'training-feedback');p.add_argument('--watch',action='store_true');args=p.parse_args()
    watch(args.output) if args.watch else export(args.output)
