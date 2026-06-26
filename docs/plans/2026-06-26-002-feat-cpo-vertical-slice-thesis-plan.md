---
title: "feat: CPO/矽光子垂直切片 v1 — 多文件擴張 + Thesis 生成"
date: 2026-06-26
status: active
type: feat
depth: standard
origin: docs/plans/2026-06-07-001-feat-cpo-vertical-slice-plan.md
---

# feat: CPO/矽光子垂直切片 v1 — 多文件擴張 + Thesis 生成

**Scope:** 完成 CPO/矽光子垂直切片的後半段：修補 L6 schema gaps（重點：跨文件 source_id 命名空間）、擴張到 5-8 篇文件、建 Cypher-based 圖 context builder，最後用 Claude API 生成第一份 Directional Lane Memo thesis 並人工評分。不包含向量 RAG embedding、Engine B（SNS）、Engine C（基本面）。

---

## Summary

v0 計畫（`docs/plans/2026-06-07-001-feat-cpo-vertical-slice-plan.md`）驗通了 extract → validate → load → 人工 review 的管線，並在 CLAUDE.md L6 記錄了四個 schema gap。一篇文件（Coherent Q3 FY2026）已入圖，pipeline 品質確認可用。

本計畫完成剩餘步驟：

1. **L6 gap patches (U1):** 修跨文件 source_id 命名空間衝突、Claim name 自動填入、vocab.json 補 `about`、extract prompt 補幻覺防護規則。這些修補必須在多文件擴張前完成。
2. **多文件擴張 (U2):** 手選 5-8 篇 Tier 1/2 CPO 相關文件跑 extract → validate → load，建立夠厚的供應鏈圖（需求端 + 供應端 + 技術層）。
3. **圖 context builder (U3):** `query/graph_context.py` 以 Cypher query 把 Neo4j 圖轉成 LLM 可消化的結構化 Markdown context，取代向量 RAG。
4. **Thesis 生成 (U4):** `thesis/generate_lane_memo.py` 呼叫 Claude API，依 CLAUDE.md 的 Directional Lane Memo 模板輸出 `thesis/cpo_v1_lane_memo.md`。
5. **人工評分 + CLAUDE.md 更新 (U5):** 定義評分標準、評分 thesis、更新引擎開發順序記錄。

---

## Problem Frame

v0 證明了「一篇文件可以被正確抽取成有來源可追溯的圖」。但存在三個剩餘問題：

- **圖太薄：** 一篇文件無法覆蓋供應鏈全貌（需求端、供應端、技術層各需多份文件交叉印證），thesis 生成需要更豐富的圖。
- **L6 gap 會在多文件後放大：** source_id 命名空間衝突（`s1` 跨文件不唯一）若不先修，會在多文件 MERGE 後積累無法追溯的引用；幻覺防護規則若不補，同樣的問題會反覆出現。
- **系統缺乏輸出投資洞見的能力：** 截至目前，Engine A 只有「存」的部分，沒有「用」的部分。thesis 生成是整條 Engine A 的最終驗收。

---

## Key Technical Decisions

**KTD1 — Global source ID: extract.py post-processing 層加前綴，LLM prompt 不變**

現狀：LLM 輸出 `s1`, `s2` 等局部 ID；跨文件 MERGE 後圖裡的 `source_ids: ["s1"]` 指向不同文件的不同 quote，追溯失效。

決策：`extract.py` 在 `json.loads()` 後、`json.dumps()` 前做一次 ID transform：把所有 `sources[].id` 從 `s{N}` 重寫成 `{doc_id}_s{N}`，並同步更新 nodes/edges/claims 的 `source_ids` 陣列。LLM prompt 不變（LLM 繼續輸出短 ID，Python 後處理）。

遷移：現有 `extractions/coherent_q3fy26_cpo.json` 使用舊格式，U1 完成後重跑 extract 覆蓋，再重跑 loader 更新 Neo4j（MERGE 安全，只會更新 source_ids）。

**KTD2 — Claim name: 在 loader 自動填入，不改 JSON Schema**

