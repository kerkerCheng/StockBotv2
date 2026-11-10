# Phase 7 研究日誌

> **性質：append-only 的歷史紀錄。** 只在檔尾追加，不改、不刪舊行（同 [`cases.md`](cases.md)）。本檔不是狀態源：
> lead、pq2、watch、讀圖、敘事的現況只住各自的 registry 與 ledger；「接下來做什麼」看計畫檔 Step 7.1b 列出的命令。
>
> **來源（2026-10-21 搬移，plan amendment A7）：** 下面三段逐字搬自
> [`docs/plans/2026-10-04-001-research-phase7-research-edge-plan.md`](../../plans/2026-10-04-001-research-phase7-research-edge-plan.md)
> §0.5 進度表 Step 7.1 列的「狀態」格（git `26da3cd6`）。原格去掉頭尾空白後 23,125 字元、
> sha256 `ecd3bd8b019a3d4dc24c4b097dc981030ec18f4d048c6ec2c24cb4536129cec2`；
> 「○（」接上第一段、第二段、第三段的正文（各段標題下的那一行，中間不加任何字元）逐位等於原格。
> 搬移時沒有改任何一個字，原文裡的筆誤、刪除線與當時的判斷照留。
>
> **之後怎麼寫：** 每個研究 session 收尾在檔尾追加一段 `## YYYY-MM-DD（第 N 段）`：做了什麼、產出 id、
> 鑄了哪些 pq2 編號、撞到的 failure log 編號。不寫回計畫表格。

## 一、2026-10-07～2026-10-20 逐日紀錄（原 7.1 狀態格，逐字）

2026-10-07 已做：InP 磊晶等五份層說明＋個股頁 S4a／S4b〔偏差 #23〕；**積壓：triaged_go 清到 0**（第二批 53 則＋深挖 12 條，全部終局）；**S1：40 則全有裁決**（證實 14、未定 6 帶到期、不適用 13、價格型 7）；**O3** POET v2 敘事（不要）；入圖 [715][719][721][727][728] 與新層、鄰層讀圖 10 份新寫或換版（CDU 層改判 neither）；AI 生醫 B1 結案、延伸的中國創新藥授權鏈 decompose（[726]，上市公司層無候選，ew_0319 等掛牌）；X 帳號四個。****晚段（同日，第二個 session）已做**：①波若威 3163.TWO 第一份敘事 `ib_a35b0492e80432ee`（缺 X）②負錨點兩檔時光機頁→ 個股頁 schema **v1.0 凍結**（brainstorm §15：分得開的是「價」自家三年百分位與「錢」的自家毛利位置，B3 供給緊四件事方向相反——改讀法不改元素；新假說候選待使用者決定登不登記）③電工鋼、冷板、分歧管三層重讀並各登兩個條件 watch（電工鋼加寫「這一層沒有可投資的公司」；冷板的邊緣台廠不在圖上 → directed lead `lead_d9c78bb0aff0b8a882d925766c309410`）④段 5 七檔全部到終局（closure-gate open 7 → closed；5411.T 補供貨邊 → pq2 [729]）⑤走圖第 1 型兩層第一份讀圖（UHP 雷射 volume、6 吋 InP 產線 undecided）⑥FAU 同義節點合併鑄 pq2 [730]；failure log #41、#42。**同晚使用者 go [729][730][731] 已做**：[729] JFE 日本本廠 GOES 供貨邊入圖（`0b1c05e0`）→ 電工鋼層重讀 `sr_761bd010a662901a`（判讀不變）；[730] FAU 同義節點合併（`a5024b04`，備份後 apply，−1 節點、殘留 0）→ FAU 層重讀 `sr_aa0b79ad032a31c4`、波若威與上詮敘事換騎；[731] H13 預先登記（`8d8043df`）後在 H12 事件全集上測 → **削弱**（兩格同時在頂端的先崩較多、也更常翻倍；S4 rubric 不寫「週期頂點的形狀」，`docs/reports/phase7/replay-h13-priced-margin-top.md`）。**同晚第三段（/phase-run）已做**：①冷板層說明 v1 `ln_4211fda64a785417` → 冷板讀圖改判 neither（`sr_c2cae5b7616559ec`；NVIDIA 集中採購、Vera Rubin 點名四家〔媒體〕）；雙鴻是量產在位者但系統口徑非倍率（分析師 16 家）→ 三條供貨邊 pq2 [732]；邊緣大小的三家台廠只到開發 ②走圖「下一層 0 條」：IC 載板上游建層——低膨脹玻纖布（T-glass）入圖包 pq2 [733]（主供應商日東紡＝系統口徑邊緣；買方景碩年報寫玻纖布缺料、要找新供應商）＋case G1 登記＋層說明草稿 ③向你要文件 [734]（T-glass 供需與第二來源）、[735]（波若威／上詮 CPO 營收與平台）；failure log #43（名冊外判不了邊緣，過 gate）、#44。**同晚第四段（使用者 go [732][733]＋開發項「可以 做掉」；10-07 深夜到 10-08 凌晨）已做**：①入圖（名冊 6a5f3a52、intake 58853cc0、69372708）後五層重讀：冷板 neither `sr_3adc3c77f10b2f57`、分歧管 undecided `sr_fdf9a8accf11c760`、CDU neither `sr_f012559123e56bad`、IC 載板 volume `sr_312353108b9975b5`（供給側加景碩）、玻纖布 volume `sr_49dcdbd60da7b239`（這一層第一份；反證 2 條＋客戶端重讀 1 條登 watch）；玻纖布層說明 ledger `ln_3552bc3a00c18c0d`（T3、T4 登 watch；T1、T2 由讀圖條件盯）；讀圖被取代的三份敘事換騎（8996.TW、ATS.VI、009150.KS）②A6 交付：`python -m alpha edge`（1f209065；failure log #43）③名冊：「被點名未登記」117 用系統口徑分層（cashtag 85＝邊緣 15／非邊緣 57／量不到 10／ETF 3；人打字串 32 裡 11 個其實已登記）→ 名冊批次 pq2 [737]（邊緣且 lead 把它放在供給側的 10 家）；載板鏈主題等權組 [736]（6 檔；Ibiden、欣興、南電三筆名冊隨號 staged）；散熱組 v2 [738]（雙鴻入組——v1 的排除理由「不在名冊」不再成立）；lead 身分重算 22 則（failure log #13 第 2 次：Credo 晚了 5 天）。**同晚第五段（10-08 凌晨）已做**：①段 5 閉包 closed——JFE（5411.T，邊緣）抄入 FY2025 `runway_inputs`（mechanical，`mo_78680661787c7b5c0a361689eb0f7791`；會死嗎現金綠、負債黃）②層深讀（「下一層 0 條」：矽光子 PIC 層判量、上游沒接）：Photonics-SOI 層說明 v1 `ln_b3a788384542e760`——客戶說換不掉（GF 20-F：占 SOI 支出約 71%、換要很久，**不分光子**）、供應商說不缺（Soitec 低稼動率；競爭者 SEH、GlobalWafers）；S1–S4 登 watch → 讀圖換版 `sr_6707b77bd1a5958c`（仍 undecided）→ SOI.PA 敘事 `ib_01af87313ad148a5`（仍「缺」，X 縮成光子用 SOI 的客戶端一手）；failure log #46（入圖時的策展摘錄漏了同一份申報裡更強的客戶端段落）③走圖第 7 型「沒人供應」：分接開關層入圖包 pq2 [739]（華明裝備 002270.SZ，系統口徑邊緣；自述全球第二、分接開關毛利率 59.6%、出口 +45%；名冊隨包 staged）＋層說明草稿 v0；同時發現 10-05 對套管瓷件那句的撤回是錯的（PDF 文字層拆字，failure log #47；lead 與 cases P2 已附加更正）④國家實驗室 2026-05 報告（媒體轉述追回原文）入圖包 pq2 [740]：美國分接開關交期 80–90 週、Reinhausen 是美國唯一在產者、套管最長 130 週——缺貨受益者是 Reinhausen（私人）與 Hitachi Energy，華明不在美國這條線上。**10-08 早上（使用者「736 737 738 739 740 go」＋daily 三個問題）已做**：①名冊 +15（9800d618）→ lead 身分重算 12 則；對照組 [736] `tc_5061f2233f77a865`、[738] `tc_113e1c8eec9e00b6`；[739][740] apply → publish（9e617677、b32229a7）→ 結案；發布者名冊補登國家實驗室（[740] 包裡寫明它是第三方，當時漏 staged）②分接開關層說明 ledger `ln_0a3b60a33ecff0cf`（T1–T5 登 watch）＋第一份讀圖 `sr_8d94aadb859c3e65`（volume：美國交期 80–90 週，但受益者是 Reinhausen 與 Hitachi Energy）、套管層 `sr_92e8df93643eedad`（volume，沒有可投資的純供應商）、LPT 層重讀 `sr_d78aa6617c9eb00f`（判讀不變）③敘事：日東紡第一份 `ib_c8f278b954e90d5d`（缺：T-glass 份額與第二來源認證、已定價主參照）、華明第一份 `ib_5c26d7071cc7ae09`（缺：全球缺口流向它的一手、已定價主參照）④daily 短版三個修正（8d29b6a8；failure log #48、#49）。**10-08 上午（使用者「A；開 S2；九項都做一做吧」＋ API key 開口要）已做**：①[741] EDINET key、[742] OpenDART key 放進「向你要文件」那一區 ②開發批次（plan `docs/plans/2026-10-08-001-dev-phase7-batch-plan.md`）：failure log 九項（#1 #2 #3 #5 #14 #15 #17 #25 #26）全部做掉、名冊候選分層與批次登記 A、個股頁 S2（commits 6b402bdf、9ddd71e6、c2450229、bf667775、610ca7f7、623b8bfa、babb9a84、87daea8c；R2：D2 GO、D7 送審）③停放的等待對齊：「沒有任何機制會回來的停放」存量 145 → 0 ④名冊批次 pq2 [743]（MaxLinear、Ouster：系統口徑邊緣、lead 把它放在供給側）⑤failure log #50。**10-08 中午（使用者「743 go／APP 的開發 phase 再講一下／然後繼續」）已做**：①[743] complete → 名冊 +2（MaxLinear、Ouster；083c6b89）②段 5 閉環：日東紡 3110.T 抄入 `runway_inputs`（mechanical，`mo_a81ba9ad2b785204a47276233920582c`；FY2026/3 自由現金流 −32.22 億日圓、含租賃計息負債 492.68 億）→ 終局；新登記的 10 檔美國申報人補跑 Engine C 歷史回填（三題的自家歷史與營收序列原本全空）；11 檔「坐哪一層」短檢查全部到終局——①補供貨邊 5 檔鑄入圖包：[744] Ouster→光達、[745] MaxLinear→新層「光模組 DSP」（＋可插拔光模組相依）、[746] Hammond→新層「乾式變壓器」（刻意不連 AI 錨）、[747] Munters→CDU、[748] AAON→CDU；②開發中寫「不要」＋反證 watch 3 檔（Navitas、Power Integrations、LPKF）；③不坐任何層寫「不要」2 檔（EnerSys、Vishay）；K&S 寫「缺 X」（打線機單季年增 197.5%，需求來源是 AI 還是中國一般擴產；ew_0580）→ 進母體、讀圖卡點 → 入圖包 [749]（新層「打線設備」＋先進封裝層）；節錄 6 份進 library/raw ③failure log #51 當下修（029e947d：①掛 pq2 後不再被列成可推進，open 11 → 1〔KLIC 掛 [749]〕）、#50 第 2 次（過 gate，7.5 提）、#52 新（技術→技術相依邊由那個產品的供應商自己說，證據等級卻標外部印證）④段 1：semantic 旗標 24 條逐條判無關（台達購置設備、全新注意交易、奇鋐／富世達搜索、高力 CB 收足）；段 2：pq1 15 則清到 0（富世達調查案掛 entity watch `ew_0585`；InP 那則的住友 3.1 倍與 JX 價格改定都已在 AXTI 敘事基準與庫內一手；Marvell Investor Day 三則取到簡報＋第三方逐字稿，預測不進圖）。**10-08 下午（使用者「744 745 746 747 748 749 go｜APP 選 B｜剩下照你推薦｜文件我給你這兩個你看一下 有符合就close吧」）已做**：①[744]–[749] 入圖（11cb0afd 光達層＋Ouster、ffc7d6b5 新層「光模組 DSP」＋MaxLinear、5764cd5f 新層「乾式變壓器」＋Hammond、e2b3d8d6／cda36b07 CDU 層＋Munters／AAON、72e7b2de 新層「打線設備」＋K&S 的先進封裝座位）→ 閉環「等入圖」5 → 0、5 檔進母體（未到終局 6：AAON、HPS-A.TO、KLIC、MTRS.ST、MXL、OUST）②使用者給的元大投顧 14 份報告（只存 `library/private/broker_reports/2026-10-08_yuanta/`，不入庫、不當入圖文件）讀完：向你要文件 6 筆停放結案（[716][720][724][725][734][735]；逐筆報告 `library/private/research_notes/doc_requests/2026-10-08_yuanta_reports.md`），[722] 高力不在包裡照舊開著；光通訊產業報告 p.8 列出 InP 基板第四家 Freiberger → AXTI 敘事更正「全世界只有三家」（`ib_8bf694e1c648b602`，候選狀態與反證連結不動）＋入圖包 pq2 [750]（Freiberger 是私人公司，名冊條目 staged 在 `library/leads/action_drafts/registry_freiberger_2026_10_08_staged.json`）③APP 選 B：個股頁 S5a（f487f2d2：首屏照十三塊排成四段，S3 的格子印「還沒做」；plan 2026-10-05-003 Amendment B）④A3（追源等待到期就轉終局並計數）照舊 ⑤failure log #53 新（`tech:ai_switch` 的產業組名把散熱、電力、封裝各鏈都標成「AI 光互連／CPO」）。**10-08 下午第二段（照「撞到 pq2 掛號後接著做下一件」，不停在 [750] 上）已做**：①七層讀圖——第一次讀五層，全部 undecided、各列缺哪一格：光模組 DSP `sr_b87499302bb15b46`（圖外由 Marvell、Broadcom 主導；`tech:dsp_1p6t` 同義未併）、乾式變壓器 `sr_266783b7673b79b2`（需求側 0 條；國家實驗室 2026-05 全文沒在手上——OSTI 下載被擋）、打線設備 `sr_c47a31c8d0881b84`（到期 2026-12-31＝K&S 10-K）、光達 `sr_e604c3ea924d89ce`（Sivers 的雷射掛在同層＝建模待補）、先進封裝 `sr_d2718a84b215f9a1`（總稱節點把產能與設備放一起，和 `tech:cowos` 沒接）；重讀兩層：CDU `sr_8b02912eafa75cf8` 維持 neither（供給側 7 家、新進者一年內做進來）、可插拔收發器 `sr_5a9e4b5fbd8aeaf3` 維持 undecided ②五份廣度短敘事：AAON、Munters、Ouster 寫「不要」（前兩家坐的 CDU 層本身不卡；Ouster 自己的 10-K 點名 13 家競爭者），MaxLinear 缺 X（`ew_0592`：DSP 層的位置；價格在自家三年最貴端）、Hammond 缺 X（`ew_0593`，11-05 叫醒：這一層卡不卡；在手訂單已連兩季比上一季少）；K&S 敘事換版（`ib_b7744e35375e31da`：座位與騎的讀圖）、高力敘事改騎現行 CDU 讀圖（`ib_59f7412be089b9c2`）③段 5 閉包 closed：到終局 40、未到終局 0（母體外 78）；候選板 可開 0／缺 X 15／等回落 3／不要 25／已持有 2 ④段 1 清空：反證待檢 7 條逐條判無關（富世達、奇鋐被搜索的重訊，高力可轉債收足） ⑤failure log #54（入圖補了座位、舊敘事沒被叫醒）、#55（非倍率頁面印「先重寫敘事」，與規則相反）、#56 當下修（讀圖、敘事、層說明的換版只准取代最新的一筆；CDU 那一筆的取代鏈分岔留在 ledger）。**10-08 傍晚（使用者「750 go 然後繼續」）已做**：①[750] 沒有 apply——repo 是公開的，它的公開入圖報告會引用私有券商報告原文、寫持倉字樣，自家庫命中數也寫錯（「0」，實際 8 份）→ 重包成 [751]（`ra_360a545dc592e1b6bf217abc9de6ad17`：圖的增量、文件、focus 相同，「為何此時入圖」改引公開一手——AXT 自己的 10-K 競爭者名單；`--supersedes` 讓 [750] apply 拒收；failure log #57 #58）②段 4 走圖：NPO 同義節點（`tech:npo`／`tech:near_package_optics`）乾跑後鑄 [752]（比照 [730]：canonical 留讀圖與敘事押注掛著的 id；重載 0 覆寫）；這是 #36 的第二例 → failure log #59 過 gate，7.5 提「別名交集」提示（全圖回放 21 對，真重複、別名污染、上下位混在一起，只能提示）；第 6 型其餘：Hammond、Ouster 的敘事寫明刻意不連 AI 錨；IME CAS、Intel 掛在 CPO 特指節點上（CPO 同義群另案）；Agility（整機廠，CCXI 敘事判不要）與 Ewellix（Schaeffler 子公司）是機器人鏈的建模缺口——「機器人即服務」與行星滾柱螺桿沒接到機器人的錨（Digit 搬物流箱有 GXO 一手 `gxo_agility_raas_deployment_2024_06_27`，但 is_variant_of 不在走訪清單），留給機器人鏈的層深讀。**10-08 晚上（使用者「750 drop 751 go 752 go」＋問國外報告與研究方向）已做**：①[750] drop；[751] 名冊條目（_note 只引公開一手）commit 22fa801d → apply → publish 308766a7 → complete-ra；InP 基板層重讀 `sr_db3b47fad27a93a1`（維持 volume；反證①重定基準「現況 4 家、第五家才算」——Freiberger 是漏列不是新進者；thesis 寫的是三家逾九成的市占，與第四家相容，不動 thesis）；AXTI 敘事改騎 `ib_8ac38dbf1f34fc1c` ②[752] NPO 合併：entity_aliases 登記（todo:752）＋`loader/migrate_npo_merge_20261008.py`（由 FAU 那支產生、程式本體只換常數）→ 本機備份 20261008T081835Z（--no-drive）→ apply（刪 1 節點、重投影 8 邊、殘留 0）→ commit 3958e434；走圖供貨走不到錨 7 → 6、建模待補 9 → 8；NPO 層重讀 `sr_189e2468ad80be54`（多了需求側、走得到錨，仍 undecided——需求句是供應商轉述客戶）、CPO 層重讀 `sr_6dd2737aab96950e`（neither 不變）；AEVA、HIMX 敘事改騎（騎舊版的非倍率檔 JX、住友電工、AVGO、FN、MRVL、TSM 照 #55 不維護）。**10-08 晚上第二段（使用者問「國外報告要不要」「開發跟研究混在一起」「現在真的沒事做了？」，排法授權以推薦為主）已做**：①source-trace 改成報告難度三級（公開我抓／免費要登入他拿：元大、凱基、IB、嘉信／付費要 exact 金額），券商原文不得進 repo（e23e5446）②個股頁 plan Amendment C：S3、S5b、S5c 延到 12-22 檢查點之後（1edddb04）——Phase 7 期間開發只剩「研究撞到才做」。**10-15～10-16 已做（research-drain，三段）**：層深讀——FAU（大立光入圖包 [761]）、InP 磊晶（英特磊、全新敘事）、打線（ASMPT [763]、K&S 改「不要」）、乾式變壓器（Hammond 改「不要」）、晶圓級燒機／CPO 全堆疊測試（TrendForce 分段列舉；FormFactor 改「不要」、Aehr 仍缺）、光模組 DSP（Coherent 10-K 買方說 DSP「generally available from several sources」＋Marvell 供貨邊 [772]、Meta LPO 反向路徑併進 [771]）、Photonics-SOI（Tower 20-F 全文：不揭露光子 SOI 來源，讀圖換版）；OCP 週 lead 全部到終局（Meta 投影片 [771]、黃仁勳 BG2 Pod 載板／矽光子 [766]、Ayar 建模 [767]＋SuperNova 插槽讀圖：Ayar 自己說「multi-vendor laser die」、Sivers 敘事換版）；向你要文件 [764]（CPO 測試）、[765]（OCS MEMS）；failure log #3 修後殘留、#11 第 4–6 次、#61–#67。**10-17 下午（使用者 go [773]–[779]）已做**：①四個入圖包 apply（[779] 收據雜湊錯 → intake 當下修 742b57b5）、三個同義節點合併（[776] 1.6T、[777] 6 吋 InP、[778] 外部光源三合一；loader/migrate_merge_batch_20261017.py，076ec081）→ 兩個邊屬性衝突鑄 [780][781] ②讀圖：CTC（volume，限美國國內）、絕緣（undecided）第一份；外部光源改判 **neither**（E2 成立：兩家平台點名約十家、買方刻意多源）；先進封裝（加 ASMPT，仍 undecided、TCB 兩條件登 watch）、FAU（Broadcom 的 FAU 夥伴只有 Corning、TwinstarTech）、6 吋 InP（NVIDIA 那句併進來、條件②未成立）、LPT（下一層接上 CTC 與絕緣）換版；InP 基板、CPO、CW DFB、矽光子四份只換 id（failure log #75：過期檢查不讀別名名冊，過 gate）——讀圖過期 9 → 0 ③段 5 閉包 closed：KSH 缺 X（`ew_0770` 11/20；歸零旗標補 mechanical 基期、兩盞紅；持續經營意見 [782]）、Precision Wires 不要、Ligent 不要（新讀一手三份進 library/raw）；ASMPT、KLIC、Sivers、波若威、上詮五份改寫，另十份機械換騎。**10-17 夜～10-18 凌晨（使用者「780–787 go」、問「47 檔全到終局？還能做啥」；盤點 workflow 8 位＋B 組 9 位撞 session 額度全滅、主 session 用下載檔接手）已做**：①閉包 closed 是建在過期座位表上（failure log #77 當下修）→ 母體 49、全部到終局 ②盤點 A 組：USAR、日東紡、英特磊、IQE 四份過時敘事改寫（#54 第 2 次）③盤點 B 組：入圖包 [788] 華明（H 股申請文件＋美國海關提單）、[789] GF–TSMC 矽中介層＋CoWoS 接先進封裝、[791] GF＋Marvell SiGe（取代 [790]，enables 方向寫反→#78 當下修）、[792] LPT 三個買方（Oncor、Core Scientific、Fermi；名冊隨包 staged 三家，working tree 未 commit）、[793] 宇樹關節模組自研自產；LPO 第一份讀圖 `sr_bfd181ebfe7dee2b`（neither）；Lynas 敘事補 6 月季報；電力鏈海關提單 175 檔只找到一家上市邊緣出貨人（神馬電力 603530.SS）→ `lead_c461550b4e3297ae7285479bd1772796` 誠實停放；停放 lead 等的文件已公開的三則補記觸發結果（CCXI 兩則：S-4 10-13 生效、424B3 無新客戶段；美光：10-K 沒有對手方）；台積電 Q3 法說、環動科技招股書無 graph delta ④IQE H1 對照 hy_0003 的 IQE 那半：未證實也未否證（文件不談價；#80：ew_0006 沒有一手管道、只會到期叫醒）——**AXTI Q3（約 10-29）後兩半一起 `hypotheses verify`** ⑤failure log #78（當下修）、#79（共用別名第 9 型漏 10 對，2 次→7.5）、#80。**[788]–[793] 核准後要做**：華明那三處重寫、LPT 層讀圖需求側重讀、人形致動器層讀圖需求側重讀、SiGe／TIA 層第一份讀圖、先進封裝讀圖缺口①標完成；名冊 staged 條目隨 [792] commit 後跑 `engine_b.cli registry-rescan`。**10-18 凌晨第二段已做**：pq2 [794] Dover 板式熱交換器；乾式變壓器讀圖換版（Hammond Fort Worth 供給側時鐘）、Hammond 敘事換騎；徐國晉原文（只有轉述）、TwinstarTech 身分（上海私人光被動元件廠）、南大光電 TMIn 旁支（無 delta）三項結案。分離重稀土讀圖換版 `sr_6f81993effe57dcf`（moat 不變；MP 2026 Q2 10-Q 指引「In the second half of 2026, we expect to begin refining HREE with initial production of terbium and dysprosium」——反證①的時鐘；Lynas 年報：德州重稀土廠「will no longer proceed」），LYC.AX 換騎、MP 換證據 id。諧波減速器讀圖換版 `sr_370c3a1bb526d518`（undecided 不變；綠的問詢回覆：匿名「客户 19」人形關節諧波減速器 2025 年 4,000.77 萬元、量產元年；半年報擴產、稼動率改善、沒有缺貨字），四檔換騎、綠的敘事更正一句。TFLN 讀圖換版 `sr_d04604c6fc744fe2`（undecided 不變；光庫年報：資料中心 PAM-4 TFLN 晶片「验证送样阶段……进度有所延后」、募投產能利用率不及預期；新易盛自述已推出 TFLN 方案、中際只有 OFC 展示），UMC 換騎。pq2 [795] 環宇-KY（GCS Holdings，邊緣）光二極體層 onboard（2025 年報自述 PD「極高的市佔率」、200G PD；名冊隨包 staged 一筆——working tree 的 config/company_identity.json 同時有 [792] 三筆與 [795] 一筆，核准時各自隨包 commit）；名冊外候選分層 93 檔（onboard_tiers.json）、邊緣未標的 12 檔讀 lead 標完（供給側 6、非 6）→ 名冊批次 pq2 [796]（Viavi、Cohu、TTM；SIMO、RMBS、TWST 標了供給側但不收）。**10-18 早上（daily 之後）已做**：閉包被 staged 名冊的兩家買方打開（Core Scientific、Fermi，[792]）→ 各寫一份「坐哪一層」短檢查「不要」（買方、不坐供給層：CORZ `ib_072294846067efec`、FRMI `ib_ec5626d672e1d6d8`），閉包回 closed；daily 帶進的 10 條 lead 全部到終局——Tower＋Semtech 擴大 SiGe 協議（Semtech 出資鎖 Tower 專用產能，雙方聯合稿）→ 入圖包 pq2 [797]（名冊隨包 staged Semtech），其餘 9 條停放（Bechtolsheim「光模組交期 3 個月→9–12 個月、部分因雷射短缺」只有二手，掛 co:arista 的文件 watch）。**10-18 早上第二段**：力感測器讀圖換版 `sr_05fe06084f3db48b`（柯力傳感 2025 年報：機器人力學感測器年銷 1,500 只、70+ 家送樣——供給端分散；柯力邊緣但瓶頸無證據、無客戶承諾、純度低 → `lead_6b9fc00b17e804c0043d810ce3d9ff00` 誠實停放），Novanta 換騎；Photonics-SOI 讀圖換版 `sr_664b041067106024`（環球晶 2025 年報：矽光子 SOI 晶圓仍是「計畫開發之新商品」），Soitec 換騎。**10-18 早上第三段**：私人公司掛牌掃描——名冊 45 家私人公司裡坐薄層的 14 家用 EDGAR 全文檢索（S-1／F-1／DRS／S-4／424B4／10-12B，2025-07 至今）：沒有一家遞件（Virginia Transformer 只出現在 MN8 Energy 信貸合約附件的 2019 年太陽能變壓器採購單；HyperLight 出現在 Xanadu F-1 是量子電腦的 TFLN 元件合作；Noveon 只在兩份 S-4 的競爭者名單）；Lessengers、Sam Dong 查無上市計畫。旁支：光環科技（TrueLight，3234.TWO，邊緣無法量）2025 年報自述 CW 雷射 OEM／ODM 代工、2026 預估矽光代工占營收 40.2% → CW DFB 層第九家，入圖包 pq2 [798]（名冊隨包 staged）；lead 池那則「LuxNet 光環」把光環與華星光（LuxNet）混為一家。**10-18 上午（ultracode：唯讀 workflow wf_00e1662d-5df，5 位、約 136 萬 token；171 條逐字全數機械比對過本機原文；寫入由主 session）已做**：①高速 PCB 材料層新建入圖包 pq2 [799]（高速 CCL、HVLP 銅箔、PCB 用 Low-Dk 布；兩條 constrained_by 由兩個買方台燿、滬電說；HVLP 供應端金居、三井皆邊緣；名冊隨包 staged 7 家；daily lead「CCL 交期 6 個月以上」查無一手，lead_ffdc392c 補記）；②T-glass 布層讀圖換版 `sr_0d8d2afdea2d7172`（volume 不變、窗口再短：Ibiden 客戶端 Q&A 說供應商由日台兩家擴到可望第三、四家；玻璃芯各家自述 2027 下半～2030）、日東紡敘事更正（#54 型：Ibiden Q&A 08-05 就公開）、反證新增玻璃芯一條；玻璃芯＋Ibiden 客戶端邊入圖包 pq2 [800]；③冷板讀圖 `sr_10c0ba5b1caa04bf`、分歧管讀圖 `sr_47059f62582b16c2` 更正：「NVIDIA 在 GTC 點名四家」查無 NVIDIA 一手（新聞稿、技術部落格、MGX 夥伴頁、主題演講字幕、法說都沒有），只有媒體；冷板 A 那一半改靠供給側，高力換騎；④私人公司掛牌（非美 12 家）：都沒有自己的申請；索爾思已由東山精密（002384.SZ，非邊緣）全額收購、Casela（南京镭芯）由劍橋科技（603083.SS，邊緣）持股 15.85% 且供其 CW DFB 雷射——兩條邊要先登記名冊，未鑄。**10-18 下午（使用者 go [788][789][791]–[800]、drop [790] 之後；ultracode：讀圖草稿 workflow wf_e097b6ef-da7 9 位、敘事草稿 wf_1c211371-2d0 6 位，全部唯讀，寫入由主 session）已做**：①11 份過期讀圖換版（分接開關更正「華明不在美國這條線上」——美國海關提單直接出貨 Prolec GE；LPT 需求側 1→4 家買方、兩家付代價鎖貨；致動器 undecided→neither（宇樹自製）；CW DFB 窗口再縮、反證改成不只數家數；板式熱交換器、T 布、IC 載板、CPO、NPO、LPO、光二極體判讀不變）；②5 份新層第一份讀圖（高速 CCL neither、HVLP 銅箔 volume〔HVLP4 以上〕、PCB 用 Low-Dk 布 volume〔只押二代〕、SiGe 平台與 TIA／驅動器 undecided）；③騎舊讀圖的 15 份敘事換騎（摩比斯、Schaeffler 改寫兩句；華明改寫「缺 X」的①、加連到新讀圖 #3 的反證、改連層說明 v2 `ln_1614e38d9e1bc5c0`）；④名冊批次 [796] 三檔短檢查③（VIAV、COHU 不坐任何層；TTMI 在高速 CCL 需求側）；⑤新鏈主題組 pq2 [801]（AI 高速 PCB 與上游材料，8 檔等權）——金居、三井金屬、富喬的第一份敘事等它 go；⑥台股新名冊檔月營收 54 個月、季報股數 20 季回補（failure log #81）；⑦段 5 第一份敘事（workflow wf_1c211371-2d0：3 位起草＋3 位反方，全判「需修正」、主 session 套用）——台玻 `ib_5a22d69af8f2d5d7`（缺 X：三份 2025 年報的進銷貨段都沒點名台玻，向你要文件 [804]）；環宇、光環定稿存 `library/private/alpha/specs/pending_after_802/`，等光互連主題組 v2 pq2 [802]（補登光環、環宇、新易盛、波若威、Ligent）go 後寫入（光環的 CW 雷射功率等級與客戶向你要文件 [803]）；台股快照股數口徑 failure log #82；⑧使用者 go [801][802]（同日晚）：兩組落地，環宇 `ib_68043682c3f52a46`、光環 `ib_43284ab94b5db843`（都是缺 X）寫入；金居 `ib_c50158c6c28beca4`（缺 X，向你要文件 [805]）、富喬 `ib_11c5d910826ae3c8`（缺 X，[806]）、三井金屬 `ib_291b5c2e3b96f04f`（不要：曝險太薄——HVLP 推不動全社，公司自己的 2030 計畫全社經常利益 1,500 億對 2025 年度 1,367 億；大頭是圖外的 MicroThin，走圖洞線索 `lead_70e453f9cd68dc7c0e972154f357195c`）——workflow wf_90ca9d92-dce（3 起草＋3 反方，三井被判狀態錯）、wf_d728f8f8-5f4（3 修訂）；三井補 runway_inputs 機械觀測（決算短信，`mo_cc356b60518367d420450aa161897917`）；段 5 閉包 closed。⑨公開文件自己抓（使用者指出「給 GPT 抓」的公開那一半該由我做；workflow wf_c76a9c48-6c7 10 位，第一次撞額度全滅後重跑）＋套用（wf_d5c838d5-879 5 位）：光環股數初版判斷錯、同日更正（failure log #82）；分接開關 `sr_c12929ba0fe07ae5`、OCS MEMS `sr_a04f3136bf4d1bb1`、HVLP `sr_3034eea415df3712`、Low-Dk 布 `sr_70e62330234aaf30`、板式熱交換器 `sr_1f99a7bd1f5fbf52` 換版（判讀都不變）；華明、Silex、金居、三井、台玻、高力敘事換版＋富喬換騎；48 份公開節錄（DART、海關彙整、賽微／Silex、Google、TPCA×工研院、古河、三井、MOPS、高力）。待辦：分接開關層說明 v3（韓國客戶端：HD 現代電氣 2025 起列 MR 為主要買進對象；美國線第二家 Virginia Transformer）、板式熱交換器層說明的 SMC 占比錯讀、台玻 2026Q2 玻纖部門營收已超過平板玻璃（[801] 排除理由要不要重議由使用者定）、古河要不要進名冊、華明 → Virginia Transformer 入圖包（先補名冊別名的一手）。⑩2026-10-19（使用者「這幾項我都同意可以鑄號後同意」＋ /research-drain）：[807] 台玻進 PCB 組 v2、[808] 古河登記、[809][810] 名冊別名、[811] 華明 → Virginia Transformer 入圖（都已結案）；分接開關層說明 v3→v4 `ln_64d64eff22e43c92`、板式熱交換器層說明 v2 `ln_de7867429c3c4ab9`（SMC 錯讀）、快接頭層說明 v2 `ln_cde6192c10608ecb`（UQD 草案與定稿分開）；lead 池 triaged_go 清到 0（workflow wf_ba574cae-7ab 7 位追線＋4 條無圖增量停放；3 停 2 包＋2 包）；讀圖換版 12 份（判讀只改一份：NPO undecided→neither `sr_7fa43e00e0b03227`；模組 DSP 反證①部分觸及 `sr_68ef6e4e806a8563`；CW DFB 新增反證⑨需求被銅分走 `sr_def7cb705477572e`）、HVLP 讀圖 `sr_09a0f817a34a4a64`（反證④補古河）；敘事起草 6 份、換騎 14 份（含 SIVE.ST 同時換兩份）、台玻已定價改引組中位數；起草 workflow wf_80221276-220（第一輪全員撞額度、第二輪接續半成品）；引文機械核對 388 段、捏造 0（取代反方 agent）。段 4：44 筆走圖命中 43 筆照 10-17 紙本、新 1 筆 → [818]。待你核准：[812] GF–TSMC 金額更正、[813] 京東方玻璃芯（onboard）、[814] [811] 季別更正、[815] Nokia 6 吋 InP（onboard）、[816] 極薄載體銅箔層（onboard 德福／方邦／CFL）、[817] Oracle LPO／LRO、[818] PD 建模邊。核准後要做：IC 載板與 T-glass 布讀圖補京東方（[813]）、三井敘事與這一層第一份讀圖（[816]）、LPO 讀圖需求側兩家（[817]）、6 吋 InP 讀圖供給列舉（[815]）。failure log #84–#86 新增、#62 第 2 次（輪詢撞已結案 lead 的同一份申報）、#85② 更正走廊乾跑不列 claim 改句（同日 2 次）——兩者是 7.5 amendment 候選。PCB 組 v2 排除古河的理由「不在名冊」已過時（[808] 後），下次換組版本時改成主業理由。⑪使用者 go [812]–[818]（同日）：七包入圖結案（兩條自己寫錯的 claim 已更正、11 條新邊在圖上）；新登記四檔補 Engine C 快照與價格史後 materialize——京東方、Nokia、古河歸非倍率，德福（邊緣）、方邦（邊緣無法量）進閉環並寫第一份敘事（兩檔都判缺 X：德福 `ib_b0a18881dae808e3`、方邦 `ib_11cc9f474690e124`，watch ew_1177／ew_1178 等 2026 年報）；極薄載體銅箔層第一份讀圖 `sr_6aca83ddbb6d63d1` 判 **moat（護城河在三井、門正在被敲）**——兩家不同國家的競爭者法定文件寫壟斷（方邦、YMT）、三井漲價而銷量照長；三井敘事 `ib_b89371762e1479a2` 加騎這層、維持不要（量被自家產能框住）；讀圖換版 7 份（判讀都不變：IC 載板 `sr_046781b61f68dff3`、IC 載板玻纖布 `sr_cd14412c16fc279b`、6 吋 InP `sr_0cde28aa6c1bcc63`、先進封裝 `sr_683cc884b92499c1`、LPO `sr_93c474eaf0b36807`〔neither 更站得住：Oracle 1.6T 自己換掉 LPO〕、可插拔 `sr_2ef646179411e5be`、光偵測器 `sr_d1ff0e724eb5d464`〔需求錨第一次走得到〕）、換騎 5 份；workflow wf_071886e0-5cf（7 位）；引文機械核對 224 段、捏造 0；閉環 closed。新的向你要文件：[819] 環宇 200G PD、[820] 德福載體銅箔（多半拿不到）。**沒提主題組 v3**：德福營收約八成三是鋰電銅箔、電子電路銅箔約一成四——跟台玻 v1 以平板玻璃為主而排除同一條準則，加組會自相矛盾；方邦主業是手機屏蔽膜。建模缺口（不鑄）：記憶體封裝這條需求邊（三井說它比光模組大）、IC 載板一個節點同時裝 ABF 與 mSAP 兩支、玻璃基板與玻璃芯兩個節點的關係；failure log #87（讀圖 digest 看不到 develops／is_variant_of，第 3 次）。⑫使用者提供元大、凱基 12 份（GPT 代抓，2026-10-19）：GPT 的 15 段逐字回原 PDF 核 0 不符；dispatch [722][764][765][803]–[806] 回 pq1，workflow wf_b043a07a-6f5（7 位）讀全文交五段報告（library/private/research_notes/doc_requests/2026-10-19_broker_reports.md），七題以 tier_1_2_honest_passthrough 結案——**全部是券商稱、不入圖**。候選狀態全部不變（缺 X 照舊等一手）；讀到的（券商內容私有，見 library/private/research_notes/doc_requests/2026-10-19_broker_reports.md）：高力新客戶與出貨時程、CPO 測試分工與量產時點、Lumentum 的 OCS 客戶地位與晶片製程來源、聯茂產品線表、金居 HVLP4 份額估計——都只當追一手的線索（敘事撤回自己「10% 多半高估」的推一步）。換版：讀圖 板式熱交換器 `sr_3ae141cc5c4257e9`、CPO 全堆疊測試 `sr_43733ba80b33970d`、MEMS 鏡陣列 `sr_6fea82e5c4f0f52c`、HVLP `sr_dc5f1d9865eda833`、Low-Dk 布 `sr_ef4ce6b4ac4b7345`；層說明 板式熱交換器 v3 `ln_1141930c2307e617`；敘事 11 份（高力、AEHR、FORM〔反證②改成有方向的量級〕、Silex、光環、華星光、聯亞、金居、富喬、台玻＋三井換騎）。引文核對 326 段 0 未命中；兩張圖片表主 session 看原頁核過。要追的一手（未鑄 lead）：FormFactor 2026Q2 法說 insertion 1 營收、Lumentum FY4Q26 法說與 10-K（OCS 大客戶、晶片製程外包、CW 毛利）、AWS Trainium3 銅箔等級、台光電 EM-896K3／台燿 TU-953Q 規格書、高力 Q3 財報。仍開著：[741][742] API key、[819] 環宇、[820] 德福。盤點清單仍開著的小缺口：諧波減速器的哈默納科有報（等 [741]）、QD 雷射（QD Laser 6613.T，等 [741]）、IC 載板時鐘（AT&S 11/05）、玻璃基板供給側列舉、行星滾柱螺桿接人形需求。⑬第三輪（2026-10-19 晚到 10-20，research-drain）：使用者點名漏抓 Microsoft 退出 Nscale——雷達市場層只會找正向大事（failure log #88），當下修 8e6dad9b（market_topics 加「需求反轉與延誤」、prompt 寫明反向事件同等重要；反向查詢兩次都帶出這則）。追一手：退的是 Loughton 一站（50 MW；Microsoft 發言人「this decision relates to a single site」，經 AFP／Reuters 轉述）；Monarch 1.35 GW 是意向書，夏天已失效、由 Anthropic 接手（Bloomberg 08-26；Nscale DRS/A 06-26 版起刪掉那句）——不是需求反轉、不計入已取消需求；FT「Monarch 另一項租用容量」原文拿不到 → 向你要文件 [821]。副產：Nscale S-1 p.31 寫站點的大型電力變壓器有顯著部分來自中國 → 入圖包 [824]（co:nscale depends_on LPT，名冊隨包 staged）；白宮行政命令 14421（2026-08-26）授權逐筆禁止受管外國實體（含中國）的大電力系統設備與關鍵零件 → 分接開關讀圖 `sr_de2bb0babc93f7b5` 更正「還沒讀到一手」（主 session 判反證③ ew_1115／ew_1121 不觸發：授權不是公告、沒點名分接開關）＋華明換騎＋12-24 日期等待 `ew_1339_2026-10-20`；LPT 讀圖 `sr_e317c089018c5d45`（volume 不變；Nscale 圖外、EO、Loughton 卡在併網不是變壓器）。缺口（未排程，1 次）：沒有任何語意 watch 盯需求錨反轉（雲端大廠砍 capex、資料中心取消延後、neocloud 融資或租約、電網延誤）。[819] 讀完（200G PD 供應商分工，券商稱、內容私有）→ 光偵測器讀圖 `sr_dc76762c792f4c96`、環宇與英特磊敘事；[820] drop 後換號重生 [822]（failure log #89）再 drop。YMT 四維不過、維持 park；極薄載體銅箔讀圖第三版 `sr_431d7f58b2bcd6ac`、三井瓶頸格措辭、德福方邦換騎。券商點名的一手核對（八條 lead；workflow wfM 八位追源＋wfN 四位建包，主 session 寫入）：FormFactor（CPO 營收逾 2,000 萬美元是全公司口徑、不是 insertion 1；10% 客戶＝台積電）→ [825]；Lumentum（OCS 大客戶沒點名、10-K 無 MEMS 無 epitaxy、聯亞的份額只有券商一個出處）→ [827] develops；CCL（聯茂官網 IT-999GSE3 用 Q 布，台燿、台光電仍券商稱；Trainium3 銅箔供應商沒人點名）→ [823] 石英布核心包、[826] 菲利華／聯茂 onboard 附加包；高力（年報印反客戶、會計師附註定案 SMC 40.26%、Bloom 31.27%；春暉智控問詢回覆點名台灣高力是 BE 供應商）→ 不出 RA：燃料電池／現場發電層是 decompose 選題、待使用者決定；走圖第 7 型 tech:lro → [828][829][830]（供給 0→7 家全自報、MaxLinear 最弱）。讀圖換版 5＋層說明 2（InP 磊晶 v2 `ln_acc43e2ebfbd2a7a`、板式熱交換器 v4 `ln_1d68c522c39ddb41`）＋敘事 9＋換騎。核准後（使用者 10-20「823…830 go」）已寫：讀圖 LRO 第一份、石英布第一份、DSP／LPO／Low-Dk／高速 CCL／LPT／CPO 測試／MEMS 換版；敘事 MXL、台玻、富喬、AEHR、FORM、Silex，聯茂（不要）與菲利華（缺 X）第一份；PCB 組 v3 → [832]。仍開著：向你要文件 [741][742][821]。⑭使用者四問（2026-10-20 下午：券商說法怎麼影響我們、價格下行時等回落與敘事是否最新、daily 補跑、NVHBM 與雷達）：調查 6 位唯讀（failure log #90–#94、ROADMAP 三列）；當下修 444bb827（materialize 逾時、雷達截短 id、市場層上限）；敘事內容修正 9 份——COHR、SIVE.ST（持股：供給家數七→九家改成帶日期、窗口在關、連讀圖反證⑧⑨）、AXTI（已定價格改寫、更正把 JX 一手標成券商說法；加 10-31 叫醒 ew_1433）、MP（等回落改缺 X：判斷當天自家歷史在協議後那一段第 1.3 百分位，撐住它的是共識）、AEVA（整份重寫：NPO 層已判 neither、Meta 需求邊已入圖）、2455.TW、CLF、NOVT、NVTS（已定價格形容詞與數字打架）；金居拿掉券商目標價；補跑 daily 後 39 條 triaged_go：10 條直接停放（NVHBM 兩則改等具名揭露並連 HBM 讀圖、Nscale 三則併案、五則無關），29 條分 6 群追源（10-20 晚完成：28 條停放——一手取得 19、等具名揭露 5、部分 1、誠實降級 1、孤立三手 1、不投入 1；HyperLight 一手補齊但只是同源供應商自述、不做入圖包；修正多處二手轉述：「出貨低於需求 30%」只指 EML、「賣到 2029」客戶未具名、10-K 的 24 億是對自己供應商的採購承諾、三星電機 2.67 億美元載板長約的對手方保密〔Micron 沒有一手〕、FCC 沒有禁中國光模組的正式文件；順帶發現先導稀材自稱在 Lumentum 供應鏈 → 新 lead；failure log #95 子代理把使用者 email 放進 SEC 請求、#96 一則推文按實體排回 13 條舊 lead）。

