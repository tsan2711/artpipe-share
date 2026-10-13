# UI polish — motion + VFX plan (2026-09-24)

Scope: every place the HUD/world needs feedback, which technique each uses, and the art it needs.
Art status lives in [asset-backlog.md](asset-backlog.md) (the rows below are mirrored there).

## Techniques — which one, when

| Technique | Where it renders | Use for | Cost |
|---|---|---|---|
| **UITween / UIMotion** (package `com.seriously.uilayers`, `Runtime/Motion`) | UI Toolkit | press squash, pop/fade/slide of views, punch, shake, pulse, count-up, fly-to | translate/scale/rotate/opacity only → repaint, never layout; 0 GC after warm-up |
| **UIFlipbook** (frame-by-frame, USS class per frame) | UI Toolkit | short shaped animations that must look hand-drawn: tap ripple, reward shine | frames ≤128 px → dynamic atlas → no extra batch |
| **UIFxPlayer.Burst** (pseudo-particles: pooled sprites tweened outward) | UI Toolkit | sparkles/confetti **over UI** (a ParticleSystem would draw *under* UI Toolkit) | budget-capped (96 live) |
| **ParticleSystem prefab + Emit** (one instance per effect type, shared by all bursts) | world, under the HUD | anything that happens *on the map*: pickups, EMP, kills, core destroyed, territory ring | one draw call per effect type; one atlas + one material |

Why not a tween library: LitMotion (MIT, zero-alloc, has UI Toolkit binders) and PrimeTween were evaluated.
The package must stay dependency-free and UI tween counts are tiny (tens), so a 300-line runner is enough.
Both libraries still work side by side — UITween only touches the inline styles it animates.
USS `transition` was rejected for view open/close: `TransitionEndEvent` does not fire when the value does not change or the element is display:none, so "hide after the exit animation" is unreliable.

Frame-by-frame vs particles: frame-by-frame only where the *shape* animates (a ring that squashes, rays that
rotate/grow). Anything that is "many small things flying" = particles (world) or pseudo-particles (UI).

## Hooks

### UI (automatic, from templates)
| Hook | Effect | Status |
|---|---|---|
| Every UIButton press | squash 0.93 → spring back (OutBack) | done (UIButton.PressFeedback) |
| Round icon buttons, cute buttons (UiKit) | same | done (UiKit adds UIPressFeedback) |
| Every stage view open/close | Pop (popups), Fade (screens), SlideUp (sheets); scrim fades | done (UIStage) |
| Toasts | slide down in, fade out | done (UIToasts) |
| Badge count changes | punch | done (UIButton.Badge) |

### UI (game hooks — NanoSwarm `HudFx`)
| Trigger | Effect | Art |
|---|---|---|
| Tap on the map | tap ripple flipbook at the finger | `fx-tap-0..5` |
| Upgrade bought | Buy bar punch + star burst on the row | `fx-star` |
| Pickup collected | icons fly from the pickup's screen point to the Energy/Matter counter, counter punch | reuse `icon-energy` / `icon-matter` |
| Offline Collect / wave cleared reward | fly-to-counter (8 icons) | reuse |
| Purchase granted / achievement / mission complete | shine flipbook + confetti burst over the toast | `fx-shine-0..7`, `fx-confetti` |
| Skill cast | skill button punch + ring burst | `fx-star`, `fx-dot` |
| Command Charge full, upgrade badge visible | pulse loop | — |

### World (ParticleSystem prefabs — `Assets/Prefabs/Fx/fx_<id>.prefab`, listed in `WorldFxCatalog`; `WorldFx` instantiates each once and calls `Emit` per event)
| Trigger (event) | Effect | Atlas tile |
|---|---|---|
| PickupCollectedEvent | sparkle pop, tinted by kind | star, glow |
| EmpHitEvent | shockwave ring + sparks | ring, spark |
| EnemyBotKilledEvent | tiny poof | puff |
| CivDefeatedEvent | big burst + confetti | glow, confetti |
| TerritoryExpandedEvent | expanding ring from the core | ring |
| HiddenCacheDiscoveredEvent | rising sparkles | star |
| NodeDepletedEvent | poof | puff |

Theme: pastel palette + ink outline `#4A3A52` from `tools/artpipe/art-direction.md`. All FX art is drawn by
`tools/artpipe/draw_vfx_sprites.py` (vector, deterministic). Diffusion was not used for FX: the 2026-09-23 batch
already failed on functional symbols, and tiny FX shapes need exact silhouettes, not "cute bubbles".

### Entities (pass 2, 2026-09-24) — `EntityVfxRenderer`, one draw call, see bot-attack-vfx.md implementation note
| Trigger | Effect |
|---|---|
| Defender fires | 2-spark muzzle flash along the shot, civ colour (player = #4FC3F7) |
| Projectile hits a bot / a Core | 4 / 7 star sparks + a glow pop |
| Bot dies | 8-particle radial dissolve in the bot's colour + a cream puff |
| Bot spawns (after boot) | 6 glows converge, then a ring pops |
| Harvest tick lands | 2 green motes rise from the node |

## Open (needs a GDD, not code)
- **Left side of the HUD is mostly empty** (Bi 2026-09-24). Decide what lives there (e.g. quest/objective tracker,
  event queue, colony stats, shortcuts) in a HUD layout GDD before adding anything.
