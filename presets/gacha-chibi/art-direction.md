# Preset: gacha-chibi — nhân vật chibi kiểu game gacha mobile

Phong cách: chibi 2.5 đầu, nét mảnh cùng màu từng mảng, mắt to hai điểm sáng, cel 2 tông, pastel ấm + một màu nhấn.
Model: `animagine-xl-4.0-opt`. Tách nền: `rembg u2net`.

**Nguồn:** đúng prefix / style / negative mà NanoSwarm dùng cho 12 Commander "Art B"
(`NanoSwarm/tools/artpipe/gen_frontline_art.py`, CHAR_*). Khác duy nhất: NanoSwarm tách nền bằng node ComfyUI
RMBG-2.0, repo này dùng `rembg u2net`.

Hợp với: nhân vật / hero / NPC / pet cho game gacha, idle RPG, chân dung shop.

**Chỉ các khối ```yaml là dữ liệu thật** — chữ ngoài khối là ghi chú cho người đọc.
Muốn đổi gu: copy cả thư mục preset này sang tên mới rồi sửa (đừng sửa tại chỗ preset đang dùng).

## Thông tin spec

```yaml
spec:
  version: "1.0.0"
  direction_name: "Gacha Chibi"
```

## Bảng màu

`element` của mỗi icon trong `icons.yaml` = một khoá ở đây (gold, red, ...). Checker đọc mã hex;
máy sinh đọc câu tả ở `element_paint` (nó không hiểu mã hex).

```yaml
palette:
  gold:   { main: "#FFC530", core: "#FFF1B8", shadow: "#C77F12", hue: 44 }
  red:    { main: "#F2414B", core: "#FFC2B8", shadow: "#A3192B", hue: 355 }
  blue:   { main: "#3FA9F5", core: "#C8ECFF", shadow: "#1F5FAF", hue: 205 }
  green:  { main: "#47C95A", core: "#C9F7B8", shadow: "#1F7A3A", hue: 128 }
  purple: { main: "#9B5CF6", core: "#E3CCFF", shadow: "#5B2BA8", hue: 265 }
  pink:   { main: "#FF5FA8", core: "#FFD0E6", shadow: "#C2286E", hue: 330 }
  outline: "#4A3A52"
  neutral:
    light: "#FFF6EC"
    mid:   "#C4B8AF"
    dark:  "#6B5A52"
```

## Chính sách bảng màu

`fatal: false` — màu chỉ để tham khảo: icon lệch màu bị đánh "xem tay", không bị loại.
Game cần khoá màu chặt (mọi icon cùng bảng màu) thì đặt `fatal: true`.

```yaml
palette_policy:
  closed: true
  fatal: false
  delta_e_tolerance: 28
  min_conforming_pixel_ratio: 0.50
  scored_on: flat_field_interior
  interior_min_sample_ratio: 0.15
```

## Độ đọc được ở cỡ nhỏ

`ui_background_reference` = màu nền UI nơi icon sẽ nằm (để chấm tương phản). Đổi theo game bạn.

```yaml
readability:
  ui_background_reference: "#1E1B2E"
  min_contrast_ratio: 3.0
  contrast_percentile: 90
  edge_density_max: 0.22
  outline_dark_lstar_max: 40
  outline_band_min_ratio: 0.5
  value_merge_delta_lstar: 4
  value_coverage_target: 0.90
```

## Đổ bóng + viền

`enforcement: light` = giữ nguyên nét vẽ của AI, chỉ vẽ thêm viền đều quanh chủ thể.

```yaml
shading:
  model: cel
  enforcement: light
  value_steps: 4
  max_distinct_values: 24
  gradients_allowed: true
  outline:
    enabled: false
    width_px_at_512: 10
    color: "#4A3A52"
    style: uniform
```

## Khung icon

```yaml
icon:
  canvas: { width: 512, height: 512, format: "PNG", channels: "RGBA" }
  background: transparent
  safe_margin_pct: 4
  silhouette_coverage_pct: [10, 85]
  display_sizes: [128, 64]
  readability_reference_size: 64
  export:
    - { size: 512, suffix: "_512" }
    - { size: 256, suffix: "_256" }
    - { size: 128, suffix: "_128" }
    - { size: 64,  suffix: "_64" }
```

## Câu lệnh cho máy sinh

Prompt mỗi icon = `prompt_prefix` + mô tả hình (`prompt:` trong icons.yaml) + màu (`element_paint`) +
`style_phrase`. CLIP chỉ đọc ~77 token đầu → từ quan trọng để đầu, mô tả hình ngắn gọn.

```yaml
generation:
  prompt_prefix: "masterpiece, best quality, very aesthetic, newest, solo, no humans, full body, official art, polished 2d mobile gacha game character illustration, chibi, 2.5 heads tall, standing,"
  style_phrase: "thin clean coloured lineart that matches each colour area, big expressive eyes with two white highlights, soft two-tone cel shading, warm pastel palette with one saturated accent colour, slightly open friendly pose with arms and legs clearly separated from the body, clean colour areas, smooth finished rendering, plain white background, centered"
  matte_method: segment
  segment_model: u2net
  max_prompt_tokens: 0
  negative_prompt: "frame, border, rounded rectangle, card, sketch, rough lines, messy lines, unfinished, doodle, lightning bolts around, motion lines, 3d render, plastic, glossy toy, vinyl figure, clay, photograph, realistic, dark, gloomy, horror, thick black outline, flat vector, sticker, white border, text, watermark, logo, multiple views, character sheet, turnaround, group, crowd, duplicate, lowres, bad anatomy, blurry, jpeg artifacts, busy background, sparkles everywhere, rays"
```

## Màu bằng lời

```yaml
element_paint:
  gold:   "gold and warm yellow"
  red:    "bright red"
  blue:   "bright sky blue"
  green:  "bright green"
  purple: "vivid purple"
  pink:   "hot pink"

element_color:
  gold:   "warm honey gold"
  red:    "soft cherry red"
  blue:   "baby blue"
  green:  "fresh mint green"
  purple: "soft lavender purple"
  pink:   "bubblegum pink"
```

## Hình dùng chung (tuỳ chọn)

Icon trong `icons.yaml` có thể dùng `subtype: <khoá>` thay cho `prompt:` để nhiều icon dùng chung một mô tả.

```yaml
subtype_shape:
  slime:  "a round bouncy slime monster with big shiny eyes and a happy smile"
  knight: "a tiny knight in round armour holding a short sword and a small shield"
```