## 二、2026-10-20 的續工指標快照（原 7.1 狀態格，逐字；已由 Step 7.1b 取代，不再維護）

**續工指標（研究主線＝層深讀，不用等財報）**：①層深讀佇列（2026-10-16 更新）——OCS 的 MEMS 鏡陣列（Silex；等 [765] 文件與 11/04 季報。2026-10-17 新事實：Lumentum OCP 場次與兩季法說都沒具名 MEMS 來源、部落格只寫「MEMS mirror design」；賽微電子北京產線 2025-08 起為國內客戶試產 MEMS-OCS、2026-04 仍「未进入量产阶段」〔不觸發 ew_0194〕；**新易盛 2026 半年報「推出了搭载自研 MEMS 芯片的光路交换机（OCS）产品」**——鏡陣列的設計不只一家；~~新易盛的 develops 邊等 [773] 帶它進名冊後另包~~ 10-17 夜 [784] 入圖、MEMS 讀圖主動換版 `sr_46a4f20ad37d0cbf`（仍判不出；新問題：新易盛的鏡陣列由誰代工）、Silex 敘事換騎補句）、六吋 InP 產線（坐的是 Coherent、穩懋兩家非邊緣；第二家量產要等 Lumentum／穩懋申報，低優先）、分接開關流向（華明；等 [742] key）、光模組 DSP 剩缺口②（MaxLinear 具名模組客戶；2026-10-17 讀了中際旭創、新易盛 2025 年報與 2026 半年報：前五大供應商只給代號〔中際「供应商 A」占採購 35.76%、新易盛「第一名」23.87%〕，DSP 向誰買沒有具名；中際寫「保证核心原材料具备多家稳定合格的供应商」、新易盛半年報寫「当前产业链核心原材料整体仍处于较为紧张的情形」——都不分 DSP。照實記「讀了、沒具名」，缺口②只剩向使用者要文件一途）；[766][771][772] 入圖後要重讀 IC 載板、CPO、NPO、外部光源、LPO、光模組 DSP 六層讀圖並換 MaxLinear 敘事——先讀公開一手，缺的再向使用者要（IB、嘉信研究區有哪些來源，第一次用前先問） ②7.3（Q3 財報季，到點插隊）：10/12 台股月營收、10 月下旬 Munters、MaxLinear、Lynas、10/30–31 AXTI 法說與華明三季報、11/04 Silex、11/05 Hammond 與 AT&S、11/06 MP、11 月上旬日東紡、11/13 AXTI 10-Q、11 月中下旬 KLIC 10-K、11/26 Sivers ③~~10/11 題材掃描~~（2026-10-17 已掃：`docs/reports/theme_scan_2026-10-17.md`，註冊 3 則、全部到終局） ④圖整理（段 4）：**2026-10-17 走圖 49 筆全部給了終局**（`docs/reports/phase7/graph-walk-terminals-2026-10-17.md`）——第 9 型 22 對：CPO 9 對照使用者決定不併、10 對逐字判定為不同東西、3 對真重複 → 合併提案 [776]（1.6T）、[778]（外部光源三合一），矽光子那對被缺抽取檔擋住沒鑄（failure log #73）；偵測器射程外另找到 6 吋 InP 一對 → [777]；外部光源 E2 早被 NVIDIA 部落格觸及 → [779]；ASMPT 先進封裝座位 → [775]。19 對「不併」會繼續被報：要讓它們安靜，名冊得能記「刻意不併」——Z2 提案、待決。Agility 的更正：走不到錨不是 is_variant_of 不在走訪清單（唯讀模擬只加它仍走不到），是 Digit→tote transfer 那條自驗錯標（failure log #60 第 3 例）；tech:logistics_tote_transfer 是死錨（三個修法都要使用者決定）。Ewellix 的 PRS 需求邊被 #14 存量擋住（lead_ba160412 停放）；#14 舊資料更正（要先決定修法） ⑤開發只在研究撞到才做：海外財報來源（20-F 只改程式；日本等 [741]；歐洲申報人沒有機械來源——Silex、Sivers、Munters、Soitec、AT&S、IQE 的「已定價」量不到）；APP 的 S3、S5b、S5c 延後（Amendment C） ⑥向你要文件：[741][742] key、[722] 高力 ⑦7.4 Wave 2（約 11 月起）：二階瓶頸三個 case、800VDC 回看、依 failure log 選題；7.5（12-22）：O5 的 2×2、假說證據帳、failure log 排序與 amendment（#50、#59）

## 三、原格結尾（逐字）

。已知偏差：散熱四份敘事早於該鏈主題等權組（failure log #26）〔研究：強模型在互動 session〕）

## 四、2026-10-22～10-23 research-drain（使用者「837 go」＋`/research-drain`）

2026-10-22 已做：**[837] 入圖**（JSW JFE 合資兩條持股邊宣告 control，`40eca7c5`）。**段 1 歸零**：反證待檢 35 條全判無關（Lam FQ1 8-K、台燿可轉債轉換價、聯亞法說邀請、Sivers 光達單；TPEx openapi 403 的兩則依 MOPS 主旨判、note 寫明）；輪詢命中 2 則判觸及——NVIDIA 10-21 供應鏈產能新聞稿具名 SPIL 為 CPO 光學引擎製造方（ew_0038，原文 `library/raw/nvidia_supply_chain_capacity_pr_2026_10_21.txt`）、鉅亨網逐字引鴻騰董事長「CW Laser…都缺」（ew_0095；工商時報命中頁 403，依同場鉅亨網報導判、note 寫明）。**段 2：triaged_go 74 → 0**——唯讀研究 workflow 10 組（中途撞額度、7 組接續重跑），提案 74 則；主 session 機械核對引文 383 句全部逐字對得上、停放理由逐條處置 impact 列出的 watch（g7 組漏寫 30 條由結構欄補進理由句）、trigger 實體全在名冊；**停放 65 則**、**入圖包 6 份**（[845] 泵浦雷射層〔Coherent 10-K 走更正走廊〕、[846] CPO 測試層、[847] SOFC 熱箱〔高力＋MTAR＋Bloom，四份文件、doc1 更正走廊〕、[848] SOFC 現場發電接需求錨、[849] NVIDIA 供應鏈產能〔載板三家＋SPIL＋Amkor＋KYEC〕、[850] InP 基板第六家光智科技），名冊隨包 staged 9 家（`d2864113`）。**段 4 走圖**：第 9 型 35 對＝10-17 已判 18＋新 17；新 17 對唯讀判定 workflow（3 位）→ 合併 [840]（UHP 雷射）[841]（微環調變器）[842]（AMAT by-market：DRAM、代工邏輯）、別名污染清理 [843]、刻意不併 [844]（4 對；其餘 22 對記不了，failure log #97）；逐對終局 `graph-walk-terminals-2026-10-22.md`。**段 5**：重建座位表後 closure-gate 閉包。**當下修**：記憶體需求錨 `tech:dram_production` 自 [506] 起失效 → 改 canonical＋「活的 config 不得寫別名」測試（`cc2dbc8f`）；research-drain skill Step 4 第 6 點「派工提示必寫不帶 email」（`e61a8b5c`）。**failure log**：#95 第 2 次（子代理 UA 帶使用者 email，過 gate）、#96 第 3 次（共用實體誤醒）、#97（keep_separate 只能掛既有條目）、#98（HBM 讀圖反證② 寫下時已成立）、#99（新進者反證 watch 只比對既有供應商，3 次，過 gate）。**否定結果**：Lightmatter（私人）、HBM 各則（大型股、不主動研究）、SOFC 七層（溫度感測、脫硫、觸媒、密封、電極粉體——Bloom 把供應商當機密，一手空白或候選未上市）不是可投資的瓶頸。**入圖後要做的研究**：IC 載板讀圖換版（[849]）、InP 基板讀圖換版＋AXTI／002428.SZ 敘事「沒有新增產能」改寫（[850]，配 AXT 10-29 財報）、UHP 與 MRM 讀圖重讀（[840][841]）、SOFC 主題等權組先鑄號再寫 MTAR／高力換騎的第一份 SOFC 敘事（failure log #26）、SIVE.ST 敘事補光達量產單並把 `when` 拆成資料中心口徑（L12）。

