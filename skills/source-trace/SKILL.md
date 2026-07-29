---
name: source-trace
description: >
  把轉述、截圖、搜尋摘要、推文或二手報導追回可逐字核對的原始文件，並依來源品質決定
  可抽取、誠實降級或只留 lead。當研究流程需要「追原文」、「找一手來源」、「這個轉述能不能
  當證據」、處理公開頁面的存取障礙、weekly scan trace、或遠端 chat 收到未驗證線索時使用。這是 lead-intake、
  weekly scan 與手機 intake 共用的追源規則書。
---

# Source Trace — 原始來源追索手冊

## 定位

**線索不是證據。先追回可逐字核對的原始文件，再決定是否抽取；追不到時要誠實降級，
不能把轉述者冒充成原始事件，也不能讓低品質材料形成互相引用的假共識。**

本手冊必須能在遠端 chat 單獨使用。標有「本機入口」的命令只適用於本機 session；
cloud routine／手機不能假設可碰本機檔案或 localhost。

### 本機音訊／podcast 入口

官方音訊沒有逐字稿時，本機 session 可執行：

```powershell
& '.venv\Scripts\python.exe' scripts\transcribe_audio.py '<本機檔案或直接音訊 URL>'
```

預設用 `small.en`＋CPU int8 在本機推論；首次使用會下載模型，之後從
`library/private/models/faster-whisper/` 讀 cache。完整逐字稿只寫入 ignored 的
`library/private/transcripts/`，固定標為 `local_only`。ASR 只用來找 timestamp；技術名詞、
數字與要引用的句子仍須回到該 timestamp 音訊核對。不得因「有機器逐字稿」就提高
`evidence_tier`，辨識含糊時仍依下方規則降級。

## 什麼算「追到原文」

至少滿足以下一種：

1. 可存取的官方／原作者頁面或文件，能看到所需主張的逐字文本，並保存穩定 URL、
   文件 metadata、locator 與有限 quote。
2. 來源授權允許保存原文時，取得逐字文件內容與可定位位置。
3. 原站只允許有限節錄時，保存 canonical URL + 研究所需的有限逐字 excerpt + locator。

以下都**不算**原文：搜尋摘要、LLM 摘要、沒有 URL/locator 的截圖、轉述者自己的改寫、
「某券商說」但找不到報告、只看到標題、或 quote 實際為 null。即使內容看起來可信，
也只能依目前真正取得的文件分級。

## 路由鏈：先專用登記表，再通用搜尋

每條 atomic claim 依序走；前一層有結果就優先使用，不為湊三份而收集同源轉述。

| 類型／市場 | 第一層：原始登記表 | 第二層：交叉方 | 第三層：通用搜尋 |
|---|---|---|---|
| 美股公司 | SEC EDGAR 的 10-K/10-Q/8-K/S-1/Form 4、公司 IR、法說逐字稿 | 客戶／供應商 filing、官方產品／design-win 公告 | 用公司名 + exact phrase + filing/form/date 搜尋 |
| 台股公司 | MOPS 公告、月營收、財報、法說會／IR | 上下游上市公司 MOPS、交易所公告 | 公司名／代號 + 公告關鍵字 + 日期 |
| A 股（備用） | 年報／季報／臨時公告、交易所問詢函、互動易 | 招投標、中標、環評能評、海關、上下游公告 | 公司名 + exact phrase + 公告類型 |
| 技術／學術 | arXiv、DOI/publisher page、OFC/ECOC 議程與論文、標準組織 | 作者／實驗室頁、專利、公司技術白皮書 | 論文標題 exact phrase、作者、conference/year |
| 產業／供應鏈 | 當事公司官方文件或被點名客戶／合作方文件 | 監管文件、正式產能／qualification 通知 | 產業媒體、券商摘要、Substack、社群只作 discovery |

美股本機可用 `fetchers/edgar.py`，但這是**本機入口**；cloud routine 應用 web search
打開 SEC/IR 原頁。通用搜尋永遠是第三層 discovery，不因搜尋結果彼此重複就算多個
`origin_entity` 或 `origin_event`。

## 公開內容的 access recovery 梯子

遇到 JS rendering、壞連結、地區 routing、搜尋只見摘要或一般抓取器讀不到時，依序嘗試並記錄；
目的只是**恢復對公開內容的正常讀取**，不是繞過付費、登入、授權或技術性 access control：

1. 先找 canonical URL、官方 research／IR index、作者頁、文件編號、日期與公開下載 endpoint。
2. 用 exact title、作者、日期、報告編號、獨特句子與當地語言查找；搜尋摘要只供 discovery，
   不能充當 quote 或原文。