中介 JSON 的 claim 物件沒有 `name` 欄位（intermediate_format.schema.json 有 `additionalProperties: false`，不能直接加）。Claim 資料進 Neo4j 後，Browser 顯示的標籤缺失。

決策：`loader/load_to_neo4j.py` 在寫 Claim 節點前 Python 端計算 `name = c.get("name") or c["statement"][:30] + "…"`，存入 `cl.name`。不修 JSON Schema（保持中介格式穩定），只修 loader 層。

**KTD3 — Thesis 不用向量 RAG，用 Cypher-based context builder**

向量 RAG 解決「不知道哪些段落相關」的問題，適用於原始文本搜尋。但本系統的知識已被 extract.py 結構化為圖（nodes/edges/claims），thesis 各段落（需求驅動、瓶頸、最強證據、可證偽條件）都對應精確的 Cypher query，直接 query 比向量搜尋更準確、有完整 source 追溯，且不需要 embedding API。向量索引（已建）留到後期語意搜尋場景再填。

**KTD4 — Thesis 生成：直接 anthropic SDK，不用 agent 框架**

`thesis/generate_lane_memo.py` 直接呼叫 `anthropic.messages.create`，context 由 `query/graph_context.py` 組裝成結構化 Markdown 後傳入（per CLAUDE.md L3：流程穩了再包框架）。

**KTD5 — 多文件選源優先順序（Tier 1 優先，覆蓋需求/供應/技術三維）**

- Tier 1 法說會：Coherent 其他季度（FY25 Q4 / FY26 Q1-Q2）、Lumentum、Broadcom CPO/AI ASIC 段落
- Tier 1 SEC 文件：COHR / LITE 最新 10-K 的 Products / Competition 章節
- Tier 2 論文：OFC 2025 CPO session（1-2 篇）
- 排除：Tier 3/4 新聞社群（thesis 主張必須有 Tier 1/2 支撐）

---

## High-Level Technical Design

### 系統流程 (v1)

```mermaid
flowchart LR
    A["library/raw/\n多篇 CPO 文件"] --> B["extract.py\n(+ source_id 前綴 post-processing)"]
    B --> C["extractions/*.json\nglobal source IDs"]
    C --> D["loader/validate.py\n三層驗證"]
    D -->|PASS| E["loader/load_to_neo4j.py\nMERGE (+ Claim name)"]
    E --> F["Neo4j\nCPO 知識圖譜"]
    F --> G["query/graph_context.py\n4 個 Cypher queries"]
    G --> H["結構化 context\nMarkdown ~3-8k tokens"]
    H --> I["thesis/generate_lane_memo.py\nClaude API + lane_memo_system.md"]
    I --> J["thesis/cpo_v1_lane_memo.md\nDirectional Lane Memo"]
    J --> K["人工評分\n(scoring_rubric.md)\n+ CLAUDE.md 更新"]
```

### Context builder 輸出結構（傳給 thesis generator 的 Markdown）

```
## CPO/矽光子供應鏈上下文

### 需求層 (end_demand)
- [node name] — role: [role], confidence: X.X (source: doc_id, tier N)
  ...

### 關鍵供應關係 (confidence >= 0.6)
| 供應商 | 關係 | 客戶/技術 | sole_source | substitutability | source (tier) |
| co:lumentum | supplies_to | tech:external_laser_source | true | 2 | coherent_q3fy26 (T1) |
...

### 瓶頸候選 (sole_source=true 或 substitutability ≤ 2)
- [A]--[relation]-->[B]: attributes summary, source

### 需求主張 (Claims, 強到弱排序)
- [statement] — proof_level: confirmed | guided | inferred
  disproof: [condition]
  subject: [entity name], confidence: X.X
```

---

## Scope Boundaries