**10-23 使用者批次「840–852 go、853 pending」之後**：入圖 [845]–[850] 全部 apply＋publish；[851] SOFC 主題組 `tc_03cbb2442aa87f16`；[844] keep_separate 4 對（`557711c4`）；[840]–[843] 圖遷移（`53e3633e`，四份 manifest 在 library/private/graph_migrations/）；[853] pending 至 10-30（AXT 財報後重問）。**[852] decompose**（NVIDIA Hyperion L4 robotaxi）：一手 NVIDIA 四份＋Hesai／Aeva／Arbe／AEye／VinFast 申報＋Sivers 新聞稿；拆出 17 層：✅ 4｜🟡 0｜🔴 13（2 層只有記憶推論，標 tier 4）；13 題進 pq1（source `decompose:nvidia_hyperion_l4_robotaxi_2026-10-23`）。⚠ 光達每台 1 顆（Hyperion 10 規格）與 3 顆（Jensen 口述，只有 X 轉述）不符，留在 R0 題目裡。**入圖後的讀圖換版（走圖第 4 型 5 → 0）**：IC 載板 `sr_f000526d93daec00`（volume；NVIDIA 預付三家，最早鬆動點提前到欣興 2027Q2）、InP 基板 `sr_5abefbbafd33afd9`（volume；光智科技是既有廠被收購＝列舉補齊，反證①照 E11 改寫成新增產能）、先進封裝 `sr_3f588ef9f4ab105e`（undecided；判不出只剩「節點裝了產能與設備兩種東西」）、MRM `sr_204b23a215c2a40a`（undecided；[841] 答掉缺①）、NPO `sr_58652539becef4bf`（neither；下一層少一條無逐字的 UHP 邊）。**當下修**：`test_phase_status_hint` 讀到真實 daily 快照（`5169cf7d`）；邊斷言的 `QUOTES` 只增不減、`source_ids` 卻覆寫，三個讀端改以 `source_ids` 過濾（failure log #100）。

**10-23 下午 research-drain（`/research-drain`）**：段 0–1 歸零後清 pq1——**robotaxi decompose 13 題（[852]）全部終局**：R0 → 入圖包 **[857]**（需求錨 `tech:robotaxi_fleet`＋Thor、相機、雷達、光達、超音波五層；NVIDIA Hyperion 10 規格每台 14 相機、9 雷達、1 光達、12 超音波、2 顆 Thor）；R7 成像雷達（Arbe）四維初判：客戶端資本承諾不過，停放，名冊先走 **[856]**（Arbe、AEye）；R2 ECU 層由 NVIDIA 一手列 6 家並存＝不卡；R1 Thor、R3 CIS、R5 GMSL 都是大型股或非邊緣；R4、R8、R9 等具名；R6、R10–R12 不追（不由記憶列候選，L18）。**CW DFB 雷射層**：源杰港股申請版本 → **[854]**（第十家，自報千萬顆級交付；最大客戶 53.4% 未具名、不推成中際旭創）；同一張 CIC 表的匿名 Company D 推一步是住友電工 → 回頭讀已入庫的住友簡報，更正換版 **[855]**（CW-LD 是主力產品）；三菱電機 SiPh 用 CW 找不到一手、不建邊。其餘 lead：力積電四維初判不過（純度、無具名客戶）停放；SEMCO 預付的韓媒說法與 DART 合約「無預付」方向相反，等季報；Liberty 1.2GW 現場發電預付 → decompose 提案 **[859]**；Abilene 換租戶是舊聞、Coherent 擴產無新事。**誤醒 19 則**（Meta Q3 10-Q 8、台積電月底 6-K 7、Tesla Q3 10-Q 4）逐則重查全是原終局，6 則改成明確不等（failure log #96 第 4 次，過 gate）。**段 5 閉包 open → closed**：300489.SZ 第一份敘事 `ib_8f50a688a5a009f3`（不要：InP 只占營收約 1–2.4%、持股 50%）；AMKR `ib_992b978542dfe9e3`（缺：2.5D 在營收裡拆不出、先進封裝讀圖判不出；ew_1532 11-10 叫醒）；MTARTECH.NS 插槽讀圖 `sr_a62c00825cda8848`（Bloom Energy Server，undecided）＋runway_inputs 機械觀測 `mo_3b29df3cb754ba412ee4e4978702c195`＋敘事 `ib_f2d2c166cb760ca7`（缺：燃料電池營收沒單拆、2.3876 億美元一攬子單客戶未具名；ew_1540 11-15 叫醒）；300943.SZ 短檢查結論① → 更正換版 **[858]**（春晖仪表供 Bloom SOFC 溫度感測器七成以上）。同日兩份敘事被自己抓到 L11 ②（AMKR「全球第二大」、MTAR「七成從 Bloom 來」），當天換版。**段 4 走圖**：46 筆命中 45 筆已有終局，新 1 對 `tech:pump_laser ↔ tech:raman_pump_laser` 判不併（上下位、記不了，#97；`graph-walk-terminals-2026-10-22.md` 補記）。**當下修**：心跳「停放未處置對照」把停放之後才登記的 watch 也算進去，寫完三份讀圖就從 22 變 120——改成只算停放時已存在的（120 → 0，failure log #103）；`config/source_routes.json` SSE 寫實測（清單通、PDF 被 JS challenge 擋，仍標未驗證）、新增 BSE 路徑（verified）、SEC 路徑的外國後綴補 .NS／.BO／.VI／.KQ。failure log 新增 #102（少數股權關係人的證據等級高估，1 次）。

## 五、2026-10-23 晚～10-27（使用者「854 855 856 857 858 859 go」）

**go 執行**：[854] 源杰（CW DFB 第十家，`e285e31d`）、[855] 住友電工（更正換版，`151df26d`）入圖；[856] 名冊登記 Arbe（ARBE）、AEye（LIDR）（`26556df0`）；[857] robotaxi 需求錨與五層感測器入圖（`ababa160`；新產業錨登記經 co:nvidia 樞紐搶走 34 列需求歸屬，已撤回登記，failure log #104）；[858] 春晖仪表 SOFC 溫度感測器（更正換版，`4b9402c8`）。10-23 晚的唯讀研究 workflow 撞週額度全滅，10-27 重跑（9 位，0 錯）。**10-27 早**：daily 的 claude -p OAuth 過期 → 未 triage 積壓；補跑分類 65 則 go，連帶叫回 25 則停放 lead（Sivers 股東會公告 20、AMAT 加碼 Besi 3、Jabil 10-K 2），逐則重查全照原終局重停（failure log #96 第 5 次，`f6d67b77`）；同一份 Sivers 公告另叫醒 15 條語意 watch，照組判無關。**當下修**：誤醒重停把前次逐條處置移進 trace_history、計數器只讀現行理由 → 停放未處置對照 34 → 158；改讀聯集（`77455b61`，L17-2），其餘 124 組逐條寫處置。

**讀圖（四份）**：光達層重讀 `sr_9fb462a951e5e12f`（undecided 不變；需求側多的那條是 NVIDIA 參考規格加車隊計畫、不是訂單；Hyperion 那一格禾賽、Aeva 各自宣稱拿到，都不在圖上）；Bloom Energy Server 插槽重讀 `sr_682f9a95b4b5981f`（undecided 不變；第一份「MTAR、高力是移出中國後的境外組裝夥伴」說過頭，改寫）；SOFC 溫度感測器層第一份 `sr_9f8a5a2b9560eeae`（undecided，傾向不是換不掉——冈崎已在 Bloom 名單上；唯一一手是關係人自報，failure log #102）；CW DFB 雷射層重讀 `sr_a7f3ed189b10aff9`（volume 不變；源杰、住友是我們先前沒讀到的在位者、不是新產能，L11-5；源杰申請版本 CIC 表 2025 年 SiPh 雷射晶片外銷前五家 89.1%；上一版「補產能比前提快」「進入門檻看起來低」撤回、反證①改成只認新產能或新進者的一手）。

**敘事**：換騎或改句——AAOI `ib_350edeaa680b2aaa`、OUST `ib_efbc8ab1160aa2fd`、AEVA `ib_bd99c411f2c32675`、MTARTECH.NS `ib_c97b63f4d73ebfe9`、8996.TW `ib_b45d6558435db552`、TTMI `ib_f3b8eb2011c8cddc`（不要，短檢查）；CW DFB 六份——3234.TWO `ib_1e5c1ad4e7239f36`、4979.TWO `ib_f0cf320545be3be9`、SIVE.ST `ib_66308b5d37efb030`、COHR `ib_007a747072544d35`、2455.TW `ib_72b5cf08b79fc020`、3081.TWO `ib_e87d6e83540ae7e4`（家數句改寫、COHR「新進者補得比前提快」那句被新讀圖直接推翻；兩份補已定價位置句的日期）。第一份：300943.SZ `ib_919c7300a7942534`（缺：座位在參股 38.69% 的春晖仪表、收購 61.3106% 深交所 10-27 仍「已问询」；`ew_1587` 2027-02-28 叫醒）、ARBE `ib_dbe2dba170a132a1`（缺：Hirain 兩個量產專案車廠未具名、雷達層沒有讀圖；`ew_1591` 2026-11-30 叫醒；不用 entity_filing_signal，6-K 太多會誤醒）、LIDR `ib_b1341fb4ebdefaf4`（不要：車用沒有量產專案、光達層十幾家、NVIDIA 合格名單沒有它）。圖外一手節錄新增 12 份（春晖半年報、三季報、重組報告書摘要、問詢回覆營收產能段、延長授權公告、深交所審核狀態、Arbe 20-F 與兩份 6-K 彙整、AEye 10-K 與 2026 申報彙整；Bloom 第三季 10-Q 節錄補產品營收兩段）。

**[859] decompose**（`decompose:ai_liberty_power_innovations_ai_1_2gw`；選題理由＝提案本身：Liberty 2026-10-21 8-K 與前沿 AI 實驗室簽 1.2GW、含預付容量費）：四組唯讀拆解（系統、原動機、電氣 BOP、燃料排放熱，一手引文機械核對：系統 110 條、原動機 99 條、燃料排放熱 75 組全中，電氣 BOP 除兩處分行的數字外全中）＋主 session 對圖。**拆出 31 層：✅ 1（GSU 落在 tech:large_power_transformer）｜🟡 1（tech:hv_circuit_breaker 零供應商）｜🔴 29**——圖上現場發電只有 SOFC 一條，燃氣這條鏈整條不在。pq1 登記 16 題 R1–R16（全部 triage go＋分類）。追源旗標：預付「3 億美元」只有一份第三方逐字稿有、另一份同句沒有、申報只寫 significant——不得使用；Bergen 合約的「powerbridge」是飛輪元件、PowerBridge LLC 是另一家園區開發商；10-Q 的「Caterpillar Agreement」是 CAT Financial 翻新設備貸款、不是 8.01 億美元供貨合約；INNIO 450MW 新聞稿沒點名 Liberty、不得連；LPI 網頁的 Rolls-Royce 20V4000 是壓裂機隊用。研究暫存在 `library/private/wf_tmp/wf_research/{liberty_power_spec,onsite_gas_prime_movers,elec_bop,fuel_emissions_heat}/`（暫存，不是 authority）。

**其他**：Marvell 10-23 的 8-K（循環信用修約）叫醒載板、先進封裝、SiGe 三份讀圖的客戶重讀 watch——判無關回 active，lead 停放（#96 同形，客戶重讀 watch 也是只看發文公司）。CW DFB 重讀發現供給側缺 Broadcom（它自己說 CW 雷射是業界標準，證據掛在需求側）→ pq1 `lead_49c26e5fd3f275c564fe51a4ca630f0e`。發現未排程：ARBE 已定價量不到是因為 20-F 申報人一律當成可能掛 ADS，但 Arbe 在 Nasdaq 掛的是普通股（1 例；修法要新增掛牌單位登記且 20-F 只有年度點，不是十行內）；NVIDIA 2026-09 把 DRIVE Hyperion 改名 NVIDIA Hyperion（搜尋字兩個都要收）。

## 六、2026-10-27（使用者「修 然後/research-drain 前三天因為額度沒跑很多東西 我們慢慢追回來吧」「繼續」）

**#96 修法**（`6abfcdb4`，Z2、R1）：entity 型等待的叫醒先過預篩（`event_watch.wake_screen` 唯一判斷）——抓得到全文的叫醒先等 daily 預篩，預篩標無關或還沒標的，擋在「叫醒擋下待確認」，由互動 `wake-queue` → `wake-judge` 一份文件判一次；判無關回 active，停放理由不動。重播 10-20 起排回的 70 則：改前有 33 則會照舊放行，改後 70 則全部先擋下等預篩；五個守門變異全紅；test_full_chain_acceptance 的既有失敗不變（它不引用本次任何模組）。代價：被擋下的叫醒最多晚一天（等 daily 預篩）；日期型、假說查核與敘事 wake_brief 不篩。

**CW DFB 雷射層第二次換版**：`sr_37be377974cb068b` 取代 `sr_a7f3ed189b10aff9`。反證①被源杰 2026-10-16 上交所自願性公告觸及：二期 2026 年底至 2027 年初開始形成產能。判讀仍是 volume，窗口第一次有了在位者新產能的開出時點；買方中际旭创的投資者關係記錄表補進。六份敘事換騎，候選狀態都不變：SIVE.ST `ib_2475353e7318ec45`、3081.TWO `ib_9f9dc7f0e13a4d6a`、4979.TWO `ib_1a325e9e8fc0a2f7`、2455.TW `ib_ccf105cdfa5becff`、3234.TWO `ib_4a5a29a75091f26a`、COHR `ib_90e07a44b9b8a489`。圖外一手節錄兩份：源杰上交所產能公告、中际旭创投資者關係記錄的鎖料段。

**[859] 拆解收完**：R1–R15 全部到終局。R10（CEMS）停放 `lead_3ab1feb0`，因為沒有一手把具名 CEMS 供應商接到資料中心表後燃氣電廠。鑄號如下：
- [860] R1：需求錨加三家整合商。
- [862] R2：往復式機組（[861] 是同包舊版，建議 drop）。
- [863] R3＋R4；[864] R5＋R6；[865] R7；[866] R8；[867] R9。
- [868] R11：微電網控制＋ERock。
- [869] R13：華城。
- [870] R14：Enerflex。
- [871] R15：Stabilis＋Superior Plus。
- [872] R12：表後 BESS。

依賴鏈：[862]–[872] 都宣告 [860] 的 `tech:onsite_gas_power`；[863]、[868]、[872] 另依賴 [862] 的往復式機組宣告；[865] 依賴 [864]。

**drain 其他鑄號**：
- [873] CW 層補 Broadcom（Q3 FY26 法說；Motley Fool 逐字稿 local_only）。
- [874] Anthropic S-1：固定或最低保證的承諾約 2,656 億美元；`co:anthropic depends_on` 大型變壓器。
- [875] 天孚 ELS 量產交付＋中际旭创 2028 需求指引。
- [876] CW 層補仕佳光子：上交所問詢回復寫 100mW CW DFB 自 2026-06 起在多家國際頭部光模組廠批量出貨、客戶已下單鎖定明年交付；CW 募投項目建設期 3 年，沒寫顆數。帳號說的「72M／年」「2029 年全產能」本輪在仕佳的說明書與回復裡沒找到——這是「我找不到」，不是「不存在」（L11-5）。

名冊隨包 staged 29 家（drop 即回退）：[859] 拆解 R1–R9 各包 22 家（Liberty、Williams、Solaris、INNIO、Caterpillar、Wärtsilä、Cummins、PSI、GE Vernova、FTAI、杰瑞、Baker Hughes、Kodiak、Siemens Energy、Doosan Enerbility、Babcock & Wilcox、Applied Digital、Accelleron、Woodward、Howmet、CECO、Johnson Matthey），加本段 7 家：ERock（EROC）、華城（1519.TW）、Enerflex（EFXT）、Stabilis（SLNG）、Superior Plus（SPB.TO）、ProPetro（PUMP）、仕佳光子（688313.SS）。[863]、[873]–[875] 沒有名冊變動。

**停放 63 則，pq1 佇列清空**（drain 段 0–1 全為 0）。
- 等事件 5 則：
  - 源杰第三季報（`lead_c767d492`）。
  - Nokia 第四季報告（`lead_50cd9390`）。
  - Amkor 第三季 10-Q（`lead_2ef544bb`）。
  - Marvell 申報寫出 Photonic Fabric 記憶體設備的出貨或客戶（`lead_97d668ff`）。
  - Anthropic 申報點名晶片設計夥伴（`lead_f5074be3`）。S-1 只寫依賴第三方晶片設計服務商做「certain custom accelerator platforms」。
- not_pursued 58 則：二手、時變觀測、已在圖上的一手的轉述，或圖上沒有的層。
- 本輪讀過一手後再停的：
  - Jabil 10-K：全文沒有 Sivers。
  - AMAT 8-K：加碼 Besi 到約 20%，是持股、不是供貨。
  - Sivers 臨時股東會：換會計師；P11 激勵計畫稀釋約 2%。
  - 聯茂 10-23 重訊：9 月單月 EPS 3.54 元，屬 6213.TW 敘事的數字格。
  - Nokia 第三季 6-K。

**延後的更正走廊**（都要等前一包入圖）：
- Bloom 10-K 的 small gas turbines competes_with：等 [860]。
- Fermi 的 SGT6-5000F 與 Solaris SISU：等 [864]。
- Fermi 10-K 的 BESS。
- ERock 424B4 的「省掉 BESS」：等 [868]。

**邊緣候選（系統口徑，10-27）**：
- 已入包：ERock 4.1 億美元／8 家、華城 62.7 億／8、Enerflex 28.6 億／2、Stabilis 0.8 億／1、Superior Plus 10.5 億／11、仕佳 72.9 億／家數拿不到。
- 未入包：LFUS 92.5 億／4、NGS 4.0 億／3、CLNE 3.2 億／6。

**發現未排程**：
- 雲嶺光電 IPO 募投（新增 70/100mW CW 1,875 萬顆／年）只在仕佳回復的同業表裡看到轉述。要入圖得讀雲嶺自己的招股書，而雲嶺不在名冊（1 例）。
- NAND（SLC／HBF）晶圓密集度是圖上沒有的層，要開屬 decompose 選題（`lead_60f861e3` 停放理由已寫明）。

**我自己的誤差（記下不改，理由已 append-only）**：
- `park_1027_10` 寫「Marvell 2026-02-02 新聞稿目標 FY2028 下半年首營收」，其實是帳號引述，沒有查過一手。
- `park_1027_09` 對 ew_0940／ew_0943 的指涉略有出入。

## 七、2026-10-27 晚（使用者「860 862 … 876 go 861 drop／掃題材／decompose NAND SLC／HBF／三天的 lead 有漏抓嗎」）

**go 執行**：[860]、[862]–[876] 共 16 包經 `scripts/apply_ra_admission.py` 依編號順序入圖，全部 applied、沒有開出衝突。15 包經 `commit_pending_intake.py` 各一個 commit、整批一次 push；[873] 是 local_only，git_status 為 not_required。16 號都用 `complete-ra` 結案；[861] drop（同包舊版，已被 [862] 取代）。
- complete-ra 每號會替新進名冊、還沒有歷史的台股回填月營收與股數（#81 E1）。第一次以 120 秒逾時跑整批，[860] 在回填華城（1519.TW，54 個月）時被砍掉，結案也沒存下；改成單號、時限 900 秒後，[860] 花 5 分鐘，其餘各號很快。

**題材掃描**（`docs/reports/theme_scan_2026-10-27.md`）：窗口 10-17～10-27，6 組主題加題材外。這一輪兼補雷達：daily 外部雷達 10-24～10-27 四輪都沒跑——10-24、10-25 撞週額度，10-26、10-27 OAuth 過期；互動 session 實測 `claude -p` 已恢復。
- 註冊 1 則：`lead_90dce94b` ← `theme_scan:robotics`。內容是 Tesla Q3 法說：Optimus 在 Fremont 高量產線開始早期生產；同一場說 2027 年 Megapack 幾乎賣完，屬 BESS 層的供給側。
- 其餘主題是 FYI，沒有新需求錨；Stage 0 的 16 個新點名代號沒有邊緣候選。

**漏抓查核**：
- harvest 四天都 ok：X、EDGAR、MOPS 照常進來。
- 沒跑的是 LLM 那幾步：雷達、分類、預篩、語意輪詢、摘要。
  - 分類：今天早上已補。
  - 語意未檢：現為 0。
  - 語意輪詢：每條帶 last_checked，下一輪會接著查。
  - 雷達：恢復後只會往回補 7 天、每個主題最多 1 則，所以由這次題材掃描補主題層級。
  - 摘要：遺失，補不回來。
- 順著 Tesla 這例查到一個系統性的漏：分類器只看得到標題時會判 no_go。2026-09-01 起有 25 則（EDGAR 6-K／8-K 8 則、雷達 14 則、MFN 3 則），記為 failure log #105，處置待決。

**decompose NAND SLC／HBF**（[877]，使用者主動選題、受理即結案）：
- 系統是一顆 Sandisk／SK hynix HBF 堆疊（OCP 規格第一代），加一台 Kioxia GP1 GPU 直連 SLC SSD。
- 來源：
  - Tom's Hardware、SemiEngineering 轉述的 HBF 規格（tier 3）。
  - TechTimes 轉述的 Kioxia GP1：FMS 2026 送評估樣品，1 億 IOPS 那一代因 PCIe 7.0 認證延到 2028（tier 3）。
  - NVIDIA BlueField-4 STX／CMX 新聞稿（tier 1）。
  - Lam 10-21 法說：SLC 比重每增加 1 個百分點，約多 2% 晶圓產能（tier 1）。
- 拆出 13 層：✅ 3｜🟡 1｜🔴 9。
  - ✅：2.5D 中介層封裝、NAND 前段設備、液冷冷板。
  - 🟡：`tech:nand` 只有 Lam、AMAT 兩條設備供貨邊，沒有任何 NAND 製造商。
  - 🔴：HBF 核心晶粒、NAND TSV、晶粒堆疊接合、HBF 基底邏輯晶粒、HBF 堆疊測試、SLC 類低延遲 NAND、高 IOPS SSD 控制器、PCIe 7.0 介面、儲存節點 DPU。
- pq1 登記 10 題，都已分類 go（`lead_d945ab2f`、`lead_f098d8b8`、`lead_f70bb572`、`lead_484d9e8e`、`lead_119e02f8`、`lead_5d94167c`、`lead_fd14dba6`、`lead_72dbe6f5`、`lead_d8472873`、`lead_f3d7c310`）。
- 追源旗標：
  - SemiEngineering 寫「256 GB per die」，但同句的 16 層 512 GB 換算是 256Gb（32 GB）一顆；以規格轉述的 256Gb 為準。
  - Tom's Hardware 寫基底晶粒的 UCIe「could be … implemented by companies like Broadcom or Marvell」，是推測句，不得當成供應商。

## 八、2026-10-27 深夜（使用者「修 #105」＋`/research-drain`）

**#105 修法**（commit `bed7c8f2`，development-flow Z1／R0）：分類前先用語意預篩同一組 fetcher 抓全文，EDGAR 6-K／8-K 抓附件 99.x；抓不到任何內文的不送分類，心跳常駐「無內文未分類 N」。
- 既有 25 則「原文為空」的 no_go 讀全文後重新分類，共重分 36 則，「原文為空」no_go 剩 0。
- 測試 482 過；變異 6/6 被抓到。

**pq1 清空**：本段處置 22 則（入圖包 4、停放 18，含本段新開的走圖 lead 1 則），triaged_go 清到 0。
- 入圖包 4 個，都建議 go：
  - [878] AI 推論情境記憶儲存層（BlueField-4 驅動的 KV cache 卸載儲存、Micron PCIe Gen6 SSD），`lead_d8472873`。
  - [879] NAND 層補 Micron、Sandisk 兩家製造商（兩份 FY2026 10-K），`lead_f3d7c310`。
  - [880] USFP 開層（NVIDIA 與 Cisco 的每通道 400G 可插拔規格，OCP 2026），`lead_30eb7a1f`。
  - [881] 成像雷達晶片組開層＋Arbe 座位（robotaxi R7），`lead_34ef9086`。
- 停放 18 則：
  - decompose NAND SLC／HBF 的 8 題（HBF 核心晶粒、TSV、堆疊接合、基底邏輯晶粒、堆疊測試、SLC 類低延遲 NAND、高 IOPS 控制器、PCIe 7.0），都是 awaiting_named_disclosure：Sandisk HBF Fact Sheet、Kioxia GP1 新聞稿、Astera Labs Aries 7 都沒有點名供應商或流程。
  - 一手已讀後停：LG 冷水機供應協議、TSLA 8-K Q3 Update、三星電機（一手已在圖上）、NVIDIA ODC 開放規格部落格、變壓器價格交期報告（三個數字是它自己的、無一手出處）、Wiwynn／Ayar／GUC 聯合新聞稿。
  - 照實轉述後停（tier 1–2 honest passthrough）：KSH（PGCIL 765kV 導線核准）、Cooler Master 2,500kW CDU、奇鋐 6MW In-Row CDU。
  - 走圖 lead：燃料調壓／加熱撬 `lead_4fc46ee3`（awaiting_named_disclosure，等 Enerflex、CECO、Wärtsilä 具名專案）。

**段 1**：wake-queue 已清（ew_0060、ew_0764 照舊不動）；語意待檢 0。

**段 5**：closure-gate exit 0，`--skip 300943.SZ`（收購案在深交所待審，等世界）與 `--skip ARBE`（座位包 [881] 待 go，等使用者）。

