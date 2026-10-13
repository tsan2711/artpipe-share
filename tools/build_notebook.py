#!/usr/bin/env python3
"""Dựng artpipe.ipynb (một notebook cho cả Colab lẫn Kaggle) và NHÚNG sẵn toàn bộ code vào trong.

    python3 tools/build_notebook.py          # sửa code/preset xong thì chạy lại lệnh này
    python3 tools/build_notebook.py --check  # selftest/CI: bundle trong notebook có khớp code không

Vì sao nhúng: repo private thì Colab/Kaggle không clone được nếu thiếu token. Có bundle nhúng
thì người dùng chỉ cần mở notebook → Run all, không khai gì. Có token (secret GH_TOKEN) hoặc repo
public thì notebook clone bản mới nhất thay vì dùng bundle.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "artpipe.ipynb"
REPO = "tsan2711/artpipe-share"

INCLUDE = ["generate.py", "setup_comfy.sh", "requirements.txt", "tools/pack_atlas.py"]
INCLUDE_DIRS = [("artpipe", ("*.py", "workflows/*.json", "themes/*.yaml")), ("presets", ("**/*",)), ("jobs", ("*.json", "*.yaml"))]


def files() -> list[Path]:
    out = [ROOT / f for f in INCLUDE]
    for d, pats in INCLUDE_DIRS:
        for pat in pats:
            out += [p for p in (ROOT / d).glob(pat) if p.is_file() and "__pycache__" not in p.parts]
    return sorted(set(out))


def bundle() -> tuple[str, str]:
    """(base64 zip, sha256 nội dung). Zip tất định: cùng code → cùng chuỗi."""
    h = hashlib.sha256()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files():
            rel = p.relative_to(ROOT).as_posix()
            data = p.read_bytes()
            h.update(rel.encode() + b"\0" + data + b"\0")
            info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if p.suffix in (".sh", ".py") else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return base64.b64encode(buf.getvalue()).decode(), h.hexdigest()[:16]


def md(src: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": src.strip("\n").splitlines(True)}


def code(src: str, hidden: bool = False) -> dict:
    meta = {"cellView": "form"} if hidden else {}
    return {"cell_type": "code", "execution_count": None, "metadata": meta, "outputs": [],
            "source": src.strip("\n").splitlines(True)}


INTRO = f"""
# 🎨 artpipe — sinh icon & sprite 2D bằng AI (Colab / Kaggle)

