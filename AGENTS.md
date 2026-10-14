# Consistent Pet

For the 725-reference library and requested RTX 6000 per-picture refinement task,
read [HANDOFF.md](HANDOFF.md) first. Folder mappings are in
`workflows/portraits/index.json`. Starting graphs are not accepted workflows;
save validated sanitized exports in each reference's own folder as directed there.

This repository contains source code, tests and generic examples for the local
portrait refinement system. Model weights, uploads, generated portraits, runtime
state, review databases, tokens, private sharing links and SSH details stay outside
Git. Use explicit file lists when publishing from another workspace.

Keep the independent visual reviewer fixed while optimizing generation. Acceptance
for the newest owner-requested qualified-input policy requires input photo >=7,
output face >=9, fur >=9, body >=7 and design >=9, high output confidence and no major
defects. Never label a budget-limited or failed workflow accepted. Historical
held-out evaluations must remain immutable and must not be relabeled as passes.

Owner update, 2026-10-14: the new roster policy explicitly refines on every
submitted dog. Treat the entire roster as development data in that new policy;
never claim those identities are still unseen holdouts. Lock one shared costume
recipe once at least 85% of qualifying roster entries pass that exact recipe. Any recipe change
invalidates earlier passes until rechecked. Export this separately identified
roster-validation format; retain the historical holdout exporter unchanged.

Later owner update: independently score original inputs without seeing outputs.
Only inputs scoring >=7 qualify for the new acceptance roster; <=6 inputs request
a clearer source photo and do not block it. Pin the source scores per run, report
excluded counts, and never claim that low input quality proves the cause of every
failed output. Historical all-9 thresholds and results remain unchanged.

Use a new run version and a frozen runner directory when changing active policies.
Preserve native ComfyUI job IDs on resume. Never restart an existing sharing tunnel
to deploy a page or worker change. Test Python orchestration on Linux; Windows
skips the flock-dependent flow tests.

Exception explicitly authorized by the owner: approved generated reference templates
in reference-library/ are published with Git LFS and mirrored to Hugging Face.
This does not permit customer photographs, customer outputs, credentials or runtime files.

Latest owner update: accept a costume when at least 85% of the FULL qualifying input roster passes one unchanged shared recipe. Required count is ceil(0.85 * roster size): 15/17. Untested dogs are not passes. Preserve face 9, fur 9, body 7, design 9, input >=7, confidence and defect gates. v3 exports include actual passing, checked and required counts. Historical evaluations and owner visual approvals remain separate.

Round order: generate and score one image per qualifying dog on the same recipe before any revision. Evaluate the complete round; >=85% locks and advances to the next costume. Otherwise the LLM revises once, then runs another complete dog sweep, up to six rounds per catalog visit. Never combine passes from different recipes.

Latest owner change: 8/10 is sufficient for face, fur and design; body remains >=7. Full-round >=85% rule and source>=7 unchanged. New v4 runs and exports use these thresholds; historical scores and approvals remain unchanged.

Latest owner correction: acceptance is the completed-round arithmetic MEAN >=8/10, not 85% individually passing dogs. Average all four dimension scores across one image of each qualifying dog on one exact recipe. All roster entries must be scored; no mix of historical candidates, no separate dimension/confidence/defect veto. Source >=7 remains. New average-v5 policy, distinct export format; historical evaluations remain immutable.