### In scope
- L6 四個 gap patches（extract.py, loader, vocab.json, extract_system.md）
- 現有 coherent_q3fy26 extraction 重跑（source_id 格式遷移）
- 手選 5-8 篇 Tier 1/2 CPO 文件，跑 extract → validate → load
- `query/graph_context.py` — Cypher-based context builder
- `thesis/generate_lane_memo.py` — Directional Lane Memo 生成腳本
- `prompts/lane_memo_system.md` — thesis system prompt
- `thesis/scoring_rubric.md` — 評分標準
- 人工評分 + CLAUDE.md 更新（引擎順序、里程碑定義）

### Deferred to Follow-Up Work
- 向量 embedding 與 vector RAG（Neo4j vector 索引已建，之後填）
- Engine C — Postgres 基本面 pipeline（下一個主要計畫）
- Engine B — SNS/X 爬蟲
- Watchlist 與 Underwrite Sheet（tier 2/3 thesis 模板）
- 文件自動爬取（現在手選）
- `concentration_score` 衍生值自動計算
- 跨文件信心衝突解析

### Outside this plan's scope
- Engine B / Engine C 的任何基礎建設
- Agent 框架（LangGraph/CrewAI）
- Postgres schema 設計
- 生產環境部署

---

## Implementation Units

### U1. L6 Gap Patches

**Goal:** 修四個已知 schema/pipeline gap，確保多文件擴張前 pipeline 是乾淨的。

**Requirements:** CLAUDE.md L6 Gap 1-4 全部修正；修後重跑 coherent_q3fy26 驗證格式遷移。

**Dependencies:** 無

**Files:**
- `extract.py` (修改：add `_prefix_source_ids()` post-processing step)
- `loader/load_to_neo4j.py` (修改：Claim MERGE 加 `name` 欄位)
- `schema/vocab.json` (修改：`relation` 陣列加 `"about"`)
- `prompts/extract_system.md` (修改：加具體產品幻覺防護規則)

**Approach:**

*source_id 前綴（extract.py）:*
在 `json.loads(cleaned)` 後、`json.dumps()` 前，呼叫新函式 `_prefix_source_ids(doc, doc_id) -> dict`：
1. 建 mapping：`{old_id: f"{doc_id}_{old_id}" for s in doc["sources"]}`
2. 重寫 `doc["sources"]` 每個 item 的 `id`
3. 重寫 nodes、edges、claims 每個 item 的 `source_ids` 陣列（替換每個元素）
函式應是純函式（in → out），不在原地 mutate。

*Claim name auto-fill（loader/load_to_neo4j.py）:*
claims 迴圈裡，在 `session.run(...)` 前計算：
`name = c.get("name") or (c["statement"][:30] + "…")`
在 Claim 的 MERGE Cypher 裡加 `SET cl.name = $name`，params 加 `name=name`。

*vocab.json:*
在 `"relation"` 陣列末尾加 `"about"`（一行，不動其他順序）。
注意：`about` 是 loader 內部建的 Claim→Entity 關係，不在中介 JSON 的 edge 裡，所以 `intermediate_format.schema.json` 的 relation enum **不需要**更動。

*extract_system.md（幻覺防護）:*
在 Attribution Rule（section 3 或相當位置）後新增一條規則，用**加粗**標示：
> **產品名稱必須逐字出現在 quote 裡。若 quote 只提到產品類別（如 "data center interconnect"、"AI optics"、"external laser"），只抽出類別節點（如 `tech:dci_optics`），不推斷具體型號（如 `prod:400zr`、`prod:zr_plus`）。型號或具體產品名稱必須在 quote 中一字不差地出現。**

**Test scenarios:**
- 重跑 coherent_q3fy26：輸出 JSON 的 `sources[0].id` 為 `coherent_q3fy26_s1`（非 `s1`）
- 重跑後 `validate.py` 仍返回 OK（referential integrity 在新 ID 格式下正確）
- 重載入 Neo4j 後：`MATCH (n:Claim) RETURN n.name LIMIT 5` 返回非 null 的 `statement[:30]` 截斷字串
- `vocab.json` 的 `relation` 陣列包含 `"about"`
- 手動 smoke test：準備一個含 "data center interconnect" 但無 ZR/ZR+ 字樣的短段落，extract 後確認輸出 nodes 裡沒有 ZR 或 400ZR 節點

