"""已被定價了嗎：把追蹤期間的股價變化拆成「估值倍數」與「獲利預估」兩部分（唯讀）。

## 為什麼需要這個

`AGENTS.md` 的 Lane Memo 規格把 **variant perception 列為必填**，操作定義是
「當前股價／估值隱含的假設是 X，本 thesis 認為真實情況會是 Y」。但系統**沒有任何欄位
或報表在回答它**——`blind-spot-audit` 的 A2 lens（反身性／已被定價）因此每次都只能靠
人臨場判斷。2026-08-18 使用者問「COHR 是不是已經被 price in」時，答案是「答不出來」。

## 這不是估值模型，是算術

三個都是 Engine C 既有欄位的確定性分解，**不預測任何東西**：

1. **股價變化** vs **forward P/E 變化**。兩者相除即隱含的獲利預估修正：
   `(1+價格變化) / (1+倍數變化) - 1`。價格漲而倍數降 → 獲利預估上修得比股價快
   （較不像已被定價）；價格漲且倍數也漲 → 多重擴張（較像已被定價）。
2. **現價 vs 分析師目標均值**。價格超過目標均值是「賣方共識已被走完」的直接訊號。
3. **毛利率**同期變化，作為基本面是否同步改善的對照。

## 明確的限制（隨輸出常駐）

- 分析師目標會**追著股價跑**，落後且有偏。它只說「賣方共識在哪」，不說「值多少」。
- forward P/E 來自 provider 的共識 EPS，同樣是共識而非真相。
- **這裡沒有任何一項能證明「便宜」或「貴」。** 它只能回答「市場在這段期間改變了什麼看法」，
  以及「你的 variant perception 是否還有空間」。要主張 variant perception，
  仍必須自己寫出 X 與 Y。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

POINTER = ROOT / "library" / "private" / "runtime_pointer.json"
DECISION_DB = ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"


def _connect_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _anchors() -> dict[str, str]:
    """每檔的追蹤起點＝Shadow 錨點日（Decision Store authority）。"""
    try:
        with _connect_ro(DECISION_DB) as conn:
            rows = conn.execute(
                "SELECT ticker, min(substr(as_of,1,10)) AS d FROM shadow_observations "
                "WHERE status='observed' AND ticker IS NOT NULL GROUP BY ticker"
            ).fetchall()
        return {str(r["ticker"]): str(r["d"]) for r in rows}
    except sqlite3.Error:
        return {}


def _pct(new, old):
    if not isinstance(new, (int, float)) or not isinstance(old, (int, float)) or not old:
        return None
    return new / old - 1.0


def _positive_pe(value) -> float | None:
    """只有正的 forward P/E 才能做倍數分解。

    ⚠ 虧損公司的 forward P/E 是負數（實測 AEVA -14、IQE.L -229、SIVE.ST -205）。
    直接相除會得出「倍數變化 +30.6%、隱含獲利預估 -0.0%」這種**無意義卻長得像有意義**
    的數字——與需求鏈那次同一類錯誤（看起來結構化、實際沒有內容）。
    負值一律回 None，讓該列顯示「虧損中」而不是假裝算得出來。
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value) if value > 0 else None


def _fmt(v, suffix="%"):
    return "—" if v is None else (f"{v * 100:+.1f}{suffix}" if suffix == "%" else f"{v:.1f}")


def main() -> int:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    engine_c = ROOT / "library" / "private" / pointer["engine_c"]
    anchors = _anchors()
    if not anchors:
        print("沒有 Shadow 錨點可用", file=sys.stderr)
        return 1

    rows = []
    with _connect_ro(engine_c) as conn:
        for ticker, anchor in sorted(anchors.items()):
            snaps = conn.execute(
                "SELECT snapshot_date, price, pe_forward, ev_revenue, gross_margin, "
                "       analyst_target_mean "
                "  FROM financial_snapshots WHERE ticker=? AND price IS NOT NULL "
                " ORDER BY snapshot_date",
                (ticker,),
            ).fetchall()
            if len(snaps) < 2:
                continue
            # 錨點日當天或之後的第一筆；Engine C 的覆蓋期可能晚於 Shadow 錨點。
            start = next((s for s in snaps if str(s["snapshot_date"]) >= anchor), snaps[0])
            end = snaps[-1]
            price_chg = _pct(end["price"], start["price"])
            pe_from, pe_to = _positive_pe(start["pe_forward"]), _positive_pe(end["pe_forward"])
            pe_chg = _pct(pe_to, pe_from)
            implied = (
                (1 + price_chg) / (1 + pe_chg) - 1
                if price_chg is not None and pe_chg is not None
                else None
            )
            target = end["analyst_target_mean"]
            upside = _pct(target, end["price"]) if target else None
            rows.append(
                {
                    "ticker": ticker,
                    "from": str(start["snapshot_date"]),
                    "price_chg": price_chg,
                    "pe_from": pe_from,
                    "pe_to": pe_to,
                    "loss_making": pe_to is None,
                    "pe_chg": pe_chg,
                    "implied_eps": implied,
                    "gm_chg": _pct(end["gross_margin"], start["gross_margin"]),
                    "price": end["price"],
                    "target": target,
                    "upside": upside,
                }
            )

    print(f"# 已被定價了嗎（{date.today().isoformat()}）— 唯讀，這是算術不是估值模型\n")
    print("| 標的 | 自 | 股價 | fwd P/E | 倍數變化 | 隱含獲利預估 | 現價 vs 分析師目標 |")
    print("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -(x["upside"] if x["upside"] is not None else 9)):
        pe_span = (
            f"{r['pe_from']:.1f}→{r['pe_to']:.1f}"
            if r["pe_from"] and r["pe_to"]
            else "虧損中"
        )
        flag = ""
        if r["upside"] is not None and r["upside"] < 0:
            flag = " 🔴"
        elif r["upside"] is not None and r["upside"] < 0.10:
            flag = " 🟠"
        print(
            f"| {r['ticker']} | {r['from']} | {_fmt(r['price_chg'])} | {pe_span} "
            f"| {_fmt(r['pe_chg'])} | {_fmt(r['implied_eps'])} "
            f"| {_fmt(r['upside'])}{flag} |"
        )

    print(
        "\n**怎麼讀：**\n"
        "- **倍數變化為負、隱含獲利預估為正** → 獲利預估上修得比股價快，"
        "市場還在追基本面，較不像已被定價完畢。\n"
        "- **倍數變化為正且幅度接近股價漲幅** → 這段漲的是多重擴張，不是獲利，"
        "較像敘事已被 price in。\n"
        "- 🔴 現價已高於分析師目標均值｜🟠 剩餘空間不到 10%。\n"
    )
    print(
        "⚠ **限制：** 分析師目標會追著股價跑，落後且有偏；forward P/E 來自共識 EPS，"
        "同樣是共識不是真相。**本表不能證明便宜或貴**——它只說市場這段期間改變了什麼看法。"
        "要主張 variant perception，仍必須自己寫出「股價隱含 X，我認為 Y，催化劑 Z」。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
