"""何時格裁決點（`alpha.narrative.checkpoints`）的兩份外部輸入——**只讀**（2026-11-10，failure log #150）。

候選板（`alpha.providers.candidates.candidate_context`）與寫入端（`alpha.providers.briefs.WriteContext.load`）共用這兩個讀法，
不各自再讀一份（L16）。讀不到回 `({}, 理由)`：那一半沒核，由呼叫端宣告（INV-3），不印成「沒過」。
"""
from __future__ import annotations

from typing import Any, Mapping

from ..narrative.checkpoints import WHEN_FORMS


def sec_filings_by_company() -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    """lead 池的 SEC 定期報告（`WHEN_FORMS`，含 /A）→ `company_id → [{form, filed, lead_id}]`。

    只收 `edgar:` 來源：那是照 ticker 監看的申報，company_id 就是申報人；指名抓的文件（`directed:`）的 company_id 是研究對象，
    不一定是申報人。`filed`＝lead 的 `published_at`（EDGAR 的申報日）。"""
    try:
        from engine_b import leads as leads_mod

        items: Any = leads_mod.load().get("leads") or {}
    except Exception as exc:  # noqa: BLE001 — 池讀不到只讓申報那一半說沒核
        return {}, f"lead 池讀不到（{type(exc).__name__}: {str(exc)[:80]}）"
    out: dict[str, list[dict[str, Any]]] = {}
    for lead in (items.values() if isinstance(items, Mapping) else items):
        if not isinstance(lead, Mapping) or not str(lead.get("source") or "").startswith("edgar:"):
            continue
        form = str(lead.get("form_type") or "").upper()
        if form.split("/")[0] not in WHEN_FORMS or not lead.get("company_id"):
            continue
        out.setdefault(str(lead["company_id"]), []).append(
            {"form": form, "filed": lead.get("published_at"), "lead_id": lead.get("lead_id")})
    return out, None


def calendar_checkpoints_by_ticker() -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    """名冊的檢核點（`thesis.lifecycle_schedule.checkpoints_by_ticker`，`{next_checkpoint_date}` 的來源之一）→ `ticker → [{date, what}]`。"""
    try:
        from thesis.lifecycle_schedule import checkpoints_by_ticker

        return checkpoints_by_ticker(), None
    except Exception as exc:  # noqa: BLE001 — 名冊讀不到只讓佔位字那一半說沒核
        return {}, f"名冊讀不到（{type(exc).__name__}: {str(exc)[:80]}）"


__all__ = ["calendar_checkpoints_by_ticker", "sec_filings_by_company"]