**段 4 走圖**（終局表 [`graph-walk-terminals-2026-10-27.md`](graph-walk-terminals-2026-10-27.md)）：
- 新命中 6 筆都有終局：FTAI 航改燃機（is_variant_of 刻意不走訪、非邊緣）、車用相機（R3／R4 已停）、車用雷達（[881]）、超音波（R10 已停）、燃料調壓撬（走圖 lead 已停）、robotaxi 車隊（需求端節點；錨刻意不登記，#104）。
- 讀圖該重讀 4 → 0，四份當天換版：
  - Bloom Energy Server 插槽 → `sr_db33dc55748a1ff2`（undecided 不改）。[860] 補的反向路徑是 Bloom 自己 10-K 的競爭者清單，不是買方改用，反證 #2 沒成立；#2 補一句排除在位者自述（否則恆亮）。需求側改寫成「繞得過、Bloom 被選的原文理由是對手交期」，新增 #5（渦輪與引擎 OEM 交期縮短）。MTARTECH.NS 換騎、改兩句。
  - CW DFB 層 → `sr_14af7e9754503353`（volume 不改）。[873] Broadcom 法說「more than tripling」、[876] 仕佳光子 100mW 自 2026-06 起批量出貨，都觸及反證①的實質部分；照 48 小時動作逐項答，沒有⑧的價格或稼動率訊號、方向相反，不改判。①改寫基準、①②⑧補兩家。六份敘事換騎（SIVE.ST、3081.TWO、4979.TWO、3234.TWO、2455.TW、COHR）。
  - 外部光源層 → `sr_6d26d3c8f69e0ec7`（neither 不改）。[875] 天孚自述 ELS「稳定量产交付」是多源的方向；改一句「這一格還在量產前」。9856.HK、SIVE.ST 只換 id。
  - 大型電力變壓器層 → `sr_63c81a98cf0f3e09`（volume 不改）。[869] 華城（台中擴建 2027Q2 投產）、[874] Anthropic S-1（第一家買方逐字寫 allocation constraints）；①補 Anthropic、③補華城。沒有敘事騎這一層；華城是邊緣、敘事還沒寫。
- 敘事該重寫 0。

**#104 重犯（我自己的誤差）**：照 [857] 草稿 ⑤ 把 `tech:robotaxi_fleet` 登記進 `config/sector_anchors.json`，跑錨鏈預告才發現 16 個節點經 co:nvidia 樞紐改判成 robotaxi 產業——跟 10-23 同一個步驟同一個錯，動 config 前沒先 grep failure log（L11-4）。當下撤回（沒有 materialize、沒有寫讀圖）；`_doc` 補一句警告（新增錨前先跑錨鏈改變的節點數預告），#104 記為第 2 次。

**發現未排程**：
- trigger 文字的實體推斷不認名冊短名（例：「Micron」解析不到 `co:micron`），停放時要手動給 `trace_trigger_entities`（1 例）。
- 華城（1519.TW）邊緣、在大型變壓器層，敘事還沒寫——下一輪 research-drain 的「邊緣卻沒敘事」。

**段 5 續（10-28 凌晨）——上面那次 exit 0 是假閉包**：[859]–[876] 同日隨包登記的 29 家還沒有頁面、快照與價格歷史，不在母體裡（failure log #106，第 1 次）。手動補齊（`webapp materialize <29 檔>`、`engine_c/etl_yfinance.py <29 檔>`、`engine_c.history_backfill --incremental --tickers <29 檔>`，都是 daily 本來就會跑的同一支）之後，可推進 11 檔，處置如下：
- 新鏈主題組先鑄號：**[882]** AI 資料中心表後燃氣發電供應鏈（INNIO、PSI、ERock 三檔等權；排除 Accelleron、B&W、CECO、Johnson Matthey、Enerflex、Stabilis、Superior Plus 與大型股，理由逐條寫在提案裡）。燃氣鏈 9 檔邊緣的第一份敘事——含組外那 6 檔——一律等 [882] 落地（failure log #26：新鏈的第一份敘事以鏈計）；組外 7 檔機器擋不到，本輪以 `--skip` 顯式排除。
- 華城（1519.TW）第一份敘事 `ib_2ae40aa82fb3b49a`：騎大型電力變壓器層，候選狀態「缺」（`ew_1679`，11-15 叫醒）——缺口流向它的一手（具名美國客戶、在手訂單、交期）沒有，2026 年 1–9 月營收約與去年持平。一手：2025 年報（MOPS 抓取，`library/raw/mops_1519_annual_report_2025.txt`）。已定價①補完價格歷史後有值（P/S 自家三年百分位 34.7）。
- 仕佳光子（688313.SS）第一份敘事 `ib_372daa54addd62e5`：騎 CW DFB 層，候選狀態「缺」（`ew_1683`，2027-04-30 叫醒）——騎的那一層只占營收零頭（2026 上半年 DFB 相關產品 4,890 萬元，光晶片及器件 12.43 億元），大頭在 AWG 與高密度光纖連接器（不在圖上）。一手：2025 年報、2026-10-24 定增問詢回復與募集說明書（節錄 `library/raw/shijia_688313_placement_docs_20261024_revenue_mix_customers_excerpt.txt`）。已定價與出現在數字裡都量不到（中國申報人沒有機械財報來源）。
- closure-gate exit 0：`--skip 300943.SZ ARBE ACLN.SW BW CECO EFXT JMAT.L SLNG SPB.TO`（300943.SZ 卡世界、ARBE 卡 [881]、其餘 7 檔卡 [882]）。心跳「邊緣卻沒敘事」會是 9（燃氣鏈，全掛 [882]）。

**發現未排程（續）**：
- 電力主題組（`tc_1a8d8a8911b327d5`）照準則可補華城（主業就是變壓器）；本輪沒鑄 v2——現有敘事不需要它，組中位數只是脈絡（1 例）。
- 仕佳的營收大頭（AWG、MPO／MMC 高密度連接器）不在圖上；若要押它，是那兩層的層深讀（1 例）。

## 九、2026-10-28（使用者 `/system-decompose 高密度光纖／光纖預製棒`＋`/research-drain`；「四個提案看起來都不是很必要」）

**decompose [883]**（一條 Corning Contour Flow 6,912 芯高密度光纜，往上到光纖、預製棒與原料；需求錨 `tech:ai_dc_fiber_cabling`）：先列層再比圖，16 層全 🔴（圖上 Corning 只連 FAU 與玻璃 CPO）。登記 13 題 pq1（source `decompose:corning_contour_flow_6_912_smf_28_contour`），研究中追加 1 題（光纖層的中國邊緣廠，`lead_7ac59c85`）。

**入圖包 4 個＋主題組 1 個，都建議 go**：
- [884] 光纖鏈開層（預製棒→光纖→光纜←AI 資料中心建置）＋STL 座位＋Corning 的 Amazon 長約、NVIDIA 擴產夥伴、「客戶分攤擴產成本」（`ra_798ace0c`）——預製棒、高芯數光纜兩題，與 GLW「share the cost and risk」那則 X lead。
- [887] 光纖連接層（MT 插芯→高密度多芯連接器←AI 資料中心建置）＋太辰光座位（`ra_ff98c363`）——MT 插芯、MMC 組件兩題。太辰光 2024 年報具名 Corning 占營收 70.10%、2025 年第一大客戶 68.48%（未具名）；子公司自產 MT 插芯已批量供貨；它自己的風險提示寫「光通信行业竞争充分」（反方向證據，已寫進包）。
- [886] 光纖材料附加包（`ra_dc0a9b48`）——飛凱 supplies_to 塗覆樹脂（onboard），菲利華 supplies_to 預製棒石英器件（那份半年報已在圖上，走更正走廊：舊 7 段逐字保留、追加 3 段）。兩家都邊緣，但光纖只占它們營收的一小塊。
- [885] 預製棒層第二家邊緣一貫化廠：永鼎（`ra_5551f779`）——自述「光纤预制棒…扩产周期长达 18-24 个月」「短期供给紧张格局仍将延续」：這句同時是反證的時鐘（新產能 18–24 個月後到）。
- [888] 主題等權組（AI 資料中心光纖與光連接供應鏈：GLW、STL、太辰光；排除永鼎、飛凱、菲利華、雲南鍺業與綜合電纜集團，理由逐條寫在提案）。**新鏈先鑄組**（failure log #26）：四包 go 之後，本鏈邊緣檔的第一份敘事——含組外的永鼎、飛凱——一律等 [888] 落地。

**decompose 停放 7 題**：
- 四氯化鍺 `partial`：雲南鍺業（名冊內、邊緣）2026 上半年光纖級鍺營收 1.07 億元、年減 8.27%，境外只占 1.45%——AI 光纖的需求沒有出現在它的數字裡；等 11-27 中國對美鍺出口禁令暫停到期後的年報與 Corning 10-K。
- 四氯化矽 `original_obtained`（STL 自製；法說被問原料時點名鍺、氦、聚乙烯，沒提它）、氦 `original_obtained`（成本與供應風險、回收可部分抵銷；光纖鏈沒有邊緣的氦座位）、設備 `not_pursued`（唯一自述全線的 Rosendahl Nextrom 未上市）、抗彎小外徑光纖 `isolated_tier_3`（份額只有 TrendForce）、空芯光纖反向路徑 `partial`、需求錨 `awaiting_named_disclosure`（Corning 客戶預付 6.39 億美元的付款人、每 GPU 光纖芯數都只有法說轉錄）。

**非光纖 lead 20 則停放**（X、EDGAR、雷達）：作者推論或二手轉述 not_pursued（SemiAnalysis／Bernstein 談話、光模組利潤評論、股價評論）；中國雲端業者記憶體長約併成一則 `lead_511b2c4f`（isolated_tier_3，等 SK 海力士、三星 Q3 法說），其餘三則併入；Broadcom 8-K 讀完一手（Item 2.03：供應商替客戶的 AI 機櫃租約提供殘值支撐，客戶未具名，不入圖）；Lumentum 執行長 theCUBE 訪談兩則 tier 2 照實轉述；CoWoS 漲價、Meta 財報、Teradyne 財報、SK 海力士股東回饋、美光工會等財務或價格觀測 not_pursued；Corning Q3 摘要的結構部分已在 [884]。每則都逐條處置了 `engine_b.impact` 列出的在盯條件。

**段 1**：語意待檢 13、叫醒擋下 10，全判無關（Broadcom 8-K 只有融資安排，沒有光源、CPO 或產能的字）。

**段 5**：英維克（002837.SZ）重寫 `ib_b2d282f040bb6f61`——10-22 因覆蓋家數判成非邊緣撤回，10-28 回到 12 家、重回母體（failure log #110）；照撤回前一版重寫並補 10-27 第三季報（液冷仍沒拆；營收年增 33%、淨利持平），候選狀態仍是「不要」，三條反證重新在盯。closure-gate exit 0：`--skip 300943.SZ ARBE ACLN.SW BW CECO EFXT JMAT.L SLNG SPB.TO`（300943.SZ 卡世界、ARBE 卡 [881]、燃氣鏈 7 檔卡 [882]）。

**段 4 走圖**：與 10-27 23:00 那一輪相比沒有新命中（只少了當晚換版的 4 份讀圖）。

**發現未排程**：
- 仕佳（688313.SS）的營收大頭之一是高密度光纖連接器（10-27 那一條）——[887] 落地後就有 `tech:high_density_fiber_connector` 可掛；下一次讀它時補供貨邊（1 例）。
- 光纖層還有三家邊緣廠沒讀一手：烽火（600498.SS）、通鼎（002491.SZ）、特發（000070.SZ），寫在 [885] 的搜尋摘要；不在名冊，所以沒有任何計數器會想起它們（1 例）。
- 光纖鏈第一份敘事寫成後，氦斷供要登記成全鏈的反證 watch（停放理由已寫明）。

## 十、2026-10-28 白天（使用者「878 879 880 881 882 884 885 886 887 888 go」）

**go 執行**（入圖與主題組各自 commit）：八個入圖包——KV cache 卸載儲存層 `4a5cea7f`、NAND 補兩家製造商 `ab60e912`、USFP `92f5e4c8`、成像雷達晶片組＋Arbe 座位 `08f721d2`、光纖鏈四包 `0e1487b0`／`247d6972`／`f59c4598`／`9c7305a8`；兩個主題組落地——[882] AI 資料中心表後燃氣發電（INNIO、ERock、PSI）、[888] 光纖與光連接（GLW、STL、太辰光）。

**光纖鏈第一份敘事（四檔，一手節錄 `6f0a9fd8`）**：STL（STLTECH.NS）`ib_c00da265c36c3f13` 已定價等回落（`ew_1700`；第二季營收年增 145%、在手 3,527 億盧比、第二家 hyperscaler 五年協議，但股價約年初的 8.8 倍，翻倍要 FY29 計畫全兌現）；永鼎（600105.SS）`ib_5c14c4ee9502efe7` 缺（`ew_1701`；現有產能沒寫、客戶只寫運營商與國家重點工程；擔保占淨資產 83.12%）；太辰光（300570.SZ）`ib_d48286697ce0a366` 缺（`ew_1703`；連接器層讀圖未定、擴產後第三季有沒有加速）；飛凱（300398.SZ）`ib_b6887d74af165e4a` 不要（光纖塗覆樹脂約兩成多營收，2023 年還把光纖塗料擴產改投液晶材料）。

**燃氣鏈：七層第一份讀圖＋九檔第一份敘事**。讀圖——現場燃氣發電（系統層）`sr_81e480f34cf1b20e` 量、往復式機組 `sr_e491c0c29221121d` 量、虛擬管線 `sr_a99a8fc750b91ec7` 量；增壓器 `sr_12a02f673d0160ef`、燃氣鍋爐 `sr_e727981dbde72702`、排放系統 `sr_ec43c226592362e4`、SCR 觸媒 `sr_cc21cecdbfeebaa6` 判不出（每份兩條反證，已登 watch）。敘事——
- 可開 1：Stabilis（SLNG）`ib_fa1fdff88b080039`：約 2 億美元 take-or-pay 的 LNG 供氣長約（2027Q1–2029Q1，客戶預付 2,500 萬美元、正好抵這份合約要的投資），一年約 9,000 萬美元、比近四季營收多六成，價格跟年初一樣。燈：現金跑道紅（6 月底非受限現金 450 萬美元）、債務契約、擴張要再籌資——都寫在必須為真；微型股（市值約 8,000 萬美元）。
- 缺 5：B&W `ib_117c0293850f62f8`（`ew_1733`；一案一客戶、自己先訂 1 GW 汽輪機；今年 ATM 賣 2,310 萬股＋公開增資 1,243 萬股）、CECO `ib_0348eec9da3f4394`（`ew_1734`；燃氣發電沒拆、OEM 設備包自帶排放系統、現金跑道紅）、Enerflex `ib_581211923504b60a`（`ew_1735`；1.75 GW 在手的金額與毛利沒寫）、ERock `ib_098b56d60ba4d7f1`（`ew_1736`；17 億美元在手的轉換時程；已定價只靠組的脈絡答「是」）、PSI `ib_a9eb39406dc80d05`（`ew_1737`；資料中心的量還沒進數字）。
- 不要 3：Accelleron `ib_7f880e79d6bcec77`（資料中心相關營收不到 9%）、Johnson Matthey `ib_7a427b71715c3fdc`（SCR 觸媒是剛併入的一家廠、層讀不出卡）、Superior Plus `ib_bd4511f124e60ecf`（CNG 只占上半年營運 EBITDA 約四分之一）。

**換騎與換版**：Arbe `ib_7e1474baae3d6194` 換騎成像雷達晶片組層第一份讀圖 `sr_6c768b76e9d9f353`（判不出，缺的三格不變）；可插拔收發器層換版 `sr_d25e6e2664408ad6`（USFP 變體邊讓讀圖 stale；判讀不變——USFP 是可插拔的下一代外形、走多源，需求側多一個一手、供給側沒有新證據）。AAOI 的「不要」不靠這一格，沒換騎（狀態燈仍是最新）。

**更正**：[888] 提案排除永鼎的理由寫「讀不到分部拆分」是錯的——2026 半年報附註有分部表（敘事已引用）。組是 append-only，沒有為此鑄號；下次組換版時重寫這條排除理由，是否仍排除另判。

**段 5**：closure-gate 未到終局只剩 300943.SZ（春暉智控，10-27 已寫敘事、缺 `ew_1587`）——它的座位在參股 38.69% 的春暉儀表，收購其餘股份還在深交所問詢；gate 列的兩格（帶可替代性的結構邊、基期觀測）一格要 Bloom 端具名（Bloom 把供應商當機密），一格在收購完成前補了也量不到 SOFC 那一塊，等世界。**段 4 走圖**：第 4 型 1 筆（上述可插拔收發器）已處理；其餘八型與 10-28 凌晨那一輪相同。段 0–1 全零，pq1 空。

**發現未排程**：
- ERock 是 Up-C 雙層股權：系統快照的市值 4.3 億美元只算 A 股（4,817 萬股），A 加 B 約 2.19 億股、約 20 億美元（failure log #111，第 2 次，同 #20 的 H 股型）。
- PSI 在燃氣組裡，組的同口徑 P/S 中位數「有值的成員 0／2」——INNIO 剛上市、ERock 的 P/S 算不出來；組的脈絡要到 INNIO 與 ERock 各有四季營收後才量得到（1 例，不排程）。
- 收尾 `audit invariants` 的 Orphans FAIL 1：[881] 入圖消化了 Arbe 那則 lead，但等它的 `ew_1528` 還在等；`engine_b.todo sync` 收掉後 PASS。入圖不會順手跑 sync，下一次 daily 也會收（1 例，維持營運，不排程）。

**收尾續（使用者「Research drain 應該要把所有數字清零…看起來你只在看 pq1」）**：上一則收尾只讀了 `engine_b.cli drain` 首行且截在 300 字，沒有讀短版 ⑤ 的待做清單（`engine_b.todo_ledger`，19 格；「歸零就不漏球」的唯一清單）。補讀後只有一格非零——敘事該重寫 2：
- AAOI 騎舊讀圖：可插拔收發器層換版後，上一則以「判讀不變、狀態燈是最新的」為由不換騎——錯，`rides_superseded` 正是為了這種情形而存在；換騎 `ib_8dd9c93f8af82f18`（只換讀圖 id，「不要」不變）。
- THK（6481.T）非邊緣仍有敘事：分析師 13 家（門檻 12）、市值 4.00B 美元；照規定撤回 10-07 的短檢查敘事 `ib_50b9b3179394df46`（撤回紀錄 `ib_4fd3ad718fec5d0a`）。它在門檻上 ±1 家——翻回邊緣就是 failure log #110 的第 2 次。
- 補讀後 19 格全 0。watch 計數器另有兩個非零但不是待做：停滯 3（09-17 補登的 AXT 兩則、AMD 一則的追源等待，2027-01-15 到期，建立時寫明到期由使用者決定續等或放棄）、到期 3（三筆都已有 `expiry_resolution`）。
- 段 4 走圖：今天的命中逐筆對過三份終局表，新的 3 筆都有終局——[`graph-walk-terminals-2026-10-28.md`](graph-walk-terminals-2026-10-28.md)（Arbe 走不到錨＝#104 刻意；光纖↔預製棒、光纖↔光纜 keep_separate，兩端都不在名冊條目上、記不進名冊，#97）。
- APP（使用者「滑 app 滑了很久看不出來這些公司為何沒有敘事」）：104 頁沒有敘事的檔原本只印「不上候選板」／「還沒寫短評」——邊緣判定早就算好、沒帶到畫面（L16 的形狀）。①候選狀態格與首頁卡片改印原因：非邊緣的市值、分析師家數、門檻與超過哪一項，撤回過的寫撤回日與理由開頭（`c704c38b`）；②首頁「沒有敘事」拆兩組（L12）：「不寫敘事（非邊緣）」放在「不要」之後、「還沒寫敘事（邊緣，該寫）」留給待做，個股頁非邊緣不再標「還沒做」。104 檔全是非邊緣：兩項都超 70、只超市值 17、只超家數 17。使用者下一個 session 大修 APP 呈現。

## 十一、2026-10-29 晚～10-30（使用者「3. 能直接做掉嗎」「Ok go 然後重寫敘事 再 /research-drain」「照你推薦 然後853 go」「891 go 890 drop 然後繼續」「892 893 894 895 go 看到的問題先修吧」）

**敘事 stale ③（ROADMAP #132）**：候選板成為「騎舊讀圖」「新邊沒讀」的唯一 owner、⑤ 讀它的清單（`80493c15`）；真資料亮 3 份——Ligent（9856.HK）、FormFactor、Fermi 的敘事沒讀過入圖後新邊的文件。讀完重寫（`ib_4118a77fa4a167ea`、`ib_08d2931895570882`、`ib_abfbb200ee0a755f`，三份仍是不要），⑤ 3→0（`7680d3ff`）。

**research-drain（10-30 清晨）**：AXT 第三季新聞稿與法說兩度觸及 InP 基板讀圖反證④（2026 年產能倍增的承諾已超過、法說再加碼）——讀圖換版三次、判讀都維持量，現行 `sr_5bd84c00f10ad7da`（最後一版把法說引文換成逐字核對過的轉錄稿，節錄 `df25693d`）；AXTI（等回落）、光智科技（不要）、雲南鍺業（缺）各換騎兩次。thesis `axt_inp`：[892] 複查、[893] 推翻條件成立（Q3 營收 7,340 萬美元 ≥ 6,000 萬）→ active 轉 review_required（`dbb30f89`）；轉了之後每天都到期，[896] 重新鑄出，pending 到 11-16（Q3 10-Q 約 11-13，結論 revised／retired 跟 10-Q 一起做，另提 thesis mutation）。

**太空太陽能新鏈（[853] decompose 已核准）**：[890] drop、[891] v2 入圖（`83a3bab7`：新錨 `tech:space_solar_array` 與七層；名冊 17 家＋雲南鍺業補中科鑫圓別名 `d6cb132d`）；需求錨照 #104 先量後登記（`09c4c0ea`：493 列改判 3 列、全是本來就該歸它的鍺列，鏈上經過樞紐公司 0 列）。第一批讀圖：太陽翼陣列 `sr_490e636bb9dadd4e` 判不出、三結外延片 `sr_15b9a67305b2a83d` 都不是（高階外延在買方手上、外包的是上一代工藝、料由買方給）、鍺襯底 `sr_d3b1a0e27590b35b` 都不是（買方寫兩家「采购单价不存在显著差异」）、三結電池片上午 `sr_ac889a9c52041a8e` 讀成量。[894] 主題組落地（成員電科藍天、5N Plus；乾照、三安、雲南鍺業、AXT、Rocket Lab、中國衛星等排除在外）；[895] 太空蓋片層入圖（`21b82de2`：Qioptiq〔2025-02 起屬 Teledyne，NASA 第三方具名〕、秦皇島星箭、SCHOTT——都沒有上市的邊緣公司，本輪沒寫蓋片層讀圖）。

**#114 當下修（使用者「看到的問題先修吧」，`9e1a7648`）**：主題組 spec 的排除名單每一項寫 `company_ids`（鑄號端必填；名字或代號點名的有代號名冊公司漏寫就拒收），閉環與 `alpha brief --add` 連排除在外的新鏈公司一起擋；舊的 13 份組 spec digest 不變。全套 4451 passed、1 skipped。

**段 5：新鏈第一份敘事（組落地之後才寫）**。母體先清：ETL 補快照後電科藍天（12.1B 美元）、中國衛星（10.1B）、Rocket Lab（35.4B、分析師 20 位）判非邊緣，不寫敘事；剩三檔。寫之前回讀買方原文，撞到三結電池片那份讀圖的錯：撐著「量」的只有 5N Plus 自述的積壓（L8），同一份買方招股說明書的採購段寫「报告期内，公司主要原材料市场供给充足，价格整体保持稳定」（主要原材料第一項就是空間單體太陽電池），2026 半年報向天津恒电的關聯採購商品反而由 3.53 億元降到 2.38 億元、全文沒有「紧张」「供不应求」「交期」「涨价」——這句不在任何一條邊上，讀圖沒讀到（failure log #115，第 1 次）。重讀改判判不出 `sr_196352cea9f0782a`（國內有買方說不卡、西方只有賣方說緊；4 條反證已登 watch，`ew_1825`–`ew_1828`）。一手節錄 9 份（乾照 ×3、三安 ×2、電科藍天招股書採購段與 2026 半年報、5N Plus 年報與年度資訊表）。
- 三安光電（600703.SS）`ib_5cd9414da64a8228` 不要：太空電池片自己說占營收「较小」、沒揭露金額；外延代工那一格只占買方外包的 4.43%；前三季歸母淨利 −1.20 億元。
- 乾照光電（300102.SZ）`ib_1925bcb52acea736` 不要：外延代工是買方第一名（2024 年 1.17 億元、49.31%）但三年沒在長（1.42 億 → 1.17 億 → 2025 上半年 6,072 萬），電池片國內報價比天津恒电高、差不到一成，前三季扣非淨利 171 萬元。
- 5N Plus（VNP.TO）`ib_8fb1550545825c7b` 缺 X（`ew_1829`，11-03 醒——第三季業績 11-02 盤後、11-03 法說）：缺西方衛星或星座買方的一手（交期、配額、預付、長約）與太空占營收多少；騎電池片與鍺襯底兩層。
- 雲南鍺業（002428.SZ）換版 `ib_77bf446488c5f152`：定位與瓶頸兩格補上層讀圖與主題組的結果，加電科藍天招股書前五大供應商表（2025 上半年「云南鑫耀半导体材料有限公司及下属单位」7,623 萬元、第二大，未拆品項）；賭注仍只押磷化銦。
- 四則故事（`st_b81c0358799d8225`、`st_89acac563a5b9ee1`、`st_ee30310e1dc5952e`、`st_1c9d724b304dc512`）與三檔首頁介紹。

**收尾**：closure-gate closed（只顯式 skip 300943.SZ，卡世界）；短版 ⑤ 二十格全 0；materialize 後重啟 8790、health `code.stale=false`。watch 計數器非零但不是待做：停滯 3（9 月補登的追源等待，2027-01-15 到期兜底）、到期 3（都已有 `expiry_resolution`）。

