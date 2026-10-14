"""Whole-subject mask preparation and FLUX repair graphs; no pasted pet pixels.

SAM3 graph follows Comfy-Org's utility_image_segment_sam3 template. FLUX graphs
extend the saved native multi-reference workflow rather than changing its model.
"""
import copy

import numpy as np
from PIL import Image, ImageFilter

SAM_MODEL='sam3.1_multiplex_fp16.safetensors'


def node(kind,**inputs):return dict(class_type=kind,inputs=inputs)


def segmentation_graph(baseline,template,clothing,prefix):
    g={'model':node('CheckpointLoaderSimple',ckpt_name=SAM_MODEL),
       'baseline':node('LoadImage',image=baseline),'template':node('LoadImage',image=template)}
    for key,image,text in [('subject','baseline','dog'),('subject-clothes','baseline',clothing),('animal','template','dog'),('clothes','template',clothing)]:
        g[key+'-text']=node('CLIPTextEncode',clip=['model',1],text=text)
        g[key]=node('SAM3_Detect',model=['model',0],image=[image,0],conditioning=[key+'-text',0],
                    threshold=.35,refine_iterations=2,individual_masks=False)
        g[key+'-image']=node('MaskToImage',mask=[key,0])
        g[key+'-save']=node('SaveImage',images=[key+'-image',0],filename_prefix=prefix+'-'+key)
    return g


def make_masks(subject,animal,clothes,size,grow=24,feather=10,subject_clothes=None,require_clothing=True):
    """Room to redraw the entire body; strip animal evidence from design reference.

    Thresholding and geometry checks fail closed on empty/oversized segmentation.
    Clothing is retained only in the conditioning image, never used as a hard
    body silhouette constraint. Final compositing leaves all unmasked pixels exact.
    """
    def binary(im):return np.asarray(im.convert('L').resize(size,Image.Resampling.BILINEAR))>127
    s,a,c=map(binary,(subject,animal,clothes))
    if not .005<float(s.mean())<.88:raise ValueError('Inspect empty or oversized animal detection')
    # SAM may call only exposed head/paws "dog" in anthropomorphic artwork.
    # Include the separately detected worn costume so the torso can be rebuilt.
    sc=binary(subject_clothes) if subject_clothes is not None else c
    s=s|sc
    coverage=float(s.mean());animal_coverage=float(a.mean())
    if not .02<coverage<.88 or not .02<animal_coverage<.88:raise ValueError('Inspect empty or oversized subject mask')
    minimum=.005 if require_clothing else -1
    if not minimum<float(c.mean())<.8 or not minimum<float(sc.mean())<.8:raise ValueError('Inspect missing or oversized clothing mask')
    fur=a&~c
    if not .02<float(fur.mean())<.8:raise ValueError('Inspect missing or oversized exposed-animal mask')
    hard=Image.fromarray(s.astype('uint8')*255).filter(ImageFilter.MaxFilter(grow*2+1))
    soft=hard.filter(ImageFilter.GaussianBlur(feather))
    # Original silhouette remains fully editable; smoothing expands only the edge.
    mask=Image.fromarray(np.maximum(np.asarray(soft),s.astype('uint8')*255))
    erase=Image.fromarray(fur.astype('uint8')*255).filter(ImageFilter.MaxFilter(13))
    return mask,erase,dict(subject_coverage=round(coverage,4),animal_coverage=round(animal_coverage,4),
                           exposed_animal_coverage=round(float(fur.mean()),4))


def neutral_reference(template,erase):
    return Image.composite(Image.new('RGB',template.size,(127,127,127)),template.convert('RGB'),erase)


def repair_graph(saved_graph,*,original,face,design,baseline,mask,prefix,identity,scene,seed=572319):
    g=copy.deepcopy(saved_graph)
    g['76']['inputs']['image']=original
    g['detailimage']['inputs']['image']=face
    g['81']['inputs']['image']=design
    g['92:105']['inputs']['noise_seed']=seed
    g['repair-base']=node('LoadImage',image=baseline)
    g['repair-mask']=node('LoadImageMask',image=mask,channel='red')
    g['repair-latent']=node('VAEEncodeForInpaint',pixels=['repair-base',0],vae=['92:107',0],mask=['repair-mask',0],grow_mask_by=0)
    g['92:103']['inputs']['latent_image']=['repair-latent',0]
    g['repair-composite']=node('ImageCompositeMasked',destination=['repair-base',0],source=['92:104',0],
                               x=0,y=0,resize_source=False,mask=['repair-mask',0])
    g['9']['inputs'].update(images=['repair-composite',0],filename_prefix=prefix)
    g['92:113']['inputs']['text']=(
        'Rebuild one complete, anatomically coherent individual dog inside the editable subject region. '
        'Image 1 is the intact ORIGINAL dog photograph and the source of truth for its whole body, coat and age. '
        'Image 2 is an unedited close-up of the SAME dog and the facial identity guide. '
        'Image 3 is a costume and scene guide with the previous animal fur deliberately erased to neutral gray. '
        'Gray regions are missing information, NOT gray fur or holes to retain. '
        +identity+' '+scene+' '
        'Recreate the face, natural ears, neck, torso, visible legs, paws and tail as parts of THIS SAME dog. '
        'Apply the original dog coat color, marking distribution, length and texture to EVERY exposed animal part. '
        'Fit the clothing around this dog\'s own build and age. Rebuild the neckline and limb sizes; do not copy the original costume wearer\'s body proportions. '
        'Keep the reference artistic medium, costume design, props and scene; adapt pose naturally to the new dog. '
        'Preserve its actual face and eye color, natural ear shape and muzzle. One connected animal, no pasted photographic cutout, '
        'no golden retriever remnants, no human hands or bodybuilder muscles, no added hoods, masks, horns or artificial ears. '
        'Respect real occlusion without inventing extra limbs. Keep all source-visible body parts available as identity evidence. '
        'Ignore the household background of the original photo. Finish the artwork naturally with matching scene lighting.')
    return g
