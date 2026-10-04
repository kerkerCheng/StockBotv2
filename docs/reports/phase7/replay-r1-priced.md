# Phase 7 Step 7.2 — R1 已定價回放（X1）

> **性質：回放報告（評估檔）。** 規則照 [`registration.md`](registration.md) §7.2 與 §1 H9（預先登記、本報告不改判讀線）；只引用 id、不改任何 ledger。
> 執行：2026-10-05（台北），量測終點＝**2026-10-02**（執行日之前最後一個完整交易日）。表格由程式從計算結果產生，程式碼逐字在附錄。

## 一句話

**H9（「已定價」這一格有沒有區分力）在本次回放判「不足」**——124 格（31 列 × 4 個時點）只有 **10** 格算得出自家三年百分位，
每一個時點、兩個子群都湊不到「高、低各 ≥ 4」。**之後曾漲到 2 倍的 21 格，在那個時點全部是「未量」**——
「已定價有沒有把贏家說服走」這個問題，現有資料**回答不了**，不是答案是否定。

## 怎麼算的（point-in-time）

- 百分位＝三題同一個純函式 `alpha.three_questions.own_history`，輸入＝`engine_c.three_question_inputs.get_three_question_inputs(today=t)`：
  價格只到 t；財報、股數逐日以「申報日 ≤ 當天」取（`shared.as_of`）；分割只套到當天。**沒有改任何產品程式**（plan §8）。
- 每個有值的格都印出「該時點實際用到的最晚申報日」——**全部 ≤ t（PIT 違規 0 格）**，見下方 PIT 表。
- 報酬與超額：追蹤表同一條序列（`scripts/outcome_if_settled_today._provider_close_series`，yfinance 調整後收盤、拿掉未收盤 K 棒）；
  超額＝對光通訊主題等權組 `tc_35b0d5cd521656ea`（**排除本檔**，`alpha.theme_cohort.cohort_return`）。
- 分組：高 ≥ 67；中 33–67；低 < 33（registration §7.2）。history 列（錨＝入圖日）與只在組裡的 9 檔（錨＝組定義日 2026-09-30）**分開判**。

## 判讀線（H9；registration §1）

| 子群 | 時點 | 高（n／平均超額） | 中 | 低 | 未量 n | 判讀線（每組 n ≥ 4） |
|---|---|---|---|---|---|---|
| history | 錨點 | 5／+2.1% | 1／-27.0% | 1／-4.5% | 15 | n 不足（高 5、低 1；每組要 ≥ 4） |
| history | −30 天 | 1／-5.8% | 0／— | 0／— | 21 | n 不足（高 1、低 0；每組要 ≥ 4） |
| history | −90 天 | 0／— | 0／— | 0／— | 22 | n 不足（高 0、低 0；每組要 ≥ 4） |
| history | −180 天 | 0／— | 0／— | 0／— | 22 | n 不足（高 0、低 0；每組要 ≥ 4） |
| cohort_only | 錨點 | 0／— | 1／+1.4% | 0／— | 8 | n 不足（高 0、低 0；每組要 ≥ 4） |
| cohort_only | −30 天 | 0／— | 1／+0.9% | 0／— | 8 | n 不足（高 0、低 0；每組要 ≥ 4） |
| cohort_only | −90 天 | 0／— | 0／— | 0／— | 9 | n 不足（高 0、低 0；每組要 ≥ 4） |
| cohort_only | −180 天 | 0／— | 0／— | 0／— | 9 | n 不足（高 0、低 0；每組要 ≥ 4） |

- **history：不足**（高≥低 0 個時點、高<低 0 個時點；其餘 n 不足）
- **只在組裡的 9 檔：不足**
- 錨點那一格（history）有值的 7 列裡 **5 列在高組**（AEHR 88.9、LITE 90.2、MU 92.3、COHR 88.8、AEVA 85.0）——入圖時多半已在自己三年區間的頂部；
  低組只有 NVDA（13.2）一列。⚠ n 太小，這是描述、不是判讀。

## 為什麼量不到（缺席分型；由產生缺席的程式自己宣告，L16）

