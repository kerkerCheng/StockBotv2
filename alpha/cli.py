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
                    # Step 0.5：supporting／calibration／comparison 分開列；同期共識只能在後兩者。
                    calibration_refs=list(spec.get("calibration_refs") or []),
                    comparison_refs=list(spec.get("comparison_refs") or []),
                    review_conditions=list(spec.get("review_conditions") or []),
                    # v3：這個值是怎麼決定的。spec 沒給就在 assumption_record 被拒——
                    # 未宣告不會被當成 independent（那會把佔位冒充成主張）。
                    derivation=spec.get("derivation"),
                    # V0：base（預設）或 variant（賭注的 overlay；三條規則由型別層擋）。
                    scenario=str(spec.get("scenario") or "base"),
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
                # 撤回紀錄沿用舊 refs、不補角色——它只是一個「撤回」標記，不是新的 provenance 主張。
                legacy_roles=True,
                # ⚠ 必須沿用被撤回那筆的 scenario。漏了它會預設成 base，而型別層正確地擋下
                # 跨 scenario supersede，結果是 **variant／downside 一旦寫錯就撤不回**
                # （2026-09-19 實測撞到）。這個分支寫於只有 base 的時期，scenario 加入後沒跟上。
                scenario=target.scenario,
            )
        try:
            path = append_assumption_record(
                record, allow_new_scope=bool(getattr(args, "allow_new_scope", False)))
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
        mark += "" if r.scenario == "base" else f"〔{r.scenario}〕"
        print(f"- {r.assumption_id} {r.period.label} {r.driver}[{r.scope}] = {r.value} {r.unit}"
              f" 〔{r.basis}｜{r.accounting_basis}〕 created {r.created_at.date()}{mark}")
        print(f"    {r.rationale[:160]}")
        print(f"    證據：{', '.join(r.evidence_refs[:3])}")
    for error in errors:
        print(f"- ⚠ 解析失敗：{error}")
    return 0


# ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`cmd_valuation`（ValuationAssumption ledger）與
# `cmd_horizon`（HorizonAssumption ledger）兩個子命令退役。** 兩本 ledger 的檔案留在
# `library/private/alpha/{valuation,horizon}/`（private append-only，L10），但沒有任何讀寫入口與消費端——
# 估值鏈整條退役，「已定價嗎」由財務三題回答（Phase 3）。


