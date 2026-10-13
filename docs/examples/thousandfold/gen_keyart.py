#!/usr/bin/env python3
"""Thousandfold — key art so sánh hướng art A/B/C (prompts.md). Chạy trên máy render qua làn script của artpipe:

    gh workflow run artpipe.yml -R tsan2711/sanne-kit -f mode=script -f project=docs/shared/thousandfold-art \
        -f script=gen_keyart.py -f script_args="out --variants 2"

Ghi out/<dir>__creature<v>.png (1024², nền trơn) + out/<dir>__scene<v>.png (1344x768); ghép bầy: compose_keyart.py. Graph tự chứa, không dùng graph icon của kit (icon cần tách nền, key art thì không).
"""
import json, os, sys, time, uuid, urllib.parse, urllib.request
from pathlib import Path

HOST = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
PREFER = ("sd_xl_base_1.0.safetensors", "animagine-xl-4.0-opt.safetensors")

# Lần 1 (run 38105835627): SDXL không vẽ được "bầy 2000 con nhỏ" từ prompt — ra vài khối khổng lồ / vệt sơn / không con
# nào, và không có robot. Nên tách: máy render vẽ (1) MỘT con trên nền trơn để tách nền, (2) cảnh ngã tư trống có robot;
# compose_keyart.py trên Mac rắc ~2000 con thành một khối chảy — đúng cách game vẽ bầy, và thử luôn cỡ 4–8 px.
SCENE = ("top-down isometric 3/4 view from about 50 degrees, small stylised city intersection, empty streets, parked "
         "cars, little shops, street trees, lamp posts, a giant three-storey police robot standing in the centre of the "
         "intersection, game key art, clean readable shapes, soft global illumination, high detail")
CREATURE = ("single cute game creature, full body, centered, front three-quarter view, simple bold readable silhouette, "
            "mobile game character sprite, clean shapes, no shadow, isolated on a flat solid {bg} background")
ROBOT = ("a giant cute police robot, three storeys tall, chunky toy-like proportions, blue and white panels, siren "
         "lights on its head, standing, full body, isometric 3/4 view from above, game key art, clean readable shapes, "
         "no shadow, isolated on a flat solid white background")
NEGATIVE = ("text, watermark, logo, ui, hud, signature, photo, photorealistic, blurry, lowres, jpeg artifacts, "
            "deformed, humans, people")
# slug: (con vật, nền tách, cảnh)
DIRS = {
    "A-slime": ("a tiny glossy candy-coloured slime droplet blob with two dot eyes, magenta jelly, wet specular "
                "highlight, jelly translucency", "white",
                "muted beige-grey city, desaturated buildings so a saturated swarm will pop"),
    # v2: chân + vệt chảy → ở 13 px chỉ còn viền. v3: khối đặc tròn, không chân, viền dày.
    "B-ink":   ("a tiny chubby round blob creature made of thick vivid neon orange paint, solid filled body, no legs, "
                "two big white eyes, one small paint splash on top, thick dark ink outline", "white",
                "colourful vivid city, saturated shop fronts and cars, painterly ink linework"),
    "C-fluff": ("a tiny round fluffy cream-coloured fur-ball critter with big shiny eyes, like a Ghibli soot sprite but "
                "warm-coloured, soft fur rim light", "dark navy blue",
                "muted blue-grey city in warm sunset light"),
}


def call(path, data=None):
    req = urllib.request.Request(HOST + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return r.read()


def checkpoint():
    info = json.loads(call("/object_info/CheckpointLoaderSimple"))
    have = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    for c in PREFER:
        if c in have:
            return c
    sys.exit(f"không có checkpoint SDXL nào trên máy render (có: {have}) — mở notebook với SDXL=True")


def graph(ckpt, prompt, seed, w, h):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 7.0, "sampler_name": "dpmpp_2m",
              "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0],
              "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "thousandfold"}},
    }


def run(g):
    pid = json.loads(call("/prompt", {"prompt": g, "client_id": uuid.uuid4().hex}))["prompt_id"]
    while True:
        h = json.loads(call(f"/history/{pid}"))
        if pid in h and h[pid].get("outputs"):
            im = h[pid]["outputs"]["7"]["images"][0]
            q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"], "type": im["type"]})
            return call(f"/view?{q}")
        if pid in h and h[pid].get("status", {}).get("status_str") == "error":
            sys.exit(f"ComfyUI báo lỗi: {h[pid]['status']}")
        time.sleep(1.0)


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    variants = int(sys.argv[sys.argv.index("--variants") + 1]) if "--variants" in sys.argv else 2
    out.mkdir(parents=True, exist_ok=True)
    ckpt = checkpoint()
    print("checkpoint:", ckpt, flush=True)
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else list(DIRS)
    for v in range(variants):
        (out / f"robot{v}.png").write_bytes(run(graph(ckpt, ROBOT, 7300 + v, 1024, 1024)))
        print("robot", v, flush=True)
    for slug, (creature, bg, scene) in DIRS.items():
        if slug not in only:
            continue
        for v in range(variants):
            seed = 7100 + v
            (out / f"{slug}__creature{v}.png").write_bytes(
                run(graph(ckpt, f"{creature}, {CREATURE.format(bg=bg)}", seed, 1024, 1024)))
            (out / f"{slug}__scene{v}.png").write_bytes(run(graph(ckpt, f"{scene}, {SCENE}", seed, 1344, 768)))
            print(slug, v, flush=True)
    (out / "README.txt").write_text(f"checkpoint={ckpt}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
