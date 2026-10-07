---
name: source-trace
description: >
  把轉述、截圖、搜尋摘要、推文或二手報導追回可逐字核對的原始文件，並依來源品質決定
  可抽取、誠實降級或只留 lead。當研究流程需要「追原文」、「找一手來源」、「這個轉述能不能
  當證據」、處理公開頁面的存取障礙、題材掃描註冊的 lead 進 pq1 後的追源、或手機經 Remote Control 丟來未驗證線索時使用。
  這是 lead-intake、pq1 研究與手機 intake 共用的追源規則書（題材掃描本身不追源）。
---

# Source Trace — 原始來源追索手冊

## 核心判準

**線索不是證據。只有真正取得、可定位、可逐字核對的文件內容，才能支持 claim。**

搜尋摘要、LLM 摘要、無 locator 截圖、同源轉述、只有標題或「某券商說」都不算原文。
`evidence_tier` 依實際取得的文件評，不繼承線索宣稱的來源等級。

`source_type` 的字彙只住 `schema/vocab.json`（不在這裡抄一份）。2026-10-01 新增的兩型怎麼評：

| source_type | 是誰說的 | tier |
|---|---|---|
| `datasheet`（產品規格書） | **供應商自報**——origin_entity＝出規格書的公司，不是印證 | 同 `ir_deck` |
| `teardown`（第三方拆解報告） | 拆解方——origin_entity 寫拆解方，不是被拆的產品廠 | 2 |

## 先分流，不要把所有缺口都叫追源

| 缺口 | 路由 |
|---|---|
| 某份文件／報告到底寫了什麼 | source trace |
| customer concentration、backlog、財務或時變數字 | 追到 filing 後交 Engine C manual observation |
| 競爭者、供應關係、可替代性、counter-path | 追一手文件後走 Graph research／RA admission |
| execution context、policy、paper／live 狀態 | Decision Lab／private authority，不用 Web 搜尋補 |

若缺口不依賴未取得文件的逐字內容，就不要建立 `source_trace_review`。

## 實際執行路由鏈

### 1. 拆 claim

每條只保留一個可驗證 atom：主體、動作／關係、對象、時間，以及線索聲稱的原始文件或事件。
先判斷這個 atom 是否真的會影響 thesis／decision；不重要的付費報告細節直接 park。

### 2. 依序嘗試四條路徑

