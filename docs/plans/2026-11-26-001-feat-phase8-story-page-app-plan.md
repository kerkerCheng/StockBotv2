---
date: 2026-11-26
topic: phase8-story-page-app
status: active
derived_from: docs/ROADMAP.md（Phase 8）、docs/brainstorms/2026-11-25-story-question-list-goal.md（§8 S4 修正案、§9 收斂）
---

# Phase 8：個股故事頁進 APP、偵探與故事頁分工（給執行模型的完整 plan）

> **執行者：便宜模型（opus），走 `skills/development-flow/SKILL.md`（Z1 以上預設 R1）。** 進度表「執行者」欄寫強模型的 Step 做到就停下交回。
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md) Phase 8 那一列與
> [決定紀錄](../brainstorms/2026-11-25-story-question-list-goal.md) §8、§9 導出；衝突時以那兩份為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文 → 決定紀錄 §8、§9 → [`skills/stock-story/SKILL.md`](../../skills/stock-story/SKILL.md)
> 與 [`skills/detective/SKILL.md`](../../skills/detective/SKILL.md)（故事頁長什麼樣、誰寫、什麼時候寫）→ `webapp/contracts.py` 檔頭
> （materialize 與 serve 是兩條責任鏈）→ 本 plan。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄。** 本 Phase 的驗收數字是機制存在與否（測試、注入被拒的筆數、畫面上印不印得出來）
> 與等待 registry、敘事裡的東西；沒有一條是「幾檔通過某個 filter」（G10）。

---

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者 2026-11-26 核准的 PLAN_PROPOSAL**：他簽了 S4 修正案，指示「先開發完一版再來滾動修正」「取代App就有一起排進去」
「你確立方向或plan後 我會給opus執行」，並答完收斂的五題（「1 可以；2 全部換；3 各 1 美元；4 不加；5 開」，決定紀錄 §9.1）。
Z2／Z3 的 Step 不再停等核准；`AGENTS.md`「常規推進授權」照用——Verdict 為 `GO` 且沒有待使用者決定的問題就直接做下一個 Step。

**執行期間六條 trigger 命中的 R2：常規 opt-in（使用者 2026-11-26「5 開」）。** 命中時直接發 `WORK_REQUEST`，不停下來問；
spawn 前先讀週額度（`python -m crons.llm_quota`）。本 plan 已知會命中的是 Step 8.2（把研究 session 寫的 HTML 印進 APP＝安全面，
同時換掉個股頁的框架＝邊界搬遷）與結案。reviewer 唯讀，NO_GO 回 `AWAITING_HUMAN`、不自動修。

**怎麼開工：** 本 plan 不在 README 的「Phase ↔ plan」那張表（Phase 7 是持續型，佔著那張表唯一的 active；session 開頭的提示照舊講研究）。
使用者貼 **`/phase-run docs/plans/2026-11-26-001-feat-phase8-story-page-app-plan.md`**，執行者從下表第一個未 ✅、而且執行者欄是自己的 Step 接續。

**每個 Step 一個 commit，訊息第一行寫 Step 編號；GO 就 push**（push 前 `git ls-files library/private` 應為空）。
進度表由執行者在每個 Step 的 commit 裡更新；commit 短碼由下一個 Step 的 commit 補填。

**同一 working tree 只讓一個 writer：** 開工先 `python scripts/writer_guard.py check`，再 `acquire --minutes <N> --purpose "Phase 8 Step <編號>"`，
收工 `release`。台北 06:30 的 daily 是另一個 writer，跨到那個時段先放鎖。強模型做 8.5 與研究時同理，兩邊不同時寫。

| Step | 內容 | 執行者 | Zoom／Review | 狀態 | commit |
|---|---|---|---|---|---|
| 8.0 | 文件：本 plan、兩份 skill 照定案的分工改寫、`AGENTS.md` 四處、ROADMAP 與 CONCEPTS 整理 | 強模型 | Z2／R1 | ✅ 2026-11-26 | `6a70068` |
| 8.1 | 故事頁的帳、片段與宣告的檢查、`python -m alpha story-page` 命令、合成範例頁 | 便宜模型 | Z2／R1 | ✅ 2026-11-26 | `5c2c9f2`＋`02ad42b` |
| 8.2 | 物化把現行故事頁放進個股物化檔；APP 個股頁換新框架（故事 → 系統裡的它；沒做深的印短故事）；樣式表 | 便宜模型 | Z3／**R2** | ✅ 2026-11-26（R2 GO） | `523952c`＋`a868f9e` |
| 8.3 | 故事和系統對不上的三種：`story-page gaps`、待做清單新一格、心跳照印 | 便宜模型 | Z2／R1 | ✅ 2026-11-26 | `c8a6580` |
| 8.4a | 「做深這一檔」按鈕；冷讀包（頁面文字＋提示，提示唯一一份在程式裡） | 便宜模型 | Z1／R1 | ✅ 2026-11-26 | （本 commit） |
| 8.4b | 畫圖工具（地圖、時間長條、對數股價圖），輸出過得了片段檢查 | 便宜模型 | Z1／R1 | ○ | |
| 8.4c | 兩份 skill、OPERATIONS、ARCHITECTURE 接上真的命令（§3 Step 8.4c 列了要改的句子） | 便宜模型 | Z0／R0 | ○ | |
| 8.5 | 三頁搬進 APP：讀回、轉成片段與宣告、對照已發布的頁、各跑一次冷讀；Sivers 頁刪到字數上限內 | **強模型** | 研究＋Z1 | ○（要能讀回私有頁面，或使用者下載 HTML） | |
| 8.6 | 結案：completion gate、R2、README 與 ROADMAP 登記、closeout 報告 | 做完 8.5 的那一位 | **R2** | ○ | |

8.1–8.4c 不依賴 8.5：用合成範例頁開發與驗收。便宜模型做完 8.4c 就停（`AWAITING_HUMAN`：「切強模型做 8.5」）。

---

## 0. 不可越線（違反即 NO_GO）

1. **故事頁的帳不是 authority。** 它不決定候選狀態、不擋任何寫入、不入圖、不鑄 pq2、不寫 Engine C、不動 thesis。四個人工 gate 不動。
2. **request path 照舊**：不跑 LLM、不寫檔、不抓外部資料、cache miss 不重建；APP 沒有寫入端點。
   查證：`python -m pytest tests/test_webapp_request_path.py`。
