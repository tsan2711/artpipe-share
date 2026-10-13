# Thử làn 3D — 2026-08-20

Một mẫu duy nhất, chạy hết vòng: ảnh → Hunyuan3D → retopo → UV → `.glb` về máy Mac.
Mục đích hẹp: **retopo tự động ra mesh dùng được hay ra rác**, vì câu trả lời đó quyết định
phần còn lại của kiến trúc asset 3D. Chưa đụng tới texture.

Lệnh:

```
python3 tools/artpipe/remote.py --out out3d --mode mesh \
    --image "3d_hunyuan3d-v2.1_input_image.png" --faces 8000
```

## Số đo

| | high (thô, sau marching cubes) | low (sau IMRemesh + UV) |
|---|---|---|
| tam giác | 1.164.642 | 8.000 |
| đỉnh | 582.299 | 6.342 |
| kín khối | **có** | **không** |
| UV | không | có, nằm gọn trong [0,1] |
| dung lượng | 20,9 MB | 224 KB |
| thời gian | | 83 giây cả hai |

Tỉ lệ giảm 146:1, và bao hình (bbox) lệch dưới 0,1% — retopo giữ đúng khối, không co rút.

## Đọc kết quả

**Hình khối: dùng được.** Ở 8.000 tam giác, bóng ngoài vẫn đọc ra đúng vật thể; các chi tiết
lồi lõm (khớp, mắt, ăng-ten) còn nguyên. Đây là mức ngân sách hợp lý cho một prop đặt rải
trong màn chơi.

**Lưới thì không đẹp.** Wireframe ra tam giác đều hướng, không có edge loop — không dùng để
biến dạng/animation được, và chia nhỏ thêm cũng không cho kết quả sạch. Với prop tĩnh thì
không sao; với bất cứ thứ gì cần rig thì phải retopo tay.

**Không kín khối sau retopo** (bản thô thì kín). Nghĩa là có lỗ hở nhỏ: bake normal có thể ra
vệt đen ở mép hở, và không dùng thẳng làm collider kín được. Sửa được ở bước hậu kỳ, nhưng
phải biết mà xử lý chứ không phải mặc định đúng.

**Atlas UV là chỗ yếu nhất.** Ảnh atlas cho thấy hàng chục mảnh nhỏ rời rạc, chèn không chặt,
phí diện tích và sinh seam khắp nơi. Đây đúng là cái Bi đã nhận xét về texture bake không
đẹp — nguyên nhân nằm ở unwrap tự động, không phải ở khâu vẽ texture.

## Kết luận

Hunyuan3D **dùng được, nhưng chỉ cho một lớp asset hẹp**: prop tĩnh, hữu cơ, độc nhất
(đá, xác tàu, đống đổ nát, tượng). Với kit environment lắp ghép thì vẫn không nên dùng —
và điều đó không liên quan tới chất lượng mesh ở đây, mà vì mô hình "mỗi object một texture
riêng" không scale được; environment phải dùng material tiling chung.

Việc cần làm trước khi mở rộng, theo thứ tự đắt dần:

1. ~~Vá lỗ hở sau retopo (điều kiện cần cho bake normal sạch).~~ **Đóng 2026-09-08 —
   không có lỗ hở nào cả, xem mục sửa dưới.**
2. Unwrap lại bằng công cụ khác thay vì atlas mặc định của node, ưu tiên gộp mảnh và
   thống nhất texel density. **Đã thử 2026-09-08, không hiệu quả như mong đợi — xem mục
   sửa dưới.**
3. Thử thêm vài mẫu đúng loại vật thể sẽ dùng thật trong June, rồi mới viết GDD đầy đủ.

---

## Sửa 2026-09-08 — đo lại cả hai kết luận trên bằng số

Bối cảnh: ADR-0016 (World Content Pipeline) đặt việc vá 2 lỗi này ở bước 5 của kế hoạch,
trước khi build prop-library lane. Đo lại trên chính hai file `.glb` của mẻ trial này
(vẫn còn nguyên trong `out3d/mesh/`) trước khi bắt tay vá, để biết đang vá cái gì thật.

### "Hở khối" — không có thật, là lỗi đo

