# Bot Attack VFX & Rival Variety

> **Status**: Approved 2026-09-20
> **Creative Director Review (CD-GDD-ALIGN)**: APPROVED 2026-09-20
> **Author**: Bi + Claude
> **Last Updated**: 2026-09-20
> **Follow-up required**: `combat-system.md` lists DEFENDER_DPS base = 15; authoritative value is 8 (per rival-faction.md + this GDD). Update combat-system.md to reconcile.
> **Implements Pillar**: Visible Swarm — mọi hoạt động của colony đều thấy được trực tiếp


> **Implementation note (2026-09-24):** built as `EntityVfxRenderer` + `EntityVfx.shader`. Two deviations, same intent:
> (1) no compute shader — each particle is written once at birth into a ring `StructuredBuffer` and the **vertex shader
> evaluates it analytically** from birth data + `_VfxTime` (drag + gravity + size + fade), so there is zero per-frame
> GPU/CPU simulation and no compute requirement on low-end Android; still one `DrawMeshInstancedIndirect`, skipped when
> nothing is alive. (2) no `RivalDestroyedEvent` — the simulation pushes requests into `Core.Vfx.EntityVfxQueue`
> (static ring, 512/frame, drops when full) from `BotCombatSystem` (Muzzle / Impact / CoreImpact) and
> `BotSimulationService` (Death / Spawn / Harvest). Capacity 4096 live, 768 births/frame. Rival variety (Rules 13–15)
> and per-6-frame arcs are not implemented; muzzle flash fires per shot instead.

## Overview

**Bot Attack VFX & Rival Variety** là lớp presentation của toàn bộ combat trong NanoSwarm Colony. Hệ thống này có hai trách nhiệm:

1. **GPU particle pipeline** — tất cả particles trên toàn map (attack arc của Defender, dissolve burst khi rival chết, ambient combat spark) được mô phỏng bằng compute shader và render trong **một drawcall duy nhất** (DrawMeshInstancedIndirect). Mỗi particle là một struct trên GPU; state (position, velocity, lifetime, color) được lưu dưới dạng texture 2D phẳng, compute shader update mỗi frame, kết quả truyền vào ComputeBuffer rồi render tất cả cùng lúc. Không có ParticleSystem GameObject, không có per-frame allocation.

2. **Rival bot variety** — ba loại rival bot (Scout / Soldier / Bruiser) với visual và behavior khác nhau, thay thế rival đơn thuần hiện tại. Mỗi loại có particle color riêng, scale riêng, và drop-on-death effect riêng.

Mục tiêu performance: duy trì **20–30 visual events/giây** trong rival wave phase (per ASMR target) với zero CPU spike từ particle spawning.

## Player Fantasy

Bạn không điều khiển một đội quân — bạn nhìn vào **một cơ thể sống**.

Khi làn sóng rival đỏ xuất hiện ở rìa màn hình, swarm không hỗn loạn. Không có lệnh nào được ra. Một lớp Defender mỏng tách ra khỏi dòng chảy thu hoạch đang lặng lẽ tiếp diễn — giống như bạch cầu tách khỏi máu — di chuyển ra để chặn, ánh lên những tia nano-arc ngắn khi chạm địch, rồi từng chấm đỏ tan ra thành burst nhỏ. Sau đó lớp Defender đó tự hòa vào colony như chưa từng rời đi. Harvest vẫn tiếp tục trong suốt quá trình đó.

Tension sống trong **game state** — làn sóng đỏ đang đến, Core HP đang giảm — không phải trong visual effects. VFX language phục vụ cảm giác hệ thống đang vận hành, không phải khuếch đại áp lực.

Không có triumph. Không có tension trong visual. Chỉ có sự hài lòng yên tĩnh khi thấy **logic của một hệ thống hoạt động hoàn hảo**.

Visual language của hệ thống này phục vụ điều đó: attack arc không phải hiệu ứng mạnh — nó là tín hiệu nhỏ chính xác. Rival dissolve không phải nổ — nó là sự tan biến lặng lẽ. Mọi particle đều là một phần của cơ thể, không phải show-off riêng lẻ.

## Detailed Design

### Core Rules

**GPU Particle Pipeline**

