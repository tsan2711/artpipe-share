# NanoSwarm — Art Direction (icon spec)

Feeds the shared artpipe tool at `sanne-kit/Tools/artpipe/` (only one project renders at a time on
the shared PC). NanoSwarm reuses the same generate → matte → stylise → tier machinery; only the
data below is NanoSwarm-specific. Icons are expressed as `kind: spell` (an existing prompt kind):
`element` picks a palette colour, `subtype` picks a shape in `subtype_shape`.

Style target: **cute chibi anime** — same engine as June/cute-pastel (`animagine-xl-4.0-opt`).
Rounded chunky shapes, thick clean outline, soft pastel palette, simple cel shading.
Friendly bots, tasty resources, satisfying upgrades. Single centred subject, transparent background.

## Palette

```yaml
palette:
  energy: { main: "#5EE89A", core: "#EDFFF5", shadow: "#2BAD6A", hue: 150 }
  matter: { main: "#C49FFF", core: "#F5EEFF", shadow: "#8257D4", hue: 265 }
  tech:   { main: "#65D4F5", core: "#E8FAFF", shadow: "#2E9CC4", hue: 195 }
  core:   { main: "#FFD97A", core: "#FFF7E0", shadow: "#D4A030", hue: 40 }
  outline: "#4A3A52"
  neutral:
    light: "#FFF6EC"
    mid:   "#C4B8AF"
    dark:  "#6B5A52"
```

## Palette policy (required by checks.check_palette_conformance)

```yaml
palette_policy:
  closed: true
  delta_e_tolerance: 28
  min_conforming_pixel_ratio: 0.50
  scored_on: flat_field_interior
  interior_min_sample_ratio: 0.15
```

## Readability (required by checks.check_readable_at_64)

```yaml
readability:
  ui_background_reference: "#0A0E14"   # NanoSwarm dark HUD background
  min_contrast_ratio: 3.0
  contrast_percentile: 90
  edge_density_max: 0.22
  outline_dark_lstar_max: 40
  outline_band_min_ratio: 0.5
  value_merge_delta_lstar: 4
  value_coverage_target: 0.90
```

## Shading

```yaml
shading:
  model: cel
  enforcement: light
  value_steps: 4
  max_distinct_values: 24
  gradients_allowed: true
  outline:
    enabled: true
    width_px_at_512: 10
    color: "#4A3A52"
    style: uniform
```

## Icon

```yaml
icon:
  canvas: { width: 512, height: 512, format: "PNG", channels: "RGBA" }
  background: transparent
  safe_margin_pct: 8
  silhouette_coverage_pct: [10, 80]
  display_sizes: [128, 64]
  readability_reference_size: 64
  export:
    - { size: 512, suffix: "_src" }
    - { size: 128, suffix: "" }
```

## Generation

```yaml
generation:
  prompt_prefix: "masterpiece, cute chibi anime game icon,"
  style_phrase: "soft pastel colours, rounded chunky shape, thick clean outline, simple shading, subtle shine"
  matte_method: segment
  max_prompt_tokens: 0
  negative_prompt: "dark, gloomy, grimdark, horror, magic circle, mandala, halo ring, washed out, desaturated, photograph, 3d render, drop shadow, text, watermark, logo, frame, border, busy background, multiple objects, sticker, white border, die-cut outline"
```

## Element paint — colour as words (the checker reads the hex above; the model reads this)

```yaml
element_paint:
  energy: "soft mint green with pale highlight"
  matter: "soft lavender purple with lilac highlight"
  tech:   "baby blue with white highlight"
  core:   "warm honey gold with cream highlight"
```

## Element colour — hue per role (structural; short-form prompt does not need it)

```yaml
element_color:
  energy: "soft mint green"
  matter: "soft lavender purple"
  tech:   "baby blue"
  core:   "warm honey gold"
```

## Subtype shape — one entry per icon

