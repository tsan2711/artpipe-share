#!/usr/bin/env python3
"""Làn ANIMATION — MỘT lệnh: dựng ComfyUI + cài làn anim (Wan 2.2 + BiRefNet, ~24GB) + sinh + hậu kỳ + nén zip.

    python3 animate.py --manifest artpipe/anims/smoke.yaml                 # idle + walk của nhân vật mẫu
    python3 animate.py --manifest artpipe/anims/smoke.yaml --only idle     # một animation
    python3 animate.py --manifest artpipe/anims/test-vfx.yaml              # VFX (lửa, nổ...) nền đen → alpha theo độ sáng
    python3 animate.py --manifest my-hero.yaml --post out/anim-xxx         # chạy lại hậu kỳ, KHÔNG cần GPU

Một ảnh nhân vật (anchor — "điểm neo" giữ danh tính) → Wan 2.2 sinh CẢ clip một lần (frame nhìn lẫn nhau
nên liền mạch) → BiRefNet tách nền → hậu kỳ cả chuỗi: một hộp cắt chung, pivot đáy-giữa, khoá bảng màu tuỳ chọn
→ <anim>_sheet.png + <anim>.json + <anim>_preview.gif. Chi tiết: docs/knowledge/anim-lane.md.

Máy: cần GPU 16GB VRAM. Kaggle (T4 16GB + 29GB RAM) hợp hơn Colab free (12.7GB RAM có thể thiếu khi đổi
expert high/low noise). Lần đầu tải ~24GB model. Một clip 33 frame trên T4 mất cỡ 10–20 phút.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE / "artpipe"
sys.path.insert(0, str(HERE))

import generate as g  # noqa: E402  (dựng ComfyUI, bật/tắt server — dùng chung với làn icon)


def stop_comfy(port: str) -> None:
    subprocess.run(["pkill", "-f", f"main.py --listen 127.0.0.1 --port {port}"])
    time.sleep(3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, required=True, help="file yaml mô tả nhân vật + các animation")
    ap.add_argument("--only", default="", help="tên animation, phân cách bằng dấu phẩy")
    ap.add_argument("--variants", type=int, default=None, help="số seed mỗi animation (ghi đè manifest)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--host", default="", help="ComfyUI có sẵn (đã cài làn anim) — bỏ qua bước dựng máy")
    ap.add_argument("--comfy-dir", type=Path, default=None)
    ap.add_argument("--post", type=Path, default=None, help="thư mục mẻ cũ — chỉ chạy lại hậu kỳ")
    args = ap.parse_args()

    manifest = args.manifest.resolve()
    out = (args.post or args.out or HERE / "out" /
           f"anim-{manifest.stem}-{datetime.now():%m%d-%H%M}").resolve()
    host = (args.host or "http://127.0.0.1:8188").rstrip("/")

    if not args.post and not args.host:
        comfy = (args.comfy_dir or g.default_comfy_dir()).resolve()
        python = g.ensure_comfy(comfy)
        ready = comfy / ".artpipe-anim-ready"
        if not g.comfy_alive(host):
            g.start_comfy(comfy, python, host)
        if not ready.exists():
            # setup_anim hỏi thẳng server đang chạy thư mục models/custom_nodes thật rồi cài vào đó.
            g.say("cài làn anim: ComfyUI-GGUF + ComfyUI-RMBG + Wan 2.2 Q4 (~24GB, lần đầu 10–20 phút)")
            r = subprocess.run([python, str(ART / "setup_anim.py"), "--host", host, "--no-reboot"],
                               env=dict(__import__("os").environ, PYTHONUTF8="1"))
            if r.returncode not in (0, 3):  # 3 = "cần khởi động lại" — tự làm ngay dưới đây
                raise SystemExit(f"{g.RED}setup_anim.py lỗi (mã {r.returncode}){g.RESET}")
            # ComfyUI chỉ quét custom_nodes lúc khởi động → bật lại.
            stop_comfy(host.rsplit(":", 1)[-1])
            g.start_comfy(comfy, python, host)
            ready.write_text("ok")
    elif args.host and not g.comfy_alive(host):
        raise SystemExit(f"{g.RED}không gọi được ComfyUI ở {host}{g.RESET}")

    cmd = [sys.executable, str(ART / "anim.py"), "--manifest", str(manifest), "--out", str(out), "--host", host]
    if args.only:
        cmd += ["--only", args.only]
    if args.variants:
        cmd += ["--variants", str(args.variants)]
    cmd.append("post" if args.post else "generate")
    g.say(("hậu kỳ lại " if args.post else "sinh animation → ") + str(out))
    rc = subprocess.run(cmd, cwd=manifest.parent).returncode
    if rc != 0:
        print(f"{g.RED}anim.py lỗi (mã {rc}){g.RESET}")
        return rc
    z = shutil.make_archive(str(out), "zip", out.parent, out.name)
    print(f"\n{g.GREEN}xong{g.RESET} → {out}\n       {z}")
    print(f"{g.DIM}mỗi animation: <tên>_sheet.png (spritesheet) · <tên>.json (toạ độ frame, pivot, fps) · "
          f"<tên>_preview.gif · review.png (so các seed){g.RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
