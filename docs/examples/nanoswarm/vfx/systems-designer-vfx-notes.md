# Systems Designer VFX Notes — Bot Attack VFX & Rival Variety

> **Author**: Systems Designer
> **Date**: 2026-09-20
> **For**: bot-attack-vfx.md — trigger rules, rival stats, elite design, GPU capacity

---

## 1. VFX Trigger Rules

### Event: Attack Arc (Defender → Rival melee hit)

| Field | Value |
|-------|-------|
| Game event | Continuous: Defender is in `Intercept` state AND rival is within `ATTACK_RANGE=1.5m` |
| Rate-limit | Fire every **6 frames** (~10/s at 60fps). One arc per Defender-Rival pair per budget tick. |
| Data passed | `defenderPosition (Vector2)`, `rivalPosition (Vector2)`, `rivalTypeId (byte)` |
| Particle budget | 1 arc strip = 3 particles (origin, mid-bend, tip). Max 20 Defenders × 1 target = 20 arcs × 3 = **60 particles** |
| Notes | Arc fires even if rival dies this frame — check alive flag at particle emit, skip if dead. |

**Conflict found:** Combat system deals damage every FixedUpdate (~50/s). Firing an arc every frame would saturate particle buffer on older Android. 6-frame rate limit (~10 arcs/s per Defender) matches the ASMR "20–30 visual events/s" target across the full colony. Do NOT tie arc emission to the damage tick directly.

---

### Event: Death Dissolve (rival destroyed)

| Field | Value |
|-------|-------|
| Game event | `Destroy(gameObject)` on rival at HP ≤ 0 — fire **before** actual destroy |
| When to fire | Subscribe to `RivalDestroyedEvent` (or add a hook in `IRivalService.DamageRival` before Destroy call) |
| Data passed | `rivalPosition (Vector2)`, `rivalTypeId (byte)`, `isElite (bool)` |
| Particle budget | Standard: **3 particles** per rival. Elite: **8 particles** (larger burst). |
| Duration | 0.6s fade lifetime for standard; 1.0s for elite. |
| Notes | Must not re-use rival's GameObject transform after Destroy — copy position into event struct. |

---

### Event: Spawn Entry (rival wave appears)

| Field | Value |
|-------|-------|
| Game event | Wave state → `Spawning`; fire once per rival bot as it is instantiated |
| Data passed | `spawnPosition (Vector2)`, `rivalTypeId (byte)` |
| Particle budget | 2 particles per rival (entry trail, 0.3s lifetime). Max 40 rivals = **80 particles** at wave start. |
| Rate-limit | Stagger across 0.5s window: emit rival[i] entry at `i × (0.5 / waveSize)` seconds. Prevents 80-particle spike on one frame. |
| Notes | Entry particles are cosmetic only — rival is already moving. Don't wait for particle completion before advancing. |

---

### Event: Elite Death (elite rival destroyed)

| Field | Value |
|-------|-------|
| Game event | Same as Death Dissolve but `isElite = true` |
| Data passed | `rivalPosition (Vector2)`, `rivalTypeId = Bruiser (2)`, `isElite = true`, `aoeRadius (float)` |
| Particle budget | 8 particles (burst ring). If AoE damage enabled: additional 4-particle ring at `aoeRadius`. Total **12 particles** max. |
| Duration | 1.0s; ring expands outward at `aoeRadius / 0.4s` speed |
| Notes | AoE visual ring is purely cosmetic — damage is computed in code. Ring radius must match `ELITE_AOE_RANGE` tuning knob exactly (visual/mechanic sync). |

---

## 2. Rival Type Stat Table

Base stats are multipliers on the existing `RIVAL_HP=20`, `RIVAL_SPEED=1.5m/s`, `RIVAL_CORE_DPS=5`.

| Type | visual_id | HP | Speed (m/s) | ScaleMultiplier | RIVAL_CORE_DPS | Particle Color |
|------|-----------|----|-------------|-----------------|----------------|----------------|
| Scout | 0 | 12 | 2.2 | 0.7 | 3 | `#FF4444` (bright red) |
| Soldier | 1 | 20 | 1.5 | 1.0 | 5 | `#CC2222` (mid red, existing) |
| Bruiser | 2 | 45 | 0.9 | 1.6 | 9 | `#880000` (dark crimson) |

**Tuning rationale:**
- Scout = fast glass cannon; dies to 1–2 Defenders before reaching Core but applies speed pressure early.
- Soldier = baseline (matches existing RIVAL_HP/RIVAL_CORE_DPS constants — no tuning required for wave 0–4).
- Bruiser = slow tank; requires 3 Defenders to kill before Core engagement begins.

**TTK cross-check (3 Defenders, DEFENDER_DPS=8):**
- Scout: 12 / (3×8) = 0.5s — dies fast, works as "spam" unit.
- Soldier: 20 / 24 = 0.83s — baseline.
- Bruiser: 45 / 24 = 1.875s — needs 4+ Defenders or takes Core hits.

---

### Wave Composition Formula

