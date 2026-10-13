"""Build a generation prompt for one asset, entirely from the spec.

Mechanism: every stylistic sentence is assembled out of the ```yaml blocks in the art
direction, so changing the direction changes the prompts with no edit here. Nothing about
SKYBORNE is hardcoded — the element names, shape descriptions, category hints and rarity
tiers are all read from the document.

An asset is described by a Descriptor. Where descriptors come from (a Unity database, a
CSV, a human) is not this module's business.

Deliberately refuses to guess. If a spell has no element or no subtype, the icon cannot
express the two-axis language the direction is built on, and a plausible-looking prompt
would produce a plausible-looking icon that silently means the wrong thing. Raising is
the cheaper failure.
"""

from __future__ import annotations

from dataclasses import dataclass


class PromptError(RuntimeError):
    pass


@dataclass
class Descriptor:
    kind: str                      # "spell" | "item" | "modifier"
    name: str                      # player-facing name, for flavour only
    element: str | None = None     # spell: key of spec['element_color']
    subtype: str | None = None     # spell: key of spec['subtype_shape']
    category: str | None = None    # item:  key of spec['item_category_hint']
    rarity: str | None = None      # item:  key of spec['rarity_glow']
    stat: str | None = None        # modifier: key of spec['modifier_stat_shape']
    mod_type: str | None = None    # modifier: key of spec['modifier_type_variant']
    description: str = ""
    shape_text: str | None = None  # mô tả hình viết thẳng trong manifest (`prompt:`), thay cho subtype
    slug_prefix: bool = True       # False = tên file không kèm "<kind>-" (manifest không khai kind)


def _style_clause(spec: dict) -> str:
    sh = spec["shading"]
    out = sh["outline"]
    parts = [
        f"{sh['model']}-shaded anime style",
        f"flat blocks of colour in exactly {sh['value_steps']} value steps",
        "no gradients, no soft shading, no painterly texture"
        if not sh.get("gradients_allowed", False) else "gradients only in the outer glow",
    ]
    if out.get("enabled"):
        parts.append(
            f"a {out['style']} dark outline in {out['color']} around every shape, "
            f"about {out['width_px_at_512']}px thick at {spec['icon']['canvas']['width']}px"
        )
    return ", ".join(parts)


def _framing_clause(spec: dict) -> str:
    gen = spec.get("generation", {})

    # Tách nền bằng nhận dạng thì KHÔNG nhắc màu nền nữa. Đo trên ba mẻ thật: câu "nền hồng"
    # làm máy sinh nhuộm hồng lên chính vật thể (đồng tiền vàng ra hồng), kéo tụt
    # palette_conformance ở cả sd-turbo lẫn SDXL. Xem segment.py.
    if gen.get("matte_method") == "segment":
        return (
            "The subject is isolated on a plain neutral background with no texture, no "
            "vignette, no gradient and no cast shadow. Single centred subject filling the "
            "frame. No frame, no border, no circle, no badge, no card, no text, no "
            "watermark, no UI chrome."
        )

    backdrop = gen.get("backdrop_hex")
    if not backdrop:
        raise PromptError(
            "spec thiếu generation.backdrop_hex — ảnh sinh ra không có nền trong suốt, "
            "nên phải chỉ định màu nền phẳng để bước tách nền có cái mà cắt"
        )
    return (
        f"The subject is isolated on a completely flat, uniform {backdrop} backdrop with no "
        "texture, no vignette, no gradient and no cast shadow. Single centred subject filling "
        "the frame. No frame, no border, no circle, no badge, no card, no text, no watermark, "
        "no UI chrome."
    )


def _colour_clause(spec: dict, role: str) -> str:
    entry = spec["palette"][role]
    return (f"{entry['main']} as the main colour, {entry['core']} for the hot inner core, "
            f"{entry['shadow']} for the shadow step")


def _neutral_clause(spec: dict) -> str:
    n = spec["palette"]["neutral"]
    return (f"{n['light']} as the light value, {n['mid']} for the mid value, "
            f"{n['dark']} for the shadow value")


