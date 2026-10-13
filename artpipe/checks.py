"""Tier-1 conformance checks: deterministic, pixel-only, no model or network.

Every check here is cheap and repeatable, so it runs first and rejects before anything
pays for a GPU or an API call. Each returns a Result rather than raising, because a
report listing four failures is more useful than an exception about the first one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from spec import hex_to_rgb, palette_colors


@dataclass
class Result:
    check_id: str
    passed: bool
    fatal: bool
    value: float | int | str
    detail: str


# ---------------------------------------------------------------- colour helpers


def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB uint8 (..., 3) -> CIE L*a*b* under D65."""
    lin = _srgb_to_linear(rgb.astype(np.float64))
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = lin @ m.T
    white = np.array([0.95047, 1.00000, 1.08883])
    t = xyz / white
    eps, kappa = 216 / 24389, 24389 / 27
    f = np.where(t > eps, np.cbrt(t), (kappa * t + 16) / 116)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], axis=-1)


def relative_luminance(rgb: np.ndarray) -> np.ndarray:
    lin = _srgb_to_linear(rgb.astype(np.float64))
    return lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    """Binary erosion with a square structuring element, numpy only."""
    out = mask.copy()
    for _ in range(radius):
        shifted = out.copy()
        shifted[1:, :] &= out[:-1, :]
        shifted[:-1, :] &= out[1:, :]
        shifted[:, 1:] &= out[:, :-1]
        shifted[:, :-1] &= out[:, 1:]
        shifted[0, :] = False
        shifted[-1, :] = False
        shifted[:, 0] = False
        shifted[:, -1] = False
        out = shifted
    return out


def _nearest_palette(img: np.ndarray, spec: dict) -> tuple[np.ndarray, np.ndarray]:
    """Chỉ số và khoảng cách ΔE tới màu bảng gần nhất, cho từng pixel.

    Duyệt từng màu trong bảng thay vì dựng nguyên khối (H, W, N, 3): bản khối cấp phát
    ~440MB float64 tạm cho ảnh 512² với 22 màu, và đo được nó ngốn hơn 5 giây mỗi lần gọi —
    trong khi bộ kiểm gọi nó nhiều lần cho mỗi ảnh. Vòng lặp 22 bước trên mảng (H, W)
    float32 cho cùng kết quả với vài chục MB.
    """
    lab_pal = to_lab(np.array([c for _, c in palette_colors(spec)], dtype=np.uint8))
    lab = to_lab(img[..., :3]).astype(np.float32)
    best_d = np.full(lab.shape[:2], np.inf, dtype=np.float32)
    best_i = np.zeros(lab.shape[:2], dtype=np.int32)
    for i, p in enumerate(lab_pal.astype(np.float32)):
        d = (lab[..., 0] - p[0]) ** 2 + (lab[..., 1] - p[1]) ** 2 + (lab[..., 2] - p[2]) ** 2
        closer = d < best_d
        best_d = np.where(closer, d, best_d)
        best_i = np.where(closer, i, best_i)
    return best_i, np.sqrt(best_d)


def _flat_field_interior(img: np.ndarray, spec: dict) -> np.ndarray:
    """Opaque pixels that sit inside a single flat colour field, not on a boundary.

    A pixel qualifies when it and its four neighbours are all opaque and all agree on
    which palette entry is nearest. Antialiasing lives exactly on the disagreements, so
    excluding them is what lets a check measure the artwork instead of the resampler.
    """
    opaque = img[..., 3] >= 128
    nearest, _ = _nearest_palette(img, spec)
    same = opaque.copy()
    same[1:, :] &= opaque[:-1, :] & (nearest[1:, :] == nearest[:-1, :])
    same[:-1, :] &= opaque[1:, :] & (nearest[:-1, :] == nearest[1:, :])
    same[:, 1:] &= opaque[:, :-1] & (nearest[:, 1:] == nearest[:, :-1])
    same[:, :-1] &= opaque[:, 1:] & (nearest[:, :-1] == nearest[:, 1:])
    same[[0, -1], :] = False
    same[:, [0, -1]] = False
    return same


# ---------------------------------------------------------------- the checks


