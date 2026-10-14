# Heaven portrait priority batch

The owner requested these 24 references at the front of the RTX 6000 refinement queue:
12 Jesus with dogs, six male angel dogs, and six female angel dogs.

Mappings: `workflows/portraits/priority-heaven24.json`. Each has its own reference,
baseline and status folder. These are pending workflow development, not accepted
customer identity-transfer workflows. Preserve the human companion in Jesus
portraits and feather wings in angel portraits while replacing only dog identity.

`scripts/run-priority-catalog.py` overlays the 24 references on the frozen
725-reference index. The effective queue has 749 entries. It retains the original
fingerprint, native jobs, completed exports, resource window and evaluation policy.
The original index is deliberately unchanged so existing runs remain resumable.
The current original portrait resumes first; then the new zero-round priority
entries precede older pending entries. Failed visits retain normal bounded retry
ordering rather than indefinitely starving the older catalog.

The wrapper is outside the frozen runner directory. Use the same runner, version,
hours and attempt limit as the original coordinator. Public queue totals include
the overlay. Never modify the frozen runner to install this overlay, reset old
checkpoints, or restart the renderer/reviewer/tunnel to change queue ordering.

The supplemental reference URLs point to completed Higgsfield generations. PNG
masters are also versioned with Git LFS; they have not yet been mirrored to the
Hugging Face dataset or added to the original library gallery/catalog.