def estimate_tokens(text: str) -> int:
    """Ước lượng số token CLIP. Cao hơn thực tế một chút — cố ý.

    Không gọi tokenizer thật vì nó kéo theo `transformers` (~2GB) vào một bước lẽ ra chỉ
    xâu chuỗi, và cổng CI cố tình không có gói đó. CLIP dùng BPE: từ thường tách thành
    1–2 token, mỗi dấu câu là một token, cộng 2 token đầu/cuối. Hệ số 1.25 đo trên chính
    các prompt của dự án — lệch về phía AN TOÀN, vì hậu quả của việc đánh giá thấp là
    prompt bị cắt cụt mà không ai biết.
    """
    import re
    pieces = re.findall(r"[A-Za-z]+|[0-9]+|[^\sA-Za-z0-9]", text)
    return int(len(pieces) * 1.25) + 2


def build(spec: dict, d: Descriptor, form: str = "short") -> str:
    """`short` for CLIP-text models (SD/SDXL), `long` for T5-text models (FLUX).

    Not a stylistic preference. SD's text encoder is CLIP, whose hard limit is 77 tokens,
    and it truncates **silently**. Measured: the long form is 182 tokens, so SD-turbo threw
    away the last 60% — which is where the colour and the flat-backdrop instruction lived.
    The image came back on a mottled #2F7274 field instead of flat #FF0F87, leaving the
    matte stage nothing to cut. A prompt that does not fit is not a slightly worse prompt;
    it is a different prompt.
    """
    if form not in ("short", "long"):
        raise PromptError(f"form không rõ: {form!r} (chỉ 'short' hoặc 'long')")

    # Từ kích hoạt của LoRA phải đứng ĐẦU. CLIP cắt phần đuôi khi quá 77 token, và một LoRA
    # phong cách mà mất từ kích hoạt thì coi như không được nạp — ảnh vẫn ra, vẫn hợp lệ,
    # chỉ là sai phong cách; không phép kiểm nào của tầng 1 phân biệt được ca đó.
    prefix = (spec.get("generation", {}).get("prompt_prefix") or "").strip()
    prefix = f"{prefix} " if prefix else ""

    if form == "short":
        out = prefix + _short(spec, d)
        limit = int(spec.get("generation", {}).get("max_prompt_tokens", 0) or 0)
        est = estimate_tokens(out)
        if limit and est > limit:
            # Ném chứ KHÔNG cắt bớt: prompt quá dài không phải prompt hơi tệ hơn, nó là
            # một prompt khác — CLIP vứt phần đuôi, mà đuôi là chỗ đặt lệnh nền và bố cục.
            raise PromptError(
                f"{d.name}: prompt ước ~{est} token, vượt max_prompt_tokens={limit}. "
                f"Rút gọn generation.style_phrase / prompt_prefix / mô tả hình.\n  {out}")
        return out
    if d.kind == "spell":
        return prefix + _spell(spec, d)
    if d.kind == "item":
        return prefix + _item(spec, d)
    if d.kind == "modifier":
        return prefix + _modifier(spec, d)
    raise PromptError(f"kind không rõ: {d.kind!r}")


def negative(spec: dict) -> str:
    """What the image must NOT contain, for providers that accept a negative prompt.

    Lives here rather than in the workflow file or the provider because it is art
    direction, not sampler tuning: it says what "Golden Hour Witch" is not. Empty when
    the spec omits it — a missing negative is a weaker prompt, never a broken run.
    """
    return spec.get("generation", {}).get("negative_prompt", "")


def _paint(spec: dict, key: str) -> str:
    """Colour as words. The hex codes in §3 are for the checker, not for the painter —
    a text encoder tokenises "#FF3B1F" into seven meaningless pieces."""
    paints = spec.get("element_paint")
    if not paints:
        raise PromptError("spec thiếu element_paint — máy sinh không đọc được mã hex")
    if key not in paints:
        raise PromptError(f"element_paint thiếu {key!r} ({sorted(paints)})")
    return paints[key]


