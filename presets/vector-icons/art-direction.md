# Preset: vector-icons — icon vector phẳng có viền

Phong cách: vector phẳng, mảng màu đặc, viền tối đều, ít chi tiết — kiểu icon kỹ năng / buff.
Model: SDXL base + LoRA `DD-vector-v2` (huấn luyện trên ảnh CC0). Tách nền: `rembg u2net`.

Hợp với: icon kỹ năng, spell, buff/debuff, bản đồ, UI phẳng. Đọc rõ ở 32–64px.
Lưu ý: từ khoá kích hoạt LoRA (`vector, outlines, simple details`) phải đứng ĐẦU prompt — đừng xoá.

**Chỉ các khối ```yaml là dữ liệu thật** — chữ ngoài khối là ghi chú cho người đọc.
Muốn đổi gu: copy cả thư mục preset này sang tên mới rồi sửa (đừng sửa tại chỗ preset đang dùng).

## Thông tin spec

```yaml
spec:
  version: "1.0.0"
  direction_name: "Vector Icons"
```

## Bảng màu

`element` của mỗi icon trong `icons.yaml` = một khoá ở đây (gold, red, ...). Checker đọc mã hex;
máy sinh đọc câu tả ở `element_paint` (nó không hiểu mã hex).

```yaml
palette:
  fire:      { main: "#FF3B1F", core: "#FFF3E0", shadow: "#B01000", hue: 8 }
  frost:     { main: "#4FD8F5", core: "#EAFBFF", shadow: "#1B7FA8", hue: 190 }
  lightning: { main: "#3A46E0", core: "#FFFFFF", shadow: "#1A1F80", hue: 235 }
  arcane:    { main: "#C64BE8", core: "#FBE3FF", shadow: "#6E1A85", hue: 292 }
  nature:    { main: "#6FE81F", core: "#D6FFA8", shadow: "#2E7A00", hue: 95 }
  holy:      { main: "#FFB74D", core: "#FFD98A", shadow: "#B8722A", hue: 36 }
  outline: "#17121C"
  neutral:
    light: "#F2ECE4"
    mid:   "#8A8290"
    dark:  "#2A2430"
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
  ui_background_reference: "#1A1520"
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
    width_px_at_512: 9
    color: "#17121C"
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
  prompt_prefix: "vector, outlines, simple details, game icon,"
  style_phrase: "flat 4-tone cel shading, bold dark outline, solid colours"
  matte_method: segment
  segment_model: u2net
  max_prompt_tokens: 77
  negative_prompt: "photograph, 3d render, gradient shading, soft airbrush, drop shadow, bloom, text, watermark, logo, frame, border, busy background, multiple objects, lowres, blurry"
```

## Màu bằng lời

```yaml
element_paint:
  fire:      "red and orange with a white-hot core"
  frost:     "pale cyan and white"
  lightning: "deep electric blue with a white core"
  arcane:    "violet purple with a pale pink core"
  nature:    "leaf green with a pale lime core"
  holy:      "warm amber gold with a cream core"

element_color:
  fire:      "red and orange"
  frost:     "pale cyan"
  lightning: "electric blue"
  arcane:    "violet purple"
  nature:    "leaf green"
  holy:      "amber gold"
```

## Hình dùng chung (tuỳ chọn)

Icon trong `icons.yaml` có thể dùng `subtype: <khoá>` thay cho `prompt:` để nhiều icon dùng chung một mô tả.

```yaml
subtype_shape:
  projectile: "magic energy arrow streaking up, trailing sparks"
  aoe:        "energy bursting outward in shockwave rings"
  orbit:      "three glowing orbs circling a bright core"
  beam:       "diagonal lance of energy, glowing core"
  zone:       "glowing rune circle on the ground with rising sparks"
  buff:       "upward arrow over a small shield, glowing"
```