3. **不放寬 CSP**（`webapp/api.py` 的 `_SECURITY_HEADERS`）。它現在擋行內樣式與行內程式，這正是要的。
4. **前端不用 `innerHTML`、`insertAdjacentHTML`、`document.write`。** 片段用 `DOMParser` 解析後照白名單重建節點。
5. **白名單只有一份**（Python 的常數），前端從 `.meta.json` 拿（`write_vocabularies`）；`app.js` 不另抄一份（L16：分類有 SSOT 就讓它跟著資料走）。
6. **不給目標價、估值模型、跨檔排序。** 對帳計數只數、不排序、不設門檻；故事頁在首頁不產生任何新的排序。
7. **敘事紀錄、短故事帳（`stories.jsonl`）、候選板、等待 registry 的格式都不動**；`ARTIFACT_SCHEMA_VERSION` 與 brief contract 不升版
   （個股物化檔多的是加法欄）。
8. **真實三頁的內容、私有網頁的網址、券商原文不進 repo。** 測試與範例一律用合成的公司；測試不讀真的 `library/private`。
9. **不改 `AGENTS.md` 的判準句**（8.0 已照使用者核准改完）。覺得要改就停，給五欄 amendment。
10. **冷讀子代理唯讀、不對外、只讀那一頁的文字**；派工提示第一行寫「對外請求不帶 email、不帶個人資訊；本任務不需要對外」。
11. **舊版個股頁的函式不刪**（過渡期還有一條路會叫到它們）；刪除是結案之後使用者決定的事。

---

## 1. 現在的邊界（2026-11-26 實讀）

- **個股頁**：`webapp/static/app.js` 的 `renderDetail` → 頁首（`whatLine`、`headerLine`、`askClaudeButton`）＋ `briefCard`
  （十三塊，`schemaFirstScreen` 照 `.meta.json` 的 `page_schema.first_screen` 排）。資料是 `library/private/app/analyst_view/<代號>.json`
  （`webapp/materialize.py` 的 `materialize` → `materialize_view`；`webapp/api.py` 的 `stock_detail` 照抄）。
- **短故事**：`alpha/providers/stories.py`（`library/private/alpha/stories.jsonl`，一版敘事一份、每格一句）＋規則 `alpha/narrative/story.py`；
  敘事換版就過期，待做清單「故事還沒寫」（`engine_b/todo_ledger.py` 的 `todo.story`）。**留著**：它是沒做深的檔的頁首。
- **長的故事頁**：現在是私有網頁（三檔：Aehr、Sivers、亞泰），不在 repo、不在 APP；原始檔與組頁腳本已隨 session 暫存夾消失（決定紀錄 §9.4）。
- **安全標頭**：`default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:`——行內 `<style>`、`style=` 屬性、行內程式在瀏覽器都不會生效。
- **複製提示**：`askClaudePrompt`／`askClaudeButton`（`tests/test_webapp_ask_claude.py` 守三件事：不抓、只讀、複製不了就說）。
- **前端沒有建置步驟**：`tests/test_webapp_static_js.py` 只擋括號不平衡與死函式。

## 2. 提議的邊界（契約）

### 2.1 故事頁片段

一個 UTF-8 的 `page.html`，根元素 `<article class="story-page">`，沒有 `<html>`、`<head>`、`<body>`。**節序固定，`id` 是契約：**

| 順序 | 元素 | 內容 |
|---|---|---|
| 1 | `<header id="hero">` | 一個 `<h1>`（標題一句）＋三到四個 `<p>`。頁首只有故事 |
| 2 | `<section id="q1">` … `<section id="q12">` | 十二題，每節一個 `<h2>`（結論句）。答案是「沒有」也留一節 |
| 3 | `<section id="bet-kind">` | 回頭看，這是哪一種賭 |
| 4 | `<section id="system" data-slot="system"></section>` | **必須是空的**——「系統裡的它」由 APP 填，不手抄 |
| 5 | `<section id="system-gap">`（選填） | 這一頁和系統對不上的地方，白話寫（判斷由人寫；數由程式算） |
| 6 | `<section id="self-eval">` | 自評表與最要緊的幾個查不到 |
| 7 | `<details id="sources">` | 出處，一處 |

- **等待**：第 11、12 題裡每一條要等的事，那個元素帶 `data-wait="<key>"`，key 對到宣告的 `waits[].key`。
  頁上不手寫「已登記」「還沒登記」——徽章由 APP 照等待 registry 印。
- **來源等級**：`<span class="src" data-src="自述">`，封閉字彙五個：自述／買方／第三方／推一步／網路。
- **圖**：一律行內 `<svg>`（8.4b 的畫圖工具產生）；顏色用 `class` 或 `currentColor`，不用 `style=`。第一版不收 `<img>`。
- **白名單**（常數住 `alpha/narrative/story_page.py`，前端經 `.meta.json` 拿到同一份）：
  - HTML：`article header section h1 h2 h3 h4 p ul ol li table thead tbody tr th td caption figure figcaption details summary blockquote strong em b i sup sub br hr span div a small code`
  - SVG：`svg g path line polyline polygon rect circle ellipse text tspan title desc defs marker`
  - 屬性：`id class title lang`；`a[href]` 只准 `https://…`、`#…`；`th／td` 的 `colspan rowspan scope`；`details[open]`；
    `data-slot data-wait data-src data-label`；SVG 的幾何與呈現屬性（`viewBox width height x y x1 y1 x2 y2 cx cy r rx ry d points transform
    fill stroke stroke-width stroke-dasharray stroke-linecap stroke-linejoin opacity fill-opacity text-anchor dominant-baseline font-size
    font-weight marker-start marker-end preserveAspectRatio role aria-label aria-hidden xmlns`）；`marker-*` 與 `fill`／`stroke` 的 `url(…)` 只准頁內 `#id`
  - **一律拒收**：其餘標籤（`script style link meta base iframe object embed form input button img video audio foreignObject use` …）、
    任何 `on*` 屬性、`style` 屬性、`javascript:`／`data:`／`http://` 網址

