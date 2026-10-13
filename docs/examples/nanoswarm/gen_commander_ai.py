#!/usr/bin/env python3
"""Commander art, AI lane (2026-10-02) — the 12 Commanders repainted by the render PC, then animated by the anim lane.

Bi picked the soft "corner creature" style (2026-09-30) and wants the Commanders drawn by the PC, not by code. Text-to-image
alone loses the designs (12 different blobs, props drift, plastic shine — rejected before), so this is IMAGE-TO-IMAGE:
the vector puppet from tools/artpipe/sumi (sumi/init/<id>.png — silhouette, colour, the held thing that says the job) is
repainted by animagine-xl at a few denoise strengths. Low = the design stays, the line + texture turn hand-drawn;
high = more of the model's own drawing. Bi picks one per Commander; the pick becomes the anchor of the anim lane
(sanne-kit/Tools/artpipe/README-anim.md, manifests in tools/artpipe/anims/).

On the render PC through the artpipe workflow, mode=script (needs COMFYUI_URL; writes into out/):
    anchor <out> [id ...] [--denoise 0.45,0.6,0.72] [--seed 8000]   → <out>/anchors/<id>__d<NN>.png (+ _raw.png)
    sheet  <out> <sheet.png>                                         → rows = Commanders, cols = vector + each strength
Locally (Mac, no GPU):
    pick   <out> id=NN ...                                           → tools/artpipe/anims/commanders/<id>/anchor.png
"""
import json, os, sys, time, uuid, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
INIT = HERE / "sumi/init"
ANCHORS = HERE / "anims/commanders"
HOST = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
TOKEN = os.environ.get("COMFYUI_TOKEN", "")
CKPT = "animagine-xl-4.0-opt.safetensors"

IDS = ["clamp", "spark", "hook", "shell", "vega", "mira", "kite", "bastion", "relay", "orrin", "nyx", "atlas"]

PREFIX = "masterpiece, best quality, very aesthetic, solo, no humans, full body, standing, front view, cute mascot character,"
# what the corner-creature style IS (sumi/sumibots.mjs header): said, never named after the reference game
STYLE = ("small round gumdrop shaped creature, no neck, tiny stubby nub arms, tiny feet, tiny black dot eyes set low and wide, "
         "tiny mouth, soft pink blush, pale cream tummy patch, soft flat pastel colours, very gentle soft shading, "
         "warm brown hand-drawn outline with slight wobble, soft crayon texture, cozy storybook illustration, matte, "
         "plain white background, centered")
NEGATIVE = ("glossy, shiny, plastic, vinyl toy, 3d render, clay, metallic reflections, specular highlights, realistic, photo, "
            "big anime eyes, sparkling eyes, humanoid, human, girl, boy, long legs, fingers, hands with fingers, "
            "thick black outline, dark, gloomy, lightning, fire, flames, magic effects, sparkles, motion lines, "
            "text, watermark, logo, frame, border, card, multiple views, character sheet, cropped, out of frame, "
            "busy background, gradient background, lowres, blurry, jpeg artifacts")

# what each one wears / holds — mirrors BOTS + ACC in sumi/sumibots.mjs (the held thing = the job at a glance)
SUBJECT = {
    "clamp":   "pale yellow little robot creature wearing a yellow miner hard hat with a lamp, holding a small pickaxe",
    "spark":   "coral pink little robot creature with a short antenna, red headband tied at the side, holding a small toy sword",
    "hook":    "beige little robot creature wearing an orange builder hard hat, holding a small hammer",
    "shell":   "mint green little robot creature with a green turtle shell on its back, hugging a pink heart",
    "vega":    "lime green little robot creature wearing a pointed green archer cap with a red feather, holding a tall spear",
    "mira":    "pink little robot creature with a short antenna, holding up a red horseshoe magnet",
    "kite":    "sky blue little robot creature with aviator goggles on its forehead and a red scarf flowing behind, red shoes",
    "bastion": "pale silver little robot creature wearing a round knight bucket helmet with a blue plume, holding a round blue shield with a pink heart",
    "relay":   "teal little robot creature wearing big headphones, hugging a green battery with a plus sign",
    "orrin":   "cream white little robot creature wearing a small golden crown, hugging a red toy drum",
    "nyx":     "lavender little robot creature in a soft hood with cat ears, holding a small heart wand",
    "atlas":   "big warm grey little robot creature wearing a viking helmet with two horns, wearing one big red boxing glove",
}


