#!/usr/bin/env python3
"""Gacha / Commander icons, painterly lane (2026-09-28 regen) — same look as the shop icons (iap-starter-pack.png).

Bi rejected the flat vector redraw (identical faces, hard flat lines, washed-out colour, sparkle spam). This drives the
local ComfyUI with the artpipe anime graph (sanne-kit/Tools/artpipe/workflows/icon_anime.json, animagine-xl-4.0-opt)
plus the ComfyUI `RMBG` node for the matte, then composes the finished 256 px icons with PIL.

    py -3 tools/artpipe/gen_gacha_painterly.py gen  <out-dir> [slug ...] [--variants 4] [--seed 5000]
    py -3 tools/artpipe/gen_gacha_painterly.py pick <out-dir> slug=variant ...     → Assets/UI/HUD/Icons/Gen/

Prompts live in CATALOG below (mirrored as subtype_shape lines in art-direction.md, "gacha painterly regen").
Prompt = art-direction prompt_prefix + subject + style_phrase, same order as artpipe prompt.build(short).
"""
import json, sys, time, uuid, urllib.request, urllib.parse
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

NS = Path(__file__).resolve().parents[2]
GEN = NS / "Assets/UI/HUD/Icons/Gen"
# ARTPIPE_KIT = the kit's Tools/artpipe (set by the artpipe workflow, mode=script); else the sibling sanne-kit clone
WORKFLOW = Path(os.environ.get("ARTPIPE_KIT") or NS.parents[1] / "sanne-kit/Tools/artpipe") / "workflows/icon_anime.json"
HOST = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
CKPT = "animagine-xl-4.0-opt.safetensors"

PREFIX = "masterpiece, best quality, solo, no humans, cute chibi anime game icon,"
STYLE = ("soft pastel colours with one saturated accent colour, soft painterly shading, gentle glossy highlight, "
         "thin dark outline, single centered subject, plain white background")
NEGATIVE = ("dark, gloomy, grimdark, horror, magic circle, mandala, halo ring, washed out, desaturated, photograph, "
            "3d render, drop shadow, text, watermark, logo, frame, border, busy background, multiple objects, sticker, "
            "white border, die-cut outline, human, girl, boy, person, hair, realistic, lineart only, monochrome, "
            "sparkles everywhere, sunburst, rays, lowres, bad anatomy, blurry, jpeg artifacts, multiple views, character sheet, "
            "sticker sheet, group, crowd, many characters, duplicate, variations, white outline border")

