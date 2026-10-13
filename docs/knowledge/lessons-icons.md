---
name: artpipe-icons
description: Sinh, sửa và nhập icon game bằng artpipe (ComfyUI qua GitHub Actions). Dùng khi cần icon mới cho spell/item/modifier, khi icon hiện có bị lỗi (nền sót, lem màu, sai màu, quá tối), khi đổi máy render, hoặc khi đọc kết quả một mẻ đã chạy.
---

# artpipe — làn icon

Cơ chế chi tiết ở `sanne-kit/Tools/artpipe/README-comfyui.md`. File này chỉ chứa **phán đoán**: chọn
lệnh nào, đọc kết quả ra sao, và những chỗ đã trả giá.

## Chọn lệnh theo tình huống — đây là quyết định quan trọng nhất

| Tình huống | Lệnh | Vì sao |
|---|---|---|
| Sửa code hậu kỳ (matte, stylise, ngưỡng) | `run.py --out <mới> ingest <cũ>/raw` | **Ảnh gốc được giữ nguyên trong `raw/`.** Chạy lại hậu kỳ mất vài phút, không tốn GPU, không cần máy render. |
| Cần ảnh mới (thêm asset, đổi prompt/checkpoint) | `remote.py --out <mới> --variants 4` | Bắt buộc qua máy render |
| Chỉ một asset | thêm `--only <slug>` | |
| Lấy lại kết quả mẻ cũ | `remote.py --attach <run_id>` | |

**Sinh lại khi đáng lẽ chỉ cần `ingest` là lỗi hay gặp nhất** — tốn GPU, mất cả tiếng, và
ảnh mới lại khác ảnh cũ nên không so sánh được thay đổi vừa làm.

## Đọc `report.json` cho đúng

`stylise.py` **ép** phong cách bằng code: snap bảng màu, gom bậc sáng, vẽ viền, ép modifier
về trung tính. Nên sau bước đó, `palette_conformance` / `value_step_count` / `outline_present`
**đúng do dựng nên đúng** — chúng không còn chấm máy sinh.

- Muốn biết máy sinh vẽ thế nào: đọc **`scores_raw`** (điểm trước khi ép) và cờ `stylised`.
- `scores` cao mà `scores_raw.palette_conformance` thấp = **còn nền sót**, và bước ép vừa
  sơn nó thành màu hợp lệ. Icon sẽ có vệt màu lạ mà không phép kiểm nào thấy.
- Tầng 1 chấm **tuân thủ**, không chấm **nhận dạng**. Hai icon khác nhau mà trông như một
  thì chỉ tầng 2 bắt được (`--tier2`, lần đầu tải ~2GB trên máy render).

## Nút thắt hiện tại (2026-08-26)

**Màu, tách nền, hình dạng, mảng phẳng: XONG.** Mẻ chuẩn để so là `out-vec3`
(sinh ở `out-vec1`, hậu kỳ chạy lại). 79/84 nhận, 21/21 asset.

```
remote.py --out <mới> --checkpoint sd_xl_base_1.0.safetensors \
          --workflow-file icon_sdxl_vector.json --gen-size 1024 --variants 4
```

Ba thứ phải đi cùng nhau, thiếu một là hỏng:
- `DD-vector-v2` LoRA (CC0 — quan trọng vì asset đi vào game bán)
- `generation.prompt_prefix` đứng ĐẦU prompt (CLIP cắt đuôi ở 77 token)
- `matte_method: segment` + `rembg` trên máy render

**Cái chặn còn lại: hình của SPELL.** Item và modifier đã tốt; spell ra những lát mảnh
chéo góc, ở 64px thì mờ. Sửa ở `subtype_shape` trong art-direction — mô tả hình, KHÔNG
phải đổi model, KHÔNG phải chỉnh hậu kỳ. Tầng 2 vẫn chưa chạy trên mẻ thật lần nào.

**Đường đã thử và loại:** `sd-turbo` (bỏ qua lệnh nền, không vẽ nổi phẳng-có-viền);
`sdxl-flat + sdxl-boldline` chồng nhau (kéo bố cục về tranh khắc gỗ kín khung — tỉ lệ đậu
cao hơn nhưng ảnh vô dụng).

## Sáu chỗ đã trả giá

1. **`out/` không được commit.** Đã lọt vào git một lần: runner checkout ra, upload-artifact
   gói lại, client nhận `report.json` của mẻ ba ngày trước — ảnh thật, điểm thật, mẻ khác.
   Mẻ không render gì vẫn in ra verdict trông hợp lệ.
2. **cfg = 1.0 làm negative prompt vô tác dụng.** Dùng `icon_txt2img_cfg.json` (steps 6,
   cfg 2) cho ảnh sạch hơn hẳn.
3. **Máy render là một URL, không phải một cái máy.** Đổi máy = đổi secret `COMFYUI_URL`,
   hoặc var `ARTPIPE_RUNNER` nếu dựng runner ngay trên máy GPU. Không sửa file nào.
4. **Màu nền trong prompt ngấm vào chính vật thể.** Câu "nền hồng gắt" (chọn để dễ khoá
   màu) làm đồng tiền vàng ra hồng, thỏi thép xanh-xám cũng ra hồng — trên **cả ba**
   checkpoint. Mất ba mẻ mới nhìn ra vì tôi đổ cho model. Nay `matte_method: segment`:
   prompt không nhắc nền, `segment.py` (rembg/U²-Net) nhận dạng chủ thể. Máy render phải
   có `rembg onnxruntime`; selftest ghim đường khoá màu qua `through_matte_chroma` nên
   cổng CI không phải tải 176MB.
5. **Ép phong cách theo từng pixel làm mảng phẳng lấm tấm.** Vân sơn dầu của SDXL khiến
   pixel lẻ nhảy bậc sáng. `_smooth_lstar` (trung vị 9, chỉ trên ĐỘ SÁNG) + `_despeckle`
   (bỏ phiếu đa số bán kính 5 trên nhãn bậc). Làm mượt RGB thì tạo dải chuyển sắc — §4
   cấm. Quét tham số trên một ảnh thật trước khi chốt số, đừng đoán.
6. **Đo sai đại lượng là lỗi hay gặp hơn đặt sai ngưỡng.** Ba lần trong một ngày: tương phản
   đo trung bình thay vì phân vị; cổng nền đo màu thay vì độ phẳng; snap màu trộn lẫn sắc
   với độ sáng. Nghi ngờ một ngưỡng thì **đo phân bố trên mẻ thật trước**, đừng chỉnh số.

## Trước khi push

`python3 <sanne-kit>/Tools/artpipe/selftest.py` (chạy từ gốc project game) phải xanh — nó có cả đối chứng âm (ảnh cố tình sai phải
bị bắt), nên nó bắt được cả khi ta vô tình làm bộ kiểm mù đi. Trên máy Mac của Bi nó chạy
khá lâu; chạy nền rồi làm việc khác.
