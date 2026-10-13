# Điểm neo (anchor) — tư duy chung và cách từng game làm

**Điểm neo** = ảnh đã được người duyệt, được **khoá lại**, rồi mọi thứ sinh sau phải bám vào nó. AI không có trí nhớ
giữa hai lần sinh: hôm nay sinh 10 icon, tuần sau sinh thêm 5 → nếu không có gì neo, 5 cái sau là một bộ khác.
Neo là cách biến "một mẻ ảnh đẹp ngẫu nhiên" thành "một bộ art nhất quán, sinh thêm được".

## Bốn loại neo

| Loại | Neo cái gì | Ở đâu trong repo |
|---|---|---|
| **Neo phong cách** | gu chung của cả bộ: model, câu tả phong cách, bảng màu, viền, seed | `presets/<p>/` (+ `artpipe/themes/*.yaml`) — một preset = một gu, **không sửa tại chỗ**, đổi gu thì tạo preset mới |
| **Neo hình mẫu** | vài ảnh đã duyệt làm thước đo "đúng gu" | `docs/samples/<bộ>/`; trong spec June: `anchor_set_id` + `style_similarity` (tầng 2) |
| **Neo danh tính** | MỘT nhân vật trông thế nào — để mọi animation / mọi tư thế vẫn là nó | `anchor:` trong manifest `artpipe/anims/*.yaml` |
| **Neo khung so sánh** | cùng cảnh, cùng khung, cùng seed khi so nhiều hướng art | `docs/examples/thousandfold/prompts.md` |

Quy trình chung, cả ba game đều đi đúng thứ tự này:

```
1. Sinh ÍT, nhiều hướng (concept)  →  2. Người chọn  →  3. KHOÁ thành neo (file + seed + preset)
        ↑                                                         │
        └── hướng bị loại: ghi lý do (để không đi lại)              ▼
                                         4. Sinh hàng loạt BÁM neo  →  5. Chấm so với neo, lệch thì loại
```

Luật rút ra: **không sinh cả bộ trước khi có neo.** NanoSwarm đã bỏ ba bộ robot vì sinh full set trước khi chốt gu.

## June (Skyborne) — neo phong cách + neo hình mẫu để hiệu chuẩn bộ chấm

Nguồn: `docs/examples/june/art-direction.md` §8–9, `theme-cute-pastel.yaml`.

- **Spec tự khai "chưa hiệu chuẩn"**: `spec.calibrated: false` cho tới khi chốt bộ anchor. Mọi ngưỡng số trước đó là phỏng
  đoán, nên kết quả tầng 2 **chỉ tư vấn, không chặn**. Chặn bằng một ngưỡng chưa hiệu chuẩn là tự mâu thuẫn (đã thấy: để
  `element_readability` chặn thì mọi icon Lightning bị loại vĩnh viễn).
- **Hiệu chuẩn bằng chính anchor**: chấm bộ anchor bằng bộ kiểm — anchor phải đạt gần trần; tỉ lệ ảnh cần người duyệt phải
  rơi về ~15%. Vượt 15% nghĩa là ngưỡng sai, không phải AI tồi.
- **Tầng 2 so với anchor**: `style_similarity` = cosine embedding DINO ViT-B/8 giữa icon mới và bộ anchor (ngưỡng tạm 0.82,
  vùng người duyệt 0.78–0.86). Đây là cách máy biết "lệch gu" mà tầng 1 (nền, viền, màu) không thấy.
- **Chọn anchor ở đúng điều kiện dùng**: `sheet.html` đặt các biến thể cạnh nhau trên **màu nền UI thật**, ở **64px** —
  chọn ở 512px trên nền trắng là chọn sai.
- **Theme khoá luôn seed**: `seed = hash(theme, tên asset, biến thể)` thay cho số gõ tay → sáu tuần sau sinh lẻ một icon vẫn
  ra đúng thứ khớp bộ cũ. Mỗi ảnh ghi `theme` + `theme_fingerprint` vào provenance → nhìn report biết ngay asset nào là
  tàn dư của một lần đổi gu đã quên.

## NanoSwarm — neo danh tính bằng phác thảo + img2img, rồi chọn tay

Nguồn: `docs/examples/nanoswarm/gen_commander_ai.py`, `gen_frontline_art.py`, `explore-findings.md`.

- **Text-to-image đơn thuần làm mất thiết kế**: 12 Commander sinh từ chữ ra 12 cục na ná nhau, đồ cầm tay trôi mất, bóng nhựa
  — bị loại. Nên neo bằng **hình**: phác thảo vector của từng Commander (silhouette + màu + món đồ nói lên nghề) là neo.
- **img2img ở vài mức denoise** (0.45 / 0.6 / 0.72): thấp = giữ thiết kế, nét + chất liệu thành vẽ tay; cao = model vẽ nhiều
  hơn. Xuất một tấm so: hàng = Commander, cột = phác thảo + từng mức. **Người chọn một ô mỗi Commander** → ô đó thành
  `anchor.png` cho làn animation.
