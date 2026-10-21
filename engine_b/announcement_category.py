"""台股重大訊息的主旨類別（Phase 7 批次二 E2；failure log #63；使用者 2026-10-21 Q2 A）。

**事發：** 例行重訊（注意交易資訊、法說會召開、內線／澄清公告）叫醒語意反證——10-15 一次判 8 條、10-16 7 條、10-17 奇鋐與富世達
內線澄清一則叫醒 14 條，全部判無關。

**做什麼（Q2 A）：** 醒來時從重訊**自己的主旨**機械附上類別（封閉字彙，下表），語意佇列照（公司、類別）分組、一組判一次。
**喚醒條件不動**——A 不減少叫醒，只減少判定次數；跑兩週量「例行類別占語意判定的比例」再談 B（INV-5：先量測後放閘）。
「取得或處分資產」**不得**列進例行：它本身就是快接頭層反證 #3 的條件。主旨寫法不一（「澄清」「說明」）→ 認不得的一律落「其他」、
單獨判（INV-3：不靜默併組）。
"""
from __future__ import annotations

from typing import Any, Mapping

#: 類別 → 給人讀的名字。封閉字彙。
CATEGORIES: Mapping[str, str] = {
    "attention_trading": "注意交易資訊",
    "investor_conference": "法說會召開",
    "insider_or_clarification": "內線或澄清",
    "intercompany": "子公司間交易",
    "asset_transaction": "取得或處分資產",
    "other": "其他",
}
#: 零內容的三類（Q2 B 才會不叫醒它們；A 只用來量占比）。「取得或處分資產」刻意不在這裡。
ROUTINE = frozenset({"attention_trading", "investor_conference", "insider_or_clarification"})
_ASSET_WORDS = ("資產", "設備", "使用權", "不動產", "有價證券", "股權", "廠房", "土地", "機器")
_INTERCOMPANY_WORDS = ("資金貸與", "背書保證", "增資", "間交易", "往來", "捐贈")


def subject_of(lead: Mapping[str, Any]) -> str | None:
    """重訊 lead 的主旨（`crons.harvest_leads.announcements_to_leads` 寫的標題「… 重訊 日期：主旨」）；不是重訊 → None。"""
    if not str(lead.get("source") or "").startswith("mops:"):
        return None
    title = str(lead.get("title") or "")
    if "重訊" in title and "：" in title:
        return title.split("：", 1)[1].strip() or None
    first = str(lead.get("raw_text") or "").strip().splitlines()
    return first[0].strip() if first else None


def category_of(subject: str | None) -> str:
    s = str(subject or "")
    if not s:
        return "other"
    if "注意交易資訊" in s or "注意股票" in s:
        return "attention_trading"
    if "法人說明會" in s or "法說會" in s:
        return "investor_conference"
    if "澄清" in s or "媒體報導" in s or "內部人" in s:
        return "insider_or_clarification"
    if ("取得" in s or "處分" in s) and any(word in s for word in _ASSET_WORDS):
        return "asset_transaction"
    if "子公司" in s and any(word in s for word in _INTERCOMPANY_WORDS):
        return "intercompany"
    return "other"


def lead_category(lead: Mapping[str, Any]) -> dict[str, str] | None:
    """重訊 lead → `{ticker, category, subject}`；不是重訊回 None（只有重訊才分組）。"""
    subject = subject_of(lead)
    if subject is None:
        return None
    return {"ticker": str(lead.get("source") or "").split(":", 1)[1].upper(), "category": category_of(subject),
            "subject": subject}


__all__ = ["CATEGORIES", "ROUTINE", "category_of", "lead_category", "subject_of"]
