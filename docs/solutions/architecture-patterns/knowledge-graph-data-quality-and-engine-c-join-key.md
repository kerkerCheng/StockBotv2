---
title: "Knowledge Graph Data Quality Patterns & Engine A→C Join Key Design"
date: 2026-07-05
category: docs/solutions/architecture-patterns/
module: engine-a-knowledge-graph
problem_type: architecture_pattern
component: database
severity: high
applies_when:
  - loading multiple documents into Neo4j property graph
  - LLM extracts claims with multiple subjects per statement
  - same concept appears under different names or abbreviations across documents
  - designing cross-engine (A to C) data flow requiring shared join keys
  - reviewing graph quality after a batch of document loads
tags:
  - neo4j
  - knowledge-graph
  - graph-quality
  - engine-c
  - ticker
  - claim-fanout
  - node-deduplication
  - canonical-id
  - isolated-nodes
  - join-key
  - loader
  - extract-pipeline
  - engine-a
  - supply-chain-graph
---

# Neo4j 圖資料品質模式 與 Engine C 啟動前置條件

> 適用場景：StockBotv2 每次多文件載入後的品質核查，以及 Engine C（基本面引擎）啟動前的架構準備。本文記錄 CPO/矽光子垂直切片 8 篇文件載入後（`docs/graph-review-v1.md`）浮現的五個可重複模式。

---

## Context

CPO/矽光子切片跑完 Milestone B（5-8 篇文件 → 圖 → thesis）之後，執行了第一次完整的圖品質人工審查（`docs/graph-review-v1.md`）。審查揭露五類問題：Claim 扇出、節點命名重複、孤立節點、跨季邊狀態變化、以及 Engine A→C join key 缺失。其中部分是 bug，部分是正確的設計選擇（只是視覺上讓人誤判），部分是必須在 Engine C 啟動前解決的架構 blocker。

這份文件整理這五類模式的判準、修法與優先順序，供下一個資料載入 session 和 Engine C 規劃直接引用。

---

## Guidance

### 模式 1：Claim 扇出問題（P1 — 立即影響 thesis 品質）

**問題描述**

`extract.py` 對每個 claim 允許多個 `subjects[]`。`loader/load_to_neo4j.py` 對 `subjects[]` 做簡單迭代，每個 subject 建一條 `ABOUT` 邊。一個 claim 有 5 個 subject 就產生 5 條 `ABOUT` 邊。

`graph_context.py` 的 Claims 查詢用 `MATCH (c:Claim)-[:ABOUT]->(s:Entity) RETURN c.statement LIMIT 20`，實際上在 20 筆配額裡重複看到同 3-4 個 claim statement，每個被展開 5-6 次。34 個 claim 節點對 thesis generator 看起來只有低多樣性。

**P1 修法（立即，不動 loader）**

在 `graph_context.py` 的 Claims 查詢改為先對 Claim 節點做 DISTINCT，再套 LIMIT：

```cypher
-- 修改前（有問題）：
MATCH (c:Claim)-[:ABOUT]->(s:Entity)
RETURN c.statement
LIMIT 20

-- 修改後（正確）：
MATCH (c:Claim)
WITH DISTINCT c
ORDER BY c.confidence DESC
RETURN c.id, c.statement, c.confidence
LIMIT 20
```

這個改法不需要重新抽取或改 loader，立即提升 thesis context 的 claim 多樣性。

**P4 修法（中期，改 extract prompt + loader）**

在 `prompts/extract_system.md` 加規則：每個 claim 最多 2 個 subject，第一個必須是「行為描述的主體」（primary subject），第二個是次要關聯。loader 收到 `subjects[]` 時只取前兩個。

---

### 模式 2：命名變體造成的重複節點（P2 — 已知技術債）

**問題描述**

不同來源文件對同一技術/產品使用不同措辭，LLM 從文件語言生成節點 ID，導致 6-8 組重複節點對：

