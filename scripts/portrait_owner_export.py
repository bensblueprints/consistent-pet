"""Export an explicitly owner-approved recipe without claiming an AI pass."""
import copy
from portrait_autorefine import signature
from portrait_roster import functional_recipe


def export_owner_approved(approval,template,graph):
    if approval.get('acceptance_basis')!='explicit_owner_override' or not approval.get('approved_at'):
        raise ValueError('Explicit recorded owner approval required')
    graph=copy.deepcopy(graph)
    for key,value in {'76':'__DOG_ORIGINAL__','detailimage':'__DOG_FACE__','81':'__COSTUME_REFERENCE__','repair-base':'__TEMPLATE_LAYOUT__','repair-mask':'__SUBJECT_MASK__'}.items():
        graph[key]['inputs']['image']=value
    graph['9']['inputs']['filename_prefix']='__OUTPUT_PREFIX__'
    graph['92:105']['inputs']['noise_seed']='__DOG_SEED__'
    graph['92:113']['inputs']['text']='__DOG_NEUTRAL_REPAIR_PROMPT__'
    graph={k:{'class_type':v['class_type'],'inputs':v['inputs']} for k,v in graph.items()}
    for node in graph.values():
        if node['class_type'] in ('LoadImage','LoadImageMask'):
            name=node['inputs']['image']
            if not (name.startswith('__') and name.endswith('__')):raise ValueError('Private image remains')
    result=dict(format='consistent-pet-owner-approved-recipe-v1',status='owner_approved',template_id=template['id'],
        acceptance_basis='explicit_owner_override',ai_acceptance_claim=False,production_enabled=False,
        recipe=functional_recipe(approval['recipe']),scene=template['scene'],clothing=template['clothing'],graph=graph,
        evaluation=dict(roster_entries=len(approval['roster']),checked_entries=approval['ai_checked'],passing_entries=approval['ai_passed'],unseen_dog_validation=False),
        binding='Bind the original dog, real face crop, costume reference, prepared template layout, subject mask and seed. Apply the saved recipe with repair_graph and apply_recipe.')
    result['sha256']=signature(result)
    return result
