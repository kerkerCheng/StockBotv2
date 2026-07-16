# Graph Schema v0.2 — identity/provenance 規格

> 本檔把 `CLAUDE.md` 的 v0 schema 落成可寫程式的規格。
> 設計原則(見 CLAUDE.md L2/L4):**表的「形狀」鎖死,字彙留鬆**;屬性按「物理 / 關係 / 時變」三分歸位。
> 這是「故意會壞、等真實資料來撞」的 v0,撞出洞再升 v1。

---

## 0. 三層解耦(鐵律)

```
原始文件 → extract.py → [DB 無關的 node/edge JSON] → loader → Neo4j
                          ↑ intermediate_format.md      ↑ load_to_neo4j.py
```

- `extract.py`:**每份文件**輸出一份 JSON(本檔 §3 的格式),只描述「這份文件說了什麼」,不做合併、不碰 DB。
- `loader`:node 依全域 `id` MERGE；canonical domain edge 依
  `(src_id, relation, dst_id)` 產生的 `edge_key` MERGE。每份文件的 edge 候選值
  另建 `EdgeAssertion`。跨文件的合併、衝突、信心累加都在這層,不在抽取層。
- DB 可換:loader 是唯一綁 DB 的地方。

---

## 1. 節點 `nodes`

### 形狀(鎖死,改要搬資料)

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | string | 全域唯一,格式 `type前綴:slug`,例 `co:lumentum`、`tech:cpo`。跨文件靠它合併。 |
| `type` | string(字彙) | 見 §4 vocab |
| `name` | string | 正式名稱 |
| `abstraction_level` | string(字彙) | stack 分層,見 §4 |
| `role` | string \| null(字彙) | 僅 Company 有意義,見 §4 |
| `aliases` | string[] | 別名/代號/ticker |
| `attributes` | object(jsonb) | 彈性欄位,內在屬性放這(見下) |
| `confidence` | float 0–1 | 此節點主張的信心 |
| `source_ids` | string[] | 證據定位符,指向 §3 的 sources |
| `updated_at` | ISO8601 | loader 寫入時戳 |

### `attributes` 內的內在(慢變)瓶頸屬性

只放「換掉關係另一端也不變」的物理屬性:

- `ramp_difficulty_intrinsic`: int 1–5 — 該品類本質上多難量產(與「哪家供應商」無關)。
- `concentration_score`: int 1–5 — **衍生值**,不可手填。由 loader/批次作業數「進入此 component 的 `supplies_to` 邊 × 加權市占」算出,存成有來源的快取。
- `intrinsic_cycle_time_weeks`: int \| null — 不因交易對手改變的典型物理製程週期。

> ⚠️ 不要往 node 放 `substitutability` / `consensus_coverage` / `demand_proof_level`(見 L4,它們分屬 edge / 時變觀測 / 證據 metadata)。

---

## 2. 邊 `edges`

### 形狀(鎖死)

| 欄位 | 型別 | 說明 |
|---|---|---|
| `edge_key` | string | 由 `(src_id, relation, dst_id)` 經單一 helper 產生的全域穩定身分 |
| `src_id` | string | 來源節點 id |
| `dst_id` | string | 目標節點 id |
| `relation` | string(字彙) | 見 §4 |
| `attributes` | object(jsonb) | EdgeAssertion 的 materialized view；有衝突未決時該屬性為 unknown |
| `confidence` | float 0–1 | 只表示關係存在的信心，不決定屬性候選值 |
| `source_ids` | string[] | assertions 引文 ID 的去重聯集（快速查詢） |
| `source_doc_ids` | string[] | assertions 文件 ID 的去重聯集（快速查詢） |
| `updated_at` | ISO8601 | |

### `attributes` 內的關係型(隨另一端而變)瓶頸屬性

主要掛在 `supplies_to` / `depends_on` 上:

- `substitutability`: int 1–5(5 = 完全不可替代,對這條特定關係而言)
- `sole_source`: bool — 此買家是否單一來源
- `structural_lead_time_weeks`: int \| null — 特定供應關係在正常條件下的慢變典型交期。
- `qualification_status`: enum `none|sampling|qualifying|qualified|designed_in` \| null
- `ramp_execution`: int 1–5 \| null — **這家供應商實際 ramp 能力**(與 node 的內在難度分開)

`lead_time_weeks` 已停用且 validator 會拒收。缺料、利用率、物流或特定日期造成的
實際交期是時變觀測；專用 Engine C schema 建成前只能存為 dated Claim。

