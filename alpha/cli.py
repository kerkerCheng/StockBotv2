"""`python -m alpha research <TICKER>` — 第一條 vertical slice。

## 兩步式，因為 LLM 就是 session

```
python -m alpha research COHR --emit-packet -o packet.json
    ↓ deterministic 取料（Engine A 排序 ＋ Engine C 快照）→ 研究包
（session 讀 packet，依 axis_prompts 寫判斷 JSON）
python -m alpha research COHR --judgment judgment.json
    ↓ 驗證引用 → 逐軸套證據上限 → AlphaSignal
```

**沒有 API 呼叫**（`target-architecture.md` §6.1）。這與既有的
`decision_lab assessment-scaffold → reassess --assessment` 同形，不是第二套流程。

## 為什麼不做「一鍵出 signal」

因為那需要程式替 session 決定四個判斷，而那正是四個 authority gate 存在的理由。
`--emit-packet` 之後停下來，是**刻意的**。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .contracts import AXES, content_digest
from .errors import AlphaError, PointInTimeUnsupported
from .identity import CompanyId, Ticker


def _resolve_company(ticker: str) -> tuple[Ticker, CompanyId]:
    """ticker → `CompanyId`，**經 registry，不猜**（INV-1／F-01）。"""
    from identity.registry import get_registry

    registry = get_registry()
    wanted = ticker.strip().upper()
    for company_id, research in registry.ticker_map.items():
        if research and str(research).upper() == wanted:
            return Ticker(str(research)), CompanyId(str(company_id))
    raise AlphaError(
        f"registry 找不到 research_ticker={ticker!r}。"
        "⚠ 「找不到」與「不存在」是兩個 claim——請先確認它是否需要 onboard，"
        "不要在這裡猜一個 co:* id（F-01）"
    )


def _build(ticker: str, as_of: date | None):
    from .context import build_research_context
    from .providers.fundamentals import EngineCFundamentalsProvider
    from .providers.graph_neo4j import open_default_provider

    resolved_ticker, company_id = _resolve_company(ticker)
    graph = open_default_provider()
    try:
        return build_research_context(
            ticker=resolved_ticker, company_id=company_id,
            graph_provider=graph,
            fundamentals_provider=EngineCFundamentalsProvider(),
            as_of=as_of,
        ), graph
    except Exception:
        graph.driver.close()
        raise


def _render(signal: Any) -> str:
    """人可讀的 signal 摘要。**每個值都指得回它的 trace。**"""
    lines = [
        f"# {signal.ticker}（{signal.company_id}）as-of {signal.as_of}",
        "",
        f"研究完整度：{'incomplete' if signal.is_incomplete else 'complete'}"
        f"｜已知維度 {len(signal.known_axes)}/5｜最弱：{signal.weakest or '—'}",
        "",
        "| 維度 | 宣告 | 生效 | 降級原因 | 證據 |",
        "|---|---|---|---|---|",
    ]
    for axis in AXES:
        score = signal.score_for(axis)
        if score is None:
            lines.append(f"| {axis} | — | — | **unknown（不知道，不是 0）** | — |")
            continue
        trace = signal.model_components.get(score.trace_id)
        lines.append(
            f"| {axis} | {score.declared} | {score.effective} | "
            f"{score.downgrade_reason or '—'} | {len(trace.evidence_refs) if trace else 0} 條 |"
        )
    lines += [
        "",
        f"**variant perception**：{signal.variant_view or '（未填）'}",
        "",
        f"disproof（{len(signal.disproof_conditions)} 條）：",
    ]
    for cond in signal.disproof_conditions:
        lines.append(f"  - {cond.condition}｜核查 {cond.check_frequency}"
                     f"｜48h：{cond.action_within_48h}")
    lines += [
        "",
        f"排序鍵：{signal.ordering_key()}",
        f"ResearchContext digest：{signal.research_context_digest}",
        "",
        "⚠ 這是**研究判斷**，不是回測或統計勝率；系統不給部位尺寸。",
    ]
    return "\n".join(lines)


def cmd_research(args: argparse.Namespace) -> int:
    from .models import build_packet, compose_signal

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    try:
        build, graph = _build(args.ticker, as_of)
    except PointInTimeUnsupported as exc:
        print(f"✗ {exc}", file=sys.stderr)
        print("\n提示：Engine A 的 as-of 投影是 Phase 6；先不帶 --as-of 跑當前視角。",
              file=sys.stderr)
        return 3
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2

    try:
        if args.judgment:
            judgment = json.loads(Path(args.judgment).read_text(encoding="utf-8"))
            signal = compose_signal(build, judgment)
            if args.format == "json":
                from .contracts import _canonical
                print(json.dumps(_canonical(signal), ensure_ascii=False, indent=2,
                                 default=str))
            else:
                print(_render(signal))
            return 0

        packet = build_packet(build)
        payload = packet.to_json()
        if args.out:
            Path(args.out).write_text(payload, encoding="utf-8")
            print(f"packet → {args.out}（{len(payload)} bytes，"
                  f"digest {packet.context_digest[:20]}…）")
            print("\n下一步：讀 packet 的 axis_prompts，寫判斷 JSON，然後")
            print(f"  python -m alpha research {args.ticker} --judgment <judgment.json>")
        else:
            print(payload)
        return 0
    finally:
        graph.driver.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m alpha", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    research = sub.add_parser(
        "research", help="組 ResearchContext；預設輸出 packet，帶 --judgment 則組 AlphaSignal")
    research.add_argument("ticker")
    research.add_argument("--as-of", help="YYYY-MM-DD。⚠ Engine A 目前會拒絕（Phase 6）")
    research.add_argument("--emit-packet", action="store_true",
                          help="（預設行為，保留為顯式旗標）")
    research.add_argument("-o", "--out", help="packet 輸出路徑")
    research.add_argument("--judgment", help="session 寫好的判斷 JSON")
    research.add_argument("--format", choices=("markdown", "json"), default="markdown")
    research.set_defaults(func=cmd_research)

    audit = sub.add_parser("audit", help="runtime invariant audit")
    audit.add_argument("what", choices=("invariants",))
    audit.set_defaults(func=lambda a: __import__(
        "alpha.audit", fromlist=["main"]).main([]))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
