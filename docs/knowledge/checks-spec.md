# Art Direction: SKYBORNE — "Golden Hour Witch"

*Created: 2026-08-13*
*Hướng: **anime dễ thương** (đổi 2026-08-27 — xem §3)*
*Status: **Draft v0** — chưa hiệu chuẩn. Mọi ngưỡng số là ước lượng ban đầu, sẽ chỉnh sau vòng anchor đầu tiên.*
*Closes: `/art-bible` task trong `game-concept.md` §Next Steps*

---

## Cách đọc tài liệu này

Tài liệu có **hai người đọc**: bạn, và pipeline sinh asset.

- **Văn xuôi** giải thích *vì sao* — dành cho người.
- **Khối `yaml`** là **nguồn chân lý duy nhất** — pipeline parse trực tiếp từ đây.

Khi văn xuôi và khối YAML mâu thuẫn, **YAML thắng**, và văn xuôi là bug cần sửa. Không có bản sao thứ hai của những con số này ở bất kỳ đâu — đó là điểm mấu chốt: art direction trôi được là vì nó tồn tại ở hai nơi và hai nơi lệch nhau.

```yaml
spec:
  version: 0.3.0               # 0.3.0 thêm tầng 2 (judge_labels, model), hạ ngưỡng độ phủ
  direction_name: "Golden Hour Witch"
  authoritative: yaml_blocks_only
  calibrated: false          # true sau khi chốt anchor và hiệu chuẩn ngưỡng
```

---

## 1. Phạm vi

v0 chỉ quản **icon** (spell / modifier / relic / item). UI, ảnh VFX, concept board sẽ thêm sau khi vòng icon chạy trơn.

> **Ranh giới với `art-bible.md` (thêm 2026-08-15).** World, VFX, environment, character và HUD do
> [`design/art/art-bible.md`](../art/art-bible.md) sở hữu — tài liệu này là spec của **pipeline sinh icon**.
> Hai thứ ràng buộc **cả hai** tài liệu: **bảng màu §3** và **màu viền `outline` §4**.
> `art-bible.md` §4C/§4D từng chép lại bảng màu và đã hoá đá — nay đã gỡ, trỏ ngược về đây.
> Đừng chép số màu sang bất kỳ file nào khác.

```yaml
scope:
  active:   [icon_spell, icon_modifier, icon_relic, icon_item]
  planned:  [ui_frame, ui_button, ui_panel, hud_bar, vfx_flipbook, vfx_glow, vfx_noise, concept_moodboard]
  excluded: [character_mesh, animation]   # chờ khảo sát khả thi 3D
```

---

## 2. Nguyên tắc gốc (kế thừa từ game-concept.md)

1. **Luật 0.5 giây** — mọi thứ trên màn hình phải đọc được trong nửa giây. Đây là luật *gác cổng*: một asset đẹp mà chậm đọc là asset hỏng.
2. **Sky as stage** — môi trường ấm (hổ phách/vàng/san hô) làm nền; tín hiệu gameplay nổi lên bằng độ bão hoà và lõi sáng, không bằng chi tiết.
3. **VFX là centerpiece** — ngân sách hình ảnh dồn vào trời, mây, spell. Đảo và prop cố tình đơn giản.
4. **Cel-shade có viền** — mảng màu phẳng chia bậc, viền nét quanh vật thể. Chọn vì hai lý do: hợp nguồn cảm hứng anime, và **kiểm được bằng máy** (bậc màu hữu hạn, viền đo được, bảng màu đóng).

---

## 3. Bảng màu

Năm vai trò tín hiệu, cách nhau đủ xa trên vòng màu để phân biệt được ở cỡ 64px.

**Sửa 2026-08-27 — chuyển sang tông dễ thương.** Bảng cũ chọn màu gắt, viền gần đen, trung tính xám tối: nó cho ra icon *nặng và u ám*, đúng thứ vừa bị bác. Bản này giữ nguyên **sắc độ** (cột `hue` không đổi, nên năm vai trò vẫn cách nhau đủ xa) nhưng **nâng độ sáng, hạ độ bão hoà**, và đổi viền từ `#17121C` gần-đen sang `#4A3A52` tím-nâu mềm. Đây là đổi *tông*, không phải đổi *hệ thống tín hiệu* — Fire vẫn là Fire.

| Vai trò | Sắc độ | Vì sao |
|---|---|---|
| Fire | ~8° đỏ tươi, lõi trắng nóng | Đẩy khỏi vùng hổ phách của trời |
| Frost | ~190° lơ nhạt + trắng | |
| Lightning | ~235° chàm điện, lõi trắng | Tách hẳn khỏi Frost — GDD cũ để cả hai ở vùng "xanh", không phân biệt được |
| Arcane | ~292° tím hồng | |
| **Hostile** (đạn địch) | ~95° xanh lá độc | Vùng duy nhất còn trống, không đụng hệ nào của người chơi |
| *Environment* | ~36° hổ phách | Nền, **không phải** tín hiệu |