- **Concept trước, bộ đủ sau**: bộ gacha-chibi (Art B) bắt đầu bằng 3 hero đại diện (Fight / Support / Legend), chọn neo
  (`spark 2 · shell 1 · orrin 2`), rồi mới vẽ 9 con còn lại "khớp với neo": mỗi con **một** đặc điểm silhouette, màu thân
  lấy từ bảng dữ liệu game.
- **Tham chiếu phong cách bằng lời, không bằng tên**: gu "corner creature" được tả bằng đặc điểm (thân viên kẹo, không cổ,
  tay mẩu, mắt chấm thấp và xa, má hồng, nét nâu hơi run) — **không bao giờ** ghi tên game/studio/nhân vật tham chiếu trong prompt.
- **A/B hai bộ art cùng lúc** (set A bánh bao / set B gacha) trong game, người chơi thử rồi mới chốt — neo cấp cả game.

## Thousandfold — neo khung so sánh + đo trên nền thật

Nguồn: `docs/examples/thousandfold/prompts.md`, `art-direction.md`, `gen_keyart.py`, `style_frame.py`.

- **So hướng art bằng một khung cố định**: cùng cảnh (ngã tư nhỏ, nhìn chéo ~50°, bầy ~2000 con tràn từ góc dưới trái, robot
  khổng lồ ở giữa), cùng tỉ lệ 16:9, 2 seed mỗi hướng. Chỉ phần "hướng" thay đổi → so được công bằng A/B/C.
- **AI không vẽ được bầy 2000 con** → tách: máy vẽ MỘT con trên nền trơn + cảnh trống; code rắc ~2000 con thành một khối
  chảy (đúng cách game render), thử luôn cỡ 4–8 px.
- **Neo màu nền thế giới**: `readability.ui_background_reference: #7A7A80` (thế giới xám) — con vật được chấm độ tương phản
  trên đúng màu nó sẽ đứng, xem ở thumbnail 16px.
- **Bớt "mùi AI"**: style frame lấy cảnh AI → lọc trung vị + giảm bậc màu thành mảng phẳng; bầy là hạt vẽ bằng code theo
  trường dòng.

## Làn animation — neo danh tính ở mọi frame

Nguồn: `docs/knowledge/anim-lane.md`, `artpipe/anims/*.yaml`.

- **Một anchor cho mọi animation** của một nhân vật (`anchor:` trong manifest). Chưa có thì `anchor_gen` để Animagine vẽ,
  người duyệt, rồi **khoá** (ghi `anchor:`; `anchor_gen` giữ làm hồ sơ, chỉ chạy lại khi xoá dòng neo) — `test-adventurer.yaml`.
- **Vòng lặp khép bằng neo**: graph `anim_wan22_loop.json` ép frame đầu = frame cuối = anchor → idle/walk tự lặp liền.
- **Neo để chẩn đoán máy**: `smoke.yaml` dùng ảnh mẫu đã biết chắc cho ra walk/idle tốt (của mor-o) → máy mình ra rác thì
  lỗi ở máy/model/graph, không ở ảnh.
- **Wan sinh cả clip một lần** (các frame nhìn lẫn nhau). Cách cũ sinh từng frame bằng SDXL → mỗi frame một con khác
  (harvester 2026-09-22, manifest `nanoswarm-anim-harvester.yaml` để lại làm ví dụ cái sai).

## VFX — neo bằng hình vẽ, không bằng chữ

Nguồn: `docs/knowledge/lessons-vfx.md`, `vfx/`.

- Thử ComfyUI cho VFX: **~50% sai vật** (sét → gấu hồng, sóng xung kích → quả trứng có mặt) mà bộ chấm tầng 1 vẫn nhận
  112/112. Nên VFX flipbook **vẽ bằng code** (`vfx/`) — hình đúng tuyệt đối ở 20–60px.
- AI chỉ dùng cho VFX khi **có hình khởi đầu** (silhouette vẽ → img2img, hoặc frame khởi đầu nền đen → Wan, `test-vfx.yaml`)
  và bật chấm tầng 2.

## Áp vào dự án của bạn

1. Chọn / tạo preset (neo phong cách). Đừng sửa preset đã dùng — tạo bản mới.
2. Sinh 3–5 asset đại diện × 4 biến thể. Duyệt trên **nền UI thật, ở cỡ thật** (`sheet.html`).
3. Chép ảnh chọn vào `docs/samples/<bộ>/` (neo hình mẫu); ghi seed + prompt (có sẵn trong `prov/`).
4. Nhân vật cần animation: chép ảnh chọn thành `anchor.png` + manifest (neo danh tính).
5. Rồi mới sinh cả bộ. Lệch neo → sửa prompt/preset, không sinh lại mù.
