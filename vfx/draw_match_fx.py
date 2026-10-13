#!/usr/bin/env python3
"""Match map VFX for Commander v2 + Match Frontline v6, drawn (artpipe-vfx lane) in the cute pastel style:
soft puffs, round stars, confetti, gentle rings — no bolts, no shards, no dark flashes.

    py -3 tools/artpipe/draw_match_fx.py [review-out]
      → Assets/Sprites/Fx/match_fx_atlas.png      8×8 grid of 128 px cells (MatchFxView slices it — keep LAYOUT in sync)
      → Assets/UI/HUD/Icons/Fx/fx-cmd-ready-<i>.png  UI loop for the Commander skill button (MatchHandHud.Skill)
    py -3 tools/artpipe/vfx_preview.py draw_match_fx <out>   → moving previews (GIF)

Tintable cells are WHITE fill + ink outline (the SpriteRenderer colour tints the fill); cells with their own colours
(gold halo, biscuit crumbs, level-up) are drawn in colour and played with a white tint.
"""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from draw_vfx_sprites import canvas, done, rgba, glow, haloed, T, K, INK, WHITE, CREAM, CORE, PINK  # noqa: E402

NS = Path(__import__("os").environ.get("VFX_OUT") or HERE / "out")  # gốc NanoSwarm → thư mục ra (repo chia sẻ)
ATLAS = NS / "Assets/Sprites/Fx/match_fx_atlas.png"
UI_OUT = NS / "Assets/UI/HUD/Icons/Fx"
C = T * K / 2
GOLD = (255, 205, 92)
BISCUIT, BISCUIT_D, BISCUIT_L = (232, 184, 120), (196, 140, 78), (250, 222, 170)


def ease_out(t): return 1 - (1 - t) ** 2
def ease_back(t, s=1.7): t -= 1; return t * t * ((s + 1) * t + s) + 1


def ell(d, x, y, r, fill=None, outline=INK, w=None, ry=None):
    ry = r if ry is None else ry
    if r <= 0.5 or ry <= 0.5: return
    d.ellipse((x - r, y - ry, x + r, y + ry), fill=fill, outline=outline, width=int(w if w is not None else 2.5 * K))


def star5(d, cx, cy, r, fill, a=255, inner=0.5, rot=-math.pi / 2, ow=None):
    """A chubby 5-point star (rounded by drawing a soft fat outline under it)."""
    pts = []
    for i in range(10):
        ang = rot + i * math.pi / 5
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=rgba(fill, a), outline=rgba(INK, a), width=int(ow or max(2 * K, r * 0.16)))


def puff_blobs(d, cx, cy, s, a=255, fill=WHITE, out=True):
    """A small cloud: 5 overlapping round blobs, ink pass then fill pass (like draw_vfx_sprites.tile_puff)."""
    blobs = [(0.0, 0.12, 0.46), (-0.38, 0.2, 0.34), (0.38, 0.22, 0.34), (-0.18, -0.2, 0.36), (0.22, -0.18, 0.34)]
    if out:
        for dx, dy, r in blobs:
            ell(d, cx + dx * s, cy + dy * s, r * s + 0.09 * s, fill=rgba(INK, a), outline=None)
    for dx, dy, r in blobs:
        ell(d, cx + dx * s, cy + dy * s, r * s, fill=rgba(fill, a), outline=None)
    ell(d, cx - 0.28 * s, cy - 0.28 * s, 0.12 * s, fill=(255, 255, 255, int(a * 0.9)), outline=None, ry=0.08 * s)


def soft_glow(im, color, alpha, power=1.8, scale=1.0):
    g = glow(int(T * K * scale), color, power)
    g.putalpha(g.getchannel("A").point(lambda v: int(v * alpha)))
    o = int((T * K - g.size[0]) / 2)
    im.alpha_composite(g, (max(0, o), max(0, o)))