```yaml
palette:
  fire:        { main: "#FF7A5C", core: "#FFEFD9", shadow: "#D0503A", hue: 8 }
  frost:       { main: "#7FE3F5", core: "#F0FCFF", shadow: "#3E9CC4", hue: 190 }
  lightning:   { main: "#6C7BF0", core: "#FFFFFF", shadow: "#3A46A8", hue: 235 }
  arcane:      { main: "#D98BF0", core: "#FCEEFF", shadow: "#8E4FB0", hue: 292 }
  hostile:     { main: "#9BEE63", core: "#E4FFCB", shadow: "#4E9B34", hue: 95 }
  environment: { main: "#FFC978", core: "#FFE6B5", shadow: "#D19553", hue: 36 }
  outline:     "#4A3A52"       # tím-nâu mềm, KHÔNG dùng đen — đen làm icon nặng và tối
  neutral:
    light:  "#FBF6EF"
    mid:    "#B9B2BE"
    dark:   "#5A5162"

palette_policy:
  closed: true                 # mọi mảng màu phải khớp một mục ở trên, trong sai số
  delta_e_tolerance: 24        # CIE76; nới 2026-08-27 cùng lúc với enforcement: light
  min_conforming_pixel_ratio: 0.55
  scored_on: flat_field_interior   # bỏ pixel giáp ranh hai màu — xem ghi chú dưới
  interior_min_sample_ratio: 0.15  # dưới mức này thì không đủ mẫu để kết luận
```

**Vì sao chỉ chấm lòng mảng màu.** Khử răng cưa trộn hai màu hợp lệ thành một màu không hợp lệ dọc mọi đường biên. Chấm toàn bộ pixel đục thì con số thu được đo *icon có bao nhiêu chu vi*, chứ không đo nó có tuân bảng màu hay không — và mức phạt tỉ lệ thuận với chu vi trên diện tích, tức là phạt nặng đúng những hình mảnh mà §5 đã kết luận là hợp lệ. Đo trên một fixture đúng chuẩn: **100%** pixel bị coi là vi phạm nằm trên đường biên, **0** pixel nằm trong lòng mảng.

Một pixel chỉ được tính khi nó và cả bốn pixel kề đều đục và cùng nhận một mục bảng màu là gần nhất. Vùng màu sai thật vẫn bị bắt: các pixel trong vùng đó vẫn "đồng thuận" nên vẫn được chấm, và ΔE lớn ở đó làm nó trượt. Nếu tỉ lệ pixel-trong-lòng tụt dưới `interior_min_sample_ratio` thì phép kiểm **báo không đủ mẫu**, không im lặng cho qua.

> **Rủi ro đã biết:** Fire (8°) và environment (36°) chỉ cách 28°. Trên nền trời hoàng hôn, spell lửa có thể chìm. Đối sách: Fire bắt buộc có **lõi trắng nóng** và độ bão hoà cao hơn nền. Vòng anchor đầu tiên phải kiểm riêng ca này.

> **Đụng GDD:** `game-concept.md` §Color philosophy hiện ghi *"đạn enemy: bright red/orange"*. Bản này thay bằng xanh lá độc để trả đỏ/cam về cho hệ Fire của người chơi. GDD cần cập nhật khi bảng màu được chốt.

---

## 4. Luật tô bóng

> **Phạm vi (thêm 2026-08-15).** Khối `shading` dưới đây là luật cho **icon 2D phẳng**. World VFX kế thừa
> có chọn lọc:
> - ✅ **kỷ luật bậc màu** — nhưng áp trên **trục thời gian** (kill beat của boss rút màu theo 4 bậc rời
>   rạc thay vì fade; xem `boss-system.md` V-6)
> - ✅ **màu viền `outline` `#17121C`** — diễn đạt lại thành **độ rộng screen-space**, không phải `width_px_at_512`
> - ❌ **KHÔNG** `width_px_at_512` — vô nghĩa trong không gian thế giới
> - ❌ **KHÔNG** `gradients_allowed: false` — particle additive bản chất là gradient; điều khoản này nếu
>   áp cho world sẽ cấm **mọi** VFX trong game
>
> Ghi ra đây vì nếu không, sẽ có người trích §4 để bác một VFX hoàn toàn đúng.

```yaml
shading:
  model: cel
  enforcement: light           # light = chỉ ép viền + nền trong suốt, GIỮ nét vẽ của máy sinh
  value_steps: 4
  emissive_step: 1             # thêm 1 bậc phát sáng cho lõi (tuỳ chọn)
  max_distinct_values: 24      # đủ rộng cho tô bóng anime; vẫn chặn ảnh chụp/3D render
  gradients_allowed: true      # đổi 2026-08-27: xem ghi chú dưới
  outline:
    enabled: true
    width_px_at_512: 9         # ≈1px khi thu về 64 — dưới ngưỡng này viền biến mất
    color: "#17121C"
    style: uniform             # dày đều, không biến thiên theo nét vẽ
```

Lý do `value_steps` từng để ở 3: đủ để tả khối, ít đủ để hai asset sinh cách nhau ba tháng vẫn trông cùng một bộ. Đổ bóng mượt là chỗ trôi phong cách xảy ra nhanh nhất.

