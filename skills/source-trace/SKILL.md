---
name: source-trace
description: >
  把轉述、截圖、搜尋摘要、推文或二手報導追回可逐字核對的原始文件，並依來源品質決定
  可抽取、誠實降級或只留 lead。當研究流程需要「追原文」、「找一手來源」、「這個轉述能不能
  當證據」、處理公開頁面的存取障礙、weekly scan trace、或遠端 chat 收到未驗證線索時使用。這是 lead-intake、
  weekly scan 與手機 intake 共用的追源規則書。
---

# Source Trace — 原始來源追索手冊

## 核心判準

**線索不是證據。只有真正取得、可定位、可逐字核對的文件內容，才能支持 claim。**

搜尋摘要、LLM 摘要、無 locator 截圖、同源轉述、只有標題或「某券商說」都不算原文。
`evidence_tier` 依實際取得的文件評，不繼承線索宣稱的來源等級。

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
`query.bottleneck --what-if`：**純結構名次有動的**才升高追平行證據的優先權（可掛
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

預設 `trace_requires_user=false` 並 park。只有 exact atom 對現有 thesis／decision 具實質影響，且下一步
確實需要使用者提供合法副本、決定是否付費或提高優先權時，才設 `true` 建立
`source_trace_review`。一般 `go` 只 dispatch bounded pq1，不授權購買；購買必須另列 vendor、方案、
exact 金額、保存範圍與預期解鎖的 atoms。

## Queue 契約

- `trace_requires_user=false`：留 trace backlog；明確 trigger 命中後回 pq1。
- `trace_requires_user=true`：`todo sync` 建 `source_trace_review`；`go` 不接受 claim、不提高 tier、不入圖。
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
