# artpipe-share — sinh icon & sprite 2D cho game bằng AI, chạy free trên Colab / Kaggle

Viết danh sách icon bằng chữ → nhận về PNG nền trong, đã cắt nền, căn giữa, có viền, xuất sẵn nhiều cỡ +
sprite sheet. Chạy trên GPU miễn phí của Google Colab hoặc Kaggle — **không cần cài gì, không cần token**.

| Preset | Ra cái gì | Model |
|---|---|---|
| `cute-icons` | icon item / tiền tệ / UI kiểu anime dễ thương | Animagine XL 4.0 |
| `vector-icons` | icon kỹ năng / spell / buff vector phẳng, viền đậm | SDXL + LoRA DD-vector-v2 |
| `chibi-sprites` | nhân vật / quái / pet chibi toàn thân | Animagine XL 4.0 |

## Chạy trong 3 bước

1. Mở `artpipe.ipynb`:
   - **Colab:** bấm nút *Open in Colab* ở đầu notebook trên GitHub (lần đầu Colab xin quyền đọc repo private — đồng ý),
     hoặc *colab.research.google.com → File → Upload notebook* → chọn `artpipe.ipynb`.
   - **Kaggle:** *kaggle.com → Create → New Notebook → File → Import Notebook* → chọn `artpipe.ipynb`.
2. Bật GPU — Colab: *Runtime → Change runtime type → T4 GPU*. Kaggle: *Settings → Accelerator → GPU T4 x2* và
   *Internet → On* (Kaggle bắt xác minh số điện thoại một lần).
3. Sửa ô **⚙️ Cấu hình** (chọn preset, dán danh sách icon của bạn — hoặc để nguyên để chạy mẫu) → **Run all**.

Lần đầu mỗi phiên ~5–8 phút dựng máy + tải model (~7GB). Sau đó ~20–40 giây/ảnh trên T4.
Ví dụ 12 icon × 4 biến thể ≈ 20–30 phút. Cuối notebook tự tải file `.zip` (Kaggle: tab *Output*).

Không cần GH token: code đã được **nhúng sẵn trong notebook**. Nếu đặt secret `GH_TOKEN` (Colab: biểu tượng 🔑;
Kaggle: *Add-ons → Secrets*) thì notebook clone bản mới nhất từ repo thay vì dùng bản nhúng.

## Trong file zip có gì

```
best/<tên>.png          bản tự chọn tốt nhất cho mỗi icon (512px, nền trong)   ← thường chỉ cần cái này
export/<tên>_256.png    best thu về các cỡ (512/256/128/64 — đổi ở art-direction.md → icon.export)
atlas.png + atlas.json  ghép mọi best thành 1 sprite sheet (JSON kiểu TexturePacker — Phaser/Pixi/Cocos đọc thẳng)
icons/                  MỌI biến thể sau hậu kỳ — không ưng best thì chọn ở đây
sheet.html              trang duyệt: mọi biến thể + điểm + lý do trượt (mở bằng trình duyệt)
raw/                    ảnh gốc AI vẽ — giữ lại để chạy lại hậu kỳ không tốn GPU
report.json · prov/     điểm + nguồn gốc từng ảnh (prompt, seed, model) — sinh lại được đúng ảnh đó
```

Màu khung trong notebook / sheet: **xanh = nhận** · **vàng = xem tay** (vd lệch bảng màu) · **đỏ = loại** (vd không cắt được nền).

## Viết danh sách icon

Trong ô cấu hình (`MY_ICONS`) hoặc trong `presets/<preset>/icons.yaml`:

```yaml
- { name: Magic Apple, prompt: "one shiny red apple with a tiny golden leaf and sparkles", element: red }
- { name: Fishing Rod, prompt: "one wooden fishing rod with a red and white bobber" }
```

- `name` → tên file (`Magic Apple` → `magic-apple.png`).
- `prompt` → **chỉ tả HÌNH**, tiếng Anh, một vật. Đừng tả nền, đừng tả phong cách — preset lo phần đó.
- `element` (tuỳ chọn) → màu chủ đạo, phải là một khoá trong bảng màu của preset.

Mẹo prompt và cách xử lý ảnh hỏng: [QUY-TRINH.md](QUY-TRINH.md).

## File ý tưởng (JSON) — một file = một mẻ

Gom preset + cài đặt + danh sách icon vào **một file JSON** (mẫu trong `jobs/`):

```json
{
  "preset": "cute-icons",
  "variants": 3,
  "seed": 1000,
  "icons": [
    { "name": "Health Potion", "prompt": "one round glass potion flask with a cork, glowing liquid inside", "element": "red" },
    { "name": "Bomb", "prompt": "one round black bomb with a short lit fuse and a spark" }
  ]
}
```