1. Tất cả VFX particles trên toàn map render trong **một DrawMeshInstancedIndirect call** duy nhất mỗi frame. Không có ParticleSystem GameObject, không có per-event allocation.
2. `ComputeBuffer` chứa tối đa `GPU_PARTICLE_CAPACITY = 1024` particle struct live cùng lúc. Struct mỗi particle: `float2 position`, `float2 velocity`, `float lifetime`, `float maxLifetime`, `float3 color`, `uint typeId`. *(Note: dùng `uint` không phải `byte` — HLSL không có byte type.)*
3. Một compute shader update toàn bộ particle mỗi frame (integrate velocity, decay lifetime, kill expired). Output ghi vào instance buffer cho vertex shader. **Dispatch chỉ chạy khi `liveCount > 0`** — skip nếu không có particle live (tránh render-pass flush không cần thiết trên tiled GPU Android).
4. CPU chỉ viết vào buffer khi có VFX event — không poll, không scan mỗi frame.

**Attack Arc (Rule 5–7)**

5. Defender trong state `Intercept`, rival còn sống trong `ATTACK_RANGE = 1.5m` → emit 1 attack arc mỗi **6 frames** (~10 arcs/giây tại 60fps). Không tie với damage tick (damage vẫn mỗi FixedUpdate).
6. Mỗi arc = 4 particles, màu `#4FC3F7` (cyan-blue), lifetime 80ms. Hướng từ `defenderPosition` về `rivalPosition`, arc subtends ~30°.
7. Kiểm tra `rival.IsAlive` ngay trước khi emit — nếu rival đã chết frame này, bỏ qua arc đó.

**Death Dissolve (Rule 8–10)**

8. `IRivalService.DamageRival()` phải fire `RivalDestroyedEvent` với payload `{rivalPosition, rivalTypeId, isElite}` **trước** `Destroy(gameObject)`. *(Implementation debt: event chưa có trong code — cần add vào IRivalService.)*
9. Standard death (Scout/Soldier/Bruiser): 8 particles, màu `#EF5350` → `#BDBDBD`, lifetime 220ms, radial burst inward-spring.
10. Elite death: 20 particles (inner ring 8 + outer ring 12), màu warm-to-cool, lifetime 400ms, dual-ring. Visual-only — không gây damage.

**Spawn Entry (Rule 11–12)**

11. Wave chuyển sang `Spawning` → mỗi rival bot emit 6 particles, màu `#FFFFFF` → rival's base color, lifetime 300ms, radial convergence thẳng về spawn point (particles xuất phát từ vị trí random quanh spawn, velocity hướng vào tâm).
12. Stagger: rival[i] emit tại `i × (0.5 / waveSize)` giây. Tránh spike 80 particles trên 1 frame. VFX system tag mỗi stagger batch với `waveId` — increments mỗi khi wave chuyển sang `Spawning`. Pending stagger items với stale `waveId` bị cancel ngay khi nhận `RivalDestroyedEvent` trước khi emit.

**Rival Variety (Rule 13–15)**

13. Ba loại rival, xác định bởi `visual_id`:

| visual_id | Type | HP | Speed | Scale | Core DPS |
|-----------|------|----|-------|-------|----------|
| 0 | Scout | 12 | 2.2 m/s | 0.7× | 3 |
| 1 | Soldier | 20 | 1.5 m/s | 1.0× | 5 |
| 2 | Bruiser | 45 | 0.9 m/s | 1.6× | 9 |

14. Wave composition:
```
bruiserCount = max(0, floor(waveIndex / 4))
soldierCount = max(0, floor(waveSize × 0.5))
scoutCount   = waveSize - soldierCount - bruiserCount
```

15. **Elite**: Spawns khi `waveIndex % 5 == 0` và `waveIndex >= 5`. HP=150, Speed=1.1m/s, Scale=2.2×, Core DPS=18. Luôn thay thế 1 Bruiser slot (vì `bruiserCount ≥ 1` tại mọi waveIndex ≥ 4 theo F1; waveSize không đổi). Matter reward khi giết: `80 + waveIndex × 5`.

### States and Transitions

GPU particle system không có state machine. Mỗi particle chỉ có: `lifetime` đang đếm ngược. Compute shader kill particle khi `lifetime ≤ 0`. CPU phía trên drive 4 VFX event types qua buffer write.

Rival type state machine không thay đổi so với `rival-faction.md` — Scout/Soldier/Bruiser đều follow cùng Advancing → Core path.

### Interactions with Other Systems

| System | Data In | Data Out | Notes |
|--------|---------|----------|-------|
| Bot Behavior (Defender) | Defender Intercept state + rival position | Attack arc emit | VFX reads state; không modify combat |
| Rival Faction / IRivalService | `RivalDestroyedEvent`, wave `Spawning` event | — | IRivalService cần thêm pre-destroy event (impl debt) |
| Combat System | — | — | VFX không touch damage math |
| ColonyBalance.cs | `GPU_PARTICLE_CAPACITY = 1024` | — | Tuning knob |