def cmd_brief(args: argparse.Namespace) -> int:
    """投資人短評 ledger 的讀寫入口（2026-09-15；**Phase 3 Step 3.4 起新寫一律 v2**）。

    - `--list`：列出 ledger 全部紀錄。
    - `--add spec.json`：append 一筆 v2。spec：`{"slots": {"demand": {"text": …, "evidence_refs": […]}, …},
      "rides": […], "disproof": […], "answers": {…}, "candidate_state": {…}, "history_not_comparable": null,
      "acknowledged_touched": […], "confirm": […], "supersedes_id": …, "note": …}`（形狀見 `python -m alpha research <T>` packet 的
      `brief_frame.spec_shape`）。寫入當下檢查讀圖現行、供給側、watch、answers、可開前提，不過就整筆拒收並逐條說明；
      通過後 `disproof[]` 自動登記成語意 watch（已在盯的只連結）、`confirm[]`（加碼條件，Phase 7 Step 7.0d）各登記一筆
      `condition_role=confirm` 的語意 watch、舊版還 active 的 `brief:` watch 收掉。
    - `--retract <id>`：append 一筆撤回紀錄（沿用被撤那筆的版本；撤回 v2 只收它登記、還 active 的 watch）。
    """
    from datetime import datetime, timezone

    from .narrative import RECORD_VERSION_V2, brief_record
    from .providers.briefs import WriteContext, read_brief_records, write_brief

    try:
        resolved_ticker, company_id = _resolve_company(args.ticker)
    except AlphaError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    ticker = str(resolved_ticker)
    if args.add or args.retract:
        if args.add:
            # 組要在這條鏈第一份敘事之前定義（plan 7.1 ④；failure log #26：10-05 散熱四檔照佇列寫了敘事、組晚落地，
            # 已定價的相對比較沒有事先登記的參照）。只擋「第一份、而且它的組提案還在 pq2」——寫過的重寫不擋。
            from .providers.closure import first_narrative_awaiting_cohort

            waiting = first_narrative_awaiting_cohort(ticker)
            if waiting is not None:
                print(f"✗ {ticker} 還沒有任何敘事，而它所屬的主題等權組提案 [{waiting}] 還沒落地——"
                      f"先請使用者 go [{waiting}]、跑 `python -m engine_b.todo complete-theme-cohort {waiting}`，"
                      "再寫第一份敘事（組要在第一份敘事之前定義）", file=sys.stderr)
                return 2
            spec = json.loads(Path(args.add).read_text(encoding="utf-8"))
            try:
                record = brief_record(
                    company_id=str(company_id), ticker=ticker, slots=spec["slots"],
                    supersedes_id=spec.get("supersedes_id"), author=str(spec.get("author") or "session"),
                    context_digest=spec.get("context_digest"), note=str(spec.get("note") or ""),
                    created_at=datetime.now(timezone.utc), record_version=RECORD_VERSION_V2,
                    rides=spec.get("rides") or (), disproof=spec.get("disproof") or (),
                    answers=spec.get("answers"), candidate_state=spec.get("candidate_state"),
                    history_not_comparable=spec.get("history_not_comparable"),
                    acknowledged_touched=spec.get("acknowledged_touched") or (),
                    confirm=spec.get("confirm") or ())
            except (KeyError, ValueError, TypeError, AlphaError) as exc:
                print(f"✗ 短評不合法：{exc}", file=sys.stderr)
                return 2
        else:
            existing, _ = read_brief_records(ticker)
            target = next((r for r in existing if r.brief_id == args.retract), None)
            if target is None:
                print(f"✗ ledger 裡沒有 {args.retract}", file=sys.stderr)
                return 2
            v2 = {}
            if target.record_version == RECORD_VERSION_V2:
                v2 = {"rides": [r.as_dict() for r in target.rides], "disproof": [d.as_dict() for d in target.disproof],
                      "answers": target.answers.as_dict() if target.answers else None,
                      "candidate_state": target.candidate_state.as_dict() if target.candidate_state else None,
                      "history_not_comparable": (target.history_not_comparable.as_dict()
                                                 if target.history_not_comparable else None),
                      "acknowledged_touched": [a.as_dict() for a in target.acknowledged_touched],
                      "confirm": [c.as_dict() for c in target.confirm]}
            record = brief_record(
                company_id=target.company_id, ticker=ticker,
                slots=[{"key": s.key, "text": s.text, "evidence_refs": list(s.evidence_refs)} for s in target.slots],
                supersedes_id=target.brief_id, retracted=True, author=target.author,
                note=str(args.rationale or "retracted"), created_at=datetime.now(timezone.utc),
                record_version=target.record_version, **v2)
        try:
            # 「今天」由 provider 取排程時區的今天（與 daily、`settle_due` 同一個定義；R2-a 覆核 non-blocking #1）——
            # alpha 核心不得直接 import engine_b（tests/test_layer_separation.py）。
            ctx = WriteContext.load(ticker)
            result = write_brief(record, ctx=ctx)
        except (AlphaError, ValueError) as exc:
            print(f"✗ {exc}", file=sys.stderr)
            return 2
        print(f"✓ {record['brief_id']} → {result['path']}")
        print(f"  watch：新登 {len(result['registered'])}｜連結既有 {len(result['linked'])}"
              f"｜收掉舊版 {len(result['consumed'])}｜處置 {len(result['acknowledged'])}"
              f"｜加碼條件新登 {len(result.get('confirm_registered') or ())}")
        print(f"  下一步：python -m webapp materialize {ticker}（首屏會長出七句；引用解析不到的格會現形）")
        return 0
    records, errors = read_brief_records(ticker)
    if args.format == "json":
        print(json.dumps({"ticker": ticker, "records": [
            {"brief_id": r.brief_id, "created_at": r.created_at.isoformat(), "retracted": r.retracted,
             "supersedes_id": r.supersedes_id, "slots": [{"key": s.key, "text": s.text, "evidence_refs": list(s.evidence_refs)} for s in r.slots]}
            for r in records], "parse_errors": errors}, ensure_ascii=False, indent=2))
        return 0
    print(f"# {ticker} 投資人短評 ledger（{len(records)} 筆，解析失敗 {len(errors)}）")
    for r in records:
        mark = "（已撤回）" if r.retracted else ""
        print(f"- {r.brief_id} created {r.created_at.date()}{mark}")
        for s in r.slots:
            print(f"    {s.key}：{s.text[:120]}")
    return 0


