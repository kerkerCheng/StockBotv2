"""研究讀燈的價格遮罩（failure log #152；ROADMAP「研究讀燈與讀敘事全文的出口遮價格欄」，2026-11-10）。

Q3W 量測（`docs/reports/phase7/cases.md`：寫裁決行之前不看價格）的曝光多半是被動的：讀燈、讀稽核區、讀敘事全文的出口
同一份就帶價格（11-10 一輪自報 5 次）。這裡只做**給研究看的畫面**——三題稽核區、research packet、敘事紀錄各遮一次；
**不改任何 artifact 與 ledger**（APP 照印價格，那是給使用者看的）。要答已定價那一格時由呼叫端加 `--prices` 拿原樣。

- 遮掉的欄位印成 `MASKED`（一個字串，不是 null——遮掉與缺席不同形，L12）。缺席照印：量不到是研究要知道的，它不是價格。
- 「出現在數字裡了嗎」整段照印（營收不是價格）；會死嗎只遮由市值導出的鍵（稀釋那一盞的發行額占市值）。
- 敘事正文裡寫的字面價格不遮——那是當時寫下的判斷，裁決要讀它。

純函式，零相依；回傳新的物件，不改輸入。
"""
from __future__ import annotations

from typing import Any, Mapping

#: 遮掉的欄位印這個字（不是 null：遮掉 ≠ 缺席）。
MASKED = "〔已遮：價格〕"
#: 遮過的畫面最上面印這一句。
PRICES_HINT = "價格欄已遮——要答已定價那一格再加 --prices（Q3W 名單內的檔先寫完裁決行）"
#: 加了 --prices 時印這一句（揭露欄照實記，cases.md Q3W）。
PRICES_SHOWN = "已印價格——Q3W 名單內的檔寫裁決行之前不看；看了就在揭露欄照實記"

#: 會死嗎 detail 裡由市值導出的鍵（`alpha.wipeout` 稀釋那一盞：發行額占市值）。
WIPEOUT_PRICE_KEYS: tuple[str, ...] = ("market_cap_usd", "pct_of_market_cap")
#: research packet `deterministic` 底下的價格欄（`alpha.contracts` 的 MarketSnapshot／ConsensusSnapshot／ValuationSnapshot）。
#: 分析師家數、營收共識、EPS 共識不是價格，照印。
PACKET_PRICE_FIELDS: Mapping[str, tuple[str, ...]] = {
    "market": ("price", "market_cap"),
    "consensus": ("target_mean", "forward_pe", "trailing_pe", "ev_revenue"),
    "valuation_market_implied": ("market_implied_growth", "market_implied_margin"),
}
#: 敘事紀錄的價格欄（寫入端記下的已定價①）。
BRIEF_PRICE_FIELDS: tuple[str, ...] = ("priced_at_write",)


def mask_three_questions(result: Mapping[str, Any]) -> dict[str, Any]:
    """三題稽核區的研究畫面：已定價每一行的值與 detail 遮掉（缺席與理由照印），會死嗎 detail 的市值鍵遮掉，
    出現在數字裡了嗎照印。"""
    out = dict(result)
    priced = []
    for row in result.get("priced_in") or ():
        row = dict(row)
        if row.get("value") is not None:
            row["value"] = MASKED
        if row.get("detail"):
            row["detail"] = {"masked": MASKED}
        priced.append(row)
    out["priced_in"] = priced
    die = []
    for row in result.get("will_it_die") or ():
        row = dict(row)
        detail = dict(row.get("detail") or {})
        for key in WIPEOUT_PRICE_KEYS:
            if detail.get(key) is not None:
                detail[key] = MASKED
        row["detail"] = detail
        die.append(row)
    out["will_it_die"] = die
    out["prices_masked"] = PRICES_HINT
    return out


def mask_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    """research packet（`JudgmentPacket.to_json()` 讀回的 dict）的研究畫面：`deterministic` 底下的市價、市值、目標價、
    本益比與市場隱含遮掉；其餘照印。"""
    out = dict(payload)
    deterministic = dict(payload.get("deterministic") or {})
    for section, fields in PACKET_PRICE_FIELDS.items():
        block = deterministic.get(section)
        if not isinstance(block, Mapping):
            continue
        block = dict(block)
        for field in fields:
            if block.get(field) is not None:
                block[field] = MASKED
        deterministic[section] = block
    out["deterministic"] = deterministic
    out["prices_masked"] = PRICES_HINT
    return out


def mask_brief_record(raw: Mapping[str, Any]) -> dict[str, Any]:
    """敘事紀錄（ledger 的一行）的研究畫面：寫入端記下的已定價①遮掉；正文照印。"""
    out = dict(raw)
    for field in BRIEF_PRICE_FIELDS:
        if out.get(field) is not None:
            out[field] = MASKED
    return out


__all__ = [
    "BRIEF_PRICE_FIELDS", "MASKED", "PACKET_PRICE_FIELDS", "PRICES_HINT", "PRICES_SHOWN", "WIPEOUT_PRICE_KEYS",
    "mask_brief_record", "mask_packet", "mask_three_questions",
]
