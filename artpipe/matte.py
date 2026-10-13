"""Turn a generated image on a flat backdrop into a normalised RGBA icon.

Mechanism only — knows nothing about SKYBORNE or any palette. Two steps:

  cutout()    flood-fill the flat backdrop away from the canvas border, then despill
  normalise() crop to the subject, scale it inside the safe area, centre on the canvas

The second step exists because a generator frames its subject however it likes. Without
it, `safe_margin` and `silhouette_coverage` would be measuring the generator's framing
instead of the artwork, and would swing wildly between two otherwise identical icons.

No ML model, no download. The backdrop is flat because the prompt orders it flat, so a
deterministic fill is both sufficient and auditable — a model would only add a dependency
and a source of non-reproducibility.
"""

from __future__ import annotations

from collections import deque

import numpy as np
from PIL import Image


class MatteError(RuntimeError):
    pass


def _srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """rgb uint8 (..., 3) -> CIE L*a*b* float (..., 3), D65."""
    v = rgb.astype(np.float64) / 255.0
    lin = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805],
                  [0.2126, 0.7152, 0.0722],
                  [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.00000, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    return np.stack([116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)], axis=-1)


def cutout(img: Image.Image, tolerance: float = 14.0, despill: bool = True) -> Image.Image:
    """Remove the flat backdrop, returning RGBA with a hard alpha.

    The key colour is the median of the canvas border rather than a constant, so the same
    code works whatever backdrop colour the prompt asked for, and tolerates the mild
    banding a generator leaves in a nominally flat fill.

    Enclosed pockets of key colour are removed too, not only backdrop connected to the
    border. The earlier rule kept them, reasoning that a pocket is more likely intentional
    artwork than a hole. That reasoning is wrong *for this pipeline*: the backdrop is chosen
    to maximise its minimum ΔE to the palette (59.4, ~5× the conformance tolerance), so a
    pixel within `tolerance` of the key colour cannot be legal artwork by construction.

    It also broke two of the five subtypes the art direction specifies: AoE is concentric
    rings and Orbit is orbs on an orbit path, and both enclose backdrop. Under the old rule
    those holes came back as opaque backdrop-coloured body, which then failed
    palette_conformance — the pipeline rejecting shapes its own §6 requires.
    """
    rgb = np.array(img.convert("RGB"))
    h, w, _ = rgb.shape

    border = np.concatenate([rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]]).reshape(-1, 3)
    key = np.median(border, axis=0)

    lab = _srgb_to_lab(rgb)
    key_lab = _srgb_to_lab(key.round().astype(np.uint8).reshape(1, 3))[0]

    # Dung sai đo từ chính tấm ảnh, không phải hằng số.
    #
    # `tolerance` mặc định giả định nền thật sự phẳng. Máy sinh yếu thì vẽ nền có vân và
    # chuyển sắc: đo trên mẻ thật, ΔE của viền canvas tới màu khoá vượt xa 14, nên flood
    # fill dừng sớm và để lại nguyên mảng nền — nhìn ra như "tách nền hỏng" chứ không ai
    # đoán được nguyên nhân là một con số cứng.
    #
    # Lấy phân vị 98 của ΔE trên viền: viền theo định nghĩa LÀ nền, nên nó nói đúng nền
    # dao động bao nhiêu. Chặn trên bằng nửa khoảng cách ΔE tới màu gần nhất của bảng màu
    # (59.4 → 29.7) để dung sai nới ra vẫn không bao giờ với tới màu hợp lệ của icon.
    border_de = np.linalg.norm(_srgb_to_lab(border) - key_lab, axis=-1)
    measured = float(np.percentile(border_de, 98))
    tolerance = float(min(max(tolerance, measured * 1.2), 28.0))

    near = np.linalg.norm(lab - key_lab, axis=-1) <= tolerance

    if not near[0, :].any() and not near[-1, :].any() \
            and not near[:, 0].any() and not near[:, -1].any():
        raise MatteError(
            "no backdrop found at the canvas border — the image is not a subject on a "
            "flat field, so there is nothing safe to cut away"
        )

    # Flood fill inward from every border pixel that matches the key.
    bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for y, x in [*((0, x) for x in range(w)), *((h - 1, x) for x in range(w)),
                 *((y, 0) for y in range(h)), *((y, w - 1) for y in range(h))]:
        if near[y, x] and not bg[y, x]:
            bg[y, x] = True
            q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))

    # Pockets: key-coloured pixels the flood fill could not reach. Cut them as well, for the
    # reason in the docstring — but only pixels that match the key, never "everything inside
    # a ring", so an intentionally filled centre survives.
    pockets = near & ~bg
    bg = bg | pockets

    bg = _flood_to_outline(bg, lab, tolerance)

    if bg.all():
        raise MatteError("the whole canvas matched the backdrop — no subject to keep")

    out = np.dstack([rgb, np.where(bg, 0, 255).astype(np.uint8)])

    if despill:
        # Antialiased edge pixels are a blend of subject and backdrop; left alone they
        # ring the icon in backdrop colour, which reads as a second outline and would
        # corrupt palette conformance. Pull opaque pixels that still sit close to the key
        # back toward their nearest non-key neighbour.
        edge = (~bg) & _dilate(bg)
        if edge.any():
            ys, xs = np.nonzero(edge)
            d = np.linalg.norm(lab[ys, xs] - key_lab, axis=-1)
            contaminated = d <= tolerance * 2.5
            out[ys[contaminated], xs[contaminated], 3] = 0

    out[..., 3] = _keep_subject(out[..., 3] > 0)
    if not (out[..., 3] > 0).any():
        raise MatteError("không còn mảnh nào sau khi dọn — ảnh không có chủ thể ở giữa")
    return Image.fromarray(out, "RGBA")


