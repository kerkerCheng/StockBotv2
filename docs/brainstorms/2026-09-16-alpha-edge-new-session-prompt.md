# 給新 session 的啟動 prompt（2026-09-17 改寫；原 2026-09-16 版見文末歷程）

> 用法：在新的 Claude Code session 貼「開工指令」那一段，或直接
> `@docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`。
>
> ⚠ **本檔的狀態句會腐壞**（`AGENTS.md`「現況數字會過期，判準不會」）。
> 每句現況都附了查證命令，**引用前先跑那一條**。進度的唯一權威是
> [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表與 `library/leads/todo_pool.json`，不是本檔。

---

## 開工指令（貼這一段）

> ## ⚠ 2026-09-18 收尾狀態（先讀這塊，再讀下面的任務書）
>
> **這一輪做完的：** ①**AXTI 的 InP 賭注已寫下**（`bet_state` 由 `unanswered` → `bet`，籃子的 `bet` 由 1 → 2）；
> ②**Phase 3 交付**（D5 帳號登記表＋計分表＋每月花費上限），ROADMAP 標 ▶ 不標 ✅。
>
> **⚠ 寫賭注之前先撞到的事（比賭注本身重要）：base 的四格 carried_forward 全部被 Q2 10-Q 推翻，而且四格同向樂觀。**
> base 六格寫於 2026-09-10，證據只有 FY2025 10-K——但 Q2 10-Q 在 **2026-08-13** 就 filed 了。
> 稀釋股數 43,933 千股（實際 1H 加權 59,642／Q2 單季 63,474）、稅率 0（實際 1H 17.99%）、
> NCI +1,942（實際是 **扣減** 2,037，方向相反）、非營業淨額全年 432（1H 已經 5,239）。
> 第五格 `operating_margin_delta` 是**由共識 EPS 逆推**的，而逆推用了錯的股數——
> **base 的 thesis 逐字寫著「共識要求營益率變成 +16.4%」，真正的數字是 +24.70%。**
> 七筆已全部 append（五筆 supersede ＋ 兩筆 variant），另補一筆 `interim_period_results`
> 當 authority 載體（mechanical，不需 pq2）。查證：`python -m alpha assumptions AXTI`。
>
> **賭注的內容（payoff 是負的，那是誠實的結果）：** 共識 FY2026 營收 218M 要求 2H 做 143.5M（Q3／Q4 各比 Q2 再 +50%），
> 而 Q2 的 47.6M 是在**對美國出口許可還沒拿到**的情況下做出來的，10-K 逐字說美國是 InP 的主要營收來源，
> Q2 10-Q 逐字說 'we cannot predict when a permit application will be reviewed and approved'。
> variant 的情境是「2H 不出現新催化劑」：營收 +92.1%（vs 共識 +146.8%）、營益率 delta +40.4pp。
> **每股約 US$47，對現價 US$64.30 是 −26.96%**（橋算的與手算一致）。`passes_filter` false、`filter_reasons` `payoff_not_positive`。
> ⚠ **這不是「賭它跌」，是把共識沒寫出來的那個前提拿掉之後值多少。** 首屏短評七格已寫（`python -m alpha brief AXTI --list`）。
>
> ⚠ **差點寫錯的賭注：** 一開始傾向寫「漲價落到毛利」，但自家 Engine C 的 `gross_margin_trend` 觀測逐字擋下了——
> ASP 貢獻**未經一手證實**（Nomura 報告仍是 tier-3 隔離），而一手數據支持的是稼動率解釋
> （營收 +164.8% 對銷貨成本 +58.5%），且 AXT 毛利率是強週期序列（2022 Q3 已達 42.0%，四季內崩到 10.7%）。
> **自家 ledger 擋下了一個本來會很好聽的故事。**
>
> **Phase 3 的實測（第一次量測就有結論）：**
>
> | | 全部點名 | 每檔只算最早一次 |
> |---|---|---|
> | 點名後 30 天 vs QQQ | −2.03%（n=617） | **−9.14%**（n=38） |
> | 點名後 30 天 vs SOXX | +3.06%（n=617） | **+2.14%**（n=38） |
> | 點名前 30 天漲幅 | −2.28% | **−5.61%** |
>
> **兩個基準給出相反符號**——只印 QQQ 會得到「這帳號沒用」，只印 SOXX 會得到「這帳號有 alpha」，兩個都是錯的。
> 追源成功率 37.59%（n=439）、no-go 率 64.63%（n=492）。**點名前是負的＝不是追高。**
> 90 天與假設命中率誠實宣告沒有值（`insufficient_sample`／`capability_absent`），**不填 0**。
> 計畫與 sandbox review 五步見 [`2026-09-17-alpha-edge-phase3-plan.md`](2026-09-17-alpha-edge-phase3-plan.md)。
>
> **開工第一件事仍然是確認昨夜 daily 沒死**（`python scripts/writer_guard.py check` ＋心跳第 1 段）。
> ⚠ 2026-09-17 實測：鎖是 null（已釋放），但 **daily 仍然沒跑成**（`daily_done_today` false），
> harvest 最後一輪停在前一天，已由互動 session 補跑（0 筆新 lead，總計 1101）。
> ⚠ **心跳排程的第一次真正自動觸發是 2026-09-18 07:00，不是 09-17**——
> 任務的 Start Date 是 09-17，但當天 07:00 時它還沒註冊，`Last Run Time` 09:45 那次是 `schtasks /Run` 手動走排程路徑。
> 所以 Phase 2 的「連續 3 天心跳」最早 **2026-09-20** 驗得完（09-18／19／20）。
> 查證：`schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V`（看 `Next Run Time` 與 `Last Result`）。
>
> **待使用者決定（本輪掛號，不自行推進）：**
> **[600]** AXTI thesis 的 disproof 更新為 variant 的三條可觀測條件（**thesis mutation gate**）。
> **[601]** `mat:inp_substrate` 讀圖的 disproof ④ 要重看——**AXT 自己已募 US$600.1M 專款擴 InP 產能**
> （2026-04-22 交割，用途逐字寫明），讀圖沒記這件事。它不推翻 volume 判定，但讓「產能補不上」**有了到期日**。
> 另有一個**要改 ROADMAP Phase 定義**的：Phase 3 驗收行寫「5 欄有值」，
> 而決定紀錄 §6 自己逐字寫著「算不回來的：假設命中率」——**兩者自相矛盾**，修驗收行要先給五欄 amendment。
>
> **不需核准就能接著做的：** Phase 6（台股月營收、MOPS 重訊 watcher、parked lead 到期）；
> Phase 4 剩下的兩條機械條件**仍然不該做**（實測會讓 0 家變 0 家，改不到 binding constraint）。
> ⚠ **binding constraint 沒有變**：籃子 16 檔現在 `bet` 2、`unanswered` 14——
> 能讓籃子非空的還是只有兩條路，兩條都要人：替某一檔寫賭注，或寫一筆 Abstention。
>
> <details><summary>上一輪（2026-09-17 晚）的收尾狀態</summary>
>
> ~~## ⚠ 2026-09-17（晚）收尾狀態（先讀這塊，再讀下面的任務書）
>
> **這一輪做完的：** Q2 ✅｜Q5 ✅｜Q1 ✅（三件都已合併 master 並 push）。外加開工時修掉的一個
> **真的壞掉的 daily**，與四個當下修的靜默缺陷。
>
> | | 決定 | 狀態 |
> |---|---|---|
> | **Q2** 籃子每列強制「有賭注 或 Abstention」 | A | ✅ 交付（commit `b43d28f`） |
> | **Q5** 讀圖落地 append-only ＋ staleness 分級 ＋ 掛心跳與 pq1 | A | ✅ 交付（commit `527d61c`） |
> | **Q1** 籃子宇宙擴到被門檻擋下的 26 條，分兩個分頁 | A | ✅ 交付（同上） |
> | Q3 量的賭注的反向橋 | B：留 Phase 7 | — |
> | **Q4** 結構讀圖（零 LLM 查詢） | A | ✅ 已交付 `python -m query.structure <node>` |
>
> **⚠ 開工第一件事（這一輪學到的）：先確認昨夜 daily 真的跑完了。**
> 2026-09-17 早上那輪在第一步就 fail closed：**前一晚的互動 session 持有 writer lock 沒 release**
> （acquire 在 `crons/harvest_leads.py`，release 在 `scripts/publish_daily_state.py`——互動側手跑
> harvest 沒有對應的 release），daily 撞上它、依 runbook 整輪中止，於是 harvest 與 APP materialize
> 整天沒跑。系統行為是**對的**（fail closed），壞的是沒被釋放的鎖。
> 查證：`python scripts/writer_guard.py check`（`writer_lock` 應為 null）＋看心跳第 1 段。
> ⚠ **手跑過 harvest 就要自己 `python scripts/writer_guard.py release`**——我在同一天又犯了一次。
>
> **最要緊的量測（Q1 與 Q2 互相印證，它決定下一步該做什麼）：**
> 護城河籃子 16 檔 **15 檔卡在 `no_bet`**；擴大宇宙後的量的候選 12 家，真正新出現、已在出貨、
> 有需求錨的只有 **2 家（3081.TWO 聯亞、SHA0.DE）**，而它們唯一被擋的理由**還是 `no_bet`**。
> ⚠ **所以 Phase 4 剩下的兩條機械條件（覆蓋厚薄、瓶頸業務占營收）現在不該做**——
> 實測加上它們會讓 0 家變 0 家，改不到 binding constraint（L14-5）。
> **binding constraint 已經移到使用者那一側：有沒有人願意替這些檔寫下一個帶 disproof 的賭注。**
>
> **[595][596][597][599] 全部 go 並結案**（2026-09-17）——**Q5 設計的完整閉環已在真資料上走完一圈：**
> 寫讀圖（`undecided`，指出缺哪一格）→ 研究補那一格 → 入圖 → **機制自動偵測到讀圖與圖不再一致並分級 high**
> → 落 pq1 段 → 心跳現形 → 重讀改判 → 回到 `current`。中間沒有任何一步靠人記得，偵測那一段是零 LLM 的。
>
> **兩份讀圖的結論（下一輪要寫賭注時直接用得上）：**
> ①`tech:cw_dfb_laser` → **volume**。供給側分布實測 5／3／3／2／2／2（不是提案時以為的「全 2–3」）；
> Coherent 那個 5 的 evidence 是 `self_reported`，依 L8 不足以支撐 A 型判準。
> ⚠ 真正更卡的在下一層：它 `depends_on mat:inp_substrate` 是 5。
> ②`mat:inp_substrate` → **volume**（由 undecided 改判）。需求側 15 條裡 7 條 sub=5、2 條 sub=4，
> 且**下一層 0 條——它是最底層、所有人都繞不過**；供給側補完是 **3／3／3**，三家彼此可替代。
> **繞不過 ＋ 沒有人獨佔 ＝ 量的賭注。**
>
> ⚠ **護城河確實存在，但在另一層**：`axt→coherent`=4、`axt→lumentum`=4、`sumitomo→lumentum`=4
> 問的是「這個客戶換不換得掉這家供應商」。材料層 3、客戶關係層 4，兩者並存不矛盾——
> **買這個賭注買的是量，不是誰的護城河。**
>
> ⚠ **真正讓它成為賭注的，是 substitutability 沒有承載也不該承載的那一半**：三家產能同時補不上
> （住友飽和、AXT 近滿載且被中國出口管制卡、JX 無擴產、6 吋 InP 均價漲 250% 到 $5,000）。
> **可替代但補不上**——DRAM 2017、ABF 載板 2021、貨櫃航運 2021 的形狀。這正是 zoom-out §4 說
> 「2–10 倍不需要護城河」的那一類，而現行門檻 4 按設計會把它濾掉。
>
> **入圖的 before → after（[597]）：可投資排序 37 → 37，一列都沒動**（3 低於門檻 4）。
> 變的是 `substitutability_unfilled` 159 → 156、`below_threshold` 26 → 29——**那三條從「沒人研究過」
> 變成「已研究、答案是否定的」，而這兩件事的下一步完全相反**。量的候選 12 → 15 家，
> 但真正新出現的公司只有 5016.T（JX）一家。
>
> **下一輪的兩件事，使用者 2026-09-17 已明確核准「1 2 都做」，不必再請 `go`：**
>
> **① 寫 InP 那個賭注**（研究；binding constraint 一整天沒動過，就在這一格）。
> **建議寫 AXTI**：純 InP 基板玩家（住友與 JX 都是大集團的一小塊）、已在籃子第 8、> **base 那條鏈已經完整**（8 筆 OperatingAssumption，readiness `ready_with_flags`），> 缺的就是 variant 那一筆——寫下去 `bet_state` 立刻由 `unanswered` 變 `bet`。
> ⚠ **寫之前先讀這個數字**：AXTI 的 FY2026 共識營收成長是 **+146.8%（2.47 倍）、只有 5 位分析師**（`oa_a3a830fcb093bf2a` 的 rationale 逐字寫著「本輪所有標的中最激進的共識」）。**市場已經在定價需求會來了**——所以賭注不能是「AI 需求會爆」，那不是差異化觀點。要說出比共識更多的東西才算賭注：漲價能持續多久、出口許可什麼時候鬆、產能釋放的時點、或者反過來賭共識過高。**寫得出差異在哪，才寫得出 payoff。**
> 命令：`python -m alpha assumptions AXTI --add spec.json`，spec 帶 `"scenario": "variant"`（不帶就是 base）。variant 是 **overlay**：只寫有差異的 driver，其餘沿用 base 的生效假設。
> 寫完跑 `python -m webapp materialize AXTI --basket` 看 payoff 與 `bet_state`。
> ⚠ 依 L7，賭注要配一條帶「核查頻率＋觸發後 48 小時動作」的 disproof；`mat:inp_substrate` 的讀圖 `sr_81832cb37d87ab1d` 已經寫好五條，其中三條是 `query.structure` 每天自動比對的，直接引用。
> ⚠ 如果研究到一半發現寫不出可辯護的賭注——**那也是答案**：寫一筆 `bet/variant.overlay` 的 Abstention（`python -m alpha abstention AXTI --add spec.json`），`bet_state` 會變 `abstained`。**兩者都是終局，只有空白不是。**
>
> **② Phase 3（D5 帳號登記表與計分表）**（開發；ROADMAP Phase 3 那一列已定義到可直接執行）。
> 它是漏斗最上游的「誰值得進佇列」，與寫賭注那條路互不阻塞。
>
> **順序建議：先 ①**（它是這條研究線的收口，而且一旦寫下賭注，籃子第一次會有第二個 `bet`）；
> ①做完或誠實 park 之後接 ②。**兩件之間不需要回來問。**
>
> **仍要停下來的（不因這次授權放寬）：** 四個人工 gate（入圖／Engine C 判讀寫入／thesis mutation／live）、資本動作、要改 `AGENTS.md` 判準句或 ROADMAP 的 Phase 定義、Verdict 不是 GO。
> 撞到就掛號、接著做下一件不需核准的事，收尾一次給批次指令。
>
> 池裡的 [598]（穩懋補獨立來源）是 collector 自動鑄的，不在這兩件事的線上。
>
> **兩個已知缺陷，刻意沒在本輪修（都動到既有契約，值得一個 Z2 proposal）：**
> ①**writer lock 的 owner 程序死了仍卡到 TTL**——今早 daily 死掉的直接原因；鎖已記了 pid／hostname，
> 「同機器且 pid 不存在就可接手」是可機械驗證的補償控制，但它改的是一道安全機制的判準。
> ②**`_read_abstentions` 讀取失敗回 `[]`**，而它自己的 docstring 寫著「不得因為讀取失敗而把
> 『刻意不主張』降級成『還沒寫』」——實作與註解相反，且現在有三個消費端。
>
> ⚠ **Phase 2 尚未完成**：驗收要「連續 3 天心跳零 LLM 成功發出」，**最早 2026-09-20 才驗得完**。
> 查證：`schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V`（看 Last Run Time 與 Last Result）。
> ⚠ 明天 07:00 是**第一次真正的自動觸發**（今天那次是 `schtasks /Run` 手動走排程路徑）。
>
> <details><summary>上一輪（2026-09-17 早）的收尾狀態</summary>
>
> ~~## ⚠ 2026-09-17 收尾狀態（先讀這塊，再讀下面的任務書）
>
> **這一輪做完的：** Phase 1 Step 1.3 收尾｜Phase 2 Step 2.1（心跳產生器）＋ 2.2（接上獨立 Windows 排程
> `StockBotv2-Heartbeat` 每日 07:00、`drain_limit_per_run` 5→0、`.codex/rules` 20→15）｜
> pq2 [587]–[590] 四項研究＋[591][594] 入圖｜`rank_bottlenecks()` 補上 INV-3 的 filtered 報表。
>
> **Q1–Q5 使用者已於 2026-09-17 全部照建議核准。下一輪直接開工，不必再問。**
>
> | | 決定 | 狀態 |
> |---|---|---|
> | **Q2** 籃子每列強制「有賭注 或 Abstention」，不准空白 | A | ○ **下一輪第一件** |
> | **Q5** 讀圖落地 append-only ＋ staleness 分級 ＋ 掛心跳與 pq1 | A | ○ 接著做 |
> | **Q1** 籃子宇宙擴到被門檻擋下的那 26 條，分兩個分頁 | A | ○ 排 Q2／Q5 之後 |
> | Q3 量的賭注的反向橋 | B：留 Phase 7 | — |
> | **Q4** 結構讀圖（零 LLM 查詢） | A | ✅ **已交付** `python -m query.structure <node>` |
>
> **為什麼 Q2 排第一（實測，不是偏好）：** 籃子 16 檔**沒有一檔**因 substitutability 被擋，
> **15 檔卡在 `no_bet`**——開別的門、擴別的宇宙，如果進來的東西一樣沒人寫賭注，籃子還是空的。
>
> **Q5 的設計已經寫完了，直接照做**（見 structural-reading-layer.md §5b／§6b）：
> 存輸入不存結論、staleness 分級（`documents` 計數變動不得觸發）、
> 落點是 pq1 新段不是心跳、必須有到期、**staleness 直接接既有 disproof 機制不另立通知路徑**。
>
> §2e 未做完清單裡 [586] 已設 pending（等外部文件），其餘已結案。
>
> **兩份必讀的新文件：**
> [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md)（為什麼籃子空的真正原因）
> 與 [`2026-09-17-structural-reading-layer.md`](2026-09-17-structural-reading-layer.md)（瓶頸性不是一條邊）。
>
> ⚠ **Phase 2 尚未完成**：驗收要「連續 3 天心跳零 LLM 成功發出」，**最早 2026-09-20 才驗得完**。
> 查證：`schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V`（看 Last Run Time 與 Last Result）。
> </details>
> </details>

~~**任務：Q2 →（Q5）→（Q1），三件都已核准。**~~（2026-09-17 晚全部交付，見上方收尾狀態）

**下一輪的任務：使用者未指定時，先問一句「要不要開始寫賭注」，不要自己往 Phase 4 剩下的條件做。**
理由是量測不是偏好：兩個宇宙加起來 28 檔候選，**26 檔卡在 `no_bet`**；
Phase 4 剩下的兩條機械條件（覆蓋厚薄、瓶頸業務占營收）實測會讓 0 家變 0 家（L14-5：改不到 binding constraint）。
**能讓籃子非空的只有兩條路，兩條都要人：**①替某一檔寫下帶 disproof 的賭注；
②寫一筆 `bet/variant.overlay` 的 Abstention 說「這一檔今天沒有可辯護的賭注」——
**兩者都是答案，只有空白不是**（Q2 的全部意義）。

不需要使用者決定就能做的（依序）：**Phase 3（D5 帳號登記表與計分表）**——它是漏斗最上游的
「誰值得進佇列」，與賭注那條路互不阻塞；Phase 6（台股月營收、MOPS 重訊 watcher、parked lead 到期）。
⚠ Phase 2 的驗收（連續 3 天心跳）最早 2026-09-20，那是等時間不是等工作。
**先讀（順序固定；這一輪需要的全部在這裡，沒有第七份）：**

| # | 檔案 | 為什麼這一輪需要它 |
|---|---|---|
| 1 | `AGENTS.md` | 憲法、六條 invariant、四個人工 gate、L1–L17（一字不動）。⚠ 尤其「Alpha 呈現契約」與 L7（disproof 三件套）——Q2 直接動到它們 |
| 2 | [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md) | **Q2／Q1 的全部依據**。籃子為什麼空的量測、A／B 兩種賭注、三條「改掉 substitutability」為什麼都是錯的 |
| 3 | [`2026-09-17-structural-reading-layer.md`](2026-09-17-structural-reading-layer.md) | **Q5 的完整設計**，§5b（存輸入不存結論）與 §6b（怎麼 trigger 重新推理）**照做即可，不要重新設計** |
| 4 | [`docs/ROADMAP.md`](../ROADMAP.md) | **進度與驗收的唯一權威**。Phase 4 那一列（Q1／Q2 要改它的定義欄，需先給五欄 amendment）、Phase 2 那一列、completion gate 八項 |
| 5 | [`2026-09-16-alpha-edge-discovery-requirements.md`](2026-09-16-alpha-edge-discovery-requirements.md) | **決定紀錄 D0–D15**（使用者原話）。⚠ Q2 動到 D2（賭注與「判斷錯了值多少」對稱）、D3（`realized` 只提醒）、D15（power-law 統計量） |
| 6 | `docs/AGENT_WORKFLOW.md` ＋ `skills/development-flow/SKILL.md` | Zoom／Review 判定與八欄交付格式。Q2 改籃子契約，**至少 Z2** |

**只在需要時才讀（不必一開始載入）：**

| 檔案 | 什麼時候 |
|---|---|
| [`2026-09-16-alpha-edge-phase1-plan.md`](2026-09-16-alpha-edge-phase1-plan.md) | 要查 Phase 1 做過什麼、§2e／§2f 六項的處置結果 |
| [`2026-09-17-alpha-edge-phase2-plan.md`](2026-09-17-alpha-edge-phase2-plan.md) | 要查心跳怎麼來的、Step 2.3（分類層）還沒做什麼 |
| `docs/OPERATIONS.md` | 要實際跑操作時（「心跳」節、「Daily / pq1 / 待辦池的參數」節） |
| `docs/ARCHITECTURE.md` §4.1／§8 | 要動 Daily 三層或 APP 呈現時 |

⚠ **本輪不必讀的**：其餘 15 份 brainstorm 都是 2026-07～08 的舊題目（confidence 五軸、capital expression、
event watch…），與 Alpha Edge 無關。**Alpha Edge 只有上面列的 6 份 brainstorm ＋ ROADMAP。**

~~**Step 1.3 要做的四件：**~~（2026-09-17 全部完成，見 ROADMAP 與計畫檔 §2d／§2e；以下留作歷程）

1. **ROADMAP Phase 1 驗收行回填 before → after 實測值。** 舊句劃線加日期留原地，不靜默刪除。
   四個 Step 的實測值都在計畫檔 §2／§2b／§2c，但**回填前先自己跑一次查證命令**，不要抄現成數字。
2. **Phase completion gate 八項逐項核對**（ROADMAP「每個 Phase 的 completion gate」），
   每項寫「過／不過＋依據」。第 8 項（該 Phase 負責的 critical historical failure 已有 executable protection）
   要對照 `docs/refactor/historical-failure-matrix.md` §9 的責任分配。
3. **標記 Phase 1 狀態。** ⚠ **驗收行明訂：可投資排序的 TW／TWO／ST 檔數仍為 0 就不得標完成**——
   2026-09-17 實測確實是 0。所以只能標「**研究已做、證據不足以進榜**」並**逐項列出缺哪份文件**，
   **不得為了讓籃子非空而放寬門檻 4**（`AGENTS.md`：籃子空就空，讓它非空的路是研究）。
4. **決定 §2c「未做完清單」四件的去向**（併入 Phase 4 篩選層，或另立 pq2）。這四件需要使用者判斷，
   所以**交回 Step 1.3 結果時把它們列成待決問題，停下等使用者**——不要自己決定。

**Step 1.3 完成後，沒有待使用者決定的事就直接接著做 Phase 2，不要停下來問。**
（2026-09-17 使用者定案，`AGENTS.md` 常規推進授權已擴大到 Phase 邊界：**Phase 做完不是停止理由**。）
Phase 2 是 D12 心跳＋分類——改排程、`drain_limit_per_run` 歸零、Codex fixed entry 與 permission test
同 change 對齊。它動到 unattended surface，所以**必出 `PLAN_PROPOSAL` 並同 change 做 sandbox impact
review 五步**；但 **plan 是思考紀律不是核准請求**——plan 裡若沒有需要使用者選的問題（ROADMAP Phase 2
那一列已定義到可直接執行），照出 plan 然後往下做。

**真正要停下來等人的只有這些：** 四個人工 gate（graph admission／Engine C 判讀寫入／thesis mutation／
live）、資本或任何 append-only authority、要改 `AGENTS.md` 判準句或 ROADMAP 的 Phase／Step 定義、
需要 R2、Verdict 不是 `GO`、或 plan 裡真有要使用者選的問題。
⚠ **撞到 pq2 就掛號繼續做下一件不需核准的事**，收尾一次給批次指令——**不得停在編號上等**。

**不得做：** 部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、因籃子空而放寬篩選條件、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯。

**收尾格式：** HUMAN SUMMARY（5–10 行）＋ 八欄 `STEP_RESULT`；有待使用者決定的事，
決策區塊放最前面（格式見 `skills/daily-brief/SKILL.md`「待核准項目的內容密度」）。

---

## 現況與查證命令（引用前先跑）

| 現況（2026-09-17 實測） | 查證命令 |
|---|---|
| 可投資排序 37 列／17 家；TW／TWO／ST **0 檔**；IQE.L 第 9 | `python -m query.bottleneck --top-n 60` |
| `audit invariants` FAIL 0／PASS 13（4,087 筆） | `python -m audit invariants` |
| 全套 pytest 2,481 passed／1 skipped | `python -m pytest -q` |
| 待辦池無本 Phase 未決編號 | `python -m engine_b.todo list` |
| `.ST`／`.L` 各 5 條路由，rung2 的 `mfn`／`rns` 皆 `verified=true` | `python -m sourcing.routes SIVE.ST` |
| canonical 邊 529 條、materialized 屬性 358 個 | `python -m loader.edge_resolution project --dry-run` |
| 七家有 `product_line_revenue_share`（AEHR 缺） | `python -m engine_c.set_manual_field --list 3081.TWO` |

## Phase 1 已完成的四個 Step（細節在計畫檔，不在這裡展開）

- **1.0** 公司名稱解析歸位——排序的證據分級改讀 registry 真有的 `display_name`（改判 39 條邊）
- **1.1** `fetchers/mfn.py`＋`fetchers/rns.py`＋`.ST`／`.L` 路由階＋三條管道各一份 smoke 文件
- **1.2** D8 補三格：七家產品線營收占比、四條新供應邊、聯亞 `substitutability`=3；
  Tower 自家公告補 IQE 的客戶端外部印證（IQE.L 第 12 → 第 9）
- **兩個當下修掉的靜默缺陷：** MOPS 的 PDF 吐出 CJK 相容表意文字害逐字比對失敗（`fetchers/mops.py` 加 NFC 正規化）；
  publish preflight 把 supersede 走廊的正常改寫當成「別的 writer 動過」而擋死六筆已核准的入圖
  （`intake/publish.py` 把兩種語意分開）

## Phase 1 的核心發現（Step 1.3 要如實寫進 ROADMAP）

**補完格之後排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的 substitutability
全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：**各家在自家年報裡逐字
互相具名指認對方是同層競爭者**（全新點名聯亞與 IQE、英特磊點名全新與 IQE、聯亞點名英特磊與 IQE）。
證據方向一致指向「多家並存的量產供應層」。

---

## 歷程（舊狀態行，不靜默刪除）

> ~~**狀態（2026-09-16）：Step 0 已核准並合併進 master（branch `docs/alpha-edge-step0`）。**
> 新 session 照下面順序讀完文件後，**直接從「Step 1 以後」開始**：先出 Phase 1 的 PLAN_PROPOSAL（Z3），停下等核准。~~
>
> ~~**狀態（2026-09-16 21:30）：** Step 0 已合併；Phase 1 PLAN 已核准（決策 A go／B 選 1／C 選 1／D 選 2，
> 順序 1.0 → 1.1 → 1.2 → 1.3）；Step 1.0 已 GO 並合併 master（merge `d06f5bf`）。**從 Step 1.1 開工**。~~
>
> ~~**狀態（2026-09-17 早）：** Step 1.1 已 GO 並合併 master；三份 smoke 文件的 RA 已 prepare 為
> pq2 [579][580][581]，入圖待使用者批次 go。**從 Step 1.2 開工**。~~
>
> ~~**狀態（2026-09-17）：** Step 1.1 與 1.2 都已做完；六個 pq2 編號 [579][580][581][583][584][585]
> 等使用者批次 go。**從 Step 1.3 收尾開工。**~~
> （2026-09-17 使用者已批次 `go`，六筆全部 apply → push → `complete-ra` 結案；
> 本檔正文於同日改寫為從 Step 1.3 開工，上列狀態行改置於此。）
>
> ~~**狀態（2026-09-17 晚）：** 從 Step 1.3 收尾開工。~~
> （Step 1.3 同日完成：ROADMAP 驗收行回填、completion gate 八項逐項核對、Phase 1 維持 ▶ 不標 ✅、未做完清單擴為六項待使用者決定去向。**本檔正文改寫為從 Phase 2 開工。**）

**2026-09-16 原版正文（Step 0 任務書）已完成並封存**——去向清單見
[`docs/refactor/alpha-edge-step0-migration.md`](../refactor/alpha-edge-step0-migration.md)，
Phase 1 的核准計畫與工單見 [`2026-09-16-alpha-edge-phase1-plan.md`](2026-09-16-alpha-edge-phase1-plan.md)。
**不要重做 Step 0，也不要重做 Step 1.0／1.1／1.2。**

**常設授權（2026-09-16 使用者定案，仍有效）：** Step 的 Verdict 為 **GO** 且沒有待使用者決定的問題時，
**直接合併 master 並接續下一個 Step，不逐 Step 請核准**。仍要停：Verdict 非 GO、有待決問題、
動到四個人工 gate／資本／append-only authority、要改 `AGENTS.md` 判準句、需要 R2。
pq2 的圖寫入（`ra_admission`）與 Engine C 判讀寫入仍逐筆核准——研究段落收尾照常給批次指令。