![mẫu](https://raw.githubusercontent.com/tsan2711/artpipe-share/main/docs/samples/kawaii-doodle-preview-light.png)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{REPO}/blob/main/artpipe.ipynb)

**Cách chạy (không cần cài gì):**

| | Google Colab | Kaggle |
|---|---|---|
| 1 | *Runtime → Change runtime type → **T4 GPU*** | *Settings → Accelerator → **GPU T4 x2*** · *Internet → **On*** (cần xác minh SĐT 1 lần) |
| 2 | Sửa ô **⚙️ Cấu hình** bên dưới (hoặc để nguyên chạy mẫu) | như Colab |
| 3 | *Runtime → **Run all*** | ***Run All*** (hoặc *Save Version → Save & Run All* để chạy nền, không cần giữ tab) |
| 4 | Cuối notebook tự tải file `.zip` về máy | Lấy `.zip` ở tab **Output** (thư mục `artpipe-share/out/`) |

Lần đầu mỗi phiên mất ~5–8 phút dựng máy + tải model (~7GB), sau đó ~20–40 giây/ảnh trên T4.
Chạy lại ô **🚀 Sinh** trong cùng phiên thì không phải dựng lại.

Có sẵn danh sách ý tưởng dạng JSON? Đặt `JOB` trong ô cấu hình (mẫu ở `jobs/`, hoặc `upload`).

Quy trình đầy đủ, cách viết prompt, cách tạo preset riêng: xem `README.md` và `QUY-TRINH.md` trong repo.
"""

CONFIG = """
#@title ⚙️ Cấu hình — sửa ở đây rồi Run all
PRESET   = "kawaii-doodle" #@param ["kawaii-doodle", "cute-icons", "vector-icons", "chibi-sprites"]
VARIANTS = 0              #@param {type:"integer"}
ONLY     = ""             #@param {type:"string"}
SAVE_TO_DRIVE = False     #@param {type:"boolean"}
JOB      = ""             #@param ["", "jobs/rpg-shop.json", "jobs/idle-ui.json", "jobs/monsters.json", "jobs/skills.json", "upload"] {allow-input: true}

# PRESET   kawaii-doodle = icon "bánh bao" vẽ tay, mặt chấm + má hồng (Animagine XL) — đã chạy thử, có ảnh mẫu
#          cute-icons    = icon item/UI anime màu tươi bóng loáng (Animagine XL)
#          vector-icons  = icon kỹ năng vector phẳng (SDXL + LoRA vector)
#          chibi-sprites = nhân vật / quái chibi toàn thân
# VARIANTS số phương án mỗi icon (0 = theo preset, thường 3–4)
# ONLY     chỉ sinh icon có tên chứa chuỗi này (vd "potion"); để trống = cả danh sách
# SAVE_TO_DRIVE  (Colab) chép thêm file zip vào Google Drive/artpipe/
# JOB      file ý tưởng JSON (preset + số biến thể + danh sách icon trong MỘT file) — có JOB thì bỏ qua PRESET/MY_ICONS.
#          "jobs/..." = mẫu trong repo · "upload" = (Colab) chọn file .json từ máy
#          · đường dẫn bất kỳ, vd Kaggle: "/kaggle/input/<dataset>/my-job.json"

# Danh sách icon CỦA BẠN (YAML). Để trống = dùng danh sách mẫu của preset.
# Mỗi dòng: name = tên file · prompt = mô tả HÌNH bằng tiếng Anh · element = màu trong preset (tuỳ chọn)
#   kawaii-doodle/cute-icons/chibi-sprites: gold red blue green purple pink   ·   vector-icons: fire frost lightning arcane nature holy
MY_ICONS = '''
# - { name: Magic Apple,  prompt: "one shiny red apple with a tiny golden leaf and sparkles", element: red }
# - { name: Fishing Rod,  prompt: "one wooden fishing rod with a red and white bobber" }
'''
"""

GET_CODE = """
#@title 📦 Lấy code + kiểm GPU (không cần sửa)
import os, sys, io, base64, zipfile, subprocess, shutil
from pathlib import Path

COLAB  = 'google.colab' in sys.modules or bool(os.environ.get('COLAB_RELEASE_TAG'))
KAGGLE = not COLAB and bool(os.environ.get('KAGGLE_KERNEL_RUN_TYPE'))
WORK   = Path('/content') if COLAB else Path('/kaggle/working') if KAGGLE else Path.cwd()
CODE   = WORK / 'artpipe-share'
REPO, BRANCH = '__REPO__', 'main'

def secret(name):
    if os.environ.get(name):
        return os.environ[name]
    try:
        if COLAB:
            from google.colab import userdata
            return userdata.get(name)
        if KAGGLE:
            from kaggle_secrets import UserSecretsClient
            return UserSecretsClient().get_secret(name)
    except Exception:
        pass
    return ''

def try_clone():
    tok = secret('GH_TOKEN')
    url = f'https://x-access-token:{tok}@github.com/{REPO}.git' if tok else f'https://github.com/{REPO}.git'
    r = subprocess.run(['git', 'clone', '--depth', '1', '--branch', BRANCH, url, str(CODE)],
                       capture_output=True, text=True, env=dict(os.environ, GIT_TERMINAL_PROMPT='0'))
    return r.returncode == 0

if (CODE / '.git').exists():
    subprocess.run(['git', '-C', str(CODE), 'pull', '--ff-only', '-q'])
    print('code: bản clone, đã pull mới nhất')
elif (CODE / 'generate.py').exists():
    print('code: đã có từ lần chạy trước')
elif try_clone():
    print(f'code: clone {REPO}@{BRANCH}')
else:
    zipfile.ZipFile(io.BytesIO(base64.b64decode(BUNDLE))).extractall(CODE)
    for p in CODE.rglob('*'):
        if p.suffix in ('.sh', '.py'):
            p.chmod(0o755)
    print(f'code: bản nhúng trong notebook ({BUNDLE_ID}) — repo private, không có GH_TOKEN nên không clone (vẫn chạy bình thường)')

gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                     capture_output=True, text=True)
if gpu.returncode != 0 or not gpu.stdout.strip():
    raise RuntimeError('❌ KHÔNG CÓ GPU — Colab: Runtime → Change runtime type → T4 GPU. '
                     'Kaggle: Settings → Accelerator → GPU T4 x2. Rồi chạy lại.')
print('GPU:', gpu.stdout.strip().replace('\\n', ' + '))
"""

RUN = """
#@title 🚀 Sinh (lần đầu ~5–8 phút dựng máy + tải model)
import subprocess, sys, time, glob
from pathlib import Path

job = JOB.strip()
if job == 'upload':
    from google.colab import files as _f
    up = _f.upload()   # chọn file .json
    name = next(iter(up))
    job = str(CODE / 'out' / name)
    Path(job).parent.mkdir(parents=True, exist_ok=True)
    Path(job).write_bytes(up[name])
elif job and not Path(job).is_absolute():
    job = str(CODE / job)
if job:
    args = [sys.executable, '-u', str(CODE / 'generate.py'), '--job', job]
    print('dùng file ý tưởng:', job)
else:
    args = [sys.executable, '-u', str(CODE / 'generate.py'), '--preset', str(CODE / 'presets' / PRESET)]
if VARIANTS:
    args += ['--variants', str(VARIANTS)]
if ONLY.strip():
    args += ['--only', ONLY.strip()]