### 2.2 宣告（`page.json`，和 `page.html` 放同一個工作資料夾）

```json
{
  "ticker": "ZZZZ",
  "brief_id": "ib_…",
  "checklist_version": "v3",
  "written_on": "2026-11-26",
  "evidence_pack": "library/private/research_notes/detective/ZZZZ_2026-11-26",
  "quote_sources": ["library/raw/zzzz_*"],
  "prices_seen": ["ZZZZ"],
  "price_as_of": "2026-11-25",
  "self_eval": {"1": "full", "2": "half", "12": "none"},
  "key_question": 5,
  "rides": ["tech:some_layer"],
  "graph_gaps": [{"text": "故事的夢在某一層，圖上沒有", "lead_ids": ["lead_…"]}],
  "waits": [{"key": "w1", "kind": "disproof", "watch_id": "ew_1234"}, {"key": "w2", "kind": "confirm", "watch_id": null}],
  "cold_read": {"report": "coldread/REPORT.md", "restated_ok": true, "asked": 4, "asked_outside": 1}
}
```

- `brief_id`＝寫的當下這一檔的現行敘事（寫入時核對）。`self_eval` 十二題都要有，值是 `full`／`half`／`none`。
- `key_question`＝決定賭注的那一題（岔路型 5、訂單型 6）。`evidence_pack`、`quote_sources`、`rides`、`graph_gaps` 可以是空的。
- `waits[].kind` ∈ `disproof`／`confirm`／`date`；`watch_id` 是 null＝頁上寫了、系統還沒登記。
- `cold_read` 二選一：上面那種，或 `{"skipped": "理由"}`。沒有這一格拒收。

### 2.3 帳與檔案（私有、只能追加）

- 片段原文：`library/private/story_pages/<代號>/<page_id>.html`，寫入後不改。
- 帳：`library/private/alpha/story_pages.jsonl`，一列一版：`page_id`（`sp_`＋`company_id`、`brief_id`、片段 sha256 三者的 sha256 前 16 碼）、
  `company_id`、`ticker`、`brief_id`、`created_at`、`author`、`kind`（`page`｜`rebind`）、`html_sha256`、`html_path`、`visible_chars`、
  `warnings`（檢查的 WARN 摘要）、宣告全文、`rebind_note`（只有 `rebind`）。
- **現行頁＝這家公司的最後一列。** `rebind`＝同一份片段、新的 `brief_id`，必附一句：新舊敘事差在哪、這一頁為什麼還站得住。
- 讀不懂的列報出來，不靜默跳過（INV-3；照 `stories.read_records` 回 `(records, problems)` 的形狀）。

### 2.4 檢查（`check`；ERROR 拒收，WARN 照印、記進帳的那一列）

**ERROR**

- E1 白名單外的標籤、屬性、網址。
- E2 必要的節缺了或順序不對；`h1` 不是剛好一個；`hero` 的 `<p>` 不在三到四個。
- E3 `#system` 裡有內容。
- E4 頁上出現私有網頁網址（`claude.ai/artifact`）、本機路徑（`library/private`、磁碟機代號）。
- E5 宣告缺欄或值不合法；`brief_id` 不是這一檔的現行敘事；`waits[].watch_id` 在等待 registry 找不到；
  頁上的 `data-wait` 集合和宣告的 `waits[].key` 集合不相等；`rides` 的節點在圖上找不到。
  圖連不上時最後這一項印「沒核（圖連不上）」並算進 WARN——不當成通過，也不擋寫入。
- E6 `cold_read` 缺。

**WARN**（每條印出命中的句子或數，最多十筆）

- W1 看得到的字數（不含 `<details>` 裡的）：印數字；超過 15,000 或不到 8,000 標出來。
- W2 `hero` 裡指向後面或別處的寫法（「見第…」「見下」「如下表」「第 N 題／節」）。
- W3 同一個帶單位的數字在看得到的字裡出現四次以上。
- W4 一句裡有兩個以上名冊上的公司名、又有「它」。公司名用 `config/company_identity.json` 的顯示名與別名。
- W5 系統的詞直接上頁（`#system-gap` 以外）：會死嗎、起始門、缺 X、neither、judgment、`co:`、`tech:`、`ew_`、`ib_`、`lead_`。字表住同一個模組。
- W6 引號裡的長字串（「…」13 字以上、"…" 6 個詞以上）在 `quote_sources` 的檔裡找不到；`quote_sources` 是空的就印「沒核引號」。
- W7 第 1 到 12 題某一節沒有任何來源等級標記。
- W8 `key_question` 那一題自評不是 `full`（skill 的規定：先補查再交）。
- W9 頁上手寫了「已登記」「還沒登記」（該由程式印）。

「看得到的字」只有一個函式，量字數、冷讀、W 類檢查共用。

### 2.5 命令（`python -m alpha story-page …`，加在 `alpha/cli.py`，旁邊是 `stories`）

| 子命令 | 做什麼 |
|---|---|
| `check <資料夾>` | 乾跑：片段與宣告的檢查，印 ERROR、WARN；有 ERROR exit 1。不寫檔 |
| `add <資料夾>` | 先 `check`；沒有 ERROR 才把片段複製進私有區、帳追加一列。印 `page_id` 與下一步 `python -m webapp materialize <代號>` |
| `rebind <代號> --note "…"` | 現行頁重綁到現行敘事（帳追加一列 `kind=rebind`） |
| `gaps` | 對帳三種（§2.6），逐檔列 |
| `text <資料夾｜代號>` | 印看得到的字 |
| `cold-pack <資料夾>` | 在資料夾裡寫 `coldread/PAGE.txt` 與 `coldread/PROMPT.md` |
| `list`／`show <代號>` | 現行頁一覽／一檔的版本史 |

### 2.6 對帳：故事和系統對不上的三種（封閉字彙，`STORY_PAGE_GAP_KINDS`）