3. 找相同標題的媒體報導以恢復 metadata／claimed origin；若它只是重述同一報告或同一貼文，標
   `same_origin`，不得當獨立佐證。發布時間緊接原線索、保留原線索特有評論或數字時，預設同源。
4. 回到被點名公司、客戶、供應商、監管機構或作者的官方頁，逐條獨立核對 atomic claims；
   可以確認廣義方向，但不得把 broad corroboration 外推成 exact named supplier mapping。
5. 公開 reader／文字轉換服務（例如 `txtify.it`）只可用於 canonical URL **原本即公開、無需登入／
   訂閱／cookie，且障礙只是 rendering compatibility** 的情況。必須同時保存 canonical URL、轉換服務、
   取得時間，並抽查標題／作者／日期／關鍵段落與原站一致；代理輸出本身不是新的 origin。
6. 使用者合法持有的本機副本預設 `local_only`；只保存研究必要 excerpt／locator，不上傳 cookie、
   token URL 或未授權全文。
7. 遇到 paywall、login、CAPTCHA、robots／anti-bot 或其他 access control 就停止；不得使用外洩鏡像、
   偽造憑證、規避限制的代理或其他 circumvention。需要購買時另走 exact vendor／金額核准。

`txtify.it` 不是預設路徑，也不是「看到 403 就試」的繞過器。若原站 403 的原因不明，先記
`access_blocked` 並做同路徑權限重跑；確認是公開頁的 rendering 問題後，才可走第 5 層。

## 每條 claim 的 Trace 迴圈

1. **拆 atomic claim：** 主體、動作／屬性、對象、時間、原線索說它來自哪裡。
2. **辨識聲稱的原始事件：** filing、法說、公告、論文、客戶名單或只是作者推斷。
3. **走對應路由：** 先官方登記表，再交叉方，最後 exact-phrase 通用搜尋。
4. **核對逐字內容：** 公司名、產品型號、數字與關係必須真的出現在 quote；只出現類別詞
   不可推導具體實體。
5. **登記 origin：** `origin_entity` 是真正發出目前取得文件的人；`origin_event` 是原始事件。
   找不到聲稱的原文件時，不得把轉述者標成原事件的發出者，也不得反過來把被轉述機構
   寫成目前文件的 `origin_entity`。
6. **依下表處置，留下完整嘗試紀錄。** 若失敗看起來來自 sandbox／proxy／本機網路權限，先將
   `failure_class` 記為 `access_blocked`，再以完全相同路徑在允許本機網路的權限下重跑一次；仍失敗時，
   至少再試一條官方替代路徑。`blocked` 不是 `no_result`、不支持也不反駁 claim，必須留在追源 backlog。
7. **park 必須帶下一個 trigger：** 寫入 lead refs 的 `trace_status`、`trace_attempts_ref`、
   `trace_next_trigger`、`trace_requires_user`，並由 Daily 的 `engine_b.cli trace-backlog` 持續可見。
   `trace_requires_user=true` 只用於需要合法 access／付費／人工優先權的 exact 問題；一般新 metadata、
   官方事件或 scheduled retry 仍留 pq1，不占 pq2。

## 分級處置（追不到不是同一種結果）

| 最終可取得材料 | 處置 |
|---|---|
| 找到原始 tier 1–2 文件與逐字 quote | `original_obtained`：可進 extract；保存原文件 origin、URL、locator、quote |
| 目前真正取得的文件本身是 tier 1–2，但它提到另一個拿不到的事件 | `tier_1_2_honest_passthrough`：可產草稿，但只引用目前文件的逐字文字；明標「原事件未獨立取得」，不可算第二 origin |
| tier 3 報導／研究，且聲稱的原文追不到 | `isolated_tier_3`：不產 extraction 草稿、不入圖；進「追源未果」backlog，保留 lead 與嘗試紀錄 |
| tier 4 社群／論壇／截圖，且原文追不到 | `lead_only_tier_4`：只留線索，不產草稿、不呼叫 `load_extraction` |
| 找到原文但它不支持、只部分支持、或直接反駁原線索 | 以原文為準，記 `contradicts`／`partial`；反向證據仍優先進 triage，不把它當追源失敗 |
| 原文有 paywall／授權限制 | 授權允許才保存；否則只存 canonical URL、metadata 與允許的有限 excerpt，或 `local_only`。付費不等於可上傳 |

`evidence_tier` 依真正取得的文件評，不繼承線索宣稱的來源等級。tier 3–4 追不到原文時
隔離，是為了阻止多篇轉述同一未見文件的報導形成假交叉驗證。