## Formulas

**F1 — Wave Composition**

```
bruiserCount(i) = max(0, floor(i / 4))
soldierCount(i) = max(0, floor(waveSize(i) × 0.5))
scoutCount(i)   = waveSize(i) − soldierCount(i) − bruiserCount(i)
```

| Variable | Symbol | Type | Range | Description |
|----------|--------|------|-------|-------------|
| waveIndex | i | int | 0, 1, 2, … | Increments sau mỗi wave resolve |
| waveSize(i) | W | int | 5–40 | Từ rival-faction.md F1 |

**Output range** *(formula: soldiers = floor(W×0.5), scouts = W − soldiers − bruisers)*:

| waveIndex | waveSize | Scouts | Soldiers | Bruisers |
|-----------|----------|--------|----------|----------|
| 0 | 5 | 3 | 2 | 0 |
| 4 | 13 | 6 | 6 | 1 |
| 8 | 21 | 9 | 10 | 2 |
| 18 | 40 (cap) | 16 | 20 | 4 |
| 20+ | 40 (cap) | 15 | 20 | 5 |

*Note: bruiserCount keeps growing beyond wave 18 (floor(i/4)); waveSize caps at 40 from wave 18.*

---

**F2 — Elite Matter Reward**

```
eliteMatterReward(i) = ELITE_MATTER_BASE + i × ELITE_MATTER_SCALE
```

| Variable | Symbol | Type | Range | Default |
|----------|--------|------|-------|---------|
| waveIndex | i | int | 5, 10, 15, … | — |
| ELITE_MATTER_BASE | Eb | int | 50–200 | 80 |
| ELITE_MATTER_SCALE | Es | int | 2–10 | 5 |

**Output:** Wave 5: 105 Matter. Wave 20: 180 Matter.

---

**F3 — Attack Arc Interval**

```
arcInterval_seconds = ARC_RATE_DIVISOR / targetFPS
```

| Variable | Default | Description |
|----------|---------|-------------|
| ARC_RATE_DIVISOR | 6 | Frames giữa hai arc events từ cùng một Defender |
| targetFPS | 60 | Android target framerate |

**Output:** 10 arcs/giây/Defender. 20 Defenders → ~200 arc events/giây trải đều.

---

**F4 — TTK (Time to Kill) per Rival Type**

*Kế thừa từ combat-system.md:* `TTK = rivalHP / (defenderCount × DEFENDER_DPS)`

| Type | HP | TTK (1 Defender) | TTK (3 Defenders) |
|------|----|-----------------|-------------------|
| Scout | 12 | 1.5 s | 0.5 s |
| Soldier | 20 | 2.5 s | 0.83 s |
| Bruiser | 45 | 5.6 s | 1.875 s |
| Elite | 150 | 18.8 s | 6.25 s |

*(DEFENDER_DPS = 8 default)*

---

**F5 — GPU Particle Budget**

Worst-case peak: attack arcs (20 Defenders × 4 = 80) + standard dissolves (8 × 8 = 64) + elite death (20) + spawn entry (10 bots × 6 = 60) = **224 particles**. Under `GPU_PARTICLE_CAPACITY = 1024` ceiling.

## Edge Cases

- **Nếu `ComputeBuffer` đầy (>1024 live particles)**: New emit call bị drop silently. VFX miss xảy ra nhưng gameplay không bị ảnh hưởng. Log warning khi `liveCount > GPU_PARTICLE_CAPACITY × 0.9` để detect budget creep.
- **Nếu rival bị Destroy trước khi arc frame timer tick**: Rule 7 check `rival.IsAlive` trước emit → arc bị bỏ qua. Không có zombie arc trỏ vào vị trí cũ.
- **Nếu `RivalDestroyedEvent` fire 2 lần cùng 1 rival**: Guard `_isDestroyed = true` trên rival instance trước khi call `Destroy()`. Event fire đúng một lần.
- **Nếu player dùng "Clear Wave" ad khi spawn stagger chưa xong**: Rival bị destroy tức thì → `RivalDestroyedEvent` fire cho từng rival. Pending spawn entry particles (scheduled nhưng chưa emit) phải bị cancel. VFX system cần track `waveId` để invalidate pending stagger batch.
- **Nếu `ARC_RATE_DIVISOR < 3`** (misconfiguration): Log error; default về 6.
- **Nếu device không hỗ trợ Compute Shader** (OpenGL ES 3.0 thay vì 3.1+): `SystemInfo.supportsComputeShaders == false` → disable toàn bộ VFX pipeline (no-VFX mode). Gameplay tiếp tục bình thường; log `"Device does not support compute shaders — bot-attack-vfx disabled"`.
- **Nếu app background mid-wave**: Tất cả rivals bị destroy (rival-faction.md Rule 12) → `RivalDestroyedEvent` fire tất cả. Worst case: 40 × 8 = 320 particles spike — dưới budget (1024). Buffer clears trong <220ms.

