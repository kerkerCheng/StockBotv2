"""
checklist.py — 5 項財務核驗清單查詢。
⚠ 舊稱「Watchlist Gate」已停用：三級階梯 2026-09-02 除役（docs/ARCHITECTURE.md §9），
   但**這五項沒有廢止**——2026-09-23 前它經 Engine D coverage 變成 cohort blocker（研究側已退役），
   現在由 lane memo 與歸零旗標消費。

get_checklist(ticker) -> dict
  回傳 5 項各自的狀態（ok / manual_required / missing）與數值，
  供 thesis/generate_lane_memo.py 的財務核驗段落使用。

後端：SQLite（預設）或 Postgres（設 POSTGRES_HOST/DSN）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


def _get_conn():
    try:
        from engine_c.db import get_conn
        return get_conn()
    except Exception:
        return None


def _snap_status(value, label: str) -> dict:
    if value is None:
        return {"status": "missing", "value": None, "label": label}
    return {"status": "ok", "value": value, "label": label}


def _manual_status(value: str | None, label: str, source_note: str | None = None) -> dict:
    if value and source_note:
        return {
            "status": "manual_reviewed",
            "value": value,
            "source": source_note,
            "label": label,
        }
    return {"status": "manual_required", "value": None, "label": label}


def _prefer_manual(auto_item: dict, manual: dict, field_name: str, label: str) -> dict:
    """已逐字核對的人工觀測優先於 financial_snapshots 的衍生值。

    自動值只看得到當期快照，會在真實世界變動時給出錯誤答案：shares_outstanding
    每天相同，稀釋因此永遠算成 +0.0%，與財報加權平均股數的實際變化矛盾（AXT
    Q2 2026 為 +45.2%）。有登記的人工觀測代表有人核過一手文件，讓它勝出；
    自動值整包留在 auto_item，不散落成會被誤讀的裸鍵。
    """
    value, source_note = manual.get(field_name, (None, None))
    if not value or not source_note:
        return auto_item
    return {
        "status": "manual_reviewed",
        "value": value,
        "source": source_note,
        "label": label,
        "auto_item": auto_item,
    }


def _extended_observations(manual: dict) -> dict:
    """把非 gate 的已登記人工觀測整理成開放讀取表面。

    每筆自帶 `authorities`（token 字彙住 config/authority_tokens.json；原為 Engine D reference index
    的需求，研究側退役後留給 Phase 3 三題引用）。未登記或無 provenance 的
    欄位一律略過——寧可不出現，也不要讓沒有來源的值被 Confidence 軸引用。
    """
    from engine_c.observation_fields import get_observation_field_registry

    registry = get_observation_field_registry()
    result: dict[str, dict] = {}
    for field_name, (value, source_note) in sorted(manual.items()):
        spec = registry.get(field_name)
        if spec is None or spec.gate_member:
            continue
        if not value or not source_note:
            continue
        result[field_name] = {
            "status": "manual_reviewed",
            "value": value,
            "source": source_note,
            "label": spec.label,
            "category": spec.category,
            "authorities": list(spec.authorities),
        }
    return result


def get_checklist(ticker: str) -> dict:
    """
    5 項財務核驗清單。

    回傳結構：
    {
      "ticker": "COHR",
      "engine_c_available": True/False,
      "items": {
        "gross_margin_trend":     {"status": "ok"|"missing", "value": [...], "label": "..."},
        "customer_concentration": {"status": "manual_required", ...},
        "backlog":                {"status": "manual_required", ...},
        "dilution":               {"status": "ok", ...},
        "valuation_pressure":     {"status": "ok", ...},
      },
      "gate_pass": True/False
    }
    """
    conn = _get_conn()
    if conn is None:
        return {
            "ticker": ticker,
            "engine_c_available": False,
            "items": {},
            "observations": {},
            "gate_pass": False,
            "note": "Engine C 資料庫不可用（db.py 匯入失敗）",
        }

    try:
        from engine_c.db import _use_postgres
        is_pg = _use_postgres()

        if is_pg:
            cur = conn.cursor()
            cur.execute("""
                SELECT snapshot_date, gross_margin, shares_outstanding,
                       pe_forward, ev_revenue, price,
                       analyst_target_mean, analyst_target_count
                FROM financial_snapshots
                WHERE ticker = %s ORDER BY snapshot_date DESC LIMIT 4
            """, (ticker,))
            snaps = cur.fetchall()
            cur.execute(
                "SELECT field_name, value, source_note FROM manual_fields WHERE ticker = %s",
                (ticker,)
            )
            manual = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
            conn.close()
        else:
            import sqlite3
            cur = conn.execute("""
                SELECT snapshot_date, gross_margin, shares_outstanding,
                       pe_forward, ev_revenue, price,
                       analyst_target_mean, analyst_target_count
                FROM financial_snapshots
                WHERE ticker = ? ORDER BY snapshot_date DESC LIMIT 4
            """, (ticker,))
            snaps = [tuple(r) for r in cur.fetchall()]
            cur2 = conn.execute(
                "SELECT field_name, value, source_note FROM manual_fields WHERE ticker = ?",
                (ticker,)
            )
            manual = {row[0]: (row[1], row[2]) for row in cur2.fetchall()}
            conn.close()

    except Exception as e:
        return {
            "ticker": ticker,
            "engine_c_available": False,
            "items": {},
            "observations": {},
            "gate_pass": False,
            "note": f"資料庫查詢失敗：{e}",
        }

    if not snaps:
        return {
            "ticker": ticker,
            "engine_c_available": True,
            "items": {
                k: {"status": "missing", "value": None, "label": l}
                for k, l in [
                    ("gross_margin_trend", "毛利率趨勢"),
                    ("customer_concentration", "客戶集中度"),
                    ("backlog", "Backlog/訂單能見度"),
                    ("dilution", "稀釋分析"),
                    ("valuation_pressure", "估值壓力"),
                ]
            },
            "observations": _extended_observations(manual),
            "gate_pass": False,
            "note": f"{ticker} 無快照，請先執行 python engine_c/etl_yfinance.py {ticker}",
        }

    # 1. 毛利率趨勢（最近 4 季）
    gm_vals = [(str(r[0]), r[1]) for r in snaps if r[1] is not None]
    gm_item = _snap_status(gm_vals or None, "毛利率趨勢（近 4 季）")
    if gm_item["status"] == "ok":
        latest = gm_vals[0][1]
        oldest = gm_vals[-1][1]
        gm_item["trend"] = "上升" if latest > oldest else ("下滑" if latest < oldest else "持平")
        gm_item["latest"] = f"{latest:.1%}"
    gm_item = _prefer_manual(gm_item, manual, "gross_margin_trend", "毛利率趨勢（近 4 季）")

    # 2. 客戶集中度（人工填入）
    cc_value, cc_source = manual.get("customer_concentration", (None, None))
    cc_item = _manual_status(
        cc_value,
        "客戶集中度（前三大客戶 % 收入）",
        cc_source,
    )

    # 3. Backlog（人工填入）
    bl_value, bl_source = manual.get("backlog", (None, None))
    bl_item = _manual_status(bl_value, "Backlog/訂單能見度", bl_source)

    # 4. 稀釋（shares_outstanding 趨勢）
    shares = [(str(r[0]), r[2]) for r in snaps if r[2] is not None]
    dil_item = _snap_status(shares or None, "稀釋分析（股數趨勢）")
    if dil_item["status"] == "ok" and len(shares) >= 2:
        delta = (shares[0][1] - shares[-1][1]) / shares[-1][1]
        dil_item["shares_change"] = f"{delta:+.1%}"
    dil_item = _prefer_manual(dil_item, manual, "dilution", "稀釋分析（股數趨勢）")

    # 5. 估值壓力
    r0 = snaps[0]
    val_data = {
        "price": r0[5], "pe_forward": r0[3], "ev_revenue": r0[4],
        "analyst_target_mean": r0[6], "analyst_target_count": r0[7],
    }
    val_label = "估值壓力（P/E, EV/Rev, 分析師目標價）"
    val_item = _snap_status(
        val_data if any(v is not None for v in val_data.values()) else None,
        val_label,
    )
    val_item = _prefer_manual(val_item, manual, "valuation_pressure", val_label)

    items = {
        "gross_margin_trend":     gm_item,
        "customer_concentration": cc_item,
        "backlog":                bl_item,
        "dilution":               dil_item,
        "valuation_pressure":     val_item,
    }
    # gate_pass 只掃 items（凍結的五項 L9 gate）。擴充欄位刻意不參與，否則新增一個
    # 欄位就會讓所有既有標的的 gate_pass 退化。
    gate_pass = all(v["status"] in ("ok", "manual_reviewed") for v in items.values())

    return {
        "ticker": ticker,
        "engine_c_available": True,
        "items": items,
        "observations": _extended_observations(manual),
        "gate_pass": gate_pass,
    }


_RUNWAY_INPUT_KEYS = ("cash_and_equivalents", "total_debt", "free_cash_flow_ttm")


def _parse_runway_inputs(value, source_note, as_of) -> dict | None:
    """把 runway_inputs 人工觀測轉成 shared.runway.derive_runway 能吃的 payload。

    三個數值缺一即視為未提供：runway 是除法，部分推導只會給出看起來精確的
    錯誤答案。provenance 沿用該筆觀測自己的 source 與 as_of，讓 derive_runway
    既有的 timestamp future／stale 檢查照常生效。
    """
    if not value or not source_note or not as_of:
        return None
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    numbers = {}
    for key in _RUNWAY_INPUT_KEYS:
        raw = payload.get(key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        numbers[key] = float(raw)
    return numbers | {"source": str(source_note), "as_of": str(as_of)}


def _fetch_runway_inputs(connection, ticker: str, *, is_pg: bool) -> dict | None:
    sql = (
        "SELECT value, source_note, updated_at FROM manual_fields "
        "WHERE ticker = {ph} AND field_name = 'runway_inputs'"
    ).format(ph="%s" if is_pg else "?")
    try:
        if is_pg:
            with connection.cursor() as cursor:
                cursor.execute(sql, (ticker,))
                row = cursor.fetchone()
        else:
            row = connection.execute(sql, (ticker,)).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    return _parse_runway_inputs(row[0], row[1], row[2])


def _cover_shares_series(connection, ticker: str, *, today) -> list | None:
    """10-K／10-Q 國內申報人的 SEC 封面股數序列，**分割調整到最新基準**（Phase 3 Step 3.3，使用者定案 #14）。

    不是國內季度申報人、或 as-of 今天已知的封面日不足兩個 → None（呼叫端續用 yfinance 快照序列；
    逐檔單一來源，兩個來源不混）。多股類的申報在回填時就被拒寫（不加總），所以這裡讀到的都是單一值。
    """
    import sqlite3 as _sqlite3

    from engine_c.history_backfill import filer_class
    from shared.as_of import latest_known_by_period

    try:
        klass, _basis = filer_class(connection, ticker, today=today)
        if klass != "domestic_quarterly":
            return None
        rows = connection.execute(
            "SELECT period_end, filed, accession, value FROM fundamental_history "
            "WHERE ticker = ? AND metric = 'shares_outstanding_cover'", (ticker,)).fetchall()
        splits = connection.execute(
            "SELECT action_date, ratio FROM corporate_actions WHERE ticker = ? AND kind = 'split'",
            (ticker,)).fetchall()
    except _sqlite3.OperationalError:
        return None   # 歷史表不存在（舊庫）：退回快照序列，不猜
    known = latest_known_by_period(
        [{"period_end": r[0], "filed": r[1], "accession": r[2], "value": r[3]} for r in rows], today)
    if len(known) < 2:
        return None
    parsed_splits = []
    for d, ratio in splits:
        try:
            parsed_splits.append((type(today).fromisoformat(str(d)[:10]), float(ratio)))
        except (TypeError, ValueError):
            continue
    series = []
    for end, row in sorted(known.items()):
        factor = 1.0
        for split_date, ratio in parsed_splits:
            if end < split_date <= today:
                factor *= ratio
        series.append((end, float(row["value"]) * factor))
    return series


#: 稀釋燈的發行金額取數用到的兩個 metric（Phase 4 Step 4.6；`engine_c.history_backfill.LATE_METRICS`）。
_EQUITY_QUARTER = "equity_issued_value_quarter"
_EQUITY_ANNUAL = "equity_issued_value_annual"
#: 窗尾（anchor）＝最新已申報季度的期末，只從**期末精確**的指標取：先取季度流量；這家一筆季度流量都沒有才退到
#: 資產負債表時點值（R2-c 覆核 #5：期末之後的時點值——例如期後事項——會把窗整個往後推，讓最早那一季掉出窗外）。
#: ⚠ 封面股數的日期不是期末（比期末晚 20–75 天，2026-10-01 正式庫 35 檔裡只有 AMAT 恰好等於期末）——拿它當窗尾，
#: 年度那一列永遠對不上窗尾、四季窗也會整個往後推。
_ANCHOR_FLOW_METRICS = ("revenue_quarter", "operating_income_quarter", _EQUITY_QUARTER)
_ANCHOR_INSTANT_METRICS = ("cash", "total_debt")
#: 「最近四季」＝期末距窗尾**不到 320 天**的季度（含窗尾那一季）。相鄰季度期末相距 80–100 天（13／14 週季度；
#: 與 `alpha/three_questions._QUARTER_GAP` 同一個判準），所以三季前最遠 300 天、四季前最近 320 天——日曆季與
#: 52／53 週制都剛好四季。⚠ 不用 365 天：52 週制四季前那一季的期末離窗尾只有 364 天，會多加一季
#: （2026-10-01 正式庫：LITE、AAPL、AMD、INTC、LRCX、MTSI 等 16 檔國內申報人是 52／53 週制）。
_FOUR_QUARTERS_DAYS = 320


def _equity_issuance(connection, ticker: str, *, today) -> dict:
    """稀釋燈要的**新股發行金額**（`us-gaap:StockIssuedDuringPeriodValueNewIssues`；Phase 4 Step 4.6）——只取數、不判色。

    - 不是 10-K／10-Q 國內申報人 → `method_not_applicable`（燈不判色，股數變化照印）。
    - 表還存不下（CHECK 未遷移）、或整張表都還沒有這兩個指標（遷移後還沒回填）→ `upstream_unavailable`——
      是我們這邊還沒準備好，**不得**說成「這家沒申報」（L12）。
    - 5 年回填窗內這家一筆都沒有 → `provider_missing`（從來沒用這個 tag，或最後一次在窗外——兩者都說不出「沒增發」）。
    - 否則 `ok`：最近四季＝期末落在（窗尾 − 320 天, 窗尾］的季度（`_FOUR_QUARTERS_DAYS`），窗尾＝今天已申報的
      最新季度期末（`_ANCHOR_FLOW_METRICS`，沒有才退到時點值）；每季取 as-of 今天已知的最新一列（含衍生的第四季），
      年度期末正好是窗尾就直接用年度那一列。**缺的季度不補 0**——列出找到幾季。
    - `issued_total`＝窗內**正值**的加總（判色看它）；`trailing_total`＝淨加總，只印（R2-c 覆核 #1：負值多半是更正，
      或年報與季報 tag 前後不一衍生出的負第四季——不得拿來抵銷真實發行）。前後不一另列 `inconsistent`。
    - `offerings`（Phase 6 Step 6.6）：同一個窗裡的募資文件與不算募資的登記表單（`_offering_documents`）——
      稀釋燈只在窗內有募資文件時才亮黃。
    """
    import sqlite3 as _sqlite3
    from datetime import timedelta

    from engine_c.history_backfill import filer_class, late_metrics_supported
    from shared.as_of import latest_known_by_period

    try:
        klass, basis = filer_class(connection, ticker, today=today)
    except _sqlite3.OperationalError:
        return {"status": "upstream_unavailable", "reason": "歷史表不存在（舊庫）"}
    if klass != "domestic_quarterly":
        return {"status": "method_not_applicable", "filer_class": klass, "filer_basis": basis}
    if not late_metrics_supported(connection):
        return {"status": "upstream_unavailable", "filer_class": klass, "filer_basis": basis,
                "reason": "fundamental_history 的 CHECK 尚未遷移，新股發行金額存不進來"
                          "（python -m engine_c.migrate_fundamental_metrics --apply）"}
    try:
        rows = connection.execute(
            "SELECT metric, period_start, period_end, filed, accession, value, currency, tag, derived "
            "FROM fundamental_history WHERE ticker = ? AND metric IN (?, ?)",
            (ticker, _EQUITY_QUARTER, _EQUITY_ANNUAL)).fetchall()
        anchor_row = None
        for group in (_ANCHOR_FLOW_METRICS, _ANCHOR_INSTANT_METRICS):
            anchor_row = connection.execute(
                "SELECT MAX(period_end) FROM fundamental_history WHERE ticker = ? AND filed <= ? "
                f"AND metric IN ({', '.join('?' for _ in group)})",
                (ticker, today.isoformat(), *group)).fetchone()
            if anchor_row and anchor_row[0]:
                break
        backfilled = rows or connection.execute(
            "SELECT 1 FROM fundamental_history WHERE metric IN (?, ?) LIMIT 1",
            (_EQUITY_QUARTER, _EQUITY_ANNUAL)).fetchone()
    except _sqlite3.OperationalError:
        return {"status": "upstream_unavailable", "reason": "fundamental_history 讀不到"}
    if not backfilled:
        return {"status": "upstream_unavailable", "filer_class": klass, "filer_basis": basis,
                "reason": "新股發行金額還沒回填（整張表一列都沒有）——遷移後要跑一次非增量 EDGAR 回填"
                          "（python -m engine_c.history_backfill --no-prices）"}
    if not rows:
        # 措辭只說到資料支持的那一格（R2-c 覆核 #2、L11-5）：期間不是季／半年／9 個月／年的 fact（成立未滿一季、
        # 會計年度變更）回填不存、只在回填報告計數——「沒有可存的」不等於「沒有任何」。
        return {"status": "provider_missing", "filer_class": klass, "filer_basis": basis,
                "reason": "5 年回填窗內 companyfacts 沒有可存成季度或年度的 StockIssuedDuringPeriodValueNewIssues"
                          "（10-K／10-Q）——期間長度不是季／半年／9 個月／年的 fact 不存，回填報告另計"}
    if not anchor_row or not anchor_row[0]:
        return {"status": "upstream_unavailable",
                "reason": "找不到最新已申報季度的期末（季度營收／營業利益／發行金額、現金、債務都沒有）"}
    anchor = type(today).fromisoformat(str(anchor_row[0])[:10])
    window_after = anchor - timedelta(days=_FOUR_QUARTERS_DAYS)
    by_metric: dict[str, list[dict]] = {_EQUITY_QUARTER: [], _EQUITY_ANNUAL: []}
    for metric, start, end, filed, accession, value, currency, tag, derived in rows:
        by_metric[str(metric)].append({"period_start": start, "period_end": end, "filed": filed,
                                       "accession": accession, "value": value, "currency": currency,
                                       "tag": tag, "derived": derived})
    quarters = latest_known_by_period(by_metric[_EQUITY_QUARTER], today)
    annuals = latest_known_by_period(by_metric[_EQUITY_ANNUAL], today)
    in_window = {end: row for end, row in quarters.items() if window_after < end <= anchor}
    exact_year = annuals.get(anchor)
    if exact_year is not None:
        facts, basis_kind = [exact_year], "annual"
    else:
        facts, basis_kind = [in_window[end] for end in sorted(in_window)], "quarters"
    currencies = sorted({str(f.get("currency")) for f in facts})
    total = sum(float(f["value"]) for f in facts) if facts else 0.0
    issued = sum(float(f["value"]) for f in facts if float(f["value"]) > 0)
    # 年報與季報 tag 前後不一（R2-c 覆核 #1；CRWV FY2025 年度 6800 萬 < Q1'25 13.9 億）：衍生出負的第四季、或年度小於
    # 該年度已知季度的加總——印出來，不拿來相減（相減會抵掉同窗的真實發行）。
    inconsistent = [{"kind": "negative_derived_quarter", "period_end": str(f["period_end"])[:10],
                     "value": float(f["value"]), "derived": f.get("derived")}
                    for f in facts if f.get("derived") and float(f["value"]) < 0]
    # 期末落在窗內的年度，若季度列加起來不到年度（缺季、前後兩年 tag 不一）：差額歸不到季——印出來，不補 0、
    # 不硬塞進某一季（L12）。窗尾那個年度已直接用年度列的不算。2026-10-01 實測 AXTI FY2025 9355 萬三份 10-Q 都沒有。
    unattributed = []
    for fy_end, fy_row in sorted(annuals.items()):
        if not (window_after < fy_end <= anchor) or (basis_kind == "annual" and fy_end == anchor):
            continue
        try:
            fy_start = type(today).fromisoformat(str(fy_row.get("period_start"))[:10])
        except ValueError:
            continue
        # 負的衍生季已知是 tag 前後不一的產物（列在 inconsistent）——不算進「已知」，否則差額會被它灌大
        known = sum(float(q["value"]) for end, q in quarters.items()
                    if fy_start < end <= fy_end and not (q.get("derived") and float(q["value"]) < 0))
        remainder = float(fy_row["value"]) - known
        entry = {"fiscal_year_end": str(fy_end), "annual": float(fy_row["value"]), "known_quarters": known,
                 "remainder": remainder, "accession": fy_row.get("accession")}
        if remainder > 0.5:                                    # 金額以元計；只防浮點誤差
            unattributed.append(entry)
        elif remainder < -0.5:
            inconsistent.append({"kind": "annual_below_quarters", **entry})
    offerings = _offering_documents(connection, ticker, facts=facts, window_after=window_after, anchor=anchor,
                                    today=today)
    return {
        "status": "ok", "filer_class": klass, "filer_basis": basis,
        "offerings": offerings,
        "window_after": window_after, "window_end": anchor, "basis": basis_kind,
        # 年度＝窗尾時加總用的是年度列，窗內季度數不參與——不印，免得讀成「用了這幾季」（R2-c 覆核 #6d）
        "quarters_found": len(in_window) if basis_kind == "quarters" else None,
        "trailing_total": total, "issued_total": issued, "currencies": currencies,
        "facts": [{**f, "period_end": str(f["period_end"])[:10], "filed": str(f["filed"])[:10]} for f in facts],
        "tags": sorted({str(f.get("tag")) for f in facts}), "unattributed": unattributed,
        "inconsistent": inconsistent,
    }


def _offering_documents(connection, ticker: str, *, facts: list, window_after, anchor, today) -> dict:
    """發行金額那個窗裡的募資文件（Phase 6 Step 6.6；清單與判定住 `engine_c.offerings`）。

    窗＝**發行金額那個窗的期間**到**最新一份定期報告的申報日**（INV-6；plan §7）：起點是窗內最早那一季（或年度列）的
    期初——金額是那幾季發生的，募資文件可能在季初就申報（2026-10-03 實測 MP：7 月 10 日的 8-K 3.02、7 月 16／18 日的
    424B5 都在第三季期初之後、期末窗下界 8 月 14 日之前）；終點是窗尾那一季的報告申報日（金額由它揭露）。
    窗內沒有可用的期初就退回期末下界。只回清單與涵蓋狀態，**不判色**（判色在 `alpha.wipeout.dilution_flag`）。
    """
    from engine_c.offerings import offerings_in_window

    starts = []
    for fact in facts:
        try:
            starts.append(type(today).fromisoformat(str(fact.get("period_start"))[:10]))
        except (TypeError, ValueError):
            continue
    start = min(starts) if starts else window_after
    row = connection.execute(
        "SELECT MAX(filed) FROM fundamental_history WHERE ticker = ? AND period_end = ? AND filed <= ?",
        (ticker, anchor.isoformat(), today.isoformat())).fetchone()
    try:
        end = type(today).fromisoformat(str(row[0])[:10]) if row and row[0] else anchor
    except ValueError:
        end = anchor
    return offerings_in_window(connection, ticker, start=start, end=end, today=today)


def _equity_authorizations(connection, ticker: str) -> list | None:
    """人工欄位 `equity_issuance_authorizations`（ATM／shelf 授權，judgment、經 pq2 寫入）的生效紀錄——當脈絡印，不上色。

    每個 as_of 各取生效的那幾筆、新的在前（R2-c 覆核 #6d：只取最新那一天會藏掉不同日登記、同時有效的授權；
    授權到期與否由讀的人看 as_of 與原文判斷，這裡不猜）。"""
    import json as _json
    import sqlite3 as _sqlite3

    from engine_c.manual_observations import live_observation_ids

    try:
        days = [str(r[0]) for r in connection.execute(
            "SELECT DISTINCT substr(as_of, 1, 10) FROM manual_observations "
            "WHERE ticker = ? AND field_name = 'equity_issuance_authorizations' ORDER BY 1 DESC", (ticker,))]
        out = []
        for day in days:
            for oid in live_observation_ids(connection, ticker, "equity_issuance_authorizations", day):
                rec = connection.execute(
                    "SELECT value, source_ref FROM manual_observations WHERE observation_id = ?", (oid,)).fetchone()
                try:
                    value = _json.loads(rec[0])
                except (TypeError, ValueError):
                    value = rec[0]
                out.append({"value": value, "source": rec[1], "as_of": day, "observation_id": oid})
        return out or None
    except _sqlite3.OperationalError:
        return None


def _going_concern_record(connection, ticker: str) -> dict | None:
    """`going_concern_opinion` 的生效紀錄：最新 as_of、supersedes 沒被指到的那一筆（Phase 3 Step 3.3）。

    同一個 as_of 有多筆生效 → `{"conflict": [...]}`（燈不挑一個）；沒有紀錄 → None。
    """
    import json as _json
    import sqlite3 as _sqlite3

    from engine_c.manual_observations import live_observation_ids

    try:
        row = connection.execute(
            "SELECT MAX(as_of) FROM manual_observations WHERE ticker = ? AND field_name = 'going_concern_opinion'",
            (ticker,)).fetchone()
    except _sqlite3.OperationalError:
        return None
    if not row or not row[0]:
        return None
    as_of = str(row[0])
    live = live_observation_ids(connection, ticker, "going_concern_opinion", as_of)
    if len(live) != 1:
        return {"conflict": list(live), "as_of": as_of} if live else None
    rec = connection.execute(
        "SELECT value, source_ref FROM manual_observations WHERE observation_id = ?", (live[0],)).fetchone()
    try:
        value = _json.loads(rec[0])
    except (TypeError, ValueError):
        return None
    return {"value": value, "source": rec[1], "as_of": as_of, "observation_id": live[0]}


def get_wipeout_inputs(ticker: str, *, conn=None) -> dict:
    """歸零旗標（D2）要的三組**原始輸入**。這裡只取數，**一個顏色都不判**。

    判色規則住 `alpha/wipeout.py`（純函式、可單測）；型別住 read model。三層分開的理由是
    L15：解析與權限分工——Engine C 擁有觀測，規則層只讀它。

    - `runway`：`shared.runway.derive_runway` 的輸出形狀。人工 `runway_inputs`（`mechanical`
      欄位）優先於 yfinance 快照——yfinance 在財報後會暫時清空 `free_cash_flow_ttm`。
    - `shares_series`：**同口徑**的在外流通股數序列（全部歷史，不截斷）。⚠ 刻意不混入
      `fiscal_year_results` 的稀釋股數：那是另一個口徑（含潛在股份），相減沒有意義。
    - `going_concern`：`litigation_and_audit_flags` 的逐字觀測（judgment 欄位）。
    """
    from datetime import date as _date

    owned_connection = conn is None
    connection = conn or _get_conn()
    if connection is None:
        return {"ticker": ticker, "status": "unavailable", "reason": "Engine C 資料庫不可用"}
    try:
        from shared.runway import derive_runway
        from engine_c.db import _use_postgres

        is_pg = _use_postgres()
        base = get_probe_financial_baseline(ticker, conn=connection)
        if base.get("status") == "unavailable":
            return {"ticker": ticker, "status": "unavailable", "reason": "Engine C 快照讀取失敗"}
        financial = {key: base.get(key) for key in _RUNWAY_INPUT_KEYS}
        # `derive_runway` 要求 as_of 帶時區；快照存的是日期。補成當日 UTC 午夜，不改變語意。
        financial["source"] = base.get("source")
        financial["as_of"] = (f"{base['as_of']}T00:00:00+00:00" if base.get("as_of") else None)
        manual = base.get("manual_runway")
        if manual:
            manual = dict(manual)
            if manual.get("as_of") and len(str(manual["as_of"])) <= 10:
                manual["as_of"] = f"{manual['as_of']}T00:00:00+00:00"
        try:
            runway = derive_runway(financial, manual_observation=manual)
        except ValueError:
            runway = {"status": "manual_required", "runway_months": None}
        # 三個輸入**一律帶著走**：燈滅時稽核層仍要看得到是哪一個缺。
        for key in _RUNWAY_INPUT_KEYS:
            runway.setdefault(key, financial.get(key))
        runway.setdefault("source", financial.get("source"))
        runway.setdefault("as_of", financial.get("as_of"))

        ph = "%s" if is_pg else "?"
        shares_sql = (
            "SELECT snapshot_date, shares_outstanding FROM financial_snapshots "
            f"WHERE ticker = {ph} AND shares_outstanding IS NOT NULL ORDER BY snapshot_date"
        )
        gc_sql = (
            "SELECT value, source_note, updated_at FROM manual_fields "
            f"WHERE ticker = {ph} AND field_name = 'litigation_and_audit_flags'"
        )
        if is_pg:
            with connection.cursor() as cursor:
                cursor.execute(shares_sql, (ticker,))
                share_rows = cursor.fetchall()
                cursor.execute(gc_sql, (ticker,))
                gc_row = cursor.fetchone()
        else:
            share_rows = connection.execute(shares_sql, (ticker,)).fetchall()
            gc_row = connection.execute(gc_sql, (ticker,)).fetchone()

        series = []
        for row in share_rows:
            try:
                series.append((_date.fromisoformat(str(row[0])[:10]), float(row[1])))
            except (TypeError, ValueError):
                continue
        del gc_row  # ⚠ 2026-09-29（Phase 3 Step 3.3）：`litigation_and_audit_flags` 的散文不再餵燈（見下）
        shares_source = "yfinance_snapshot"
        if not is_pg:
            cover = _cover_shares_series(connection, ticker, today=_date.today())
            if cover is not None:
                series, shares_source = cover, "sec_cover_shares"
        going_concern = None if is_pg else _going_concern_record(connection, ticker)
        # 新股發行金額（Phase 4 Step 4.6）：稀釋燈的判色輸入。市值（只為印「占市值 %」）不在這裡取——
        # 那是研究層的正規化（`alpha/providers/market_normalization.py`），資料層不往下游引用
        # （串接點 `alpha.providers.wipeout.wipeout_for`）。
        if is_pg:
            issuance = {"status": "upstream_unavailable", "reason": "歷史表只在 SQLite（Postgres 尚未接）"}
        else:
            issuance = _equity_issuance(connection, ticker, today=_date.today())
            issuance["authorizations"] = _equity_authorizations(connection, ticker)
        return {"ticker": ticker, "status": "ok", "runway": runway,
                "shares_series": series, "shares_source": shares_source, "going_concern": going_concern,
                "issuance": issuance}
    except Exception as exc:  # noqa: BLE001 — 取不到就誠實說取不到，不回一組看起來合理的空值
        return {"ticker": ticker, "status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}
    finally:
        if owned_connection and connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass


def get_probe_financial_baseline(ticker: str, *, conn=None) -> dict:
    """回傳 runway 所需的 point-in-time raw scalars，不在 Engine C 算部位。"""

    owned_connection = conn is None
    connection = conn or _get_conn()
    if connection is None:
        return {"ticker": ticker, "status": "unavailable"}
    try:
        from engine_c.db import _use_postgres

        if _use_postgres():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT snapshot_date, cash_and_equivalents, total_debt,
                           free_cash_flow_ttm, fetched_at
                    FROM financial_snapshots
                    WHERE ticker = %s
                    ORDER BY snapshot_date DESC, fetched_at DESC
                    LIMIT 1
                    """,
                    (ticker,),
                )
                row = cursor.fetchone()
        else:
            row = connection.execute(
                """
                SELECT snapshot_date, cash_and_equivalents, total_debt,
                       free_cash_flow_ttm, fetched_at
                FROM financial_snapshots
                WHERE ticker = ?
                ORDER BY snapshot_date DESC, fetched_at DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()
        if row is None:
            return {"ticker": ticker, "status": "missing"}
        values = tuple(row)
        result = {
            "ticker": ticker,
            "as_of": str(values[0]),
            "cash_and_equivalents": values[1],
            "total_debt": values[2],
            "free_cash_flow_ttm": values[3],
            "fetched_at": str(values[4]),
            "source": "yfinance.info",
        }
        result["status"] = (
            "observed"
            if all(result[key] is not None for key in _RUNWAY_INPUT_KEYS)
            else "manual_required"
        )
        if result["status"] == "manual_required":
            manual_runway = _fetch_runway_inputs(
                connection, ticker, is_pg=_use_postgres()
            )
            if manual_runway is not None:
                result["manual_runway"] = manual_runway
        return result
    except Exception:
        return {"ticker": ticker, "status": "unavailable"}
    finally:
        if owned_connection and connection is not None:
            connection.close()


def format_checklist(result: dict) -> str:
    lines = [f"## 5 項財務核驗清單：{result['ticker']}"]

    if not result.get("engine_c_available"):
        lines.append(f"⚠ {result.get('note', 'Engine C 未啟動')}")
        return "\n".join(lines)

    if result.get("note"):
        lines.append(f"⚠ {result['note']}")

    icon_map = {"ok": "✓", "manual_reviewed": "✓(人工)", "manual_required": "⚠(人工待填)", "missing": "✗"}
    for key, item in result.get("items", {}).items():
        icon = icon_map.get(item["status"], "?")
        extra = ""
        if key == "gross_margin_trend" and item.get("trend"):
            extra = f"  趨勢：{item['trend']}，最新：{item.get('latest', 'N/A')}"
        elif key == "dilution" and item.get("shares_change"):
            extra = f"  股數變化：{item['shares_change']}"
        elif key == "valuation_pressure" and isinstance(item.get("value"), dict):
            v = item["value"]
            parts = []
            if v.get("price"):       parts.append(f"${v['price']:.2f}")
            if v.get("pe_forward"):  parts.append(f"FwdPE={v['pe_forward']:.1f}x")
            if v.get("ev_revenue"):  parts.append(f"EV/Rev={v['ev_revenue']:.1f}x")
            if v.get("analyst_target_mean"):
                parts.append(f"分析師=${v['analyst_target_mean']:.2f}(N={v.get('analyst_target_count','?')})")
            extra = "  " + ", ".join(parts) if parts else ""
        lines.append(f"{icon} {item['label']}{extra}")

    # ⚠ 這行只說「五項齊不齊」，**不說升格**：Watchlist／Underwrite 三級模板已於
    # 2026-09-02 除役（docs/ARCHITECTURE.md §9），終點層級是 Decision cohort。
    # 五項本身仍然有效——（2026-09-23 前）它經 Engine D coverage 變成 cohort blocker；研究側已退役。
    gate = (
        "✓ 財務核驗五項齊備"
        if result.get("gate_pass")
        else "✗ 財務核驗五項未齊備（上方標 ⚠ 的就是缺口）"
    )
    lines.append(f"\n**{gate}**")
    return "\n".join(lines)


def main() -> int:
    import json
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "COHR"
    result = get_checklist(ticker)
    print(format_checklist(result))
    print("\n--- raw ---")
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("gate_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
