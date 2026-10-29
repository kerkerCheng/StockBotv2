"""每家公司在圖上的 assertion 寫入紀錄——敘事 stale 計數器 ③（ROADMAP「敘事 stale 計數器」，2026-10-29）用。

一筆 EdgeAssertion＝一份文件對一條邊的主張，帶寫入時間（`updated_at`）、兩端 id 與逐字；SourceDoc 帶原始 URL。
③ 要回答的是「這家公司在敘事正文寫完之後，圖上多了哪些邊、它們來自哪份文件、敘事讀過沒有」——每筆 assertion 就是
那一份文件寫進圖的紀錄，而且兩端就是公司 id（入圖收據 `library/private/intake_state/*.json` 只有 doc_id，不回指公司，
也不是每條入圖路徑都會寫）。逐字用來判「讀過」：raw 是節錄，同一個網址常有好幾份，比網址會把另一段節錄當成讀過。

唯讀、零判斷：只把列取出來、依兩端 id 建索引；哪一條算「敘事沒讀過」由 `alpha.candidates.unread_new_edges` 判。
"""
from __future__ import annotations

from typing import Any

# 逐字：`QUOTES` 只增不減、`source_ids` 重載時覆寫——有效逐字以 `source_ids` 為準（與 `query.sub_language.fetch_all_quotes`
# 同一個條件）。回傳 `id` 讓兩筆欄位全同的 assertion 不會在 collect 時被併成一列。
_Q_ASSERTIONS = """
MATCH (a:EdgeAssertion)
OPTIONAL MATCH (d:SourceDoc {id: a.source_doc_id})
OPTIONAL MATCH (a)-[:QUOTES]->(s:Source) WHERE s.id IN a.source_ids
RETURN a.id AS id, a.src_id AS src, a.relation AS relation, a.dst_id AS dst, a.updated_at AS updated_at,
       a.source_doc_id AS doc_id, d.url AS url, collect(DISTINCT s.quote) AS quotes
"""
_FIELDS = ("id", "src", "relation", "dst", "updated_at", "doc_id", "url")


def fetch_company_assertions(session) -> dict[str, list[dict[str, Any]]]:
    """節點 id → 碰到它的每一筆 assertion（`id`、`src`、`relation`、`dst`、`updated_at`、`doc_id`、`url`、`quotes`）。
    兩端各收一份；圖上沒有任何 assertion 的公司不在索引裡（呼叫端 `.get(cid, [])`：查過了、真的沒有）。"""
    out: dict[str, list[dict[str, Any]]] = {}
    for row in session.run(_Q_ASSERTIONS).data():
        item = {k: row.get(k) for k in _FIELDS}
        item["quotes"] = [str(q) for q in row.get("quotes") or () if q]
        for side in {str(row.get("src")), str(row.get("dst"))}:
            out.setdefault(side, []).append({**item, "quotes": list(item["quotes"])})
    return out


def load_company_assertions() -> dict[str, list[dict[str, Any]]]:
    """開一次唯讀連線取 `fetch_company_assertions`（連線設定與 `query.structure._load_edges` 同一份）。"""
    from .structure import _graph_driver

    driver = _graph_driver()
    try:
        with driver.session() as session:
            return session.execute_read(fetch_company_assertions)
    finally:
        driver.close()


__all__ = ["fetch_company_assertions", "load_company_assertions"]