def _short(spec: dict, d: Descriptor) -> str:
    """Ordered by what must survive truncation: subject, colour, backdrop, then style."""
    gen = spec.get("generation", {})
    segment = gen.get("matte_method") == "segment"
    backdrop = gen.get("backdrop_name")
    if not backdrop and not segment:
        raise PromptError("spec thiếu generation.backdrop_name — cần TỪ tả màu nền, "
                          "vì máy sinh không hiểu generation.backdrop_hex")

    if d.kind == "spell" and d.shape_text:
        # Manifest viết thẳng mô tả hình (`prompt:`): không cần khai subtype_shape trong spec.
        # element vẫn tuỳ chọn — có thì thêm câu tả màu của nó.
        subject = d.shape_text.strip().rstrip(".")
        if d.element:
            subject = f"{subject}, {_paint(spec, d.element)}"
    elif d.kind == "spell":
        shapes = spec.get("subtype_shape", {})
        if not d.subtype or d.subtype not in shapes:
            raise PromptError(f"{d.name}: subtype {d.subtype!r} không hợp lệ ({sorted(shapes)})")
        if not d.element:
            raise PromptError(f"{d.name}: chưa khai element")
        subject = f"{shapes[d.subtype]}, {_paint(spec, d.element)}"
    elif d.kind == "modifier":
        shapes = {**spec["modifier_stat_shape"], **spec.get("modifier_behaviour_shape", {})}
        if not d.stat or d.stat not in shapes:
            raise PromptError(f"{d.name}: stat {d.stat!r} không hợp lệ ({sorted(shapes)})")
        subject = f"{shapes[d.stat]}, {spec.get('neutral_paint', 'flat grey, no colour')}"
    elif d.kind == "item":
        # Mô tả riêng của MÓN thắng gợi ý của LOẠI: hai món cùng loại mà dùng chung một
        # câu tả thì máy sinh vẽ ra hai icon giống hệt nhau, và tầng 1 không thấy gì cả.
        override = (spec.get("item_shape_override") or {}).get(d.name)
        if override:
            subject = f"{d.name}, {override}"
        else:
            hints = spec["item_category_hint"]
            if not d.category or d.category not in hints:
                raise PromptError(
                    f"{d.name}: category {d.category!r} không hợp lệ ({sorted(hints)})")
            subject = f"{d.name}, {hints[d.category]}"
    else:
        raise PromptError(f"kind không rõ: {d.kind!r}")

    sh = spec["shading"]
    # Câu tả phong cách nằm trong spec, không nhúng cứng: đổi checkpoint là đổi cả cách
    # nói chuyện với nó. "flat N-tone cel shading" kéo SDXL về mảng phẳng — đúng ý khi
    # dùng LoRA vector, sai hoàn toàn khi dùng model anime.
    style = spec.get("generation", {}).get("style_phrase") \
        or f"flat {sh['value_steps']}-tone cel shading, thick dark outline"
    # Đuôi giữ ngắn nhất có thể: mỗi từ ở đây ăn vào ngân sách 77 token của CLIP, và
    # phần bị cắt luôn là phần cuối. "game icon:" bỏ đi vì prompt_prefix đã nói rồi.
    where = "on plain background" if segment else f"on flat {backdrop} background"
    return f"{subject}. {style}, centred {where}, no text, no frame."


def _spell(spec: dict, d: Descriptor) -> str:
    elements, shapes = spec["element_color"], spec["subtype_shape"]

    if not d.element:
        raise PromptError(
            f"{d.name}: chưa khai element. Trục MÀU của icon = hệ nguyên tố, không có nó thì "
            f"icon không nói được nửa nghĩa. Hợp lệ: {sorted(elements)}"
        )
    if d.element not in elements:
        raise PromptError(f"{d.name}: element {d.element!r} không có trong spec ({sorted(elements)})")
    if not d.subtype:
        raise PromptError(
            f"{d.name}: chưa khai subtype. Trục HÌNH của icon = kiểu spell. Hợp lệ: {sorted(shapes)}"
        )
    if d.subtype not in shapes:
        raise PromptError(f"{d.name}: subtype {d.subtype!r} không có trong spec ({sorted(shapes)})")

    return " ".join([
        f"A single video-game spell icon: {_style_clause(spec)}.",
        f"Shape: {shapes[d.subtype]}.",
        f"Colour: {elements[d.element]}. {_colour_clause(spec, d.element)}.",
        _framing_clause(spec),
    ])


