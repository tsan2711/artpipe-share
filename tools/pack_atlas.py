#!/usr/bin/env python3
"""Ghép một thư mục PNG thành một sprite sheet (atlas) dạng lưới + JSON toạ độ.

    python3 tools/pack_atlas.py out/<mẻ>/best                    # → out/<mẻ>/best/../atlas.png + atlas.json
    python3 tools/pack_atlas.py out/<mẻ>/best --cell 128 --cols 8 --out my_atlas

JSON theo dạng "hash" của TexturePacker ({"frames": {"<tên>.png": {"frame": {x,y,w,h}}}}) —
Phaser, PixiJS, Cocos, Godot plugin đọc thẳng được. Unity: kéo atlas.png vào, Sprite Mode =
Multiple, Sprite Editor → Slice → Grid By Cell Size: Pixel Size = cỡ ô, Offset = đệm,
Padding = 2×đệm (lệnh in ra đủ ba số ở cuối).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--cell", type=int, default=128, help="cỡ mỗi ô (px)")
    ap.add_argument("--cols", type=int, default=0, help="số cột (0 = tự chọn cho gần vuông)")
    ap.add_argument("--pad", type=int, default=2, help="khoảng trống quanh mỗi ô, chống lem khi lọc ảnh")
    ap.add_argument("--out", type=Path, default=None, help="tên file không đuôi (mặc định <folder>/../atlas)")
    args = ap.parse_args()

    pngs = sorted(args.folder.glob("*.png"))
    if not pngs:
        print(f"không có PNG nào trong {args.folder}")
        return 2
    cols = args.cols or math.ceil(math.sqrt(len(pngs)))
    rows = math.ceil(len(pngs) / cols)
    step = args.cell + 2 * args.pad
    sheet = Image.new("RGBA", (cols * step, rows * step), (0, 0, 0, 0))
    frames = {}
    for i, p in enumerate(pngs):
        img = Image.open(p).convert("RGBA").resize((args.cell, args.cell), Image.LANCZOS)
        x = (i % cols) * step + args.pad
        y = (i // cols) * step + args.pad
        sheet.paste(img, (x, y))
        frames[p.name] = {"frame": {"x": x, "y": y, "w": args.cell, "h": args.cell},
                          "rotated": False, "trimmed": False,
                          "spriteSourceSize": {"x": 0, "y": 0, "w": args.cell, "h": args.cell},
                          "sourceSize": {"w": args.cell, "h": args.cell}}
    out = args.out or args.folder.parent / "atlas"
    sheet.save(out.with_suffix(".png"))
    out.with_suffix(".json").write_text(json.dumps({
        "frames": frames,
        "meta": {"image": out.with_suffix(".png").name, "format": "RGBA8888",
                 "size": {"w": sheet.width, "h": sheet.height}, "scale": "1",
                 "app": "artpipe-share/tools/pack_atlas.py"},
    }, indent=1), "utf-8")
    print(f"atlas {len(pngs)} sprite · lưới {cols}×{rows} → {out.with_suffix('.png')}\n"
          f"  Unity Slice Grid By Cell Size: Pixel Size {args.cell} · Offset {args.pad} · Padding {2 * args.pad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