def check_canvas_size(img: np.ndarray, spec: dict) -> Result:
    """Guard, not a style rule.

    Every threshold below is expressed in source-canvas pixels. Scoring a downscaled
    export against them fails quietly and wrongly — a 9px outline becomes 1px and the
    outline check reports "no outline" on an icon that has one. Refuse instead.
    """
    canvas = spec["icon"]["canvas"]
    want = (canvas["height"], canvas["width"])
    got = img.shape[:2]
    ok = got == want
    return Result(
        "canvas_size", ok, True, f"{got[1]}x{got[0]}",
        f"ảnh {got[1]}x{got[0]}, spec yêu cầu bản gốc {want[1]}x{want[0]} "
        "(ngưỡng tính theo pixel của bản gốc)" if not ok else f"{got[1]}x{got[0]}",
    )


def check_bg_transparent(img: np.ndarray, spec: dict) -> Result:
    h, w = img.shape[:2]
    ring = max(1, round(min(h, w) * 0.01))
    border = np.concatenate(
        [
            img[:ring, :, 3].ravel(),
            img[-ring:, :, 3].ravel(),
            img[:, :ring, 3].ravel(),
            img[:, -ring:, 3].ravel(),
        ]
    )
    ratio = float((border == 0).mean())
    ok = ratio >= 0.98
    return Result(
        "bg_transparent", ok, True, round(ratio, 4),
        f"{ratio:.1%} viền canvas trong suốt (cần ≥98%)",
    )


def check_safe_margin(img: np.ndarray, spec: dict) -> Result:
    pct = spec["icon"]["safe_margin_pct"] / 100.0
    h, w = img.shape[:2]
    my, mx = round(h * pct), round(w * pct)
    alpha = img[..., 3]
    band = alpha.copy()
    band[my : h - my, mx : w - mx] = 0
    intruding = int((band > 16).sum())
    ok = intruding == 0
    return Result(
        "safe_margin", ok, True, intruding,
        f"{intruding} pixel lấn vào lề {spec['icon']['safe_margin_pct']}%",
    )


def check_silhouette_coverage(img: np.ndarray, spec: dict) -> Result:
    lo, hi = spec["icon"]["silhouette_coverage_pct"]
    ratio = float((img[..., 3] >= 128).mean()) * 100
    ok = lo <= ratio <= hi
    return Result(
        "silhouette_coverage", ok, True, round(ratio, 2),
        f"chiếm {ratio:.1f}% canvas (cần {lo}–{hi}%)",
    )


def check_palette_conformance(img: np.ndarray, spec: dict) -> Result:
    """Score only the interior of each flat colour field, never the boundaries between them.

    Antialiasing blends two legal colours into an illegal one along every edge, so scoring
    all opaque pixels measures how much perimeter the icon has, not whether it obeys the
    palette. That penalty scales with the perimeter-to-area ratio, which means it punishes
    thin shapes — the exact shapes §5 already ruled legitimate. Measured on a conforming
    fixture, 100% of the "violations" were boundary pixels and none were interior.

    A pixel counts only if it and its four neighbours are opaque and agree on which palette
    entry is nearest. A genuinely off-palette region is still caught: agreement makes its
    interior eligible, and the large ΔE there fails it.
    """
    policy = spec["palette_policy"]
    tol = policy["delta_e_tolerance"]
    need = policy["min_conforming_pixel_ratio"]
    min_sample = policy.get("interior_min_sample_ratio", 0.15)
    # `fatal: false` = bảng màu chỉ để THAM KHẢO (preset vẽ tự do màu): trượt thì "xem tay", không loại.
    fatal = bool(policy.get("fatal", True))

    opaque = img[..., 3] >= 128
    if not opaque.any():
        return Result("palette_conformance", False, fatal, 0.0, "không có pixel đục")

    _, d_min = _nearest_palette(img, spec)
    same = _flat_field_interior(img, spec)
    share = float(same.sum()) / float(opaque.sum())
    if share < min_sample:
        return Result(
            "palette_conformance", False, fatal, round(share, 4),
            f"chỉ {share:.1%} pixel đục nằm trong lòng mảng màu (cần ≥{min_sample:.0%}) — "
            "hình quá vụn hoặc quá nhiều chuyển sắc để chấm bảng màu",
        )

    ratio = float((d_min[same] <= tol).mean())
    ok = ratio >= need
    return Result(
        "palette_conformance", ok, fatal, round(ratio, 4),
        f"{ratio:.1%} pixel trong lòng mảng màu nằm trong ΔE≤{tol} của bảng màu "
        f"(cần ≥{need:.0%}; chấm trên {share:.0%} pixel đục, bỏ pixel biên)",
    )


