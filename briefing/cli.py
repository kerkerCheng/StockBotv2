"""`python -m briefing alpha-card <TICKER>` — 單一公司的完整 Alpha Card（CLI consumer）。

它與 Daily Brief 的精簡摘要消費**同一份** `AlphaInvestmentView`；差別只在 renderer 印多少。
純讀：不 freeze context、不建 decision、不寫任何 authority。

⚠ handler 一律是本模組的具名函式（不得是 lazy `__import__` 的 lambda）——
`tests/test_alpha_cli_dispatch.py` 記過 `alpha audit` 壞了整段時間沒人發現的機制。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def cmd_alpha_card(args: argparse.Namespace) -> int:
    from alpha.errors import AlphaError, PointInTimeUnsupported

    from .alpha_view import render_alpha_investment_view_markdown
    from .alpha_view.sources import fetch_alpha_investment_view

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    try:
        view = fetch_alpha_investment_view(
            args.ticker, as_of=as_of,
            judgment_path=Path(args.judgment) if args.judgment else None,
            allow_stale_judgment=not args.strict_judgment,
            include_causal=not args.no_causal,
        )
    except PointInTimeUnsupported as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 3
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        text = json.dumps(view.to_dict(), ensure_ascii=False, indent=2)
    else:
        text = render_alpha_investment_view_markdown(view)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"alpha card → {args.out}（{len(text)} chars）")
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m briefing", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    card = sub.add_parser("alpha-card", help="單一公司的 canonical Alpha Investment View")
    card.add_argument("ticker")
    card.add_argument("--as-of", help="YYYY-MM-DD；走 Engine A as-of 投影與 Engine C 時序")
    card.add_argument("--format", choices=("markdown", "json"), default="markdown")
    card.add_argument("--judgment", help="指定 session 判斷 JSON（預設找 library/private/alpha/judgments/<TICKER>.json）")
    card.add_argument("--strict-judgment", action="store_true",
                      help="判斷檔的 context digest 與目前不一致時視為無判斷（預設：仍呈現但標 stale）")
    card.add_argument("--no-causal", action="store_true", help="略過依賴／替代路徑與結構事件（較快）")
    card.add_argument("-o", "--out", help="輸出路徑")
    card.set_defaults(func=cmd_alpha_card)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
