"""Safe display projection of a versioned, visually reviewed dog-input registry."""
from pathlib import Path

DISPLAY_FIELDS=('id','label','quality_tier','quality_notes','input','crop','thumbnail','crop_thumbnail','tuning_eligible')
MEDIA_FIELDS=('input','crop','thumbnail','crop_thumbnail')


def identity_crop(row,dogs):
    """Keep each historical output bound to the exact source crop it used."""
    dog=next((d for d in dogs if d['id']==row.get('dog_id')),None)
    name=row.get('identity_crop') or (dog['crop'] if dog else None)
    if name and (not isinstance(name,str) or '/' in name or '\\' in name or Path(name).name!=name):
        raise ValueError('Invalid identity crop name')
    return name


def public_catalog(registry):
    rows=[]
    for dog in registry.get('dogs',[]):
        if not dog.get('input') or not dog.get('crop'):continue
        if any(not isinstance(dog[k],str) or '/' in dog[k] or '\\' in dog[k] or Path(dog[k]).name!=dog[k] for k in MEDIA_FIELDS if dog.get(k)):
            raise ValueError('Registry media must use basenames')
        rows.append({k:dog[k] for k in DISPLAY_FIELDS if k in dog})
    return dict(version=registry.get('version'),dogs=rows,total=len(rows),
                clear=sum(d.get('quality_tier')=='clear' for d in rows),
                challenging=sum(d.get('quality_tier')=='challenging' for d in rows))
