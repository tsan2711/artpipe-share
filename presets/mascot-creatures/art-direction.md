# Preset: mascot-creatures — sinh vật mascot vector phẳng (gu của Thousandfold)

**Nguồn:** spec thật của game Thousandfold (`Seriously/docs/shared/thousandfold-art/art-direction.md`), chép nguyên.
Bộ ảnh mẫu `docs/samples/mascot-creatures` sinh bằng đúng spec này: SDXL base + `icon_sdxl_vector.json` (LoRA DD-vector),
seed 1000–1002, chạy trên Colab (run 38114816113, 2026-10-11).

---


Hướng B đã chốt (2026-10-11): thế giới xám, bầy đi qua tô màu lại. Con vật phải là **mảng màu rực, phẳng, viền tối dày**
để nổi trên nền xám ở cỡ 8–16 px. Dùng chung máy artpipe của sanne-kit (generate → matte → stylise → tier), giống NanoSwarm;
file này chỉ giữ dữ liệu của Thousandfold. Con vật viết dạng `kind: spell`: `element` chọn màu, `subtype` chọn hình.

Style target: **flat vector cute** — mảng màu đặc, ít bậc sáng, viền đều, không gradient cầu vồng, không bóng loáng kiểu sticker.

## Palette

```yaml
palette:
  coral:  { main: "#FF6B5A", core: "#FFE3DC", shadow: "#C94236", hue: 6 }
  sun:    { main: "#FFC93C", core: "#FFF3CF", shadow: "#D6962A", hue: 43 }
  mint:   { main: "#3FD9A5", core: "#DDFBEF", shadow: "#219E74", hue: 160 }
  violet: { main: "#8E6BFF", core: "#ECE6FF", shadow: "#5B3FC4", hue: 254 }
  outline: "#2E2A36"
  neutral:
    light: "#F4F1EC"
    mid:   "#A9A6AE"
    dark:  "#55515C"
```

## Palette policy (required by checks.check_palette_conformance)

```yaml
palette_policy:
  closed: true
  delta_e_tolerance: 28
  min_conforming_pixel_ratio: 0.50
  scored_on: flat_field_interior
  interior_min_sample_ratio: 0.15
```

## Readability (required by checks.check_readable_at_64)

```yaml
readability:
  ui_background_reference: "#7A7A80"   # thế giới xám của hướng B — con phải nổi trên nền này
  min_contrast_ratio: 3.0
  contrast_percentile: 90
  edge_density_max: 0.22
  outline_dark_lstar_max: 40
  outline_band_min_ratio: 0.5
  value_merge_delta_lstar: 4
  value_coverage_target: 0.90
```

## Shading

```yaml
shading:
  model: cel
  enforcement: light
  value_steps: 4
  max_distinct_values: 24
  gradients_allowed: true
  outline:
    enabled: true
    width_px_at_512: 10
    color: "#2E2A36"
    style: uniform
```

## Icon

```yaml
icon:
  canvas: { width: 512, height: 512, format: "PNG", channels: "RGBA" }
  background: transparent
  safe_margin_pct: 8
  silhouette_coverage_pct: [10, 80]
  display_sizes: [128, 64]
  readability_reference_size: 64
  export:
    - { size: 512, suffix: "_src" }
    - { size: 128, suffix: "" }
```

## Generation

```yaml
generation:
  prompt_prefix: "flat vector game sprite, cute mascot creature,"
  style_phrase: "solid flat colour fills, thick even dark outline, two-tone cel shading, simple round chunky shape, tiny dot eyes"
  matte_method: segment
  segment_model: u2net
  max_prompt_tokens: 0
  negative_prompt: "rainbow, gradient, iridescent, holographic, glossy, shiny plastic, sticker, white border, die-cut outline, 3d render, photograph, realistic, detailed texture, many colours, text, watermark, logo, frame, busy background, multiple objects, drop shadow"
```

## Element paint — colour as words (the checker reads the hex above; the model reads this)

```yaml
element_paint:
  coral:  "solid coral red"
  sun:    "solid sunny yellow"
  mint:   "solid mint green"
  violet: "solid violet purple"
```

## Element colour — hue per role

```yaml
element_color:
  coral:  "coral red"
  sun:    "sunny yellow"
  mint:   "mint green"
  violet: "violet purple"
```

## Subtype shape — one entry per creature

Luật: một con = một khối tròn đặc + MỘT dấu nhận diện. Không tay chân dài, không chi tiết nhỏ (ở 12 px sẽ mất).

```yaml
subtype_shape:
  cr-wisp:   "a tiny round glowing light spirit with a short soft flame tail, single colour"
  cr-drop:   "a tiny round paint droplet with a pointed top, single colour"
  cr-crayon: "a tiny short crayon stub with a pointed tip, stubby round body, no arms"
  cr-sprout: "a tiny round seed creature with one small leaf sprout on its head"
  cr-brush:  "a tiny round creature whose head is a fluffy paintbrush bristle tuft dipped in paint"
  cr-chick:  "a tiny perfectly round baby chick, tiny beak, tiny wings, no legs"
  cr-star:   "a tiny soft puffy rounded five-point star"
  cr-jelly:  "a tiny round gummy bear, solid colour, simple"
```
