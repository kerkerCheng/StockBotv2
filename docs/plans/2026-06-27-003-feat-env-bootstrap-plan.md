---
title: "feat: StockBotv2 環境重建 — plan002 前置 bootstrap"
date: 2026-06-27
status: active
type: feat
depth: standard
---

# feat: StockBotv2 環境重建 — plan002 前置 bootstrap

**Scope:** 從空機器重建 plan001 完成時的狀態：Neo4j Desktop DBMS 跑起來且 schema 套好、手工樣本已載入、Coherent Q3 FY2026 CPO 段落跑通 extract → validate → load 並入圖。這是 plan002 唯一的前置條件。本計畫不撰寫任何新程式碼。

---

## Summary

plan001 的所有程式碼已 commit 進 repo。現在需要在乾淨環境上逐步重建 plan001 的產物：

1. **Neo4j Desktop DBMS 建立 (U1):** 在已安裝的 Neo4j Desktop 2.1.4 裡建立一個新的 Local DBMS（Neo4j 5.x），密碼設為與 `.env` 一致的值，安裝 APOC plugin，啟動後在 Browser 確認可連線。
2. **Python 依賴安裝 (U2):** 在現有 `.venv` 裡跑 `pip install -r requirements.txt`。
3. **Schema 套用 + 樣本載入 (U3):** 透過 Neo4j Browser 套 `schema/neo4j_setup.cypher`，再用 `loader/load_to_neo4j.py` 載入 `samples/cpo_external_laser_source.json`，驗收四項 Browser query（對應 plan001 U1）。
4. **原始文件入庫 + extract 管線 (U4):** 把手邊的 `coherent_q3fy26_cpo.txt` 複製進 `library/raw/`，執行 `extract.py → validate.py → load_to_neo4j.py`，Browser 人工 review（對應 plan001 U2–U3）。
5. **plan002 起點確認 (U5):** 逐項確認 plan002 前置條件，確認 L6 gap 可重現（plan002 U1 要修的）。

---

## Problem Frame

程式碼全在 repo，pipeline 在上次 run 已驗通（L6 記錄了四個 schema gap）。缺的是：

- Neo4j Desktop 沒有 Active DBMS（環境重建後資料歸零）
- Python 套件未安裝（`.venv` 存在但 `requirements.txt` 尚未跑過）
- `.env` 的 `ANTHROPIC_API_KEY` 仍是佔位符 `sk-ant-...`
- `library/raw/` 空目錄，`extractions/` 空目錄

注意：repo 裡有 `docker-compose.yml`，但 Docker Desktop 尚未安裝，本計畫改用 Neo4j Desktop（已安裝 v2.1.4）。

---

## Requirements

| ID | Requirement |
|---|---|
| R1 | Neo4j Desktop DBMS (Neo4j 5.x) 建立完成，密碼與 `.env` 的 `NEO4J_PASSWORD` 一致 |
| R2 | APOC plugin 已安裝並啟用（DBMS 狀態 Running） |
| R3 | Browser 連 http://localhost:7474 可登入 |
| R4 | `schema/neo4j_setup.cypher` 套完後 `SHOW INDEXES` 看到 ≥4 個索引 |
| R5 | 手工樣本 loader 成功：`MATCH (n) RETURN count(n)` = 10，冪等性確認 |
| R6 | `.venv` 內四個套件 import 成功（anthropic / neo4j / dotenv / jsonschema） |
| R7 | `.env` 中 `ANTHROPIC_API_KEY` 填入真實值（非佔位符） |
| R8 | `library/raw/coherent_q3fy26_cpo.txt` 存在且開頭有 `# Source:` 注記行 |
| R9 | `extract.py` 執行完畢，產出 `extractions/coherent_q3fy26_cpo.json` |
| R10 | `validate.py` 對上述 JSON 印 OK，無 FAIL |
| R11 | `load_to_neo4j.py` 成功 MERGE 進圖，`co:coherent` 節點不重複 |
| R12 | 人工抽查 ≥3 條邊：quote 支持關係成立，無明顯幻覺 |

**plan002 起點標準:** R1–R12 全過。

---

## Key Technical Decisions

**KTD1 — Neo4j Desktop，非 Docker Compose**

Docker Desktop 未安裝，`docker-compose.yml` 暫不使用。Neo4j Desktop 2.1.4 已在機器上，直接建 Local DBMS 最快。`docker-compose.yml` 留在 repo 供未來 CI 或其他環境用。

**KTD2 — DBMS 密碼以 `.env` 的 `NEO4J_PASSWORD=c4780647` 為準**

建立 DBMS 時輸入密碼 `c4780647`，與 `.env` 一致，Python scripts 開箱即用。不需修改 `.env` 或任何程式碼。

**KTD3 — 原始文件直接複製，不重新取得**

使用者確認手邊仍有 `coherent_q3fy26_cpo.txt`，直接 copy 進 `library/raw/`，跳過重新找資料的步驟。

