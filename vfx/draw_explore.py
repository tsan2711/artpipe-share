#!/usr/bin/env python3
"""PIPELINE TEST batch — not art for any game. Stress-tests the drawn-art lane (draw_*.py) with many VFX + character
shapes to find where the pipeline itself is weak. Writes NOTHING into Assets/. Findings: tools/artpipe/explore-findings.md.

    python3 tools/artpipe/draw_explore.py [out-dir]      (default: tools/artpipe/out-explore)
      → vfx_sheet.png  chars_sheet.png  swarm_realsize.png  + per-item PNGs in vfx/ and chars/
"""
import math, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

HERE = Path(__file__).resolve().parent
K, T = 4, 128
C = T * K / 2
INK = (74, 58, 82, 255)
WHITE = (255, 255, 255, 255)
CREAM = (255, 246, 236, 255)
MAP_BG = (246, 230, 212, 255)          # Colony.unity camera clear colour
HUD_BG = (10, 14, 20, 255)
TECH, ENERGY, MATTER, CORE, PINK = (101, 212, 245), (94, 232, 154), (196, 159, 255), (255, 217, 122), (251, 175, 203)
DANGER = (255, 110, 110)
PLAYER = (74, 140, 255)
CIVS = [("veyra", "#9B6BFF"), ("orka", "#FF8A1F"), ("lumi", "#FF5FC8"), ("thalos", "#1FD1B5"), ("zarn", "#A8E22A"),
        ("morra", "#C23BE0"), ("cyra", "#2BC4E0"), ("rust", "#D2692A"), ("vorn", "#7A3FD1"), ("pyre", "#6FBF3A"),
        ("selu", "#FF7A9E"), ("aeon", "#22C47E")]