# ── skill cast: a gold halo — glow bloom, a ring that opens, round stars riding it out ─────────────────
def fx_skill_halo(n=8):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = int(255 * (1 - t ** 1.6))
        soft_glow(im, GOLD, 0.75 * (1 - t) ** 1.4, 1.6)
        r = (0.28 + 0.62 * ease_out(t)) * C
        w = (0.16 - 0.10 * t) * C
        ell(d, C, C, r + w / 2, outline=rgba(INK, a), w=w + 2.5 * K)
        ell(d, C, C, r + w / 2, outline=rgba(GOLD, a), w=w)
        ell(d, C, C, r - w * 0.1, outline=rgba(CREAM, a), w=w * 0.35)
        for k in range(8):
            ang = k * math.pi / 4 + t * 0.6
            sr = C * (0.11 if k % 2 == 0 else 0.07) * (1 - 0.5 * t)
            star5(d, C + math.cos(ang) * (r + w), C + math.sin(ang) * (r + w), sr, CREAM if k % 2 else GOLD, a)
        out.append(done(im))
    return out


# ── hero strike: a tiny soft pop (round puff ring + twinkle), cheap — fires per kill ───────────────────
def fx_hero_spark(n=5):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = int(255 * (1 - t ** 1.3))
        soft_glow(im, WHITE, 0.8 * (1 - t), 2.0, 0.8)
        r = (0.22 + 0.5 * ease_out(t)) * C
        ell(d, C, C, r, outline=rgba(INK, a), w=(0.16 - 0.1 * t) * C + 2 * K)
        ell(d, C, C, r, outline=rgba(WHITE, a), w=(0.16 - 0.1 * t) * C)
        tw = C * (0.42 * (1 - t) + 0.1)
        pts = []
        for k in range(8):                                     # 4-point twinkle with round-ish shoulders
            ang = -math.pi / 2 + k * math.pi / 4
            rr = tw if k % 2 == 0 else tw * 0.55        # chubby, not a shard
            pts.append((C + rr * math.cos(ang), C + rr * math.sin(ang)))
        d.polygon(pts, fill=rgba(WHITE, a), outline=rgba(INK, a), width=int(2.5 * K))
        for k in range(4):                                     # 4 dots fly out
            ang = math.pi / 4 + k * math.pi / 2
            rr = (0.3 + 0.55 * ease_out(t)) * C
            ell(d, C + math.cos(ang) * rr, C + math.sin(ang) * rr, C * 0.07 * (1 - t * 0.6),
                fill=rgba(WHITE, a), outline=rgba(INK, a), w=2 * K)
        out.append(done(im))
    return out


# ── hero down: a big round "poof" — cloud blobs push out and shrink, two dizzy stars ─────────────────
def fx_hero_poof(n=8):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = int(255 * (1 - t ** 2.2))
        pop = ease_back(min(1.0, 0.45 + t * 2.0)) if t < 0.3 else 1.0       # frame 0 already big (the beat)
        for k in range(7):
            ang = k * 2 * math.pi / 7 + 0.3
            rr = (0.12 + 0.52 * ease_out(t)) * C
            s = C * (0.34 * pop) * (1 - 0.55 * t)
            puff_blobs(d, C + math.cos(ang) * rr, C + math.sin(ang) * rr * 0.9, s, a)
        puff_blobs(d, C, C, C * 0.5 * pop * (1 - 0.7 * t), a)
        if 0.15 < t < 0.95:                                    # dizzy stars circling
            for k in range(2):
                ang = t * 5 + k * math.pi
                star5(d, C + math.cos(ang) * C * 0.42, C * 0.7 + math.sin(ang) * C * 0.16, C * 0.12, CORE, a)
        out.append(done(im))
    return out


# ── hero back: sparkles gather in, then a round star pops with a ring ─────────────────────────────────
def fx_hero_back(n=8):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas()
        if t < 0.45:                                           # gather: 8 little stars close in
            u = t / 0.45; a = int(255 * min(1, 0.55 + u * 2))
            soft_glow(im, GOLD, 0.35 * u, 1.6)
            for k in range(8):
                ang = k * math.pi / 4 + u * 1.2
                rr = (0.9 - 0.7 * ease_out(u)) * C
                star5(d, C + math.cos(ang) * rr, C + math.sin(ang) * rr, C * 0.09, CREAM if k % 2 else GOLD, a)
        else:                                                  # pop: star + opening ring
            u = (t - 0.45) / 0.55; a = int(255 * (1 - u ** 1.8))
            soft_glow(im, GOLD, 0.8 * (1 - u), 1.5)
            r = (0.3 + 0.6 * ease_out(u)) * C
            ell(d, C, C, r, outline=rgba(INK, a), w=(0.12 - 0.06 * u) * C + 2.5 * K)
            ell(d, C, C, r, outline=rgba(CREAM, a), w=(0.12 - 0.06 * u) * C)
            star5(d, C, C, C * (0.42 * ease_back(min(1, u * 2.5)) * (1 - 0.4 * u)), GOLD, a)
            ell(d, C - C * 0.12, C - C * 0.16, C * 0.06, fill=(255, 255, 255, a), outline=None)
        out.append(done(im))
    return out


