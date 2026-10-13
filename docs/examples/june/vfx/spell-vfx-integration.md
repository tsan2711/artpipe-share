# Spell VFX Integration

> **Status**: **Approved with 2026-09-11 amendments** (gốc Approved 2026-08-28 sau design-review pass 2)
> **Author**: Bi + Claude (design-system)
> **Last Updated**: 2026-09-11
> **System**: #30 — Visual | Vertical Slice | WorldSession
> **Implements Pillar**: art-direction "VFX là centerpiece + nguồn power fantasy" (non-numerical spectacle scaling)

> ### ⚠️ Amendment 2026-09-11 — đọc trước khi implement
>
> Bản Approved 2026-08-28 được duyệt dựa trên **4 thay đổi liên hệ thống mà chưa ai làm**. Một phiên
> đối chiếu-với-code (3 persona, mỗi bên mở file trước khi cho điểm) đã **huỷ cả 4**, và Bi đã chốt
> đổi backend render sang **VFX Graph buffer-driven**. Doc này đã được viết lại theo đó — nó giờ mô tả
> thứ sắp được xây, không phải thứ từng được duyệt.
>
> | Thay đổi liên hệ thống (bản cũ) | Trạng thái |
> |---|---|
> | `IVfxPoolService.Rent() → PooledHandle` | **Huỷ.** Facade sở hữu vé; #30 không bao giờ cầm `PooledHandle`. |
> | `PoolCatalog.PlayerReservedCap` + `isPlayerRequest` | **Huỷ.** Enemy dùng **id catalog riêng**. |
> | `SpellCastCommandElement.ComplexityTier` + `ProjectileData.ComplexityTier`/`SpellGuid` | **Huỷ.** Thay bằng **một byte `VfxVariant`** rơi vào padding có sẵn. |
> | `ProjectileHitEvent.complexityTier` | **Huỷ.** Rule 9 đi qua `ImpactVfxElement`, không qua `ProjectileHitEvent`. |
>
> Ngoài ra: **16 prefab → 2 VFX Graph variant-driven**; `Physical` là **lỗi authoring**;
> Rule 6 (beam) ra khỏi slice đầu và nửa retune-giữa-hold **cắt**.
>
> Nguồn: `production/session-state/spell-vfx-debate.md` (5 quyết định, 3 BLOCKING đã đóng) ·
> `docs/architecture/vfx-graph-buffer-driven-research-2026-09-10.md` ·
> `production/session-state/spell-vfx-slice1-plan.md` (v2 + thẩm định) · ADR-0017 tunable wire.
> Lịch sử review pass 1/pass 2 xem review log — các phát hiện của chúng vẫn còn giá trị, nhưng mọi
> quyết định mâu thuẫn với mục này đều đã bị thay thế.

## Overview