**Verification:** 重跑 coherent_q3fy26 完整 pipeline（extract → validate → load），Neo4j Browser 中 Claim 節點的 `name` 屬性顯示正常；所有 source_ids 含 `coherent_q3fy26_` 前綴。

---

### U2. 多文件 Curation + Batch Extraction

**Goal:** 累積 5-8 篇 Tier 1/2 CPO 相關文件到圖裡，使供應鏈圖覆蓋需求端、供應端、技術層三個維度。

**Requirements:** 每份文件通過 validate.py；與既有節點正確 MERGE（無重複）；圖跨越至少 4 個 abstraction_level。

**Dependencies:** U1（source_id 格式已統一，才能安全多文件 MERGE）

**Files:**
- `library/raw/<doc>.txt` × 5-8（人工準備，非 generated）
- `extractions/<doc>.json` × 5-8（pipeline 輸出）

**Approach:**

*選源優先順序（per KTD5）:*
每類至少涵蓋一篇，以下為建議清單：
1. Coherent Corp：FY26 Q1 或 Q2 法說會 CPO 段落（比較季度趨勢）
2. Lumentum (LITE)：最近 1 季法說會 external laser / CPO 段落
3. Broadcom (AVGO)：最近 1 季法說會 CPO / Tomahawk / AI ASIC 段落
4. Coherent 最新 10-K（Products 章節）：提供更完整的產品線描述
5. OFC 2025 論文（1-2 篇）：技術架構視角，補 Tier 2 證據

*前置確認（U2 開始前跑一次）:*
確認 Neo4j DBMS 已重啟且 APOC 生效（Desktop 安裝 APOC plugin 後需 restart）：
```cypher
RETURN apoc.version();
-- 正常應印出版本號，若報錯代表 APOC 未啟用，先重啟 DBMS 再繼續
```

*每份文件處理（重複以下步驟）:*
```powershell
python extract.py `
    --input "library/raw/<doc>.txt" `
    --source-type <transcript|filing|paper> `
    --evidence-tier <1|2> `
    --title "<描述>" `
    --out "extractions/<doc>.json"

python loader\validate.py extractions\<doc>.json
# 必須 OK，有 FAIL 先修再繼續

python loader\load_to_neo4j.py extractions\<doc>.json --apoc
```

*MERGE 確認（每份文件 load 後）:*
```cypher
MATCH (n:Entity {id: 'co:coherent'}) RETURN n.source_ids;
-- source_ids 陣列應有新增（跨文件累積）
MATCH (n:Entity) WHERE n.id CONTAINS 'coherent' RETURN n.id;
-- 不應出現 co:coherent_2 或類似重複
```

*已知：手工 sample 的 source_ids 格式不一致（v0 接受，不修）*
`samples/cpo_external_laser_source.json` 的 source_ids 是手工短 ID（`s1`, `s2`），不走 extract.py，不會被 U1 的前綴修補覆蓋到。Review 邊時若看到短格式 `s1`，先用 edge.id 比對各 JSON 的 edges 清單確認來源文件，再到對應 JSON 查 quote。跨文件命名空間統一（含 sample）列為 Deferred。

**Test scenarios:**
- 每份文件 validate.py 返回 OK（0 hard errors）
- 每份文件 load 後圖節點總數有增加
- `co:coherent`、`co:lumentum`、`co:broadcom`、`tech:cpo` 等核心節點的 `source_ids` 陣列隨文件數增長（跨文件 MERGE 成功）
- `MATCH (n:Entity) RETURN n.abstraction_level, count(n)` 顯示至少 4 個不同 level 有節點
- 抽查 2 份新文件各 2 條 edge：quote 支持關係方向（人工驗收）。Review 方式：用 `r.id` 比對各 source JSON 的 edges 清單找出所屬文件，再到該文件的 sources 取 quote，而非混查不同文件的 sources（Gap 2 防範）

**Verification:** 載入 5-8 份文件後，`MATCH (n:Entity)-[r]->(m:Entity) RETURN n, r, m LIMIT 100` 能看到跨越需求端、module/device、foundry/material 等多層的關係網絡。

---

### U3. Graph Context Builder

**Goal:** `query/graph_context.py` 用四個 Cypher query 把 Neo4j 圖轉成 LLM-ready 的結構化 Markdown context，供 thesis 生成使用。

**Requirements:** Context 涵蓋需求層、供應關係、瓶頸候選、Claims；每項含 source 追溯；總長度 < 8000 tokens（避免超出單次 API call）。

**Dependencies:** U2（圖需有足夠資料——至少 4-5 份文件入圖後才有意義）

**Files:**
- `query/__init__.py` (新建空檔，建立 module)
- `query/graph_context.py` (新建)

**Approach:**

主函式簽名：`build_context(driver) -> str`，回傳 Markdown 字串。

四個 Cypher query（依序執行，組合成一個 Markdown 字串）：

```cypher
-- 1. 需求層節點
MATCH (n:Entity {abstraction_level: 'end_demand'})
RETURN n.name, n.role, n.confidence, n.source_ids
ORDER BY n.confidence DESC LIMIT 10