| kind | 判法 | 怎麼清 |
|---|---|---|
| `stale` | 現行頁的 `brief_id` ≠ 這家公司的現行敘事 | 對過新舊兩版：頁上講的沒變就 `rebind`，變了就小修後 `add` |
| `unregistered_wait` | 現行頁的 `waits` 有 `watch_id` 是 null 的 | 敘事換版把它登記成反證或加碼條件，再 `add` 一版補上 id；不該等的就從頁上拿掉 |
| `ride_mismatch` | `rides` 有節點不在現行敘事押的單位裡；或 `graph_gaps` 有一項沒有 `lead_ids` | 敘事換版改押；圖上沒有的那一層登記成線索（入圖照人工 `go`） |

三種都是互動 session 自己清得掉的（圖上缺的那一層只要求登記成線索，不要求入圖——否則這一格會恆亮，L14④）。
`watch_id` 寫入後在 registry 找不到，印成讀取問題，不算進這三種。

### 2.7 個股頁新框架（`renderDetail`）

1. **頁首**：代號、公司名、做什麼一行、現價一行；兩顆按鈕「做深這一檔（複製提示）」「問 Claude（複製提示）」。
2. **有現行故事頁**：一行版本（寫於哪天、清單版本、看過誰的股價、股價圖畫到哪天）；`stale` 時一條橫幅「敘事在某天換版了，這一頁還沒對版」→
   故事片段。片段裡 `#system` 的空位換成「系統裡的它」；每個 `data-wait` 元素後面加徽章（已登記・哪天醒來重看／還沒登記）。
3. **沒有故事頁**：一行「還沒做深」→ 短故事（`story:` 各格；沒有短故事印敘事各格；沒有敘事印「還沒寫敘事」）→ 系統示意圖（有的話）→「系統裡的它」。
4. **頁尾**：一個小連結「舊版個股頁（過渡期）」，走原本的 `briefCard`。路由寫法由執行者定，記進 OPERATIONS。

**「系統裡的它」**（一個函式，固定順序，全部沿用現有元件、不新算任何數）：
①候選狀態一行與賭注句（`candidateLine`）②押在哪一層、路徑（`seatsSentence`、`pathSentences`）與示意圖（`diagramFigure`；有故事頁時示意圖放這裡）
③讀圖的判讀 ④會不會先死：四盞燈與數字日期（`lampsBlock`）⑤已定價嗎、出現在數字裡了嗎（`wordsBlock`），數字收一個展開（`numbersDrill`）
⑥已登記的等待：反證、加碼條件、對帳日 ⑦現在的股價（`priceFigure`）⑧對不上的（只在有故事頁時；物化時算好的 §2.6 三種，各印白話一句）。

**物化**（`webapp/materialize.py` 的 `materialize`）：讀這一檔的現行故事頁 → 片段再檢查一次（只跑 E1–E4）→ 個股物化檔多一格 `story_page`：
`{page_id, brief_id, current_brief_id, stale, written_on, checklist_version, prices_seen, price_as_of, visible_chars, html, waits[{key, kind, watch_id, status, wake_on, expires}], gaps[], self_eval}`。
沒有故事頁＝`story_page: null`。有但檢查不過或檔讀不到＝`story_page: {absence: {kind, reason}}`——**只有故事那一塊印「故事頁讀不到：原因」，
整份物化檔照寫**（個股頁其餘的不因此讀不到）。白名單與來源等級字彙由 `write_vocabularies` 寫進 `.meta.json`。

**前端**：`storyFragment(html, allowed)` 用 `DOMParser().parseFromString(html, 'text/html')` 解析，遞迴重建白名單內的節點
（HTML 用 `document.createElement`、SVG 用 `createElementNS`），白名單外的節點丟掉並在主控台記一筆；連結一律加 `rel="noopener noreferrer"`、`target="_blank"`
（頁內錨除外）。樣式住新檔 `webapp/static/story.css`（`index.html` 連上；用 `styles.css` 既有的變數，手機寬度先看）。

### 2.8 冷讀

- `cold-pack` 寫出 `PAGE.txt`（看得到的字）與 `PROMPT.md`。提示唯一一份在程式裡（照 `alpha/detective.py` 的 `PROMPT_TEMPLATE` 的做法），內容：
  讀者只拿到這一頁的文字，不給清單、不給對話；回六樣——五句話重述這家公司在賭什麼／第一次出現時沒解釋的詞／要回頭重讀的句子／
  讀完還想問的（最多五個）／覺得重複的／最容易被讀錯的三處；不查資料、不對外、不給投資建議、不寫任何檔。
- 派工、對照、記帳是 skill 的事（`skills/stock-story`）：乾淨 context 的唯讀便宜模型、每頁一位；主 session 拿重述對頁首、拿「還想問的」對問題清單。
  常規 opt-in 在 `AGENTS.md`「協作與邊界」。

---

## 3. Steps

每個 Step 的「第④問」＝L11-6：如果這個修法是錯的，最先壞掉的是哪一筆現有資料——落地時去看那一筆。

### Step 8.1 故事頁的帳、檢查、命令（Z2／R1）

- **改哪裡**：新 `alpha/narrative/story_page.py`（純規則：白名單、解析（標準庫 `html.parser`，不加相依）、節序、看得到的字、W 類檢查、
  宣告的形狀）；新 `alpha/providers/story_pages.py`（帳的讀寫、`page_id`、現行頁、`rebind`、對宣告做需要讀別的帳的核對：現行敘事、等待 registry、
  圖上節點——**用現有的讀取函式，不自己 parse 別人的 jsonl**）；`alpha/cli.py` 加 `story-page`；`.gitignore` 不必動（`library/private` 整個不進版控）。
  合成範例頁放 `tests/fixtures/story_page/`（公司用虛構的 `ZZZZ`，十二節齊、兩條等待、一張行內 SVG、一個表、一個摺疊）。
- **怎麼驗**：`tests/test_story_page.py`（規則）與 `tests/test_story_pages_provider.py`（帳；一律 `tmp_path`）。必含變異：
  - 注入四筆各自被 E1 拒：`<script>`、`<p onclick=…>`、`<p style=…>`、`<a href="javascript:…">`；外加 `<img>`、`<svg><use href="http://…">`、`data:` 網址。
  - 節序對調、少一節、`#system` 塞字、`data-wait` 和宣告對不起來、`brief_id` 不是現行、`cold_read` 缺——各自變紅。
  - 把檢查拿掉一條，對應的 fixture 要變綠（確認測試真的靠那一條）。
  - 範例頁原樣：0 ERROR；`text` 的字數穩定。
