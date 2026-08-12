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
   - 台股：MOPS、交易所、公司 IR。
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
