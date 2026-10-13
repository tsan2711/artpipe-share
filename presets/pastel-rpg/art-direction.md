# Preset: pastel-rpg — icon RPG pastel (gu của June / Skyborne)

Phong cách: anime dễ thương, khối tròn mập, viền sạch dày, pastel mềm, bóng nhẹ + chút ánh. Model: `animagine-xl-4.0-opt`.

**Nguồn:** đúng prefix / style / negative / bảng màu của theme `cute-pastel` mà June (Skyborne) dùng để sinh
21 icon spell/item/modifier (`sanne-kit/Tools/artpipe/themes/cute-pastel.yaml`). Thêm `white background` vào
style vì chạy thử ở repo này cho thấy thiếu nó thì nền ra gradient và tách nền hỏng.

Hợp với: icon item / spell / tiền tệ cho RPG nhẹ nhàng, nền UI tối.

**Chỉ các khối ```yaml là dữ liệu thật** — chữ ngoài khối là ghi chú cho người đọc.
Muốn đổi gu: copy cả thư mục preset này sang tên mới rồi sửa (đừng sửa tại chỗ preset đang dùng).

## Thông tin spec

```yaml
spec:
  version: "1.0.0"
  direction_name: "Pastel RPG"
```

## Bảng màu

`element` của mỗi icon trong `icons.yaml` = một khoá ở đây (gold, red, ...). Checker đọc mã hex;
máy sinh đọc câu tả ở `element_paint` (nó không hiểu mã hex).

```yaml
palette:
  fire:        { main: "#FF7A5C", core: "#FFEFD9", shadow: "#D0503A", hue: 8 }
  frost:       { main: "#7FE3F5", core: "#F0FCFF", shadow: "#3E9CC4", hue: 190 }
  lightning:   { main: "#6C7BF0", core: "#FFFFFF", shadow: "#3A46A8", hue: 235 }
  arcane:      { main: "#D98BF0", core: "#FCEEFF", shadow: "#8E4FB0", hue: 292 }
  hostile:     { main: "#9BEE63", core: "#E4FFCB", shadow: "#4E9B34", hue: 95 }
  environment: { main: "#FFC978", core: "#FFE6B5", shadow: "#D19553", hue: 36 }
  outline: "#4A3A52"
  neutral:
    light: "#FBF6EF"
    mid:   "#B9B2BE"
    dark:  "#5A5162"
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
  prompt_prefix: "masterpiece, cute chibi anime game icon,"
  style_phrase: "soft pastel colours, rounded chunky shape, thick clean outline, simple shading, subtle shine, white background, simple background"
  matte_method: segment
  segment_model: u2net
  max_prompt_tokens: 0
  negative_prompt: "sticker, white border, die-cut outline, dark, gloomy, grimdark, horror, magic circle, mandala, halo ring, washed out, desaturated, photograph, 3d render, drop shadow, text, watermark, logo, frame, border, busy background, multiple objects, gradient background"
```

## Màu bằng lời

```yaml
element_paint:
  fire:        "red and orange with a white-hot core"
  frost:       "pale cyan and white"
  lightning:   "deep electric blue with a white core"
  arcane:      "violet purple with a pale pink core"
  hostile:     "acid green"
  environment: "warm amber gold"

element_color:
  fire:        "red and orange"
  frost:       "pale cyan and white"
  lightning:   "deep electric blue"
  arcane:      "violet purple"
  hostile:     "acid green"
  environment: "warm amber gold"
```

## Hình dùng chung (tuỳ chọn)

Icon trong `icons.yaml` có thể dùng `subtype: <khoá>` thay cho `prompt:` để nhiều icon dùng chung một mô tả.

```yaml
subtype_shape:
  projectile: "magic energy arrow streaking up, trailing sparks"
  beam:       "diagonal lance of energy, glowing core"
```