**發現未排程**：
- 讀圖只看得到邊上的逐字：買方文件裡講整體供給的句子（採購段、原材料價格變動）不具名供應商，入圖時不會被抽成邊（failure log #115，1 例，gate 否）。
- 電科藍天向雲南鍺業集團的採購：2024 年中科鑫圓鍺片 6,043.59 萬元（占材料採購 3.40%），2025 上半年「鑫耀及下屬單位」7,623.34 萬元（占採購總額 6.84%）——兩個口徑不同、後者沒拆品項，不能直接比；雲南鍺業光伏級鍺 2026 上半年年減 26.87%。鍺襯底層的讀圖不因此改判（1 例，記在敘事，不排程）。

## 十二、2026-10-31（使用者點名 SLNG：「深入了解 Stabilis…請先只讀」「剩下的東西你也幫我找吧」「好 改寫吧 還是可開？ 那目標價會想怎麼估」）

**只讀一輪**：SLNG 敘事 `ib_fa1fdff88b080039`（可開，騎虛擬管線層「量」`sr_a99a8fc750b91ec7`）答不出「客戶為什麼選這家」——敘事寫「自有液化廠」，管理層法說寫發電合約「served largely with third-party provided LNG」；第二份資料中心合約是六個月試運轉，不是多客戶；Galveston、兩個債務契約測試日、ATM 都沒寫。使用者給了 Morningstar 量化報告（模型產生、沒有分析師；不進 repo），其餘自己找：EDGAR 2026 年的 8-K／10-K／10-Q／委託書、兩場法說逐字稿、Aggreko F-1/A（全文沒有 Stabilis、沒有 LNG）、Maxim 降評轉述。節錄 12 份進 `library/raw/`：SEC 來源 56 段逐字核對全中；網頁來源（逐字稿 12 段、Maxim 4 段）以網頁原文逐段核對全中（逐字稿修了兩處起句、補「EBITDA 率 high teens」原句）。

**層重讀**：虛擬管線層由量改判不出——B 型的核心「產能一時補不上」上一版自己列為缺格，圖外一手反而指向原料不緊（外購 LNG、30 多家液化廠、Maxim「limited barriers to entry」二手）。`sr_1dddba4365229e99` 寫完發現一句把推論寫成事實（「Aggreko 就是那份占 19% 的路易斯安那合約的客戶」——10-K 只點名 Aggreko 超過一成），同日更正為 `sr_2c7c211426ab2617`（判讀不變；watch `ew_1843`–`ew_1845`）。

**敘事**：SLNG 換版 `ib_a6720d895ba7287f`，可開 → 缺 X（層的問題；`ew_1842` 11-20 叫醒看第三季 10-Q 與 Superior Plus 季報）；必須為真補兩個債務契約測試（AmeriState 2026-12-31 年度、Huntington 2027-03-31 起每季）、Galveston、ATM、查核意見；已定價那格拿掉價格數字（首屏不放價格報酬）。Superior Plus 換騎 `ib_2592c2823d16a6fd`（不要，判斷不變）。兩則故事 `st_602757a442ea257d`、`st_d1f3d165b531ca55`。候選板可開 1 → 0（可開為零就零）。

**目標價**：系統不給（G3，Phase 0 退役），由敘事「要從 {market_cap} 翻倍需要什麼」取代；本次寫成營業條件（長約照時程、2027 營收破億、利潤率、撐過兩個契約測試、Galveston 不靠大幅增資）。

**發現未排程**：
- 歸零旗標的營業現金流含客戶預付、yfinance 自由現金流與 EDGAR 對不起來，兩盞黃燈的理由「本業賺得出現金」不成立（failure log #118，1 例，gate 否）。
- 唯一的可開是 SLNG，它的可開騎在一份前提沒證據的「量」上——這份讀圖寫入時自己就列了缺格（單價有沒有溢價）；「讀圖自列的缺格正好是判讀類型的核心前提」沒有機械提醒（1 例，不排程）。

**補記（同日，使用者「做掉吧」＋「每檔都挖沒有 token…zoom out」）**：
- **更正上面第一條**：#118 動手前做效力檢查（L11-6），扣掉客戶預付後近四季營業現金流仍是 +255 萬（那幾季還有 2025 年第四季才結束的大合約），燈看近四季，所以「本業賺得出現金」在燈的口徑下成立，扣預付後兩盞燈的顏色與句子都不變；「不成立」是我拿半年（−51 萬）對近四季說的，說過頭了。真正的不一致是自由現金流的定義（yfinance −2,275 萬 vs EDGAR +797 萬），而只換來源不扣預付會讓 SLNG 判綠。效力 0、又要動 Engine C 欄位（Z2），回報後未實作；#118 已改寫。
- **zoom out 的盤點**（候選板與讀圖 ledger，10-31）：缺 X 36 檔散在約 30 層，同一層最多 3 檔；等回落 4 檔的價格叫醒全部已觸發（3081.TWO、4979.TWO、AXTI、STLTECH.NS）；兩檔持股都騎 CW DFB 雷射層，那一層共 7 份敘事。錢附近的讀圖深度差很多：CW DFB 15 版、InP 基板 19 版，光纖預製棒 1 版（STLTECH.NS 騎它）。可開最容易出現在研究最淺的地方（failure log #119）。提案：深挖不按檔排序，而是跟著「離錢的距離」事件走（宣告可開前、等回落叫醒、持股反證醒），廣度那一側照舊；等使用者定。

**補記二（同日，使用者「總結一下你推薦做哪些開發？」→「都做然後記下來吧 收尾」）**：
- **兩項開發同日交付**（ROADMAP 旁支）：「首屏敘事不寫死燈色與價格報酬」（#120：寫入端燈色拒收、收盤價只印，故事同規則）、「宣告可開前的深挖清單」（#119：SKILL 段 5＋`alpha brief --add` 宣告可開時只印的清單；回放舊版 SLNG 可開 spec 印出「沒有深挖清單」）。#118 照前一則補記不實作。
- **13 份敘事只改字面值換版**（判斷不變）：4971.TWO、AAON 的紅燈（今天黃燈），AAOI、CECO、OUST 的燈色（今天一致，燈一變就錯），9 份已定價那一格的收盤價；13 份故事跟著改，依據拿掉價位與漲幅數字後故事的價格脈絡句也改成文字（故事不比依據多主張）。計數（`current_v2_briefs`）：寫死燈色 5 份 → 0、收盤價 9 → 0、故事燈色 1 → 0、故事還沒寫 0。第一次掃故事時迴圈走到 dict 的鍵、印出 0，改寫後才掃到 AAOI 那一處（L11-5：「沒命中」先問掃的是不是那份東西）。
- **換版後才發現的副作用**（#121）：判斷日的鍵含已定價那一格原文，11 份的判斷日被重設成 10-31，候選板印得出判斷日的 5 列都變成 10-31（4971.TWO 原 10-06、−26.5%；AAON 原 10-08、−22.6%；BW、PSIX、STLTECH.NS 原 10-28），STLTECH.NS 的已回落叫醒消失（materialize 後已回落 4 → 3）。換版前沒跑 L11-6「最先壞的那一筆」——這一輪的失誤。補償：`ew_1870`（11-01 醒，進「敘事該重寫」）；SKILL 段 5 加「不要只為了清字面值單獨換版」。修法（敘事選填 `restates`，判斷日與正文版遇到就跳回被重述的那一版）動 contract，是 Z2，提案給使用者、不自己做。
- **當下修一件不屬於這兩項的**：全套測試 `tests/test_engine_b_cli.py::test_trace_backlog_keeps_legacy_parked_trace_visible` 紅——10-30 交付缺 X 三分法時 trace backlog 多了五個 `review_*` 鍵，那次跑的是相關測試、沒跑這一支；補期望值。
- **研究佇列（不是開發驗收）**：等回落 4 檔的價格叫醒都已觸發（3081.TWO、4979.TWO、AXTI、STLTECH.NS），照新清單深挖後重答；先後看觸發時間。

**補記三（同日，使用者「修吧 修完我直接清空然後research drain?」）**：
- **#121 修好**（ROADMAP 旁支「只改字面值的換版不重設判斷日」）：敘事選填 `restates`，判斷日與正文版遇到就跳回被重述的那一版。動手前回放：新舊走法對 474 版 v2 敘事逐筆比對差異 0（現有紀錄都沒有這一欄，行為不變）。
- 13 份各補一版重述（文字照抄 10-31 字面值換版，`restates` 指換字前那一版）＋13 份故事照抄：判斷日／正文版／滯留起點 13／13 回到換版前；候選板 4971.TWO 判斷日 10-06（−26.5%）、AAON 10-08（−22.6%）、BW／PSIX／STLTECH.NS 10-28，已回落 3 → 4。補償叫醒 `ew_1870` 收掉（consumed，收據寫明被修法取代）。
- 這幾檔在 10-31 各有三版（換字前、字面值換版、重述）：中間那一版沒宣告，是修法之前寫的；之後只改字面值一律直接寫 `restates`（SKILL 段 5）。

## 十三、2026-10-31 晚（使用者 `/research-drain`、「繼續」）

**開工計數**（短版 ⑤）：待深挖 lead 31、未檢 23、叫醒擋下待確認 2、敘事該重寫 11、T2 命中待檢 8、停放未處置對照 9、接不上的等待 3、邊緣卻沒敘事 2。

**機械段**：consume-fired、todo sync、standing-go 跑完後未檢／叫醒擋下／T2／停放未處置全歸零。「接不上的等待 3」是假陽性——三則都是「向你要文件」型（[897]–[899] 都開著），收集器從 lead 推出 pq2 項目、lead 這端永遠不會回寫 `pq2_ref`；`todo_ledger.requires_user_without_pq2` 補讀待辦池未結案項目的 `ref_id`（對稱面同 `leads.parked_without_expiry`），3 → 0（測試 +1）。

**敘事該重寫 11 → 0**：等回落四檔的已回落叫醒照 ⓪ 重答——3081.TWO `ib_4ea3946ae2a167c7`（10-28 法說與 MOPS 簡報）、4979.TWO `ib_10c3162318d18749`、AXTI `ib_22424c1f01f6ca63`（騎 InP 基板 `sr_5bd84c00f10ad7da`）、STLTECH.NS `ib_f84942c958a64495`（Q2 FY27 簡報的在手訂單）——四檔仍「已定價等回落」，錨重設、叫醒照登；300395.SZ `ib_1c0bba935e67a6e4`、002270.SZ `ib_fbaef401915f3723` 讀第三季報告後仍缺 X（filing）；FormFactor 第三季法說後換版 `ib_db66057e95962670`（不要，判斷不變）。七則故事同步寫入、materialize。

**pq1 31 則全部停放**（`engine_b.cli drain` 順序；停放理由逐條處置直接命中的 watch）：一手拿到（`original_obtained`）21 則——京元電（MOPS：NVIDIA International, Inc. 預付＋Fort Worth 廠房；非邊緣 99.9 億美元／16 家，7 條 watch 不相關）、nVent 與 FormFactor 第三季法說、CCXI 8-K（贖回與募資；不要不變）、源杰與長飛第三季報告（長飛：預製棒層在位者缺席，日後 `ra_admission`）、AXT 四則（同源）、景碩兩則、光寶科五則、Lumentum Hurlston 專訪兩則；不追（`not_pursued`）8 則——日月光、Marvell–Lumentum 傳聞、三星 HBM4 法說（ew_0762 自述不觸及）、CXMT、緯穎、Prometheus、Amazon capex（錨只收 10-Q）、Intel 兩則、TrendForce DRAM；部分（`partial`＋收據）2 則——HD Hyundai Electric（DART 잠정실적拿到，新接單與在手訂單只有媒體轉述；ew_1332 判未達「轉為下滑」）、Hyosung Heavy（同形；ew_1332 方向相反）。DART 無 API key 的路（`dsab007/detailSearch.ax` → `main.do` 的 `viewDoc` → `viewer.do`）記在 `library/private/tmp/dart_simple.py`。一手節錄 23 份進 `library/raw/`。

**段 5 每檔閉環**（closure-gate 未到終局 3：LYC.AX、300943.SZ、AMKR）：
- LYC.AX：10-22 因家數 >12 撤回，10-31 `alpha edge` 回到 12 家（8.57B 美元）翻回邊緣、缺 brief。讀 10-28 的 2027 財年第一季季報（NdPr 2,082 噸創高、Dy＋Tb 23 噸、季營收 3.101 億澳元年增 55%、均價 102.1 澳元／公斤年增 88%、保底價覆蓋過半、12 月季停機一個月；節錄 `lynas_asx_quarterly_sept_2026_excerpt.txt`）與 2026 年報的分部（單一分部、全賣澳洲以外、沒有單一客戶揭露）與 JARE 貸款段。重發 `ib_514f4fefdd74a1d0`：缺 X（filing；`ew_1935` 2027-02-05 醒）——重稀土量距 JARE 確定採購規模還遠、已定價量不到；騎 `sr_6f81993effe57dcf` 不換；出現在數字裡了嗎寫入端擋「yes」（稽核區沒機械序列，印（尚無）就得答量不到），改量不到、文字寫明季報說的是價不是量。故事 `st_868a735a0adfb336`、首頁介紹補上。
- AMKR：10-29 因市值 104.9 億撤回，10-31 97.9 億／10 家翻回。第三季 10-Q 之後沒有新一手，照 10-29 那版重發 `ib_4ff1d4605b6fa314`（缺 X filing；`ew_1936` 2027-02-26 醒、可輪詢）；寫入端要求 `supersedes_id` 指最新一筆（撤回紀錄 `ib_29e6181d78ea931d`），不是被撤回的那版。故事 `st_9b7b2c810bc0704a`。
- 300943.SZ（春晖智控）：blocker 是讀圖格 `upstream_unavailable`「圖上沒有它供貨或開發的層」——它自己不坐任何層，座位在 38.69% 權益法投資的春晖仪表（收購其餘 61.31% 深交所「已问询」）。既不是補供貨邊、也不是需求側；誠實終局是 Abstention（刻意不主張、收購完成或終止時撤回重寫）。提案檔 `library/private/alpha/abstention_proposals/300943.SZ_readings_no_seat.json`，鑄 **[901]**（帶 `--company-id`，closure 認成掛在 pq2），等 go。
- MP 非邊緣（7.05B／16 家）不寫；#110 第 3 次（LYC.AX、AMKR 都是門檻 ±1 家／±10% 內翻轉），ROADMAP 旁支新增「邊緣門檻的遲滯與在門檻上計數器」○。

**段 4 走圖**：九型命中逐筆對 10-17／10-22／10-27／10-28 四份終局表（`library/private/wf_tmp/diff_gw_terminals_1031.py`），新命中 0；供給側未填 3／8 母體 <10 只印不判。

**收尾**：`engine_b.cli drain` 段 0–1 全零、pq1 空；短版 ⑤ 二十格全 0；`audit invariants --only QueueSegments` PASS；closure-gate closed（到終局 76／顯式跳過 1：300943.SZ 掛 [901]）；候選板可開 0／缺 X 38／等回落 4／不要 46／已持有 2／無敘事 106（可開為零就零）。watch 計數器非零但不是待做：停滯 3、到期 3（都已有 `expiry_resolution`，同 10-30）。全量 materialize 197/197 後重啟 8790，health `code.stale=false`。相關測試 237 passed（todo_ledger、heartbeat、daily digest、webapp request path）。新鑄 pq2：[901] 一筆；新 watch：`ew_1935`（Lynas）、`ew_1936`（Amkor）。decompose：本輪沒有新錨提案（距上次掃題材 4 天，門檻 7 天）。

**發現未排程**：
- 寫入端對 `answers.in_numbers=yes` 的檢查（稽核區沒值就得答量不到）是對的，但澳洲申報人的季報本身就是一手數字——「系統量不到」與「文件寫了」在敘事裡要分兩句寫，LYC.AX 這版照此寫（1 例，不排程）。
- `--company-id` 鑄的 manual pq2 不會讓 closure 認成 defer（`deferred_tickers` 只看 `deferred_at`，要使用者 pending 過才有）；本輪照 10-30 先例用 `closure-gate --skip` 顯式宣告，理由寫在這裡（1 例，不排程）。

**補記（同日，使用者「901 go」）**：`alpha abstention 300943.SZ --add` 寫入 `ab_138a198261325ab2`，[901] 以收據 `authority:abstention_ledger;ref:ab_138a198261325ab2` 結案；materialize 後 300943.SZ 的讀圖格 `deliberate_abstention`（settled），closure-gate **不帶 skip 也 closed（每一檔都到終局）**；8790 重啟、health `code.stale=false`。
- 發現未排程：Abstention 的 `readings` 層 subject 字彙只有 `demand_side`（「它在需求側、不坐任何層」），寫入端拒收提案原本的 `no_seat_until_acquisition`；控股端（座位在參股公司）符合它的操作意義「不坐任何層」但不是買方——改用 `demand_side` 並在理由第一句寫明取的是哪一半。要不要把字彙拆成「需求側」與「沒有座位」兩個 subject 是 contract 題（Z2），1 例，不排程；第 2 例再提。

## 十四、2026-11-01 凌晨（使用者 `/research-drain`）

**開工計數**（`engine_b.cli drain` 首行）：段 1 反證待檢 7、叫醒擋下待確認 6、敘事該重寫 3（三條就是被叫醒的 brief 來源 watch，不是另外三檔）；段 5 到終局 77／77；pq1 空；待辦池 13（向你要文件 3、等事件 10、待你決定 0）。外面新進 lead 0。

**機械段**：consume-fired 0、todo sync 新增 0、standing-go 候選 0。sync 裡的 `check_watches` 叫醒 16 次，全部來自 10-30 晚景碩與光寶科的董事會重訊（已在 10-31 drain 停放的那幾則）。

**反證待檢 7＋敘事該重寫 3 → 0**：兩份重訊各叫醒一組語意 watch——景碩「限制員工權利新股收買註銷」（員工未達既得條件、註銷 10,200 股、減資 102,000 元、比率 0.00%）叫醒玻璃核心載板／低 CTE 玻纖布／帶載體極薄銅箔／德福／載板降價 9 條（ew_0421、1159、1160、1161、1341、1342、1348、1389、1505）；光寶科「對 LITE-ON VIETNAM CO., LTD. 現金增資 1.1 億美元、用途『產能擴增支出需求』」叫醒 LIDR 敘事的 AEye 反證 ew_1595。全文都讀（MOPS 重訊自帶 raw_text），一條都沒觸及，逐組 `judge --touches no` 回 active；三條 brief 來源（ew_1348／1389／1595）同時離開「敘事該重寫」，301511.SZ、1802.TW、LIDR 三檔敘事不改。

**叫醒擋下待確認 6 → 0**：景碩 598 億專案資本支出（只寫「為擴充營運所需」、依客戶需求彈性調整）叫醒讀圖 ew_0416（玻纖布層等需求側客戶）與追源 ew_1919；光寶科兩則越南子公司增資（2.1 億＋1.1 億美元，只寫「產能擴增」）叫醒追源 ew_1920、1922、1923、1924。六條 `wake-judge --touches no`，lead 照舊停放、停放理由一字不動（本來就含這幾則）。預篩還沒跑（daily 05:15 才跑），「判定一致」計分這六筆不算。

**段 5**：closure-gate exit 0（到終局 77：ready 76／settled 1；母體外 119：非倍率 106、邊緣沒座位已查 13）。**段 4 走圖**：55 筆命中逐筆對 10-17／10-22／10-27／10-28 四份終局表（`library/private/wf_tmp/diff_gw_terminals_1101.py`），新命中 0；供給側未填 3／8 母體 <10 只印不判。**故事**：缺 0。**T2 命中**：0。

**停止條件成立**：drain 段 0–1 全零、pq1 空；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；`audit invariants --only QueueSegments` PASS；短版 ⑤ 二十格全 0；候選板可開 0／缺 X 38（已開口 3｜可拿未開口 0｜未分 33）／等回落 4（已回落 0）／不要 46／已持有 2。非零但不是待做：停滯 3、到期 3（同 10-31）；「追源需處置 1」＝ew_0092（AMD Helios CPO 推文的 related_entity_signal，09-17 Phase 6 補期限那批：標的已消化過一輪、等 2027-01-15 到期由使用者決定）——`TRACE_NEEDS_ATTENTION_STATES` 把 stalled 算進「需處置」，而它自己的 wake_state_reason 寫「不需要人決定」（L12 的形狀，1 例，不排程；第 2 例再提）。

**發現並當下修（failure log #122）**：ew_1919–1924 被同一場董事會的 sibling 重訊叫醒，根因是「published_at 早於建立日就不叫醒」那道閘拿 `created_at[:10]`（UTC 日期）去對 MOPS 的台北日期——停放時建的追源 watch `created_at`＝lead 進 pq1 的時間（daily 05:43 台北＝10-30 21:43Z），UTC 10-30 對台北 10-30 算「不早於」；entity 型與語意型兩個 matcher 各寫一份、都錯。反向對 EDGAR 是靜默漏接（台北 08:00–12:00 建的 watch 把前一晚美東的 8-K 當回補舊文件擋掉；還沒撞到實例）。修法：`_created_day` 把建立時刻換算到 published_at 那本日曆（`mops:`→Asia/Taipei、`edgar:`／sec.gov→America/New_York、其餘 UTC 不變）。重播今天 16 次叫醒（`library/private/tmp/replay_wakes_1101.py`）：5 次不發生、11 次照舊；`tests/test_published_calendar.py` 7 條。段 5.5 ④ 三問：不改使用者能核准什麼／是「同一本日曆上比」（MOPS 收緊、EDGAR 邊界補漏，不是放寬）／不動封閉字彙、無第二 owner → 當下修。

**收尾**：全量 materialize 197/197（候選板可開 0／缺 X 38／等回落 4／不要 46／已持有 2／無敘事 106）後重啟 8790（00:59，health `code.stale=false`）；writer lock 釋放。測試：`test_published_calendar`＋`test_semantic_watch`＋`test_trace_wait_plan` 87 passed；`-k "watch or wake or queue_segments or heartbeat or todo_ledger or daily_digest or semantic"` 578 passed（3911 deselected）。decompose 本輪無新 lead、無新錨提案；距上次掃題材 5 天（門檻 7）。新鑄 pq2：0；新 watch：0；敘事改動：0。順手更正 research-drain SKILL 兩處「`writer_guard verify`」（子命令不存在，實際是 `check`）。

## 十五、2026-11-01 早（使用者 `/research-drain`）

**開工計數**（短版 ⑤）：待深挖 lead 17、未檢 1、敘事該重寫 2（watch 醒 2；非邊緣仍有敘事 1）、T2 命中待檢 2（1 條等待）；段 5 到終局 77／77；待辦池 13（向你要文件 3、等事件 10）。

**機械段**：consume-fired 0、todo sync 新增 0（watch 812；反證對帳「沒有結構化反證 3」由 Step 1.6 補登記）、standing-go 候選 0。

**段 1**：上詮 10-30 重訊（子公司中山上詮總經理退休、特助兼業務副總暫代）叫醒 FAU 層讀圖反證 ew_1079 與上詮敘事的 ew_1123／ew_1124（後兩條就是「敘事該重寫 2」）——全文讀過，一組 `judge --touches no` 回 active，敘事不改。**T2 命中**：ew_1540（MTAR 敘事等 FY27 第二季結果）被 Yahoo／GuruFocus 10-30 法說摘要命中，判觸及 → 敘事列進該重寫。

**敘事該重寫 → MTAR 重寫** `ib_6873140c653e5741`（取代 `ib_75bcc730d2ee5609`；故事 `st_04b78a86c59511c4`）：一手讀了 10-29 新聞稿與未審計財報（兩家全資子公司併入、單一分部）、10-30 更正版投資人簡報（NSE 附件，更正第 9、10 頁營收分類與第 15 頁訂單）、Bloom 10-22 第三季 8-K（營收年增 138%、全年指引上修到 44–46 億美元）。第二季營收 40.68 億盧比（年增 200%）、在手 597.65 億（清潔能源 407.55 億、占 67%）、Kaiga 核電 50.4 億與 SLB 資料中心鈑金首件 4.5 億的單、第二期 11 月底／第三期 2027-03 擴產、全年指引營收 +80%；營運資金天數 172→50、營業現金流 35 億，但借款 36.93→46.63 億、現金 0.03 億。候選狀態仍缺 X（`missing_kind=layer`：插槽讀圖兩半——Bloom 的買方為什麼選 SOFC、Bloom 的第二來源；燃料電池仍沒單拆、大單客戶與交期沒寫、法說逐字稿未申報）；ew_1540 以 `still_holds` 處置，新叫醒 `ew_1951`（2027-02-14 第三季結果，可輪詢）。插槽讀圖 `sr_db33dc55748a1ff2` 不換騎（Bloom 第三季新聞稿沒有第二來源或買方理由）。故事第一版「必須為真」178 字被寫入端擋（上限 160），拿掉日期與出處後過。

**非邊緣仍有敘事 1 → LYC.AX 撤回** `ib_6197543b76dce17f`（撤 10-31 的 `ib_514f4fefdd74a1d0`）：`alpha edge LYC.AX` → 13 家、8.57B 美元、coverage_over_edge；照 10-31 寫下的規則撤回、不加遲滯（failure log #110 第 4 次：門檻 ±1 家翻轉——10-22 撤、10-31 發、11-01 再撤）。

**pq1 17 則全部停放**（`drain` 順序；每則逐條處置 `engine_b.impact` 列出的在盯條件，`library/private/tmp/park.py`）：一手取得 4——源杰三季報的新浪二手（一手 10-31 已入庫，同源 lead_b7510a6f）、NVIDIA 10-21 供應鏈產能新聞稿（SPIL CPO 光引擎 15 倍，已在庫；OOI 仍研究階段）、GXO–Agility 擴站聯合新聞稿（Statesville、Lebanon，2027 年初 Digit 4；節錄 `gxo_agility_expansion_statesville_lebanon_2026_10_26`）、Oracle 10-28 Investor Day 8-K（FY30 營收 2,250 億美元以上、籌資上限 200 億；報導寫的 800 億 RPO 不在 8-K）；不追 13——carrioresearch 五則評論（AXT／Marvell–Lumentum 傳聞、中國光模組、Lumentum 3-2 協議重述、SK 海力士 14 家長約、MSFT／AMZN capex）、Terafab 追加報導（原文沒搜到；等待已由 lead_0f6a3beb 的 ew_1456 持有）、Advantest 與 Trane 財報（名冊外、非邊緣）、鴻海／Altman 媒體轉述、CoWoS 漲價傳聞、美光獎金、上詮人事重訊。一手節錄 6 份進 `library/raw/`。

**段 4 走圖**：55 筆命中逐筆對四份終局表（`diff_gw_terminals_1101.py`），新命中 0。

**段 5**：全量 materialize 197/197 後 closure-gate **closed、不帶 skip**（到終局 77：ready 76／settled 1；母體外 120：非倍率 107（LYC.AX 撤回後歸這裡）、邊緣沒座位已查 13、等入圖 0、等主題組 0）。

