# Phase 8 個股故事頁進 APP — 結案報告（2026-11-27）

> plan：[`docs/plans/2026-11-26-001-feat-phase8-story-page-app-plan.md`](../plans/2026-11-26-001-feat-phase8-story-page-app-plan.md)（各 Step 的執行紀錄在 §3）；
> 決定紀錄：[`docs/brainstorms/2026-11-25-story-question-list-goal.md`](../brainstorms/2026-11-25-story-question-list-goal.md)（§8 S4 修正案、§9 收斂）；
> 清單與冷讀的成績單：[漏題帳](phase8/story-question-log.md)（不是本 Phase 的驗收，plan §4）。
> 執行者：8.0 強模型；8.1–8.4c 便宜模型；8.5–8.6 由使用者 2026-11-27 改派（plan §0.5 進度表）。
> 數字都是 2026-11-27 上午（台北）量的；**現況數字會腐壞，引用前重跑各列的查證命令**。量測腳本與輸出在 session 暫存區，全部唯讀；
> 真實三頁的內容與私有網址不進 repo。

## 0. 做了什麼（起點 `28b40385`＝使用者 11-26 的簽核紀錄）

| Step | commit | 內容 |
|---|---|---|
| 簽核 | 28b40385 | 記錄使用者 11-26 的簽核與指示（S4 修正案、Aehr 算過、先開發完一版） |
| 8.0 | 6a700688 | plan 定案；偵探（蒐證、拼線索、落帳）與故事頁（呈現、檢查、冷讀）的分工寫進兩份 skill；AGENTS 四處；ROADMAP 整理 |
| 8.1 | 5c2c9f21、02ad42b5 | 故事頁的帳（只能追加，一版對一版敘事）；片段與宣告的檢查（E 擋、W 提醒）；`python -m alpha story-page`；合成範例頁 |
| 8.2 | 523952cf、a868f9e5 | 物化把現行故事頁放進個股物化檔（片段再檢查一次）；APP 個股頁換新框架（故事 → 系統裡的它；沒做深的印短故事；舊版留在 `#/old/<代號>`）；`story.css`。**R2 GO**，非阻擋一條當下修（svg 的 title／desc 只放字） |
| 8.3 | c8a65802 | 故事頁和系統對不上的三種（敘事換版、等待沒登記、押的單位對不上）：`story-page gaps`、⑤ 新一格「故事頁該對版」 |
| 8.4a | 928dd3f2 | 「做深這一檔」按鈕；冷讀包 `cold-pack`（提示唯一一份在程式裡） |
| 8.4b | 63be1f21 | 畫圖工具 `alpha/story_kit.py`（誰賣給誰、時間長條、對數股價），輸出過得了片段檢查 |
| 8.4c | d69ead6a | stock-story skill、OPERATIONS、ARCHITECTURE §6.12、CONCEPTS 接上真的命令 |
| 8.5 | 8b33a604 | 三頁（Aehr、Sivers、亞泰）搬進 APP：先落帳（三檔敘事換版、等待登記）→ 轉成片段與宣告 → 檢查 → 冷讀 → 物化；APP 加句尾標記的圖例、表格那一列的徽章放進最後一格 |
| 8.6 | （本 commit） | 本報告；全套抓到 8.2 帶進來的兩條失敗，當下修（§4 第 1 條）；AEHR、亞泰的賭注句綁到新版敘事（§4 第 2 條） |

範圍：`git diff --stat 28b40385^..8b33a604`＝49 個檔、+5,290／−159。新程式檔：`alpha/narrative/story_page.py`（規則）、`alpha/providers/story_pages.py`（帳）、
`alpha/story_kit.py`（畫圖）、`webapp/static/story.css`。
**本 Phase 沒有 Neo4j 寫入、沒有鑄 pq2**（待辦池最新一筆 `added_at` 是 2026-11-25 21:40 UTC＝那天的 daily，早於起點）、**沒有動資本與四個人工 gate**；
`ARTIFACT_SCHEMA_VERSION` 與 brief contract 沒升版（個股物化檔多的是加法欄）。

