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


# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`cmd_multi_year` 與 `multi-year` 子命令已移除。**
# 多年反向橋（要幾倍、哪一格得為真）整條在 Phase 0 退役（ROADMAP Phase 0／D 組）。
# 接手「這個結構允不允許翻倍」的是讀圖（Phase 2）與財務三題（Phase 3），**不是另一條橋**。

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


# ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`cmd_valuation`（第 13 節）與 `cmd_implied_return`
# （第 13a 節）退役**——read model 已沒有 valuation／implied_return 兩個 section。


def cmd_analyst_view(args: argparse.Namespace) -> int:
    """Analyst Consumer（Step 3.5）：把 canonical read model 依消費者問句投影成一份判讀畫面。

    **純讀、純投影**：不重算 EPS／估值／報酬，不寫任何 authority，不呼叫 LLM。
    產出可預先 materialize（`--format json`）讓未來 APP 點擊直接讀。
    """
    from alpha.errors import AlphaError, PointInTimeUnsupported

    from .alpha_view.sources import fetch_alpha_investment_view
    from .analyst_view import build_analyst_view, render_analyst_view_markdown

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    try:
        view = fetch_alpha_investment_view(
            args.ticker, as_of=as_of,
            judgment_path=Path(args.judgment) if args.judgment else None,
            include_causal=False, scenario=args.scenario,
            sandbox_hurdle=args.sandbox_hurdle)
    except PointInTimeUnsupported as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 3
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    analyst = build_analyst_view(view)
    if args.format == "json":
        text = json.dumps(analyst.to_dict(), ensure_ascii=False, indent=2)
    else:
        text = render_analyst_view_markdown(analyst)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"analyst view → {args.out}（{len(text)} chars）")
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
                                                "new_actual", "disproof"),
                         help="在真實 state 上疊一件假想變化（不寫任何 authority）")
    refresh.add_argument("--judgment", help="指定 session 判斷 JSON")
    refresh.add_argument("--format", choices=("markdown", "json"), default="markdown")
    refresh.add_argument("-o", "--out", help="輸出路徑")
    refresh.set_defaults(func=cmd_refresh)
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`valuation` 與 `implied-return` 子命令隨 C／H 組退役。
    analyst = sub.add_parser(
        "analyst-view",
        help="Analyst Consumer（Step 3.5）：一檔股票的完整判讀畫面（頭條／基本面／怎麼算的／研究現況／optional entry）")
    analyst.add_argument("ticker")
    analyst.add_argument("--as-of", help="YYYY-MM-DD：只看 T 之前已知的判斷、假設、內部基本面與行情")
    analyst.add_argument("--scenario", choices=("price_only", "consensus_revision", "graph_edge", "new_guidance",
                                                "new_actual", "disproof"),
                         help="在真實 state 上疊一件假想變化（不寫任何 authority）")
    analyst.add_argument("--sandbox-hurdle", type=float, default=None,
                         help="非持久驗算：只在記憶體疊一筆 author=sandbox 的年化要求報酬（例 0.15）；不寫 ledger")
    analyst.add_argument("--judgment", help="指定 session 判斷 JSON")
    analyst.add_argument("--format", choices=("markdown", "json"), default="markdown")
    analyst.add_argument("-o", "--out", help="輸出路徑（可預先 materialize 給 APP 讀）")
    analyst.set_defaults(func=cmd_analyst_view)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
