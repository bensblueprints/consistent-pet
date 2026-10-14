# Setup and operation

## Runtime environment

The pilot runs on Linux/Python 3.12 with an RTX PRO 6000 Blackwell 96 GB,
PyTorch 2.10.0+cu130, Transformers 5.17.0 and native ComfyUI. Use a CUDA-compatible
PyTorch environment that already works on the GPU. `requirements.txt` does not
replace PyTorch or install GPU drivers.

Provision models separately under their publishers' applicable licenses. Do not
put weights or access tokens in this repository. The baseline graph expects:

| ComfyUI location | Filename |
| --- | --- |
| `models/diffusion_models` | `flux-2-klein-base-4b-fp8.safetensors` |
| `models/text_encoders` | `qwen_3_4b.safetensors` |
| `models/vae` | `full_encoder_small_decoder.safetensors` |
| `models/checkpoints` | `sam3.1_multiplex_fp16.safetensors` |

The local reviewer is `Qwen/Qwen3-VL-32B-Instruct`, pilot revision
`0cfaf48183f594c314753d30a4c4974bc75f3ccb`. The private manifest points to an existing
local weights directory. Models are loaded with `local_files_only=True`.

Required native nodes include `SAM3_Detect`, `EmptyFlux2LatentImage`,
`Flux2Scheduler`, `ReferenceLatent`, `SamplerCustomAdvanced`, image scaling,
mask loading, inpainting VAE encoding and masked compositing. Run the preflight
script against the actual ComfyUI instance before starting.

The bundled baseline graph came from the existing, functioning multi-reference
FLUX.2 klein workflow, with photo names, prompts and output paths replaced by
placeholders. SAM segmentation follows Comfy-Org's SAM3 utility template. The
refinement runner builds the repair and composite nodes around that baseline.

## Private manifest

Copy `examples/manifest.example.json` outside the repository and replace its
paths. Image paths can be absolute or relative to that manifest. The judge model
path must identify an installed local directory.

Supply actual, distinct dog identities. The initializer hashes the original file
for identity grouping; it cannot discover that two different photographs show
the same dog. Do not list one dog as several identities. At least seven dogs are
required; ten gives more useful coverage. Face crops must be real, unedited
close-ups from the same dog. Automatic subject detection/cropping of new user
uploads is not part of this evaluation harness.

Each reference needs a short costume description for segmentation and a scene
instruction. Keep these pet-neutral: describe the suit, pose and setting, not
the old template animal's breed or fur. `require_clothing: false` allows a design
without clothing; the animal mask must still satisfy geometry checks.

Initialization creates a new runtime atomically and refuses to overwrite an
existing path. It submits no GPU work. The subsequent `--run` explicitly enables
generation, which consumes the rented GPU's time.

## Services

Run the scorer, auto-refiner, studio and optional telemetry under a process
manager. [Supervisor examples](../examples/supervisor.conf.example) use fixed
code/runtime locations that you must adapt before installing.

The scorer owns one long-lived Qwen process. The refiner submits jobs to native
ComfyUI, which serializes its queue with other existing work. An image's score
is read only after the exact output hash matches the current whole-pet rubric.
Auto-refinement rows have priority within the first-score queue.

Do not blindly restart failed refinement runs: inspect their private job records
first. Normal resume recovers the recorded native UUID. If its submission cannot
be reconciled, the runner stops rather than risking a second charged render.

To stop new submissions, create `STOP` inside
`$FPG_REVIEW_ROOT/auto-refinement/<run>/`, or stop only the refiner service.
An already queued native job can finish. Resuming the same version requires the
same code, plan, inputs and judge specification. Policy changes require a new
version, preserving earlier outputs and assessments.

## Public studio

Only explicitly staged rows and their allowlisted images are served. Private
plans, job graphs, SQLite files, model configuration and GPU controls are not
HTTP endpoints. The view token is generated once and retained across restarts.
Use a trusted HTTPS proxy; never expose the raw ComfyUI control port for viewers.

The live four-column page offers an **Auto refinement** filter and a **What the
AI changed for this attempt** panel. It shows separate face/fur/body/design
scores. Human stars and notes remain optional and do not gate the auto-loop.
