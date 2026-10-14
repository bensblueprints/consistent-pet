# Bonnie the Getaway Queen — refinement report

Status: **in_progress**. Updated 2026-10-14T07:08:25Z.

Queue `catalog-llm-v3`; run `catalog-llm-v3-mobsters-011-bonnie-the-getaway-queen-round-2`; 2 rounds started; 8 generated candidates.

The resident Qwen3-VL-32B proposes bounded graph changes from reference images, original tuning pets, previous outputs and training-only critiques. The independent scoring prompt and weights remain fixed.
Graph strategies: whole-subject inpainting or fresh subject latent with protected-background compositing. FLUX.2 Klein base 4B and SAM3.1 remain the generation/segmentation stack.

Acceptance requires every face/fur/body/design score >=9, high confidence, no major defects, and successful frozen cross-dog checks. AI scores are estimates, not proof of perfect identity or print quality.
Exact customer images, masks, graph attempts, critiques and provisional recipes remain in the private runtime. No provisional graph has been published as an accepted workflow.
Training failures return to the queue. Failed held-out checks are not supplied as tuning feedback. Technical failures retain their native job IDs for safe resume.
