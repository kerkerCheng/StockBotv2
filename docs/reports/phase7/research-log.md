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
