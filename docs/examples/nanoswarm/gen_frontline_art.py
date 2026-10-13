#!/usr/bin/env python3
"""Match Frontline v6 + Commander v2 art (2026-10-01) — design/gdd/match-frontline-v6.md §9, commander-v2-buildup.md §8.

Two lanes, both on the local ComfyUI (animagine-xl-4.0-opt + RMBG), reusing gen_gacha_painterly's graph:

* ICONS — same painterly shop-icon look as Assets/UI/HUD/Icons/Gen/iap-starter-pack.png (cute rules apply to HUD icons).
* CHARACTERS — moodboard direction C (session-state/robot-refs/web/findings.md): 2–2.5-head 2D gacha chibi, thin line that
  takes the colour of each area, eyes with two highlights, soft cel 2-tone, warm pastel; limbs readable apart for a 2D rig.
  Style reference only — no game, studio or character names in prompts. Characters are CONCEPTS for Bi to pick first
  (memory: three robot styles were rejected — do not ship a full set without approval).

    py -3 tools/artpipe/gen_frontline_art.py gen   <out-dir> <group|slug ...> [--variants 3] [--seed 7000]
    py -3 tools/artpipe/gen_frontline_art.py sheet <out-dir> <group> <sheet.png>      → review contact sheet
    py -3 tools/artpipe/gen_frontline_art.py pick  <out-dir> slug=variant ...           → Assets/UI/HUD/Icons/Gen/<slug>.png (icons)
Groups: icons-weapons, icons-skills, icons-ui, icons-branch, icons-camp, icons-units, chars-heroes, chars-units, chars-wild
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_gacha_painterly as gp   # graph(), call(), run(), icon(), trim()

NS = gp.NS
GEN = NS / "Assets/UI/HUD/Icons/Gen"

ICON_PREFIX = gp.PREFIX
ICON_STYLE = gp.STYLE
ICON_NEG = gp.NEGATIVE

CHAR_PREFIX = "masterpiece, best quality, very aesthetic, newest, solo, no humans, full body, official art, polished 2d mobile gacha game character illustration, chibi, 2.5 heads tall, standing,"
CHAR_STYLE = ("thin clean coloured lineart that matches each colour area, big expressive eyes with two white highlights, soft "
              "two-tone cel shading, warm pastel palette with one saturated accent colour, slightly open friendly pose with arms "
              "and legs clearly separated from the body, clean colour areas, smooth finished rendering, plain white background, centered")
CHAR_NEG = ("frame, border, rounded rectangle, card, sketch, rough lines, messy lines, unfinished, doodle, lightning bolts around, motion lines, 3d render, plastic, glossy toy, vinyl figure, clay, photograph, realistic, dark, gloomy, horror, thick black outline, "
            "flat vector, sticker, white border, text, watermark, logo, frame, multiple views, character sheet, turnaround, "
            "group, crowd, duplicate, lowres, bad anatomy, blurry, jpeg artifacts, busy background, sparkles everywhere, rays")

BOT = "a cute small robot hero, round head with a soft face screen"

ICONS = {
    # ── weapons (commander-v2 §3) ──
    "wpn-wrench":       "one chunky cute toy wrench, silver head, orange rubber grip, small star sticker",
    "wpn-battery":      "one cute spare battery cell, mint green with a lightning bolt label, small cap",
    "wpn-whistle":      "one cute round whistle, sky blue with a pink lanyard",
    "wpn-pulsecore":    "one glowing round energy core orb in a small metal cage, violet glow",
    "wpn-hourglass":    "one cute hourglass, golden frame, pink sand flowing",
    "wpn-badge":        "one round medal badge with a ribbon, honey gold star in the middle",
    "wpn-starhammer":   "one big cute war hammer, golden head shaped like a star, red handle",
    "wpn-mothershield": "one big round guardian shield, white and sky blue, a soft pink heart gem in the middle, wings on the sides",
    "wpn-goldcompass":  "one golden pocket compass, open lid, glowing mint needle",
    # ── match skills (commander-v2 §1) ──
    "ic-cs-clamp":   "one wooden supply crate with a parachute, glowing green energy orbs peeking out",
    "ic-cs-spark":   "one orange lightning bolt with speed lines, a tiny sneaker",
    "ic-cs-hook":    "one cute little stone watch tower with a blue roof",
    "ic-cs-shell":   "one round mint green turtle shell shield glowing",
    "ic-cs-vega":    "one round red and white bullseye target with three small violet arrows stuck in it",
    "ic-cs-mira":    "one pink horseshoe magnet pulling small gift boxes",
    "ic-cs-kite":    "one teal diamond shaped paper kite with a long red ribbon tail and a small white star, flying",
    "ic-cs-bastion": "one small cute castle tower with a silver flag",
    "ic-cs-relay":   "one yellow wrench crossing a pink heart, repair",
    "ic-cs-orrin":   "one small golden crown in the center with two round sky blue shockwave rings around it",
    "ic-cs-nyx":     "one lavender potion flask with swirling purple smoke",
    "ic-cs-atlas":   "one giant rusty orange robot foot stomping, small dust clouds",
    # ── Lobby UI ──
    "ui-armory":   "one cute blacksmith anvil with a small hammer resting on it, warm orange glow",
    "ui-levelup":  "one big mint green up arrow with a small gold star",
    # ── point upgrade branches (frontline §3.4) ──
    "br-barracks": "one cute small army tent, red and cream stripes, a little flag on top",
    "br-tower":    "one cute round grey stone castle turret with battlements on top and a small orange cannon poking out of a window",
    "br-forge":    "one cute little forge furnace with glowing orange fire and a sword",
    # ── wild camp rewards (frontline §3.5) ──
    "camp-energy":  "one glowing mint green energy crystal cluster",
    "camp-command": "one blue command scroll with a gold seal",
    "camp-xp":      "one shiny purple experience star with a plus sign",
    "camp-relic":   "one ancient golden relic amulet with a teal gem",
    # ── unit-type badges on Points (frontline §3.1) ──
    "unit-grunt":  "one simple round silver helmet",
    "unit-shield": "one sturdy rectangular blue tower shield",
    "unit-runner": "one teal winged boot",
    "unit-ranged": "one small orange cannon",
    "unit-sapper": "one round black bomb with a lit fuse and a pink bow",
    "unit-guard":  "one cute watch eye lantern on a pole",
}

CHARS = {
    # ── hero concepts: 3 representative Commanders first (Fight / Support / Legend) ──
    "hero-spark":  f"{BOT}, orange body, spiky lightning bolt hair tuft, cheeky wink, running pose, small arm cannon",
    "hero-shell":  f"{BOT}, mint green body, a round turtle shell backpack, sleepy calm smile, holding a round shield",
    "hero-orrin":  f"{BOT}, golden yellow body, small golden crown, proud grin, a short cape, raising a fist with a pulse glow",
    # ── the other 9 (Bi 2026-10-02: heroes = this direction C; anchors spark 2 · shell 1 · orrin 2). One silhouette
    #    feature each, matching the cmd-<id> portraits; body colour = commanders.csv tint ──
    "hero-clamp":   f"{BOT}, honey yellow body, a miner hard hat with a head lamp, happy open smile, carrying a small pickaxe on the shoulder",
    "hero-hook":    f"{BOT}, sky blue body, a builder hard hat, focused cute face, holding a big wrench",
    "hero-vega":    f"{BOT}, lavender purple body, a sniper scope monocle over one eye, cool confident smirk, holding a small crossbow",
    "hero-mira":    f"{BOT}, soft pink body, a big horseshoe magnet held up in both hands, cheerful sparkly eyes",
    "hero-kite":    f"{BOT}, aqua teal body, flight goggles on the head and a long scarf blowing, energetic pose",
    "hero-bastion": f"{BOT}, silver grey body, a little knight helmet with a plume, holding a big round shield, brave face",
    "hero-relay":   f"{BOT}, lemon yellow body, a small satellite dish on the head and big headphones, friendly wave",
    "hero-nyx":     f"{BOT}, deep violet body, a soft hood with cat ears, sly half-closed eyes, a wisp of purple smoke around one hand",
    "hero-atlas":   f"{BOT}, rusty orange red body, larger and chunky, a horned helmet, determined grin, heavy stomping pose",
    # ── unit types (frontline §3.1): tiny troops, tintable — mostly white and light grey with one accent. Front view,
    #    symmetrical stance: a swarm troop must not face left or right (Bi 2026-09-24). Art set B of the A/B test. ──
    "trp-grunt":  "a tiny cute round robot soldier, white and light grey body, small helmet, simple, readable silhouette, one teal accent, front view facing the viewer, symmetrical stance",
    "trp-shield": "a tiny cute chunky robot carrying a big tower shield, white and light grey body, sturdy, one blue accent, front view facing the viewer, symmetrical stance",
    "trp-runner": "a tiny cute slim robot with winged boots, leaning forward running, white and light grey body, one teal accent, front view facing the viewer, symmetrical stance",
    "trp-ranged": "a tiny cute robot with a small cannon on its shoulder, white and light grey body, one orange accent, front view facing the viewer, symmetrical stance",
    "trp-sapper": "a tiny cute robot hugging a round bomb with a lit fuse, white and light grey body, one pink accent, front view facing the viewer, symmetrical stance",
    "trp-guard":  "a tiny cute robot sentry holding a lantern spear, white and light grey body, one yellow accent, front view facing the viewer, symmetrical stance",
    # ── wild camps + wild boss, chapter 1 "breakfast table" theme ──
    "wild-crumb":   "a cute small monster made of a cookie crumb, angry little eyebrows but cute, tiny legs",
    "wild-cereal":  "a cute small monster that is a cereal ring, round, cheeky grin, tiny arms",
    "wild-jam":     "a cute small jelly blob monster made of strawberry jam, wobbly, big shiny eyes",
    "wild-nest":    "a cute big cereal bowl full of milk with cereal rings floating, a cozy monster nest, no character, front view",
    "wild-boss":    "a big cute boss monster whose whole body is one round golden brown chocolate chip cookie, cookie texture with chocolate chips, stubby arms and legs, determined frown, a tiny sugar cube crown",
}

GROUPS = {
    "icons-weapons": [k for k in ICONS if k.startswith("wpn-")],
    "icons-skills":  [k for k in ICONS if k.startswith("ic-cs-")],
    "icons-ui":      ["ui-armory", "ui-levelup"],
    "icons-branch":  [k for k in ICONS if k.startswith("br-")],
    "icons-camp":    [k for k in ICONS if k.startswith("camp-")],
    "icons-units":   [k for k in ICONS if k.startswith("unit-")],
    "chars-heroes":  [k for k in CHARS if k.startswith("hero-")],
    "chars-units":   [k for k in CHARS if k.startswith("trp-")],
    "chars-wild":    [k for k in CHARS if k.startswith("wild-")],
}


def entry(slug, group):
    if group.startswith("chars"):
        return f"{CHAR_PREFIX} {CHARS[slug]}, {CHAR_STYLE}", CHAR_NEG
    return f"{ICON_PREFIX} {ICONS[slug]}, {ICON_STYLE}", ICON_NEG


def group_of(slug):
    for g, l in GROUPS.items():
        if slug in l:
            return g
    raise SystemExit(f"unknown slug {slug}")


def gen(out_dir, targets, variants, seed0):
    out_dir.mkdir(parents=True, exist_ok=True)
    slugs = []
    for t in targets:
        slugs += [(s, t) for s in GROUPS[t]] if t in GROUPS else [(t, group_of(t))]
    for si, (slug, group) in enumerate(slugs):
        prompt, neg = entry(slug, group)
        tag = f"{group.split('-')[0]}_{slug}"
        for v in range(variants):
            dst = out_dir / f"{tag}__{v}.png"
            if dst.exists():
                continue
            gp.NEGATIVE = neg
            raw, alpha = gp.run(prompt, seed0 + si * 100 + v)
            (out_dir / f"{tag}__{v}_raw.png").write_bytes(raw)
            dst.write_bytes(alpha)
            print(tag, v, flush=True)
    gp.NEGATIVE = ICON_NEG


def sheet(out_dir, group, dst, cell=256):
    slugs = GROUPS[group]
    tagp = group.split('-')[0]
    files = {s: sorted(out_dir.glob(f"{tagp}_{s}__[0-9].png")) for s in slugs}
    cols = max((len(v) for v in files.values()), default=1)
    W, H = 220 + cols * (cell + 12), 40 + len(slugs) * (cell + 12)
    im = Image.new("RGB", (W, H), (250, 246, 238))
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    d.text((12, 8), f"{group} — variants 0..{cols - 1}", fill=(74, 58, 82), font=font)
    for r, s in enumerate(slugs):
        y = 40 + r * (cell + 12)
        d.text((12, y + cell // 2 - 10), s, fill=(74, 58, 82), font=font)
        for c, f in enumerate(files[s]):
            x = 220 + c * (cell + 12)
            src = Image.open(f).convert("RGBA")
            src.thumbnail((cell, cell))
            bg = Image.new("RGBA", (cell, cell), (255, 255, 255, 255))
            bg.alpha_composite(src, ((cell - src.width) // 2, (cell - src.height) // 2))
            im.paste(bg.convert("RGB"), (x, y))
            d.text((x + 6, y + 4), str(c), fill=(160, 120, 170), font=font)
    im.save(dst)
    print("sheet", dst)


def pick(out_dir, picks):
    GEN.mkdir(parents=True, exist_ok=True)
    for p in picks:
        slug, v = p.split("=")
        src = out_dir / f"icons_{slug}__{v}.png"
        img = gp.icon(Image.open(src).convert("RGBA"))
        img.save(GEN / f"{slug}.png")
        print("picked", slug, v)


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd, out = a[0], Path(a[1])
    rest = a[2:]
    variants, seed = 3, 7000
    if "--variants" in rest: i = rest.index("--variants"); variants = int(rest[i + 1]); del rest[i:i + 2]
    if "--seed" in rest: i = rest.index("--seed"); seed = int(rest[i + 1]); del rest[i:i + 2]
    if cmd == "gen": gen(out, rest, variants, seed)
    elif cmd == "sheet": sheet(out, rest[0], Path(rest[1]))
    elif cmd == "pick": pick(out, rest)
