"""記錄一筆手動成交：append 不可變事件紀錄，並更新 Google Sheet 持股與現金。

設計約束（2026-08-01 使用者定案，來由見對話與 `docs/brainstorms/`）：

1. **Sheet 仍是持股唯一權威**，本腳本只改「從券商通知逐字可讀」的數字
   （股數、現金）與由它們算出的 `avg_cost`；不碰市值、不碰 NAV、不碰其他欄位。
2. **人工編輯與程式寫入必須共存。** 因此按欄名定位（使用者會調欄序）、
   按內容比對定位列、且寫入前重讀確認現值——不符即整批中止。
   永遠只寫指定儲存格，絕不寫整列或範圍。**唯一例外是首次建倉（`--open-position`，2026-09-30 使用者定案）**：
   新插的那一列本來不存在、沒有使用者手填的值可蓋，公式從標準列複製、寫完回讀驗證，不過就刪掉還原（`fetchers/gsheets.py`）。
   同一筆成交重跑 `--apply` 一律拒絕；一筆成交只讀一次 Sheet，同一份交給定位、硬擋與收據。
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
7. **回填舊成交（2026-10-02，Phase 5 Step 5.3；使用者定案 #2）。** 收據機制上線（2026-09-30）之前的 alpha 成交，
   用 `--log-only --backfill-before-receipts "<理由>"` 補進 trade_log：成交日必須早於上線日、只收 alpha、必附理由；
   收據寫 `narrative: backfilled`，**不讀敘事、候選板、個股頁**（不拿今天的判斷冒充當時，INV-6）。硬擋照算
   （`--log-only` 語意）；`--apply`／`--open-position`／Sheet 讀寫路徑一行不動。回填哪幾筆由使用者照 Sheet 下指令。

用法：
    python scripts/record_trade.py --symbol QQQ --side buy --shares 10 \\
        --price 687.79 --executed-at 2026-07-31T13:04:53-04:00 \\
        --broker IB --note "IB Trade notification ..." [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
#: 開列請求丟例外、第一次回讀判成「此刻沒套用」時，隔幾秒再讀一次（伺服器可能稍後才套用；R2 第三次覆核）。
ABSENT_RECHECK_SECONDS = 3.0


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


def _trade_key(entry: dict) -> tuple | None:
    """同一筆成交的正規化鍵：代號大寫、券商不分大小寫、成交時間換成 UTC、股數與價格轉數字（R2 2026-09-30：
    原本比原始字串，`axti` 或換一種時區寫法重跑就繞過重跑防呆）。解析不了回 None（只比 trade_id）。"""
    try:
        when = datetime.fromisoformat(str(entry["executed_at"]).replace("Z", "+00:00"))
        when = when.astimezone(timezone.utc).isoformat() if when.tzinfo else when.isoformat()
        return (str(entry["symbol"]).strip().upper(), str(entry["broker"]).strip().casefold(),
                str(entry["side"]).strip().lower(), float(entry["shares"]), float(entry["price"]), when)
    except (KeyError, TypeError, ValueError):
        return None


def _already_recorded(trade_id: str, payload: dict | None = None) -> bool:
    if not TRADE_LOG.exists():
        return False
    key = _trade_key(payload) if payload else None
    for line in TRADE_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("trade_id") == trade_id or (key is not None and _trade_key(entry) == key):
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
    ap.add_argument("--broker", default=None, help="Sheet 的 broker 欄值（預設 IB；--open-position 時必須明給）")
    ap.add_argument("--currency", default=None,
                    help="成交幣別（沒給時是 USD；既有列必須等於 Sheet 那一列的 currency，對不上就拒收；"
                         "--open-position 時必須明給）")
    ap.add_argument(
        "--cash-column",
        default=None,
        help="要扣款／入帳的現金欄：cash_usd（預設）／cash_twd／none（金流不經 Sheet 現金列，只改股數與成本；"
             "日圓、歐元成交只能用 none）；必須與成交幣別一致",
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
    ap.add_argument("--open-position", action="store_true",
                    help="首次建倉：Sheet 還沒有這一列（symbol＋broker）時新增一列；必須明確給，避免打錯代號就開出新列")
    ap.add_argument("--bucket", default=None, help="--open-position 必填：新列的 bucket（例：觀察、CORE、大盤）")
    ap.add_argument("--company", default=None, help="--open-position 可選：新列的公司名")
    ap.add_argument("--also-at-other-broker", action="store_true",
                    help="--open-position：這個代號已在別家券商有列、真的是在新券商建倉時才給（預設拒收：多半是 --broker 給錯）")
    ap.add_argument("--backfill-before-receipts", default=None, metavar="理由",
                    help="回填收據機制上線（2026-09-30）前的舊 alpha 成交：只准配 --log-only、成交日要早於上線日、必附理由；"
                         "收據標 backfilled、不讀今天的敘事")
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


def _research_inputs(symbol: str, *, today, sheet_rows: list | None = None, sheet_error: str | None = None) -> dict:
    """研究收據的原料——**一次讀好**：Sheet 那一列（readonly，只為解析公司）、敘事 ledger、watch registry、
    thesis lifecycle、讀圖 ledger（騎的那幾份寫入當時的 result_digest）、當天的候選板與個股頁 artifact。
    全是本機檔案或 Sheet readonly——**不連 Neo4j、不打行情或 FX**（讀圖對圖與邊緣判定已在 materialize 算好）。
    任何一項讀不到都記進 `problems`（或各自的 `*_error`），**不擋成交**（A3 不替 A5 做決定）。
    `sheet_rows`：`main` 讀好的**同一份**持股列（2026-09-30：一筆成交只讀一次 Sheet）；`None`＝那一份解析不了。"""
    from portfolio import research_receipt

    problems: list[str] = []
    sheet_read = sheet_rows is not None
    rows = list(sheet_rows or [])
    if not sheet_read:
        problems.append(f"Sheet 讀不到（{sheet_error or '持股列解析失敗'}）——公司改由 execution 別名／registry 解析")
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
            held = [r for r in resolution["rows"] if r["company_id"] == cid and (r["shares"] or 0) > 0 and not r["cash"]]
            out["held_company"] = bool(held)
            from fetchers.gsheets import canonical_symbol

            out["company_held_symbols"] = sorted({canonical_symbol(str(r.get("ticker") or "")) for r in held})
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


def _backfill_refusal(args: argparse.Namespace, *, is_beta: bool) -> str | None:
    """`--backfill-before-receipts` 的入口檢查（碰 Sheet 之前；Phase 5 Step 5.3）。回拒收理由，或 None。

    只收「收據機制上線前的舊 alpha 成交、Sheet 已是現況」：成交日（排程時區）早於 `RECEIPT_EPOCH`、配 `--log-only`、
    附理由；不收 beta（本來就不需要收據）、不配任何會去讀今天判斷的旗標。"""
    if args.backfill_before_receipts is None:
        return None
    from portfolio.research_receipt import RECEIPT_EPOCH

    if not args.backfill_before_receipts.strip():
        return "必須附理由（例：「Sheet 已有這筆、trade_log 沒有」）——沒有理由的回填不留收據"
    if is_beta:
        return f"{args.symbol} 是 beta：beta 本來就不需要研究收據，直接用 --log-only 記事件"
    if not args.log_only:
        return "只准配 --log-only（回填的是 Sheet 上已經有的舊成交，不再改 Sheet）"
    if args.apply:
        return "--log-only 不寫 Sheet，--apply 在這裡沒有意義；拿掉 --apply 重跑"
    if args.no_narrative_override is not None or args.disproof_watch is not None:
        return "回填不讀今天的敘事與 watch——--no-narrative-override／--disproof-watch 在這裡沒有意義"
    # 日期閘門用排程時區、**讀不到就拒收**（R2-a NB4）：正常路徑的 `_local_date` 會退回本機時區（不讓成交 crash），
    # 但這裡是一道閘——回填不趕時間，閘門的輸入不得靜默換一個來源。
    try:
        from engine_b import event_watch as ew

        zone = ew._local_timezone()
    except Exception as exc:  # noqa: BLE001
        return f"排程時區讀不到（{type(exc).__name__}）——回填的日期閘門不退回本機時區；修好再跑"
    try:
        executed_on = datetime.fromisoformat(str(args.executed_at)).astimezone(zone).date()
    except (TypeError, ValueError):
        executed_on = None
    if executed_on is None or executed_on >= RECEIPT_EPOCH:
        return (f"成交日 {executed_on}（排程時區）不早於收據機制上線日 {RECEIPT_EPOCH}——這筆應該走正常路徑"
                "（照常 --log-only，收據會讀記錄當下的現行敘事）")
    return None


def _backfill_identity(symbol: str, sheet_rows: list | None) -> dict:
    """回填只解析公司身分（INV-1：走 `resolve_holding`，與正常收據同一支）。

    名冊**讀不到就讓例外上拋**、由呼叫端 fail closed（R2-a NB3）：吞成 `company_id: None` 的話，「名冊讀不到」與
    「名冊真的沒有這家」在 append-only 的收據裡同形（L12），而那一行之後改不了。名冊讀得到、只是沒有這家＝照實記 None。"""
    from identity.registry import get_registry
    from portfolio.holdings import resolve_holding

    key = symbol.strip().upper()
    row = next((r for r in (sheet_rows or []) if str(r.get("ticker") or "").strip().upper() == key), None) \
        or {"ticker": symbol}
    return resolve_holding(row, registry=get_registry())


def _print_receipt(receipt: dict) -> None:
    from portfolio.research_receipt import NARRATIVE_STATES

    print(f"\n研究收據（alpha {receipt['side']}）：narrative＝{receipt['narrative']}"
          f"（{NARRATIVE_STATES[receipt['narrative']]}）｜公司 {receipt.get('company_id') or '解析不到'}"
          f"（{receipt.get('research_ticker') or '—'}；解析 {receipt.get('resolution') or '—'}）")
    print(f"  why：{receipt['why']}")
    if receipt["narrative"] == "backfilled":
        print(f"  回填理由：{receipt.get('backfill_reason')}")
        print("  declared／derived：不補（當時沒有收據機制；不拿今天的敘事與候選板冒充當時）")
        return
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


def _hard_cap_verdict(args: argparse.Namespace, rows: list | None = None, rows_error: str | None = None):
    """買進前過兩道硬擋；用 `main` 讀好的**同一份**持股列（readonly scope）。回 `HardCapVerdict`。"""
    from risk.hard_caps import check_trade_hard_caps, gross_in_base_currency

    if args.side != "buy":
        return check_trade_hard_caps(None, symbol=args.symbol, side=args.side, gross_base=None)
    if rows is None:  # 讀不到或解析不了就是量不到，交給 verdict fail closed
        return check_trade_hard_caps(
            None, symbol=args.symbol, side=args.side, gross_base=None,
            gross_reason=f"持股列讀取失敗：{rows_error or '未知'}",
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
    if args.fx_to_base is not None and not (math.isfinite(args.fx_to_base) and args.fx_to_base > 0):
        # 0、負數、NaN、inf 在硬擋那一端會被當成「未提供」、收尾卻指路 --override（第三次覆核 N4、第四次 NB1）——入口就拒收。
        print(f"✗ --fx-to-base 必須是大於 0 的有限數（給的是 {args.fx_to_base}）：它是「1 成交幣等於多少 NAV 基準幣」",
              file=sys.stderr)
        return 2
    if args.open_position and (args.side != "buy" or args.log_only):
        print("✗ --open-position 只用在買進，而且要由本腳本寫 Sheet（不能配 --log-only）", file=sys.stderr)
        return 2
    if args.open_position and (not (args.bucket or "").strip() or args.bucket.strip().upper() == "CASH"):
        print("✗ --open-position 必須給 --bucket（例：觀察、CORE、大盤；不能是 CASH）——不猜新列歸哪一格", file=sys.stderr)
        return 2
    blank = [flag for flag, value in (("--broker", args.broker), ("--currency", args.currency),
                                      ("--cash-column", args.cash_column)) if value is not None and not value.strip()]
    if blank:  # 給了空字串＝使用者以為給了（例：shell 變數展開成空）——不退回預設（3.8 R1 同一條規則）
        print(f"✗ {'、'.join(blank)} 給了空字串——要用預設就別給這個旗標", file=sys.stderr)
        return 2
    try:
        if datetime.fromisoformat(args.executed_at.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("沒有時區")
    except ValueError as exc:
        print(f"✗ --executed-at 必須是含時區的 ISO-8601（例：2026-09-30T10:00:00-04:00）：{exc}", file=sys.stderr)
        return 2
    refused = _backfill_refusal(args, is_beta=is_beta)
    if refused:
        print(f"✗ --backfill-before-receipts：{refused}——未讀 Sheet、未寫入任何東西", file=sys.stderr)
        return 2
    if not args.open_position and (args.bucket is not None or args.company is not None or args.also_at_other_broker):
        print("✗ --bucket／--company／--also-at-other-broker 只在 --open-position（首次建倉）時有意義", file=sys.stderr)
        return 2
    if args.open_position:
        # 新列沒有既有的一列可以對：券商、幣別、現金欄的預設值會被照寫進 Sheet、灌進 NAV 公式（R2 2026-09-30 blocking：
        # 台股代號配預設 USD，市值高估約 31 倍、回讀驗證抓不到）——所以建倉時三個都必須明給，跟 --bucket 同一個規則。
        missing = [flag for flag, value in (("--broker", args.broker), ("--currency", args.currency),
                                            ("--cash-column", args.cash_column)) if not (value or "").strip()]
        if missing:
            print(f"✗ --open-position 必須明給 {'、'.join(missing)}——新列沒有既有列可以核對，不猜", file=sys.stderr)
            return 2
    currency_given = args.currency is not None
    args.broker = args.broker or "IB"
    args.currency = (args.currency or "USD").strip().upper()
    args.cash_column = (args.cash_column if args.cash_column is not None else "cash_usd").strip().lower()
    # 現金欄是封閉字彙（R2 覆核 N2：原本任何欄名都放行——`market_usd` 會定位到公式格）：Sheet 只有這兩個現金欄。
    cash_currency = {"cash_usd": "USD", "cash_twd": "TWD", "none": None}
    if args.cash_column not in cash_currency:
        print(f"✗ --cash-column 只收 {'／'.join(cash_currency)}（給的是 {args.cash_column!r}）", file=sys.stderr)
        return 2
    # 現金欄的幣別必須等於成交幣別——**兩條路徑都擋**（R2 2026-09-30 覆核 C1：原本只有建倉路徑檢查；既有列加碼日股／歐股
    # 沒給 --cash-column 時，預設的 cash_usd 會把日圓／歐元金額當美元扣掉，--apply 就照寫）。--log-only 不碰現金格，不擋。
    # 沒給 --currency 的那一半由下面「成交幣別對 Sheet 那一列的幣別」接住（第二次覆核 B1）。
    if not args.log_only and cash_currency[args.cash_column] and cash_currency[args.cash_column] != args.currency:
        fix = (f"請給 --cash-column cash_{args.currency.lower()} 或 none" if args.currency in ("USD", "TWD") else
               f"Sheet 沒有 {args.currency} 的現金欄——請給 --cash-column none（帳上的現金另行手動更新）")
        # 給了 --currency 卻給錯時，這裡還不知道 Sheet 那一列的幣別（還沒讀 Sheet）——提醒一併核對（第四次覆核 NB5）。
        # 建倉時 Sheet 還沒有那一列，不提（第五次覆核 NB-2）。
        check = "（也請確認 --currency 與 Sheet 那一列一致）" if currency_given and not args.open_position else ""
        print(f"✗ 現金欄 {args.cash_column} 是 {cash_currency[args.cash_column]}，成交幣別是 {args.currency}"
              f"{'' if currency_given else '（沒給 --currency，預設 USD）'}——金額會以錯的幣別扣款；{fix}{check}",
              file=sys.stderr)
        return 2
    from fetchers import gsheets

    # 一筆成交只讀一次 Sheet（2026-09-30 使用者定案，plan §14 #38）：同一份原始格交給定位、硬擋與研究收據——
    # 三份不同時間點的快照會讓收據的持有與硬擋的 NAV 不是同一份。寫入前的逐格重讀是防同時手改，照留。
    try:
        sheet_values = gsheets.read_portfolio_values()
    except Exception as exc:  # noqa: BLE001 — 讀不到就什麼都不寫
        print(f"✗ Google Sheet 讀不到（{type(exc).__name__}: {str(exc)[:160]}）——未寫入任何東西", file=sys.stderr)
        return 2
    try:
        sheet_rows = list(gsheets.fetch_portfolio(strict_operational=True, values=sheet_values))
        sheet_error = None
    except Exception as exc:  # noqa: BLE001 — 解析不了：硬擋量不到（fail closed）、收據照實記
        sheet_rows, sheet_error = None, f"{type(exc).__name__}: {str(exc)[:160]}"

    gross = round(args.shares * args.price, 2)
    signed_shares = args.shares if args.side == "buy" else -args.shares

    # 同一檔可能分屬多個券商（如 LON:VWRA 同時在 IB 與 FUBON），
    # 持股列必須用 symbol＋broker 一起定位，否則兩列即歧義中止。
    skip_cash = args.cash_column.strip().lower() in ("", "none")
    cash_request = {"match": {"broker": args.broker, "bucket": "CASH"}, "column": args.cash_column}
    plan = None
    try:
        if args.open_position:
            # 首次建倉（2026-09-30 使用者定案）：規劃要看公式原文——多讀一次公式，只拿來比對形狀，不做數字決定。
            formulas = gsheets.read_portfolio_values(formulas=True)
            plan = gsheets.plan_new_position(sheet_values, formulas, broker=args.broker, symbol=args.symbol,
                                             currency=args.currency, allow_other_broker=args.also_at_other_broker)
            if args.bucket.strip() not in plan["buckets"]:
                raise ValueError(f"bucket {args.bucket!r} 不在 Sheet 既有的值裡（{'、'.join(plan['buckets'])}）——"
                                 "封閉字彙，不隨手開新的一格")
            shares_cell = cost_cell = None
            cash_cell = None if skip_cash else gsheets.locate_portfolio_cells([cash_request], values=sheet_values)[0]
            old_shares = old_cost = 0.0
        else:
            requests = [
                {"match": {"symbol": args.symbol, "broker": args.broker}, "column": "shares"},
                {"match": {"symbol": args.symbol, "broker": args.broker}, "column": "avg_cost"},
                # 那一列的幣別（R2 第二次覆核 B1）：沒給 --currency 就預設 USD，日圓／歐元／台幣金額會被當美元扣現金、
                # 硬擋也用錯幣別量——既有列有自己的幣別，拿來對，對不上就拒收（--log-only 也擋：trade_log 的幣別是 append-only）。
                {"match": {"symbol": args.symbol, "broker": args.broker}, "column": "currency"},
            ]
            if not skip_cash:
                requests.append(cash_request)
            cells = gsheets.locate_portfolio_cells(requests, values=sheet_values)
            shares_cell, cost_cell, currency_cell = cells[0], cells[1], cells[2]
            cash_cell = None if skip_cash else cells[3]
            row_currency = str(currency_cell["current"] or "").strip().upper()
            if row_currency != args.currency:
                # 一次寫齊要給的旗標（第三次覆核 N3：只寫 --currency 時，現金欄還會再擋一兩次才收斂）；
                # 匯率只有買進要（賣出不量硬擋），--log-only 不碰現金格所以不提現金欄。
                # 匯率的基準幣讀 Sheet 的 base_currency（第四次覆核 NB4：原本寫死 USD，基準幣一改就叫人給錯匯率）。
                base = next((str(r.get("base_currency") or "").strip().upper() for r in (sheet_rows or [])
                             if r.get("base_currency")), "USD")
                fx = (f" --fx-to-base <1 {row_currency} 等於多少 {base}>"
                      if row_currency not in ("", base) and args.side == "buy" else "")
                cash = ("" if args.log_only else
                        f" --cash-column {'cash_' + row_currency.lower() + ' 或 none' if row_currency in ('USD', 'TWD') else 'none'}")
                raise ValueError(f"Sheet 那一列（{currency_cell['a1']}）的幣別是 {row_currency or '（空）'}，成交幣別是 "
                                 f"{args.currency}{'' if currency_given else '（沒給 --currency，預設 USD）'}——"
                                 + (f"請給 --currency {row_currency}{fx}{cash}" if row_currency
                                    else "先在 Sheet 補上那一列的幣別"))
            old_shares = _number(shares_cell["current"])
            old_cost = _number(cost_cell["current"])
    except ValueError as exc:
        hint = ""
        if not args.open_position and "命中 0 列" in str(exc) and "symbol" in str(exc):
            elsewhere = sorted({str(r.get("broker") or "").strip() for r in (sheet_rows or [])
                                if gsheets.canonical_symbol(str(r.get("ticker") or "")) == gsheets.canonical_symbol(args.symbol)}
                               - {""})
            same_broker = [str(r.get("ticker")) for r in (sheet_rows or [])
                           if gsheets.canonical_symbol(str(r.get("ticker") or "")) == gsheets.canonical_symbol(args.symbol)
                           and str(r.get("broker") or "").strip().casefold() == args.broker.strip().casefold()]
            hint = (f"\n  代號請寫成 Sheet 的寫法 {same_broker[0]}（{args.broker} 那一列）" if same_broker else
                    f"\n  {args.symbol} 在 {'、'.join(elsewhere)} 有列——是不是 --broker 沒給對？" if elsewhere else
                    "\n  Sheet 還沒有這一列？首次建倉請加 --open-position --broker … --currency … --cash-column … --bucket …")
        print(f"✗ {'首次建倉：' if args.open_position else ''}{exc}{hint}", file=sys.stderr)
        return 2
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
    cash_a1 = None if skip_cash else _shifted_a1(cash_cell["a1"], plan["insert_at"] if plan else None)
    if plan is not None:
        print(f"\n首次建倉：將在第 {plan['insert_at']} 列**新增一列**（公式與格式複製自第 {plan['template']} 列；"
              f"NAV 加總範圍 {plan['nav_range'][1]}–{plan['nav_range'][2]} 列會自動涵蓋新列，寫完回讀驗證，不過就刪掉還原）：")
        print(f"  broker {args.broker}｜bucket {args.bucket.strip()}｜symbol {args.symbol}｜shares {new_shares:g}"
              f"｜avg_cost {new_cost}｜currency {args.currency}｜company {(args.company or '').strip() or '（空）'}")
        for row, columns in (plan.get("manual_exceptions") or {}).items():
            print(f"  （第 {row} 列的 {'、'.join(columns)} 是手寫公式，不當範本）")
        if skip_cash:
            print("  （現金列不改：--cash-column none，金流不經 Sheet 現金列，由使用者另行更新）")
        else:
            print(f"  {cash_a1:<16} {args.cash_column:<15} {old_cash:,.2f} → {new_cash:,.2f}"
                  f"{'   ← 插列後下移一列' if cash_a1 != cash_cell['a1'] else ''}")
    else:
        print(f"\n將變更的儲存格（僅此{'兩' if skip_cash or args.log_only else '三'}格，其餘欄位不動）：")
        print(f"  {shares_cell['a1']:<16} shares          {old_shares:g} → {new_shares:g}")
        print(f"  {cost_cell['a1']:<16} avg_cost        {old_cost} → {new_cost}"
              f"   ← 由本腳本計算，非通知逐字值")
        if args.log_only:
            # --log-only 不碰現金格、也不比現金欄幣別——印出現金的前後對照會被照著手改（第三次覆核 F2：
            # 日圓成交配預設 cash_usd 會印出 H21 18,700 → −16,300 這種不適用的數字）。
            print("  （--log-only：現金格不比對、不寫；Sheet 由你手動更新）")
        elif skip_cash:
            print("  （現金列不改：--cash-column none，金流不經 Sheet 現金列，由使用者另行更新）")
        else:
            print(f"  {cash_cell['a1']:<16} {args.cash_column:<15} {old_cash:,.2f} → {new_cash:,.2f}")

    # 兩道硬擋：dry-run 也擋（讓人在 --apply 之前就看到會被擋），override 留收據。
    verdict = _hard_cap_verdict(args, sheet_rows, sheet_error)
    _print_verdict(verdict)
    receipt: dict = {"hard_cap_check": verdict.to_dict()}
    if not verdict.allows:
        base = next((str(r.get("base_currency") or "").strip().upper() for r in (sheet_rows or [])
                     if r.get("base_currency")), None)
        if not args.override and verdict.status == "unmeasurable" and args.fx_to_base is None and base \
                and base != args.currency:
            # 缺的是匯率，不是放行（R2 第二次覆核 FX-4：照正確幣別記帳的人會先撞到這一步，別把他引去 override）。
            print(f"\n✗ 未寫入。成交幣別 {args.currency} 與 NAV 基準幣別 {base} 不同——請加 --fx-to-base "
                  f"<1 {args.currency} 等於多少 {base}>，硬擋才量得到。", file=sys.stderr)
            return EXIT_HARD_CAP
        if not args.override:
            print("\n✗ 未寫入。要放行請加 --override --reason「<理由>」（理由與 verdict 會寫進事件紀錄）。",
                  file=sys.stderr)
            return EXIT_HARD_CAP
        receipt["override_reason"] = args.reason.strip()
        print(f"\n⚠ override 放行：{args.reason.strip()}（將寫進事件紀錄）")

    # 研究收據（alpha；Phase 3 Step 3.8）。順序：locate → 硬擋 → 收據；dry-run 也組、也印、也擋。
    # 兩個放行互不放行：硬擋的 --override 不放行缺敘事，--no-narrative-override 不放行硬擋（上面已先過硬擋）。
    if not is_beta and args.backfill_before_receipts is not None:
        # 回填（Phase 5 Step 5.3）：只解析公司身分（今天也拿得回來的事實），**不讀敘事、候選板、個股頁**——
        # 那些是今天的判斷，填進一筆收據機制上線前的成交就是冒充當時（INV-6）。也不跑「缺 v2 就擋」那一道：
        # 當時根本沒有收據機制，缺的是紀錄本身。
        from portfolio import research_receipt

        try:
            identity = _backfill_identity(args.symbol, sheet_rows)
        except Exception as exc:  # noqa: BLE001 — 名冊讀不到：fail closed（R2-a NB3），什麼都還沒寫
            print(f"✗ --backfill-before-receipts：名冊讀不到（{type(exc).__name__}: {str(exc)[:120]}）——"
                  "「讀不到」與「名冊沒有這家」寫進 append-only 的收據會同形；回填不趕時間，修好再跑——"
                  "Sheet 只讀過、未寫入任何東西", file=sys.stderr)
            return 2
        research = research_receipt.build_backfill_receipt(
            side=args.side, why=(args.why or "").strip(), symbol=args.symbol,
            company_id=identity["company_id"], research_ticker=identity["research_ticker"],
            resolution=identity["source"], reason=args.backfill_before_receipts.strip())
        _print_receipt(research)
        receipt["research_receipt"] = research
    elif not is_beta:
        from portfolio import research_receipt

        try:
            today = _today()
            today_problem = None
        except Exception as exc:  # noqa: BLE001 — 排程時區讀不到：退回本機日期、照實記，不讓成交 crash
            from datetime import date

            today, today_problem = date.today(), f"排程時區讀不到（{type(exc).__name__}）——「今天」退回本機日期"
        inputs = _research_inputs(args.symbol, today=today, sheet_rows=sheet_rows, sheet_error=sheet_error)
        from fetchers.gsheets import canonical_symbol

        held_symbols = set(inputs.get("company_held_symbols") or ())
        same_symbol_held = bool(held_symbols) and held_symbols <= {canonical_symbol(args.symbol)}
        # 同代號在別家券商持有不算：5% 硬擋本來就跨券商按代號加總（R2 覆核 non-blocking）。但只要這家公司還有**任何
        # 別的代號**在持有，就照擋（第二次覆核：豁免只看「有沒有同代號」會把另一個代號漏掉）。
        if plan is not None and inputs.get("held_company") and not same_symbol_held:
            # 5% 單筆上限按代號加總：同一家公司換一個掛牌建倉會繞過它（R2 2026-09-30 non-blocking）。按公司合併是
            # 資本規則、要使用者決定（Phase 4）；在那之前建倉這一條路 fail closed。
            print(f"\n✗ 首次建倉：{inputs.get('company_id')} 在 Sheet 已經以別的代號持有——5% 上限只按代號加總，"
                  "換代號建倉會繞過它。請用已持有那一列的代號記帳（不加 --open-position）。", file=sys.stderr)
            return 2
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

    if _already_recorded(trade_id, payload):
        print("\n⚠ 這筆成交已在 trade_log.jsonl 中；重複執行不會再寫事件紀錄。")

    if args.log_only:
        if _already_recorded(trade_id, payload):
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

    if not skip_cash and new_cash < 0:
        print(f"\n⚠ 成交後現金會變負數（{new_cash:,.2f}）——確認是不是現金欄或幣別給錯")
    if not args.apply:
        if _already_recorded(trade_id, payload):
            print("\n（dry-run）這筆已在事件紀錄；加 --apply 會被拒絕（不重複寫 Sheet）。")
            return 0
        print("\n（dry-run）確認無誤後加 --apply 實際寫入。")
        print("  若這筆你已手動改過 Sheet，改用 --log-only 只記事件、不重複計算。")
        return 0

    # 重跑 --apply 一律 fail closed（2026-09-30 使用者定案，plan §14 #34）：事件已記過，Sheet 再寫一次就是
    # 股數與現金重複計算（HEAD 起既有的洞：原本只印警告、照寫 Sheet）。要補改 Sheet 請手動。
    if _already_recorded(trade_id, payload):
        print(f"\n✗ 這筆成交（{trade_id}）已在 {_shown(TRADE_LOG)}——重跑 --apply 會把 Sheet 的股數與現金再算一次。"
              "未寫入任何東西；Sheet 若需要更正請手動改。", file=sys.stderr)
        return 2

    opened = None
    if plan is not None:
        fill = {"broker": args.broker, "bucket": args.bucket.strip(), "symbol": args.symbol, "shares": new_shares,
                "avg_cost": new_cost, "currency": args.currency, "company": (args.company or "").strip(),
                "base_currency": (plan.get("template_values") or {}).get("base_currency", "")}
        try:
            opened = gsheets.open_position_row(plan, fill)
        except Exception as exc:  # noqa: BLE001 — 原子請求：驗證錯誤就沒改動；但 client 逾時不等於伺服器沒套用
            print(f"\n✗ 新增列失敗（{type(exc).__name__}: {str(exc)[:160]}）", file=sys.stderr)
            try:
                state = gsheets.new_row_state(plan, fill)
                if state == "absent" and ABSENT_RECHECK_SECONDS:
                    import time

                    time.sleep(ABSENT_RECHECK_SECONDS)
                    state = gsheets.new_row_state(plan, fill)
            except Exception as read_exc:  # noqa: BLE001
                state = f"讀不到（{type(read_exc).__name__}）"
            if state == "landed":
                print("  回讀發現新列其實已經套用（插入點那一列的代號、券商、股數都對）——刪掉還原：", file=sys.stderr)
                return _rollback(gsheets, {"row": plan["insert_at"]}, fill, plan)
            if state == "absent":
                print(f"  目前讀回未套用（列數沒變、沒有 {args.symbol}／{args.broker} 的列）；事件紀錄沒有寫。"
                      f"伺服器可能稍後才套用——重跑前先看一眼第 {plan['insert_at']} 列附近。", file=sys.stderr)
                return 2
            print(f"  ⚠⚠ 無法確認新列有沒有套用（回讀：{state}）——請手動看 Sheet 第 {plan['insert_at']} 列附近；"
                  "事件紀錄沒有寫。重跑前一定先核對，否則股數可能重複。", file=sys.stderr)
            return 2
        try:
            problems = gsheets.verify_new_position(plan, fill)
        except Exception as exc:  # noqa: BLE001 — 回讀本身失敗（網路、429／5xx）＝沒驗過，照樣還原
            problems = [f"回讀驗證失敗（{type(exc).__name__}: {str(exc)[:120]}）——沒驗過就不留"]
        if problems:
            print("\n✗ 新列寫完回讀沒通過，刪掉還原：", file=sys.stderr)
            for problem in problems:
                print(f"  · {problem}", file=sys.stderr)
            return _rollback(gsheets, opened, fill, plan)
        writes = []
    else:
        writes = [
            {"a1": shares_cell["a1"], "expected": shares_cell["current"], "value": new_shares},
            {"a1": cost_cell["a1"], "expected": cost_cell["current"], "value": new_cost},
        ]
    if not skip_cash:
        writes.append({"a1": cash_a1, "expected": cash_cell["current"], "value": new_cash})
    confirmed_note = None
    try:
        result = gsheets.write_portfolio_cells(writes)
    except gsheets.StaleCellError as exc:  # 寫入前逐格比對不符＝一格都沒寫（先全部比對才寫）；建倉的新列一併還原
        print(f"\n✗ 寫入中止（{str(exc)[:200]}）", file=sys.stderr)
        return _rollback(gsheets, opened, fill, plan) if opened else 2
    except Exception as exc:  # noqa: BLE001 — 網路類：可能已套用、也可能沒有——回讀決定，不猜（R2 覆核 blocking #3）
        print(f"\n✗ 寫入回應失敗（{type(exc).__name__}: {str(exc)[:200]}）", file=sys.stderr)
        if not opened:
            print("  ⚠ 既有列路徑沒有還原：部分儲存格可能已寫入——請手動核對 "
                  + "、".join(w["a1"] for w in writes) + "；事件紀錄沒有寫。", file=sys.stderr)
            return 2
        outcome = _cash_outcome(gsheets, cash_a1, old=cash_cell["current"], new=new_cash)
        if outcome == "old":
            print("  回讀現金格仍是寫入前的值——現金沒動，刪掉新列還原：", file=sys.stderr)
            return _rollback(gsheets, opened, fill, plan)
        if outcome != "new":
            print(f"  ⚠⚠ 無法確認：第 {opened['row']} 列新建倉已在，現金格 {cash_a1} 回讀是 {outcome!r}"
                  f"（預期 {cash_cell['current']} 或 {new_cash}）。不刪、不記事件——請手動核對 Sheet。", file=sys.stderr)
            return 2
        confirmed_note = "現金寫入回應失敗，回讀確認已套用（新列與現金都寫進 Sheet）"
        print(f"  {confirmed_note}——照常記事件。", file=sys.stderr)
        result = {"written": [{"a1": cash_a1, "from": cash_cell["current"], "to": new_cash, "confirmed_by_readback": True}]}
    written = list(opened["written"] if opened else []) + list(result["written"])
    _append_trade(
        {
            "trade_id": trade_id,
            **payload,
            "currency": args.currency,
            "gross_amount": gross,
            "account_ref": args.account_ref,
            "note": args.note,
            "recorded_at": _now(),
            "sheet_writes": written,
            **({"sheet_opened_row": opened["row"]} if opened else {}),
            **({"sheet_write_note": confirmed_note} if confirmed_note else {}),
            **receipt,
        }
    )
    print(f"\n✓ 已寫入 {len(written)} 格{f'（第 {opened["row"]} 列為新建倉）' if opened else ''}，"
          f"事件已記於 {_shown(TRADE_LOG)}")
    print("  Sheet 仍是持股唯一權威；市值與 NAV 未被本腳本改動。")
    return 0


def _shifted_a1(a1: str, insert_at: int | None) -> str:
    """插一列之後，原本在插入點（含）以下的儲存格下移一列；插入點以上不動。"""
    if insert_at is None:
        return a1
    sheet, _, ref = a1.rpartition("!")
    letters = ref.rstrip("0123456789")
    row = int(ref[len(letters):])
    return f"{sheet}!{letters}{row + 1 if row >= insert_at else row}"


def _cash_outcome(gsheets, a1: str, *, old: str, new: float) -> str:
    """寫入丟例外後回讀現金格：`old`＝沒寫進去、`new`＝已寫進去、其他＝回傳讀到的原值（或讀不到的理由）。"""
    try:
        now = gsheets.read_cell_value(a1)
    except Exception as exc:  # noqa: BLE001
        return f"讀不到（{type(exc).__name__}）"
    try:
        value = _number(now)
    except ValueError:
        return now
    if abs(value - _number(old)) < 0.005:
        return "old"
    if abs(value - float(new)) < 0.005:
        return "new"
    return now


def _rollback(gsheets, opened, fill, plan=None) -> int:
    try:
        check = gsheets.delete_position_row(opened, fill, expect=plan)
        if check.get("verified"):
            print(f"  已刪掉第 {opened['row']} 列並回讀確認 Sheet 回到寫入前（{check['detail']}）；事件紀錄沒有寫。",
                  file=sys.stderr)
        else:
            print(f"  已刪掉第 {opened['row']} 列，但回讀**沒能確認**回到寫入前（{check.get('detail')}）——"
                  "請手動看一眼 Sheet；事件紀錄沒有寫。", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — 還原失敗要大聲說，不吞
        print(f"  ⚠⚠ 還原失敗（{type(exc).__name__}: {str(exc)[:200]}）——請手動檢查 Sheet 第 {opened['row']} 列；"
              "事件紀錄沒有寫。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