`mesh.py::stats()` (bản cũ) gọi thẳng `trimesh.load(path).is_watertight` — và với BẤT KỲ
mesh nào có UV, mỗi seam UV bắt buộc tách đỉnh (một đỉnh 3D nằm nhiều toạ độ UV thì phải
nhân bản), nên trimesh coi các đỉnh tách đó là *không nối nhau*. Đo trên bản `_low` của
chính mẻ này: raw báo `watertight=False`, `body_count=277`. Gộp lại đỉnh trùng vị trí
(`merge_vertices(merge_tex=True, merge_norm=True)`) — đúng phép trimesh dùng nội bộ để
vẽ preview, xem `mesh_preview.py` — thì `watertight=True`, **1 khối duy nhất, 0 boundary
edge trên cả 8000 tam giác**. Con số `277` trong bản đo cũ không phải "277 lỗ hở", mà là
277 mảnh UV atlas bị đếm nhầm thành 277 mảnh hình học vì không gộp đỉnh trước khi đo.

**Kết luận cũ "Không kín khối sau retopo" là sai — do đo sai, không phải do mesh sai.**
`mesh.py::stats()` đã sửa (2026-09-08) để gộp đỉnh trước khi kiểm watertight; số báo ra
từ nay đáng tin.

### UV atlas vụn — có thật, nhưng đổi công cụ unwrap không chữa được

Số đo xác nhận đúng như mô tả cũ: **277 mảnh atlas, 81 mảnh ≤3 tam giác** (đúng bằng số
"khối" báo sai ở trên — cùng một phép đếm connected-component, chỉ khác không gian đo:
3D cho khối, UV cho mảnh atlas). Tổng diện tích UV chiếm 74.6% ô vuông [0,1]².

Thử vá bằng `xatlas` (thư viện unwrap chuẩn công nghiệp, khác hẳn node gốc) trên đúng
topology đã gộp đỉnh ở trên — kết quả: **277 → 275 mảnh**, gần như không đổi, kể cả khi
nới `ChartOptions.max_cost` từ 2.0 (mặc định) lên 8/24/64 (rất dễ dãi, ưu tiên gộp mảnh
tối đa). Đổi công cụ unwrap **không sửa được** vấn đề.

Lý do nhiều khả năng: chính đoạn mô tả "lưới không đẹp" ở trên đã nói đúng nguyên nhân —
retopo (IMRemesh) ra "tam giác đều hướng, không có edge loop". Một mặt lưới không có
dòng cạnh tự nhiên (edge loop) thì bất kỳ thuật toán chia atlas nào (node gốc hay xatlas)
đều không có "đường nối tự nhiên" để bám theo, và phải cắt tuỳ tiện thành nhiều mảnh nhỏ
gần đều nhau — đây là hệ quả của CHẤT LƯỢNG RETOPO, không phải của lựa chọn công cụ UV.

**Nghĩa là gì cho bước 5 của ADR-0016**: build cả batch prop-library (8–12 biến thể) qua
IMRemesh như hiện tại sẽ tiếp tục ra atlas vụn, bất kể unwrap bằng gì. Việc cần làm không
còn là "đổi công cụ unwrap" (đã thử, không ăn thua) mà là một trong hai hướng đắt hơn:
(a) tìm/tinh chỉnh thuật toán retopo có edge loop sạch hơn IMRemesh, hoặc (b) chấp nhận
atlas vụn và đo/tối ưu riêng độ CHẶT của việc sắp mảnh (packing — bao nhiêu padding lãng
phí giữa các mảnh), tách biệt với SỐ mảnh.

---

## Sửa 2026-09-09 — tìm ra nguyên nhân THẬT, không phải do thuật toán retopo