| 重複組 | 節點 A | 節點 B |
|--------|--------|--------|
| 縮寫 vs 全名 | `tech:ocs` | `tech:optical_circuit_switch` |
| 有無類型後綴 | `tech:eml_laser` | `tech:eml` |
| 前綴差異 | `tech:transceiver_1_6t` | `tech:cloud_transceiver_1_6t` |
| 單複數 | `tech:dci_transceivers` | `tech:dci_transceiver` |
| 描述方式不同 | `tech:inp_6inch_fab` | `tech:six_inch_inp_production` |

**影響**：`source_ids` 和 `confidence` 分散在兩個節點，跨文件 MERGE 失效，瓶頸查詢的信心分數被稀釋。

**P2 修法（v2 項目）**

在 `schema/vocab.json` 加入 `aliases` 對照表，loader 在建立任何節點前先查對照表，找到別名就 MERGE 到 canonical ID：

```json
// schema/vocab.json — 新增 aliases 欄位
{
  "aliases": {
    "tech:ocs": "tech:optical_circuit_switch",
    "tech:eml_laser": "tech:eml",
    "tech:transceiver_1_6t": "tech:cloud_transceiver_1_6t",
    "tech:dci_transceivers": "tech:dci_transceiver",
    "tech:inp_6inch_fab": "tech:six_inch_inp_production"
  }
}
```

```python
# loader/load_to_neo4j.py — 載入節點前的正規化
ALIASES = vocab_config.get("aliases", {})

def resolve_canonical_id(node_id: str) -> str:
    return ALIASES.get(node_id, node_id)

# 在每個 node MERGE 前呼叫：
canonical_id = resolve_canonical_id(node["id"])
```

v1 先接受這批重複節點為已知技術債；v2 載入新文件前先更新 `aliases` 對照表。

---

### 模式 3：孤立節點（P3 — 查詢後品質核查標準動作）

**問題描述**

每次載入後用以下 Cypher 查孤立節點（無任何邊的非 Claim 節點）：

```cypher
MATCH (n:Entity)
WHERE NOT (n)-[]-() AND NOT n:Claim
RETURN n.id, n.type, labels(n)
ORDER BY n.type
```

本次審查發現 9 個孤立節點，其中最需要優先處理的：

- `co:jabil`（Company）：Lumentum 文件含有製造關係，但載入時未建邊
- `mat:gaas_substrate`（Material）：應有 `competes_with` 邊指向 InP 路徑（替代材料競爭）
- Person 節點（`hock_tan`, `wupen_yuen`, `james_anderson`, `julie_eng`）：無指向 Company 或 Claim 的邊

**處理原則**

- Company 和 Material 孤立節點優先：這兩類直接影響供應鏈查詢和瓶頸分析
- Person 節點優先順序較低：不影響供應鏈結構查詢，除非有具體需要（如法說會發言人 attribution）
- 每次載入後必跑此查詢，結果為零才算合格

---

### 模式 4：跨季邊狀態變化（正確模式，非 bug）

**現象（表面上看起來像重複）**

`co:lumentum --[SUPPLIES_TO]--> tech:uhp_laser` 在圖中出現兩次，`qualification_status` 不同：
- Q2 來源：`designed_in`
- Q3 來源：`qualifying`

**為何這是正確設計**

loader 的 MERGE 以邊的 ID（含 `doc_id`）為鍵；不同季度來源 = 不同 ID = 兩條邊共存。這保留了資格認證進程的時間歷史（`designed_in → qualifying` 代表跨世代的 scale-out → scale-up 進程）。

**關鍵洞見**：這個模式只有在多文件入圖後才可見。單一文件圖會遺漏這個跨代細節，而它正是 thesis 的核心支撐之一（技術成熟度軌跡）。

**操作規則**

瓶頸查詢返回同一方向的兩條邊時，先看 `source_ids` 的 doc date 再下判斷。視覺上看起來重複是可接受的資料噪音，不需要去重——去重反而會丟失時間維度資訊。

---

### 模式 5：Engine A→C Join Key — Ticker 欄位架構（P0 BLOCKER）

**問題描述**