**停止條件成立**：`engine_b.cli drain` 段 0–1 全零、pq1 空（triaged_go 0）；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；`audit invariants --only QueueSegments` PASS；短版 ⑤ 二十格全 0（`library/private/tmp/ledger_cells.py`，與心跳同一份判定；全量重算後再印一次仍全 0）；候選板可開 0／缺 X 37／等回落 4／不要 46／已持有 2／無敘事 107（可開為零就零）。非零但不是待做：停滯 3、到期 3（同 10-31，都已有 `expiry_resolution`）。8790 重啟（09:08，health `code.stale=false`）；writer lock 釋放。新鑄 pq2：0；新 watch：`ew_1951`（MTAR）；敘事改動：MTAR 換版、LYC.AX 撤回；故事：MTAR 一則。測試：`test_source_routes` 12 passed。decompose：本輪 17 則 lead 的需求錨都是 AI capex 或人形放量，無新錨提案；距上次掃題材 5 天（門檻 7）。

**發現未排程**：
- BSE 公告 API（source_routes 10-23 實測可用）今天用 repo 預設 UA 回 Akamai 403「Access Denied」；NSE 的 `/api/corporate-announcements?index=equities&symbol=` 帶瀏覽器 UA 可直接打（首頁 403 無妨），附件在 nsearchives 可下載——`config/source_routes.json` 新增 `nse_india`（verified）、`bse_india` 標回未驗證（當下修，Z0 設定；`test_source_routes` 12 passed）。
- 投資人簡報同日兩版（MTAR 首版 00:30、更正版 17:35，更正營收分類與訂單頁）：抓 NSE 清單時取同日最後一筆、不是第一筆——寫進 nse_india 的 how（1 例）。
- LYC.AX 門檻 ±1 家第三次翻轉（10-22 撤、10-31 發、11-01 再撤）：ROADMAP 旁支「邊緣門檻的遲滯與在門檻上計數器」○ 已有，不重列；本輪照 10-31 寫下的規則撤回。
- Bloom 10-22 第三季 8-K（Items 2.02／7.01）不在 lead 池：co:bloom_energy 的 entity watch（ew_1490／1492）仍 active、沒被它叫醒——EDGAR harvest 是否涵蓋 Bloom 這家非邊緣在位者，下次 daily 看 harvest-health 再判（1 例，不排程）。

## 十六、2026-11-04（使用者 `/research-drain`；中途壓縮一次，接著做完）

**開工計數**（當天 daily 的短版 ⑤）：未 triage 3、待深挖 lead 84、未檢 64、叫醒擋下待確認 31、敘事該重寫 15、讀圖該重讀 1、層說明該重讀 1、T2 命中待檢 4、邊緣卻沒敘事 1、加碼條件還沒查 2。

**前半（已在 `dc8aeaaa`）**：段 0–1 歸零；AEHR、002428.SZ、300570.SZ、VNP.TO 照 11-03 兩道門由缺 X 改宣告可開（各補逾期型反證）；深挖清單引文帶註記時逐一核對每個路徑（當下修）；Q3W 兩行裁決；[902] 抽中、乾淨 context 唯讀核完。

**中段**：外部光源層說明換版 `ln_c5aad8f09b6b8bc7`（Lumentum 11-02 兩份 8-K）；`materialize --structure-readings` 後讀圖／層說明該重讀歸零；七份斷鏈敘事換騎（2455.TW、3234.TWO、688313.SS、COHR、SIVE.ST 等，故事一起換）；等回落（11-03 已併回可開）的 3081.TWO、4979.TWO、AXTI、STLTECH.NS 重新宣告可開、深挖清單十項查完——新讀聯亞兩張可轉債條件、華星光第二季合併報表、AIXTRON 九個月報、STL 的 FY26 年報主要客戶與 Q2 FY27 結果表股本附註；AXTI 的 Q3W 一行。STL 那一版把 crore 寫成「億」（差十倍），同日 restates 更正（failure log #125）。

**後段（壓縮之後）**：
- **SIVE.ST**（已持有）`ib_fa3a9fa2c100bf44`：仍缺 X，補 `missing_kind=filing`——起始門卡在會死嗎：會計師 2025 年報查核報告的持續經營重大不確定性（2026-05-13），現金跑道與負債照 6 月 30 日資產負債表；同一份季報寫了期後約 7 億克朗的定向增發、8 月起沒有計息債務，要 11-26 第三季報告才進燈。深挖清單十項（新讀 2025 年報 Note 5：三家各過一成的客戶合計約六成、全在無線）；ELS 時間表那條標成逾期型；加碼條件 c3（為什麼選它）。圖上家數照讀圖現值改成 13。
- **002428.SZ、300570.SZ、VNP.TO** 只補「最新一場法說的逐字」（restates）：A 股走巨潮 `tabName=relation` 的投資者關係活動記錄表（09-11 調研、10-30 走進成份股），VNP 的 11-03 法說經抓取工具轉錄（本機下載 403）——三份讀過都沒有和七格相反的內容。
- **600118.SS 第一份敘事** `ib_6bf6ff97b579848f`：不要、不押讀圖（它不在電池片層的供給側，寫入端擋下押讀圖）——持股一半併表的天津恒电上半年營收 2.84 億元、約占集團一成五、比去年同期少約 44%，同期買方電科藍天營收年增 32.09%；判準與同層的三安、乾照一致；附首頁介紹。
- **SILEX.ST** 第三季報告（11-04）後 `ib_ec150dd0b2b4ab98`：缺 X → 可開——第一次寫出 OCS 約占總營收三成；客戶點名與 Lumentum 鏡片來源改列加碼條件 c1、c2；逾期型反證：2027-06-30 前開發中的 OCS 客戶沒有一家轉量產；Q3W 一行（寫的時候沒看價格）。
- **量測抽樣①**：種子 2026-11-04 抽中 4991.TWO `ib_3a006e2f3d922739`，36 句、事實錯 0、無引用 1。
- **段 4 走圖**：55 筆命中對 10-17／10-22／10-27／10-28 四份終局表，新命中 0。**故事**：缺 0。

**發現未排程**：
- 人工核准的邊屬性決議到不了讀圖工具（9／24 印出來的與決議不同）——brainstorm `2026-10-28-app-attention-ia` F19，ROADMAP 候選。
- 巨潮 hisAnnouncement/query 可用、`tabName=relation` 就是 A 股投資者關係紀錄：`config/source_routes.json` 新增 `cninfo`（verified），深交所那條 09-11「CNINFO 被擋、不要再試」改成有日期的史實（當下修，Z0 設定；`test_source_routes`＋`test_config_tracking` 27 passed）。同日前半曾把兩檔寫成「互動易沒有路線」——是沒試（L11-5）。
- 會死嗎的燈只認最近一期資產負債表：期後事項（同一份季報寫的增資、還債）要等下一期才進燈——SIVE.ST 1 例，照 INV-6 是對的行為，只在敘事寫明。
- 瑞典申報人的會死嗎多半只亮得起負債一盞（現金跑道缺自由現金流、going concern 要有人讀查核報告、稀釋查法不適用）：SILEX 1 例（負債那盞亮、所以不是 fail closed）。
- 法說逐字稿站（Investing.com、Benzinga、GuruFocus）本機下載 403，經抓取工具轉錄可讀——節錄的 STORAGE 標明「本機沒核到原文」（SILEX、VNP 2 例）。
- COHR 的 Q3W 到點未寫：FY27 第一季財報在美東 11-04 盤後（台北 11-05 清晨），本輪寫不了。

**停止條件成立**：`engine_b.cli drain` 段 0–1 全零、pq1 空（段 5 到終局 76／未到終局 0）；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；`audit invariants --only QueueSegments` PASS；closure-gate exit 0；短版 ⑤ 二十二格全 0（全量 materialize 197/197 之後的心跳）；候選板可開 9／缺 X 32／不要 47／已持有 2／無敘事 106。本日候選狀態移動：缺 X → 可開 5（AEHR、002428.SZ、300570.SZ、VNP.TO、SILEX.ST）、等回落（舊版）→ 可開 4（3081.TWO、4979.TWO、AXTI、STLTECH.NS）、無敘事 → 不要 1（600118.SS）；SIVE.ST 仍缺 X。非零但不是待做：停滯 3、到期 3（同 10-31）；追源需處置 1＝ew_0092（同 11-01）；健康紅燈 1＝AXTI thesis 在 review_required，等 Q3 10-Q 一起複查（[896]，11-16）；逾期型反證 0 條的持有／可開敘事 6 → 1，剩 COHR——非倍率持股的反證住 thesis，補要走 thesis mutation（[836] 財報後改寫 lane memo 時一起提），不拿敘事代寫；Q3W 到點未寫 1：COHR（上一條）。8790 重啟（18:51，health `code.stale=false`）；writer lock 釋放。新鑄 pq2（全日）：[902]、[903]、[904]。decompose：本輪沒有新錨提案（CPO 耦合／對位設備在 AI capex 錨內，要不要拆是使用者選題）；距上次掃題材 8 天（門檻 7），本輪不掃。

## 十七、2026-11-04 晚（使用者「902 903 904 go」「建議現在做的可以做掉」；中途壓縮一次）

**go 三筆**：[902] 入圖（雲南鍺業子公司雲南鑫耀→AOI 2027–2031 磷化銦基板長約，`5ed67877`）、[904] 入圖（Tower→中際旭創 NPO 早期量產，`74e34c05`）、[903] 名冊登記羅博特科 300757.SZ（含全資子公司 ficonTEC；只登記身分，`caf47864`）。

**「建議現在做」＝F19**：人工核准的屬性決議走到讀圖工具（`1e8735aa`，本機 commit、**未 push**）——真資料 28／28 份決議生效、讀圖工具印的與決議不同 9 → 0；投影漂移 9 → 0（全量重投影，failure log #126）；全套 4795 passed。Phase 7 開發 Step 常規 R2 回 **CONDITIONAL_GO**：F1 更正走廊重載後「證據等級預告」「圖影響」會降級（`rows_after_load` 不帶 `source_ids`；16 份文件、39 筆 supporting 引用暴露）、F2 一份決議的 supporting 來源被更正改掉時所有預設收斂都 raise（要使用者選：全域 fail closed，或逐條隔離）、F3–F7 非阻斷——等使用者決定，F19 不 push。

**下游換版**（F19 讓讀圖工具改印核准值）：
- 讀圖六份換版、判讀都不改：諧波減速機 `sr_bc71af9008edae9e`、稀土磁材 `sr_f6888e317022f5ea`、CW DFB 雷射 `sr_4f1640e81bd5f841`、外部光源 `sr_0103be4fc3ede304`、CPO `sr_b38454c20adc3ceb`、NPO `sr_f374bdfe9a32e5d5`；三份 neither（外部光源、CPO、NPO）照 11-03 盲點修法第 12 條補標引用 basis（buyer_policy：Meta 的 multi-sourcing／multi-vendor；buyer_fact：NVIDIA 部落格點名三家；third_party：Broadcom 生態系；media：TechNews 轉述台積電）。
- 敘事 21 份換版：只換連結 10 份（2455.TW、3081.TWO、3234.TWO、4979.TWO、6680.HK、688313.SS、9856.HK、COHR、SIVE.ST、USAR）；HIMX、6324.T 換騎時被「量得到就要答」擋下，已定價改答 yes（自家歷史百分位 81.5、82.4），6324.T 出現在數字裡改答 no；AEVA「卡在哪」補 NPO 供給側三家、中際旭創進入早期量產；「量不到」但稽核區今天有值 12 筆（7 檔：2768.T、5411.T、6268.T、5706.T、3110.T、ARBE、POET）→ 0；AAOI 讀 [902] 新邊（長約是它自己雷射產線的料，不是客戶端具名，「不要」不變）。5411.T 順手更正「GO 供貨邊已打包等入圖」——那條邊 10-07 已入圖。故事缺 0。

**羅博特科短檢查**（closure-gate 唯一擋著的一檔：邊緣、沒座位、沒敘事）：在深股通合資格名單上（HKEX 11-04 版）；讀 2025 年報、2026 半年報的業務段與客戶段，和兩份重大合同公告（2026-028、2026-043）。結論①補供貨邊：半年報「在 CPO 领域」段寫 ficonTEC 配合核心客戶完成雙面晶圓測試與晶粒測試設備的驗證後，取得多筆量產訂單、部分已確收——坐圖上既有的「CPO 全堆疊測試」層（第四家）。營收大宗是耦合封裝設備（同一集團客戶累計約 12.61 億元訂單；兩份公告的交易對手豁免披露），圖上沒有對應的層；「CPO 封裝與系統組裝」「模組組裝」兩層的供給側是代工組裝廠，掛上去會讓一條邊承載兩種意思（L12），所以不掛——要不要拆一層是使用者的 decompose 選題。入圖包 `ra_037389be0a373658d44aa3ff42425f68` 鑄 [905]（乾跑兩次都乾淨才正式跑一次；九句引文由產生器斷言是半年報抽字的子字串；抽查沒抽中）；自家庫命中 1 份 TrendForce 10-13 節錄（第三方的能力描述，只當脈絡）。closure-gate 列「等入圖（[905]）」。

**發現**：
- F20「量不到」過期沒人點名（寫入端只在換版時擋，9 檔）、F21 故事層沒有「已定價位置詞要帶日期」的檢查（20／90 份）、F22 投影漂移根因（1 次）——brainstorm `2026-10-28-app-attention-ia` 的開發候選，未排程。
- ⑤「邊緣卻沒敘事」不認等入圖（#51 的對稱面，第 2 次；failure log #127）：當下修——閉環佇列與 ⑤ 共用 `pending_admission_tickers`，⑤ 扣掉等入圖的檔、在註記點名；測試 2 條、變異 2 個都紅。

**停止條件成立**：`engine_b.cli drain` 段 0–1 全零、pq1 空（段 5 到終局 76／未到終局 0；母體外 121＝非倍率 106、邊緣沒座位已查 14、等入圖 1）；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；`audit invariants --only QueueSegments` PASS；closure-gate exit 0；短版 ⑤ 二十二格全 0（「邊緣卻沒敘事」註記 300757.SZ 等入圖 [905]）；候選板可開 9／缺 X 32／不要 47／已持有 2／無敘事 107（全量 materialize 203/203）。非零但不是待做：停滯 3、到期 3（同上一節）。新鑄 pq2：[905]。距上次掃題材 8 天（門檻 7），本輪不掃。

## 十八、2026-11-05（使用者「905 go；『核准決議走到讀圖』照審查建議修，條件二選 b」「到期 thesis 核查現在包含在 research drain 裡面嗎？是不是應該包？」`/research-drain`；中途壓縮兩次）

**開工計數**（當天 daily 短版 ⑤）：待深挖 lead 35、未檢 73、叫醒擋下待確認 10、敘事該重寫 14（watch 醒 17；前提失效 5）、讀圖該重讀 5、假設對照 1。

**go 與條件**：[905] 入圖（羅博特科→CPO 全堆疊測試層，第四家；公開檔發布等 push 後 `commit_pending_intake`＋`complete-ra`）。F19 的 R2 條件照審查建議修、條件二選 b（`16050fbe`：入圖預告重建列帶 `source_ids`；決議失效只隔離那一格；「不給值」不再當未填），條件覆核 GO。

**到期 thesis 核查**：連紅 6 天的那盞是 AXTI——review_required、[896] 已掛號等 11-16 的 Q3 10-Q，沒有人做得了事；健康審查不分「已掛號等有日期事件」與「沒人管」（failure log #128，`b48837b0`）。沒掛號的照舊進 ⑤「thesis 該核查未進 pq2」，drain 本來就包。

**COHR**：[836] thesis v3 lane memo＋變更提案 [906]（revised → active、next_check 2027-02-12）；Q3W 裁決 COHR；envelope schema 收 `disproof_conditions`（failure log #129，`a6d8c357`）。AEVA 第三季 8-K 節錄、敘事換版 `ib_a960b37256a0b890`（反證③觸及：光互連第一筆營收是交付聯合開發客戶做驗證；仍不要，③改盯量產出貨）。

**段 0–1**：未檢、叫醒擋下判完；讀圖重讀 5 份、判讀與家數都沒變——InP 基板 `sr_36505176157af3f8`（反證⑥觸及：翻倍的是 Coherent 的元件晶圓廠、不是自供基板，⑥改寫成只算自製基板）、InP DFB `sr_ab7dec2b636728f7`（反證②觸及：擴產第一段落地、缺口沒跟著消失）、光模組 DSP `sr_72dff6c738f4e7f4`、半導體設備 `sr_c768e47d0a2b111f`（GF 第三季 6-K）、六吋 InP `sr_f9f07562a7d9d36a`；換騎 002428.SZ、300489.SZ、AXTI（InP 基板）、MXL（DSP；寫入端擋下「最貴」補日期），故事跟著換。

**pq1**：43 則停放（一手已取得 21、判不追 15、部分取得 4、等具名揭露 2、一手照轉 1）＋1 包 [907]（環宇 4991.TWO 開發 70／100mW CW 雷射——CW DFB 層的 develops 邊；`ra_b6400e3ccedb583120388ea3f0f7a87e`）。環宇第三季公告那則掛日期 watch `ew_2166`（11-16 起查 MOPS 產品別營收、對 ew_1255）。停放時撞到 failure log #130：觸發寫「無」又明示空標的會落成日期 watch、已明示不等的 lead 舊追源 watch 醒了照樣排回——當下修，測試 2 條、變異 4 個全紅。

**段 5**：[905] 入圖後全堆疊測試層換版 `sr_fb7269d0f5f6fece`（undecided 不變、供給側 3 → 4）；AEHR、FORM 換騎（只改「卡在哪」的家數）。**300757.SZ 第一份敘事：可開**——押全堆疊測試層（undecided）；逾期型反證：2027-04-30 前年報寫不出 CPO 測試新量產訂單或客戶；加碼條件 c1 客戶端或第三方一手點名 ficonTEC、c2 測試設備拆出且占光電子兩成以上。四份一手節錄（三季報、10-28 投資者關係活動記錄表、2025 年報、H 股超額配售公告）每句引文寫入前斷言是原文抽字；短標「光模組耦合與測試設備」。

**量測抽樣①**：種子 2026-11-05 抽中 300757.SZ 第一版（同日自己寫的，不盲）——39 句、事實錯 2（「一家」海外核心客戶，原文沒寫幾家；把 TrendForce 的 CPO **測試**架構收斂寫成 CPO 架構）、無引用 3（「營收大宗是耦合與組裝設備」兩句是沒標的推論——營收沒拆，只有訂單撐得起「已知最大的一筆」；法定期限一句）。同日改版 `ib_4c0f62346f9acdf9`。上一節「營收大宗是耦合封裝設備」是同一個推論，史實不改。TrendForce 新聞稿當天重抓全文核「七段、每段點名多家」：每段對得到至少兩家，歸段是我們做的。

**收尾物化撞到 failure log #131**：300757 已定價答 yes、稽核區四行全缺席——寫入端收下、候選板當天判前提失效。寫入端 ⑥ 補上候選板那條的對稱面（測試 1 條、變異 4 個全紅、真實資料試送第二版只報這一條）；第三版 `ib_c8afaa3f507dbed3` 改答 unmeasurable（同 002428.SZ、300570.SZ），回到可開。

**停止條件成立**：`engine_b.cli drain` 段 0–1 全零、pq1 空（段 5 到終局 77／未到終局 0；母體外 120＝非倍率 106、邊緣沒座位已查 14、等入圖 0）；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；`audit invariants --only QueueSegments` PASS；closure-gate exit 0；⑤ 二十二格全 0（重新物化讀圖與候選板之後——收尾前那份心跳讀的是早上的板，印「讀圖該重讀 5」「前提失效 5」都是舊數）；走圖 55 筆命中、新命中 0；候選板可開 10／缺 X 32／不要 47／已持有 2／無敘事 106。**本段候選狀態移動 6**：前提失效 → 可開 5（002428.SZ、AXTI：押的 InP 基板讀圖換版後換騎；3081.TWO、4979.TWO、SILEX.ST：名下醒來的反證 watch 判完不觸及）、無敘事 → 可開 1（300757.SZ）；**鑄 ra_admission 1**（[907]）。非零但不是待做：停滯 3、到期 3；追源需處置 1＝ew_0092（AMD Helios CPO 推文，2027-01-15 到期兜底）。新鑄 pq2：[906]、[907]。距上次掃題材 9 天（門檻 7），本輪不掃。

## 十九、2026-11-06（使用者「可以push 906 907 go」）

**push 與 [905]**：本機領先的 11 筆 push（`caf47864..6e659610`）；[905] 發布 `a87c52ec`、`complete-ra 905` 結案。

**[906]**：`complete-thesis-mutation 906`——COHR thesis（coherent_cpo）revised → active、下次核查 2027-02-12。提案理由寫明的 memo 指標 v2 → v3、檢核點換成三個（2027-02 第二季、2027-05 第三季、2028-02 財報），`apply_proposal` 不支援，照核准內容手補（failure log #132，修法要你點頭）；`todo sync` 反證對帳收掉 v2 的 ew_0102–0106、登記 v3 的 ew_2191–2195，`audit invariants --only Orphans` PASS（`99e1ebde`）。

**[907]**：經 `scripts/apply_ra_admission.py` 入圖（環宇 develops CW DFB 雷射層）、發布 `cfb21bdf`、`complete-ra 907` 結案。下游：CW DFB 讀圖換版 `sr_66fd90d4e2384bd9`——判讀 volume 不變（開發者 1 → 2、供給側 13 家不變；環宇只寫研發與「規劃」後段產線，反證①要的量、產能或開出時點沒寫，未觸發）；七檔只換連結（COHR、SIVE.ST、2455.TW、3234.TWO、688313.SS、3081.TWO、4979.TWO），4979.TWO 同版處置三條被 11-05 可轉債注意交易公告叫醒的 watch（ew_2098／2099／2100，still_holds）；故事照抄改指新版；3081.TWO、4979.TWO 由前提失效回到可開。4991.TWO 不換騎：它在這一層只在開發者角度、不在供給側，寫入端也不讓押。

**沒做**：當天 daily 帶進來的待深挖 lead 49、未檢 44、叫醒擋下待確認 23、watch 醒來的敘事 9 檔（含 002428.SZ、SILEX.ST 的前提失效）、T2 命中 1、邊緣卻沒敘事 2（5801.T、INIO）——daily 判「只剩維護」，留給下一段 drain。候選板可開 8／缺 X 32／不要 47／已持有 2／無敘事 106；故事缺 0。

## 二十、2026-11-06 下午到晚上（使用者「掃題材 然後 /research-drain」；中途壓縮兩次）

**開工計數**：接上一節的「沒做」。

**掃題材**（`566102df`；上一份 10-27）：`docs/reports/theme_scan_2026-11-06.md`，WebSearch 19、WebFetch 6。註冊兩則 lead——MLCC（村田五年約 1 兆日圓、因 AI 伺服器用量婉拒部分訂單；圖上沒有的一層，MLCC 本身是大型股寡占，要看的是上游陶瓷粉體與鎳粉是不是更薄的一層）、日立能源 10-22 巴西套管與分接開關新廠（圖上兩層的供給側擴產，華明裝備 002270.SZ 騎分接開關層）；AI capex 錨的反向叢集只當脈絡（錨層級的反證在 [900]）。沒有新需求錨、沒有 onboard 提名。

**段 0–1**：未檢、叫醒擋下照組判完；10:50:41 UTC 語意佇列又醒 24 筆，同輪判完（為什麼又醒沒查）。SILEX.ST 騎的 MEMS 鏡陣列讀圖兩條反證（ew_1367、ew_1370）被 Alphabet 11-05 的 8-K（60 億歐元票據）叫醒、判不觸及——前提失效解除。PSIX 的 ew_1887（敘事第 3 條反證：10-Q 寫資料中心銷售下半年沒改善，或兩個大客戶任一停單）：PSI 是語意叫不醒的美股實體，10-Q 自動叫不醒，人工讀第三季 10-Q、結果寫在停放理由。ew_0068（Google OCS 鏡陣列代工具名的事實核對）的實體含 LITE／Lumentum，任何 Lumentum 的 lead 都叫醒它——今天又一次雜訊。

**pq1**：60 則停放（一手已取得 29、判不追 26、部分取得 2、一手照轉 2、與一手矛盾 1）＋1 包——
- [908] `ra_e39a7d6a285d4995024bff19a206ea53`：模組 DSP 層補一條買方邊。新易盛（300502.SZ）10-29 投資者關係活動記錄表被問「DSP 等核心物料緊張」，答原材料整體偏緊、不局限於單一物料、核心原材料備貨週期拉長、第三季受一定影響——讀圖缺的那一半（第一份書面的買方一手）。要你判斷的是：沒自己寫出 DSP，算不算。
- AAOI 第三季 8-K 與 10-Q：O4 第一個裁決點「量撐住了、具名還沒有」（`cases.md`）；ATM 缺口回答了（lead_49085eb7 由 `contradicts` 改 `original_obtained`），8 月 TLDR「第四季逾 5 億美元」被指引推翻（lead_20eb32ac，與一手矛盾）。敘事不換版。