- Notebook: ô cấu hình → `JOB = "jobs/rpg-shop.json"`, hoặc `JOB = "upload"` (Colab: chọn file từ máy),
  hoặc Kaggle: upload file thành Dataset rồi `JOB = "/kaggle/input/<dataset>/<file>.json"`.
- Dòng lệnh: `python3 generate.py --job jobs/rpg-shop.json` (cờ dòng lệnh như `--only` vẫn ghi đè được file).
- Khoá: `preset` (bắt buộc — tên thư mục trong `presets/`), `variants`, `seed`, `only`, `icons` (bắt buộc).
  Khoá bắt đầu bằng `_` (vd `_ghi_chu`) bị bỏ qua. Viết YAML thay JSON cũng được.
- Mẫu: `rpg-shop` (item RPG) · `idle-ui` (icon UI) · `monsters` (quái chibi) · `skills` (icon kỹ năng vector).

## Tất cả file cấu hình

| File | Ai sửa | Chứa gì |
|---|---|---|
| `jobs/*.json` | người dùng, mỗi mẻ | preset nào + bao nhiêu biến thể + danh sách ý tưởng icon |
| ô ⚙️ Cấu hình trong notebook | người dùng, mỗi lần chạy | `PRESET` / `JOB` / `VARIANTS` / `ONLY` / `MY_ICONS` |
| `presets/<p>/icons.yaml` | ai làm preset | danh sách mẫu của preset (dùng khi không có JOB / MY_ICONS) |
| `presets/<p>/art-direction.md` | ai làm preset, hiếm khi | phong cách: bảng màu, câu tả phong cách, negative prompt, viền, cỡ xuất, ngưỡng chấm |
| `presets/<p>/preset.yaml` | ai làm preset, hiếm khi | model + link tải, graph ComfyUI, cỡ sinh, biến thể/seed mặc định |
| `artpipe/workflows/*.json` | hầu như không | graph ComfyUI (sampler, steps, cfg, LoRA) — sửa trong ComfyUI rồi *Export (API)* |

## Chạy ở máy khác (không phải Colab/Kaggle)

```bash
pip install -r requirements.txt
python3 generate.py --preset presets/cute-icons --dry-run            # xem prompt, không cần GPU
python3 generate.py --preset presets/cute-icons                      # máy Linux có GPU NVIDIA: tự dựng ComfyUI
python3 generate.py --preset presets/cute-icons --host http://IP:8188 # đã có ComfyUI ở đâu đó (Windows, máy thuê…)
python3 generate.py --preset presets/cute-icons --ingest out/<mẻ>/raw # chạy lại hậu kỳ, không cần GPU
```

ComfyUI tự dựng (Windows/máy khác) phải có đúng model + LoRA ghi trong `presets/<preset>/preset.yaml`.

## Cấu trúc repo

```
artpipe.ipynb       notebook Colab + Kaggle (dựng bởi tools/build_notebook.py, code nhúng sẵn)
generate.py         MỘT lệnh: dựng ComfyUI → tải model → sinh → tách nền → chấm → chọn → xuất → zip
setup_comfy.sh      dựng ComfyUI trên Linux GPU (generate.py tự gọi)
jobs/*.json         file ý tưởng mẫu: preset + cài đặt + danh sách icon trong một file
presets/<tên>/      art-direction.md (phong cách, bảng màu, luật chấm) · icons.yaml (danh sách) · preset.yaml (model)
artpipe/            lõi pipeline: prompt, gọi ComfyUI, tách nền, ép viền, chấm điểm, trang duyệt
  workflows/        graph ComfyUI (API format)
tools/              selftest.py · build_notebook.py · pack_atlas.py
```

## Sửa code / preset rồi đẩy lên

```bash
python3 tools/build_notebook.py   # nhúng lại code vào notebook — BẮT BUỘC, không thì Colab chạy code cũ
python3 tools/selftest.py         # phải XANH (CI cũng chạy)
```

## Giấy phép model

Animagine XL 4.0 và SDXL base: CreativeML OpenRAIL++-M (dùng thương mại được, kèm điều khoản sử dụng của giấy phép).
LoRA DD-vector-v2: huấn luyện trên ảnh CC0/public domain. Tự kiểm lại giấy phép trước khi đưa asset vào sản phẩm bán.

Gốc: tách từ `sanne-kit/Tools/artpipe` (làn icon) — bản này chạy độc lập, không cần sanne-kit / Unity / GitHub runner.