def check_value_steps(img: np.ndarray, spec: dict) -> Result:
    """How many flat values does it take to explain this icon?

    Scored on flat-field interiors only, for the same reason as the palette check: an
    antialiased boundary between two legal steps is itself a third luminance.

    Counting histogram bins — the obvious implementation, and the one that was here — turns
    out to measure where a colour sits relative to a bin edge. Measured: `outline` (L* 6.3)
    and `neutral.dark` (L* 15.3) straddle bins and the blend between them lights a third,
    so a legal 4-value neutral modifier reported 6 while a legal fire icon reported 4 purely
    because fire's values happen to land mid-bin.

    So the count is greedy peak coverage instead: take the heaviest luminance, absorb
    everything within ±`value_merge_delta_lstar` of it as the same step, repeat until
    `value_coverage_target` of the pixels are explained. That is the design rule stated
    literally — cel shading means a few flat values explain the whole icon — and it keeps
    the property that matters: a smooth ramp has no dominant plateau, so it needs many
    steps and still fails. Measured on fixtures: four legal icons all land at exactly 4,
    a gradient needs 6.
    """
    max_steps = spec["shading"]["max_distinct_values"]
    r = spec["readability"]
    merge = int(r["value_merge_delta_lstar"])
    target = float(r["value_coverage_target"])

    interior = _flat_field_interior(img, spec)
    scored = interior if interior.any() else (img[..., 3] >= 128)
    lstar = to_lab(img[..., :3][scored])[..., 0]
    hist, _ = np.histogram(lstar, bins=100, range=(0, 100))
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return Result("value_step_count", False, False, 0, "không có pixel nào để chấm")

    covered, steps = 0.0, 0
    while covered / total < target and hist.sum() > 0:
        peak = int(hist.argmax())
        lo, hi = max(0, peak - merge), min(len(hist), peak + merge + 1)
        covered += hist[lo:hi].sum()
        hist[lo:hi] = 0.0
        steps += 1
        if steps > max_steps * 4:          # far past failing; stop counting a ramp forever
            break

    ok = steps <= max_steps
    return Result(
        "value_step_count", ok, False, steps,
        f"cần {steps} mức phẳng để giải thích {target:.0%} icon (cho phép ≤{max_steps})",
    )


def check_outline(img: np.ndarray, spec: dict) -> Result:
    outline = spec["shading"]["outline"]
    if not outline.get("enabled", False):
        return Result("outline_present", True, False, "n/a", "spec không yêu cầu viền")

    src = spec["icon"]["canvas"]["width"]
    width = round(outline["width_px_at_512"] * img.shape[1] / src)
    width = max(2, width)
    dark_max = spec["readability"]["outline_dark_lstar_max"]
    need = spec["readability"]["outline_band_min_ratio"]

    mask = img[..., 3] >= 128
    band = mask & ~_erode(mask, width)
    if not band.any():
        return Result("outline_present", False, False, 0.0, "không tìm được dải viền")

    lstar = to_lab(img[..., :3][band])[..., 0]
    ratio = float((lstar <= dark_max).mean())
    ok = ratio >= need
    return Result(
        "outline_present", ok, False, round(ratio, 4),
        f"{ratio:.1%} dải viền {width}px là màu tối (cần ≥{need:.0%})",
    )


