# Portrait of Pope Innocent X — Dog Portrait — development-roster report

Status: **in_progress**. Updated 2026-10-19T00:00:51Z.

0 / 5 qualifying input records pass the current shared recipe. 15 source photos excluded by the input-quality gate. 7 candidate recipes; 31 renders.

The independent output critic stays fixed. Acceptance: original input >=7; complete round arithmetic mean >=8 across all four scores for every qualifying dog. Individual dimension minima and the 85% pass fraction do not gate this policy.
Each successful dog check is checkpointed privately. A recipe change invalidates earlier passes until those dogs are checked again. One exact recipe must be checked on the full qualifying roster and average >=8 to lock this costume. Incomplete rounds cannot pass.

All submitted photos are development data under the owner-requested policy. Historical holdout runs remain immutable; this new result is not independent validation on unseen dogs. AI estimates do not establish universal or perfect performance.

| Candidate | Dogs checked | Dogs passing | Lowest body | Strategy | Pose policy |
| --- | ---: | ---: | ---: | --- | --- |
| 1 | 5 | 2 | 5 | fresh-latent | source-compatible |
| 2 | 5 | 2 | 5 | inpaint | natural-sitting |
| 3 | 5 | 1 | 5 | fresh-latent | reference |
| 4 | 5 | 2 | 5 | inpaint | reference |
| 5 | 5 | 1 | 5 | fresh-latent | reference |
| 6 | 5 | 1 | 5 | fresh-latent | source-compatible |
| 7 | 1 | 0 | 5 | fresh-latent | natural-sitting |

Exact images, per-dog checkpoints, native job IDs, critiques and unsuccessful graphs remain private. Accepted exports are parameterized and omit customer identities and media paths.
Difficult references remain provisional for another catalog pass; technical failures require inspection. The submission deadline does not become an acceptance shortcut.