## 嘗試紀錄格式

每條 claim 都輸出一筆，成功與失敗都記：

```yaml
claim: "可單獨驗證的主張"
lead_url: "起始線索 URL"
claimed_origin: "線索聲稱來自誰／哪個事件"
attempts:
  - route: "SEC EDGAR | MOPS | customer IR | arXiv | exact-phrase search | ..."
    access_method: "canonical | official_index | exact_title | same_title_media | public_transformer | local_copy"
    query_or_url: "實際查過的 query 或 canonical URL"
    canonical_url: "聲稱原文的穩定 URL；沒有則 null"
    transformation_service: "例如 txtify.it；未使用則 null"
    origin_linkage: "independent | same_origin | metadata_only | unknown"
    result: "found | no_result | blocked | paywalled | mismatch | contradicts"
    failure_class: "access_blocked | paywall_or_login | anti_bot | timeout | tls_failure | transport_failure | provider_api_error | null"
    note: "找到/沒找到什麼"
trace_status: "original_obtained | tier_1_2_honest_passthrough | isolated_tier_3 | lead_only_tier_4"
obtained_origin_entity: "真正取得文件的發出者；沒有則 null"
obtained_source_type: "filing | transcript | official_pr | paper | industry_report | social | ..."
evidence_tier: 1
quote: "逐字引文；追不到則 null"
locator: "頁碼／段落／timestamp；追不到則 null"
storage_permission: "repo_full | repo_excerpt | local_only | unknown"
next_action: "extract | park_trace_backlog | lead_only | investigate_contradiction"
```

### Backlog → pq1／pq2 路由

- `trace_requires_user=false`：保留在 trace backlog；`trace_next_trigger` 命中後重新排入 pq1。
- `trace_requires_user=true`：`todo sync` 建立 `source_trace_review`。使用者 `go` 只授權 bounded
  source trace 並 dispatch 回 pq1；不代表接受 claim，也不授權付費或入圖。
- pq1 取得可引用原文並產生 graph delta：prepare Research Action，另進 `ra_admission` pq2。
- pq1 仍未取得原文：以 `trace:<trace_status>` terminal receipt 結束本次 review，保留下一個 trigger。
- 需要購買新報告／訂閱：必須另提出 vendor、方案、exact 金額與 storage permission；不得由一般
  `source_trace_review go` 推定消費核准。

禁止只寫「Google 沒找到」。至少記錄試過的專用登記表、交叉方與 exact-phrase query；
若環境無法連某路徑，寫 `blocked`，不要假裝已查完；完成權限重跑與官方替代路徑前，不得改寫成
`no_result`。後續成功時保留原 attempt 並加 recovered attempt，不能刪掉第一次失敗造成的觀測偏誤。
同標題報導、搜尋摘要與公開轉換服務還必須記 `origin_linkage`；它們可以幫忙找路，不能製造新的
evidence origin。

## 遠端 chat／routine intake SOP

1. 收到未驗證線索先讀本手冊（手機／網頁用 MCP `get_source_trace_manual`；cloud routine
   也可直接讀 repo 本檔）。
2. 拆 claim 並跑 Trace；tier 3–4 未果只回 lead/backlog，不生成假 extraction。
3. 通過者再讀 `get_extraction_rules`，依 quote 與真正 origin 產 provider-independent JSON。
4. 向使用者展示來源核對表與降級標記；只有人工核准後才能呼叫 `load_extraction`。
5. 寫入工具若支援 raw/provenance 參數，依 `storage_permission` 傳 canonical URL、有限 excerpt
   或獲授權全文；授權不明預設 `local_only`，不得把 secret-bearing URL/cookie 寫入 repo。
6. 回報實際落地／入圖結果。失敗保留為 pending，不可宣稱完成。

## 快速走查

- Tier 3 文章聲稱「客戶只用 Sivers」，SEC/客戶 IR/官方公告都找不到：
  `isolated_tier_3`，進追源未果清單，**沒有 extraction 草稿**。
- 官方合作方公告提到 Sivers 元件，但拿不到它引用的客戶測試：
  `tier_1_2_honest_passthrough`，只抽公告實際寫出的合作內容，客戶測試標未獨立取得。
- 推文截圖聲稱 Broadcom 客戶轉回 copper，找到客戶法說逐字原文：以客戶法說為 evidence；
  即使方向反駁現有 CPO thesis，也交 signal-triage 優先放行。
- 社群謠言無 URL、無 quote、無原文：`lead_only_tier_4`，不呼叫寫圖工具。