**段 5**：
- **002428.SZ** `ib_d4bd15eef71f00d8`：加碼條件 c1 由 AOI 11-05 的 10-Q 確認（買方一手、金額一致、沒具名）；需求與時點兩格改寫、深挖清單核心前提改引 AOI 10-Q，判讀與候選狀態不變——前提失效解除、仍可開。
- **3363.TWO** `ib_e419cb775d8649eb`：缺 X → 可開（11-05 董事會重訊、奇景 6-K、鉅亨報導、9-09 法說第三方整理；凍結版那一行見 `cases.md`）。
- **ATS.VI** `ib_fa6e2936923f5eec`：缺 X → 可開（半年報、第二季法說簡報；凍結版那一行見 `cases.md`）。
- **NVTS** `ib_58bcfc4c9ffdd33a`：不要 → 缺 X（第三季 10-Q 與法說轉錄稿）：①押的那一層沒有讀圖——800V／AI 資料中心電源的功率元件，圖上 Navitas 沒有邊；②資料中心客戶沒具名（季報只到經銷商，100 萬顆 800V 訂單沒寫是誰）。短檢查日 11-06，closure-gate 列「邊緣沒座位已查」、2027-02-04 重問。
- **INIO 第一份敘事：可開** `ib_a28c6ee2ac43b437` → 同日第二版 `ib_e31dda876950bfa0`（讀了法說第三方逐字與 10-Q 分部表：補深挖清單法說與毛利兩項、瓶頸格加 INNIO 自己的擴產〔窗口會關〕、已定價格加資料中心開發商信用風險的脈絡；候選狀態與 answers 不變）；故事 `st_b8710a518900c6f2`、首頁介紹「燃氣引擎與發電機組」；四份一手節錄。Engine C 快照缺自由現金流、四盞歸零燈原本全灰——機械觀測 runway_inputs `mo_6ade88c9ced362206363860948680518`（as-of 2026-09-30；現金、總債、自由現金流近四季 6.913 億美元，抄自 10-Q 與 424B4）寫入後現金跑道與負債兩盞量得到；稀釋（IPO 全是大股東售股、查不到發新股紀錄）與 going concern（判讀型，要 pq2）仍灰。
- **600118.SS**：Abstention `ab_dd547648d2cfc606`（readings／demand_side：中國衛星自己不坐任何層，座位在子公司名下，比照 300943.SZ）——讀圖面板 settled；同日市值 10.1B 翻成非邊緣（在門檻上，連續兩次才列撤回建議）。
- **5801.T 古河電工**（圖上沒有節點）短檢查結論①補供貨邊：[909] `ra_ebd031417d61941805ccae4288ee20f2`——事業說明會簡報（2026-06-04）與第一季決算質疑應答錄（2026-08-06），四條 supplies_to：HVLP 銅箔、CW DFB 雷射、光纖、光纖纜線；水冷模組、HDD 基板、TFLN 調變器、ELS 模組不給邊。市值 9.53B 在門檻上；closure-gate 列「等入圖（[909]）」。

**量測抽樣①**：種子 2026-11-06 抽中 CECO `ib_f345308446e7b039`（10-31 版）——22 句、事實錯 1（定位格把 10-Q 的訂單歸因寫成營收歸因；營收段寫的是有機成長最大來源是發電市場、其餘增加來自 6 月 1 日合併的 Thermon）、無引用 1（第三季財報日期；事實對，11-09 美東盤前）。同日改版 `ib_8d7690602aaf1a29`（restates 判斷版，判斷與候選狀態不變）＋故事 `st_52c11fba13873aab`；新節錄 `library/raw/ceco_10q_2026q2_net_sales_orders_segment_excerpt.txt`（六段，斷言是重抓原文的子字串）。核對時發現現金跑道燈用的自由現金流（yfinance −1.629 億美元）與 EDGAR 營業現金流減資本支出（−2,160 萬）差七倍——failure log #118 第 2 次。

**段 4 走圖**：55 筆命中對四份終局表（`library/private/wf_tmp/diff_gw_terminals_1106.py`），新命中 0；供給側未填 3／8 母體 <10 只印不判。**故事**：缺 0。

**發現未排程**：
- failure log #118 第 2 次（CECO）：只換來源，CECO 的現金跑道燈會由紅翻黃；兩半一起改仍紅——扣合約負債那一半要先分得出預收現金與預開帳單，才不會重複扣。過次數 gate；新增 Engine C 現金流量表與合約負債欄位是 Z2，等使用者點頭。
- [899]（向你要 CECO 文件）的「已經知道的」寫著「第二季營收年增五成多、主要來自燃氣發電」「等 11-12 第三季財報」——同一個主詞錯；財報實際是 11-09（11-12 是 watch 叫醒日）。文件請求本身仍成立；todo 沒有改說明的子命令，照留。
- 語意叫不醒的實體 186 → 190（counters `semantic_unreachable`）：美股申報人的 10-Q 不在語意叫醒路徑上，PSIX 1 例人工補。
- 名冊 6501.T 有英文別名「Hitachi Energy」、沒有中文「日立能源」：題材掃描那則中文 lead 解析不到（1 例）。
- 雙鴻（3324.TWO）11-18 法說的簡報可能不會被 harvest 收進來（未驗證；到時看 daily 有沒有帶進來）。
- MLCC：圖上沒有的一層，在 AI capex 錨內（不是新錨）——要不要拆一層是使用者的 decompose 選題。

**停止條件成立**：`engine_b.cli drain` 段 0–1 全零、pq1 空（段 5 到終局 79：ready 77／settled 2；未到終局 0；母體外 118＝非倍率 104、邊緣沒座位已查 13、等入圖 1）；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；`audit invariants --only QueueSegments` PASS；closure-gate exit 0；走圖 55 筆命中、新命中 0；⑤ 二十二格全 0（全量物化 198/198，再物化讀圖、走圖、watch、層說明之後的心跳；「邊緣卻沒敘事」註記 5801.T 等入圖 [909]）；候選板可開 13／缺 X 31／不要 46／已持有 2／無敘事 105。**本段候選狀態移動 6**：前提失效 → 可開 2（002428.SZ、SILEX.ST）、缺 X → 可開 2（3363.TWO、ATS.VI）、不要 → 缺 X 1（NVTS）、無敘事 → 可開 1（INIO）；**鑄 ra_admission 2**（[908]、[909]，都沒被抽查抽中）。非零但不是待做：停滯 3、到期 3、追源需處置 1、邊緣無法量 9；逾期型反證 0 條的持有／可開敘事 1＝COHR（同 11-04）。8790 重啟、writer lock 釋放（見收尾）。新鑄 pq2：[908]、[909]。decompose：本輪沒有新錨提案。

## 二十一、2026-11-07（使用者「908 909 go」`/research-drain`；中途壓縮多次）

**段 0–1**：早上語意佇列 22 條、叫醒擋下 8 條（Meta 8-K 融資、波若威董事會決議兩份文件）全判不觸及，敘事該重寫 2（波若威敘事連到的兩條 watch）判完歸零；中午又醒反證待檢 3、叫醒擋下 1，照組判完，敘事該重寫 2 是早上已換騎的兩份。

**[908]／[909]**：經 `scripts/apply_ra_admission.py` 入圖、發布（`7445b796`、`9b646772`）、`complete-ra` 結案。下游：
- **模組 DSP 層**讀圖三版：neither → undecided（`sr_ef32f51071c3406f`，[908] 新易盛那條買方邊）→ volume（`sr_1bdf1b11e59f75b8`：中際旭創 10-29、11-03 投資者關係活動記錄表自己寫 DSP 產能偏緊、價格堅挺、明年 1.6T 按訂單鎖量；MaxLinear 法說說緊在晶圓廠、交期 26–28 週）→ `sr_59fdb499b282135b`（判讀不改，補 AAOI 第三季法說：1.6T DSP 緊是交期錯配、預期 2027 第一季大幅改善、兩家合格加第三家）。中際旭創那條買方邊鑄成 [910]。
- **MXL**：不要 → 缺 X（`ib_cbc62014be7239c6`，換騎第三版讀圖 `ib_f2cedd272d3f1eea`）：「這一層不卡」不成立了；缺的是會死嗎——負債燈紅（定期貸款 1.25 億美元加循環額度 4,000 萬、現金 8,109 萬；前九個月營運現金流 −1,770 萬，為資料中心產品預付晶圓與備貨約 1.376 億），ew_2257 等第四季財報與 10-K。它 10-22 的第三季 10-Q、財報稿與法說 16 天沒人讀（failure log #133）。
- **CW DFB 雷射層**讀圖兩版：`sr_a12d7dd9710dc20d`（古河入圖，供給側 13 → 14 家，窗口再短一格）→ `sr_790f15cdae054ce3`（更正自己的一句：「古河 DFB 產能已到 2023 年度五倍以上」——質疑應答錄沒寫哪一年度達到，「已到」是讀多了；L11-1 措辭精度本身是 claim；判讀不改）。七檔換騎（COHR、SIVE.ST、2455.TW、3234.TWO、688313.SS、3081.TWO、4979.TWO），候選狀態都不變。
- **HVLP 銅箔層**讀圖 `sr_47b56eb69019ad2d`（古河入圖，判讀不改）；5706.T、8358.TWO 換騎。
- **5801.T 古河電工**第一份 v2 敘事：無敘事 → 缺 X（`ib_db61a3aa9d6d00a3` → 同日第二版 `ib_0ef16726991b946d`，補已定價的「必須為真」寫法；故事 `st_82aab69670f5adbe`）——最大的 AI 曝險是光纖與光纜（上修理由第一個寫光ソリューション、第一季法說說光纖產量已到能力上限），這兩層圖上還沒讀圖，說不出該押哪一層；ew_2314 等第二季決算。三份決算短信節錄。會死嗎的現金與債務寫機械觀測 runway_inputs（`mo_225d8e41bd1538deabc73c974bd47d73`），寫的時候撞到解析端丟掉營業現金流（failure log #134，當下修：負債燈 紅 → 黃）。
- **NVTS**：Power GaN 層補供貨邊（onboard）鑄成 [911]——第三季財報稿寫首批美國製 Gen 5 GaNFast 經 GlobalFoundries 出貨、用於 AI 基礎設施；客戶沒具名，只建供貨邊。closure-gate 以 `--skip NVTS` 排除（卡 pq2 [911]）。

**pq1**：開工 51 則，全部到終局——停放 50（一手照轉 15、一手已取得 17、判不追 18）＋入圖包 1：
- **[912]**：光智科技（300489.SZ）公告 2026-069（11-06）子公司先锐與 Coherent 簽 2027–2029 六吋磷化铟衬底長期供貨意向協議（不低於 6.01 億美元；最終協議與出口許可未定，Coherent 沒申報）。同一則觸發 300489.SZ 不要 → 缺 X（`ib_8918ab60ef2f532e`：舊版三個前提——買方沒寫、量主要對境內、份量個位數——加上三季報六吋在手訂單近萬片、海外訂單約 63% 是六吋，都不成立了；缺最終協議與出口許可，ew_2317 2026-12-31 重查）；AXTI 換版 `ib_5a2398613c6e7598`（可開不變，補先锐那句；反證 ew_2152 未觸發——協議沒寫 AXT）。
- **AAOI 第三季法說**（11-05，tradingkey 第三方逐字稿，tier 2）讀完、相關段落存 `library/raw/aaoi_q3_2026_call_transcript_tradingkey_excerpt.txt`：同一批 15 則推文與筆記逐條核到（長約 10–15 億美元、第二份長約更大且含 800G 與雷射、1.6T DSP 卡第四季、四到五家客戶在認證 CPO 雷射），一手照轉；估值與情緒是作者看法、不入圖。
- **CCXI → AGLT**：合併 11-04 完成、11-05 起以 AGLT 交易（8-K 11-06）——敘事重述 `ib_3209a04a5e05ba3b`（判斷不變：不要，整機廠、需求側；拿掉收盤價）＋故事 `st_dbd9b9b9d85d7909`。研究代號仍是 CCXI：帳本都以代號為鍵（failure log #135）。
- 台股重訊 8 則、Tower／MP／META／Ouster 的申報與 carrioresearch 第三季彙整（逐句對到庫內一手）一手已取得；KYEC、Carrier 與其餘 16 則（中國記憶體、ASTS、Amkor、Intel EMIB、OpenAI、ASE、Micron、H200、YMTC、鴻海、Sony 等）判不追，在盯條件逐條處置。

**段 5（敘事自訂的觀測點到了）**：
- **4979.TWO** `ib_1377263d575f95ea`（故事 `st_d09171be28615919`）：第三季財報 11-05 已發布（早於 11-14 法定期限）——營業利益年增約一倍、毛利率約 27%，晶粒占比持平約 13.6%（合併財報產品別收入）；可開不變。新節錄 `library/raw/mops_4979_q3_2026_consolidated_excerpt.txt`。
- **3234.TWO** `ib_bb400ace8d786037`（故事 `st_ce50d310e5347aa0`）：第三季重訊（11-05）單季轉盈、毛利率約 30%（累計數減上半年推算），9 月現增後總負債 3.3 億元、權益 23.9 億元；仍缺 X。核對時發現歸零燈用的是 yfinance 6-30 期末、`as_of` 卻寫取數日（failure log #136）。新節錄 `library/raw/tpex_3234_q3_2026_material_info_excerpt.txt`。

**量測抽樣①**：種子 2026-11-07 抽中 POWI `ib_f4c788a5b4122f7e`（10-08 版）——20 句、事實錯 3（年報「開發要幾年」寫在電動車驅動與垂直氮化鎵那一段，敘事把它接到資料中心；候選理由與故事五格同錯）、無引用 2。同日改版 `ib_546a7daafb789244`（restates，判斷與候選狀態不變；反證 watch 換登 ew_2336）＋故事 `st_0b36c991521d9690`；新節錄 `library/raw/powi_10k_fy2025_strategy_10q_2026q3_excerpt.txt`。這份敘事自訂的觀測點（第三季 10-Q，11-05）抽到前沒有人讀——failure log #133 第 3 次。累積 4 份、有事實錯 3 份。

**段 4 走圖**：55 筆命中對四份終局表（`library/private/wf_tmp/diff_gw_terminals_1107.py`），新命中 0。

**發現未排程**：
- failure log #133 第 3 次（POWI）：EDGAR 監看不含 v2 敘事的公司——**要你點頭**（改 unattended daily 的 harvest 範圍）。
- failure log #134（當下修）：人工 runway 觀測的營業現金流被丟掉；殘留 5 檔負債燈仍是「分不出」的紅（3110.T、4971.TWO、9856.HK、KSHINTL.NS、PRECWIRE.NS），候選狀態都不靠它，下次碰到補錄。
- failure log #135（第 1 次，提案）：SPAC 換代號 CCXI → AGLT，帳本以代號為鍵；SEC 代號表換表後 `get_cik` 的寬鬆備援會把 CCXI 解成 ChemoCentryx 舊 CIK。
- failure log #136（第 1 次，提案）：歸零燈的 `as_of` 是取數日、不是資料期末——3234.TWO 兩盞燈用增資前的 6-30 數字。
- 5801.T 的 X 是光纖、光纜兩層沒讀圖：圖上有這兩層、沒有讀圖，是下一段可以自己做的研究（不用核准）。
- INIO：市值 10.33B 跨過門檻、今天判非邊緣（前一次邊緣），機械移出可開到「非邊緣待確認」——連續兩次才列撤回建議，不是研究改判。

**停止條件成立**：`engine_b.cli drain` 段 0–1 全零、pq1 空（triaged_go 0、action_prepared 1＝[912]）；段 5 到終局 79（ready 78／settled 1）、未到終局 1＝NVTS（卡 pq2 [911]，`--skip NVTS`）、母體外 117（非倍率 104、邊緣沒座位已查 13、等入圖 0）；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；standing-go 候選 0；`audit invariants --only QueueSegments` PASS；closure-gate exit 0；走圖 55 筆命中、新命中 0；⑤ 二十二格全 0（全量物化 198/198，再物化讀圖、走圖、watch、層說明之後的心跳）；候選板可開 12／缺 X 34／不要 44／已持有 2／無敘事 104。**本段候選狀態移動 3**：不要 → 缺 X 2（MXL、300489.SZ）、無敘事 → 缺 X 1（5801.T）；另 INIO 可開 → 非邊緣待確認是機械移動、不算。**鑄 ra_admission 3**（[910]、[911]、[912]，都沒被抽查抽中）。非零但不是待做：停滯 3、到期 3（已處置：lead 早已終局 2、讀圖到期 1）、追源需處置 1、邊緣無法量 9、在門檻上 21；逾期型反證 0 條的持有／可開敘事 1＝COHR（同 11-04）；語意叫不醒 190 → 191。程式修正 `9317c940`（#134）。8790 重啟、writer lock 釋放（見收尾）。新鑄 pq2：[910]、[911]、[912]。decompose：本輪沒有新錨提案。

## 二十二、2026-11-07 傍晚（使用者「910 911 912 go」）

**[910]／[911]／[912]**：經 `scripts/apply_ra_admission.py` 入圖（四道檢查通過）、`scripts/commit_pending_intake.py` 發布（`e259dc63`、`1b70bbf7`、`05e6466b`）、`complete-ra` 結案；三包都沒被入圖抽查抽中。下游：
- **模組 DSP 層**讀圖第四版 `sr_ad028e11a75d4cb9`（volume 不改）：中際旭創 10-29、11-03 兩份投資者關係活動記錄表由圖外改成圖上引用、需求側 4 → 5 條，沒有新事實；反證①–③出處改寫成沿用上一版。MXL 換騎 `ib_440dd84748e6056f`＋故事 `st_e264ae73df6a78df`（缺 X 不變）。
- **Power GaN 層**第一份讀圖 `sr_33e1591376daceef`：判不出（undecided）——供給側圖上 2 家（GlobalFoundries、Navitas）都是供應商自述；需求側 0 條、走不到任何需求錨。缺的那一格：買方或第三方的一手寫明 AI 資料中心電源用 GaN、量多大、向誰買。另記窗口：Navitas 自己說原生 800V 2027 年底前量產、2028 年才有量，那張 100 萬顆的 GaN 訂單是給 800V DC-DC 電源磚。NVTS 換騎 `ib_c6498238f5b2fb2e`＋故事 `st_608408b3686943ba`：仍缺 X，X① 由「押的那一層沒有讀圖」改成上面那一格，補 missing_kind＝layer；段 5 的 NVTS 由未到終局變成到終局（ready）。
- **[912]**（光智供貨給 Coherent）：磷化銦基板層讀圖沒有過期（新邊是公司對公司，不改層的五個角度）；300489.SZ、AXTI 的正文本來就寫了這件事，不換版。
- **段 4**：56 筆命中、新 1＝`co:navitas` 供貨走不到錨——intentional（[911] 刻意只建供貨邊、客戶沒具名；第一份讀圖寫明缺需求側）；終局表 `docs/reports/phase7/graph-walk-terminals-2026-11-07.md`。
- **COHR 新邊沒讀**（全量物化後 ⑤ 敘事該重寫 1）：[912] 那條「光智供貨給 Coherent」是 COHR 名下的新邊——讀了公告 2026-069，位置格補「六吋磷化銦產線要用的基板，向光智（先锐）簽了 2027–2029 長期供貨意向（不低於 6.01 億美元；最終協議與出口許可未定，Coherent 自己沒申報）」並引用；判斷（不要：非倍率持股）、answers、反證不變。新版 `ib_04236381b4fb7cba`＋故事 `st_dd45c9312a7c0987`。

**停止條件成立**：段 0–1 全零；pq1 空（triaged_go 0、action_prepared 0）；段 5 到終局 80（ready 79／settled 1）、未到終局 0——closure-gate 不必 `--skip`、exit 0；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0；`audit invariants --only QueueSegments`、`--only Orphans` PASS；走圖 56 筆命中、新命中 0（co:navitas 已記終局）；⑤ 二十二格全 0（全量物化 198/198，再物化讀圖、走圖、watch、層說明，COHR 換版後再跑一次心跳）。候選板可開 12／缺 X 34／不要 44／已持有 2／無敘事 104——**本段候選狀態移動 0**（NVTS 仍缺 X，只是 X① 由「沒讀圖」換成讀圖寫明的那一格）／**鑄 ra_admission 0**。

## 二十三、2026-11-07 深夜（使用者「開發項我都同意 然後繼續 /research-drain」）

**開發項**：
- **#133 已交付**（`469f4297`；failure log #133 那一列、OPERATIONS 11-07 那一節）——EDGAR 監看多兩個推導來源（現行敘事的美股、還在盯的等待所等的美股），監看 24 → 73 檔、`semantic_unreachable` 191 → 106、反證全部叫不醒的現行敘事 46 → 23。明天（11-08）的 daily 第一次照新範圍抓：冷啟動非持股申報約 187 份照常進分類（每天抓內文上限 20 份，約九、十天消化；持股與追蹤公司的新申報排在前面），其中發布日不早於等待建立日的約叫醒 74 條（讀圖 55、敘事 17、層筆記 2）——第三季財報季漏讀的申報，下一段 drain 照組判。全套 4,647 過、1 紅（request-path 那條：跑的時候寫了敘事，假紅），`-x` 停下後把那個檔與之後 7 檔單獨重跑 187 過。#118、#132 照使用者「先記下」；#135、#136 不動。
- **#137 當下修**（`526d3942`；L17：只認得當初那個案例的機制當下就修）——量測抽樣抽中 MOD 撞到：①故事層沒接 #94 的已定價位置詞檢查（故事不准寫日期，「第 {own_history_pctile} 百分位，在中間」只會凍住）；②#120 的寫死燈色只認「紅燈」、不認「負債燈是紅的」。寫入端兩條檢查、測試 2 組、變異 9 個全紅；回放 0 誤報。資料：故事 20 份換寫、敘事 4 份只改字面換版（MOD、HIMX、XFAB.PA、MXL）——首屏與即時百分位、即時燈色矛盾的檔數 5 → 0（MOD、KLIC、1815.TWO、HIMX、XFAB.PA）。剩 2 句帶日期的燈色（3234.TWO 候選理由、5706.T）照讀，3234.TWO 11-16 重看時照新規則改。

**光纖、光纜兩層第一份讀圖（古河的 X）**：
- `tech:optical_fiber` `sr_84add17ab9984b2d`：量（volume）。需求側有一份買方一手——太辰光 2025 年報把「光纤供应的保障」寫進 2026 年經營規劃；雲端業者鎖量的長約（Amazon–Corning、Corning 第三季四份、擴產由長約分攤成本）都是 Corning 自己申報的。供給側圖上 4 家（Corning、STL、永鼎、古河）都說緊、都在擴，圖外還有長飛、亨通等——不是護城河。時鐘是光棒擴產 18–24 個月（永鼎半年報），與光棒層 `sr_dc097916aa46cd9f`（10-28，量）同一個。圖外第三方 TrendForce 10-19（缺口 1.8 億纖公里、稼動率 92%、短缺至少到 2028）同方向、不入判斷。反證 4 條（窗口關閉、需求側鬆動、新產能提前到位、某規格只有一家通過認證→評估 moat）。
- `tech:optical_fiber_cable` `sr_71d06f98fb13ec3e`：量。光纜本身多家能做，緊的是光纖（古河一手明說「ボトルネックはファイバ」），有自己光纖的一貫化廠拿得到量與價格；STL 依產能挑單、古河ローラブルリボン 2028 年度下期後翻倍。反證 3 條。
- 古河（5801.T）`ib_6e46b929768cca9c`：缺 X → **可開**——押的光纖與光纜兩層讀過、判量；會死嗎不是紅（現金跑道綠、負債黃）；反證有到期；已定價寫成一句。寫入端提醒沒有逾期型反證，同晚換第四版 `ib_c88a01f052897ddd`：補「古河未在 2027-05-31 前公布 2027 年 3 月期通期營業利益達 1,230 億日圓以上（08-06 因資料中心產品上修後的通期預想）」（`ew_2356`），其餘照第三版。故事 `st_c455d9650a8de603`（第一次寫的 `st_3da563b1d809c7c2` 同晚照 #137 拿掉凍住的位置詞換寫）。順手更正第一、二版的事實錯誤：圖上的 `co:jiangsu_etern` 是江蘇永鼎（600105.SS），兩版都寫成「江蘇亨通」。

**Power GaN 需求側（NVTS 的 X）——找了、補不滿那一格**：讀圖 `sr_33e1591376daceef` 缺的是「買方或第三方的一手寫明 AI 資料中心電源用 GaN、量多大、向誰買」。這一輪找到三樣：①NVIDIA 800 VDC 白皮書（Jared Huntington、Mike Tu；PDF 建檔 2025-10-09）第 4 頁「It benefits from the growing maturity of Silicon Carbide (SiC) and Gallium Nitride (GaN) power conversion devices…」——平台方寫了會用到 SiC 與 GaN，沒寫量、沒寫向誰買；②NVIDIA 技術部落格（2025-05-20、7-31 更新；2025-10-13）的 800 VDC 矽元件夥伴名單（10 家／14 家，含 Navitas、Innoscience、Infineon、Power Integrations）——兩篇都沒寫出「GaN」字樣，拿名單推「這幾家供 GaN」是我們的推論（L6：具體型號／公司名必須在引文裡逐字出現），不能用；③台達有自己的 GaN 子公司安可（Ancora，2022 年成立，與 ROHM 共同出資——安可官網與 eeNews 報導），台達官網 11-03 有一篇 Ancora 談 AI 伺服器的文章，本輪沒拿到原文。三樣都沒有量、也沒有買方寫「向誰買」，讀圖不換版、NVTS 仍缺 X。**如果答案存在，它最可能在**：台達 2025 年報的「主要原料之供應狀況」與轉投資（安可）段，或電源廠法說問答裡 GaN 在 AI 電源的占比——下次 NVTS 的缺 X 等待醒來時先讀這兩份。③那條若成立，是 NVTS「什麼會讓它被換掉」的反面證據（最大的 AI 電源廠自己做 GaN），寫進下一版敘事前要先有一手。

**量測抽樣①**：種子 2026-11-07 抽中 MOD `ib_f20c19fb2f6dfeb6`（10-17 版；同一個種子、清單已換了幾版，抽到的跟第二十一節不同）——24 句、事實錯 3（1 句寫錯：把圖上 4 → 8 家寫成一年內的市場進入、把 Modine 寫成新進者；2 句跟著即時值漂：「第 5 百分位，在中間」「最新一季〔已是第二季〕…同季降 340 個基點到 20.8%〔第一季的數〕」）、無引用 2。同日改版 `ib_0b47a5f1742076a7`（restates，判斷與候選狀態〔不要〕不變）＋故事 `st_5c68839e51d36e6d`；新節錄 `library/raw/modine_10_q_20261104_data_centers_margin_excerpt.txt`。MOD 的第二季 10-Q 11-04 已申報、沒人讀（failure log #133 第 4 次，修法生效前的漏讀）；照讀：CDU 仍沒拆、沒有交期字樣、零件供應受限照寫，三條反證都沒碰到。兩句漂移是機制缺口 → #137。累積 5 份、有事實錯 4 份（判讀線 ≥ 10 份才判）。**補記第二十二節**：那一段漏了量測抽樣這一行——沒有抽（收尾時漏做），照段 6 記為「沒做」。

**收尾**：段 0–1 全零；pq1 空（triaged_go 0）；段 5 到終局 80（ready 79／settled 1）、未到終局 0；段 4 走圖 56 筆命中、新的 0（逐筆對過五份終局表）；`event_watch counters` fired_unconsumed 0、semantic_pending_check 0、wake_held 0、expiry_* 全 0（semantic_unreachable 108——比 #133 量的 106 多古河第三、四版新登的兩條，日本公司的申報不在一手涵蓋面）；`audit invariants --only QueueSegments` PASS；全量物化 198 檔（候選板：可開 13／缺 X 33／不要 44／已持有 2）＋讀圖、走圖、層說明、等待四種畫面；心跳短版 ⑤ 22 格全 0；APP 重啟、`code.stale=false`。④ 照舊點名「逾期型反證 0 條的持有敘事 1：COHR」——已持有、敘事是不要（非邊緣），能寫成「X 未在 D 前發生」的是六吋磷化銦產能倍增，手上沒有寫明完成時點的一手，這段不硬寫，下次 COHR 換版時補。本輪無新錨（沒有需求錨不在 `config/sector_anchors.json` 的實體系統）。

