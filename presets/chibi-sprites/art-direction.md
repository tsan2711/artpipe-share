# Preset: chibi-sprites — nhân vật / quái chibi toàn thân

Phong cách: nhân vật chibi toàn thân (đầu to, thân nhỏ), đứng, nhìn chéo 3/4, viền tối dày, màu tươi bão hoà.
Model: `animagine-xl-4.0-opt`. Tách nền: `rembg u2net`.

Hợp với: sprite nhân vật / quái / NPC / pet tĩnh cho game 2D, avatar, chân dung trong shop/gacha.
Sprite tĩnh (1 khung). Ghép nhiều sprite thành atlas: `python3 tools/pack_atlas.py out/<mẻ>/best`.

**Chỉ các khối ```yaml là dữ liệu thật** — chữ ngoài khối là ghi chú cho người đọc.
Muốn đổi gu: copy cả thư mục preset này sang tên mới rồi sửa (đừng sửa tại chỗ preset đang dùng).

## Thông tin spec

```yaml
spec:
  version: "1.0.0"
  direction_name: "Chibi Sprites"
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
    enabled: true
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
  prompt_prefix: "masterpiece, high score, great score, absurdres, solo, chibi, full body, game character sprite,"
  style_phrase: "big head small body, standing, three quarter view, thick dark outline, vibrant saturated colours, cel shading, white background, simple background"
  matte_method: segment
  segment_model: u2net
  max_prompt_tokens: 0
  negative_prompt: "lowres, worst quality, low quality, low score, bad score, average score, blurry, jpeg artifacts, signature, watermark, username, text, logo, frame, border, gradient background, colorful background, busy background, scenery, pastel, washed out, pale, desaturated, photograph, 3d render, realistic, multiple views, character sheet, reference sheet, turnaround, cropped, cut off feet, bad anatomy, extra limbs, multiple characters, sticker, white border"
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
