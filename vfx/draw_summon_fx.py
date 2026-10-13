#!/usr/bin/env python3
"""Signal Station pull show — VFX sprites, card backs and the landing pad, DRAWN (design/ux/commander-summon.md §3.6, §9).

    python3 tools/artpipe/draw_summon_fx.py [contact-dir]
      → Assets/UI/HUD/Icons/Fx/fx-sum-*.png      particles (≤ 64 px → UI Toolkit dynamic atlas) + beam / pillar / ring
      → Assets/UI/HUD/Icons/Gen/cardback-*.png   the "?" card backs ×3 (reveal beat 6)
      → Assets/UI/HUD/Icons/Gen/summon-pad.png   the cream landing pad (lights stay separate elements — they blink)
      → <contact-dir or ./out-vfx>/summon_fx_contact.png

VFX go the drawing lane, never ComfyUI (artpipe-vfx: the model turns effects into mascots). Cute rules (§3.6): round
4-point stars with an ink rim, bubbles with a highlight, white poof clouds, pastel confetti (round + rounded rects),
soft glows ≤ 35 % — no shards, no lightning. Tintable pieces are WHITE fill (+ ink rim): the show tints them per rarity.
"""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from draw_vfx_sprites import canvas, done, star4, glow, INK, WHITE, CREAM, K  # noqa: E402

NS = Path(__import__("os").environ.get("VFX_OUT") or Path(__file__).resolve().parent / "out")  # gốc NanoSwarm → thư mục ra (repo chia sẻ)
FX = NS / "Assets/UI/HUD/Icons/Fx"
GEN = NS / "Assets/UI/HUD/Icons/Gen"
FONT = Path(__file__).parent / "fonts"

SKY, LILAC, BUTTER, BLUSH, MINT = (101, 212, 245), (196, 159, 255), (255, 217, 122), (255, 169, 198), (94, 232, 154)


def small(im, size):
    return im.convert("RGBa").resize((size, size), Image.LANCZOS).convert("RGBA")


def soft_halo(im, spread, strength=0.8):
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(spread)).point(lambda v: min(255, int(v * strength)))
    halo = Image.new("RGBA", im.size, WHITE); halo.putalpha(a)
    halo.alpha_composite(im)
    return halo


# ── particles ─────────────────────────────────────────────────────────────────────────────────────────────
def sum_star():
    """Round-tipped 4-point star, white fill, ink rim, a highlight dot, soft white halo (tint colours star + halo)."""
    im, d = canvas(); c = 128 * K / 2
    star4(d, c, c, c * 0.7, 0.42, WHITE, INK, int(c * 0.09))
    d.ellipse((c - c * 0.2, c - c * 0.36, c - c * 0.04, c - c * 0.2), fill=(255, 255, 255, 255))
    return small(soft_halo(done(im), 5, 0.55), 64)


def sum_bubble():
    """Glassy bubble: pale fill, white rim, curved shine + dot — tint gives it the rarity colour."""
    im, d = canvas(); c = 128 * K / 2; r = c * 0.82
    d.ellipse((c - r, c - r, c + r, c + r), fill=(255, 255, 255, 90), outline=(255, 255, 255, 255), width=int(c * 0.1))
    d.arc((c - r * 0.7, c - r * 0.7, c + r * 0.7, c + r * 0.7), 200, 260, fill=(255, 255, 255, 235), width=int(c * 0.1))
    d.ellipse((c + r * 0.25, c - r * 0.6, c + r * 0.45, c - r * 0.4), fill=(255, 255, 255, 255))
    return small(done(im), 64)


def sum_puff():
    """White poof cloud with an ink outline (landing, §3.2 beat 4) — outlines first, fills on top."""
    im, d = canvas(); c = 128 * K / 2
    blobs = [(0.0, 0.14, 0.44), (-0.4, 0.22, 0.32), (0.4, 0.24, 0.32), (-0.18, -0.18, 0.36), (0.24, -0.16, 0.32)]
    for dx, dy, r in blobs:
        x, y, rr = c + dx * c, c + dy * c, r * c + c * 0.07
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=INK)
    for dx, dy, r in blobs:
        x, y, rr = c + dx * c, c + dy * c, r * c
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=WHITE)
    d.ellipse((c - c * 0.36, c - c * 0.34, c - c * 0.12, c - c * 0.18), fill=(236, 230, 255, 255))
    return small(done(im), 64)


