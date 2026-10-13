---
name: artpipe-vfx
description: Gen VFX 2D (flipbook frame-by-frame, sprite particle, tile atlas) bằng làn VẼ của artpipe rồi xem chúng CHẠY (GIF, cỡ thật, nền sáng/tối). Dùng khi cần hiệu ứng mới (nổ, trúng đòn, vòng sóng, hồi máu, cảnh báo…), khi sửa/đánh giá VFX có sẵn, hoặc khi test pipeline VFX.
---

# artpipe — làn VFX

Phán đoán + quy trình. Code: `tools/artpipe/draw_*.py` (vẽ) và `tools/artpipe/vfx_preview.py` (xem chạy).
Kết quả test pipeline đã ghi ở `tools/artpipe/explore-findings.md` — đọc trước khi đổi hướng.

## Quyết định đầu tiên: mẻ này là gì?

| Bi nói | Là | Ghi ở đâu |
|---|---|---|
| "gen thêm để xem thiếu gì", "test pipeline" | **Test pipeline**, không phải asset game | `tools/artpipe/out-*` + `explore-findings.md`. KHÔNG đụng `Assets/`, KHÔNG ghi asset-backlog |
| "làm VFX cho <system>", "thêm hiệu ứng khi X" | Asset game | `Assets/…` + dòng `asset-backlog.md` + row CSV (vd `world_fx.csv`) trong cùng thay đổi |

Không chắc → hỏi một câu, đừng đoán (đã đoán sai 2026-09-24).

## Chọn làn — VFX đi làn VẼ, không đi ComfyUI

Test 2026-09-24 (run 35990039405): ComfyUI + animagine cho **~50% VFX sai vật thể** (sét → gấu hồng,
sóng xung kích → quả trứng có mặt, chém → mặt trăng) mà tier 1 vẫn "nhận" 112/112. Model kéo mọi thứ thành
mascot bóng bẩy, không có glow/trong suốt, không có frame. Nên:

- **VFX (flipbook / particle tile) → vẽ bằng code** (`draw_vfx_sprites.py`, `draw_explore.py`). Hình đúng tuyệt đối.
- **ComfyUI chỉ khi** cần texture/chất liệu, và phải có hình khởi đầu (silhouette vẽ → img2img) + bật `--tier2`.
  Chưa có mode VFX riêng trong ComfyUI (xem C2/C4 trong findings) — đừng chạy mẻ VFX bằng theme icon rồi tin verdict.

## Hợp đồng một hiệu ứng

```python
def fx_<name>(n=6):            # trả list frame RGBA 128px
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - t)   # t: 0→1, fade qua alpha
        ...                                                    # vẽ 4× supersample, done(im) hạ về 128
        out.append(done(im))
    return out
VFX = [("<name>", fx_<name>, "<sự kiện kích hoạt>"), ...]
```

- **Fill trắng = tint được** (ParticleSystem/UI tô màu), viền mực `#4A3A52`. Hiệu ứng mang màu cố định (lửa, độc) thì vẽ màu thẳng.
- One-shot 4–10 frame @12fps; loop (cảnh báo, beacon) thì frame cuối nối frame đầu (`t = i / n`, không `n-1`).
- Particle tile = **1 frame**, để ParticleSystem lo chuyển động (size/rotation/velocity over lifetime) — rẻ hơn flipbook.
- Hiệu ứng bắn liên tục (chết bot, trúng đòn, harvest) phải **rẻ + nhỏ**: ≤6 frame, ít chi tiết. Khoảnh khắc hiếm (phá core, prestige) mới được to và dài.

## Luôn xem nó CHẠY — không duyệt bằng dải frame tĩnh

```
python3 tools/artpipe/vfx_preview.py <module> [out] [--only a,b] [--fps 12]
open -a Safari <out>/vfx_all_anim.gif        # Preview.app KHÔNG chạy GIF, chỉ liệt kê frame
```

Ra: `vfx_all_anim.gif` (tất cả cùng chạy), `vfx_gif/<name>.gif` (nền sáng | tối), `vfx_frames/<name>/` (từng frame),
`vfx_realsize.gif` (24/48/96 px). Bi hỏi "đâu, mở lên" → mở GIF trong Safari, không đưa contact sheet.

## Checklist duyệt (các lỗi đã thấy)

1. **Nền sáng**: fill trắng + viền mảnh biến mất trên nền kem → viền dày hơn, hoặc luôn tint, hoặc lớp lót tối.
2. **Nền tối**: viền mực chìm vào nền HUD; frame fade thành xám đục → cần biến thể viền sáng cho VFX nằm trên panel tối.
3. **Cỡ thật** (`vfx_realsize.gif`): ở 24px chi tiết trong mất hết — hình phải đọc được bằng **đường bao**.
4. Nhịp: one-shot có đủ "đập" (frame đầu to/sáng nhất) và tắt gọn; loop không giật ở chỗ nối.
5. Hai hiệu ứng khác nghĩa không được trông giống nhau khi chạy (vd trúng đòn vs nhặt đồ).

## Khi thành asset game

Frame → `Assets/UI/HUD/Icons/Fx/` (UI flipbook, `HudFx`) hoặc tile trong `Assets/Sprites/Fx/world_fx_atlas.png`
(world, `WorldFx` + `Config/Fx/world_fx.csv`). Thêm dòng `asset-backlog.md` cùng lúc. Ảnh UI ≤64px để vào dynamic atlas.
