# Feedback loop and saved workflows

## One reference at a time

1. Build a whole-animal and costume mask from the original reference artwork.
   Erase the former animal's exposed fur from the conditioning reference.
2. Render using the intact original dog, its face crop and the neutralized costume
   guide. The editable region includes the body, so this is not a face overlay.
3. Independently score face identity, coat distribution/texture, body anatomy and
   design fidelity. The local vision LLM supplies concrete visible evidence and
   proposed corrections alongside the four scores.
4. Compile the critique into a new recipe. Apply dog-specific correction text only
   to that same dog. Adjust the repair region, relative reference resolution,
   sampling steps and guidance; give each attempt a deterministic new seed.
5. Repeat on the two tuning dogs until both pass every dimension or the configured
   limit is reached. Keep every candidate and critique, including failed attempts.
6. Freeze the best recipe and its generic API graph, then evaluate at least three different
   validation dogs. Only when tuning and validation all pass, run the final two
   dogs once. Their feedback never selects another recipe within this run.
7. Save an accepted workflow only when all required dogs pass. Otherwise save the
   best provisional recipe and a report explaining which stages did not pass.

The target is **at least nine on all four dimensions**, high confidence and no
major defects. Minor differences can remain at a nine. An 8.9 overall or three
tens plus a body eight does not pass. The evaluator's prompt, scoring rules and
weights are not modified to reach the target.

The current compiler changes an existing graph family. It does not autonomously
invent arbitrary ComfyUI nodes, install models, tune the critic or train weights.
Specific LLM correction text is generation evidence, never Python/shell code.

## Runtime artifacts

| Private path | Contents |
| --- | --- |
| `dog-revisions.json` | Every auto-attempt shown in the studio |
| `reviews.sqlite3` | Versioned AI assessments and optional append-only human reviews |
| `judge-evidence/` | Raw critic response, model/rubric IDs and exact image hashes |
| `auto-refine-status.json` | Allowlisted summary for the page |
| `auto-refinement/<run>/state.json` | Resume state, recipes, scores and stage membership |
| `auto-refinement/<run>/jobs/` | Exact submitted graphs, UUIDs and native history |
| `auto-refinement/<run>/<reference>-frozen.json` | Best parameterized recipe, frozen before different-dog checks |
| `auto-refinement/<run>/<reference>-report.json` | Outcomes and limitations for this reference |
| `auto-refinement/<run>/accepted/<reference>.json` | Only workflows that met every required acceptance check |

The frozen graph has placeholders for the dog original, face crop, costume guide,
template layout, mask, seed, output prefix and input-specific prompt. Actual
accepted generations remain the exact graphs in `jobs/`. This distinction avoids
accidentally baking a tuning dog's coat description into a different dog's prompt.

`portrait_autorefine.dog_instruction`, `apply_recipe` and
`portrait_body_repair.repair_graph` are the binding functions used for the
cross-dog replays. Frozen recipes omit the tuning dog's critique text.

To export an accepted recipe for source control without images, runtime paths,
dog identifiers or assessment records:

```bash
python scripts/export-accepted-workflow.py \
  --accepted /private/runtime/auto-refinement/RUN/accepted/REFERENCE.json \
  --output workflows/REFERENCE.json
```

The exported file is a reusable API-graph configuration. Matching model weights
and the operator's reference/mask assets are still required. The exporter refuses
provisional workflows and rechecks every assessment in the frozen evaluation
groups before exporting, including all dogs in an expanded validation cohort.

## Expanding the submitted-dog cohort

A plan can set `dogs_manifest` to a private JSON basename and
`validate_all_dogs: true`. Keep the old manifest and files intact. New registry
entries require `id`, `source_sha256`, `input` and `crop`; use `identity_group`
to keep alternate photographs of a possible same dog in one split. When extending
an existing evaluation, pin every entry's `split` to `train`, `validation` or
`test`, preserving the earlier holdouts.

Visually reviewed inputs may include `quality_tier` (`clear` or `challenging`),
`quality_rank`, `quality_notes` and `tuning_eligible`. Tuning then requires two
clear, eligible training identities. Remaining training inputs and the pinned
validation inputs run against the frozen recipe. Final test identities remain
conditional on preceding stages passing and never drive candidate selection.
Use a new version and frozen runner whenever the registry or its policy changes.

Copy the approved private registry to `input-catalog.json` to show its selected
pet crops in the token-protected studio. The server projects display fields and
allowlisted image basenames only; source hashes, split groups and audit records
are not exposed. Rows carry their exact `identity_crop`, so new crops never
silently replace the evidence used for older scores. The reviewer records that
crop's checksum alongside the input, reference and output hashes.

## Limits and interpretation

Budget exhaustion is not success. Unimproved attempts remain visible and no
below-target workflow enters the accepted directory. Time limits gate new
submissions; an already running native job or a score wait can finish afterward.
The default pilot caps retries rather than generating indefinitely.

AI scores can be wrong or reward artifacts they fail to notice. The held-out
checks test transfer to the selected dogs, not every possible future upload.
Historical pilot failures included close faces with body scores around seven.
No claim that all templates reach the target is made by this repository.

Optional human-review export/report tools retain human and AI evidence separately.
They prepare data for future evaluation; they do not train or deploy new weights.