### EdgeAssertion（每份文件的 edge 證據真相）

每個 extraction edge 建一個 `(:EdgeAssertion)`：

| 欄位 | 說明 |
|---|---|
| `id` | `<doc_id>_<local_edge_id>`，全域唯一 |
| `local_id` | extraction 內的原始 edge id |
| `edge_key` | 對應 canonical domain relationship |
| `src_id` / `relation` / `dst_id` | 可獨立重建 canonical triple |
| `attributes` | 該文件提出的候選屬性 JSON；不得被其他文件覆寫 |
| `confidence` | 該 assertion 對關係存在／候選資訊的信心 |
| `source_ids` | 該文件內逐字引文 ID |
| `source_doc_id` | 文件 `doc_id`；U3 以 `CITES` 連到 SourceDoc |

Canonical relationship 的屬性是 assertions 的 materialized view，不是最後載入者的
值，也不得用 relationship confidence 對衝突屬性投票。

### Edge attribute conflict / resolution

衝突單位是 `edge_key + attribute`。Detector 只比較 EdgeAssertion 中明確出現的候選：

- 全部明確值相同 → 自動投影；
- null 加一個明確值 → 投影明確值；
- 兩個以上不同的明確值 → open conflict，canonical 該屬性不存在。

`conflict_id` 由 `edge_key + attribute` 穩定產生；`candidate_set_hash` 由排序後的
assertion IDs 與 canonical candidate values 產生。Open queue 每次現算，不落 mutable
registry。核准決議才存 `library/resolutions/<conflict_id>.json`，且必須符合
`schema/edge_resolution.schema.json`。候選集合改變時決議 stale、衝突自動重開。

Projector 每次完整重建 relationship `attributes`，並維護：

- `open_conflict_attributes`: 未解或 stale 的屬性名稱；
- `attribute_resolution_meta_json`: 自動一致或人工決議的 confidence、resolution ID、
  action、理由與 as-of；
- relationship `confidence`: 仍只代表關係存在，不參與屬性 tie-break。

`unknown`、`split_scope`、`move_to_observation` 都不捏造 canonical value；後兩者另要求
人工 schema/observation refactor。LLM 只能產 proposal，deterministic resolver 驗證
live candidate hash、assertion/source IDs、JSON Schema 與明確人工核准後才可寫決議與投影。

### SourceDoc（每份文件一個 provenance node）

每份 extraction 建一個 `(:SourceDoc {id: doc_id})`。固定 properties 為：
`title`、`source_type`、`evidence_tier`、`origin_entity`、`url`、`publisher`、
`published_at`、`retrieved_at`、`storage_permission`、`permission_basis`。
Phase I 舊 corpus 缺 URL、日期或 storage metadata 時允許 null；新遠端入口在 U12
開始要求 storage permission 兩欄必填。

Extraction properties 描述文件入庫時的 provenance；事後發生的可信度事件不回寫
凍結 extraction。這類可變狀態由 `library/source_audits/*.json` 版本化，經
`loader/project_source_audits.py` 投影為 `source_under_audit`、`audit_status`、
`audit_id`、`audit_note`、`audit_review_by`、`audit_ledger_path`。Lane Memo 實際引用
active audit 的 SourceDoc 時必須降級為 Research Note。

每個 Claim 與 EdgeAssertion 都必須各有且只有一條 `[:CITES]->(:SourceDoc)`。
Canonical domain relationship 不直接 CITES，僅保留 `source_doc_ids` / `source_ids`
去重聯集作快速查詢；逐文件、逐屬性證據一律經 EdgeAssertion → CITES 查詢。

---

## 3. 需求主張 `claims`(可選 array)

需求/瓶頸主張不是 node 靜態欄,是帶證據的獨立物件:

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | string | `<doc_id>_<local_claim_id>`；loader 會將舊 corpus 的 `cl1` 正規化為全域 ID |
| `statement` | string | 自然語言主張,例「CPO 放量會把外置雷射源需求拉 3x」 |
| `subject_id` | string | extraction 內可指向 node id 或 document-local edge id；入圖後分成 `subject_kind=node + ABOUT`，或 `subject_kind=edge + subject_edge_key` |
| `demand_proof_level` | enum | `confirmed|guided|inferred|speculative` |
| `disproof_condition` | string | **可證偽是一等公民**:什麼出現就推翻此主張 |
| `confidence` | float 0–1 | |
| `source_ids` | string[] | |