## 1. 九項 completion gate（plan §3 Step 8.6）

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | 8.0–8.5 進度表全 ✅ | ✅ 九個 Step commit 都在 plan §0.5 進度表 | plan §0.5 |
| 2 | 全套綠；invariants 沒有新的違反 | ✅ 修後重跑全套 **5,307 passed、2 skipped、0 failed**（33 分 40 秒）；第一次跑 2 failed，都是 8.2 帶進來的，當下修（§4 第 1 條）。`audit invariants` **15 PASS／0 FAIL（共檢查 25,828 筆）**；兩條既有註記照舊（PointInTime 28 份 SourceDoc 未定日；GateDiscrimination 40／64 個 gate 樣本不足，audit 自己標「不當作通過也不當作失敗」） | `python -m pytest -q -p no:cacheprovider`；`python -m audit invariants` |
| 3 | 三檔印出故事頁；一檔沒有故事頁的印新框架 | ✅ headless Edge（390 寬、展開全開）：**AEHR、SIVE.ST、6727.TWO** 各印一份 `article.story-page`、句尾標記圖例、`data-wait` 14／13／13 列各帶一個徽章（Sivers 3 個「醒了待判」）、「系統裡的它」一塊；**AXTI、COHR**（沒有故事頁）印「這一檔還沒做深」＋新框架；`#/old/COHR` 舊版照印、頁首有「回新版」。六頁溢出 0、頁面程式錯誤 0。疊字 10／29／14 對都在照搬的手繪圖上（§4 第 8 條）；APP 自己畫的頁（AXTI、COHR、舊版）0 | `http://127.0.0.1:8790/?selfcheck=1&w=390&open=1#/<代號>`（selfcheck 寫進 `#selfcheck`；OPERATIONS「做深一檔與故事頁」） |
| 4 | 四種注入在寫入與物化都被拒 | ✅ **寫入**（E1）：`tests/test_story_page.py::test_each_injection_is_rejected_by_the_whitelist[script\|event\|style\|javascript_href]`；拿掉任一道仍擋得住的變異：`test_mutation_tag_whitelist_is_what_rejects_script`、`test_mutation_event_and_style_attributes_are_caught_by_two_layers[event-onclick\|style-style]`、`test_mutation_javascript_href_is_caught_by_two_layers`。**物化**：`tests/test_webapp_materialize.py::test_a_broken_fragment_is_an_absence_and_the_artifact_is_still_written`（4 個參數；壞片段＝故事那一塊印讀不到的理由，整份物化檔照寫）。第三道（前端照白名單重建）由 8.2 的 R2 以四十多筆注入＋headless Edge 驗過（plan 8.2 執行紀錄） | 上列測試 |
| 5 | `library/private` 不進版控；新增行沒有私有網址 | ✅ `git ls-files library/private`＝0 行；`git diff 28b40385^..HEAD \| grep "^+.*claude.ai/artifact"`＝6 行，全是規則文字（E4 的說明、本 gate 的原文）與測試裡的假網址 `…/artifact/abc` | 兩條命令 |
| 6 | ⑤「故事頁該對版」與 `story-page gaps` 一致、逐檔列得出原因 | ✅ 兩邊都是 **0**：手跑心跳 ⑤「0 的格」列出這一格；`story-page gaps`＝0 檔 0 件（重綁賭注句、重物化之後再跑一次，仍是 0）。**逐檔原因今天是空的成立**——非零時逐檔印種類與怎麼清，由 8.3 的測試證明：`tests/test_todo_ledger.py::test_story_page_gaps_count_tickers_one_fixture_per_kind`（三種各一檔）、`tests/test_story_pages_provider.py::test_story_page_gaps_command_prints_each_gap_and_how_to_clear`；帳讀不到印「未讀到」不是 0：`tests/test_todo_ledger.py::test_story_page_ledger_unreadable_is_not_zero_and_other_cells_still_print` | `python -m alpha story-page gaps`；`python -m crons.heartbeat --out <檔> --brief-out <檔>`（不帶 `--write-snapshot`） |
| 7 | 等待 registry 與敘事（進展） | 見 §2 | §2 |
| 8 | OPERATIONS、ARCHITECTURE、兩份 skill 講的命令都跑得起來 | ✅ 8.5 實跑：`story-page check／add／list／show／text／gaps／cold-pack`、`webapp materialize <代號>`、selfcheck 網址、舊版路由 `#/old/<代號>`（8.6 再開一次 `#/old/COHR`）；`rebind` 只跑 `--help`（8.5 的對版是換宣告重 `add`，沒用到它；8.1 的測試跑過真的 rebind）；detective skill 的 `alpha detective`、`briefing alpha-card`、`engine_b.cli register` 參數解析得過 | 各命令 `--help` 與 8.5 執行紀錄 |
| 9 | closeout 報告 | ✅ 本檔；要你決定的在 §5 | — |