**Sửa 2026-08-27 — `enforcement: light`.** Luật trên đúng về nguyên tắc nhưng sai về hệ quả: `stylise` dập MỌI ảnh về ba mảng phẳng, nên máy sinh vẽ đẹp cỡ nào cũng ra một icon phẳng, cứng, "trông AI". Đo được: cùng một mẻ Animagine, ảnh gốc trông mềm và có chất liệu, ảnh sau khi ép thì không dùng được. Từ nay chỉ ép hai thứ **không thương lượng** — nền trong suốt và viền tối — còn tô bóng để nguyên như máy sinh vẽ.

Cái mất phải nói rõ: bộ kiểm **không còn bảo đảm đồng bộ phong cách** nữa. `palette_conformance` và `value_step_count` giờ chỉ chặn ca thô bạo (ảnh chụp, 3D render, sai hẳn hệ màu), không còn là hàng rào chống trôi. Đồng bộ từ nay dựa vào việc dùng **cùng một checkpoint + cùng prompt_prefix** cho cả bộ, và vào mắt người duyệt.

---

## 5. Đặc tả icon

```yaml
icon:
  canvas:        { width: 512, height: 512, format: "PNG", channels: "RGBA" }
  background:    transparent          # không khung vẽ sẵn — khung do UI Toolkit vẽ
  safe_margin_pct: 8                  # không có pixel đục trong lề này
  silhouette_coverage_pct: [8, 75]    # chặn trên/dưới cho tỉnh táo, KHÔNG phải luật phong cách
  display_sizes: [128, 64]
  readability_reference_size: 64      # mọi luật đọc-được chấm ở cỡ này
  export:
    - { size: 512, suffix: "_src" }   # bản gốc, lưu để sinh lại
    - { size: 128, suffix: "" }       # bản dùng trong game
```

Nền trong suốt, không khung: khung đổi kiểu lúc nào cũng được mà không phải sinh lại toàn bộ icon. Đây là quyết định *chống trôi*, không phải quyết định thẩm mỹ.

**Nhưng máy sinh không cho ra nền trong suốt.** Nên khâu sinh phải yêu cầu một nền phẳng rồi cắt bỏ. Màu nền đó là tham số kỹ thuật, không phải lựa chọn thẩm mỹ, và nó phải cách xa **mọi** màu trong bảng — bất kỳ pixel nào của chủ thể nằm gần màu nền đều có nguy cơ bị cắt nhầm thành lỗ thủng.

**Sửa 2026-08-25 — bỏ khoá màu, chuyển sang nhận dạng chủ thể.** Cách trên tách sạch nhưng hỏng ở khâu trước đó: ra lệnh "nền hồng" thì máy sinh **nhuộm hồng vào chính vật thể**. Đo trên ba mẻ (sd-turbo, SDXL+2 LoRA, SDXL trần), `palette_conformance` thô lần lượt 0.583 / 0.261 / thấp — đồng tiền vàng ra hồng, thỏi thép xanh-xám cũng ra hồng. Đổi model không chữa được vì lỗi nằm trong câu prompt. Từ nay `matte_method: segment`: prompt không nhắc màu nền nữa, khâu tách dùng `rembg`. `backdrop_hex` / `backdrop_name` giữ lại để chạy lại được các mẻ cũ và để quay về khi máy render không có rembg.

```yaml
generation:
  # Từ kích hoạt của LoRA vẽ vector (DD-vector-v2) + ba từ điều khiển của chính nó, ánh xạ
  # 1-1 sang ba luật của §4: outlines = viền, simple details = đọc được ở 64px,
  # solid color background = một nền phẳng cho khâu tách. ĐỨNG ĐẦU prompt vì CLIP cắt đuôi.
  # Tiền tố cho Animagine XL 4.0: model này huấn luyện theo thẻ chất lượng kiểu danbooru,
  # và "masterpiece / best quality" là cách nói chuẩn của nó. ĐỪNG để lẫn từ kích hoạt của
  # LoRA vector ở đây — "vector, outlines, simple details" kéo thẳng về mảng phẳng.
  prompt_prefix: "masterpiece, cute chibi anime game icon,"
  # Ba yêu cầu gộp vào đây: lộng lẫy (ornate, filigree), đậm nét (thick black outline,
  # high contrast), đồng bộ (cùng góc nhìn + cùng nguồn sáng cho CẢ bộ — đây là thứ giữ
  # 21 icon trông cùng một bộ, sau khi bộ kiểm không còn bảo đảm đồng bộ nữa).
  # Về đúng tông của mẻ cute1: pastel mềm, hình tròn mập, tô bóng đơn giản. "ornate gold
  # filigree, sparkles" đã thử và bị bác — quá nhiều chi tiết, quá sặc sỡ. Chỉ thêm
  # "subtle shine" để mặt vật liệu có chút phản quang, không thêm gì nữa.
  style_phrase: "soft pastel colours, rounded chunky shape, thick clean outline, simple shading, subtle shine"
  matte_method: segment       # tách nền bằng nhận dạng chủ thể (rembg/U²-Net), không khoá màu
  backdrop_hex: "#FF0F87"      # ΔE tối thiểu tới bảng màu = 59.4, gần 5× dung sai 12
  backdrop_name: "hot pink"    # TỪ cho máy sinh — nó không đọc được mã hex
  backdrop_rationale: "quét lưới RGB, chọn màu tối đa hoá khoảng cách ΔE nhỏ nhất tới bảng màu"
  matte_tolerance_delta_e: 14  # bán kính coi một pixel là nền, đủ rộng cho vân nhiễu của máy sinh
  max_prompt_tokens: 77        # giới hạn CỨNG của bộ mã hoá chữ CLIP trong SD/SDXL
  # Chỉ dùng được với provider chạy local (ComfyUI / diffusers). API kiểu flux-schnell
  # không nhận negative prompt — ở đó câu này bị bỏ qua, không phải bị nuốt im lặng.
  negative_prompt: "sticker, white border, die-cut outline, dark, gloomy, grimdark, horror, magic circle, mandala, halo ring, washed out, desaturated, photograph, 3d render, drop shadow, text, watermark, logo, frame, border, busy background, multiple objects"

# Màu bằng CHỮ, cho máy sinh. Mã hex ở §3 là để KIỂM, không phải để VẼ.
element_paint:
  Fire:      "red and orange with a white-hot core"
  Frost:     "pale cyan and white"
  Lightning: "deep electric blue with a white core"
  Arcane:    "violet purple with a pale pink core"
neutral_paint: "polished silver and steel"
```