| 缺席原因 | 格數 | 代號 |
|---|---|---|
| 非美國 SEC 申報人、非台股：沒有機械的財報歷史（`upstream_unavailable`） | 40 | 000660.KS、300308.SZ、6268.T、6324.T、6594.T、6680.HK、ENA.V、IQE.L、LYC.AX、SIVE.ST |
| 三年窗不滿：Engine C 價格歷史 2023-08-31 起（`insufficient_evidence`） | 34 | AAOI、AEHR、AEVA、AXTI、COHR、FN、LITE、MP、MU、NVDA |
| 台股沒有歷史股數，市值序列組不出來（`upstream_unavailable`） | 20 | 2455.TW、3081.TWO、3363.TWO、4971.TWO、4979.TWO |
| 20-F／40-F：companyfacts 股數與掛牌單位（ADS）比率沒登記（`inputs_incompatible`） | 16 | GFS、HIMX、POET、TSEM |
| 當天的 EV/S 算不出來（`insufficient_evidence`） | 4 | META |
| **有值** | **10** | |

**卡住較早時點的是「窗<3年」**：11 檔美股的 Engine C 價格歷史一律從 **2023-08-31** 起（財報回到 2021 年）；三年窗的容差是 30 天
（`HISTORY_SLACK_DAYS`），所以**時點 t 不早於約 2026-07-31 才量得到**——錨點前 30／90／180 天大多落在這之前（AEHR 的錨點前 30 天＝08-01，剛好過線）。
其餘缺席是結構性的（台股沒有歷史股數、非 SEC 申報人沒有機械財報、20-F 的 ADS 比率）。
→ failure log **#12**（本報告 case X1）。

## 另印：之後曾達 2 倍的格在那個時點被分在哪一組（不進判讀線）

21 格（18 檔），**全部「未量」**：000660.KS、2455.TW、300308.SZ、3081.TWO、6324.T、AAOI、AEHR、AEVA、AXTI、ENA.V、GFS、HIMX、IQE.L、LITE、MU、POET、SIVE.ST、TSEM。
贏家出現的時點正好都是量不到的時點（太早、或台股／海外）——這是本次最重要的一件事：H9 想防的「判斷層把我們從贏家身上說服走」（AXTI，n＝1），
在可量測的資料裡**一筆樣本都沒有**。

## 每列明細（百分位或缺席分型；錨點起報酬與超額）

| lane | 代號 | 錨點 | 錨點 | −30 天 | −90 天 | −180 天 | 錨點→10-02 報酬 | 對光通訊組超額 | 之後曾達 2 倍的時點 |
|---|---|---|---|---|---|---|---|---|---|
| cohort_only | 2455.TW | 2026-09-30 | 台股 | 台股 | 台股 | 台股 | +5.1% | -3.1% | −180 |
| cohort_only | 300308.SZ | 2026-09-30 | 非SEC | 非SEC | 非SEC | 非SEC | +0.0% | -8.6% | −180 |
| cohort_only | 3081.TWO | 2026-09-30 | 台股 | 台股 | 台股 | 台股 | +8.5% | +0.6% | −90、−180 |
| cohort_only | 3363.TWO | 2026-09-30 | 台股 | 台股 | 台股 | 台股 | +3.4% | -4.9% | — |
| cohort_only | 4971.TWO | 2026-09-30 | 台股 | 台股 | 台股 | 台股 | +8.9% | +1.0% | — |
| cohort_only | 4979.TWO | 2026-09-30 | 台股 | 台股 | 台股 | 台股 | +2.8% | -5.5% | — |
| cohort_only | ENA.V | 2026-09-30 | 非SEC | 非SEC | 非SEC | 非SEC | +4.3% | -4.0% | −180 |
| cohort_only | FN | 2026-09-30 | 61.5（中） | 58.5（中） | 窗<3年 | 窗<3年 | +9.3% | +1.4% | — |
| cohort_only | POET | 2026-09-30 | 20-F | 20-F | 20-F | 20-F | +4.1% | -4.1% | −180 |
| history | 000660.KS | 2026-09-10 | 非SEC | 非SEC | 非SEC | 非SEC | -0.6% | -11.8% | −180 |
| history | 6268.T | 2026-08-31 | 非SEC | 非SEC | 非SEC | 非SEC | +6.8% | -4.6% | — |
| history | 6324.T | 2026-08-19 | 非SEC | 非SEC | 非SEC | 非SEC | +16.1% | +4.1% | −180 |
| history | 6594.T | 2026-09-01 | 非SEC | 非SEC | 非SEC | 非SEC | -17.7% | -31.8% | — |
| history | 6680.HK | 2026-08-31 | 非SEC | 非SEC | 非SEC | 非SEC | -11.2% | -22.7% | — |
| history | AAOI | 2026-07-24 | 窗<3年 | 窗<3年 | 窗<3年 | 窗<3年 | +15.4% | -15.3% | −180 |
| history | AEHR | 2026-08-31 | 88.9（高） | 91.5（高） | 窗<3年 | 窗<3年 | +35.2% | +23.8% | −180 |
| history | AEVA | 2026-08-14 | 85.0（高） | 窗<3年 | 窗<3年 | 窗<3年 | -36.6% | -41.4% | −180 |
| history | AXTI | 2026-07-28 | 窗<3年 | 窗<3年 | 窗<3年 | 窗<3年 | +100.8% | +64.0% | 錨點、−180 |
| history | COHR | 2026-08-18 | 88.8（高） | 窗<3年 | 窗<3年 | 窗<3年 | +10.0% | +3.9% | — |
| history | GFS | 2026-09-10 | 20-F | 20-F | 20-F | 20-F | +9.4% | -1.8% | −180 |
| history | HIMX | 2026-08-27 | 20-F | 20-F | 20-F | 20-F | +8.3% | +1.7% | −180 |
| history | IQE.L | 2026-08-03 | 非SEC | 非SEC | 非SEC | 非SEC | +34.6% | +5.3% | −180 |
| history | LITE | 2026-07-21 | 窗<3年 | 窗<3年 | 窗<3年 | 窗<3年 | +29.6% | +3.0% | −180 |
| history | LITE | 2026-08-11 | 90.2（高） | 窗<3年 | 窗<3年 | 窗<3年 | +32.3% | +21.5% | — |
| history | LYC.AX | 2026-08-30 | 非SEC | 非SEC | 非SEC | 非SEC | -20.4% | -33.8% | — |
| history | META | 2026-07-31 | EV/S缺 | EV/S缺 | EV/S缺 | EV/S缺 | +30.9% | -8.9% | — |
| history | MP | 2026-08-27 | 65.8（中） | 窗<3年 | 窗<3年 | 窗<3年 | -20.4% | -27.0% | — |
| history | MU | 2026-08-19 | 92.3（高） | 窗<3年 | 窗<3年 | 窗<3年 | +14.7% | +2.8% | −180 |
| history | NVDA | 2026-08-11 | 13.2（低） | 窗<3年 | 窗<3年 | 窗<3年 | +7.7% | -4.5% | — |
| history | SIVE.ST | 2026-07-23 | 非SEC | 非SEC | 非SEC | 非SEC | -1.1% | -25.9% | −90、−180 |
| history | TSEM | 2026-08-27 | 20-F | 20-F | 20-F | 20-F | +9.6% | +3.0% | −180 |