# ── hero level-up: two gold rings rise and fade, then a star pops on top with confetti dots ───────────
def fx_hero_level(n=8):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas()
        for k in range(2):
            u = min(1.0, max(0.0, 0.12 + t * 1.4 - k * 0.25))
            if u <= 0 or u >= 1: continue
            a = int(255 * min(1.0, 1.6 * math.sin(u * math.pi)))
            y = C * (1.55 - 0.9 * ease_out(u)); rx = C * (0.62 - 0.12 * u); ry = rx * 0.34
            ell(d, C, y, rx, outline=rgba(INK, a), w=0.12 * C + 2.5 * K, ry=ry)
            ell(d, C, y, rx, outline=rgba(GOLD, a), w=0.12 * C, ry=ry)
        if t >= 0.4:
            u = (t - 0.4) / 0.6; a = int(255 * (1 - u ** 2))
            soft_glow(im, GOLD, 0.5 * (1 - u), 1.8, 0.7)
            s = C * 0.34 * ease_back(min(1, u * 2.2))
            star5(d, C, C * 0.62 - u * C * 0.1, s, GOLD, a)
            ell(d, C - s * 0.25, C * 0.62 - u * C * 0.1 - s * 0.3, s * 0.13, fill=(255, 255, 255, a), outline=None)
            for k in range(6):
                ang = -math.pi / 2 + (k - 2.5) * 0.5
                rr = C * (0.3 + 0.45 * ease_out(u))
                col = (CREAM, PINK, GOLD)[k % 3]
                ell(d, C + math.cos(ang) * rr, C * 0.62 + math.sin(ang) * rr * 0.8, C * 0.06,
                    fill=rgba(col, a), outline=rgba(INK, a), w=2 * K)
        out.append(done(im))
    return out


# ── boss wakes: soft ground ripples (round, top-down), tintable ───────────────────────────────────────
def fx_boss_ripple(n=8):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas()
        for k in range(3):
            u = min(1.0, max(0.0, 0.06 + t * 1.3 - k * 0.2))
            if u <= 0 or u >= 1: continue
            a = int(255 * (1 - u) ** 1.2)
            r = (0.18 + 0.78 * ease_out(u)) * C
            w = (0.14 - 0.08 * u) * C
            ell(d, C, C, r, outline=rgba(INK, a), w=w + 2.5 * K)
            ell(d, C, C, r, outline=rgba(WHITE, a), w=w)
        out.append(done(im))
    return out


# ── barricade built / broken: biscuit crumbs hop out of a little cloud ────────────────────────────────
def fx_crumbs(n=6):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = int(255 * (1 - t ** 2))
        puff_blobs(d, C, C * 1.05, C * 0.5 * (1 - 0.5 * t) * (0.9 + 0.3 * min(1, t * 3)), a, fill=CREAM)
        for k in range(7):
            ang = -math.pi / 2 + (k - 3) * 0.42
            v = C * (0.25 + 0.6 * ease_out(t)) * (0.8 + 0.1 * (k % 3))
            x = C + math.cos(ang) * v; y = C + math.sin(ang) * v + C * 0.9 * t * t   # hop up, fall back
            s = C * (0.15 + 0.04 * (k % 2)) * (1 - 0.3 * t)
            ell(d, x, y, s, fill=rgba(BISCUIT, a), outline=rgba(INK, a), w=2.5 * K, ry=s * 0.8)   # round chunk
            ell(d, x - s * 0.3, y - s * 0.2, s * 0.22, fill=rgba(BISCUIT_D, a), outline=None)
            ell(d, x + s * 0.25, y + s * 0.15, s * 0.16, fill=rgba(BISCUIT_D, a), outline=None)
        out.append(done(im))
    return out


