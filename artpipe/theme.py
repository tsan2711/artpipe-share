"""Một THEME là toàn bộ những gì quyết định diện mạo asset, gói trong một file có tên.

Vì sao tồn tại: cho tới 2026-08-27, "theme" nằm rải rác trong `art-direction.md` — bảng
màu ở §3, `prompt_prefix` và `style_phrase` ở §6, checkpoint và graph thì nằm trên dòng
lệnh. Mỗi lần chỉnh gu là sửa tại chỗ, và **asset sinh sau không còn khớp asset sinh
trước**. Không phép kiểm nào thấy: cả hai đều qua tầng 1, chỉ khác nhau ở diện mạo.

Yêu cầu của Bi, và cũng là hợp đồng của file này:

  1. Chọn một theme → một lần chạy sinh **toàn bộ** asset theo theme đó.
  2. Sinh lại **lẻ một** asset sau này (icon, item, sau này mesh/VFX) **không** phải chạy
     lại cả bộ, mà kết quả vẫn đồng nhất với những cái đã có.

Điều 2 là điều khó, và nó đòi ba thứ:

  * **Gói kín.** Mọi tham số ảnh hưởng diện mạo nằm TRONG file theme, kể cả checkpoint và
    graph. Tham số nào còn phải gõ tay trên dòng lệnh là một tham số sẽ bị gõ khác đi.
  * **Seed tất định.** Seed suy ra từ `(theme, slug, variant)` chứ không phải từ một số
    gốc gõ tay, nên sinh lại một asset ra đúng ảnh cũ mà không cần nhớ mẻ trước dùng seed
    nào.
  * **Dấu vân tay.** `fingerprint()` băm toàn bộ nội dung theme. Provenance ghi lại, nên
    lúc nào cũng đối chiếu được: asset này có thật sự sinh bằng theme đang dùng không, hay
    nó là tàn dư của một lần chỉnh gu đã quên.

Đổi theme thì tạo file MỚI, đừng sửa file cũ — sửa tại chỗ là làm hỏng đúng điều 2, vì
những asset sinh bằng bản trước không còn cách nào nhận ra là đã lạc hậu.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

DIR = Path(__file__).parent / "themes"

# Những nhánh của spec mà theme được phép đè. Danh sách đóng, cố ý: theme quyết định DIỆN
# MẠO, không được lặng lẽ đổi luật kiểm tra hay kích thước canvas — đó là chỗ ranh giới
# giữa "đổi gu" và "hạ chuẩn cho ảnh xấu lọt qua".
OVERRIDABLE = ("generation", "shading", "palette", "element_paint", "subtype_shape",
               "modifier_stat_shape", "modifier_behaviour_shape", "modifier_type_variant", "item_shape_override",
               "item_category_hint", "neutral_paint", "palette_policy")


class ThemeError(RuntimeError):
    pass


def available() -> list[str]:
    return sorted(p.stem for p in DIR.glob("*.yaml"))


def load(name: str) -> dict:
    p = DIR / f"{name}.yaml"
    if not p.exists():
        raise ThemeError(f"không có theme {name!r} (có: {', '.join(available()) or 'chưa có cái nào'})")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or "theme" not in data:
        raise ThemeError(f"{p}: thiếu khối `theme:` (cần id, checkpoint, workflow)")
    for k in ("id", "checkpoint", "workflow"):
        if not data["theme"].get(k):
            raise ThemeError(f"{p}: theme.{k} bỏ trống — theme phải gói kín, "
                             f"không để tham số nào rơi ra dòng lệnh")
    if data["theme"]["id"] != name:
        raise ThemeError(f"{p}: theme.id={data['theme']['id']!r} không khớp tên file {name!r}")
    return data


def fingerprint(theme: dict) -> str:
    """Băm nội dung theme. Đổi một chữ trong style_phrase là đổi dấu vân tay."""
    blob = json.dumps(theme, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def apply(art: dict, theme: dict) -> dict:
    """Phủ theme lên spec, chỉ ở những nhánh được phép, và trộn theo TỪNG KHOÁ.

    Trộn nông một cấp chứ không thay cả nhánh: theme thường chỉ muốn đổi `style_phrase`
    mà vẫn giữ `max_prompt_tokens` của spec. Thay cả nhánh sẽ âm thầm xoá mất những khoá
    không được nhắc tới, và cái mất đầu tiên là hàng rào 77 token.
    """
    out = dict(art)
    for key in OVERRIDABLE:
        patch = theme.get(key)
        if patch is None:
            continue
        base = out.get(key)
        if isinstance(base, dict) and isinstance(patch, dict):
            merged = dict(base)
            merged.update(patch)
            out[key] = merged
        else:
            out[key] = patch
    out["_theme"] = {"id": theme["theme"]["id"],
                     "version": theme["theme"].get("version", 1),
                     "fingerprint": fingerprint(theme)}
    return out


def seed_for(theme_id: str, slug: str, variant: int) -> int:
    """Seed tất định từ (theme, asset, biến thể).

    Không dùng `seed_gốc + v` như trước: con số gốc nằm trên dòng lệnh, nên sinh lại một
    asset sáu tuần sau đòi phải nhớ hôm đó gõ số mấy. Băm thì không phải nhớ gì — cùng ba
    đầu vào luôn ra cùng một seed, khác asset thì khác seed.

    Chặn ở 2^31 vì ComfyUI nhận seed là số nguyên có dấu 32-bit.
    """
    h = hashlib.sha256(f"{theme_id}\x00{slug}\x00{variant}".encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") & 0x7FFFFFFF