def check_readable_at_64(img: np.ndarray, spec: dict) -> Result:
    r = spec["readability"]
    size = spec["icon"]["readability_reference_size"]
    bg = np.array(hex_to_rgb(r["ui_background_reference"]), dtype=np.float64)

    small = np.asarray(
        Image.fromarray(img, "RGBA").resize((size, size), Image.LANCZOS), dtype=np.float64
    )
    a = (small[..., 3:4] / 255.0)
    composited = small[..., :3] * a + bg * (1 - a)

    solid = a[..., 0] >= 0.5
    if not solid.any():
        return Result("readable_at_64", False, True, 0.0, "icon biến mất ở 64px")

    # Phân vị, không phải trung bình.
    #
    # Viền tối dày là LUẬT của chính tài liệu này, và nó kéo trung bình độ sáng xuống ở mọi
    # icon đúng chuẩn — đo trên mẻ 63 ảnh thật, luật trung bình loại 50 ảnh mà phần lớn
    # nhìn bằng mắt vẫn đọc tốt ở 64px. Người nhận ra icon nhờ mảng sáng nhất đủ lớn của
    # nó, nên đó mới là thứ phải đem so với nền menu.
    pct = float(r.get("contrast_percentile", 90))
    l_fg = float(np.percentile(relative_luminance(composited[solid]), pct))
    l_bg = float(relative_luminance(bg))
    hi, lo = max(l_fg, l_bg), min(l_fg, l_bg)
    contrast = (hi + 0.05) / (lo + 0.05)

    gray = composited.mean(axis=2) / 255.0
    gy, gx = np.gradient(gray)
    edge_density = float(np.hypot(gx, gy).mean())

    ok_contrast = contrast >= r["min_contrast_ratio"]
    ok_edges = edge_density <= r["edge_density_max"]
    ok = ok_contrast and ok_edges
    why = []
    if not ok_contrast:
        why.append(f"tương phản {contrast:.1f}:1 < {r['min_contrast_ratio']}:1")
    if not ok_edges:
        why.append(f"nhiễu cạnh {edge_density:.3f} > {r['edge_density_max']}")
    return Result(
        "readable_at_64", ok, True, round(contrast, 2),
        "; ".join(why) if why else f"tương phản {contrast:.1f}:1, nhiễu cạnh {edge_density:.3f}",
    )


def check_modifier_neutral(img: np.ndarray, spec: dict) -> Result:
    """A modifier icon must be built from neutrals and the outline colour, nothing else.

    §6b makes the *absence* of an element colour the signal that a modifier belongs to no
    element. Nothing else in the suite can enforce that: a modifier painted in Fire red is
    perfectly legal to `palette_conformance` — red IS in the palette — and tier 2 does not
    ask a colourless asset about colour. So the one icon kind whose rule is about colour had
    no colour check at all.

    Phrased as "nearest palette entry must be neutral", not as a chroma threshold, so it
    inherits the palette instead of introducing a second, independently-driftable number.
    """
    policy = spec["palette_policy"]
    need = policy["min_conforming_pixel_ratio"]

    labels = [label for label, _ in palette_colors(spec)]
    allowed = {i for i, label in enumerate(labels)
               if label == "outline" or label.startswith("neutral.")}
    if not allowed:
        return Result("modifier_neutral", False, True, 0.0,
                      "spec không có mục neutral/outline nào để đối chiếu")

    interior = _flat_field_interior(img, spec)
    if not interior.any():
        return Result("modifier_neutral", False, True, 0.0,
                      "không đủ pixel trong lòng mảng màu để kết luận")

    nearest, _ = _nearest_palette(img, spec)
    picked = nearest[interior]
    ratio = float(np.isin(picked, list(allowed)).mean())
    ok = ratio >= need

    if ok:
        detail = f"{ratio:.1%} pixel trong lòng mảng là neutral/viền (cần ≥{need:.0%})"
    else:
        offenders = {labels[i]: int((picked == i).sum()) for i in np.unique(picked)
                     if i not in allowed}
        worst = sorted(offenders.items(), key=lambda kv: -kv[1])[:2]
        detail = (f"chỉ {ratio:.1%} là neutral/viền (cần ≥{need:.0%}) — modifier đang mang "
                  f"màu hệ: {', '.join(f'{k} {v} px' for k, v in worst)}")
    return Result("modifier_neutral", ok, True, round(ratio, 4), detail)


ALL = [
    check_canvas_size,
    check_bg_transparent,
    check_safe_margin,
    check_silhouette_coverage,
    check_palette_conformance,
    check_value_steps,
    check_outline,
    check_readable_at_64,
]

# Checks that only make sense for one kind of asset. Kept out of ALL so the generic path
# stays generic, and so `cli.py` can still score a loose folder of PNGs it knows nothing about.
BY_KIND = {
    "modifier": [check_modifier_neutral],
}


def run_all(png_path, spec: dict, kind: str | None = None) -> list[Result]:
    """Every generic check, plus the ones specific to `kind` when the caller knows it.

    `kind` is optional because two callers legitimately do not have it: `cli.py` scores an
    arbitrary folder, and the selftest fixtures are not tied to an authored asset.
    """
    img = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
    return [fn(img, spec) for fn in ALL + BY_KIND.get(kind or "", [])]
