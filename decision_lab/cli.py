"""Engine D operational CLI；正常路徑從 Signal、today 與 explicit live facts 出發。"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, TextIO

from .action_card import RedactionError, assert_safe_payload, build_action_card, render_markdown
from .bootstrap import open_default_store
from .brief import ranking_annotations
from .execution import (
    ExecutionError,
    assess_probe,
    record_live_choice,
    record_live_fill,
)
from .references import build_reference_options, render_reference_options_markdown
from .store import DecisionStore
from .workflow import (
    EvaluationRequest,
    WorkflowError,
    evaluate_signal,
    reassess,
    render_workflow_markdown,
)
from .workflow_ports import WorkflowDataProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_lab",
        description="從一條 Signal 產生 Action Card，或回答今天是否需要動作。",
    )
    parser.add_argument("--store", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--private-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--repo-root", type=Path, help=argparse.SUPPRESS)
    subcommands = parser.add_subparsers(dest="command", required=True)

    evaluate = subcommands.add_parser(
        "evaluate-signal",
        help="從原始 Signal 自動建立 context、Coverage、decision 與 Action Card。",
    )
    evaluate.add_argument("signal", help="推文、網址說明、公司／ticker 或一句 thesis。")
    evaluate.add_argument("--source-url")
    evaluate.add_argument("--ticker")
    evaluate.add_argument("--company")
    evaluate.add_argument("--company-id", help=argparse.SUPPRESS)
    evaluate.add_argument("--thesis")
    evaluate.add_argument("--catalyst")
    evaluate.add_argument("--disproof")
    evaluate.add_argument("--expiry")
    evaluate.add_argument("--as-of")
    evaluate.add_argument(
        "--intent", choices=("research", "paper", "live"), default="research"
    )
    evaluate.add_argument("--direction", choices=("long", "short", "neutral"), default="neutral")
    evaluate.add_argument("--source-id", default="unattributed")
    evaluate.add_argument("--source-traced", action="store_true")
    evaluate.add_argument("--evidence-tier", type=int, default=4)
    evaluate.add_argument("--confirm-holdings", action="store_true")
    evaluate.add_argument("--assessment", help="研究 agent 產生的五軸 JSON 檔。")
    evaluate.add_argument("--format", choices=("json", "markdown"), default="markdown")

    reassess_parser = subcommands.add_parser(
        "reassess",
        help="以既有 decision／cohort 重新讀 authorities，保留舊 decision。",
    )
    reassess_parser.add_argument("target_id")
    reassess_parser.add_argument("--as-of")
    reassess_parser.add_argument("--ticker")
    reassess_parser.add_argument("--company")
    reassess_parser.add_argument("--company-id", help=argparse.SUPPRESS)
    reassess_parser.add_argument("--intent", choices=("research", "paper", "live"))
    reassess_parser.add_argument("--confirm-holdings", action="store_true")
    reassess_parser.add_argument("--assessment")
    reassess_parser.add_argument("--catalyst")
    reassess_parser.add_argument("--disproof")
    reassess_parser.add_argument("--expiry")
    reassess_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")

    close_parser = subcommands.add_parser(
        "close",
        help="結案一個 probe 並寫入 outcome 歸因（人工判斷，不自動觸發）。",
    )
    close_parser.add_argument("cohort_id")
    close_parser.add_argument(
        "--terminal-status",
        required=True,
        choices=("promoted", "rejected", "expired", "revised"),
    )
    close_parser.add_argument(
        "--claim-correctness",
        required=True,
        choices=("true", "false", "mixed", "unknown"),
        help="事後看，這條 claim 對不對；unknown 是合法答案，不要硬猜。",
    )
    close_parser.add_argument("--reason", required=True)
    close_parser.add_argument("--evidence-ref", action="append", default=[])
    close_parser.add_argument("--format", choices=("json", "markdown"), default="json")

    today = subcommands.add_parser(
        "today",
        help="純讀輸出瓶頸排序、NAV 比例，以及哪些標的今天需要複查。",
    )
    today.add_argument("--as-of")
    today.add_argument("--format", choices=("json", "markdown"), default="markdown")

    references = subcommands.add_parser(
        "references",
        help="純讀列出各信心軸有哪些合格引用可用；寫 assessment 前先查，不要猜。",
    )
    references.add_argument("target_id", help="decision_id 或 cohort_id")
    references.add_argument(
        "--assessment", help="一併診斷這份 assessment 的引用會不會讓某軸落回 unknown。"
    )
    references.add_argument("--format", choices=("json", "markdown"), default="markdown")

    scaffold = subcommands.add_parser(
        "assessment-scaffold",
        help="從 frozen context 的 reference_index 產出五軸 assessment 骨架——"
        "引用預填、判斷留白（level=unknown）。",
    )
    scaffold.add_argument("target_id", help="decision_id 或 cohort_id")
    scaffold.add_argument(
        "--out",
        help="輸出路徑；預設 library/private/decision_lab/assessment_scaffold_<cohort>.json",
    )

    vp = subcommands.add_parser(
        "variant-perception",
        help="寫入或讀取 cohort 的 variant perception（市場隱含 X／本 thesis 認為 Y／催化劑 Z）。",
    )
    vp.add_argument("cohort_id")
    vp.add_argument("--text", help="不給即為讀取最新一筆")
    vp.add_argument("--supersedes", help="修正既有筆時填入被取代的 th_* id")

    card = subcommands.add_parser("card", help="純讀既有 decision 的 Action Card。")
    card.add_argument("decision_id")
    card.add_argument("--as-of")
    card.add_argument("--format", choices=("json", "markdown"), default="json")

    choice = subcommands.add_parser(
        "record-choice", help="明確記錄使用者自訂尺寸、skip 或 override 的 live 選擇。"
    )
    choice.add_argument("decision_id")
    choice.add_argument("--selected-weight", required=True, type=float)
    choice.add_argument("--decided-at")
    choice.add_argument("--reason")
    choice.add_argument("--confirmation-ref", required=True)
    choice.add_argument("--explicit", action="store_true")
    choice.add_argument(
        "--user-sized",
        action="store_true",
        help=(
            "明確標記這筆尺寸由使用者決定（--reason 必填）。系統本來就不給建議尺寸；"
            "5%% 單筆上限與 ETF 槓桿 cap 對所有非零選擇一律硬擋。"
        ),
    )
    choice.add_argument("--format", choices=("json", "markdown"), default="json")

    fill = subcommands.add_parser(
        "record-fill", help="在使用者手動下單後，明確回報 live fill。"
    )
    fill.add_argument("decision_id")
    fill.add_argument("--execution-ref", required=True)
    fill.add_argument("--shares", required=True, type=float)
    fill.add_argument("--price", required=True, type=float)
    fill.add_argument("--currency", required=True)
    fill.add_argument("--executed-at")
    fill.add_argument("--explicit", action="store_true")
    fill.add_argument("--format", choices=("json", "markdown"), default="json")

    # 保留 v1 low-level surface 供 deterministic fixtures／維護用途。
    assess = subcommands.add_parser(
        "assess", help="維護用低階相容入口；正常操作請使用 evaluate-signal。"
    )
    assess.add_argument("--input", default="-", help=argparse.SUPPRESS)
    return parser


def _read_json(source: str, stdin: TextIO) -> dict[str, Any]:
    text = stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    assert_safe_payload(value)
    return value


def _read_optional_json(source: str | None) -> Mapping[str, Any] | None:
    if source is None:
        return None
    value = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("assessment must be a JSON object")
    assert_safe_payload(value)
    return value


def _write_json(value: Any, stdout: TextIO) -> None:
    assert_safe_payload(value)
    json.dump(
        value,
        stdout,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    stdout.write("\n")


def _timestamp(value: str | None) -> str:
    return value or datetime.now(timezone.utc).isoformat()


def _open_store(args: argparse.Namespace) -> DecisionStore:
    configured = (args.store, args.private_root, args.repo_root)
    if any(configured):
        if not all(configured):
            raise ValueError("private store configuration is incomplete")
        return DecisionStore.open(
            args.store,
            private_root=args.private_root,
            repo_root=args.repo_root,
        )
    return open_default_store()


def _provider(current: WorkflowDataProvider | None) -> WorkflowDataProvider:
    if current is not None:
        return current
    from engine_d_runtime.bootstrap import build_default_runtime_provider

    return build_default_runtime_provider()


def _optional(builder: Any) -> dict[str, Any] | None:
    """取一份可缺席的首屏區塊。取不到就 `None`——不是空結果。

    ⚠ 這裡吞例外是刻意的，但吞掉的只有「這一區拿不到」，不是「這一區是空的」。
    brief 對 `None` 渲染「未提供」、對空結果渲染「沒有候選」，兩者不可互換（L12）。
    """

    try:
        return builder()
    except Exception:  # noqa: BLE001 — 缺一區不阻斷整份 brief
        return None


def _render(
    payload: Mapping[str, Any],
    *,
    format_name: str,
    stdout: TextIO,
    markdown_renderer,
) -> None:
    if format_name == "json":
        _write_json(payload, stdout)
    else:
        stdout.write(markdown_renderer(payload) + "\n")


def run(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    provider: WorkflowDataProvider | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    args = build_parser().parse_args(argv)
    store: DecisionStore | None = None
    try:
        store = _open_store(args)
        if args.command == "evaluate-signal":
            result = evaluate_signal(
                store,
                _provider(provider),
                EvaluationRequest(
                    raw_signal=args.signal,
                    source_url=args.source_url,
                    ticker_hint=args.ticker,
                    company_hint=args.company,
                    company_id_hint=args.company_id,
                    thesis=args.thesis,
                    catalyst=args.catalyst,
                    disproof=args.disproof,
                    expiry=args.expiry,
                    as_of=args.as_of,
                    execution_intent=args.intent,
                    direction=args.direction,
                    source_id=args.source_id,
                    source_traced=args.source_traced,
                    evidence_tier=args.evidence_tier,
                    confirm_holdings=args.confirm_holdings,
                    assessment=_read_optional_json(args.assessment),
                ),
            )
            _render(
                result,
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=render_workflow_markdown,
            )
        elif args.command == "reassess":
            result = reassess(
                store,
                _provider(provider),
                args.target_id,
                as_of=args.as_of,
                execution_intent=args.intent,
                ticker_hint=args.ticker,
                company_hint=args.company,
                company_id_hint=args.company_id,
                confirm_holdings=args.confirm_holdings,
                assessment=_read_optional_json(args.assessment),
                catalyst=args.catalyst,
                disproof=args.disproof,
                expiry=args.expiry,
            )
            _render(
                result,
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=render_workflow_markdown,
            )
        elif args.command == "close":
            from identity.registry import get_registry

            from .outcomes import close_probe

            runtime = _provider(provider)
            shadow = store.get_shadow(args.cohort_id)
            identity_row = store.cohort_identity(args.cohort_id)
            identity = runtime.resolve_identity(
                company_id_hint=identity_row.get("company_id"),
                ticker_hint=identity_row.get("research_ticker"),
            )
            now = datetime.now(timezone.utc).isoformat()
            snapshot = runtime.snapshot(identity=identity, evaluation_at=now)
            company = get_registry().company(str(identity_row.get("company_id") or ""))
            benchmark_symbol = getattr(company, "benchmark_symbol", "QQQ") if company else "QQQ"
            # 沒有 Shadow 錨點就沒有可歸因的起點；此時 benchmark 一併標 unavailable，
            # close_probe 會誠實輸出 market_return_status=unknown，而不是用 0 冒充。
            benchmark = (
                runtime.benchmark_snapshot(
                    symbol=benchmark_symbol, since=str(shadow.as_of)
                )
                if shadow.status == "observed" and shadow.as_of
                else {"status": "unavailable"}
            )
            result = close_probe(
                store,
                args.cohort_id,
                terminal_status=args.terminal_status,
                claim_correctness=args.claim_correctness,
                current_market=dict(snapshot.market),
                benchmark=benchmark,
                reason=args.reason,
                evidence_refs=tuple(args.evidence_ref),
                effective_at=now,
            )
            _render(
                {
                    "cohort_id": args.cohort_id,
                    "terminal_status": args.terminal_status,
                    "benchmark_symbol": benchmark_symbol,
                    "outcome": getattr(result, "payload", None) or str(result),
                },
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=None,
            )
        elif args.command == "today":
            evaluation_at = _timestamp(args.as_of)
            runtime = _provider(provider)
            try:
                holdings = runtime.current_holdings(
                    evaluation_at=evaluation_at
                )
            except Exception:
                holdings = {"status": "unavailable"}
            # 首屏是瓶頸排序在前、NAV 比例在後。兩者都需要 `decision_lab` 不得 import
            # 的 authority（Neo4j／Google Sheet），所以在這一層取好再注入。
            # 兩者各自 fail-soft：缺席時 brief 照常渲染並明說「未提供」，不是「沒有候選」。
            #
            # `briefing` 是 B6 之後的組裝層：它看得到 alpha／portfolio／Engine D
            # 三邊，`cli.py` 本身是 composition root，所以在這裡 import 是正確方向。
            from briefing.render import render_today_markdown
            from briefing.today import build_today_brief
            from engine_d_runtime.adapters import (
                fetch_identity_alignment,
                fetch_nav_exposure,
                fetch_ranking_view,
            )

            annotations = ranking_annotations(store, as_of=evaluation_at)
            ranking = _optional(
                lambda: fetch_ranking_view(
                    weakest_axes=annotations["weakest_axes"],
                    disproofs=annotations["disproofs"],
                )
            )
            nav_exposure = _optional(fetch_nav_exposure)
            identity_alignment = _optional(fetch_identity_alignment)
            # Alpha Card 精簡摘要（2026-09-05）：對可行動排序前段的標的各組一份 canonical
            # view 再壓成一列。同樣 fail-soft：整批讀不到就 None（「未提供」），單檔讀不到
            # 由 fetch_alpha_cards 自己降級成那一列的 unavailable。沒有排序就沒有候選 → None。
            from briefing.alpha_view.sources import fetch_alpha_cards, tickers_from_ranking

            alpha_cards = (
                _optional(lambda: fetch_alpha_cards(tickers_from_ranking(ranking)))
                if ranking else None
            )
            brief = build_today_brief(
                store,
                as_of=evaluation_at,
                current_holdings=holdings,
                provider=runtime,
                ranking=ranking,
                nav_exposure=nav_exposure,
                identity_alignment=identity_alignment,
                alpha_cards=alpha_cards,
            )
            _render(
                brief,
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=render_today_markdown,
            )
        elif args.command == "references":
            result = build_reference_options(
                store,
                args.target_id,
                assessment=_read_optional_json(args.assessment),
            )
            _render(
                result,
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=render_reference_options_markdown,
            )
        elif args.command == "assessment-scaffold":
            from pathlib import Path as _Path

            from .references import _resolve_context, build_assessment_scaffold

            _decision, bundle = _resolve_context(store, args.target_id)
            scaffold_payload = build_assessment_scaffold(
                bundle.payload.get("reference_index") or {}
            )
            out_path = _Path(
                args.out
                or f"library/private/decision_lab/assessment_scaffold_{bundle.cohort_id}.json"
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(scaffold_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summary = {
                "out": str(out_path),
                "cohort_id": bundle.cohort_id,
                "context_digest": bundle.digest,
                "axes": {
                    axis: len(body.get("evidence_refs") or [])
                    for axis, body in scaffold_payload.items()
                },
                "note": "引用已預填、判斷留白；填完 reason/level 後用 "
                "`decision_lab references <cohort> --assessment <out>` 驗證再 reassess。",
            }
            # variant perception 提醒（2026-09-02 cohort 是終點）：assessment 是研究
            # 收尾動作，順帶點名 thesis 差異點還沒寫的 cohort——只提示不阻擋。
            vp_reader = getattr(store, "latest_variant_perception", None)
            if callable(vp_reader) and vp_reader(bundle.cohort_id) is None:
                summary["variant_perception"] = (
                    "未寫——收尾前補一句「市場隱含 X／本 thesis 認為 Y／催化劑 Z」："
                    f"decision_lab variant-perception {bundle.cohort_id} --text …"
                )
            print(json.dumps(summary, ensure_ascii=False, indent=2), file=stdout)
        elif args.command == "variant-perception":
            if args.text:
                thesis_id = store.record_variant_perception(
                    args.cohort_id,
                    variant_perception=args.text,
                    supersedes_id=args.supersedes,
                )
                print(
                    json.dumps(
                        {"thesis_id": thesis_id, "cohort_id": args.cohort_id},
                        ensure_ascii=False,
                    ),
                    file=stdout,
                )
            else:
                current = store.latest_variant_perception(args.cohort_id)
                print(
                    json.dumps(
                        current or {"cohort_id": args.cohort_id, "variant_perception": None},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    file=stdout,
                )
        elif args.command == "card":
            card = build_action_card(store, args.decision_id, as_of=args.as_of)
            _render(
                card,
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=render_markdown,
            )
        elif args.command == "record-choice":
            decided_at = _timestamp(args.decided_at)
            choice_id = record_live_choice(
                store,
                args.decision_id,
                selected_weight=args.selected_weight,
                decided_at=decided_at,
                explicit=args.explicit,
                reason=args.reason,
                confirmation_ref=args.confirmation_ref,
                user_sized=args.user_sized,
            )
            # ⚠ 回報**實際持久化的** choice_type，不是旗標。U7 之後 store 對每一筆
            # 非零、非 override 的選擇一律寫 `user_sized`，所以「不帶旗標就回報
            # `system`」會說出一個系統已經不再做的事（系統不給尺寸）——輸出與 authority
            # 相反，比不輸出更糟。
            recorded = store.latest_live_choice(args.decision_id) or {}
            payload = {
                "status": "recorded",
                "choice_id": choice_id,
                "decision_id": args.decision_id,
                "choice_type": recorded.get("choice_type"),
            }
            _render(
                payload,
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=lambda item: (
                    f"# Live choice 已記錄\n\n- Decision：{item['decision_id']}\n"
                    f"- Choice：{item['choice_id']}"
                ),
            )
        elif args.command == "record-fill":
            fill_id = record_live_fill(
                store,
                args.decision_id,
                execution_ref=args.execution_ref,
                shares=args.shares,
                price=args.price,
                currency=args.currency.upper(),
                executed_at=_timestamp(args.executed_at),
                explicit=args.explicit,
            )
            payload = {
                "status": "recorded",
                "fill_id": fill_id,
                "decision_id": args.decision_id,
            }
            _render(
                payload,
                format_name=args.format,
                stdout=stdout,
                markdown_renderer=lambda item: (
                    f"# Live fill 已記錄\n\n- Decision：{item['decision_id']}\n"
                    f"- Fill：{item['fill_id']}"
                ),
            )
        else:
            request = _read_json(args.input, stdin)
            required = {
                "context_digest",
                "coverage_assessment_id",
                "assessment",
                "idempotency_key",
                "effective_at",
            }
            if set(request) != required:
                raise ValueError("assess input fields do not match the public contract")
            bundle = store.get_context_bundle(str(request["context_digest"]))
            coverage = store.get_coverage_result(
                str(request["coverage_assessment_id"])
            )
            result = assess_probe(
                store,
                bundle,
                coverage,
                request["assessment"],
                idempotency_key=str(request["idempotency_key"]),
                effective_at=str(request["effective_at"]),
            )
            _write_json(asdict(result), stdout)
        return 0
    except (
        ExecutionError,
        WorkflowError,
        RedactionError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        code = (
            "SENSITIVE_INPUT_REJECTED"
            if isinstance(exc, RedactionError)
            else "NOT_FOUND"
            if isinstance(exc, KeyError)
            else "IDEMPOTENCY_CONFLICT"
            if "idempotency" in str(exc).casefold()
            else "INVALID_REQUEST"
        )
        _write_json({"status": "error", "code": code}, stdout)
        return 2
    finally:
        if store is not None:
            store.close()


def main(argv: list[str] | None = None) -> int:
    return run(argv)