def _modifier(spec: dict, d: Descriptor) -> str:
    """Neutral body on purpose — see art-direction §6b.

    A modifier attaches to any spell, so painting it in an element colour would assert
    something false. The absence of an element colour is itself the signal, which is why
    the body colour is read from the spec's `modifier.body_color` rather than guessed here.
    """
    # Modifier hành vi không sửa chỉ số nào: hình của nó tra theo tên hành vi (catalog đặt
    # stat = tên hành vi, mod_type = "Behaviour"). Hai bảng chung một không gian khoá.
    shapes = {**spec["modifier_stat_shape"], **spec.get("modifier_behaviour_shape", {})}
    variants = spec["modifier_type_variant"]

    if not d.stat:
        raise PromptError(
            f"{d.name}: chưa khai stat. Trục HÌNH của icon modifier = chỉ số bị sửa. "
            f"Hợp lệ: {sorted(shapes)}"
        )
    if d.stat not in shapes:
        raise PromptError(f"{d.name}: stat {d.stat!r} không có trong spec ({sorted(shapes)})")
    if not d.mod_type:
        raise PromptError(
            f"{d.name}: chưa khai mod_type. Không có nó thì hai modifier cùng chỉ số ra "
            f"icon giống hệt nhau. Hợp lệ: {sorted(variants)}"
        )
    if d.mod_type not in variants:
        raise PromptError(f"{d.name}: mod_type {d.mod_type!r} không có trong spec ({sorted(variants)})")

    role = spec.get("modifier", {}).get("body_color", "neutral")
    if role != "neutral":
        raise PromptError(
            f"spec đặt modifier.body_color = {role!r}. Chỉ 'neutral' được hỗ trợ: màu hệ "
            "trên một modifier là khẳng định sai, vì modifier cắm vào spell hệ nào cũng chạy"
        )

    return " ".join([
        f"A single video-game spell-modifier icon: {_style_clause(spec)}.",
        f"Shape: {shapes[d.stat]}.",
        f"Composition: {variants[d.mod_type]}.",
        f"Colour: strictly greyscale-neutral, no elemental hue at all — {_neutral_clause(spec)}.",
        _framing_clause(spec),
    ])


def _item(spec: dict, d: Descriptor) -> str:
    hints, glows = spec["item_category_hint"], spec["rarity_glow"]

    if not d.category:
        raise PromptError(f"{d.name}: chưa khai category. Hợp lệ: {sorted(hints)}")
    if d.category not in hints:
        raise PromptError(f"{d.name}: category {d.category!r} không có trong spec ({sorted(hints)})")
    rarity = d.rarity or "Common"
    if rarity not in glows:
        raise PromptError(f"{d.name}: rarity {rarity!r} không có trong spec ({sorted(glows)})")

    parts = [
        f"A single video-game inventory item icon: {_style_clause(spec)}.",
        f"Subject: {d.name} — {hints[d.category]}.",
    ]
    if d.description:
        parts.append(f"Flavour, for silhouette only: {d.description.rstrip('.')}.")

    glow = glows[rarity]
    if glow["radius_px_at_512"] > 0:
        parts.append(
            f"A soft outer glow of about {glow['radius_px_at_512']}px at "
            f"{spec['icon']['canvas']['width']}px, opacity {glow['opacity']}, hugging the "
            "silhouette. The glow must not tint the subject itself."
        )
    else:
        parts.append("No outer glow at all.")

    parts.append(_framing_clause(spec))
    return " ".join(parts)
