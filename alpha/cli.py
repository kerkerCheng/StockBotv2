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
            from .contracts import _canonical
            payload = _canonical(signal)

            if args.emit_assessment:
                # ⚠ **composition root 負責序列化**——Engine D 的 adapter 吃 dict，
                # 不吃 `AlphaSignal` 物件，所以 Engine D 依然不 import `alpha/`。
                from decision_lab.adapters.alpha_signal import (
                    coverage_assessment_from_signal,
                )

                bridged = coverage_assessment_from_signal(payload)
                out = Path(args.emit_assessment)
                out.write_text(json.dumps(bridged["assessment"], ensure_ascii=False,
                                          indent=2, default=str), encoding="utf-8")
                mirror = out.with_suffix(".alpha_signal.json")
                mirror.write_text(json.dumps(bridged["_alpha_signal"],
                                             ensure_ascii=False, indent=2, default=str),
                                  encoding="utf-8")
                print(f"assessment → {out}")
                print(f"⚠ 有損轉換的完整鏡像 → {mirror}")
                print("  （五軸裝不下 Q5 catalyst，也表達不了 evidence quality 的"
                      "『上限』語意；鏡像保留原值供還原）")
                print("")
                print("下一步：python -m decision_lab reassess <cohort_id> "
                      f"--assessment {out}")
                print("⚠ 那一步會**寫進 append-only 的 Decision Store**——"
                      "它是既有的人工 gate，本命令只負責寫檔。")
                return 0

            if args.format == "json":
                print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
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


