# Per-reference GPU workflows

Start with [the RTX 6000 handoff](../../HANDOFF.md). [index.json](index.json) maps all 725 unique portrait IDs to their reference assets and dedicated folders.

Each folder has a reference manifest, visual README, shared baseline API graph and progress status. Baselines are **not** independently tuned or validated for each picture. Save accepted, sanitized recipe bundles as `workflow.json` only after the existing cross-dog validation and exporter gates pass. See the handoff for provisional results, reports, GPU operation and privacy rules.

Regenerate missing starting files without overwriting existing per-reference work:

```bash
python scripts/build-reference-workflow-folders.py
```

This command organizes files only. It submits no GPU jobs and does not change live customer generation.