## 2. 驗收數的層（plan §4）

**進展（只數這兩樣）：**

| 層 | 數的東西 | 結果 |
|---|---|---|
| 等待 registry | 三頁 `waits` 裡有 `watch_id` 的條數 | **40／40**（AEHR 14、Sivers 13、亞泰 13）。原本沒有編號的 15 列，由 8.5 新登記的 **13 條條件**（Sivers 反證 1；亞泰反證 4、加碼條件 2；Aehr 反證 5、加碼條件 1）與 **1 條日期等待**（Sivers 第三季報告延到 11-30）接上；其餘 25 列對上既有的等待。徽章今天：Sivers 3 個「醒了待判」（11-23 LITE 與 META 的 8-K 叫醒的，還沒判） |
| 敘事 | 三檔裡因為做深而換版的檔數 | **3／3**：Sivers 換版一次（加反證第 8 條、缺 X 的日期改掛 11-30）；亞泰重述一次（改正一處事實：昆山睿平是亞泰的子公司，不是台光電的第二家設備商；判斷不變），同版補反證 4、加碼條件 2；Aehr 換版兩次（「卡在哪」補三件與反證、加碼條件；之後為錨點核出的兩處字重述一次） |

**機制（存在與否，照印、不算進展）：**
- 測試檔 316 → **319**（＋`test_story_page`、`test_story_pages_provider`、`test_story_kit`；退役 0）；測試函式 4164 → **4259**，新增 95、**拿掉 0**
  （`test_story_page` 38、`test_story_pages_provider` 30、`test_story_kit` 12、`test_webapp_materialize` 8、`test_webapp_static_js` 4、`test_todo_ledger` 2、`test_webapp_ask_claude` 1）。
  8.6 改了一條既有測試的斷言主詞（§4 第 1 條），沒拿掉任何斷言。查證：`git grep -n -E "^\s*(async )?def test_" <rev> -- 'tests/*.py'` 兩版相減。
- 三頁看得到的字：Sivers 14,931、AEHR 14,925、亞泰 11,815（Sivers 由超過 1.5 萬刪進來）。
- 冷讀：三頁現行版各一次（前向）、三份舊版各一次（回測）；回測時你讀後說的 10 句，冷讀先抓到 3 句（寫法 3 句抓到 2；清單外與題內 7 句抓到 1）——
  冷讀擋得了寫法、擋不了清單外。逐句在漏題帳。
- 研究副產品：`library/raw` 新節錄 5 份；錨點 Aehr 14 個、亞泰 12 個；`brief-check --record` 三筆。

## 3. 沒做的（plan §6 不在範圍，照舊不做）

層的數字帳（「4 不加」）；X 搜尋變常規；刪舊版個股頁的程式與 `page_schema`（§5 #1）；股價圖物化時重畫（§5 #2）；把故事頁寫作排進 drain 或無人值守；
亞泰與 Aehr 的社群風向、技術文件、Aehr 圖補燒機層（是研究，照偵探流程做）。

## 4. 執行中發現、實際做了什麼（偏差摘要；全文在 plan 各 Step 的執行紀錄）