# ── ComfyUI ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def _req(path, data=None, headers=None):
    h = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(HOST + path, data=data, headers=h), timeout=600) as r:
        return r.read()


def upload(png: Path) -> str:
    """POST /upload/image (multipart) → the name LoadImage reads."""
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"cmdinit_{png.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png.read_bytes() + \
           f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n".encode()
    return json.loads(_req("/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={b}"}))["name"]


def graph(image_name, prompt, seed, denoise):
    """artpipe's icon_anime graph (checkpoint → prompts → sampler → decode) with the empty canvas swapped for the vector
    puppet — inlined so the script runs on the render PC without the kit checked out."""
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["1", 2]}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 6.5, "sampler_name": "euler_ancestral",
              "scheduler": "normal", "denoise": denoise, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
              "latent_image": ["11", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "cmd_raw"}},
    }
    g["8"] = {"class_type": "RMBG", "inputs": {"image": ["6", 0], "model": "RMBG-2.0", "sensitivity": 1.0,
              "process_res": 1024, "mask_blur": 0, "mask_offset": 0, "invert_output": False,
              "refine_foreground": True, "background": "Alpha"}}
    g["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "cmd_alpha"}}
    return g


def run(g):
    pid = json.loads(_req("/prompt", json.dumps({"prompt": g, "client_id": uuid.uuid4().hex}).encode(),
                          {"Content-Type": "application/json"}))["prompt_id"]
    while True:
        h = json.loads(_req(f"/history/{pid}"))
        if pid in h and h[pid].get("outputs"):
            break
        time.sleep(1.0)
    out = {}
    for node, o in h[pid]["outputs"].items():
        for im in o.get("images", []):
            q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"], "type": im["type"]})
            out[node] = _req(f"/view?{q}")
    return out["7"], out["9"]


# ── commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def anchor(out, ids, strengths, seed0):
    dst = out / "anchors"
    dst.mkdir(parents=True, exist_ok=True)
    for i, cid in enumerate(ids):
        name = upload(INIT / f"{cid}.png")
        prompt = f"{PREFIX} {SUBJECT[cid]}, {STYLE}"
        for d in strengths:
            tag = f"d{round(d * 100):02d}"
            if (dst / f"{cid}__{tag}.png").exists():
                continue
            t = time.time()
            raw, alpha = run(graph(name, prompt, seed0 + i * 10, d))
            (dst / f"{cid}__{tag}_raw.png").write_bytes(raw)
            (dst / f"{cid}__{tag}.png").write_bytes(alpha)
            print(cid, tag, f"{time.time() - t:.0f}s", flush=True)
    (out / "prompts.json").write_text(json.dumps({"prefix": PREFIX, "style": STYLE, "negative": NEGATIVE,
                                                  "subject": SUBJECT, "ckpt": CKPT, "seed0": seed0,
                                                  "denoise": strengths}, indent=1))


def sheet(out, dst, cell=300):
    files = sorted((out / "anchors").glob("*__d??.png"))
    tags = sorted({f.stem.split("__")[1] for f in files})
    ids = [c for c in IDS if any(f.stem.startswith(c + "__") for f in files)]
    head = 34
    page = Image.new("RGB", ((1 + len(tags)) * cell, head + len(ids) * cell), (255, 243, 227))
    d = ImageDraw.Draw(page)
    try:
        font = ImageFont.truetype(str(HERE / "fonts/Fredoka-VF.ttf"), 22)
    except OSError:
        font = ImageFont.load_default()
    for c, label in enumerate(["vector (khung)"] + [f"AI {t[1:]}%" for t in tags]):
        d.text((c * cell + 10, 6), label, fill=(90, 60, 50), font=font)
    for r, cid in enumerate(ids):
        cells = [INIT / f"{cid}.png"] + [out / "anchors" / f"{cid}__{t}.png" for t in tags]
        for c, f in enumerate(cells):
            if not f.exists():
                continue
            im = Image.open(f).convert("RGBA")
            bb = im.getbbox() or (0, 0, im.width, im.height)
            im = im.crop(bb)
            im.thumbnail((cell - 20, cell - 20), Image.LANCZOS)
            x, y = c * cell + (cell - im.width) // 2, head + r * cell + (cell - im.height) // 2
            page.paste(im, (x, y), im)
        d.text((6, head + r * cell + 4), cid, fill=(120, 90, 80), font=font)
    dst.parent.mkdir(parents=True, exist_ok=True)
    page.save(dst)
    print("sheet ->", dst)


# anim lane manifest per Commander (sanne-kit/Tools/artpipe/README-anim.md). Wan runs cfg=1: describe only what to see.
# Anchor is front view → every move is done on the spot, facing the viewer (the map mirrors it to face its walk).
# loop: true = first = last frame = the anchor, so a strike / cheer also lands back in the standing pose.
MANIFEST = """# Commander {cid} — gen_commander_ai.py pick (anchor = AI repaint {tag}, approved by Bi)
character: cmd-{cid}
anchor: {cid}/anchor.png
anchor_bg: "#FFFFFF"
style: "soft hand-drawn storybook cartoon, warm brown outline, flat soft pastel colours, gentle crayon texture"
defaults:
  frames: 33
  width: 512
  height: 512
  variants: 2
  seed: 3000
  cell: 256
  pad: 4
  count: 8
  upscaler: RealESRGAN_x4plus_anime_6B.pth
  upscale: 2
  sharpen: 60
animations:
  idle:
    prompt: "the little round creature stands in place and gently bobs up and down, its body squashing softly, it blinks once, stays on the same spot"
    loop: true
    fps: 8
  walk:
    prompt: "the little round creature waddles on the spot facing the viewer, body rocking left and right with tiny quick steps, stays on the same spot"
    loop: true
    fps: 12
  attack:
    prompt: "the little round creature swings the thing it holds forward in one quick strong strike, then settles back into its standing pose, stays on the same spot"
    frames: 25
    loop: true
    fps: 14
  cheer:
    prompt: "the little round creature hops happily once with both little arms raised, then lands back in its standing pose, stays on the same spot"
    frames: 25
    loop: true
    fps: 12
"""


def pick(out, picks):
    for p in picks:
        cid, tag = p.split("=")
        src = out / "anchors" / f"{cid}__d{int(tag):02d}.png"
        dst = ANCHORS / cid / "anchor.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(src).convert("RGBA")
        im.crop(im.getbbox()).save(dst)
        (ANCHORS / f"{cid}.yaml").write_text(MANIFEST.format(cid=cid, tag=f"d{int(tag):02d}"), encoding="utf-8")
        print(cid, "<-", src.name)


def _opt(args, key, default):
    if key in args:
        k = args.index(key); v = args[k + 1]; del args[k:k + 2]; return v
    return default


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a.pop(0)
    if cmd == "anchor":
        strengths = [float(x) for x in _opt(a, "--denoise", "0.45,0.6,0.72").split(",")]
        seed0 = int(_opt(a, "--seed", "8000"))
        anchor(Path(a[0]), a[1:] or IDS, strengths, seed0)
    elif cmd == "sheet":
        sheet(Path(a[0]), Path(a[1]))
    elif cmd == "pick":
        pick(Path(a[0]), a[1:])
    else:
        sys.exit(__doc__)
