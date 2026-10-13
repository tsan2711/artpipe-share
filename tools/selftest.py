#!/usr/bin/env python3
"""Kiểm cả repo KHÔNG cần GPU — chạy trước khi push (CI cũng chạy).

    python3 tools/selftest.py

1. Mọi preset: đủ file, preset.yaml hợp lệ, workflow tồn tại và có đủ {{PROMPT}}/{{SEED}}/{{CKPT}}
   (thiếu {{SEED}} = 20 ảnh giống hệt nhau mà không phép kiểm nào thấy), mọi icon dựng được prompt.
2. Chạy TRỌN generate.py với một ComfyUI giả (trả ảnh mẫu): sinh → tách nền → chấm → best/ →
   export/ → atlas → zip. Ảnh mẫu nền hồng phẳng nên dùng tách nền theo màu thay cho rembg.
3. Notebook: bundle nhúng trong artpipe.ipynb khớp code hiện tại (quên `tools/build_notebook.py`
   = người dùng Colab chạy code cũ).
"""

from __future__ import annotations

import http.server
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "artpipe"))

import yaml  # noqa: E402

import catalog  # noqa: E402
import prompt as prompt_mod  # noqa: E402
import spec as spec_mod  # noqa: E402

FAILS: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def presets() -> list[Path]:
    return sorted(p for p in (ROOT / "presets").iterdir() if (p / "preset.yaml").exists())


def test_presets() -> None:
    print("[1] preset")
    for p in presets():
        cfg = yaml.safe_load((p / "preset.yaml").read_text("utf-8"))
        for k in ("checkpoint", "workflow"):
            check(bool(cfg.get(k)), f"{p.name}: preset.yaml có '{k}'")
        wf = ROOT / "artpipe" / "workflows" / cfg["workflow"]
        check(wf.exists(), f"{p.name}: workflow {cfg['workflow']} tồn tại")
        if wf.exists():
            text = wf.read_text("utf-8")
            for ph in ("{{PROMPT}}", "{{SEED}}", "{{CKPT}}"):
                check(ph in text, f"{p.name}: {cfg['workflow']} có {ph}")
            for lora in re.findall(r'"lora_name":\s*"([^"]+)"', text):
                have = any(d.get("dir") == "loras" and d["url"].rsplit("/", 1)[-1].split("?")[0] == lora
                           for d in cfg.get("downloads") or [])
                check(have, f"{p.name}: preset tải LoRA {lora} mà workflow cần")
        names = [d["url"].rsplit("/", 1)[-1].split("?")[0] for d in cfg.get("downloads") or []]
        check(cfg["checkpoint"] in names, f"{p.name}: preset tải checkpoint {cfg['checkpoint']}")
        art = spec_mod.load(p / "art-direction.md")
        entries = catalog.entries_from_manifest(p / "icons.yaml")
        check(len(entries) > 0, f"{p.name}: icons.yaml có {len(entries)} icon")
        slugs = [catalog.slug(e.descriptor) for e in entries]
        check(len(slugs) == len(set(slugs)), f"{p.name}: tên icon không trùng nhau")
        errs = []
        for e in entries:
            try:
                prompt_mod.build(art, e.descriptor)
            except prompt_mod.PromptError as exc:
                errs.append(str(exc))
        check(not errs, f"{p.name}: mọi icon dựng được prompt {errs[:2] if errs else ''}")


def test_jobs() -> None:
    print("[1b] file ý tưởng (jobs/)")
    for j in sorted((ROOT / "jobs").glob("*.json")):
        r = subprocess.run([sys.executable, str(ROOT / "generate.py"), "--job", str(j), "--dry-run"],
                           capture_output=True, text=True)
        check(r.returncode == 0, f"{j.name}: dựng được prompt mọi icon"
              + ("" if r.returncode == 0 else "\n" + (r.stdout + r.stderr)[-800:]))


class FakeComfy(http.server.BaseHTTPRequestHandler):
    image = b""
    prompts: list[dict] = []

    def log_message(self, *a):  # im lặng
        pass

    def _send(self, body: bytes, ctype="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n))
        FakeComfy.prompts.append(payload["prompt"])
        self._send(json.dumps({"prompt_id": f"p{len(FakeComfy.prompts)}"}).encode())

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/system_stats":
            return self._send(b"{}")
        if u.path.startswith("/history/"):
            pid = u.path.rsplit("/", 1)[-1]
            return self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {
                "7": {"images": [{"filename": "a.png", "subfolder": "", "type": "output"}]}}}}).encode())
        if u.path == "/view":
            return self._send(FakeComfy.image, "image/png")
        self.send_response(404)
        self.end_headers()


def test_end_to_end() -> None:
    print("[2] trọn đường ống với ComfyUI giả")
    FakeComfy.image = (ROOT / "artpipe" / "fixtures" / "generated_fire_projectile_raw.png").read_bytes()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeComfy)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    host = f"http://127.0.0.1:{srv.server_address[1]}"
    with tempfile.TemporaryDirectory() as tmp:
        pre = Path(tmp) / "preset"
        shutil.copytree(ROOT / "presets" / "cute-icons", pre)
        ad = pre / "art-direction.md"
        # Ảnh mẫu nền hồng phẳng → tách nền theo màu (không cần rembg ~170MB trong CI).
        ad.write_text(ad.read_text("utf-8").replace(
            "  matte_method: segment\n",
            '  matte_method: chroma\n  backdrop_hex: "#FF0F87"\n  backdrop_name: hot pink\n'), "utf-8")
        out = Path(tmp) / "out"
        r = subprocess.run([sys.executable, str(ROOT / "generate.py"), "--preset", str(pre),
                            "--host", host, "--only", "potion", "--variants", "2", "--out", str(out)],
                           capture_output=True, text=True)
        tail = (r.stdout + r.stderr)[-1500:]
        check(r.returncode == 0, f"generate.py thoát 0{'' if r.returncode == 0 else chr(10) + tail}")
        check(len(FakeComfy.prompts) == 2, f"gửi 2 prompt (gửi {len(FakeComfy.prompts)})")
        if len(FakeComfy.prompts) == 2:
            seeds = {n["inputs"]["seed"] for g in FakeComfy.prompts for n in g.values()
                     if "seed" in n.get("inputs", {})}
            check("{{" not in json.dumps(FakeComfy.prompts[0]), "graph gửi đi không còn {{chỗ trống}}")
            check(len(seeds) == 2, "hai biến thể khác seed")
        for f in ("report.json", "sheet.html", "best/potion.png", "export/potion_64.png",
                  "atlas.png", "atlas.json"):
            check((out / f).exists(), f"có {f}")
        check(Path(str(out) + ".zip").exists(), "có file zip")
    srv.shutdown()


def test_notebook() -> None:
    print("[3] notebook")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_notebook.py"), "--check"],
                       capture_output=True, text=True)
    check(r.returncode == 0, "bundle trong artpipe.ipynb khớp code — " + (r.stdout + r.stderr).strip())


def main() -> int:
    test_presets()
    test_jobs()
    test_end_to_end()
    test_notebook()
    print(f"\n{'XANH' if not FAILS else f'ĐỎ — {len(FAILS)} lỗi'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