def cmd_abstention(args: argparse.Namespace) -> int:
    """Abstention ledger 的讀寫入口（Step 5：**「刻意不主張」是研究結論，不是待辦**）。

    - `--list`：列出 ledger 全部紀錄（含已撤回者，稽核用）。
    - `--add spec.json`：append 一筆。spec 必須明寫 `layer`／`subject`／`reason`／`revisit_when`；
      可選 `period_end`／`evidence_refs`／`supersedes_id`／`author`。
    - `--retract <id>`：append 一筆撤回紀錄（撤回後該格回到 `not_yet_recorded`）。

    ⚠ **它不會產生任何數字。** `Abstention` 在 import 當下就被掃描，長出 value／target／multiple
    之類的欄位是 import 失敗——所以不可能用它偷渡一個估值。宣告後 fair value 仍然缺席、
    readiness 仍然 blocked；改變的只有「為什麼缺席」這句話。
    """
    from datetime import date, datetime, timezone

    from .abstention.contracts import ABSTENTION_LAYERS, ABSTENTION_SUBJECTS, abstention_record
    from .providers.abstentions import append_abstention_record, read_abstention_records

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
                record = abstention_record(
                    company_id=str(company_id), ticker=ticker,
                    layer=str(spec["layer"]), subject=str(spec["subject"]),
                    reason=str(spec.get("reason") or ""), revisit_when=str(spec.get("revisit_when") or ""),
                    period_end=(date.fromisoformat(str(spec["period_end"])[:10]) if spec.get("period_end") else None),
                    evidence_refs=list(spec.get("evidence_refs") or []),
                    supersedes_id=spec.get("supersedes_id"),
                    author=str(spec.get("author") or "user"), created_at=datetime.now(timezone.utc),
                )
            except (KeyError, ValueError, TypeError, AlphaError) as exc:
                print(f"✗ abstention 不合法：{exc}", file=sys.stderr)
                return 2
        else:
            existing, _ = read_abstention_records(ticker)
            target = next((r for r in existing if r.abstention_id == args.retract), None)
            if target is None:
                print(f"✗ ledger 裡沒有 {args.retract}", file=sys.stderr)
                return 2
            record = abstention_record(
                company_id=target.company_id, ticker=ticker, layer=target.layer, subject=target.subject,
                reason=target.reason, revisit_when=target.revisit_when, period_end=target.period_end,
                evidence_refs=list(target.evidence_refs), supersedes_id=target.abstention_id, retracted=True,
                author=target.author, created_at=datetime.now(timezone.utc),
            )
        try:
            path = append_abstention_record(record)
        except AlphaError as exc:
            print(f"✗ {exc}", file=sys.stderr)
            return 2
        print(f"✓ {record['abstention_id']} → {path}")
        print(f"  下一步：python -m briefing analyst-view {ticker}"
              "（fair value 仍然缺席——改變的是「為什麼」，不是有沒有）")
        return 0

    records, errors = read_abstention_records(ticker)
    if args.format == "json":
        print(json.dumps({"ticker": ticker, "records": [r.to_display() for r in records],
                          "parse_errors": errors,
                          "layers": list(ABSTENTION_LAYERS),
                          "subjects": {k: list(v) for k, v in ABSTENTION_SUBJECTS.items()}},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"# Abstention ledger — {ticker}（{len(records)} 筆；解析失敗 {len(errors)} 行）")
    if not records:
        print("（空）——這一檔沒有任何「刻意不主張」宣告；缺席一律讀成 not_yet_recorded（還沒做）")
    for r in records:
        mark = "（已撤回）" if r.retracted else ""
        period = r.period_end.isoformat() if r.period_end else "不綁期間"
        print(f"- `{r.abstention_id}`{mark} {r.layer}／{r.subject}｜{period}｜宣告於 {r.created_on.isoformat()}")
        print(f"  - 為什麼不主張：{r.reason}")
        print(f"  - 什麼會改寫它：{r.revisit_when}")
    for line in errors:
        print(f"- ⚠ 解析失敗：{line}")
    return 0


def _register_watches(record: dict, register) -> int:
    """讀圖寫入之後的等待登記（Phase 1 Step 1.5）。失敗就大聲說、非零離開——ledger 已寫、watch 沒登記，
    `--register-watches` 可冪等重跑。"""
    try:
        summary = register(record)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 讀圖已寫入，但等待登記失敗：{type(exc).__name__}: {exc}"
              f"——修好後跑 `python -m alpha structure-reading {record.get('node')} --register-watches`",
              file=sys.stderr)
        return 1
    print(f"  反證 watch 登記 {len(summary['registered'])}、被取代收掉 {len(summary['consumed'])}；"
          f"客戶重讀 watch 登記 {len(summary['reread_registered'])}、已重讀收掉 {len(summary['reread_consumed'])}"
          f"；觸及已處置 {len(summary['touched_handled'])}")
    print("  下一步：python -m webapp materialize --structure-readings"
          "（心跳第 2 段才看得到它的 staleness）")
    return 0