---

## Scope Boundaries

### In scope
- Neo4j Desktop DBMS 建立（密碼、APOC、啟動）
- Python 依賴安裝
- `.env` ANTHROPIC_API_KEY 填入
- Schema 套用 + 樣本載入 + 驗收
- 原始文件入庫 + extract → validate → load
- 人工 review + plan002 起點確認

### Deferred to Follow-Up Work
- plan002 U1 — L6 gap patches（source_id 前綴、Claim name 自動填、幻覺防護、vocab.json 補 `about`）
- plan002 U2 — 多文件擴張（5-8 篇）
- plan002 U3–U4 — graph_context.py + thesis 生成

### Outside this plan's scope
- 任何新 Python 程式碼
- docker-compose 環境設定（留給之後）
- Engine B / C 的任何基礎建設

---

## Implementation Units

### U1. Neo4j Desktop DBMS 建立

**Goal:** 在 Neo4j Desktop 建立一個 Local DBMS，密碼設為 `c4780647`，安裝 APOC plugin，啟動後 Browser 可連線。

**Requirements:** R1, R2, R3

**Dependencies:** 無

**Files:** 無（Desktop GUI 操作）

**Approach:**

1. 開啟 Neo4j Desktop。
2. 左側選 "Local DBMSs" → "+ New" → "Local DBMS"。
3. Name 隨意（如 `stockbot-dev`），Version 選 **Neo4j 5.x**（最新 5.x），Password 輸入 `c4780647`。點 Create。
4. DBMS 建立後，點 DBMS 旁的 "Plugins" 按鈕 → 搜尋 **APOC** → Install → 等安裝完成。
5. 點 "Start" 啟動 DBMS，等狀態顯示 **Running**（約 30 秒）。
6. 點 "Open" → Browser 在 http://localhost:7474 開啟，以 `neo4j` / `c4780647` 登入確認。

**Test scenarios:**
- Browser 連線成功，左上角顯示已連線的 DBMS 名稱
- 執行 `RETURN 1 AS ping` → 回傳 1（基本連線驗證）

**Verification:** Browser 可登入，`RETURN 1` 正常回傳。

---

### U2. Python 依賴安裝 + API key 填入

**Goal:** 安裝 `requirements.txt` 四個套件，填入真實 ANTHROPIC_API_KEY。

**Requirements:** R6, R7

**Dependencies:** 無（可與 U1 並行）

**Files:** `.env`（不 commit）

**Approach:**

1. 安裝套件：
   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. 驗證安裝：
   ```powershell
   .venv\Scripts\python.exe -c "import anthropic, neo4j, dotenv, jsonschema; print('OK')"
   ```

3. 編輯 `.env`，把 `ANTHROPIC_API_KEY=sk-ant-...` 換成真實的 API key。

**Test scenarios:**
- 四個套件 import 無 `ModuleNotFoundError`
- `.env` 中 `ANTHROPIC_API_KEY` 不以 `...` 結尾

**Verification:** `python -c "import anthropic, neo4j, dotenv, jsonschema; print('OK')"` 印出 OK；`.env` 中 key 為真實值。

---

### U3. Schema 套用 + 手工樣本載入

**Goal:** 套 `schema/neo4j_setup.cypher`，載入 `samples/cpo_external_laser_source.json`，四項驗收 query 全過（對應 plan001 U1）。

**Requirements:** R4, R5

**Dependencies:** U1, U2

**Files:** 無（Schema + loader 都已存在，只是執行）

**Approach:**

**套 Schema（Browser 方式最簡）:**
1. 開啟 http://localhost:7474。
2. 把 `schema/neo4j_setup.cypher` 全文貼進查詢框，點執行。
3. 確認沒有紅色錯誤訊息。

**載入樣本:**
```powershell
.venv\Scripts\python.exe loader\load_to_neo4j.py samples\cpo_external_laser_source.json --apoc
```

**Test scenarios（在 Browser 執行）:**
```cypher
SHOW INDEXES;
-- 應看到 ≥4 個索引 (entity_id_unique, entity_type, entity_level, entity_role + fulltext + vector)

MATCH (n) RETURN count(n);
-- 應為 10 (9 Entity + 1 Claim)

MATCH ()-[r:SUPPLIES_TO]->() RETURN r.attributes;
-- 應看到 2 筆，各有 substitutability / lead_time_weeks / qualification_status

-- 冪等性測試：重跑 loader，節點數不增加
```
再跑一次 loader，`MATCH (n) RETURN count(n)` 仍為 10。

**Verification:** 四項 query 全過，冪等性確認。

---

### U4. 原始文件入庫 + Extract 管線執行

**Goal:** 把 `coherent_q3fy26_cpo.txt` 複製到 `library/raw/`，跑完 extract → validate → load，人工 review ≥3 條邊（對應 plan001 U2–U3）。