1. **原始登記表／官方頁：**
   - 美股：SEC EDGAR、公司 IR、法說逐字稿。
   - **法說會 quote 專用路由（2026-08-15 實測，省下重走四條死路）：**
     推文／二手轉述引用的管理層說法，**多半不在任何 SEC filing 裡**——實測 COHR 的
     press release ＋ 10-K 對 `indium phosphide`／`backlog` 皆 0 hits、MTSI 的 10-Q ＋
     8-K EX-99.1 對 `laser`／`DFB`／`shortage` 皆 0 hits，兩者的 CEO 評論在 filing 裡
     只有一句泛泛場面話。**先查 filing 會落空，直接去 transcript。**
     依序：公司 IR 的 webcast replay（唯一 tier-1）→ **Investing.com（免費全文，實測
     可取得完整逐字）** → Motley Fool（只有部分季度，非每季都有）→ Yahoo Finance
     ／MarketScreener（實測 404／403）→ Seeking Alpha（paywall，須依「付費報告」節
     另行核准）。
     ⚠ **第三方轉錄不是 issuer 一手。** 對「CEO 說了什麼」是標準做法且多家可互相
     校對，但 evidence tier 最高 2；要升 tier 1 必須以 IR replay 逐句核對後才改標。
     ⚠ 不要用猜的 URL 格式——2026-08-15 兩次直接組 fool.com／Yahoo 的 transcript
     路徑都吃 404，改用 exact 標題搜尋才找到真正可得的那一家。
   - **台股：走 MOPS 電子書，不要走公司 IR 網站。** 有現成 fetcher：

     ```bash
     python -m fetchers.mops --co-id 3081 --list            # 先看有哪些文件
     python -m fetchers.mops --co-id 3081 --kind annual_report
     ```

     年報的「營運概況」章節含**最近二年度占進（銷）貨總額 10% 以上之客戶**（客戶集中度
     的一手來源）與產業結構描述；財報附註含分部與重要交易事項。
     ⚠ **公司官網通常抓不到**（2026-08-28 實測聯亞、Harmonic 皆然）：IR 頁面的年報 PDF
     連結是動態載入，靜態抓取只會拿到零散附件。聯亞那次只取得「年報前十大股東關係表」，
     一度被判成「可抽文字為 0」而 park——那是抓錯地方，不是公司沒揭露。
     ⚠ **台股沒有法定 backlog 揭露。** 年報找不到「在手訂單／未交貨／接單」是**準則的
     結構性缺席**，不是追源失敗；要記 backlog 只能填替代指標並註明（見 L11 第 5 點：
     「我找不到」與「它不存在」是兩個不同的 claim）。
     ⚠ 客戶常以代號揭露（「因客戶與本公司有營業保密約定，故以代號為之」），
     C06／A01 這類代號**不得**對應到任何具名公司。
     fetcher 已封裝的四個坑（自己刻請先讀 `fetchers/mops.py` docstring）：兩段式下載、
     列表頁 big5、`year` 是民國查詢年度而非資料年度、同年度多份修訂會撞 doc_id。
   - **瑞典（Nasdaq Stockholm／First North）：走 MFN 法定揭露，有現成 fetcher（2026-09-17）：**

     ```bash
     python -m fetchers.mfn --company sivers-semiconductors --list --match "Q2 2026"
     python -m fetchers.mfn --url https://mfn.se/cis/a/sivers-semiconductors/<headline-slug>-<id>
     ```

     期中報告本體是公告頁附件 PDF（`{doc_id}_att1`），RSS 裡沒有；瑞典文與英文各發一則、同一事件，只取英文版；
     `published_at` 只認 JSON-LD `datePublished`（UTC）。⚠ 探到 404 先看 URL 尾端有沒有 8 碼 id。
   - **英國（LSE RNS）：走 investegate 鏡像，不走 iqep.com（SSL 鏈壞）／investis RSS（軟 404）（2026-09-17）：**

     ```bash
     python -m fetchers.rns --company IQE --list --match results
     python -m fetchers.rns --url https://www.investegate.co.uk/announcement/rns/iqe--iqe/<headline-slug>/<id>
     ```

     `published_at` 取 RNS 本體 dateline（清單的日期＋時間一併記入 basis）；「Summary by AI」不是一手。站點 502 是
     「暫時不可用」不是「不存在」。⚠ 年報 PDF 查核報告雙欄交錯讀不出來——going concern 附註抓年度業績 RNS 全文（HTML）。
   - **日股：有価証券報告書走 EDINET，受注残高與決算數字走決算短信（TDnet）。**
     ⚠ EDINET API v2 需 subscription key（未申請）；2026-08-28 實測改抓 TDnet 決算短信
     正本即取得受注残高與主要相手先販売実績，未被 key 擋住。公司 IR 網頁同樣是動態表格，
     抽不到文字——與台股同一個形狀。
   - A 股：交易所公告、年／季報、問詢函、互動易。
   - 技術：DOI／publisher、arXiv、OFC／ECOC、標準組織、專利。
2. **交叉方官方文件：** 被點名客戶、供應商、合作方或監管機構的 filing、公告與法說。
3. **精確搜尋：** 用 exact title、作者、日期、報告編號或獨特句子搜尋，再打開 canonical／作者頁。
   搜尋摘要只用來找路；多篇重述同一報告仍是 `same_origin`。
4. **可讀性恢復：** 「公開內容的 access recovery 梯子」只適用於原本即公開的頁面：
   in-app browser → 官方下載／公開文字版 → `txtify.it`；
   使用者合法持有的本機副本標 `local_only`。官方音訊無 transcript 時，本機可用：

```powershell
& '.venv\Scripts\python.exe' scripts\transcribe_audio.py '<本機檔案或直接音訊 URL>'
```

ASR 只用來找 timestamp；數字、技術詞與 quote 必須回聽核對。

### 2b. 輸入是層／節點時（走圖問句、層讀圖、「這一層還有誰」）

輸入不是一句 claim、而是一個節點（例：`tech:cw_dfb_laser`）時，要找的是**列舉這一層供應商集合**的文件——
一份文件逐字具名多家，比多讀一份供應商自述有用（G4）。上面「先查 filing 會落空，直接去 transcript」那條
**對 claim 仍成立**；這一節只管「輸入是層」。選源順序：

1. **客戶端申報的供應商段**：客戶 10-K／20-F／年報的原物料、主要供應商、single-source 風險段；台股年報
   「最近二年度占進貨總額 10% 以上之供應商」。客戶說誰供它＝L8 要的交易對手方。
2. **產業報告**：自己產生市占／出貨數據的研究機構——登記在 `config/publishers.json` 的自產資料類別才算外部印證；
   媒體轉述同一份報告是 `same_origin`。
3. **規格書／teardown**：teardown 是第三方拆解（tier 2）；datasheet 是供應商自報（見上表）。
4. **供應商自己的文件**（年報競爭者段、法說）：可以列舉，但不算印證（L8：供應商自稱是弱主張）。

