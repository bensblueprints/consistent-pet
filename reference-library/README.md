---
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

**Male: 62 · Female: 90 · Unisex: 573.**

Sex is **costume eligibility**, not a biological-sex inference from an animal image. Existing intended boy/girl collections retain their labels. Most profession, adventure and vintage designs are unisex. The vintage batch had provisional alternating boy/girl assignments: those were normalized to unisex except explicitly gendered titles/outfits. `source_sex` and `classification_basis` preserve the distinction. For a male or female pet, include matching-sex **and unisex** references.

| Category | Male | Female | Unisex |
|---|---:|---:|---:|
| Armor and Tech | 0 | 0 | [10](references/unisex/armor-and-tech/) |
| Around the World | 0 | 0 | [20](references/unisex/around-the-world/) |
| BatDog | 0 | 0 | [10](references/unisex/batdog/) |
| Bonnie and Clyde | [1](references/male/bonnie-and-clyde/) | [4](references/female/bonnie-and-clyde/) | [5](references/unisex/bonnie-and-clyde/) |
| British Crime Club | [1](references/male/british-crime-club/) | [2](references/female/british-crime-club/) | [7](references/unisex/british-crime-club/) |
| Casino Royals | 0 | [2](references/female/casino-royals/) | [8](references/unisex/casino-royals/) |
| Cinema posters | [1](references/male/cinema-posters/) | 0 | [9](references/unisex/cinema-posters/) |
| Coastal Living | 0 | 0 | [20](references/unisex/coastal-living/) |
| Cosmic Guardians | 0 | 0 | [10](references/unisex/cosmic-guardians/) |
| Country Life | 0 | 0 | [20](references/unisex/country-life/) |
| Detectives and Secret Agents | 0 | 0 | [2](references/unisex/detectives-and-secret-agents/) |
| Dogs With Day Jobs | 0 | 0 | [20](references/unisex/dogs-with-day-jobs/) |
| Elemental Heroes | 0 | 0 | [10](references/unisex/elemental-heroes/) |
| Exploration | 0 | 0 | [1](references/unisex/exploration/) |
| Extreme sports | [10](references/male/extreme-sports/) | [10](references/female/extreme-sports/) | 0 |
| Fantasy and Magic | 0 | 0 | [4](references/unisex/fantasy-and-magic/) |
| Foodie Favorites | 0 | 0 | [20](references/unisex/foodie-favorites/) |
| Funny Dogs Being Dogs | 0 | 0 | [20](references/unisex/funny-dogs-being-dogs/) |
| Heists and Getaways | 0 | 0 | [10](references/unisex/heists-and-getaways/) |
| Heroine Collection | 0 | [10](references/female/heroine-collection/) | 0 |
| Hobbies With Personality | 0 | 0 | [20](references/unisex/hobbies-with-personality/) |
| Holidays and Celebrations | 0 | [1](references/female/holidays-and-celebrations/) | [19](references/unisex/holidays-and-celebrations/) |
| Household documents | 0 | 0 | [10](references/unisex/household-documents/) |
| Keepsakes | 0 | 0 | [10](references/unisex/keepsakes/) |
| Knights and Warriors | 0 | 0 | [3](references/unisex/knights-and-warriors/) |
| Magazine covers | 0 | 0 | [10](references/unisex/magazine-covers/) |
| Memorial and Remembrance | 0 | 0 | [1](references/unisex/memorial-and-remembrance/) |
| Miami Crime Drama | [1](references/male/miami-crime-drama/) | [2](references/female/miami-crime-drama/) | [7](references/unisex/miami-crime-drama/) |
| Music and Performance | 0 | 0 | [1](references/unisex/music-and-performance/) |
| Music and the Spotlight | 0 | 0 | [20](references/unisex/music-and-the-spotlight/) |
| Newspapers | 0 | 0 | [10](references/unisex/newspapers/) |
| Noir City | 0 | [2](references/female/noir-city/) | [8](references/unisex/noir-city/) |
| Original Champions | [1](references/male/original-champions/) | [1](references/female/original-champions/) | [8](references/unisex/original-champions/) |
| Outdoor Adventures | 0 | 0 | [20](references/unisex/outdoor-adventures/) |
| Pirates and Naval | 0 | 0 | [2](references/unisex/pirates-and-naval/) |
| Playful Crime Legends | 0 | 0 | [10](references/unisex/playful-crime-legends/) |
| Princess | 0 | [10](references/female/princess/) | 0 |
| Retro Futures and Original Characters | 0 | 0 | [20](references/unisex/retro-futures-and-original-characters/) |
| Retro advertisements | 0 | 0 | [10](references/unisex/retro-advertisements/) |
| Roaring Twenties | [1](references/male/roaring-twenties/) | [3](references/female/roaring-twenties/) | [6](references/unisex/roaring-twenties/) |
| Royal fantasy | [10](references/male/royal-fantasy/) | 0 | 0 |
| Royalty | [1](references/male/royalty/) | [2](references/female/royalty/) | [1](references/unisex/royalty/) |
| Science Fiction | [1](references/male/science-fiction/) | 0 | [2](references/unisex/science-fiction/) |
| Science and Inventors | 0 | 0 | [1](references/unisex/science-and-inventors/) |
| Snow-Day Personalities | [1](references/male/snow-day-personalities/) | [1](references/female/snow-day-personalities/) | [18](references/unisex/snow-day-personalities/) |
| Spider Dawg | 0 | 0 | [10](references/unisex/spider-dawg/) |
| Sports | [10](references/male/sports/) | [10](references/female/sports/) | 0 |
| Sports collectibles | 0 | 0 | [10](references/unisex/sports-collectibles/) |
| Steampunk and Time Travel | 0 | 0 | [2](references/unisex/steampunk-and-time-travel/) |
| Storybook Adventures | 0 | 0 | [20](references/unisex/storybook-adventures/) |
| Street Heroes | 0 | 0 | [10](references/unisex/street-heroes/) |
| Studio portraits | [1](references/male/studio-portraits/) | [3](references/female/studio-portraits/) | [6](references/unisex/studio-portraits/) |
| Super Dog | 0 | 0 | [10](references/unisex/super-dog/) |
| Superhero | [10](references/male/superhero/) | [10](references/female/superhero/) | 0 |
| Surreal adventure | [10](references/male/surreal-adventure/) | [10](references/female/surreal-adventure/) | 0 |
| The Pawfather | [1](references/male/the-pawfather/) | [2](references/female/the-pawfather/) | [7](references/unisex/the-pawfather/) |
| Underworld Elegance | [1](references/male/underworld-elegance/) | [2](references/female/underworld-elegance/) | [7](references/unisex/underworld-elegance/) |
| Up in the Air | 0 | 0 | [20](references/unisex/up-in-the-air/) |
| Wanted posters | 0 | 0 | [10](references/unisex/wanted-posters/) |
| Western | 0 | 0 | [1](references/unisex/western/) |
| Wheels and Racing | 0 | 0 | [20](references/unisex/wheels-and-racing/) |
| Wonder and Lightning | 0 | [3](references/female/wonder-and-lightning/) | [7](references/unisex/wonder-and-lightning/) |
| Working dogs | 0 | 0 | [10](references/unisex/working-dogs/) |

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
