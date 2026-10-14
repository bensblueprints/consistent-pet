"""Read-only check of installed native nodes, model filenames and local judge."""
import json
import os
from pathlib import Path
import requests
from portrait_body_repair import segmentation_graph
from portrait_reviews import ROOT

api=os.environ.get('COMFY_API','http://127.0.0.1:18188').rstrip('/')
reply=requests.get(api+'/object_info',timeout=30);reply.raise_for_status();available=reply.json()
graph=json.loads((Path(__file__).resolve().parents[1]/'workflows/flux-klein-4b-base-api.json').read_text())
graph.update({'sam-'+k:v for k,v in segmentation_graph('fixture.png','fixture.png','jacket','preflight').items()})
errors=[]
for kind in ('VAEEncodeForInpaint','LoadImageMask','ImageCompositeMasked'):
    if kind not in available:errors.append('Missing node: '+kind)
for node in graph.values():
    kind=node['class_type']
    if kind not in available:errors.append('Missing node: '+kind);continue
    inputs=available[kind].get('input',{}).get('required',{})
    for name,value in node['inputs'].items():
        if name in ('ckpt_name','unet_name','clip_name','vae_name'):
            choices=inputs.get(name,[[]])[0]
            if isinstance(choices,list) and value not in choices:errors.append('Missing model: '+value)
spec=ROOT/'judge32-model.json'
if not spec.exists():errors.append('Initialize the private runtime and judge32-model.json')
elif not Path(json.loads(spec.read_text())['path']).is_dir():errors.append('Local judge model directory is missing')
if errors:raise SystemExit('\n'.join(sorted(set(errors))))
print('Installed graph nodes, generator model filenames and judge directory are ready. No generation submitted.')
