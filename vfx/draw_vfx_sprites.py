#!/usr/bin/env python3
"""VFX art for NanoSwarm, drawn (not generated) in the art-direction palette — ui-polish-vfx-plan-2026-09-24.md.

    python3 NanoSwarm/tools/artpipe/draw_vfx_sprites.py
      → Assets/UI/HUD/Icons/Fx/fx-*.png        UI Toolkit flipbook frames + pseudo-particles (128 px, atlased)
      → Assets/Sprites/Fx/world_fx_atlas.png   4×4 atlas of 128 px tiles for the world ParticleSystems
      → <scratchpad or ./out-vfx>/vfx_contact.png  contact sheet for review

Why drawn: FX silhouettes must be exact at 20–60 px (the 2026-09-23 diffusion batch turned functional shapes into
"cute bubbles"). Tintable sprites are WHITE fill + ink outline: the tint colours the fill, the outline stays dark.
Supersampled 4× then downscaled, like draw_ui_symbols.py.
"""
import math, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

NS = Path(__import__("os").environ.get("VFX_OUT") or Path(__file__).resolve().parent / "out")  # gốc NanoSwarm → thư mục ra (repo chia sẻ)
UI_OUT = NS / "Assets/UI/HUD/Icons/Fx"
WORLD_OUT = NS / "Assets/Sprites/Fx"
K = 4                                     # supersample
T = 128                                   # tile / frame size
INK = (74, 58, 82, 255)
WHITE = (255, 255, 255, 255)
CREAM = (255, 246, 236, 255)
TECH, ENERGY, MATTER, CORE, PINK = (101, 212, 245), (94, 232, 154), (196, 159, 255), (255, 217, 122), (251, 175, 203)


def canvas(size=T):
    im = Image.new("RGBA", (size * K, size * K), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def done(im, size=T):
    # premultiplied resize: plain RGBA LANCZOS drags transparent-black into soft edges (grey halos)
    return im.convert("RGBa").resize((size, size), Image.LANCZOS).convert("RGBA")


def rgba(c, a=255):
    return (c[0], c[1], c[2], a)


def star4(d, cx, cy, r, inner, fill, outline=INK, ow=None):
    pts = []
    for i in range(8):
        a = -math.pi / 2 + i * math.pi / 4
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill, outline=outline, width=ow or max(2, int(r * 0.14)))


def glow(size=T, color=WHITE, power=1.6):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); px = im.load(); c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            r = math.hypot(x - c, y - c) / c
            a = max(0.0, 1.0 - r) ** power
            px[x, y] = (color[0], color[1], color[2], int(255 * a))
    return im


def haloed(im, shrink=0.8, spread=0.075, strength=0.7):
    """Baked glow (no post-processing — Bi 2026-09-24): shrink the shape to leave margin, then lay a soft halo of
    its own silhouette under it. White halo on a white tintable sprite → the particle tint colours both."""
    n = int(T * shrink); o = (T - n) // 2
    small = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    small.alpha_composite(im.convert("RGBa").resize((n, n), Image.LANCZOS).convert("RGBA"), (o, o))
    a = small.getchannel("A").filter(ImageFilter.GaussianBlur(T * spread))
    a = a.point(lambda v: min(255, int(v * strength * 1.8)))
    halo = Image.new("RGBA", (T, T), WHITE); halo.putalpha(a)
    halo.alpha_composite(small)
    return halo