Spell VFX Integration (#30) là một **subscriber-only presentation service** (WorldSession scope) nghe `SpellCastEvent` và `HeatChangedEvent` qua Zenith event bus, map `spellGuid` × modifier chain sang một lời gọi VFX cụ thể trên VFX Pipeline (#6). Nó **không** sở hữu screen-space overlay (Combat Feedback #29), **không** phát âm thanh (Audio #8), và **không** định nghĩa lại cơ chế pool (#6/ADR-0008) — nó là consumer thuần, tác giả cho vocabulary hiệu ứng riêng của spell: muzzle flash, impact burst, và (về sau) cast glow, trail, beam — tất cả phát ra từ chính spell hoặc enemy trong không gian 3D, không phải lớp phủ trên màn hình.

Nhiệm vụ trung tâm là dịch heat và độ dài modifier chain thành spectacle **phi-số**: đạn to hơn, hiệu ứng dày hơn khi heat cao, chain dài hơn tạo hiệu ứng phức tạp hơn — không hiển thị con số nào, đúng nguyên tắc "spectacle scale, không phải damage number" mà art-direction.md đã chốt. Không có #30, mọi spell trông giống nhau bất kể build của người chơi ra sao.

Player không tương tác trực tiếp với #30 — nó là hệ phản ứng thuần túy; player chỉ cảm nhận kết quả.

## Player Fantasy

Cast spell trong SKYBORNE không chỉ là một hành động — nó là bằng chứng sống của hai thứ cùng lúc: **build này là của bạn**, và **bạn đang chơi ở rìa của lửa**.

**"Đang cháy, đang bay gần lửa."** Heat không chỉ là thanh chắn spam — nó là một đồng hồ bạn *nhìn thấy* qua chính spell mình đang cast: heat càng cao, hiệu ứng càng to và sáng. Không có con số nào nhảy lên màn hình — bạn đọc rủi ro và sức mạnh qua mắt, trong 0.5 giây, đúng luật Golden Hour Witch.

Đây là fantasy liên tục, không phải một cú nổ: **Instant/projectile cast** đọc heat **tại mỗi lần bấm** — càng bấm gần đỉnh overheat, mỗi phát bắn tiếp theo càng to/sáng hơn phát trước, và vì bạn bấm liên tục nên bạn thấy nó liên tục. **Beam** đọc heat *tại khoảnh khắc bạn quyết định giữ* — tia beam mang đúng cường độ của thời điểm bạn cam kết, và giữ nguyên cho tới khi bạn nhả. Cả hai đều là "ride the edge of overheat = max spectacle"; khác nhau ở chỗ Instant thưởng cho **nhịp bấm**, Beam thưởng cho **thời điểm bắt đầu**.

> *(Sửa 2026-09-11: bản cũ hứa beam sáng/mờ liên tục suốt lúc giữ. Không code nào sẽ giao điều đó — Rule 6 giờ khoá cường độ tại BeamStart. Một fantasy section hứa thứ build không làm là cách nhanh nhất để nó thôi load-bearing.)*

**"Chữ ký của tôi, sống động."** Modifier chain của bạn không nằm trong một bảng stat — nó nằm trong chính hình dạng của spell. Hai player cùng cầm Frost Bolt nhưng chain khác nhau sẽ thấy hiệu ứng khác nhau: dày hơn, phân nhánh hơn, phức tạp hơn. Khi bạn quick-swap loadout tại checkpoint và quay lại combat, bạn *thấy* build mới **ngay từ cú cast đầu tiên** — không cần mở bảng stat.

Hai lớp chồng lên nhau nhưng không cạnh tranh: modifier chain quyết định **hình dạng** (cố định theo build), heat quyết định **cường độ** (biến thiên theo khoảnh khắc). #30 giữ kỷ luật ambient, gắn liền với spell trong không gian 3D — nó **không** giành sân khấu với những khoảnh khắc "to tiếng" hiếm hoi của Combat Feedback #29; #30 là nhịp thở thường trực, #29 là tiếng hét thỉnh thoảng.

## Detailed Design

### Core Rules

**Rule 1 — Effect inventory: variant-driven, không phải một prefab cho mỗi tổ hợp.**
Trục nguyên tố là **`SpellData.damageType`**, và nó có **4 cột dùng được**: Fire 8° / Frost 190° /
Lightning 235° / Arcane 292°. `Physical` (giá trị mặc định của struct) **là lỗi authoring**, không
phải cột thứ 5 — tooltip của chính field đó đã ghi *"Physical has no palette entry, so a player-facing
spell left at Physical cannot have an icon generated"*. Một spell của player để `Physical` ⇒ log
warning Dev-build có tên spell + render tạm bằng Arcane; nó **không bao giờ** là trạng thái hợp lệ.
*(Điều kiện tiên quyết: đổi `damageType` của các spell đang author khỏi `Physical` trước khi #30 chạy.)*

Bốn **loại** hiệu ứng: cast glow · muzzle flash · trail · impact-burst flourish. Nhưng **nguyên tố
không nhân thành prefab riêng** — nó là dữ liệu đi kèm mỗi lần phát (`VfxVariant`, Rule 9), và graph
tự bake hue theo đó. Slice đầu author **2 VFX Graph** (`muzzle_flash`, `impact_burst`) phục vụ cả 4
nguyên tố, thay cho ma trận 16 prefab của bản cũ.

Hợp đồng scale (thay cho `SetIntensity(float t01)` của bản cũ):
```csharp
public readonly struct VfxScale { public readonly float Size, Emission; }   // blittable
public interface IScalableEffect { void SetScale(in VfxScale scale); }      // chỉ backend Pooled
```
**Service tính, effect chỉ nhân.** Hệ số của Formula IntensityFromHeat sống trong `SpellVfxConfig`
(ADR-0017, `[Tunable]`), **không** trong prefab/graph. Nhờ vậy lỗi "áp `sqrt` hai lần" mà bản cũ phải
viết hẳn một đoạn để cảnh báo trở thành **bất khả thi** — không còn chỗ nào trong asset để áp lần hai.

`SetComplexity(int tier)` **hoãn**: nó nghĩa là nhiều lớp hạt phụ được author riêng. Slice đầu pin
tier = 0; byte `VfxVariant` vẫn mang tier thật nên bật lên sau không phải sửa lại ECS.

---

**Rule 2 — Hai backend, một facade. #30 không bao giờ cầm `PooledHandle`.**
*(Viết lại hoàn toàn — bản cũ yêu cầu `IVfxPoolService.Rent()` trả handle cho #30.)*

Lý do bản cũ sai: auto-return **không** phải thuộc tính của pool, của catalog, hay của handle — nó là
một closure mà `VfxPoolService.Play` tự viết quanh cái handle chính nó vừa mượn. Trao handle trần cho
một presentation service là trao luôn nghĩa vụ trả ⇒ **mỗi lần Rent thành công đều mất vĩnh viễn một
slot**, pool cạn tới `Cap` trong vài giây combat. *(Ghi nhận: `Rent()` trả handle **không** làm sống
lại lỗi nào trong 4 lỗi của ADR-0008 — D1/D2 sống trong `Return`, D4 trong reclaim; đổi *ai* gọi
không đổi *cái gì được kiểm*. Vấn đề là quyền sở hữu, không phải an toàn.)*

`IPoolService` **không đổi một dòng**. `IVfxPoolService` (facade, tầng game) nhận:

```csharp
// one-shot — facade mượn, đặt vị trí, áp scale, Play, và SỞ HỮU auto-return.
void Play(byte effectId, float3 position, float3 normal, in VfxScale scale);

// sustained (beam) — không auto-return; caller sở hữu vé và phải dừng nó.
bool TryPlaySustained(byte effectId, float3 position, float3 normal, in VfxScale scale,
                      out PooledHandle handle);
void StopSustained(in PooledHandle handle);
```

Sau lưng facade có **hai backend**, khai theo từng id trong `PoolCatalog` (`PoolBackend { Pooled, Batched }`):

| | `Pooled` (ParticleSystem + `IPoolService`) | `Batched` (VFX Graph + GraphicsBuffer) |
|---|---|---|
| Đơn vị | 1 GameObject / hiệu ứng | **0 GameObject** — 1 record 32 B trong ring buffer |
| Draw call | 1–4 nếu chung material | **1 / family**, bất kể N |
| CPU mỗi frame | bookkeeping + culling **mỗi system** | 1 `SetData` + 1 `SendEvent` |
| Cull | từng hiệu ứng | **không cull** (bounds phủ region) |
| Dùng cho | thưa, gắn transform, cần `Stop` | **đông, ngắn, fire-and-forget** |

Ranh giới **theo vòng đời, không theo công nghệ**: bất cứ thứ gì cần một cái vé (beam), một transform
cha (cast-glow ở socket tay), hay một component đi kèm (audio, light) **phải** là `Pooled`. Ngược
lại, pool GameObject **chủ động phá** batching của VFX Graph (instancing vỡ khi `Instantiate()` —
bug Unity 6.2 chưa fix), nên đường batched bắt buộc là 0 GameObject.

`IPooledEffect` giữ nguyên một `Play()`. `IScalableEffect` được áp **bên trong facade**, ngay trước
`Play()` — prefab thiếu interface thì **degrade thành phát không-scale**, không bị bỏ qua. Vì vậy
nhánh "Rent thành công nhưng cast interface thất bại ⇒ leak" của bản cũ **không còn tồn tại**
(EC-12 và AC-19 bị xoá).

---

**Rule 3 — Cast-time flow (Instant).** Subscribe `SpellCastEvent`. Với `castType == Instant`: resolve
nguyên tố từ `SpellData.damageType`, đọc `_cachedHeat01` (Rule 4) → `t_vis = sqrt(heat01)` → tính
`VfxScale` từ `SpellVfxConfig` → gọi `Play(muzzleId, pos, dir, scale)`.

Slice đầu **chỉ muzzle-flash**. Cast-glow và trail hoãn:
- **Cast-glow** chưa có điểm gắn — `Play` nhận world position, nên ở MVP nó render tại vị trí caster **cùng frame, cùng điểm, cùng blend additive** với muzzle-flash. Nó cần socket tay/gậy: phụ thuộc **rig**, không phải VFX.
- **Trail** đã bị pass 2 hạ cấp từ "vệt nối theo quỹ đạo" xuống "cụm hạt bắn ra tại điểm phóng, không bám projectile" — tức là **puff thứ ba tại cùng điểm phóng**. Nó thôi làm trail rồi. Quay lại khi thiết kế một trail thật (bám projectile), thứ cần đúng cái hook per-frame mà Rule 8 từ chối một cách đúng đắn.

Vì chỉ còn **một** lời gọi mỗi cast, toàn bộ logic thứ tự-rent và partial-failure của bản cũ (EC-11,
AC-22) không còn đối tượng.

**Rule 4 — Heat intensity cache.** Subscribe `HeatChangedEvent`, cache
`_cachedHeat01 = clamp01(max > 0 ? current / max : 0)` — guard `max == 0` **tường minh** (chia 0 sinh
NaN trước khi `clamp01` kịp áp dụng). Lưu **`heat01` thô**; `t_vis = sqrt(heat01)` tính lại tại điểm
dùng. Snapshot-at-cast, không tween.

**Rule 5 — Chain complexity cache — khoá theo `spellGuid`, KHÔNG phải slotIndex.**
*(Sửa: `SpellCastEvent` **không mang slot index**, chỉ mang `SpellGuid` — bản cũ index cache bằng
`slotIndex` nên không implement được.)* Subscribe `LoadoutChangedEvent` + `ActiveSlotChangedEvent`;
với mỗi slot có spell, gọi `ISpellCastingService.GetPreviewStats(slotIndex).ModifierCount` (pure),
map sang tier, cache **theo guid của spell ở slot đó**. Rebuild toàn bộ mỗi lần event tới — rẻ vì tối
đa `maxSpellSlots` (4) lần gọi. Slice đầu vẫn build cache nhưng chưa có đầu tiêu thụ (tier pin 0).

**Rule 6 — Beam: cường độ khoá tại BeamStart. Hoãn khỏi slice đầu.**
*(Sửa: bản cũ có retune-giữa-hold hai chiều + `BeamDownwardDecayFactor`. Bi xác nhận không chơi beam
nhiều ⇒ **nửa retune bị cắt**, không chỉ hoãn.)*

Khi `SpellCastEvent.castType == BeamStart`: sample `t_vis` và tier **một lần**, `TryPlaySustained`,
giữ `PooledHandle` trong `_activeBeamEffect`, giữ nguyên cường độ suốt hold. Khi `BeamStop` (nhả
trigger **hoặc** bị ép qua `OverheatEvent`): `StopSustained(handle)`, clear.

Beam **không nằm trong slice đầu** vì nó kéo theo đường rent-giữ-vé, đường dọn dẹp lúc teardown
(EC-10 — hôm nay **không có hook nào**), nhánh ép-dừng-khi-overheat, và prefab loop riêng.
*(Ghi chú kỹ thuật: chi phí không phải lý do — retune 60 Hz trên Shuriken đo ra ~120 lời gọi setter
native/giây ≈ 0.0004 ms/frame. Lý do là phạm vi.)*

**Rule 7 — Enemy cast: baseline cố định, **id catalog riêng**.**
*(Sửa: bản cũ dùng chung id với player + `PlayerReservedCap` để player khỏi bị cướp slot.)*
`SpellCastEvent.isPlayerCast == false` ⇒ `VfxScale` cố định (tương đương `t_vis = 0.4`) và tier 1,
**phát trên id catalog riêng của enemy**. Phân vùng id cho **đảm bảo cứng** (demand của enemy vĩnh
viễn không chạm nổi id của player), tốn **một dòng catalog mỗi hiệu ứng, 0 cơ chế mới, 0 đổi chữ ký,
0 guard trong pool** — trong khi `PlayerReservedCap` là arbitration **bên trong mechanism** (đúng thứ
ADR-0008 D1 từ chối, và Audio #8 sẽ thừa kế dù không cần), và dự trữ nó tạo ra là 1 slot trên 18.
Enemy prefab không cần hành vi scale nên **dùng lại đúng prefab/graph đó dưới id khác**.

**Rule 8 — Projectile trail: property trên asset, không theo dõi entity mỗi frame.** Trail dùng
velocity-inherit tại thời điểm phát (hạt bắn ra theo hướng cast ban đầu rồi fade, **không** bám vị trí
thực của projectile ECS đang bay) — vì `Play` không có hook update-per-frame, thêm hook đó sẽ vi phạm
nguyên tắc "pool dumb". Trail lifetime nằm trong cap 0.08–0.35 s theo tier (#19 V-3) — đây là tuổi thọ
**từng hạt**, không phải thời gian bay. **Hoãn khỏi slice đầu** (Rule 3).

**Rule 9 — Impact-burst flourish: một byte, và đi qua `ImpactVfxElement`.**
*(Viết lại: bản cũ đi qua `ProjectileHitEvent.spellGuid` + `ProjectileData.ComplexityTier`/`SpellGuid`.)*

Tiền đề của bản cũ **sai theo code**: `ProjectileHitEvent.SpellGuid` **hardcode `0ul`** trong job
(`SpellProjectileMoveSystem`), kèm comment thừa nhận *"ProjectileData carries no spell identity"*; và
event đó **chỉ bắn khi trúng target** — đâm tường không publish gì, nên flourish sẽ im lặng biến mất ở
đúng ca trượt phổ biến nhất.

Đường mới:
1. **`byte VfxVariant`** — bit 0–1 tier, bit 2–3 nguyên tố (đánh số **từ 1**, để `Variant != 0` phân biệt được "có flourish"). `SpellCastingService` đóng gói lúc build command (nó đã cầm sẵn `damageType` và `chain.Count`).
2. Đi theo đúng đường `ImpactVfxId` đã đi: `SpellCastCommandElement` → `ProjectileData` → `ImpactVfxElement`. Trên `ProjectileData` nó rơi vào **padding có sẵn** ⇒ struct giữ nguyên kích thước.
3. `VfxRequestBridge` (đã là consumer main-thread duy nhất) drain như hôm nay, cộng một lời gọi flourish khi `Variant != 0`.

`ImpactVfxId` tĩnh tiếp tục chạy y hệt hôm nay — flourish là lớp **thứ hai, additive** chồng lên nó.

Vì sao **không** thêm `SpellGuid: ulong` vào `ProjectileData`: việc duy nhất nó làm trong #30 là
resolve nguyên tố. Mang một GUID 8 byte suốt 2–3 giây bay để bên nhận biến nó thành một enum 2 bit là
đi ngược đầu của phép đánh đổi — và nó đẩy struct từ 68 B lên 80 B (94 → 88 entity/chunk trong job
nóng nhất game). *(Chi phí đó thật nhưng nhỏ — ~0.018% băng thông bộ nhớ ở 10k projectile. Bác nó vì
**thừa**, không phải vì chậm.)* Hệ quả phụ: **SVX-OQ-6 đóng** — không cần
`ISpellDatabase.GetSpell(guid).element` (interface chưa từng tồn tại), vì không có tra cứu nào lúc impact.

### States and Transitions

| State | Trigger | → Next |
|---|---|---|
| Idle (per slot) | — | CastFired khi `SpellCastEvent` Instant nhận |
| CastFired | `Play(...)` hoàn tất | Idle ngay — one-shot **không giữ state**: backend `Batched` không có gì để trả, backend `Pooled` thì facade sở hữu auto-return |
| Idle | `SpellCastEvent` BeamStart *(slice sau)* | BeamActive |
| BeamActive | `BeamStop` **hoặc** `OverheatEvent` (force-stop qua SpellCasting Rule 6) | Idle (`StopSustained`) |
| *(ambient)* | `HeatChangedEvent` | cập nhật `_cachedHeat01`, không đổi state |
| *(ambient)* | `LoadoutChangedEvent` / `ActiveSlotChangedEvent` | rebuild cache complexity, không đổi state |

### Interactions with Other Systems

| System | Direction | Data |
|---|---|---|
| Spell Casting (#18) | ← subscribe, → read | `SpellCastEvent`; `GetPreviewStats(slotIndex).ModifierCount`; **`SpellCastCommandElement.VfxVariant`** (byte mới) |
| Heat/Overheat (#13) | ← subscribe | `HeatChangedEvent { current, max }` |
| Spell Database (#4) | ← read | `SpellData.damageType` — **field thật**, không phải `.element`; truy cập qua đường #4 đang dùng (`AsSelf()`, ADR-0001) |
| VFX Pipeline (#6) | → consume + **thay đổi nhỏ** | `IVfxPoolService.Play(id, pos, normal, in VfxScale)`; `PoolCatalog.Entry.Backend`; `IPoolService.TryGetStats` (đã tồn tại) — **`IPoolService` không đổi** |
| ECS / Projectile (#14/#26) | ← drain | `ImpactVfxElement.Variant` (byte mới). **Không** dùng `ProjectileHitEvent` |
| Combat Feedback (#29) | peer | Ranh giới: #29 screen-space, #30 local-3D |
| Loadout (#24) | ← subscribe | `LoadoutChangedEvent`, `ActiveSlotChangedEvent` |
| Boss (#19) | peer, Hard | Kế thừa V-3 (rigid-motion cap 1.0 s), V-4 (additive suppression ×0.45 trong hazard stencil) |

## Formulas

**IntensityFromHeat:**
`t_vis = sqrt(heat01)` ; `sizeMult = sizeBase + sizeSpan × t_vis` ; `emissionMult = emissionBase + emissionSpan × t_vis`

| Variable | Type | Range | Description |
|---|---|---|---|
| `heat01` | float | 0–1 | `clamp01(max > 0 ? current/max : 0)` — guard `max == 0` tường minh trước phép chia |
| `t_vis` | float | 0–1 | Heat sau remap `sqrt` — heat thấp vẫn đẩy hiệu ứng lên nhanh, diminishing return ở heat cao |
| `sizeBase/sizeSpan` | float | 0.8 / 0.8 | **Knob** (`SpellVfxConfig`, ADR-0017) → `sizeMult` 0.8–1.6 |
| `emissionBase/emissionSpan` | float | 0.7 / 1.3 | **Knob** → `emissionMult` 0.7–2.0 |

**Example:** `heat01 = 0.25` → `t_vis = 0.5` → `sizeMult = 1.2`, `emissionMult = 1.35` — hiệu ứng đã rõ ràng dù heat còn thấp.

*(Bốn hệ số là **knob trên wire**, không phải hằng số trong asset — ADR-0017 luật 2. Bản cũ để chúng
nằm trong prefab, tức là 8 bản sao hardcode.)*

---

**ComplexityTierFromChainLength:** `tier = min(2, modifierCount / 2)` (floor).
`modifierCount` 0–5 (cap ở `MAX_ACTIVE_MODIFIERS`) → tier 0/1/2 = Simple/Medium/Complex.
**Example:** `3 → 1`, `5 → 2`.

---

~~**BeamDownwardDecay**~~ — **cắt** cùng nửa retune-giữa-hold của Rule 6.

**Enemy baseline (Rule 7)** — hằng số tuning, không phải formula: `t_vis = 0.4` (`sizeMult ≈ 1.12`), tier 1.

## Edge Cases

- **EC-1** — **Pool/buffer cạn**: bỏ qua hiệu ứng đó, KHÔNG chặn cast. **Silent** — không log, vì cạn là tình huống mong đợi ở tải cao. Backend `Batched`: `TryAppend` trả `false`, **không grow** (GCLess luật 1). Backend `Pooled`: `Play` là no-op.
- **EC-2** — **Beam không rent được tại BeamStart** *(slice sau)*: beam vẫn bắt đầu bình thường (damage/heat-drain không phụ thuộc VFX), #30 **không lưu gì** và ghi một `bool` là không có beam VFX. `BeamStop` khi đó **không thực hiện return nào**. *(Mẹo "vẫn gán handle rỗng cho nhất quán" của bản cũ bị xoá — một `bool` là trạng thái trung thực.)*
- **EC-3** — **Flourish không phát được**: `ImpactVfxId` tĩnh vẫn phát bình thường — impact-damage không bao giờ phụ thuộc flourish.
- **EC-4** — **`spellGuid == 0`**: không xảy ra trên happy path (`SpellCastingService` chặn tại nguồn). #30 không cần code phòng thủ.
- **EC-5** — **`LoadoutChangedEvent` giữa lúc Beam active** *(slice sau)*: beam KHÔNG bị gián đoạn; cường độ/tier giữ giá trị khoá tại BeamStart.
- **EC-6** — **Spell bị gỡ khỏi loadout SAU khi projectile đã bay**: vô hại — `VfxVariant` đã snapshot vào `ProjectileData` lúc spawn, không tra lại cache lúc impact.
- **EC-7** — **Rapid-fire cùng nguyên tố**: #30 **không** tự đặt cooldown/gate — hoàn toàn dựa vào cạn-thì-drop của #6. Backend `Batched` gần như không bao giờ chạm trần vì không có `Cap` per-hiệu-ứng, chỉ có sức chứa ring buffer một frame.
- **EC-8** — **Chưa từng có `HeatChangedEvent`/`LoadoutChangedEvent`** (frame đầu WorldSession): `_cachedHeat01 = 0` (⇒ `sizeMult 0.8`, `emissionMult 0.7` — thấp nhất công thức cho phép) và tier `0` (Simple). **Không** dùng hằng số enemy `0.4`; không undefined behavior.
- **EC-9** — **`damageType` không resolve được** (dữ liệu hỏng thật): fallback prefab/variant Arcane, không crash. **Khác với `Physical`** — Physical resolve hoàn hảo, nó là **lỗi authoring** (Rule 1) và log warning nêu tên spell.
- **EC-10** — **WorldSession teardown / RegionUnloading khi Beam active** *(slice sau)*: `StopSustained` trong teardown path. Beam VFX không gắn entity nên không có destroy-callback tự dọn.
- **EC-13** *(mới)* — **`GraphicsBuffer` và world scene unload**: host `VisualEffect` của backend `Batched` được tạo bằng code dưới root `DontDestroyOnLoad` (mirror `PoolService`), **không** author trong scene world — nếu không, unload world destroy component trong khi Root vẫn giữ buffer trỏ vào nó. `GraphicsBuffer` không phải `UnityEngine.Object`: phải `Release()` tay.
- ~~**EC-11**~~, ~~**EC-12**~~ — **xoá.** EC-11 (partial-failure giữa 3 rent) không còn đối tượng vì slice đầu chỉ có một lời gọi mỗi cast (Rule 3). EC-12 (leak khi cast interface thất bại) không còn tồn tại vì facade sở hữu mọi vé (Rule 2).

## Dependencies

| System | Direction | Hard/Soft | Interface |
|---|---|---|---|
| **VFX Pipeline (#6)** | upstream | Hard | `IVfxPoolService.Play(byte, float3, float3, in VfxScale)`; `PoolCatalog.Entry.Backend`; `IPoolService.TryGetStats` (đã tồn tại). **`IPoolService` không đổi.** |
| **Spell Casting (#18)** | upstream | Hard | `SpellCastEvent`; `GetPreviewStats(slotIndex).ModifierCount`; `SpellCastCommandElement.VfxVariant` (byte mới) |
| **Heat/Overheat (#13)** | upstream | Hard | `HeatChangedEvent { current, max }` |
| **Spell Database (#4)** | upstream | Hard | `SpellData.damageType` — **SVX-OQ-6 đóng**, không cần interface mới |
| **ECS / Projectile (#14/#26)** | upstream | Hard | `ImpactVfxElement.Variant` + `ProjectileData.VfxVariant` (byte, vào padding có sẵn) |
| **Loadout** | upstream | Hard | `LoadoutChangedEvent`, `ActiveSlotChangedEvent` |
| **Combat Feedback (#29)** / **Audio (#8)** | peer | Soft | Không interface chung — chỉ ranh giới sở hữu |
| **Boss (#19)** | peer | Hard | Kế thừa V-3, V-4 |

## Tuning Knobs

| Knob | Default | Safe range | Affects |
|---|---|---|---|
| `sizeBase` / `sizeSpan` | 0.8 / 0.8 | `sizeMult ∈ [0.7, 2.0]×` | Độ lớn theo heat |
| `emissionBase` / `emissionSpan` | 0.7 / 1.3 | `emissionMult ∈ [0.5, 3.0]×` | Mật độ hạt theo heat |
| Heat remap (`sqrt`) | `sqrt` | — | Quá nhanh (`pow(x,0.3)`) → heat thấp đã full; quá chậm (tuyến tính/`pow(x,2)`) → nửa đầu thanh heat vô hình |
| Chain-tier boundary (`÷2`) | 0-1/2-3/4-5 | cố định theo `MAX_ACTIVE_MODIFIERS=5` | Số bậc phức tạp |
| Enemy baseline | `t_vis` 0.4, tier 1 | [0.2, 0.6] | Quá cao: enemy lấn VFX player lúc heat cao. Quá thấp: không đọc được "địch đang cast hệ gì" |

**Bốn knob đầu ở trên wire** (`SpellVfxConfig`, domain `spellvfx`, `Facet = Authored`, ADR-0017).

**Cố ý NGOÀI wire** (ADR-0017 luật 1 — knob giả tệ hơn không có knob):
- `PoolCatalog` `Prewarm`/`Cap`/`Lifetime` — đọc **một lần** lúc start (ADR-0008); ghi runtime không resize pool. Sửa asset rồi restart.
- **Sức chứa ring buffer** của backend `Batched` — `GraphicsBuffer` **không resize được**, cấp phát một lần. Đây là ô "sizing → `const`" của cây phân loại.

~~`PlayerReservedCap` per-id~~ — **xoá** cùng Rule 7 (id riêng thay thế).

**Sở hữu ở nơi khác:** trail lifetime cap 0.08/0.18/0.35 s theo tier (#19 V-3, enforce tại #6 R-7);
additive ×0.45 trong hazard stencil (#19 V-4, #6 R-8).

**Sizing — chưa có số đo.** Con số enemy 298 shots/s mà bản cũ dùng để tính `Cap` là **cận trên của
một `MaxActiveCasters` chưa từng được chọn**, rồi chia 4 theo một giả thiết mà chính OQ-7(d) đã tự
bác. Nó vi phạm R-6 của #6 (*"`Prewarm` = observed `PoolStats.PeakRented` from a real session"*). Mọi
số `Cap` phải đo lại (F9 `PoolSizingReport`). Backend `Batched` phần lớn thoát khỏi câu hỏi này —
chi phí của nó không tỉ lệ với số hiệu ứng đang sống.

## Visual/Audio Requirements

**Ngôn ngữ hình theo loại.** Muzzle-flash là bùng nổ tức thời tại điểm phóng, đọc trong 1–2 frame,
silhouette rõ nhất — đây là "tín hiệu bắt đầu". Impact-burst-flourish là climax, ăn ngân sách hình ảnh
lớn nhất vì đây là điểm player nhận feedback "trúng". Cast-glow là aura bùng tại tay/staff *(hoãn —
cần socket)*; với Instant nó **không ramp**, chỉ tồn tại một khung hình ngắn. Trail là **cụm hạt bắn
ra tại điểm phóng** (launch-puff), velocity-inherit rồi fade trong 0.08–0.35 s — **không** bám theo
projectile *(hoãn)*.

**Ngôn ngữ hình theo nguyên tố.** **Fire** = cầu lửa lởm chởm, cạnh bùng nổ bất quy tắc, phồng-vỡ.
**Frost** = tinh thể sắc cạnh hình học cứng, vỡ giòn không phồng. **Lightning** = tia rẽ nhánh, chuyển
động tức thời không có giai đoạn "lớn dần". **Arcane** = vòng xoáy hình học đều, xoay/co vào tâm —
đối lập trực tiếp với sự bất quy tắc của Fire.

**Constraint bắt buộc.**
- Additive blend toàn bộ (ràng buộc bởi hazard stencil ×0.45 + world-VFX gradient rule của art-direction.md).
- **Một material Additive dùng chung + một atlas**; hue nguyên tố nằm ở vertex colour / `startColor` theo `VfxVariant`, **không** ở material riêng ⇒ 1–4 draw call bất kể số instance. Vẫn thoả "bake sẵn hue, không đổi hue runtime".
- **Cast shadows + receive shadows = OFF.** Backend `Batched` không bao giờ cull (bounds phủ region); bật shadow sẽ đẩy toàn bộ hạt vào **mọi** shadow pass. Additive không cần shadow.
- Backend `Pooled`: **Play On Awake = OFF** — pool gọi `SetActive(true)` *bên trong* rent nên setter scale luôn rơi sau khi object đã sống.
- Cấm full-screen flash/overlay — mọi hiệu ứng cục bộ tại nguồn/quỹ đạo, tách vùng pixel với heat-vignette (đã khoá ở combat-feedback-system.md).
- Trail rigid-motion cap 0.08–0.35 s theo tier (#19 V-3) — không viền cứng nào tồn tại quá 1 s.

**Enemy-cast palette.** Giữ nguyên hue nguyên tố, không desaturate riêng. Khác biệt nằm ở
**motion/tempo** (player sống động theo heat, enemy luôn tĩnh), không phải màu — đúng nguyên tắc "hue
chỉ mang nghĩa nguyên tố, không mang nghĩa phe".

**Nguyên tắc art bible.** *"VFX là centerpiece — ngân sách hình ảnh dồn vào trời, mây, spell"* — đây là
lý do #30 được cấp asset riêng. *"Sky as stage — tín hiệu gameplay nổi lên bằng độ bão hoà và lõi
sáng, không bằng chi tiết"* — quyết định trực tiếp cơ chế tách nền: heat-driven saturation/lõi sáng,
không phải thêm chi tiết hình học khi mạnh lên.

## UI Requirements

Không có. #30 là hiệu ứng thuần trong không gian 3D — không chạm UI, không chạm HUD.

## Acceptance Criteria

**SVX-AC-1a** *(BLOCKING, [Unit])* — **GIVEN** mỗi asset VFX đã author, **WHEN** kiểm tra, **THEN** backend `Pooled` implement cả `IPooledEffect` lẫn `IScalableEffect`; backend `Batched` có graph đọc `VfxVariant` từ buffer — Rule 1/2.

**SVX-AC-1b** *(ADVISORY, [Config/Data])* — hue bake khớp spec (Fire 8°/Frost 190°/Lightning 235°/Arcane 292°) — Rule 1.

**SVX-AC-1c** *(BLOCKING, [Config/Data], mới)* — **GIVEN** một `SpellData` của player để `damageType = Physical`, **WHEN** cast, **THEN** một warning Dev-build **nêu tên spell** được log và hiệu ứng render bằng Arcane — Rule 1, EC-9.

**SVX-AC-2** *(BLOCKING, [Integration], viết lại)* — **GIVEN** `IVfxPoolService`, **WHEN** gọi `Play(id, pos, normal, scale)` cho một id backend `Batched`, **THEN** **không** `GameObject` nào được rent, một record được append, và `IPooledEffect`/`IPoolService` **không đổi chữ ký** — Rule 2.

**SVX-AC-2b** *(BLOCKING, [Unit], mới)* — **GIVEN** `PoolCatalog` có một entry `Batched`, **WHEN** `PoolService` khởi tạo, **THEN** id đó **có mặt** trong `PoolIds` (nên `OnValidate` vẫn bắt được trùng id với domain khác — ADR-0008 R6), `TryRent(id)` trả `false`, và **0 warning** được log.

**SVX-AC-3** *(BLOCKING, [Integration])* — **GIVEN** player cast một spell Instant, **WHEN** `SpellCastEvent` bắn ra, **THEN** muzzle-flash đúng nguyên tố được phát với scale từ heat hiện tại, trong cùng lần drain Zenith xử lý event đó — Rule 3.

**SVX-AC-4** *(BLOCKING, [Unit])* — **GIVEN** `HeatChangedEvent{current, max}` vừa publish, **WHEN** cast Instant tiếp theo, **THEN** scale áp dụng tính từ `t_vis = sqrt(clamp01(max > 0 ? current/max : 0))` — không phải heat của lần cast trước — Rule 4.

**SVX-AC-5** *(BLOCKING, [Integration], viết lại)* — **GIVEN** `LoadoutChangedEvent` đổi modifier count của một spell, **WHEN** ngay sau đó cast spell đó, **THEN** tier áp dụng là tier MỚI, tra **theo `spellGuid`**; và **không** hiệu ứng nào được phát tại thời điểm xử lý chính `LoadoutChangedEvent` — Rule 5.

**SVX-AC-7** *(BLOCKING, [Integration], slice sau)* — **GIVEN** Beam active, **WHEN** `BeamStop` (hoặc force-stop qua `OverheatEvent`), **THEN** outstanding-rent của id đó về baseline trước-BeamStart (verify qua `PoolStats.Rented`), và một `BeamStop` thứ hai liên tiếp là no-op an toàn — Rule 6.

**SVX-AC-7b** *(BLOCKING, [Integration], slice sau, viết lại)* — **GIVEN** `TryPlaySustained` trả `false` tại BeamStart, **WHEN** `BeamStop` sau đó, **THEN** không exception, và **không thao tác return nào** được thực hiện — EC-2.

**SVX-AC-8** *(BLOCKING, [Integration])* — **GIVEN** `isPlayerCast == false`, **WHEN** VFX enemy phát, **THEN** scale/tier là hằng số cố định bất kể heat/chain, **trên id catalog riêng của enemy**, và không `HeatChangedEvent` nào chỉnh lại — Rule 7.

**SVX-AC-9** *(ADVISORY, [Visual])* — **GIVEN** VFX player cạnh VFX enemy cùng nguyên tố, quét `heat01` = 0, ≈0.4, 1.0, **WHEN** so sánh, **THEN** hiệu ứng player đọc rõ hơn baseline enemy ở **mọi** mức heat được quét — Rule 7. *(Ở `heat01=0`, `sizeMult` player = 0.8 < enemy ≈ 1.12 — đúng failure mode bảng Tuning Knobs tự nêu.)*

**SVX-AC-10** *(BLOCKING, [Integration], slice sau)* — **GIVEN** trail đã phát lúc cast, **WHEN** entity ECS di chuyển ở các frame sau, **THEN** hạt trail **KHÔNG** cập nhật theo vị trí sống của entity — Rule 8.

**SVX-AC-11** *(BLOCKING, [Integration], viết lại)* — **GIVEN** một projectile cast với tier 2, **WHEN** loadout đổi trước khi nó trúng, rồi nó trúng, **THEN** flourish đọc tier 2 từ **`ImpactVfxElement.Variant`** — không tra lại cache runtime — Rule 9, EC-6.

**SVX-AC-12** *(BLOCKING, [Integration], viết lại)* — **GIVEN** `VfxVariant` đóng gói lúc build command, **WHEN** nó đi `SpellCastCommandElement` → `ProjectileData` → `ImpactVfxElement` → lời gọi flourish, **THEN** byte giống hệt ở mọi chặng — và **`sizeof(ProjectileData)` không tăng** so với trước khi thêm field — Rule 9.

**SVX-AC-12b** *(BLOCKING, [Integration], mới)* — **GIVEN** một projectile đâm **tường** (env hit, không trúng target), **WHEN** impact xảy ra, **THEN** flourish vẫn phát — đây là ca mà `ProjectileHitEvent` không phủ được và là lý do Rule 9 đổi đường.

**SVX-AC-13** *(BLOCKING, [Unit])* — `heat01 = 0.25` ⇒ `t_vis = 0.5`, `sizeMult = 1.2` (±0.01), `emissionMult = 1.35` (±0.01).

**SVX-AC-13b** *(BLOCKING, [Unit])* — `max = 0` ⇒ `heat01 = 0` (không NaN/Infinity).

**SVX-AC-14** *(BLOCKING, [Unit])* — `modifierCount = 3` ⇒ tier 1; `= 5` ⇒ tier 2; tier không bao giờ vượt 2 với mọi `modifierCount ∈ [0,5]`.

**SVX-AC-15** *(BLOCKING, [Integration], gộp từ AC-15a/b/c)* — **GIVEN** pool/buffer của một id đã cạn, **WHEN** `Play(...)` được gọi, **THEN** đó là **no-op im lặng** — không throw, **không cấp phát**, không log — và cast/impact/damage vẫn chạy đủ. Backend `Batched` cụ thể: `TryAppend` trả `false` và **không grow buffer** — EC-1.

**SVX-AC-16** *(BLOCKING, [Integration], slice sau)* — **GIVEN** teardown/RegionUnloading khi Beam active, **WHEN** teardown chạy, **THEN** vé beam được `StopSustained` tường minh, zero handle leak — EC-10.

**SVX-AC-16b** *(BLOCKING, [Integration], mới)* — **GIVEN** backend `Batched` đang chạy, **WHEN** world scene unload rồi load lại, **THEN** host `VisualEffect` vẫn sống (nó ở root `DontDestroyOnLoad`), buffer không bị treo, và không exception — EC-13. Khi service dispose, `GraphicsBuffer.Release()` được gọi.

**SVX-AC-17** *(BLOCKING, [Integration], slice sau)* — **GIVEN** Beam active, **WHEN** `LoadoutChangedEvent` bắn trước `BeamStop`, **THEN** cường độ/tier của beam **không** bị chỉnh — Rule 6, EC-5.

**SVX-AC-18** *(BLOCKING, [Unit])* — `damageType` không resolve được ⇒ fallback Arcane, không throw, có warning Dev-build — EC-9.

**SVX-AC-20** *(BLOCKING, [Unit])* — WorldSession mới, chưa `HeatChangedEvent`/`LoadoutChangedEvent` nào, cast ngay ⇒ `heat01 = 0` (`sizeMult 0.8`, `emissionMult 0.7`) và tier 0 — không NaN, không uninitialized — EC-8.

**SVX-AC-21** *(BLOCKING, [Integration])* — **GIVEN** nhiều Instant cast liên tiếp nhanh hơn tốc độ hồi của pool, **WHEN** các lần phát sau xảy ra, **THEN** #30 **KHÔNG** tự áp cooldown/gate của riêng nó — chỉ dựa vào cạn-thì-drop — EC-7.

**SVX-AC-23** *(BLOCKING, [Integration], mới — đóng lỗi thứ tự frame)* — **GIVEN** trong cùng một frame có cả một impact (drain ở `Update`) lẫn một `SpellCastEvent` (Zenith drain ở `PostLateUpdate`), **WHEN** frame kết thúc, **THEN** **cả hai** hiệu ứng xuất hiện **trong cùng frame đó** — muzzle-flash không được trễ một frame so với impact.

~~AC-6, AC-6b, AC-6c~~ — **xoá** cùng nửa retune-giữa-hold của Rule 6.
~~AC-19~~ — **xoá**: nhánh "Rent thành công, cast interface thất bại" không còn tồn tại (Rule 2).
~~AC-22~~ — **xoá**: slice đầu chỉ có một lời gọi mỗi cast nên không có partial-failure để rollback (Rule 3).

## Open Questions

| ID | Question | Owner | Resolve by |
|---|---|---|---|
| **SVX-OQ-4** | Nếu #15/#6 triển khai Mass tier cho enemy projectile bodies — #30 có cần mở rộng gì không? *(Bớt gấp: backend `Batched` **chính là** hình dạng Mass tier, nên hai đường giờ hội tụ thay vì phân kỳ.)* | Bi | Cùng lúc với #15 |
| **SVX-OQ-5** | Hai spell cùng nguyên tố (Fireball vs Fire Nova) trông **giống hệt nhau về hình**, chỉ khác cường độ/tier. Chấp nhận cho MVP, hay spell "signature" cần biến thể riêng? *(Bớt gấp: với graph variant-driven, thêm một biến thể = thêm giá trị vào `VfxVariant` + một nhánh trong graph, **không** phải một prefab mới. Rẻ để thử, rẻ để sửa.)* | Bi | Trước content-lock |
| **SVX-OQ-7** | **Sizing chưa có số đo.** (a) chưa có worked example cho flourish; (b) pierce/AoE sinh N impact cùng frame; (c) `MaxActiveCasters` (#15) chưa chốt nên 298 shots/s vẫn là placeholder; (d) encounter đơn-nguyên-tố dồn hết demand lên một id. *(Backend `Batched` vô hiệu hoá phần lớn (a)–(d) vì chi phí không tỉ lệ số hiệu ứng sống; phần còn lại chỉ áp cho id `Pooled`.)* | Bi | Trước content-lock |
| **SVX-OQ-8** | **Ngân sách VFX.** (a) `technical-preferences.md` ghi "500K–1M GPU particles (VFX Graph)" — sau khi cài package thì ngân sách này **mới thực sự áp dụng được**, nhưng (b) vẫn **chưa có ngân sách overdraw/fill-rate**, và batching **không** sửa overdraw. (c) Batching compatibility đã trả lời: **một material, hue ở vertex colour**. | Bi / performance-analyst | Trước content-lock |
| ~~SVX-OQ-1~~ | #6 chấp nhận `Rent()` — **đóng**: `Rent()` bị huỷ, thay bằng overload `Play` trên facade. | — | — |
| ~~SVX-OQ-2~~ | `SpellCastCommandElement.ComplexityTier` — **đóng**: thay bằng `VfxVariant` (một byte, gói cả nguyên tố lẫn tier). | — | — |
| ~~SVX-OQ-3~~ | `ProjectileHitEvent.complexityTier` + `ProjectileData.SpellGuid` — **đóng**: xác nhận đường đó **không tồn tại** (`SpellGuid` hardcode `0ul`, event không bắn khi đâm tường). Rule 9 đổi sang `ImpactVfxElement`. | — | — |
| ~~SVX-OQ-6~~ | `ISpellDatabase.GetSpell(guid).element` — **đóng**: field thật là `SpellData.damageType`, và sau Rule 9 thì không có tra cứu database nào lúc impact. | — | — |
