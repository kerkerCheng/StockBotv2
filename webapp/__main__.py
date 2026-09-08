"""`python -m webapp <materialize|serve|status|verify>`。

⚠ **改任何 `python -m <module>` 命令字串前先走 sandbox impact review 五步**（OPERATIONS）——
`.codex/rules/stockbot-automations.rules` 的 exact prefix 會靜默打斷排程。本模組是新增的命令，
不動任何既有命令字串。

artifact 有兩類：per-ticker 的 Analyst View（`analyst_view/<TICKER>.json`）與跨標的的 state
（`state/<kind>.json`，目前只有 `ranking`）。兩類都是 derived cache，同一套 atomic write／
fail-closed read；差別只在主詞是 ticker 還是 kind。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .store import ArtifactStore, StateArtifactStore, resolve_state_dir


def _tracked_tickers() -> list[str]:
    """daily 追蹤中的 ticker。

    **與 pq1 drain 用的是同一個導出權威**（`engine_b.routine_config`：非 retired lifecycle ＋
    non-terminal Decision cohort ＋主題核心公司），不在這裡另寫一份清單——手寫清單會腐壞，
    而腐壞的方式是「某一檔安靜地不再被 materialize」，沒有任何東西會報錯。
    """
    from engine_b.routine_config import discover_tracked_tickers, load_config

    return sorted(discover_tracked_tickers(load_config()))


def _stores(args: argparse.Namespace) -> tuple[ArtifactStore, StateArtifactStore]:
    analyst_dir = Path(args.dir) if getattr(args, "dir", None) else None
    explicit_state = Path(args.state_dir) if getattr(args, "state_dir", None) else None
    return ArtifactStore(analyst_dir), StateArtifactStore(resolve_state_dir(analyst_dir, explicit_state))


def cmd_materialize(args: argparse.Namespace) -> int:
    """跑完整條鏈並寫下 artifact。**這是唯一會跑模型、連 DB、讀 private ledger 的入口。**"""
    from .materialize import (
        materialize_beta, materialize_coverage, materialize_many, materialize_positions,
        materialize_ranking, materialize_watches, write_vocabularies,
    )

    store, state_store = _stores(args)
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    failed = 0
    total = 0

    if args.ranking:
        total += 1
        try:
            path, payload = materialize_ranking(as_of=as_of, store=state_store)
        except Exception as exc:  # noqa: BLE001 — 理由原樣回報，不吞
            failed += 1
            print(f"✗ ranking：{type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        else:
            print(f"✓ ranking → {path.name}（{path.stat().st_size:,} bytes；"
                  f"可行動 {len(payload['rows'])} 條／純結構 {len(payload['structural_rows'])} 條）")

    if args.beta:
        total += 1
        try:
            path, payload = materialize_beta(store=state_store)
        except Exception as exc:  # noqa: BLE001 — 理由原樣回報，不吞
            failed += 1
            print(f"✗ beta：{type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        else:
            print(f"✓ beta → {path.name}（{path.stat().st_size:,} bytes；"
                  f"sleeve {len(payload['allocation']['sleeves'])} 格／商品 {len(payload['instruments'])} 檔）")

    if args.coverage:
        total += 1
        try:
            path, payload = materialize_coverage(store=state_store)
        except Exception as exc:  # noqa: BLE001 — 理由原樣回報，不吞
            failed += 1
            print(f"✗ coverage：{type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        else:
            counts = payload["counts"]
            print(f"✓ coverage → {path.name}（{path.stat().st_size:,} bytes；"
                  f"🔴 真缺口 {counts['research_gap_real']}／🟡 建模待補 {counts['modelling_gap']}）")

    if args.watches:
        total += 1
        try:
            path, payload = materialize_watches(store=state_store)
        except Exception as exc:  # noqa: BLE001 — 理由原樣回報，不吞
            failed += 1
            print(f"✗ watches：{type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        else:
            k = payload["counters"]
            print(f"✓ watches → {path.name}（{path.stat().st_size:,} bytes；"
                  f"在等 {k['active']}／停滯 {k['stalled']}／fired 未消化 {k['fired_unconsumed']}）")

    if args.positions:
        total += 1
        try:
            path, payload = materialize_positions(store=state_store)
        except Exception as exc:  # noqa: BLE001 — 理由原樣回報，不吞
            failed += 1
            print(f"✗ positions：{type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        else:
            print(f"✓ positions → {path.name}（{path.stat().st_size:,} bytes；"
                  f"逐檔 {len(payload['rows'])}／真實成交 {len(payload['live']['tickers'])} 檔）")

    # 不給 ticker 且沒要求 ranking ＝ 重跑目錄裡已有的每一檔（原行為）。
    # 只給 --ranking ＝ 只做 ranking，不順手重跑單檔（那是另一件事，也是另一段時間）。
    state_only = bool(args.ranking or args.beta or args.coverage or args.watches or args.positions)
    tickers = list(args.tickers) if args.tickers else ([] if state_only else store.tickers())
    if args.tracked:
        tracked = _tracked_tickers()
        print(f"追蹤中 {len(tracked)} 檔（來源：thesis lifecycle ＋ Decision cohort ＋主題核心公司）")
        tickers = sorted(set(tickers) | set(tracked))
    if not tickers and not state_only:
        print("✗ 沒有指定 ticker，而 artifact 目錄也是空的——第一次請明寫要 materialize 哪幾檔",
              file=sys.stderr)
        return 2
    if tickers:
        results = materialize_many(tickers, as_of=as_of, store=store)
        vocab_path = write_vocabularies(store)
        total += len(results)
        for ticker, path, reason in results:
            if path is None:
                failed += 1
                print(f"✗ {ticker}：{reason}", file=sys.stderr)
            else:
                size = path.stat().st_size
                print(f"✓ {ticker} → {path.name}（{size:,} bytes）")
        print(f"字彙表 → {vocab_path.name}")
    print(f"完成 {total - failed}/{total}；下一步：python -m webapp serve")
    return 1 if failed else 0


def cmd_serve(args: argparse.Namespace) -> int:
    """啟動 read-only HTTP server。**不 materialize、不重建、不寫任何東西。**"""
    import uvicorn

    from .api import bind_host, bind_port, create_app

    directory = Path(args.dir) if args.dir else None
    state_directory = Path(args.state_dir) if args.state_dir else None
    app = create_app(directory, state_directory)
    host = args.host or bind_host()
    port = args.port or bind_port()
    store: ArtifactStore = app.state.store
    state_store: StateArtifactStore = app.state.state_store
    count = len(store.tickers())
    if count == 0:
        print("⚠ artifact 目錄是空的——APP 會正常啟動，但每一檔都會回 503（**不會自己重建**）。"
              "請先跑 `python -m webapp materialize <TICKER>`", file=sys.stderr)
    missing = state_store.missing_kinds()
    if missing:
        print(f"⚠ state artifact 缺席：{', '.join(missing)}——對應頁面會回 503（**不會自己重建**）。"
              f"請跑 `python -m webapp materialize --{missing[0]}`", file=sys.stderr)
    present = ", ".join(state_store.kinds()) or "無"
    print(f"StockBot APP → http://{host}:{port}/（{count} 檔已 materialize；state：{present}）")
    print("外部存取請走 Cloudflare Tunnel ＋ Access（deploy/cloudflare/README.md）；本程式沒有帳號密碼系統。")
    uvicorn.run(app, host=host, port=port, log_level=args.log_level, access_log=False)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """列出每一份 artifact 的新鮮度與 readiness。壞掉的一併現形（INV-3）；缺席的 state kind 也現形。"""
    store, state_store = _stores(args)
    rows = list(store.read_all())
    state_rows = list(state_store.read_all())
    missing = state_store.missing_kinds()
    if args.format == "json":
        print(json.dumps({
            "analyst_views": [
                {"ticker": t,
                 "ok": payload is not None,
                 "reason": reason,
                 "generated_at": None if payload is None else payload["generated_at"],
                 "freshness": None if freshness is None else freshness.to_dict(),
                 "readiness": None if payload is None else payload["readiness"]["state"],
                 "content_digest": None if payload is None else payload["content_digest"],
                 "freshness_identity": None if payload is None else payload["freshness_identity"]}
                for t, payload, freshness, reason in rows],
            "state": [
                {"kind": kind,
                 "ok": payload is not None,
                 "reason": reason,
                 "generated_at": None if payload is None else payload["generated_at"],
                 "freshness": None if freshness is None else freshness.to_dict(),
                 "content_digest": None if payload is None else payload["content_digest"],
                 "freshness_identity": None if payload is None else payload["freshness_identity"]}
                for kind, payload, freshness, reason in state_rows],
            "state_missing": missing,
        }, ensure_ascii=False, indent=2))
        return 0
    print(f"# Materialized Analyst Views（{len(rows)} 份；目錄由 STOCKBOT_APP_ARTIFACT_DIR 決定）")
    for ticker, payload, freshness, reason in rows:
        if payload is None or freshness is None:
            print(f"- ✗ {ticker}：{reason}")
            continue
        state = payload["readiness"]["state"]
        blockers = payload["readiness"].get("blocker_details") or []
        kinds = "、".join(f"{b['panel']}={b['absence_kind']}" for b in blockers) or "—"
        print(f"- {ticker}｜{state}｜{freshness.state}（{freshness.age_hours:.1f}h）"
              f"｜refresh={payload['refresh']['overall']}｜blockers: {kinds}")
    print(f"# State artifacts（{len(state_rows)} 份；目錄由 STOCKBOT_APP_STATE_DIR 決定）")
    for kind, payload, freshness, reason in state_rows:
        if payload is None or freshness is None:
            print(f"- ✗ {kind}：{reason}")
            continue
        extra = ""
        if kind == "ranking":
            extra = f"｜可行動 {len(payload['rows'])} 條／純結構 {len(payload['structural_rows'])} 條"
        elif kind == "beta":
            extra = f"｜sleeve {len(payload['allocation']['sleeves'])} 格／商品 {len(payload['instruments'])} 檔"
        elif kind == "coverage":
            extra = (f"｜🔴 真缺口 {payload['counts']['research_gap_real']}"
                     f"／🟡 建模待補 {payload['counts']['modelling_gap']}")
        elif kind == "watches":
            extra = (f"｜在等 {payload['counters']['active']}"
                     f"／停滯 {payload['counters']['stalled']}")
        elif kind == "positions":
            extra = (f"｜逐檔 {len(payload['rows'])}"
                     f"／真實成交 {len(payload['live']['tickers'])} 檔")
        print(f"- {kind}｜{freshness.state}（{freshness.age_hours:.1f}h）"
              f"｜{payload['point_in_time']['mode']}{extra}")
    for kind in missing:
        print(f"- — {kind}：尚未 materialize（`python -m webapp materialize --{kind}`）")
    ok = (all(p is not None for _, p, _, _ in rows)
          and all(p is not None for _, p, _, _ in state_rows))
    return 0 if ok else 1


def cmd_verify(args: argparse.Namespace) -> int:
    """把每一份 artifact 重新驗一次（schema／digest／必要欄位）。CI 與備份後的健檢用。"""
    store, state_store = _stores(args)
    bad = [(t, r) for t, p, _, r in store.read_all() if p is None]
    bad += [(k, r) for k, p, _, r in state_store.read_all() if p is None]
    for subject, reason in bad:
        print(f"✗ {subject}：{reason}", file=sys.stderr)
    total = len(store.tickers()) + len(state_store.kinds())
    print(f"{total - len(bad)}/{total} 份 artifact 通過 fail-closed 驗證")
    return 1 if bad else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m webapp", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def _dirs(p: argparse.ArgumentParser) -> None:
        p.add_argument("--dir", help="analyst view artifact 目錄（預設 library/private/app/analyst_view）")
        p.add_argument("--state-dir",
                       help="state artifact 目錄（預設：--dir 底下的 state/，或 library/private/app/state）")

    mat = sub.add_parser("materialize", help="跑完整條鏈並寫下 artifact（唯一會跑模型的入口）")
    mat.add_argument("tickers", nargs="*", help="不給就重新 materialize 目錄裡已有的每一檔")
    mat.add_argument("--ranking", action="store_true",
                     help="另外（或只）materialize 跨標的瓶頸排序：rank_bottlenecks() 的輸出照抄")
    mat.add_argument("--beta", action="store_true",
                     help="另外（或只）materialize 資產配置：daily_beta_snapshot（--no-refresh --no-record-risk）的輸出照抄")
    mat.add_argument("--tracked", action="store_true",
                     help="materialize 所有追蹤中的標的（與 pq1 drain 同一個導出權威，不手寫清單）")
    mat.add_argument("--coverage", action="store_true",
                     help="另外（或只）materialize 覆蓋掃描：query.coverage_gaps.scan() 的輸出照抄")
    mat.add_argument("--watches", action="store_true",
                     help="另外（或只）materialize 事件監看：Event Watch registry ＋ 追源 backlog 的原值照抄")
    mat.add_argument("--positions", action="store_true",
                     help="另外（或只）materialize 部位與問責：outcome 腳本 collect() ＋ Decision Store 計數器")
    mat.add_argument("--as-of", help="YYYY-MM-DD：point-in-time 視角（單檔與 ranking 都適用）")
    _dirs(mat)
    mat.set_defaults(func=cmd_materialize)

    serve = sub.add_parser("serve", help="啟動 read-only HTTP server（不重建任何東西）")
    serve.add_argument("--host", help="預設 127.0.0.1；綁其他介面需 STOCKBOT_APP_ALLOW_PUBLIC_BIND=1")
    serve.add_argument("--port", type=int, help="預設 8790")
    _dirs(serve)
    serve.add_argument("--log-level", default="warning")
    serve.set_defaults(func=cmd_serve)

    status = sub.add_parser("status", help="列出每份 artifact 的新鮮度與 readiness")
    _dirs(status)
    status.add_argument("--format", choices=("markdown", "json"), default="markdown")
    status.set_defaults(func=cmd_status)

    verify = sub.add_parser("verify", help="重新驗證全部 artifact（schema／digest／必要欄位）")
    _dirs(verify)
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