## Dependencies

| System | Direction | Nature | Interface |
|--------|-----------|--------|-----------|
| Bot Behavior (Defender) | upstream | hard | Defender `Intercept` state + `rivalPosition` → trigger Attack Arc |
| Rival Faction / IRivalService | upstream | hard | `RivalDestroyedEvent{pos, typeId, isElite}` (cần add) + wave `Spawning` state → trigger Death Dissolve + Spawn Entry |
| Combat System | upstream | soft | `ATTACK_RANGE` = arc length reference; VFX không modify combat math |
| ColonyBalance.cs | upstream | soft | `GPU_PARTICLE_CAPACITY`, `ARC_RATE_DIVISOR`, `ELITE_MATTER_BASE`, `ELITE_MATTER_SCALE` |
| Resource System | downstream | soft | Elite kill → `IResourceService.Add(Matter, eliteMatterReward)` |
| Audio System | downstream | soft | VFX events trigger SFX per event type |
| HUD | downstream | soft | Screen-edge flash on wave Spawning (2D UI overlay, không phải GPU particle) |

**Implementation debt:** `IRivalService` cần thêm `RivalDestroyedEvent` pre-destroy hook trước khi system này có thể implement.

## Tuning Knobs

| Knob | Default | Range | Effect |
|------|---------|-------|--------|
| `GPU_PARTICLE_CAPACITY` | 1024 | 512–2048 | Max live particles. Tăng nếu future ambient VFX cần budget |
| `ARC_RATE_DIVISOR` | 6 | 3–12 | Frames giữa 2 attack arcs. Thấp hơn = dày hơn, tốn hơn |
| `SCOUT_HP` | 12 | 8–25 | Scout fragility — thấp = die nhanh = ít visual event |
| `SCOUT_SPEED` | 2.2 m/s | 1.8–3.5 | Scout velocity; phải > RIVAL_SPEED (1.5 default) |
| `BRUISER_HP` | 45 | 30–80 | Bruiser tank — cao = cần nhiều Defenders |
| `BRUISER_SPEED` | 0.9 m/s | 0.5–1.3 | Phải < RIVAL_SPEED (1.5 default) |
| `ELITE_HP` | 150 | 80–250 | Elite durability |
| `ELITE_CORE_DPS` | 18 | 10–30 | Punishment nếu Elite reach Core |
| `ELITE_MATTER_BASE` | 80 | 50–200 | Matter reward floor khi giết Elite |
| `ELITE_MATTER_SCALE` | 5 | 2–10 | Matter reward growth per wave index |

## Visual/Audio Requirements

*Full visual spec: `design/gdd/art-director-vfx-notes.md`*

**Creative direction:** "Signal, not show." Mọi effect là tín hiệu nhỏ, chính xác — không phải explosion.

### VFX Summary

| Event | Particles | Color | Duration | Shape |
|-------|-----------|-------|----------|-------|
| Defender Attack Arc | 4 | `#4FC3F7` (cyan-blue) | 80ms | Arc sweep 30°, 0.9m |
| Standard Death (Scout/Soldier/Bruiser) | 8 | `#EF5350` → `#BDBDBD` | 220ms | Radial burst inward-spring |
| Elite Death | 20 | `#EF5350` → `#FF8A65` → `#CFD8DC` | 400ms | Dual-ring (inner r=0.35m, outer r=0.8m) |
| Spawn Entry | 6/bot | `#FFFFFF` → rival color | 300ms | Radial convergence inward (thẳng về spawn point) |

### Rival Sprite Variants

| Type | Color | Scale | Shape |
|------|-------|-------|-------|
| Scout | `#FF7043` (orange-red) | 0.7× | Hexagon pointed-top |
| Soldier | `#EF5350` (standard red) | 1.0× | Hexagon flat-top |
| Bruiser | `#D32F2F` (deep red) | 1.6× | Hexagon flat-top, thicker outline |
| Elite | `#D32F2F` + glow ring | 2.2× | Bruiser sprite với emissive ring |