def sum_confetti_round():
    im, d = canvas(); c = 128 * K / 2; r = c * 0.62
    d.ellipse((c - r, c - r, c + r, c + r), fill=WHITE, outline=INK, width=int(c * 0.12))
    d.ellipse((c - r * 0.5, c - r * 0.55, c - r * 0.05, c - r * 0.2), fill=(255, 255, 255, 255))
    return small(done(im), 32)


def sum_confetti_rect():
    im, d = canvas(); c = 128 * K / 2
    d.rounded_rectangle((c - c * 0.36, c - c * 0.66, c + c * 0.36, c + c * 0.66), int(c * 0.22), fill=WHITE,
                        outline=INK, width=int(c * 0.12))
    return small(done(im), 32)


def sum_glow():
    return small(glow(128, WHITE, 1.9), 64)


def sum_line():
    """Soft speed line (fall, beat 3): a white rounded streak fading to the top."""
    w, h = 16, 96
    im = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((w * K * 0.2, 0, w * K * 0.8, h * K), int(w * K * 0.3), fill=WHITE)
    a = im.getchannel("A"); px = a.load()
    for y in range(h * K):
        k = (y / (h * K)) ** 1.4
        for x in range(w * K):
            px[x, y] = int(px[x, y] * k * 0.85)
    im.putalpha(a)
    return im.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")


def sum_ring():
    """Soft ring, white — expands from landings / reveals."""
    im, d = canvas(); c = 128 * K / 2
    d.ellipse((c * 0.1, c * 0.1, c * 1.9, c * 1.9), outline=WHITE, width=int(c * 0.12))
    return done(im).filter(ImageFilter.GaussianBlur(0.9))


def sum_beam():
    """Beat 2: a rounded gold beam with a white core, soft glow around, fading at the top."""
    w, h = 64, 512
    im = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((w * K * 0.22, 0, w * K * 0.78, h * K), int(w * K * 0.28), fill=BUTTER + (255,))
    d.rounded_rectangle((w * K * 0.4, w * K * 0.1, w * K * 0.6, h * K - w * K * 0.1), int(w * K * 0.1), fill=WHITE)
    im = im.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
    im = soft_halo(im, 6, 0.6)
    a = im.getchannel("A"); px = a.load()
    for y in range(h):
        k = min(1.0, (y / h) * 1.8)
        for x in range(w):
            px[x, y] = int(px[x, y] * k)
    im.putalpha(a)
    return im


def sum_pillar():
    """×10 rare / legend: a soft pastel light pillar (white — tinted per rarity), brightest at the base."""
    w, h = 64, 256
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); px = im.load()
    for y in range(h):
        v = (y / (h - 1)) ** 1.6
        for x in range(w):
            u = abs(x - (w - 1) / 2) / ((w - 1) / 2)
            a = max(0.0, 1 - u ** 2) * v
            px[x, y] = (255, 255, 255, int(200 * a))
    return im


# ── card backs (reveal) ───────────────────────────────────────────────────────────────────────────────
def font(size):
    for name in ("Baloo2-ExtraBold.ttf", "Fredoka-Bold.ttf", "Nunito-Black.ttf"):
        p = FONT / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    for p in FONT.glob("*.ttf"):                                  # Fredoka-VF: pick the Bold instance
        f = ImageFont.truetype(str(p), size)
        try: f.set_variation_by_name("Bold")
        except Exception: pass
        return f
    return ImageFont.load_default()


