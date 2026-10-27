# previz2shot
Blender grey playblast → FLUX.2 Klein 4B styled first frame → LTX-2.5 22B IC-LoRA Layout-to-Render video → back into Blender VSE.
Open weights only, core ComfyUI nodes only (no partner/API nodes).

## Pipeline
1. **Blender** — render a grey playblast with the addon (`addon/previz2shot`, Blender 4.2+).
2. **First frame** — `workflows/flux2_klein_first_frame_api.json`: playblast frame 1 + prompt → styled 1920x1088 keyframe (FLUX.2 Klein 4B, 4 steps, ReferenceLatent).
3. **Video** — `workflows/ltx25_l2r_twostage_kf_api.json`: layout video + keyframe → render (960x544 8 steps → 1920x1088 3 steps, CFG 1).
4. **Back to Blender** — import the result into the VSE.

## Models (ComfyUI `models/`)
FLUX.2 Klein 4B (open weights):
- diffusion_models: `flux-2-klein-4b.safetensors`
- text_encoders: `qwen_3_4b.safetensors`
- vae: `flux2-vae.safetensors`

LTX-2.5:
- diffusion_models: `ltx-2.5-22b-distilled-transformer-bf16.safetensors`
- loras: `ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors`
- latent_upscale_models: `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors`
- vae: `ltx-2.5-video-vae-bf16.safetensors`
- text_encoders: `gemma4-12b-with-proj-ltx-2.5-bf16.safetensors`

## Install & run
```
pip install -e .            # needs ffmpeg on PATH
export COMFY_API_KEY=...    # Comfy Cloud (default backend)
previz2shot run --layout shot.mp4 --prompt "..." --out out.mp4
# --backend local  -> self-hosted ComfyUI (COMFY_BASE_URL, default http://127.0.0.1:8188)
# --backend api    -> your own deployment (COMFY_BASE_URL + COMFY_API_KEY)
```
Optional: `COMFY_MIN_BALANCE_CENTS` refuses to submit a job when the Cloud balance is below that floor.

## Demo
`demo.mp4` (16 s, 1920x1088, h264, silent): titled grey playblast vs LTX render side by side for two shots.
Note: the LTX clips are earlier runs (s7), not renders of the newest v3 grey playblasts.

## FLUX 3
FLUX 3 is **not** used. The BFL FLUX 3 bonus is blocked until FLUX 3 weights are available on Comfy Cloud.

## License
Code: MIT (`LICENSE`). LTX-2.x weights: LTX-2.x Community License (not MIT). FLUX.2 Klein weights: their own license. See `NOTICE`.

## Docs
- [Atlas Studio bake pipeline (RU)](docs/atlas_studio_bake_ru.md) — node graph hi-poly→retopo→Bake High→Low; Cycles recipe for IEA-5 / characters.