### Audio

SFX spec thuộc `audio-system.md`. Trigger points cần SFX:
- Attack arc emit → light "zap" tick (pitched by rival type)
- Standard death dissolve → soft "fizzle" 
- Elite death → slightly larger "pop" + low resonance
- Wave spawn → "materialise" hiss (per-bot, staggered)

**Screen-edge flash** (wave Spawning alert): 2D UI overlay, 8px red vignette, 500ms fade — owned by HUD, not GPU particle system.

📌 **Asset Spec** — Visual/Audio requirements defined. Run `/asset-spec system:bot-attack-vfx` sau khi art bible approved để generate per-asset descriptions + prompts.

## UI Requirements

Hệ thống này không có UI riêng. Hai UI touches:
1. **Screen-edge flash** (wave Spawning): owned by HUD system — 8px red vignette overlay, 500ms. Không phải GPU particle.
2. **Elite kill Matter toast**: owned by Resource System / HUD — hiển thị "+X Matter" khi Elite bị giết, giống mọi resource gain khác.

## Acceptance Criteria

- **GIVEN** device hỗ trợ compute shaders và wave → `Spawning`, **WHEN** 40 rivals spawn, **THEN** mỗi rival emit 6 particles (white→rival color), stagger hoàn tất trong 0.5s, frame time trên device mid-range Android ≤ 33ms trong frame spawn đó (đo qua Profiler).
- **GIVEN** Defender trong `Intercept` state, rival trong `ATTACK_RANGE=1.5m`, **WHEN** 6 frames trôi qua, **THEN** 1 attack arc 4 particles (cyan #4FC3F7, 80ms) emit từ Defender về phía rival.
- **GIVEN** rival HP ≤ 0 và `RivalDestroyedEvent` fire, **WHEN** particle system nhận event, **THEN** 8 particles (red→grey, 220ms radial burst) emit tại `rivalPosition`; rival đã bị `Destroy()` trước khi particles kết thúc.
- **GIVEN** Elite HP ≤ 0, **WHEN** destroyed, **THEN** 20 particles (dual-ring, 400ms) emit; `IResourceService.Add(Matter, 80 + waveIndex×5)` được gọi.
- **GIVEN** waveIndex=5, **WHEN** wave composition tính toán, **THEN** bruiserCount=1 (floor(5/4)=1) → Elite spawn thay thế 1 Bruiser slot; wave cuối = 7 Scouts + 7 Soldiers + 0 Bruisers + 1 Elite = tổng 15 bots (waveSize không đổi).
- **GIVEN** waveIndex=8, **WHEN** F1 chạy, **THEN** bruiserCount=2, soldierCount=10, scoutCount=9 (total=21).
- **GIVEN** worst-case peak (20 Defenders attacking + 8 rivals dying + elite death + 10 spawn stagger), **WHEN** GPU particle count measured, **THEN** liveCount ≤ 250 (worst-case formula: 80+64+20+60=224; threshold includes 10% headroom).
- **GIVEN** device không hỗ trợ compute shaders, **WHEN** game starts, **THEN** VFX disabled; log `"Device does not support compute shaders — bot-attack-vfx disabled"`; rivals vẫn move, damage, die bình thường.
- **GIVEN** "Clear Wave" ad tapped khi spawn stagger đang chạy, **WHEN** tất cả rivals bị destroy, **THEN** không có particle nào emit thêm; pending stagger items với `waveId` hiện tại bị cancel (per Rule 12 — `waveId` increments mỗi `Spawning` event).
- **GIVEN** Elite killed tại waveIndex=20, **THEN** Matter reward = 80 + 20×5 = 180.

## Open Questions

1. **ADR cho GPU pipeline** — Compute shader + DrawMeshInstancedIndirect là một architectural decision đáng có ADR riêng (Android Vulkan/GLES 3.1 requirement, fallback strategy, shader compile time). Run `/architecture-decision gpu-particle-pipeline` trước khi impl.

2. **Audio SFX spec** — SFX trigger points đã listed trong Visual/Audio Requirements nhưng actual sound design (pitch, volume, layering) thuộc `audio-system.md`. Cần spec khi audio system được implement.

3. **Fallback visual cho no-compute-shader devices** — no-VFX mode là safe fallback nhưng không có ASMR feel. Có nên implement CPU fallback (simple sprite flash thay cho particle) không? Deferred — profile device coverage trước.
