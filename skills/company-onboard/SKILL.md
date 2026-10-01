---
name: company-onboard
description: >
  把一家新公司加入知識圖譜（Engine A）。
  當使用者說「onboard XXX」、「把 XXX 加入圖」、「我想研究 XXX 但圖裡還沒有」、
  「幫我找 XXX 的文件」、「XXX 還沒入圖」時，使用本 skill。
  觸發詞：onboard、加入圖、入圖、找文件、onboarding。
---

# Company Onboard Skill

## 定位一句話

**先答它坐哪一層 → 找文件 → 用戶看來源組成（L8）→ extract → validate → prepare → pq2 `ra_admission` → 核准後經 apply 入口入圖 → 驗收。**

研究 agent（Claude Code / Codex）是搜尋與格式化引擎；用戶是獨立性的最終判官（L8 不能自動化），
入圖是四個人工 gate 之一——**本 skill 沒有任何一步直接寫 Neo4j**。

---

## 流程總覽（5 步）

```
Step 1 — 它坐哪一層（必答）＋名冊登記
Step 2 — 找文件（選源順序住 source-trace，不在這裡另列）
Step 3 — 用戶確認來源組成（自報／客戶端／第三方各幾份；L8）
Step 4 — extract → validate → prepare（凍結成 Research Action）
Step 5 — pq2 ra_admission → 使用者核准 → apply 入口 → 驗收
```

---

## Step 1 — 它坐哪一層（必答）＋名冊

**必答：這家公司坐在圖上的哪一層？** 寫出節點 id（例：`mat:inp_substrate`、`tech:cw_dfb_laser`）。
不知道就寫「未知」，並**先**走 `skills/system-decompose`（由上而下拆一個真實系統）或走圖
（`python -m query.graph_walk`）找它該掛的層——沒有層的公司入圖後只會變成走圖第 6 型「供貨走不到錨」，
不是研究進展。

**名冊：** `co:*` 的唯一權威是 `config/company_identity.json`（研究 ticker、`display_name`、`name_aliases`；
私人公司 ticker 明確為 null，不猜）。新公司先在那裡登記，`display_name` 只填 mechanical 來源
（年報封面／交易所公告名／EDGAR 註冊名），並寫 `_display_name_source`。圖上的 ticker 由名冊派生，
不要改任何 loader 程式碼。

---

## Step 2 — 找文件

選源順序照 `skills/source-trace` 的「2b. 輸入是層／節點時」（客戶 filing 的供應商段 → 產業報告 → 規格書／teardown →
供應商自己的文件）；各市場的一手怎麼抓、哪幾條路徑還沒試，看同一份 skill 與 `config/source_routes.json`
（例：`python -m fetchers.edgar --ticker <T> --forms 10-K,10-Q,8-K`、`python -m fetchers.mops --co-id <代號> --kind annual_report`）。
本 skill 不另列一份清單——清單抄兩份就會開始偏離（L16）。

---

## Step 3 — 用戶確認來源組成（L8 獨立性審查）

找到文件後，**必須呈現給用戶審查**，不自動入庫。格式：

```
發現以下 <N> 份文件：

1. [文件名] origin_entity=<誰發出> evidence_tier=<tier> source_type=<型別> — <一句描述>
2. ...

來源組成：
- 供應商自報（origin＝它自己）：<份數>——<列出>
- 客戶端（客戶的 filing／法說／新聞稿）：<份數>——<列出>
- 第三方（登記在 config/publishers.json 的自產資料發布者、或名冊裡的其他公司）：<份數>——<列出>
- 媒體轉述（同一事件的報導）：<份數>——不算印證，要追它轉述的一手

這一包對 Step 1 那一層列舉了哪幾家：<node> ← <supplier, ...>（origin_role＝customer_filing／industry_report／spec_or_teardown／supplier_self）

確認入庫？(Y/n) 或 說明哪份文件不應入庫
```

**不設份數門檻**：份數是讀了多少文件，不是證據強度（AGENTS「這個指標會隨我們多讀一份文件而單調上升嗎？」）。
要說的是**缺哪一類**（例：只有自報、沒有客戶端）。

**L8 判準提醒（每次都要說）：**
- 供應商自己的法說會／年報／規格書 = 自報（`origin_entity` = 供應商本身）
- 客戶法說會或 filing 提到此供應商 = 獨立佐證
- 產業研究、拆解、標準組織、政府、學術（`config/publishers.json` 登記的自產資料類別）= 獨立佐證；媒體不是
- `sole_source` 主張需客戶端或第三方確認；供應商自稱是弱主張

---

## Step 4 — Extract → Validate → Prepare

用戶確認後，逐一處理每份文件：

### 4a. 確認 raw 文件在 library/raw/

若文件是 txt/pdf 摘要，放 `library/raw/<doc_name>.txt`；fetcher 已輸出到 `library/raw/` 的直接用。

