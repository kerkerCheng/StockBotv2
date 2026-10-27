"""分類前的內文（failure log #105；2026-10-27 使用者「修 #105」）。

事發：daily ⑦ 的分類器只看得到 lead 的 `raw_text`。EDGAR、MFN、公司新聞頁的 lead 在 harvest 時沒有 `raw_text`
（6-K／8-K 的主文件又只是封面，內容在附件 EX-99.x），雷達 lead 的事實句放在 `refs.radar_fact`、組 prompt 時沒帶——
分類器只看到標題就判 no_go。2026-09-01 起 25 則的理由寫「原文為空」，其中有一手申報（GFS、POET 6-K）與雷達挑出的事件
（Samsung 基板擴產拿到客戶支持）。它和「看了、不相關」同形，也沒有任何計數器說它是因為沒讀到（L13、INV-3）。

修法（根除，不是叫模型別這樣做）：分類批次組裝時（`engine_b.cli list --triage-batch`，daily ⑥）每則先決定
「分類器看得到什麼」，寫進批次列的 `body_status`（封閉字彙 `STATUSES`）：

- 送分類：`raw_text`（自帶）、`radar_fact`（雷達模型寫的一句事實，prompt 照實標明不是原文）、`self_described`
  （互動 session 登記的：沒有 `source_class`，標題就是研究 session 讀過來源後寫的摘要）、`cached`／`fetched`
  （用語意預篩同一組 fetcher、同一個存檔抓全文，批次列帶 `body_text`）。
- **不送分類**：`no_fetcher`（沒有取全文的方法）、`fetch_failed`（這次抓不到，下一輪重抓）、`deferred`
  （超過本輪抓取上限，下一輪先抓）。它們留在 pending、**不佔分類上限**；心跳「未 triage」那一行與 ⑤「未 triage」格
  印「其中無內文 N」（`held_pending`，不連網），由互動 session 讀全文後 triage。

沒有內文的 lead 到不了分類器，所以不會再因為看不到內文被判 no_go。

`source_class` 只由 harvest feed 宣告與雷達寫入（`leads.validate_provenance`）；互動 `register` 不寫它——
所以「沒宣告」就是「互動 session 自己寫的標題」。這是那個欄位唯一的寫入者決定的，不是另一層語意。
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from engine_b import semantic_prescreen as sp

TEXT_DIR = sp.TEXT_DIR
#: 批次列 `body_text` 的上限（與 `crons/llm_step.py::RAW_TEXT_MAX_CHARS` 同量級；附件放在前面，見 `semantic_prescreen`）。
BODY_MAX_CHARS = 3000
TRUNCATION_MARK = "……（以下截斷）"
#: 一輪最多抓幾份（daily ⑥ 的時限是分鐘級；EDGAR 6-K 一份要索引頁＋主文件＋附件三到五個請求）。
FETCH_LIMIT_PER_RUN = 20

#: `body_status` 封閉字彙 → 人話。
STATUSES: Mapping[str, str] = {
    "raw_text": "自帶原文",
    "radar_fact": "雷達事實句（雷達模型寫的摘要，不是原文）",
    "self_described": "互動 session 登記、標題就是摘要",
    "cached": "全文已存檔",
    "fetched": "本輪抓到全文",
    "no_fetcher": "沒有取全文的方法",
    "fetch_failed": "這次抓不到全文",
    "deferred": "超過本輪抓取上限",
}
SENDABLE = frozenset({"raw_text", "radar_fact", "self_described", "cached", "fetched"})
HELD = frozenset(STATUSES) - SENDABLE


def offline_status(lead: Mapping[str, Any], *, text_dir: Path = TEXT_DIR) -> str:
    """不連網判斷分類器看得到什麼：`raw_text`｜`radar_fact`｜`self_described`｜`cached`｜`missing`（要抓）。
    存檔照 `semantic_prescreen.cached_text` 的同一條規則：#105 之前只存了封面的 6-K／8-K 算 `missing`。"""
    if str(lead.get("raw_text") or "").strip():
        return "raw_text"
    if str((lead.get("refs") or {}).get("radar_fact") or "").strip():
        return "radar_fact"
    if not lead.get("source_class"):
        return "self_described"
    if sp.cached_text(str(lead.get("lead_id")), lead, text_dir=Path(text_dir)) is not None:
        return "cached"
    return "missing"


def held_pending(leads: Mapping[str, Mapping[str, Any]], *, text_dir: Path = TEXT_DIR) -> list[str]:
    """pending 裡分類器看不到任何內文的 lead（daily 不送分類、等互動 session）。不連網——心跳與 drain 用。"""
    return sorted(lid for lid, lead in leads.items()
                  if lead.get("status") == "pending"
                  and offline_status({**lead, "lead_id": lid}, text_dir=text_dir) == "missing")


def attach(rows: Iterable[Mapping[str, Any]], *, text_dir: Path = TEXT_DIR, fetch: bool = True,
           fetch_limit: int = FETCH_LIMIT_PER_RUN,
           fetcher: Callable[[Mapping[str, Any]], Callable[[], str | None] | None] | None = None,
           ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter]:
    """(送分類的列, 擋下的列, 各狀態計數)。順序不變；送分類的列帶 `body_status`，抓到全文的另帶 `body_text`。

    `fetch=False`：不連網（測試與手動檢視用），要抓的一律記 `deferred`。"""
    pick = fetcher or sp.fetcher_for
    sendable: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    counts: Counter = Counter()
    attempts = 0
    for row in rows:
        lead_id = str(row.get("lead_id"))
        status = offline_status(row, text_dir=text_dir)
        text: str | None = None
        if status == "cached":
            text = sp.cached_text(lead_id, row, text_dir=Path(text_dir))
        elif status == "missing":
            fn = pick(row)
            if fn is None:
                status = "no_fetcher"
            elif not fetch or attempts >= fetch_limit:
                status = "deferred"
            else:
                attempts += 1
                text, _reused = sp.load_or_fetch_text(lead_id, row, text_dir=Path(text_dir), fetch=fn)
                status = "fetched" if text else "fetch_failed"
        counts[status] += 1
        out = {**row, "body_status": status}
        if text:
            out["body_text"] = text[:BODY_MAX_CHARS] + (TRUNCATION_MARK if len(text) > BODY_MAX_CHARS else "")
        (sendable if status in SENDABLE else held).append(out)
    return sendable, held, counts


def summary_line(counts: Mapping[str, int], held: Iterable[Mapping[str, Any]]) -> str:
    """批次組裝的那一行：抓了多少、擋下多少與為什麼（INV-3：擋下要說話）。"""
    held = list(held)
    got = "、".join(f"{STATUSES[k]} {counts[k]}" for k in ("fetched", "cached") if counts.get(k))
    line = "內文：" + (got or "本輪沒有要抓的")
    if held:
        why = "、".join(f"{STATUSES[k]} {counts[k]}" for k in ("no_fetcher", "fetch_failed", "deferred") if counts.get(k))
        ids = "、".join(str(r.get("lead_id"))[:13] for r in held[:8]) + ("…" if len(held) > 8 else "")
        line += (f"；**無內文、不送分類 {len(held)} 則**（{why}：{ids}）——"
                 "留在 pending、不佔上限，互動 session 讀全文後 triage（failure log #105）")
    return line
