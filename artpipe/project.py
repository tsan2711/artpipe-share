"""Gốc project game mà artpipe đang phục vụ.

artpipe sống ở sanne-kit (`Tools/artpipe/`), còn dữ liệu nằm trong từng game: spec art-direction,
DB spell/item của Unity, thư mục Assets/ để nhập icon. Nên "project" là một tham số, không phải
vị trí của file này:

    ARTPIPE_PROJECT=<gốc project Unity>   # CI đặt biến này (game/<project>)
    (trống)                               # thư mục đang đứng (cwd) — chạy tay từ gốc game

`HOME` là thư mục của chính artpipe (workflows/, themes/, anims/).
"""

from __future__ import annotations

import os
from pathlib import Path

HOME = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("ARTPIPE_PROJECT") or os.getcwd()).resolve()


def rel(path: Path) -> str:
    """Đường dẫn để in: tương đối theo project nếu nằm trong đó, không thì theo artpipe, không thì tuyệt đối."""
    p = Path(path).resolve()
    for base in (ROOT, HOME):
        try:
            return str(p.relative_to(base))
        except ValueError:
            pass
    return str(p)
