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
requires every dimension to reach at least 9/10, high confidence and no major
defects. Never label a budget-limited or failed workflow accepted. Historical
held-out evaluations must remain immutable and must not be relabeled as passes.

Owner update, 2026-10-14: the new roster policy explicitly refines on every
submitted dog. Treat the entire roster as development data in that new policy;
never claim those identities are still unseen holdouts. Lock one shared costume
recipe only after every roster entry passes that exact recipe. Any recipe change
invalidates earlier passes until rechecked. Export this separately identified
roster-validation format; retain the historical holdout exporter unchanged.

Use a new run version and a frozen runner directory when changing active policies.
Preserve native ComfyUI job IDs on resume. Never restart an existing sharing tunnel
to deploy a page or worker change. Test Python orchestration on Linux; Windows
skips the flock-dependent flow tests.

Exception explicitly authorized by the owner: approved generated reference templates
in reference-library/ are published with Git LFS and mirrored to Hugging Face.
This does not permit customer photographs, customer outputs, credentials or runtime files.