- **第④問**：這一步只加新檔，沒有現有資料會壞；最先壞的是 `python -m alpha --help`（子命令註冊錯會讓整個 CLI 起不來）——跑一次。
- **執行紀錄（2026-11-26，和上面契約不同或契約沒寫的）**：
  - SVG 屬性多收 `markerWidth markerHeight refX refY orient markerUnits dx dy stroke-opacity`（畫箭頭與字距要用；都是幾何與呈現，不帶網址）。
  - 註解、`<!DOCTYPE>`、CDATA 一律 E1（註解會把私有字串藏在看不到的地方）；非空元素自閉合（`<p/>`）算 E2（瀏覽器與 `html.parser` 讀法不同）。
  - 圖連不上記成 **W10**（契約說算進 WARN、沒給編號）。看得到的字含 `<summary>`（摺疊時看得到那一行），SVG 的 `title`／`desc` 不算。
  - 對版那一句最少 12 字。W4 的公司名用名冊的顯示名＋別名，不用 `fact_checks.company_names`（那份含代號，掃散文會被短代號誤報）。
  - `gaps`、`cold-pack` 照 Step 排在 8.3、8.4a。
  - **留給 8.2**：片段的 `id` 進 APP 會變成頁面上真的 id——前端重建節點時一律加前綴（`#…` 連結與 `url(#…)` 一起改），
    不在 Python 另抄一份 APP 的 id 清單（app.js 現在用 `app`、`selfcheck`、`page-question`、`footer-warning`、`code-banner`）。

### Step 8.2 物化與 APP 新框架（Z3／R2）

- **改哪裡**：`webapp/materialize.py`（`materialize` 讀現行故事頁、`materialize_view` 多一個 `story_page` 參數、`write_vocabularies` 多一段；
  多檔時現行故事頁與等待 registry 各載一次傳進來，照這支函式其他 context 的做法）；
  `webapp/static/app.js`（`renderDetail` 改成 §2.7；新 `storyFragment`、`systemBlock`、`storyPageHead`、`waitBadge`；`briefCard` 留給過渡期連結）；
  `webapp/static/story.css`、`index.html`；`webapp/api.py` 只在靜態檔白名單需要時動（`_static_file`）。`webapp/contracts.py` 的版本不升。
- **怎麼驗**：
  - `tests/test_webapp_materialize.py` 加：有故事頁時 `story_page.html` 等於帳裡的片段、`stale` 算對、`waits` 帶 registry 的狀態；
    沒有時是 null；片段被改壞（塞 `<script>`）時 `story_page.absence` 有理由、整份物化檔照寫。
  - `tests/test_webapp_request_path.py`、`tests/test_webapp_static_js.py`、`tests/test_webapp_ask_claude.py` 全綠（改主詞不刪判準）。
    新增一條：`app.js` 全檔沒有 `innerHTML`、`insertAdjacentHTML`、`document.write`。
  - **真的開一次**（headless Edge，手機寬 390；做法見記憶「APP 前端用 headless Edge 驗」與 OPERATIONS）：把範例頁 `add` 進一個暫存的私有目錄、
    物化、dump-dom——畫面上有 `article.story-page`、`#system` 裡有候選狀態與四盞燈、兩條等待後面各有徽章；再開一檔沒有故事頁的真實代號，
    對照舊版確認候選狀態、燈、等待日曆、股價都還印得出來。截圖存 `library/private/tmp/`，不進 repo。
  - 改完重啟 8790 的 serve，`/api/v1/health` 的 `code.stale` 是 false。
- **R2**：`WORK_REQUEST` 的 Claimed acceptance 寫「研究 session 寫的 HTML 經白名單兩次檢查與前端重建才上畫面；四種注入在寫入與物化都被拒；
  request path 四個證明照綠；沒有故事頁的個股頁沒有少印候選狀態、燈、等待、股價」。