-- 2. 關鍵供應關係
MATCH (a:Entity)-[r]->(b:Entity)
WHERE r.confidence >= 0.6
RETURN a.name, type(r), b.name, r.attributes, r.confidence, r.source_ids
ORDER BY r.confidence DESC LIMIT 50

-- 3. 瓶頸候選（sole_source 或 低 substitutability）
MATCH (a:Entity)-[r]->(b:Entity)
WHERE r.attributes CONTAINS '"sole_source": true'
   OR r.attributes CONTAINS '"substitutability": 1'
   OR r.attributes CONTAINS '"substitutability": 2'
RETURN a.name, b.name, r.relation, r.attributes, r.source_ids

-- 4. Claims（confirmed/guided 優先）
MATCH (c:Claim)-[:ABOUT]->(s:Entity)
RETURN c.statement, c.demand_proof_level, c.disproof_condition,
       c.confidence, s.name, c.source_ids
ORDER BY
  CASE c.demand_proof_level
    WHEN 'confirmed' THEN 1 WHEN 'guided' THEN 2
    WHEN 'inferred' THEN 3 ELSE 4 END,
  c.confidence DESC
LIMIT 20
```

Token 控制：context 組裝後做 `len(context) // 4` 粗估，若超過 7500 則縮減各 query 的 LIMIT（50→30→15）。

`query/graph_context.py` 的 env var 載入和 driver 建立，follow `loader/load_to_neo4j.py` 的既有模式。

**Patterns to follow:** `loader/load_to_neo4j.py` 的 env var 載入（dotenv + os.environ）與 driver 建立方式。

**Test scenarios:**
- `python -c "from query.graph_context import build_context; ..."` 執行成功，返回非空字串
- Context 字串含「需求層」段落（至少 1 個 end_demand 節點）
- Context 字串含至少 5 條供應關係
- Context 字串含至少 1 個 Claim 及其 disproof_condition
- 估計 token 數（`len(context) // 4`）< 8000
- 若圖為空（Neo4j 無資料），函式返回適當的「圖資料不足」訊息而非崩潰

**Verification:** `build_context()` 輸出的 Markdown 可直接貼入 Claude.ai 閱讀，結構清楚、每項都有 source 標注。

---

### U4. Directional Lane Memo Generator

**Goal:** `thesis/generate_lane_memo.py` 呼叫 Claude API，依 CLAUDE.md Directional Lane Memo 模板輸出 `thesis/cpo_v1_lane_memo.md`。

**Requirements:** Thesis 覆蓋 7 個必要段落；每個主張可追溯到圖中節點/邊；包含 disproof_condition；不含圖中沒有的幻覺主張。

**Dependencies:** U3（graph_context.py 能正常運行且返回有意義的 context）

**Files:**
- `thesis/__init__.py` (新建空檔)
- `thesis/generate_lane_memo.py` (新建)
- `prompts/lane_memo_system.md` (新建，thesis system prompt)
- `thesis/cpo_v1_lane_memo.md` (生成輸出)

