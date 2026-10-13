> **2026-10-02: every HUD icon + UI frame is now the "bánh bao" look** — source of truth `sumi/icons.mjs` (+ `sumi/kit.py`, `sumi/pieces.py`, `sumi/badges.py`).
> The older draw_*.py / gen_* icon scripts write the same files in the old look — don't re-run them. See `production/banhbao-redraw.md`.

# NanoSwarm — artpipe (icon lane)

NanoSwarm uses the shared artpipe tool in **sanne-kit** (`sanne-kit/Tools/artpipe/`) (only one project renders at a
time on the shared PC). Nothing is duplicated — NanoSwarm only owns its **data**:

- `art-direction.md` — theme/spec (palette, shading, generation, subtype_shape). Nanobot flat-vector.
- `nanoswarm-icons.yaml` — icon manifest (10 icons: Energy, Matter, 3 bots, 5 upgrades).

The tool reads everything relative to the **project root** (`ARTPIPE_PROJECT`, default = cwd), so run it
from `Seriously/NanoSwarm/`.

## Generate (via CI — the normal path)

Runs on the shared render PC through GitHub Actions in **sanne-kit** (self-hosted runner) — no LAN IP
needed. The job checks out this repo's `NanoSwarm/` folder (branch you are on — push it first), so
`spec`/`catalog` are relative to `NanoSwarm/`. Run from `Seriously/NanoSwarm/`:

```
python3 ../../sanne-kit/Tools/artpipe/remote.py \
    --out      tools/artpipe/out \
    --spec     tools/artpipe/art-direction.md \
    --catalog  tools/artpipe/nanoswarm-icons.yaml \
    --checkpoint sd_xl_base_1.0.safetensors \
    --workflow-file icon_sdxl_vector.json \
    --gen-size 1024 --variants 4
```

Prereq: the render PC has **SDXL base + DD-vector-v2 LoRA + rembg** (`sanne-kit/Tools/artpipe/setup_pc.ps1 -Sdxl`) and
the runner is online. Add `--only harvester` for one icon; `--attach <run_id>` to re-fetch a batch.

Output downloads to `--out`: `icons/<slug>.png` (128px, matte'd + stylised) · `raw/` (originals) ·
`report.json` (verdicts — read `scores_raw`, not `scores`; see the artpipe-icons skill).

## Post-tuning without the GPU

Changed matte/stylise thresholds? Re-run post only, no render, from `Seriously/NanoSwarm/`:
`../../sanne-kit/Tools/artpipe/.venv/bin/python3 ../../sanne-kit/Tools/artpipe/run.py --spec tools/artpipe/art-direction.md --catalog tools/artpipe/nanoswarm-icons.yaml --out tools/artpipe/out2 ingest tools/artpipe/out/raw`

(Direct LAN run — `COMFYUI_URL=http://<ip>:8188 run.py … generate --provider comfyui` — also works if
you ever want to bypass CI, but CI is the normal path.)

## Import to Unity

Copy accepted `out/icons/*.png` → `NanoSwarm/Assets/UI/HUD/Icons/` (overwriting the placeholder
geometric icons), reimport as Sprite. The HUD USS references them by filename.

## Validated offline (2026-09-17)

All 10 manifest icons build valid ≤77-token prompts against this spec. Only blocker to a real run:
the PC's `COMFYUI_URL`.