def cardback(color, stars):
    """The "?" card: rarity colour, candy gloss streak, cream inner rim, a big white "?" with an ink outline, and
    1 / 2 / 3 little stars along the bottom (more = rarer)."""
    W, H = 256, 304
    im = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = 34 * K; ow = 7 * K
    d.rounded_rectangle((ow, ow, W * K - ow, H * K - ow), r, fill=color + (255,), outline=INK, width=ow)
    inset = 16 * K
    d.rounded_rectangle((inset, inset, W * K - inset, H * K - inset), r - 10 * K, outline=CREAM, width=4 * K)
    # soft darker lower half for depth
    shade = Image.new("RGBA", im.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    sd.rounded_rectangle((ow, H * K * 0.55, W * K - ow, H * K - ow), r, fill=(74, 58, 82, 38))
    im.alpha_composite(shade)
    # gloss streak
    gl = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    gd.rounded_rectangle((inset + 10 * K, inset + 10 * K, inset + 40 * K, H * K * 0.42), 14 * K, fill=(255, 255, 255, 120))
    im.alpha_composite(gl)
    # dotted pattern (on its own layer: ImageDraw replaces pixels, so a translucent dot drawn straight would punch a hole)
    dots = Image.new("RGBA", im.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(dots)
    for gy in range(5):
        for gx in range(4):
            if (gx + gy) % 2: continue
            x, y = (40 + gx * 58) * K, (44 + gy * 52) * K
            dd.ellipse((x - 5 * K, y - 5 * K, x + 5 * K, y + 5 * K), fill=(255, 255, 255, 90))
    im.alpha_composite(dots)
    # the "?"
    f = font(170 * K)
    txt = "?"
    bbox = d.textbbox((0, 0), txt, font=f, stroke_width=12 * K)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((W * K - tw) / 2 - bbox[0], (H * K * 0.46 - th / 2) - bbox[1]), txt, font=f, fill=WHITE,
           stroke_width=12 * K, stroke_fill=INK)
    # stars
    for i in range(stars):
        cx = W * K / 2 + (i - (stars - 1) / 2) * 44 * K
        star4(d, cx, H * K * 0.84, 17 * K, 0.42, WHITE if stars < 3 else BUTTER + (255,), INK, 4 * K)
    return im.convert("RGBa").resize((W, H), Image.LANCZOS).convert("RGBA")


# ── landing pad ───────────────────────────────────────────────────────────────────────────────────────
def pad():
    """Cream pad: a thick side, glossy top, a soft inner disc (tinted by the show — kept white here), ink outline."""
    W, H = 384, 110
    im = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ow = 6 * K
    d.ellipse((ow, H * K * 0.22, W * K - ow, H * K - ow), fill=(233, 217, 200, 255), outline=INK, width=ow)
    d.ellipse((ow, ow, W * K - ow, H * K * 0.78), fill=CREAM, outline=INK, width=ow)
    d.ellipse((W * K * 0.2, H * K * 0.16, W * K * 0.8, H * K * 0.62), fill=(255, 255, 255, 255), outline=(233, 217, 200, 255), width=3 * K)
    d.arc((W * K * 0.08, H * K * 0.06, W * K * 0.5, H * K * 0.5), 190, 250, fill=(255, 255, 255, 255), width=8 * K)
    return im.convert("RGBa").resize((W, H), Image.LANCZOS).convert("RGBA")


def contact(named, path):
    cell = 160; cols = 6
    rows = (len(named) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell * 2), (0, 0, 0, 0))
    for band, bg in ((0, (255, 246, 236, 255)), (1, (60, 50, 80, 255))):
        for i, (_, im) in enumerate(named):
            x, y = (i % cols) * cell, ((i // cols) + band * rows) * cell
            sheet.paste(bg, (x, y, x + cell, y + cell))
            t = im.copy(); t.thumbnail((cell - 12, cell - 12), Image.LANCZOS)
            sheet.alpha_composite(t, (x + (cell - t.width) // 2, y + (cell - t.height) // 2))
    sheet.save(path)


if __name__ == "__main__":
    FX.mkdir(parents=True, exist_ok=True)
    GEN.mkdir(parents=True, exist_ok=True)
    named = []
    for name, im in (("fx-sum-star", sum_star()), ("fx-sum-bubble", sum_bubble()), ("fx-sum-puff", sum_puff()),
                     ("fx-sum-confetti-round", sum_confetti_round()), ("fx-sum-confetti-rect", sum_confetti_rect()),
                     ("fx-sum-glow", sum_glow()), ("fx-sum-line", sum_line()), ("fx-sum-ring", sum_ring()),
                     ("fx-sum-beam", sum_beam()), ("fx-sum-pillar", sum_pillar())):
        im.save(FX / f"{name}.png"); named.append((name, im))
    for name, im in (("cardback-common", cardback(SKY, 1)), ("cardback-rare", cardback(LILAC, 2)),
                     ("cardback-legend", cardback(BUTTER, 3)), ("summon-pad", pad())):
        im.save(GEN / f"{name}.png"); named.append((name, im))
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "out-vfx"
    out.mkdir(parents=True, exist_ok=True)
    contact(named, out / "summon_fx_contact.png")
    print(f"{len(named)} → {FX} + {GEN}; contact → {out / 'summon_fx_contact.png'}")