def ledger_lines(node: str) -> list[str]:
    from .providers.structure_readings import ledger_path

    path = ledger_path(node)
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def cmd_structure_reading(args: argparse.Namespace) -> int:
    """結構讀圖 ledger 的讀寫入口（Q5，2026-09-17）——**存輸入，不存結論**。

    - `--list`（預設）：列出這個節點的全部紀錄（含已撤回者，稽核用）。
    - `--check`：跟**現在的圖**比一次，印 status 與分級後的變化（唯讀，不寫任何東西）。
    - `--add spec.json`：append 一筆。spec 必須明寫 `unit`／`kind`／`reading`／`expires`；
      可選 `tickers`／`author`／`supersedes_id`／`disproof`／`citations`。
      ⚠ **快照由本命令自己跑 `query.structure` 產生**，spec 不得夾帶——手組的快照偵測不了
      「多了一條我當初沒讀到的邊」，而那正是這本 ledger 存在的理由。
      ⚠ v3（2026-09-25）：`citations` 由本命令對**同一次查詢**的圖上逐字核對，對不上就整筆拒收並逐條說明。
    - `--retract <id>`：append 一筆撤回紀錄。
    - `--unit layer|socket`：只看這個單位（`--list`／`--check`／`--register-watches`；預設兩種都列）。

    ⚠ 它**不 gate 任何東西**：不濾候選、不改排序、不給尺寸。讀圖是寫賭注的輸入（L15-2）。
    """
    from datetime import date, datetime, timezone

    from .providers.structure_readings import (
        append_reading_record, evidence_rank, fetch_structure_snapshot, fetch_structure_snapshot_with_quotes,
        read_reading_records, register_reading_watches,
    )
    from .structure_reading import (
        READING_KINDS, READING_UNITS, needs_reread, reading_status, select_readings, structure_reading_record,
    )

    node = str(args.node)
    records, errors = read_reading_records(node)
    units = [args.unit] if getattr(args, "unit", None) else list(READING_UNITS)

    if args.add or args.retract:
        quotes = None
        if args.add:
            spec = json.loads(Path(args.add).read_text(encoding="utf-8"))
            if "structure" in spec or "angles" in spec or "result_digest" in spec:
                print("✗ spec 不得夾帶快照——快照必須由本命令現跑 query.structure 產生", file=sys.stderr)
                return 2
            if not spec.get("unit"):
                print(f"✗ spec 必須寫 unit（{'／'.join(READING_UNITS)}）——讀的是一層還是一格插槽由寫的人宣告，"
                      "程式不替你補", file=sys.stderr)
                return 2
            # ⚠ 走 providers，不直接 import query：alpha/ 的契約與模型層不得依賴外部世界
            # （`tests/test_layer_separation.py`；2026-09-17 它真的擋下過一次）。
            structure, quotes = fetch_structure_snapshot_with_quotes(node)
            try:
                record = structure_reading_record(
                    node=node, structure=structure, unit=str(spec["unit"]),
                    kind=str(spec["kind"]), reading=str(spec.get("reading") or ""),
                    expires=date.fromisoformat(str(spec["expires"])[:10]),
                    tickers=list(spec.get("tickers") or []),
                    supersedes_id=spec.get("supersedes_id"),
                    author=str(spec.get("author") or "user"), created_at=datetime.now(timezone.utc),
                    disproof=spec.get("disproof"), citations=spec.get("citations"),
                )
            except (KeyError, ValueError, TypeError, AlphaError) as exc:
                print(f"✗ 讀圖紀錄不合法：{exc}", file=sys.stderr)
                return 2
        else:
            target = next((r for r in records if r.reading_id == args.retract), None)
            if target is None:
                print(f"✗ ledger 裡沒有 {args.retract}", file=sys.stderr)
                return 2
            record = structure_reading_record(
                node=node, structure=fetch_structure_snapshot(node), unit=target.unit,
                kind=target.kind, reading=target.reading,
                expires=target.expires, tickers=list(target.tickers),
                supersedes_id=target.reading_id, retracted=True,
                author=target.author, created_at=datetime.now(timezone.utc),
            )
        try:
            path = append_reading_record(record, quotes=quotes)
        except AlphaError as exc:
            print(f"✗ {exc}", file=sys.stderr)
            return 2
        print(f"✓ {record['reading_id']}（{record['unit']}）→ {path}")
        return _register_watches(record, register_reading_watches)

    today = date.today()
    current_by_unit = {u: r for u, r in select_readings(records, today=today).items() if u in units}

    if getattr(args, "register_watches", False):
        # 冪等補登記：append 之後登記失敗（或更早的紀錄）時，以每個單位現行那一份重跑等待登記。
        if not current_by_unit:
            print("✗ 沒有現行的讀圖紀錄可以登記", file=sys.stderr)
            return 2
        code = 0
        for current in current_by_unit.values():
            raw = next(json.loads(line) for line in ledger_lines(node)
                       if json.loads(line).get("reading_id") == current.reading_id)
            code = max(code, _register_watches(raw, register_reading_watches))
        return code

    statuses: dict[str, dict] = {}
    if args.check:
        if not current_by_unit:
            print("✗ 沒有現行的讀圖紀錄可以比對", file=sys.stderr)
            return 2
        snapshot = fetch_structure_snapshot(node)
        rank = evidence_rank()
        statuses = {u: reading_status(r, snapshot, today=today, evidence_rank=rank) for u, r in current_by_unit.items()}

    shown = [r for r in records if r.unit in units]
    if args.format == "json":
        print(json.dumps({
            "node": node,
            "records": [{"reading_id": r.reading_id, "unit": r.unit, "kind": r.kind, "reading": r.reading,
                         "read_on": r.created_on.isoformat(), "expires": r.expires.isoformat(),
                         "tickers": list(r.tickers), "retracted": r.retracted,
                         "citations": [c.as_dict() for c in r.citations]} for r in shown],
            "current": {u: r.reading_id for u, r in current_by_unit.items()},
            "status": statuses, "parse_errors": errors,
            "kinds": dict(READING_KINDS), "units": dict(READING_UNITS),
        }, ensure_ascii=False, indent=2))
        return 0

    current_ids = {r.reading_id for r in current_by_unit.values()}
    print(f"# 結構讀圖 — {node}（{len(shown)} 筆；單位 {'／'.join(units)}；解析失敗 {len(errors)} 行）")
    if not shown:
        print("（空）——這個節點還沒有人寫過這個單位的讀圖紀錄。"
              f"先跑 `python -m query.structure {node} --quotes` 看五個角度與原文，再 --add 一筆。")
    for r in shown:
        mark = "（已撤回）" if r.retracted else ("（現行）" if r.reading_id in current_ids else "")
        print(f"- `{r.reading_id}`{mark} [{r.unit}] {r.kind}｜讀於 {r.created_on.isoformat()}"
              f"｜到期 {r.expires.isoformat()}｜關聯 {'、'.join(r.tickers) or '（未關聯標的）'}")
        print(f"  - 讀成什麼：{READING_KINDS.get(r.kind, r.kind)}")
        print(f"  - 憑什麼：{r.reading}")
        for c in r.citations:
            flag = "｜independent" if c.independent else ""
            print(f"  - 引用［{c.angle}］{c.edge[0]} {c.edge[1]} {c.edge[2]}：«{c.quote}»（{c.source_id}{flag}）")
    for line in errors:
        print(f"- ⚠ 解析失敗：{line}")
    for unit, status in statuses.items():
        print(f"\n## 跟現在的圖比 [{unit}]（{status['status']}）")
        print(f"- digest 變了：{status['digest_changed']}｜到期還有 {status['days_to_expiry']} 天"
              f"｜該重讀：{needs_reread(status)}")
        if status.get("reason"):
            print(f"- ⚠ {status['reason']}")
        for change in status["changes"]:
            flag = "｜**同時是 disproof 觸發**" if change["disproof_trigger"] else ""
            print(f"- [{change['grade']}] {change['angle']}／{change['kind']}：{change['detail']}{flag}")
        if not status["changes"]:
            print("- （沒有任何角度變動）")
    return 0