## PIT 核對（每個有值的格）

| 代號 | 時點 t | 百分位 | 口徑 | 覆蓋率 | 該時點用到的最晚申報日 | ≤ t？ |
|---|---|---|---|---|---|---|
| AEHR | 2026-08-31 | 88.9 | P/S | 1.0 | 2026-07-27 | ✅ |
| AEHR | 2026-08-01 | 91.5 | P/S | 1.0 | 2026-07-27 | ✅ |
| LITE | 2026-08-11 | 90.2 | P/S | 1.0 | 2026-05-06 | ✅ |
| MU | 2026-08-19 | 92.3 | P/S | 1.0 | 2026-06-25 | ✅ |
| NVDA | 2026-08-11 | 13.2 | EV/S | 1.0 | 2026-05-20 | ✅ |
| COHR | 2026-08-18 | 88.8 | P/S | 1.0 | 2026-08-14 | ✅ |
| MP | 2026-08-27 | 65.8 | P/S | 1.0 | 2026-08-07 | ✅ |
| AEVA | 2026-08-14 | 85.0 | P/S | 1.0 | 2026-08-06 | ✅ |
| FN | 2026-09-30 | 61.5 | P/S | 1.0 | 2026-08-18 | ✅ |
| FN | 2026-08-31 | 58.5 | P/S | 1.0 | 2026-08-18 | ✅ |

## 偏差標註（registration §0.1）

| 偏差 | 本報告的情況 |
|---|---|
| ① discovery lookahead | history 列的錨點是**入圖日**（舊店 shadow 錨點、不含判斷）——系統當時有路徑看見它，但入圖本身是選擇；只在組裡的 9 檔錨點是 2026-09-30 組定義日，組是看了題材之後才定的 |
| ② 選樣偏差 | 母體＝曾入圖的 history lane（含輸家）∪ 光通訊組；不是隨機樣本；有值的 10 格全是美國 10-Q 申報人 |
| ③ 超額基準回溯 | 光通訊組 2026-09-30 才定義——**所有早於 09-30 的時點都是拿今天的組回頭比**（回溯） |

