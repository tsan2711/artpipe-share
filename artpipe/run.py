"""Drive the whole pipeline in one command, and write a provenance record per image.

Two entry points, because generation is the one stage that costs money and the one stage
that can happen on someone else's machine:

    python3 tools/artpipe/run.py generate --out out/           # cần credit
    python3 tools/artpipe/run.py ingest raws/ --out out/       # ảnh sinh nơi khác (Colab)

Everything after generation is identical in both: matte → tier-1 checks → provenance. That
split is the whole reason the free lane exists at all. `gen.py` is one interchangeable
source of bytes, not the spine of the pipeline, so losing access to every paid provider
costs a stage, not the tool.

Output layout under --out:
    raw/      what the generator returned, untouched (an image you cannot reproduce is
              not evidence; keep the original even when the icon is rejected)
    icons/    matted + normalised RGBA, the only files fit to import
    prov/     one JSON per image, matching art-direction §9
    report.json / a printed table
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image  # noqa: E402

import catalog  # noqa: E402
import checks  # noqa: E402
import matte  # noqa: E402
import prompt as prompt_mod  # noqa: E402
import spec as spec_mod
import theme as theme_mod  # noqa: E402
import synth  # noqa: E402

from project import ROOT as REPO  # gốc project game (ARTPIPE_PROJECT hoặc cwd)
DEFAULT_SPEC = REPO / "claude-code-game-studios/design/gdd/art-direction.md"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def verdict_of(results: list[checks.Result]) -> str:
    if any(not r.passed and r.fatal for r in results):
        return "auto_reject"
    if any(not r.passed for r in results):
        return "needs_review"
    return "auto_accept"


def target_guid(entry: catalog.Entry) -> str:
    """GUID of the ScriptableObject file this icon serves, for the provenance record."""
    if entry.asset_path is None:
        return ""  # manifest icon with no Unity write-back target (e.g. NanoSwarm UI PNGs)
    meta = entry.asset_path.with_suffix(entry.asset_path.suffix + ".meta")
    if not meta.exists():
        return ""
    m = re.search(r"^guid: ([0-9a-f]{32})\s*$", meta.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def post_process(raw_path: Path, entry: catalog.Entry, prompt_text: str, art: dict,
                 out: Path, gen_record: dict, tier2_on: bool = False,
                 anchor_dir: Path | None = None, stylise_on: bool = True) -> dict:
    """Matte → ép phong cách → check → provenance. Nửa pipeline không tốn tiền.

    `stylise_on=False` để đo máy sinh trần: sau khi ép phong cách thì ba luật màu/bậc
    sáng/viền đúng do dựng nên đúng, nên muốn biết checkpoint mới có khá hơn không thì
    phải tắt bước ép mới so được.
    """
    slug = catalog.slug(entry.descriptor)
    # Output keeps the variant suffix from the source filename. Naming outputs by slug
    # alone silently collapsed a batch: the notebook generates several variants per asset
    # precisely so there is something to choose between, and each one overwrote the last.
    variant = raw_path.stem
    icon_path = out / "icons" / f"{variant}.png"
    icon_path.parent.mkdir(parents=True, exist_ok=True)

    matte_error = None
    try:
        img = synth.through_matte(Image.open(raw_path).convert("RGB"), art)
        raw_scores = {}
        if stylise_on:
            import stylise
            # Chấm TRƯỚC khi ép phong cách, và giữ lại điểm đó.
            #
            # Ép phong cách hợp thức hoá mọi thứ nó chạm vào: một mảng nền còn sót sau khi
            # tách sẽ được snap sang màu hợp lệ rồi qua hết bộ kiểm — icon vẫn có vệt nền,
            # nhưng không phép kiểm nào còn thấy. Điểm trước khi ép là thứ duy nhất còn nói
            # thật về máy sinh và về khâu tách nền.
            pre = out / "pre" / f"{variant}.png"
            pre.parent.mkdir(parents=True, exist_ok=True)
            img.save(pre)
            raw_scores = {r.check_id: r.value
                          for r in checks.run_all(pre, art, entry.descriptor.kind)}
            img = stylise.cel(img, art, entry.descriptor.kind, entry.descriptor.element)
        img.save(icon_path)
        results = checks.run_all(icon_path, art, entry.descriptor.kind)

        # Tier 2 only after tier 1 is clean: §8 orders the tiers cheap → expensive so a
        # rejected image never pays for a model. Loading torch on an icon we already know
        # is malformed buys nothing but seconds.
        if tier2_on and verdict_of(results) != "auto_reject":
            import tier2
            results = results + tier2.run_all(icon_path, art, entry.descriptor, anchor_dir)

        v = verdict_of(results)
        scores = {r.check_id: r.value for r in results}
        failures = [r.check_id for r in results if not r.passed]
        details = {r.check_id: r.detail for r in results if not r.passed}
    except matte.MatteError as exc:
        # A cutout failure is a real result about the image, not a crash of the run: the
        # generator ignored the flat-backdrop instruction. Record it and keep going.
        matte_error, v = str(exc), "auto_reject"
        scores, failures, details = {}, ["matte"], {"matte": str(exc)}
        raw_scores = {}

    record = {
        "asset_path": str(icon_path.relative_to(out)),
        "raw_path": str(raw_path.relative_to(out)) if raw_path.is_relative_to(out) else str(raw_path),
        "target_guid": target_guid(entry),
        "target_object": entry.object_name,
        "spec_version": art.get("spec", {}).get("version", "unknown"),
        # Ghi theme + dấu vân tay của nó vào TỪNG asset: sau này nhìn report là biết ngay
        # asset nào còn khớp theme đang dùng, asset nào là tàn dư của một lần chỉnh gu đã
        # quên. Không có nó thì "đồng nhất theme" chỉ kiểm được bằng mắt.
        "theme": (art.get("_theme") or {}).get("id", ""),
        "theme_fingerprint": (art.get("_theme") or {}).get("fingerprint", ""),
        "anchor_set_id": art.get("spec", {}).get("anchor_set_id", ""),
        "slug": slug,
        "variant": variant,
        "kind": entry.descriptor.kind,
        "prompt_full": prompt_text,
        "prompt_hash": hashlib.sha256(prompt_text.encode()).hexdigest()[:16],
        "scores": scores,
        "failures": failures,
        "failure_detail": details,
        "matte_error": matte_error,
        # Ghi lại vì nó đổi ý nghĩa của điểm số: có ép phong cách thì palette/bậc sáng/viền
        # đúng do dựng nên đúng, không còn là phép chấm máy sinh.
        "stylised": stylise_on,
        # Điểm của chính ảnh máy sinh, trước khi ép phong cách. Palette thấp ở đây mà cao ở
        # `scores` nghĩa là còn nền sót lại và bước ép vừa sơn nó thành màu hợp lệ.
        "scores_raw": raw_scores,
        "verdict": v,
        "human_note": None,
        **gen_record,
    }
    prov = out / "prov" / f"{variant}.json"
    prov.parent.mkdir(parents=True, exist_ok=True)
    prov.write_text(json.dumps(record, indent=2, ensure_ascii=False), "utf-8")
    return record


def cmd_generate(args, art: dict, entries: list[catalog.Entry]) -> list[dict]:
    import gen

    kw = {"model": args.model or gen.DEFAULT_MODEL[args.provider]}
    if args.provider == "comfyui":
        # The negative prompt is art direction, so it comes from the spec through
        # prompt.py — not from the workflow file, where it would drift out of the
        # document's reach, and not from gen.py, which must not know what SKYBORNE is.
        # Cỡ SINH khác cỡ CANVAS, và phải tách được. SDXL huấn luyện ở 1024; ép nó vẽ 512
        # thì ra bố cục vỡ. Còn canvas của icon vẫn là 512 vì mọi ngưỡng của bộ kiểm tính
        # theo đó — `matte.normalise` thu ảnh về canvas nên hai con số này độc lập.
        kw |= {"host": args.host, "workflow": args.workflow,
               "size": args.gen_size or art["icon"]["canvas"]["width"],
               "negative": prompt_mod.negative(art)}
    try:
        provider = gen.PROVIDERS[args.provider](**kw)
    except gen.ProviderError as exc:
        print(f"{RED}DỪNG{RESET} — {exc}")
        return []
    records = []
    for entry in entries:
        text = prompt_mod.build(art, entry.descriptor, args.form)
        slug = catalog.slug(entry.descriptor)
      # Several variants per asset: the pick step needs something to pick between, and
      # one sample says nothing about whether the prompt works.
        for v in range(args.variants):
          # Seed suy ra từ (theme, asset, biến thể), không từ một số gõ tay. Cách cũ
          # `--seed 1000 + v` bắt phải NHỚ hôm đó gõ số mấy thì sáu tuần sau mới sinh lại
          # được đúng một icon — và nhớ sai thì ra ảnh khác mà không có gì báo.
          theme_id = (art.get("_theme") or {}).get("id")
          if theme_id:
              seed = theme_mod.seed_for(theme_id, slug, v)
          elif args.seed is not None:
              seed = args.seed + v
          else:
              seed = None
          try:
            g = provider.generate(text, seed=seed)
          except gen.ProviderError as exc:
            # Stop the whole run rather than carry on. Every remaining call fails the same
            # way — an empty balance stays empty, an unreachable server stays unreachable,
            # a malformed graph stays malformed — and a half-finished batch that burned the
            # last of the credit is the worst outcome. `OutOfCredit` is a ProviderError.
            print(f"{RED}DỪNG{RESET} — {exc}")
            return records
          raw = args.out / "raw" / f"{slug}__{g.seed}.png"
          raw.parent.mkdir(parents=True, exist_ok=True)
          raw.write_bytes(g.image)
          rec = post_process(raw, entry, text, art, args.out, {
              "provider": g.provider, "model_id": g.model_id,
              "model_version": g.model_version, "seed": g.seed,
              "generated_at": g.generated_at, "gen_settings": g.extra,
          }, tier2_on=args.tier2, anchor_dir=args.anchors,
              stylise_on=not args.no_stylise)
          records.append(rec)
          print(f"  {DIM}{rec['variant']} → {rec['verdict']}{RESET}", flush=True)
    return records


def cmd_ingest(args, art: dict, entries: list[catalog.Entry]) -> list[dict]:
    """Take images generated elsewhere. Filenames carry the mapping: `<slug>__<anything>.png`."""
    by_slug = {catalog.slug(e.descriptor): e for e in entries}
    records, unknown = [], []
    for raw in sorted(args.folder.glob("*.png")):
        slug = raw.stem.split("__")[0]
        entry = by_slug.get(slug)
        if entry is None:
            unknown.append(raw)
            continue
        text = prompt_mod.build(art, entry.descriptor)
        records.append(post_process(raw, entry, text, art, args.out, {
            "provider": args.provider_name, "model_id": args.model_name,
            "model_version": "", "seed": args.seed_from_name and _seed_of(raw) or 0,
            "generated_at": datetime.fromtimestamp(
                raw.stat().st_mtime, timezone.utc).isoformat(),
        }, tier2_on=args.tier2, anchor_dir=args.anchors,
              stylise_on=not args.no_stylise))
    for raw in unknown:
        print(f"{YELLOW}BỎ QUA{RESET} {raw.name}: không khớp slug nào")
    return records


def _seed_of(path: Path) -> int:
    m = re.search(r"__(\d+)", path.stem)
    return int(m.group(1)) if m else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--catalog", type=Path, default=None,
                    help="manifest icon (yaml) thay cho catalog game June — cho project khác "
                         "(NanoSwarm) dùng chung pipeline mà không đọc DB spell/item của June")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default=None, help="lọc theo slug, khớp chuỗi con")
    ap.add_argument("--gen-size", type=int, default=0,
                    help="cỡ ảnh máy sinh vẽ ra (0 = theo canvas). SDXL cần 1024")
    ap.add_argument("--no-stylise", action="store_true",
                    help="bỏ bước ép phong cách cel — dùng khi muốn đo máy sinh trần")
    ap.add_argument("--theme", default=None,
                    help="tên theme trong tools/artpipe/themes/ — mang theo checkpoint, "
                         "graph, cỡ sinh và seed, nên sinh lẻ không phải gõ lại gì")
    ap.add_argument("--tier2", action="store_true",
                    help="chạy thêm check do model chấm (cần tools/artpipe/.venv)")
    ap.add_argument("--anchors", type=Path, default=None,
                    help="thư mục anchor cho style_similarity (chưa có → AD-1)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="sinh ảnh qua provider (replicate tốn tiền)")
    g.add_argument("--provider", default="replicate",
                   choices=["replicate", "local", "comfyui", "fal"])
    g.add_argument("--model", default=None,
                   help="mặc định theo provider (comfyui: tên file checkpoint)")
    g.add_argument("--host", default=None,
                   help="comfyui: địa chỉ server, mặc định $COMFYUI_URL hoặc :8188")
    g.add_argument("--workflow", type=Path, default=None,
                   help="comfyui: graph API-format, mặc định workflows/icon_txt2img.json")
    g.add_argument("--variants", type=int, default=1, help="số phương án mỗi asset")
    g.add_argument("--seed", type=int, default=None, help="seed gốc (để sinh lại được)")
    g.add_argument("--form", default="short", choices=["short", "long"],
                   help="short = model dùng CLIP (SD/SDXL, 77 token); long = T5 (FLUX)")

    i = sub.add_parser("ingest", help="nhận ảnh sinh sẵn ở nơi khác (Colab/Kaggle)")
    i.add_argument("folder", type=Path)
    i.add_argument("--provider-name", default="colab")
    i.add_argument("--model-name", default="unknown")
    i.add_argument("--seed-from-name", action="store_true",
                   help="đọc seed từ tên file dạng <slug>__<seed>.png")

    args = ap.parse_args()
    art = spec_mod.load(args.spec)

    # Theme phủ lên spec và ĐIỀN LUÔN các tham số dòng lệnh còn trống. Điền chứ không ép:
    # gõ tay --model vẫn thắng, để còn thử nghiệm được. Nhưng không gõ gì thì mọi thứ
    # quyết định diện mạo đều đến từ file theme — đó là điều kiện để sinh lẻ một asset
    # sáu tuần sau vẫn ra đúng thứ khớp với bộ cũ.
    if args.theme:
        th = theme_mod.load(args.theme)
        art = theme_mod.apply(art, th)
        meta = th["theme"]
        if getattr(args, "model", "sentinel") is None:
            args.model = meta["checkpoint"]
        if getattr(args, "workflow", "sentinel") is None:
            args.workflow = Path(__file__).parent / "workflows" / meta["workflow"]
        if not args.gen_size and meta.get("gen_size"):
            args.gen_size = int(meta["gen_size"])
        print(f"{DIM}theme {meta['id']} v{meta.get('version', 1)} "
              f"· {art['_theme']['fingerprint']}{RESET}")

    entries = catalog.entries_from_manifest(args.catalog) if args.catalog else catalog.entries()
    if args.only:
        entries = [e for e in entries if args.only in catalog.slug(e.descriptor)]
        if not entries:
            print(f"--only {args.only!r} không khớp slug nào")
            return 2

    args.out.mkdir(parents=True, exist_ok=True)
    records = cmd_generate(args, art, entries) if args.cmd == "generate" \
        else cmd_ingest(args, art, entries)

    if not records:
        print("không xử lý được ảnh nào")
        return 2

    tally = {"auto_accept": 0, "needs_review": 0, "auto_reject": 0}
    for r in sorted(records, key=lambda r: r["variant"]):
        tally[r["verdict"]] += 1
        tag = {"auto_accept": f"{GREEN}NHẬN{RESET}", "needs_review": f"{YELLOW}XEM{RESET} ",
               "auto_reject": f"{RED}LOẠI{RESET}"}[r["verdict"]]
        print(f"{tag}  {r['variant']}")
        for cid in r["failures"]:
            print(f"        {DIM}{cid}: {r['failure_detail'][cid]}{RESET}")

    (args.out / "report.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), "utf-8")
    print(f"\n{tally['auto_accept']} nhận · {tally['needs_review']} cần xem tay · "
          f"{tally['auto_reject']} loại   {DIM}→ {args.out}/report.json{RESET}")
    if tally["auto_accept"]:
        print(f"{DIM}bước sau: mở {args.out}/sheet.html để chọn biến thể{RESET}")
    return 1 if tally["auto_reject"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
