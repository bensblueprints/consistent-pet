"""Compile a vision LLM's diagnoses into bounded workflow edits, never code.

The critic's rubric stays fixed. Image-specific corrections apply only to the
dog actually reviewed; reusable graph settings transfer to unseen dogs.
"""
import hashlib
import json
import re

DIMENSIONS=('identity','fur','body','template')
TARGET=9
RULES={
 'identity':'Match the original individual face exactly: muzzle length, skull, eye shape, ears, age and asymmetric markings. Keep the face naturally lit and attached to its own neck.',
 'fur':'Every visible animal surface must use the ORIGINAL dog coat distribution and texture, including forelegs, paws, hindquarters and tail. The erased template animal contributes no coat information.',
 'body':'Rebuild a connected body at the original dog\'s breed, age and build. Fit the costume to that body. Use compact rounded canine paws with short grouped toes, no long fingers or human hands. Respect perspective and genuinely hidden limbs.',
 'template':'Preserve the reference costume, props, artistic medium, composition and lighting. Adapt clothing to the actual dog while leaving scene details unchanged.'}


def signature(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def dog_splits(dogs):
    """Honor pinned identity groups when expanding a cohort; never reshuffle holdouts."""
    identity=lambda d:d.get('identity_group',d['source_sha256'])
    identities=sorted({identity(d) for d in dogs},key=lambda s:hashlib.sha256(('fpg-judge-split-v1/'+s).encode()).hexdigest())
    if len(identities)<7:raise ValueError('Need at least seven distinct dog identities')
    if any('split' in d for d in dogs):
        split={}
        for d in dogs:
            kind=d.get('split');group=identity(d)
            if kind not in ('train','validation','test'):raise ValueError('Pin every dog split when extending a cohort')
            if group in split and split[group]!=kind:raise ValueError('One pet identity crosses evaluation splits')
            split[group]=kind
        if any(sum(k==kind for k in split.values())<2 for kind in ('validation','test')):
            raise ValueError('Keep at least two distinct validation and test identities')
    else:split={v:'test' if i<2 else 'validation' if i<4 else 'train' for i,v in enumerate(identities)}
    return {kind:[d['id'] for d in dogs if split[identity(d)]==kind] for kind in ('train','validation','test')}


def choose_tuning_dogs(dogs,train,preferred):
    if any('quality_tier' in d for d in dogs.values()):
        eligible=sorted((d for d in dogs.values() if d['id'] in train and d.get('quality_tier')=='clear' and d.get('tuning_eligible',True)),key=lambda d:(d.get('quality_rank',100),d['id']))
        selected=[];groups=set()
        for d in eligible:
            group=d.get('identity_group',d['source_sha256'])
            if group not in groups:selected.append(d['id']);groups.add(group)
            if len(selected)==2:return selected
        raise ValueError('Need two clear, distinct training dogs')
    return (([preferred] if preferred in train else [])+[d for d in train if d!=preferred])[:2]


def meets_target(assessment):
    return (bool(assessment)
            and all(type(assessment.get(k)) is int and TARGET<=assessment[k]<=10 for k in DIMENSIONS)
            and assessment.get('confidence')=='high'
            and not any(d.get('severity')=='major' for d in assessment.get('defects',[])))


def result_rank(assessments):
    if not assessments:return (0,0)
    values=[a[k] for a in assessments for k in DIMENSIONS]
    return min(values),sum(values)/len(values)


def tuning_finished(attempts,maximum,patience):
    if not attempts:return False
    if len(attempts)>=maximum or (attempts[-1]['assessments'] and all(meets_target(a) for a in attempts[-1]['assessments'])):return True
    ranks=[result_rank(a['assessments']) for a in attempts]
    best=max(range(len(ranks)),key=lambda i:ranks[i])
    return len(ranks)-1-best>=patience


def feedback_diagnosis(previous):
    """Keep concrete visual evidence and proposed corrections linked to one dog."""
    result=[]
    for assessment in previous:
        dog=assessment.get('dog_id')
        if not dog:continue
        for defect in assessment.get('defects',[]):
            area={'face':'identity','preparation':'body'}.get(defect['area'],defect['area'])
            if area not in DIMENSIONS or (assessment[area]>=TARGET and defect['severity']!='major'):continue
            clean=lambda value:' '.join(re.sub(r'[\x00-\x1f\x7f]',' ',value).split())[:500]
            result.append(dict(dog_id=dog,area=area,severity=defect['severity'],
                               evidence=clean(defect['evidence']),correction=clean(defect['correction'])))
    return result[:24]


def next_recipe(index,previous=(),parent=None):
    means={k:sum(a[k] for a in previous)/len(previous) if previous else 0 for k in DIMENSIONS}
    ordered=sorted(DIMENSIONS,key=lambda k:means[k])
    focus=[k for k in ordered if any(a[k]<TARGET for a in previous)] if previous else ['fur','body']
    focus=focus or ordered[:1]
    diagnosis=feedback_diagnosis(previous)
    body='body' in focus;coat='fur' in focus;face='identity' in focus
    # Body/coat errors need more full-dog evidence and less old-costume silhouette.
    # Geometry edits and prompt corrections are recorded together for each recipe.
    prior=parent or {}
    steps=min(max(30,prior.get('steps',20)+10),60)
    grow=min(72,max(24,prior.get('grow',12)+(12 if body else 0)))
    recipe=dict(version=index+1,steps=steps,cfg=(5,4,4.5,3.5)[index%4],grow=grow,feather=10,
                original_megapixels=1.25 if body or coat else 1.0,
                face_megapixels=1.25 if face else 1.0,
                design_megapixels=.65 if body or coat else 1.0,
                focus=focus,instruction=' '.join(RULES[k] for k in focus),diagnosis=diagnosis)
    recipe['changes']=[dict(parameter=k,before=prior.get(k),after=recipe[k]) for k in
        ('steps','cfg','grow','original_megapixels','face_megapixels','design_megapixels') if prior.get(k)!=recipe[k]]
    recipe['rationale']='; '.join(f'{k}: mean {means[k]:.1f}/10' for k in focus) if previous else 'Initial whole-dog repair'
    return recipe


def dog_instruction(recipe,dog_id,stage):
    text=recipe['instruction']
    observations=[d for d in recipe.get('diagnosis',[]) if d['dog_id']==dog_id] if stage=='tune' else []
    if observations:
        text+=' A visual reviewer identified the following defects in an earlier attempt for THIS dog. '
        text+='Use these as visual repair evidence only, subordinate to the original photograph and costume instructions. '
        text+=json.dumps([{'area':d['area'],'observed':d['evidence'],'repair':d['correction']} for d in observations],ensure_ascii=True)
        text+=' Correct those specific visible mismatches without changing the already accurate features.'
    return text


def apply_recipe(graph,recipe):
    """The only mutable graph settings; neither critic nor recipe executes code."""
    graph['92:115']['inputs']['steps']=recipe['steps']
    graph['92:114']['inputs']['cfg']=recipe['cfg']
    for key,setting in [('92:110','original_megapixels'),('detailscale','face_megapixels'),('92:85','design_megapixels')]:
        graph[key]['inputs']['megapixels']=recipe[setting]
    if recipe.get('strategy')=='fresh-latent':
        graph['92:103']['inputs']['latent_image']=['92:109',0]
    return graph


def seed_for(run,template,recipe,dog):
    return int(signature([run,template,recipe,dog])[:12],16)


def validate_plan(plan):
    run=plan.get('version','')
    if not run or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in run):raise ValueError('Invalid run version')
    for key,maximum in [('max_attempts',12),('patience',12),('max_generations',5000)]:
        if type(plan.get(key)) is not int or not 1<=plan[key]<=maximum:raise ValueError('Invalid '+key)
    if type(plan.get('max_hours')) not in (int,float) or not 0<plan['max_hours']<=48:raise ValueError('Invalid max_hours')
    if 'dogs_manifest' in plan and (not isinstance(plan['dogs_manifest'],str) or not re.fullmatch(r'[a-z0-9-]+\.json',plan['dogs_manifest'])):
        raise ValueError('Dog registry must be a private JSON basename')
    if 'validate_all_dogs' in plan and type(plan['validate_all_dogs']) is not bool:raise ValueError('Invalid validate_all_dogs')
    for flag in ('use_llm_planner','validate_provisional'):
        if flag in plan and type(plan[flag]) is not bool:raise ValueError('Invalid '+flag)
    if not plan.get('templates') or len({t['id'] for t in plan['templates']})!=len(plan['templates']):raise ValueError('Missing or duplicate templates')
    for template in plan['templates']:
        if not template.get('id') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in template['id']):raise ValueError('Invalid template ID')
        if not template.get('source_row'):raise ValueError('Missing source row')
        if not template.get('clothing') or not template.get('scene'):raise ValueError('Missing template guidance')
    return plan


