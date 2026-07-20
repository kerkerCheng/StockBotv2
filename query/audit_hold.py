"""audit_hold.py — Engine-A-owned 來源可信度 hold（跨引擎閘門的單一真相來源）。

`source_under_audit` 這個「事實」只住在 Engine A 的 SourceDoc 屬性上。促成升格的
兩個閘門面——L9 gate（`thesis/preconditions.py`）與 memo 的 evidence gate
（`thesis/evidence_manifest.py`）——都應該讀同一個事實，而不是各自重寫判斷。

本模組提供公司層級的 audit hold：若某公司的「證據基底」（它的 Claim 或它的邊上
EdgeAssertion 所 CITES 的 SourceDoc）裡有任一份 `source_under_audit=true`，則該公司
處於 credibility hold，不得升格為 [Investment Note]，直到審查解除。

刻意放在 query/（Engine A 讀取層），不塞進 Engine C：Engine C 維持獨立、只管量化
事實；「來源可不可信」是 provenance 判斷，屬 Engine A，由閘門層跨引擎消費。
"""
from __future__ import annotations

# 與 generate_lane_memo._Q_SOURCE_DIVERSITY 同一條證據基底路徑（claim about node
# + 公司邊上的 EdgeAssertion），只是篩 source_under_audit=true。
_Q_AUDIT_HOLD = """
MATCH (company:Entity {id: $company_id})
CALL (company) {
  MATCH (claim:Claim)-[:CITES]->(sd:SourceDoc)
  WHERE claim.subject_kind = 'node'
    AND claim.subject_node_id = company.id
  RETURN sd
  UNION
  MATCH (company)-[relationship]-()
  WHERE relationship.edge_key IS NOT NULL
  MATCH (assertion:EdgeAssertion {edge_key: relationship.edge_key})-[:CITES]->(sd:SourceDoc)
  RETURN sd
}
WITH DISTINCT sd
WHERE sd.source_under_audit = true
RETURN sd.id AS doc_id, sd.audit_note AS note, sd.audit_review_by AS review_by
ORDER BY doc_id
"""


def audit_hold_for_company(driver, company_id: str) -> dict:
    """回傳 {held, company_id, docs:[{doc_id,note,review_by}...]}。

    held=True 表示該公司證據基底有在審查中的來源 → 升格 hold。
    driver 由呼叫端提供（閘門層已握有 Neo4j 連線）。
    """
    if not company_id:
        return {"held": False, "company_id": company_id, "docs": []}
    with driver.session() as session:
        docs = [session_record.data() for session_record in session.run(
            _Q_AUDIT_HOLD, company_id=company_id
        )]
    return {"held": bool(docs), "company_id": company_id, "docs": docs}
