# GPU recovery handoff

At 2026-10-14 22:05 UTC, the RTX 6000 instance reported NVIDIA-SMI ERR/N/A
telemetry. A fresh Python process reported CUDA unavailable and tensor allocation
failed with `RuntimeError: No CUDA GPUs are available`. GPU device nodes remain
present. This is not merely a disconnected dashboard or a queue ordering issue.

The coordinator was stopped to prevent further timeout/error accumulation.
Renderer, reviewer and sharing tunnel were not restarted. The private queue was
backed up before recovery work. No jobs, outputs or accepted workflows were deleted.

Last recorded queue: 749 total, 86 accepted, 646 pending, 16 retry pending,
1 started/resumable, 0 blocked. Four of the 24 heaven references passed; the
remaining 20 are NOT complete. The current reference is Female Angel Golden Retriever.

Recovery requires restoring GPU availability on the rented host. Do not install
drivers inside the container or destroy/recycle the instance. After host recovery:

1. Verify a fresh CUDA allocation and synchronization, not just device enumeration.
2. Reconcile retained native ComfyUI prompt IDs/history before retrying interrupted renders.
3. Inspect cached heaven planner failures; archive failed responses with evidence
   before retrying so the same cached error is not repeatedly consumed.
4. Resume the existing priority wrapper with its unchanged frozen runner and run
   version. Preserve accepted artifacts, input scores and original resource limits.
5. Verify an actual new render and independent assessment before reporting resumed.

Original catalog work follows the priority references. Do not equate completed
Higgsfield template generation with completed GPU identity-transfer validation.
