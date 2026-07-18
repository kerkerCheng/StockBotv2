---
name: evidence-conflict-resolution
description: >
  審查 Engine A 同一 canonical edge 屬性的多份 EdgeAssertion 衝突，判斷時間／產品／客戶 scope、
  新證據是否 supersede 舊證據、或是否應移到 dated observation，並產生可由 deterministic resolver
  驗證的 resolution proposal。當使用者說「merge edge conflict」「解決 sole_source／substitutability／
  qualification／lead-time 衝突」「看 conflict queue」「這兩份證據怎麼合併」時使用。只處理投資研究
  圖譜的 evidence conflict，不處理 Git merge conflict；不得自行修改 resolution JSON 或 Neo4j。
---

# Edge Evidence Conflict Resolution

把 EdgeAssertion 候選證據整理成一份 proposal，交由使用者核准與 deterministic resolver 執行。
confidence 只描述證據強度，永遠不是勝負票數。

## Hard boundary

- 只輸出 proposal；不要直接編輯 `library/resolutions/` 或 Neo4j。
- 不要把 open queue 當錯誤或硬清零。`unknown` 是合法結論。
- 不要以「較新」「confidence 較高」單獨決勝；先確認 scope 與逐字證據。
- `sole_source`、`substitutability`、`structural_lead_time_weeks` 必須逐筆取得使用者明確核准。
- Proposal 當回合不得視為核准。只有使用者後續明確說批准該 `conflict_id + candidate_set_hash`
  時，外層 agent 才可呼叫 deterministic resolver；不得手改 persisted resolution。

## Workflow

1. 先跑 `python loader/edge_resolution.py project --dry-run`：`open_conflicts` 才是「真正未處置」數，
   `0` 代表全部已解、無事可做（`edge_conflicts.py` 的 raw 數字不會因已解而下降，別被它誤導）。
   確有未處置項時再執行 `python query/edge_conflicts.py` 選最高風險 conflict；需要機讀資料時加 `--json`。
2. 核對 `conflict_id`、`candidate_set_hash`、edge triple、attribute 與每個 assertion。
3. 依 `source_ids` 回到 frozen manifest 指向的 extraction，讀逐字 quote 與 SourceDoc metadata。
   找不到原文或 assertion/source ID 對不上時，停止並提 `unknown`；不可補猜。
4. 依序判斷：
   - 客戶、產品、地區或定義不同 → `split_scope`。
   - 短缺、利用率、物流或日期特定的實際交期 → `move_to_observation`。
   - 同 scope 的狀態隨時間前進，且較新文件明確取代舊狀態 → 可 `choose_value`，理由要寫
     清楚 supersession 與日期；僅「較新」仍不夠。
   - 真正互斥且無法判定 → `unknown`。
5. 套用證據階序：客戶端／獨立第三方優先於供應商自報；同一 origin_event 的轉述不算獨立。
   `sole_source=true` 沒有客戶端或第三方支持時不得升格為強結論。
6. 輸出下列 proposal JSON，接著用短文字說明取捨與需要使用者核准的點。不要加入
   `approved_by`、`approved_at` 或假裝使用者已批准。

```json
{
  "conflict_id": "conflict_<64 hex>",
  "edge_key": "edge:<64 hex>",
  "attribute": "qualification_status",
  "candidate_set_hash": "<64 hex>",
  "action": "choose_value|unknown|split_scope|move_to_observation",
  "selected_value": null,
  "supporting_assertion_ids": ["<doc_id>_e1"],
  "rejected_assertion_ids": ["<doc_id>_e2"],
  "supporting_source_ids": ["<doc_id>_s1"],
  "rationale": "說明 scope、時間、獨立性、supersession 與不採其他候選的原因",
  "resolved_confidence": 0.0
}
```

`choose_value` 的 `selected_value` 必須是現有候選值，supporting assertions/sources 必須真的支持
該值。其他 action 的 `selected_value` 必須是 `null`。

## Approval handoff

使用者後續明確核准後，外層 agent 只能用下列 deterministic 入口；它會重新查 live candidates、
驗 candidate hash、assertion/source IDs、approval 與 JSON Schema，失敗時不寫檔也不動圖：

```powershell
python loader/edge_resolution.py approve proposal.json `
  --approved-by "<human>" `
  --approved-at "<ISO-8601 with timezone>"
```

`split_scope` / `move_to_observation` 即使獲准也只保存決策並回報需人工 refactor，不自行改 schema。
