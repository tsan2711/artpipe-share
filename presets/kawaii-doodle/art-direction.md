# Preset: kawaii-doodle — icon "bánh bao" vẽ tay dễ thương

Phong cách: doodle kawaii vẽ tay — viền nâu tím dày như bút sáp, màu pastel phẳng không đổ bóng, vật có mặt chấm
+ má hồng, bóng bầu dục mờ dưới chân. Model: `animagine-xl-4.0-opt`. Màu viết dạng `(tên màu:1.3)` = nhấn trọng số (cú pháp ComfyUI). Tách nền: `rembg u2net`.

Hợp với: game casual / idle / cozy, icon tài nguyên, item, sticker, pet. Đọc rõ ở 64px nhờ viền dày.

**Chỉ các khối ```yaml là dữ liệu thật** — chữ ngoài khối là ghi chú cho người đọc.
Muốn đổi gu: copy cả thư mục preset này sang tên mới rồi sửa (đừng sửa tại chỗ preset đang dùng).

## Thông tin spec

```yaml
spec:
  version: "1.0.0"
  direction_name: "Kawaii Doodle"
```

## Bảng màu

`element` của mỗi icon trong `icons.yaml` = một khoá ở đây (gold, red, ...). Checker đọc mã hex;
máy sinh đọc câu tả ở `element_paint` (nó không hiểu mã hex).

```yaml
palette:
  gold:   { main: "#FFD36E", core: "#FFF1C2", shadow: "#E9AE4A", hue: 42 }
  red:    { main: "#FF9C9C", core: "#FFE0DC", shadow: "#E86C76", hue: 0 }
  blue:   { main: "#9CC8F5", core: "#E2F0FF", shadow: "#6E9FD8", hue: 210 }
  green:  { main: "#9EE3B2", core: "#E3FAE9", shadow: "#62BD84", hue: 140 }
  purple: { main: "#C6B2F2", core: "#F0E9FF", shadow: "#9A82D8", hue: 260 }
  pink:   { main: "#FFB3CF", core: "#FFE6F0", shadow: "#EE80A8", hue: 335 }
  outline: "#6A4F5E"
  neutral:
    light: "#FFF8EE"
    mid:   "#D9CCC2"
    dark:  "#8A7468"
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
    width_px_at_512: 12
    color: "#6A4F5E"
    style: uniform
```

## Khung icon

```yaml
icon:
  canvas: { width: 512, height: 512, format: "PNG", channels: "RGBA" }
  background: transparent
  safe_margin_pct: 8
  silhouette_coverage_pct: [10, 80]
  ground_shadow: { color: "#D8BFD0", opacity: 0.5 }   # bóng bầu dục dưới chân — xoá dòng này nếu không muốn
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
  prompt_prefix: "masterpiece, high score, great score, absurdres, no humans, kawaii doodle game icon, hand drawn,"
  style_phrase: "thick dark brown outline, flat colours, no shading, cute tiny dot eyes and blush, white background, simple background"
  matte_method: segment
  segment_model: u2net
  max_prompt_tokens: 0
  negative_prompt: "lowres, worst quality, low quality, low score, bad score, average score, blurry, jpeg artifacts, signature, watermark, username, text, logo, frame, border, gradient background, colorful background, busy background, gradient, shading, shadow, 3d, glossy, shiny, metallic, realistic, detailed, intricate, sparkles, black outline, sketch lines, multiple objects, multiple views, human, person, sticker, white border"
```

## Màu bằng lời

```yaml
element_paint:
  gold:   "(butter yellow colour:1.3)"
  red:    "(coral red colour:1.3)"
  blue:   "(sky blue colour:1.3)"
  green:  "(mint green colour:1.3)"
  purple: "(lilac purple colour:1.3)"
  pink:   "(pink colour:1.3)"

element_color:
  gold:   "butter yellow"
  red:    "coral red"
  blue:   "sky blue"
  green:  "mint green"
  purple: "lilac"
  pink:   "pink"
```

## Hình dùng chung (tuỳ chọn)

Icon trong `icons.yaml` có thể dùng `subtype: <khoá>` thay cho `prompt:` để nhiều icon dùng chung một mô tả.

```yaml
subtype_shape:
  coin: "one thick round gold coin with a star stamped in the middle"
  gem:  "one diamond shaped gemstone with big flat facets"
```