1. **（8.6）全套第一次跑：2 failed／5,305 passed／2 skipped（33 分鐘），兩條都是 8.2（`523952cf`）帶進來的**——8.1–8.5 每一步的驗收只跑相關測試，
   結案的全套才抓到（gate 2 存在的理由）：
   - `tests/test_five_questions_shared_bet.py::test_the_meta_carries_the_one_copy_and_app_js_keeps_none`：新框架的「系統裡的它」把三個塊名寫死在前端
     （B3「營收從哪來」、B5「事件與影響多大」、B9「會不會死」）——塊名的唯一一份在 `page_schema`、經 `.meta.json` 給前端（L16）。
     修法：`app.js` 加 `blockTitle(key)` 照合約取名（同 `lampNames` 的做法；讀不到合約就不印標題，不在前端留第二份），三處改用它。
     測試一字未改；修前紅、修後綠。畫面上三個標題照樣印出（gate 3 的 dump-dom 逐字數到）。
   - `tests/test_stock_page_s5b_charts.py::test_diagrams_show_as_images_in_b4_and_on_the_layer_page_labelled_as_illustration`：8.2 把 B4 的示意圖抽成
     新舊兩版共用的 `pageDiagrams`，行為沒變，測試還在 `blockVisuals` 裡找字。修法：斷言照留、主詞改成共用的函式（同 8.4a 的先例）。
2. **（8.6）換版讓下游的帳過期，這次撞到四本**：敘事一換版，短故事、賭注句、故事頁、事實錨點都跟著過期，各有 ⑤ 一格點名（沒有靜默）。
   8.5 對了短故事、故事頁、錨點，**漏了賭注句**：結案時讀 ⑤ 才發現「賭注句還沒寫」的「敘事換版」是 AEHR 與亞泰（兩檔的賭注句綁在 11-23 那一版）。
   兩檔賭注句引用的反證（AEHR 第 1 條、亞泰第 2 條）在新版逐字相同，照原文綁到新版（`stories --bet-only`），沒改字；重物化後候選板上兩檔不再是「敘事換版」。
3. **（8.5）自己寫的反證與加碼條件每次換版都換新 watch 編號**，重述也一樣；連到讀圖的反證與日期等待才保留編號。故事頁的 `waits` 因此要重對號：
   8.5 裡亞泰對了一次、AEHR 兩次。現在三頁掛在「這一版敘事自己登記」的列：**AEHR 14／14、亞泰 12／13、Sivers 3／13**（Sivers 的反證多半連讀圖）——
   下一次換版，這 29 列都要重對。對號照 watch 來源上的 `brief:<id>#<第幾條>` 走、不手抄；`story-page gaps` 會點名沒對上的。→ §5 #4。
4. **（8.5）判完醒來的等待，候選板跟著變**：亞泰換版被 26 條醒來的等待擋住（台光電 11-26 受邀法說的重訊叫醒的），逐條判無關、放回去續等。
   這 26 條掛在玻纖布、石英布、高速基板、銅箔、含浸機、壓合機等讀圖與六份敘事上；重物化候選板後「可開」15 → 19——多出亞泰、台玻 1802、富喬 1815、
   菲利华 300395.SZ，早上 daily 時它們是「前提失效」（31 → 27）。這是判讀的結果，不是規則變了。
5. **（8.5）SIVE.ST 的「裁決點過了」是對的**：何時格的文字還寫 11-26（報告延到 11-30），8.5 只把日期等待改到 11-30、沒改文字，
   所以 ⑤「敘事該重寫」點名它。結案時不重述：11-30 報告出來還要再換一次版，兩次換版會讓這一頁的等待重對號兩次（第 3 條）——等報告出來一起換。
6. **（8.5）L11-5 更正**：11-26 寫「三頁的暫存夾已經不在」是錯的——一直在本機暫存區（以 session 編號為名），11-27 搬進私有區；
   決定紀錄 §9.4、漏題帳、stock-story skill 各接一條更正。
7. **（8.5）綁錨點核出兩處字**：Aehr 新聞稿寫的是「預計出貨與安裝」，敘事寫成已裝好；「有兩個反例要看」改成「要看下面的反例」——重述一次。
8. **（8.5）疊字量到 53 對，全在照搬的手繪圖上**：都是上下兩行的字框擦到（50 對 0.5 px、3 對 1.2–2.4 px），截圖看墨跡沒碰到。
   量法不改（APP 自己畫的圖照舊 0 才算過），手繪圖照發布的樣子不動。
