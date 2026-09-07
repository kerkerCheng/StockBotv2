"""`python -m webapp <materialize|serve|status|verify>`。

⚠ **改任何 `python -m <module>` 命令字串前先走 sandbox impact review 五步**（OPERATIONS）——
`.codex/rules/stockbot-automations.rules` 的 exact prefix 會靜默打斷排程。本模組是新增的命令，
不動任何既有命令字串。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .store import ArtifactStore


def cmd_materialize(args: argparse.Namespace) -> int:
    """跑完整條鏈並寫下 artifact。**這是唯一會跑模型、連 DB、讀 private ledger 的入口。**"""
    from .materialize import materialize_many, write_vocabularies

    store = ArtifactStore(Path(args.dir) if args.dir else None)
    tickers = args.tickers or store.tickers()
    if not tickers:
        print("✗ 沒有指定 ticker，而 artifact 目錄也是空的——第一次請明寫要 materialize 哪幾檔",
              file=sys.stderr)
        return 2
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    results = materialize_many(tickers, as_of=as_of, store=store)
    vocab_path = write_vocabularies(store)
    failed = 0
    for ticker, path, reason in results:
        if path is None:
            failed += 1
            print(f"✗ {ticker}：{reason}", file=sys.stderr)
        else:
            size = path.stat().st_size
            print(f"✓ {ticker} → {path.name}（{size:,} bytes）")
    print(f"字彙表 → {vocab_path.name}")
    print(f"完成 {len(results) - failed}/{len(results)}；下一步：python -m webapp serve")
    return 1 if failed else 0


def cmd_serve(args: argparse.Namespace) -> int:
    """啟動 read-only HTTP server。**不 materialize、不重建、不寫任何東西。**"""
    import uvicorn

    from .api import bind_host, bind_port, create_app

    directory = Path(args.dir) if args.dir else None
    app = create_app(directory)
    host = args.host or bind_host()
    port = args.port or bind_port()
    store: ArtifactStore = app.state.store
    count = len(store.tickers())
    if count == 0:
        print("⚠ artifact 目錄是空的——APP 會正常啟動，但每一檔都會回 503（**不會自己重建**）。"
              "請先跑 `python -m webapp materialize <TICKER>`", file=sys.stderr)
    print(f"StockBot APP → http://{host}:{port}/（{count} 檔已 materialize）")
    print("外部存取請走 Cloudflare Tunnel ＋ Access（deploy/cloudflare/README.md）；本程式沒有帳號密碼系統。")
    uvicorn.run(app, host=host, port=port, log_level=args.log_level, access_log=False)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """列出每一份 artifact 的新鮮度與 readiness。壞掉的一併現形（INV-3）。"""
    store = ArtifactStore(Path(args.dir) if args.dir else None)
    rows = list(store.read_all())
    if args.format == "json":
        print(json.dumps([
            {"ticker": t,
             "ok": payload is not None,
             "reason": reason,
             "generated_at": None if payload is None else payload["generated_at"],
             "freshness": None if freshness is None else freshness.to_dict(),
             "readiness": None if payload is None else payload["readiness"]["state"],
             "content_digest": None if payload is None else payload["content_digest"],
             "freshness_identity": None if payload is None else payload["freshness_identity"]}
            for t, payload, freshness, reason in rows], ensure_ascii=False, indent=2))
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
    return 0 if all(p is not None for _, p, _, _ in rows) else 1


def cmd_verify(args: argparse.Namespace) -> int:
    """把每一份 artifact 重新驗一次（schema／digest／必要欄位）。CI 與備份後的健檢用。"""
    store = ArtifactStore(Path(args.dir) if args.dir else None)
    bad = [(t, r) for t, p, _, r in store.read_all() if p is None]
    for ticker, reason in bad:
        print(f"✗ {ticker}：{reason}", file=sys.stderr)
    total = len(store.tickers())
    print(f"{total - len(bad)}/{total} 份 artifact 通過 fail-closed 驗證")
    return 1 if bad else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m webapp", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    mat = sub.add_parser("materialize", help="跑完整條鏈並寫下 artifact（唯一會跑模型的入口）")
    mat.add_argument("tickers", nargs="*", help="不給就重新 materialize 目錄裡已有的每一檔")
    mat.add_argument("--as-of", help="YYYY-MM-DD：point-in-time 視角")
    mat.add_argument("--dir", help="artifact 目錄（預設 library/private/app/analyst_view）")
    mat.set_defaults(func=cmd_materialize)

    serve = sub.add_parser("serve", help="啟動 read-only HTTP server（不重建任何東西）")
    serve.add_argument("--host", help="預設 127.0.0.1；綁其他介面需 STOCKBOT_APP_ALLOW_PUBLIC_BIND=1")
    serve.add_argument("--port", type=int, help="預設 8790")
    serve.add_argument("--dir", help="artifact 目錄")
    serve.add_argument("--log-level", default="warning")
    serve.set_defaults(func=cmd_serve)

    status = sub.add_parser("status", help="列出每份 artifact 的新鮮度與 readiness")
    status.add_argument("--dir")
    status.add_argument("--format", choices=("markdown", "json"), default="markdown")
    status.set_defaults(func=cmd_status)

    verify = sub.add_parser("verify", help="重新驗證全部 artifact（schema／digest／必要欄位）")
    verify.add_argument("--dir")
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