icons_text = '\\n'.join(l for l in MY_ICONS.splitlines() if l.strip() and not l.strip().startswith('#'))
if icons_text and not job:
    custom = CODE / 'out' / 'my-icons.yaml'
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text('icons:\\n' + '\\n'.join('  ' + l.strip() for l in icons_text.splitlines()), 'utf-8')
    args += ['--icons', str(custom)]
    print('dùng danh sách icon riêng:', custom)

t0 = time.time()
p = subprocess.Popen(args, cwd=CODE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
for line in p.stdout:
    print(line, end='')
p.wait()
print(f'\\n⏱  {(time.time() - t0) / 60:.1f} phút')
if p.returncode != 0:
    raise RuntimeError(f'❌ generate.py lỗi (mã {p.returncode}) — đọc dòng đỏ phía trên')
OUT = Path(max(glob.glob(str(CODE / 'out' / '*' / 'report.json')), key=lambda s: Path(s).stat().st_mtime)).parent
print('kết quả:', OUT)
"""

SHOW = """
#@title 🖼️ Xem kết quả (best = bản tự chọn; dưới là mọi biến thể)
import base64, json
from IPython.display import HTML, display

def tag(png, size, label, color='#9a92a6'):
    b = base64.b64encode(png.read_bytes()).decode()
    return (f'<figure style="margin:6px;display:inline-block;text-align:center;width:{size + 8}px">'
            f'<img src="data:image/png;base64,{b}" style="width:{size}px;height:{size}px;object-fit:contain;'
            f'background:#1e1b2e;border-radius:8px"><figcaption style="font:11px monospace;color:{color};'
            f'word-break:break-all">{label}</figcaption></figure>')

report = {r['variant']: r for r in json.loads((OUT / 'report.json').read_text())}
COL = {'auto_accept': '#4caf50', 'needs_review': '#e0a33a', 'auto_reject': '#e2504a'}
html = '<div style="background:#141118;padding:12px;border-radius:10px"><h3 style="color:#eee">best/</h3>'
html += ''.join(tag(p, 128, p.stem) for p in sorted((OUT / 'best').glob('*.png')))
html += '<h3 style="color:#eee">mọi biến thể (xanh = nhận · vàng = xem tay · đỏ = loại)</h3>'
for p in sorted((OUT / 'icons').glob('*.png')):
    r = report.get(p.stem, {})
    html += tag(p, 96, p.stem, COL.get(r.get('verdict'), '#9a92a6'))
display(HTML(html + '</div>'))
print('Không ưng bản best/? Lấy biến thể khác trong icons/ (cùng tên + __seed). '
      'Lý do trượt của từng ảnh: sheet.html trong zip.')
"""

DOWNLOAD = """
#@title 💾 Tải về
import shutil
ZIP = OUT.with_suffix('.zip')
if COLAB:
    if SAVE_TO_DRIVE:
        from google.colab import drive
        drive.mount('/content/drive')
        dst = Path('/content/drive/MyDrive/artpipe'); dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ZIP, dst / ZIP.name); print('đã chép vào Drive:', dst / ZIP.name)
    from google.colab import files
    files.download(str(ZIP))
elif KAGGLE:
    print('Kaggle: file ở tab Output (bên phải) →', ZIP.relative_to('/kaggle/working'))
else:
    print('file:', ZIP)
"""


def build() -> dict:
    b64, bid = bundle()
    get_code = GET_CODE.replace("__REPO__", REPO)
    # Ô bundle phải chạy TRƯỚC ô lấy code (Run all chạy từ trên xuống) → đặt ngay sau ô cấu hình.
    # Colab gập ô dạng form nên chuỗi base64 dài không hiện ra.
    cells = [
        md(INTRO),
        code(CONFIG, hidden=True),
        code(f"#@title 🔒 code nhúng (tự chạy, đừng sửa — dựng bởi tools/build_notebook.py)\n"
             f"BUNDLE_ID = '{bid}'\nBUNDLE = '{b64}'", hidden=True),
        code(get_code, hidden=True),
        code(RUN, hidden=True),
        code(SHOW, hidden=True),
        code(DOWNLOAD, hidden=True),
    ]
    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "T4", "toc_visible": False},
            "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True, "isGpuEnabled": True,
                       "language": "python", "sourceType": "notebook"},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "artpipe_bundle": bid,
        },
        "nbformat": 4, "nbformat_minor": 0,
    }


def main() -> int:
    if "--check" in sys.argv:
        _, bid = bundle()
        if not NB.exists():
            print("chưa có artpipe.ipynb — chạy python3 tools/build_notebook.py")
            return 1
        have = json.loads(NB.read_text("utf-8")).get("metadata", {}).get("artpipe_bundle")
        if have != bid:
            print(f"bundle cũ ({have} ≠ {bid}) — chạy python3 tools/build_notebook.py")
            return 1
        print(f"khớp ({bid})")
        return 0
    nb = build()
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{NB.name}: {len(nb['cells'])} ô, bundle {nb['metadata']['artpipe_bundle']}, "
          f"{NB.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