**Requirements:** R8, R9, R10, R11, R12

**Dependencies:** U3

**Files:**
- `library/raw/coherent_q3fy26_cpo.txt` — 手動複製放入
- `extractions/coherent_q3fy26_cpo.json` — extract.py 產出（gitignored）

**Approach:**

1. 把手邊的 `coherent_q3fy26_cpo.txt` 複製到 `library/raw/`。確認檔案開頭有 `# Source:` 注記行。

2. 跑 extract：
   ```powershell
   .venv\Scripts\python.exe extract.py `
       --input "library/raw/coherent_q3fy26_cpo.txt" `
       --source-type transcript `
       --evidence-tier 1 `
       --title "Coherent Q3 FY2026 Earnings Call — CPO section" `
       --out "extractions/coherent_q3fy26_cpo.json"
   ```
   若失敗：開 `extractions/coherent_q3fy26_cpo_raw.txt` 看原始回應；調整 `prompts/extract_system.md` 後重跑。

3. 驗證 JSON：
   ```powershell
   .venv\Scripts\python.exe loader\validate.py extractions\coherent_q3fy26_cpo.json
   ```
   **必須印 OK，無 FAIL。**

4. 載入圖：
   ```powershell
   .venv\Scripts\python.exe loader\load_to_neo4j.py extractions\coherent_q3fy26_cpo.json --apoc
   ```

5. Browser 全圖預覽：
   ```cypher
   MATCH (n:Entity)-[r]->(m:Entity) RETURN n, r, m LIMIT 100;
   ```

**Test scenarios:**
- `validate.py` 印 OK（JSON Schema / vocab / referential integrity 三層全過）
- `co:coherent` 節點唯一（不出現 `co:coherent2` 等重複）
- 人工抽查 ≥3 條邊：找到 `source_ids` → 回 JSON 的 `sources` 確認 `quote` 支持該關係
- 無明顯幻覺（文件未提及的具體公司/型號不應出現）

**Verification:** validate.py 無 FAIL；人工 review ≥3 邊通過。

---

### U5. plan002 起點確認

**Goal:** 確認 plan002 所有前置條件達標；確認 L6 gap 可在本次 extraction 中重現（plan002 U1 要修的）。

**Requirements:** R1–R12（全部）

**Dependencies:** U4

**Files:** `CLAUDE.md`（若本次發現新 gap 才補）

**Approach:**

對照 plan002 Problem Frame 的三個前提逐一確認：

1. ✅ `extractions/coherent_q3fy26_cpo.json` 存在且已入圖
2. ✅ Neo4j 運行中，schema 套好（R3–R5）
3. ✅ L6 已記錄在 CLAUDE.md（勿重複記錄）

**確認 L6 gap 可重現（plan002 U1 的修補對象）：**

- **Gap 1 — Claim 缺 name：** 在 Browser 跑 `MATCH (c:Claim) RETURN c.id, c.confidence LIMIT 5` → Claim 節點顯示 `confidence` 當標籤（無 `name`）→ 確認 gap 存在
- **Gap 2 — source_ids 為局部 ID：** 開 `extractions/coherent_q3fy26_cpo.json`，確認 `source_ids` 裡是 `"s1"`, `"s2"` 等短 ID（不是 `coherent_q3fy26_s1`）→ 確認 gap 存在

若本次 extract 出現 L6 以外的新 gap，補記 `### L7 — ...` 至 CLAUDE.md，沿用 L6 格式。

**Test scenarios:**
- Browser `MATCH (c:Claim) RETURN c` → Claim 節點可見，gap 1 狀態確認
- 打開 JSON 確認 source_ids 格式，gap 2 狀態確認
- plan002 的所有 U 都有其前置條件（U1 需要：有一份舊格式 extraction + Neo4j running）

**Verification:** plan002 前置條件清單逐項打勾，可直接進入 plan002 U1。

---

## Open Questions

- **`library/raw/` gitignore 狀態：** 確認 `library/raw/coherent_q3fy26_cpo.txt` 不會被意外 commit（應已在 `.gitignore`）。若未加，加上 `library/raw/*.txt` 規則。
- **Python 3.14 相容性：** `.venv` 用的是 Python 3.14.6（非常新）。若 `pip install` 時任何套件出現 build error，降版至 3.11 或 3.12 建新 venv 是退路。

---

## Sources & Research

- `docs/plans/2026-06-07-001-feat-cpo-vertical-slice-plan.md` — plan001 原始驗收標準與 KTD（本計畫重執行 plan001 U1–U3）
- `docs/integration-run.md` — 手動執行清單（本計畫 U3/U4 步驟指令的來源）
- `CLAUDE.md L6` — 四個已知 schema gap（plan002 U1 的修補對象；本計畫 U5 確認可重現）
- `docker-compose.yml` — 存在但本計畫不使用（Docker 未安裝；KTD1 依據）