def _flood_to_outline(bg: np.ndarray, lab: np.ndarray, tolerance: float,
                      dark_lstar: float = 35.0) -> np.ndarray:
    """Nới vùng nền ra tới tận VIỀN TỐI của chủ thể, không dừng ở ranh giới màu.

    Đây là chỗ chữa hai lời phàn nàn thật: nền còn sót thành quầng màu quanh chủ thể, và
    mép icon bị lem. Keying theo màu chỉ cắt được pixel *đủ giống* màu nền; phần nền chuyển
    dần sang chủ thể thì không giống nữa, nên nó ở lại, rồi bước ép phong cách sơn nó thành
    một màu hợp lệ — quầng tím quanh mấy lọ thuốc chính là thứ đó.

    Luật thay thế đọc thẳng từ art-direction: **mọi hình đều có viền tối bao quanh**. Vậy
    thì mọi thứ đi được từ mép canvas vào mà chưa chạm viền tối đều là nền, bất kể nó màu gì.
    Quầng chuyển sắc nằm ngoài viền nên bị cắt sạch; ruột icon nằm trong viền nên an toàn.

    Rủi ro của luật này là viền hở: chỉ cần một khe là vùng nền tràn vào trong và ăn mất
    ruột. Vì vậy kết quả bị BÁC BỎ khi nó ăn quá nhiều — lúc đó giữ nguyên kết quả keying
    theo màu, tức là tệ hơn nhưng không hỏng.
    """
    h, w = bg.shape
    dark = lab[..., 0] <= dark_lstar          # viền tối, và cũng là mọi mảng rất tối
    passable = ~dark

    grown = bg.copy()
    seeds = grown & passable
    if not seeds.any():
        return bg

    # Lan bằng phép giãn nở có chặn, vector hoá — cùng lý do tốc độ như ở `_keep_subject`.
    while True:
        prev = grown
        d = _dilate(grown) & passable
        grown = grown | d
        if np.array_equal(grown, prev):
            break

    # Trả lại một vòng pixel sát viền tối.
    #
    # Mép viền bị khử răng cưa là pha trộn giữa viền và nền, nên nó KHÔNG tối và vùng nền
    # lan được vào đó — ăn mòn viền từ ngoài vào, và icon vẽ đúng chuẩn cũng trượt
    # outline_present. Đối chứng dương của selftest bắt được đúng chuyện này.
    gained = grown & ~bg
    grown = bg | (gained & ~_dilate(dark))

    before = float((~bg).sum())
    after = float((~grown).sum())
    if before <= 0 or after / before < 0.5:
        # Ăn quá nửa chủ thể: gần như chắc chắn viền hở và vùng nền đã tràn vào trong.
        return bg
    return grown


