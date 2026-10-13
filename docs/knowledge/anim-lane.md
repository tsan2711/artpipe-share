# Làn anim — animation nhân vật 2D frame-by-frame

Một ảnh nhân vật (anchor) → spritesheet animation. Dùng chung cho mọi project (June, NanoSwarm, …):
project chỉ sở hữu **manifest + anchor**, tool nằm ở đây.

```
anchor.png ──► [PC] Wan 2.2 I2V 14B (GGUF Q4_K_M) ──► BiRefNet tách nền ──► frame RGBA
           ──► [Mac] anim_post: cắt 1 hộp chung · pivot đáy-giữa · (khoá bảng màu) · số đo
           ──► <anim>_sheet.png + <anim>.json + <anim>_preview.gif
```

Wan sinh **cả clip trong một lần**, các frame nhìn lẫn nhau → liền mạch. Khác hẳn lối cũ sinh từng
frame độc lập bằng SDXL (bản harvester 2026-09-22: mỗi frame một con bubble khác).

Nền tảng: [mor-o/comfyui-2d-character-pipeline](https://github.com/mor-o/comfyui-2d-character-pipeline)
(MIT) W2 + W3, chỉnh cho card 16GB. Bỏ phần cosmetic layer (W4/W5) — ngoài phạm vi.

## File

| File | Vai trò |
|---|---|
| `anim.py` | client: đọc manifest, nạp anchor, chạy graph, tải frame, gọi hậu kỳ |
| `anim_post.py` | hậu kỳ CẢ chuỗi, chạy độc lập được (không cần GPU) |
| `workflows/anim_wan22_i2v.json` | graph clip một lần (tấn công, nhảy…) |
| `workflows/anim_wan22_loop.json` | graph vòng lặp: frame đầu = frame cuối = anchor (idle, walk…) |
| `anims/smoke.yaml` | manifest mẫu + smoke test máy render (anchor mẫu của mor-o) |

## Cài máy render (một lần)

Qua CI, không cần ngồi trước PC:

```
gh workflow run artpipe.yml -f mode=setup-anim
```

`setup_anim.py` hỏi server đang chạy thư mục thật (`/internal/folder_paths`), clone
`ComfyUI-GGUF` + `ComfyUI-RMBG`, pip các gói còn thiếu (không nâng cấp gói có sẵn), tải ~24GB
model (có nối lại khi đứt). Cài node mới xong **phải khởi động lại ComfyUI bằng tay** (server
không có ComfyUI-Manager), rồi chạy lại job để kiểm. Card 24GB+ thì đặt
`models: {high: …Q5_K_M.gguf, low: …Q5_K_M.gguf}` trong manifest.

Đang ở máy PC: `powershell -ExecutionPolicy Bypass -File setup_pc.ps1 -Anim` làm việc tương tự.

## Chạy

Qua CI (bình thường), từ gốc project game (vd `Seriously/June`):

```
python3 ../../sanne-kit/Tools/artpipe/remote.py --mode anim --out out/anim-run \
    --manifest anims/smoke.yaml --only idle --variants 1
```

Manifest của game tính từ gốc project; không có ở đó thì tìm trong `Tools/artpipe/` (manifest mẫu).

Trực tiếp (cùng LAN): `COMFYUI_URL=http://<pc>:8188 python3 tools/artpipe/anim.py --manifest … --out out/anim generate`

Đổi cell/fps/count/colors → **không render lại**: `anim.py … post` chạy lại hậu kỳ trên frame đã tải.

## Kết quả

```
out/anim/<character>/
  report.json                         số đo mọi biến thể
  <anim>/review.png                   mỗi biến thể một hàng — chọn bằng mắt
  <anim>/s<seed>/raw/  rgba/          frame gốc (giữ lại để hậu kỳ lại)
  <anim>/s<seed>/prov.json            prompt, seed, model, hash graph
  <anim>/s<seed>/post/<anim>_sheet.png   dải ngang, ô vuông `cell`
  <anim>/s<seed>/post/<anim>.json        fps, count, loop, pivot [0.5,0], số đo
  <anim>/s<seed>/post/<anim>_preview.gif xem nhanh bằng Quick Look
```

Số đo (`anim_post.metrics`): `iou_min` (nhảy hình), `loop_iou` (khép vòng), `drift_x` (trôi khỏi
chỗ), `area_ratio`, `color_drift` (đổi màu). Chỉ **gắn cờ**, không loại — ngưỡng chưa hiệu chỉnh
trên output thật của máy mình; chỉnh sau mẻ đầu.

## Viết manifest cho nhân vật thật

Copy `anims/test-adventurer.yaml` (mẫu đầy đủ nhất). Khoá quan trọng:

| Khoá | Ý nghĩa |
|---|---|
| `anchor` / `anchor_gen` | ảnh nhân vật có sẵn, hoặc để máy render tự vẽ (animagine) rồi duyệt + khoá lại |
| `width`, `height` | khung sinh, bội số 16 — **tuỳ mục đích** (480x832 cho nhân vật đứng) |
| `frames` | 4n+1 (17/25/33/49/81); vòng lặp bỏ frame cuối trùng frame đầu |
| `loop: true` | frame đầu = frame cuối = anchor: idle/walk lặp, **và đòn đánh về lại tư thế đứng** |
| `count` | số frame giữ lại (0 = tất cả) |
| `cell`, `fill`, `pad` | ô spritesheet; nhân vật đứng cao `fill` phần ô, chân chạm đáy — **chung cho mọi animation** của một nhân vật (khung theo tư thế đứng), nên đổi animation không đổi cỡ |
| `hold_extreme` | giữ frame đỉnh động tác N nhịp (ghi vào `durations` trong .json) |
| `vfx_key: black` | clip có hiệu ứng phát sáng: sinh trên nền đen → alpha theo độ sáng, không viền trắng, thêm `<anim>_vfx_sheet.png` |
| `colors` | khoá bảng màu chung cả chuỗi |

Luật prompt đã đo được:

- **Negative prompt KHÔNG có tác dụng** — bản distill lightx2v chạy cfg=1. Chỉ tả cái muốn thấy.
  Đừng nhắc thứ không muốn: "breathing" ở bài smoke làm Wan vẽ thêm miệng + làn hơi.
- Anchor phải **đúng hướng/tư thế bắt đầu**. Anchor nhìn thẳng → đi/chạy chỉ làm được TẠI CHỖ
  hướng về người xem; side-scroller cần anchor nghiêng.
- Walk/run: ghi rõ **"stays on the same spot"** (`drift_x` gắn cờ nếu nhân vật trôi).
- `style` tả nét vẽ, `prompt` tả chuyển động.

## Đã đo (2026-09-23, RTX 5060 Ti 16GB)

| | |
|---|---|
| idle 33 frame 512² | ~70–115 s/clip (lần đầu nạp model chậm hơn) |
| 8 clip walk/run/punch/cast | ~8 phút cả mẻ |
| giữ nhân vật (đồ, màu) | tốt qua 32 frame: `iou_min` 0.84–0.98, `color_drift` 2–8 |
| vòng lặp | `loop_iou` ≥ 0.98 mọi clip |
| đã thử và BỎ | san viền bằng trung vị 3 frame — không đo được cải thiện |
