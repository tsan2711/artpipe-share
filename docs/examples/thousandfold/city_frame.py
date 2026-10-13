#!/usr/bin/env python3
"""Thousandfold — môi trường thử: thành phố isometric khối phẳng (kiểu Alto / Monument Valley) dựng bằng code, rồi cho bầy
'light' (style_frame.py, đã chốt) chảy dọc đường phố và tô màu lại chỗ nó đi qua.

    python3 city_frame.py <out_dir> [--seed 3] [--n 3500]
Ghi <out_dir>/city-colour.png (bản màu đầy đủ — game tự làm xám) + city-light.png (style frame).
"""
import math, random, sys
from pathlib import Path

from PIL import Image, ImageDraw

import style_frame as sf

W, H, SS = 1344, 768, 2           # vẽ ở 2x rồi thu nhỏ để mịn cạnh
TW, TH, HZ = 150, 75, 34           # ô iso (px ở 1x) và chiều cao một tầng — phóng to, thành phố tràn khung
N = 13                              # lưới N×N ô; đường phố ở hàng/cột giữa
ROAD = N // 2

# Bản màu phải ĐẬM: chỗ bầy tô lại chỉ đẹp khi khác hẳn bản xám (bản kem nhạt trông như vệt sương trắng).
BUILD = [(240, 110, 90), (250, 190, 70), (60, 190, 160), (130, 105, 230), (240, 120, 170), (90, 160, 230)]
GROUND, ROADC, LINE, PAVE = (110, 185, 115), (78, 82, 120), (250, 230, 160), (236, 196, 140)
TREE = [(60, 160, 90), (120, 200, 80)]


def iso(gx, gy, z=0.0):
    ox, oy = W * 0.5, H * 0.55 - (ROAD + 0.5) * TH   # ngã tư ở giữa khung
    return ((gx - gy) * TW / 2 + ox) * SS, ((gx + gy) * TH / 2 - z * HZ + oy) * SS


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def box(d, gx, gy, sx, sy, z, c, windows=False):
    """Khối hộp tại góc (gx,gy), cỡ sx×sy ô, cao z tầng: mặt trên sáng, mặt trái vừa, mặt phải tối."""
    a, b, cc, e = iso(gx, gy), iso(gx + sx, gy), iso(gx + sx, gy + sy), iso(gx, gy + sy)
    up = lambda p: (p[0], p[1] - z * HZ * SS)
    d.polygon([e, cc, up(cc), up(e)], fill=shade(c, 0.86))          # mặt trái (hướng +gy)
    d.polygon([b, cc, up(cc), up(b)], fill=shade(c, 0.70))          # mặt phải (hướng +gx)
    d.polygon([up(a), up(b), up(cc), up(e)], fill=shade(c, 1.06))   # mặt trên
    if windows and z >= 1.5:
        for f in range(1, int(z)):
            for k in range(1, int(sy * 4)):
                t = k / (sy * 4)
                x, y = e[0] + (cc[0] - e[0]) * t, e[1] + (cc[1] - e[1]) * t - (f + 0.35) * HZ * SS
                d.rectangle([x - 5 * SS, y - 8 * SS, x + 5 * SS, y + 8 * SS], fill=shade(c, 0.6))


def tree(d, gx, gy, rng):
    x, y = iso(gx + 0.5, gy + 0.5)
    c = TREE[rng.randrange(len(TREE))]
    t = 30 * SS
    d.rectangle([x - 4 * SS, y - t, x + 4 * SS, y], fill=(150, 120, 100))
    r = rng.uniform(22, 30) * SS
    d.ellipse([x - r, y - t - r * 1.6, x + r, y - t + r * 0.4], fill=c)
    d.ellipse([x - r * 0.9, y - t - r * 1.5, x + r * 0.2, y - t - r * 0.4], fill=shade(c, 1.12))


def city(seed):
    rng = random.Random(seed)
    img = Image.new("RGB", (W * SS, H * SS), GROUND)
    d = ImageDraw.Draw(img)
    for gx in range(N):                                  # nền: đường, vỉa hè
        for gy in range(N):
            road = gx == ROAD or gy == ROAD
            pave = abs(gx - ROAD) == 1 or abs(gy - ROAD) == 1
            c = ROADC if road else PAVE if pave else GROUND
            d.polygon([iso(gx, gy), iso(gx + 1, gy), iso(gx + 1, gy + 1), iso(gx, gy + 1)], fill=c)
    for k in range(N):                                   # vạch giữa đường
        if k != ROAD and k % 2 == 0:
            d.line([iso(ROAD + 0.5, k + 0.2), iso(ROAD + 0.5, k + 0.8)], fill=LINE, width=6 * SS)
            d.line([iso(k + 0.2, ROAD + 0.5), iso(k + 0.8, ROAD + 0.5)], fill=LINE, width=6 * SS)
    items = []
    for gx in range(N):
        for gy in range(N):
            if abs(gx - ROAD) <= 1 or abs(gy - ROAD) <= 1:
                if (abs(gx - ROAD) == 1) != (abs(gy - ROAD) == 1) and rng.random() < 0.35 and gx != ROAD and gy != ROAD:
                    items.append((gx + gy, "tree", gx, gy))
                elif (gx == ROAD) != (gy == ROAD) and rng.random() < 0.12:
                    items.append((gx + gy + 0.5, "car", gx, gy))
                continue
            if (gx + gy) % 2 == 0 or rng.random() < 0.3:
                h = rng.choice([1, 1.5, 2, 2, 2.5, 3])
                items.append((gx + gy + 1, "box", gx, gy, h, BUILD[rng.randrange(len(BUILD))]))
            elif rng.random() < 0.5:
                items.append((gx + gy, "tree", gx, gy))
    for it in sorted(items, key=lambda t: t[0]):       # vẽ xa → gần
        if it[1] == "box":
            _, _, gx, gy, h, c = it
            box(d, gx + 0.08, gy + 0.08, 0.84, 0.84, h, c, windows=True)
            if rng.random() < 0.4:
                box(d, gx + 0.3, gy + 0.3, 0.4, 0.4, h + 0.6, shade(c, 0.95))
        elif it[1] == "tree":
            tree(d, it[2], it[3], rng)
        else:
            gx, gy = it[2], it[3]
            along_x = gy == ROAD
            sx, sy = (0.55, 0.3) if along_x else (0.3, 0.55)
            box(d, gx + 0.22 + (0 if along_x else 0.05), gy + 0.22 + (0.05 if along_x else 0), sx, sy, 0.45,
                BUILD[rng.randrange(len(BUILD))])
    return img.resize((W, H), Image.LANCZOS)


def guide():
    """Đường bầy đi: vào từ mép dưới-trái theo đường phố, thẳng qua ngã tư, đầu bầy dừng 2 ô sau ngã tư —
    nửa phía trên-phải vẫn xám (trước/sau trong cùng một khung)."""
    s = lambda gx, gy: tuple(v / SS for v in iso(gx, gy))
    return [s(ROAD + 0.5, N + 2), s(ROAD + 0.5, ROAD - 2)]


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "out")
    out.mkdir(parents=True, exist_ok=True)
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 3
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 3500
    img = city(seed)
    img.save(out / "city-colour.png")
    for dusk in (False, True):
        f = out / ("city-light-dusk.png" if dusk else "city-light.png")
        sf.render(img, "light", n, 21, guide=guide(), simplify_scene=False, dusk=dusk).save(f)
        print(f)


if __name__ == "__main__":
    main()