BOT = "a cute chibi round nanobot robot character, big round head, tiny body, head and shoulders portrait"
CATALOG = {
    # ── 12 Commanders: own face + body + colour + one feature each ──
    "cmd-clamp":   f"{BOT}, honey yellow round body, wearing a miner helmet with a headlamp, cheerful big grin, round sparkly eyes",
    "cmd-spark":   f"{BOT}, orange body, spiky lightning bolt shaped hair tuft, cheeky wink, one eye closed, tongue out",
    "cmd-hook":    f"{BOT}, sky blue body, wearing an orange hard hat, focused determined eyes, holding a tiny wrench",
    "cmd-shell":   f"{BOT}, mint green body, wearing a round turtle shell on its back, sleepy half closed eyes, calm smile",
    "cmd-vega":    f"{BOT}, violet purple body, a sniper scope monocle over one eye, confident smirk, cool",
    "cmd-mira":    f"{BOT}, pink body, a big horseshoe magnet on its head, happy closed eyes smile, blushing",
    "cmd-kite":    f"{BOT}, turquoise teal body, aviator goggles on forehead and a red scarf flowing, excited open mouth",
    "cmd-bastion": f"{BOT}, silver grey body, wearing a small knight helmet with a red plume, shy blushing eyes looking aside",
    "cmd-relay":   f"{BOT}, lemon yellow body, a satellite dish antenna on top and headphones, gentle calm eyes",
    "cmd-orrin":   f"{BOT}, golden yellow body, wearing a golden crown with gems, proud heroic grin, star shaped eye highlights",
    "cmd-nyx":     f"{BOT}, deep lavender purple body, wearing a cozy hood with cat ears, mysterious sly half lidded eyes, small smile",
    "cmd-atlas":   f"{BOT}, rusty orange red chunky body, wearing a viking helmet with two horns, fierce but cute frown, puffed cheeks",
    # ── gachapon balls ──
    "capsule-common": "one round plastic toy ball like a pokeball, top half glossy baby blue dome, bottom half white, thin band in the middle, small cute face with blush on the white half",
    "capsule-rare":   "one round plastic toy ball like a pokeball, top half glossy lavender purple dome, bottom half white, thin band in the middle, small cute face with blush on the white half",
    "capsule-legend": "one round plastic toy ball like a pokeball, top half glossy shiny gold dome, bottom half white, thin band in the middle, small cute face with blush on the white half",
    # ── role badges ──
    "role-harvest": "one small green seedling sprout with two round green leaves in a little brown clay pot",
    "role-build":   "one chunky toy hammer, yellow metal head, brown wooden handle",
    "role-fight":   "one chunky short toy sword, silver blade, red round guard, brown grip",
    "role-support": "one round sky blue shield with a pink heart emblem in the middle",
    # ── currencies / UI ──
    "ui-signal":    "a cute small radio antenna tower with a round glowing honey gold bulb on top and two curved signal waves",
    "ui-stardust":  "a cute little glass jar full of glowing lavender and gold star dust, cork lid",
    "ui-commander": "a cute chibi round mint green nanobot robot wearing a tiny navy captain hat, big shiny eyes, saluting",
    # ── skill icons ──
    "sk-squadcarry":   "a cute little cardboard box overflowing with glowing mint green energy orbs",
    "sk-squaddamage":  "a cute orange fist punching with a small impact star",
    "sk-squadbuild":   "a cute wrench and hammer crossed, sky blue handles",
    "sk-squadhp":      "a cute mint green heart with a white plus sign",
    "sk-squadpierce":  "a cute violet arrow flying through two small targets",
    "sk-pickupmagnet": "one red and silver U shaped horseshoe magnet with small pink orbs flying toward it",
    "sk-squadspeed":   "one teal sneaker shoe with small white wings on the side and speed lines",
    "sk-stillshield":  "a cute round silver dome bubble shield",
    "sk-chargeregen":  "one yellow battery cell with a green charge level and a round refresh arrow around it",
    "sk-pulseemp":     "a cute golden round pulse wave ring bursting from a small orb",
    "sk-convert":      "a cute lavender purple potion flask with a swirl turning a grey blob into a heart",
    "sk-giant":        "a cute big rusty orange robot fist smashing a small rock",
    # ── Signal Station scene (design/ux/commander-summon.md §3.1, §9) — gen with the SAME seed so both stations match ──
    "summon-station":       "a cute chubby lavender purple antenna tower robot, full body, a round cream face screen with big round shiny eyes and pink blush and a small smile, a honey gold glowing bulb on top of a thin mast, three white rings around the mast, stubby little feet",
    "summon-station-happy": "a cute chubby lavender purple antenna tower robot, full body, a round cream face screen with happy closed eyes shaped like upside down U and pink blush and a big smile, a honey gold glowing bulb on top of a thin mast, three white rings around the mast, stubby little feet",
    "summon-cloud-a":       "one fluffy round white cartoon cloud, soft lavender shading underneath",
    "summon-cloud-b":       "one small fluffy white cartoon cloud, wide and flat, soft pink shading underneath",
}


