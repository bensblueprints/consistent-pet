"""Export a validated, generic workflow without private evaluation assets."""
import argparse
import copy
import json
from pathlib import Path
from portrait_autorefine import meets_target,signature


def sanitized(item):
    if item.get('status')!='AI target met across dogs':raise ValueError('Only accepted workflows can be exported')
    frozen=item['workflow']
    if frozen.get('recipe_sha256')!=signature({k:v for k,v in frozen.items() if k!='recipe_sha256'}):
        raise ValueError('Frozen workflow checksum differs')
    seen=set()
    for stage,amount in [('tuning',2),('validation',3),('test',2)]:
        reviews=item[stage] if stage=='tuning' else item['scores'][stage]
        ids=[r.get('dog_id') for r in reviews]
        group=frozen['tune_dogs' if stage=='tuning' else stage+'_dogs']
        if len(reviews)!=amount or not all(meets_target(r) for r in reviews):raise ValueError('Required assessments did not pass')
        if None in ids or len(set(ids))!=amount or set(ids)!=set(group) or seen&set(ids):
            raise ValueError('Evaluation identities overlap or do not match the frozen groups')
        seen.update(ids)
    graph={k:{'class_type':v['class_type'],'inputs':copy.deepcopy(v['inputs'])} for k,v in frozen['graph'].items()}
    for node in graph.values():
        if node['class_type'] in ('LoadImage','LoadImageMask'):
            value=node['inputs']['image']
            if not (value.startswith('__') and value.endswith('__')):raise ValueError('Graph contains a bound private image')
    recipe={k:frozen['recipe'][k] for k in ('version','steps','cfg','grow','feather','original_megapixels','face_megapixels','design_megapixels','focus','instruction')}
    result=dict(format='consistent-pet-api-recipe-v1',template_id=frozen['template_id'],target=9,
                scene=frozen['scene'],clothing=frozen['clothing'],recipe=recipe,graph=graph,
                status='AI target met across dogs',evaluation=dict(tuning_dogs=2,validation_dogs=3,test_dogs=2,ai_estimate_only=True),
                binding='Use repair_graph, dog_instruction and apply_recipe with operator-supplied private reference assets.')
    result['sha256']=signature(result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--accepted',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=sanitized(json.loads(args.accepted.read_text()))
    with args.output.open('x',encoding='utf-8') as destination:json.dump(result,destination,indent=2)
    print('Exported accepted generic workflow; no evaluation photos or dog identifiers included.')
