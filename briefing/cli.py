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


def cmd_refresh(args: argparse.Namespace) -> int:
    """單一公司的 Refresh／Invalidation Report（read model 的第 15 節）；`--scenario` 疊一件假想變化。"""
    from alpha.errors import AlphaError, PointInTimeUnsupported

    from .alpha_view.render import render_refresh_status_lines
    from .alpha_view.sources import fetch_alpha_investment_view

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    try:
        view = fetch_alpha_investment_view(
            args.ticker, as_of=as_of, include_causal=False, scenario=args.scenario,
            judgment_path=Path(args.judgment) if args.judgment else None)
    except PointInTimeUnsupported as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 3
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    section = view.refresh_status
    if args.format == "json":
        payload = view.to_dict()["refresh_status"]
        payload["identity"] = {"ticker": view.identity.ticker, "company_id": view.identity.company_id,
                               "as_of": view.identity.as_of.isoformat() if view.identity.as_of else None,
                               "generated_on": view.identity.generated_on.isoformat(),
                               "research_context_digest": view.identity.research_context_digest,
                               "signal": view.to_dict()["identity"]["signal"]}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        head = [f"# Refresh／Invalidation Report — {view.identity.company_label}",
                f"- 生成日 {view.identity.generated_on.isoformat()}｜視角 {view.identity.point_in_time_mode}"
                + (f"（as-of {view.identity.as_of.isoformat()}）" if view.identity.as_of else "")
                + (f"｜情境 **{args.scenario}**" if args.scenario else ""),
                "", "| Artifact | State | Why |", "|---|---|---|"]
        for item in section.items:
            why = item.reasons[0] if item.reasons else "—"
            head.append(f"| {item.label}（`{item.artifact_type}:{item.artifact_id[:24]}`） | **{item.state}** | {why} |")
        head.append("")
        text = "\n".join(head + render_refresh_status_lines(view))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"refresh report → {args.out}（{len(text)} chars）")
    else:
        print(text)
    return 0


def cmd_valuation(args: argparse.Namespace) -> int:
    """單一公司的估值（read model 第 13 節）：internal EPS × explicit target multiple → fair value → gap。"""
    from alpha.errors import AlphaError, PointInTimeUnsupported

    from .alpha_view.render import render_valuation_lines
    from .alpha_view.sources import fetch_alpha_investment_view

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    try:
        view = fetch_alpha_investment_view(
            args.ticker, as_of=as_of, include_causal=False, scenario=args.scenario,
            judgment_path=Path(args.judgment) if args.judgment else None)
    except PointInTimeUnsupported as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 3
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        payload = view.to_dict()["valuation"]
        payload["identity"] = {"ticker": view.identity.ticker, "company_id": view.identity.company_id,
                               "as_of": view.identity.as_of.isoformat() if view.identity.as_of else None,
                               "generated_on": view.identity.generated_on.isoformat()}
        payload["refresh_items"] = [i for i in view.to_dict()["refresh_status"]["items"]
                                    if i["artifact_type"] in ("valuation_assumption", "fair_value", "fair_value_gap")]
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        head = [f"# Valuation — {view.identity.company_label}",
                f"- 生成日 {view.identity.generated_on.isoformat()}｜視角 {view.identity.point_in_time_mode}"
                + (f"（as-of {view.identity.as_of.isoformat()}）" if view.identity.as_of else "")
                + (f"｜情境 **{args.scenario}**" if args.scenario else ""), ""]
        text = "\n".join(head + render_valuation_lines(view))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"valuation → {args.out}（{len(text)} chars）")
    else:
        print(text)
    return 0