# ── ComfyUI ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def graph(prompt, seed, size=1024):
    g = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    g["1"]["inputs"]["ckpt_name"] = CKPT
    g["2"]["inputs"]["text"] = prompt
    g["3"]["inputs"]["text"] = NEGATIVE
    g["4"]["inputs"]["width"] = size; g["4"]["inputs"]["height"] = size
    g["5"]["inputs"]["seed"] = seed
    g["7"]["inputs"]["filename_prefix"] = "gacha_raw"
    g["8"] = {"class_type": "RMBG", "inputs": {"image": ["6", 0], "model": "RMBG-2.0", "sensitivity": 1.0,
              "process_res": 1024, "mask_blur": 0, "mask_offset": 0, "invert_output": False,
              "refine_foreground": True, "background": "Alpha"}}
    g["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "gacha_alpha"}}
    return g


def call(path, data=None):
    req = urllib.request.Request(HOST + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def run(prompt, seed):
    cid = uuid.uuid4().hex
    pid = json.loads(call("/prompt", {"prompt": graph(prompt, seed), "client_id": cid}))["prompt_id"]
    while True:
        h = json.loads(call(f"/history/{pid}"))
        if pid in h and h[pid].get("outputs"):
            break
        time.sleep(1.0)
    out = {}
    for node, o in h[pid]["outputs"].items():
        for im in o.get("images", []):
            q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"], "type": im["type"]})
            out[node] = call(f"/view?{q}")
    return out["7"], out["9"]


def gen(out_dir, slugs, variants, seed0):
    out_dir.mkdir(parents=True, exist_ok=True)
    for si, slug in enumerate(slugs):
        prompt = f"{PREFIX} {CATALOG[slug]}, {STYLE}"
        for v in range(variants):
            dst = out_dir / f"{slug}__{v}.png"
            if dst.exists():
                continue
            raw, alpha = run(prompt, seed0 + si * 100 + v)
            (out_dir / f"{slug}__{v}_raw.png").write_bytes(raw)
            dst.write_bytes(alpha)
            print(slug, v, flush=True)


# ── composing ────────────────────────────────────────────────────────────────────────────────────────────────────────
def hexcol(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


TINT = {"cmd-clamp": "#E8B84A", "cmd-spark": "#F07A4A", "cmd-hook": "#7AB8E8", "cmd-shell": "#8AD08A",
        "cmd-vega": "#B07AF0", "cmd-mira": "#F0A0D0", "cmd-kite": "#60E0D0", "cmd-bastion": "#A0A0B8",
        "cmd-relay": "#F0E060", "cmd-orrin": "#FFD24A", "cmd-nyx": "#8050C0", "cmd-atlas": "#D06040"}


def trim(im, pad=0.04):
    box = im.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
    if not box:
        return im
    im = im.crop(box)
    return im


def fit(im, size, margin):
    im = trim(im)
    k = (size * (1 - 2 * margin)) / max(im.size)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


def backdrop(size, tint, radius):
    """Soft rounded square, plain vertical gradient (no rays) washed from the Commander's tint."""
    top, bot = mix(tint, (255, 255, 255), 0.72), mix(tint, (255, 246, 236), 0.45)
    grad = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(grad)
    for y in range(size):
        c = mix(top, bot, y / (size - 1)); d.line([(0, y), (size, y)], fill=c + (255,))
    glow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(glow).ellipse((size * .12, size * .08, size * .88, size * .7), fill=90)
    grad.paste(Image.new("RGBA", (size, size), (255, 255, 255, 255)), (0, 0), glow.filter(ImageFilter.GaussianBlur(size * .08)))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0)); out.paste(grad, (0, 0), mask)
    return out, mask


def portrait(src, slug, S=256):
    big = S * 4
    bg, mask = backdrop(big, hexcol(TINT[slug]), int(big * .2))
    ch = fit(src, big, 0.1)                     # whole character inside the frame opening (frame band ≈ 6.5 %)
    x = (big - ch.width) // 2; y = (big - ch.height) // 2 + int(big * .02)
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0)); layer.alpha_composite(ch, (x, y))
    clipped = Image.new("RGBA", (big, big), (0, 0, 0, 0)); clipped.paste(layer, (0, 0), Image.composite(layer.getchannel("A"), Image.new("L", (big, big), 0), mask))
    bg.alpha_composite(clipped)
    return bg.resize((S, S), Image.LANCZOS)