**Approach:**

`prompts/lane_memo_system.md` 的 system prompt 結構：
1. **Role：** 你是半導體供應鏈投資研究員，負責根據知識圖譜資料撰寫投資方向備忘錄。
2. **Context 說明：** 你收到的上下文來自結構化知識圖譜（非原始文件），每條關係都有 source 和 confidence。
3. **輸出格式（7 段，依序）：**
   - **一句 thesis**（30 字以內，點出投資核心論點）
   - **需求驅動**（AI/雲端算力 → CPO 需求的因果鏈）
   - **Stack 摘要**（供應鏈哪幾層在發生什麼）
   - **主瓶頸**（誰是 chokepoint，為什麼，用供應鏈邊的屬性支撐）
   - **最強證據**（Tier 1/2 引用，具體數字或公司明確表態）
   - **什麼會推翻這個 thesis**（具體、可觀測的 disproof_condition）
   - **接下來盯什麼**（leading indicators / catalysts）
4. **約束：** 只用 context 中有來源的資訊；引用需標 source；每個主要論點必須有對應的 disproof_condition；不得自行加入市場知識。

`thesis/generate_lane_memo.py`:
- 建立 Neo4j driver，呼叫 `query.graph_context.build_context(driver)`
- 讀 `prompts/lane_memo_system.md`
- `anthropic.messages.create(model="claude-sonnet-4-6", max_tokens=4096, ...)`
- 輸出寫入 `thesis/cpo_v1_lane_memo.md`
- CLI：`python thesis/generate_lane_memo.py --out thesis/cpo_v1_lane_memo.md`

**Test scenarios:**
- 腳本 exit 0，`thesis/cpo_v1_lane_memo.md` 存在且非空
- 輸出含「一句 thesis」、「需求驅動」、「主瓶頸」、「最強證據」、「推翻條件」、「接下來盯什麼」等對應段落
- Thesis 中提到的公司名稱（如 Coherent、Lumentum）都在 Neo4j 圖中有對應節點（人工交叉確認）
- Thesis 包含至少 1 個具體的 disproof_condition（可從 Claims 追溯）
- ANTHROPIC_API_KEY 缺失時，腳本 exit 1 並印出明確錯誤訊息

**Verification:** 生成的 `thesis/cpo_v1_lane_memo.md` 人工可閱讀，結構完整，每個主張有 source 標記，disproof_condition 具體可觀測。

---

### U5. 人工評分 + CLAUDE.md 更新

**Goal:** 定義評分標準、人工評分 thesis、記錄學習、更新 CLAUDE.md 引擎順序與里程碑定義。

**Requirements:** 評分標準可指導未來 thesis 品質判斷；CLAUDE.md 反映已驗證的 A-first 路線與 A/C 交替策略；新 Lesson 記錄本次 thesis 主要發現。

**Dependencies:** U4

**Files:**
- `thesis/scoring_rubric.md` (新建)
- `CLAUDE.md` (修改：引擎順序、里程碑定義、新 Lesson)

**Approach:**

`thesis/scoring_rubric.md` 定義 5 個維度（各 1-5 分）：
1. **可信度（Credibility）：** 主張都有 Tier 1/2 一手來源支持？ (1=全部推測，5=全部 Tier 1)
2. **瓶頸清晰度（Chokepoint Clarity）：** 供應鏈的 chokepoint 被準確識別並解釋？
3. **可證偽性（Falsifiability）：** 每個主要論點有具體、可觀測的 disproof_condition？
4. **洞見密度（Insight Density）：** 投資者看完能採取行動，還是全是已知事實？
5. **完整性（Completeness）：** 7 個段落都有實質內容，且涵蓋需求/供應/技術三個視角？

評分後，把結果（各維分數 + 評語 + 整體評估 + 最弱的環節）記進 CLAUDE.md 新 Lesson（L7 或下一個可用編號）。

*CLAUDE.md 修改項目：*

