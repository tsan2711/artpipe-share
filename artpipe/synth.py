"""Synthesise fixtures: one drawn to the spec, and degraded copies that look generated.

Why the degraded ones exist. A fixture drawn straight from the spec shares the spec's blind
spots — it is pixel-exact, axis-aligned and hard-edged, so it never exercises the path every
real image takes. That is precisely how the antialiasing bug in `palette_conformance` and
`value_step_count` survived a green suite: both checks were really measuring
perimeter-to-area ratio, and the spec-drawn fixture has almost no antialiased perimeter to
measure. `degrade()` puts the resampling, the noise and the off-centre framing back in.

Nothing here knows anything about SKYBORNE. Colours, sizes and the backdrop all come from
the spec, so the fixtures follow the art direction instead of pinning it in place.

The negative variants are the other half of the argument: a gate that passes everything and
a gate that works are indistinguishable until something that should fail, fails.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import matte
import spec as spec_mod

# Fixed seed: a fixture that changes between runs turns a real regression into "probably
# just noise", and that doubt is worth more than the extra coverage a random seed buys.
SEED = 0x5EED


def _role_values(art: dict, role: str) -> tuple[tuple, tuple, tuple]:
    """(main, core, shadow) for a palette role.

    `neutral` is shaped differently in the spec — light/mid/dark instead of
    main/core/shadow — because it is not an element. Mapped here rather than reshaped in
    the spec: modifiers are defined by having no element (§6b), and giving neutral an
    element's field names would blur exactly that distinction.
    """
    pal = art["palette"]
    if role == "neutral":
        n = pal["neutral"]
        return (spec_mod.hex_to_rgb(n["mid"]), spec_mod.hex_to_rgb(n["light"]),
                spec_mod.hex_to_rgb(n["dark"]))
    entry = pal[role]
    return (spec_mod.hex_to_rgb(entry["main"]), spec_mod.hex_to_rgb(entry["core"]),
            spec_mod.hex_to_rgb(entry["shadow"]))


def _scale(points, factor, cx, cy):
    return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in points]


def draw_icon(art: dict, *, role: str = "fire", size: int | None = None,
              outline: bool = True, gradient: bool = False,
              subtype: str = "Projectile") -> Image.Image:
    """Colour axis = `role`, shape axis = `subtype`.

    `outline=False` and `gradient=True` produce deliberate violations of §5 — they exist so
    the suite can prove the outline and value-step checks actually reject something.

    The non-Projectile shapes exist for one reason: tier 2 claims to read the shape axis,
    and that claim cannot be tested with a single shape. A model that silently classifies
    by colour alone would score perfectly on a one-shape fixture set.
    """
    if subtype != "Projectile":
        return _draw_subtype(art, role, size or art["icon"]["canvas"]["width"], subtype)
    size = size or art["icon"]["canvas"]["width"]
    outline_rgb = spec_mod.hex_to_rgb(art["palette"]["outline"])
    main, core, shadow = _role_values(art, role)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2

    # Dart pointing up-right, with a short tail — the Projectile silhouette.
    #
    # The first version of this polygon was two offset quadrilaterals, which reads as a
    # zig-zag, i.e. as the Bounce subtype. Tier 1 scored it 8/8 the whole time, because no
    # pixel statistic can tell a dart from a zig-zag. Tier 2 named it Bounce at 94%, which
    # is what a player would have said too. Barbed arrowhead + tapered tail now.
    # Kept inside [0.14, 0.86] so the stroked outline still clears the 8% safe margin —
    # this fixture is drawn straight to canvas, with no normalise pass to rescue it.
    body = [
        (0.86, 0.14),   # tip
        (0.81, 0.43),   # right barb, outer
        (0.64, 0.36),   # notch back into the shaft
        (0.31, 0.76),   # shaft, lower-right edge
        (0.16, 0.86),   # tail end
        (0.26, 0.71),   # shaft, upper-left edge
        (0.59, 0.31),   # notch
        (0.53, 0.17),   # left barb
    ]
    body = [(x * size, y * size) for x, y in body]

    # Stroke the edges rather than scaling the polygon up: uniform scaling thins the
    # apparent stroke wherever the shape is narrow, which the spec forbids (style: uniform).
    w = round(art["shading"]["outline"]["width_px_at_512"] * size / 512)
    d.polygon(body, fill=(main if outline else main) + (255,))
    if outline:
        d.line(body + [body[0]], fill=outline_rgb + (255,), width=2 * w, joint="curve")
        for x, y in body:                        # round off the joins the stroke leaves open
            d.ellipse([x - w, y - w, x + w, y + w], fill=outline_rgb + (255,))
        d.polygon(_scale(body, 1 - (2 * w) / (size * 0.62), c, c), fill=main + (255,))

    if gradient:
        # A smooth vertical ramp across the body: no flat fields, no countable steps —
        # exactly the painterly shading §5 forbids.
        ramp = Image.new("RGBA", (size, size))
        rd = ImageDraw.Draw(ramp)
        for y in range(size):
            t = y / (size - 1)
            rd.line([(0, y), (size, y)],
                    fill=tuple(round(core[i] * (1 - t) + shadow[i] * t) for i in range(3)) + (255,))
        img.paste(ramp, (0, 0), Image.fromarray(
            (np.array(img)[..., 3] * (0.85 if outline else 1.0)).astype(np.uint8), "L"))
        return img

    # Two more value steps: lit facet and shadow facet, both inside the body.
    d.polygon(_scale([body[0], body[1], body[2], body[7]], 0.94, c, c), fill=core + (255,))
    d.polygon(_scale([body[3], body[4], body[5], body[6]], 0.94, c, c), fill=shadow + (255,))
    return img


def _draw_subtype(art: dict, role: str, size: int, subtype: str) -> Image.Image:
    """Crude but unambiguous renderings of the other four subtypes in §6.

    Deliberately plain: these are test instruments, not art. What matters is that a human
    reading them at 64px would name the right subtype — if a fixture is ambiguous to us,
    a low CLIP score on it says nothing about CLIP.
    """
    outline_rgb = spec_mod.hex_to_rgb(art["palette"]["outline"]) + (255,)
    _m, _c, _s = _role_values(art, role)
    main, core, shadow = _m + (255,), _c + (255,), _s + (255,)
    w = max(2, round(art["shading"]["outline"]["width_px_at_512"] * size / 512))

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = lambda f: f * size  # noqa: E731 — fraction of canvas, used constantly below

    if subtype == "AoE":
        # Concentric rings spreading from the centre.
        for i, (r, fill) in enumerate([(0.46, shadow), (0.32, main), (0.16, core)]):
            box = [s(0.5 - r), s(0.5 - r), s(0.5 + r), s(0.5 + r)]
            d.ellipse(box, fill=None if i < 2 else fill,
                      outline=outline_rgb, width=w)
            inner = [v + (w * 1.5 if j < 2 else -w * 1.5) for j, v in enumerate(box)]
            d.ellipse(inner, fill=fill, outline=None) if i == 2 else d.arc(
                box, 0, 360, fill=fill, width=max(2, w))
    elif subtype == "Orbit":
        # Three small orbs on an ellipse.
        d.ellipse([s(0.10), s(0.30), s(0.90), s(0.70)], outline=outline_rgb, width=w)
        for cx, cy, fill in [(0.16, 0.50, main), (0.50, 0.31, core), (0.84, 0.50, shadow)]:
            r = 0.11
            box = [s(cx - r), s(cy - r), s(cx + r), s(cy + r)]
            d.ellipse(box, fill=fill, outline=outline_rgb, width=w)
    elif subtype == "Beam":
        # A straight taper running lower-left to upper-right.
        beam = [(0.10, 0.86), (0.24, 0.90), (0.90, 0.18), (0.84, 0.10)]
        pts = [(s(x), s(y)) for x, y in beam]
        d.polygon(pts, fill=main)
        d.line(pts + [pts[0]], fill=outline_rgb, width=w, joint="curve")
        d.polygon([(s(0.20), s(0.82)), (s(0.26), s(0.84)),
                   (s(0.82), s(0.20)), (s(0.78), s(0.16))], fill=core)
    elif subtype == "Bounce":
        # A zig-zag polyline linking three points.
        zig = [(0.12, 0.74), (0.38, 0.26), (0.62, 0.74), (0.88, 0.26)]
        pts = [(s(x), s(y)) for x, y in zig]
        d.line(pts, fill=outline_rgb, width=round(w * 4.5), joint="curve")
        d.line(pts, fill=main, width=round(w * 2.5), joint="curve")
        for x, y in pts:
            r = w * 1.6
            d.ellipse([x - r, y - r, x + r, y + r], fill=core, outline=outline_rgb, width=w)
    else:
        raise ValueError(f"subtype chưa có hình mẫu: {subtype!r}")
    return img


def degrade(icon: Image.Image, art: dict, *, seed: int = SEED,
            out_size: int = 1024, subject_pct: float = 0.62,
            angle: float = 6.5, offset_pct: tuple[float, float] = (-0.07, 0.05),
            blur: float = 1.1, noise_sigma: float = 2.6) -> Image.Image:
    """Make a clean icon look like something a diffusion model returned.

    Four properties of real output, each of which a spec-drawn fixture lacks:
      resampled  — rotated and rescaled, so every edge is a blend of two colours
      off-centre — the generator frames the subject where it likes; normalise() must fix it
      soft       — a slight blur, since no generator returns a hard-edged vector shape
      noisy      — mild per-pixel noise, including across the "flat" backdrop

    Returns RGB on the spec's opaque backdrop, i.e. the exact thing `matte.cutout` is
    handed in production — not an RGBA icon.
    """
    rng = np.random.default_rng(seed)
    backdrop = spec_mod.hex_to_rgb(art["generation"]["backdrop_hex"])

    subject = icon.rotate(angle, resample=Image.BICUBIC, expand=True)
    side = max(1, round(out_size * subject_pct))
    subject = subject.resize((side, side), Image.LANCZOS)

    canvas = Image.new("RGB", (out_size, out_size), backdrop)
    ox = round((out_size - side) / 2 + offset_pct[0] * out_size)
    oy = round((out_size - side) / 2 + offset_pct[1] * out_size)
    canvas.paste(subject, (ox, oy), subject)

    if blur:
        canvas = canvas.filter(ImageFilter.GaussianBlur(blur))

    arr = np.asarray(canvas, dtype=np.float64)
    arr += rng.normal(0.0, noise_sigma, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def through_matte_chroma(raw: Image.Image, art: dict) -> Image.Image:
    """Ghim đường khoá màu, bất kể spec đang đặt gì.

    selftest dùng cái này: fixture của nó do `synth.draw_icon` + `synth.degrade` VẼ RA, và
    chúng vẽ sẵn nền phẳng đúng màu. Cho chúng đi qua model nhận dạng vừa sai bản chất
    (không có gì để "nhận dạng" ở một hình vẽ tổng hợp), vừa buộc cổng CI phải tải 176MB
    trọng số — biến cổng nhanh thành cổng chậm, đúng lý do tier 2 bị để ngoài.
    """
    return through_matte(raw, art, method="chroma")


def through_matte(raw: Image.Image, art: dict, method: str | None = None) -> Image.Image:
    """The production path: cut the backdrop away, then normalise onto the icon canvas."""
    if (method or art.get("generation", {}).get("matte_method")) == "segment":
        # Nhận dạng chủ thể thay cho khoá màu. `_require_backdrop` không áp dụng: không
        # còn nền phẳng nào được yêu cầu, và segment.cutout tự có hai cổng của riêng nó.
        import segment
        cut = segment.cutout(raw, model=art.get("generation", {}).get("segment_model", "u2net"))
    else:
        _require_backdrop(raw, art)
        cut = matte.cutout(raw)
    return matte.normalise(
        cut,
        canvas=art["icon"]["canvas"]["width"],
        safe_margin_pct=art["icon"]["safe_margin_pct"],
    )


def _require_backdrop(raw: Image.Image, art: dict, max_spread: float = 45.0) -> None:
    """Từ chối ngay khi máy sinh KHÔNG vẽ nền phẳng đúng màu đã yêu cầu.

    Máy sinh đôi khi vẽ nguyên một khung cảnh kín khung — nền gạch, tường, nét chì phủ kín.
    Lúc đó khâu tách nền vẫn chạy: nó lấy màu viền canvas làm màu khoá rồi cắt, và cái còn
    lại là một mớ nét tối phủ hết canvas. Kết quả là một "icon" hỏng nhưng vẫn đi tiếp qua
    mọi bước sau, và lỗi chỉ lộ ra ở tận điểm tương phản — đọc như icon quá tối chứ không
    ai thấy nguyên nhân là máy sinh bỏ qua lệnh nền.

    Đo bằng ĐỘ PHẲNG của viền canvas, không bằng việc nó có đúng màu hồng đã yêu cầu hay
    không. Đo trên 63 ảnh thật: độ lệch sắc so với `backdrop_hex` KHÔNG tách được hai nhóm
    (trung vị 47 ở nhóm tốt, 64-83 ở nhóm hỏng — chồng lên nhau), vì máy sinh hay vẽ hồng
    nhạt thay vì hồng gắt và đó vẫn là nền phẳng dùng được. Còn độ phẳng thì tách rõ:
    trung vị 18 ở nhóm tốt, 54-70 ở nhóm hỏng.
    """
    if not art.get("generation", {}).get("backdrop_hex"):
        return
    rgb = np.array(raw.convert("RGB"))
    border = np.concatenate([rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]]).reshape(-1, 3)
    lab = matte._srgb_to_lab(border)
    key = matte._srgb_to_lab(np.median(border, axis=0).round().astype(np.uint8).reshape(1, 3))[0]
    spread = float(np.percentile(np.linalg.norm(lab - key, axis=-1), 98))
    if spread > max_spread:
        raise matte.MatteError(
            f"viền canvas không phẳng (ΔE p98 = {spread:.0f}, cho phép {max_spread:.0f}) — "
            f"máy sinh vẽ cả khung cảnh chứ không phải chủ thể trên nền phẳng, nên không có "
            f"gì an toàn để cắt")


def off_palette(icon: Image.Image, art: dict) -> Image.Image:
    """Repaint the body a colour the closed palette has no entry for.

    Picked by search rather than hardcoded, so it stays illegal if the palette changes —
    a fixed "obviously wrong" hex could quietly become legal after a palette edit and turn
    this negative control into a silent pass.
    """
    from checks import to_lab

    pal = np.array([c for _, c in spec_mod.palette_colors(art)], dtype=np.uint8)
    lab_pal = to_lab(pal)
    grid = np.array([(r, g, b) for r in range(0, 256, 32)
                     for g in range(0, 256, 32) for b in range(0, 256, 32)], dtype=np.uint8)
    d = np.linalg.norm(to_lab(grid)[:, None, :] - lab_pal[None, :, :], axis=2).min(axis=1)
    worst = tuple(int(v) for v in grid[int(d.argmax())])

    arr = np.array(icon)
    # Leave the outline alone, so the fixture isolates one violation instead of tripping
    # the outline check as well and leaving it ambiguous which check did the rejecting.
    outline_lab = to_lab(np.array([spec_mod.hex_to_rgb(art["palette"]["outline"])], dtype=np.uint8))
    d_outline = np.linalg.norm(to_lab(arr[..., :3]) - outline_lab[0], axis=-1)
    body = (arr[..., 3] >= 128) & (d_outline > 20.0)
    arr[body, :3] = worst
    return Image.fromarray(arr, "RGBA")