> **77 token — đo được, không phải phỏng đoán.** Bản prompt dài đầu tiên là **182 token**; SD-turbo cắt cụt ở 77 và **im lặng** vứt đúng hai thứ sống còn nằm ở cuối câu: mã màu và lệnh nền phẳng. Ảnh sinh ra có nền `#2F7274` loang lổ thay vì `#FF0F87` phẳng, tức khâu tách nền mất cơ sở. Vì thế prompt có **hai dạng**: `short` (mặc định, cho SD/SDXL) và `long` (cho model dùng T5 như FLUX, ngữ cảnh 512 token). Dạng `short` xếp theo thứ tự quan trọng — hình, màu, nền, rồi mới tới phong cách — vì thứ bị cắt luôn là thứ đứng cuối.

> Đừng dùng xanh lá làm nền dù đó là thói quen phim ảnh: hệ `hostile` đã chiếm vùng xanh lá, nên nền xanh sẽ lem vào chủ thể và bước tách nền sẽ ăn mất đạn địch.

**Về `silhouette_coverage_pct`** — v0 đặt [45, 70] và chạy thử cho thấy đó là sai lầm về *loại*: một vòng tròn nội tiếp vùng an toàn chiếm ~55%, còn một thanh kiếm mảnh chỉ ~20%, và cả hai đều đúng phong cách. Độ phủ không phải luật phong cách; nó chỉ đủ sức bắt hai ca hỏng thô: icon gần như rỗng, và icon tràn kín khung. Độ chặt theo từng hình dáng thuộc về tầng 2 (đọc ra đúng subtype), không thuộc về một con số duy nhất cho mọi icon.

*Hạ ngưỡng dưới 18 → 8 (2026-08-15), theo số đo.* Dựng cả **năm** subtype của §6 rồi cho qua đúng đường matte, độ phủ đo được: Projectile 13.4% · Bounce 14.2% · AoE 12.5% · Orbit 11.1% · Beam 11.4%. Ngưỡng 18 đang **loại 5/5 hình do chính tài liệu này quy định** — con số 20% cho "thanh kiếm mảnh" ở đoạn trên là ước lượng bằng mắt, và nó sai. 8% vẫn bắt được icon rỗng (8% của 512² ≈ 21k pixel, không thể nhầm với trống).

*Đổi cách đếm bậc sáng (2026-08-17), theo số đo.* Bản cũ đếm **ô histogram**, và thứ nó thật sự đo là *màu nằm gần mép ô hay giữa ô*: `outline` (L\*6.3) với `neutral.dark` (L\*15.3) rơi hai ô kề nhau, phần chuyển giữa chúng thắp ô thứ ba — nên một modifier neutral **hợp lệ** bị báo 6 bậc, trong khi icon Fire hợp lệ báo 4 chỉ vì các giá trị của Fire tình cờ rơi giữa ô. Nay đếm theo *phủ đỉnh tham lam*: lấy mức sáng nặng nhất, gộp mọi thứ trong ±`value_merge_delta_lstar` vào cùng một bậc, lặp tới khi giải thích được `value_coverage_target` số pixel. Đó chính là luật cel phát biểu thẳng — vài mảng phẳng giải thích hết icon. Đo trên fixture: neutral/fire/frost/AoE đều đúng **4**, gradient cần **6**. Hai cách sửa khác đã thử và **bỏ**: lọc chỉ pixel đúng bảng màu, và gom cụm ΔL\*8 — cả hai đều làm **gradient lọt qua**.

