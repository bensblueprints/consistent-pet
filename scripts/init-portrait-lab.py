"""Stage operator-supplied dog/reference fixtures into a NEW private runtime.

No generation, model download, network access, or existing-runtime overwrite.
Face crops are supplied by the operator, not invented by a face detector.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from PIL import Image,ImageOps
from portrait_autorefine import dog_splits,validate_plan


def checked_id(value):
    if not isinstance(value,str) or not re.fullmatch('[a-z0-9][a-z0-9-]{0,100}',value):
        raise ValueError('IDs must contain lowercase letters, digits and hyphens')
    return value


def initialize(manifest_path,root,graph_path):
    root=root.resolve()
    if root.exists():raise ValueError('Runtime already exists; initialization never overwrites it')
    manifest=json.loads(manifest_path.read_text())
    graph=json.loads(graph_path.read_text())
    required=('76','detailimage','81','92:113','92:115','92:110','detailscale','92:85','9')
    if any(k not in graph for k in required):raise ValueError('Unsupported baseline API graph')
    judge=manifest['judge']
    if not all(isinstance(judge.get(k),str) and judge[k] for k in ('path','model','revision')):
        raise ValueError('Judge needs local path, model ID and pinned revision')
    if not Path(judge['path']).is_dir():raise ValueError('Install the local judge weights first')
    raw_dogs=manifest['dogs'];raw_templates=manifest['templates']
    for items in (raw_dogs,raw_templates):
        if len({checked_id(item['id']) for item in items})!=len(items):raise ValueError('Duplicate IDs')
    root.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.portrait-setup-',dir=root.parent) as temporary:
        staged=Path(temporary)/'runtime';staged.mkdir();media=staged/'media';media.mkdir()
        jobs=staged/'dog-library-jobs';jobs.mkdir()
        def copy_image(source,name):
            path=Path(source)
            if not path.is_absolute():path=manifest_path.parent/path
            raw=path.read_bytes()
            with Image.open(path) as image:
                ImageOps.exif_transpose(image).convert('RGB').save(media/name)
            return hashlib.sha256(raw).hexdigest()
        dogs=[]
        for dog in raw_dogs:
            identity=checked_id(dog['id']);original=identity+'-original.png';crop=identity+'-face.png'
            source_sha=copy_image(dog['original'],original);copy_image(dog['face'],crop)
            dogs.append(dict(id=identity,label=dog['label'],input=original,crop=crop,source_sha256=source_sha))
        splits=dog_splits(dogs)
        preferred=next(d for d in dogs if d['id']==splits['train'][0])
        rows=[];templates=[]
        for item in raw_templates:
            identity=checked_id(item['id']);reference=identity+'-reference.png'
            copy_image(item['reference'],reference)
            row_id='dogs10-full-library-bootstrap-'+identity
            row=dict(id=row_id,dog_id=preferred['id'],label=preferred['label'],input=preferred['input'],
                     reference=reference,template=item['title'],pack=item.get('pack','custom'),category=item.get('category','custom'),
                     status='Reference ready',mode='Reference template',index=len(rows))
            rows.append(row)
            native=copy.deepcopy(graph)
            for key,value in [('76',preferred['input']),('detailimage',preferred['crop']),('81',reference)]:native[key]['inputs']['image']=value
            native['92:113']['inputs']['text']='Reference fixture; the refinement runner builds the actual prompt.'
            native['92:87']['inputs']['text']=''
            native['9']['inputs']['filename_prefix']='consistent-pet/'+identity
            (jobs/(row_id+'.json')).write_text(json.dumps(native,indent=2))
            templates.append(dict(id=identity,source_row=row_id,clothing=item['clothing'],scene=item['scene'],require_clothing=item.get('require_clothing',True)))
        plan=validate_plan(dict(version=manifest.get('version','auto-repair-v1'),max_attempts=manifest.get('max_attempts',8),
            patience=manifest.get('max_attempts',8),max_generations=manifest.get('max_generations',90),
            max_hours=manifest.get('max_hours',6),templates=templates))
        for name,value in [('selected-dogs.json',{'dogs':dogs}),('dog-library-batch.json',{'rows':rows,'status':'References staged'}),
                           ('dog-batch.json',{'rows':[]}),('dog-revisions.json',{'rows':[]}),('judge32-model.json',judge),('plan.json',plan)]:
            (staged/name).write_text(json.dumps(value,indent=2))
        os.replace(staged,root)
    return dict(runtime=str(root),dogs=len(dogs),templates=len(templates),splits=splits,generations_submitted=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--graph',type=Path,default=Path(__file__).resolve().parents[1]/'workflows/flux-klein-4b-base-api.json')
    args=parser.parse_args();print(json.dumps(initialize(args.manifest,args.root,args.graph),indent=2))
