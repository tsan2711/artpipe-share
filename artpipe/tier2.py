"""Tier 2 — the checks a model has to judge, because pixels cannot.

Tier 1 measures **compliance**: right canvas, legal colours, countable value steps, a
visible outline. It can never measure **identity**. A fixture once passed all eight tier-1
checks while being unrecognisable as a fire projectile, and that is not a gap to patch —
no pixel statistic answers "would a player read this as fire?". That question needs a
model that has seen what fire looks like.

Two axes, judged separately, for the same reason §6 splits them: "reads as Frost but is
declared Fire" is a different defect from "reads as a beam but is declared a projectile",
and one score cannot say which happened.

  colour axis — CLIP zero-shot over the element names in the spec (spells only)
  shape  axis — CLIP zero-shot over the shape descriptions in the spec (all kinds)
  style       — DINO cosine similarity against the anchor set

Labels are built from the spec, never written here. The spec's shape strings are English
precisely because they flow into a model prompt, so they can be used verbatim.

Cost note: this module imports torch. That import alone costs seconds, so nothing here is
imported until an image has already passed tier 1 — the cheap gate stays cheap.

Setup (once):
    python3 -m venv tools/artpipe/.venv
    tools/artpipe/.venv/bin/pip install torch transformers pillow numpy
Then run the pipeline with that interpreter:
    tools/artpipe/.venv/bin/python tools/artpipe/run.py ...
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
from PIL import Image

from checks import Result

CLIP_ID = "openai/clip-vit-base-patch32"
DINO_ID = "facebook/dino-vitb8"


class ModelUnavailable(RuntimeError):
    """Raised when the tier-2 dependencies are not installed.

    Kept distinct from a failed check: "the icon is wrong" and "we could not look at the
    icon" must never collapse into the same verdict, or a broken install silently becomes
    a passing batch.
    """


def _require_torch():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        raise ModelUnavailable(
            "tier 2 cần torch + transformers. Tạo venv rồi chạy pipeline bằng nó:\n"
            "  python3 -m venv tools/artpipe/.venv\n"
            "  tools/artpipe/.venv/bin/pip install torch transformers pillow numpy"
        ) from exc


@functools.lru_cache(maxsize=2)
def _clip(model_id: str = CLIP_ID):
    _require_torch()
    from transformers import CLIPModel, CLIPProcessor
    model = CLIPModel.from_pretrained(model_id).eval()
    return model, CLIPProcessor.from_pretrained(model_id)


@functools.lru_cache(maxsize=2)
def _dino(model_id: str = DINO_ID):
    _require_torch()
    from transformers import AutoImageProcessor, AutoModel
    model = AutoModel.from_pretrained(model_id).eval()
    return model, AutoImageProcessor.from_pretrained(model_id)


# ------------------------------------------------------------------ presentation

def _on_ui_background(png_path: Path, spec: dict) -> Image.Image:
    """Composite the RGBA icon over the UI background the readability rules assume.

    A transparent PNG handed to CLIP is composited on black by most loaders, which is not
    where the icon will ever be seen. Judging it there would score a background choice we
    did not make. `readability.ui_background_reference` is the surface the icon actually
    sits on, so that is the surface it gets judged on.
    """
    from spec import hex_to_rgb

    img = Image.open(png_path).convert("RGBA")
    bg = Image.new("RGB", img.size, hex_to_rgb(spec["readability"]["ui_background_reference"]))
    bg.paste(img, (0, 0), img)
    return bg


# ------------------------------------------------------------------ label building

def _judge_labels(spec: dict, axis: str) -> dict[str, str]:
    """Captions written for the judge, not for the generator — art-direction §8.

    These were originally the generator's own phrases, on the reasoning that the judge
    should be asked exactly what the artist was told. Measured on the fixture set, that
    reasoning lost: short noun phrases scored 4/5 on shape where the generator's long
    descriptions scored 3/5, and 3/4 vs 2/4 on colour. Two vocabularies for one concept is
    not duplication when they address two models with different strengths.

    No fallback to the generator strings. A missing label is a hole in the spec, and a
    silent fallback would hide it behind a slightly worse score nobody could explain.
    """
    labels = spec.get("judge_labels", {}).get(axis)
    if not labels:
        raise KeyError(
            f"spec thiếu judge_labels.{axis} — tầng 2 không có caption để hỏi model. "
            "Xem art-direction §8 'Caption cho model chấm'"
        )
    return dict(labels)


def element_labels(spec: dict) -> dict[str, str]:
    return _judge_labels(spec, "element")


def shape_labels(spec: dict, kind: str) -> dict[str, str]:
    return _judge_labels(spec, {"spell": "spell_subtype",
                                "modifier": "modifier_stat",
                                "item": "item_category"}[kind])


def _declared_shape_key(descriptor) -> str | None:
    return {"spell": descriptor.subtype,
            "modifier": descriptor.stat,
            "item": descriptor.category}[descriptor.kind]


# ------------------------------------------------------------------ the checks

def _zero_shot(png_path: Path, spec: dict, labels: dict[str, str]) -> list[tuple[str, float]]:
    """Softmax over the label set, highest first."""
    import torch

    model, processor = _clip()
    names = list(labels)
    inputs = processor(text=[labels[n] for n in names],
                       images=_on_ui_background(png_path, spec),
                       return_tensors="pt", padding=True)
    with torch.no_grad():
        probs = model(**inputs).logits_per_image.softmax(dim=1)[0].tolist()
    return sorted(zip(names, probs), key=lambda p: -p[1])


def check_element_readability(png_path: Path, spec: dict, descriptor) -> Result:
    cfg = _tier2_cfg(spec, "element_readability")
    margin_need = cfg.get("min_margin", 0.05)

    ranked = _zero_shot(png_path, spec, element_labels(spec))
    (top, p_top), (second, p_second) = ranked[0], ranked[1]
    margin = p_top - p_second
    ok = top == descriptor.element and margin >= margin_need

    if top != descriptor.element:
        detail = (f"đọc ra {top} ({p_top:.0%}) nhưng khai là {descriptor.element} — "
                  f"sai TRỤC MÀU")
    elif margin < margin_need:
        detail = (f"đọc ra {top} ({p_top:.0%}) nhưng chỉ hơn {second} {margin:.0%} "
                  f"(cần ≥{margin_need:.0%}) — hai hệ lẫn vào nhau")
    else:
        detail = f"{top} {p_top:.0%} (kế tiếp {second} {p_second:.0%}, cách {margin:.0%})"
    return Result("element_readability", ok, cfg.get("fatal", True), round(p_top, 4), detail)


def check_shape_readability(png_path: Path, spec: dict, descriptor) -> Result:
    cfg = _tier2_cfg(spec, "subtype_readability")
    declared = _declared_shape_key(descriptor)
    labels = shape_labels(spec, descriptor.kind)

    ranked = _zero_shot(png_path, spec, labels)
    (top, p_top), (second, p_second) = ranked[0], ranked[1]
    ok = top == declared
    detail = (f"{top} {p_top:.0%} (kế tiếp {second} {p_second:.0%})" if ok else
              f"đọc ra {top} ({p_top:.0%}) nhưng khai là {declared} — sai TRỤC HÌNH")
    return Result("shape_readability", ok, cfg.get("fatal", False), round(p_top, 4), detail)


def anchor_embeddings(anchor_dir: Path) -> np.ndarray:
    """DINO embeddings of the anchor set, L2-normalised."""
    import torch

    model, processor = _dino()
    pngs = sorted(anchor_dir.glob("*.png")) if anchor_dir.exists() else []
    if not pngs:
        return np.empty((0, 0))
    with torch.no_grad():
        feats = []
        for p in pngs:
            out = model(**processor(images=Image.open(p).convert("RGB"), return_tensors="pt"))
            v = out.last_hidden_state[:, 0].numpy()[0]     # CLS token
            feats.append(v / np.linalg.norm(v))
    return np.stack(feats)


def check_style_similarity(png_path: Path, spec: dict, anchor_dir: Path) -> Result:
    """Cosine similarity to the closest anchor.

    Blocked by AD-1 until an anchor set exists, and it says so instead of passing. A style
    gate with nothing to compare against does not "pass" — it has no opinion, and an
    opinion-free gate reported as green is worse than no gate at all.
    """
    cfg = _tier2_cfg(spec, "style_similarity")
    threshold = cfg.get("threshold", 0.82)

    anchors = anchor_embeddings(anchor_dir)
    if anchors.size == 0:
        return Result(
            "style_similarity", False, cfg.get("fatal", True), 0.0,
            f"chưa có anchor nào trong {anchor_dir} (AD-1) — không có gì để so, "
            "nên đây là 'chưa chấm được', không phải 'đạt'",
        )

    import torch
    model, processor = _dino()
    with torch.no_grad():
        out = model(**processor(images=Image.open(png_path).convert("RGB"), return_tensors="pt"))
    v = out.last_hidden_state[:, 0].numpy()[0]
    v = v / np.linalg.norm(v)

    sims = anchors @ v
    best = float(sims.max())
    ok = best >= threshold
    return Result("style_similarity", ok, cfg.get("fatal", True), round(best, 4),
                  f"giống anchor gần nhất {best:.3f} (cần ≥{threshold})")


def _tier2_cfg(spec: dict, check_id: str) -> dict:
    for entry in spec.get("checks", {}).get("model_judged", []) or []:
        if entry.get("id") == check_id:
            return entry
    return {}


def run_all(png_path: Path, spec: dict, descriptor, anchor_dir: Path | None = None) -> list[Result]:
    """Every tier-2 check that applies to this asset kind.

    Only spells carry an element, so only spells get the colour axis. Modifiers are
    deliberately colourless (§6b) and items are described by category, so both are judged
    on shape alone.

    While `spec.calibrated` is false, every tier-2 result is downgraded to advisory. The
    spec says in its own header that these numbers are uncalibrated guesses, so treating
    them as a gate contradicts the document. It is not hypothetical: measured today, the
    Lightning palette entry is read as Arcane, so a fatal colour check would auto-reject
    every Lightning icon forever — a gate that always rejects one element is worse than no
    gate, because the failure looks like a verdict instead of a miscalibration.
    """
    results = []
    if descriptor.kind == "spell":
        results.append(check_element_readability(png_path, spec, descriptor))
    results.append(check_shape_readability(png_path, spec, descriptor))
    if anchor_dir is not None:
        results.append(check_style_similarity(png_path, spec, anchor_dir))

    if not spec.get("spec", {}).get("calibrated", False):
        results = [Result(r.check_id, r.passed, False, r.value,
                          r.detail + ("" if r.passed else "  [tư vấn — spec.calibrated=false]"))
                   for r in results]
    return results
