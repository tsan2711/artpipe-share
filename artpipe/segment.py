"""Tách vật thể khỏi nền bằng NHẬN DẠNG, không bằng màu phông.

Vì sao cần: cách cũ ra lệnh cho máy sinh vẽ nền hồng gắt rồi khoá theo màu đó. Nó tách
sạch, nhưng đo trên ba mẻ thật (sd-turbo, SDXL+LoRA, SDXL trần) thì **màu nền ngấm vào
chính vật thể**: đồng tiền vàng ra hồng, thỏi thép xanh-xám cũng ra hồng. Đó là lý do
`palette_conformance` thô thấp ở cả ba, và không mẻ nào chữa được bằng cách đổi model —
lỗi nằm trong câu prompt, không nằm trong máy sinh.

Bỏ câu đó đi thì không còn màu khoá để cắt, nên khâu tách phải tự nhận ra đâu là vật thể.
`rembg` (U²-Net) làm đúng việc đó và chạy trên CPU trong khoảng một giây mỗi ảnh.

Đánh đổi phải biết: khác `matte.cutout`, đây KHÔNG tất định theo nghĩa "đọc code là biết
kết quả" — nó là một mạng nơ-ron với trọng số tải về. Bù lại đầu ra vẫn kiểm được bằng
đúng bộ tier 1 cũ, và trọng số u2net cố định nên cùng ảnh vào vẫn cho cùng ảnh ra.

Không có rembg thì ném `SegmentError` chứ KHÔNG âm thầm quay về lối cũ: quay lui im lặng
sẽ cho ra một mẻ trông như đã đổi cách làm nhưng thật ra chưa, và không con số nào trong
report nói cho ta biết điều đó.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

import matte


class SegmentError(matte.MatteError):
    """Kế thừa MatteError để run.py xử lý y như hỏng tách nền: ghi lại là auto_reject cho
    RIÊNG ảnh đó rồi đi tiếp, thay vì làm chết cả mẻ."""


_SESSION = None
_SESSION_MODEL = ""


def _session(model: str = "u2net"):
    """Nạp model một lần cho cả mẻ — mỗi lần `new_session` là một lần đọc lại 176MB.

    `model`: tên model rembg — `u2net` (mặc định, đa dụng), `isnet-anime` (nét anime/chibi),
    `isnet-general-use`, `birefnet-general`… Khai ở spec: `generation.segment_model`.
    """
    global _SESSION, _SESSION_MODEL
    if _SESSION is None or _SESSION_MODEL != model:
        try:
            from rembg import new_session
        except ImportError as exc:
            raise SegmentError(
                "thiếu rembg — cài vào venv của máy render: pip install rembg onnxruntime"
            ) from exc
        _SESSION = new_session(model)
        _SESSION_MODEL = model
    return _SESSION


def cutout(img: Image.Image, min_coverage: float = 0.02, model: str = "u2net") -> Image.Image:
    """RGB -> RGBA, alpha do model quyết định. Ném khi kết quả rỗng hoặc kín canvas.

    Hai cổng ở cuối bắt đúng hai kiểu hỏng đã thấy thật:
      * alpha gần rỗng — máy sinh vẽ nền kín khung, model không tìm ra chủ thể nào;
      * alpha gần kín canvas — cũng cùng nguyên nhân, nhưng model nhận nhầm cả bức tranh
        là chủ thể. Cái này nguy hơn vì nó ĐI TIẾP được và chỉ lộ ra ở điểm tương phản.
    """
    session = _session(model)     # ném SegmentError khi thiếu rembg, trước khi import remove
    from rembg import remove

    out = remove(img.convert("RGB"), session=session).convert("RGBA")
    alpha = np.array(out)[..., 3]
    frac = float((alpha >= 128).mean())
    if frac < min_coverage:
        raise SegmentError(f"không tìm thấy chủ thể — chỉ {frac:.1%} canvas là đục")
    if frac > 0.98:
        raise SegmentError(
            f"{frac:.1%} canvas là đục — máy sinh vẽ kín khung, không có nền để tách")
    return out