def icon(src, S=256, margin=0.08):
    big = S * 4
    ch = fit(src, big, margin)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.alpha_composite(ch, ((big - ch.width) // 2, (big - ch.height) // 2))
    return out.resize((S, S), Image.LANCZOS)


INK = (74, 58, 82)
RARITY = {"common": ((150, 222, 250), (78, 176, 226)), "rare": ((214, 190, 255), (150, 110, 230)),
          "legend": ((255, 232, 150), (236, 170, 50))}


def vgrad(size, top, bot):
    w, h = size
    g = Image.new("RGBA", size)
    d = ImageDraw.Draw(g)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=mix(top, bot, y / max(1, h - 1)) + (255,))
    return g


def shape(size, draw_fn):
    m = Image.new("L", size, 0); draw_fn(ImageDraw.Draw(m)); return m


def gloss(canvas, box, strength=150, blur=0.04):
    """A soft white highlight blob (the painterly shine the shop icons have)."""
    w, h = canvas.size
    m = shape((w, h), lambda d: d.ellipse(box, fill=strength)).filter(ImageFilter.GaussianBlur(w * blur))
    alpha = Image.composite(m, Image.new("L", (w, h), 0), canvas.getchannel("A").point(lambda a: 255 if a > 200 else 0))
    white = Image.new("RGBA", (w, h), (255, 255, 255, 0)); white.putalpha(alpha)
    canvas.alpha_composite(white)


def frames(S=256):
    """Soft glossy rounded border, transparent centre, same radius as the portrait backdrop (20 %)."""
    big = S * 4; r = int(big * .2); t = int(big * .065)
    for key, (light, deep) in RARITY.items():
        band = shape((big, big), lambda d: (d.rounded_rectangle((0, 0, big - 1, big - 1), r, fill=255),
                                            d.rounded_rectangle((t, t, big - 1 - t, big - 1 - t), r - t, fill=0)))
        ink = shape((big, big), lambda d: (d.rounded_rectangle((0, 0, big - 1, big - 1), r, fill=255),
                                           d.rounded_rectangle((t + 14, t + 14, big - 15 - t, big - 15 - t), r - t - 14, fill=0)))
        out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        out.paste(Image.new("RGBA", (big, big), INK + (255,)), (0, 0), ink)
        inner = shape((big, big), lambda d: (d.rounded_rectangle((12, 12, big - 13, big - 13), r - 12, fill=255),
                                             d.rounded_rectangle((t + 2, t + 2, big - 3 - t, big - 3 - t), r - t - 2, fill=0)))
        g = vgrad((big, big), mix(light, (255, 255, 255), .35), deep)
        out.paste(g, (0, 0), inner)
        gloss(out, (big * .06, big * .005, big * .6, big * .09), 170, .012)
        if key == "legend":                                   # two small cream dots, nothing more
            for cx in (big * .5 - big * .08, big * .5 + big * .08):
                d = ImageDraw.Draw(out); rr = big * .022
                d.ellipse((cx - rr - 8, t / 2 - rr - 8 + 6, cx + rr + 8, t / 2 + rr + 8 + 6), fill=INK + (255,))
                d.ellipse((cx - rr, t / 2 - rr + 6, cx + rr, t / 2 + rr + 6), fill=(255, 246, 236, 255))
        out.resize((S, S), Image.LANCZOS).save(GEN / f"frame-{key}.png")
        print("-> frame", key)


def dossiers(S=256):
    """Folder with the photo slot EXACTLY at (145,325)–(615,795) of 1024 (CommanderScreen.DossierArt lays the face in)."""
    big = 1024
    for key in ("rare", "legend"):
        light, deep = RARITY[key]
        out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(out)
        body = (60, 190, 964, 880); tab = (60, 130, 420, 260)
        for box, rad in ((tab, 60), (body, 90)):
            d.rounded_rectangle((box[0] - 14, box[1] - 14, box[2] + 14, box[3] + 14), rad + 14, fill=INK + (255,))
        m = shape((big, big), lambda dd: (dd.rounded_rectangle(tab, 60, fill=255), dd.rounded_rectangle(body, 90, fill=255)))
        out.paste(vgrad((big, big), mix(light, (255, 255, 255), .45), deep), (0, 0), m)
        gloss(out, (120, 200, 700, 300), 150, .02)
        d = ImageDraw.Draw(out)
        d.rounded_rectangle((131, 311, 629, 809), 70, fill=INK + (255,))
        d.rounded_rectangle((145, 325, 615, 795), 60, fill=(255, 246, 236, 255))
        for i, y in enumerate((380, 470, 560)):                  # three soft text lines
            d.rounded_rectangle((680, y, 900 - i * 40, y + 38), 19, fill=mix(deep, (255, 255, 255), .4) + (255,))
        d.rounded_rectangle((680, 680, 900, 790), 40, fill=INK + (255,))
        d.rounded_rectangle((692, 692, 888, 778), 32, fill=(255, 169, 198, 255))
        try:
            from PIL import ImageFont
            f = ImageFont.truetype(str(NS / "Assets/UI/Fonts/Fredoka-Bold.ttf"), 76)
            d.text((790, 735), "×3", font=f, fill=INK + (255,), anchor="mm")
        except Exception as e:
            print("font", e)
        out.resize((S, S), Image.LANCZOS).save(GEN / f"dossier-{key}.png")
        print("-> dossier", key)


def banner():
    W, H = 1024 * 2, 360 * 2
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = shape((W, H), lambda d: d.rounded_rectangle((0, 0, W - 1, H - 1), 90, fill=255))
    ink = Image.new("RGBA", (W, H), INK + (255,)); out.paste(ink, (0, 0), m)
    m2 = shape((W, H), lambda d: d.rounded_rectangle((16, 16, W - 17, H - 17), 76, fill=255))
    out.paste(vgrad((W, H), (214, 196, 250), (255, 222, 206)), (0, 0), m2)
    clouds = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cd = ImageDraw.Draw(clouds)
    for cx, cy, r in ((180, 640, 150), (360, 690, 120), (1860, 620, 170), (1660, 690, 120), (1020, 720, 160)):
        cd.ellipse((cx - r, cy - r * .7, cx + r, cy + r * .7), fill=(255, 255, 255, 230))
    clouds = clouds.filter(ImageFilter.GaussianBlur(18))
    ca = Image.composite(clouds.getchannel("A"), Image.new("L", (W, H), 0), m2)
    cl = Image.new("RGBA", (W, H), (255, 255, 255, 0)); cl.putalpha(ca); out.alpha_composite(cl)
    for x, y, r in ((300, 150, 12), (1760, 170, 10), (1500, 90, 8)):           # a few soft dots, like the shop icons
        ImageDraw.Draw(out).ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 200))
    fr = Image.open(GEN / "frame-legend.png").convert("RGBA")
    for slug, cx, size in (("cmd-nyx", 610, 470), ("cmd-atlas", 1438, 470), ("cmd-orrin", 1024, 590)):
        p = Image.open(GEN / f"{slug}.png").convert("RGBA").resize((size, size), Image.LANCZOS)
        p.alpha_composite(fr.resize((size, size), Image.LANCZOS))
        sh = shape((W, H), lambda d: d.rounded_rectangle((cx - size / 2 + 10, H / 2 - size / 2 + 26, cx + size / 2 + 10, H / 2 + size / 2 + 26), size * .2, fill=70)).filter(ImageFilter.GaussianBlur(14))
        shl = Image.new("RGBA", (W, H), INK + (0,)); shl.putalpha(sh); out.alpha_composite(shl)
        out.alpha_composite(p, (int(cx - size / 2), int(H / 2 - size / 2)))
    out.resize((1024, 360), Image.LANCZOS).save(GEN / "cmd-pull-banner.png")
    print("-> banner")


