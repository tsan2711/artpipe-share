# Preset: cute-icons — icon game anime dễ thương

Phong cách: chibi anime, khối tròn mập, viền sạch dày, màu pastel + một màu nhấn, bóng mềm.
Model: `animagine-xl-4.0-opt` (SDXL anime). Tách nền: `rembg isnet-anime`.

Hợp với: icon item / tiền tệ / UI / kỹ năng của game mobile casual, idle, RPG nhẹ.

**Chỉ các khối ```yaml là dữ liệu thật** — chữ ngoài khối là ghi chú cho người đọc.
Muốn đổi gu: copy cả thư mục preset này sang tên mới rồi sửa (đừng sửa tại chỗ preset đang dùng).

## Thông tin spec

```yaml
spec:
  version: "1.0.0"
  direction_name: "Cute Icons"
```

## Bảng màu

`element` của mỗi icon trong `icons.yaml` = một khoá ở đây (gold, red, ...). Checker đọc mã hex;
máy sinh đọc câu tả ở `element_paint` (nó không hiểu mã hex).

```yaml
palette:
  gold:   { main: "#FFD166", core: "#FFF6D6", shadow: "#D49A2A", hue: 42 }
  red:    { main: "#FF7A7A", core: "#FFE3E0", shadow: "#D04848", hue: 0 }
  blue:   { main: "#6EC8FF", core: "#E6F7FF", shadow: "#3A8CC8", hue: 205 }
  green:  { main: "#7EE08A", core: "#EAFFEC", shadow: "#3FA552", hue: 128 }
  purple: { main: "#C49FFF", core: "#F5EEFF", shadow: "#8257D4", hue: 265 }
  pink:   { main: "#FF9CCB", core: "#FFEAF4", shadow: "#D45C95", hue: 330 }
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
  safe_margin_pct: 8
  silhouette_coverage_pct: [10, 80]
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
  prompt_prefix: "masterpiece, best quality, no humans, cute chibi anime game icon,"
  style_phrase: "soft pastel colours, rounded chunky shape, thick clean outline, simple shading, subtle shine"
  matte_method: segment
  segment_model: isnet-anime
  max_prompt_tokens: 0
  negative_prompt: "dark, gloomy, horror, washed out, desaturated, photograph, 3d render, realistic, drop shadow, text, watermark, logo, frame, border, busy background, multiple objects, sticker, white border, die-cut outline, lowres, blurry, jpeg artifacts, character sheet, multiple views"
```

## Màu bằng lời

```yaml
element_paint:
  gold:   "warm honey gold with cream highlight"
  red:    "soft cherry red with pink highlight"
  blue:   "baby blue with white highlight"
  green:  "fresh mint green with pale highlight"
  purple: "soft lavender purple with lilac highlight"
  pink:   "bubblegum pink with white highlight"

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
  coin: "a shiny round coin with a star stamped in the middle"
  gem:  "a faceted cut gemstone with a bright glint"
```