```yaml
subtype_shape:
  # ── HUD icons ──
  energy-cell:    "a cute glowing round energy orb with a sparkle, friendly and bright"
  matter-crystal: "a cute pastel crystal gem with a few sparkles around it"
  bot-harvester:  "a tiny chubby adorable round robot with big shiny eyes and a little drill claw"
  bot-builder:    "a tiny chubby cute robot with big eyes holding a little wrench"
  bot-defender:   "a tiny chubby cute robot with big eyes wearing a round shield"
  up-speed:       "a cute rounded arrow with two motion lines and little stars"
  up-yield:       "a cute upward arrow over a glowing orb with sparkles"
  up-territory:   "cute expanding concentric circles with little stars at the tips"
  up-shield:      "a cute rounded shield with a star emblem on it"
  up-offline:     "a cute crescent moon hugging a glowing orb, tiny sleeping stars nearby"
  # ── Entity sprites — tiny in-game dots, must read at 16-32px ──
  # Design rule: solid coloured bubble + ONE minimal mark. No robot limbs, no text.
  ent-harvester:  "a small soft round bubble with a tiny drill bite notch on one side, cute and simple"
  ent-builder:    "a small soft round bubble with a tiny wrench silhouette inside, cute and simple"
  ent-defender:   "a small soft round bubble with a tiny shield arc on the front, cute and simple"
  ent-rival:      "a small soft round bubble with tiny spike bumps on its outline, slightly grumpy face, cute"
  ent-core:       "a large glowing soft circle dome with a gentle happy face, surrounded by a faint ring, cute"
  ent-node:       "a small sparkling teardrop gem with a single star glint on top, cute and simple"
  # ── Ally harvester animation frames ──
  # Character anchor: ONE soft round mint-green bubble, dark outline, simple shape only
  # Rule: describe SHAPE change only, never use action verbs (lunge/strike/snap)
  # idle — gentle scale pulse
  anim-harv-idle-0:   "one soft round mint green bubble, dark outline, normal size, calm, soft inner glow, white highlight dot"
  anim-harv-idle-1:   "one soft round mint green bubble, dark outline, slightly larger rounder shape, brighter glow, white highlight dot"
  anim-harv-idle-2:   "one soft round mint green bubble, dark outline, normal round shape, sleepy half-closed eyes, soft glow"
  anim-harv-idle-3:   "one soft round mint green bubble, dark outline, slightly smaller deflated shape, dim glow, relaxed"
  anim-harv-idle-4:   "one soft round mint green bubble, dark outline, normal round shape, eyes open, fresh glow"
  anim-harv-idle-5:   "one soft round mint green bubble, dark outline, slightly tilted right, white highlight dot, happy eyes"
  anim-harv-idle-6:   "one soft round mint green bubble, dark outline, slightly tilted left, dim white highlight, content"
  anim-harv-idle-7:   "one soft round mint green bubble, dark outline, perfectly round, centered highlight dot, neutral face"
  # move — horizontal squish/stretch shape only
  anim-harv-move-0:   "one soft mint green bubble, dark outline, wide flat oval shape squished horizontal, wider than tall, white highlight"
  anim-harv-move-1:   "one soft mint green bubble, dark outline, very flat wide oval shape, speed lines on left side, no face"
  anim-harv-move-2:   "one soft mint green bubble, dark outline, oval shape leaning right, wider right side, highlight dot"
  anim-harv-move-3:   "one soft mint green bubble, dark outline, tear-drop shape stretched right side, white highlight"
  anim-harv-move-4:   "one soft mint green bubble, dark outline, round shape with slight right bulge, recovering form"
  anim-harv-move-5:   "one soft mint green bubble, dark outline, round shape wobbling, wavy bottom edge, highlight dot"
  anim-harv-move-6:   "one soft mint green bubble, dark outline, round compact shape, small motion lines right, cute face"
  anim-harv-move-7:   "one soft mint green bubble, dark outline, round shape tilting forward, highlight dot, determined eyes"
  # attack — brightness/glow change on same round shape
  anim-harv-atk-0:    "one soft mint green bubble, dark outline, round shape, white glow ring around outline, bright inner light"
  anim-harv-atk-1:    "one soft mint green bubble, dark outline, round shape, very bright white inner core glow, squinting eyes"
  anim-harv-atk-2:    "one soft mint green bubble, dark outline, round shape with bright flash spike on right side, energy burst"
  anim-harv-atk-3:    "one soft mint green bubble, dark outline, round shape, large white star burst shape inside, full glow"
  anim-harv-atk-4:    "one soft mint green bubble, dark outline, round shape, bright yellow-green inner glow fading, open eyes"
  anim-harv-atk-5:    "one soft mint green bubble, dark outline, round shape, small sparkle rings around outside, satisfied face"
  anim-harv-atk-6:    "one soft mint green bubble, dark outline, round shape, faint glow ring shrinking, relaxed eyes"
  anim-harv-atk-7:    "one soft mint green bubble, dark outline, normal round shape, calm glow, white highlight dot, happy"
  # ── UI completion batch 2026-09-23 ──
  # UI
  ui-settings: "a cute rounded cog gear with a soft glossy highlight"
  ui-close: "a cute chunky rounded X cross mark"
  ui-missions: "a cute rolled paper scroll with a ribbon and a tiny check mark"
  ui-nano-core: "a cute glowing faceted crystal core orb with a bright inner star, precious"
  ui-trophy: "a cute golden trophy cup with two round handles and a star"
  ui-shop: "a cute shopping bag with a round handle and a heart tag"
  ui-ad: "a cute rounded rectangle screen with a big play triangle in the middle"
  ui-vol-master: "a cute speaker with three curved sound waves"
  ui-vol-sfx: "a cute little bell with sparkles ringing"
  ui-vol-music: "a cute pair of eighth music notes joined by a beam"
  ui-lock: "a cute chunky padlock with a round keyhole"
  ui-check: "a cute round badge with a bold check mark"
  ui-rivals: "a cute waving flag on a short pole with a round emblem"
  ui-knowledge: "a cute open book with a small glowing flask on top"
  # Achievement tabs
  tab-colony: "a cute little dome house colony with a round window"
  tab-combat: "a crossed sword and round shield, simple and bold"
  tab-prestige: "a cute shining star with a small upward arrow"
  tab-collection: "a cute open treasure box with gems peeking out"
  tab-secret: "a cute round question mark bubble"
  # IAP
  iap-remove-ads: "a tv screen with a play triangle covered by a big red prohibition circle slash"
  iap-starter-pack: "a cute gift box with a big bow, a green orb and a purple crystal peeking out"
  iap-prestige-boost: "a cute rocket flying up with a sparkling star trail"
  # Fix blank HUD icons
  fix-expand: "a cute circle with four rounded arrows pointing outward"
  fix-speed-up: "a cute lightning bolt with a small upward arrow"
  fix-yield-up: "a cute glowing green orb with a small upward arrow and sparkles"
  # App icon
  app-icon: "a cute round mint green bubble robot with big shiny eyes and a tiny drill, happy face, glowing, hero pose"
  # Prestige Tree nodes
  pt-legacy-harvesters: "a cute mint bubble robot with a tiny crown"
  pt-echo-yield: "a cute glowing orb with an echo ring around it"
  pt-fast-start: "a cute stopwatch with motion swoosh"
  pt-matter-seed: "a cute purple crystal sprouting from a seed with two leaves"
  pt-builder-legacy: "a cute blue bubble robot holding a tiny wrench, with a small crown"
  pt-nano-memory: "a cute glowing brain chip with a small star"
  pt-territory-memory: "a folded paper map with a red location pin and a dotted circle border"
  pt-rival-taming: "a cute grumpy spiky bubble wearing a tiny bow, calm"
  pt-quantum-harvest: "a purple atom symbol with three elliptical orbit rings around a glowing gem"
  pt-nano-evolution: "a cute DNA helix made of tiny bubbles"
  pt-matter-cascade: "a cute waterfall of small purple crystals"
  pt-defender-legacy: "a round blue shield with a big golden crown sitting on top of it"
  pt-singularity: "a cute swirling golden vortex with a bright center"
  pt-hive-mind: "a golden honeycomb made of six hexagon cells with small glowing dots connected by lines"
  pt-infinite-territory: "a big golden infinity sign ribbon floating above a small green planet"
  pt-nano-ascension: "a cute bubble robot with small angel wings and a halo of stars"
  # Research Tree nodes
  rt-swarm-sync: "three cute tiny bubble robots in a row with sync lines"
  rt-node-memory: "a glowing green orb with a circular refresh arrow wrapped around it"
  rt-energy-compression: "a cute battery squeezed by a clamp, glowing"
  rt-threat-intel: "a green round radar screen with sweep line and one red warning dot"
  rt-passive-scan: "a cute magnifying glass over a small glowing orb"
  rt-formation-tactics: "three cute tiny bubble robots in a triangle formation"
  rt-rapid-survey: "a cute compass with a speed swoosh"
  rt-matter-extraction: "a cute pickaxe chipping a purple crystal"
  rt-adaptive-shield: "a cute shield with a small plus heal sign"
  rt-rare-vein: "a cute golden glowing ore vein in a rock"
  rt-auto-target: "a red and white bullseye target with an arrow stuck in the center"
  rt-offline-tripler: "a cute crescent moon with a small x3 tag"
  rt-expanded-roster: "a cute bubble robot with a small plus two badge"
  rt-deep-survey: "a big eye with a green iris looking over a small folded map"
  rt-coordinated-strike: "three cute arrows converging on one point"
  rt-nano-reserve: "a cute treasure chest filled with glowing orbs"
  rt-quantum-router: "a signpost with three arrows pointing in different directions"
  rt-field-researcher: "a cute clipboard with a small flask"
  rt-expanded-field: "a small planet surrounded by a wide ring made of many tiny dots"
  rt-neural-pathfinding: "a network of glowing dots connected by lines forming a winding path with an arrow"
  rt-multiplier-extension: "a golden badge with a big bold number 2 and a plus sign, sparkles"
  rt-defense-network: "three cute small shields linked together"
  rt-corrupted-analysis: "a cute dark purple cracked crystal with a magnifying glass"
  rt-cache-proliferation: "two cute small treasure chests with sparkles"
  rt-hive-core: "a cute glowing golden reactor core with energy rays"
  # HUD icon refresh 2026-09-23
  hud-energy: "a glowing mint green lightning bolt inside a round energy orb"
  hud-matter: "a faceted lavender purple crystal gem with sparkles"
  hud-harvester: "a cute round mint green bubble robot holding a tiny drill, big shiny eyes"
  hud-builder: "a cute round baby blue bubble robot holding a tiny wrench, big shiny eyes"
  hud-defender: "a cute round honey gold bubble robot holding a small round shield, big shiny eyes"
  hud-speed: "a blue sneaker with wing and speed lines"
  hud-yield: "a green orb overflowing from a small basket with an upward arrow"
  hud-territory: "a round map with a flag planted in the middle and a dotted circle border"
  hud-shield: "a round golden shield with a star emblem in the center"
  hud-offline: "a sleeping crescent moon wearing a night cap with small Z letters"
  # Entity sprites v2 2026-09-23
  ent2-harvester: "a small round bubble bot with big shiny eyes and a tiny drill on one side, thick dark outline, very simple"
  ent2-builder: "a small round bubble bot with big shiny eyes holding a tiny wrench, thick dark outline, very simple"
  ent2-defender: "a small round bubble bot with big shiny eyes behind a round shield, thick dark outline, very simple"
  ent2-rival: "a small round bubble bot with little spikes on top and grumpy eyes, thick dark outline, very simple"
  ent2-core: "a round glowing dome reactor core with a happy face and a soft ring around it, thick dark outline"
  ent2-civ-core: "a round dome fortress core with a small flag on top and a soft ring around it, thick dark outline"
  ent2-node-energy: "a small glowing round energy orb with a sparkle, thick dark outline, very simple"
  ent2-node-matter: "a small faceted crystal cluster, thick dark outline, very simple"
  ent2-node-rare: "a small shining golden gem nugget with bright star glints, thick dark outline"
  ent2-node-corrupted: "a small dark purple cracked crystal with a faint glowing aura, thick dark outline"
  ent2-node-cache: "a small cute treasure chest slightly open with light glowing out, thick dark outline"
  # ── Gacha painterly regen 2026-09-28 (gen_gacha_painterly.py — same text as its CATALOG; animagine-xl-4.0-opt, icon_anime.json + RMBG) ──
  gacha-cmd-clamp: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, honey yellow round body, wearing a miner helmet with a headlamp, cheerful big grin, round sparkly eyes"
  gacha-cmd-spark: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, orange body, spiky lightning bolt shaped hair tuft, cheeky wink, one eye closed, tongue out"
  gacha-cmd-hook: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, sky blue body, wearing an orange hard hat, focused determined eyes, holding a tiny wrench"
  gacha-cmd-shell: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, mint green body, wearing a round turtle shell on its back, sleepy half closed eyes, calm smile"
  gacha-cmd-vega: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, violet purple body, a sniper scope monocle over one eye, confident smirk, cool"
  gacha-cmd-mira: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, pink body, a big horseshoe magnet on its head, happy closed eyes smile, blushing"
  gacha-cmd-kite: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, turquoise teal body, aviator goggles on forehead and a red scarf flowing, excited open mouth"
  gacha-cmd-bastion: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, silver grey body, wearing a small knight helmet with a red plume, shy blushing eyes looking aside"
  gacha-cmd-relay: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, lemon yellow body, a satellite dish antenna on top and headphones, gentle calm eyes"
  gacha-cmd-orrin: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, golden yellow body, wearing a golden crown with gems, proud heroic grin, star shaped eye highlights"
  gacha-cmd-nyx: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, deep lavender purple body, wearing a cozy hood with cat ears, mysterious sly half lidded eyes, small smile"
  gacha-cmd-atlas: "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait, rusty orange red chunky body, wearing a viking helmet with two horns, fierce but cute frown, puffed cheeks"
  gacha-capsule-common: "one round plastic toy ball like a pokeball, top half glossy baby blue dome, bottom half white, thin band in the middle, small cute face with blush on the white half"
  gacha-capsule-rare: "one round plastic toy ball like a pokeball, top half glossy lavender purple dome, bottom half white, thin band in the middle, small cute face with blush on the white half"
  gacha-capsule-legend: "one round plastic toy ball like a pokeball, top half glossy shiny gold dome, bottom half white, thin band in the middle, small cute face with blush on the white half"
  gacha-role-harvest: "one small green seedling sprout with two round green leaves in a little brown clay pot"
  gacha-role-build: "one chunky toy hammer, yellow metal head, brown wooden handle"
  gacha-role-fight: "one chunky short toy sword, silver blade, red round guard, brown grip"
  gacha-role-support: "one round sky blue shield with a pink heart emblem in the middle"
  gacha-ui-signal: "a cute small radio antenna tower with a round glowing honey gold bulb on top and two curved signal waves"
  gacha-ui-stardust: "a cute little glass jar full of glowing lavender and gold star dust, cork lid"
  gacha-ui-commander: "a cute chibi round mint green nanobot robot wearing a tiny navy captain hat, big shiny eyes, saluting"
  gacha-sk-squadcarry: "a cute little cardboard box overflowing with glowing mint green energy orbs"
  gacha-sk-squaddamage: "a cute orange fist punching with a small impact star"
  gacha-sk-squadbuild: "a cute wrench and hammer crossed, sky blue handles"
  gacha-sk-squadhp: "a cute mint green heart with a white plus sign"
  gacha-sk-squadpierce: "a cute violet arrow flying through two small targets"
  gacha-sk-pickupmagnet: "a cute pink horseshoe magnet pulling small orbs"
  gacha-sk-squadspeed: "a cute teal winged boot with speed lines"
  gacha-sk-stillshield: "a cute round silver dome bubble shield"
  gacha-sk-chargeregen: "a cute lemon yellow battery with a circular refresh arrow"
  gacha-sk-pulseemp: "a cute golden round pulse wave ring bursting from a small orb"
  gacha-sk-convert: "a cute lavender purple potion flask with a swirl turning a grey blob into a heart"
  gacha-sk-giant: "a cute big rusty orange robot fist smashing a small rock"
```