def cmd_assumptions(args: argparse.Namespace) -> int:
    """OperatingAssumption ledger 的讀寫入口（Causal Fundamental Model）。

    - `--list`：列出 ledger 全部紀錄（含已撤回／被取代者，稽核用）。
    - `--add spec.json`：append 一筆。spec 只給 driver／scope／period_end／value／basis／
      rationale／evidence_refs（＋可選 accounting_basis／supersedes_id）；id 與 created_at 由程式產生。
    - `--retract <id>`：append 一筆撤回紀錄。

    ⚠ 這裡**不算任何財務數字**，也不驗證 evidence_refs 解析得到哪裡——解析在模型執行時做，
    解析不到的假設會被拒用並計數（INV-3），不會靜默生效。
    """
    from datetime import datetime, timezone

    from .fundamental.assumptions import assumption_record
    from .providers.assumptions import append_assumption_record, read_assumption_records

    try:
        resolved_ticker, company_id = _resolve_company(args.ticker)
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    ticker = str(resolved_ticker)

    if args.add or args.retract:
        if args.add:
            spec = json.loads(Path(args.add).read_text(encoding="utf-8"))
            try:
                record = assumption_record(
                    company_id=str(company_id), ticker=ticker,
                    period_end=date.fromisoformat(str(spec["period_end"])),
                    driver=str(spec["driver"]), scope=str(spec.get("scope") or ""),
                    value=float(spec["value"]), basis=str(spec["basis"]),
                    rationale=str(spec.get("rationale") or ""),
                    evidence_refs=list(spec.get("evidence_refs") or []),
                    accounting_basis=str(spec.get("accounting_basis") or "not_applicable"),
                    supersedes_id=spec.get("supersedes_id"),
                    author=str(spec.get("author") or "session"),
                    created_at=datetime.now(timezone.utc),
                )
            except (KeyError, ValueError, TypeError, AlphaError) as exc:
                print(f"✗ 假設不合法：{exc}", file=sys.stderr)
                return 2
        else:
            existing, _ = read_assumption_records(ticker)
            target = next((r for r in existing if r.assumption_id == args.retract), None)
            if target is None:
                print(f"✗ ledger 裡沒有 {args.retract}", file=sys.stderr)
                return 2
            record = assumption_record(
                company_id=target.company_id, ticker=ticker, period_end=target.period.end,
                driver=target.driver, scope=target.scope, value=target.value, basis=target.basis,
                rationale=str(args.rationale or "retracted"), evidence_refs=target.evidence_refs,
                accounting_basis=target.accounting_basis, supersedes_id=target.assumption_id,
                retracted=True, created_at=datetime.now(timezone.utc),
            )
        try:
            path = append_assumption_record(record)
        except AlphaError as exc:
            print(f"✗ {exc}", file=sys.stderr)
            return 2
        print(f"✓ {record['assumption_id']} → {path}")
        print("  下一步：python -m briefing alpha-card "
              f"{ticker} 會在模型執行時解析 evidence_refs；解析不到會被拒用並計數")
        return 0

    records, errors = read_assumption_records(ticker)
    if args.format == "json":
        payload = [{
            "assumption_id": r.assumption_id, "period": r.period.label,
            "period_end": r.period.end.isoformat(), "driver": r.driver, "scope": r.scope,
            "value": r.value, "unit": r.unit, "basis": r.basis,
            "accounting_basis": r.accounting_basis, "created_at": r.created_at.isoformat(),
            "author": r.author, "supersedes_id": r.supersedes_id, "retracted": r.retracted,
            "evidence_refs": list(r.evidence_refs), "rationale": r.rationale,
        } for r in records]
        print(json.dumps({"ticker": ticker, "records": payload, "parse_errors": errors},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"# {ticker} OperatingAssumption ledger（{len(records)} 筆，解析失敗 {len(errors)}）")
    for r in records:
        mark = "（已撤回）" if r.retracted else ""
        print(f"- {r.assumption_id} {r.period.label} {r.driver}[{r.scope}] = {r.value} {r.unit}"
              f" 〔{r.basis}｜{r.accounting_basis}〕 created {r.created_at.date()}{mark}")
        print(f"    {r.rationale[:160]}")
        print(f"    證據：{', '.join(r.evidence_refs[:3])}")
    for error in errors:
        print(f"- ⚠ 解析失敗：{error}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m alpha", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    assumptions = sub.add_parser(
        "assumptions", help="OperatingAssumption ledger：--list／--add spec.json／--retract <id>")
    assumptions.add_argument("ticker")
    assumptions.add_argument("--list", action="store_true", help="（預設）列出 ledger")
    assumptions.add_argument("--add", help="append 一筆假設（JSON spec 檔路徑）")
    assumptions.add_argument("--retract", help="append 一筆撤回紀錄（指定 assumption_id）")
    assumptions.add_argument("--rationale", help="撤回理由")
    assumptions.add_argument("--format", choices=("markdown", "json"), default="markdown")
    assumptions.set_defaults(func=cmd_assumptions)

    research = sub.add_parser(
        "research", help="組 ResearchContext；預設輸出 packet，帶 --judgment 則組 AlphaSignal")
    research.add_argument("ticker")
    research.add_argument("--as-of", help="YYYY-MM-DD。⚠ Engine A 目前會拒絕（Phase 6）")
    research.add_argument("--emit-packet", action="store_true",
                          help="（預設行為，保留為顯式旗標）")
    research.add_argument("-o", "--out", help="packet 輸出路徑")
    research.add_argument("--judgment", help="session 寫好的判斷 JSON")
    research.add_argument("--format", choices=("markdown", "json"), default="markdown")
    research.add_argument(
        "--emit-assessment",
        help="把 AlphaSignal 轉成 Engine D 的五軸 assessment 檔（**有損**，"
             "會同時寫一份 .alpha_signal.json 完整鏡像）。"
             "⚠ 寫檔而已——入圖／decision 仍需既有人工 gate",
    )
    research.set_defaults(func=cmd_research)

    audit = sub.add_parser(
        "audit",
        help="（已搬走）runtime invariant audit → 改用 `python -m audit invariants`",
    )
    audit.add_argument("what", choices=("invariants",))
    audit.set_defaults(func=cmd_audit_moved)
    return parser


def cmd_audit_moved(_args: argparse.Namespace) -> int:
    """**這條子命令刻意不執行 audit，只指路。**

    `audit/` 於 2026-09-04 從 `alpha/audit/` 搬到 top-level，因為那些 check 必須同時
    讀 registry、Neo4j、Engine C、leads state 與 Decision Store——**一個讀遍所有層的
    東西不可能住在 core 裡**（`tests/test_layer_separation.py::test_nothing_imports_audit`
    是這道剎車）。搬家時漏改的就是這裡，於是 `python -m alpha audit invariants`
    從 commit `5b11c85` 起**每一次呼叫都是 ModuleNotFoundError**，直到 2026-09-04
    才被實跑撞出來——L13：沒有下游消費者跑過的路徑不算接通。

    ⚠ 修法不是把 import 改指 `audit`：那會讓 `alpha/` 在 runtime 依賴 audit，
    正好反轉上面那條測試在守的依賴方向。所以這裡只印出正確入口並 fail。
    """
    print("`python -m alpha audit` 已停用——audit 站在所有層之上，不由 alpha 呼叫。",
          file=sys.stderr)
    print("請改用：python -m audit invariants", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