- **第④問**：最先壞的是沒有故事頁的一百多檔——新框架少印了東西而沒有人發現。落地時挑三檔對照舊版：一檔已持有、一檔可開、一檔沒有敘事。
- **執行紀錄（2026-11-26）**：
  - 舊版個股頁的路由是 `#/old/<代號>`（小寫帶斜線，不撞 ticker）；新版頁尾一個小連結過去，舊版頁首一個連結回來。
  - 片段的 `id` 一律加前綴 `sp-`，頁內 `#…` 連結與 `url(#…)` 跟著改；頁內連結攔下來捲動（APP 用 hash 換頁，真的改網址會跳頁）。
  - 網址與 id 的四條規則原文也經 `.meta.json`（`story_page.patterns`）交給前端，app.js 用 `new RegExp` 照用；為了兩邊判得一樣，
    Python 那幾條不再用 `\w`（Python 認 Unicode 字母、JavaScript 只認 ASCII）。缺任何一條規則前端就不印片段，不放寬。
  - 等待狀態用這一輪 `_event_context` 已載入的那一份等待 registry（同一輪同一個快照，不另讀）。as-of 視角下有故事頁的檔印
    `point_in_time_unavailable`。片段讀不到或沒過第二次檢查＝`invalidated`；帳讀不到＝`upstream_unavailable`。
  - 對不上的三種（`page_gaps`）、等待徽章（`wait_states`、`WAIT_STATUS_LABELS`）、`current_brief` 先放進 `alpha/providers/story_pages.py`
    ——物化要用；8.3 的 `gaps_now`、待做清單與 `story-page gaps` 直接用同一個函式。
  - 落地時逐行對照舊版（COHR 已持有、1595.TWO 可開、000660.KS 沒有敘事），補回 §2.7 清單沒列、但舊版有、不該少的：
    和持有的檔押同一個需求（AGENTS「必須點明相關性」）、研究寫的這條鏈怎麼走與引文（使用者 11-26 擔心的「走圖的敘事」）、
    名詞解釋、參考尺與營收從哪來（客戶集中度、backlog；收在「數字與出處」）、事件與影響多大、時間表、敘事的狀態燈；
    短故事改成逐格（有短故事印短故事、沒有印敘事原文——「有一格寫了就整份只印短故事」會讓其餘格消失）。
    **只留在舊版的**：需求錨的四張圖、吃到多少、各格的依據（原文）、各塊標題、會不會死那一行摘要（四盞燈全句已在）——
    刪舊版程式之前要先決定它們的去處（8.6 待決）。
  - `tests/test_webapp_static_js.py` 的「頂層宣告兩次」擴到 `const`／`let`：這一步新宣告的 `const SVG_NS` 撞到畫圖那一段的
    同名常數（整支程式語法錯誤），舊守衛只看 `function` 抓不到，是 `node --check` 抓到的。
  - 驗收：暫存帳（`library/private/tmp/story_check/`，範例頁借 AEHR 的身分走真的寫入檢查）→ 物化四檔到暫存目錄 → 暫存 serve（8796）
    → headless Edge：故事頁、兩個徽章（已登記・在等／還沒登記）、「系統裡的它」、對不上兩條都印出；四頁 390 寬零溢出、零疊字；
    片段裡零個 `style`／`script`／`on*`（傾印裡唯一的 `style` 是示意圖框位，APP 自己用 JS 設的）。
  - **R2（乾淨 context、唯讀，2026-11-26）：GO**。四十多筆注入（實體編碼、空白與零寬字、`xlink:href`、svg 的 `a`／`animate`／`set`／`use`／
    `image`／`style`／`foreignObject`、`math`、`template`、CDATA、大寫標籤與屬性……）兩道服務端都擋；第三道用改過的物化檔＋暫存 serve＋
    headless Edge 驗：DOM 裡沒有任何注入節點、`on*`、壞網址；request path 四個證明綠；CSP 一字沒動；沒有故事頁的三檔候選狀態、四盞燈、
    反證與到期、股價都在。非阻擋一條**當下修了（本 commit 補）**：Python 3.14 的 `html.parser` 把 `title` 當 RCDATA，
    `<svg><title><script>…` 在寫入與物化兩道都放行（瀏覽器把 svg 的 title 當 HTML 整合點，裡面的標記會變成元素；第三道擋住了）。
    修法：檢查器不把 title 當 RCDATA（照瀏覽器讀）＋明文規則 `SVG_TEXT_ONLY`（svg 的 title／desc 只放字；字裡像標記的也擋——
    解析器哪天又改，標記不會躲進字裡）；規則經 `.meta.json` 的 `svg_text_only` 交給前端，缺這條前端整頁不印片段。
    變異測試證明兩道各自擋得住；審查者的注入腳本重跑，那三列都擋。另修：有故事頁但讀不到時不再印「還沒做深」。
    其餘兩條非阻擋照記不修：`_SAFE_HREF` 收反引號與超長網址、文字屬性只受 2 MB 總上限（都沒有執行風險）。

### Step 8.3 對帳計數（Z2／R1）

- **改哪裡**：`alpha/providers/story_pages.py` 加 `gaps_now`（§2.6）；`engine_b/todo_ledger.py` 加一列
  `LedgerRow("todo.story_page", "故事頁該對版", "檔", "`python -m alpha story-page gaps` → 對版 `rebind`、小修 `add`、登記等待或線索")`、
  狀態對照表三行（`story_page:stale`／`unregistered_wait`／`ride_mismatch` → `todo.story_page`）與計算函式（照 `todo.story` 的寫法，`guarded`）；
  涵蓋登記表的測試會要求每個 kind 都宣告去處。`skills/research-drain/SKILL.md` 的 ⑤ 清單加這一格與一段「故事頁對版」（三句：讀新舊兩版敘事的差、
  頁上講的沒變就 `rebind`、變了才小修；不重寫整頁）。
- **怎麼驗**：`tests/test_todo_ledger.py` 的涵蓋測試綠；新測試三種各一筆 fixture；帳讀不到時這一格印「未讀到」不是 0（INV-3）。
  `python -m crons.phase_status_hint` 的「要清的」在有值時會多這一項。
- **第④問**：最先壞的是待做清單的總表——新一格的 loader 丟例外會不會拖垮整張表。`guarded` 擋著；測試裡讓 loader 丟一次例外確認其他格照印。
  落地當天這一格的真實值預期是 0（帳是空的，三頁還沒搬進來）；8.5 之後才會有數。
- **執行紀錄（2026-11-26）**：
  - `gaps_now` 帳有壞行就 raise（讀不懂哪一版是現行頁＝未讀到，同 `fact_checks.gaps_now`）；帳檔還不存在＝還沒有任何一頁，是真的 0。
    命令讀不到印「未讀到（不是 0）」、exit 1。
  - 每項多帶 `since`（敘事換版＝新一版的日子、等待沒登記＝頁寫進帳的日子、押的單位對不上＝兩者取晚的），⑤ 這一格因此有「最老幾天」——
    「故事還沒寫」那一格沒有；drain 的「任一格最老 ≥ 7 天才推」靠它（不是進展格，只在太老時叫人）。
  - 三種的短標 `STORY_PAGE_GAP_LABELS` 與怎麼清 `STORY_PAGE_GAP_REMEDY` 都只有 `alpha/providers/story_pages.py` 那一份，命令與 ⑤ 照印。
    ⑤ 計數算檔（一檔可以同時有幾種），工作量逐檔寫種類，最多點名 5 檔。
  - 驗收：真的帳 `story-page gaps` → 0 檔 0 件；手跑心跳（`--out` 暫存、不寫快照、不發送）→ 短版與完整心跳 ⑤「0 的格」都列出這一格，
    較昨變動印「首日 1 項（今天起比對：待做 故事頁該對版）」。測試：涵蓋登記表三種都有去處；三種各一檔的 fixture 用真的 `page_gaps` 做；
    loader 丟例外時這一格未讀到、隔壁格照算；「要清的」有值時多這一項。

### Step 8.4a 「做深這一檔」與冷讀包（Z1／R1）