圖中所有 Company 節點的 `attributes` JSON 缺少 `ticker` 欄位。Engine C（基本面引擎）要把 `co:coherent` 對應到 Postgres 裡的 `COHR` 財務數字，就需要這個 join key。這是 CLAUDE.md L9 明確列出的 Engine C 設計前置條件。

**為何單純修 extract prompt 是錯的**

讓 LLM 在抽取時生成 ticker 有三個根本問題：
1. LLM 對非美股 ticker 容易幻覺（如台股代號、KRX 代號）
2. 私人公司（Anthropic、OpenAI）沒有 ticker，LLM 可能捏造
3. LLM 不是金融識別碼的 source of truth；ticker 是靜態事實，應由人工維護

**正確解法：Plan A（立即）+ Plan B（系統性）**

**Plan A — 一次性 Cypher patch（立即修復現有 20 個節點）**

```python
# scripts/add_tickers.py
from neo4j import GraphDatabase
import json

TICKER_MAP = {
    "co:coherent": "COHR",
    "co:lumentum": "LITE",
    "co:broadcom": "AVGO",
    "co:nvidia": "NVDA",
    "co:tsmc": "TSM",
    "co:intel": "INTC",
    "co:samsung": "005930.KS",
    "co:apple": "AAPL",
    "co:corning": "GLW",
    "co:arista": "ANET",
    "co:meta": "META",
    "co:google": "GOOGL",
    # 私人公司 — 明確設為 null（表示已知無 ticker，不是「未查」）
    "co:anthropic": None,
    "co:openai": None,
}

PATCH_QUERY = """
MATCH (c:Entity {id: $node_id})
SET c.attributes = apoc.map.merge(
    coalesce(c.attributes, {}),
    {ticker: $ticker}
)
"""

def patch_tickers(driver):
    with driver.session() as session:
        for node_id, ticker in TICKER_MAP.items():
            session.run(PATCH_QUERY, node_id=node_id, ticker=ticker)
            print(f"Patched {node_id} → {ticker}")
```

**Plan B — loader 層 TICKER_MAP（系統性修復，防止未來載入重破）**

```python
# loader/load_to_neo4j.py — 在 Company 節點載入段加入

# 這是唯一的 source of truth；Plan A 的 scripts/add_tickers.py 從這裡同步
TICKER_MAP = {
    "co:coherent": "COHR",
    "co:lumentum": "LITE",
    "co:broadcom": "AVGO",
    "co:nvidia": "NVDA",
    "co:tsmc": "TSM",
    "co:intel": "INTC",
    "co:samsung": "005930.KS",
    "co:apple": "AAPL",
    "co:corning": "GLW",
    "co:arista": "ANET",
    "co:meta": "META",
    "co:google": "GOOGL",
    "co:anthropic": None,   # 私人公司，明確 null
    "co:openai": None,      # 私人公司，明確 null
}

def load_company_node(tx, node: dict):
    node_id = node["id"]
    attrs = dict(node.get("attributes", {}))

    if node_id in TICKER_MAP:
        # 已知公司：設 ticker（可能是 None，代表私人公司）
        attrs["ticker"] = TICKER_MAP[node_id]
    # 若 node_id 不在 TICKER_MAP：不設 ticker，表示「尚未查」
    # 這樣 Engine C 可以區分「確認無 ticker」vs「尚未建檔」

    # ... 後續 MERGE 邏輯不變
```

**為何兩個 plan 都必要**

- 沒有 Plan A：現有 20 個節點繼續沒有 ticker，直到重新抽取（代價高）
- 沒有 Plan B：每份新文件產生的 Company 節點都沒有 ticker，Engine C 對任何新公司都會再次斷 join
- 兩者合用：立即修好存量，系統性保護增量

---

## Why This Matters

**Claim 扇出（模式 1）**：thesis generator 的 claim context 品質直接決定 thesis 深度。如果 20 個配額裡只有 3-4 個不重複的 claim，生成的 thesis 論點單薄，risk 分析缺乏多角度支撐。這是 Milestone B 驗收品質的直接影響因素。

**重複節點（模式 2）**：`confidence` 分散在兩個節點，任何瓶頸評分邏輯都會低估真實信心。跨文件的供應商關係也無法正確 MERGE，導致 `sole_source` 評估失準。

