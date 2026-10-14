# Consistent Pet

This repository contains source code, tests and generic examples for the local
portrait refinement system. Model weights, uploads, generated portraits, runtime
state, review databases, tokens, private sharing links and SSH details stay outside
Git. Use explicit file lists when publishing from another workspace.

Keep the independent visual reviewer fixed while optimizing generation. Acceptance
requires every dimension to reach at least 9/10, high confidence and no major
defects. Never label a budget-limited or failed workflow accepted. Do not train on
held-out dog identities or use their results to select another candidate.

Use a new run version and a frozen runner directory when changing active policies.
Preserve native ComfyUI job IDs on resume. Never restart an existing sharing tunnel
to deploy a page or worker change. Test Python orchestration on Linux; Windows
skips the flock-dependent flow tests.