def cmd_theme_cohort(args: argparse.Namespace) -> int:
    """主題等權組（Phase 3 Step 3.3）：**唯讀**——列出各題材現行的組、查一檔屬於哪幾組。

    ⚠ 本命令不寫任何東西。成分是判斷：研究步驟以 `python -m engine_b.todo add-theme-cohort --spec <file>`
    把 spec 凍結進一個 pq2 編號；使用者 go 之後由 `python -m engine_b.todo complete-theme-cohort <n>`
    讀凍結的那一份、比對 digest 才寫 ledger（bare go 拒收）。
    """
    from .providers.theme_cohorts import THEME_COHORT_DIR, current_cohorts, memberships

    cohorts, errors = current_cohorts()
    if args.ticker:
        cohorts = memberships(args.ticker, cohorts)
    if args.format == "json":
        print(json.dumps({"cohorts": [{
            "cohort_id": c.cohort_id, "theme": c.theme, "decided_on": c.decided_on.isoformat(),
            "pq2_ref": c.pq2_ref, "reason": c.reason,
            "members": [{"ticker": m.ticker, "company_id": m.company_id, "reason": m.reason} for m in c.members],
            "excluded": [dict(e) for e in c.excluded]} for c in cohorts], "parse_errors": errors},
            ensure_ascii=False, indent=2))
        return 0
    if not cohorts:
        where = f"（{args.ticker} 不在任何一組）" if args.ticker else f"（{THEME_COHORT_DIR} 沒有任何紀錄）"
        print(f"主題等權組：0 組{where}——已定價②③會印 not_yet_recorded")
    for c in cohorts:
        print(f"## {c.theme}｜{c.cohort_id}｜決定於 {c.decided_on.isoformat()}（pq2 [{c.pq2_ref}]）｜{len(c.members)} 檔等權")
        print(f"理由：{c.reason}")
        for m in c.members:
            print(f"- {m.ticker}（{m.company_id}）：{m.reason}")
        for e in c.excluded:
            print(f"- ✗ 排除 {e.get('name')}：{e.get('reason')}")
    if errors:
        print(f"⚠ 解析失敗 {len(errors)} 行：" + "；".join(errors[:3]))
    return 0


