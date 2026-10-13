"""Nhân vật 2D -> animation frame-by-frame, qua ComfyUI + Wan 2.2 I2V.

    python3 tools/artpipe/anim.py --manifest path/hero-anim.yaml --out out/anim generate
    python3 tools/artpipe/anim.py --manifest path/hero-anim.yaml --out out/anim --only walk generate
    python3 tools/artpipe/anim.py --manifest path/hero-anim.yaml --out out/anim post   # không GPU

## Luồng

    anchor.png (nhân vật đã duyệt)  ──►  [máy render] Wan 2.2 I2V 14B  ──►  video N frame
                                          └─ BiRefNet tách nền trong cùng graph
                                    ──►  tải frame RGBA về  ──►  anim_post (hậu kỳ CẢ chuỗi)
                                    ──►  <anim>_sheet.png + <anim>.json + preview.gif

Qwen-Image-Edit giữ DANH TÍNH (tạo anchor/keyframe tư thế — bước ngoài file này), Wan giữ
CHUYỂN ĐỘNG: mọi frame được sinh chung trong một lần và nhìn lẫn nhau, nên không có kiểu
"mỗi frame một con khác" của lối sinh từng ảnh độc lập (bản harvester 2026-09-22).

Nền tảng: pipeline MIT của mor-o/comfyui-2d-character-pipeline (W2 + W3), chỉnh cho card
16GB: bản GGUF Q4_K_M thay Q5_K_M, và KHÔNG dùng node VRAMUnloadModel của họ — node đó móc
vào call stack nội bộ của ComfyUI (vỡ khi ComfyUI đổi `execution.execute`), còn card 16GB +
64GB RAM thì cơ chế offload sẵn có của ComfyUI tự đẩy expert high-noise sang RAM trước khi
nạp expert low-noise.

## Vòng lặp

`loop: true` dùng graph `anim_wan22_loop.json`: frame đầu và frame cuối đều ép bằng anchor,
nên clip tự khép. `anim_post` bỏ frame cuối (trùng frame đầu) để khi phát lặp không có
nhịp đứng hình.

## Hai lệnh

`generate` tốn GPU. `post` chỉ chạy lại hậu kỳ trên frame đã tải về — đổi cell/fps/count/
colors thì dùng `post`, không bao giờ render lại (cùng triết lý với `run.py ingest`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import anim_post  # noqa: E402
import gen  # noqa: E402
import mesh  # noqa: E402  (ComfyMesh = client HTTP chung: upload, /prompt, /history, /view)

RED, GREEN, YELLOW, DIM, RESET = mesh.RED, mesh.GREEN, mesh.YELLOW, mesh.DIM, mesh.RESET
HERE = Path(__file__).parent

#: Bản cho card 16GB (RTX 5060 Ti). Mỗi expert Q4_K_M 9.66GB; hai expert không cùng nằm
#: trong VRAM — ComfyUI offload expert này sang RAM trước khi nạp expert kia.
#: Có 24GB+ thì đổi sang Q5_K_M trong manifest (`models:`), không sửa ở đây.
DEFAULT_MODELS = {
    "high": "wan2.2_i2v_A14b_high_noise_lightx2v_4step-Q4_K_M.gguf",
    "low": "wan2.2_i2v_A14b_low_noise_lightx2v_4step-Q4_K_M.gguf",
    "text_encoder": "umt5-xxl-encoder-Q5_K_M.gguf",
    "vae": "wan_2.1_vae.safetensors",
    "rmbg": "BiRefNet_toonout",
}

DEFAULTS = {
    "frames": 33,        # Wan: 4n+1. 33 frame @16fps = 2 giây
    "size": 512,         # canvas sinh vuông; `width`/`height` ghi đè (vd 480x832 cho nhân vật
                         # đứng — gần gấp đôi pixel trên người). Wan cần bội số 16
    "variants": 2,       # số seed mỗi animation
    "seed": 1000,
    "loop": False,
    # hậu kỳ (anim_post)
    "cell": 128, "pad": 4, "fps": 10, "count": 8, "step": 1,
    "trim_start": 0, "trim_end": 0, "colors": 0, "alpha_threshold": 0,
    "fill": 0.8,             # nhân vật đứng cao bao nhiêu phần ô (chừa chỗ cho tay/hiệu ứng)
    "hold_extreme": 0,       # >1: giữ frame đỉnh động tác N nhịp (đòn đánh có lực)
    "vfx_key": "",           # "black": nhân vật + hiệu ứng phát sáng trên nền đen (alpha nhân
                             #   vật từ BiRefNet, hiệu ứng từ độ sáng); "luma": CHỈ hiệu ứng, không
                             #   nhân vật — alpha hoàn toàn theo độ sáng (lửa, sét, nổ…)
    "framing": "rest",       # "rest": khung chung theo tư thế đứng; "union": vừa khít clip (VFX)
    "upscaler": "",          # model upscale trên máy render (vd RealESRGAN_x4plus_anime_6B.pth)
    "upscale": 2,            # hệ số phóng THỰC sau upscaler (x4 rồi thu về còn x2)
    "sharpen": 0,            # unsharp mask sau khi thu về ô, % (0 = tắt; 60-120 hợp anime)
}

#: Nối sau prompt chuyển động của mọi animation. Ba điều Wan hay tự ý làm và sprite thì cấm:
#: đẩy camera, cho nhân vật đi ra khỏi khung, và vẽ thêm nền.
MOTION_SUFFIX = ("fixed static camera, full body always visible in frame, the character "
                 "stays centered in place")

DEFAULT_NEGATIVE = (
    "camera movement, camera pan, zoom in, zoom out, camera shake, scene change, "
    "background scenery, ground shadow, cast shadow, floor, extra characters, duplicate "
    "character, text, watermark, logo, blurry, motion blur, distorted body, extra limbs, "
    "missing limbs, deformed hands, melting, morphing, flicker, color shift, "
    "photorealistic, 3d render")

GRAPHS = {False: "anim_wan22_i2v.json", True: "anim_wan22_loop.json"}
REQUIRED = ("{{IMAGE}}", "{{PROMPT}}", "{{SEED}}", "{{LENGTH}}",
            "{{PREFIX_RAW}}", "{{PREFIX_RGBA}}")


class AnimError(RuntimeError):
    pass


class ComfyAnim(mesh.ComfyMesh):
    """Client HTTP của làn mesh, với hợp đồng graph của làn anim."""

    def _patch(self, values: dict) -> dict:
        graph, found = gen.ComfyUI._substitute(self.graph, values)
        missing = [s for s in REQUIRED if s not in found]
        if missing:
            raise AnimError(f"{self.workflow_path.name} thiếu {', '.join(missing)}")
        stray = sorted({v for _, v in gen._walk_strings(graph) if v.startswith("{{")})
        if stray:
            raise AnimError(f"còn chuỗi thay thế lạ trong graph: {stray}")
        return graph

    @staticmethod
    def images_of(entry: dict, graph: dict, prefix: str) -> list[dict]:
        """Ảnh của đúng node SaveImage mang `prefix`, theo thứ tự frame."""
        nids = [nid for nid, n in graph.items() if n.get("class_type") == "SaveImage"
                and n["inputs"].get("filename_prefix") == prefix]
        imgs = [img for nid in nids
                for img in entry.get("outputs", {}).get(nid, {}).get("images", [])]
        return sorted(imgs, key=lambda i: i["filename"])

    def fetch_image(self, img: dict) -> bytes:
        sub = img.get("subfolder", "")
        return self.fetch(f"{sub}/{img['filename']}" if sub else img["filename"])


# -- manifest ----------------------------------------------------------------------------

def load_manifest(path: Path) -> dict:
    m = yaml.safe_load(path.read_text("utf-8")) or {}
    for k in ("character", "animations"):
        if not m.get(k):
            raise AnimError(f"{path.name}: thiếu khoá `{k}`")
    def has_anchor(d: dict) -> bool:
        return bool(d.get("anchor") or (d.get("anchor_gen") or {}).get("prompt"))
    m["_dir"] = path.parent
    m["models"] = {**DEFAULT_MODELS, **(m.get("models") or {})}
    base = {**DEFAULTS, **(m.get("defaults") or {})}
    anims = {}
    for name, a in m["animations"].items():
        a = {**base, **(a or {})}
        if not a.get("prompt"):
            raise AnimError(f"animation `{name}` thiếu prompt")
        if (int(a["frames"]) - 1) % 4:
            raise AnimError(f"animation `{name}`: frames={a['frames']} sai luật 4n+1 của "
                            f"Wan (hợp lệ: 17, 25, 33, 49, 81)")
        a["width"] = int(a.get("width") or a["size"])
        a["height"] = int(a.get("height") or a["size"])
        if a["width"] % 16 or a["height"] % 16:
            raise AnimError(f"animation `{name}`: {a['width']}x{a['height']} phải là bội số 16")
        a["bg"] = a.get("bg") or ("#000000" if a.get("vfx_key") in ("black", "luma")
                                  else m.get("anchor_bg", "#FFFFFF"))
        if not has_anchor(a) and not has_anchor(m):
            raise AnimError(f"animation `{name}`: không có anchor — khai `anchor`/`anchor_gen` "
                            f"ở đầu manifest hoặc trong chính animation")
        anims[name] = a
    m["animations"] = anims
    return m


def _anchor_alpha(im: Image.Image) -> Image.Image:
    """Alpha của anchor: dùng kênh alpha nếu có thật, không thì tách nền phẳng dính mép.

    Anchor sinh bằng anchor_gen là ảnh NỀN TRẮNG LIỀN, không alpha. Muốn đặt nó lên nền
    khác (nền đen cho clip hiệu ứng phát sáng) thì phải bỏ được nền trắng đó — flood fill
    từ 4 góc với ngưỡng màu, nên phần trắng BÊN TRONG nhân vật (áo sơ mi) không bị ăn.
    """
    if im.getextrema()[3][0] < 255:
        return im.getchannel("A")
    rgb = im.convert("RGB")
    marker = (1, 254, 3)                      # màu gần như không bao giờ có trong tranh
    for xy in ((0, 0), (rgb.width - 1, 0), (0, rgb.height - 1), (rgb.width - 1, rgb.height - 1)):
        if rgb.getpixel(xy) != marker:
            ImageDraw.floodfill(rgb, xy, marker, thresh=24)
    a = np.where((np.asarray(rgb) == marker).all(axis=2), 0, 255).astype(np.uint8)
    return Image.fromarray(a, "L")


def prepare_anchor(path: Path, width: int, height: int, bg: str) -> Image.Image:
    """Anchor -> khung `width`x`height`, nền đặc màu `bg`, nhân vật cắt sát rồi căn giữa.

    Bắt buộc nền đặc: LoadImage của ComfyUI bỏ kênh alpha, và RGB dưới vùng trong suốt là
    rác tuỳ phần mềm xuất — Wan sẽ coi rác đó là cảnh nền và "diễn" luôn nó. Cắt sát trước
    khi đặt vào khung: anchor sinh ra có lề rộng, để nguyên thì khung dọc 480x832 cũng không
    thêm được pixel nào lên người nhân vật.
    """
    if path.read_bytes()[:40].startswith(b"version https://git-lfs"):
        raise AnimError(f"{path.name} là file con trỏ Git LFS, chưa phải ảnh — chạy "
                        f"`git lfs pull` (runner: checkout cần lfs: true)")
    im = Image.open(path).convert("RGBA")
    im.putalpha(_anchor_alpha(im))
    box = im.getchannel("A").getbbox()
    if box:
        im = im.crop(box)
    scale = min(width * 0.9 / im.width, height * 0.9 / im.height)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                   Image.LANCZOS)
    canvas = Image.new("RGBA", (width, height), bg)
    canvas.alpha_composite(im, ((width - im.width) // 2, (height - im.height) // 2))
    return canvas.convert("RGB")


def ensure_anchor(m: dict, dst: Path, host: str | None) -> Path:
    """Ảnh anchor: file có sẵn thì dùng; không thì sinh bằng `anchor_gen` trên cùng máy render.

    Ảnh sinh ra lưu ở out/<character>/anchor.png và được DÙNG LẠI ở lần chạy sau — đổi
    anchor giữa chừng thì các animation của cùng một nhân vật không còn khớp nhau. Muốn
    sinh lại: xoá file đó. Chọn được anchor ưng ý thì commit nó cạnh manifest và khai
    `anchor:` — từ đó làn này không bao giờ vẽ lại nhân vật nữa.

    `m` là manifest (anchor chung của nhân vật) hoặc một animation có anchor riêng (VFX:
    mỗi hiệu ứng một ảnh khởi đầu). `dst` là chỗ lưu ảnh sinh ra.
    """
    if m.get("anchor"):
        src = (m["_dir"] / m["anchor"]).resolve()
        if src.exists():
            return src
        if not m.get("anchor_gen"):
            raise AnimError(f"không thấy anchor: {src}")
    if dst.exists():
        print(f"{DIM}dùng lại anchor đã sinh: {dst}{RESET}")
        return dst
    g = m["anchor_gen"]
    c = gen.ComfyUI(model=g.get("checkpoint", "animagine-xl-4.0-opt.safetensors"), host=host,
                    workflow=HERE / "workflows" / g.get("workflow", "icon_anime.json"),
                    size=int(g.get("size", 1024)), negative=g.get("negative", ""))
    print(f"sinh anchor {DIM}{c.model} seed={g.get('seed', 1)}{RESET}", flush=True)
    r = c.generate(g["prompt"].strip(), seed=int(g.get("seed", 1)), timeout=900)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(r.image)
    (dst.parent / "anchor.json").write_text(json.dumps(
        {"prompt": r.prompt_full, "negative": g.get("negative", ""), "seed": r.seed,
         "checkpoint": c.model, "graph": c.workflow_path.name}, indent=2, ensure_ascii=False),
        "utf-8")
    print(f"  {GREEN}✓{RESET} anchor -> {dst}")
    return dst


def _is_dark(hex_color: str) -> bool:
    r, g, b = (int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b < 64


def prompt_for(m: dict, a: dict) -> tuple[str, str]:
    bg = "plain solid black background" if _is_dark(a["bg"]) else "plain flat white background"
    parts = [a["prompt"].strip().rstrip("."), m.get("style", "").strip().rstrip("."),
             m.get("motion_suffix", MOTION_SUFFIX), bg]
    neg = ", ".join(x for x in (m.get("negative", ""), DEFAULT_NEGATIVE) if x)
    return ". ".join(p for p in parts if p) + ".", neg


# -- generate ----------------------------------------------------------------------------

def variant_dir(out: Path, m: dict, name: str, seed: int) -> Path:
    return out / m["character"] / name / f"s{seed}"


def add_upscale(graph: dict, model: str, net: float) -> dict:
    """Chèn upscaler ngay sau VAEDecode: mọi node đang đọc ảnh decode chuyển sang đọc ảnh
    đã phóng. Frame raw lẫn RGBA đều nét hơn, BiRefNet tách nền trên ảnh nét.

    Vì sao cần: Wan sinh ở ~480p qua VAE video + distill 4 bước + GGUF Q4 — nét vẽ mảnh lại
    và nhoè (so trên cùng vùng mặt với anchor 1024px, 2026-09-23). Upscaler anime (ESRGAN)
    vẽ lại nét viền sắc, mỗi frame độc lập nên không cần hiểu chuyển động.

    Chèn bằng code thay vì nhân đôi file graph: bật/tắt là một khoá trong manifest, không
    phải bốn file JSON phải giữ đồng bộ tay.
    """
    import copy
    g = copy.deepcopy(graph)
    dec = next(nid for nid, n in g.items() if n.get("class_type") == "VAEDecode")
    native = 2 if ("x2" in model.lower() or "2x" in model.lower()) else 4
    for n in g.values():
        for k, v in n.get("inputs", {}).items():
            if v == [dec, 0]:
                n["inputs"][k] = ["up_scale", 0]
    g["up_model"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": model},
                     "_meta": {"title": "Upscaler (anime ESRGAN)"}}
    g["up_run"] = {"class_type": "ImageUpscaleWithModel",
                   "inputs": {"upscale_model": ["up_model", 0], "image": [dec, 0]},
                   "_meta": {"title": f"Upscale x{native}"}}
    g["up_scale"] = {"class_type": "ImageScaleBy",
                     "inputs": {"image": ["up_run", 0], "upscale_method": "lanczos",
                                "scale_by": round(net / native, 4)},
                     "_meta": {"title": f"Thu về x{net:g}"}}
    return g


def generate(m: dict, out: Path, only: set[str], variants: int | None, host: str | None,
             timeout: int) -> list[dict]:
    shared = None
    results, uploaded = [], {}
    for name, a in m["animations"].items():
        if only and name not in only:
            continue
        c = ComfyAnim(host=host, workflow=HERE / "workflows" / GRAPHS[bool(a["loop"])])

        if a.get("anchor") or a.get("anchor_gen"):
            anchor_src = ensure_anchor({**a, "_dir": m["_dir"]},
                                       out / m["character"] / name / "anchor.png", host)
        else:
            shared = shared or ensure_anchor(m, out / m["character"] / "anchor.png", host)
            anchor_src = shared
        w, h, bg = a["width"], a["height"], a["bg"]
        key = (str(anchor_src), w, h, bg)
        if key not in uploaded:
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / (f"anim_{m['character']}_{anchor_src.parent.name}_"
                                f"{w}x{h}_{bg.lstrip('#')}.png")
                prepare_anchor(anchor_src, w, h, bg).save(p)
                uploaded[key] = c.upload(p)
            print(f"{DIM}đã nạp anchor -> {uploaded[key]}{RESET}")

        md = m["models"]
        models = {
            "{{HIGH}}": c.resolve_model("UnetLoaderGGUF", "unet_name", md["high"]),
            "{{LOW}}": c.resolve_model("UnetLoaderGGUF", "unet_name", md["low"]),
            "{{TEXT_ENCODER}}": c.resolve_model("CLIPLoaderGGUF", "clip_name",
                                                md["text_encoder"]),
            "{{VAE}}": c.resolve_model("VAELoader", "vae_name", md["vae"]),
            "{{RMBG}}": md["rmbg"],
        }
        prompt, negative = prompt_for(m, a)
        upscaler = (c.resolve_model("UpscaleModelLoader", "model_name", a["upscaler"])
                    if a.get("upscaler") else "")

        for v in range(variants or int(a["variants"])):
            seed = int(a["seed"]) + v
            tag = f"anim/{m['character']}/{name}/s{seed}-{int(time.time())}"
            graph = c._patch({
                **models, "{{IMAGE}}": uploaded[key], "{{PROMPT}}": prompt,
                "{{NEGATIVE}}": negative, "{{SEED}}": seed, "{{LENGTH}}": int(a["frames"]),
                "{{WIDTH}}": w, "{{HEIGHT}}": h,
                "{{PREFIX_RAW}}": f"{tag}/raw", "{{PREFIX_RGBA}}": f"{tag}/rgba",
            })
            if upscaler:
                graph = add_upscale(graph, upscaler, float(a["upscale"]))
            print(f"sinh {name} {DIM}seed={seed} frames={a['frames']} loop={a['loop']}{RESET}",
                  flush=True)
            t0 = time.time()
            entry = c.run(graph, timeout)
            took = round(time.time() - t0, 1)

            vd = variant_dir(out, m, name, seed)
            for kind in ("raw", "rgba"):
                imgs = c.images_of(entry, graph, f"{tag}/{kind}")
                if not imgs:
                    raise AnimError(f"{name} s{seed}: graph chạy xong nhưng không có frame "
                                    f"'{kind}' — xem log ComfyUI")
                (vd / kind).mkdir(parents=True, exist_ok=True)
                for i, img in enumerate(imgs):
                    (vd / kind / f"{i:03d}.png").write_bytes(c.fetch_image(img))

            prov = {
                "character": m["character"], "animation": name, "seed": seed,
                "prompt": prompt, "negative": negative, "frames": int(a["frames"]),
                "size": [w, h], "bg": bg, "loop": bool(a["loop"]), "graph": c.workflow_path.name,
                "models": {k.strip("{}").lower(): v for k, v in models.items()},
                "upscaler": upscaler, "upscale": float(a["upscale"]) if upscaler else 1.0,
                "graph_hash": hashlib.sha256(
                    json.dumps(graph, sort_keys=True).encode()).hexdigest()[:16],
                "prompt_id": entry.get("_prompt_id"), "seconds": took,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            (vd / "prov.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False),
                                          "utf-8")
            results.append(post_one(vd, name, a))
            print(f"  {GREEN}✓{RESET} {took}s -> {vd}")
    return results


# -- post --------------------------------------------------------------------------------

def post_one(vd: Path, name: str, a: dict) -> dict:
    meta = anim_post.process(vd / "rgba", vd / "post", name, a)
    return {"animation": name, "variant": vd.name, "dir": str(vd), **meta["metrics"]}


def post_all(m: dict, out: Path, only: set[str]) -> list[dict]:
    results = []
    for name, a in m["animations"].items():
        if only and name not in only:
            continue
        for vd in sorted((out / m["character"] / name).glob("s*")):
            if (vd / "rgba").is_dir():
                results.append(post_one(vd, name, a))
    return results


def report(m: dict, out: Path, results: list[dict]) -> int:
    root = out / m["character"]
    by_anim: dict[str, list[dict]] = {}
    for r in results:
        by_anim.setdefault(r["animation"], []).append(r)
    for name, rs in by_anim.items():
        anim_post.review_sheet(
            [(r["variant"], Path(r["dir"]) / "post" / f"{name}_sheet.png") for r in rs],
            root / name / "review.png")
        print(f"\n{name}  {DIM}({root / name / 'review.png'}){RESET}")
        for r in rs:
            flag = f"{YELLOW}!{RESET}" if r["flags"] else f"{GREEN}✓{RESET}"
            loop = f" loop_iou {r['loop_iou']}" if "loop_iou" in r else ""
            print(f"  {flag} {r['variant']}  {DIM}iou_min {r['iou_min']} · drift_x "
                  f"{r['drift_x']} · color_drift {r['color_drift']}{loop}{RESET}")
            for f in r["flags"]:
                print(f"      {YELLOW}{f}{RESET}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "report.json").write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                      "utf-8")
    return 0 if results else 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="nhân vật 2D -> animation frame-by-frame (Wan 2.2)")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="", help="tên animation, phân cách bằng dấu phẩy")
    ap.add_argument("--variants", type=int, default=None, help="ghi đè số seed mỗi animation")
    ap.add_argument("--host", default=None)
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("cmd", choices=("generate", "post"))
    args = ap.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    try:
        m = load_manifest(args.manifest)
        unknown = only - set(m["animations"])
        if unknown:
            raise AnimError(f"--only có animation không nằm trong manifest: {sorted(unknown)}")
        if args.cmd == "generate":
            results = generate(m, args.out, only, args.variants, args.host, args.timeout)
        else:
            results = post_all(m, args.out, only)
        return report(m, args.out, results)
    except (AnimError, mesh.MeshError, gen.ProviderError) as exc:
        print(f"{RED}DỪNG{RESET} — {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
