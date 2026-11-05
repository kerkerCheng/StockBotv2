<!-- ticker: COHR | gates_all_pass: False | checklist_pass: True | l9_pass: True | evidence_manifest_pass: True | evidence_gate_pass: False -->

# Directional Lane Memo — Coherent（CPO 高功率雷射／自有 InP 產能）v3
**生成日期：** 2026-11-05
**Thesis 狀態：** `revised`。本 memo 是 2026-09-21 [636] revise 決議的執行；lifecycle 轉回 `active` 要另一個 thesis mutation 編號的 `go`。
**v3 改了什麼：** ①照 09-21 決議改四處：§1 差異點拿掉「唯一供應商」框架、§4 把 sole_source 寫成已否證、§6 補整合雷射模組（ILM）這條品類層的路、併入盯營收有沒有出現的反證；②2026-11-04 第一季 FY2027 財報（8-K、10-Q、法說）提前回答了 v2 的 12 月檢核點，第二個需求錨（PhotonLink 長約）寫進 §2。
**核查頻率與觸發動作：** 每季財報＋法說後 5 個工作日內完整核查；客戶與競爭者的新文件由語意層逐份標旗。任一反證觸發 → 48 小時內人工決定降評、維持或退場。下一個檢核點：2027-02 第二季 FY2027 財報。
**圖外資料怎麼標：** 2026-11-04 的 8-K 與 10-Q 還沒入圖（pq1 `lead_781f58da…`、`lead_a33d8ef8…`），本 memo 引用時寫明出處、不加 [E#]。法說取自 gloom.sh 的自動轉錄（WebFetch 讀取；轉錄把 NVIDIA 聽成「Envidu」、indium 聽成「Indian」），沒有和官方逐字稿核對，只當弱證據。

## 1. 一句 thesis

Coherent 靠自有六吋 InP 產能，在 CPO 雷射放量期（CY26–28）拿份額。

> **Variant Perception：**
> **市場現在信什麼（X）：** 2026-11-04 收盤（財報在盤後公布）$195.09，forward P/E 14.0x（Yahoo，forward EPS 13.97）、EV/Revenue 5.6x、分析師目標均價 $387.80（N=25）。股價比 v2 寫作時（2026-07-17，$277.60）低三成，也比 NVIDIA 2026-03 的認購價 $256.80 低 24% [E1]。以這個價格買的人，不必相信 CY2028 以後還有高成長——14 倍 forward 本益比放在一家指引 FY2027 營收年增六成以上的公司身上，等於把這一輪當成光通訊週期的高點。
> **本 thesis 認為（Y）：** 放量的上限是 InP 元件產能。Coherent 的自有產能 2026-09 季已年增一倍、比承諾早一季，CY27 底前再倍增（8-K 投影片，圖外）；需求錨不只 NVIDIA 的 20 億美元股權與 multibillion 採購承諾 [E2]——第一季又簽了約 200 億美元、五年、CY2028 初開始認列的 PhotonLink 長約（8-K 投影片），法說說那是 NVIDIA 長約之外的另一位「major AI company」客戶（自動轉錄，弱）。「唯一供應商」已被客戶端文件否證 [E3]，所以這不是獨占溢價，而是三家具名外部光源供應商之下的產能位置與份額。
> **催化劑（Z）：** 2027-02 第二季財報（CPO 用的 400mW CW 雷射開始認列營收）；2027-03 季 PhotonLink 營收破 1 億美元；CY27 底前 PhotonLink 每季 2.5 億美元與第二次 InP 倍增——三個數字都是公司 2026-11-04 自己寫下的。

## 2. 需求驅動

- **客戶拿資本鎖產能**：NVIDIA 以每股 $256.80 認購 20 億美元股權 [E1]；客戶端新聞稿寫明 multibillion 採購承諾與 future access and capacity rights，Coherent 自己的 10-Q 寫這份協議是 non-exclusive，也寫這份多年產能協議「could affect revenue concentration」——同一份協議同時是需求錨與集中度風險 [E2]。
- **高功率 CW 雷射的量由買方拉，缺口在供給端**：第三方供應鏈查核寫 NVIDIA 給 Coherent 與 Lumentum 的高功率 CW 雷射 guidance 由約 4,000 萬顆升到約 1 億顆 [E4]；競爭者 Lumentum 自己說高功率雷射出貨「way behind」[E5]——不是只有 Coherent 說缺。
- **第二個需求錨（圖外）**：8-K 投影片寫第一季簽下「a PhotonLink™ agreement valued at ~$20B over five years; with revenue beginning to ramp in early CY2028」，PhotonLink 營收預計 2027-03 季超過 1 億美元、CY27 底前每季超過 2.5 億美元。法說補充這份長約「anchored by our laser, our 400 milliwatt CW laser」，而且「in addition to our previously announced LTA with NVIDIA」（自動轉錄，弱）。客戶沒有具名。
- **時程**：Coherent 原本說 scale-out CPO 營收 CY2026 下半年開始、scale-up CY2027 下半年開始 [E6]；法說說 CPO 用的 400mW CW 雷射「is expected to begin generating revenue this quarter」（2026-12 季；自動轉錄），和原時程一致。
- **風險側**：NVIDIA 已把中國資料中心算力營收排除在展望外 [E7]，需求總量對出口政策敏感。

## 3. Stack 摘要

(a) **InP 元件層（最緊）**：六吋線已 qualified、首批含六吋元件的收發器已出貨 [E8]，六吋良率高於三吋、原訂 2026 年第四季前把自有產量翻倍 [E9]；Coherent 說 InP 產能仍是主要限制、組裝測試不是 [E10]。2026-11-04 的 8-K 投影片寫「Internal InP output capacity doubled YoY one quarter early; on track to more than double again by CY27-end」，10-Q 寫在 Sherman 與瑞典擴產以因應「industry-wide shortage」；法說另說蘇黎世六吋線 2027 上半年開始生產（自動轉錄）。
(b) **外部光源／模組層**：NVIDIA 在自家 silicon photonics 文章裡點名 Lumentum、住友、Coherent 三家做 ELS 組裝、光學對準與測試 [E3]；Lumentum 的第一筆 ELS 模組訂單要到 2027 下半年才交貨 [E11]。規格層另有一條路：Coherent 共同發起的 Open CPX 插槽式 CPO MSA [E12]，規格同時允許外部光源模組（ELM）與整合雷射模組（ILM）——規格允許不等於有人做得出來，目前圖上沒有具名的 ILM 客戶或出貨（規格層證據是 [642] 入圖的那一份，不在本 memo 的 Coherent 清冊裡）。
(c) **基板層**：AXT 拿 Coherent 22,288,500 美元預付款，承諾北京廠 2026–2028 擴充六吋 InP 基板產能 [E13]；Reuters 引述知情人士說換基板供應商要經過很長的認證週期 [E14]。法說執行長說 Coherent 有「over five different suppliers of substrates」、和其中幾家簽了長約、下一次倍增要的基板已鎖定（自動轉錄，弱）——基板對 Coherent 不是單點，但換家仍慢。

## 4. 主瓶頸

- **公司／技術**：Coherent 的高功率（400mW 級）CW DFB 雷射，以及生產它的自有六吋 InP 產線。
- **為什麼是它**：NVIDIA 協議涵蓋的產品包括高功率 CW 雷射，圖上狀態 designed_in [E4]；Coherent 說客戶當初選它，關鍵是這顆雷射在 Sherman 的六吋線生產 [E15]（自報）。可替代性：CW 雷射這條邊 substitutability=4，是三份 Coherent 自報（4/5/4）的決議值、resolved_confidence 0.6 [E16]；第三方只點名兩家拿到 NVIDIA 的高功率 CW 雷射 guidance [E4]，是旁證，沒有給可替代性的值。法說執行長說 400mW 這一級「we really only have one competitor」（自報、自動轉錄，弱）。
- **sole_source：已否證**。客戶端文件點名三家 ELS 供應商 [E3]，客戶端新聞稿與 Coherent 10-Q 都寫協議 non-exclusive [E2]；圖上 Coherent→NVIDIA 這條邊 sole_source=false。這條邊的 substitutability=5 還留著，但全部出自 Coherent 自報、resolved_confidence 0.6 [E17]——本 memo 不把它當已確認的瓶頸證據。
- **進度**：v2 的 12 月檢核點（自有 InP 產量翻倍）已由 2026-11-04 8-K 投影片提前回答：年增一倍、早一季（Coherent 自報，沒拆六吋與三吋；原承諾寫的是 internal indium phosphide production，這次寫 output capacity——產能翻倍不等於產量翻倍）。六吋線 ramp_execution=4 [E8]。
- **上游**：見 §3(c)。

## 5. 最強證據

- [E2] NVIDIA 客戶端新聞稿：multibillion 採購承諾與 capacity rights；Coherent 10-Q：non-exclusive，且可能影響營收集中度（客戶端＋發行人法定文件）。
- [E3] NVIDIA silicon photonics 文章點名三家 ELS 供應商（客戶端；否證「唯一」，也確認 Coherent 在名單裡）。
- [E4] 第三方供應鏈查核：NVIDIA 給的高功率 CW 雷射 guidance 由約 4,000 萬顆升到約 1 億顆，只點名 Coherent 與 Lumentum（Global Semi Research）。
- [E13] AXT 8-K：Coherent 預付 22,288,500 美元鎖六吋基板產能（交易對手的法定文件）。
- 圖外（時變財務事實，屬 Engine C、不入圖）：2026-11-04 8-K——第一季營收 23.70 億美元；Datacenter & Communications 分部 19.517 億美元，年增 79%（上一季 16.150 億、去年同季 10.900 億）；第二季營收指引 25.5–27.5 億美元；FY2027 pro forma 營收成長指引 >60%。

## 6. 什麼會推翻這個 thesis

- 若 Coherent 揭露六吋 InP 線出現良率或產能問題，或把「CY27 底前自有 InP 產能再倍增」（2026-11-04 8-K 投影片）延後或下修，產能位置的論點失效，thesis 需降評。
- 若客戶端或第三方文件揭露 Lumentum、住友、Coherent 之外的第四家 ELS 或高功率 CW 雷射供應商在 NVIDIA 或 PhotonLink 長約客戶處取得量產份額，或 Coherent 在 NVIDIA 的份額被具名縮減，三家之下的份額論點被稀釋，thesis 需降評。
- 若有具名客戶或出貨揭露 Open CPX 整合雷射模組（ILM，雷射整合在 CPO 模組裡、不用外部光源）進入量產，外部光源這個品類的必要性下降，thesis 需降評。(推導，非圖中明確主張)
- 若 PhotonLink 營收 2027-03 季沒有超過 1 億美元、CY27 底前沒有到每季 2.5 億美元，或公司下修 FY2027 pro forma 營收成長 >60% 的指引（三個數都是 2026-11-04 8-K 自己寫下的），CPO 放量沒有出現在數字裡，thesis 需降評。
- 若中國 InP 出口管制升級導致 AXT 北京廠的基板無法出貨，且 Coherent 下一份 10-Q 或法說沒有寫出替代來源已到位，放量計畫受阻，thesis 需降評或退場。

## 7. 接下來盯什麼

- **每季（Coherent 財報＋法說）**：PhotonLink 營收（2026-12 季小量、2027-03 季 >1 億美元、CY27 底前每季 >2.5 億）、Datacenter & Communications 分部年增率、400mW CW 雷射的 CPO 營收從 2026-12 季開始認列 [E6]。
- **CY27 底**：自有 InP 產能第二次倍增；蘇黎世六吋線 2027 上半年投產（法說，自動轉錄）[E8][E9]。
- **每次客戶或競爭者公告**：ELS 供應商名單有沒有變、有沒有具名的 ILM 客戶 [E3][E12]。Lumentum 2026-11-01 和 Marvell 簽了合併協議（Lumentum 10-Q：每股換 4.5 股 Marvell，最晚可延到 2028-08-01 交割），同一份 10-Q 寫 2026-09 和一位客戶簽產能保留協議、第一期 1 億美元。法說說 400mW 這一級只有一家競爭者；若那一家是 Lumentum [E5]，合併後的 Marvell 會同時握有光 DSP 與高功率雷射，要看它會不會把雷射綁進自己的光引擎（推導；兩份文件都在圖外，pq1 `lead_48ea4a51…`）。
- **上游（每季＋事件）**：AXT 出口許可與北京廠交付；Coherent 和基板廠的長約 [E13][E14]。

## Evidence Gate Notes
- ⚠ [E16] 瓶頸主張只由供應方／被分析公司單一自報來源支持 (`single_origin_self_report`)
- ⚠ [E17] 瓶頸主張只由供應方／被分析公司單一自報來源支持 (`single_origin_self_report`)

本報告因上述 evidence gate 未通過，維持 Research Note。