---

## 4. 字彙對照表(留鬆,加一列即可,不動表結構)

權威來源 = `schema/vocab.json`。新增字彙 = 改該檔 + extract prompt,**不動 DB schema**。

- `type`: `Company | Product | TechNode | Material | Standard | Person`
- `abstraction_level`(8 層 stack,由需求端到底層):
  `end_demand | network_systems | module_subsystem | device_chip | test_yield | foundry_packaging | equipment_epitaxy | materials_substrate`
- `role`(Company 在 stack 的角色):
  `leader | bottleneck_supplier | disruptor | foundry | test | network | adjacent_silicon | material_base`
- `relation`:
  `supplies_to | is_component_of | competes_with | enables | depends_on | invests_in | licenses_to`

---

## 5. 證據與信心(四階,鐵律:每個 node/edge/claim 必掛 source_ids)

`sources[].evidence_tier`:

1. **strongest** — filings / 法說會逐字稿 / IR 材料 / 客戶供應商直接揭露
2. **strong** — 官方供應商名單變動 / design-win 公告 / 產能擴張通知
3. **medium** — 可信產業報導 / 券商研究摘要
4. **weak** — 社群貼文 / 未證實論壇說法

`confidence` 建議起手式(v0,之後校準):tier1=0.9, tier2=0.75, tier3=0.55, tier4=0.3,多來源交叉再上調。

### 事後降級（來源可信度危機時的 confidence 調降程序）

confidence 不只會上調——當某文件**事後**爆出可信度危機（造假指控／審計持續經營疑慮／財報重編），以它為唯一來源的 node/edge/claim 需降級。程序（2026-07-12 Sivers 首例確立，對應 investment-sop.md 出場條件表）：

1. 查出所有 `source_ids` **完全**來自受質疑文件的 claims/edges（混合來源者不動）
2. 逐條判斷：公司自利型主張（量產時程、pipeline 金額、客戶關係）→ 調降 confidence（首例降至 0.4）；產業通識型主張（有其他文件間接佐證）→ 只標注不降級
3. 受影響項目一律加兩個屬性：
   - `source_under_audit`（bool）——標記來源正被審計/指控中
   - `audit_note`（string）——日期 + 原因 + 降級幅度 + 預計驗證日
4. 危機解除（如重編證實無虞）→ 移除標記、confidence 回調；證實指控 → 依 disproof 流程處理 thesis

Canonical relationship 的 `source_ids` / `source_doc_ids` 在 APOC 與非 APOC
路徑都必須使用去重聯集；逐文件候選值一律查 EdgeAssertion。

---

## 6. Sources — 來源欄位與獨立性鐵律

每個 node / edge / claim 的 `source_ids[]` 指向文件中的來源物件，每條來源應記錄：

| 欄位 | 說明 |
|------|------|
| `id` | 全域唯一格式 `<doc_id>_s<N>`，例 `coherent_q3fy26_s2` |
| `origin_entity` | 哪家公司發出（發出方，不是被分析方） |
| `origin_event` | 哪個原始事件，例 `coherent_fy26q3_earnings` |
| `evidence_tier` | 見 §5 |
| `quote` | 逐字引文，具體型號/公司名必須在 quote 裡出現才可建節點 |

**來源獨立性鐵律：** `confidence` 只在不同 `origin_event` 之間才累加。同一場法說會的多份摘要、同一 PR 被多家媒體轉發，算一個 `origin_event`，不是多重佐證。

---

## 7. `sole_source` 驗證規則

必須區分兩種情況，信心強度不同：

- `verified_by_absence`：文件沒有提到第二供應商 → 弱主張，`confidence` 不得超過 0.5，標 `sole_source_evidence_quality: weak`
- `verified_by_search`：主動查過競品 / 替代路徑 / 客戶自製可能，確認暫無 → 強主張

**鐵律：** 供應商自己的法說會說「我們是唯一供應商」不算 `verified_by_search`；需要**客戶端或第三方**來源印證。若某條 `sole_source=true` 的邊，其所有 source_ids 的 `origin_entity` 全是同一家供應商 → 自動標 `sole_source_evidence_quality: weak`（L8）。

---

## 8. 不進圖的東西（時變觀測，歸引擎 C 的 SQLite）

- `consensus_coverage`（underfollowed/emerging/crowded）：Company 的帶時戳市場認知，進時間序列。
- 股價、估值、月營收、產能利用率等所有數字：SQLite（Engine C），不進圖。