*Đổi cách đo tương phản (2026-08-20), theo số đo.* Bản cũ dùng **4.5:1** trên **trung bình độ sáng** của toàn icon, và cả hai vế đều sai loại. 4.5:1 là ngưỡng WCAG cho **chữ**; với đồ hoạ và thành phần giao diện, WCAG 1.4.11 quy định **3:1**. Còn trung bình độ sáng thì bị chính luật viền của tài liệu này kéo xuống: viền 9px màu `#17121C` chiếm phần đáng kể diện tích, nên một icon có ruột sáng rõ vẫn báo tương phản thấp. Người đọc ra icon bằng **hình**, không bằng độ sáng trung bình — nên đo ở **phân vị 90**, tức phần sáng nhất có diện tích đáng kể.

Đo trên mẻ 63 ảnh thật: luật cũ cho **13/63** đạt, luật mới cho **48/63**. Chênh lệch đó gần như toàn bộ là icon hợp lệ bị loại oan chứ không phải icon hỏng được cho qua — kiểm bằng mắt trên tập đạt thêm. Đây **là** hạ ngưỡng so với v0.3, và ghi ra đây để lần sau không ai tưởng nó luôn là 3:1.

**Về kích thước ảnh đem kiểm** — mọi ngưỡng ở đây tính trên **bản gốc 512**, không phải bản xuất 128/64. Chạy bộ kiểm trên bản đã thu nhỏ cho kết quả sai (viền 9px co thành 1px rồi biến mất khi lọc). Bộ kiểm phải từ chối ảnh không đúng cỡ canvas thay vì âm thầm chấm sai.

---

## 6. Ngôn ngữ hai trục

Icon phải nói **hai** điều. Người chơi chỉ học 4 màu + 5 hình, đọc được 20 tổ hợp.

```yaml
axes:
  color_means: element
  shape_means: spell_subtype

element_color:
  Fire:      fire
  Frost:     frost
  Lightning: lightning
  Arcane:    arcane

subtype_shape:
  Projectile: "magic energy arrow streaking up, trailing sparks"
  Bounce:     "crackling bolt forking between three points"
  AoE:        "energy bursting outward in shockwave rings"
  Orbit:      "three glowing orbs circling a bright core"
  Beam:       "diagonal lance of energy, glowing core"
  Summon:     "small winged spirit familiar with glowing eyes"
  Zone:       "glowing rune circle on the ground with rising sparks"
```

> **Vì sao các chuỗi trong khối yaml viết bằng tiếng Anh** trong khi cả tài liệu là tiếng Việt: những chuỗi này đi **nguyên văn** vào prompt gửi cho máy sinh. FLUX/SDXL huấn luyện gần như toàn bộ trên caption tiếng Anh — mô tả hình bằng tiếng Việt sẽ bị hiểu lệch, và ta sẽ trả tiền cho những icon sai hình mà không biết vì sao. Văn xuôi quanh nó vẫn là tiếng Việt vì người đọc là Bi. Luật chung: **chuỗi nào chảy vào prompt thì tiếng Anh, còn lại tiếng Việt.**

**Vì sao tách hai trục:** máy chấm được từng trục riêng. Sai màu là một lỗi, sai hình là một lỗi khác — báo được cụ thể *"icon này đọc ra Frost nhưng khai là Fire"*, thay vì một điểm số mơ hồ.

---

## 6b. Modifier — trục riêng, cố tình không có màu hệ

Modifier gắn được vào **bất kỳ** spell nào. Tô nó bằng một màu hệ là nói dối: người chơi đọc "Overcharge màu đỏ" thành "Overcharge là đồ hệ Fire", trong khi cắm vào FrostLance nó chạy y hệt. Nên thân modifier dùng **neutral** — và chính việc *vắng màu hệ* là tín hiệu: "cái này không thuộc hệ nào, nó sửa spell của bạn".

Ba sự thật được mã hoá, cả ba đã có sẵn trong `ModifierData`, không phải khai thêm gì:

| Trục | Đọc ra | Lấy từ |
|---|---|---|
| Màu | *không* phải nguyên tố | cố định `neutral` |
| Hình | sửa **chỉ số nào** | `targetStat` |
| Biến thể | cộng thẳng hay nhân | `type` (Flat / Multiply) |

Vì sao cần trục thứ ba: có 8 modifier nhưng chỉ 6 `targetStat`, nên **Overcharge/Sharpen** (cùng Damage) và **Coolant/Efficiency** (cùng HeatCost) sẽ ra hình y hệt nhau. `type` tách đúng hai cặp đó, và nó là sự thật gameplay thật chứ không phải hoa văn bịa ra để phân biệt.

