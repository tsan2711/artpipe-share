"""artpipe — run the art-direction conformance checks over a folder of PNGs.

    python3 tools/artpipe/cli.py <png-or-folder> [--spec PATH] [--json OUT.json]

Prints a per-asset table and writes one provenance record per asset. Exit code is 1 if
any asset failed a fatal check, so this drops straight into CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import checks  # noqa: E402
import spec as spec_mod  # noqa: E402

from project import ROOT as REPO  # gốc project game (ARTPIPE_PROJECT hoặc cwd)
DEFAULT_SPEC = REPO / "claude-code-game-studios/design/gdd/art-direction.md"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def collect(target: Path) -> list[Path]:
    target = target.resolve()
    if target.is_file():
        return [target]
    return sorted(p.resolve() for p in target.rglob("*.png"))


def show(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def verdict(results: list[checks.Result]) -> str:
    if any(not r.passed and r.fatal for r in results):
        return "auto_reject"
    if any(not r.passed for r in results):
        return "needs_review"
    return "tier1_pass"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    art_spec = spec_mod.load(args.spec)
    version = art_spec.get("spec", {}).get("version", "unknown")
    pngs = collect(args.target)
    if not pngs:
        print(f"không tìm thấy .png nào dưới {args.target}")
        return 2

    print(f"{DIM}spec {args.spec.name} v{version} · {len(pngs)} asset{RESET}\n")

    records, failed = [], 0
    for png in pngs:
        results = checks.run_all(png, art_spec)
        v = verdict(results)
        if v == "auto_reject":
            failed += 1
        tag = {"tier1_pass": f"{GREEN}PASS{RESET}",
               "needs_review": f"{YELLOW}WARN{RESET}",
               "auto_reject": f"{RED}FAIL{RESET}"}[v]

        print(f"{tag}  {show(png)}")
        for r in results:
            if r.passed:
                continue
            mark = f"{RED}✗{RESET}" if r.fatal else f"{YELLOW}!{RESET}"
            print(f"      {mark} {r.check_id}: {r.detail}")

        records.append({
            "asset_path": show(png),
            "spec_version": version,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "tier": 1,
            "verdict": v,
            "scores": {r.check_id: r.value for r in results},
            "failures": [r.check_id for r in results if not r.passed],
        })

    passed = sum(1 for r in records if r["verdict"] == "tier1_pass")
    warned = sum(1 for r in records if r["verdict"] == "needs_review")
    print(f"\n{passed} pass · {warned} warn · {failed} fail")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(records, indent=2, ensure_ascii=False), "utf-8")
        print(f"{DIM}ghi {len(records)} bản ghi → {args.json}{RESET}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