找到 → RA request 帶 `layer_enumerations`（`origin_role` 照實填；prepare 會核對引文真的具名每一家）→ pq2 `ra_admission`。
公開一手找不到、或只有付費 → 先照「向使用者要文件」一節開口（`trace_requires_user=true`）；使用者說拿不到或不要，lead 才停在 `awaiting_named_disclosure`（trigger entities＝這一層的客戶或供應商），
不要用再讀一份供應商自述去補（L8）。路徑表的 `layer_document` 那一格指的就是這一節。

### 3. access boundary

遇到 paywall、login、CAPTCHA、anti-bot 或其他 access control 就停止。不得偽裝 Googlebot、偽造
Referer；不得使用外洩鏡像、共用登入或規避限制的代理／快取。公開頁可以去除導覽、廣告與 UI 雜訊，
但只保存研究必要的有限 quote 與 locator，不重製全文。

### 4. 核對與 origin 去重

- 公司名、產品、數字與關係必須真的出現在 quote；類別詞不能推出具名公司。
- `origin_entity` 是目前取得文件的發出者；`origin_event` 是它描述的原始事件。
- 搜尋摘要只供 discovery；同標題報導、公開 reader 與同一張截圖都標 `same_origin`／`origin_linkage`，
  代理輸出本身不是新的 origin。
- 找到官方廣義方向，不等於找到券商的排名、TAM、目標價或獨家原句。

## 結果只用這六種

| 結果 | 處置 |
|---|---|
| `original_obtained` | 有原文、URL、quote、locator；依 tier 進 extract 或 park |
| `tier_1_2_honest_passthrough` | 取得的一手文件提到另一個拿不到的事件；只抽目前文件明寫的內容 |
| `partial` | 只有部分 atoms 被一手來源支持；其餘逐項標未驗證 |
| `contradicts` | 原文不支持或反駁線索；以原文為準，反證回 triage |
| `isolated_tier_3` | tier 3 報導／券商轉述追不到原文；不產 extraction、不入圖 |
| `lead_only_tier_4` | 社群／論壇／截圖追不到原文；只留 lead |

只找到報告標題、作者、日期或 canonical URL 時，寫進 `attempts_ref`，但不另創 trace status，
也不提高 evidence tier。

**`isolated_tier_3`／`lead_only_tier_4` park 前多做一步（2026-08-31 定案）：** 若截圖/轉述
含可結構化的具體主張（誰供應誰、誰付錢給誰），park 時同步建假設
（`python -m engine_b.hypotheses add`，見 `docs/OPERATIONS.md`「截圖假設層」）＋跑一次
`query.bottleneck --what-if`：**結構表有動的（多一列、或錨可達性／sub 改變；2026-09-23 起不比名次）**才升高追平行證據的優先權（可掛
fact_verification watch）；沒動的照常 park——沉底從此是計算結果不是黑洞。假設永不入圖、
永不參與 evidence 分級；入圖唯一路徑仍是本 skill 的一手取得流程。

取得 tier 3 報告只解決可核對性；tier 3 仍維持 tier 3，不因「找到原報告」升級。

## 最小紀錄

每條 claim 至少留下：

```yaml
claim: "可單獨驗證的主張"
claimed_origin: "聲稱來自哪份文件／事件"
attempts_ref: "查過的官方登記表、交叉方與 exact query／URL"
trace_status: "六種結果之一"
obtained_origin_entity: "真正取得文件的發出者；沒有則 null"
quote: "必要有限引文；沒有則 null"
locator: "頁碼／段落／timestamp；沒有則 null"
storage_permission: "repo_excerpt | local_only | unknown"
trace_next_trigger: "什麼新事件值得再查"
trace_requires_user: false
```

禁止只寫「Google 沒找到」。若某路徑是網路／權限失敗，記 `access_blocked`，不能改寫成
`no_result`；但不用為同一個失敗反覆製造沒有新資訊的 retry。

## 付費報告

先拆成兩類：

- **公開一手來源可驗證的 atoms：** 照正常 SOP 處理。
- **只有報告原文能證明的 atoms：** 如排名、TAM、目標價、券商原句；未合法取得前維持未驗證。