Bi chọn hướng (a) ở trên. Trước khi đi tìm công cụ khác (Blender QuadriFlow, Hunyuan3D
3.0...), tra lại code của chính node đang dùng (`Hy3D21IMRemesh` trong
`ComfyUI-Hunyuan3d-2-1/nodes.py`) thì phát hiện: **retopo (Instant Meshes) chưa từng bị lỗi
thuật toán — nó tính ra lưới đẹp thật, nhưng code của node có một dòng bug làm kết quả đó
không bao giờ được dùng**. Cụ thể: hàm `remesh()` tính `new_verts`/`new_faces` từ Instant
Meshes, kiểm tra thành công, rồi... bỏ qua luôn hai biến đó — giá trị trả về (`new_mesh`)
vẫn là bản sao mesh GỐC (trước retopo), chỉ bị cắt bớt tam giác nếu vượt trần
(`FaceReducer`, một phép giảm-đỉnh thô, không phải Instant Meshes). Tức là mọi mesh "low"
sinh ra từ trước tới giờ **chưa bao giờ thực sự đi qua Instant Meshes** — chỉ là bản gốc bị
cắt thô, đúng khớp với triệu chứng "tam giác đều hướng, không theo dòng cạnh tự nhiên" đã
quan sát.

**Đã vá 1 dòng** (dựng `new_mesh` từ đúng `new_verts`/`new_faces` trước khi cắt trần), khởi
động lại ComfyUI, sinh thử lại một mesh mới (ảnh quái vật đã vẽ ở phiên làm việc này) —
đo lại đúng phép đo đã dùng ở trên:

| | Trước vá | Sau vá |
|---|---|---|
| Số mảnh atlas | 277 | **33** |
| Mảnh vụn (≤3 tam giác) | 81 | **6** |
| Mảnh lớn nhất | 300 tam giác | **1862 tam giác** |
| Kín khối | Có | Có (không đổi) |

Xem trực quan (`mesh_preview.py`) cũng khớp: UV atlas giờ ra từng mảng lớn thay vì hàng
trăm mảnh confetti.

**Kết luận**: không cần đổi công cụ (chưa cần Blender/Hunyuan3D 3.0). Nguyên nhân là một bug
cụ thể, đã vá. Việc còn lại: build thử batch nhiều mẫu hơn để xác nhận cải thiện này ổn định
(không phải may mắn trên đúng 1 mẫu), rồi mới build batch prop-library thật (8–12 biến thể).

---

## Sửa 2026-09-09 (tiếp) — thử trên đá góc cạnh (prop môi trường thật), bug-fix không đủ

Bug đã vá ở trên test tốt trên **quái vật tròn/hữu cơ**. Nhưng loại asset môi trường quan
trọng nhất (đá, đổ nát — góc cạnh, có khe nứt) là một hình khối khác hẳn. Test trên một
viên đá vỡ góc cạnh (`rock_alpha-777`, 746k tam giác thô, xác nhận kín khối 1 khối trước
retopo) — sau retopo: **không kín khối, 31 khối rời, 1844 cạnh hở, 799 mảnh atlas**. Tệ hơn
cả trước khi vá bug, trên đúng shape này.

### Có phải do Blender (QuadriFlow) làm tốt hơn không? — Không, cùng fail

Thử `bpy.ops.object.quadriflow_remesh` (Blender 5.2, headless) trên đúng file `.glb` cao độ
phân giải đó qua **10 biến thể xử lý khác nhau**: mesh gốc thẳng, sau khi dọn tam giác lỗi
(`dissolve_degenerate`/`remove_doubles`), sau decimate 5%, sau khi vá lại lỗi do chính
decimate gây ra, sau Voxel Remesh (đảm bảo đặc kín 100%) ở nhiều độ phân giải kể cả rất thô
(2730 mặt) — **tất cả đều bị QuadriFlow từ chối** với đúng một câu: "mesh needs to be
manifold and have face normals that point in a consistent direction". Đo độc lập bằng
`trimesh` (watertight, winding_consistent) VÀ bằng chính `bmesh` của Blender (non-manifold
edge/vert count, wire edges, winding-consistency giữa 2 mặt kề) ở MỌI biến thể trên: **0 lỗi
mọi lúc**. Test một quả cầu UV thường (không qua import glTF) qua đúng operator đó thì chạy
bình thường. Kết luận: đây là hạn chế/lỗi của bản thân `quadriflow_remesh` (Blender 5.2, chế
độ `--background`) với mesh nhập từ glTF trong môi trường này, không phải lỗi hình học của
viên đá — nhưng dù nguyên nhân là gì thì kết quả thực tế vẫn là **Blender không dùng được
làm phương án thay thế lúc này**.

### Đổi cách vẽ ảnh đá (tròn hơn, bỏ khe nứt) — có cải thiện thật, nhưng chưa đủ

