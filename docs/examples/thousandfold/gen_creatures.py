#!/usr/bin/env python3
"""Thousandfold — vẽ thử nhiều kiểu con cho hướng B (thế giới xám, bầy tô màu lại). Bi chê con mực v3 (xấu, dị),
nên giữ cơ chế màu, đổi con vật. Mỗi kiểu một ảnh nền trơn để xem riêng và để compose_keyart.py tách được.

    gh workflow run artpipe.yml -R tsan2711/sanne-kit -f mode=script -f game_repo=tsan2711/Seriously -f game_ref=main \
        -f project=docs/shared/thousandfold-art -f script=gen_creatures.py -f script_args="out --variants 3"
"""
import sys
from pathlib import Path

from gen_keyart import checkpoint, graph, run

STYLE = ("single cute mascot character, full body, centered, simple bold readable silhouette, soft rounded shapes, "
         "kawaii mobile game character, clean flat colours with soft shading, appealing friendly face, no shadow, "
         "isolated on a flat solid white background")
KINDS = {
    "wisp":    "a tiny glowing colour spirit, round soft body like a firefly light, short trailing tail of rainbow light",
    "drop":    "a tiny cute droplet of bright paint, teardrop shape, simple happy face, glossy",
    "crayon":  "a tiny cute crayon stub character, short stubby crayon body with a paper wrapper, little arms",
    "sprout":  "a tiny cute round seed creature with a small leaf sprout and one flower bud on its head",
    "brush":   "a tiny cute paintbrush-tip creature, fluffy bristle head dipped in bright paint, small round body",
    "chick":   "a tiny cute round baby bird chick, bright colourful feathers, very round body, small wings",
    "star":    "a tiny cute five-point star creature, soft puffy rounded star shape, sparkle",
    "jelly":   "a tiny cute gummy bear made of bright translucent candy",
}


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    variants = int(sys.argv[sys.argv.index("--variants") + 1]) if "--variants" in sys.argv else 3
    out.mkdir(parents=True, exist_ok=True)
    ckpt = checkpoint()
    print("checkpoint:", ckpt, flush=True)
    for slug, desc in KINDS.items():
        for v in range(variants):
            (out / f"{slug}__{v}.png").write_bytes(run(graph(ckpt, f"{desc}, {STYLE}", 7500 + v, 1024, 1024)))
            print(slug, v, flush=True)


if __name__ == "__main__":
    main()