def hexc(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(c, a=255):
    return (c[0], c[1], c[2], int(max(0, min(255, a))))


def canvas(n=1):
    im = Image.new("RGBA", (T * K * n, T * K), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def done(im, size=T):
    w = size * im.width // im.height
    return im.convert("RGBa").resize((w, size), Image.LANCZOS).convert("RGBA")


def ell(d, x, y, r, fill=None, outline=INK, w=None, ry=None):
    ry = ry or r
    d.ellipse((x - r, y - ry, x + r, y + ry), fill=fill, outline=outline, width=int(w if w is not None else max(K, r * 0.12)))


def starpts(cx, cy, r, inner, n, rot=-math.pi / 2):
    return [(cx + (r if i % 2 == 0 else r * inner) * math.cos(rot + i * math.pi / n),
             cy + (r if i % 2 == 0 else r * inner) * math.sin(rot + i * math.pi / n)) for i in range(n * 2)]


def regular(cx, cy, r, n, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * i / n), cy + r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


def glow(size, color, power=1.6, alpha=1.0):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); px = im.load(); c = (size - 1) / 2
    for y in range(0, size):
        for x in range(0, size):
            r = math.hypot(x - c, y - c) / c
            px[x, y] = rgba(color, 255 * alpha * max(0.0, 1.0 - r) ** power)
    return im


def ease_out(t): return 1 - (1 - t) ** 2


# ══════════════════════════════ VFX candidates (flipbooks unless noted) ══════════════════════════════
def fx_bot_pop(n=6):
    """EnemyBotKilledEvent / EventBotKilledEvent — a bot pops into 3 shards + a tiny ring. Needs to be CHEAP: fires a lot."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - t ** 1.5)
        r = C * (0.2 + 0.55 * ease_out(t))
        ell(d, C, C, r, outline=rgba(INK, a), w=int(C * 0.1 * (1 - t) + K), fill=None)
        ell(d, C, C, r, outline=rgba(WHITE, a), w=int(C * 0.05 * (1 - t) + K / 2), fill=None)
        for k in range(3):
            ang = -math.pi / 2 + k * 2 * math.pi / 3 + t * 0.8
            x, y = C + math.cos(ang) * r * 1.05, C + math.sin(ang) * r * 1.05
            s = C * 0.16 * (1 - t * 0.7)
            d.polygon(regular(x, y, s, 3, ang), fill=rgba(WHITE, a), outline=rgba(INK, a), width=2 * K)
        if i == 0: ell(d, C, C, C * 0.35, fill=WHITE)
        out.append(done(im))
    return out


def fx_hit_flash(n=4):
    """Projectile hit on a bot / core — a hard 4-point flash, gone in 4 frames."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - t)
        r = C * (0.9 - 0.5 * t)
        d.polygon(starpts(C, C, r, 0.22 + 0.2 * t, 4, -math.pi / 2 + t * 0.3), fill=rgba(WHITE, a), outline=rgba(INK, a), width=2 * K)
        out.append(done(im))
    return out


def fx_spawn_warp(n=7):
    """BotSpawnedEvent — vertical beam collapses into a ring (bots appear from the core, not from nothing)."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas()
        beam_w = C * 0.5 * (1 - t) ** 1.5
        if beam_w > K:
            d.rounded_rectangle((C - beam_w, 0, C + beam_w, C * 2), int(beam_w), fill=rgba(TECH, 200 * (1 - t)))
            d.rounded_rectangle((C - beam_w * 0.45, 0, C + beam_w * 0.45, C * 2), int(beam_w * 0.45), fill=rgba(WHITE, 230 * (1 - t)))
        r = C * (0.25 + 0.6 * t)
        ell(d, C, C * 1.35, r, ry=r * 0.35, outline=rgba(INK, 255 * (1 - t)), w=3 * K)
        ell(d, C, C * 1.35, r * 0.96, ry=r * 0.33, outline=rgba(TECH, 255 * (1 - t)), w=2 * K)
        out.append(done(im))
    return out


def fx_node_crumble(n=7):
    """NodeDepletedEvent / NodeRemovedEvent — rock chunks fall + dust puff."""
    out = []; rnd = random.Random(3)
    chunks = [(rnd.uniform(-.5, .5), rnd.uniform(-.4, .1), rnd.uniform(.12, .22), rnd.uniform(0, 6)) for _ in range(6)]
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - t ** 2)
        for dx, dy, s, rot in chunks:
            x = C + dx * C * (1 + t * 0.6); y = C + dy * C + t * t * C * 0.9
            d.polygon(regular(x, y, s * C, 5, rot + t * 3), fill=rgba((196, 170, 190), a), outline=rgba(INK, a), width=2 * K)
        for k in range(3):                                          # dust
            x = C + (k - 1) * C * 0.45; r = C * (0.1 + 0.25 * t)
            ell(d, x, C * 1.55, r, fill=rgba(CREAM, a * 0.8), outline=rgba(INK, a * 0.6), w=2 * K)
        out.append(done(im))
    return out


def fx_meteor_impact(n=8):
    """Active Event MeteorShower — shockwave + debris + scorch. (Only the falling meteor sprite exists today.)"""
    out = []; rnd = random.Random(7)
    debris = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(.5, 1)) for _ in range(9)]
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - t ** 1.3)
        ell(d, C, C * 1.1, C * 0.55, ry=C * 0.22, fill=rgba((110, 90, 100), 120 * (1 - t * 0.5)), outline=None, w=0)   # scorch
        r = C * (0.2 + 0.75 * ease_out(t))
        ell(d, C, C * 1.1, r, ry=r * 0.42, outline=rgba(INK, a), w=int(C * 0.1 * (1 - t)) + K)
        ell(d, C, C * 1.1, r, ry=r * 0.42, outline=rgba(CORE, a), w=int(C * 0.06 * (1 - t)) + K)
        if t < 0.4:
            g = glow(T * K, (255, 240, 200), 1.4, 1 - t / 0.4); im.alpha_composite(g)
        for ang, sp in debris:
            dist = C * sp * ease_out(t) * 0.85
            x = C + math.cos(ang) * dist; y = C * 1.1 + math.sin(ang) * dist * 0.5 - C * 0.6 * math.sin(t * math.pi) * sp
            ell(d, x, y, C * 0.06 * (1 - t * 0.5), fill=rgba(PINK if sp > .75 else CORE, a), outline=rgba(INK, a), w=K * 2)
        out.append(done(im))
    return out


def fx_core_explode(n=9):
    """CivDefeatedEvent — the big one: flash → fireball puffs → ring → confetti-ish shards. Biggest reward moment."""
    out = []; rnd = random.Random(11)
    puffs = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(.3, .7), rnd.uniform(.2, .32)) for _ in range(7)]
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - max(0, t - 0.3) / 0.7)
        if t < 0.25: im.alpha_composite(glow(T * K, WHITE, 1.2, 1 - t / 0.25))
        r = C * (0.2 + 0.78 * ease_out(t))
        ell(d, C, C, r, outline=rgba(INK, a), w=int(C * 0.09 * (1 - t)) + K)
        ell(d, C, C, r, outline=rgba(WHITE, a), w=int(C * 0.05 * (1 - t)) + K)
        for ang, dist, s in puffs:
            x = C + math.cos(ang) * C * dist * ease_out(t); y = C + math.sin(ang) * C * dist * ease_out(t) - t * C * 0.2
            rr = C * s * (0.5 + 0.8 * t) * (1 - t * 0.4)
            ell(d, x, y, rr + 3 * K, fill=rgba(INK, a), outline=None, w=0)
        for ang, dist, s in puffs:
            x = C + math.cos(ang) * C * dist * ease_out(t); y = C + math.sin(ang) * C * dist * ease_out(t) - t * C * 0.2
            rr = C * s * (0.5 + 0.8 * t) * (1 - t * 0.4)
            col = CORE if t < 0.3 else (PINK if t < 0.6 else (200, 190, 200))
            ell(d, x, y, rr, fill=rgba(col, a), outline=None, w=0)
        out.append(done(im))
    return out


def fx_wave_warning(n=6):
    """WaveSpawnedEvent / RaidRequestedEvent — a red chevron pulse at the map edge where the wave enters (loops)."""
    out = []
    for i in range(n):
        t = i / n; im, d = canvas()
        for k in range(3):
            p = (t + k / 3) % 1
            y = C * 1.7 - p * C * 1.4; a = 255 * math.sin(p * math.pi)
            w = C * 0.55
            pts = [(C - w, y + w * 0.5), (C, y), (C + w, y + w * 0.5), (C + w, y + w * 0.5 + C * 0.18), (C, y + C * 0.18), (C - w, y + w * 0.5 + C * 0.18)]
            d.polygon(pts, fill=rgba(DANGER, a), outline=rgba(INK, a), width=2 * K)
        out.append(done(im))
    return out


def fx_core_hit(n=5):
    """RivalAttackedCoreEvent / CoreHpChangedEvent (down) — crack lines + red flash on the player core."""
    out = []
    cracks = [[(0, 0), (.25, -.1), (.4, -.35), (.62, -.4)], [(0, 0), (-.2, .2), (-.28, .5)], [(0, 0), (-.3, -.2), (-.55, -.18)]]
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - t)
        ell(d, C, C, C * 0.8, outline=rgba(DANGER, a * 0.9), w=int(C * 0.14 * (1 - t)) + K)
        for cr in cracks:
            pts = [(C + x * C * (0.6 + 0.4 * t), C + y * C * (0.6 + 0.4 * t)) for x, y in cr]
            d.line(pts, fill=rgba(INK, a), width=5 * K, joint="curve"); d.line(pts, fill=rgba(WHITE, a), width=2 * K)
        out.append(done(im))
    return out


def fx_rally_beacon(n=8):
    """RallyStartedEvent — a flag-pin with two expanding ground rings (loops while rally is live)."""
    out = []
    for i in range(n):
        t = i / n; im, d = canvas()
        for k in range(2):
            p = (t + k * 0.5) % 1; r = C * (0.2 + 0.7 * p)
            ell(d, C, C * 1.5, r, ry=r * 0.35, outline=rgba(CORE, 255 * (1 - p)), w=3 * K)
        bob = math.sin(t * 2 * math.pi) * C * 0.06
        d.line([(C, C * 1.5), (C, C * 0.45 + bob)], fill=INK, width=6 * K)
        d.polygon([(C, C * 0.4 + bob), (C + C * 0.55, C * 0.6 + bob), (C, C * 0.82 + bob)], fill=rgba(CORE), outline=INK, width=3 * K)
        out.append(done(im))
    return out


def fx_magnet_pull():
    """SkillUsedEvent(Magnet) — curved inward streaks (single tile, rotate + tint in the ParticleSystem)."""
    im, d = canvas()
    for k in range(6):
        a0 = k * math.pi / 3
        pts = [(C + math.cos(a0 + s * 0.5) * C * (0.95 - s * 0.6), C + math.sin(a0 + s * 0.5) * C * (0.95 - s * 0.6)) for s in [j / 10 for j in range(11)]]
        d.line(pts, fill=INK, width=7 * K, joint="curve"); d.line(pts, fill=WHITE, width=3 * K, joint="curve")
    return [done(im)]


def fx_surge_lines():
    """SkillUsedEvent(SwarmSurge) — speed streak tile, stretched along velocity on each bot."""
    im, d = canvas()
    for k, (y, ln) in enumerate(((0.7, 1.4), (1.0, 1.8), (1.3, 1.2))):
        d.rounded_rectangle((C * (2 - ln), C * y - 3 * K, C * 1.9, C * y + 3 * K), 3 * K, fill=WHITE, outline=INK, width=2 * K)
    return [done(im)]


def fx_replicate(n=6):
    """NanoReplicationProcEvent — a bot splits in two (cell division)."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); off = C * 0.38 * ease_out(t); r = C * (0.42 - 0.08 * t)
        for sx in (-1, 1):
            ell(d, C + sx * off, C, r, fill=rgba(WHITE), w=3 * K)
        if 0.2 < t < 0.9:
            d.polygon(starpts(C, C - r * 1.1, C * 0.18, 0.4, 4), fill=rgba(CORE), outline=INK, width=2 * K)
        out.append(done(im))
    return out


def fx_prestige_nova(n=10):
    """PrestigeCompletedEvent — full-screen rainbow ring + rays. The rarest, biggest moment in the game."""
    out = []; cols = [PINK, CORE, ENERGY, TECH, MATTER]
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = 255 * (1 - t ** 2)
        for k, col in enumerate(cols):
            r = C * (0.1 + 0.9 * ease_out(max(0, t - k * 0.05)))
            ell(d, C, C, r, outline=rgba(col, a), w=int(C * 0.07) )
        for k in range(12):
            ang = k * math.pi / 6 + t * 0.5; l = C * (0.3 + 0.6 * ease_out(t))
            d.line([(C, C), (C + math.cos(ang) * l, C + math.sin(ang) * l)], fill=rgba(WHITE, a * 0.8), width=3 * K)
        d.polygon(starpts(C, C, C * 0.3 * (1 - t * 0.6), 0.4, 4), fill=rgba(WHITE, a), outline=rgba(INK, a), width=2 * K)
        out.append(done(im))
    return out


def fx_zap_chain():
    """EMP / defender attack — jagged bolt tile (stretched between two points)."""
    im, d = canvas(); rnd = random.Random(5)
    pts = [(C * 0.1, C)] + [(C * (0.1 + 1.8 * j / 7), C + rnd.uniform(-.35, .35) * C) for j in range(1, 7)] + [(C * 1.9, C)]
    d.line(pts, fill=INK, width=12 * K, joint="curve"); d.line(pts, fill=rgba(TECH), width=7 * K); d.line(pts, fill=WHITE, width=3 * K)
    return [done(im)]


def fx_shield_hex(n=6):
    """CoreShield upgrade / core under attack — a hex-cell bubble that flashes the hit side."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas()
        ell(d, C, C, C * 0.9, fill=rgba(TECH, 50), outline=rgba(TECH, 220), w=3 * K)
        for q in range(-3, 4):
            for r in range(-3, 4):
                x = C + (q + r * 0.5) * C * 0.28; y = C + r * C * 0.245
                if math.hypot(x - C, y - C) < C * 0.8:
                    hit = max(0, 1 - math.hypot(x - C * 1.5, y - C * 0.6) / (C * 0.9)) * (1 - t)
                    d.polygon(regular(x, y, C * 0.13, 6, math.pi / 6), outline=rgba(WHITE, 60 + 190 * hit), width=K * 2,
                              fill=rgba(TECH, 200 * hit))
        out.append(done(im))
    return out


def fx_anomaly_rift(n=8):
    """Active Event Anomaly — rift opening (the anomaly sprite exists; it has no open/close)."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); open_ = math.sin(t * math.pi)
        w = C * 0.15 + C * 0.2 * open_; h = C * 0.85 * (0.2 + 0.8 * open_)
        ell(d, C, C, w + C * 0.15, ry=h + C * 0.1, fill=rgba(MATTER, 90), outline=None, w=0)
        ell(d, C, C, w, ry=h, fill=rgba((60, 30, 110)), outline=INK, w=4 * K)
        for k in range(5):
            ang = k * 2 * math.pi / 5 + t * 4
            x = C + math.cos(ang) * (w + C * 0.3); y = C + math.sin(ang) * (h * 0.8)
            d.polygon(starpts(x, y, C * 0.1 * open_ + K, 0.4, 4), fill=rgba(MATTER), outline=INK, width=K * 2)
        out.append(done(im))
    return out


def fx_golden_glint(n=6):
    """GoldenNode event — sweeping glint across a node (overlay on the node sprite)."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); x = C * (-0.4 + 2.8 * t)
        d.polygon([(x - C * 0.25, C * 1.9), (x + C * 0.05, C * 1.9), (x + C * 0.45, C * 0.1), (x + C * 0.15, C * 0.1)], fill=rgba(WHITE, 200))
        d.polygon(starpts(C * 1.5, C * 0.5, C * 0.25 * math.sin(t * math.pi) + K, 0.35, 4), fill=rgba(CORE), outline=INK, width=K * 2)
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).ellipse((C * 0.2, C * 0.2, C * 1.8, C * 1.8), fill=255)
        im.putalpha(ImageChops.multiply(im.getchannel("A"), m))
        out.append(done(im))
    return out


def fx_harvest_beam():
    """NodeHarvestedEvent — thin mining beam tile (harvester → node). Fires constantly → must be subtle."""
    im, d = canvas()
    for k, a in ((0, 255), (1, 140)):
        y = C + (k - 0.5) * C * 0.3
        pts = [(C * 0.1 + j * C * 0.12, y + math.sin(j * 1.3) * C * 0.08) for j in range(16)]
        d.line(pts, fill=rgba(ENERGY, a), width=4 * K, joint="curve")
    for x in (0.4, 1.0, 1.6):
        ell(d, C * x, C, C * 0.07, fill=rgba(WHITE), w=K * 2)
    return [done(im)]


def fx_levelup(n=7):
    """UpgradeUnlockedEvent / BotTypeUnlockedEvent on the map — rising chevrons over the core."""
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas()
        for k in range(3):
            p = min(1, max(0, t * 1.4 - k * 0.2)); y = C * 1.6 - p * C * 1.2; a = 255 * math.sin(p * math.pi)
            w = C * 0.4
            d.polygon([(C - w, y + w * 0.6), (C, y), (C + w, y + w * 0.6), (C + w, y + w * 0.6 + C * .16), (C, y + C * .16), (C - w, y + w * 0.6 + C * .16)],
                      fill=rgba(ENERGY, a), outline=rgba(INK, a), width=2 * K)
        out.append(done(im))
    return out


VFX = [
    ("bot_pop", fx_bot_pop, "EnemyBotKilled / EventBotKilled"),
    ("hit_flash", fx_hit_flash, "projectile hit"),
    ("spawn_warp", fx_spawn_warp, "BotSpawned"),
    ("node_crumble", fx_node_crumble, "NodeDepleted / NodeRemoved"),
    ("meteor_impact", fx_meteor_impact, "MeteorShower"),
    ("core_explode", fx_core_explode, "CivDefeated"),
    ("wave_warning", fx_wave_warning, "WaveSpawned / Raid"),
    ("core_hit", fx_core_hit, "RivalAttackedCore"),
    ("rally_beacon", fx_rally_beacon, "RallyStarted"),
    ("magnet_pull", fx_magnet_pull, "Skill Magnet"),
    ("surge_lines", fx_surge_lines, "Skill SwarmSurge"),
    ("replicate", fx_replicate, "NanoReplicationProc"),
    ("prestige_nova", fx_prestige_nova, "PrestigeCompleted"),
    ("zap_chain", fx_zap_chain, "EMP / defender shot"),
    ("shield_hex", fx_shield_hex, "CoreShield hit"),
    ("anomaly_rift", fx_anomaly_rift, "Anomaly open/close"),
    ("golden_glint", fx_golden_glint, "GoldenNode"),
    ("harvest_beam", fx_harvest_beam, "NodeHarvested"),
    ("levelup", fx_levelup, "UpgradeUnlocked"),
]


# ══════════════════════════════ characters (greyscale → tinted like BotInstanced.shader) ══════════════════════════════
S = 512
BINK, RIM, BODY, BCORE = (64, 58, 66, 255), (196, 196, 196, 255), (238, 238, 238, 255), (255, 255, 255, 255)
BW = 30


def layered(shape_fn):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for scale, col in ((1.0, BINK), (1.0 - BW / 230, RIM), (0.74, BODY), (0.36, BCORE)):
        shape_fn(d, scale, col)
    return im, d


def ch_harvester():
    c = S / 2
    im, d = layered(lambda d, k, col: d.ellipse((c - 230 * k, c - 230 * k, c + 230 * k, c + 230 * k), fill=col))
    for x, y in regular(c, c, 150, 6, -math.pi / 2): d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=BCORE)
    return im


def ch_builder():
    c = S / 2
    im, d = layered(lambda d, k, col: d.polygon(regular(c, c, 238 * k, 6, math.pi / 6), fill=col))
    d.polygon(regular(c, c, 44, 6, math.pi / 6), fill=RIM); return im


def ch_defender():
    c = S / 2
    im, d = layered(lambda d, k, col: d.rounded_rectangle((c - 236 * k * .72, c - 236 * k * .72, c + 236 * k * .72, c + 236 * k * .72), 236 * k * .22, fill=col))
    im = im.rotate(45, resample=Image.BICUBIC); d = ImageDraw.Draw(im)
    d.ellipse((c - 70, c - 70, c + 70, c + 70), outline=RIM, width=18); return im


def ch_rival():
    c = S / 2
    im, d = layered(lambda d, k, col: d.polygon(starpts(c, c, 244 * k, 150 / 244, 8), fill=col))
    d.ellipse((c - 40, c - 40, c + 40, c + 40), fill=BINK); return im


# — new candidate roles —
def ch_scout():
    """Fast explorer — triangle-in-circle (3-fold symmetric, still no facing)."""
    c = S / 2
    im, d = layered(lambda d, k, col: d.polygon(regular(c, c, 240 * k, 3, -math.pi / 2), fill=col) if k > 0.5 else d.ellipse((c - 90 * k / .74, c - 90 * k / .74, c + 90 * k / .74, c + 90 * k / .74), fill=col))
    return im


def ch_carrier():
    """Hauler — ring with a hollow cargo centre."""
    c = S / 2
    im, d = layered(lambda d, k, col: d.rounded_rectangle((c - 230 * k, c - 230 * k, c + 230 * k, c + 230 * k), 90 * k, fill=col))
    d.rounded_rectangle((c - 90, c - 90, c + 90, c + 90), 24, fill=RIM, outline=BINK, width=14)
    d.line([(c - 90, c), (c + 90, c)], fill=BINK, width=14); d.line([(c, c - 90), (c, c + 90)], fill=BINK, width=14)
    return im


def ch_medic():
    """Repair bot — rounded plus/cross."""
    c = S / 2
    def f(d, k, col):
        a, b = 230 * k, 90 * k
        d.rounded_rectangle((c - a, c - b, c + a, c + b), b * 0.7, fill=col); d.rounded_rectangle((c - b, c - a, c + b, c + a), b * 0.7, fill=col)
    return layered(f)[0]


def ch_bomber():
    """Kamikaze — circle with 4 short fuse spikes."""
    c = S / 2
    def f(d, k, col):
        d.ellipse((c - 200 * k, c - 200 * k, c + 200 * k, c + 200 * k), fill=col)
        for x, y in regular(c, c, 205 * k, 4, math.pi / 4): d.ellipse((x - 48 * k, y - 48 * k, x + 48 * k, y + 48 * k), fill=col)
    im, d = layered(f); d.ellipse((c - 50, c - 50, c + 50, c + 50), fill=(255, 120, 120, 255)); return im


def ch_elite_rival():
    """Elite / wave leader — double star with a crown ring (reads 'dangerous, bigger')."""
    c = S / 2
    def f(d, k, col):
        d.polygon([(c + (250 * k if i % 2 == 0 else 190 * k) * math.cos(-math.pi / 2 + math.pi * i / 12),
                    c + (250 * k if i % 2 == 0 else 190 * k) * math.sin(-math.pi / 2 + math.pi * i / 12)) for i in range(24)], fill=col)
    im, d = layered(f); d.ellipse((c - 80, c - 80, c + 80, c + 80), fill=BINK); d.ellipse((c - 36, c - 36, c + 36, c + 36), fill=(255, 110, 110, 255))
    return im


def ch_raid_bot():
    """Raid event bot (EventBotTag.Raid) — rival star + red slash band so it differs from a civ rival."""
    im = ch_rival(); d = ImageDraw.Draw(im); c = S / 2
    d.ellipse((c - 150, c - 150, c + 150, c + 150), outline=(255, 110, 110, 255), width=26); return im


def ch_anomaly_bot():
    """Anomaly event bot (EventBotTag.Anomaly) — wobbly blob with void core."""
    c = S / 2
    def f(d, k, col):
        pts = [(c + (220 + 22 * math.sin(i * 5 * 2 * math.pi / 60)) * k * math.cos(i * 2 * math.pi / 60),
                c + (220 + 22 * math.sin(i * 5 * 2 * math.pi / 60)) * k * math.sin(i * 2 * math.pi / 60)) for i in range(60)]
        d.polygon(pts, fill=col)
    im, d = layered(f); d.ellipse((c - 70, c - 70, c + 70, c + 70), fill=(60, 30, 110, 255)); return im


def civ_core(color, seed):
    """Civ Core — civ_roster.csv core_sprite is EMPTY for all 12 civs. One base, 12 crown variants by seed."""
    c = S / 2; rnd = random.Random(seed); n = [5, 6, 7, 8][seed % 4]; spike = [0.0, 0.18, 0.3][seed % 3]
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = rgba(hexc(color)); dark = rgba(tuple(int(v * 0.62) for v in hexc(color)))
    outer = [(c + (240 if i % 2 == 0 else 240 * (1 - spike)) * math.cos(-math.pi / 2 + math.pi * i / n),
              c + (240 if i % 2 == 0 else 240 * (1 - spike)) * math.sin(-math.pi / 2 + math.pi * i / n)) for i in range(n * 2)]
    d.polygon(outer, fill=dark, outline=INK, width=24)
    d.polygon(regular(c, c, 165, n, -math.pi / 2), fill=col, outline=INK, width=20)
    d.ellipse((c - 70, c - 70, c + 70, c + 70), fill=(255, 250, 240, 255), outline=INK, width=18)
    d.ellipse((c - 30, c - 50, c + 5, c - 20), fill=(255, 255, 255, 200))
    return im


def mothership():
    """Boss-sized rival carrier — candidate for late civ tiers / Raid finale."""
    c = S / 2
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon(regular(c, c, 250, 8, math.pi / 8), fill=BINK)
    d.polygon(regular(c, c, 222, 8, math.pi / 8), fill=RIM)
    for x, y in regular(c, c, 160, 8, 0): d.ellipse((x - 34, y - 34, x + 34, y + 34), fill=BODY, outline=BINK, width=10)
    d.ellipse((c - 95, c - 95, c + 95, c + 95), fill=BODY, outline=BINK, width=16)
    d.ellipse((c - 45, c - 45, c + 45, c + 45), fill=(255, 110, 110, 255), outline=BINK, width=12)
    return im


def tint(im, color):
    """BotInstanced.shader: sprite.rgb × tint. Ink stays dark, white body takes the colour."""
    r, g, b, a = im.split()
    tr = r.point(lambda v: v * color[0] // 255); tg = g.point(lambda v: v * color[1] // 255); tb = b.point(lambda v: v * color[2] // 255)
    return Image.merge("RGBA", (tr, tg, tb, a))


def to128(im): return im.resize((T, T), Image.LANCZOS)


CHARS = [("harvester*", ch_harvester), ("builder*", ch_builder), ("defender*", ch_defender), ("rival*", ch_rival),
         ("scout", ch_scout), ("carrier", ch_carrier), ("medic", ch_medic), ("bomber", ch_bomber),
         ("elite_rival", ch_elite_rival), ("raid_bot", ch_raid_bot), ("anomaly_bot", ch_anomaly_bot), ("mothership", mothership)]


# ══════════════════════════════ sheets ══════════════════════════════
def label(d, x, y, text, col=INK):
    d.text((x, y), text, fill=col)


def vfx_sheet(out):
    rows = [(name, fn(), note) for name, fn, note in VFX]
    maxf = max(len(f) for _, f, _ in rows); cell = 100; lw = 170
    sheet = Image.new("RGBA", (lw + maxf * cell * 2 + 20, len(rows) * cell + 30), (255, 255, 255, 255)); d = ImageDraw.Draw(sheet)
    label(d, 8, 8, "VFX candidates — left block: cream map bg · right block: dark HUD bg (flipbook frames L→R)")
    for r, (name, frames, note) in enumerate(rows):
        y = 30 + r * cell
        label(d, 8, y + 30, name); label(d, 8, y + 46, note, (120, 110, 120))
        for blk, bg in enumerate((MAP_BG, HUD_BG)):
            for i, f in enumerate(frames):
                x = lw + blk * (maxf * cell + 10) + i * cell
                sheet.paste(bg, (x, y, x + cell - 4, y + cell - 4))
                sheet.alpha_composite(f.resize((cell - 8, cell - 8), Image.LANCZOS), (x + 2, y + 2))
        (out / "vfx").mkdir(exist_ok=True)
        strip = Image.new("RGBA", (T * len(frames), T), (0, 0, 0, 0))
        for i, f in enumerate(frames): strip.alpha_composite(f, (i * T, 0))
        strip.save(out / "vfx" / f"{name}.png")
    sheet.save(out / "vfx_sheet.png")
    return len(rows), sum(len(f) for _, f, _ in rows)


def chars_sheet(out):
    (out / "chars").mkdir(exist_ok=True)
    teams = [("player", PLAYER)] + [(n, hexc(h)) for n, h in CIVS[:5]]
    cell = 96; lw = 110
    sheet = Image.new("RGBA", (lw + (len(teams) + 3) * cell, 30 + (len(CHARS) + 4) * cell), (255, 255, 255, 255)); d = ImageDraw.Draw(sheet)
    label(d, 8, 8, "Bots (* = shipping today) tinted by team · last 3 cols = 24/16/11 px on the map")
    for i, (n, _) in enumerate(teams): label(d, lw + i * cell + 4, 20, n)
    for r, (name, fn) in enumerate(CHARS):
        src = to128(fn()); src.save(out / "chars" / f"{name.strip('*')}.png"); y = 34 + r * cell
        label(d, 8, y + 40, name)
        for i, (_, col) in enumerate(teams):
            x = lw + i * cell; sheet.paste(MAP_BG, (x, y, x + cell - 4, y + cell - 4))
            sheet.alpha_composite(tint(src, col).resize((cell - 12, cell - 12), Image.LANCZOS), (x + 4, y + 4))
        for j, px in enumerate((24, 16, 11)):
            x = lw + (len(teams) + j) * cell; sheet.paste(MAP_BG, (x, y, x + cell - 4, y + cell - 4))
            sm = tint(src, PLAYER).resize((px, px), Image.LANCZOS)
            sheet.alpha_composite(sm.resize((px * 3, px * 3), Image.NEAREST), (x + (cell - 4 - px * 3) // 2, y + (cell - 4 - px * 3) // 2))
    # civ cores: 12 in a strip
    y0 = 34 + len(CHARS) * cell + 10; label(d, 8, y0, "Civ Cores (core_sprite is empty in civ_roster.csv for all 12)")
    for i, (n, h) in enumerate(CIVS):
        im = to128(civ_core(h, i)); im.save(out / "chars" / f"core_{n}.png")
        x = 8 + (i % 6) * (cell + 40); y = y0 + 16 + (i // 6) * (cell + 16)
        sheet.paste(MAP_BG, (x, y, x + cell, y + cell)); sheet.alpha_composite(im.resize((cell - 8, cell - 8), Image.LANCZOS), (x + 4, y + 4))
        label(d, x, y + cell, n)
    sheet.save(out / "chars_sheet.png")


def swarm_mock(out):
    """Real-size battle: player swarm (blue) vs 2 civs meeting at a node. Bots at 22–26 px, cores 72 px, fx on top."""
    W_, H_ = 900, 520; rnd = random.Random(1)
    im = Image.new("RGBA", (W_, H_), MAP_BG)
    def put(sprite, x, y, px):
        s = sprite.resize((px, px), Image.LANCZOS); im.alpha_composite(s, (int(x - px / 2), int(y - px / 2)))
    shapes = {n.strip("*"): to128(fn()) for n, fn in CHARS}
    put(to128(civ_core("#4A8CFF", 1)), 130, 260, 90); put(to128(civ_core(CIVS[1][1], 1)), 780, 140, 80); put(to128(civ_core(CIVS[0][1], 0)), 760, 400, 80)
    for side, (cx, cy, col, kinds) in enumerate(((330, 260, PLAYER, ["harvester", "builder", "defender", "defender"]),
                                                  (600, 190, hexc(CIVS[1][1]), ["rival", "rival", "elite_rival"]),
                                                  (590, 350, hexc(CIVS[0][1]), ["rival", "bomber", "rival"]))):
        for _ in range(60):
            k = rnd.choice(kinds); x = cx + rnd.gauss(0, 55); y = cy + rnd.gauss(0, 45)
            put(tint(shapes[k], col), x, y, 26 if k == "elite_rival" else 20)
    vf = dict((n, fn()) for n, fn, _ in VFX)
    for n, x, y, px, fi in (("bot_pop", 470, 230, 48, 2), ("bot_pop", 500, 300, 48, 3), ("hit_flash", 455, 270, 36, 0),
                            ("zap_chain", 430, 250, 80, 0), ("core_hit", 130, 260, 110, 1), ("meteor_impact", 300, 420, 110, 3),
                            ("spawn_warp", 180, 300, 60, 2)):
        put(vf[n][fi], x, y, px)
    im.save(out / "swarm_realsize.png")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out-explore"
    out.mkdir(parents=True, exist_ok=True)
    n, frames = vfx_sheet(out); chars_sheet(out); swarm_mock(out)
    print(f"{n} VFX ({frames} frames) + {len(CHARS)} bots + {len(CIVS)} civ cores → {out}")
