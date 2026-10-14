"""Accept one complete qualifying-dog round when its mean score is at least eight."""
import copy
from portrait_autorefine import signature
from portrait_llm_planner import BOUNDS

POLICY='qualified-inputs-average-v5'
AVERAGE_TARGET=8
PASS_PERCENT=85

def required_passes(total):return (total*PASS_PERCENT+99)//100

def score_values(candidate):
    values=[]
    for evidence in candidate['checks'].values():
        if evidence.get('recipe_sha256')!=candidate['recipe_sha256']:raise ValueError('Mixed recipe evidence')
        for key in ('identity','fur','body','template'):
            value=evidence['assessment'].get(key)
            if type(value) is not int or not 1<=value<=10:raise ValueError('Missing or invalid score')
            values.append(value)
    return values


def round_average(candidate):
    values=score_values(candidate)
    return sum(values)/len(values) if values else None


def set_passes(state):
    candidate=state['candidates'][-1]
    if set(candidate['checks'])!=set(state['roster']) or not state['roster']:return False
    values=score_values(candidate)
    return sum(values)>=AVERAGE_TARGET*len(values)

THRESHOLDS=dict(identity=8,fur=8,body=7,template=8)


def meets_target(assessment):
    return (assessment.get('confidence')=='high'
            and all(type(assessment.get(k)) is int and minimum<=assessment[k]<=10 for k,minimum in THRESHOLDS.items())
            and not any(d.get('severity')=='major' for d in assessment.get('defects',[])))
RECIPE_FIELDS=(*BOUNDS,'strategy','pose_policy','focus','instruction')


def functional_recipe(recipe):return {k:recipe[k] for k in RECIPE_FIELDS if k in recipe}


def recipe_hash(recipe):return signature(functional_recipe(recipe))


def new_candidate(state,recipe):
    if state.get('locked'):raise ValueError('Locked workflow is immutable')
    digest=recipe_hash(recipe)
    if any(c['recipe_sha256']==digest for c in state['candidates']):raise ValueError('Duplicate functional recipe')
    item=dict(recipe=copy.deepcopy(recipe),recipe_sha256=digest,checks={})
    state['candidates'].append(item);return item


def record_check(candidate,dog,assessment,row):
    if assessment.get('dog_id')!=dog:raise ValueError('Assessment belongs to a different dog')
    if assessment.get('output_sha256')!=row['output_sha256']:raise ValueError('Assessment belongs to a different output')
    evidence=dict(assessment=copy.deepcopy(assessment),row_id=row['id'],output_sha256=row['output_sha256'],
                  prompt_id=row['prompt_id'],graph_sha256=row['graph_sha256'],recipe_sha256=candidate['recipe_sha256'])
    if dog in candidate['checks'] and candidate['checks'][dog]!=evidence:raise ValueError('Do not replace an earlier check')
    candidate['checks'][dog]=evidence


def passing(candidate):
    return {d for d,e in candidate['checks'].items() if e['recipe_sha256']==candidate['recipe_sha256'] and meets_target(e['assessment'])}


def next_dog(state):
    candidate=state['candidates'][-1]
    if set_passes(state):return None
    unchecked=[d for d in state['roster'] if d not in candidate['checks']]
    if unchecked:
        return next((d for d in unchecked if state.get('visit_attempts',{}).get(d,0)<6),None)
    pending=sorted(state['roster'],key=lambda d:sum(candidate['checks'][d]['assessment'][k] for k in ('identity','fur','body','template')))
    focus=state.get('focus_dog')
    if focus in pending:pending.remove(focus);pending.insert(0,focus)
    return next((d for d in pending if state.get('visit_attempts',{}).get(d,0)<6),None)


def export_locked(state,template,graph):
    """Separate format: known-roster development evidence, never holdout proof."""
    candidate=state['candidates'][-1];roster=state['roster']
    if candidate['recipe_sha256']!=recipe_hash(candidate['recipe']):raise ValueError('Candidate recipe changed after scoring')
    if len(roster)<7 or len(set(roster))!=len(roster):raise ValueError('Invalid roster')
    if not set(candidate['checks']).issubset(roster) or not set_passes(state):raise ValueError('A complete qualifying round must average at least 8 on the same recipe')
    for dog,e in candidate['checks'].items():
        if e['assessment'].get('dog_id')!=dog or e['assessment'].get('output_sha256')!=e['output_sha256'] or not all(e.get(k) for k in ('row_id','output_sha256','prompt_id','graph_sha256')):
            raise ValueError('Missing bound evidence')
    if len({e['prompt_id'] for e in candidate['checks'].values()})!=len(candidate['checks']):raise ValueError('Native job evidence reused across dogs')
    graph=copy.deepcopy(graph)
    bindings={'76':'__DOG_ORIGINAL__','detailimage':'__DOG_FACE__','81':'__COSTUME_REFERENCE__','repair-base':'__TEMPLATE_LAYOUT__','repair-mask':'__SUBJECT_MASK__'}
    for key,value in bindings.items():graph[key]['inputs']['image']=value
    graph['9']['inputs']['filename_prefix']='__OUTPUT_PREFIX__';graph['92:105']['inputs']['noise_seed']='__DOG_SEED__'
    graph['92:113']['inputs']['text']='__DOG_NEUTRAL_REPAIR_PROMPT__'
    graph={k:{'class_type':v['class_type'],'inputs':v['inputs']} for k,v in graph.items()}
    for node in graph.values():
        if node['class_type'] in ('LoadImage','LoadImageMask'):
            name=node['inputs']['image']
            if not (name.startswith('__') and name.endswith('__')):raise ValueError('Private image remains in graph')
    quality=state.get('input_quality',{})
    from portrait_input_quality import eligible
    if not all(eligible(quality.get(d,{})) for d in roster):raise ValueError('Each qualifying input must score at least 7')
    result=dict(format='consistent-pet-average-recipe-v1',template_id=template['id'],status='locked_on_average',thresholds={'round_average':AVERAGE_TARGET},
                recipe=functional_recipe(candidate['recipe']),scene=template['scene'],clothing=template['clothing'],graph=graph,
                evaluation=dict(policy=POLICY,roster_entries=len(roster),passing_entries=len(passing(candidate)),checked_entries=len(candidate['checks']),average_score=round_average(candidate),score_sum=sum(score_values(candidate)),score_count=len(score_values(candidate)),required_average=AVERAGE_TARGET,same_recipe_for_all=True,
                                unseen_dog_validation=False,ai_estimate_only=True,input_minimum=7,
                                excluded_input_entries=state.get('excluded_input_entries',0)),production_enabled=False,
                binding='Bind original dog, real face crop, reference assets and seed through repair_graph and apply_recipe. Do not add dog-specific review corrections.')
    result['sha256']=signature(result);return result
