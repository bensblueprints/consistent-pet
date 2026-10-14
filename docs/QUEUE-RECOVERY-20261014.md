# Costume queue recovery — 14 October 2026

The live `catalog-llm-v3` queue blocked Bonnie the Getaway Queen after three coordinator retries. The saved local planner response proposed `design_megapixels: 0.2`, below the existing minimum of `0.25`. Each retry consumed the same failed response, so the coordinator never reached a new render. This was not a failed quality assessment or a GPU outage.

## Recovery applied

The queue coordinator alone was stopped briefly. The failed request/response and queue state were backed up in the private runtime's `planner-recovery/` directory. The rejected numeric parameter was explicitly changed to `0.25` and the entire proposal was checked using the original frozen runner's validator. The original raw response and an operator-recovery audit record were retained. The same blocked run was made resumable and the coordinator restarted.

All pre-existing native job records were hash-compared before and after recovery and were unchanged. Code fingerprints, original photos, assessments, acceptance thresholds, reviewer weights, generation service and sharing tunnel were not modified. The active Bank Job Darling validation run remains resumable with its saved results.

`scripts/recover-planner-bound.py` implements this narrowly scoped operator action. It requires the catalog lock, a blocked reference matching the request, matching payload fingerprints, precisely the rejected design-conditioning bound error, and full schema validation of the repaired proposal. It refuses unrelated errors, out-of-range replacements and changed requests. It is not an automatic acceptance mechanism or a general-purpose failure override. Runtime use requires Linux and the original frozen runner directory; do not add it to an already fingerprinted runner directory.

Example (use actual private locations and IDs):

```bash
python /operator-tools/recover-planner-bound.py \
  --root /private/runtime --runner /private/frozen-runner/scripts \
  --queue-version QUEUE --reference-id REFERENCE --request-id REQUEST \
  --design-megapixels 0.25
```

Stop only the queue coordinator first and restart it even if recovery fails. The parameter repair does not change the planner's general response-generation behavior: other invalid responses can still require inspection. Never clear unrelated errors or mark a workflow accepted to move the counter.

## Queue display

The live review page now explains that accepted means a fully validated costume workflow. It shows renders submitted in the current round, actual rendering/scoring activity when available, the last coordinator stage and its age. Started/resumable workflows are no longer labeled as simultaneously active GPU jobs. These UI updates are read from disk and required no tunnel or review-server restart.

## Verification

Three recovery tests passed locally and on Linux using the deployed frozen validator: evidence preservation, bounds/schema enforcement, and rejection of unrelated errors or mismatched requests. JavaScript syntax check passed and the served private review page contains the new progress labels.

Post-recovery snapshot: zero blocked, zero accepted, 723 pending, two started/resumable references. Bonnie advanced from four renders in the preserved round to six; five rows were complete and the sixth was rendering. Quality validation remains in progress. This fixes the recorded blocker; it does not claim all 725 workflows are finished or accepted.
