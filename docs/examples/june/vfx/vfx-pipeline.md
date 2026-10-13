# VFX Pipeline

> **Status**: **Approved** (2026-08-30 — flipped from Draft v2 after confirming the 2026-08-21 revision pass left no outstanding design decision; Discrete path ready as-is, Mass tier specified pending VF-OQ-1/VF-OQ-2 package-install fork with #15)
> **Author**: Bi + Claude (`design-system`)
> **Created**: 2026-08-20
> **Last Updated**: 2026-08-20
> **System**: #6 — Foundation | MVP *(promoted 2026-08-07, SL-3)* | Root scope (pool) + ECS bridge
> **Implements Pillar**: Pillar 2 (spectacle scales with the build, not with new art), Pillar 4 (scope guard — one VFX vocabulary, reused)
> **Governing ADRs**: [ADR-0008](../../docs/architecture/ADR-0008-pooling-shared-mechanism-verified-ownership.md) (pooling), [ADR-0011](../../docs/architecture/ADR-0011-asset-pipeline-addressables-and-validated-import.md) (asset import/validation)

> 🔴 **Bi's ruling, 2026-08-20 — HYBRID.** Discrete one-shot effects keep the built-in **ParticleSystem**
> (shipped, pooled, play-tested — `cc877cd`). Mass GPU effects get **VFX Graph**, which requires installing
> `com.unity.visualeffectgraph`, **currently not in the project** (`manifest.json` carries only
> `com.unity.modules.particlesystem`). The seam that makes this a configuration change rather than a rewrite
> already exists in code: `IPooledEffect`, whose own doc comment names the upgrade path —
> *"install `com.unity.visualeffectgraph` and add a `VfxGraphEffect : MonoBehaviour, IPooledEffect` … the
> catalog swaps the prefab and nothing else changes."*

## Overview

The **VFX Pipeline** is the infrastructure every visual effect in SKYBORNE is produced through: which
technology an effect uses, how it is pooled, how a parallel Burst job asks for one, what it may cost, and
what makes it legal against the art direction. It owns no effect — Spell VFX #30, Combat Feedback #29 and
Boss #19's hazard surfaces each author their own — it owns the **rules and the plumbing** they all share.

Its shape is set by one hard constraint: **the systems that know an effect should play cannot play it**.
Projectile impacts are decided inside a parallel `[BurstCompile]` job, which cannot touch a managed
`GameObject`, a `ParticleSystem` or a `VisualEffect`. So the pipeline is a producer/consumer split — jobs
append value snapshots (`ImpactVfxElement`: position, normal, one byte of id) to a registry buffer, one
main-thread bridge drains it each frame and drives a pooled effect host through `IVfxPoolService`. That path
is shipped and play-tested. This document specifies it, and adds the half that does not exist: **the mass
tier**.

**Two tiers, one seam.**

| Tier | Tech | What it is for | State |
|---|---|---|---|
| **Discrete** | Built-in `ParticleSystem` behind `IPooledEffect` | Countable one-shots the game asks for by id: impacts, pickups, muzzle flashes, hit flashes, death puffs | ✅ shipped |
| **Mass** | **VFX Graph** (GPU) | Effects whose *count* is the point: thousands of enemy projectile bodies, swarm trails, large-scale ambient | ⬜ package not installed |

The reason both exist is that they fail in opposite directions. A ParticleSystem per enemy projectile at
swarm density is thousands of managed components ticking on the CPU — the *"CPU 1023-batch loop"* class of
solution this project has already rejected once. A VFX Graph for a single impact is a GPU dispatch and a
graphics buffer round-trip to place one puff, with worse latency and no clean way to say *"this exact effect,
right now, exactly here"*.

## Player Fantasy

**"Càng đánh giỏi, màn hình càng đẹp — và tôi vẫn đọc được nó."**

The approved power fantasy is explicit: *"ride the edge of overheat = max spectacle."* Spectacle is the
reward for playing well, which makes it a **gameplay** system wearing an art costume, and it produces the
central tension this pipeline exists to resolve:

**Spectacle must scale up without eating legibility.** At maximum heat with three spells chained, the frame
is full of the player's own light — and that is exactly the moment a boss telegraph, an enemy projectile or
a hazard boundary must still be readable. Boss #19's Rule V-2 answers this for hazards by inverting the
figure-ground relationship (hazards render the *unsafe* volume, so the safe band is the hole — the only
channel that gets **more** legible as the frame brightens), and Rule V-4 backs it with a stencil pass that
multiplies player additive VFX by 0.45 inside hazard surfaces. **This pipeline is what makes those rules
implementable**, and it inherits them rather than restating them.

**Two felt properties this system owns:**

1. **"It never hitches."** Fifty enemies dying at once must not be fifty instantiations. Pooling is not an
   optimisation here, it is the difference between a spectacle system and a stutter system.
2. **"Effects belong to someone."** #19's Rule V-3 makes this falsifiable: *no player-authored VFX may
   exhibit coherent rigid-body motion for longer than 1.0 second; boss hazard surfaces always do.* The
   player's light is emissive, radial, short-lived; the world's threats move rigidly. A player who cannot
   name the difference can still read it peripherally — and only if the pipeline enforces the rule at
   authoring time rather than hoping.

### What this fantasy forbids

- **No per-effect bespoke tech.** An effect is Discrete or Mass; a third answer is a scope failure (Pillar 4).
- **No `RenderMeshInstanced`-style CPU batch loops for mass visuals** — rejected on this project already.
  Mass means GPU: VFX Graph, or `DrawMeshInstancedIndirect` + `ComputeBuffer`.
- **No effect that allocates at play time.** Pool or no effect (ADR-0008).
- **No screen-space scale as a telegraph channel** (#19 V-1) — it collides with the heat-spectacle fantasy
  at exactly the moment both are maximal.
- **No full-screen flashes** (art-bible §7D photosensitivity).

**PT-GATE-VFX-1 (falsifier).** At max heat with three spells chained, against ≥8 enemies, a naive tester can
still point at the boss telegraph and the enemy projectiles. If spectacle wins, the pipeline has failed
regardless of frame rate.

## Detailed Rules

### R-1 — The tier decision rule. One predicate, applied at authoring time.

> **Mass tier ⇔ the effect's instance count is driven by simulation and can exceed ~100 concurrent.**
> Everything else is Discrete.

| Effect | Tier | Why |
|---|---|---|
| Projectile impact (player + enemy) | Discrete | One per impact, requested by id, needs exact placement |
| Muzzle flash, pickup sparkle, chest open | Discrete | Countable, event-driven |
| Player death / enemy death puff | Discrete | ≤ 50 concurrent worst case |
| **Enemy projectile bodies at swarm density** | **Mass** | #15's budget is thousands in flight; the count *is* the effect |
| Ambient world motes, cloud-deck dust | Mass | Persistent, high count, no per-instance identity |
| Boss hazard boundary surfaces | **Neither — mesh, not particles** | #19 V-2 specifies boundary *shells* (≈2 quads / N×2 quads / a 24-side tube). Rendering them as particles is a category error and blows the overdraw budget |

**The rule is deliberately about count, not about importance.** A boss telegraph is the most important
effect in the game and is Discrete (or mesh); an ambient mote is unimportant and is Mass.

### R-2 — Everything Discrete goes through the pool. No exceptions, no `Instantiate` at play time.

The shipped chain, unchanged by this document:

```
Burst job → ImpactVfxElement (value snapshot) → VfxRequestBridge (main thread, ITickable)
          → IVfxPoolService.Play(id, position, normal) → IPoolService rent
          → IPooledEffect.Play() → auto-return after catalog lifetime (UniTask)
```

- **The pool stays dumb** — it rents and returns host `GameObject`s and knows nothing about effects
  (ADR-0008's mechanism/policy split). Playback is polymorphic through `IPooledEffect`, one method.
- **`IVfxPoolService` is Root-scoped**; `PoolService`'s constructor calls `DontDestroyOnLoad`. ⚠️ Whether
  that is *correct* is B-1's open item, not this document's — but a handle held across a WorldSession
  boundary must be invalidated by ADR-0008's generation stamp.
- **An unknown or zero effect id is a safe no-op.** `ImpactVfxId = 0` means "no VFX", and an empty catalog
  makes `Play` do nothing — so simulation, damage and environment collision all run **headless with no art
  at all**. This is what lets combat be tested before any effect exists, and it must survive.

### R-3 — `IPooledEffect` is the technology seam, and it is the whole hybrid.

```csharp
public interface IPooledEffect { void Play(); }
```

`ParticleSystemEffect` implements it today. `VfxGraphEffect` will implement it for the mass tier. **Adding
VFX Graph changes a prefab reference in `PoolCatalog` and nothing else** — not the bridge, not the ECS side,
not `IVfxPoolService`, not any calling system.

> This is the single most valuable property in the pipeline and it exists because the seam was designed
> before the technology was chosen. **Do not widen `IPooledEffect`** — every method added to it is a
> capability the pool must then understand, which is how a dumb pool becomes a VFX engine.

### R-4 — Mass-tier effects are driven by a buffer, not by requests.

Discrete effects are **pull**: something happened, play one. Mass effects are **push**: here is the current
state of N things, render them.

```
ECS (Burst)  → NativeArray<InstanceData> (position, velocity, id, age)
             → GraphicsBuffer  (kind-A bridge, #26)
             → VFX Graph reads it per frame
```

Consequences that are design decisions, not implementation detail:

- **No per-instance managed object exists.** There is no `GameObject` per enemy projectile body; the ECS
  entity is the simulation and the GPU buffer is the visual. A mass effect therefore **cannot** carry a
  script, cannot be clicked, cannot collide — all of which are simulation's job anyway.
- **The buffer is written once per frame from the main thread, reading the *previous* frame's completed
  simulation output — never a synchronous `.Complete()` on the current frame's jobs.** ⚠️ **Ruled
  (design-review 2026-08-21, finding 8, resolved against project precedent — ADR-0005 Swarm Perf):** an
  earlier draft's "after the simulation's jobs complete" was ambiguous between (a) the main thread calling
  `.Complete()` synchronously mid-frame and copying, or (b) consuming the prior frame's already-finished
  buffer. (a) forces a job-graph completion stall on the main thread at exactly the frame this document
  calls its worst case (a swarm wipe / max-heat spike, #15's 5,000–10,000-entity simulation) — this project
  has already been bitten by main-thread stalls of this shape once (ADR-0005) and the fix there was the same
  shape as here. **This document adopts (b): one frame of intentional visual latency, no synchronous wait.**
  Consequence: the very first frame after a region loads (no previous buffer yet) must render zero instances
  from this buffer, not garbage — a new edge case (VF-EC-16) names this.
- **Spawn/despawn is expressed as buffer contents, not as events.** A projectile that stops existing simply
  stops being in the buffer next frame. Its *impact* is a Discrete effect, requested by id, as usual.

### R-5 — Effect ids are one namespace, shared with every pooled domain.

`PoolCatalog` ids are `byte`, `1..255`, `0` reserved for "none", and they are **shared across all domains
that use the pool** — VFX today, audio voices and damage numbers later. A collision between a VFX id and an
audio id is a real authoring hazard, and `OnValidate` already reports duplicates, id 0 and `Cap < Prewarm`
while the asset is being edited.

> **255 ids is a real ceiling** and this document accepts it for v1.0: the MVP's whole effect vocabulary is
> in the low tens (Pillar 4's scope guard is the actual limit, not the byte). If the ceiling is ever
> approached, the fix is **splitting the namespace per domain**, not widening the field — widening it
> touches `ProjectileData`, the element, the bridge and every catalog.

⚠️ **Correction (design-review 2026-08-21, finding 6): no invariant bounded the SUM of `Cap` across every
entry in a catalog** — D-1 only bounds per-id `Cap`, and nothing checked the total. 255 ids × a generous
per-id `Cap` is a silent multi-thousand-instance worst case (boot-time instantiation cost and memory, a
different failure mode from R-6's per-request drop). **`PoolCatalog.OnValidate` must additionally warn when
`Σ Prewarm` across all entries exceeds `CatalogPrewarmBudget` (default 500, a sanity ceiling, not a hard
game-design limit — `[A]`, revisit once MVP's real vocabulary is authored).** This is deliberately a
warning, not a hard refusal (an author may have a legitimate reason to exceed it), matching the pattern
`OnValidate` already uses for duplicate ids.

### R-6 — Pool sizing is measured, never guessed.

`Prewarm` = observed `PoolStats.PeakRented` from a real session. `Cap` = a hard ceiling; renting past it is
**refused** — the request is dropped with no allocation and no crash, and warns once in Dev builds.

**Dropping is correct and is a design position.** The alternative — growing the pool under load — turns the
worst frame in the game (a swarm wipe at max heat) into the frame that allocates. A missing puff among two
hundred is invisible; a 40 ms hitch is not.

⚠️ **Correction (design-review 2026-08-21, finding 1): dropping needs a stated order, not just a stated
policy.** An earlier draft said only *that* excess requests drop, never *which* ones. The code answers this
today by accident: whichever requests `VfxRequestBridge.Tick()` reads first out of the ECS buffer, which is
job-chunk scheduling order — not gameplay significance. That is exactly wrong for the moment this rule calls
"the worst frame in the game": a swarm wipe at max heat is, by this game's own design, the player's
best-played moment (heat-gated spectacle), and an arbitrary drop can just as easily cut the killing blow the
player is looking at as an off-screen trash puff. **Rule: before requests are handed to the pool each frame,
`VfxRequestBridge` sorts the frame's batch by distance-to-camera (nearest first) and rents in that order** —
so when `Cap` is hit, the drops are always the farthest-from-view requests, never a job-scheduling accident.
This is a single sort over at most a few hundred elements per frame (the batch already fits in a
`DynamicBuffer`), not a new allocation or a per-request cost — cheap relative to the frame budget this
document already spends on pool operations.

**Also corrected: D-1's worst-case sizing now has a real number for the enemy side**, not an unquantified
term (design-review 2026-08-21, finding 2). See D-1.

### R-7 — Art law the pipeline enforces, not merely documents.

Inherited, with the enforcement point named:

| Rule | Source | Enforced at |
|---|---|---|
| Closed palette; no new hue for any effect | `art-direction.md` §3 | Asset validation (**P-1**, ADR-0011) |
| Player VFX may not show coherent rigid motion > **1.0s** | #19 V-3 | QA fails the build; orbit spells are the risk (orbiting orbs must be *player-anchored rotation*) |
| Trail lifetimes capped **0.08 / 0.18 / 0.35s** by tier | #19 V-3 | Effect authoring + validator |
| Player additive VFX × **0.45** inside hazard stencil | #19 V-4 | One URP Renderer Feature, before the transparent pass |
| Grade executes **before** the VFX pass so signals are never desaturated | #19 V-4/V-7 | Same feature |
| No full-screen flash | art-bible §7D | Validator + review |
| Additive-vs-alpha: hazard boundaries are **alpha**, player VFX additive | #19 V-2 | Authoring; additive on a bright sky washes to white |

> ⚠️ **`gradients_allowed: false` from `art-direction.md` §4 does NOT apply to world VFX** — additive
> particles are gradients by construction, and applying that clause literally would forbid every effect in
> the game. #19's amendment (9) already records this; it is repeated here because this is the document an
> effect author reads.

### R-8 — The renderer feature is one pass, budgeted, and measured in a build.

One URP Renderer Feature doing two jobs (#19 V-4): the hazard stencil suppression and the phase-desaturation
grade, both **before** the transparent VFX pass. Budget: **≤ 0.3 ms** at 1080p — 1.8% of a 16.6 ms frame.

**Measured in a Development IL2CPP build only.** Editor numbers on this project have been misleading before
(Burst runtime compilation, Mono JIT, subscene live baking and editor overhead all pollute the profile).

### R-9 — Installing VFX Graph is a gated change, not a package add.

`com.unity.visualeffectgraph` is not installed. Before it is:

1. **Verify it resolves on Unity 6.5 + URP 17.5** — this project has one package-version scar already
   (Havok was not installable on 6.5; 17 `CS0122` errors, reverted) and one MCP-plugin scar. Treat a package
   add as a spike with a rollback, never as a chore.
2. **Check IL2CPP + `link.xml`.** The project has been bitten once (Zenith attributes stripped).
3. **Measure build size and boot time before/after.** VFX Graph pulls shader variants.
4. **Add nothing to the Discrete path.** If the install cannot be justified by a Mass-tier effect that
   actually exists, it should not happen yet — which means **#6's install is scheduled with #15**, not
   before.

## Formulas

> **[R]** registry · **[G:doc]** another Approved GDD · **[A]** assumption introduced here.

### D-1 — Discrete-tier concurrency and pool size

```
peak_concurrent(id) = request_rate(id) × Lifetime(id)
Prewarm(id)         = measured PoolStats.PeakRented        (never estimated)
Cap(id)             ≥ 1.5 × Prewarm
```

| Variable | Value | Description |
|---|---|---|
| `Lifetime(id)` | ≥ **0.05 s**, typical **0.4–1.0 s** | Catalog auto-return: burst duration + tail |
| `request_rate` | per-effect | Impacts/s, deaths/s |
| Worst-case impact rate | **~60/s player + up to ~298/s enemy** | Player side heat-gated (**[G:heat-overheat]**); enemy side is #15's own corrected worst case — **127–298 shots/second** (`enemy-projectile-system.md`, `MaxActiveCasters` fairness cap, design-review 2026-08-21), not the ~60/s this document originally assumed |
| `Cap` headroom | **1.5×** **[A]** | Absorbs a burst without allocating |

**Output**: a per-id integer. **Example** — impact VFX at 20 impacts/s with `Lifetime = 0.5 s` → peak ≈ 10 →
`Prewarm 12`, `Cap 20`. A swarm wipe spikes to 60 concurrent → the pool refuses the excess, drops ~40 puffs
among 60, and does not allocate. Correct trade (R-6).

⚠️ **Correction (design-review 2026-08-21, finding 2).** The original worked example sized the enemy side
against an unquantified "#15's enemy rate," while #15 is named elsewhere in this document as *the reason
the Mass tier exists* — an internal contradiction (a system cited as the hard case with no number attached
to it). #15's own design-review (2026-08-21) corrected its shots/second worst case to **127–298/s**
(`MaxActiveCasters` not yet numerically set, gated on the same review's structural fix). Every enemy
projectile shot resolves to exactly one Discrete impact request (player hit, terrain hit, or expiry) — so
this is the real worst-case `request_rate` for enemy-projectile-impact ids, not ~60/s. **The impact-VFX
`Cap` for enemy-projectile-impact ids must be sized against 298/s** (the upper corrected bound, before
`MaxActiveCasters` narrows it further) **until #15 ships a measured number**, not against this document's
original placeholder. This is a sizing-input correction, not a new mechanism — R-6's drop policy and its new
distance-sort ordering (above) already handle whatever the real number turns out to be.

### D-2 — Mass-tier GPU particle budget

```
particles_live   = Σ_effects ( spawn_rate × lifetime )   ≤ ParticleCeiling
gpu_cost         ∝ particles_live × overdraw_per_particle
buffer_write_cost = instance_count × bytes_per_instance          (CPU-side, main thread, per frame)
```

| Variable | Value | Description |
|---|---|---|
| `ParticleCeiling` | **500 K – 1 M** | Technical-preferences budget **[R]** |
| Target hardware | **GTX 1060 / RX 580**, 1080p | **[R]** |
| Frame budget | **16.6 ms** | 60 fps **[R]** |
| Draw calls | **< 300** total | **[R]** — a mass effect is *one* draw call, which is the point |
| `bytes_per_instance` | struct-dependent (position/velocity/id/age) | `NativeArray<InstanceData>` → `GraphicsBuffer.SetData` |
| `instance_count` (worst case) | **thousands** (#15's 5,000–10,000-entity budget) | Same source as the enemy rate in D-1 |

⚠️ **Correction (design-review 2026-08-21, finding 7): the formula above models GPU rasterization cost only
— it had no term for the CPU side of the same per-frame write.** `buffer_write_cost` is new: the main-thread
cost of copying `instance_count` entries into the `GraphicsBuffer` every frame (R-4). Because R-4 (above)
now mandates reading the *previous* frame's completed buffer rather than forcing `.Complete()`, this cost is
a plain memcpy-scale operation with no job-graph wait folded in — but it is still a real per-frame main-thread
line item at thousands of instances and must be measured (VF-AC-11) alongside `gpu_cost`, not assumed free.
This is why R-4's synchronous-vs-lagged question had to be resolved before this budget could be written
correctly: the two readings have an order-of-magnitude-different cost here.

**Output**: a ceiling, and the design reading is the **draw-call line**. The reason mass effects go on the
GPU is not particle count for its own sake — it is that 5 000 projectile bodies must be **one** draw call.
Any CPU-side approach lands at thousands and blows a budget of 300 before anything else renders.

### D-3 — Transparent overdraw ceiling

```
overdraw_ratio = Σ (transparent fragments shaded) / screen_pixels ≤ 1.5×   (hazard surfaces, any camera angle)
```

**[G:boss-system V-7]**, hard budget, measured in a Development IL2CPP build. This is the number that bites
on a 1060, and it is why #19 V-2 specifies boundary **shells** rather than volume fills: a filled hazard
occludes the boss, occludes the arena, and costs fill-rate the target GPU does not have. *The readability
argument and the fill-rate argument reached the same geometry, which is the sign the decision is right.*

### D-4 — The tier predicate, as a checkable inequality

```
Mass ⇔ ( max_concurrent_instances > 100 ) ∧ ( per_instance_identity_needed = false )
```

| Variable | Description |
|---|---|
| `max_concurrent_instances` | From the owning system's own budget, not from an art estimate |
| `per_instance_identity_needed` | True if anything must address one instance after it starts (stop it, move it, query it) |

**Output**: a tier. **Both** clauses must hold for Mass. An effect with 5 000 instances that must each be
individually stoppable is not Mass — it is a design that needs revisiting, because the GPU path has no
handles by construction (R-4).

## Edge Cases

- **VF-EC-1 — Effect id 0 or an id absent from the catalog.** `Play` is a no-op. Simulation is unaffected.
  This is the property that lets combat ship before art does.
- **VF-EC-2 — Empty or unassigned catalog.** The pool serves nothing; every `Play` is a no-op. Valid state,
  not an error.
- **VF-EC-3 — Duplicate ids in the catalog.** First wins, error logged; `OnValidate` reports it while
  editing so it is caught before play.
- **VF-EC-4 — A VFX id collides with an audio id** (shared namespace, R-5). Same detection. The real fix if
  it ever bites is namespace splitting, never a wider field.
- **VF-EC-5 — Pool exhausted mid-burst.** Rent refused, request dropped, one Dev-build warning. No
  allocation, no crash (R-6).
- **VF-EC-6 — A rented host is returned twice** (double-return / ABA). Prevented by ADR-0008's
  generation-stamped `PooledHandle` — one of the four real defects that framework's tests found.
- **VF-EC-7 — A handle is held across a WorldSession teardown.** The generation stamp invalidates it; the
  stale return is refused rather than corrupting the free list. ⚠️ **Unproven until B-1's leak tests run** —
  this is one of the four cases B-1 asserts.
- **VF-EC-8 — An impact fires at the position of an entity that died the same frame.** Harmless by
  construction: `ImpactVfxElement` is a **value snapshot** carrying position and normal, never an `Entity`
  (#26 R-3).
- **VF-EC-9 — A prefab in the catalog has no `IPooledEffect` component.** It is rented, positioned and never
  plays. Silent, and the worst kind of silent — **the asset validator (P-1) must fail this**, not runtime.
- **VF-EC-10 — A `ParticleSystem` host is reused before its previous burst finished.** `Play()` calls
  `Clear(true)` then `Play(true)` so a reused host starts clean. Without the clear, a recycled host shows
  the tail of its previous life.
- **VF-EC-11 — `Lifetime` in the catalog is shorter than the effect's own duration.** The host is returned
  mid-burst and the effect visually snaps off. Authoring error; the catalog's minimum (`0.05 s`) does not
  catch it. Validator candidate.
- **VF-EC-12 — Mass-tier buffer written while the previous frame's dispatch is in flight.** Double-buffer or
  fence; a partially-written buffer renders garbage for a frame. This is the first real hazard of the Mass
  tier and does not exist in the Discrete one.
- **VF-EC-13 — VFX Graph package installed but the GPU does not support compute.** Below the project's
  target hardware; no fallback is designed and none should be — the minimum spec is a 1060/580.
- **VF-EC-14 — Play-stop with effects live.** Hosts are `DontDestroyOnLoad` under Root; the bridge is
  scope-owned and disposes. No effect outlives the process.
- **VF-EC-15 — An author gives a player spell a rigid element lasting > 1.0s** (an orbiting orb implemented
  as world-anchored motion). Violates #19 V-3 and degrades every boss hazard read in the same frame. **QA
  fails the build**; the correct implementation is rotation *about the player*, player-anchored.
- **VF-EC-16 — The very first frame a Mass-tier buffer has a reader, no previous frame's data exists yet**
  (design-review 2026-08-21, finding 8's consequence). Per R-4's one-frame-lag rule, this frame renders
  **zero instances** from the buffer, never garbage — the buffer must be explicitly cleared/zero-initialized
  before first read, not left at whatever `GraphicsBuffer.SetData` last wrote from a previous region/session.

## Dependencies

| System | Direction | Hard/Soft | Interface |
|---|---|---|---|
| **Pooling (ADR-0008)** | upstream | Hard | `IPoolService`, `PoolCatalog`, generation-stamped `PooledHandle` |
| **ECS Bridge #26** | upstream | Hard | `ImpactVfxElement` drain is the canonical kind-A bridge; the Mass tier's `GraphicsBuffer` write is a new kind-A case |
| **Spell Projectile #14** | upstream | Hard | Produces `ImpactVfxElement`; its contract with this system is one byte (`ImpactVfxId`) plus a prefab |
| **Enemy Projectile #15** | upstream | Hard | **The reason the Mass tier exists.** #15's density is what forces VFX Graph; the install is scheduled with it (R-9) |
| **Boss System #19** | peer | Hard | Inherits V-1…V-12. Hazard surfaces are **meshes**, not particles (R-1); V-4's renderer feature is R-8; V-3 is enforced here |
| **Spell VFX Integration #30** | downstream | Hard | Authors per-spell effects against this pipeline; *"spectacle scales with combo/heat"* is its rule, this document's budgets are its ceiling |
| **Combat Feedback #29** | downstream | Soft | Hit flashes, screen effects — Discrete tier |
| **Asset Pipeline #41 / ADR-0011** | upstream | Hard | **P-1 validator** is where R-7 stops being a document and starts being a gate |
| **Audio #8 / ADR-0009** | peer | Soft | Shares the pool and the id namespace (R-5); the voice budget is the audio analogue of D-1 |
| **Scope lifecycle B-1** | peer | Hard | VF-EC-7: pool ownership (Root vs WorldSession) and handle invalidation across a session boundary |

### Interface contracts this GDD owns

1. **The two tiers and D-4's predicate** — every effect in the game is classified by it.
2. **`IPooledEffect`** as the technology seam, and the rule that it stays one method (R-3).
3. **`IVfxPoolService.Play(byte, float3 position, float3 normal)`** — the Discrete request surface,
   no-op-safe on unknown ids.
4. **`PoolCatalog` id namespace**: `byte`, `1..255`, `0` reserved, shared across pooled domains (R-5).
5. **The budgets**: `ParticleCeiling`, the 1.5× overdraw ceiling, the ≤0.3 ms renderer feature, < 300 draw
   calls — all measured in a Development IL2CPP build.
6. **`PoolCatalog.Entry` gains a `Tier` field** (⚠️ new, design-review 2026-08-21 finding 4): `Discrete` or
   `Mass`, authored per entry. `OnValidate` checks it against D-4's predicate wherever the owning system can
   supply `max_concurrent_instances`/`per_instance_identity_needed` as authored data (e.g. #15's
   `MaxActiveCasters`-derived count for enemy-projectile-body entries); where the count isn't yet
   authorable, the field still records the classification so VF-AC-08 has something concrete to check
   instead of an unattached "fails review." Today's catalog (`PoolCatalog.cs`) has no such field — this is
   new schema, not a reverse-doc correction.

### Bidirectional edits owed

- **systems-index.md** — #6 `Not Started` → `Draft v1`; record the **hybrid ruling** and that
  `com.unity.visualeffectgraph` is **not yet installed**, with the install scheduled alongside #15.
- **boss-system.md** — V-4's renderer feature and V-3's coherence rule now have an owning pipeline (R-7,
  R-8); one pointer each.
- **spell-projectile-system.md** — R-10's presentation seam points here for the tier question.
- **art-direction.md** — its §4 `gradients_allowed: false` scope clause is load-bearing for world VFX (R-7's
  warning); #19 amendment (9) already records it, this is the second consumer.
- **technical-preferences.md** — lists `com.unity.visualeffectgraph` under allowed libraries as though it
  were present; mark it as **approved but not installed** until R-9's gate passes.
- **ADR** — the hybrid decision deserves its own short ADR (or an amendment to ADR-0008) once the package
  install is attempted, because it is a dependency decision with a rollback plan.

## Tuning Knobs

| Knob | Default | Safe range | Affects | Too high | Too low |
|---|---|---|---|---|---|
| `Prewarm` (per id) | measured | = `PoolStats.PeakRented` | Boot allocation vs first-use hitch (D-1) | boot time + memory for effects nobody plays | first burst allocates — the hitch pooling exists to prevent |
| `Cap` (per id) | 1.5 × `Prewarm` | [1.2, 2.0] × | Burst absorption (R-6) | memory held for a case that happens once | visible drops in ordinary combat, not just swarm wipes |
| `Lifetime` (per id) | 0.4–1.0 s | ≥ 0.05 | Concurrency (D-1) | pool churns; concurrency rises linearly | host returned mid-burst → effect snaps off (VF-EC-11) |
| `ParticleCeiling` | 1 M | [500 K, 1 M] | GPU load (D-2) | frame budget on a 1060 | mass effects thin out and stop reading as mass |
| Hazard overdraw ceiling | **1.5×** screen | — | Fill rate (D-3) | **[G:boss-system V-7]** — hard budget, not a preference | — |
| Renderer-feature budget | **≤ 0.3 ms** | — | Frame (R-8) | eats 1.8%+ of the frame | — |
| Player additive suppression inside stencil | **0.45** | [0.35, 0.6] **[G:boss-system V-4]** | Legibility at max heat | player VFX looks dimmed and wrong inside hazards | hazard washes out under bloom — the failure V-4 exists to prevent |

**Coupled — never tune independently:** `Prewarm` ↔ `Cap` ↔ `Lifetime` (all three set concurrency);
`ParticleCeiling` ↔ overdraw (particle count is meaningless without fill cost).

**Owned elsewhere:** per-spell effect authoring (#30), telegraph grammar and colour (#19 V-1…V-12 /
art-direction §3), voice budget (#8), asset import rules (ADR-0011).

## Acceptance Criteria

> **[Unit]** headless · **[Integration]** live world + pool · **[Visual]** screenshot + sign-off ·
> **[Perf]** Development **IL2CPP** build, GTX 1060 / RX 580 @1080p · **[Bake]** asset-validation pass ·
> **[Manual]** human walkthrough.

### The Discrete path (shipped — these are regression criteria)
- **VF-AC-01** *(BLOCKING, Integration)* — **GIVEN** `ImpactVfxId = 0` or an id absent from the catalog,
  **THEN** `Play` is a no-op and the projectile's damage + destruction are unaffected (VF-EC-1).
- **VF-AC-02** *(BLOCKING, Integration)* — **GIVEN** an empty catalog, **THEN** a full combat sequence runs
  headless with zero errors (VF-EC-2).
- **VF-AC-03** *(BLOCKING, Integration)* — **GIVEN** 200 impact requests in one frame against a pool of
  `Cap = 20`, **THEN** exactly 20 hosts are rented, the excess is dropped, **zero** allocations occur, and
  one warning is logged (R-6 / VF-EC-5).
- **VF-AC-04** *(BLOCKING, Integration)* — **GIVEN** a host returned and re-rented, **THEN** its particle
  system starts clean with no tail from the previous use (VF-EC-10).
- **VF-AC-05** *(BLOCKING, Integration)* — **GIVEN** a `PooledHandle` from a previous WorldSession, **THEN**
  the return is **refused** by generation stamp and nothing crashes (VF-EC-7). *Shared with B-1's leak suite.*
- **VF-AC-06** *(BLOCKING, Unit)* — **GIVEN** a catalog with duplicate ids, a `0` id, or `Cap < Prewarm`,
  **THEN** `OnValidate` reports each while editing (VF-EC-3/4).
- **VF-AC-07** *(BLOCKING, Bake)* — **GIVEN** a catalog entry whose prefab carries no `IPooledEffect`,
  **THEN** **asset validation fails the build** — not a runtime warning (VF-EC-9, the silent failure).

### The tier rule
- **VF-AC-08** *(BLOCKING, Bake)* — **GIVEN** every catalog entry, **THEN** its `Tier` field (Interface
  Contracts §6) is set, and `OnValidate`/P-1 flags any entry with `Tier = Mass` but no declared
  `max_concurrent_instances`/`per_instance_identity_needed` source, or `Tier = Discrete` for an entry whose
  owning system's own budget states `max_concurrent_instances > 100`. ⚠️ **Retagged from `[Manual]`
  (design-review 2026-08-21, findings 4)** — the original wording had no data-model field to check against,
  so "fails review" meant a human judgment call with nothing to look at. With `Tier` added to the catalog
  this becomes a Bake-tier check, same enforcement class as VF-AC-07/19, not a checklist item.
- **VF-AC-09** *(BLOCKING, Integration)* — **GIVEN** a Mass-tier effect at its budgeted instance count,
  **THEN** it costs **one** draw call (D-2's real constraint).
- **VF-AC-10** *(BLOCKING, Integration)* — **GIVEN** a Mass-tier buffer written each frame, **THEN** no
  frame renders a partially-written buffer (VF-EC-12).

### Budgets — IL2CPP build only
- **VF-AC-11** *(BLOCKING, Perf)* — **GIVEN** a max-heat 3-spell chain against ≥8 enemies, **THEN** frame
  time ≤ **16.6 ms** on the target GPU at 1080p.
- **VF-AC-12** *(BLOCKING, Perf)* — **THEN** the renderer feature (stencil suppression + grade) costs
  ≤ **0.3 ms** at 1080p (R-8).
- **VF-AC-13** *(BLOCKING, Perf)* — **THEN** boss hazard transparent overdraw ≤ **1.5×** screen area at any
  camera angle (D-3).
- **VF-AC-14** *(BLOCKING, Perf)* — **THEN** total draw calls stay < **300** with a Mass effect at full
  count (D-2).
- **VF-AC-15** *(BLOCKING, Perf)* — **GIVEN** the VFX Graph package installed, **THEN** build size delta
  ≤ **50 MB** and boot-time delta ≤ **500 ms** (both **[A]**, provisional — Bi may tighten once a real
  measurement exists), **else the install is reverted per R-9's spike-with-rollback framing**. ⚠️
  **Corrected (design-review 2026-08-21, finding 3):** the original wording ("recorded... signed off") had
  no threshold — any delta, however large, satisfied it as long as someone wrote the numbers down. This is
  now a real pass/fail predicate, matching the rest of this AC table.

### Art law
- **VF-AC-16** *(BLOCKING, Visual)* — **GIVEN** any frame with ≥8 enemies, **THEN** no player-authored VFX
  element shows coherent rigid-body motion > **1.0 s** (#19 V-3 / VF-EC-15).
- **VF-AC-17** *(BLOCKING, Visual)* — **GIVEN** max heat inside a hazard stencil, **THEN** the hazard's
  bright line and dark contour remain separable — player additive VFX is suppressed × 0.45 (#19 V-4).
- **VF-AC-18** *(BLOCKING, Visual)* — **GIVEN** the phase grade active, **THEN** telegraph colours are
  **not** desaturated: the grade runs before the VFX pass (#19 V-4/V-7).
- **VF-AC-19** *(BLOCKING, Bake)* — **THEN** no effect introduces a hue outside `art-direction.md` §3's
  closed palette (P-1 validator, ADR-0011).
- **VF-AC-20** *(BLOCKING, Visual)* — **THEN** no effect produces a full-screen flash (art-bible §7D).
- **VF-AC-21** *(ADVISORY, Manual — PT-GATE-VFX-1)* — At max heat with 3 spells chained against ≥8 enemies,
  a naive tester can still point at the boss telegraph and at enemy projectiles.

**Readiness: 21 criteria — 20 BLOCKING / 1 ADVISORY.** ⚠️ **Corrected (design-review 2026-08-21, finding
5):** the pooling **mechanism** underlying several of these criteria is already proven — `PoolFrameworkTests.cs`
(ADR-0008, 16/16 passing) already headlessly exercises cap-refusal-with-zero-alloc
(`Rent_RefusesAtCap_AndCountsTheFailure`, underlying VF-AC-03), generation-stamped double-return/stale-handle
rejection (`DoubleReturn_IsRejected_...`, underlying VF-AC-05), and unknown-id silent refusal
(`PoolService_UnknownId_RefusesQuietly`, underlying VF-AC-01/02). **Split reading: pool mechanism — proven
(ADR-0008, 16/16) · VFX-specific wiring (bridge/service glue, `OnValidate`) — 1 test today** (VF-AC-06). The
Discrete-path criteria still need the ECS/pool harness for their VFX-specific half; every `[Perf]` and
`[Visual]` criterion needs a Development IL2CPP build and art that does not exist yet.

**Implementation prerequisites:**

*Exists:* `IPoolService` + `PoolCatalog` + `PooledHandle` (ADR-0008, 16/16 tests) · `IVfxPoolService` +
`VfxPoolService` · `IPooledEffect` + `ParticleSystemEffect` · `VfxRequestBridge` · `ImpactVfxElement`.

*Missing:* `com.unity.visualeffectgraph` **(not installed — R-9's gate first)** · `VfxGraphEffect :
IPooledEffect` · the Mass-tier `GraphicsBuffer` bridge and its double-buffering · the URP Renderer Feature
(stencil suppression + grade) · the P-1 asset validator rules for R-7 · **all effect art**.

## Open Questions

| ID | Question | Owner | Resolve by |
|---|---|---|---|
| **VF-OQ-1** | **When exactly does the VFX Graph package land?** R-9 says "with #15", because installing it without a Mass-tier effect that exists buys risk and no benefit. But #15's density also *depends* on it, so the two must be scheduled as one piece of work rather than as a dependency chain. | Bi | With #15 |
| **VF-OQ-2** | **Does `DrawMeshInstancedIndirect` + `ComputeBuffer` beat VFX Graph for enemy projectile bodies?** Projectile bodies are *meshes*, not particles — they have a defined shape, orientation and (per #19 V-3) coherent rigid motion. VFX Graph can do it; a plain indirect draw might be simpler and avoids the package entirely. **This is a real fork and the hybrid ruling does not settle it** — it settles *not-CPU*, which both options satisfy. | Bi | Before #15's first story |
| **VF-OQ-3** | **Pool ownership: Root or WorldSession?** `PoolService..ctor` calls `DontDestroyOnLoad`, so it is implicitly Root. B-1 owns the decision; this document only requires that handles crossing a session boundary be invalidated (VF-EC-7). | Bi | B-1 |
| **VF-OQ-4** | **Does a fizzling projectile deserve an effect?** #14's SP-OQ-3, restated from the pipeline side: it is one catalog id and one prefab, so the cost is trivial and the question is purely whether the beat should exist. | Bi | With #29 |
| **VF-OQ-5** | **Is 255 shared ids enough through v1.0?** R-5 accepts it. Worth one count of the projected effect + audio vocabulary at content lock, because the fix (namespace split) is cheap *before* ids are authored and annoying after. | Bi | Content lock |

---

## Review log

| Date | Pass | Verdict |
|---|---|---|
| 2026-08-20 | `design-system` — authored against the shipped pool/VFX chain (`cc877cd`), ADR-0008/0011, and Boss #19's V-rules; **Bi's hybrid ruling taken 2026-08-20** | Draft v1 — 9 rules · 4 formulas · 15 edge cases · 21 AC (20 BLOCKING / 1 ADVISORY) · 5 OQ |
| 2026-08-21 | `/design-review` — 4 independent adversarial passes (`game-designer`, `systems-designer`, `qa-lead`, `unity-dots-specialist`, persona workaround) | **NEEDS REVISION** — 8 BLOCKING (deduped from 9 raw findings across passes), full report [reviews/vfx-pipeline-review-log.md](reviews/vfx-pipeline-review-log.md) |

## Revision pass — 2026-08-21

All 8 blocking findings closed same session — none required a design decision beyond what established
project precedent (ADR-0005, #15's own resolved review) already settles:

| # | How it was closed |
|---|---|
| **1** | R-6: swarm-wipe drops now ordered — `VfxRequestBridge` sorts the frame's batch by distance-to-camera before renting, so drops are always farthest-from-view, never a job-scheduling accident. |
| **2** | D-1: the unquantified "#15's enemy rate" replaced with #15's own corrected worst case (127–298 shots/second, `enemy-projectile-system.md`, 2026-08-21 review) — every shot resolves to one Discrete impact request. |
| **3** | VF-AC-15 given real thresholds (build size ≤ 50 MB, boot time ≤ 500 ms, both `[A]` provisional) with an explicit revert-on-fail clause, replacing the threshold-less "recorded and signed off." |
| **4** | New `Tier` field on `PoolCatalog.Entry` (Interface Contracts §6); VF-AC-08 retagged `[Manual]` → `[Bake]`, now checkable against real schema instead of an unattached "fails review." |
| **5** | "Runnable today: 1" corrected — pool mechanism (ADR-0008, 16/16) is already proven; only VFX-specific wiring is untested. Split reading recorded in the Readiness line. |
| **6** | R-5: new `CatalogPrewarmBudget` (default 500, `[A]`) — `OnValidate` warns when Σ `Prewarm` across all catalog entries exceeds it; closes the "255 ids × generous per-id Cap = unbounded total" gap. |
| **7** | D-2: new `buffer_write_cost` term for the Mass tier's CPU-side per-frame buffer write, previously invisible to a formula that only modeled GPU rasterization cost. |
| **8** | R-4: resolved the sync-vs-lagged ambiguity as **one-frame lag, no synchronous `.Complete()`** — precedent: ADR-0005 (Swarm Perf) already fixed a main-thread stall of this exact shape once. New **VF-EC-16** covers the first-frame-with-no-previous-buffer case this ruling introduces. |

**Not applied as GDD edits, tracked as Recommended/Nice-to-have in the full review log:** R-7's
"enforces vs documents" framing for VF-EC-15/V-3 (QA-gated, not validator-gated); the 60/s-vs-60-concurrent
unit ambiguity in D-1's prose; `ImpactVfxInitSystem`'s `EnsureCapacity(64)` unmanaged-allocator growth under
burst load; system #41's missing systems-index row; VF-AC-10's undefined detection method for a
partially-written Mass buffer; VF-AC-03's "zero allocations" claim not scoped to exclude `DynamicBuffer`
growth; the Discrete path's frame-cadence invariant (FixedStep sub-steps vs. once-per-frame drain) left
implicit rather than stated. None are blocking; revisit alongside the Mass-tier implementation or #15/#41
integration work.

### Verdict of this pass

All 8 blocking findings closed as mechanism additions or corrected numbers, sourced from either this
project's own precedent (ADR-0005) or a sibling GDD's own resolved review (#15). **Ready for
implementation of the Discrete path (already shipped) and specified for the Mass tier**; the Mass tier
itself still awaits R-9's package-install gate and VF-OQ-2's VFX-Graph-vs-indirect-draw fork, both
pre-existing open questions untouched by this pass.

**Not yet run:** `art-director` / `technical-artist` visual-quality pass. Sharpest remaining exposure:
**VF-OQ-2** — the hybrid ruling settles *not-CPU*, but not VFX Graph vs indirect-draw for #15's projectile
bodies, and that choice decides whether the package install happens at all.
