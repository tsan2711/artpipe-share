# Drawn-art lane — pipeline test findings (2026-09-24)

Test batch: `draw_explore.py` → `out-explore/` (19 VFX / 107 frames, 12 bot silhouettes, 12 tinted cores, one
real-size composite). This is **not art for any game**. It only exists to find what the `draw_*.py` lane is missing.

## Weak spots in the pipeline

| # | Problem seen in the test | What the pipeline lacks |
|---|---|---|
| 1 | White sprites + thin ink outline vanish on a light background | **Contrast check against the real background** (`checks.check_readable_at_64` only tests against the dark `#0A0E14`) → needs a list of backgrounds, not just one |
| 2 | On a dark background the ink `#4A3A52` outline disappears; faded frames go muddy grey | **Outline mode per background** (dark ink / light rim / both) + fade with a premultiplied blend instead of alpha on the outline |
| 3 | Several silhouettes collapse into one another at 11–16 px (spiky star ×3, round/square ×3) | **Silhouette distinctness check**: downscale → compare IoU/Hu moments pairwise within a set, fail if too similar. Inner detail doesn't count |
| 4 | Tint colours pass one at a time but clash as a set (3 violets, 3 greens) | **Pairwise ΔE check for tint palettes** + colourblind simulation (deuteranopia/protanopia) |
| 5 | Every flipbook hand-writes `t`, `ease_out`, alpha fade and frame count again | **Flipbook helper**: `frames(n, draw(t))` + a standard easing set + fade that keeps the outline |
| 6 | `glow()` loops per pixel in Python (512² × several calls) | Vectorise it (numpy) or cache it by (size, colour, power) |
| 7 | No preview of motion: the sheet only shows a frame strip | Write **GIF/APNG** per flipbook + an optional real-fps preview |
| 8 | The real-size composite is the most useful review step, but it's ad-hoc | Turn it into a standard `preview_realsize(sprites, bg, px)` step for every lane |
| 9 | Helpers (`canvas`, `ell`, `starpts`, `regular`, `tint`, `contact`) are copied across draw_*.py files | Factor them into a shared `drawkit.py` module |
| 10 | The greyscale→tint model (`sprite × colour`) makes the ink darker per team; accents (red core) get dyed too | Support an **untinted accent layer** (a separate mask), not just multiply |

## Suggested order
3 + 4 (automated checks, the most value) → 1 + 2 (backgrounds/outline) → 5 + 9 (helpers) → 7 + 8 (preview) → 6, 10.

---

# ComfyUI lane — pipeline test (2026-09-24, run 35990039405)

28 items (14 VFX, 14 characters) × 4 variants, animagine-xl-4.0-opt + icon_anime.json, 1024. Spec/manifest:
`pipetest/` (branch `artpipe/pipetest-2026-09-24`). Output: `out-pipetest1/` (+ `review_fx.png`, `review_ch.png`).

**Result: 112/112 "accepted" by tier 1, yet about half of the VFX are the wrong object.** This is the most important finding.

| # | Seen | Pipeline weakness |
|---|---|---|
| C1 | lightning → pink bear 3/4, shockwave → egg with a face, slash → moon/eye, magic-circle → blocks, coin-burst → eggs, levelup → random shapes | **Tier 1 does not check identity.** Needs a mandatory tier 2 (CLIP prompt↔image) before any "accepted" verdict. Right now the verdict looks valid while the images are wrong |
| C2 | Everything turns into a glossy pastel "bubble"; effects grow faces | `prompt_prefix "cute chibi anime game icon"` + animagine drag every subject into a **mascot**. VFX need a separate prefix/theme (no "chibi", add "effect, energy, no face") + negative "face, eyes, character" |
| C3 | `element` does not show: lightning (tech) comes out pink, slime (core) and poison look the same | Colour words sit at the end of the prompt → cut or outweighed by the style words. Check the order in `prompt.build()` / the 77-token cap |
| C4 | VFX come out as solid objects: no glow, no transparency, no motion | The lane only has an **"object icon" mode**. VFX need their own mode: white/greyscale output (tintable), additive/soft alpha, stylise must NOT fill flat areas, and frame output (anim lane or drawn) |
| C5 | Variants of the same item diverge wildly (composition, subject count) | No composition control (ControlNet / a reference image / a silhouette from the drawn lane as init). **Drawn lane → img2img** is a cheap way to get both the correct shape and the model's texture |
| C6 | Characters are fine: mushroom, cat, ghost, knight, slime, tank, bomber read well. Mothership / golem → round blobs | Characters fit the lane; the weak spot is "big" subjects (boss, spaceship) that get shrunk down to cute. A per-subject scale/size word is needed |
| C7 | On a dark background the ink outline disappears (same as the drawn lane) | The readability check uses only one background → see #1 above |

## Updated priorities
1. **C1: make tier 2 mandatory** (tier 1 alone lets through the wrong object).
2. **C2 + C4: separate VFX mode/theme** (prefix, negative, no stylise, greyscale output).
3. **C5: drawn silhouette → img2img**: combines the strengths of both lanes.
4. Then #3/#4 of the drawn lane (shape distinctness + tint ΔE).