### 4b. Extract（對話式，主路線）

研究 agent 讀 `prompts/extract_system.md` 的完整規則，產生中介 JSON 寫入 `extractions/<doc_id>.json`，
並立刻自我檢查：具體型號／公司名是否逐字出現在 quote（L6）。`origin_entity` 寫**真正發出這份文件的人**
（研究機構名、論文作者所屬機構、客戶公司名）——**不要寫泛稱**（例：`Third-party Research`）：泛稱無法登記成發布者，
那些邊會一直停在「待判定」（2026-10-01 Phase 4 Step 4.3 實測：一篇論文的 31 條邊就是這樣）。

兩段式 CLI（同一套規則，產生提示與收回 session 產出）：

```bash
python extract.py --input library/raw/<doc_name>.txt --source-type <type> --evidence-tier <1-4> --scaffold <提示輸出路徑>
python extract.py --input library/raw/<doc_name>.txt --source-type <type> --evidence-tier <1-4> --response <session 產出的 JSON> --out extractions/<doc_id>.json
```

`--source-type` 的字彙只住 `schema/vocab.json`（含 `datasheet`、`teardown`）。

### 4c. Validate

```bash
python loader/validate.py extractions/<doc_id>.json
```

- 有 hard error → 修 JSON 後重跑
- 有 WARN: origin_entity 未填 → 手動補填
- 全 OK → 繼續

### 4d. Prepare（凍結成 Research Action，不寫圖）

把 request 寫到 `library/leads/action_drafts/<slug>.json`（六個 report 欄位、documents、`focus_company_id`＝這家公司、
`layer_enumerations`＝Step 3 那一行；格式見 `prompts/intake_protocol.md` §4.1），然後：

```bash
python scripts/prepare_research_action.py --action-file library/leads/action_drafts/<slug>.json
```

prepare 會核對 `layer_enumerations`（每一家都在本包、引文逐字具名它）並對帶 `substitutability` 的邊印
「sub 引文核對」——都在 packet 裡。成功回 action ID、完整 digest 與 packet。

---

## Step 5 — pq2 → 核准 → apply 入口 → 驗收

```bash
python -m engine_b.todo sync          # ready 的 Research Action 進 pq2，取得 ra_admission 編號
```

把**原樣 packet** 給使用者看，然後停下來等核准（pq2 `go`）。核准後才跑固定入口：

```bash
python scripts/apply_ra_admission.py --pq2 <編號> --digest <action_digest>
```

入口過四道 fail closed 後先蓋核准戳記再 apply；它不 publish、不結案——之後照 `prompts/intake_protocol.md` §6
publish，再 `python -m engine_b.todo complete-ra <編號> --digest <action_digest>` 結案。

**驗收（入圖之後）：**

```bash
python -m query.structure <Step 1 的節點> --quotes      # 這一層的供給側多了這家、每條邊的逐字與證據等級
python -m query.graph_walk                               # 走圖：這家沒有落進「供貨走不到錨」；層的問句有沒有變
```

- [ ] 這家出現在 Step 1 那一層的供給側，且每條邊的逐字確實具名它
- [ ] 證據等級照實（自報／外部印證／媒體轉述…），不是為了好看去挑來源
- [ ] 沒有孤立節點、沒有落進「供貨走不到錨」

---

## 常見問題

### 法說會逐字稿不在 EDGAR

見 `skills/source-trace` 的「法說會 quote 專用路由」：先查 filing 多半落空，直接去 transcript；第三方轉錄 tier 最高 2。

### 文件是 PDF

用研究 agent 直接讀 PDF（Read tool），摘錄關鍵段落放 `library/raw/<doc>.txt`，再走 extract 流程。

### origin_entity 不確定怎麼填

`origin_entity` = **誰發出這份文件**（不是被分析的公司）。

| 文件類型 | origin_entity 範例 |
|---------|------------------|
| Coherent 法說會 | `Coherent` |
| Lumentum 提到 Coherent 的法說會 | `Lumentum` |
| 產業研究報告 | 研究機構名（例：`TrendForce`、`Cignal AI`） |
| 學術論文 | 作者所屬機構或論文團隊（不要寫 `Third-party Research`） |
| 媒體報導 | 媒體名；轉述別人新聞稿的就照實，並在 `origin_linkage` 宣告 `same_origin` |
| 客戶公司年報提到供應商 | `<客戶公司名>` |

---

## 與其他 skill 的分工

| 情況 | 用哪個 skill |
|------|-------------|
| 新公司入圖、找文件、跑 pipeline | 本 skill |
| 不知道它坐哪一層 | `skills/system-decompose` |
| 公司已在圖、問投資問題 | `skills/investment-research` |
| 丟進來一條推文/新聞要入庫 | `skills/lead-intake` |
| 找既有 thesis 的反駁角度 | `skills/blind-spot-audit` |
