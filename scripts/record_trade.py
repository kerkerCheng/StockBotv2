"""記錄一筆手動成交：append 不可變事件紀錄，並更新 Google Sheet 持股與現金。

設計約束（2026-08-01 使用者定案，來由見對話與 `docs/brainstorms/`）：

1. **Sheet 仍是持股唯一權威**，本腳本只改「從券商通知逐字可讀」的數字
   （股數、現金）與由它們算出的 `avg_cost`；不碰市值、不碰 NAV、不碰其他欄位。
2. **人工編輯與程式寫入必須共存。** 因此按欄名定位（使用者會調欄序）、
   按內容比對定位列、且寫入前重讀確認現值——不符即整批中止。
   永遠只寫指定儲存格，絕不寫整列或範圍。
3. **預設 dry-run。** 要實際寫入必須加 `--apply`，且會先印出完整 diff。
4. **事件紀錄與持股狀態分開。** `library/trades/trade_log.jsonl` 是 append-only
   事件流（發生了什麼），不是持股真相（現在有多少）——後者永遠只有 Sheet。
5. **兩道資本硬擋住在這裡（2026-09-23，Phase 0 Step 0b.4／G12）。** 每一筆買進在寫 Sheet
   或 trade_log 之前都過 `risk/hard_caps.py`：5% 單筆 NAV 上限（alpha）與 ETF 槓桿 cap
   （nominal／effective）。超過或**量不到**一律 fail closed（dry-run 也擋）；
   `--override --reason "<理由>"` 才放行，且事件紀錄寫 `override_reason` 與整份 verdict 當收據。
   賣出不檢查（不增加曝險）。成交幣別 ≠ NAV 基準幣別時要給 `--fx-to-base`，否則量不到。
6. **alpha 成交附研究收據（2026-09-30，Phase 3 Step 3.8；使用者 2026-09-29 預先授權 #16）。**
   alpha／beta 只由 `risk/hard_caps.py` 的公開判別決定（賣出也判）。alpha 一律要 `--why "<一句>"`（碰 Sheet 之前就驗）；
   事件紀錄多一個 `research_receipt`：`declared`（現行 v2 敘事的宣告）與 `derived`（當天候選板與個股頁 artifact 的推導）
   分開記，組法住 `portfolio/research_receipt.py`。**alpha 買進沒有現行 v2 敘事 → fail closed（exit 4）**，
   `--no-narrative-override "<理由>"` 放行並留收據；它與硬擋的 `--override` **互不放行**。賣出可附
   `--disproof-watch <id>`（以來源歸屬驗它屬於這檔）。收據路徑只讀檔案與 Sheet readonly——不連 Neo4j、不打行情或 FX；
   artifact 缺席或過期只記 `derived: upstream_unavailable`，不擋成交（A3 不替 A5 做決定）。beta 行為不變。

用法：
    python scripts/record_trade.py --symbol QQQ --side buy --shares 10 \\
        --price 687.79 --executed-at 2026-07-31T13:04:53-04:00 \\
        --broker IB --note "IB Trade notification ..." [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

TRADE_LOG = _ROOT / "library" / "trades" / "trade_log.jsonl"

#: 硬擋擋下時的 exit code（與 2＝輸入／持股不合法區分，讓呼叫端與測試分得出「被煞車擋」）。
EXIT_HARD_CAP = 3
#: alpha 買進沒有現行 v2 敘事被擋下（Phase 3 Step 3.8）。與硬擋（3）、輸入錯誤（2）各自區分。
EXIT_NARRATIVE = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _number(value: str) -> float:
    """Sheet 的數字可能帶千分位或空白；空字串視為 0。"""
    cleaned = str(value).replace(",", "").strip()
    return float(cleaned) if cleaned else 0.0


def _trade_id(payload: dict) -> str:
    canonical = json.dumps(
        {k: payload[k] for k in ("executed_at", "broker", "symbol", "side", "shares", "price")},
        sort_keys=True,
        ensure_ascii=False,
    )
    return "tr_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _already_recorded(trade_id: str) -> bool:
    if not TRADE_LOG.exists():
        return False
    for line in TRADE_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line).get("trade_id") == trade_id:
            return True
    return False


def _append_trade(entry: dict) -> None:
    TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRADE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="記錄成交並更新 Google Sheet")
    ap.add_argument("--symbol", required=True, help="Sheet 的 symbol 欄值，如 QQQ")
    ap.add_argument("--side", required=True, choices=("buy", "sell"))
    ap.add_argument("--shares", required=True, type=float)
    ap.add_argument("--price", required=True, type=float)
    ap.add_argument("--executed-at", required=True, help="成交時間（ISO-8601，含時區）")
    ap.add_argument("--broker", default="IB", help="Sheet 的 broker 欄值")
    ap.add_argument("--currency", default="USD")
    ap.add_argument(
        "--cash-column",
        default="cash_usd",
        help="要扣款／入帳的現金欄名；傳 none 表示金流不經 Sheet 現金列（如台幣交割戶未入帳），只改股數與成本",
    )
    ap.add_argument("--account-ref", default="", help="遮蔽後的帳號，如 U****1599")
    ap.add_argument("--note", default="", help="券商通知逐字內容，供稽核")
    ap.add_argument("--apply", action="store_true", help="實際寫入；省略則只顯示 diff")
    ap.add_argument(
        "--log-only",
        action="store_true",
        help="只記事件、不碰 Sheet。用於「已手動更新過 Sheet」的成交——"
        "腳本無法自行判斷這件事，必須由使用者明確聲明。",
    )
    ap.add_argument(
        "--fx-to-base",
        type=float,
        default=None,
        help="成交幣別對 NAV 基準幣別的匯率（1 成交幣 = X 基準幣）；幣別不同且未提供時硬擋量不到、fail closed",
    )
    ap.add_argument(
        "--override",
        action="store_true",
        help="硬擋擋下時仍放行；必須同時給 --reason，理由與整份 verdict 會寫進事件紀錄當收據",
    )
    ap.add_argument("--reason", default="", help="override 的理由（--override 必填）")
    ap.add_argument("--why", default=None,
                    help="alpha 成交必填：為什麼現在買／賣的一句話（寫進研究收據）；beta 不收")
    ap.add_argument("--no-narrative-override", default=None, metavar="理由",
                    help="alpha 買進沒有現行 v2 敘事時放行，理由寫進收據；**不放行**硬擋（那要 --override）")
    ap.add_argument("--disproof-watch", default=None, metavar="WATCH_ID",
                    help="alpha 賣出：觸發這次賣出的反證 watch id（以來源歸屬驗它屬於這檔）")
    return ap


def _today():
    """排程時區的今天（與 daily、候選板 artifact 的 today 同一個定義）。"""
    from engine_b import event_watch as ew

    return ew._today()


def _shown(path: Path) -> str:
    """顯示用路徑：repo 內印相對路徑，repo 外（測試的暫存 log）印絕對路徑——顯示不得讓成交 crash。"""
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return str(path)


def _research_inputs(symbol: str, *, today) -> dict:
    """研究收據的原料——**一次讀好**：Sheet 那一列（readonly，只為解析公司）、敘事 ledger、watch registry、
    thesis lifecycle、讀圖 ledger（騎的那幾份寫入當時的 result_digest）、當天的候選板與個股頁 artifact。
    全是本機檔案或 Sheet readonly——**不連 Neo4j、不打行情或 FX**（讀圖對圖與邊緣判定已在 materialize 算好）。
    任何一項讀不到都記進 `problems`（或各自的 `*_error`），**不擋成交**（A3 不替 A5 做決定）。"""
    from portfolio import research_receipt

    problems: list[str] = []
    sheet_read = True
    try:
        from fetchers.gsheets import fetch_portfolio

        rows = list(fetch_portfolio(strict_operational=True))
    except Exception as exc:  # noqa: BLE001 — 讀不到就改由別名／registry 解析，照實記
        rows, sheet_read = [], False
        problems.append(f"Sheet 讀不到（{type(exc).__name__}）——公司改由 execution 別名／registry 解析")
    key = symbol.strip().upper()
    row = next((r for r in rows if str(r.get("ticker") or "").strip().upper() == key), None) or {"ticker": symbol}
    try:
        from identity.registry import get_registry
        from portfolio.holdings import resolve_holding, resolve_holdings

        registry = get_registry()
        resolved = resolve_holding(row, registry=registry)
    except Exception as exc:  # noqa: BLE001 — registry／別名讀不到＝解析不到（不猜），照實記
        registry = None
        resolved = {"company_id": None, "research_ticker": None, "source": None}
        problems.append(f"registry／execution 別名讀不到（{type(exc).__name__}）——公司解析不到")
    cid = resolved["company_id"]
    out: dict = {"company_id": cid, "research_ticker": resolved["research_ticker"],
                 "resolution_source": resolved["source"], "records": [], "narrative_readable": True,
                 "watches": [], "lifecycle": None, "reading_digests": {}, "candidates": None,
                 "candidates_error": None, "analyst": None, "analyst_error": None, "held_company": None,
                 "problems": problems}
    # 公司層級的「成交前有沒有持有」：同一家公司在 Sheet 任何一列股數 > 0（候選板「已持有」同一個層級；INV-1）。
    if sheet_read and cid and registry is not None:
        try:
            resolution = resolve_holdings(rows, registry=registry)
            out["held_company"] = any(r["company_id"] == cid and (r["shares"] or 0) > 0 and not r["cash"]
                                      for r in resolution["rows"])
        except Exception as exc:  # noqa: BLE001
            problems.append(f"Sheet 持股解析失敗（{type(exc).__name__}）——公司層級持有沒記")
    research = resolved["research_ticker"]
    if cid and not research:
        out["narrative_readable"] = False
        problems.append(f"registry 沒有 {cid} 的 research ticker——敘事 ledger 以 ticker 為鍵，無從對（不是「沒有敘事」）")
    if research:
        try:
            from alpha.providers.briefs import read_brief_records

            records, errors = read_brief_records(str(research))
            out["records"] = list(records)
            if errors:
                # 有壞行時 select_brief 可能退回較舊的一版——確認不了現行是哪一版，fail closed（3.8 R1）。
                out["narrative_readable"] = False
                problems.append(f"敘事 ledger 有 {len(errors)} 行解析失敗——確認不了現行是哪一版")
        except Exception as exc:  # noqa: BLE001 — 讀不到≠沒有（L11-5），照實記、買進 fail closed
            out["narrative_readable"] = False
            problems.append(f"敘事 ledger 讀不到（{type(exc).__name__}）")
    try:
        from engine_b import event_watch as ew

        out["watches"] = list(ew.load_watches().get("watches") or ())
    except Exception as exc:  # noqa: BLE001
        problems.append(f"watch registry 讀不到（{type(exc).__name__}）——收據沒有在盯的 watch")
    from engine_b.disproof import load_lifecycle

    out["lifecycle"] = load_lifecycle()
    if out["lifecycle"] is None:
        problems.append("thesis lifecycle 讀不到——thesis 來源的 watch 歸屬不到本檔")
    brief = research_receipt.current_brief(out["records"], today=today)
    for ride in getattr(brief, "rides", ()) or ():
        try:
            from alpha.providers.structure_readings import read_reading_records

            recs, reading_errors = read_reading_records(ride.node)
            hit = next((r for r in recs if r.reading_id == ride.reading_id), None)
            out["reading_digests"][ride.reading_id] = hit.result_digest if hit is not None else None
            if reading_errors:
                problems.append(f"讀圖 ledger {ride.node} 有 {len(reading_errors)} 行解析失敗")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"讀圖 ledger {ride.node} 讀不到（{type(exc).__name__}）")
    from webapp.store import ArtifactStore, StateArtifactStore

    try:
        out["candidates"], _fresh = StateArtifactStore().read("candidates")
    except Exception as exc:  # noqa: BLE001
        out["candidates_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    if research:
        try:
            out["analyst"], _fresh = ArtifactStore().read(str(research))
        except Exception as exc:  # noqa: BLE001
            out["analyst_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    else:
        # 沒有個股頁可對（不是「讀不到」——下一步是補 registry，不是修讀取；L12）。
        out["analyst_error"] = ("Sheet symbol 解析不到公司，沒有個股頁 artifact 可對" if not cid
                                else f"registry 沒有 {cid} 的 research ticker，對不到個股頁 artifact")
    return out


def _print_receipt(receipt: dict) -> None:
    from portfolio.research_receipt import NARRATIVE_STATES

    print(f"\n研究收據（alpha {receipt['side']}）：narrative＝{receipt['narrative']}"
          f"（{NARRATIVE_STATES[receipt['narrative']]}）｜公司 {receipt.get('company_id') or '解析不到'}"
          f"（{receipt.get('research_ticker') or '—'}；解析 {receipt.get('resolution') or '—'}）")
    print(f"  why：{receipt['why']}")
    declared = receipt.get("declared")
    if declared:
        cs = declared.get("candidate_state") or {}
        answers = declared.get("answers") or {}
        print(f"  declared：敘事 {declared['brief_id']}｜候選 {cs.get('state')}"
              f"{'（等 ' + str(cs.get('watch_id')) + '）' if cs.get('watch_id') else ''}"
              f"｜已定價 {answers.get('priced_in')}／數字裡 {answers.get('in_numbers')}"
              f"｜在處理中的 watch {len(declared.get('watches') or [])} 筆")
        for ride in declared.get("rides") or ():
            print(f"    騎 {ride['node']}（{ride['unit']}）{ride['reading_id']} digest "
                  f"{(ride.get('result_digest') or '讀不到')[:16]}")
    derived = receipt.get("derived") or {}
    if derived.get("status") == "available":
        cand = derived.get("candidate") or {}
        where = cand.get("derived") or cand.get("side") or (derived.get("candidate_note") if not cand else None) or "—"
        print(f"  derived：候選板 {derived.get('candidate_as_of')}｜推導 {where}"
              f"｜前提失效 {len(cand.get('preconditions') or [])}｜三題 {len(derived.get('three_questions') or [])} 行")
    else:
        print(f"  derived：upstream_unavailable——{derived.get('reason')}（不擋成交）")
    sheet = derived.get("sheet") or {}
    print(f"  Sheet：這一列成交前持有 {sheet.get('held_before_this_row')}｜公司層級 {sheet.get('held_before_company')}"
          f"（{sheet.get('sheet_state')}）")
    if receipt.get("narrative_override_reason"):
        print(f"  ⚠ 缺敘事放行：{receipt['narrative_override_reason']}")
    if receipt.get("disproof_watch"):
        dw = receipt["disproof_watch"]
        print(f"  觸發賣出的反證 watch：{dw['watch_id']}（{dw.get('status')}；來源 {dw.get('source_ref')}）")
    for problem in receipt.get("input_problems") or ():
        print(f"  · {problem}")


def _hard_cap_verdict(args: argparse.Namespace):
    """買進前過兩道硬擋；讀 Sheet 持股列（readonly scope）。回 `HardCapVerdict`。"""
    from fetchers.gsheets import fetch_portfolio
    from risk.hard_caps import check_trade_hard_caps, gross_in_base_currency

    if args.side != "buy":
        return check_trade_hard_caps(None, symbol=args.symbol, side=args.side, gross_base=None)
    try:
        rows = list(fetch_portfolio(strict_operational=True))
    except Exception as exc:  # noqa: BLE001 — 讀不到就是量不到，交給 verdict fail closed
        return check_trade_hard_caps(
            None, symbol=args.symbol, side=args.side, gross_base=None,
            gross_reason=f"持股列讀取失敗：{type(exc).__name__}",
        )
    base_currency = next(
        (str(r.get("base_currency") or "").strip().upper() for r in rows if r.get("base_currency")),
        None,
    )
    gross_base, gross_reason = gross_in_base_currency(
        gross=round(args.shares * args.price, 2),
        trade_currency=args.currency,
        base_currency=base_currency,
        fx_to_base=args.fx_to_base,
    )
    return check_trade_hard_caps(
        rows,
        symbol=args.symbol,
        side=args.side,
        gross_base=gross_base,
        gross_reason=gross_reason,
        already_in_sheet=bool(args.log_only),
    )


def _print_verdict(verdict) -> None:
    label = {
        "pass": "✓ 硬擋通過",
        "not_applicable": "－ 硬擋不適用",
        "blocked": "✗ 硬擋擋下",
        "unmeasurable": "✗ 硬擋量不到（fail closed）",
    }[verdict.status]
    print(f"\n{label}（5% 單筆 NAV 上限／ETF 槓桿 cap；規則見 risk/hard_caps.py）")
    for reason in verdict.reasons:
        print(f"  · {reason}")
    measures = verdict.measures
    if "post_trade_weight" in measures:
        print(f"  · 成交後占 NAV {measures['post_trade_weight']:.2%}"
              f"（上限 {measures['single_position_nav_cap']:.0%}）")
    if "post_trade_nominal_weight" in measures:
        print(f"  · nominal_weight {measures['post_trade_nominal_weight']:.2%}"
              f"（cap {measures['leveraged_nominal_cap']:.0%}）；"
              f"effective_weight {measures['post_trade_effective_weight']:.2%}"
              f"（cap {measures['leveraged_effective_cap']:.0%}）")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.override and not args.reason.strip():
        print("✗ --override 必須附 --reason「<理由>」；沒有理由的放行不留收據，拒絕", file=sys.stderr)
        return 2
    if args.reason.strip() and not args.override:
        print("✗ --reason 只在 --override 時有意義；沒有 override 的成交不需要理由", file=sys.stderr)
        return 2
    # alpha／beta 只由硬擋的公開判別決定（Phase 3 Step 3.8；賣出也判——不靠 verdict 間接取得）。
    from risk.hard_caps import is_beta_symbol

    is_beta = is_beta_symbol(args.symbol)
    # 以「有沒有給這個旗標」判斷，不以值的真假——空字串代表使用者以為給了（例：shell 變數展開成空；3.8 R1）。
    research_flags = [flag for flag, given in (("--why", args.why is not None),
                                               ("--no-narrative-override", args.no_narrative_override is not None),
                                               ("--disproof-watch", args.disproof_watch is not None)) if given]
    if is_beta and research_flags:
        print(f"✗ {args.symbol} 是 beta：不需要研究收據，{'／'.join(research_flags)} 只用在 alpha", file=sys.stderr)
        return 2
    if not is_beta:
        if not (args.why or "").strip():
            print("✗ alpha 成交必須附 --why「<一句：為什麼現在買／賣>」——它寫進研究收據（Phase 3 Step 3.8）",
                  file=sys.stderr)
            return 2
        if args.no_narrative_override is not None and (args.side != "buy" or not args.no_narrative_override.strip()):
            print("✗ --no-narrative-override 只用在 alpha 買進，而且必須附理由", file=sys.stderr)
            return 2
        if args.disproof_watch is not None and (args.side != "sell" or not args.disproof_watch.strip()):
            print("✗ --disproof-watch 只用在 alpha 賣出（觸發這次賣出的反證），而且要給 watch id", file=sys.stderr)
            return 2
    from fetchers.gsheets import locate_portfolio_cells, write_portfolio_cells

    gross = round(args.shares * args.price, 2)
    signed_shares = args.shares if args.side == "buy" else -args.shares

    # 同一檔可能分屬多個券商（如 LON:VWRA 同時在 IB 與 FUBON），
    # 持股列必須用 symbol＋broker 一起定位，否則兩列即歧義中止。
    skip_cash = args.cash_column.strip().lower() in ("", "none")
    requests = [
        {"match": {"symbol": args.symbol, "broker": args.broker}, "column": "shares"},
        {"match": {"symbol": args.symbol, "broker": args.broker}, "column": "avg_cost"},
    ]
    if not skip_cash:
        requests.append(
            {"match": {"broker": args.broker, "bucket": "CASH"}, "column": args.cash_column}
        )
    cells = locate_portfolio_cells(requests)
    shares_cell, cost_cell = cells[0], cells[1]
    cash_cell = None if skip_cash else cells[2]
    old_shares = _number(shares_cell["current"])
    old_cost = _number(cost_cell["current"])
    old_cash = 0.0 if skip_cash else _number(cash_cell["current"])

    new_shares = old_shares + signed_shares
    if new_shares < 0:
        print(f"✗ 賣出 {args.shares} 股會使持股變成 {new_shares}，中止", file=sys.stderr)
        return 2
    if args.side == "buy":
        # 加權平均成本只在買進時變動；賣出不改變成本基礎。
        new_cost = (
            round((old_shares * old_cost + args.shares * args.price) / new_shares, 2)
            if new_shares > 0
            else 0.0
        )
    else:
        new_cost = old_cost
    new_cash = round(old_cash - gross if args.side == "buy" else old_cash + gross, 2)

    payload = {
        "executed_at": args.executed_at,
        "broker": args.broker,
        "symbol": args.symbol,
        "side": args.side,
        "shares": args.shares,
        "price": args.price,
    }
    trade_id = _trade_id(payload)

    print(f"成交：{args.side.upper()} {args.shares:g} {args.symbol} @ {args.price} "
          f"{args.currency}　總額 {gross:,.2f}")
    print(f"trade_id：{trade_id}")
    print(f"\n將變更的儲存格（僅此{'兩' if skip_cash else '三'}格，其餘欄位不動）：")
    print(f"  {shares_cell['a1']:<16} shares          {old_shares:g} → {new_shares:g}")
    print(f"  {cost_cell['a1']:<16} avg_cost        {old_cost} → {new_cost}"
          f"   ← 由本腳本計算，非通知逐字值")
    if skip_cash:
        print("  （現金列不改：--cash-column none，金流不經 Sheet 現金列，由使用者另行更新）")
    else:
        print(f"  {cash_cell['a1']:<16} {args.cash_column:<15} {old_cash:,.2f} → {new_cash:,.2f}")

    # 兩道硬擋：dry-run 也擋（讓人在 --apply 之前就看到會被擋），override 留收據。
    verdict = _hard_cap_verdict(args)
    _print_verdict(verdict)
    receipt: dict = {"hard_cap_check": verdict.to_dict()}
    if not verdict.allows:
        if not args.override:
            print("\n✗ 未寫入。要放行請加 --override --reason「<理由>」（理由與 verdict 會寫進事件紀錄）。",
                  file=sys.stderr)
            return EXIT_HARD_CAP
        receipt["override_reason"] = args.reason.strip()
        print(f"\n⚠ override 放行：{args.reason.strip()}（將寫進事件紀錄）")

    # 研究收據（alpha；Phase 3 Step 3.8）。順序：locate → 硬擋 → 收據；dry-run 也組、也印、也擋。
    # 兩個放行互不放行：硬擋的 --override 不放行缺敘事，--no-narrative-override 不放行硬擋（上面已先過硬擋）。
    if not is_beta:
        from portfolio import research_receipt

        try:
            today = _today()
            today_problem = None
        except Exception as exc:  # noqa: BLE001 — 排程時區讀不到：退回本機日期、照實記，不讓成交 crash
            from datetime import date

            today, today_problem = date.today(), f"排程時區讀不到（{type(exc).__name__}）——「今天」退回本機日期"
        inputs = _research_inputs(args.symbol, today=today)
        if today_problem:
            inputs["problems"].append(today_problem)
        brief = research_receipt.current_brief(inputs["records"], today=today)
        state = research_receipt.narrative_state(inputs["company_id"], brief,
                                                 readable=bool(inputs.get("narrative_readable", True)))
        watch_summary = None
        if args.disproof_watch is not None:
            watch_summary, error = research_receipt.check_disproof_watch(
                args.disproof_watch, company_id=inputs["company_id"], ticker=inputs["research_ticker"],
                records=inputs["records"], brief=brief, watches=inputs["watches"], lifecycle=inputs["lifecycle"])
            if error:
                print(f"✗ --disproof-watch：{error}", file=sys.stderr)
                for problem in inputs["problems"]:
                    print(f"  · {problem}", file=sys.stderr)
                return 2
        if args.side == "buy" and state == "present" and args.no_narrative_override is not None:
            print("✗ 這檔有現行 v2 敘事，不需要 --no-narrative-override（放行只給缺敘事的買進）", file=sys.stderr)
            return 2
        research = research_receipt.build_receipt(
            side=args.side, why=(args.why or "").strip(), symbol=args.symbol, today=today, inputs=inputs,
            # --log-only 時 Sheet 已是成交後的狀態，推不出「成交前有沒有持有」——照實記 None 並標明（不回推）。
            held_before=(None if args.log_only else old_shares > 0), log_only=bool(args.log_only),
            narrative_override=(args.no_narrative_override.strip() if args.no_narrative_override else None),
            disproof_watch=watch_summary)
        _print_receipt(research)
        if args.side == "buy" and state != "present" and args.no_narrative_override is None:
            print(f"\n✗ 未寫入。alpha 買進需要現行 v2 敘事（現在：{research_receipt.NARRATIVE_STATES[state]}）。"
                  "先寫敘事（python -m alpha brief <T> --add spec.json），或加 --no-narrative-override「<理由>」放行"
                  "（理由寫進收據；它不放行硬擋）。", file=sys.stderr)
            return EXIT_NARRATIVE
        receipt["research_receipt"] = research

    if _already_recorded(trade_id):
        print("\n⚠ 這筆成交已在 trade_log.jsonl 中；重複執行不會再寫事件紀錄。")

    if args.log_only:
        if _already_recorded(trade_id):
            print("\n這筆成交已在事件紀錄中，未重複寫入。")
            return 0
        _append_trade(
            {
                "trade_id": trade_id,
                **payload,
                "currency": args.currency,
                "gross_amount": gross,
                "account_ref": args.account_ref,
                "note": args.note,
                "recorded_at": _now(),
                "sheet_writes": [],
                "sheet_update": "manual_by_user",
                **receipt,
            }
        )
        print(f"\n✓ 事件已記於 {_shown(TRADE_LOG)}；"
              "Sheet 未被改動（已由使用者手動更新）。")
        print("  上方 diff 僅供對照，不是待執行的變更。")
        return 0

    if not args.apply:
        print("\n（dry-run）確認無誤後加 --apply 實際寫入。")
        print("  若這筆你已手動改過 Sheet，改用 --log-only 只記事件、不重複計算。")
        return 0

    writes = [
        {"a1": shares_cell["a1"], "expected": shares_cell["current"], "value": new_shares},
        {"a1": cost_cell["a1"], "expected": cost_cell["current"], "value": new_cost},
    ]
    if not skip_cash:
        writes.append({"a1": cash_cell["a1"], "expected": cash_cell["current"], "value": new_cash})
    result = write_portfolio_cells(writes)
    if not _already_recorded(trade_id):
        _append_trade(
            {
                "trade_id": trade_id,
                **payload,
                "currency": args.currency,
                "gross_amount": gross,
                "account_ref": args.account_ref,
                "note": args.note,
                "recorded_at": _now(),
                "sheet_writes": result["written"],
                **receipt,
            }
        )
    print(f"\n✓ 已寫入 {len(result['written'])} 格，事件已記於 {_shown(TRADE_LOG)}")
    print("  Sheet 仍是持股唯一權威；市值與 NAV 未被本腳本改動。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
