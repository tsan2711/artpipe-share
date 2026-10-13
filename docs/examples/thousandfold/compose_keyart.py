#!/usr/bin/env python3
"""Thousandfold — ghép key art so sánh A/B/C trên Mac từ ảnh gen_keyart.py vẽ (máy render chỉ vẽ 1 con + cảnh trống).

    python3 compose_keyart.py <thư mục ảnh tải về> [--count 2000] [--size 13]

Rắc ~count con thành một khối chảy từ góc dưới trái vào robot giữa cảnh, có nhánh trèo lên robot. Ghi
<dir>/<slug>__key<v>.png + <dir>/compare.png (3 hướng cạnh nhau, kèm bản thu nhỏ cỡ điện thoại để thử độ đọc).
Hướng B: cảnh xám hết, chỉ chỗ bầy đã đi qua mới có màu (đúng ý "tô lại thế giới").
"""
import colorsys, math, os, random, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

KIT = Path(os.environ.get("ARTPIPE_KIT", Path.home() / "Documents/GitHub/Unity/sanne-kit/Tools/artpipe"))
sys.path.insert(0, str(KIT))
import matte  # noqa: E402  (tách nền phẳng, không model)

# slug: các độ xoay hue (0 = màu gốc của con vẽ ra) — một bầy nhiều màu kẹo / mực / lông
TINTS = {"A-slime": [0.0, 0.33, 0.52], "B-ink": [0.0, 0.72, 0.45], "C-fluff": [0.0, 0.02, -0.03]}
VALUE = {"C-fluff": [1.0, 0.85, 0.7]}  # lông: đổi độ sáng (kem / đào / nâu) thay vì đổi màu


def sprite(path):
    rgba = matte.cutout(Image.open(path).convert("RGB"))
    return rgba.crop(rgba.getbbox())


def shift(im, dh, dv=1.0):
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
    hsv = np.asarray(im.convert("RGB").convert("HSV")).astype(np.float32) / 255
    hsv[..., 0] = (hsv[..., 0] + dh) % 1.0
    hsv[..., 2] = np.clip(hsv[..., 2] * dv, 0, 1)
    rgb = np.asarray(Image.fromarray((hsv * 255).astype(np.uint8), "HSV").convert("RGB")).astype(np.float32) / 255
    return Image.fromarray((np.dstack([rgb, a[..., 3:]]) * 255).astype(np.uint8), "RGBA")


def swarm_points(w, h, n, rng):
    """Khối chảy: dòng chính dọc đường cong từ góc dưới trái tới robot (giữa), loe rộng ở đuôi; 15% trèo lên robot."""
    pts = []
    cx, cy = w * 0.5, h * 0.55
    for _ in range(int(n * 0.85)):
        t = rng.random() ** 0.7                       # dày về phía đầu bầy
        x = (1 - t) * (-0.05 * w) + t * cx
        y = (1 - t) * (1.05 * h) + t * cy - math.sin(t * math.pi) * h * 0.08
        spread = h * (0.04 + 0.12 * (1 - t))   # v3: hẹp hơn để đọc thành một khối
        a = rng.gauss(0, 1) * spread
        pts.append((x + a * 0.6, y + a * 0.8 + rng.gauss(0, spread * 0.3)))
    for _ in range(n - len(pts)):                     # bám/trèo robot
        pts.append((cx + rng.gauss(0, w * 0.03), cy - abs(rng.gauss(0, h * 0.14))))
    return pts


def compose(scene_path, creature_path, slug, count, size, seed, robot_path=None):
    rng = random.Random(seed)
    scene = Image.open(scene_path).convert("RGB")
    w, h = scene.size
    if robot_path and robot_path.exists():  # robot vẽ riêng (SDXL bỏ qua robot trong prompt cảnh), đứng giữa ngã tư
        r = sprite(robot_path)
        r = r.resize((round(r.width * h * 0.5 / r.height), round(h * 0.5)), Image.LANCZOS)
        scene.paste(r, (int(w * 0.5 - r.width / 2), int(h * 0.6 - r.height)), r)
    base = sprite(creature_path)
    s = size / base.height
    base = base.resize((max(1, round(base.width * s)), size), Image.LANCZOS)
    vals = VALUE.get(slug, [1.0])
    kinds = [shift(base, dh, vals[i % len(vals)]) for i, dh in enumerate(TINTS[slug])]
    pts = sorted(swarm_points(w, h, count, rng), key=lambda p: p[1])

    shadow = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(shadow)
    for x, y in pts:
        sd.ellipse([x - size * 0.45, y + size * 0.3, x + size * 0.45, y + size * 0.55], fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(2))

    if slug == "B-ink":  # xám hết, chỉ vệt bầy đi qua có màu
        trail = Image.new("L", (w, h), 0)
        td = ImageDraw.Draw(trail)
        for x, y in pts:
            r = size * 2.2
            td.ellipse([x - r, y - r, x + r, y + r], fill=255)
        trail = trail.filter(ImageFilter.GaussianBlur(size * 0.8))
        grey = ImageOps.grayscale(scene).convert("RGB")
        scene = Image.composite(scene, grey, trail)

    out = scene.convert("RGBA")
    out = Image.composite(Image.new("RGBA", (w, h), (0, 0, 0, 255)), out, shadow.point(lambda v: v * 0.6))
    for x, y in pts:
        k = kinds[rng.randrange(len(kinds))]
        if rng.random() < 0.5:
            k = ImageOps.mirror(k)
        out.alpha_composite(k, (int(x - k.width / 2), int(y - k.height)))
    return out.convert("RGB")


def main():
    d = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "out")
    arg = lambda k, dft: type(dft)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else dft
    count, size = arg("--count", 2000), arg("--size", 14)
    rows = []
    for slug in TINTS:
        keys = []
        for v in range(4):
            sc, cr = d / f"{slug}__scene{v}.png", d / f"{slug}__creature{v}.png"
            if not (sc.exists() and cr.exists()):
                continue
            try:
                robots = sorted(d.glob("robot*.png"))
                im = compose(sc, cr, slug, count, size, 100 + v, robots[v % len(robots)] if robots else None)
            except matte.MatteError as e:
                print(f"{slug} v{v}: tách nền hỏng ({e}) — bỏ qua", flush=True)
                continue
            im.save(d / f"{slug}__key{v}.png")
            keys.append(im)
            print(d / f"{slug}__key{v}.png", flush=True)
        if keys:
            rows.append(keys)
    if not rows:
        sys.exit("không ghép được ảnh nào")
    cw, ch = 672, 384
    cols = max(len(r) for r in rows)
    sheet = Image.new("RGB", (cols * cw + 240, len(rows) * ch), "white")
    for i, r in enumerate(rows):
        for j, im in enumerate(r):
            sheet.paste(im.resize((cw, ch), Image.LANCZOS), (j * cw, i * ch))
        # bản cỡ điện thoại (rộng 240 px ≈ một ô thumbnail feed) để xem bầy còn đọc được không
        sheet.paste(r[0].resize((240, 137), Image.LANCZOS), (cols * cw, i * ch))
    sheet.save(d / "compare.png")
    print(d / "compare.png")


if __name__ == "__main__":
    main()