- **改哪裡**：`app.js` 加 `deepDivePrompt(payload, view)` 與按鈕（和 `askClaudeButton` 共用複製與攤開的那段，不抄兩份）。提示內容：
  第一行「做深 <代號>（<公司名>）」；照 `skills/detective/SKILL.md` 的「做深」蒐證、拼線索、落帳（全程不看股價）、出蒐證包；
  再照 `skills/stock-story/SKILL.md` 寫故事頁、檢查、冷讀、存進 APP；附這一頁的現況（做什麼、候選狀態與理由、故事頁有沒有、是不是過期）；
  邊界一行（圖的洞登記成線索、入圖等我 `go`；不改候選狀態；不給目標價與排序；付費來源先問我金額）。
  `askClaudePrompt` 最後那句「偵探 <代號>」保留。`alpha/narrative/story_page.py` 加 `COLD_READ_PROMPT` 與 `cold-pack`。
- **怎麼驗**：`tests/test_webapp_ask_claude.py` 加：新提示只用 payload 組、不抓任何東西、含兩份 skill 的路徑與那一行邊界；`?ask=1` 的隱藏預覽同時印得出兩段。
  `cold-pack` 的測試：`PAGE.txt` 不含 `<details>` 裡的字、`PROMPT.md` 含「不對外」「不寫任何檔」與六樣回報。
- **第④問**：最先壞的是既有的「問 Claude」按鈕（共用程式抽壞了）——headless 用 `?ask=1` 讀一次預覽。
- **執行紀錄（2026-11-26）**：
  - 共用的不只複製與攤開（`copyPromptButton`；全檔 `navigator.clipboard.writeText` 只剩一處）：「這一頁的現況」也抽成一份
    （`pageStatusLines`），兩段提示照用，多一行「故事頁：還沒有／有，寫於哪天；過期一句」——過期那一句和頁首橫幅同一個函式（`storyStaleText`）。
    `test_webapp_ask_claude.py` 原有判準照留、主詞改成共用的函式。
  - `COLD_READ_PROMPT`（與六樣 `COLD_READ_SECTIONS`）照計畫放在規則模組；`cold_pack` 要寫檔，放帳模組 `alpha/providers/story_pages.py`
    （規則模組維持純函式）。提示第一行就是派工規定的那一句「對外請求不帶 email……」；冷讀包寫 `coldread/PAGE.txt`、`coldread/PROMPT.md`，
    回報存 `coldread/REPORT.md`（宣告 `cold_read.report` 指它，E6 核得到）。`PAGE.txt` 就是量字數與 W 類檢查用的那一份看得到的字。
  - 驗收：正式 APP 重啟（`code.stale=false`）→ headless `?ask=1`：COHR、000660.KS 兩段隱藏預覽都印得出來，「做深」第一行
    「做深 COHR（Coherent Corp.）」、最後一行是邊界；頁首兩顆按鈕；390 寬零溢出、零疊字。

### Step 8.4b 畫圖工具（Z1／R1）

- **改哪裡**：新 `alpha/story_kit.py`，三個純函式，回傳 SVG 字串（只用 §2.1 白名單、顏色用 class）：
  `ladder_map(tiers, focus)`——誰賣給誰，由下往上幾排，主角標色；`time_bars(rows, unit, highlight)`——量或錢的時間長條；
  `price_log(closes, events, as_of)`——對數股價折線＋編號事件，圖上寫明畫到哪一天。寬度以手機為準（`viewBox` 寬 360 上下），字不疊。
  不抓資料：呼叫的人把數列傳進來。
- **怎麼驗**：`tests/test_story_kit.py`：三張圖的輸出各自過得了 8.1 的片段檢查；同樣輸入兩次輸出一字不差；空數列回一個寫明「沒有資料」的圖，不丟例外。
  範例頁改用它們的輸出重產一次，headless 看一眼。
- **備註**：長相在 8.5 由強模型對照已發布的三頁再調；這一步先求能用。

### Step 8.4c 文件接上真的命令（Z0／R0）

8.0 的兩份 skill 是照「私有網頁」的現況寫的。命令落地後改這幾處，別處不動：

- `skills/stock-story/SKILL.md`：步驟「交稿前核對」加「先跑 `python -m alpha story-page check <資料夾>`，ERROR 清到 0、WARN 逐條看過」；
  步驟「冷讀」的「把看得到的字存成純文字」改成 `story-page cold-pack`；步驟「發布」改成 `story-page add` → `python -m webapp materialize <代號>` →
  重啟 serve（私有網頁不再是預設產出；使用者要分享給別人時才另發）；「版面沿用已發布的頁」那一條改成「圖用 `alpha/story_kit.py`、樣式用 `webapp/static/story.css`」。
- `skills/detective/SKILL.md`：蒐證包的骨架若做成命令就換上，沒有就不動。
- `docs/OPERATIONS.md`：加一節「做深一檔與故事頁」（命令順序、對版、過渡期的舊版連結怎麼開）。
- `docs/ARCHITECTURE.md`：§6.12 個股頁改寫成新框架；新增故事頁的帳一段（檔案、欄位、白名單在哪、對帳三種、它不是 authority）。
- `CONCEPTS.md`：「故事頁」一條的「一頁私有網頁」改成現況。
- 跑 `python scripts/sync_agent_skills.py` 與文件測試那十個檔。

### Step 8.5 三頁搬進 APP（強模型；研究＋Z1）

1. 讀回三頁現行版（Aehr 第 2 版、Sivers 第 10 版、亞泰第 7 版；網址在執行者的記憶檔，不進 repo），或用使用者下載的 HTML。
   原檔存 `library/private/story_pages/src/<代號>/`。
2. 轉成 §2.1 的片段：行內樣式改 class、頁尾「系統裡的它」拆成空位與 `#system-gap`、等待加 `data-wait`、來源等級改成 `data-src`；寫 `page.json`。
   三檔的敘事若還沒換版（Aehr `ib_5fdd4c3e93736504` 要改三處），先照偵探的落帳做完，`waits` 才填得出 `watch_id`。
3. `check` → `add` → 物化 → 手機寬逐頁和已發布的頁對照（節、表、圖一樣不少）；`story.css` 與 `story_kit` 的長相在這裡調。
4. 各跑一次冷讀（第一次真跑）；回報存各自的資料夾；漏題帳補「冷讀先抓到了嗎」。舊版若拿得到，照決定紀錄 §8.3 回測。
5. Sivers 頁看得到的字刪到 15,000 以內。