# ── branch picked: a flower burst of round petals (tinted by branch) ──────────────────────────────────
def fx_branch_bloom(n=5):
    out = []
    for i in range(n):
        t = i / (n - 1); im, d = canvas(); a = int(255 * (1 - t ** 2.0))
        soft_glow(im, WHITE, 0.6 * (1 - t), 1.6)
        rr = (0.25 + 0.5 * ease_out(t)) * C
        for k in range(6):
            ang = -math.pi / 2 + k * math.pi / 3
            px, py = C + math.cos(ang) * rr, C + math.sin(ang) * rr
            s = C * 0.2 * (1 - 0.45 * t)
            ell(d, px, py, s, fill=rgba(WHITE, a), outline=rgba(INK, a), w=2.5 * K)
        ell(d, C, C, C * 0.2 * (1 - 0.5 * t) + 1, fill=rgba(CREAM, a), outline=rgba(INK, a), w=2.5 * K)
        out.append(done(im))
    return out


# ── particle tiles (1 frame, MatchFxView moves them) ─────────────────────────────────────────────────
def tile_puff():
    im, d = canvas(); puff_blobs(d, C, C, C * 0.82); return done(im)


def tile_star():
    im, d = canvas(); star5(d, C, C * 1.04, C * 0.86, WHITE)
    ell(d, C - C * 0.22, C - C * 0.18, C * 0.12, fill=(255, 255, 255, 255), outline=None)
    return haloed(done(im), 0.82, 0.06, 0.55)


def tile_dot():
    im, d = canvas()
    soft_glow(im, WHITE, 0.9, 1.4)
    ell(d, C, C, C * 0.42, fill=WHITE, outline=INK, w=0.1 * C)
    ell(d, C - C * 0.13, C - C * 0.14, C * 0.11, fill=(255, 255, 255, 255), outline=None)
    return done(im)


def tile_crumb():
    im, d = canvas(); s = C * 0.72
    pts = [(C + s * math.cos(q * 2 * math.pi / 6 + 0.3) * (1 if q % 2 else 0.86),
            C + s * 0.82 * math.sin(q * 2 * math.pi / 6 + 0.3)) for q in range(6)]
    d.polygon(pts, fill=rgba(BISCUIT), outline=INK, width=int(0.12 * C))
    for dx, dy in ((-0.25, -0.1), (0.2, 0.15), (0.05, -0.32)):
        ell(d, C + dx * C, C + dy * C, C * 0.08, fill=rgba(BISCUIT_D), outline=None)
    ell(d, C - C * 0.3, C - C * 0.3, C * 0.1, fill=rgba(BISCUIT_L), outline=None)
    return done(im)


def tile_confetti_round():
    im, d = canvas(); ell(d, C, C, C * 0.6, fill=WHITE, outline=INK, w=0.14 * C); return done(im)


def tile_confetti_rect():
    im, d = canvas()
    d.rounded_rectangle((C - C * 0.34, C - C * 0.62, C + C * 0.34, C + C * 0.62), int(C * 0.18), fill=WHITE,
                        outline=INK, width=int(C * 0.13))
    return done(im)


def tile_bubble():
    """Camp reward pop: a round bubble with a star inside — tinted by the reward."""
    im, d = canvas()
    ell(d, C, C, C * 0.86, fill=WHITE, outline=INK, w=0.12 * C)
    star5(d, C, C * 1.04, C * 0.46, CREAM)
    ell(d, C - C * 0.42, C - C * 0.42, C * 0.14, fill=(255, 255, 255, 255), outline=None, ry=C * 0.09)
    return done(im)


def tile_warn_ring():
    """Boss warning: a soft dashed ring of round beads (no hard edge) — tinted coral."""
    im, d = canvas()
    for k in range(16):
        ang = k * math.pi / 8
        ell(d, C + math.cos(ang) * C * 0.84, C + math.sin(ang) * C * 0.84, C * 0.1, fill=WHITE, outline=INK, w=2 * K)
    return done(im)


