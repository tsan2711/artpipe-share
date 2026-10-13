# Quy trình làm asset với artpipe

```
 1. Chọn / tạo preset   →  2. Viết danh sách icon  →  3. Thử nhỏ (--only, 2 biến thể)
        ↑                                                      │
        └──── 6. Sửa PROMPT/PRESET, không sinh lại mù  ←── 4. Duyệt sheet.html
                                                               │
                                          5. Lấy best/ (hoặc chọn tay trong icons/) → đưa vào game
```

## 1. Chọn hoặc tạo preset

Preset = **một phong cách** (model + bảng màu + câu tả phong cách + luật chấm). Mọi icon của một game nên
dùng cùng một preset để đồng bộ.

Tạo preset riêng: copy nguyên thư mục `presets/_template` (hoặc preset gần giống nhất) sang `presets/<game-của-bạn>`, rồi sửa:

| File | Sửa gì |
|---|---|
| `art-direction.md` | `palette` (màu game) · `element_paint` (màu đó bằng lời) · `generation.prompt_prefix` / `style_phrase` (phong cách) · `readability.ui_background_reference` (màu nền UI) |
| `icons.yaml` | danh sách icon |
| `preset.yaml` | model (`checkpoint`, `downloads`), `variants`, `seed` |

**Đừng sửa tại chỗ một preset đã dùng để làm asset** — icon sinh trước và sau sẽ lệch nhau mà không ai nhận ra.
Muốn đổi gu → tạo preset mới. Thêm preset vào ô cấu hình notebook: sửa dòng `#@param [...]` trong
`tools/build_notebook.py` rồi chạy lại nó.

## 2. Viết danh sách icon

```yaml
- { name: Fire Sword, prompt: "one short sword with a flaming blade", element: red }
```

Luật prompt (đã trả giá mới biết):

- **Chỉ tả hình.** Phong cách, nền, viền do preset thêm. Viết thêm "cute, anime, white background" chỉ làm loãng.
- **Một chủ thể.** Bắt đầu bằng "one ..." / "a single ...". Hai vật → AI vẽ cảnh, tách nền hỏng.
- **Ngắn.** Model đọc ~77 token đầu; phần cuối bị CẮT IM LẶNG. 1 vật + 1–2 chi tiết nhận diện là đủ.
- **Hai icon khác nhau phải khác hình**, không chỉ khác màu — ở 64px chỉ còn thấy hình khối.
- **Đừng nhắc màu nền.** "on pink background" làm chính vật thể ngả hồng (đã thấy: đồng vàng ra hồng).
- Tả **hình khối**, không tả hành động: "a round bomb with a lit fuse" tốt hơn "a bomb exploding".
- Nhân vật: loài/nghề + 1 món đồ + màu chủ đạo + biểu cảm. "a tiny mage with a big pointy hat and a star wand, purple robe".

Kiểm prompt trước khi tốn GPU: `python3 generate.py --preset presets/<p> --dry-run`.

## 3. Thử nhỏ trước

Notebook: `ONLY = "fire-sword"`, `VARIANTS = 2`. Ưng rồi mới chạy cả danh sách với 4 biến thể.
Một ảnh nói rất ít — 2–4 biến thể mới cho biết prompt có ổn không.

## 4. Duyệt

Mở `sheet.html` trong zip (hoặc xem lưới trong notebook). Nhìn **cả mẻ**, không nhìn từng ảnh:

| Thấy | Nghĩa là | Sửa ở |
|---|---|---|
| Nhiều ảnh cùng trượt một check | prompt / preset sai, không phải AI tồi | preset, không sinh lại |
| `matte` / "không tìm thấy chủ thể" / "vẽ kín khung" | AI vẽ cả khung cảnh | prompt: thêm "one ...", bớt chi tiết |
| `palette_conformance` thấp | màu lệch bảng màu preset | `element` / `element_paint`, hoặc bỏ qua (preset mẫu để `fatal: false`) |
| `readable_at_64` trượt | ở 64px nhoè, tương phản thấp | hình đơn giản hơn, khối to hơn |
| `silhouette_coverage` | vật quá bé / quá to trong khung | prompt ("small"/"big"), hoặc `icon.silhouette_coverage_pct` |
| Hai icon trông như nhau | prompt quá giống nhau | tả lại HÌNH cho khác |
| Ảnh đẹp nhưng sai vật | AI không biết vật đó | tả bằng hình khối đơn giản thay vì tên riêng |

Chấm điểm chỉ kiểm **tuân thủ** (nền, viền, màu, đọc rõ ở 64px), không kiểm "có đúng là cái kiếm không".
Mắt người vẫn phải duyệt.

## 5. Lấy kết quả

- `best/` là bản tự chọn (nhận > xem tay > loại, rồi đọc rõ ở 64px hơn). Không ưng → chọn biến thể khác trong
  `icons/<tên>__<seed>.png`.
- Muốn sinh lại đúng ảnh đó sau này: cùng preset + cùng prompt + cùng seed (seed nằm trong tên file và `prov/`).
- Unity: kéo PNG vào, *Texture Type = Sprite (2D and UI)*, *Alpha Is Transparency* bật. Atlas: *Sprite Mode = Multiple* →
  Sprite Editor → Slice theo số lệnh in ra.

## 6. Sửa đúng chỗ

| Muốn | Làm |
|---|---|
| Đổi ngưỡng chấm / viền / cỡ xuất | sửa `art-direction.md` rồi `generate.py --ingest out/<mẻ>/raw` — **không tốn GPU**, vài phút |
| Đổi prompt / thêm icon / đổi model | sinh lại (chỉ những icon đó: `--only`) |

**Sinh lại khi chỉ cần `--ingest` là lỗi hay gặp nhất** — tốn GPU, và ảnh mới khác ảnh cũ nên không so được thay đổi vừa làm.

## Hỏng thường gặp

| Lỗi | Sửa |
|---|---|
| `KHÔNG CÓ GPU` | bật GPU (README bước 2) rồi chạy lại |
| Kaggle: tải model lỗi / không có mạng | *Settings → Internet → On* (cần xác minh SĐT) |
| Kaggle: "Maximum weekly GPU quota" | hết 30h/tuần → dùng Colab |
| Colab: "cannot connect to GPU backend" | hết quota Colab trong ngày → thử lại sau, hoặc dùng Kaggle |
| `ComfyUI không lên` | đọc log in ra; thường do hết RAM → Runtime → Restart rồi Run all |
| Phiên bị ngắt giữa chừng | Run all lại — bước nào xong rồi tự bỏ qua (model còn trên đĩa nếu phiên chưa reset) |
| GPU P100 trên Kaggle báo lỗi CUDA | chọn T4 — torch mới không còn hỗ trợ P100 |
