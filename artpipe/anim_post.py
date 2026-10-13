"""Hậu kỳ một chuỗi frame nhân vật 2D -> spritesheet dùng được trong game.

    python3 tools/artpipe/anim_post.py out/anim/hero/walk/s1000/rgba --out /tmp/walk \\
        --name walk --cell 128 --fps 10 --loop --count 8

Đầu vào là các PNG RGBA mà `anim.py` tải về (đã tách nền trên máy render). Không cần GPU,
không cần torch — chạy trên Mac, chạy lại bao nhiêu lần cũng được mà không tốn một giây GPU.

## Vì sao xử lý CẢ CHUỖI chứ không từng ảnh

Làn icon cắt/chuẩn hoá từng ảnh riêng, và đó đúng là cách làm hỏng animation: mỗi frame tự
cắt theo hộp bao của riêng nó thì nhân vật co giãn, nhảy lên nhảy xuống giữa các frame dù
video gốc đứng yên. Nên mọi quyết định hình học ở đây dựa trên **toàn chuỗi**:

  * một hộp bao chung (hợp của mọi frame) -> cùng một phép cắt + cùng một tỉ lệ cho mọi frame
  * pivot ở đáy giữa ô — chân nhân vật nằm cố định trên một đường
  * (tuỳ chọn) một bảng màu chung cho cả chuỗi — màu không "sôi" giữa các frame

## Số đo, không phải phán xét

`metrics()` in ra các con số để người chọn biến thể nhìn vào, và gắn cờ khi vượt ngưỡng. Nó
KHÔNG loại biến thể nào: ngưỡng chỉ đúng sau khi đo trên output thật của máy render, cùng luật
với làn mesh (xem `mesh.summarise_mesh`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

#: alpha > ngưỡng này mới tính là "thân nhân vật" khi đo hộp bao / silhouette. Thấp hơn là
#: viền mờ của matte — tính cả vào thì hộp bao phình theo nhiễu.
ALPHA_SOLID = 128

#: Ngưỡng gắn cờ. Đặt theo lý thuyết, CHƯA hiệu chỉnh trên output thật — sửa sau mẻ đầu.
FLAG_MIN_IOU = 0.55        # hai frame liền nhau trùng silhouette dưới mức này = nhảy hình
FLAG_LOOP_IOU = 0.70       # frame cuối -> frame đầu của vòng lặp
FLAG_DRIFT_X = 0.12        # trọng tâm trôi ngang quá 12% bề rộng ô = nhân vật đi khỏi chỗ
FLAG_AREA_RATIO = 1.8      # diện tích lớn nhất / nhỏ nhất — nhân vật phình/co bất thường
FLAG_COLOR_DRIFT = 28.0    # lệch màu trung bình (0-255) so với frame đầu = đổi màu áo/da


def load_frames(folder: Path) -> list[Image.Image]:
    files = sorted(p for p in folder.glob("*.png"))
    if not files:
        raise SystemExit(f"không có PNG nào trong {folder}")
    return [Image.open(p).convert("RGBA") for p in files]


def select(n: int, loop: bool = False, count: int = 0, step: int = 1,
           start: int = 0, end: int = 0) -> list[int]:
    """Chọn chỉ số frame giữ lại.

    `loop`: graph vòng lặp ép frame cuối = frame đầu (cùng một ảnh anchor), nên giữ cả hai
    thì khi phát lặp sẽ có một nhịp đứng hình. Bỏ frame cuối.

    `count` thắng `step`: chia đều `count` frame trên đoạn đã cắt. Với vòng lặp, chia theo
    kiểu không lấy điểm cuối, để khoảng cách từ frame cuối quay về frame đầu cũng đều.
    """
    last = n - 1 if loop else n
    stop = last - end if end else last
    idx = list(range(start, max(start, stop)))
    if not idx:
        return []
    if count and count < len(idx):
        pos = np.linspace(0, len(idx), count, endpoint=False) if loop else \
            np.linspace(0, len(idx) - 1, count)
        return [idx[int(round(p))] for p in pos]
    return idx[::max(1, step)]


def union_bbox(frames: list[Image.Image],
               thr: int = ALPHA_SOLID) -> tuple[int, int, int, int] | None:
    box = None
    for f in frames:
        a = np.asarray(f)[:, :, 3] >= thr
        ys, xs = np.nonzero(a)
        if not len(xs):
            continue
        b = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), max(box[3], b[3]))
    return box


def fit_cells(frames: list[Image.Image], box: tuple[int, int, int, int], cell: int,
              pad: int = 4) -> list[Image.Image]:
    """Cắt đúng MỘT hộp cho mọi frame, thu cùng MỘT tỉ lệ, đặt đáy-giữa ô."""
    bw, bh = box[2] - box[0], box[3] - box[1]
    avail = cell - 2 * pad
    scale = min(avail / bw, avail / bh)
    w, h = max(1, round(bw * scale)), max(1, round(bh * scale))
    x, y = (cell - w) // 2, cell - pad - h
    out = []
    for f in frames:
        c = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
        c.alpha_composite(f.crop(box).resize((w, h), Image.LANCZOS), (x, y))
        out.append(c)
    return out


def fit_rest(frames: list[Image.Image], rest: tuple[int, int, int, int], cell: int,
             pad: int = 4, fill: float = 0.8) -> list[Image.Image]:
    """Khung CỐ ĐỊNH theo tư thế đứng — cùng tỉ lệ + cùng vị trí chân cho MỌI animation.

    `fit_cells` thu theo hộp bao của riêng một clip: clip có vầng sáng phép to thì nhân vật
    bị thu nhỏ hơn clip idle, vào game đổi animation là nhân vật đổi cỡ. Mọi clip đều bắt
    đầu từ cùng một anchor, nên frame đầu (tư thế đứng) là thước chung: nhân vật đứng cao
    `fill` phần ô, chân chạm đáy ô trừ `pad`. Cái gì vượt ra ngoài ô thì bị cắt — `metrics`
    gắn cờ khi xảy ra, để tăng cell hoặc giảm fill.
    """
    rw, rh = rest[2] - rest[0], rest[3] - rest[1]
    avail = cell - 2 * pad
    scale = min(avail * fill / rh, avail / rw)
    fw, fh = frames[0].size
    w, h = max(1, round(fw * scale)), max(1, round(fh * scale))
    cx = (rest[0] + rest[2]) / 2 * scale
    x, y = round(cell / 2 - cx), round(cell - pad - rest[3] * scale)
    out = []
    for f in frames:
        c = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
        big = f.resize((w, h), Image.LANCZOS)
        c.alpha_composite(big, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
        out.append(c)
    return out


def palette_lock(frames: list[Image.Image], colors: int) -> list[Image.Image]:
    """Một bảng `colors` màu chung cho cả chuỗi, map từng frame vào đó, giữ nguyên alpha.

    Quantize riêng từng frame thì mỗi frame một bảng -> màu nhấp nháy khi phát. Bảng chung
    được dựng từ pixel đặc của MỌI frame dồn lại một ảnh.
    """
    solid = [np.asarray(f)[:, :, :3][np.asarray(f)[:, :, 3] >= ALPHA_SOLID] for f in frames]
    px = np.concatenate([s for s in solid if len(s)] or [np.zeros((1, 3), np.uint8)])
    side = int(np.ceil(np.sqrt(len(px))))
    pool = np.zeros((side * side, 3), np.uint8)
    pool[:len(px)] = px
    pool[len(px):] = px[0]
    pal = Image.fromarray(pool.reshape(side, side, 3), "RGB").quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT)
    out = []
    for f in frames:
        rgb = f.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB")
        o = rgb.convert("RGBA")
        o.putalpha(f.getchannel("A"))
        out.append(o)
    return out


def harden_alpha(frames: list[Image.Image], threshold: int) -> list[Image.Image]:
    """Alpha nhị phân — cho pixel art / sprite cần viền sắc, bỏ viền bán trong suốt."""
    out = []
    for f in frames:
        a = np.asarray(f.getchannel("A"))
        o = f.copy()
        o.putalpha(Image.fromarray(np.where(a >= threshold, 255, 0).astype(np.uint8)))
        out.append(o)
    return out


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 1.0


def metrics(cells: list[Image.Image], loop: bool, vfx: bool = False) -> dict:
    """Các con số để chọn biến thể: độ liền mạch, độ trôi, độ giữ danh tính."""
    arr = [np.asarray(c) for c in cells]
    masks = [a[:, :, 3] >= ALPHA_SOLID for a in arr]
    cell = arr[0].shape[1]
    ious = [_iou(masks[i], masks[i + 1]) for i in range(len(masks) - 1)]
    areas = [int(m.sum()) for m in masks]
    cx = [float(np.nonzero(m)[1].mean()) if m.any() else cell / 2 for m in masks]
    mean_rgb = [a[:, :, :3][m].mean(axis=0) if m.any() else np.zeros(3)
                for a, m in zip(arr, masks)]
    color = [float(np.abs(c - mean_rgb[0]).mean()) for c in mean_rgb]

    d = {
        "frames": len(cells),
        "iou_min": round(min(ious), 3) if ious else 1.0,
        "iou_mean": round(float(np.mean(ious)), 3) if ious else 1.0,
        "drift_x": round((max(cx) - min(cx)) / cell, 3),
        "area_ratio": round(max(areas) / max(1, min(areas)), 3),
        "color_drift": round(max(color), 1),
        "empty_frames": sum(1 for a in areas if a == 0),
        "clipped_frames": sum(1 for m in masks
                              if m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()),
    }
    if loop and len(masks) > 1:
        d["loop_iou"] = round(_iou(masks[-1], masks[0]), 3)

    flags = []
    if d["empty_frames"]:
        flags.append(f"{d['empty_frames']} frame trống (matte ăn mất nhân vật)")
    if d["clipped_frames"]:
        flags.append(f"{d['clipped_frames']} frame chạm mép ô (bị cắt) — tăng cell hoặc giảm fill")
    if d["iou_min"] < FLAG_MIN_IOU:
        flags.append(f"nhảy hình giữa 2 frame (iou_min {d['iou_min']})")
    if d.get("loop_iou", 1.0) < FLAG_LOOP_IOU:
        flags.append(f"vòng lặp không khép (loop_iou {d['loop_iou']})")
    if d["drift_x"] > FLAG_DRIFT_X:
        flags.append(f"nhân vật trôi ngang (drift_x {d['drift_x']}) — prompt thiếu 'in place'?")
    if d["area_ratio"] > FLAG_AREA_RATIO:
        flags.append(f"thân phình/co bất thường (area_ratio {d['area_ratio']})")
    if d["color_drift"] > FLAG_COLOR_DRIFT and not vfx:  # hiệu ứng CỐ Ý đổi màu
        flags.append(f"đổi màu giữa chừng (color_drift {d['color_drift']})")
    d["flags"] = flags
    return d


def key_black(rgba: list[Image.Image], raw: list[Image.Image],
              use_char: bool = True) -> tuple[list[Image.Image], list[Image.Image]]:
    """Clip sinh trên NỀN ĐEN -> (nhân vật + hiệu ứng, chỉ hiệu ứng), không viền.

    Hiệu ứng phát sáng vẽ trên nền trắng thì lõi trắng của nó TRÙNG màu nền — không phép
    tách nào khôi phục được, nên BiRefNet để lại viền trắng (cast, 2026-09-23). Trên nền
    đen thì độ sáng CHÍNH LÀ độ phủ: alpha = độ sáng trên mức nền, màu thật = ảnh / alpha
    (bỏ nhân trước với đen). Nhân vật vẫn lấy mask của BiRefNet — phần tối của nhân vật
    (quần đen, viền) có độ sáng thấp nên không thể key bằng độ sáng.

    `use_char=False`: clip CHỈ có hiệu ứng (lửa, sét, nổ) — bỏ mask BiRefNet, toàn bộ alpha
    theo độ sáng. BiRefNet học tách NHÂN VẬT; với một quả cầu lửa nó đoán bừa.
    """
    both, vfx = [], []
    border = np.asarray(raw[0].convert("RGB")).astype(np.float32)
    floor = float(np.median(np.concatenate([border[0], border[-1], border[:, 0], border[:, -1]])))
    for fg, rw in zip(rgba, raw):
        f = np.asarray(fg).astype(np.float32)
        r = np.asarray(rw.convert("RGB").resize(fg.size)).astype(np.float32)
        a_char = f[:, :, 3] / 255.0 if use_char else np.zeros(f.shape[:2], np.float32)
        a_luma = np.clip((r.max(axis=2) - floor) / max(1.0, 255.0 - floor), 0.0, 1.0)
        unpre = np.clip(r / np.maximum(a_luma, 1e-3)[:, :, None], 0, 255)
        is_char = a_char >= 0.5
        rgb = np.where(is_char[:, :, None], f[:, :, :3], unpre)
        a = np.maximum(a_char, np.where(is_char, 0.0, a_luma))
        both.append(Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), "RGBA"))
        av = np.where(is_char, 0.0, a_luma)
        vfx.append(Image.fromarray(np.dstack([unpre, av * 255]).astype(np.uint8), "RGBA"))
    return both, vfx


def extreme_index(cells: list[Image.Image]) -> int:
    """Frame lệch xa tư thế đầu nhất = đỉnh động tác (cú đấm duỗi hết, tay giơ cao nhất)."""
    masks = [np.asarray(c)[:, :, 3] >= ALPHA_SOLID for c in cells]
    return int(np.argmax([1.0 - _iou(m, masks[0]) for m in masks]))


def edge_flicker(cells: list[Image.Image]) -> float:
    """Độ rung viền: chênh alpha trung bình giữa 2 frame liền nhau, chỉ trên pixel viền.

    Chỉ để theo dõi. Đã thử san bằng trung vị 3 frame trên pixel viền (2026-09-23): idle
    6.98 -> 6.83, walk/punch còn TĂNG — rung chủ yếu là chuyển động thật + khử răng cưa khi
    thu nhỏ, không phải mask BiRefNet nhảy. Nên bỏ, không để lại núm vô tác dụng.
    """
    a = [np.asarray(c)[:, :, 3].astype(np.int16) for c in cells]
    vals = []
    for x, y in zip(a, a[1:]):
        soft = ((x > 0) & (x < 255)) | ((y > 0) & (y < 255))
        if soft.any():
            vals.append(float(np.abs(x - y)[soft].mean()))
    return round(float(np.mean(vals)), 2) if vals else 0.0


def sharpen(cells: list[Image.Image], percent: int) -> list[Image.Image]:
    """Unsharp mask trên RGB, giữ nguyên alpha. Làm SAU khi thu về ô: thu nhỏ làm mềm nét,
    làm sắc trước khi thu thì công cốc."""
    from PIL import ImageFilter
    out = []
    for c in cells:
        o = c.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=percent,
                                                             threshold=2)).convert("RGBA")
        o.putalpha(c.getchannel("A"))
        out.append(o)
    return out


def strip(cells: list[Image.Image]) -> Image.Image:
    cell = cells[0].width
    s = Image.new("RGBA", (cell * len(cells), cell), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        s.alpha_composite(c, (i * cell, 0))
    return s


def preview_gif(cells: list[Image.Image], path: Path, fps: int, scale: int = 2,
                bg=(42, 42, 53), durations: list[int] | None = None) -> None:
    """GIF để xem nhanh trên Mac (Quick Look). Nền đặc — chỉ để xem, không đưa vào game."""
    frames = []
    for c in cells:
        b = Image.new("RGBA", c.size, bg + (255,))
        b.alpha_composite(c)
        frames.append(b.convert("RGB").resize((c.width * scale, c.height * scale),
                                              Image.NEAREST))
    base = 1000 / max(1, fps)
    dur = [max(20, round(base * d)) for d in (durations or [1] * len(frames))]
    frames[0].save(path, save_all=True, append_images=frames[1:], loop=0,
                   duration=dur, disposal=2)


def process(src: Path, out: Path, name: str, cfg: dict) -> dict:
    """Toàn bộ hậu kỳ cho một biến thể. `cfg` dùng đúng các khoá của manifest anim."""
    frames = load_frames(src)
    loop = bool(cfg.get("loop"))
    keep = select(len(frames), loop=loop, count=int(cfg.get("count", 0)),
                  step=int(cfg.get("step", 1)), start=int(cfg.get("trim_start", 0)),
                  end=int(cfg.get("trim_end", 0)))
    if not keep:
        raise SystemExit(f"{src}: không còn frame nào sau khi cắt/chọn")
    vfx = None
    if cfg.get("vfx_key") == "luma":
        raw_dir = src.parent / "raw"
        if not raw_dir.is_dir():
            raise SystemExit(f"vfx_key=luma cần frame gốc ở {raw_dir}")
        frames, _ = key_black(frames, load_frames(raw_dir), use_char=False)
        rest0 = frames[0]
    elif cfg.get("vfx_key") == "black":
        raw_dir = src.parent / "raw"
        if not raw_dir.is_dir():
            raise SystemExit(f"vfx_key=black cần frame gốc ở {raw_dir}")
        rest0 = frames[0]                       # khung chuẩn lấy từ mask nhân vật, trước khi gộp
        frames, vfx = key_black(frames, load_frames(raw_dir))
    else:
        rest0 = frames[0]
    chosen = [frames[i] for i in keep]
    # Hiệu ứng thuần: rìa sáng mờ (alpha thấp) VẪN là hình — khung theo ngưỡng đặc sẽ cắt cụt
    # quầng sáng. Nhân vật thì ngược lại: viền mờ của matte không được làm phình khung.
    box = union_bbox(chosen, 16 if cfg.get("vfx_key") == "luma" else ALPHA_SOLID)
    if box is None:
        raise SystemExit(f"{src}: mọi frame đều trong suốt — matte hỏng hoặc sai thư mục")

    cell, pad = int(cfg.get("cell", 128)), int(cfg.get("pad", 4))
    framing = cfg.get("framing", "rest")
    rest = union_bbox([rest0]) if framing == "rest" else None
    fill = float(cfg.get("fill", 0.8))
    if rest is not None:
        box = rest
        cells = fit_rest(chosen, rest, cell, pad, fill)
        vcells = fit_rest([vfx[i] for i in keep], rest, cell, pad, fill) if vfx else None
    else:  # "union": ô vừa khít riêng clip này — chỉ dùng khi clip không cần khớp clip khác
        cells = fit_cells(chosen, box, cell, pad)
        vcells = fit_cells([vfx[i] for i in keep], box, cell, pad) if vfx else None
    if int(cfg.get("sharpen", 0)):
        cells = sharpen(cells, int(cfg["sharpen"]))
    if int(cfg.get("colors", 0)):
        cells = palette_lock(cells, int(cfg["colors"]))
    if int(cfg.get("alpha_threshold", 0)):
        cells = harden_alpha(cells, int(cfg["alpha_threshold"]))

    out.mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(exist_ok=True)
    for i, c in enumerate(cells):
        c.save(out / "frames" / f"{name}_{i:02d}.png")
    strip(cells).save(out / f"{name}_sheet.png")
    if vcells:
        strip(vcells).save(out / f"{name}_vfx_sheet.png")
    fps = int(cfg.get("fps", 10))
    # Giữ lâu ở đỉnh động tác: đòn đánh có lực nhờ khoảnh khắc "đứng lại" ở điểm ra đòn,
    # không phải nhờ thêm frame. Ghi thành thời lượng từng frame, không nhân bản ảnh.
    durations = [1] * len(cells)
    hold = int(cfg.get("hold_extreme", 0))
    peak = extreme_index(cells) if hold > 1 else None
    if peak is not None:
        durations[peak] = hold
    preview_gif(cells, out / f"{name}_preview.gif", fps, durations=durations)

    meta = {
        "name": name, "cell": cell, "count": len(cells), "fps": fps, "loop": loop,
        "layout": "horizontal_strip", "pivot": [0.5, 0.0],
        "source_frames": len(frames), "kept_indices": keep,
        "framing": "rest" if rest is not None else "union",
        "crop_box": list(box), "durations": durations, "peak_frame": peak,
        "vfx_layer": f"{name}_vfx_sheet.png" if vcells else None,
        "metrics": {**metrics(cells, loop, vfx=bool(vcells)), "edge_flicker": edge_flicker(cells)},
    }
    (out / f"{name}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    return meta


def review_sheet(strips: list[tuple[str, Path]], dest: Path, max_cell: int = 96) -> None:
    """Mỗi biến thể một hàng, để chọn bằng mắt. Nhãn = tên biến thể."""
    rows = [(label, Image.open(p).convert("RGBA")) for label, p in strips if p.exists()]
    if not rows:
        return
    label_w = 120
    cell = min(max_cell, rows[0][1].height)
    scaled = [(lab, im.resize((max(1, im.width * cell // im.height), cell), Image.LANCZOS))
              for lab, im in rows]
    w = label_w + max(im.width for _, im in scaled)
    sheet = Image.new("RGBA", (w, cell * len(scaled)), (30, 30, 40, 255))
    draw = ImageDraw.Draw(sheet)
    for r, (lab, im) in enumerate(scaled):
        y = r * cell
        if r % 2:
            draw.rectangle([0, y, w, y + cell], fill=(38, 38, 50, 255))
        draw.text((6, y + cell // 2 - 6), lab, fill=(220, 225, 255))
        sheet.alpha_composite(im, (label_w, y))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="chuỗi frame RGBA -> spritesheet + số đo")
    ap.add_argument("src", type=Path, help="thư mục PNG RGBA (vd .../s1000/rgba)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--name", default="anim")
    ap.add_argument("--cell", type=int, default=128)
    ap.add_argument("--pad", type=int, default=4)
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--count", type=int, default=0, help="số frame giữ lại, chia đều")
    ap.add_argument("--step", type=int, default=1, help="lấy 1 trong mỗi N frame")
    ap.add_argument("--trim-start", type=int, default=0)
    ap.add_argument("--trim-end", type=int, default=0)
    ap.add_argument("--colors", type=int, default=0, help="khoá bảng màu chung (0 = tắt)")
    ap.add_argument("--alpha-threshold", type=int, default=0, help="alpha nhị phân (0 = tắt)")
    a = ap.parse_args()
    meta = process(a.src, a.out, a.name, {
        "cell": a.cell, "pad": a.pad, "fps": a.fps, "loop": a.loop, "count": a.count,
        "step": a.step, "trim_start": a.trim_start, "trim_end": a.trim_end,
        "colors": a.colors, "alpha_threshold": a.alpha_threshold})
    m = meta["metrics"]
    print(f"{meta['count']} frame · iou_min {m['iou_min']} · drift_x {m['drift_x']} · "
          f"color_drift {m['color_drift']}" + (f" · loop_iou {m['loop_iou']}" if "loop_iou" in m else ""))
    for f in m["flags"]:
        print(f"  ! {f}")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