def capsules():
    """The model never draws 3 matching gachapon colours, so one picked ball (capsule-legend, gold lid) is the master:
    the lid's saturated gold is hue-shifted to blue / lavender, and it is split at the band into capsule-top (lid,
    desaturated toward white so code can tint it) + capsule-bottom (everything below the band)."""
    import colorsys
    src = Image.open(GEN / "capsule-legend.png").convert("RGBA")
    w, h = src.size
    a = src.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    sp = src.load()
    def dark(y):                                               # the seam is the darkest row in the middle band
        return sum(1 for x in range(a[0], a[2]) if sp[x, y][3] > 200 and sum(sp[x, y][:3]) < 240)
    lo, hi = a[1] + int((a[3] - a[1]) * .4), a[1] + int((a[3] - a[1]) * .7)
    band = max(range(lo, hi), key=dark)

    def recolor(target_h, sat_k):
        px = src.copy(); p = px.load()
        for y in range(h):
            for x in range(w):
                r, g, b, al = p[x, y]
                if not al: continue
                hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if ss > .2 and .04 < hh < .22:               # gold / yellow only; outline + highlights untouched
                    nr, ng, nb = colorsys.hsv_to_rgb(target_h, min(1, ss * sat_k), vv)
                    p[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), al)
        return px
    recolor(0.55, 0.85).save(GEN / "capsule-common.png")
    recolor(0.76, 0.75).save(GEN / "capsule-rare.png")
    top = src.copy(); tp = top.load()
    for y in range(h):
        for x in range(w):
            r, g, b, al = tp[x, y]
            if y > band: tp[x, y] = (0, 0, 0, 0); continue
            if not al: continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if ss > .2 and .04 < hh < .22:                   # lid colour → light grey value map (multiply-tint in code)
                l = int(150 + 105 * vv); tp[x, y] = (l, l, l, al)
    top.save(GEN / "capsule-top.png")
    bot = src.copy(); bp = bot.load()
    for y in range(min(h, band + 1)):
        for x in range(w):
            bp[x, y] = (0, 0, 0, 0)
    bot.save(GEN / "capsule-bottom.png")
    print("-> capsules (common/rare recoloured, top/bottom split at y", band, ")")


def pick(out_dir, pairs):
    for p in pairs:
        slug, v = p.split("=")
        src = Image.open(out_dir / f"{slug}__{v}.png").convert("RGBA")
        im = portrait(src, slug) if slug in TINT else icon(src)
        im.save(GEN / f"{slug}.png")
        print("->", slug)


if __name__ == "__main__":
    cmd, out = sys.argv[1], Path(sys.argv[2])
    rest = sys.argv[3:]
    if cmd == "gen":
        variants, seed = 4, 5000
        if "--variants" in rest: i = rest.index("--variants"); variants = int(rest[i + 1]); del rest[i:i + 2]
        if "--seed" in rest: i = rest.index("--seed"); seed = int(rest[i + 1]); del rest[i:i + 2]
        gen(out, rest or list(CATALOG), variants, seed)
    elif cmd == "pick":
        pick(out, rest)
    elif cmd == "compose":          # frames + dossiers + banner (banner reads the picked Legend portraits)
        frames(); dossiers(); capsules(); banner()