def cmd_layer_note(args: argparse.Namespace) -> int:
    """層說明 ledger 的讀寫入口（個股頁 plan S4a；2026-10-07）——一個薄層或技術轉換一份，同層每一頁共用。

    - `--list`（預設）：列出這個節點的全部紀錄（含已撤回、已被取代者；標出現行那一份）。
    - `--add spec.json`：append 一筆。spec：`unit`（layer／transition）、`title`、`expires`（重讀日）、`reread_reason`、
      `sections`（physics／variants／selection，各 `text`＋`citations`）、`claims[]`（L7 三件套＋`entities`＋`evidence`＋`citations`）、
      選填 `supersedes_id`（換版）、`body_ref`（全文 markdown）。出處只認 `raw:<library/raw 的檔名>`／`lead:<id>`，寫入端核對指得回去
      （圖上 SourceDoc id 不一定等於檔名——failure log #37）；
      成功後每條主張登記一筆語意 watch（`layer_note:<note_id>#<n>`），換版時舊版的條件收掉。
    - `--retract <note_id>`：append 一筆撤回紀錄（它的 watch 一併收掉）。
    - `--register-watches`：以現行那一份冪等重跑 watch 登記（append 之後登記失敗時用）。

    ⚠ 它**不 gate 任何東西**：不濾候選、不排序、不給尺寸（AGENTS 消費契約：讀圖與敘事是研究判斷）。
    """
    from datetime import datetime, timezone

    from .layer_note import EVIDENCE_LABELS, SECTION_LABELS, layer_note_record, select_current
    from .providers.layer_notes import ledger_path, read_note_records, register_note_watches, write_note

    node = str(args.node)
    records, errors = read_note_records(node)

    def _register(record: dict) -> int:
        try:
            summary = register_note_watches(record)
        except Exception as exc:  # noqa: BLE001 — 紀錄已寫進去；登記失敗要說清楚怎麼補，不得安靜（INV-3）
            print(f"⚠ 紀錄已寫入，但 watch 登記失敗（{type(exc).__name__}: {exc}）——修好後跑 "
                  f"`python -m alpha layer-note {node} --register-watches`", file=sys.stderr)
            return 1
        print(f"  主張 watch 新登 {len(summary['registered'])}、舊版條件收掉 {len(summary['consumed'])}")
        return 0

    if args.add or args.retract:
        stamp = datetime.now(timezone.utc)
        if args.add:
            spec = json.loads(Path(args.add).read_text(encoding="utf-8"))
            if spec.get("node") and str(spec["node"]) != node:
                print(f"✗ spec 的 node（{spec['node']}）與命令列（{node}）不一致——節點只寫在命令列", file=sys.stderr)
                return 2
            try:
                record = layer_note_record({**spec, "node": node}, created_at=stamp,
                                           author=str(spec.get("author") or "session"))
            except (KeyError, ValueError, TypeError, AlphaError) as exc:
                print(f"✗ 層說明不合法：{exc}", file=sys.stderr)
                return 2
        else:
            target = next((r for r in records if r.note_id == args.retract), None)
            if target is None:
                print(f"✗ ledger 裡沒有 {args.retract}", file=sys.stderr)
                return 2
            record = layer_note_record({"node": node, "unit": target.unit, "title": target.title, "retracted": True,
                                        "supersedes_id": target.note_id, "sections": {}, "claims": []},
                                       created_at=stamp, author=target.author)
        # 唯一的寫入入口（R2 C1）：先在 registry 副本上預演 watch 登記，失敗就整筆拒收、ledger 不動
        try:
            result = write_note(record)
        except AlphaError as exc:
            print(f"✗ {exc}", file=sys.stderr)
            return 2
        print(f"✓ {record['note_id']}（{record['unit']}）→ {result['path']}")
        print(f"  主張 watch 新登 {len(result['registered'])}、舊版條件收掉 {len(result['consumed'])}")
        return 0

    if getattr(args, "register_watches", False):
        current = select_current(records)
        if current is None:
            print("✗ 沒有現行的層說明可以登記", file=sys.stderr)
            return 2
        path = ledger_path(node)
        raw = next(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                   if line.strip() and json.loads(line).get("note_id") == current.note_id)
        return _register(raw)

    current = select_current(records)
    if args.format == "json":
        path = ledger_path(node)
        lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip()] if path.is_file() else []
        print(json.dumps({"node": node, "current": current.note_id if current else None, "records": lines,
                          "parse_errors": errors}, ensure_ascii=False, indent=2))
        return 0
    print(f"# 層說明：{node}（{len(records)} 筆；現行 {current.note_id if current else '—'}）")
    for r in records:
        mark = "▶ 現行" if current is not None and r.note_id == current.note_id else (
            "撤回" if r.retracted else "已被取代")
        day = r.created_at.date().isoformat()
        if r.retracted:
            print(f"- {r.note_id}｜{day}｜{mark}（撤回 {r.supersedes_id}）")
            continue
        levels = sorted({c.evidence for s in r.sections.values() for c in s.citations})
        print(f"- {r.note_id}｜{day}｜{mark}｜{r.title}｜重讀日 {r.expires}｜主張 {len(r.claims)} 條｜"
              f"段：{'、'.join(SECTION_LABELS[k] for k in r.sections)}｜證據等級：{'、'.join(EVIDENCE_LABELS[x] for x in levels)}")
    if errors:
        print(f"⚠ 解析失敗 {len(errors)} 行：" + "；".join(errors[:3]))
    return 0


# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`cmd_entry_criterion` 與 `entry-criterion` 子命令退役（F 組）。**
# EntryCriterion ledger 的讀寫入口。ledger 檔案本身留在 `library/private/alpha/entry_criteria/`
# （private append-only，L10：拿不回來的只能 append），但**沒有任何消費端**——進場靠判斷。


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m alpha", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`entry-criterion` 子命令隨 F 組退役。
    reading = sub.add_parser(
        "structure-reading",
        help="結構讀圖 ledger：--list／--check／--add spec.json／--retract <id>（Q5；存輸入不存結論）")
    reading.add_argument("node", help="圖節點 id，例如 tech:cw_dfb_laser（不是 ticker）")
    reading.add_argument("--list", action="store_true", help="（預設）列出 ledger")
    reading.add_argument("--check", action="store_true", help="跟現在的圖比一次並分級（唯讀）")
    reading.add_argument("--add", help="append 一筆（JSON spec：unit／kind／reading／expires 必填；快照與引用核對由本命令現跑）")
    reading.add_argument("--retract", help="append 一筆撤回紀錄（指定 reading_id）")
    reading.add_argument("--register-watches", action="store_true",
                         help="以現行讀圖冪等重跑等待登記（反證語意 watch、需求側客戶的重讀 watch；Phase 1 Step 1.5）")
    reading.add_argument("--unit", choices=("layer", "socket"),
                         help="只看這個單位（層／插槽，v3）；預設兩種都列。--add 的單位寫在 spec 裡")
    reading.add_argument("--format", choices=("markdown", "json"), default="markdown")
    reading.set_defaults(func=cmd_structure_reading)

    note = sub.add_parser(
        "layer-note",
        help="層說明 ledger：--list／--add spec.json／--retract <id>／--register-watches（個股頁 plan S4a；同層每頁共用）")
    note.add_argument("node", help="節點或轉換 id，例如 mat:inp_epiwafer（不是 ticker）")
    note.add_argument("--list", action="store_true", help="（預設）列出 ledger")
    note.add_argument("--add", help="append 一筆（JSON spec；出處核對與主張 watch 登記由本命令做）")
    note.add_argument("--retract", help="append 一筆撤回紀錄（指定 note_id）")
    note.add_argument("--register-watches", action="store_true", help="以現行那一份冪等重跑主張 watch 登記")
    note.add_argument("--format", choices=("markdown", "json"), default="markdown")
    note.set_defaults(func=cmd_layer_note)

    edge = sub.add_parser(
        "edge", help="研究時判邊緣（唯讀）：名冊外的代號也能判——同一個判定函式與門檻，缺的輸入用 yfinance 補、逐欄標來源")
    edge.add_argument("tickers", nargs="+", help="代號，例如 3324.TWO 3110.T（照交易所後綴寫）")
    edge.add_argument("--format", choices=("markdown", "json"), default="markdown")
    edge.set_defaults(func=cmd_edge)

    cohort = sub.add_parser(
        "theme-cohort", help="主題等權組（唯讀）：列出現行的組／查一檔屬於哪幾組；寫入只經 pq2 complete-theme-cohort")
    cohort.add_argument("ticker", nargs="?", help="只看這一檔屬於哪幾組")
    cohort.add_argument("--format", choices=("markdown", "json"), default="markdown")
    cohort.set_defaults(func=cmd_theme_cohort)

    abstention = sub.add_parser(
        "abstention", help="Abstention ledger：--list／--add spec.json／--retract <id>（Step 5；「刻意不主張」）")
    abstention.add_argument("ticker")
    abstention.add_argument("--list", action="store_true", help="（預設）列出 ledger")
    abstention.add_argument("--add", help="append 一筆 abstention（JSON spec 檔路徑；reason 與 revisit_when 必填）")
    abstention.add_argument("--retract", help="append 一筆撤回紀錄（指定 abstention_id）")
    abstention.add_argument("--format", choices=("markdown", "json"), default="markdown")
    abstention.set_defaults(func=cmd_abstention)

    brief = sub.add_parser("brief", help="投資人短評 ledger（七格前因後果；文字 session 寫、數字 authority 填）")
    brief.add_argument("ticker")
    brief.add_argument("--list", action="store_true", help="（預設）列出 ledger")
    brief.add_argument("--add", help="append 一筆短評（JSON spec 檔路徑；七格缺一不可）")
    brief.add_argument("--retract", help="append 一筆撤回紀錄（指定 brief_id）")
    brief.add_argument("--rationale", help="撤回理由")
    brief.add_argument("--format", choices=("markdown", "json"), default="markdown")
    brief.set_defaults(func=cmd_brief)

    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`valuation` 與 `horizon` 子命令隨 C／H 組退役。
    assumptions = sub.add_parser(
        "assumptions", help="OperatingAssumption ledger：--list／--add spec.json／--retract <id>")
    assumptions.add_argument("ticker")
    assumptions.add_argument("--list", action="store_true", help="（預設）列出 ledger")
    assumptions.add_argument("--add", help="append 一筆假設（JSON spec 檔路徑）")
    assumptions.add_argument(
        "--allow-new-scope", action="store_true",
        help="放行『overlay 引入 base 沒有的 scope』。⚠ 預設拒收：未命中 base 的 overlay "
             "不會覆蓋而是與 base 同時生效（數值相加），而打錯 scope 與真的要新切分在資料上同形")
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