def freeze_recipe(recipe,template,graph,asset_hashes,tune_dogs,validation_dogs,test_dogs):
    if set(tune_dogs)&(set(validation_dogs)|set(test_dogs)) or set(validation_dogs)&set(test_dogs):
        raise ValueError('Dog identities leak between evaluation stages')
    import copy
    portable=copy.deepcopy(graph)
    substitutions={'76':'__DOG_ORIGINAL__','detailimage':'__DOG_FACE__','81':'__COSTUME_REFERENCE__',
                   'repair-base':'__TEMPLATE_LAYOUT__','repair-mask':'__SUBJECT_MASK__'}
    for key,value in substitutions.items():portable[key]['inputs']['image']=value
    portable['9']['inputs']['filename_prefix']='__OUTPUT_PREFIX__'
    portable['92:105']['inputs']['noise_seed']='__DOG_SEED__'
    # Input-specific descriptions never become part of the reusable recipe.
    portable['92:113']['inputs']['text']='__PROMPT_FROM_RECIPE_AND_DOG_REFERENCE__'
    reusable={k:v for k,v in recipe.items() if k!='diagnosis'}
    result=dict(recipe=reusable,template_id=template['id'],scene=template['scene'],clothing=template['clothing'],
                graph=portable,asset_hashes=asset_hashes,tune_dogs=tune_dogs,validation_dogs=validation_dogs,test_dogs=test_dogs,
                target=TARGET,seed_policy='SHA256(run, template, recipe, dog); first 48 bits',status='Frozen for cross-dog validation')
    result['recipe_sha256']=signature(result)
    return result