```yaml
modifier:
  body_color: neutral          # KHÔNG dùng element_color — modifier không thuộc hệ nào

modifier_stat_shape:
  Damage:          "glowing sword blade wrapped in sparks"
  ProjectileSpeed: "winged boot trailing wind"
  Duration:        "hourglass with glowing sand"
  HeatCost:        "frosted vial of blue coolant"
  BeamDrainRate:   "cracked crystal lens leaking light"
  BlastRadius:     "round bomb bursting into a wide ring of shockwave"
  BounceRange:     "spark jumping a long arc between two distant posts"
  MaxBounces:      "one spark zig-zagging off three small pegs in a row"
  BounceDamagePercent: "spark leaping between two posts, growing larger at the second"
  All:             "faceted prism gem radiating light"

# Modifier HÀNH VI (lớp con BehaviourModifierData) không sửa chỉ số nào — trục hình là chính
# hành vi. Khoá = tên lớp bỏ hậu tố `ModifierData`; artpipe tự dò danh sách lớp từ code, nên
# thêm lớp hành vi mới mà quên khai hình ở đây thì mẻ báo lỗi ngay, không ra icon đoán mò.
modifier_behaviour_shape:
  ElementShift:  "curved arrow looping back on itself, its head turned in a new direction"
  LingeringZone: "shallow ring on the ground with wisps of vapour rising from it"
  SplitShot:     "one arrow splitting into three diverging arrows"
  Seeker:        "arrow whose tip sits inside a small target reticle"
  ExtraSummon:   "two small spectral wolf heads side by side"
  ExtraOrb:      "ring of small orbs circling one central orb"
  Pierce:        "arrow passing clean through a thin wooden plank"

modifier_type_variant:
  Behaviour: "one single solid mark, centred in frame, no second copy and no arc"
  Flat:     "one single solid mark, centred in frame"
  Multiply: "two identical marks overlapping with an offset, the rear one one value step darker"
  AddPercent: "one solid mark with a partial arc wrapped around it, the arc left open at the top"
```

`AddPercent` ứng với `AddPercentModifierData` — lớp đã có trong code từ bản refactor
`fa61664` nhưng chưa asset nào dùng. Khai sẵn ở đây để modifier đầu tiên dùng nó không làm
chết cả mẻ. Cung hở phân biệt với `Multiply` (chồng hình) mà không cần đọc chữ số.

**Không mã hoá dấu (+/−) của giá trị.** Coolant *giảm* heat và đó là điều tốt; Overcharge *tăng* damage cũng là điều tốt. "Lên = tốt" sai ở nửa số ca, nên mũi tên lên/xuống sẽ dạy người chơi một luật không đúng. Chiều lợi/hại thuộc về tooltip, không thuộc về icon.

---

## 7. Bậc hiếm (item) và loại item

Bậc hiếm thể hiện bằng **quầng sáng ngoài**, không bằng khung, không bằng đổi màu chủ thể — để không đụng trục màu-nguyên-tố.

```yaml
rarity_glow:
  Common:    { radius_px_at_512: 0,  opacity: 0.0 }
  Uncommon:  { radius_px_at_512: 6,  opacity: 0.35 }
  Rare:      { radius_px_at_512: 12, opacity: 0.5 }
  Epic:      { radius_px_at_512: 18, opacity: 0.65 }
  Legendary: { radius_px_at_512: 26, opacity: 0.8 }

# Mô tả riêng cho từng món, tra theo displayName. Gợi ý theo LOẠI ở dưới chỉ còn là mức
# dự phòng: hai món cùng loại sẽ nhận cùng một mô tả và ra hai icon giống hệt nhau
# (Ancient Coin và Gold cùng ra một quả cầu vàng), còn món nào có tên rất cụ thể thì gợi ý
# chung lại tả sai hẳn (Stormcaller Blade bị tả là "vật thể hình học đối xứng").
item_shape_override:
  Ancient Coin:      "one worn gold coin stamped with a rune"
  Gold:              "heap of shining gold coins"
  Ether Draught:     "slender corked vial of glowing violet ether"
  Health Potion:     "round corked flask of glowing crimson liquid"
  Iron Ingot:        "dark grey cast iron bar"
  Skysteel Ingot:    "cast bar of pale blue glowing skysteel"
  Ancient Relic:     "round bronze amulet engraved with runes"
  Sealed Dispatch:   "rolled scroll with red wax seal"
  Stormcaller Blade: "sword with lightning-etched blade, winged crossguard"

item_category_hint:
  Misc:       "a neutral blocky object in muted neutral colours"
  Currency:   "a round coin shape with a metallic sheen"
  Consumable: "a flask or vial holding a glowing liquid"
  Material:   "a rough fragment with broken edges"
  Gear:       "a symmetrical, structured geometric object"
  Quest:      "a scroll or wax seal with an ornate border"
```

---

## 8. Bộ kiểm tuân thủ

Ba tầng, theo thứ tự rẻ → đắt. Asset trượt tầng rẻ thì không cần chạy tầng đắt.

Tham số mà tầng 1 cần. `ui_background_reference` là nền menu mà icon sẽ nằm lên — không có nó thì "độ tương phản" không có nghĩa, vì icon nền trong suốt tự nó không có tương phản với cái gì cả.

```yaml
readability:
  ui_background_reference: "#1A1520"   # nền menu tối; đổi nếu UI đổi
  min_contrast_ratio: 3.0              # WCAG 1.4.11 Non-text Contrast (đồ hoạ/thành phần UI)
  contrast_percentile: 90              # đo phần SÁNG NHẤT của icon, không phải trung bình
  edge_density_max: 0.18               # chi tiết vụn làm icon "bẩn" khi thu nhỏ
  outline_dark_lstar_max: 35           # L* tối đa để một pixel được tính là viền
  outline_band_min_ratio: 0.6
  value_merge_delta_lstar: 4           # hai màu cách nhau dưới ngần này L* đọc thành CÙNG một bậc
  value_coverage_target: 0.95          # số bậc phải giải thích được ngần này pixel trong lòng mảng
```

