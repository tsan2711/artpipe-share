#!/usr/bin/env python3
"""Dựng ảnh bìa bộ sưu tập cho README từ docs/samples/<bộ>/*.png.

    python3 tools/make_gallery.py      # → docs/samples/<bộ>.png (mỗi bộ một dải thẻ) + docs/samples/cover.png

Thêm bộ mới: tạo docs/samples/<tên>/ chứa PNG nền trong, thêm một dòng vào SETS, chạy lại.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "docs" / "samples"
# tên thư mục, tiêu đề, màu nền dải (trên → dưới), màu thẻ
SETS = [
    ("kawaii-doodle", "kawaii-doodle", ((255, 240, 228), (255, 226, 236)), (255, 252, 248)),
    ("gacha-chibi", "gacha-chibi", ((222, 236, 255), (236, 226, 255)), (255, 255, 255)),
    ("pastel-rpg", "pastel-rpg", ((44, 36, 66), (70, 46, 84)), (58, 50, 82)),
]
CARD, GAP, PAD = 168, 18, 28


def font(size: int):
    for f in ("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", "/System/Library/Fonts/Avenir Next.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def gradient(w: int, h: int, top, bottom) -> Image.Image:
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return g.resize((w, h))


def strip(folder: str, title: str, bg, card_col) -> Image.Image:
    pngs = sorted((SAMPLES / folder).glob("*.png"))
    n = len(pngs)
    head = 54
    w = PAD * 2 + n * CARD + (n - 1) * GAP
    h = head + CARD + 26 + PAD
    img = gradient(w, h, *bg).convert("RGBA")
    dark = sum(bg[0]) < 300
    ink = (250, 246, 255) if dark else (70, 52, 74)
    d = ImageDraw.Draw(img)
    d.text((PAD, 16), title, font=font(26), fill=ink)
    for i, p in enumerate(pngs):
        x, y = PAD + i * (CARD + GAP), head
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x + 2, y + 6, x + CARD + 2, y + CARD + 6), 26, fill=(0, 0, 0, 60 if dark else 28))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        ImageDraw.Draw(img).rounded_rectangle((x, y, x + CARD, y + CARD), 26, fill=card_col + (255,))
        im = Image.open(p).convert("RGBA")
        bbox = im.getbbox() or (0, 0, *im.size)
        im = im.crop(bbox)
        s = (CARD - 26) / max(im.size)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        img.alpha_composite(im, (x + (CARD - im.width) // 2, y + (CARD - im.height) // 2))
        label = p.stem.replace("-", " ")
        tw = d.textlength(label, font=font(15))
        ImageDraw.Draw(img).text((x + (CARD - tw) / 2, y + CARD + 6), label, font=font(15), fill=ink)
    return img.convert("RGB")


def main() -> int:
    strips = []
    for folder, title, bg, card in SETS:
        if not (SAMPLES / folder).is_dir():
            continue
        s = strip(folder, title, bg, card)
        s.save(SAMPLES / f"{folder}.png", optimize=True)
        strips.append(s)
        print(f"docs/samples/{folder}.png  {s.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