1. 把「引擎順序 C → A → B」段落更新為：
   > **開發順序（更新版）:** A 先（垂直切片驗證端到端路線）→ 之後 A/C 交替推進（A 出 thesis → C 補基本面校準 → A 精進 → ...）→ B 最後。  
   > **判準：** A 切片讓系統能輸出洞見（thesis 為 A 的驗收），C 提供量化錨點（基本面數字校準 A 的定性判斷），兩者互補。A-first 已在 CPO/矽光子切片中驗證。

2. 在垂直切片段落補充兩段里程碑說明：
   - Milestone A（已完成）：1 篇文件 extract → graph → human edge review，L6 gap 記錄
   - Milestone B（本計畫）：5-8 篇文件 → Cypher context builder → thesis 生成 → 人工評分

**Test scenarios:**
- `thesis/scoring_rubric.md` 存在，5 個維度定義清楚
- 人工對 thesis 評分，結果（數字 + 文字）記進 CLAUDE.md
- CLAUDE.md 中不再有「引擎順序 C → A → B」的硬性順序字樣，改為更新後的描述
- CLAUDE.md 有新 Lesson（Lx）記錄 thesis 評分結果與發現
- Milestone A / Milestone B 定義可在 CLAUDE.md 中找到

**Verification:** CLAUDE.md 更新後，新 session 讀入時能清楚知道目前狀態（Milestone B 完成）和下一步（Engine C）。

---

## Open Questions

| # | Question | Status |
|---|---|---|
| OQ1 | Broadcom 法說會的 CPO 相關段落較分散（Tomahawk / AI ASIC / silicon photonics），要選哪幾段？ | 實作 U2 時決定；抓明確提到 co-packaged optics 或 external laser source 的段落 |
| OQ2 | graph_context.py 的 context 大小：5 份文件後 token 估計是否仍在 8k 以內？ | 實作 U3 後量測，必要時調降各 query 的 LIMIT |
| OQ3 | Thesis 中是否要納入 Watchlist（具體股票名）？ | 第一版 Directional Lane Memo 不加（per CLAUDE.md：「thesis 成立後才給名字」）；Watchlist 留給下一份文件（Watchlist 模板） |

---

## Risks & Dependencies

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| source_id 前綴 transform 產生雙重前綴（如 `doc_doc_s1`，若函式重複呼叫）| Low | 資料汙染 | `_prefix_source_ids()` 加防衛：若 source_id 已含 `_s` 格式則跳過；加 smoke test |
| 多文件後出現新 vocab gap，validate 失敗 | Medium | 需要先修 vocab 再繼續 | validate 失敗即停，看 VOCAB 錯誤訊息，更新 vocab.json，重跑 |
| 圖資料不足（文件太少）導致 thesis 空洞 | Medium | Thesis 無法驗證 | U2 至少 4-5 份文件入圖後才執行 U3/U4；context builder 若資料不足則返回警告 |
| context builder token 超限 | Low | API call 失敗 | Cypher LIMIT 動態調整；組裝後 token 估計並記錄 |
| LLM 在 thesis 生成時添加圖外幻覺 | Medium | Thesis 可信度下降 | system prompt 明確約束「只用 context 中有來源的資訊」；人工 U5 評分的「可信度」維度會抓到 |

---

## Sources & Research

- `docs/plans/2026-06-07-001-feat-cpo-vertical-slice-plan.md` — v0 計畫，本計畫延伸自此
- `CLAUDE.md` — L6 gap 定義、thesis 三級模板（Directional Lane Memo）、一手來源登記表、開發順序討論
- `schema/vocab.json` — 字彙對照表（本計畫補 `about`）
- `schema/intermediate_format.schema.json` — 確認 claim 無 `name` 欄位（additionalProperties: false），loader auto-fill 是正確做法
- `extract.py` — source_id transform 的實作位置
- `loader/load_to_neo4j.py` — Claim MERGE 的實作位置；graph_context.py 的 driver 建立 pattern
- `extractions/coherent_q3fy26_cpo.json` — 現有抽取輸出，U1 完成後重跑遷移格式
