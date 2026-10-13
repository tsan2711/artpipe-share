"""Ép ảnh đã tách nền về đúng phong cách cel của art-direction.

    from stylise import cel
    img = cel(img, spec)                     # PIL RGBA 512 -> PIL RGBA 512

## Tại sao có bước này

Ba luật của tầng 1 — đúng bảng màu, ≤N bậc sáng, có viền tối — là **ràng buộc xác định**,
không phải chuyện thẩm mỹ chủ quan. Mô hình khuếch tán không tuân theo chúng bằng chữ:
"exactly 3 value steps" trong prompt không ép được cái gì cả, và đo trên mẻ thật thì
sd-turbo trượt cả ba, trượt xa (43.9% đúng bảng màu, 8 bậc sáng, 33.4% viền tối).

Vậy nên đổi vai, giống hệt cách làn 3D đổi vai của Hunyuan: **máy sinh lo bố cục và hình
khối, pipeline lo luật phong cách.** Máy sinh giỏi việc "cái dart lửa trông thế nào",
kém việc "chỉ được dùng 4 mức sáng"; đoạn code này thì ngược lại.

## Hệ quả phải nói thẳng

Sau bước này, ba luật kia **đúng do dựng nên đúng**, không còn là phép kiểm độc lập. Tầng 1
từ chỗ chấm máy sinh trở thành chốt kiểm rằng bước ép phong cách chạy đúng — vẫn đáng giữ
(nó bắt được ép hỏng), nhưng đừng đọc "auto_accept" như bằng chứng máy sinh vẽ đẹp.
Việc đánh giá bố cục/ý nghĩa vẫn thuộc tầng 2 và mắt người.

Cái nó KHÔNG cứu được: hình sai ý (dart lửa ra hình cái nơ), bố cục lệch, chủ thể vụn.
Ép phong cách một bức vẽ hỏng chỉ ra một bức vẽ hỏng đúng bảng màu.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from checks import _erode, to_lab
from spec import palette_colors


def _snap(rgb: np.ndarray, opaque: np.ndarray, pal_rgb: np.ndarray,
          pal_lab: np.ndarray) -> np.ndarray:
    """Chỉ số màu bảng gần nhất cho từng pixel đục, đo bằng ΔE trong Lab.

    Duyệt từng màu bảng chứ không dựng khối (H, W, N, 3) — xem ghi chú ở
    `checks._nearest_palette`: bản khối tốn hàng trăm MB tạm và hàng giây mỗi lần gọi.
    """
    lab = to_lab(rgb).astype(np.float32)
    best_d = np.full(lab.shape[:2], np.inf, dtype=np.float32)
    idx = np.zeros(lab.shape[:2], dtype=np.int32)
    for i, p in enumerate(pal_lab.astype(np.float32)):
        d = (lab[..., 0] - p[0]) ** 2 + (lab[..., 1] - p[1]) ** 2 + (lab[..., 2] - p[2]) ** 2
        closer = d < best_d
        best_d = np.where(closer, d, best_d)
        idx = np.where(closer, i, idx)
    idx[~opaque] = -1
    return idx


def _family(names_cols, rgb, opaque, kind: str, element: str | None) -> str:
    """Chọn HỌ MÀU cho icon: 'fire', 'frost', 'neutral', ...

    Biết trước thì dùng cái biết: spell có element trong dữ liệu Unity, modifier bắt buộc
    trung tính theo §6b. Chỉ item mới phải đoán, vì §7 cho item tự do màu ("chất lỏng phát
    sáng", "ánh kim") — đoán bằng sắc độ trung bình của chủ thể, ít sắc thì về trung tính.
    """
    fams = sorted({n.split(".")[0] for n, _ in names_cols if "." in n})
    if kind == "modifier":
        return "neutral"
    if element:
        e = element.strip().lower()
        if e in fams:
            return e
    lab = to_lab(rgb[opaque]).astype(np.float32)
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    if float(np.percentile(chroma, 90)) < 18.0:
        return "neutral"
    # Chỉ nhìn phần RỰC MÀU nhất, không lấy trung bình toàn chủ thể: một lọ thuốc là cái
    # chai trắng xám to bao quanh vũng nước xanh lá nhỏ, nên trung bình bị màu chai kéo về
    # gần trung tính rồi chọn nhầm họ — lọ xanh lá ra thành xanh lam. Phần mang màu mới là
    # phần nói icon này thuộc họ nào.
    vivid = lab[chroma >= np.percentile(chroma, 75)]
    mean_ab = vivid[:, 1:].mean(axis=0)
    best, best_d = "neutral", float("inf")
    for f in fams:
        main = [c for n, c in names_cols if n == f + ".main"]
        if not main:
            continue
        p = to_lab(np.array(main, dtype=np.uint8))[0]
        d = float(np.hypot(p[1] - mean_ab[0], p[2] - mean_ab[1]))
        if d < best_d:
            best, best_d = f, d
    return best


def _ramp(names_cols, family: str) -> np.ndarray:
    """Ba bậc tối → sáng của một họ màu, theo đúng thứ tự L* thật chứ không theo tên."""
    cols = [c for n, c in names_cols if n.startswith(family + ".")]
    if len(cols) < 2:
        cols = [c for n, c in names_cols if n.startswith("neutral.")]
    arr = np.array(cols, dtype=np.uint8)
    return arr[np.argsort(to_lab(arr)[:, 0])]


def _map_to_ramp(rgb: np.ndarray, opaque: np.ndarray, ramp: np.ndarray,
                 cuts=(0.30, 0.72)) -> np.ndarray:
    """Ánh xạ theo BẬC SÁNG, không phải theo màu gần nhất.

    Đây là chỗ sửa lỗi "ảnh gốc đẹp mà ảnh cuối xấu". Snap theo màu gần nhất trộn lẫn hai
    thứ khác nhau — sắc và độ sáng — nên một icon vẽ tông nâu-be (không có trong bảng màu)
    bị kéo hết về mấy màu trung tính TỐI, và icon thành một khối đen đọc không ra.

    Ánh xạ theo phân vị độ sáng giữ nguyên cấu trúc sáng-tối mà máy sinh vẽ ra, chỉ thay
    bảng màu. Vì bậc sáng nhất luôn được cấp phát nên icon chắc chắn có mảng sáng — đó
    cũng chính là thứ `readable_at_64` đo.
    """
    lab = to_lab(rgb).astype(np.float32)
    lstar = _smooth_lstar(lab[..., 0])
    vals = lstar[opaque]
    if vals.size == 0:
        return rgb
    edges = [float(np.quantile(vals, c)) for c in cuts[:len(ramp) - 1]]

    out = rgb.copy()
    band = np.zeros(lstar.shape, dtype=np.int32)
    for e in edges:
        band += (lstar > e).astype(np.int32)
    band = _despeckle(band, opaque, len(ramp))
    for i, col in enumerate(ramp):
        out[opaque & (band == i)] = col
    return out


def _smooth_lstar(lstar: np.ndarray, size: int = 9) -> np.ndarray:
    """Lọc trung vị độ sáng TRƯỚC khi chia bậc.

    Vân sơn dầu của SDXL tạo những mảng loang to hơn cửa sổ bỏ phiếu, nên `_despeckle`
    một mình không xoá được — đo trên thỏi kim loại: bán kính 2 và 5 đều còn vệt, chỉ khi
    làm mượt độ sáng trước thì mặt phẳng mới sạch. Trung vị (không phải trung bình) vì nó
    giữ nguyên bậc nhảy ở biên hai mảng, đúng thứ cel-shading cần.

    Chỉ đụng vào ĐỘ SÁNG, không đụng vào sắc: sắc do bảng màu quyết, và làm mượt RGB sẽ
    tạo dải chuyển sắc — thứ §4 cấm.
    """
    from PIL import ImageFilter
    img = Image.fromarray(np.clip(lstar * 2.55, 0, 255).astype(np.uint8))
    return np.array(img.filter(ImageFilter.MedianFilter(size)), dtype=np.float32) / 2.55


def _despeckle(band: np.ndarray, opaque: np.ndarray, levels: int,
               radius: int = 5) -> np.ndarray:
    """Bỏ phiếu đa số trong cửa sổ (2r+1)² cho NHÃN BẬC, không cho màu.

    SDXL vẽ có vân sơn dầu. Snap từng pixel một thì pixel vân lẻ loi nhảy sang bậc sáng
    khác và mặt phẳng thành lấm tấm hạt muối — đây chính là cái "lem" nhìn thấy trên thỏi
    kim loại và các ô lục giác.

    Lọc trên nhãn bậc (số nguyên nhỏ), không lọc trên RGB: làm mờ RGB sẽ kéo màu ra khỏi
    bảng và tạo dải chuyển sắc — đúng hai thứ §4 cấm. Bỏ phiếu đa số giữ mảng phẳng phẳng
    và giữ biên giữa hai mảng sắc nét, vì trong lòng mảng đa số luôn thắng tuyệt đối còn
    ngay tại biên thì nó chỉ dịch đường biên đi dưới một pixel.
    """
    if radius < 1:
        return band

    def _box(mask: np.ndarray) -> np.ndarray:
        """Tổng trong cửa sổ vuông, tính bằng ảnh tích luỹ — O(1) mỗi pixel, không vòng lặp
        Python. numpy thuần, không kéo thêm scipy vào chỉ để lọc một cửa sổ."""
        ii = np.zeros((mask.shape[0] + 1, mask.shape[1] + 1), dtype=np.int32)
        ii[1:, 1:] = np.cumsum(np.cumsum(mask.astype(np.int32), axis=0), axis=1)
        h, w = mask.shape
        r = radius
        y0 = np.clip(np.arange(h) - r, 0, h)[:, None]
        y1 = np.clip(np.arange(h) + r + 1, 0, h)[:, None]
        x0 = np.clip(np.arange(w) - r, 0, w)[None, :]
        x1 = np.clip(np.arange(w) + r + 1, 0, w)[None, :]
        return ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]

    # Chỉ đếm pixel đục: nếu tính cả nền trong suốt thì pixel sát biên luôn thua phiếu và
    # bị kéo về bậc của hàng xóm phía trong — viền ngoài mỏng đi một cách có hệ thống.
    votes = np.stack([_box(opaque & (band == l)) for l in range(levels)], axis=0)
    winner = votes.argmax(axis=0).astype(np.int32)
    return np.where(opaque, winner, band)


def _lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """Lab -> sRGB uint8. Nghịch đảo của `to_lab`, cần cho việc rút sắc mà giữ độ sáng."""
    L, a_, b_ = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    fx, fz = fy + a_ / 500.0, fy - b_ / 200.0
    def inv(f):
        f3 = f ** 3
        return np.where(f3 > 0.008856, f3, (f - 16.0 / 116.0) / 7.787)
    xyz = np.stack([inv(fx) * 0.95047, inv(fy), inv(fz) * 1.08883], axis=-1)
    m = np.array([[3.2406, -1.5372, -0.4986],
                  [-0.9689, 1.8758, 0.0415],
                  [0.0557, -0.2040, 1.0570]])
    lin = xyz @ m.T
    srgb = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
    return np.clip(srgb * 255.0, 0, 255).astype(np.uint8)

def cel(img: Image.Image, spec: dict, kind: str = "",
        element: str | None = None) -> Image.Image:
    """Snap bảng màu -> giới hạn bậc sáng -> vẽ viền tối theo đúng biên alpha.

    `kind="modifier"` thu bảng màu về đúng phần trung tính + màu viền: §6b lấy việc VẮNG
    màu nguyên tố làm tín hiệu "modifier không thuộc nguyên tố nào". Máy sinh bỏ qua luật
    này gần như mọi lần (đo trên mẻ 21 asset: 21/21 modifier bị tô màu), và đây là luật
    phát biểu bằng bảng màu chứ không bằng thẩm mỹ, nên ép được mà không mất gì.
    """
    a = np.array(img.convert("RGBA"))
    rgb, alpha = a[..., :3], a[..., 3]
    opaque = alpha >= 128
    if not opaque.any():
        return img

    names_cols = palette_colors(spec)
    if kind == "modifier":
        # Cùng cách nhận diện mà check_modifier_neutral dùng: theo TÊN mục trong bảng màu,
        # không theo ngưỡng chroma riêng — hai con số độc lập thì sớm muộn cũng lệch nhau.
        neutral = [(n, c) for n, c in names_cols
                   if n.startswith("neutral") or n == "outline"]
        if neutral:
            names_cols = neutral
    pal_rgb = np.array([c for _, c in names_cols], dtype=np.uint8)
    pal_lab = to_lab(pal_rgb)

    sh = spec["shading"]
    if sh.get("enforcement") == "light":
        # Giữ nguyên nét vẽ của máy sinh; chỉ vẽ viền ở dưới. Chính bước snap bảng màu là
        # thứ làm icon trông phẳng và "AI" — xem art-direction §4, ghi chú 2026-08-27.
        out = rgb.copy()
        if kind == "modifier":
            # §6b: modifier KHÔNG mang màu hệ — vắng màu chính là tín hiệu "cái này không
            # thuộc nguyên tố nào". Máy sinh bỏ qua luật này gần như mọi lần (theme dễ
            # thương vẽ chúng thành kiếm vàng), nên rút màu bằng code.
            #
            # Rút chroma trong Lab chứ không dùng thang xám thường: thang xám tính trung
            # bình RGB nên hai màu khác nhau mà cùng độ chói ra cùng một xám, làm phẳng mất
            # khối. Giữ nguyên L*, ép a*b* về 0 thì khối và bậc sáng còn nguyên, chỉ mất sắc.
            lab = to_lab(out).astype(np.float32)
            lab[..., 1:] = 0.0
            out = np.where(opaque[..., None], _lab_to_srgb(lab), out)
    else:
        fam = _family(names_cols, rgb, opaque, kind, element)
        ramp = _ramp(names_cols, fam)[:max(2, int(sh["max_distinct_values"]) - 1)]
        out = _map_to_ramp(rgb, opaque, ramp)

    outline = sh.get("outline", {})
    col = outline.get("color")
    if isinstance(col, str) and col.startswith("#"):
        col = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
    if col is None:
        # Không khai màu viền thì lấy màu tối nhất trong bảng — vẫn nằm trong bảng nên
        # không phá luật palette.
        col = tuple(int(v) for v in pal_rgb[int(pal_lab[:, 0].argmin())])
    col_arr = np.array(col, dtype=np.uint8)

    if outline.get("enabled", False):
        src = spec["icon"]["canvas"]["width"]
        width = max(2, round(outline["width_px_at_512"] * a.shape[1] / src))
        # Cùng công thức dải viền mà check_outline dùng, nên cái được vẽ và cái được đo là
        # một. Lệch công thức ở đây thì viền vẽ ra vẫn trượt phép kiểm.
        band = opaque & ~_erode(opaque, width)
        out[band] = col_arr

    a[..., :3] = out
    a[..., 3] = _feather(opaque)
    # Pixel trong suốt vẫn phải mang màu viền, không phải màu nền cũ: PNG lưu RGB kể cả ở
    # chỗ alpha=0, và khi Unity lọc bilinear lúc thu nhỏ, nó TRỘN cả những pixel đó vào —
    # đó chính là "lem màu" nhìn thấy ở icon nhỏ. Sơn phần trong suốt bằng màu viền thì
    # phần trộn vào cũng là màu viền.
    a[a[..., 3] == 0, :3] = col_arr
    return Image.fromarray(a, "RGBA")


def _feather(mask: np.ndarray) -> np.ndarray:
    """Alpha mềm một pixel ở mép, thay cho alpha cứng 0/255.

    Khâu tách nền trả về mask nhị phân, nên mép icon là bậc thang — ở 64px trong UI nó
    hiện ra rõ. Lấy trung bình 3×3 của mask làm độ phủ xấp xỉ: pixel trong lòng vẫn 255,
    pixel mép nhận giá trị theo phần diện tích thực sự bị chiếm.
    """
    m = mask.astype(np.float32)
    acc = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            acc += np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    cov = acc / 9.0
    # Pixel thuộc mask giữ ĐỤC HOÀN TOÀN, phần mềm nằm ở vòng ngoài. Làm mềm vào bên
    # trong sẽ kéo alpha của pixel mép xuống dưới 128, và mọi phép kiểm đều lấy 128 làm
    # ranh giới — icon sẽ teo đi một pixel dưới mắt bộ kiểm mà không ai thấy tại sao.
    out = np.where(mask, 1.0, cov)
    return np.clip(out * 255.0, 0, 255).astype(np.uint8)
