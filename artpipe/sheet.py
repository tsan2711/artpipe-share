"""Build a review page for a batch: every variant of every asset, with its scores.

    python3 tools/artpipe/sheet.py out/ --open

Exists because choosing is the one step in this pipeline that a person has to do, and it
was the one step with no tool. The notebook makes several variants per asset so there is
something to choose between; `run.py` scores them; but comparing them meant opening PNGs
one at a time in a file browser with the scores in another window.

Two jobs, and the second is the reason it earns its place:

  1. Pick anchors (AD-1). Variants sit side by side, on the real UI background, at the
     size the icon is actually seen — 64px matters more than 512px for this decision.
  2. See the batch, not the icon. A single bad icon is noise. Twenty icons all failing
     `outline_present` means the prompt is wrong, and that pattern is invisible when you
     review one file at a time. The failure tally at the top is there for exactly that.

Self-contained HTML with the images referenced relatively — no server, no dependency, and
it keeps working if the folder is copied elsewhere as long as the icons come along.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import spec as spec_mod  # noqa: E402

from project import ROOT as REPO  # gốc project game (ARTPIPE_PROJECT hoặc cwd)
DEFAULT_SPEC = REPO / "claude-code-game-studios/design/gdd/art-direction.md"

VERDICT_LABEL = {"auto_accept": "NHẬN", "needs_review": "XEM TAY", "auto_reject": "LOẠI"}


def _card(rec: dict, ui_bg: str) -> str:
    verdict = rec.get("verdict", "?")
    fails = rec.get("failures", [])
    detail = rec.get("failure_detail", {})
    rows = "".join(
        f'<li><code>{html.escape(c)}</code> {html.escape(str(detail.get(c, "")))}</li>'
        for c in fails
    )
    scores = rec.get("scores", {})
    # The two model-judged numbers are the ones a person actually second-guesses, so they
    # are shown on the card instead of hidden in the JSON.
    judged = " · ".join(
        f'{k.replace("_readability", "")} {scores[k]:.2f}'
        for k in ("element_readability", "shape_readability") if isinstance(scores.get(k), float)
    )
    return f"""
    <figure class="card {verdict}">
      <div class="shots">
        <div class="big" style="background:{ui_bg}"><img src="{html.escape(rec['asset_path'])}" alt=""></div>
        <div class="small" style="background:{ui_bg}"><img src="{html.escape(rec['asset_path'])}" alt=""></div>
      </div>
      <figcaption>
        <div class="name">{html.escape(rec.get('variant', rec.get('slug', '?')))}</div>
        <div class="verdict">{VERDICT_LABEL.get(verdict, verdict)}{(' · ' + judged) if judged else ''}</div>
        <ul>{rows}</ul>
      </figcaption>
    </figure>"""


def build(records: list[dict], art: dict) -> str:
    ui_bg = art["readability"]["ui_background_reference"]
    small = art["icon"]["readability_reference_size"]

    by_slug: dict[str, list[dict]] = {}
    for r in records:
        by_slug.setdefault(r.get("slug", "?"), []).append(r)

    tally = Counter(r.get("verdict") for r in records)
    fail_tally = Counter(c for r in records for c in r.get("failures", []))
    batch = "".join(
        f"<li><code>{html.escape(c)}</code> — <b>{n}</b>/{len(records)} ảnh</li>"
        for c, n in fail_tally.most_common()
    ) or "<li>không ảnh nào trượt check nào</li>"

    sections = "".join(
        f'<section><h2>{html.escape(slug)} <span class="n">{len(v)} phương án</span></h2>'
        f'<div class="row">{"".join(_card(r, ui_bg) for r in sorted(v, key=lambda r: r.get("variant", "")))}</div></section>'
        for slug, v in sorted(by_slug.items())
    )

    return f"""<!doctype html>
<meta charset="utf-8">
<title>artpipe — duyệt mẻ</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ background:#141118; color:#e8e2ee; font:14px/1.5 ui-sans-serif,system-ui,sans-serif;
         margin:0; padding:24px 28px; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .meta {{ color:#9a92a6; margin-bottom:20px; }}
  .batch {{ background:#1d1926; border:1px solid #2e2838; border-radius:10px;
            padding:14px 18px; margin-bottom:28px; max-width:760px; }}
  .batch h3 {{ margin:0 0 8px; font-size:14px; color:#c9c1d6; }}
  .batch ul {{ margin:0; padding-left:20px; }}
  section {{ margin-bottom:30px; }}
  h2 {{ font-size:15px; margin:0 0 10px; border-bottom:1px solid #2a2434; padding-bottom:6px; }}
  h2 .n {{ color:#7d7489; font-weight:400; font-size:12px; margin-left:8px; }}
  .row {{ display:flex; flex-wrap:wrap; gap:14px; }}
  .card {{ margin:0; width:210px; background:#1b1723; border:1px solid #2e2838;
           border-top-width:3px; border-radius:10px; overflow:hidden; }}
  .card.auto_accept {{ border-top-color:#4caf50; }}
  .card.needs_review {{ border-top-color:#e0a33a; }}
  .card.auto_reject {{ border-top-color:#e2504a; }}
  .shots {{ display:flex; align-items:flex-end; gap:8px; padding:10px; }}
  .big {{ width:132px; height:132px; border-radius:6px; }}
  .big img {{ width:100%; height:100%; object-fit:contain; }}
  .small {{ width:{small}px; height:{small}px; border-radius:6px; }}
  .small img {{ width:100%; height:100%; object-fit:contain; image-rendering:auto; }}
  figcaption {{ padding:0 10px 10px; }}
  .name {{ font-family:ui-monospace,monospace; font-size:11px; color:#cdc5da;
           word-break:break-all; }}
  .verdict {{ font-size:11px; color:#9a92a6; margin:3px 0 4px; }}
  figcaption ul {{ margin:0; padding-left:16px; font-size:11px; color:#d59a96; }}
  code {{ font-family:ui-monospace,monospace; }}
</style>
<h1>artpipe — duyệt mẻ</h1>
<div class="meta">
  {len(records)} ảnh · {len(by_slug)} asset ·
  {tally['auto_accept']} nhận · {tally['needs_review']} xem tay · {tally['auto_reject']} loại ·
  spec v{html.escape(str(art.get('spec', {}).get('version', '?')))}
</div>
<div class="batch">
  <h3>Trượt theo cả mẻ — con số này quan trọng hơn từng ảnh</h3>
  <ul>{batch}</ul>
  <p style="color:#9a92a6;margin:10px 0 0">
    Một ảnh trượt là nhiễu. Phần lớn mẻ cùng trượt một check nghĩa là <b>prompt hoặc spec sai</b>,
    không phải máy sinh tồi — sửa ở đó, đừng sinh lại.
  </p>
</div>
{sections}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path, help="thư mục --out của run.py")
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--open", action="store_true", help="mở luôn trong trình duyệt")
    args = ap.parse_args()

    report = args.out_dir / "report.json"
    if not report.exists():
        print(f"không thấy {report} — chạy run.py trước")
        return 2

    art = spec_mod.load(args.spec)
    records = json.loads(report.read_text(encoding="utf-8"))
    page = args.out_dir / "sheet.html"
    page.write_text(build(records, art), encoding="utf-8")
    print(f"{len(records)} ảnh → {page}")

    if args.open:
        import webbrowser
        webbrowser.open(page.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
