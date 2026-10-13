#!/usr/bin/env python3
"""Motion preview for drawn VFX — so effects are judged MOVING, not as a still frame strip.

    python3 tools/artpipe/vfx_preview.py <module> [out-dir] [--only a,b] [--fps 12]
      <module>  a draw script next to this file exposing VFX = [(name, fn() -> [frames], note), ...]
                (draw_explore, or any draw_*.py that follows the same contract)
      → <out>/vfx_all_anim.gif        every effect looping at once (open in Safari — Preview shows frames, not motion)
      → <out>/vfx_gif/<name>.gif      one effect, light map bg | dark HUD bg side by side
      → <out>/vfx_frames/<name>/*.png every frame as its own file
      → <out>/vfx_realsize.gif        the same loop at real on-screen sizes (24 / 48 / 96 px) — the readability test

Frames are RGBA 128 px, white fill (= tintable) + ink outline, like draw_vfx_sprites.py. One-shots get a short blank
gap before looping so they read as one-shots.
"""
import argparse, importlib, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
LIGHT, DARK = (246, 230, 212), (10, 14, 20)          # map clear colour · HUD panel
INK = (74, 58, 82)
GAP = 3                                              # blank frames after a one-shot


def _on(bg, frame, size):
    im = Image.new("RGB", (size, size), bg)
    f = frame.resize((size, size), Image.LANCZOS)
    im.paste(f, (0, 0), f)
    return im


def _save_gif(seq, path, fps):
    seq[0].save(path, save_all=True, append_images=seq[1:], duration=int(1000 / fps), loop=0)


def export(fx, out, fps=12):
    out = Path(out); (out / "vfx_gif").mkdir(parents=True, exist_ok=True); (out / "vfx_frames").mkdir(exist_ok=True)
    for name, frames in fx:
        d = out / "vfx_frames" / name; d.mkdir(exist_ok=True)
        for i, f in enumerate(frames): f.save(d / f"{name}_{i:02d}.png")
        blank = Image.new("RGBA", frames[0].size, (0, 0, 0, 0))
        seq = []
        for f in frames + [blank] * GAP:
            im = Image.new("RGB", (512, 256))
            im.paste(_on(LIGHT, f, 256), (0, 0)); im.paste(_on(DARK, f, 256), (256, 0))
            seq.append(im)
        _save_gif(seq, out / "vfx_gif" / f"{name}.gif", fps)

    n_t = max(len(f) + GAP for _, f in fx) * 2
    cols, cell = 5, 200; rows = (len(fx) + cols - 1) // cols
    grid = []
    for t in range(n_t):
        im = Image.new("RGB", (cols * cell, rows * cell), LIGHT); d = ImageDraw.Draw(im)
        for k, (name, frames) in enumerate(fx):
            i = t % (len(frames) + GAP); x, y = (k % cols) * cell, (k // cols) * cell
            if i < len(frames):
                f = frames[i].resize((170, 170), Image.LANCZOS); im.paste(f, (x + 15, y + 10), f)
            d.text((x + 6, y + 184), name, fill=INK)
        grid.append(im)
    _save_gif(grid, out / "vfx_all_anim.gif", fps)

    sizes = (24, 48, 96); row = 110; colw = sum(sizes) + 24
    real = []
    for t in range(n_t):
        im = Image.new("RGB", (len(fx) * colw, 2 * row), LIGHT)
        im.paste(DARK, (0, row, len(fx) * colw, 2 * row))
        for k, (_, frames) in enumerate(fx):
            i = t % (len(frames) + GAP)
            if i >= len(frames): continue
            x = k * colw + 6
            for s in sizes:
                f = frames[i].resize((s, s), Image.LANCZOS)
                for yb in (0, row):
                    im.paste(f, (x, yb + (row - s) // 2), f)
                x += s + 4
        real.append(im)
    _save_gif(real, out / "vfx_realsize.gif", fps)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("module"); ap.add_argument("out", nargs="?", default=None)
    ap.add_argument("--only", default=""); ap.add_argument("--fps", type=float, default=12)
    a = ap.parse_args()
    sys.path.insert(0, str(HERE)); mod = importlib.import_module(a.module)
    only = {s for s in a.only.split(",") if s}
    fx = [(n, fn()) for n, fn, *_ in mod.VFX if not only or n in only]
    out = export(fx, a.out or HERE / f"out-{a.module}", a.fps)
    print(f"{len(fx)} effects → {out}/vfx_all_anim.gif  (open -a Safari)")
