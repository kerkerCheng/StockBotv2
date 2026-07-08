# 新公司 Onboarding SOP（5 步流程）

> 當 `graph_context.py --company-id co:<ticker>` 回傳「公司不在圖中」時，依照以下步驟執行。

---

## 前置確認

1. 確認公司是上市公司且有 SEC EDGAR 資料（美股）
2. 確認 `.env` 有 `EDGAR_CONTACT_EMAIL`（EDGAR fair-access 要求）
3. 確認 Neo4j 已啟動：`docker compose up neo4j -d`

---

## Step 1 — EDGAR 取文件

```powershell
python fetchers/edgar.py --ticker <TICKER> --forms 10-K,10-Q --n 2
```

成功後 `library/raw/` 會有：
- `<ticker>_10_k_<date>.txt`
- `<ticker>_10_k_<date>.meta.json`
- `<ticker>_10_q_<date>.txt`（等）

**台股 / 非美股：** yfinance 覆蓋有限，需人工從 IR 官網或 MOPS 下載，手動放入 `library/raw/` 並建立對應 `meta.json`（格式參考 `library/raw/*.meta.json`）。

---

## Step 2 — Extract

```powershell
python extract.py `
    --input "library/raw/<doc_id>.txt" `
    --source-type filing `
    --evidence-tier 1 `
    --title "<公司名稱> <Form> <季度>" `
    --out "extractions/<doc_id>.json"
```

長文件（> 50 頁）建議先只抽 Business / MD&A / Risk Factors 段落，
貼到 `library/raw/<doc_id>_excerpt.txt` 再跑 extract，避免超出 context 上限。

---

## Step 3 — Validate

```powershell
python loader/validate.py extractions/<doc_id>.json
```

有 FAIL 先修（通常是 vocab gap 或 schema 違規），再繼續。

---

## Step 4 — Load

```powershell
python loader/load_to_neo4j.py extractions/<doc_id>.json --apoc
```

Load 後確認 MERGE 成功：

```cypher
MATCH (n:Entity {id: 'co:<ticker_lower>'}) RETURN n.id, n.name, n.attributes
```

---

## Step 5 — 更新 TICKER_MAP

在 `loader/load_to_neo4j.py` 的 `TICKER_MAP` 補上新公司的 graph node id 與 ticker：

```python
"co:<ticker_lower>": "<TICKER>",   # 例："co:sive": "SIVE"
```

這樣 Engine C 的 ETL 會自動抓取財務數據，且 `scripts/add_tickers.py` 可 patch 現有節點。

---

## Step 6 — 驗證查詢

```powershell
python query/graph_context.py --company-id co:<ticker_lower>
```

不再出現「公司不在圖中」即完成 onboarding。

---

## 孤立節點核查（每次 Load 後）

```cypher
MATCH (n:Entity)
WHERE NOT (n)-[]-() AND NOT n:Claim
RETURN n.id, n.type, labels(n)
ORDER BY n.type
```

Company 和 Material 孤立節點需優先處理（無邊 = 不出現在供應鏈查詢中）。

---

## 來源獨立性檢查（多文件選源前）

- 至少 3 個不同 `origin_entity`（不同公司的文件）
- 被分析公司自己的法說會只算佐證，不算主要確認來源（CLAUDE.md L8）
- `sole_source` 判定需要客戶端或第三方來源（非供應商自稱）

---

## 相關文件

- [`docs/solutions/tooling-decisions/engine-c-sqlite-dual-backend.md`](solutions/tooling-decisions/engine-c-sqlite-dual-backend.md) — 非美股 yfinance suffix 規則、EDGAR 適用範圍限制、pdfplumber 頁面抽取模式、TICKER_MAP `None` 的意義