def cmd_edge(args: argparse.Namespace) -> int:
    """研究時判邊緣（failure log #43）：名冊外的代號也能判，判定與門檻同候選板；唯讀。"""
    from .providers.edge import adhoc_edge_states

    tickers = [t.strip() for t in args.tickers if t.strip()]
    rows = adhoc_edge_states(tickers)
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        return 0
    print("| 代號 | 判定 | 市值（USD） | 分析師 | 理由 | 市值來源 | 家數來源 |")
    print("|---|---|---|---|---|---|---|")
    for t in tickers:
        r = rows[t]
        cap = r.get("market_cap_usd")
        cap_s = f"{cap / 1e9:.2f}B" if cap is not None else f"—（{r.get('market_cap_absence') or '缺'}）"
        cnt = r.get("analyst_count")
        src = r.get("sources") or {}
        print(f"| {t} | {r['label']} | {cap_s} | {cnt if cnt is not None else '—'} | {'、'.join(r['reasons'])} | "
              f"{src.get('market_cap') or '—'} | {src.get('analyst_count') or '—'} |")
    lim = next(iter(rows.values()))["thresholds"] if rows else {}
    print(f"\n門檻（config/alpha_screen.json，兩條 AND）：市值 ≤ {lim.get('market_cap_max_usd', 0) / 1e9:.0f}B 美元、分析師 ≤ {lim.get('analyst_count_max')} 家。"
          "這只回答「算不算倍率候選」，不排序、不給尺寸。")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
