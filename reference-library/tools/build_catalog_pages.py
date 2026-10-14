from pathlib import Path
import json,collections,csv
root=Path(__file__).resolve().parent.parent
records=json.loads((root/'catalog.json').read_text(encoding='utf8'));stats=json.loads((root/'inventory.json').read_text())
fields=['id','name','sex','category','collection','description','file_name','preview','print_variant','qa_flags']
(root/'gallery-data.js').write_text('window.PET_REFERENCES='+json.dumps([{k:r[k] for k in fields} for r in records],ensure_ascii=False).replace('<','\\u003c')+';\n',encoding='utf8')
with (root/'catalog.csv').open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=['id','name','sex','category','collection','file_name','sha256','width','height','print_variant','print_variant_sha256']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in records)
sex=stats['sex_counts'];readme='''---
language:
- en
tags:
- synthetic
- pet-portraits
- image-to-image
- reference-images
pretty_name: Consistent Pet Portrait References
configs:
- config_name: default
  data_files:
  - split: train
    path:
    - metadata.jsonl
    - references/**/*.png
---
# Consistent Pet — portrait reference library

This project uses a 96 GB Blackwell GPU and image-editing models to preserve a pet's identity across portrait references. This release packages the existing Higgsfield template library; it does **not** enable bulk generation on the live store.

**725 distinct reference concepts**, all full-resolution PNGs at1792×2240, plus100 separately labeled vintage poster versions. Every master was decoded and SHA-256 matched against its source manifest. There are725 optimized browsing thumbnails. No customer originals, customer portraits, credentials, provider account URLs or private storage keys are included.

- [Hugging Face dataset](https://huggingface.co/datasets/bensblueprints/consistent-pet)
- [GitHub repository](https://github.com/bensblueprints/consistent-pet)
- Open `index.html` locally for searchable previews and sex/category/collection filters.
- `catalog.json`, `catalog.csv` and ImageFolder-compatible `metadata.jsonl` provide machine-readable labels, filenames, provenance, prompts, hashes and dimensions.

## Collections

| Collection | Concepts |
|---|---:|
| Original costume references |25|
| Surreal superheroes, princesses and sports |100|
| Vintage newspapers, wanted posters and keepsakes |100|
| Mobsters |100|
| Superheroes |100|
| New300 costume collection |300|
| **Total** |**725**|

## Sex and category organization

Files are organized as `references/{male,female,unisex}/{category}/{stable-id}.png`. Thumbnails mirror this under `previews/`; vintage poster versions mirror it under `print-variants/`.

'''+f'**Male: {sex["male"]} · Female: {sex["female"]} · Unisex: {sex["unisex"]}.**\n\n'+'''Sex is **costume eligibility**, not a biological-sex inference from an animal image. Existing intended boy/girl collections retain their labels. Most profession, adventure and vintage designs are unisex. The vintage batch had provisional alternating boy/girl assignments: those were normalized to unisex except explicitly gendered titles/outfits. `source_sex` and `classification_basis` preserve the distinction. For a male or female pet, include matching-sex **and unisex** references.

| Category | Male | Female | Unisex |
|---|---:|---:|---:|
'''
for category in sorted(stats['category_counts']):
 row=[category]
 for group in ['male','female','unisex']:
  matches=[r for r in records if r['sex']==group and r['category']==category]
  row.append(f'[{len(matches)}]({Path(matches[0]["file_name"]).parent.as_posix()}/)' if matches else '0')
 readme+='| '+' | '.join(row)+' |\n'
readme+='''
## Download

GitHub stores full originals and thumbnails in **Git LFS**. GitHub's source ZIP may contain LFS pointers rather than images; clone with LFS for the complete library:

```sh
git lfs install
git clone https://github.com/bensblueprints/consistent-pet.git
cd consistent-pet
git lfs pull
cd reference-library
python tools/validate_library.py
```

Or download from Hugging Face without Git LFS:

```sh
pip install huggingface_hub pillow
hf download bensblueprints/consistent-pet --repo-type dataset --local-dir consistent-pet
```

Metadata follows Hugging Face ImageFolder conventions. The dataset's default image split includes the725 master references; thumbnails and poster variants are not additional training examples. Dataset-viewer indexing is asynchronous.

## Quality and reuse notes

These are synthetic concept references, not identity-transfer proofs or inpainting masks. The first surreal female collection has inherited canine-anatomy concerns and is flagged `anatomy-review-required`; keep those out of automatic customer production until individually corrected/reviewed. Some vintage compositions deliberately contain multiple pets or paired ages; they are flagged separately. The original Dragon Guardian has a secondary creature. The archive retains all requested concepts rather than silently discarding these items.

`reference_used` records whether generation used an input reference. Retried standalone generations retain their actual effective prompts. Source masters are unmodified; vintage `print_variant` files include the finished caption layout while `file_name` is the clean artwork layer. `customer_identity_transfer_validated=false` is deliberate. Classification does not certify production readiness. No new license grant is made by this organizational upload.

## Rebuild and verify

`tools/build_library.py` accepts the four existing completed-manifest collection directories and the original25 manifest/directory. It copies only explicitly listed image files after hash/decode checks, creates previews and sanitized metadata, and refuses a mismatched inventory. It never scans customer storage or publishes generation/account journals. Then run `tools/build_catalog_pages.py` and `tools/validate_library.py`.

Uploads to Hugging Face use `tools/upload_huggingface.py` with your locally authenticated token. Credentials are never stored in this repository.
'''
(root/'README.md').write_text(readme,encoding='utf8')
