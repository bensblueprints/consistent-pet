# Handoff: 725 portrait references and RTX 6000 workflow refinement

Updated: 2026-10-14. **Start here, then read AGENTS.md and the operational documents linked below.**

Latest owner-requested policy: `scripts/run-roster-catalog.py` gives each submitted
dog up to six scored generations per costume per catalog visit, stopping that dog
early when it passes. The resident LLM revises failures immediately. Earlier dogs
must be rechecked whenever the shared recipe changes. Unresolved costumes return
to the queue; they are never accepted merely because six attempts were used.
This new development-roster policy is separate from the immutable historical
holdout runs. See the six-attempt section in `docs/WORKFLOW.md`.

Implementation update: `scripts/run-costume-catalog.py` now provides the persistent
725-reference queue with resident-LLM planning. See [the workflow guide](docs/WORKFLOW.md)
for bounded retries, frozen cross-dog checks, resource limits and report publishing.
The studio's default generation-history view compares attempts horizontally and
retains AI critiques, applied changes and optional human reviews. These are workflow
optimization tools, not evidence that all references are tuned or model weights
have been trained. Per-folder status and reports record actual progress.

## Owner's requested next task

Use the rented **RTX PRO 6000 Blackwell 96 GB** to improve identity transfer for **all 725 unique portrait references**. Work through the catalog systematically. For each reference, refine the GPU workflow until it preserves the uploaded pet's face, coat, body and the intended design, evaluate it on different dogs, and save the resulting reusable workflow in that reference's own folder under `workflows/portraits/<reference-id>/`.

This is a per-reference workflow development task. Do not simply run the same untuned graph 725 times and call the collection finished. Do not enable automatic generation of all 725 portraits for live customers as a side effect.

## Verified asset locations