Prompt gốc có chữ "with subtle cracks" — đổi hẳn sang "river-smoothed stone... no sharp
facets, no deep cracks... gentle surface bumps" (bỏ khe nứt, giữ độ gồ ghề nhẹ để còn ra
dáng đá chứ không phải quả trứng nhẵn). Sinh lại toàn bộ chuỗi ảnh → Hunyuan3D → retopo
(cùng tham số 4000 mặt). Đo lại:

| | Đá góc cạnh (cũ) | Đá tròn (mới) | Quái vật tròn (đối chứng) |
|---|---|---|---|
| Kín khối | Không | Không | **Có** |
| Số khối rời | 31 | **13** | 1 |
| Cạnh hở | 1844 | **1221** | 0 |
| Mảnh atlas | 799 | **527** | 33 |
| Mảnh vụn (≤3 tam giác) | (chưa đo) | 379 | 6 |

Vẽ đá tròn hơn giúp thật (khối rời giảm ~58%, cạnh hở giảm ~34%, mảnh atlas giảm ~34%) —
không phải ảo giác đo sai. Nhưng **không giải quyết dứt điểm**: vẫn hở khối, vẫn vụn atlas
nặng, cách xa kết quả sạch của quái vật. Tức là hướng "đổi art direction cho tròn hơn" đúng
nhưng chưa đủ tự nó — bản thân IMRemesh (Instant Meshes) vẫn xử lý kém với khối bất đối xứng
kiểu đá/prop môi trường so với khối gần-đối-xứng kiểu nhân vật, dù đã tròn.

**Việc còn để ngỏ, chưa quyết**: (a) tinh chỉnh thêm tham số IMRemesh riêng cho lớp prop môi
trường (`smooth_iter`, `align_to_boundaries`, tăng `vertex_count` rồi giảm hậu kỳ...), (b)
chấp nhận vá lỗ hở bằng hậu kỳ tự động (fill-hole) sau retopo thay vì đòi retopo ra sạch
ngay, hoặc (c) coi lớp "đá/prop môi trường góc cạnh" là một class asset cần quy trình riêng
(không dùng chung IMRemesh mặc định) — quyết định thuộc Bi, chưa chốt trong phiên này.

Bi chọn hướng (b). Đã làm.

### Vá tự động sau retopo — `mesh.py::repair()`, dùng `pymeshfix`

Thử `trimesh.repair.fill_holes` trước (công cụ có sẵn, không cần cài thêm) — không ăn thua:
chạy trên `rock_round_902_low` (13 khối rời, 1221 cạnh hở), số tam giác và số cạnh hở
KHÔNG đổi trước/sau, kể cả khi chỉ chạy trên đúng khối chính (2268 tam giác, bỏ hết mảnh
vụn) — `fill_holes` chỉ nối quạt (fan) đơn giản, không xử lý được lỗ phức tạp/nhiều lỗ rải
rác trên cùng một khối.

Đổi sang `pymeshfix` (thư viện MeshFix, `pip install pymeshfix`) — làm 2 việc trong 1 bước:
bỏ mảnh vụn rời rạc (rác của IMRemesh, không phải hình khối thật) rồi tam giác hoá lại đúng
biên chỗ còn thiếu. Đo trên đúng mesh trên:

| | Trước vá | Sau vá |
|---|---|---|
| Kín khối | Không | **Có** |
| Số khối rời | 13 | **1** |
| Cạnh hở | 1221 | **0** |
| Số tam giác | 3994 | 2356 (bỏ ~41% là mảnh vụn, không phải hình khối) |

Đã nối vào `mesh.py` làm bước chuẩn: hàm `repair(path, out_path)` + cờ `--repair` trên CLI
(mesh nào `stats()` báo hở khối thì tự vá, ghi thêm `<tên>_repaired.glb`). Có test hồi quy
trong `selftest.py::check_mesh_repair()` (hộp hở 1 mặt + rác rời -> phải vá thành 1 khối
kín) — chạy qua.

**Chưa làm**: `pymeshfix` không giữ UV — atlas cũ mất khớp topology mới, phải unwrap lại
(`xatlas`, đã có sẵn trong material lane) trước khi bake texture lên mesh đã vá. Đây là bước
tiếp theo trước khi build batch prop-library thật.
