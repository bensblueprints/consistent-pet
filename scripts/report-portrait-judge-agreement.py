"""Measure current AI estimates against genuine human reviews before adaptation.

This is evaluation only. It never tunes a model, overwrites labels, or treats
unreviewed AI scores as ground truth. Exported held-out identities stay separate.
"""
import json
import statistics
from pathlib import Path

from portrait_reviews import ROOT


def summarize(records):
    matched=[]
    for item in records:
        ai=item.get('ai_estimate') or {}
        if ai.get('output_sha256')!=item['image_hashes']['output']:continue
        if not isinstance(ai.get('score'),(int,float)):continue
        matched.append(dict(id=item['id'],dog_id=item['dog_id'],human=item['human_score'],
                            ai=ai['score'],error=round(ai['score']-item['human_score'],2),
                            notes=item['human_notes'],rubric=ai.get('rubric')))
    return dict(count=len(matched),
                mean_absolute_error=round(statistics.mean(abs(r['error']) for r in matched),3) if matched else None,
                mean_signed_error=round(statistics.mean(r['error'] for r in matched),3) if matched else None,
                within_one_point=sum(abs(r['error'])<=1 for r in matched),
                disagreements=sorted(matched,key=lambda r:abs(r['error']),reverse=True))


def report(directory):
    splits={name:[json.loads(line) for line in (directory/(name+'.jsonl')).read_text().splitlines()]
            for name in ('train','validation','test')}
    result=dict(kind='Pretrained judge agreement with current human labels; no adaptation',
                overall=summarize([row for rows in splits.values() for row in rows]),
                splits={name:summarize(rows) for name,rows in splits.items()},
                note='Small, selectively reviewed sample. These errors are descriptive, not proof of generalization. Preserve held-out dog identities for a later controlled comparison.')
    all_records=[row for rows in splits.values() for row in rows]
    rubrics=sorted({r['ai_estimate'].get('rubric','unknown') for r in all_records if r.get('ai_estimate')})
    result['by_rubric']={rubric:summarize([r for r in all_records if (r.get('ai_estimate') or {}).get('rubric')==rubric]) for rubric in rubrics}
    result['mixed_rubrics']=len(rubrics)>1
    if result['mixed_rubrics']:result['note']+=' Re-review is in progress: use by_rubric metrics; the overall summary mixes scoring methods.'
    temp=directory/'judge-agreement.tmp';temp.write_text(json.dumps(result,indent=2));temp.replace(directory/'judge-agreement.json')
    print(json.dumps({k:v for k,v in result['overall'].items() if k!='disagreements'},indent=2))
    return result


if __name__=='__main__':report(ROOT/'training-feedback')