### Step 8.6 結案

Completion gate（每項附查證命令或截圖路徑）：

1. 8.1–8.5 進度表全 ✅。
2. 全套測試綠；`python -m audit invariants` 沒有新的違反。
3. 三檔的個股頁印出故事頁（headless dump-dom 各一次）；一檔沒有故事頁的印出新框架。
4. 四種注入在寫入與物化都被拒（測試名）。
5. `git ls-files library/private` 為空；自 8.0 起新增的行裡 grep 不到 `claude.ai/artifact`
   （`git diff <8.0 的前一個 commit>..HEAD | grep "^+.*claude.ai/artifact"`；repo 裡 2026-10 個股頁 schema 那兩份文件原有的樣稿連結不算）。
6. 待做清單「故事頁該對版」當天的值與 `story-page gaps` 的輸出一致，逐檔列得出原因。
7. **等待 registry**：三頁的 `waits` 裡有 `watch_id` 的條數（＝由故事頁新登記或對上的等待）；**敘事**：三檔裡已換版的檔數。這兩個是進展；其餘是機制。
8. OPERATIONS、ARCHITECTURE、兩份 skill 講的命令都跑得起來。
9. closeout 報告 `docs/reports/<日期>-phase8-closeout.md`：做了什麼、沒做什麼、執行中發現要使用者決定的事（至少含：舊版個股頁的程式什麼時候刪、
   股價圖要不要改成物化時重畫、下一檔做哪一檔）。

**結案 R2（已常規 opt-in）：**

```
WORK_REQUEST（R2）
Target: Phase 8 全部 commit（git log --grep "8\." 自 8.0 起）；重點檔 alpha/narrative/story_page.py、alpha/providers/story_pages.py、
        webapp/materialize.py、webapp/static/app.js、webapp/static/story.css、engine_b/todo_ledger.py
Claimed acceptance: ①研究 session 寫的 HTML 只有經過白名單（寫入一次、物化一次、前端重建一次）才上畫面，行內程式、行內樣式、事件屬性、
        外部資源都進不來；②request path 仍然不跑 LLM、不寫檔、不抓外部、不重建；③故事頁的帳不決定候選狀態、不擋任何寫入；
        ④沒有故事頁的個股頁沒有少印候選狀態、四盞燈、等待、股價；⑤對帳三種的數與逐檔輸出一致，沒有一種是 session 自己清不掉的；
        ⑥repo 裡沒有真實三頁的內容與私有網址
Do not trust: 上面是待驗證的宣稱，不是事實
Task: 直接讀 repo 與 diff，自己跑可證偽的檢查（自己再寫兩筆注入試試；開一次 APP 看畫面），回 REVIEW（含 verdict）
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis；對外請求不帶 email、不帶個人資訊
```

**結案之後：停。** 進度表標 ✅、README 那一列改 completed、ROADMAP Phase 8 列更新，印 closeout 的待決清單，`AWAITING_HUMAN`。不自己開下一個 Phase。

---

## 4. 驗收數的是哪一層

- **機制（存在與否）**：測試數、注入被拒的筆數、畫面上印不印得出來、待做清單新一格。照印，不算研究進展。
- **等待 registry**：由故事頁新登記或對上的 watch 條數（§3 Step 8.6 第 7 項）。
- **敘事**：三檔裡因為做深而換版的檔數。
- 漏題帳的清單外條數、冷讀先抓到幾條是清單與冷讀的成績，另記在漏題帳，不是本 plan 的驗收。

## 5. 已知陷阱

- **CSP 擋行內樣式**：片段裡的 `style=` 在瀏覽器不生效，檢查也拒收；SVG 的 `fill`、`stroke` 是屬性、不受影響。別為了省事去放寬標頭。
- **`app.js` 沒有編譯器**：2026-10-08 函式撞名整頁空白、測試全綠。改完一定 headless 開一頁，不只跑 pytest。
- **改了 webapp 就重啟 8790 的 serve**（8791 是使用者別的專案，不要碰），驗 `code.stale=false`。
- **不要全量物化**（`--tracked --registry-listed` 實測 36 分鐘）：只物化要驗的幾檔。全套測試跑的時候不要並行物化（request-path 測試會假紅）。
- **Windows**：子行程用 `sys.executable`；`read_text`＋`write_text` 會把 LF 檔改成 CRLF（改既有檔用 bytes）；`library/private` 底下的暫存 `.py` 不能帶 BOM
  （用 Write 工具寫）；Bash 的 heredoc 不放程式碼。
- **別人的帳用別人的讀取函式**：現行敘事、押的單位、等待 registry、圖上節點都有現成的讀法（`alpha/providers/`、`engine_b/event_watch`、
  `webapp/materialize.py` 裡組個股頁時已經在用），不要自己打開 jsonl。
- **DOMParser 會把片段包進 `<html><body>`**：重建時從 `body` 的子節點走；SVG 節點要用 `createElementNS`，否則畫不出來而且不報錯。
- **SVG 屬性分大小寫**（`viewBox`、`preserveAspectRatio`）：Python 的 `html.parser` 會把屬性名轉小寫，白名單比對與前端重建要各自處理，測試放一筆 `viewBox`。
- **短故事帳與「故事還沒寫」那一格不動**；新一格叫「故事頁該對版」，兩格不要併。
- **`tests/test_roadmap_refs.py` 會核文件裡的連結**：文件提到的檔要真的存在。
- 8.1–8.4 的時候 `story_pages.jsonl` 是空的：一切「讀真資料看一眼」的驗證都用暫存目錄裡的範例頁，不要為了驗證把範例寫進真的私有區。

## 6. 不在範圍

- 層的數字帳（使用者 2026-11-26「4 不加」）。
- X 上的搜尋變成常規（要先有程式擋上限與記帳；另提）。
- 刪掉舊版個股頁的程式與 `page_schema`（結案後由使用者決定）。
- 故事頁的股價圖改成每次物化重畫。
- 把故事頁的寫作排進 research-drain 或無人值守（它由使用者點名；drain 只做對版）。
- 亞泰與 Aehr 的社群風向、技術文件、Aehr 圖補燒機層——是研究，照偵探的流程做，不在本 plan 的進度表。