**本段候選狀態移動 1（5801.T：缺 X → 可開）／鑄 ra_admission 0。**

**停止條件成立**：closure-gate exit 0（不必 `--skip`）、⑤ 全 0、佇列各段 0。

## 二十四、2026-11-09（使用者點名 AXTI：「先只讀……告訴我①②③」，接著「你說要做的我都OK 都做吧」）

**只讀的回答（第一則，不寫任何 authority）**：①賭的是磷化銦基板這一層的量——在幾家擴產開出來之前，短缺讓 AXT 的出貨一季一季往上，客戶的預付與押金是證據；推翻它的是別家擴產開出、出口管制解除、客戶退出產能協議、第三季那一跳撐不住。②讀到一半：「客戶為什麼選它」對 Lumentum 有一手（為了多一份基板產能，不是換不掉），對 Coherent 沒有——它在 Coherent 是主力還是之一，兩個二手說法不一致、一手沒寫；「什麼會讓它被換掉」：買方多來源化、中國側新產能、出口許可。③缺的寫成加碼條件與一份文件請求。

**自己抓的一手（新存 4 份節錄，全部本機逐字核對）**：
- `cohr_q1fy27_earnings_call_substrates_excerpt.txt`——Coherent FY2027 第一季法說（11-04，第三方機器轉錄 gloom.sh，Motley Fool 交叉）：基板來源「over five different suppliers」、和其中幾家簽了長約、2027 年底再翻倍所需的基板已鎖定、蘇黎世 2027 上半年開始六吋；沒有點名任何一家。
- `gzkj_300489_ir_20260924_xianrui_capacity_excerpt.txt`——光智科技投資者關係活動記錄表 2026-003（巨潮「调研」欄 09-24）：先锐兩個擴產案（清遠年產 40 噸磷化铟晶片已獲批；50 億元化合物半導體衬底擴建已備案、規劃年產 100 萬片 6 吋），都沒寫時程；高純紅磷是國內大尺寸基板放量的上游瓶頸。
- `gzkj_300489_ir_20261102_inp_excerpt.txt`——同一張表 2026-004（11-01 電話會議）：六吋在手訂單近萬片、「同时扩产也是6英寸长晶炉」、三年鎖 100 噸高純銦與 100 噸紅磷代工。
- `cls_kcb_inp_substrate_shortage_buyers_2026_08_22_excerpt.txt`——科創板日報 2026-08-22（媒體轉述，tier 3）：長光華芯證券部說因全球緊缺在驗證導入雲南鍺業、北京通美；源杰、仕佳、三安都外購、多來源；雲南鍺業董秘辦說 6 吋大規模量產尚需時日；一位基板廠高管說驗證到批量供貨要 2–3 年。13 段逐段比對原頁。
- 另核：AXT 第二季 10-Q 的營收歸因——產品別寫「as a result of additional export approvals」，但地區別拆開增加最多的是中國境內（+1,630 萬美元，含原料子公司），歐洲、台灣、日本合計 +1,040 萬是許可放行，北美 −6.3 萬（出口管制）；敘事原本只寫了前半。AOI 第三季法說（11-05，第三方轉錄）財務長：「we're fine through 2027 on indium phosphide」。EDGAR（repo 的 fetcher）：AXT 第三季 10-Q 截至 11-09 還沒申報。

**讀圖反證①判實質觸及 → 磷化銦基板層換版兩次**：
- `sr_260d9f90fe119da4`（11-09 稍早）→ 同日更正 `sr_0b5c82b7f896c8e6`。更正三處：①稍早那一版寫雲南鍺業→AOI、先锐→Coherent「兩者都沒入圖」是錯的——兩條都已入圖成公司對公司的邊（11-04、11-07 [912]），只是不在這一層的角度上（寫之前沒查圖，L11-6）；②需求側 sub=5 是 6 條不是 7 條——09-18 [610] 把 InP EML 併進 EML 之後，各版讀圖照抄了合併前的數（讀圖正文的計數沒有對快照重數）；③補 AOI 法說一句。
- 判讀維持量（volume）：需求側繞不過照舊；三種買方（美系元件廠、台灣磊晶廠、中國光晶片廠）都在多來源化——B 最直接的證據。改的是窗口：除了三家既有大廠的擴產，多兩個時鐘——中國兩家的新產能（雲南鍺業 18 個月建設期，推估約 2027 年 10 月；先锐沒時程）與中國廠對海外買方的出口許可（AOI 2027 年度合同、Coherent 意向 2027–2029）。對美國公司來說，AXT 和雲南鍺業、先锐在同一個許可桶子裡。
- 反證：①改寫成已讀兩家擴產案為基準、核查頻率補巨潮「调研」欄；⑦補 Coherent 五家以上；新增⑧「中國廠對海外買方的量開始交付」。watch 換登 8 條。

**三份騎這一層的敘事換騎（①的 48 小時動作：AXTI、雲南鍺業、光智科技重答已定價）**：
- AXTI `ib_3404da090f1a4434`：可開不變。已定價仍「是」，翻倍條件把中國兩家的新產能算進去；第二季歸因改準；「卡在誰」改寫（買方在分散、許可桶子）；新增反證：連到讀圖⑧、通美私募 2026-12-31 前沒交割（逾期型）；新增加碼條件 c1（Coherent 自己的文件寫出 AXT 的角色）、c2（境內買方的一手具名通美）。深挖清單十項的引用改指現行讀圖與新節錄。
- 雲南鍺業 `ib_4b1b29b6df8d10ad`：可開不變；已定價仍量不到、仍當已定價看；「想殺它的」補先锐擴產、刪「Coherent 自建襯底」（11-04 的季報與法說都沒寫自製基板）。
- 光智科技 `ib_de6afb4491d44e50`：仍缺 X（最終協議與出口許可，`ew_2317`）；反證連結 #1、#5 換到新讀圖；「卡在它」補先锐兩案與紅磷。
- 故事三則（`st_72aa6e211428c095`、`st_83b91438f5a05a13`、`st_f858865fea5db833`），`stories --gaps` 0。

**入圖：這一段沒有可入圖的變更**。原本要把一份券商說法走入圖包——券商是 tier 2、不能當入圖證據，自己更正；改去找住友或 JX 供 Coherent 的一手，沒有；Coherent 法說沒點名任何一家，依 L6（公司名要逐字出現在引文裡）也不能拿來支持哪一條邊。沒鑄 ra_admission。另記一個觀察、不提案：這一層的需求側沒有 AOI 那條邊（AOI 自己的 10-Q 只寫「a key raw material」，法說那句是第三方轉錄）——補了也不改判讀，答不出 go 會讓哪個數變（L14），先不鑄。

**文件請求**：鑄 [913]（凱基〈光通產業〉更新版，看 Coherent 的基板主力；`flips_state=false`）。原本想一起要的嘉信／IB 的 Coherent 報告沒鑄：Coherent 自己已經說「超過五家」而且不點名，美系報告點名基板廠的機會低，鑄了只佔名額（上限 5，現在 4 筆：[897][898][899][913]）。

**量測**：`cases.md` Q3W 裁決段補 5 行——AXTI 11-05、11-07（回填）、11-09；雲南鍺業 11-06（回填）、11-09。AXTI 凍結版（10-20）必須為真②的後半「也沒有新增的產能」記成 `already_available`：雲南鍺業半年報（08-28）與先锐調研紀錄（09-24）都早於凍結版；判讀與候選狀態沒動。

**failure log**：#138（A 股的公告與調研紀錄沒有 producer，反證叫不醒）、#139（改寫反證時條件寫下即成立、沒對現有證據跑一次）、#140（錯的訊號沒搬進 disproof[]；條數比對抓不到這一筆，修法候選改成逐條標反證編號）、#141（私有券商報告沒索引，Grep 工具預設還略過私有區）——都是第 1 次。

**沒做／等事件**：[896] thesis `axt_inp` review_required 照舊等 AXT 第三季 10-Q（11-16 叫醒）；thesis mutation 是人工 gate，這一段沒動。

**收尾**：物化 AXTI、002428.SZ、300489.SZ＋候選板＋讀圖＋事件監看（讀圖現行 75／stale 0／該重讀 0；三檔在候選板上「該重寫」「加碼條件還沒查」都是 0）；8790 重啟，`code.stale=false`，三檔個股頁 API 200。候選板可開 8（11-07 是 13）：少的 5 檔（300570.SZ、3363.TWO、AEHR、ATS.VI、STLTECH.NS）是反證 watch 醒來待判、移到前提失效，不是這一段的改動——留給下一段 research-drain。

**本段候選狀態移動 0／鑄 ra_admission 0／鑄文件請求 1（[913]）。**

**同日補正**：回答使用者「這檔是已定價？還能賭嗎」時，發現 11-09 版已定價格寫「11-07 當天的價格下倍數約 23 倍」是錯的——23 倍是 10-29 收盤算的，11-04 起各版照抄成「同一個價格」，價格掉了數字沒動，11-09 版又標錯日期。用重述版 `ib_dab0eafb05d15bd9`（restates，判斷日不歸零）改成「10-29 收盤約 23 倍、11-06 收盤約 15 倍」，故事 `st_09fa329d37dfa1d9` 對新 id 照原文重寫；failure log #137 追加同族一次。

## 二十五、2026-11-09 下午（使用者「好 照你推薦 直接做吧」——個股頁「問 Claude」那段提示，可開每一檔都貼一次跑完）

**先做機制（使用者指示，不走 gate）**：research-drain 加「完整重讀＝清單之外的五項回掃」（`896fb209`；第 (3) 項同日更正成「敘事必須為真格的錯的訊號逐條對反證」，`4af5e5a2`）——AXTI 十項全查完、⑤ 是 0 仍漏了五件事（第二十四節），所以另走五項、先層後檔；個股頁「問 Claude」提示加一行指向它，測試核提示點名的那一段存在。子代理沒開（使用者選本 session 逐層做）。

**範圍**：候選板可開 8＋已持有 2（物化的 candidates 逐列核過，與計畫一致；AXTI 第二十四節已做）。順序：CW DFB → 古河的光纖三層 → CPO 全堆疊測試 → MEMS 鏡陣列 → 太空三結電池片 → 雲南鍺業補個股層。

**層（讀圖都不換版——沒有反證被觸及、判讀沒有實質改變）**：
- CW DFB（`sr_790f15cdae054ce3`，騎它 8 份）：穩懋 11 月簡報 CW-DFB 仍是合格中（⑦）；Lumentum 10-Q 沒寫自家 CW 比例（⑥），11-01 與 Marvell 簽全股票併購協議；住友半年決算、源杰三季報沒有產能數字（①）；古河 11-09 決算說明會簡報的 DFB「5 倍」基準換成 2026 年度期初、滿載在 2028 年度下期——同一個倍數、時點更晚，照字面不算觸及①，下一版讀圖寫進去；Arista 第三季「copper when you can」不是⑨要的改銅或延後。①的 entities 沒有環宇（failure log #143）。
- 光纖、光纜、HVLP：古河 11-09 決算（通期營業利益上修到 1,360 億日圓、「タイトな需給環境が継続」）與永鼎三季報（「量价齐升、供需偏紧」）——反證方向相反，三層都不換。
- CPO 全堆疊測試（`sr_fb7269d0f5f6fece`）：巨潮 10-29 之後沒有新的 CPO 測試訂單或客戶；旺矽 09-18、致茂 10-29 法說簡報都沒寫 CPO 站別。一份私有券商報告有相反的線索（只寫進私有敘事，內容不進 repo），一手沒有對應。
- MEMS 鏡陣列（`sr_8dd7652e9ca791bf`）：賽微三季報沒寫 OCS 量產（①）；Lumentum 10-Q 全文沒有 MEMS、OCS 這一季貢獻 1.08 億美元以上（一季超過 2026 財年全年的 9,000 萬美元以上），併購電話會（Marvell 依 Rule 425 申報）只說它是 MEMS OCS 的主要供應者（③④）。
- 太空三結電池片（`sr_196352cea9f0782a`）：國內買方電科藍天第三季報（10-28；讀圖只讀到半年報）全文沒有緊張、交期、漲價的字，10-30 股價異常波動公告寫商業航天要「低成本、高性价比」電源、沒寫改用哪種電池（#1、#3）；EDGAR 全文搜尋 10-01 到 11-09 的 10-Q／8-K／10-K 沒有衛星或星座業者寫太空電池的交期、配額或改用（#2、#3；Rocket Lab 第三季 10-Q 還沒出）。

**個股（判斷全部不變；10 檔的錯的訊號都標上「（第 n 條）」）**：
- 聯亞 `ib_12493ccc3f5a8b04`：第三季個別財報 10-28 就上傳，10-31 起六版都沒讀財報本身（failure log #142）——長約履約保證金美金 5,000 萬元截至發布日尚未收訖、三份原料長約、設備合約未認列 5.60 億元；補兩條逾期型反證（保證金 2027-03-31、10–12 月營收 2027-01-31）；已定價改 11-06 收盤（P/S 41 倍、第 74.6 百分位）。
- 華星光 `ib_d88ba85698358391`（restates，判斷日不歸零）：第三季財報 11-07 那版已讀；這次只標錯的訊號編號、補上第 3 條，深挖清單兩行過期的改掉。
- Sivers `ib_360aad29a29b40f2`：10-22 臨時股東會換會計師（Deloitte → EY）、P11 認股權最多 728 萬股（約 2%）。
- 古河 `ib_028171533160b1b9`：七格換成 11-09 決算；反證 #4／#5 門檻改 1,360 億日圓。
- 罗博特科 `ib_cc64ebde60044d0c`：私有券商報告的相反線索寫進卡在哪一格（私有敘事）；耦合設備那一半的錯的訊號寫明不另登。
- Silex `ib_1b7298d392fc3048`：補 Lumentum OCS 季營收與併購、法說原文的美國廠時程（CFIUS 核准預計 2027 年初、交割 2027 年底、之後再投約 16 億克朗）、原母公司賽微與 Bure 合計 29% 的 180 天鎖定期約 11 月初屆滿（到 11-09 巨潮與 MFN 都沒有賣出的公告）；已定價格原寫「上市價 81 克朗，5 個月後約翻倍」——日線是上市首日就大漲、之後回落，這句讀起來像一路漲上來，改成兩件一手事實；「客戶把 MEMS 收回自製」拆成對得到反證的兩種。
- 5N Plus `ib_bd8b148406db06c4`：全公司積壓 299 天（比上一季少 14 天，特種半導體仍頂在 365 天上限）、9 月的美國國防部砷化鎵補助（賣方自述，碰不到 c1）。
- 雲南鍺業 `ib_4a353f1d49f6152c`：已定價格「2026-10-30 的快照 42 倍、715 倍」錯——第三季報前的快照數字照抄十四版、11-04 補日期時標錯（那天是 27.9 倍、275 倍）；改成 11-06 收盤 29 倍、268 倍，故事改用 {market_cap}／{revenue_ttm}（failure log #137 同族第 3 次）；11-07 控股股東不減持承諾補進已定價格的脈絡；錯的訊號補上原本沒列的第 2、5 條。
- COHR、AXTI 不換（COHR 錯的訊號已明寫連到讀圖兩條；AXTI 第二十四節剛做完）。故事 8 則重寫，`stories --gaps` 0。

**新節錄（12 份新檔＋1 份補句；英文逐句是原文攤平空白後的子字串、中文刪空白後是子字串）**：`mops_3081_separate_financial_statement_202603_excerpt.txt`、`sive_egm_2026_10_22_bulletin_excerpt.txt`、古河三份（`furukawa_kessan_q2fy2027_20261109_excerpt.txt`、`furukawa_forecast_revision_20261109_excerpt.txt`、`furukawa_q2fy2027_presentation_20261109_excerpt.txt`）、`lite_10q_20260926_ocs_excerpt.txt`、`mrvl_lite_425_merger_call_2026_11_02_ocs_excerpt.txt`、`vnp_pr_20261102_q3_2026_results_excerpt.txt`、`vnp_pr_20260903_gaas_dow_award_excerpt.txt`、`cetc_lantian_688818_q3_2026_report_excerpt.txt`、`cetc_lantian_688818_abnormal_volatility_20261030_excerpt.txt`、`yng_002428_ann_2026_055_no_sell_pledge_excerpt.txt`；`silex_q3_2026_call_investing_excerpt.txt` 補三句（同一份逐字稿、經抓取工具轉錄）。

**量測**：`cases.md` Q3W 裁決段補 2 行——4979.TWO（11-07 回填）、3081.TWO（11-09）；名單把台股季報的裁決點寫成法定期限 11-14，照實際上架日評；兩行都是「錯：無」，揭露寫的時候看過價格。

**failure log**：#137 同族第 3 次；#140 第 2、3 次（5801.T、300757.SZ），改為過 gate——提給使用者：寫入端核「錯的訊號每條都有反證編號」；新 #142（台股季報上架日被當成法定期限；財報電子書沒有 producer）、#143（讀圖反證的新進者不在 entities）。另記一個工具坑、不開條：repo 的 EDGAR 標頭寫死 `Host: data.sec.gov`，拿去打全文搜尋（efts）會回 404 NoSuchKey——repo 沒有程式用全文搜尋，只影響臨時腳本。

**沒做／等事件**：古河決算說明會的問答錄 11-09 還是佔位檔，上網後讀（還說不說光纖到能力上限）；電科藍天 10-29 業績說明會問答沒讀到（上證路演中心）；Rocket Lab 第三季 10-Q 未出；華星光 10 月營收 11-09 還沒申報。入圖 0、thesis 0。文件請求名額剩 1（[897][898][899][913]），這一段沒鑄。

**收尾**：物化 8 檔＋候選板＋讀圖＋事件監看（候選板可開 8／缺 X 33／不要 44／已持有 2，沒有移動；讀圖現行 75／stale 0／該重讀 0；10 檔都不在「該重寫」「有新邊沒讀」上，加碼條件還沒查 0）；8790 重啟，`code.stale=false`，8 檔個股頁與候選板 API 200，首屏核過 Silex 與雲南鍺業的新故事（佔位符填成「市值 473.1 億 CNY、近四季營收 16.3 億 CNY」）。

**本段候選狀態移動 0／鑄 ra_admission 0／鑄文件請求 0。**

## 二十六、2026-11-09 晚上到 11-10 上午（使用者「一起做吧」——缺 X 季報回掃＋可開與持有找讀到邊，子代理分組；中途撞額度兩次、壓縮兩次）

**分工（子代理委派是使用者這次的明確 opt-in；子代理只讀、只交 packet，寫入全由主 session）**：
- 缺 X 33 檔完整重讀（五項回掃，季報優先）：A（2455、3234、4971、4991、688313）、B（1802、1815、3110、8358、300395）、C（3163、300489、600105、IQE.L、MXL）、D（EFXT、EROC、PSIX、SLNG）、E（002270、1519、BW、CECO、KSHINTL.NS）、F（8996、AMKR、ARBE、NVTS、USAR）、G（300943、301511、688020、MTARTECH.NS）。
- 可開與持有 9 檔只做第 ② 題（客戶為什麼選它、什麼會讓它被換掉）：E1（002428、SILEX、AXTI）、E2（3081、4979、SIVE）、E3（300757、5801、VNP.TO）；COHR 非倍率不做。
- 起始門重判（套用使用者 11-03 定的門，不是新決定）：草稿多數照舊留缺 X，但缺的那一格是讀到邊或加碼條件——H1（2455、3163、8996、KSHINTL.NS、1519、300489、600105）、H2（USAR、002270、IQE.L、AMKR、ARBE、NVTS）逐檔核四項後出可開版或寫明卡在哪一項。

**結果（候選板 11-10 物化：可開 34／缺 X 10／不要 44／已持有 2；前提失效 0）**：
- 缺 X → 可開 23：002270.SZ、1519.TW、1802.TW、1815.TWO、2455.TW、300395.SZ、300489.SZ、3110.T、3163.TWO、4971.TWO、4991.TWO、600105.SS、8996.TW、AMKR、ARBE、EFXT、EROC、KSHINTL.NS、MTARTECH.NS、NVTS、PSIX、SLNG、USAR。移動幾乎都來自門的設計改變（原本的 X 屬讀到邊或深挖清單，改列加碼條件），不是 X 被回答；例外兩檔——KSHINTL.NS 是會死嗎改用 9 月底的數（機械觀測 `mo_0c53b7c4d1ada6ec993b5cd33d5cd665`，mechanical、不經 pq2：11-04 董事會決議附件 A 的上半年財報），8996.TW 是押注收窄成只押分歧管層（CDU 層判 neither，過不了起始門②）。
- 仍缺 X 10，各自卡在哪：會死嗎有紅燈——IQE.L（負債那一盞含 IFRS 16 租賃；不含租賃是淨現金，口徑交使用者，failure log #118 第 3 次）、MXL、301511.SZ、3234.TWO、688313.SS、BW；CECO（第三季現金流還沒進會死嗎，10-Q 後重判）；300943.SZ 沒押任何讀圖；688020.SS 押的讀圖是它賭注的反面（主 session 判，不宣告可開）；8358.TWO 可轉債的稀釋要等轉換價格。**其中 688313.SS、3234.TWO、BW 的狀態對，但候選理由還寫舊的 X（雷射營收、代工內容、第二個客戶），沒寫卡在會死嗎**——下次換版改寫（failure log #144 同形）。已持有 SIVE.ST 仍缺 X（會死嗎：持續經營疑慮，等 11-26 季報）。
- 讀到邊（第 ② 題）：9 檔的加碼條件都沒有被完整回答。新事實：AOI 執行長說基板有六家供應商、每家都在合作（002428 的 c1 由已存在的法說確認、拿掉；什麼會換掉它＝AOI 另外的供應商）；TrendForce 2026-06-03 已把聯亞、華星光列在 CW-DFB 產能 Broadcom、住友之後——兩檔凍結版寫「第三方第一次具名是券商」不成立（`already_available`，事實格）；Lightwave 2010 寫 DALSA 替 JDSU 量產 WSS 的 MEMS 鏡陣列（Silex 以外至少一家 Lumentum 用過的代工）；POET 2025-09-29 的聯合新聞稿寫選 Sivers 是因為高功率，但之後的 20-F 與 MD&A 不再提——**主 session 判 SIVE 的 c3（`ew_2503`）不收**（兩家的聯合稿不算「不只 Sivers 自己說」），c3 照舊盯；Teradyne 2025-03-31 寫選 ficonTEC 的理由（夥伴，不是客戶）；York 併購 Solestial 的兩份公告寫三五族太空電池產能受限、交期超過兩年——太空三結電池片層重讀 `sr_f97ef292ba08ace1`（西方那一半改讀成量），300102、600118 只換騎、「不要」不變。
- watch：醒著的 78 筆逐組判，全部沒觸及。值得記的三件：Oracle 11-02 發 100 億美元股與 100 億美元債（7.000%～8.650%）——和 AI capex 融資錨有關，留給 [900] 那條錨的盯法；Dover 熱交換器需求加速、book-to-bill 1.23（反證的反方向）；MXL 10-Q 的晶圓預付是 DSP（5nm CMOS），不是 SiGe。
- AEHR：10-Q 起會計年度改到 6 月底，近四季營收接不成一年，已定價改答量不到（要到 2027 會計年度年報，約 2027 年 8～9 月）。

**機制（L17 當下修）**：燈色偵測器補兩種寫法——燈名緊接顏色（「負債紅」）與「盞…是／為＋顏色」（`alpha/narrative/contracts.py` 的 `LAMP_COLOUR_CLAIM`，failure log #120 第 5 次；5801.T、MXL、XFAB.PA、3234.TWO 四份只改字面重述）；research-drain SKILL 完整重讀 (2) 之後加四條：巨潮「调研」欄只收深交所（#145）、IR 網站與 E-IR 要翻（#147）、缺席主張前先查登記 corroborates 的研究機構、EDGAR 全文時間窗與前身（#149）、反證與加碼條件寫金額不寫占比（#146）。

**量測**：`cases.md` Q3W 裁決段補 22 行（名單內這一輪換版的檔）＋補記 1 行（11-03 之後只換騎或只改字面的 23 版當時沒寫行）；處置紀錄補月營收量測的干擾揭露——窗內數到 3 檔，全是起始門重判、不是營收；多檔 10 月營收 11-10 前就上了 MOPS，這個月多半不可判，判讀方式交使用者，11-14 照登記寫結果。`錯` 這一輪記了 `already_available` 4 檔（USAR、8358、3081、4979）、`emerged_later` 2 檔（USAR、8358）。

**failure log**：#32、#118、#120、#137、#139–#143 追加這一輪的 case；新 #144–#152。過 gate 的開發提案（等使用者點頭）：#147（IR 網站限定文件沒有 producer）、#148（MOPS 重訊只抓當日、不回補，建議與 #142 一起做）、#150（when 格的裁決點過了、敘事沒跟著）、#152（Q3W 價格被動曝光沒有機械紀錄），以及這一輪過 gate 的 #32、#139、#141、#143。

**新節錄**：`library/raw` 79 份新檔＋`lite_10q_20260926_ocs_excerpt.txt` 補一句（代工廠所在地，沒點名）。

**沒做／等事件**：AXT 第三季 10-Q（[896]）；KSH 第二季法說逐字稿與簡報；8996、3234 第三季合併財報上電子書；688313.SS、3234.TWO、BW 的理由改寫（上面）；MTAR 讀圖正文「不得寫可開」那句待下次重讀；`ew_0420` 沒醒、層說明待換版；名冊還沒有 York、Redwire、Solestial、SMCI、Teledyne DALSA；1519 的 [897] 建議收窄成「具名客戶與交期」。計數器仍待清：加碼條件還沒查 10（23 檔新可開的深挖清單有缺）、叫醒擋下 31、688017.SS 邊緣卻沒敘事、未 triage 237、待深挖 97。入圖 0、thesis 0。文件請求名額剩 1（這一段沒鑄）。

**收尾**：物化 45 檔個股頁＋候選板＋讀圖＋事件監看＋層說明；8790 重啟、測試、audit 見 commit。

**本段候選狀態移動 23（全部缺 X → 可開）／鑄 ra_admission 0／鑄文件請求 0。**