```yaml
checks:

  # Tầng 1 — tất định, chạy trên pixel, gần như miễn phí
  deterministic:
    - id: bg_transparent
      rule: "≥98% pixel viền canvas có alpha = 0"
      fatal: true
    - id: safe_margin
      rule: "không có pixel alpha>16 trong lề 8%"
      fatal: true
    - id: silhouette_coverage
      rule: "tỉ lệ pixel đục nằm trong icon.silhouette_coverage_pct"
      fatal: true
    - id: palette_conformance
      rule: "≥95% pixel TRONG LÒNG mảng màu nằm trong ΔE≤12 của một màu trong palette"
      fatal: true
    - id: value_step_count
      rule: "≤4 mức phẳng là đủ giải thích 95% pixel trong lòng mảng màu"
      fatal: false
    - id: outline_present
      rule: "phát hiện được viền tối liên tục quanh silhouette, dày ≥7px"
      fatal: false
    - id: readable_at_64
      rule: "thu về 64px, độ tương phản silhouette/nền ≥ 4.5:1 và mật độ cạnh ≤ ngưỡng nhiễu"
      fatal: true

  # Tầng 2 — model chấm. Chạy trên CPU máy dev, KHÔNG cần GPU hay API.
  model_judged:
    - id: style_similarity
      metric: "cosine similarity embedding DINO ViT-B/8 so với bộ anchor"
      model: "facebook/dino-vitb8"
      threshold: 0.82           # TẠM — hiệu chuẩn sau vòng anchor
      fatal: true
    - id: element_readability
      metric: "CLIP zero-shot trên 4 nhãn nguyên tố"
      model: "openai/clip-vit-base-patch32"
      rule: "argmax phải khớp element đã khai, biên ≥ min_margin"
      min_margin: 0.05
      fatal: true
    - id: subtype_readability
      metric: "CLIP zero-shot trên nhãn hình dáng (spell/modifier/item)"
      model: "openai/clip-vit-base-patch32"
      rule: "argmax phải khớp nhãn hình đã khai"
      fatal: false

  # Tầng 3 — người
  human:
    trigger: borderline_only
    borderline_band: [0.78, 0.86]   # theo style_similarity
    target_review_rate_pct: 15      # nếu vượt, ngưỡng đang sai — hiệu chuẩn lại
```

### Caption cho model chấm (tầng 2)

Ban đầu tầng 2 dùng **lại chính** câu mô tả đã gửi cho máy sinh, với lý lẽ nghe rất xuôi: hỏi người chấm đúng thứ đã dặn người vẽ. Đo thử thì lý lẽ đó sai — CLIP zero-shot đọc cụm danh từ ngắn tốt hơn hẳn câu tả dài. Trên cùng bộ fixture: trục hình **3/5 → 4/5**, trục màu **2/4 → 3/4** chỉ nhờ đổi cách viết caption.

Nên có hai bộ chữ cho cùng một khái niệm, và đó **không** phải trùng lặp: một bộ để *ra lệnh vẽ*, một bộ để *hỏi có đọc ra không*. Chúng phục vụ hai mô hình khác nhau với hai điểm mạnh khác nhau.

```yaml
judge_labels:
  element:
    Fire:      "a red and orange flame"
    Frost:     "a pale cyan ice crystal"
    Lightning: "a deep blue electric bolt"
    Arcane:    "a purple magic sigil"
  spell_subtype:
    Projectile: "an icon of an arrow"
    Bounce:     "an icon of a zigzag line"
    AoE:        "an icon of concentric circular rings"
    Orbit:      "an icon of small orbs orbiting"
    Beam:       "an icon of a long straight laser beam"
  modifier_stat:
    Damage:          "an icon of a spearhead"
    ProjectileSpeed: "an icon of speed streaks"
    Duration:        "an icon of an hourglass"
    HeatCost:        "an icon of a droplet"
    BeamDrainRate:   "an icon of an arc with two bars"
    All:             "an icon of a hexagon"
  item_category:
    Misc:       "an icon of a plain block"
    Currency:   "an icon of a gold coin"
    Consumable: "an icon of a potion bottle"
    Material:   "an icon of a rough ore fragment"
    Gear:       "an icon of a weapon or armour piece"
    Quest:      "an icon of a paper scroll"
```

### Tầng 2 đo được gì (2026-08-15)

Dựng 9 fixture tổng hợp — 4 màu × hình Projectile, và 5 hình × màu Fire — rồi chấm:

| | Kết quả |
|---|---|
| Khai **đúng** đọc ra đúng nhãn | **8/9** (chỉ Lightning sai, xem AD-8) |
| Khai **sai** bị bắt, **đúng trục** | **9/9** |

Vế thứ hai mới là vế quan trọng. Độ chính xác trên fixture tổng hợp phần lớn nói về tay vẽ của fixture; thứ bắt buộc phải đúng là **bác được nhãn sai, và bác đúng trục** — sai màu báo là sai màu, sai hình báo là sai hình.