# ── UI: tap ripple (frame-by-frame: the ring squashes + a few droplets pop, then fades) ─────────────────
def tap_frames(n=6):
    frames = []
    for i in range(n):
        t = i / (n - 1)
        im, d = canvas(); c = T * K / 2
        r = (0.24 + 0.6 * (1 - (1 - t) ** 2)) * c
        th = max(3 * K, int((0.22 - 0.14 * t) * c))
        a = int(255 * (1 - 0.8 * t ** 1.4))
        sq = 1 + 0.12 * math.sin(t * math.pi)                         # a little horizontal squash
        box = (c - r * sq, c - r / sq, c + r * sq, c + r / sq)
        ow = 3 * K
        d.ellipse((box[0] - ow, box[1] - ow, box[2] + ow, box[3] + ow), outline=rgba(INK, a), width=th + 2 * ow)
        d.ellipse(box, outline=rgba(CREAM, a), width=th)
        d.arc((box[0] + th * 0.3, box[1] + th * 0.3, box[2] - th * 0.3, box[3] - th * 0.3), 200, 250,
              fill=rgba(TECH, a), width=max(K, th // 3))                 # little glint
        if 0 < i < n - 1:                                            # droplets
            for k in range(4):
                ang = math.pi / 4 + k * math.pi / 2
                rr = r * 1.16; sz = (0.085 - 0.04 * t) * c
                x, y = c + rr * math.cos(ang), c + rr * math.sin(ang)
                d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=rgba(TECH, a), outline=rgba(INK, a), width=K * 3)
        frames.append(done(im))
    return frames


# ── UI: reward shine (rays grow + turn, centre glow fades) ────────────────────────────────────────────
def shine_frames(n=8):
    frames = []
    for i in range(n):
        t = i / (n - 1)
        im, d = canvas(); c = T * K / 2
        a = int(255 * (1 - t ** 2.2))
        rot = t * math.pi / 5
        grow = math.sin(min(1.0, t * 1.6) * math.pi / 2)
        g = glow(T * K, CREAM, 1.8)
        g.putalpha(g.getchannel("A").point(lambda v: int(v * (1 - t) * 0.85)))
        im.alpha_composite(g)
        for k in range(8):
            ang = rot + k * 2 * math.pi / 8
            big = k % 2 == 0
            l = (0.42 + 0.50 * grow) * c * (1.0 if big else 0.72)
            hw = (0.11 if big else 0.08) * c                           # chunky diamond ray, half width
            ux, uy = math.cos(ang), math.sin(ang); nx, ny = -uy, ux
            r0, rm = 0.16 * c, 0.16 * c + (l - 0.16 * c) * 0.38
            p = [(c + ux * r0, c + uy * r0), (c + ux * rm + nx * hw, c + uy * rm + ny * hw),
                 (c + ux * l, c + uy * l), (c + ux * rm - nx * hw, c + uy * rm - ny * hw)]
            d.polygon(p, fill=rgba(CORE if big else CREAM, a), outline=rgba(INK, a), width=2 * K)
        star4(d, c, c, c * (0.30 - 0.12 * t), 0.42, rgba(CREAM, a), outline=rgba(INK, a), ow=2 * K)
        frames.append(done(im))
    return frames


def ui_star():
    im, d = canvas(); c = T * K / 2
    star4(d, c, c, c * 0.86, 0.38, rgba(CORE))
    d.ellipse((c - c * 0.28, c - c * 0.46, c - c * 0.08, c - c * 0.26), fill=(255, 255, 255, 190))
    return done(im)


def ui_confetti():
    im, d = canvas(); c = T * K / 2
    d.rounded_rectangle((c - c * 0.36, c - c * 0.62, c + c * 0.36, c + c * 0.62), int(c * 0.18), fill=WHITE,
                        outline=INK, width=int(c * 0.12))
    return done(im)


# ── world atlas tiles (white = tintable via particle start colour) ────────────────────────────────────
def tile_ring():
    im, d = canvas(); c = T * K / 2
    d.ellipse((c * 0.12, c * 0.12, c * 1.88, c * 1.88), outline=WHITE, width=int(c * 0.14))
    return done(im).filter(ImageFilter.GaussianBlur(0.8))


def tile_puff():
    im, d = canvas(); c = T * K / 2
    blobs = [(0.0, 0.12, 0.46), (-0.38, 0.2, 0.34), (0.38, 0.22, 0.34), (-0.18, -0.2, 0.36), (0.22, -0.18, 0.34)]
    for dx, dy, r in blobs:                                          # outline pass
        x, y, rr = c + dx * c, c + dy * c, r * c
        d.ellipse((x - rr - c * 0.08, y - rr - c * 0.08, x + rr + c * 0.08, y + rr + c * 0.08), fill=INK)
    for dx, dy, r in blobs:
        x, y, rr = c + dx * c, c + dy * c, r * c
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=WHITE)
    d.ellipse((c - c * 0.4, c - c * 0.38, c - c * 0.14, c - c * 0.2), fill=(255, 255, 255, 255))
    return done(im)


def tile_spark():
    im, d = canvas(); c = T * K / 2
    d.polygon([(c, c * 0.06), (c + c * 0.16, c), (c, c * 1.94), (c - c * 0.16, c)], fill=WHITE, outline=INK, width=int(c * 0.06))
    return done(im)


def tile_star():
    im, d = canvas(); c = T * K / 2
    star4(d, c, c, c * 0.86, 0.38, WHITE)
    return done(im)


def tile_mote():
    im, d = canvas(); c = T * K / 2
    d.polygon([(c, c * 0.25), (c * 1.55, c), (c, c * 1.75), (c * 0.45, c)], fill=WHITE, outline=INK, width=int(c * 0.1))
    return done(im)


def world_atlas():
    # star / spark / mote carry a baked halo; puff is smoke and confetti is paper, so they stay flat
    tiles = [glow(), haloed(tile_star()), tile_ring(), tile_puff(), haloed(tile_spark()), ui_confetti(),
             haloed(tile_mote())]
    atlas = Image.new("RGBA", (T * 4, T * 4), (0, 0, 0, 0))
    for i, t in enumerate(tiles):
        atlas.alpha_composite(t, ((i % 4) * T, (i // 4) * T))
    return atlas, tiles


def contact(named, path):
    cols = 8; cell = 140
    rows = (len(named) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell * 2), (0, 0, 0, 0))
    for bg_row, bg in ((0, (255, 246, 236, 255)), (1, (10, 14, 20, 255))):
        for i, (_, im) in enumerate(named):
            x, y = (i % cols) * cell, ((i // cols) + bg_row * rows) * cell
            sheet.paste(bg, (x, y, x + cell, y + cell))
            sheet.alpha_composite(im.resize((128, 128)), (x + 6, y + 6))
    sheet.save(path)


if __name__ == "__main__":
    UI_OUT.mkdir(parents=True, exist_ok=True); WORLD_OUT.mkdir(parents=True, exist_ok=True)
    named = []
    for i, f in enumerate(tap_frames()):
        f.save(UI_OUT / f"fx-tap-{i}.png"); named.append((f"tap{i}", f))
    for i, f in enumerate(shine_frames()):
        f.save(UI_OUT / f"fx-shine-{i}.png"); named.append((f"shine{i}", f))
    for name, im in (("fx-star", haloed(ui_star())), ("fx-confetti", ui_confetti()), ("fx-dot", glow())):
        im.save(UI_OUT / f"{name}.png"); named.append((name, im))
    atlas, tiles = world_atlas()
    atlas.save(WORLD_OUT / "world_fx_atlas.png")
    named += [(f"tile{i}", t) for i, t in enumerate(tiles)]
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "out-vfx"
    out.mkdir(parents=True, exist_ok=True)
    contact(named, out / "vfx_contact.png")
    print(f"{len(named)} sprites → {UI_OUT} + {WORLD_OUT}; contact → {out / 'vfx_contact.png'}")