9. **（8.2）R2 抓到 Python 3.14 的 `html.parser` 把 `title` 當 RCDATA**：`<svg><title><script>` 寫入與物化兩道都放行、第三道擋住；
   當下修（檢查器照瀏覽器讀、svg 的 title／desc 只放字），變異證明兩道各自擋得住。
10. **（8.2）只留在舊版個股頁的五樣**：需求錨的四張圖、吃到多少、各格的依據（原文）、各塊標題、會不會死那一行摘要（四盞燈全句新版已有）。→ §5 #1。
11. **（8.4b）兩條測試拿掉機制照綠**（避讓與換行的案例沒撞到）——改到拿掉機制會紅才算數。
12. **（8.6）長駐 APP 的重啟方式**：8.5 重啟的 serve 是掛在 session 背景任務底下的行程（背景任務有時限）。8.6 改成照開機腳本的方式
    （repo 根目錄、隱藏視窗、不等待）另起一個獨立行程；`/api/v1/health` 的 `code.stale=false`。
13. 其餘小偏差（白名單多收畫箭頭用的 SVG 屬性、註解與 CDATA 一律拒收、`#/old/<代號>` 路由、片段 id 加 `sp-` 前綴、對帳每項帶 `since`、
    共用的複製按鈕與頁面現況）都在 plan 各 Step 的執行紀錄。

## 5. 要你決定的事

1. **舊版個股頁的程式什麼時候刪**（plan §0 第 11 條：結案之後你決定）。現在新版頁尾有連結到 `#/old/<代號>`，舊版只多五樣（§4 第 10 條）。
   ①**先留著**，等你在手機上用新版讀完三頁、逐樣說要不要，要的搬進「系統裡的它」再刪（推薦——五樣有沒有你會想念的，只有你讀過才知道）；
   ②現在就把五樣搬進新版、刪舊版；③現在刪、五樣不要。
2. **故事頁的股價圖要不要改成物化時重畫**。現在是寫的時候畫好、圖上寫明畫到哪一天；「系統裡的它」另有今天的股價圖。
   ①**維持寫的時候畫**（推薦——頁上的圖是寫那天的脈絡，今天的價格已在系統那一段）；②物化時重畫（片段要多一個空位、物化多一步，契約加法）。
3. **下一檔做哪一檔**——由你點名（AGENTS：哪一檔要做深由使用者點名，系統不排序）。現況：已持有 2 檔裡 COHR 還沒有故事頁；可開 19 檔裡 17 檔還沒有。
   點名之後照「做深 <代號>」走偵探 → 故事頁，一次寫到交稿。
4. **（開發候選，未排程）換版時自己寫的反證與加碼條件，條件逐字相同就沿用原本的 watch 編號**（現在是收舊開新）。真實案例：8.5 一天內重對號三次
   （亞泰一次、AEHR 兩次）；三頁 40 列裡 29 列會在下一次換版時再對一次（§4 第 3 條）。不改也不會漏（`story-page gaps` 會點名），
   只是每次換版多一步、多一次手誤的機會。要排就進 ROADMAP；不自己排。

**照帶（研究，下一次 drain 或做深時處理，不需要你決定）：**
- Sivers 3 條醒了待判（11-23 LITE、META 的 8-K）；11-30 第三季報告出來後換版並改何時格（§4 第 5 條）。SIVE.ST（已持有）的賭注句從沒寫過。
- 亞泰 8 句媒體引文只見過搜尋摘要、原文沒存（W6，網路級）：下次做深補原文或拿掉引號；48 句事實句還沒錨點是換版前的舊帳。
- 漏題帳的前向列（三頁現行版）要等你讀過才填。

## 6. 你的動作（不擋結案）

- 在手機上開 APP 個股頁 AEHR、SIVE.ST、6727 從頭讀一次，讀後問的問題記進漏題帳（前向冷讀那三列跟著填）；想對照舊版走頁尾的連結。

## 7. 結案 R2（已常規 opt-in）

（審查中——乾淨 context、唯讀；WORK_REQUEST 照 plan §3 Step 8.6。結果與處置寫在這一節。）
