# Spell VFX — từ "chạy được" đến "ship được"

Ngày: 2026-09-13 · Bối cảnh: ADR-0018, Spell VFX #30 · Trạng thái: **danh sách nợ**, chưa lên lịch

Hiện tại đường batched đã thông và nhìn ra hiệu ứng. Tài liệu này liệt kê khoảng cách còn lại tới
chất lượng ship, tách theo *ai làm được*.

---

## A. Nợ kỹ thuật (code/asset — làm được ngay, không cần hoạ sĩ)

### A1. `Color over Life` — hạt đang tắt phụp

Chưa có block nào giảm alpha theo tuổi. Hết `lifetime` là hạt biến mất đột ngột. Đây là khác biệt
lớn nhất giữa "hiệu ứng tạm" và "hiệu ứng nhìn được", và nó là **một block**.

### A2. `FrameCapacity` đang là số đoán

`128` cho muzzle, `512` cho impact — không đo từ đâu cả. `BatchedVfxFamily.DroppedThisSession` có
đếm số record bị bỏ khi tràn, nhưng **không ai đọc nó**, nên hiện không biết trần có đủ không.

Đúng bài học GCLess luật 7 ("đo trước, chỉnh sau") và đúng vấn đề `PoolSizingReport` đã giải cho pool
GameObject. Cần một bản báo cáo tương đương cho batched family: dump `DroppedThisSession` +
peak-per-frame lúc thoát play mode.

⚠️ Lưu ý khi làm: **đừng lấy mẫu `aliveParticleCount` mỗi frame** — hàm đó đọc ngược từ GPU, ép đồng
bộ CPU–GPU và làm sập frame rate (đã bị một lần, 2026-09-12, tưởng nhầm là bug projectile). Đếm ở
phía CPU (`_count` trước khi Flush) là đủ và miễn phí.

### A3. ADR-0018 vẫn là *Proposed*

Bảng verification của chính nó đòi số liệu profiling từ **Development Build (IL2CPP)** trước khi
chuyển sang Accepted. Editor profile không tính — Burst compile lúc chạy, Mono JIT và subscene baking
đều làm nhiễu (xem `reference_editor_profiling_gotchas`).

### A4. Dọn rác

- 4 prefab `ImpactExplosion` / `ImpactFrost` / `ImpactArc` / `ImpactSiphon` giờ không ai tham chiếu.
- Chạy `BatchedVfxCatalogInvariantTests` (3 test, chưa chạy lần nào).

---

## B. Nợ nội dung (cần hoạ sĩ VFX, hoặc mua)

Hiện cả ba graph dùng **texture hạt mặc định của VFX Graph** và **một lớp quad duy nhất**. Một hiệu
ứng va chạm đạt chuẩn thương mại thường là 3–5 lớp chồng nhau:

| Lớp | Vai trò | Hiện có? |
|---|---|---|
| Flash | loé sáng 2–3 frame tại điểm chạm | ✗ |
| Spark | vệt nhỏ bay nhanh, tắt nhanh | ✗ (quad tròn thay thế) |
| Smoke | khối mờ nở chậm, alpha blend | ✗ |
| Shockwave | vòng phẳng loang ra | ✗ |
| Debris | mảnh vỡ theo normal | ✗ |

Ngoài ra chưa có **flipbook** (texture động), chưa có biến thiên xoay/scale theo tuổi.

Đây là công việc của người làm VFX, không phải của lập trình. Ước lượng trung thực: phần code đã
xong ~90%, phần nhìn mới ~20%.

---

## C. Hai quyết định kiến trúc cần chốt trước khi mua/thuê

### C1. VFX mua sẵn **không cắm thẳng vào backend batched được**

Một `.vfx` mua trên Asset Store là graph tự chứa: nó tự spawn theo Spawn context, tự đặt vị trí từ
transform của GameObject. Backend batched thì ngược lại — graph **phải** đọc 6 `GraphicsBuffer`, nhận
Direct Link từ Event context, và dùng cấu trúc seed → GPU Event → burst. Mua về là phải mổ lại toàn
bộ phần khung, chỉ giữ được phần nhìn (texture, gradient, curve).

**Nhưng facade đã có sẵn lối thoát.** `PoolCatalog.Backend` chọn theo *từng id*, và caller không biết
backend là gì. Nên chiến lược hợp lý:

- **Batched** — thứ bắn nhiều, mỗi frame vài chục đến vài trăm: impact puff, muzzle flash, flourish.
  Đây là chỗ kiến trúc này sinh ra để phục vụ.
- **Pooled** — thứ bắn thưa, một lúc vài cái: boss telegraph, kill beat, hiệu ứng cốt truyện, và
  **mọi thứ mua sẵn**. Cắm prefab vào là chạy, không phải mổ graph.

Nói cách khác: đừng ép mọi hiệu ứng qua batched. Trần GameObject chỉ là vấn đề khi số lượng lớn.

### C2. Nên tách phần khung thành **VFX Subgraph**

Ba graph hiện giống hệt nhau, và phần "đọc 6 buffer + seed + GPU event" chiếm ~80% số node nhưng
**không bao giờ đổi**. Mỗi lần thêm một loại hiệu ứng mới là chép lại toàn bộ khung đó bằng tay —
đúng cách ba graph này ra đời, và cũng là lý do **một lỗi (`location: Current`) nhân bản ra cả ba**.

Gói phần khung vào một **Subgraph Block** thì hoạ sĩ chỉ còn dựng phần nhìn, và sửa khung một lần là
cả ba (hay ba mươi) graph cùng được sửa. Đây là việc nên làm **trước** khi có người thứ hai đụng vào
VFX, không phải sau.

---

## Thứ tự đề xuất

1. **A1** (`Color over Life`) — rẻ nhất, cải thiện thấy rõ nhất.
2. **A4** (dọn prefab + chạy test) — đóng sổ #30.
3. **C2** (Subgraph) — làm trước khi số graph tăng, nếu không chi phí nhân lên.
4. **A2** (đo `FrameCapacity`) — trước khi có màn đông quân thật.
5. **A3** (profiling IL2CPP) — cùng đợt đo perf tổng, không làm lẻ.
6. **B** — khi có người làm VFX. Trước đó giữ nguyên bản hiện tại, nó đã đủ để chơi và test.
