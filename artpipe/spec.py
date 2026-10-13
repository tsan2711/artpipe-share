"""Load an art-direction spec.

Mechanism only — knows how to find and merge the authoritative YAML blocks inside a
markdown document. It knows nothing about SKYBORNE, icons, or any particular palette;
swap the markdown file and the same loader serves a different project.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_FENCE = re.compile(r"^```yaml\s*$(.*?)^```\s*$", re.MULTILINE | re.DOTALL)


class SpecError(RuntimeError):
    pass


def load(md_path: Path) -> dict:
    """Merge every ```yaml block in the document into one dict.

    Top-level keys must be unique across blocks. A duplicate means the same fact is
    stated twice, which is exactly the drift this file exists to prevent, so it is an
    error rather than a last-one-wins merge.
    """
    text = Path(md_path).read_text(encoding="utf-8")
    blocks = _FENCE.findall(text)
    if not blocks:
        raise SpecError(f"{md_path}: no ```yaml blocks — nothing authoritative to read")

    merged: dict = {}
    for i, raw in enumerate(blocks):
        parsed = yaml.safe_load(raw)
        if parsed is None:
            continue
        if not isinstance(parsed, dict):
            raise SpecError(f"{md_path}: yaml block #{i + 1} is not a mapping")
        for key, value in parsed.items():
            if key in merged:
                raise SpecError(
                    f"{md_path}: top-level key '{key}' defined in more than one yaml "
                    "block. One fact, one place — merge them."
                )
            merged[key] = value
    return merged


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def palette_colors(spec: dict) -> list[tuple[str, tuple[int, int, int]]]:
    """Flatten the palette into (label, rgb) pairs, including neutrals and outline."""
    out: list[tuple[str, tuple[int, int, int]]] = []
    for role, entry in spec.get("palette", {}).items():
        if isinstance(entry, str):
            out.append((role, hex_to_rgb(entry)))
        elif isinstance(entry, dict):
            for tone, value in entry.items():
                if isinstance(value, str) and value.startswith("#"):
                    out.append((f"{role}.{tone}", hex_to_rgb(value)))
    if not out:
        raise SpecError("spec has no palette colours")
    return out