**孤立節點（模式 3）**：未連接的 Company 節點（如 `co:jabil`）不會出現在任何供應鏈 Cypher 查詢中，等於憑空消失。如果 jabil 是一個重要的製造夥伴，thesis 對供應鏈結構的描述就不完整。

**Ticker 缺失（模式 5）**：Engine C 啟動後，若 join key 不存在，財務查詢（毛利率、backlog）無法自動對齊圖節點，Watchlist 升格的 5 項財務核驗清單就無法一鍵完成——這是 CLAUDE.md L9 明確列為 Engine C 的前置條件。

---

## When to Apply

**每次多文件載入後**（品質核查 checklist）：

1. 執行孤立節點查詢（模式 3）：結果不為零則需要審查
2. 確認 `graph_context.py` 已使用 DISTINCT Claim 查詢（模式 1）
3. 新增公司節點時檢查是否已在 `TICKER_MAP` 中，沒有則補上（模式 5）

**Engine C 設計啟動前**（一次性前置工作）：

1. 跑 `scripts/add_tickers.py` patch 現有節點（模式 5 Plan A）
2. 確認 `loader/load_to_neo4j.py` 已合入 `TICKER_MAP` 邏輯（模式 5 Plan B）
3. 驗證：`MATCH (c:Entity {type: 'Company'}) RETURN c.id, c.attributes.ticker` — 所有已知公司應有 ticker 或明確 null

**新增來源文件的抽取 prompt review**：

- 如果文件是新的「主題領域」（非 CPO/矽光子）或來自新類型公司，預先更新 `TICKER_MAP` 和 `schema/vocab.json` 的 `aliases`

---

## Examples

### 確認 Claim 扇出修復效果

修復 `graph_context.py` 後，執行以下查詢驗證 claim 多樣性：

```cypher
-- 確認不重複的 claim 數量 vs 總 ABOUT 邊數
MATCH (c:Claim)
RETURN count(DISTINCT c) AS distinct_claims

MATCH ()-[:ABOUT]->()
RETURN count(*) AS total_about_edges
```

修復前：`distinct_claims = 34`，但 `graph_context.py` LIMIT 20 只看到 3-4 個；修復後：LIMIT 20 應覆蓋至少 15-18 個不重複的 claim。

### 驗證 Ticker Patch 結果

```cypher
-- 查所有 Company 節點的 ticker 狀態
MATCH (c:Entity)
WHERE c.type = 'Company'
RETURN c.id, c.attributes.ticker AS ticker,
       CASE
         WHEN c.attributes.ticker IS NULL AND c.id IN ['co:anthropic','co:openai']
           THEN 'known_private'
         WHEN c.attributes.ticker IS NULL
           THEN 'not_mapped'
         ELSE 'ok'
       END AS status
ORDER BY status, c.id
```

目標狀態：所有已知上市公司為 `ok`，私人公司為 `known_private`，無 `not_mapped`（除新載入但尚未建檔的公司外）。

### 跨季邊狀態確認（判讀範例）

```cypher
-- 看同一 src-dst pair 的所有邊及其來源季度
MATCH (a:Entity {id: 'co:lumentum'})-[r:SUPPLIES_TO]->(b:Entity {id: 'tech:uhp_laser'})
RETURN r.id, r.attributes.qualification_status, r.source_ids, r.updated_at
ORDER BY r.updated_at
```

預期結果：兩條邊，`qualification_status` 分別為 `designed_in`（Q2）和 `qualifying`（Q3）。這是正確的時間序列保留，不需要去重。

## Related

- `docs/graph-review-v1.md` — 本次審查的原始報告（raw review，含完整 Cypher 輸出）
- `docs/plans/2026-06-26-002-feat-cpo-vertical-slice-thesis-plan.md` — Milestone B 計畫，此文件源自其完成後的審查
- CLAUDE.md L9 — Engine C 設計前置條件（ticker join key 是其中之一）
- CLAUDE.md L6 — 第一次真實抽取撞出的 schema/pipeline gap（source ID 命名空間等）