**預設改成開口（2026-10-06 使用者指示；Phase 7 failure log #29）：** 拿不到的來源若是使用者可能拿得到的（券商報告、法說逐字或 memo、
論文全文、付費資料庫、公司 IR 回覆），而且 atom 落在「薄層上的邊緣公司」或層說明的範圍，就設 `trace_requires_user=true` 建立
`source_trace_review`，照下一節的格式開口；**不得只因為拿不到就 park**。仍可設 `false` 並 park 的只有兩種情形：atom 不影響任何讀圖、敘事或候選狀態；
或它根本不存在於任何可取得的文件（要寫出「如果答案存在，它會在哪一節」，L11-5）。
一般 `go` 只 dispatch bounded pq1，不授權購買；購買必須另列 vendor、方案、exact 金額、保存範圍與預期解鎖的 atoms
（`config/standing_authorization.json`：付費永不列入常規授權）。

## 向使用者要文件（2026-10-06）

要之前答不出「它說了什麼」，但答得出「它是不是回答這個問題的指定位置」。所以要求分兩種，寫明是哪一種：

| 種類 | 什麼時候 | 要求裡必須有 |
|---|---|---|
| **有問題型** | 已經有一個具體問題，這份文件是答案該在的地方 | 問題一句；**結果表**：每一種可能的答案各會改變什麼（證實 → 哪個狀態或邊會變；推翻 → 哪個主張記「講過頭」、哪個 watch 改期；沒提 → 缺席怎麼寫） |
| **探索型** | 這一層很薄、這份是該層的指定一手來源、我們這邊沒人讀過；事前講不出會變什麼 | 明標「探索」；**上限**（例：一層一份初次覆蓋加兩份法說）；不假裝有目標 |

兩種都用同一格式：

```text
要：<文件名、發布者、日期或期別>
種類：<有問題型｜探索型>
為什麼：<有問題型＝問題＋結果表；探索型＝這一層薄在哪、為什麼是指定來源、上限>
已經知道的（不用再找）：<我查過的公開來源與它說了什麼；媒體轉述的投顧結論照寫並標「轉述」、寫出媒體與日期>
去哪找（5 分鐘內做得完）：
  1. <哪裡：使用者的券商 App 研究報告區（元大、凱基）或一個指定網址> 搜：<公司名／代號／關鍵字> 找：<哪一家、哪段日期、標題或內容要有什麼字>
  2. <第二個地方（可省）>
找不到就回「沒有」：<回了之後我怎麼處理——用哪個替代、或照缺席寫>
拿不到的替代：<退而求其次的公開來源，或「沒有，等」>
```

**「去哪找」不得空泛（2026-10-07 使用者：「會給我要去哪個券商找嗎？我不太能大海撈針」）：**
- 寫到使用者照著做就能在五分鐘內有結論：哪個 App 或網址、搜什麼字、找哪段日期；查得到是哪一家投顧、哪天出的（媒體常轉述目標價），就把它寫出來。
  使用者有元大、凱基帳號（研究報告區）；外資報告散戶帳號多半看不到——不要叫使用者去找外資報告，除非他說拿得到。
- **公開的我先自己抓**：MOPS 年報與法說簡報、公司 IR、SEC、官網、新聞——抓過才開口，抓過的寫進「已經知道的」；還沒抓過的公開來源不得列進「去哪找」。
- 「找不到就回『沒有』」是使用者的完整回覆，不再追問；我照那一行處理（drop 或照缺席寫）。

**讀完必交報告**（問責的時點在讀後，不在讀前）：問了什麼／哪些答到／哪些沒答到／哪些答案相反／哪些是沒問到卻讀到的新東西。
它讓「要你拿文件」這條管道可量：你拿來的文件裡，有幾份真的改了一條主張或一個候選狀態（ledger／registry）。
心跳段 3 印「等你提供的文件 N 份」＝pq2 `source_trace_review` 未結案數。

## Queue 契約

- `trace_requires_user=false`（只限「付費報告」一節的兩種情形）：留 trace backlog；明確 trigger 命中後回 pq1。
- `trace_requires_user=true`：`todo sync` 建 `source_trace_review`，hint 帶「向使用者要文件」的格式；`go` 不接受 claim、不提高 tier、不入圖；
  心跳「等你提供的文件 N 份」數的就是它。
- 取得原文且有 graph delta：prepare RA，另進 `ra_admission` pq2。
- 只屬 Engine C observation：交對應 authority lane，不製造空 RA。
- 仍未取得：以 `trace:<trace_status>` terminal receipt 結束本次 review，保留下一個 trigger。

## 對使用者的短格式

```text
已取得：<文件／quote／locator，或「無」>
支持：<被支持的 atoms>
未支持：<仍缺原文的 atoms>
結果：<trace_status>
下一步：<extract／其他 authority／park + trigger／需要使用者的 exact 選擇>
```

本機與遠端都遵守同一判準；只有本機可假設能讀 private local copy、執行音訊轉錄或寫入本機 authority。
