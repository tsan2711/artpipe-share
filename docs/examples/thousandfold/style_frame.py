#!/usr/bin/env python3
"""Thousandfold — style frame hướng B kiểu trừu tượng (Bi 2026-10-11: không con vật, không mặt mũi, đẹp kiểu Gris/Ori).

Bầy = hàng nghìn hạt chảy theo một trường dòng (flow field), vẽ bằng code chứ không bằng AI — đúng cách game sẽ render
(hạt GPU), và không mang "mùi AI". Cảnh nền (ảnh AI) bị làm xám + giản lược thành mảng; chỗ bầy đi qua màu loang lại
như màu nước.

    python3 style_frame.py <scene.png> <out_dir> [--n 3000]
Ghi <out_dir>/frame-{petal,light,ink}.png
"""
import math, random, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

PALETTE = [(255, 107, 90), (255, 201, 60), (63, 217, 165), (142, 107, 255), (255, 150, 200)]


def simplify(img):
    """Ảnh AI → mảng phẳng: lọc trung vị + giảm bậc màu, bớt chi tiết vụn (chỗ lộ 'mùi AI' nhất)."""
    im = img.filter(ImageFilter.MedianFilter(7)).filter(ImageFilter.MedianFilter(5))
    return ImageOps.posterize(im, 4).filter(ImageFilter.SMOOTH_MORE)


def noise(w, h, scale, rng):
    small = Image.fromarray((np.array([[rng.random() for _ in range(w // scale + 2)]
                                       for _ in range(h // scale + 2)]) * 255).astype(np.uint8))
    return np.asarray(small.resize((w, h), Image.BICUBIC)).astype(np.float32) / 255


def along(guide, t):
    """Điểm + pháp tuyến tại tỉ lệ độ dài t (0..1) trên đường gấp khúc guide."""
    seg = [math.dist(guide[i], guide[i + 1]) for i in range(len(guide) - 1)]
    L, acc = sum(seg) * t, 0.0
    for i, l in enumerate(seg):
        if acc + l >= L or i == len(seg) - 1:
            u = (L - acc) / l if l else 0
            (x0, y0), (x1, y1) = guide[i], guide[i + 1]
            nx, ny = -(y1 - y0) / l, (x1 - x0) / l
            return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, nx, ny
        acc += l


def flow_paths(w, h, n, rng, guide=None):
    """Dòng chính: vào từ góc dưới trái, uốn qua giữa, toả ra phía trên phải; mỗi hạt lệch theo nhiễu.
    Có guide (đường phố) thì chảy dọc guide, bề ngang hẹp dần về phía đầu bầy."""
    if guide:
        paths = []
        for _ in range(n):
            lane, t0 = rng.gauss(0, 1), rng.random() ** 0.8
            t0 *= 1 - 0.12 * abs(rng.gauss(0, 1)) * (abs(lane) + 0.3)  # đầu bầy tròn, không cắt thẳng
            pts = []
            for k in range(rng.randint(3, 9)):
                t = min(1.0, t0 + k * 0.005)
                x, y, nx, ny = along(guide, t)
                off = lane * h * (0.05 - 0.02 * t) + math.sin(t * 40 + lane * 3) * 4
                pts.append((x + nx * off, y + ny * off))
            paths.append((pts, 1 - t0))
        return paths
    paths = []
    for _ in range(n):
        lane = rng.gauss(0, 1)
        t0 = rng.random()
        pts = []
        for k in range(rng.randint(3, 9)):
            t = min(1.0, t0 + k * 0.006)
            x = w * (-0.05 + 1.0 * t) + math.sin(t * 7 + lane) * w * 0.03
            y = h * (1.02 - 0.75 * t) - math.sin(t * math.pi) * h * 0.18 + lane * h * (0.035 + 0.06 * t)
            pts.append((x, y))
        paths.append((pts, t0))
    return paths


def render(scene, kind, n, seed, guide=None, simplify_scene=True, dusk=False):
    rng = random.Random(seed)
    w, h = scene.size
    flat = simplify(scene) if simplify_scene else scene
    grey = ImageOps.grayscale(flat)
    grey = (ImageOps.autocontrast(grey, cutoff=2).point(lambda v: 70 + v * 0.55) if simplify_scene
            else grey.point(lambda v: (18 + v * 0.42) if dusk else (40 + v * 0.8))).convert("RGB")  # cảnh code: xám giữ độ sáng gần bản màu
    paths = flow_paths(w, h, n, rng, guide)

    # vệt màu nước: mặt nạ từ đường đi của bầy, mép loang theo nhiễu
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    for pts, t0 in paths:
        md.line(pts, fill=255, width=int(h * (0.025 + 0.05 * (1 - t0)) * (3 if guide else 1)))  # có guide: vệt rộng
    mask = mask.filter(ImageFilter.GaussianBlur(22))
    m = np.asarray(mask).astype(np.float32) / 255
    m = np.clip((m + (noise(w, h, 40, rng) - 0.5) * 0.6 - 0.25) * 2.2, 0, 1)
    colour = flat if not simplify_scene else ImageOps.autocontrast(flat, cutoff=1)  # cảnh vẽ bằng code: giữ màu gốc
    base = Image.composite(colour, grey, Image.fromarray((m * 255).astype(np.uint8)))

    glow = Image.new("RGB", (w, h), 0)
    top = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd, td = ImageDraw.Draw(glow), ImageDraw.Draw(top)
    for pts, t0 in paths:
        c = PALETTE[rng.randrange(len(PALETTE))]
        x, y = pts[-1]
        if kind == "light":                       # đốm sáng, đuôi mảnh
            td.line(pts, fill=c + (110,), width=2)
            r = rng.uniform(1.5, 3.5)
            td.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 235, 255))
            gd.ellipse([x - r * 4, y - r * 4, x + r * 4, y + r * 4], fill=c)
        elif kind == "petal":                     # cánh hoa: elip xoay theo hướng chảy
            (x0, y0) = pts[-2] if len(pts) > 1 else (x - 1, y)
            a = math.atan2(y - y0, x - x0) + rng.uniform(-0.8, 0.8)
            L, W = rng.uniform(5, 10), rng.uniform(2.5, 4.5)
            poly = [(x + math.cos(a) * L * math.cos(s) - math.sin(a) * W * math.sin(s),
                     y + math.sin(a) * L * math.cos(s) + math.cos(a) * W * math.sin(s))
                    for s in np.linspace(0, 2 * math.pi, 12)]
            td.polygon(poly, fill=c + (235,))
            gd.ellipse([x - 8, y - 8, x + 8, y + 8], fill=tuple(v // 2 for v in c))
        else:                                     # mực: nét cọ dày thon dần
            for i in range(len(pts) - 1):
                td.line([pts[i], pts[i + 1]], fill=c + (int(80 + 170 * i / len(pts)),),
                        width=max(1, int(1 + 5 * i / len(pts))))
            gd.line(pts, fill=tuple(v // 2 for v in c), width=8)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    out = ImageChops.screen(base, glow)
    out = out.convert("RGBA")
    out.alpha_composite(top)
    return out.convert("RGB")


def main():
    scene = Image.open(sys.argv[1]).convert("RGB")
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 3000
    for i, kind in enumerate(("petal", "light", "ink")):
        render(scene, kind, n, 11 + i).save(out / f"frame-{kind}.png")
        print(out / f"frame-{kind}.png")


if __name__ == "__main__":
    main()