## 對檢查點的意義（plan §14 第 4、10 項）

- 「已定價等回落」的寫法（§14 #4）：本次 R1 **不構成**改 skill 文字的證據（不足 ≠ 削弱）；但它說明「已定價①」在現有資料下對歷史判斷幾乎量不到。
- 三題的 as-of 視角（§14 #10）：**as-of 本身算得出來**（取數函式接受 today、純函式逐日 as-of）——真正的限制是 Engine C 的歷史深度與結構性缺席，不是 as-of 沒接。
  要讓 R1 在第二期有判讀力，最小的動作是把美股價格歷史往前補（可重建的 projection；寫入要另外決定，本 Step 不做）。

## 附錄：產生程式碼（逐字；`r1_replay.py`）

```python
"""Phase 7 Step 7.2 — R1 已定價回放（X1；registration §7.2；H9 判讀線見 registration §1 H9）。

唯讀：Engine C（sqlite mode=ro）＋ yfinance（追蹤表同一支 `scripts.outcome_if_settled_today._provider_close_series`）。
百分位＝三題同一個純函式 `alpha.three_questions.own_history`，輸入是 `engine_c.three_question_inputs.get_three_question_inputs(today=t)`
——價格只到 t、財報與股數逐日以「filed ≤ 當天」取（`shared.as_of`），所以每個時點都是 point-in-time；另記每個時點實際用到的
最晚申報日（INV-6 的可檢查證據）。不改任何產品程式、不寫任何 ledger。輸出 r1_result.json（本檔同目錄）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
sys.path.insert(0, str(ROOT))

from alpha.providers.theme_cohorts import current_cohorts  # noqa: E402
from alpha.theme_cohort import close_on_or_before, cohort_return, series_return  # noqa: E402
from alpha.three_questions import own_history  # noqa: E402
from engine_c.three_question_inputs import get_three_question_inputs  # noqa: E402
from scripts.outcome_if_settled_today import _provider_close_series  # noqa: E402

OUT = Path(__file__).parent / "r1_result.json"
END = date(2026, 10, 2)            # 執行日 2026-10-04（週日）之前最後一個完整交易日
OFFSETS = (0, 30, 90, 180)         # 錨點，與錨點前 30／90／180 個日曆日
COHORT_ID = "tc_35b0d5cd521656ea"  # 光通訊主題等權組（2026-09-30，pq2 [656]）
COHORT_ONLY_ANCHOR = date(2026, 9, 30)
DB = ROOT / "library" / "private" / "engine_c" / "stockbot-engine-c-private-v1-458db5270ee2.db"


def group_of(pct: float | None) -> str:
    if pct is None:
        return "未量"
    if pct >= 67:
        return "高"
    if pct >= 33:
        return "中"
    return "低"


def latest_filed_used(inp: dict, t: date) -> str | None:
    filed = [str(r.get("filed"))[:10] for key in ("revenue_quarters", "revenue_annual", "shares_cover", "cash", "total_debt",
                                                    "operating_income_quarters")
             for r in inp.get(key) or () if r.get("filed") and str(r.get("filed"))[:10] <= t.isoformat()]
    return max(filed) if filed else None


def main() -> None:
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    pos = json.loads((ROOT / "library" / "private" / "app" / "state" / "positions.json").read_text(encoding="utf-8"))
    assert pos["lanes"]["history"]["n"] == 22 and len(pos["rows"]) == 22, "history lane 不是 22 列——停手核對"
    current, errors = current_cohorts()
    assert not errors, f"主題組 ledger 有壞行：{errors}"
    cohorts = [c for c in current if c.cohort_id == COHORT_ID]
    assert len(cohorts) == 1, "找不到光通訊組"
    cohort = cohorts[0]

    entries = [{"lane": "history", "ticker": r["ticker"], "company_id": r["company_id"],
                "anchor": date.fromisoformat(str(r["anchor_date"])[:10])} for r in pos["rows"]]
    history_tickers = {e["ticker"] for e in entries}
    for m in cohort.members:
        if m.ticker not in history_tickers:
            entries.append({"lane": "cohort_only", "ticker": m.ticker, "company_id": m.company_id, "anchor": COHORT_ONLY_ANCHOR})
    assert len({e["ticker"] for e in entries}) == 30, "去重後不是 30 檔"

    starts = [e["anchor"] - timedelta(days=max(OFFSETS)) for e in entries]
    fetch_from = min(starts) - timedelta(days=10)
    tickers = sorted({e["ticker"] for e in entries} | {m.ticker for m in cohort.members})
    series: dict[str, dict] = {}
    units: dict[str, str | None] = {}
    for tk in tickers:
        s, unit = _provider_close_series(tk, fetch_from)
        series[tk], units[tk] = s, unit

    rows = []
    for e in entries:
        for off in OFFSETS:
            t = e["anchor"] - timedelta(days=off)
            inp = get_three_question_inputs(e["ticker"], conn=conn, today=t, company_id=e["company_id"])
            res = own_history(inp, today=t)
            pct = res.get("value")
            ser = series.get(e["ticker"]) or {}
            abs_ret = series_return(ser, t, END)
            coh = cohort_return(cohort, start=t, end=END, series=series, exclude_company=e["company_id"],
                                exclude_ticker=e["ticker"])
            start_close = close_on_or_before(ser, t)
            later = [v for d, v in ser.items() if start_close and start_close[0] < d <= END]
            reached_2x = (max(later) / start_close[1] >= 2.0) if (start_close and later) else None
            rows.append({
                "lane": e["lane"], "ticker": e["ticker"], "company_id": e["company_id"], "anchor": e["anchor"].isoformat(),
                "offset_days": off, "t": t.isoformat(), "pct": pct, "group": group_of(pct),
                "absence_kind": res.get("absence_kind"), "absence_reason": res.get("reason"), "basis": res.get("basis"),
                "coverage": (res.get("detail") or {}).get("coverage"), "samples": (res.get("detail") or {}).get("samples"),
                "as_of_bar": res.get("as_of"), "latest_filed_used": latest_filed_used(inp, t),
                "filed_before_t": (latest_filed_used(inp, t) or "") <= t.isoformat(),
                "start_close_date": start_close[0].isoformat() if start_close else None,
                "abs_return": abs_ret, "cohort_return": coh["return"], "cohort_used": coh["members_used"],
                "cohort_missing": coh["missing"], "excess": (abs_ret - coh["return"]) if (abs_ret is not None and coh["return"] is not None) else None,
                "reached_2x_after_t": reached_2x, "quote_unit": units.get(e["ticker"]),
            })

    def summarize(lane: str) -> dict:
        out = {}
        for off in OFFSETS:
            sub = [r for r in rows if r["lane"] == lane and r["offset_days"] == off]
            groups = {}
            for g in ("高", "中", "低", "未量"):
                gs = [r for r in sub if r["group"] == g]
                ex = [r["excess"] for r in gs if r["excess"] is not None]
                groups[g] = {"n": len(gs), "n_excess": len(ex), "mean_excess": (sum(ex) / len(ex)) if ex else None,
                             "tickers": [r["ticker"] for r in gs]}
            hi, lo = groups["高"], groups["低"]
            if hi["n_excess"] >= 4 and lo["n_excess"] >= 4:
                verdict = "高≥低" if hi["mean_excess"] >= lo["mean_excess"] else "高<低"
            else:
                verdict = f"n 不足（高 {hi['n_excess']}、低 {lo['n_excess']}；每組要 ≥ 4）"
            out[str(off)] = {"groups": groups, "line": verdict}
        weak = sum(1 for v in out.values() if v["line"] == "高≥低")
        strong = sum(1 for v in out.values() if v["line"] == "高<低")
        status = "削弱" if weak >= 2 else ("支持" if strong >= 3 else "不足")
        return {"by_offset": out, "high_ge_low": weak, "high_lt_low": strong, "H9_status_for_this_subgroup": status}

    result = {"end": END.isoformat(), "fetch_from": fetch_from.isoformat(), "cohort": COHORT_ID,
              "n_entries": len(entries), "n_rows": len(rows), "rows": rows,
              "summary": {"history": summarize("history"), "cohort_only": summarize("cohort_only")},
              "two_x": [{"ticker": r["ticker"], "lane": r["lane"], "t": r["t"], "group_at_t": r["group"]}
                        for r in rows if r["reached_2x_after_t"]],
              "pit_violations": [r for r in rows if r["pct"] is not None and not r["filed_before_t"]]}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    measured = sum(1 for r in rows if r["pct"] is not None)
    print(f"entries {len(entries)} rows {len(rows)} measured_pct {measured} pit_violations {len(result['pit_violations'])}")
    for lane in ("history", "cohort_only"):
        s = result["summary"][lane]
        print(lane, "→", s["H9_status_for_this_subgroup"], "|", {k: v["line"] for k, v in s["by_offset"].items()})


if __name__ == "__main__":
    main()
```