def cmd_implied_return(args: argparse.Namespace) -> int:
    """單一公司的 base-case implied return（read model 第 13a 節）：現價 ＋ fair value 時點語意 ＋ 明示 horizon → 隱含價格報酬。"""
    from alpha.errors import AlphaError, PointInTimeUnsupported

    from .alpha_view.render import render_implied_return_lines
    from .alpha_view.sources import fetch_alpha_investment_view

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    try:
        view = fetch_alpha_investment_view(
            args.ticker, as_of=as_of, include_causal=False, scenario=args.scenario,
            judgment_path=Path(args.judgment) if args.judgment else None)
    except PointInTimeUnsupported as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 3
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        payload = view.to_dict()["implied_return"]
        payload["identity"] = {"ticker": view.identity.ticker, "company_id": view.identity.company_id,
                               "as_of": view.identity.as_of.isoformat() if view.identity.as_of else None,
                               "generated_on": view.identity.generated_on.isoformat()}
        payload["refresh_items"] = [i for i in view.to_dict()["refresh_status"]["items"]
                                    if i["artifact_type"] in ("horizon_assumption", "implied_return",
                                                              "valuation_assumption", "fair_value")]
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        head = [f"# Base-case implied return — {view.identity.company_label}",
                f"- 生成日 {view.identity.generated_on.isoformat()}｜視角 {view.identity.point_in_time_mode}"
                + (f"（as-of {view.identity.as_of.isoformat()}）" if view.identity.as_of else "")
                + (f"｜情境 **{args.scenario}**" if args.scenario else ""), ""]
        text = "\n".join(head + render_implied_return_lines(view))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"implied return → {args.out}（{len(text)} chars）")
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
    refresh = sub.add_parser("refresh", help="單一公司的 Refresh／Invalidation Report（什麼變了、影響誰、要做什麼）")
    refresh.add_argument("ticker")
    refresh.add_argument("--as-of", help="YYYY-MM-DD：只看 T 之前已知的變化與成果")
    refresh.add_argument("--scenario", choices=("price_only", "consensus_revision", "graph_edge", "new_guidance",
                                                "new_actual", "fiscal_rollover", "disproof"),
                         help="在真實 state 上疊一件假想變化（不寫任何 authority）")
    refresh.add_argument("--judgment", help="指定 session 判斷 JSON")
    refresh.add_argument("--format", choices=("markdown", "json"), default="markdown")
    refresh.add_argument("-o", "--out", help="輸出路徑")
    refresh.set_defaults(func=cmd_refresh)
    valuation = sub.add_parser("valuation", help="單一公司的估值（Step 1：fair value／現價／gap／refresh state）")
    valuation.add_argument("ticker")
    valuation.add_argument("--as-of", help="YYYY-MM-DD：只看 T 之前已知的假設、內部基本面與行情")
    valuation.add_argument("--scenario", choices=("price_only", "consensus_revision", "graph_edge", "new_guidance",
                                                  "new_actual", "fiscal_rollover", "disproof"),
                           help="在真實 state 上疊一件假想變化（不寫任何 authority）")
    valuation.add_argument("--judgment", help="指定 session 判斷 JSON")
    valuation.add_argument("--format", choices=("markdown", "json"), default="markdown")
    valuation.add_argument("-o", "--out", help="輸出路徑")
    valuation.set_defaults(func=cmd_valuation)
    implied = sub.add_parser("implied-return", help="單一公司的 base-case implied return（Step 2：現價／fair value 時點／horizon／報酬／refresh state）")
    implied.add_argument("ticker")
    implied.add_argument("--as-of", help="YYYY-MM-DD：只看 T 之前已知的 horizon 判斷、估值假設、內部基本面與行情")
    implied.add_argument("--scenario", choices=("price_only", "consensus_revision", "graph_edge", "new_guidance",
                                                "new_actual", "fiscal_rollover", "disproof"),
                         help="在真實 state 上疊一件假想變化（不寫任何 authority）")
    implied.add_argument("--judgment", help="指定 session 判斷 JSON")
    implied.add_argument("--format", choices=("markdown", "json"), default="markdown")
    implied.add_argument("-o", "--out", help="輸出路徑")
    implied.set_defaults(func=cmd_implied_return)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