def _keep_subject(mask: np.ndarray) -> np.ndarray:
    """Bỏ những mảnh không phải chủ thể, trả về kênh alpha đã dọn.

    Hai loại rác sau khi keying, cả hai đều thấy được trên mẻ thật:
    mảng nền còn sót vì nền không phẳng, và đốm lấm tấm do vân của máy sinh.

    Luật bỏ chọn theo đúng những gì art-direction đã quy định, không phải theo cảm tính:

    * **Chạm mép canvas** → bỏ. Direction bắt chủ thể nằm gọn trong lề an toàn, nên một
      mảnh dính mép canvas không thể là chủ thể; nó là nền chưa cắt hết.
    * **Nhỏ hơn 0.5% mảnh lớn nhất** → bỏ. Ngưỡng cố ý đặt rất thấp: subtype Orbit là các
      quả cầu RỜI nhau và AoE là vòng tròn đồng tâm, chúng phải sống sót. Một quả cầu orbit
      chiếm cỡ vài phần trăm chủ thể, còn đốm nhiễu thì dưới một phần nghìn.

    Đây chính là chỗ bản trước đã sai một lần theo hướng ngược lại (xem docstring của
    `cutout`): luật dọn quá tay sẽ xoá đúng những hình mà §6 yêu cầu.
    """
    h, w = mask.shape
    if not mask.any():
        return np.zeros((h, w), dtype=np.uint8)

    # Gán nhãn bằng lan truyền cực tiểu, không phải BFS từng pixel: bản BFS thuần Python
    # chạy đúng nhưng mất hàng phút cho mỗi ảnh 512², tức là bước dọn còn đắt hơn cả sinh
    # ảnh. Mỗi vòng ở đây là vài phép numpy trên cả mảng, số vòng bằng đường kính mảnh.
    INF = h * w
    lab = np.where(mask, np.arange(h * w, dtype=np.int64).reshape(h, w), INF)
    while True:
        prev = lab
        m = lab.copy()
        m[1:, :] = np.minimum(m[1:, :], lab[:-1, :])
        m[:-1, :] = np.minimum(m[:-1, :], lab[1:, :])
        m[:, 1:] = np.minimum(m[:, 1:], lab[:, :-1])
        m[:, :-1] = np.minimum(m[:, :-1], lab[:, 1:])
        lab = np.where(mask, m, INF)

        # Nhảy con trỏ: mỗi pixel nhảy thẳng tới nhãn của pixel mà nó đang trỏ vào, nên
        # tầm lan toả BÌNH PHƯƠNG sau mỗi vòng thay vì chỉ nhích một pixel. Không có bước
        # này thì số vòng bằng đường kính mảnh (~500 với ảnh 512²) và selftest chạy hàng
        # chục phút — đã đo.
        flat = lab.reshape(-1).copy()
        lab = np.where(mask, flat[np.where(mask, lab, 0)], INF)

        if np.array_equal(lab, prev):
            break

    ids, inverse, sizes = np.unique(lab[mask], return_inverse=True, return_counts=True)
    biggest = int(np.argmax(sizes))
    floor = sizes[biggest] * 0.005

    border = np.zeros((h, w), dtype=bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    touching = np.unique(lab[mask & border])

    keep = (sizes >= floor) & ~np.isin(ids, touching)
    keep[biggest] = True                   # chủ thể ở lại kể cả khi nó chạm mép

    out = np.zeros((h, w), dtype=np.uint8)
    out[mask] = np.where(keep[inverse], 255, 0)
    return out


def _dilate(mask: np.ndarray) -> np.ndarray:
    d = mask.copy()
    d[1:, :] |= mask[:-1, :]
    d[:-1, :] |= mask[1:, :]
    d[:, 1:] |= mask[:, :-1]
    d[:, :-1] |= mask[:, 1:]
    return d


def normalise(img: Image.Image, canvas: int, safe_margin_pct: float,
              fill_pct: float = 96.0) -> Image.Image:
    """Centre the subject on a square canvas, scaled to fill the safe area.

    `fill_pct` is how much of the safe box the subject's longest side spans. Slightly
    under 100 so that a hard-edged silhouette cannot land a stray pixel on the margin
    boundary and fail `safe_margin` on a rounding error.
    """
    if img.mode != "RGBA":
        raise MatteError("normalise expects RGBA — run cutout() first")

    alpha = np.array(img)[..., 3]
    ys, xs = np.nonzero(alpha > 16)
    if len(ys) == 0:
        raise MatteError("image is fully transparent — nothing to normalise")

    subject = img.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))

    safe = canvas * (1.0 - 2.0 * safe_margin_pct / 100.0)
    target = safe * fill_pct / 100.0
    scale = target / max(subject.width, subject.height)
    size = (max(1, round(subject.width * scale)), max(1, round(subject.height * scale)))
    subject = subject.resize(size, Image.LANCZOS)

    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    out.paste(subject, ((canvas - size[0]) // 2, (canvas - size[1]) // 2))
    return out
