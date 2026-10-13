"""Ảnh -> mesh 3D, qua ComfyUI + node Hunyuan3D-2.1.

    python3 tools/artpipe/mesh.py --out out/mesh --server-image ref.png
    python3 tools/artpipe/mesh.py --out out/mesh --image ./ref.png --faces 6000

Đây là BẢN THỬ, cố ý hẹp: chỉ hình khối, không texture. Câu hỏi duy nhất nó trả lời là
"retopo tự động ra mesh dùng được hay ra rác", vì câu trả lời đó quyết định phần còn lại
của kiến trúc asset 3D. Texture cho environment sẽ KHÔNG đi đường này — mỗi object một
texture riêng là mô hình không scale được; environment dùng material tiling chung.

Mỗi lần chạy xuất HAI file để so sánh trực tiếp:
    <tên>_high.glb  mesh thô ngay sau marching cubes (hàng trăm nghìn tam giác)
    <tên>_low.glb   sau IMRemesh + UV unwrap — cái thật sự đem vào game được hay không

Đường lấy file về đi qua node PreviewAny: `Hy3D21ExportMesh` trả tên file dưới dạng
STRING nhưng KHÔNG ghi gì vào `ui`, nên /history không thấy nó. Nối STRING đó vào
PreviewAny thì tên file hiện ra trong history và client tải bằng /view như ảnh thường —
nhờ vậy không cần đọc đĩa máy chủ, ComfyUI ở đâu cũng chạy được.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gen  # noqa: E402  (dùng lại _substitute + ProviderError, không chép lại)

RED, GREEN, YELLOW, DIM, RESET = (
    "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m")

#: Chỉ thay những thứ BẮT BUỘC khác nhau giữa các lần chạy. Steps, guidance, octree
#: resolution, smooth_iter... nằm trong file graph và do người sửa trong UI — cùng luật
#: với làn icon, để cái graph đang chạy luôn là cái graph trong repo.
SENTINELS = ("{{IMAGE}}", "{{SEED}}", "{{DIT}}", "{{VAE}}",
             "{{VERTS}}", "{{FACES}}", "{{PREFIX_LOW}}", "{{PREFIX_HIGH}}")
REQUIRED = ("{{IMAGE}}", "{{SEED}}", "{{PREFIX_LOW}}")


class MeshError(RuntimeError):
    pass


class ComfyMesh:
    def __init__(self, host: str | None = None, token: str | None = None,
                 workflow: Path | None = None) -> None:
        self.host = (host or os.environ.get("COMFYUI_URL")
                     or "http://127.0.0.1:8188").rstrip("/")
        self.token = token or os.environ.get("COMFYUI_TOKEN", "")
        self.workflow_path = workflow or (
            Path(__file__).parent / "workflows" / "prop_img2mesh.json")
        if not self.workflow_path.exists():
            raise MeshError(f"không thấy workflow: {self.workflow_path}")
        self.graph = json.loads(self.workflow_path.read_text("utf-8"))
        self.client_id = uuid.uuid4().hex[:16]

    @property
    def _headers(self) -> dict:
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path: str, timeout: int = 120) -> bytes:
        req = urllib.request.Request(f"{self.host}{path}", headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.URLError as exc:
            raise MeshError(f"không gọi được ComfyUI ở {self.host}: {exc}") from exc

    # -- nạp ảnh vào thư mục input của server ------------------------------------------
    def upload(self, path: Path) -> str:
        """POST /upload/image, trả về tên file mà node LoadImage sẽ thấy.

        Ảnh nên có alpha: node Hy3D21LoadImageWithTransparency đưa kênh alpha thẳng cho
        MeshGenerator, và nền không tách sạch thì nền biến thành khối 3D dính vào vật thể.
        """
        data = path.read_bytes()
        boundary = f"----artpipe{uuid.uuid4().hex}"
        ctype = mimetypes.guess_type(path.name)[0] or "image/png"
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {ctype}\r\n\r\n".encode(),
            data, b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
            f"--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            f"{self.host}/upload/image", body,
            {**self._headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as exc:
            raise MeshError(f"upload ảnh lỗi {exc.code}: "
                            f"{exc.read().decode('utf-8', 'replace')[:300]}") from exc
        except urllib.error.URLError as exc:
            raise MeshError(f"không upload được ảnh: {exc}") from exc
        name = d.get("name")
        if not name:
            raise MeshError(f"/upload/image không trả tên file: {str(d)[:200]}")
        sub = d.get("subfolder") or ""
        return f"{sub}/{name}" if sub else name

    def resolve_model(self, node_class: str, field: str, want: str) -> str:
        """Khớp tên model với tên mà SERVER thật sự khai, bỏ qua khác biệt dấu phân cách.

        ComfyUI liệt kê model theo đường dẫn của HĐH nó đang chạy: `thư-mục\\file.ckpt` trên
        Windows, `thư-mục/file.ckpt` trên Linux. Viết cứng một kiểu là khoá pipeline vào một
        hệ điều hành — đúng thứ phải tránh khi máy render hôm nay là PC mượn, mai là GPU
        thuê ngoài chạy Linux.
        """
        try:
            raw = self._get(f"/object_info/{node_class}", timeout=60)
            spec = json.loads(raw)[node_class]["input"]["required"][field]
            # Hai định dạng: cũ [[opt, ...], {...}], mới (node schema V3) ["COMBO",
            # {"options": [...]}]. Đọc định dạng mới như cũ thì "COMBO" bị duyệt thành
            # từng chữ cái — đã gặp với UpscaleModelLoader, 2026-09-23.
            opts = spec[1].get("options", []) if spec[0] == "COMBO" else spec[0]
        except Exception:                      # noqa: BLE001 - dò tên là tiện nghi, không phải cổng
            return want
        if want in opts:
            return want
        norm = want.replace("\\", "/").lower()
        for o in opts:
            if str(o).replace("\\", "/").lower() == norm:
                return o
        if opts:
            raise MeshError(f"{node_class}.{field}: không có '{want}' trên máy render. "
                            f"Đang có: {', '.join(map(str, opts))}")
        return want

    # -- chạy graph ---------------------------------------------------------------------
    def _patch(self, values: dict) -> dict:
        graph, found = gen.ComfyUI._substitute(self.graph, values)
        missing = [s for s in REQUIRED if s not in found]
        if missing:
            raise MeshError(
                f"{self.workflow_path.name} thiếu {', '.join(missing)} — graph không có chỗ "
                f"nhận ảnh/seed/tên file thì mọi lần chạy sẽ ghi đè lên nhau và provenance "
                f"ghi sai.")
        stray = sorted({v for _, v in gen._walk_strings(graph) if v.startswith("{{")})
        if stray:
            raise MeshError(f"còn chuỗi thay thế lạ trong graph: {stray}")
        return graph

    def run(self, graph: dict, timeout: int) -> dict:
        body = json.dumps({"prompt": graph, "client_id": self.client_id}).encode()
        req = urllib.request.Request(
            f"{self.host}/prompt", body,
            {**self._headers, "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as exc:
            raise MeshError(f"/prompt trả {exc.code}: "
                            f"{exc.read().decode('utf-8', 'replace')[:600]}") from exc
        except urllib.error.URLError as exc:
            raise MeshError(f"không gọi được ComfyUI ở {self.host}: {exc}") from exc

        pid = d.get("prompt_id")
        if not pid:
            raise MeshError(f"/prompt không trả prompt_id: {str(d)[:300]}")

        deadline = time.time() + timeout
        while True:
            hist = json.loads(self._get(f"/history/{pid}") or b"{}")
            if pid in hist:
                break
            if time.time() > deadline:
                raise MeshError(f"quá {timeout}s chưa xong (prompt_id={pid}). Sinh mesh "
                                f"nặng hơn sinh ảnh nhiều — thử tăng --timeout.")
            time.sleep(2.0)

        entry = hist[pid]
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            msgs = [m for m in status.get("messages", []) if "error" in str(m[0])]
            raise MeshError(f"workflow lỗi: {str(msgs)[:600]}")
        entry["_prompt_id"] = pid
        return entry

    @staticmethod
    def exported_paths(entry: dict) -> list[str]:
        """Đường dẫn tương đối của các file .glb, đọc từ node PreviewAny trong history."""
        out = []
        for node in entry.get("outputs", {}).values():
            for t in node.get("text", []) or []:
                t = str(t).strip()
                if t.lower().endswith((".glb", ".obj", ".ply", ".stl")):
                    out.append(t)
        return out

    def fetch(self, rel: str) -> bytes:
        p = Path(rel.replace("\\", "/"))
        q = urllib.parse.urlencode({"filename": p.name,
                                    "subfolder": str(p.parent) if str(p.parent) != "." else "",
                                    "type": "output"})
        return self._get(f"/view?{q}", timeout=600)


def stats(path: Path) -> dict:
    """Vài con số đủ để nói mesh dùng được hay không, khi có trimesh; không có thì bỏ qua.

    Ba thứ quan trọng nhất với asset game: bao nhiêu tam giác, có kín khối không (hở thì
    bake normal ra vệt đen), và UV atlas có gộp mảnh tốt không (vụn = phí texel + seam
    khắp nơi).

    **Sửa 2026-09-08, theo số đo — `watertight` từng báo sai.** Bản cũ gọi thẳng
    `m.is_watertight` trên mesh vừa `trimesh.load()`, và với bất kỳ mesh có UV nào, mỗi
    seam UV buộc phải tách đỉnh (một đỉnh 3D nằm ở nhiều toạ độ UV thì phải nhân bản) —
    trimesh xem các đỉnh tách đó là KHÔNG nối nhau, nên report `watertight: False` /
    `body_count` cao dù mặt thực sự kín tuyệt đối. Đo trên đúng mesh của
    `mesh-trial-2026-08-20.md`: raw báo `watertight=False`, nhưng gộp lại đỉnh trùng vị
    trí (`merge_vertices(merge_tex=True, merge_norm=True)`) thì `watertight=True`, 1 khối
    duy nhất, **0 boundary edge** trên cả 8000 tam giác — tức mesh trial cũ ghi "hở khối"
    là kết luận sai, không phải mesh sai. Đây là lý do hàm này giờ đo trên bản đã gộp.
    """
    try:
        import trimesh  # type: ignore
        import numpy as np
    except ImportError:
        return {}
    try:
        m = trimesh.load(path, force="mesh")
    except Exception as exc:  # noqa: BLE001 - file hỏng thì báo, đừng làm sập cả mẻ
        return {"loi": str(exc)[:200]}

    geo = m.copy()
    geo.merge_vertices(merge_tex=True, merge_norm=True)
    d = {"faces": int(len(m.faces)), "verts": int(len(m.vertices)),
         "watertight": bool(geo.is_watertight),
         "bbox": [round(float(x), 4) for x in m.extents]}

    # "Độ đặc" — thể tích thật / thể tích bao lồi (convex hull). Sinh ra để bắt đúng
    # lỗi "hoá thành cái ly/xô" đã gặp thật trong batch đá 2026-09-09 (mesh watertight,
    # UV bình thường, số tam giác hợp lý — KHÔNG check nào ở trên bắt được, chỉ phát
    # hiện bằng mắt lúc soát từng cục). Đo trên đúng dữ liệu batch đó: đá tốt (đã xác
    # nhận bằng mắt) ra 0.83–1.00, cục hỏng ("rock_06", cái xô) ra 0.277 — cách biệt
    # rõ, dùng được làm ngưỡng. CHỈ áp cho asset dạng "khối đặc" (đá tảng) — mảnh vỡ/
    # rubble góc cạnh CỐ Ý lõm (wreckage tốt trong đúng batch đó đo ra 0.30–0.96), nên
    # gọi hàm này có tham số riêng, không tự động áp cho mọi kind.
    if geo.is_watertight:
        try:
            hull_vol = float(geo.convex_hull.volume)
            d["convexity"] = round(float(geo.volume) / hull_vol, 4) if hull_vol > 0 else None
        except Exception:  # noqa: BLE001 - convex hull có thể fail trên mesh suy biến
            d["convexity"] = None

    uv = getattr(getattr(m, "visual", None), "uv", None)
    if uv is not None and len(uv):
        u, v = np.asarray(uv)[:, 0], np.asarray(uv)[:, 1]
        d["uv_min"] = [round(float(u.min()), 4), round(float(v.min()), 4)]
        d["uv_max"] = [round(float(u.max()), 4), round(float(v.max()), 4)]
        d["co_uv"] = True

        # Đếm mảnh atlas: dựng một mesh "giả" lấy toạ độ UV làm vị trí đỉnh, gộp đỉnh
        # trùng UV, rồi đếm thành phần liên thông — hai tam giác cùng mảnh atlas thì
        # chung ít nhất một đỉnh trong không gian UV. Đây chính là phép đo đã dùng để
        # bắt ra 277 mảnh (81 mảnh ≤3 tam giác) trên mesh trial cũ — số liệu áp đảo, không
        # phải cảm tính "trông rời rạc".
        uv3 = np.column_stack([u, v, np.zeros(len(u))])
        uv_mesh = trimesh.Trimesh(vertices=uv3, faces=m.faces, process=False)
        uv_mesh.merge_vertices()
        islands = uv_mesh.split(only_watertight=False)
        sizes = sorted((len(c.faces) for c in islands), reverse=True)
        d["uv_islands"] = len(islands)
        d["uv_islands_tiny"] = sum(1 for s in sizes if s <= 3)
    else:
        d["co_uv"] = False
    return d


def repair(path: Path, out_path: Path) -> dict:
    """Vá lỗ hổng hình học còn sót lại sau IMRemesh, bằng `pymeshfix` (MeshFix) —
    `trimesh.repair.fill_holes` đã thử trước và không ăn thua trên mesh thật (đo trên
    `rock_round_902_low`: 0 mảnh được vá, boundary edge không đổi cả trước lẫn sau).

    Hai việc `pymeshfix` làm mà `fill_holes` không làm được, đo được bằng số trên đúng
    mesh trên (xem `mesh-trial-2026-08-20.md`, mục "Sửa 2026-09-09 (tiếp)"):
    1. Bỏ mảnh vụn rời rạc (nhiều tam giác lẻ/đôi trôi nổi, rác của retopo) — không phải
       hình khối, không thể vá bằng cách lấp lỗ.
    2. Lấp lỗ hổng thật trên phần khối chính bằng tam giác hoá đúng biên, không chỉ nối
       quạt (fan) đơn giản như `fill_holes`.
    Kết quả trên `rock_round_902_low`: 13 khối rời/1221 cạnh hở/không kín ->
    **1 khối/0 cạnh hở/kín tuyệt đối**, đổi lại còn 2356/3994 tam giác (bỏ ~41% là mảnh
    vụn, không phải bỏ hình khối thật).

    KHÔNG tự vá UV — pymeshfix chỉ làm việc trên vị trí đỉnh/tam giác, atlas UV cũ (nếu
    có) không còn khớp topology mới và phải unwrap lại (`xatlas`) trước khi bake texture.
    Trả `{}` nếu thiếu `pymeshfix`/`trimesh` — bỏ qua êm, không chặn build (cùng kiểu với
    `stats()`), nhưng in rõ lý do ra để không tưởng nhầm là "đã vá mà vẫn hở".
    """
    try:
        import trimesh  # type: ignore
        import pymeshfix  # type: ignore
    except ImportError as exc:
        return {"bo_qua": f"chưa cài {exc.name} (pip install pymeshfix trimesh)"}

    m = trimesh.load(path, force="mesh")
    m.merge_vertices(merge_tex=True, merge_norm=True)
    before = {"faces": int(len(m.faces)), "watertight": bool(m.is_watertight),
              "body_count": int(m.body_count)}

    mf = pymeshfix.MeshFix(m.vertices, m.faces)
    mf.repair()
    fixed = trimesh.Trimesh(vertices=mf.points, faces=mf.faces, process=False)
    fixed.export(out_path)

    after = {"faces": int(len(fixed.faces)), "watertight": bool(fixed.is_watertight),
             "body_count": int(fixed.body_count)}
    return {"before": before, "after": after, "out": str(out_path)}


def main() -> int:
    # Same Windows console gotcha fixed in asset_record.py/material.py/ui_asset.py/
    # selftest.py — the classic console codepage can't encode these Vietnamese
    # prints and crashes before anything shows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="ảnh -> mesh 3D qua ComfyUI (bản thử)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--image", type=Path, default=None,
                    help="ảnh trên máy này, sẽ upload lên ComfyUI (nên có nền trong suốt)")
    ap.add_argument("--server-image", default="",
                    help="tên ảnh CÓ SẴN trong thư mục input của ComfyUI")
    ap.add_argument("--name", default="", help="tên asset (mặc định lấy theo tên ảnh)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--faces", type=int, default=8000, help="trần tam giác sau retopo")
    ap.add_argument("--verts", type=int, default=0,
                    help="đỉnh mục tiêu cho IMRemesh (mặc định = --faces/2)")
    ap.add_argument("--dit", default="hunyuan3d-dit-v2-1\\model.fp16.ckpt")
    ap.add_argument("--vae", default="hunyuan3d-vae-v2-1\\model.fp16.ckpt")
    ap.add_argument("--host", default=None)
    ap.add_argument("--workflow", type=Path, default=None)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--repair", action="store_true",
                    help="mesh nào hở khối (IMRemesh để lại rác/lỗ) thì tự vá bằng "
                         "pymeshfix, ghi thêm file <tên>_repaired.glb bên cạnh")
    args = ap.parse_args()

    if bool(args.image) == bool(args.server_image):
        print(f"{RED}DỪNG{RESET} — chọn đúng một trong --image (file trên máy này) "
              f"hoặc --server-image (file đã có trên ComfyUI)")
        return 2

    try:
        c = ComfyMesh(host=args.host, workflow=args.workflow)

        if args.image:
            if not args.image.exists():
                raise MeshError(f"không thấy ảnh: {args.image}")
            server_name = c.upload(args.image)
            src = args.image.stem
            print(f"{DIM}đã nạp {args.image.name} -> {server_name}{RESET}")
        else:
            server_name = args.server_image
            src = Path(server_name).stem

        name = args.name or src
        seed = random.randrange(2**31 - 1) if args.seed is None else args.seed
        verts = args.verts or max(100, args.faces // 2)
        # Tên file trên server phải khác nhau giữa các lần chạy, nếu không hai mẻ ghi đè
        # nhau và không cách nào biết file tải về là của mẻ nào.
        tag = f"{name}-{seed}"

        dit = c.resolve_model("Hy3D21MeshGenerator", "model", args.dit)
        vae = c.resolve_model("Hy3D21VAELoader", "model_name", args.vae)

        graph = c._patch({
            "{{IMAGE}}": server_name, "{{SEED}}": seed,
            "{{DIT}}": dit, "{{VAE}}": vae,
            "{{VERTS}}": verts, "{{FACES}}": args.faces,
            "{{PREFIX_LOW}}": f"3D/{tag}_low",
            "{{PREFIX_HIGH}}": f"3D/{tag}_high",
        })

        print(f"sinh mesh {name} {DIM}seed={seed} faces<={args.faces}{RESET}", flush=True)
        t0 = time.time()
        entry = c.run(graph, args.timeout)
        took = time.time() - t0

        rels = c.exported_paths(entry)
        if not rels:
            raise MeshError(
                "graph chạy xong nhưng history không có tên file .glb — thiếu node "
                "PreviewAny nối vào đầu ra STRING của Hy3D21ExportMesh (ExportMesh không "
                "tự khai file vào history).")

        args.out.mkdir(parents=True, exist_ok=True)
        written = []
        for rel in rels:
            dest = args.out / Path(rel.replace("\\", "/")).name
            dest.write_bytes(c.fetch(rel))
            written.append(dest)

        report = {"name": name, "seed": seed, "faces_max": args.faces,
                  "verts_target": verts, "source_image": server_name,
                  "workflow": c.workflow_path.name,
                  "graph_sha256": hashlib.sha256(
                      json.dumps(graph, sort_keys=True).encode()).hexdigest()[:16],
                  "prompt_id": entry.get("_prompt_id"),
                  "seconds": round(took, 1),
                  "generated_at": datetime.now(timezone.utc).isoformat(),
                  "files": {}}

        for dest in written:
            s = stats(dest)
            report["files"][dest.name] = {"bytes": dest.stat().st_size, **s}
            n = s.get("faces")
            extra = ""
            if n:
                extra = f"{DIM}{n} tam giác"
                if s.get("co_uv") is False:
                    extra += ", KHÔNG có UV"
                if s.get("watertight") is False:
                    extra += ", hở khối"
                extra += RESET
            print(f"  {GREEN}✓{RESET} {dest.name}  {extra}")

            if args.repair and s.get("watertight") is False:
                fixed_path = dest.with_name(dest.stem + "_repaired.glb")
                r = repair(dest, fixed_path)
                if "bo_qua" in r:
                    print(f"    {YELLOW}vá bỏ qua{RESET}: {r['bo_qua']}")
                else:
                    a = r["after"]
                    print(f"    {GREEN}✓ vá xong{RESET} -> {fixed_path.name}  "
                          f"{DIM}{a['faces']} tam giác, "
                          f"{'kín khối' if a['watertight'] else 'VẪN HỞ'}{RESET}")
                report["files"][dest.name]["repair"] = r

        (args.out / f"{tag}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
        print(f"{DIM}{took:.0f}s → {args.out}{RESET}")
        return 0

    except (MeshError, gen.ProviderError) as exc:
        print(f"{RED}DỪNG{RESET} — {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
