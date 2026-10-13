#!/usr/bin/env python3
"""artpipe-share — MỘT lệnh: dựng ComfyUI + tải model + sinh + tách nền + chấm + chọn + xuất + nén zip.

    python3 generate.py --preset presets/cute-icons                 # cả preset
    python3 generate.py --preset presets/cute-icons --only potion   # một icon (khớp chuỗi con)
    python3 generate.py --preset presets/cute-icons --icons my.yaml # danh sách icon riêng
    python3 generate.py --job jobs/rpg-shop.json                    # file ý tưởng: preset + cài đặt + danh sách
    python3 generate.py --preset presets/cute-icons --dry-run       # chỉ in prompt, không cần GPU
    python3 generate.py --preset presets/cute-icons --host http://1.2.3.4:8188   # ComfyUI có sẵn ở nơi khác
    python3 generate.py --preset presets/cute-icons --ingest out/cute-icons-1/raw  # chỉ chạy lại hậu kỳ

Đầu ra: out/<preset hoặc tên job>-<giờ>/
    best/<slug>.png         biến thể tốt nhất mỗi icon (512px, nền trong)  ← thứ thường cần
    export/<slug>_<cỡ>.png  best thu về các cỡ trong art-direction icon.export
    atlas.png + atlas.json  ghép mọi best thành 1 tấm (sprite sheet)
    icons/                  MỌI biến thể sau hậu kỳ  ·  raw/ ảnh gốc của AI (giữ để chạy lại hậu kỳ)
    sheet.html              trang duyệt: mọi biến thể + điểm + lý do trượt
    report.json             điểm từng ảnh
và out/<preset>-<giờ>.zip chứa tất cả.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE / "artpipe"
sys.path.insert(0, str(ART))

import yaml  # noqa: E402

GREEN, RED, YELLOW, CYAN, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[2m", "\033[0m"
VERDICT_RANK = {"auto_accept": 0, "needs_review": 1, "auto_reject": 2}


def say(msg: str) -> None:
    print(f"{CYAN}▶{RESET} {msg}", flush=True)


def platform() -> str:
    # Colab trước: máy Colab cũng có /kaggle.
    if os.environ.get("COLAB_RELEASE_TAG") or "google.colab" in sys.modules:
        return "colab"
    if os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        return "kaggle"
    return "local"


def default_comfy_dir() -> Path:
    return {"colab": Path("/content/ComfyUI"),
            # KHÔNG để trong /kaggle/working: thư mục đó bị lưu làm output (giới hạn 20GB).
            "kaggle": Path("/tmp/ComfyUI")}.get(platform(), Path.home() / "ComfyUI")


# ------------------------------------------------------------------ ComfyUI

def comfy_alive(host: str) -> bool:
    try:
        urllib.request.urlopen(f"{host}/system_stats", timeout=3)
        return True
    except Exception:
        return False


def ensure_comfy(comfy: Path) -> str:
    """Cài ComfyUI nếu chưa có; trả về python mà ComfyUI dùng."""
    marker = comfy / ".artpipe-python"
    if not (comfy / "main.py").exists() or not marker.exists():
        say(f"dựng ComfyUI ở {comfy} (lần đầu ~3–5 phút)")
        args = ["bash", str(HERE / "setup_comfy.sh"), "--dir", str(comfy)]
        if platform() in ("colab", "kaggle"):
            args.append("--system-python")
        subprocess.run(args, check=True)
    return marker.read_text().strip()


def download_models(comfy: Path, downloads: list[dict]) -> None:
    for d in downloads or []:
        url = d["url"]
        name = d.get("name") or url.rsplit("/", 1)[-1].split("?")[0]
        dst = comfy / "models" / d.get("dir", "checkpoints") / name
        if dst.exists() and dst.stat().st_size > 1_000_000:
            print(f"    {DIM}đã có {dst.name}{RESET}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        say(f"tải {name} → models/{d.get('dir', 'checkpoints')}/")
        part = dst.with_suffix(dst.suffix + ".part")
        # curl: nối tiếp được (-C -) khi đứt mạng giữa chừng; .part để file dở không bị coi là xong.
        subprocess.run(["curl", "-L", "--fail", "-C", "-", "-#", "-o", str(part), url], check=True)
        part.rename(dst)


def start_comfy(comfy: Path, python: str, host: str, wait: int = 600) -> None:
    log = comfy / "comfyui.log"
    port = host.rsplit(":", 1)[-1]
    say(f"bật ComfyUI (log: {log})")
    proc = subprocess.Popen(
        [python, "-s", "main.py", "--listen", "127.0.0.1", "--port", port],
        cwd=comfy, stdout=open(log, "a"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        start_new_session=True)  # sống tiếp sau khi lệnh này xong → lần chạy sau không phải bật lại
    t0 = time.time()
    while time.time() - t0 < wait:
        if comfy_alive(host):
            print(f"    {GREEN}ComfyUI lên sau {time.time() - t0:.0f}s{RESET}")
            return
        if proc.poll() is not None:
            break
        time.sleep(3)
    print(log.read_text(errors="replace")[-4000:])
    raise SystemExit(f"{RED}ComfyUI không lên — đọc log phía trên{RESET}")


# ------------------------------------------------------------------ hậu kỳ

def pick_best(out: Path) -> dict[str, dict]:
    """Mỗi icon chọn 1 biến thể: nhận > xem tay > loại, rồi ít lỗi hơn, rồi đọc rõ ở 64px hơn."""
    records = json.loads((out / "report.json").read_text("utf-8"))
    best: dict[str, dict] = {}
    for r in records:
        key = (VERDICT_RANK[r["verdict"]], len(r["failures"]),
               -float((r.get("scores") or {}).get("readable_at_64") or 0))
        cur = best.get(r["slug"])
        if cur is None or key < cur["_key"]:
            best[r["slug"]] = {**r, "_key": key}
    (out / "best").mkdir(exist_ok=True)
    for slug, r in best.items():
        src = out / r["asset_path"]
        if src.exists():
            shutil.copy2(src, out / "best" / f"{slug}.png")
    return best


def export_sizes(out: Path, art: dict) -> None:
    from PIL import Image
    sizes = (art.get("icon") or {}).get("export") or [{"size": 128, "suffix": "_128"}]
    (out / "export").mkdir(exist_ok=True)
    for png in sorted((out / "best").glob("*.png")):
        img = Image.open(png).convert("RGBA")
        for e in sizes:
            s = int(e["size"])
            im = img if img.width == s else img.resize((s, s), Image.LANCZOS)
            im.save(out / "export" / f"{png.stem}{e.get('suffix', f'_{s}')}.png")


def run_py(args: list[str], env: dict) -> int:
    return subprocess.run([sys.executable, str(ART / "run.py"), *args], env=env).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job", type=Path, default=None,
                    help="file ý tưởng .json/.yaml: {preset, variants, seed, only, icons:[...]} — xem jobs/")
    ap.add_argument("--preset", type=Path, default=None, help="thư mục preset (presets/cute-icons)")
    ap.add_argument("--icons", type=Path, default=None, help="danh sách icon riêng (mặc định <preset>/icons.yaml)")
    ap.add_argument("--only", default=None, help="chỉ sinh icon có tên file chứa chuỗi này")
    ap.add_argument("--variants", type=int, default=None, help="số biến thể mỗi icon (mặc định theo preset)")
    ap.add_argument("--seed", type=int, default=None, help="seed gốc (mặc định theo preset)")
    ap.add_argument("--out", type=Path, default=None, help="thư mục đầu ra (mặc định out/<preset>-<giờ>)")
    ap.add_argument("--host", default=os.environ.get("COMFYUI_URL", ""),
                    help="ComfyUI có sẵn ở đâu đó — bỏ qua bước dựng máy")
    ap.add_argument("--comfy-dir", type=Path, default=None, help="nơi cài ComfyUI")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in prompt sẽ gửi, không sinh")
    ap.add_argument("--ingest", type=Path, default=None,
                    help="thư mục raw/ của mẻ cũ — chỉ chạy lại hậu kỳ, không cần GPU")
    ap.add_argument("--no-zip", action="store_true")
    args = ap.parse_args()

    if args.job:
        # File ý tưởng = một mẻ trọn gói. Cờ dòng lệnh vẫn thắng (để thử nhanh --only mà không sửa file).
        job = yaml.safe_load(args.job.read_text("utf-8"))  # YAML đọc được cả JSON
        if not isinstance(job, dict) or not isinstance(job.get("icons"), list):
            raise SystemExit(f"{RED}{args.job}: cần một object có khoá \"icons\": [...]{RESET}")
        if args.preset is None and job.get("preset"):
            p = Path(job["preset"])
            args.preset = p if p.is_dir() else HERE / "presets" / p
        args.icons = args.icons or args.job
        for k in ("variants", "seed", "only"):
            if getattr(args, k) is None and job.get(k) not in (None, "", 0):
                setattr(args, k, job[k])
    if args.preset is None:
        raise SystemExit(f"{RED}cần --preset hoặc --job có khoá \"preset\"{RESET}")
    preset_dir = args.preset.resolve()
    spec = preset_dir / "art-direction.md"
    icons = (args.icons or preset_dir / "icons.yaml").resolve()
    for f in (spec, icons, preset_dir / "preset.yaml"):
        if not f.exists():
            raise SystemExit(f"{RED}thiếu {f}{RESET}")
    cfg = yaml.safe_load((preset_dir / "preset.yaml").read_text("utf-8"))

    import catalog
    import prompt as prompt_mod
    import spec as spec_mod
    art = spec_mod.load(spec)
    entries = catalog.entries_from_manifest(icons)
    if args.only:
        entries = [e for e in entries if args.only in catalog.slug(e.descriptor)]
        if not entries:
            raise SystemExit(f"{RED}--only {args.only!r} không khớp icon nào{RESET}")

    # Kiểm prompt TRƯỚC khi đụng GPU: lỗi spec/icons.yaml lộ ra ngay, không phải sau 10 phút tải model.
    bad = 0
    for e in entries:
        try:
            text = prompt_mod.build(art, e.descriptor)
            if args.dry_run:
                print(f"{GREEN}{catalog.slug(e.descriptor)}{RESET}\n    {text}")
        except prompt_mod.PromptError as exc:
            bad += 1
            print(f"{RED}LỖI{RESET} {e.descriptor.name}: {exc}")
    if bad:
        return 2
    if args.dry_run:
        print(f"\n{len(entries)} icon · negative: {DIM}{prompt_mod.negative(art)}{RESET}")
        return 0

    stamp = datetime.now().strftime("%m%d-%H%M")
    name = args.job.stem if args.job else preset_dir.name
    out = (args.out or HERE / "out" / f"{name}-{stamp}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ARTPIPE_PROJECT=str(preset_dir), PYTHONUNBUFFERED="1")

    common = ["--spec", str(spec), "--catalog", str(icons), "--out", str(out)]
    if args.only:
        common += ["--only", args.only]
    if cfg.get("gen_size"):
        common += ["--gen-size", str(cfg["gen_size"])]
    if not cfg.get("stylise", True):
        common.append("--no-stylise")

    if args.ingest:
        say(f"chạy lại hậu kỳ trên {args.ingest}")
        run_py(common + ["ingest", str(args.ingest.resolve()), "--seed-from-name",
                         "--model-name", cfg["checkpoint"]], env)
    else:
        host = (args.host or "http://127.0.0.1:8188").rstrip("/")
        if args.host and not comfy_alive(host):
            raise SystemExit(f"{RED}không gọi được ComfyUI ở {host}{RESET}")
        if not args.host:
            comfy = (args.comfy_dir or default_comfy_dir()).resolve()
            python = ensure_comfy(comfy)
            download_models(comfy, cfg.get("downloads"))
            if not comfy_alive(host):
                start_comfy(comfy, python, host)
        n = len(entries) * (args.variants or cfg.get("variants", 4))
        say(f"sinh {n} ảnh ({len(entries)} icon × {args.variants or cfg.get('variants', 4)} biến thể)"
            f" — T4 mất ~20–40 giây/ảnh, lần đầu thêm ~1 phút nạp model")
        run_py(common + ["generate", "--provider", "comfyui", "--host", host,
                         "--model", cfg["checkpoint"],
                         "--workflow", str(ART / "workflows" / cfg["workflow"]),
                         "--variants", str(args.variants or cfg.get("variants", 4)),
                         "--seed", str(args.seed if args.seed is not None else cfg.get("seed", 1000))], env)

    if not (out / "report.json").exists():
        print(f"{RED}không có ảnh nào được xử lý — xem lỗi phía trên{RESET}")
        return 2

    subprocess.run([sys.executable, str(ART / "sheet.py"), str(out), "--spec", str(spec)], env=env)
    best = pick_best(out)
    export_sizes(out, art)
    subprocess.run([sys.executable, str(HERE / "tools" / "pack_atlas.py"), str(out / "best"),
                    "--out", str(out / "atlas")], env=env)

    print()
    for slug, r in sorted(best.items()):
        tag = {"auto_accept": f"{GREEN}NHẬN{RESET}", "needs_review": f"{YELLOW}XEM {RESET}",
               "auto_reject": f"{RED}LOẠI{RESET}"}[r["verdict"]]
        print(f"  {tag}  best/{slug}.png  {DIM}← {r['variant']}{RESET}")
    if not args.no_zip:
        z = shutil.make_archive(str(out), "zip", out.parent, out.name)
        print(f"\n{GREEN}xong{RESET} → {out}\n       {z}")
    else:
        print(f"\n{GREEN}xong{RESET} → {out}")
    print(f"{DIM}mở sheet.html để xem mọi biến thể; best/ là bản tự chọn — không ưng thì lấy biến thể khác trong icons/{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
