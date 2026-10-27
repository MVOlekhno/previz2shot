# workflows
ComfyUI API-format exports (File → Export (API)) used by `previz2shot run`. All core/open-weights nodes.

## flux2_klein_first_frame_api.json
FLUX.2 Klein 4B (flux-2-klein-4b, qwen_3_4b, flux2-vae) — NOT FLUX 3. Grey playblast frame 1 → ReferenceLatent → 4-step styled first frame 1920x1088.
Patched by CLI: `l1.image` (LoadImage), `5.text` (prompt), `10.filename_prefix` (SaveImage).

## ltx25_l2r_twostage_kf_api.json (used by CLI)
LTX-2.5 22B IC-LoRA Layout-to-Render, two-stage distilled (960x544 8 steps → 1920x1088 3 steps, CFG 1, euler_ancestral) with first-frame keyframe.
Patched by CLI: `8.file` (LoadVideo), `10.image` (LoadImage keyframe), `5.text` (prompt), `22.filename_prefix` (SaveVideo).

## ltx25_l2r_twostage_api.json / ltx25_l2r_stage1_api.json
Same graph without keyframe / stage 1 only (preview). Not used by the CLI.

`upstream/` — original ComfyUI-LTXVideo UI workflow this was derived from.
