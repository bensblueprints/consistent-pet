# Workflow recovery and off-server copies

Accepted workflows are mirrored every five minutes to GitHub `bensblueprints/consistent-pet` and the Hugging Face dataset with the same name. Paths match: `workflows/portraits/<costume-id>/workflow.json`. The mirror also contains the committed runner scripts, baseline templates, reference metadata and operational documentation. Existing reference-library images on Hugging Face remain untouched.

An export is a parameterized recipe plus graph. Supply the original dog, real face crop, costume reference, prepared layout and subject mask through the saved pipeline. It does not embed customer photographs or model weights. Owner-approved exports are explicitly labelled and do not claim that the AI acceptance gate passed.

The operator's separate private recovery directory contains a verified full archive followed by incremental archives, plus SHA-256 manifests. These contain customer media and MUST NOT be uploaded to a public repository. Each archive includes changed runtime state, jobs, source/output media, a SQLite online-backup snapshot of reviews, and the current frozen runner. No sharing token is included. Retain the first archive and every later incremental archive.

To recover after GPU-server loss:

1. Verify archive SHA-256 values against their manifests. Restore the full archive, then incrementals in timestamp order, into an isolated workspace. Archives are additive; inspect state before starting workers.
2. Restore the current runner dependencies and the same model versions on a compatible GPU. Download model weights separately; they are not in these backups.
3. Restore media into the pipeline and ComfyUI input directories as needed. Inspect the latest queue, plan and run checkpoints; use a new version when code or inputs change.
4. Preserve completed jobs and scores. Reconcile any rendering/submitted job against surviving media/history before resubmission: a replacement server does not retain the old ComfyUI queue. Never assume an old native job is still running.
5. Reconfigure authenticated access and a sharing address. A temporary Cloudflare tunnel URL cannot be guaranteed after server loss.

Both public synchronization and private backup currently run on the operator computer. That computer must stay awake and online with its existing SSH/Git/Hugging Face access. GPU rendering itself continues independently. A verified archive is a recovery checkpoint, not an atomic snapshot of the entire live GPU queue; the newest in-flight work may need reconciliation.