- [GitHub library](https://github.com/bensblueprints/consistent-pet/tree/main/reference-library)
- [Hugging Face dataset](https://huggingface.co/datasets/bensblueprints/consistent-pet)
- [Machine-readable catalog](reference-library/catalog.json) and [raw catalog URL](https://raw.githubusercontent.com/bensblueprints/consistent-pet/main/reference-library/catalog.json)
- [All workflow-folder mappings](workflows/portraits/index.json)
- [Category tables and library documentation](reference-library/README.md)
- [Searchable gallery](reference-library/index.html): open locally after downloading images, or serve the library with `python -m http.server 8771 --directory reference-library`.

Primary Windows checkout: `C:\Users\DELL\consistent-pet`. Its images are in `reference-library/references/` and workflow folders in `workflows/portraits/`. The earlier isolated preparation checkout is `C:\Users\DELL\consistent-pet-reference-library`; use the primary checkout for this handoff. Do not rely on these Windows paths on the GPU host; clone the repository there and use repository-relative paths.

The library publication was verified at Git commit `76285ead7b3f8fd091cd389a58e5d6c56b5d553e` and Hugging Face revision `ec39f9cb7cfda4ab53faca0e72eaadacde47f804`. All 825 full-resolution hashes matched; actual GitHub downloads from each collection were checked. These revisions establish the asset snapshot, not completed GPU validation. Later commits add this handoff and the workflow folders.

| Collection key | Unique portraits |
| --- | ---: |
| original25 | 25 |
| surreal | 100 |
| vintage | 100 |
| mobsters | 100 |
| superheroes | 100 |
| costumes300 | 300 |
| **Total** | **725** |

There are also **100 captioned vintage poster variants**, not 100 extra concepts, and **725 WebP thumbnails**. The image payload is about 5.5 GB. Masters are 1792 x 2240 PNGs across 63 categories. Costume eligibility is 62 male, 90 female, 573 unisex; include unisex designs for either sex. This classification does not infer an animal's biological sex.

## Download actual images, not LFS pointers

```bash
git lfs install
git clone https://github.com/bensblueprints/consistent-pet.git
cd consistent-pet
git lfs pull
python -m pip install pillow
python reference-library/tools/validate_library.py
```

For an existing checkout, inspect local changes before pulling. Never reset another agent's work. GitHub source ZIPs or raw Git URLs may return LFS pointer text. To retrieve an individual actual image without Git LFS, use:

```text
https://huggingface.co/datasets/bensblueprints/consistent-pet/resolve/main/<catalog file_name>
```

Every per-picture `reference.json` already contains that direct `reference_url`. To download the entire Hugging Face copy separately:

```bash
python -m pip install huggingface_hub
hf download bensblueprints/consistent-pet --repo-type dataset --local-dir /your/path/pet-reference-library
```

Hugging Face places `catalog.json`, `references/`, `previews/` and `print-variants/` at the dataset root; GitHub nests them under `reference-library/`. HF's automatic viewer may index asynchronously; the files do not depend on that viewer.

## Find each picture and its GPU folder

```python
import json
from pathlib import Path

repo = Path.cwd()  # Run from the repository root.
catalog = json.loads((repo / 'reference-library/catalog.json').read_text(encoding='utf-8'))
assert len(catalog) == 725
for portrait in catalog:
    reference_image = repo / 'reference-library' / portrait['file_name']
    workflow_folder = repo / 'workflows/portraits' / portrait['id']
    assert reference_image.is_file() and workflow_folder.is_dir()
    # Load the image in a vision-capable tool; reading its filename is not visual inspection.
    print(portrait['id'], reference_image, workflow_folder)
```

The catalog contains stable IDs, source prompts/model information, eligibility/category/collection labels, dimensions, hashes and QA flags. `file_name` is the clean master; `print_variant` is an optional captioned poster. Source generation prompts can mention the original template dog's breed: **do not reuse those identity descriptions as the new customer's prompt**. Derive pet-neutral scene/clothing instructions and preserve the new pet's own anatomy and markings.

## Per-picture folder contract

Each of the 725 folders starts with:

- `README.md`: visual thumbnail, full image link and instructions.
- `reference.json`: exact reference mapping, hash, description and source prompt.
- `baseline.api.json`: shared FLUX.2 Klein baseline graph with placeholders. This is a starting graph, not a reference-specific tuned workflow.
- `status.json`: initially `pending_gpu_refinement`; no accepted workflow is claimed.

During refinement, update the matching folder:

- `workflow.json`: **accepted sanitized export only**, produced by `scripts/export-accepted-workflow.py` after all required checks pass. This is a recipe bundle containing a ComfyUI API graph, not a drag-and-drop GUI workflow.
- `provisional.workflow.json`: optional sanitized best incomplete recipe, clearly marked provisional. Do not put it in `workflow.json` or bypass the accepted-workflow exporter. If a safe provisional export is unavailable, retain it privately and record that fact in the report instead.
- `REPORT.md`: generic changes, model/runner versions, attempt counts, measured timings, per-stage outcomes, known limitations and next steps. No private dog IDs, file paths, original photos or customer details.
- `status.json`: actual state (`in_progress`, `provisional`, `accepted`, or `blocked`), accepted/provisional relative filenames, run version and UTC update time. Set `customer_identity_transfer_validated` true only after required validation passes; retain the limitation that AI scoring is an estimate.

`scripts/build-reference-workflow-folders.py` recreates missing starting files and rebuilds the index without overwriting existing per-picture work. Do not regenerate these folders from scratch or erase completed tuning.

## RTX 6000 execution instructions for the next LLM

1. Read [AGENTS.md](AGENTS.md), [setup](docs/SETUP.md), [workflow behavior](docs/WORKFLOW.md), and [private manifest example](examples/manifest.example.json). Locate the existing GPU connection through the operator's private environment. No SSH host, credential, private sharing link or customer image is stored in this public handoff. Check `nvidia-smi`, installed models and active jobs before changing anything; this handoff does not certify the current server is reachable.
2. Use the existing RTX PRO 6000 environment and native ComfyUI runner. The documented stack is FLUX.2 Klein base 4B, SAM3.1 segmentation and Qwen3-VL-32B-Instruct as the independent reviewer. Verify actual node/model availability with the existing preflight script. Do not replace the critic or tune its rubric to make scores look better.
3. Inspect existing pilot state before starting. Preserve native ComfyUI job IDs and any running review service/tunnel. Use a new frozen runner and run version for policy changes. Never reinitialize an existing private runtime or submit duplicate jobs after an ambiguous timeout.
4. Read the 725-entry index and current folder statuses. Resume incomplete references. Visually inspect the reference and resolve its QA flags. Prepare pet-neutral scene/clothing instructions and the required whole-animal/costume masks; use the full source dog and real face crop. Build a **new private manifest** with selected references and at least seven genuinely distinct authorized dog identities; runtime files stay outside Git.
5. Follow the existing feedback loop: two clear tuning dogs, at least three separate validation dogs, then two final held-out dogs. The expanded-cohort option evaluates all remaining eligible inputs with pinned historical splits; see the workflow guide. Freeze the recipe before cross-dog checks. Do not tune on held-out results or copy one dog's coat instructions to another. Keep exact outputs, masks, graphs, hashes and independent assessments in the private runtime.
6. Require **face, fur, body and design each >= 9/10**, high confidence and no major defects for all required assessments. An average score cannot conceal a weak dimension. AI scores still need scrutiny; known anatomy defects must not be waved through. Bounded retries/timeouts produce a provisional result, not false acceptance. Continue systematically through all 725 and report blocked references honestly.
7. Export each accepted result directly into its own folder, for example:

   ```bash
   python scripts/export-accepted-workflow.py \
     --accepted /private/runtime/auto-refinement/RUN/accepted/REFERENCE_ID.json \
     --output workflows/portraits/REFERENCE_ID/workflow.json
   ```

   Replace placeholders with the real run and ID. The exporter refuses non-accepted results and existing output files; preserve/version earlier exports rather than deleting them silently. Update the report and status alongside every saved result. Public exports must remain parameterized and free of private images, paths and customer-specific descriptions.
8. Commit only explicit sanitized source/report/workflow files, update GitHub and Boardly, and report accepted/provisional/blocked/pending counts totaling 725. Do not make live store or production-queue changes merely because a research workflow passed.

## Current completion boundary and known issues

The image library is complete and verified. The 725 dedicated GPU folders provide starting graphs and tracking; **725 tuned workflows have not been produced or validated by this handoff**. The existing refinement implementation is documented separately and its current pilot must be inspected, not assumed complete.

Older surreal female templates have `anatomy-review-required` flags; some vintage references contain multiple subjects or age variants; Dragon Guardian contains a secondary creature. Review those before automatic customer use. No masks, weights, customer originals, runtime jobs or credentials are included in these public folders.

Boardly project 56, card 625 records the library publication and verification. The root README and AGENTS.md link to this handoff for future agents.
