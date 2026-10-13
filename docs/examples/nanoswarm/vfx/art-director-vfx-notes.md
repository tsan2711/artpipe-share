# Art Director VFX Notes — Bot Attack VFX

> **Author**: Art Director (Claude)
> **Date**: 2026-09-20
> **For system**: bot-attack-vfx.md
> **Creative direction**: "Living Architecture" — colony as single organism; signals not spectacles

---

## Design Principles

All visual events follow three rules:

1. **Signal, not show.** Attack effects communicate state change, not power. Duration is short enough to never distract from the colony flow.
2. **Color is faction identity.** Blue (#4FC3F7 family) = colony. Red (#EF5350 family) = rival. Never mix. White/neutral = neutral system events (spawning from void, dissolve into void).
3. **GPU budget discipline.** Total particle count across all simultaneous events must stay under 2,000 live particles on a mid-range Android (Snapdragon 778G). Individual event budgets are set accordingly.

---

## VFX Event Specs

### 1. Defender Attack Arc

**Trigger**: Defender is within `ATTACK_RANGE` (1.5 m) of a Rival; fires continuously per damage tick.

| Property | Value |
|----------|-------|
| Color | `#4FC3F7` (cyan-blue, HSV 199°/67%/97%) → fades to transparent |
| Shape | Short directed arc — 3–5 line-segment particles swept from Defender center toward Rival position; arc subtends ~30° |
| Duration | 80 ms per arc (one-shot, re-fires each damage tick) |
| Particle count | 4 particles per arc event |
| Loop | No — one-shot per tick; frequency driven by `DEFENDER_DPS` tick rate |
| Scale | Arc length = `ATTACK_RANGE` × 0.6 (0.9 m). Line width = 0.04 m world-space |
| Alpha curve | Linear: 1.0 → 0 over 80 ms |
| Emissive | Mild bloom: intensity 1.4 in URP bloom pass |

**Intent**: Looks like a nerve impulse or electrical synapse — quick, precise, biological. Not a laser, not a slash. A signal.

---

### 2. Rival Death Dissolve (Standard — Scout / Soldier)

**Trigger**: Any non-Elite rival bot reaches HP ≤ 0.

| Property | Value |
|----------|-------|
| Color | Starts `#EF5350` (warm red, HSV 1°/66%/94%) → shifts to `#BDBDBD` (neutral grey) → transparent |
| Shape | Radial burst of 8 point particles (uniform angular spread), each moving outward then curving inward (spring-back) |
| Duration | 220 ms total (burst outward: 0–100 ms, spring back + fade: 100–220 ms) |
| Particle count | 8 particles |
| Loop | No — one-shot |
| Scale | Burst radius peak: 0.3 m. Particles start at bot center, settle at 0.1 m radius |
| Alpha curve | Hold 1.0 until 120 ms, then linear fade to 0 |
| Emissive | None — intentionally flat; dissolution should feel like signal loss, not explosion |

**Intent**: The red dot stops being a threat and quietly collapses inward — like a cell membrane rupturing and reabsorbing. No flash, no impact. Just absence.

---

### 3. Rival Spawn Entry

**Trigger**: Wave state transitions `Spawning`; rival bots materialise at map edge.

| Property | Value |
|----------|-------|
| Color | `#FFFFFF` (pure white, 100% value) → shifts to rival bot color (`#EF5350` / `#FF7043` / `#D32F2F` depending on type) |
| Shape | Inward convergence — 6 point particles spiral inward toward bot spawn position from 0.5 m radius |
| Duration | 300 ms (convergence over 300 ms, bot sprite fades in during final 100 ms) |
| Particle count | 6 particles per spawning bot |
| Loop | No — one-shot per bot; all bots in wave fire simultaneously |
| Scale | Convergence radius: 0.5 m. Particles disappear when they reach center (< 0.02 m from target) |
| Alpha curve | 0 → 1.0 over first 50 ms, hold, then fade out as particles converge |
| Emissive | Mild: intensity 1.2 only during first 100 ms (materialising phase) |
| Screen-edge flash | Separate HUD-layer effect (not GPU particle): thin 8 px red edge vignette on screen border, 500 ms fade. This is a 2D UI overlay, not part of the particle budget |

**Intent**: Rivals don't teleport in — they coalesce from environmental noise. The player perceives arrival as organic, not spawned. The screen-edge flash is the alert signal; the convergence spiral is the flavour.

---

### 4. Elite Rival Death Dissolve (Every 5th Wave — 1 Large Rival)

**Trigger**: The Elite rival (1 per every 5th wave, larger scale, higher HP) reaches HP ≤ 0.

| Property | Value |
|----------|-------|
| Color | Phase 1 (0–150 ms): `#EF5350` → `#FF8A65` (warm coral). Phase 2 (150–400 ms): `#FF8A65` → `#CFD8DC` (cool light grey) → transparent |
| Shape | Two-ring burst: inner ring = 8 particles at 0.2 m radius, outer ring = 12 particles at 0.6 m radius. Both radii expand then contract |
| Duration | 400 ms |
| Particle count | 20 particles (inner 8 + outer 12) |
| Loop | No — one-shot |
| Scale | Inner ring peak radius 0.35 m; outer ring peak radius 0.8 m. Particle size = 0.06 m |
| Alpha curve | Inner ring: hold 1.0 → fade 200–400 ms. Outer ring: peak at 150 ms → fade 150–400 ms (slightly delayed) |
| Emissive | Intensity 1.6 during Phase 1; drops to 1.0 during Phase 2 — creates a brief "heat pulse" feel |
| Camera | No camera shake — ASMR tone forbids it |

**Intent**: Bigger than standard, but still not an explosion. The two-ring structure makes the eye register "this was different" without disrupting colony calm. The warm-to-cool color shift signals the threat decomposing into inert matter.

---

## Rival Bot Visual Variants

These are sprite/scale specs, not particle specs. Defined here for consistency with the VFX color specs above.

### Scout

| Property | Value |
|----------|-------|
| Shape | Hexagon, pointed top orientation |
| Scale | 0.6× standard bot size |
| Base color | `#FF7043` (orange-red, HSV 14°/73%/100%) |
| Outline | 1 px, `#BF360C` (dark orange-brown) |
| Movement | `RIVAL_SPEED × 1.4` — fastest rival |
| Death dissolve color | Uses standard dissolve spec; burst radius 0.2 m (smaller than Soldier) |

### Soldier (Standard)

| Property | Value |
|----------|-------|
| Shape | Hexagon, flat-top orientation |
| Scale | 1.0× standard bot size |
| Base color | `#EF5350` (standard red, HSV 1°/66%/94%) |
| Outline | 1 px, `#B71C1C` (dark red) |
| Movement | `RIVAL_SPEED × 1.0` |
| Death dissolve color | Uses standard dissolve spec; burst radius 0.3 m |

### Bruiser

| Property | Value |
|----------|-------|
| Shape | Hexagon, flat-top orientation, slightly rounder corners (sprite variant) |
| Scale | 1.8× standard bot size |
| Base color | `#D32F2F` (deep red, HSV 0°/78%/82%) |
| Outline | 2 px, `#7F0000` (near-black red) |
| Movement | `RIVAL_SPEED × 0.65` — slowest rival |
| Death dissolve color | Standard dissolve spec; burst radius 0.45 m (larger) |

---

## GPU Particle Budget Summary

Worst-case scenario: 5 simultaneous Defender attack arcs + 8 Soldier death dissolves + 1 Elite death + wave spawn entry (10 bots):

| Event | Count | Particles each | Total |
|-------|-------|---------------|-------|
| Defender attack arcs (×5) | 5 | 4 | 20 |
| Standard death dissolves (×8) | 8 | 8 | 64 |
| Elite death dissolve (×1) | 1 | 20 | 20 |
| Spawn entry (×10 bots) | 10 | 6 | 60 |
| **Total** | | | **164** |

Well within 2,000 particle budget. Headroom is intentional — colony ambient particles (harvest sparks, energy pulses) will also draw from this budget.

---

## Color Reference Card

| Identity | Hex | HSV | Usage |
|----------|-----|-----|-------|
| Colony blue | `#4FC3F7` | 199°/67%/97% | Defender arc, colony particles |
| Rival red (Scout) | `#FF7043` | 14°/73%/100% | Scout sprite |
| Rival red (Soldier) | `#EF5350` | 1°/66%/94% | Soldier sprite, death dissolve start |
| Rival red (Bruiser) | `#D32F2F` | 0°/78%/82% | Bruiser sprite |
| Rival red (Elite pulse) | `#FF8A65` | 14°/47%/100% | Elite death Phase 1 |
| Dissolve neutral | `#BDBDBD` | 0°/0%/74% | Standard death mid-transition |
| Dissolve cool | `#CFD8DC` | 200°/11%/86% | Elite death final phase |
| Spawn white | `#FFFFFF` | 0°/0%/100% | Spawn convergence origin |