# ── UI loop: the Commander skill button is ready — a soft gold halo with 3 sparkles orbiting ──────────
def fx_cmd_ready(n=8):
    out = []
    for i in range(n):
        t = i / n; im, d = canvas()                            # loop: t = i / n
        breath = 0.5 + 0.5 * math.cos(t * 2 * math.pi)
        soft_glow(im, GOLD, 0.55 + 0.25 * breath, 1.1)
        r = C * (0.8 + 0.03 * breath)
        ell(d, C, C, r, outline=rgba(GOLD, 235), w=0.1 * C)
        ell(d, C, C, r, outline=rgba(CREAM, 200), w=0.03 * C)
        for k in range(3):
            ang = t * 2 * math.pi / 3 + k * 2 * math.pi / 3 - math.pi / 2   # 1/3 turn per loop → seamless
            s = C * (0.13 + 0.03 * math.sin(t * 2 * math.pi + k))
            star5(d, C + math.cos(ang) * r, C + math.sin(ang) * r, s, CREAM, 255)
        out.append(done(im))
    return out


# name → (row, first column, frames)  — MatchFxView.Cells mirrors this
LAYOUT = {
    "skill_halo": (0, 0, 8), "hero_poof": (1, 0, 8), "hero_back": (2, 0, 8), "hero_level": (3, 0, 8),
    "boss_ripple": (4, 0, 8), "crumbs": (5, 0, 6), "puff": (5, 6, 1), "star": (5, 7, 1),
    "hero_spark": (6, 0, 5), "dot": (6, 5, 1), "crumb": (6, 6, 1), "confetti_round": (6, 7, 1),
    "branch_bloom": (7, 0, 5), "confetti_rect": (7, 5, 1), "bubble": (7, 6, 1), "warn_ring": (7, 7, 1),
}

FNS = {
    "skill_halo": fx_skill_halo, "hero_poof": fx_hero_poof, "hero_back": fx_hero_back, "hero_level": fx_hero_level,
    "boss_ripple": fx_boss_ripple, "crumbs": fx_crumbs, "hero_spark": fx_hero_spark, "branch_bloom": fx_branch_bloom,
    "puff": lambda: [tile_puff()], "star": lambda: [tile_star()], "dot": lambda: [tile_dot()],
    "crumb": lambda: [tile_crumb()], "confetti_round": lambda: [tile_confetti_round()],
    "confetti_rect": lambda: [tile_confetti_rect()], "bubble": lambda: [tile_bubble()], "warn_ring": lambda: [tile_warn_ring()],
}

VFX = [
    ("skill_halo", fx_skill_halo, "HandService.SkillPlayed (gold tint none)"),
    ("hero_spark", fx_hero_spark, "IMatchHero.HeroStrike (throttled)"),
    ("hero_poof", fx_hero_poof, "IMatchHero.HeroDowned"),
    ("hero_back", fx_hero_back, "IMatchHero.HeroRespawned"),
    ("hero_level", fx_hero_level, "IMatchHero.HeroLeveled"),
    ("boss_ripple", fx_boss_ripple, "IMatchFrontline.BossWoke / BossWarned"),
    ("crumbs", fx_crumbs, "BarricadeBuilt / BarricadeGone"),
    ("branch_bloom", fx_branch_bloom, "PointUpgraded with a new branch"),
    ("cmd_ready", fx_cmd_ready, "UI loop on match-cmd-skill"),
    ("tiles", lambda: [tile_puff(), tile_star(), tile_dot(), tile_crumb(), tile_confetti_round(), tile_confetti_rect(),
                       tile_bubble(), tile_warn_ring()], "particle tiles (stills)"),
]


def build_atlas():
    atlas = Image.new("RGBA", (T * 8, T * 8), (0, 0, 0, 0))
    for name, (row, col, n) in LAYOUT.items():
        frames = FNS[name]()
        assert len(frames) == n, (name, len(frames), n)
        for k, f in enumerate(frames):
            atlas.alpha_composite(f, ((col + k) * T, row * T))   # row 0 = top of the PNG
    return atlas


if __name__ == "__main__":
    ATLAS.parent.mkdir(parents=True, exist_ok=True)
    build_atlas().save(ATLAS)
    UI_OUT.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(fx_cmd_ready()):
        f.save(UI_OUT / f"fx-cmd-ready-{i}.png")
    print("atlas →", ATLAS, "· ui loop →", UI_OUT / "fx-cmd-ready-*.png")