Model: **CLIP ViT-B/32**. Đã thử ViT-L/14 (to gấp ~6 lần): trục hình **tệ hơn** (3/5 so với 5/5), trục màu ngang nhau. To hơn không đồng nghĩa hợp hơn cho tranh phẳng ít chi tiết.

**Trong lúc `spec.calibrated: false`, mọi kết quả tầng 2 chỉ là tư vấn**, không chặn. Tài liệu này tự khai ngưỡng chưa hiệu chuẩn, nên dùng nó làm cổng chặn là tự mâu thuẫn — và cụ thể: nếu để `element_readability` fatal ngay bây giờ thì **mọi** icon Lightning sẽ bị loại vĩnh viễn, một cổng luôn từ chối một hệ còn tệ hơn không có cổng, vì cái sai trông giống một phán quyết.

**Ngưỡng là phỏng đoán.** Chúng chỉ có nghĩa sau khi có anchor thật. Cách hiệu chuẩn: chấm chính bộ anchor bằng bộ kiểm này; anchor phải đạt gần trần, và tỉ lệ cần người duyệt phải rơi về khoảng 15%.

---

## 9. Hồ sơ xuất xứ

Ghi cho **mọi** asset được sinh, kể cả asset bị loại. Rẻ, và trả về ba thứ: sinh lại được, hồ sơ pháp lý, và dữ liệu đo trôi phong cách theo thời gian.

```yaml
provenance_record:
  asset_path:      string
  target_guid:     string        # GUID của SpellData/ItemDefinition mà icon này phục vụ
  spec_version:    string        # version của chính file này
  anchor_set_id:   string
  provider:        string        # fal | together | replicate | local
  model_id:        string
  model_version:   string
  prompt_hash:     string
  prompt_full:     string
  seed:            integer
  generated_at:    iso8601
  scores:          map            # mọi check ở §8 và điểm số của nó
  verdict:         enum[auto_accept, human_accept, human_reject, auto_reject]
  human_note:      string?
```

---

## 10. Còn treo

| # | Câu hỏi | Chặn cái gì |
|---|---|---|
| AD-1 | Anchor chưa tồn tại — cần sinh 6–8 phương án để Bi chọn | Toàn bộ tầng 2 của bộ kiểm |
| AD-2 | Mọi ngưỡng ở §8 chưa hiệu chuẩn | Tỉ lệ duyệt tay thực tế |
| AD-3 | Fire (8°) sát environment (36°) — chưa kiểm trên nền trời thật | Bảng màu có thể phải dịch |
| ~~AD-4~~ | ~~`game-concept.md` còn ghi đạn địch đỏ/cam~~ — **đóng 2026-08-14**. Sửa luôn một mâu thuẫn thứ hai không nằm trong AD-4: bản cũ chốt "player spell: blue-violet spectrum" trong khi người chơi có hệ Fire ấm | — |
| AD-5 | Không phải thiếu khoá mà là **không đâu còn tiền**: fal.ai bị khoá vì hết số dư, Replicate 402, và sinh ảnh Gemini **không có hạng miễn phí trên bất kỳ model nào** (`limit: 0` — gói Google AI Pro không cấp hạn mức API). Chạy local bất khả thi (M2 8GB RAM, ~4GB đĩa trống). Bi chốt sẽ nạp Replicate nhưng hiện chưa có ngân sách. Ngả miễn phí thật còn lại: GPU T4 của Google Colab | Khâu sinh — chặn AD-1, do đó chặn AD-2 |
| AD-6 | 3D/animation 100% bằng AI — chưa khảo sát khả thi | Phạm vi pipeline giai đoạn 2 |
| **AD-8** | **Lightning (236°) bị model đọc thành Arcane (287°)**, 82% tin cậy. Đổi caption không cứu được: viết "blue" cho Lightning thì Frost (190°) bị kéo theo — tức nửa lạnh của bảng đang chen 3 mục trong 97°, trong khi nửa ấm chỉ có Fire (8°). Chưa đủ căn cứ để đổi bảng màu: đây là một model đặt tên màu thô, trên fixture tổng hợp. Vòng anchor phải kiểm riêng ca Lightning↔Arcane đúng như AD-3 kiểm Fire↔environment | `element_readability` cho hệ Lightning; ArcShard là spell Lightning duy nhất hiện có |

**AD-9 — `hostile` (95°) có người dùng thứ hai: mặt hazard của boss, ở diện tích màn hình lớn.** *(thêm 2026-08-15)*
Đối với nền trời tím giữa (§4B) thì tương phản tốt, nhưng đối với **dải hổ phách sát chân trời**, 95° và 36°
gần như bù nhau và sẽ **rung thị giác** trên một mặt phẳng lớn. Phase A của boss kết thúc hành trình hạ xuống
ở **+12m** — thứ hazard thấp nhất, sát chân trời nhất trong game. Kiểm cùng vòng anchor với AD-3 (Fire vs environment).
**Chặn:** tính đọc được của trần/sàn Phase A ở cao độ thấp. Xem `boss-system.md` BOSS-OQ-1/OQ-5.