```
waveSize = min(WAVE_BASE_SIZE + waveIndex × WAVE_SCALE_PER_INDEX, MAX_WAVE_SIZE)  // existing

bruiserCount = max(0, floor(waveIndex / 4))           // first Bruiser at wave 4
soldierCount = max(0, floor(waveSize × 0.5))          // 50% base
scoutCount   = waveSize - soldierCount - bruiserCount  // remainder
```

**Wave composition lookup (sample):**

| waveIndex | waveSize | Scouts | Soldiers | Bruisers |
|-----------|----------|--------|----------|----------|
| 0 | 5 | 2 | 3 | 0 |
| 2 | 9 | 4 | 5 | 0 |
| 4 | 13 | 5 | 7 | 1 |
| 8 | 21 | 7 | 11 | 2 |
| 12 | 29 | 8 | 15 | 3 |
| 17 | 39 | 9 | 20 | 5 |
| 18+ | 40 (cap) | 10 | 20 | 5 |

---

## 3. Elite Rival

Spawns on every **5th wave** (waveIndex % 5 == 0, starting from waveIndex=5).

| Stat | Value | Notes |
|------|-------|-------|
| HP | 150 | = Bruiser base × ~3.3; requires 5+ Defenders or 6+ seconds uncontested |
| Speed | 1.1 m/s | Slightly faster than Bruiser; not slow enough to ignore |
| ScaleMultiplier | 2.2 | Visually distinct — clearly larger than Bruiser |
| RIVAL_CORE_DPS | 18 | ~3.6× Soldier; elite reaching Core is a punishing outcome |
| AoE range on death | 3.0 m (optional) | Damages any remaining nearby rivals' HP? **No — see conflict note below** |
| Matter reward on kill | `ELITE_MATTER_REWARD = 80 + waveIndex × 5` | Wave 5: 105. Wave 20: 180. |
| Wave slot | **Replaces 1 Bruiser slot** (not additive). If bruiserCount=0 at that waveIndex, adds as +1 to waveSize. | Keeps total wave size on budget. |

**AoE on death — design conflict:** "AoE damage range on death" targeting other rivals would help the player (kills clustered scouts), but the rival faction is a threat system. Recommend: AoE on death is **a cosmetic ring only** — no damage. If future design wants AoE to damage the player's Core or Defenders that would contradict "no friendly fire" and "no projectiles" rules in combat-system.md. Flag for Bi to confirm: AoE effect is visual-only OR provide explicit carve-out in combat-system.md.

---

## 4. GPU Particle Capacity Estimate

### Simultaneous particle breakdown

| Source | Count | Particles each | Total |
|--------|-------|----------------|-------|
| Attack arcs (20 Defenders × 1 arc) | 20 | 3 | 60 |
| Death dissolve (standard, worst case 10 die/s) | 10 | 3 | 30 |
| Death dissolve (elite, 1/wave) | 1 | 8 | 8 |
| Spawn entry (staggered, worst peak) | ~8 per frame window | 2 | 16 |
| Ambient combat spark (low-priority ambient) | 20 | 1 | 20 |
| **Total peak** | | | **134** |

### Recommendation

**512 ParticleCapacity is sufficient** for the designed event set (peak ~134 with safety headroom of 3.8×).

**1024 is safer** and is the correct production choice for the following reasons:
1. Android devices with slower GPU schedulers can see frame-delayed particle emissions pile up.
2. Wave spawn stagger (40 rivals × 2 = 80 particles) fires over 0.5s — if device hitches, these could arrive in 2–3 frames simultaneously.
3. Future ambient spark polish (orbit glows, node harvest particles) will share the same budget.
4. Cost difference: 1024 vs 512 floats in ComputeBuffer = 2KB extra VRAM — negligible on any Android device that runs Unity 6.5.

**Verdict: ship with 1024, expose as `GPU_PARTICLE_CAPACITY` tuning knob in ColonyBalance.cs.**

---

## 5. Design Conflicts / Open Questions for Bi

1. **Attack arc rate-limit:** 6-frame interval chosen to hit 10 arcs/s per Defender. If ASMR feel needs denser visual feedback, drop to 3-frame (20/s) and keep an eye on 512→1024 overflow. Confirm target density.

2. **Elite AoE on death:** As designed, AoE ring is cosmetic only (no damage). Combat-system.md Rule 6 states "no friendly fire" but doesn't define Defender-side splash. If you want the elite death to damage surrounding rival bots (helping the player), that's a valid change — but needs a line added to combat-system.md permitting it.

3. **Bruiser slot replacement for Elite:** Elite replaces 1 Bruiser. At waveIndex < 4, bruiserCount=0 — so elite adds +1 to waveSize instead. This means wave 5 is `waveSize=15 + 1 elite = 16 effective`. Is that acceptable escalation, or should elite always strictly replace (skip spawn if no Bruiser slot)?

4. **`RivalDestroyedEvent` lifecycle:** Bot-attack-vfx.md needs `IRivalService` to fire an event before `Destroy(gameObject)` so position can be sampled. Current combat-system.md just says `Destroy(gameObject)` at HP≤0. Need to confirm: does `IRivalService.DamageRival()` already fire a pre-destroy hook, or does this need to be added?
