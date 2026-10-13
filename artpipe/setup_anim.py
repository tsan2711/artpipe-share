"""Cài làn anim lên máy render ĐANG CHẠY — gọi từ CI (job setup-anim) hoặc tay.

    python3 tools/artpipe/setup_anim.py            # COMFYUI_URL mặc định 127.0.0.1:8188
    python3 tools/artpipe/setup_anim.py --dry-run  # chỉ in kế hoạch

## Vì sao không gọi setup_pc.ps1 -Anim từ CI

Máy PC có HAI bản ComfyUI (README-comfyui.md, sự cố 2026-09-10) và biến `ARTPIPE_PYTHON`
của runner trỏ vào bản cũ KHÔNG chạy (`D:\\sangcute\\ComfyUI`). Cài theo đường dẫn khai
sẵn là cài vào chỗ không ai đọc. Nên script này hỏi thẳng SERVER đang nghe cổng:

  * `/internal/folder_paths` -> thư mục custom_nodes / unet / text_encoders / vae thật
  * `/system_stats`          -> bản Python của server, để chọn đúng venv mà pip vào

và chỉ cài vào đó. Không đoán, không dùng đường dẫn cứng.

## Cài tối thiểu, không nâng cấp gì

`requirements.txt` của ComfyUI-RMBG kéo groundingdino, onnxruntime-gpu, SAM… — nâng cấp
transformers/protobuf trong venv đang chạy có thể làm hỏng node khác (Hunyuan3D). Node
BiRefNet chỉ cần vài gói, và ComfyUI-RMBG nạp từng file node trong try/except, nên thiếu gói
của node khác không kéo sập BiRefNet. `pip install` KHÔNG kèm `-U`: gói đã có thì giữ nguyên.

## Khởi động lại

ComfyUI chỉ quét custom_nodes lúc khởi động. Script thử nút reboot của ComfyUI-Manager
(Desktop có sẵn); không được thì dừng với mã 3 và bảo khởi động lại tay.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RED, GREEN, YELLOW, DIM, RESET = "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m"

NODES = [
    ("ComfyUI-GGUF", "https://github.com/city96/ComfyUI-GGUF"),
    ("ComfyUI-RMBG", "https://github.com/1038lab/ComfyUI-RMBG"),
]
# gguf: ComfyUI-GGUF. Còn lại: đúng import của AILab_BiRefNet.py + birefnet.py (HF 1038lab/BiRefNet).
PIP = ["gguf", "huggingface-hub", "opencv-python", "safetensors", "einops", "kornia",
       "timm", "transformers"]

WAN = "https://huggingface.co/jayn7/WAN2.2-I2V_A14B-DISTILL-LIGHTX2V-4STEP-GGUF/resolve/main"
MODELS = [  # (khoá folder_paths, tên file, url) — khớp anim.DEFAULT_MODELS
    ("diffusion_models", "wan2.2_i2v_A14b_high_noise_lightx2v_4step-Q4_K_M.gguf",
     f"{WAN}/high_noise/wan2.2_i2v_A14b_high_noise_lightx2v_4step-Q4_K_M.gguf"),
    ("diffusion_models", "wan2.2_i2v_A14b_low_noise_lightx2v_4step-Q4_K_M.gguf",
     f"{WAN}/low_noise/wan2.2_i2v_A14b_low_noise_lightx2v_4step-Q4_K_M.gguf"),
    ("text_encoders", "umt5-xxl-encoder-Q5_K_M.gguf",
     "https://huggingface.co/city96/umt5-xxl-encoder-gguf/resolve/main/umt5-xxl-encoder-Q5_K_M.gguf"),
    # VAE 2.1, không phải 2.2 — Wan 2.2 14B i2v thừa kế VAE 2.1 ("36 vs 64 channels" nếu sai).
    ("vae", "wan_2.1_vae.safetensors",
     "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"),
    # Upscaler anime (17MB, BSD-3). CỐ Ý không dùng 4x-AnimeSharp dù phổ biến: license
    # CC BY-NC-SA — cấm thương mại, mà asset này đi vào game bán.
    ("upscale_models", "RealESRGAN_x4plus_anime_6B.pth",
     "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"),
]
NEED_GB = 26


class SetupError(RuntimeError):
    pass


class Server:
    def __init__(self, host: str, token: str) -> None:
        self.host, self.token = host.rstrip("/"), token

    def get(self, path: str, timeout: int = 30) -> dict:
        h = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        with urllib.request.urlopen(urllib.request.Request(self.host + path, headers=h),
                                    timeout=timeout) as r:
            return json.loads(r.read() or b"{}")

    def alive(self) -> bool:
        try:
            self.get("/system_stats", timeout=5)
            return True
        except Exception:  # noqa: BLE001
            return False


def server_python(custom_nodes: Path, want_version: str) -> str:
    """Venv của server: <base>/.venv hoặc <base>/venv, base = cha của custom_nodes.

    Đối chiếu version với /system_stats để chắc là đúng interpreter đang chạy server —
    đúng cái bẫy hai-bản-ComfyUI: một venv có thật nhưng không phải của server.
    """
    base = custom_nodes.parent
    for rel in (".venv/Scripts/python.exe", "venv/Scripts/python.exe",
                ".venv/bin/python", "venv/bin/python"):
        py = base / rel
        if not py.exists():
            continue
        v = subprocess.run([str(py), "-c", "import sys; print(sys.version)"],
                           capture_output=True, text=True).stdout.strip()
        if v.split()[0] == want_version.split()[0]:
            return str(py)
        print(f"  {YELLOW}{py} là Python {v.split()[0]}, server chạy {want_version.split()[0]} "
              f"— bỏ qua{RESET}")
    raise SetupError(f"không tìm thấy venv của server cạnh {custom_nodes} khớp Python "
                     f"{want_version.split()[0]}")


def _writable(d: Path) -> bool:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".artpipe_write_probe"
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


def _exists(f: Path) -> bool:
    try:
        return f.exists()
    except OSError:  # thư mục không đọc được (quyền) = coi như chưa có ở đó
        return False


def pick_dir(paths: list[str], prefer: str | None = None) -> Path:
    """Thư mục đầu tiên mà RUNNER ghi được, ưu tiên tên `prefer`.

    Server liệt kê model từ MỌI thư mục đã đăng ký, nên ghi vào thư mục nào trong danh sách
    cũng được. Đã gặp thật: runner chạy dưới tài khoản khác, bị "Access is denied" ở thư mục
    dùng chung của Comfy Desktop trong AppData của người dùng — trong khi thư mục models của
    chính bản ComfyUI đang chạy thì ghi được.
    """
    ps = [Path(p) for p in paths]
    ps.sort(key=lambda p: p.name != prefer)
    for p in ps:
        if _writable(p):
            return p
    raise SetupError(f"runner không ghi được vào thư mục nào trong: {[str(p) for p in ps]}")


def _fetch_once(url: str, part: Path) -> int:
    """Một lượt tải tiếp từ byte đã có. Trả tổng kích thước file (0 nếu server không nói)."""
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
    with urllib.request.urlopen(req, timeout=120) as r:
        if have and r.status != 206:
            have = 0  # server không hỗ trợ Range -> tải lại từ đầu
        total = have + int(r.headers.get("Content-Length") or 0)
        done, last = have, time.time()
        with open(part, "ab" if have else "wb") as fh:
            while chunk := r.read(8 << 20):
                fh.write(chunk)
                done += len(chunk)
                if time.time() - last > 60:
                    pct = f"{done * 100 / total:.0f}%" if total else ""
                    print(f"    {DIM}{part.name}: {done / 1e9:.2f}/{total / 1e9:.2f} GB {pct}{RESET}",
                          flush=True)
                    last = time.time()
    return total


def download(url: str, dst: Path, attempts: int = 30) -> None:
    """Tải có tiếp tục, tự nối lại khi đứt.

    Đã gặp thật: CDN của HuggingFace cắt kết nối sau ~66MB của file 9.6GB, và urllib coi
    đó là hết file (read() trả rỗng, không ném lỗi). Nên phải so với Content-Length rồi
    xin Range tiếp — một lượt không bao giờ đủ với file cỡ này.
    """
    part = dst.with_name(dst.name + ".part")
    total, fails = 0, 0
    while fails < attempts:
        before = part.stat().st_size if part.exists() else 0
        try:
            total = _fetch_once(url, part) or total
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            print(f"    {YELLOW}đứt ({exc}) — nối lại{RESET}", flush=True)
        size = part.stat().st_size if part.exists() else 0
        if total and size >= total:
            break
        fails = 0 if size > before else fails + 1
        time.sleep(min(30, 2 + fails * 3))
    size = part.stat().st_size if part.exists() else 0
    if not total or size != total:
        raise SetupError(f"{dst.name}: tải thiếu ({size} / {total} byte) sau {attempts} lần "
                         f"không tiến — chạy lại để tải tiếp")
    part.replace(dst)


def reboot_and_wait(s: Server, timeout: int = 300) -> bool:
    for path in ("/api/manager/reboot", "/manager/reboot"):
        try:
            s.get(path, timeout=10)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
        except Exception:  # noqa: BLE001 — server tắt giữa chừng khi reboot là chuyện bình thường
            pass
        print(f"  {DIM}đã gọi {path}, chờ server tắt rồi lên lại…{RESET}", flush=True)
        t0 = time.time()
        while time.time() - t0 < 60 and s.alive():
            time.sleep(2)
        while time.time() - t0 < timeout:
            if s.alive():
                return True
            time.sleep(3)
        return False
    return False


def verify(s: Server) -> list[str]:
    missing = []
    for node in ("UnetLoaderGGUF", "CLIPLoaderGGUF", "BiRefNetRMBG", "WanImageToVideo",
                 "WanFirstLastFrameToVideo", "UpscaleModelLoader", "ImageUpscaleWithModel"):
        try:
            if not s.get(f"/object_info/{node}"):
                missing.append(node)
        except Exception:  # noqa: BLE001
            missing.append(node)
    return missing


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="cài làn anim lên máy ComfyUI đang chạy")
    ap.add_argument("--host", default=os.environ.get("COMFYUI_URL") or "http://127.0.0.1:8188")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-reboot", action="store_true")
    a = ap.parse_args()
    s = Server(a.host, os.environ.get("COMFYUI_TOKEN", ""))

    try:
        # ComfyUI vừa mở lại có thể còn đang nạp node (lần đầu nạp node mới chậm), hoặc mở
        # ở cổng khác: bản chạy tay nghe 8188, Comfy Desktop mặc định 8000. Chờ + dò cả hai.
        t0 = time.time()
        while not s.alive() and time.time() - t0 < 180:
            other = a.host.replace(":8188", ":8000") if ":8188" in a.host else None
            if other and Server(other, s.token).alive():
                print(f"{YELLOW}server đang nghe {other}, không phải {a.host} — dùng {other}. "
                      f"Sửa secret COMFYUI_URL nếu muốn các làn khác cũng thấy.{RESET}")
                s = Server(other, s.token)
                break
            time.sleep(10)
        if not s.alive():
            raise SetupError(f"ComfyUI không trả lời ở {a.host} (cả :8000) sau 3 phút — "
                             f"ComfyUI đã mở chưa, hay đang hỏng lúc khởi động?")
        stats = s.get("/system_stats")
        fp = s.get("/internal/folder_paths")
        sysi = stats.get("system", {})
        for d in stats.get("devices", []):
            print(f"GPU  {d.get('name')}  VRAM {d.get('vram_total', 0) / 2**30:.1f} GB")
        print(f"RAM  {sysi.get('ram_total', 0) / 2**30:.0f} GB · ComfyUI "
              f"{sysi.get('comfyui_version')} · Python {sysi.get('python_version', '').split()[0]}")

        cn = Path(fp["custom_nodes"][0])
        py = server_python(cn, sysi.get("python_version", ""))
        print(f"custom_nodes  {cn}\nvenv server   {py}")

        targets = []
        for key, name, url in MODELS:
            paths = fp.get(key) or fp.get({"diffusion_models": "unet",
                                           "text_encoders": "clip"}.get(key, key)) or []
            if not paths:
                raise SetupError(f"server không khai thư mục '{key}'")
            if any(_exists(Path(p) / name) for p in paths):
                print(f"  {DIM}đã có {name}{RESET}")
                continue
            d = pick_dir(paths, "unet" if key == "diffusion_models" else None)
            targets.append((d / name, url))
            print(f"  sẽ tải {name} -> {d}")

        new_nodes = [(n, u) for n, u in NODES if not (cn / n / "__init__.py").exists()]
        for n, _ in new_nodes:
            print(f"  sẽ clone {n} -> {cn / n}")
        if a.dry_run:
            return 0

        if targets:
            root = targets[0][0].parent
            free = shutil.disk_usage(root).free / 1e9
            if free < NEED_GB:
                raise SetupError(f"ổ chứa {root} còn {free:.0f} GB, cần ~{NEED_GB} GB")

        for n, u in new_nodes:
            subprocess.run(["git", "clone", "--depth", "1", u, str(cn / n)], check=True)
        r = subprocess.run([py, "-m", "pip", "install", *PIP])
        if r.returncode:
            raise SetupError("pip install lỗi — xem log phía trên")

        for dst, url in targets:
            dst.parent.mkdir(parents=True, exist_ok=True)
            print(f"tải {dst.name}", flush=True)
            download(url, dst)
            print(f"  {GREEN}✓{RESET} {dst}")

        # Reboot khi server CHƯA thấy node, không chỉ khi vừa clone: node clone ở một lần
        # chạy trước (lần đó dừng giữa chừng) vẫn nằm trên đĩa mà server chưa nạp — đã gặp.
        if verify(s):
            if a.no_reboot or not reboot_and_wait(s):
                print(f"{YELLOW}ĐÃ CÀI, nhưng ComfyUI cần KHỞI ĐỘNG LẠI để nhận custom node "
                      f"mới — tắt/mở ComfyUI Desktop rồi chạy lại job này để kiểm.{RESET}")
                return 3
        missing = verify(s)
        if missing:
            raise SetupError(f"server vẫn thiếu node: {missing} — xem log khởi động của ComfyUI")
        print(f"{GREEN}xong — làn anim sẵn sàng.{RESET} BiRefNet_toonout tự tải ở lần chạy đầu.")
        return 0
    except (SetupError, subprocess.CalledProcessError, urllib.error.URLError, KeyError) as exc:
        print(f"{RED}DỪNG{RESET} — {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
