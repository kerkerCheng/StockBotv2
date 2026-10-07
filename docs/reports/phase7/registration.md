# Phase 7 預先登記（registration）——T0＝2026-10-04

> **性質：預先登記。本檔 commit 之後不改**；更正只能在檔尾「更正與追加」一節之後 append（日期、改什麼、為什麼）。
> 新增 case 也是 append，開題日＝那次 append 的 commit 日，不得早於它（plan §0 不可越線第 2 條）。
> **用途：** 讓 2026-10-04 之後出現的證據去裁決今天寫下的假說與 case，不能事後挪球門（proposal §5.4）。
> **研究與評估分離：** 本檔與 `cases.md`、`failure-log.md`、`cohort-changes.md` 只**引用** id（`sr_*`、`ib_*`、`ew_*`、`hy_*`、lead id、pq2 編號、SourceDoc id），
> 不改任何 ledger；lead、pq2、watch 的狀態只住各自的 registry（AGENTS「不建立第二個狀態源」）。
> **數字都是 T0 快照**（T0 manifest 生成於 2026-10-04T07:09:14Z，對照心跳 `heartbeat_2026-10-04.md`；§8）。判準不會腐壞，數字會。
> 來源：plan [`2026-10-04-001`](../../plans/2026-10-04-001-research-phase7-research-edge-plan.md) §1（Step 7.0a）、
> proposal [`2026-10-04-phase7-research-edge-proposal.md`](../../brainstorms/2026-10-04-phase7-research-edge-proposal.md) §3–§8。

---

## 0. 判讀總則（先於一切假說與 case）

1. **每個假說的狀態只有三種：支持／削弱／不足。不合成分數**，不加權成總分（plan §11 第 2 項）。
2. **殺死條件裡的數字是預先登記的判讀線，不是投資門檻**：不進候選狀態的前提、不排序、不給尺寸（AGENTS 消費契約、G1）。
   n 照印；低於最小 n 就是「不足」，不判方向。
3. **逐份判斷算，不逐檔算**（proposal §0）：同一檔上的讀圖、敘事、thesis 各自一列；AXTI 的讀圖可能對、thesis 可能錯。
4. **評估用開題當時那一版**：§2 每個 case 寫的 id 就是被評的版本。之後的新版是新紀錄，可以另開一列，但不取代開題那一列
   （paper lane 用第一份 v2 敘事是同一個紀律）。
5. **選題不依預期報酬**：16 個 case 依假說與類型覆蓋選（proposal §6.2、plan §10），不依「哪檔會漲」。
6. **LLM 不站在 2026-06 之前判讀**（研究者知識截止，proposal §4.2）；任何要求「假裝站在 2026-06 之前」的判讀不進證據帳，計數照印。
7. **H8（point-in-time）是效度條件，不是 edge 假說**：不測它、只守它。違反的列（例：紀錄的 `created_at` 早於本檔 commit 卻自稱是 wave 1 產出、
   拿今天的財報算過去的百分位）從證據帳排除，排除筆數照印（INV-3、INV-6）。

### 0.1 時點與量法定義（本 Phase 唯一的一份；評估檔引用，不另定）

| 名詞 | 定義 |
|---|---|
| **第一次接觸日**（discovery PIT） | lead registry 中該公司最早的 `first_seen`（`company_id` 或 `entities.company_ids` 指向它；名冊沒有的公司以 cashtag／代號字串或公司名逐字比對，**比對方法逐列記下**——ticker 不是 identity，INV-1）。沒有任何 lead → 該公司第一次被寫進讀圖或敘事的 `created_at`；都沒有 →「系統沒有接觸」。⚠ X 帳號在 2026-07 下旬做過 30 天回補：**帳號發文日**（`called_on`／lead `published_at`）與**系統接觸日**（`first_seen`）分開記，不互相代替。⚠ lead registry 只從 2026-07-22 起是真的（proposal §4.1）：T0 之前的接觸日受系統開機日截斷，與 T0 之後的接觸分開列 |
| **證據時點**（evidence PIT） | SourceDoc `published_at`；推不出日期留 null 並計數，**不得用 retrieval／ingest 日期冒充**（AGENTS L11-5） |
| **追高** | 沿用既有唯一定義：錨點前 30 個日曆日的漲跌幅 > 錨點後到量測日的漲跌幅（`scripts/outcome_if_settled_today.py` 的 `PRE_ANCHOR_DAYS = 30`、`_pre_anchor_return`、`chase_count`；追蹤表「入圖前已漲」「敘事前已漲」同一個函式）。本 Phase 不另定 |
| **超額** | 對**該鏈**的主題等權組：光通訊＝`tc_35b0d5cd521656ea`（2026-09-30，pq2 [656]）；電力、散熱＝7.1 前瞻定義的組（id 記進 `cohort-changes.md`）。某段期間該鏈的組還沒定義 → 那一格寫「組未定義」，**不拿別的組代替、不寫 0**。價格走既有取價層（追蹤表同一條序列），排除未收盤 K 棒（Phase 6 Step 6.7c 的 owner） |
| **2×2 的錨點** | 有 v2 敘事的 case＝**第一份 v2 敘事日**（paper lane 錨點）；開題時沒有敘事的 case＝之後第一份 v2 敘事日（必須晚於本檔 commit）；O5 另定（見該段） |
| **量測日** | 檢查點當天（台北）之前最後一個完整交易日；Q3 裁決的量測日＝該份財報發布日之後第 30 個日曆日（不到 30 天就寫「未滿」） |
| **偏差標註** | 回放與評估的每一列都標：①discovery lookahead（這一列是怎麼被看見的、當時系統有沒有路徑看見它）②選樣偏差（這一列是怎麼進樣本的）③超額基準是否回溯定義（光通訊組在 2026-09-30 才定義，更早的錨點是拿今天的組回頭比） |

### 0.2 「錯」的分法（沿用 `alpha/structure_reading/predictions.py::WRONG_KINDS`；不另定）

判定錯的那份新來源（或判觸及引用的文件）的 `published_at`，對被評紀錄的建立日（讀圖 `created_on`、敘事 `created_on`、thesis memo 生成日）：

| kind | 意思 | 判法 |
|---|---|---|
| `already_available` | **當時已有反例**（讀得不夠） | 新來源的發表日早於被評紀錄的建立日 |
| `emerged_later` | **之後才出現**（判斷錯） | 新來源全部晚於或同日 |
| `undated` | **未定日** | 沒有新來源、沒日期、或日期精度跨過建立日那一天 |
| `upstream_unavailable` | 日期對照表讀不到（不是未定日） | 程式讀不到 SourceDoc 日期時 |

---

## 1. 十個假說（H1–H10）

> 每個假說：一句話｜今天的證據（含 n）｜用哪些 case 測｜**削弱（殺死條件）**｜支持｜不足｜量在哪一層。
> case 代號見 §2；判讀在 7.5 檢查點（2026-12-22）做第一次，之後每季。

### H1 層／插槽讀圖能在價格之前找到薄層

| | |
|---|---|
| 今天的證據 | AXTI 弱正面（n＝1）：AXT 8-K（SourceDoc `axti_8_k_20260702_coherent_inp_supply`，`published_at` 2026-07-02；EDGAR lead 記 07-08）早於 07-29 → 07-31 的三天 +63% 約四週，系統第一次接觸（`lead_f05f3fd8a753c084704afc3b06330a47`，`first_seen` 2026-07-22）早約一週。反面：追蹤表 history lane「入圖前已漲」8／22（追高定義，§0.1） |
| 用哪些 case 測 | 主：P1、P2、C1（新鏈，接觸日在 T0 之後）；輔：O1、X3、X4 |
| 單位 | Phase 7 新寫的讀圖（層或插槽）裡被讀成**供給側**、坐在「薄層」上的上市公司——薄層＝該讀圖判 `volume` 或 `moat`，或判 `undecided` 但供給側 ≤ 3 家。每家一列：錨＝第一次接觸日（§0.1）、追高與否、量測日 |
| **削弱（殺死條件）** | **T0 之後接觸的配對列 n ≥ 6，而且追高 ≥ 半數** → 削弱（初判）；下一個季檢查點仍 ≥ 半數 → 削弱（確認） |
| 支持 | T0 之後接觸的配對列 n ≥ 6，追高 ≤ 三分之一 |
| 不足 | n < 6，或介於兩者之間 |
| 另印（不進判讀線） | T0 之前接觸的列（光通訊既有）另列——接觸日受 07-22 開機日截斷；X3 前四分之一裡「系統接觸早於窗口起點」的比例——量的是發現面寬度（F6），不是讀圖 |
| 量在哪一層 | 讀圖（哪些公司）、registry（`first_seen`）、追蹤表（價格） |

### H2 一手來源紀律提高準確度（保守的成本沒有大過它擋下的錯）

| | |
|---|---|
| 今天的證據 | 擋下錯誤 n＝2（Sivers 重編指控經一手稽核不成立、AXT v1 被紅隊推翻）；**成本那一側 n＝0**：parked 484 則，其中 `original_obtained` 353 則；InP 兩則截圖假說（`hy_0001_2026-08-31` 短缺／史上最大漲價、`hy_0003_2026-08-31` Nomura ASP）至今 active 未證實，期間股價方向與主張一致（60.61 → 85.87；n＝1，不是裁決） |
| 用哪些 case 測 | X2（R2 抽樣 36 則，§7.3）、P3（800VDC 擱置五則）；O1 的兩則截圖假說列為輔證 |
| 「證實」的定義 | 之後的**一手**文件補上了當初 park 理由所缺的那一樣（例：理由是「生態系成員不等於供貨合約」→ 之後出現具名供貨合約或客戶端具名）。只有二手 → 不算（L11-3）。記文件 id／網址與 `published_at` |
| 量法 | 證實比例：各層分開印，合併時依層的母體大小加權（§7.3）。每則證實者：park 日（lead `triage.decided_at`，缺則 `first_seen`）→ 證實日的超額，對比證實日 → 量測日的超額 |
| **削弱（殺死條件）** | **加權證實比例 ≥ 1/3，而且證實者中過半「證實前超額 > 證實後超額」**（行情在一手證實前就走掉了） |
| 支持 | 加權證實比例 < 1/6；或證實者中過半「證實後超額 ≥ 證實前超額」（等一手沒有錯過行情） |
| 不足 | 證實 < 4 則，或其他情形 |
| 量在哪一層 | registry（lead 終局、證實文件）、追蹤表（價格） |

### H3 客戶端／第三方印證預測持久性

| | |
|---|---|
| 今天的證據 | Phase 6 已把證據標籤做誠實；**outcome n＝0**。T0 分布（manifest `graph.classified_edges`）：534 條 canonical 邊，外部印證 236；其中 `supplies_to` 205 條＝外部印證 32、供應商自報 65、自報·filing 66、媒體轉述 35、待判定 4、雙方聯合 3 |
| 用哪些 case 測 | 主：T0 全部 `supplies_to` 邊；case 證據：O2（Sivers 供貨邊只有自報）、O4（AAOI 供應商自報強、客戶證據弱）、X4 |
| 單位與分組 | T0 manifest 的 `supplies_to` 邊，**等級以 T0 為準**（之後的升降不改分組）；外部印證組（32）對自報組（自報 65＋自報·filing 66） |
| 推翻事件（每條邊至多記一次） | ①之後的一手文件否定這條供貨關係、或它的 `sole_source`／合格狀態，且圖經 pq2 更正；②綁這條邊兩端實體的讀圖／敘事反證被判觸及，而且觸及理由指向這條邊；③遷移中因「錯」而退役 |
| **削弱（殺死條件）** | **推翻事件 ≥ 3，而且外部印證組的推翻率 ≥ 自報組的推翻率** |
| 支持 | 推翻事件 ≥ 3，而且自報組推翻率 ≥ 外部印證組的兩倍 |
| 不足 | 推翻事件 < 3 |
| 量在哪一層 | 圖（T0 分組與更正）、registry（觸及、pq2） |

### H4 合格狀態／可替代性證據預測第二來源事件

| | |
|---|---|
| 今天的證據 | n＝1，而且在 T0 之前：COHR「NVIDIA CPO 外部光源唯一」被第二供應商推翻（2026-09-19；推翻文件發表於 2025-03-27、2026-03-02、2026-05-06——見 O5） |
| 用哪些 case 測 | 主：T0 全部 `supplies_to` 邊；case 證據：O5、O1、O2 |
| 分組 | 高組＝T0 時 `substitutability` ≥ 4 或 `sole_source`＝true；低組＝`substitutability` ≤ 3；sub 為空、且 `sole_source` 不是 true 的邊不進 H4（筆數照印） |
| 第二來源事件 | 之後的一手或第三方文件具名同一個下游節點（dst）的另一家供應商（圖上新增一條 `supplies_to` 到同一 dst，且 origin 不是那家供應商自己），或客戶端文件說明多來源 |
| **削弱（殺死條件）** | **事件 ≥ 3，而且高組的事件率 ≥ 低組** |
| 支持 | 事件 ≥ 3，而且高組事件率 ≤ 低組的一半 |
| 不足 | 事件 < 3。O5 只當 T0 前的案例描述，不進比率 |
| 量在哪一層 | 圖、registry |

### H5 往上游走（二階瓶頸）比第一層更容易找到非共識公司

| | |
|---|---|
| 今天的證據 | 無（n＝0） |
| 用哪些 case 測 | 三個二階 case：**P2**（變壓器上游）、**O1-U**（InP 上游）、**O6**（光通訊磊晶與 MOCVD 產能） |
| 每個 case 的結論（兩部分，7.4 寫進 case 段） | (i) 擋住研究的是什麼：表示法／證據／都沒擋；(ii) 上游有沒有比第一層更不擁擠、而且可投資的公司：**有**（列名字與讀圖／敘事 id）／**沒有**（巨頭、私人公司，或已被同樣定價）。結論要指得出讀圖、敘事或 Abstention 紀錄（plan §10） |
| **削弱（殺死條件）** | **三個裡 ≥ 2 個的 (ii)＝沒有** |
| 支持 | 三個裡 ≥ 2 個的 (ii)＝有 |
| 不足 | 其餘 |
| 另 | proposal §8 的產品化條件（≥ 2 個顯示「表示法擋住」**而且**上游找得到第一層看不到的候選）由 (i)(ii) 直接讀出，在 7.5 提；**三個 case 的判準在 wave 2 不得改**，只能 append 新 case |
| 量在哪一層 | 讀圖、敘事（或 Abstention） |

### H6 專家 SNS 比別的管道早知道後來被證實的事

| | |
|---|---|
| 今天的證據 | 帳號計分表（as-of 2026-10-03，**只有 1 個帳號**）：30 天對主題等權組 −6.3%（n＝802）、首次點名 90 天 −11.1%（n＝29）、追源成功率 39%（n＝471）；`hypothesis_hit_rate`＝`capability_absent`（n＝0）。⚠ 主題等權組是回溯定義 |
| 用哪些 case 測 | S1（40 則首次點名；規則 §6）。雷達（7.0f）的 lead 是「一般資訊」的對照組，7.5 只並列印出、不進本假說的判讀線（晚於 T0 才開始，不同期） |
| 量法 | 主判讀只用**結構型與財務型**主張：證實率＝證實 ÷（證實＋推翻），未定另列；**提前天數**＝一手 `published_at` − 帳號發文日（正＝帳號較早）；另列「對系統其他管道」的提前：其他管道對同一家公司最早的 `first_seen` − 帳號發文日 |
| **削弱（殺死條件）** | **已裁決（證實＋推翻）≥ 10，而且（證實率 < 1/3，或證實者提前天數的中位數 ≤ 0）** |
| 支持 | 已裁決 ≥ 10、證實率 ≥ 1/2、證實者提前天數的中位數 > 7 |
| 不足 | 已裁決 < 10，或其他情形 |
| 量在哪一層 | registry（截圖假說層、lead registry）、追蹤表（價格） |

### H7 反證／watch 改善出場時點

| | |
|---|---|
| 今天的證據 | n＝1：AXT thesis 反證第 6 條 2026-08-04 觸發（65.27），之後 95.97 → 56.11 → 85.87（10-02）——到今天偏負面（觸及時出場會少賺），波動大；COHR thesis 2026-09-19 觸發（revised），之後價格未量 |
| 用哪些 case 測 | O1、O2、O5，以及 7.3 財報季裡所有被判觸及的反證 |
| 單位 | 每一條被判觸及（`event_watch judge` 判 yes）的反證，讀圖、敘事、thesis 各自算；**同一檔同一天的多條觸及算一條**。T0 之前的兩次（AXT 08-04、COHR 09-19）列為「T0 前案例」另列，不進判讀線 |
| 量法 | 觸及日起 30 天、與觸及日到量測日（取 90 天與實際天數較短者），對該鏈主題等權組的超額 |
| **削弱（殺死條件）** | **T0 之後觸及 ≥ 4 條，而且觸及後超額平均 ≥ 0**（照反證出場平均會少賺） |
| 支持 | T0 之後觸及 ≥ 4 條，觸及後超額平均 < 0，而且過半為負 |
| 不足 | < 4 條 |
| 量在哪一層 | registry（watch 觸及紀錄）、追蹤表（價格） |

### H8 point-in-time 紀律——**效度條件，不是 edge 假說**

不測、只守（§0 第 7 條）。守法：本檔 commit 時間早於 wave 1 每一份新讀圖／敘事的 `created_at`（7.1 結束時核對）；回放每一列標偏差（§0.1）；
R1 每個時點用的財報 `filed` 日早於該時點；T0／T1 manifest 對照（§8、plan §11 第 5 項）。違反的列排除並計數。

### H9 「已定價」（自家三年百分位）的判斷有價值

| | |
|---|---|
| 今天的證據 | AXTI：2026-09-29 判已定價（78.18）之後 3 天 +10%（雜訊，n＝1）；結構性疑慮：power-law 贏家**照定義**會衝出自己的歷史區間。T0 三題「已定價①」有值 28／缺席 48（76 檔） |
| 用哪些 case 測 | X1（R1；分組 §7.2）、O1、P1；以及 campaign 中每一份判「已定價」的新敘事（判定日為錨） |
| **削弱（殺死條件）** | **R1 四個時點中 ≥ 2 個，高組之後的平均超額 ≥ 低組（每組 n ≥ 4）**——這一格沒有區分力。2 比 2 平手算削弱：未量測的機制不享有默認信任，舉證責任在「已定價」這一格（INV-5） |
| 支持 | 四個時點中 ≥ 3 個，高組平均超額 < 低組（每組 n ≥ 4） |
| 不足 | 其他（含任何時點因 as-of 視角沒接而「未量」，Phase 3 #15） |
| 另印（不進判讀線） | 之後曾達 2 倍的列，在錨點被分在哪一組——「贏家被標成已定價」的頻率 |
| 量在哪一層 | 追蹤表（R1 分組表）、敘事 |

### H10 客戶資本承諾（預付、押金、帶對價的長約、客戶入股）是最強的單一結構訊號

| | |
|---|---|
| 今天的證據 | AXTI 三份帶對價的合約（Coherent 預付 22,288,500 美元、Lumentum 兩筆各 4,350 萬美元押金、Casela 人民幣 1.73 億元先付一半），第一份公開後市場三週沒反應（n＝1）；COHR：NVIDIA 投資 20 億美元＋非獨家採購承諾；反例 POET：供應商以 2,292 萬份認股權證換 Lumilens 訂單（ARCHITECTURE §6） |
| 用哪些 case 測 | O1、O3、P1、C1，以及新鏈中每一份寫了付錢方向的敘事 |
| 分組 | 每個 case 開題時（或第一份敘事時）依一手原文標**付錢方向**（封閉四選一）：客戶掏錢／供應商掏錢（認股權證、回扣、供應商入股客戶）／無／不明。T0 已知：O1＝客戶掏錢、O3＝供應商掏錢、COHR（O5 脈絡）＝客戶掏錢 |
| 量法 | 各組的結構確認率（快／中迴路裁決＝證實的比例）與錨點起對該鏈組的超額 |
| **削弱（殺死條件）** | **「客戶掏錢」組已裁決 ≥ 3 個 case，而且確認率 ≤「無」組，而且平均超額 ≤「無」組** |
| 支持 | 「客戶掏錢」組已裁決 ≥ 3 個 case，確認率與平均超額**都**高於「無」組 |
| 不足 | 其他 |
| 量在哪一層 | 敘事（付錢方向與裁決）、追蹤表（價格） |

---

## 2. 驗證集（16 個 case＝附錄 A 的 14 個＋plan §10 要求在 7.0a 一併登記的兩個二階 case）

> 開題日一律＝本檔 commit 日。「開題時已知」只列 id 與日期，不列結論以外的推論；「被評的版本」＝§0 第 4 條所說的那一版。

### O1 AXTI／InP 基板（光通訊）

| 欄 | 內容 |
|---|---|
| 類型 | 結構對、判斷可能錯（winner；也是「股價大漲但 thesis 不成立」的那一半） |
| 測 | H1、H7、H9、H10（另：H2 輔證 `hy_0001`、`hy_0003`） |
| 開題時已知 | 讀圖 `mat:inp_substrate` 8 筆（2026-09-17 起），現行 **`sr_b8b405c96d8747c1`**（2026-10-03，volume，反證 7 條＝`ew_0158`–`ew_0164`_2026-10-03，到期 2027-01-01）；敘事現行 **`ib_8c35bc994d0c1047`**（2026-10-03，`priced_wait`，候選 watch `ew_0148_2026-09-29`（until 2026-11-13）、自有反證 `ew_0171_2026-10-03`），第一份 v2 **`ib_b6b3b1b8ebaaa438`**（2026-09-29，paper lane 錨點），v1 `ib_143a8faf3ebbee4e`（2026-09-17；「往下的差異」那一格的 `{bet_target}` 填的是同日寫下的 variant 賭注，每股約 47 美元，thesis memo §7b、pq2 [600]）；thesis `axt_inp` active（memo `thesis/axt_inp_v1_lane_memo.md`，v4 2026-08-04「謹慎偏空」，反證 6 條 `ew_0096`–`ew_0101`_2026-09-24，last_checked 2026-09-17、next_check 2026-11-15）；截圖假說 `hy_0001_2026-08-31`、`hy_0003_2026-08-31`（active）；第一次接觸 `lead_f05f3fd8a753c084704afc3b06330a47`（edgar:AXTI，`first_seen` 2026-07-22）；history lane 入圖日 2026-07-28；關鍵一手 `axti_8_k_20260702_coherent_inp_supply`（2026-07-02）、`axt_pr_lumentum_lta_2026_07_30`（2026-07-30）、`jx_metals_inp_capacity_pr_2026_06_16`（2026-06-16） |
| 被評的結構斷言 | ①讀圖：量的賭注——三家供給、可互換、產能同時補不上，窗口到 2026–2028 擴產開出來；②敘事「必須為真」：Q2 是新基本盤、三家擴產沒提前也沒有第四家、客戶照約付款；③thesis v4：AXT 不是結構性受益者（供給側 2028 前大幅擴張） |
| 付錢方向（H10） | 客戶掏錢（三份帶對價合約） |
| 預期會暴露的 failure mode | F3：判斷層把我們從贏家身上說服走；**四份判斷彼此不一致**（讀圖偏多、thesis 謹慎偏空、variant 約 47 美元、敘事等回落）；「已定價」把贏家標成已定價（H9） |
| 支持／削弱的判準 | **H7**：Q3 裁決 ①② 成立，而且 2026-08-04 觸發日之後到量測日對光通訊組超額 > 0 → 本 case 記「削弱 H7」；Q2 被證明是一次性（Q3 營收 < 47.589M 美元或毛利率 < 35%）而且觸發日後超額 ≤ 0 → 記「支持 H7」。**H9**：2026-09-29 判已定價起到量測日對光通訊組超額 > 0 而且②成立 → 記「削弱 H9」；超額 ≤ 0 → 記「支持 H9」。**H10**：Q3 10-Q／8-K 顯示預付或押金已入帳、而且營收或出貨上升 → 記「支持 H10」；客戶退出或沒照約付款 → 記「削弱 H10」。**H1**：錨＝07-22 的追高判定記一列（T0 前接觸，另列） |
| 2×2 | 三列：讀圖①、敘事②、thesis③；欄＝2026-09-29 起到量測日對光通訊組超額 |
| 裁決點 | Q3 法說（lifecycle 估 2026-10-30，以公司公告為準）；Q3 10-Q（估 2026-11-13）；讀圖到期 2027-01-01 |

### O1-U InP 上游：銦、晶體生長、出口管制（光通訊；二階 case 之一）

| 欄 | 內容 |
|---|---|
| 類型 | 二階瓶頸 |
| 測 | H5 |
| 開題時已知 | 圖上 `mat:inp_substrate` **之上沒有任何節點**（沒有銦金屬、磷、晶體生長〔VGF〕設備的節點或邊；`DEPENDS_ON` 都是下游指向基板）；出口管制只以讀圖反證⑤（`ew_0162_2026-10-03`）與 Reuters 2026-06-11 的報導（pq2 [666] 升外部印證）出現；名冊沒有銦供應商 |
| 預期會暴露的 failure mode | 表示法擋住還是證據擋住：上游原料在下游 filing 很少具名；中國供應鏈的一手來源可得性 |
| 支持／削弱的判準 | 依 H5 的兩部分結論（i）（ii） |
| 裁決點 | Wave 2（7.4）結論；7.5 檢查點 |

### O2 SIVE.ST／CW DFB 與 ELS（光通訊）

| 欄 | 內容 |
|---|---|
| 類型 | 結構漂亮、獲利攫取弱（稀釋、執行時程）；flat 型 |
| 測 | H3（另：H7） |
| 開題時已知 | 讀圖：層 **`sr_00e18cf604cc66b9`**（`tech:cw_dfb_laser`，2026-10-03，volume，反證 6 條 `ew_0165`–`ew_0170`_2026-10-03）、插槽 **`sr_d85d672998445c50`**（`prod:supernova`，2026-10-01，undecided，`ew_0154`–`ew_0157`_2026-10-01）、插槽 **`sr_35ca0ce58617d5f6`**（`prod:els_8ch_module`，2026-09-25，undecided，`ew_0139`–`ew_0141`_2026-09-25）；敘事現行 **`ib_c9445bd7b28f7fcf`**（2026-10-03，`missing`，候選 watch `ew_0149_2026-09-29`（until 2026-11-26）），第一份 v2 **`ib_84e5efaf6360f042`**（2026-09-29）；thesis `sivers` active（memo `thesis/sivers_v4_lane_memo.md`，反證 `ew_0107`–`ew_0111`_2026-09-24；其中 **`ew_0108`（Jabil 通道）已被 JBL 8-K lead `lead_40ce405ec8b6542b8f4943b4ba364ccd`（2026-09-30）標旗、未判定**；last_checked 2026-09-29、next_check 2026-10-29）；已持有（Sheet）；第一次接觸 `lead_09abba7335ec575ec76ca63a92e5663f`（x:aleabitoreddit，2026-07-25）；history lane 入圖日 2026-07-23；截圖假說 `hy_0002_2026-08-31` verified |
| 被評的結構斷言 | 敘事「必須為真」①客戶端一手具名它供雷射陣列並走到量產、②外部光源模組年底前可量產且 2027 上半年前有非 NRE 的付費量產訂單、③錢夠用不必再大額增發；插槽讀圖的「確認」與「推翻」條件 |
| 付錢方向（H10） | 不明（T0 沒有客戶掏錢的一手） |
| 預期會暴露的 failure mode | 供貨邊只有自報（H3）；兩個插槽都判不出；瑞典申報人沒有機械的財報歷史（「已定價」與「出現在數字裡」都量不到）；稀釋 |
| 支持／削弱的判準 | **H3**：Q3（11-26）沒有非 NRE 產品營收、ELS 延後 → 本 case 記「自報斷言未撐住」（支持 H3 方向）；客戶端一手具名 Sivers → 記「自報被客戶端確認」（削弱 H3 方向）。**H7**：若 `ew_0108` 等反證被判觸及，依 H7 量法記一列 |
| 2×2 | 一列：敘事①②；欄＝2026-09-29 起對光通訊組超額 |
| 裁決點 | Q3 報告 2026-11-26；ELS production readiness 2026-12-31；thesis next_check 2026-10-29 |

### O3 POET（光通訊）

| 欄 | 內容 |
|---|---|
| 類型 | 公司小但不是關鍵供應商（供應商給權證換訂單） |
| 測 | H10（反例） |
| 開題時已知 | 圖：`co:poet_technologies supplies_to co:lumilens`（6-K 2026-05-14 designed_in、sub 4；6-K 2026-08-13 qualifying）、`develops prod:blazar`（6-K 2026-08-13）、`prod:blazar competes_with tech:cw_dfb_laser`（damnang substack，無日期，待判定；是 CW DFB 讀圖反證③的現況那 1 條）、`co:sivers_semiconductors supplies_to co:poet_technologies`（sampling）；認股權證換 Lumilens 訂單：RA `ra_353d5e662ef996de0a8f0f649e599819`（2026-08-31）與 ARCHITECTURE §6；X 主張「Sivers 雷射 production 年底」被一手反駁：`lead_d3b3988d99ff494fe07af958c6b5bc1e`（parked，contradicts）；在光通訊主題等權組；**沒有敘事、沒有以它為主體的讀圖**；S1 框架裡的首次點名 2026-07-02 |
| 付錢方向（H10） | 供應商掏錢（認股權證） |
| 預期會暴露的 failure mode | 「不要」的理由要說「不是瓶頸」而不是「非邊緣」——候選狀態的理由與付錢方向能不能清楚寫出來；它同時是 CW DFB 層反向路徑上的替代者 |
| 支持／削弱的判準 | 7.1 依既有證據寫 v2 敘事（預期「不要」）。之後：POET 沒有拿到客戶端或第三方的關鍵供應商具名、而且對光通訊組超額 ≤ 0 → 記「支持 H10」（反例成立）；拿到客戶端具名的關鍵地位、而且超額 > 0 → 記「削弱 H10」 |
| 2×2 | 一列：7.1 敘事的結構結論；欄＝該敘事日起對光通訊組超額 |
| 裁決點 | 既有證據即可結案（7.1）；價格在 7.5 記一次 |

### O4 AAOI（光通訊）

| 欄 | 內容 |
|---|---|
| 類型 | 供應商自報強、客戶證據弱（加上 ATM 稀釋） |
| 測 | H3 |
| 開題時已知 | 圖：`co:applied_optoelectronics` 供 pluggable／1.6T（自家新聞稿 2026-07-14、primetrading substack、Zacks）、`competes_with` Coherent／Lumentum（10-K 2026-02-27）、`constrained_by` 400mW pump laser（法說 2026-08-06）；RA `ra_629fa230dd48b82ed39db2f3dc161027`（ELSFP 2028 年月產約 40 萬件，已入圖）；截圖假說 `hy_0004_2026-08-31`（Rosenblatt summit：美國產溢價、產能售罄、多份 LTA，active，到期 2026-12-31）；`lead_cad23eb9c017f318ac8f52d75da7d4a8`（ATM 稀釋，triaged_go，2026-09-24）、`lead_7bffab80ea65599892880f07b65189d3`（parked）；歸零燈有紅；history lane 入圖日 2026-07-24；在光通訊主題等權組；**沒有敘事、沒有讀圖**；S1 首次點名 2026-06-29 |
| 被評的結構斷言 | 供應商自報的產能與需求（LTA、售罄、ELSFP 2028 產能）會不會被客戶端或第三方確認 |
| 付錢方向（H10） | 不明（T0 沒有客戶掏錢的一手；ATM 是向市場募資） |
| 預期會暴露的 failure mode | 自報被當成結構；稀釋燈與「要翻倍需要什麼」的衝突 |
| 支持／削弱的判準 | Q3 前後：客戶端或第三方一手具名 AAOI 的量產供貨 → 記「自報被確認」（削弱 H3 方向）；`hy_0004` 到期未證實、或 Q3 顯示自報的量沒出現 → 記「自報未撐住」（支持 H3 方向） |
| 2×2 | 有敘事才填（錨＝第一份 v2 敘事日）；沒有敘事 → 「尚未到裁決點」 |
| 裁決點 | AAOI Q3 財報（11 月上旬，以公司公告為準）；`hy_0004` 到期 2026-12-31 |

### O5 COHR 外部光源第二來源（光通訊）

| 欄 | 內容 |
|---|---|
| 類型 | 圖的斷言被推翻（已發生，2026-09-19） |
| 測 | H4（另：H7 的 T0 前案例） |
| 開題時已知 | 被推翻的斷言：`co:coherent supplies_to co:nvidia` `sole_source`＝true（「NVIDIA CPO 外部光源目前只有它一家」——敘事 v1 `ib_5c84b4d53fdab440`，2026-09-15）；推翻：pq2 [627] 把 `sole_source` 改 false、pq2 [629] thesis `coherent_cpo` active → review_required（2026-09-19）、pq2 [636] → revised（2026-09-21）；推翻文件 `nvidia_sipho_blog_partner_roles`（`published_at` **2025-03-27**）、`nvda_lumentum_partnership_pr_2026_03_02`（**2026-03-02**）、`cohr_10_q_20260506`（**2026-05-06**）；之後的敘事 `ib_37dfb9b27153eba8`（2026-09-19，v1）、第一份 v2 `ib_9a581a19a43d2e41`（2026-09-29，`pass`）、現行 `ib_0c22f37bf4b8052c`（2026-10-03，`pass`，非邊緣）；thesis 反證 `ew_0102`–`ew_0106`_2026-09-24；已持有（Sheet）；第一次接觸 `lead_bdd03e8e9f98242b0023cb2a3a7eff0c`（edgar:COHR，2026-07-22）；history lane 入圖日 2026-08-18 |
| 付錢方向（H10 脈絡） | 客戶掏錢（NVIDIA 投資 20 億美元，非獨家） |
| 預期「錯」的種類 | **`already_available`（當時已有反例）**——三份推翻文件都早於「唯一」那個判斷（2026-07 thesis、2026-09-15 敘事）。7.1 從 mutation 歷史與當時的圖核對；若核對結果不同，寫進 case 段的裁決行，本格不改 |
| 預期會暴露的 failure mode | 讀得不夠：反例早已在一手文件裡，判斷時沒讀到 |
| 支持／削弱的判準 | 只當 H4 的 T0 前案例描述（不進比率）：核對結果是 `already_available` → 記「當時的 sole_source 證據沒有預測到第二來源，而且反例早已公開」；H7 的 T0 前案例另列（觸發 2026-09-19 之後的超額） |
| 2×2 | 一列：斷言＝推翻；欄＝**2026-09-19（推翻日）起**到量測日 COHR 對光通訊組超額；另列 thesis memo 2026-07-17 重生成日 → 2026-09-19 的超額作脈絡 |
| 裁決點 | 已發生；7.1 寫 case 段；價格在 7.5 記 |

### O6 光通訊磊晶與 MOCVD 產能（光通訊；二階 case 之一）

| 欄 | 內容 |
|---|---|
| 類型 | 二階瓶頸 |
| 測 | H5 |
| 開題時已知 | 圖：磊晶側 `co:iqe`（供 MACOM、Tower；`constrained_by mat:inp_substrate`，IQE 年報 2026-05-28）、`co:intelliepi`（供 VCSEL、photodiode，sub 2）、VPEC 與 LandMark 對 IQE 的 `competes_with`；**MOCVD 設備商（例：Aixtron、Veeco）不在圖、不在名冊**；光通訊主題等權組有 IQE.L、4971.TWO、2455.TW |
| 預期會暴露的 failure mode | 設備產能這種二階限制，下游文件很少寫；磊晶「自製還是外購」的比例沒有表示法 |
| 支持／削弱的判準 | 依 H5 的兩部分結論（i）（ii） |
| 裁決點 | Wave 2（7.4）結論；7.5 檢查點 |

### S1 X 帳號 40 則首次點名的 claim 裁決（跨鏈）

| 欄 | 內容 |
|---|---|
| 類型 | SNS 早點名但沒被一手證實（來源看錯／看對） |
| 測 | H6 |
| 開題時已知 | 帳號計分表（as-of 2026-10-03）`aleabitoreddit` probation（2026-09-17 起）：具名點名 992、40 檔；框架 40 則見附錄 B（sha256 `2f12fc28…`）；截圖假說層 T0 有 7 則（`hy_0001`–`hy_0007`）；計分表 `hypothesis_hit_rate`＝`capability_absent` |
| 規則 | §6（看結果之前寫） |
| 預期會暴露的 failure mode | 框架只含名冊有 id 的代號（計分表的 lead 過濾已濾掉「沒點名公司」126 則、「代號不在名冊」44 則）——**選樣偏向我們已在追的名字**；一則貼文多檔；回補造成「帳號發文日」與「系統接觸日」不同 |
| 支持／削弱的判準 | 照 H6 的判讀線（§1）：已裁決 ≥ 10 才判方向 |
| 裁決點 | 抽樣當下（7.1）＋每則各自的到期 |

### P1 345／765 kV 超高壓變壓器（電力；新鏈）

| 欄 | 內容 |
|---|---|
| 類型 | 瓶頸明顯、市場高度共識；預期「thesis 成立但股價沒表現」或「系統該說沒有 edge」 |
| 測 | H1 對 H9（另：H10） |
| 開題時已知 | **圖上 0 個變壓器節點；名冊沒有以電網設備（變壓器、開關設備）為主業的公司**（住友電工、LiteOn 在名冊裡，登記的角色是 InP 基板與 POET 夥伴）；**lead registry 沒有任何以變壓器為主題的 lead**（只有一則 X 腦暴清單順帶點名乾式變壓器股，`lead_1f5a72a9cba09c5fd62dbe8771534c95`，parked `not_pursued`）；`config/themes.txt` 沒有電力主題；結構表 10 個需求錨裡沒有電力；沒有主題等權組 |
| 預期會暴露的 failure mode | 系統能不能說「結構對但已是共識」；海外一手來源（韓國 DART 等，旁支）；巨頭主導 |
| 支持／削弱的判準 | **H1**：讀圖找到坐在薄層上的邊緣公司，而且以第一次接觸日為錨的追高＝否 → 記一列支持；追高＝是 → 記一列削弱。**H9**：本鏈判「已定價」的敘事，之後對電力組超額 ≤ 0 → 記「支持 H9」；> 0 → 記「削弱 H9」。**H10**：依付錢方向記 |
| 2×2 | 錨＝本鏈第一份 v2 敘事日；欄＝對電力主題等權組超額（組在第一份敘事之前定義，§0.1） |
| 裁決點 | 各家 Q3 財報（10 月下旬至 11 月，以公告為準）與之後的訂單／產能公告；7.5 檢查點 |

### P2 變壓器上游：電工鋼（GOES）、套管、分接開關、測試產能（電力；二階 case 之一）

| 欄 | 內容 |
|---|---|
| 類型 | 二階瓶頸；很可能「沒有可投資的公司」（私人或巨頭） |
| 測 | H5 |
| 開題時已知 | 圖、名冊、lead registry 都是 0 |
| 預期會暴露的 failure mode | 上游供應商很少在下游 filing 具名（證據擋住）；可投資標的多為巨頭或私人公司 |
| 支持／削弱的判準 | 依 H5 的兩部分結論（i）（ii） |
| 裁決點 | 擴產公告、交期；Wave 2（7.4）；7.5 檢查點 |

### P3 800VDC 功率半導體與電源層（09-03 擱置的五則；電力）

| 欄 | 內容 |
|---|---|
| 類型 | park 之後世界動了什麼 |
| 測 | H2（另：F5） |
| 開題時已知 | 五則 parked（`original_obtained`，2026-09-03，decompose-800vdc-2026-09-03）：`lead_18be6b7764b40d7cb853925a0a4836eb`（板上 VRM／multiphase；理由「named-supplier role remains unproven」）、`lead_3e0ba028986066e33b30d7c97c0a33b9`（BBU／超級電容；「true unknown layer」）、`lead_4c2881be9b2f66a3b2b54291e26985aa`（整流與 800V busway；「ecosystem membership is not a supply contract」）、`lead_a4c2e14392aec9ce92ee74d1f1b6e81d`（GaN／SiC；「beneficiary ranking would be inference」）、`lead_fa672a299978b3f3ec2b0cf8ae1d4130`（DC/DC power shelf；「supplier relationship not proven」）；相關：`lead_f82cfe4629a23bc3a83a328b45bc7676`（Navitas 官方，parked）、`lead_3a7c4e5db3ecc1c420c1464fb73ac3c2`（X-FAB SiC 800V，parked partial）、`lead_798000da36c2b1aa3070ddf51bdd6019`（BBU 電芯短缺，X，parked）；圖上只有 `tech:power_gan`（GlobalFoundries 一條邊）與 `co:liteon`（POET 夥伴） |
| 預期會暴露的 failure mode | park 之後沒有人再看（F5）；理由正當不等於沒有成本 |
| 支持／削弱的判準 | 每則：當初 park 的理由今天站不站得住（有沒有一手補上缺的那一樣，H2 的「證實」定義）、證實前後的價格。五則與 X2 合併進 H2 的判讀（P3 自成一層，不併進 X2 的層） |
| 裁決點 | Wave 2（7.4）回看；7.5 檢查點 |

### C1 液冷（冷板、CDU、快接頭）台股供應商（散熱；新鏈、小）

| 欄 | 內容 |
|---|---|
| 類型 | 圖上不顯眼、但數字可能加速（台股月營收讓中迴路變快） |
| 測 | H1、H10 |
| 開題時已知 | 圖：`tech:thermal_solutions`（只有 Coherent 一條邊，IR deck 2026-03-17）、`tech:tec`；**系統 2026-08-29 已有一個結論**：`lead_1446a653c191897aeddb8b84419e4456`（decompose CPO switch 液冷層，parked）——「多供應商＋開放規格＝競爭層非瓶頸；Boyd／CoolIT 未上市、Vertiv 大市值廣覆蓋。不建議投入更多研究」；X 腦暴清單 `lead_1f5a72a9cba09c5fd62dbe8771534c95`（parked not_pursued）；名冊 0 家台股散熱公司；沒有主題等權組 |
| 預期會暴露的 failure mode | 08-29 的「競爭層」結論會不會讓研究先入為主；台股名字不在名冊（INV-1） |
| 支持／削弱的判準 | **H1**：讀圖找到坐在薄子層（快接頭、CDU、冷板之一）的台股邊緣公司，以第一次接觸日為錨的追高＝否 → 記一列支持；＝是 → 記一列削弱。若結論是「這一層沒有瓶頸」（讀圖或 Abstention）→ 不算 H1 的正反，照實記。**H10**：依付錢方向記 |
| 2×2 | 錨＝本鏈第一份 v2 敘事日；欄＝對散熱主題等權組超額 |
| 裁決點 | 每月 10 日月營收（2026-11-10、2026-12-10）；7.5 檢查點 |

### X1 已定價回放（R1；跨鏈）

| 欄 | 內容 |
|---|---|
| 類型 | 機械回放（零 LLM 判讀） |
| 測 | H9 |
| 開題時已知 | 母體＝history lane（22 列、21 檔）∪ 光通訊主題等權組（15 檔），去重 30 檔，其中有自家三年歷史的那些；T0 三題「已定價①」有值 28／76 |
| 規則 | §7.2 |
| 預期會暴露的 failure mode | 三題的 as-of 視角沒接（Phase 3 #15）；海外檔多半缺自家歷史 |
| 支持／削弱的判準 | 照 H9 的判讀線（§1）；history 列與 9 檔子群分開判 |
| 裁決點 | 7.2 一次性 |

### X2 parked 回查（R2；跨鏈）

| 欄 | 內容 |
|---|---|
| 類型 | 系統的保守有多貴 |
| 測 | H2 |
| 開題時已知 | parked × `original_obtained` 353 則（id 集合在 T0 manifest `leads.parked_original_obtained_ids`） |
| 規則 | §7.3（抽樣在本檔就固定，36 則，附錄 C） |
| 預期會暴露的 failure mode | F4／F5：拿到原文仍 park 之後沒有人再看；park 理由寫的是「當時缺什麼」，但沒有登記「什麼出現就該重看」 |
| 支持／削弱的判準 | 照 H2 的判讀線（§1），與 P3 合併判 |
| 裁決點 | 7.2 一次性 |

### X3 漏網稽核（R3；跨鏈；含「刻意不做 HBM」的代價）

| 欄 | 內容 |
|---|---|
| 類型 | 系統完全沒找到 |
| 測 | H1（輔）、F6 |
| 開題時已知 | 母體 §5（T0 定、之後只 append 不刪） |
| 規則 | §5.3 |
| 預期會暴露的 failure mode | F6：發現管道窄（新公司的入口只有 1 個 X 帳號、已追蹤公司的 filing、使用者選題的 decompose、互動題材掃描）——「系統沒找到」與「沒有機會」同形 |
| 支持／削弱的判準 | 不直接判任何假說的方向；「系統接觸早於窗口起點」的比例並列在 H1 旁（§1 H1「另印」），沒接觸的前四分之一逐檔進 7.5 的 failure log 候選 |
| 裁決點 | 每季：第一次在 7.2（窗口 2026 Q3），第二次在 7.5 |

### X4 history lane 輸家驗屍（R4；跨鏈）

| 欄 | 內容 |
|---|---|
| 類型 | 圖看錯，還是只是價格路徑 |
| 測 | H1、H3 |
| 開題時已知 | AEVA（入圖 2026-08-14）、MP（2026-08-27）、LYC.AX（2026-08-30）、6594.T（2026-09-01）、6680.HK（2026-08-31）；proposal §4.3 記的跌幅（AEVA −37%、MP −20%、LYC.AX −19%、6594.T −15%、6680.HK −12%）是 2026-10-04 的快照 |
| 規則 | 入圖日的圖投影（`query.bottleneck.project_assertions_as_of`）說了什麼 vs 之後的一手文件說了什麼；每檔結論封閉三選一：「結構讀錯」／「結構沒錯、是價格路徑」／「證據不足以判」 |
| 預期會暴露的 failure mode | 入圖時的圖只有一部分證據（discovery lookahead 反過來：當時沒讀到的反例）；錨點是入圖日、不是任何判斷 |
| 支持／削弱的判準 | 「結構讀錯」的檔：入圖時那條邊的 T0 證據等級進 H3 的事件（自報或外部印證）；「是價格路徑」的檔：不算 H1／H3 的反例，照實記 |
| 裁決點 | 7.2 一次性 |

---

## 3. 裁決規則

### 3.1 三個迴路（proposal §5.2）

| 迴路 | 時間尺度 | 單位 | 裁決來源 | 已有的機制 |
|---|---|---|---|---|
| **快** | 2–12 週 | 有日期、可否證的結構斷言（讀圖反證、敘事「必須為真」、截圖假說、S1 的主張） | 之後的一手文件（客戶 filing、季報、公告） | 語意 watch 的觸及／到期；圖預測表；截圖假說的 verify |
| **中** | 一季–一年 | thesis 要件：產能、合格、客戶導入、營收、毛利 | 每季財報；台股月營收 | 三題「出現在數字裡了嗎」；候選狀態序列；thesis 複查 |
| **慢** | 12–24 個月 | 主題調整後報酬、power-law 贏家 | 價格 | 追蹤表 paper／live lane、主題等權組、三個 power-law 統計量 |

### 3.2 「錯」怎麼記

用 §0.2 的四種 kind。每一筆「錯」在 case 段的裁決行寫：日期、判定錯的文件（id 或網址＋`published_at`）、被評紀錄的建立日、kind。

### 3.3 2×2（proposal §5.3）

每個 case、每份判斷各填一格：

| | 對該鏈主題等權組超額 > 0 | ≤ 0 |
|---|---|---|
| **結構斷言被證實** | 研究價值＋投資 alpha | 研究有價值、但市場早已定價 |
| **結構斷言被推翻** | 運氣或主題 beta | 研究錯、價格也錯 |

- 列＝快或中迴路對該 case「被評的結構斷言」的裁決；到量測日還沒有裁決 → 寫「尚未到裁決點」，不填格。
- 欄＝§0.1 的錨點起到量測日的超額；組未定義 → 「組未定義」，不填格。
- 累積到約 20 筆裁決再談要不要自動化（proposal §5.3）；本 Phase 手動。

### 3.4 裁決紀錄怎麼寫

- 每次裁決在 `cases.md` 該 case 段 **append 一行**：日期｜文件｜結論｜「錯」的 kind（若是錯）。不改舊行。
- 研究動作本身（新讀圖、新敘事、watch 判定、截圖假說 verify、pq2）照常寫進各自的 ledger／registry、照常走四個人工 gate；
  `cases.md` 只記 id。**是驗證 case 不改變任何東西**：出現「可開」照常上候選板，由使用者決定買不買（proposal §5.4）。

---

## 4. failure log 模板與開發 gate

每條 failure log（`failure-log.md`）回答七問（plan 附錄 B）：

1. 哪個真實 case 暴露了它？
2. 是第幾次出現（列出其他 case）？
3. 為什麼現有系統＋人工研究不夠？
4. 它增加的是**資訊**，還是只是**便利**？
5. 它有沒有新增 authority surface？
6. 怎麼驗收？
7. 做完之後，哪一個研究 outcome 會變好、怎麼知道？

**開發 gate（AGENTS「開發項不走 pq2」2026-10-04 那一句的執行面）：至少兩個 case 重複、第 3 問答得出來、第 7 問指得到某個迴路的量，才以五欄 amendment 提給使用者、定案後進 ROADMAP。**
例外只有 L17 的當下修（十行內、不動 contract）。使用者直接指示的開發項寫「使用者指示」，不受 gate 限制。

---

## 5. 漏網稽核（R3）的母體——T0 定，之後只 append 不刪

### 5.1 三個主題等權組的成分

- **光通訊**（現有）：`tc_35b0d5cd521656ea`（2026-09-30，pq2 [656]）15 檔——AXTI、IQE.L、4971.TWO、2455.TW、3081.TWO、4979.TWO、SIVE.ST、COHR、LITE、300308.SZ、AAOI、FN、POET、ENA.V、3363.TWO。
- **電力、散熱**：7.1 前瞻定義後 append 到檔尾「更正與追加」段（附 pq2 編號與日期），並記進 `cohort-changes.md`。

### 5.2 AI 基礎設施觀察名單（43 檔；今天列、看任何價格之前列）

> ⚠ 列的時候**沒有查任何價格、報酬或漲幅**；依據是 2026-06 之前的公開業務知識與 T0 的圖況。理由是「為什麼它屬於 AI 基礎設施的這一類」，**不是看好的理由**。
> 名單上的公司**不因在名單上而進任何研究佇列**——它只是 R3 的分母。ticker 不是 identity（INV-1）：R3 比對時名冊有的以 `co:*` 為準，沒有的以代號與公司名字串比對、記比對法。
> 光通訊組的成員不重複列；MU、000660.KS 同時在 history lane（照列，量「刻意不做 HBM」的代價）。

| # | 代號 | 公司 | 類別 | 為什麼在名單上 |
|---|---|---|---|---|
| 1 | CRDO | Credo Technology | 光通訊 | AI 叢集機櫃內短距互連的主動電纜（AEC）與 SerDes——「銅還是光」那條替代路徑上的主角（cpo 主題的反證關鍵字 copper interconnect） |
| 2 | 300502.SZ | 新易盛 Eoptolink | 光通訊 | 800G／1.6T 光收發模組的主要供應商之一；中國廠，直接受美國政策風險影響 |
| 3 | 300394.SZ | 天孚通信 TFC Optical | 光通訊 | 光器件與光引擎的上游元件供應商，CPO 光學元件的候選供應層 |
| 4 | 5803.T | 藤倉 Fujikura | 光通訊 | 資料中心高密度光纖、光纜與連接器——AI 資料中心佈線的量 |
| 5 | CIEN | Ciena | 光通訊 | 資料中心互連（DCI）的相干光學與光傳輸設備——跨機房連線的量 |
| 6 | 3450.TW | 聯鈞 Elite Advanced Laser | 光通訊 | 光通訊雷射元件封裝與矽光子後段；台股，月營收 |
| 7 | 6451.TW | 訊芯-KY ShunSin | 光通訊 | 光通訊模組與 CPO 的系統級封裝（SiP）代工；台股，月營收 |
| 8 | 267260.KS | HD 現代電機 HD Hyundai Electric | 電力 | 超高壓變壓器（含 765 kV）出口北美的主要廠之一（P1 的層） |
| 9 | 298040.KS | 曉星重工業 Hyosung Heavy Industries | 電力 | 超高壓變壓器，在美國有生產據點（P1） |
| 10 | 010120.KS | LS Electric | 電力 | 變壓器、開關設備與配電系統，接資料中心與北美電網（P1） |
| 11 | 1519.TW | 華城電機 Fortune Electric | 電力 | 變壓器出口北美電網的台廠；月營收讓中迴路變快（P1） |
| 12 | 1503.TW | 士林電機 Shihlin Electric | 電力 | 變壓器與配電設備的台廠；月營收（P1） |
| 13 | POWL | Powell Industries | 電力 | 中壓開關設備與電力控制模組，客戶含公用事業與資料中心（P1 周邊） |
| 14 | HPS-A.TO | Hammond Power Solutions | 電力 | 乾式與配電變壓器的中小型廠（P1 的邊緣型） |
| 15 | CLF | Cleveland-Cliffs | 電力 | 美國唯一的取向電工鋼（GOES）生產者——變壓器上游（P2） |
| 16 | GEV | GE Vernova | 電力 | 燃氣渦輪與電網設備（變壓器、開關）的共識大型股（P1 的共識對照） |
| 17 | ENR.DE | Siemens Energy | 電力 | 電網技術（變壓器、HVDC）與燃氣渦輪的共識大型股（P1 的共識對照） |
| 18 | BE | Bloom Energy | 電力 | 資料中心現地燃料電池發電——繞過電網排隊的那條路 |
| 19 | NVTS | Navitas Semiconductor | 電力 | GaN 功率元件，800VDC 生態系成員（P3 的層） |
| 20 | VRT | Vertiv | 散熱 | 資料中心電源與液冷（CDU）一體的大型股（C1 的共識對照） |
| 21 | 3017.TW | 奇鋐 AVC | 散熱 | 伺服器液冷冷板與散熱模組；月營收（C1） |
| 22 | 3324.TWO | 雙鴻 Auras | 散熱 | 液冷冷板、水冷模組與 CDU；月營收（C1） |
| 23 | 2308.TW | 台達電 Delta Electronics | 散熱 | 機櫃電源（800VDC power shelf 的具名廠之一）與液冷 CDU（C1、P3） |
| 24 | 8996.TW | 高力 Kaori | 散熱 | 熱交換器與 CDU；月營收（C1） |
| 25 | 3653.TW | 健策 Jentech | 散熱 | 均熱片、散熱上蓋與液冷零件；月營收（C1） |
| 26 | MOD | Modine | 散熱 | 資料中心冷卻（冷水機、CDU）（C1） |
| 27 | NVT | nVent | 散熱 | 液冷機櫃、CDU 與電氣機箱（C1） |
| 28 | 6515.TW | 穎崴 WinWay | 先進封裝／測試 | AI 晶片測試座與探針卡；月營收 |
| 29 | 6223.TWO | 旺矽 MPI | 先進封裝／測試 | 探針卡與測試設備；月營收 |
| 30 | 3131.TWO | 弘塑 Grand Process | 先進封裝／測試 | CoWoS 等先進封裝的濕製程設備；月營收 |
| 31 | 3583.TW | 辛耘 Scientech | 先進封裝／測試 | 先進封裝製程設備；月營收 |
| 32 | FORM | FormFactor | 先進封裝／測試 | 探針卡（含 HBM 測試） |
| 33 | CAMT | Camtek | 先進封裝／測試 | 先進封裝與 HBM 的檢測量測設備 |
| 34 | BESI.AS | BE Semiconductor | 先進封裝／測試 | 混合鍵合（hybrid bonding）設備 |
| 35 | 042700.KS | 韓美半導體 Hanmi Semiconductor | 先進封裝／測試 | HBM 堆疊用的熱壓鍵合（TC bonder）設備 |
| 36 | MU | Micron | 記憶體 | HBM／DRAM（「刻意不做 HBM」的代價要量它） |
| 37 | 000660.KS | SK hynix | 記憶體 | HBM 龍頭（同上） |
| 38 | 005930.KS | 三星電子 Samsung Electronics | 記憶體 | HBM／DRAM／NAND（同上） |
| 39 | SNDK | SanDisk | 記憶體 | NAND |
| 40 | 285A.T | Kioxia | 記憶體 | NAND |
| 41 | 2408.TW | 南亞科 Nanya Technology | 記憶體 | DRAM；月營收 |
| 42 | 2344.TW | 華邦電 Winbond | 記憶體 | 利基型 DRAM 與 NOR；月營收 |
| 43 | 3006.TW | 晶豪科 ESMT | 記憶體 | 利基型記憶體 IC 設計；月營收 |

### 5.3 R3 怎麼跑（機械）

1. **窗口**：第一次＝2026-07-01 → 2026-09-30（2026 Q3）；第二次（7.5）＝2026-10-01 → 檢查點量測日。之後每季一個窗口。
2. **每個窗口的母體**：窗口**開始之前**已在本節的名字。⚠ 7.1 才 append 的電力、散熱組成分**不進第一個窗口**（它們是在看得到 Q3 價格之後才選的）；從第二個窗口起進。
3. **排名**：窗口內報酬對光通訊主題等權組的超額（第一個窗口只有這一組存在；第二個窗口起照樣用它排名，以保持可比——
   同一個基準下排名等於絕對報酬排名；各鏈組的超額另欄並列）。前四分之一＝有完整價格的列數 × 1/4（無條件進位）。沒有價格的列計數「未量」。
4. **每一檔前四分之一**：lead registry 的 `first_seen`（最早一則）、來源、最後狀態、「為什麼沒進研究」（registry 查得到的照抄 park／no_go 理由；查不到寫「系統沒有接觸」）、
   是否在名冊、是否在圖；比對法照記（§0.1）。
5. 每一列標 discovery lookahead 與選樣偏差（§0.1）。

---

## 6. S1 抽樣規則（看任何裁決結果之前寫）

1. **框架**：帳號計分表（`library/private/app/state/account_scorecard.json`，as-of 2026-10-03）的 `stamps`，每個 `(source_id, symbol)` 取 `called_on` 最早的一則
   （同日取 `lead_id` 字典序最小）。T0 結果＝**40 則（全查，不再抽樣）**，逐列見附錄 B（sha256 `2f12fc28503c4127cb7c804de88c162d999f52bc40616a2f349441043bd894e0`）。
2. **主張**：那則 lead 原文（registry 的 `title`／原文欄）中，**關於該 symbol 的第一個可否證陳述**（依文字順序）。一則貼文點名多檔時，各檔各取關於自己的那一句；
   只列了代號、沒有陳述 → 類型＝無可否證主張。
3. **類型（封閉四選一）**：結構（供應關係、客戶、產能、合格、份額）／財務（營收、毛利、訂單金額、募資、指引）／價格（股價、目標價、估值倍數）／無可否證主張（只點名、情緒、問句）。
4. **裁決（封閉三選一）**：證實／推翻／未定。只對結構與財務型主張做一手裁決：一手＝發行人或客戶的 filing、官方新聞稿、IR 簡報、法說逐字稿、主管機關文件；
   二手只能帶路、不算證實（L11-3）。主張的核心（實體＋關係或數字，照主張自己的精度）被一手確認＝證實；被一手否定＝推翻；其餘＝未定。
   價格型只記點名到量測日的價格路徑，**不做一手裁決、不進 H6 主判讀**；無可否證主張只計數，**不寫進截圖假說層**（寫進去會變成一條永遠叫不醒的等待），在 `cases.md` S1 段記「不適用」。
5. **每則要記**：主張原文｜類型｜最早的一手證實或推翻文件與 `published_at`｜帳號發文日（`called_on`）｜系統接觸日（該 lead 的 `first_seen`）｜
   系統其他管道對同一家公司最早的 `first_seen`｜點名日 → 一手日的價格變化與對光通訊組超額（非光通訊的公司照列並標註）｜裁決。
6. **寫入**：結構與財務型主張以 `python -m engine_b.hypotheses add` 登記、`verify` 裁決（截圖假說層）；**未定的帶到期**：主張自己寫了日期 → 那個日期＋30 天；沒寫 → 2027-03-31。
   到期是重問不是丟（INV-2）。結果摘要寫進 `cases.md` S1 段——它是計分表 `hypothesis_hit_rate` 那一格的手動版，**不改計分表程式**。
7. **重疊**：附錄 B 的 40 則來自 30 個不同的 lead（一則貼文可點名多檔）；其中只有 1 個同時在 R2 樣本——`lead_cb2644d6e095834e6f0d38ff5348f862`（R2 的 X 層）。
   各自裁決各自的問題（S1 問主張、R2 問 park 決定），計數時不合併。

---

## 7. 回放的預先規則

### 7.1 共同

報告 `docs/reports/phase7/replay-<名稱>.md`；每一列標 §0.1 的三種偏差；產生用的程式碼貼在報告附錄。

### 7.2 R1 已定價回放（X1）

- **母體**：history lane 22 列（21 檔）∪ 光通訊主題等權組 15 檔，去重 30 檔，取有自家三年歷史的。
- **錨點**：history lane 的列＝它的入圖日（追蹤表 `anchor_date`）；只在主題等權組的 9 檔（4971.TWO、2455.TW、3081.TWO、4979.TWO、300308.SZ、FN、POET、ENA.V、3363.TWO）
  ＝組定義日 2026-09-30——**這 9 檔另列成一個子群**，不與 history 列合併計算判讀線。
- **時點**：錨點，與錨點前 30／90／180 天（四個時點）。
- **百分位**：三題同一個純函式（`alpha/three_questions.py` 與 `engine_c/three_question_inputs.py` 的取數規則、`shared/as_of.py` 的 as-of 規則），
  輸入以該時點的 as-of 篩過（每個時點用的財報 `filed` 日必須早於該時點）；算不出來 → 寫 failure log、該格「未量」，**不在本 Step 改產品程式**（plan §8）。
- **分組**：高＝百分位 ≥ 67；中＝33 ≤ 百分位 < 67；低＝< 33。
- **之後報酬**：時點 → R1 執行日（最後完整交易日）的絕對報酬與對光通訊組超額；非光通訊的列照列並標註。
- 呈現分組表（高／中／低 × 之後報酬），n 照印；**不算 p 值、不下「有效／無效」以外的結論**。H9 的判讀線見 §1。

### 7.3 R2 parked 回查（X2）的抽樣（本檔就固定）

- **母體**：T0 的 parked × `trace_status`＝`original_obtained`（353 則）**扣掉 P3 的五則**＝348 則。
- **分層**（`family()`，附錄 C 程式）：EDGAR 237／X 67／公司與新聞 feed 36／decompose 4／題材掃描 2／圖內部 2。
- **配額**：X 10、公司與新聞 feed 8、EDGAR 10；其餘三層全取（4＋2＋2）＝**36 則**（附錄 C 逐則列出）。不按比例——EDGAR 多半是例行申報，照比例抽會讓樣本幾乎只剩它；
  **合併任何比例時依層的母體大小加權**，各層也分開印。
- **層內順序**：`sha256("phase7-R2|" + lead_id)` 由小到大取前 k 則（確定、可重算、不看內容）。
- **每則**：之後有沒有一手證實（H2 的定義，文件與日期）、證實前價格走了多少、當初 park 的理由現在看站不站得住。
- 重疊（樣本 36 則裡有 3 則也出現在別的 case）：`lead_1446a653c191897aeddb8b84419e4456`（液冷，C1 的開題已知）、`lead_798000da36c2b1aa3070ddf51bdd6019`（BBU 電芯短缺，P3 的「相關」）、
  `lead_cb2644d6e095834e6f0d38ff5348f862`（S1 框架的一則）——各自回答各自的問題，計數不合併。

### 7.4 R4 輸家驗屍（X4）

見 §2 X4。入圖時的圖投影以 `project_assertions_as_of(<入圖日>)` 取；之後的一手文件以 `published_at` 晚於入圖日者為限。

---

## 8. T0 manifest 摘要與對照心跳

- **檔案**：`library/private/measurement/phase7/T0-2026-10-04.json`（private、不進 Git），sha256 `eb13ae65709a842209e19ae16bfb9d878a22776815dd2d76da4aa19b0afa924a`，
  生成於 **2026-10-04T07:09:14Z**（台北 15:09）。產生程式碼＝附錄 A（以既有 CLI、檔案讀取與 READ 模式 Cypher 組成，唯一寫入是 manifest 本身）。
  同日 07:06:17Z 先生成過一版（沒有逐邊證據等級），**在任何使用之前刪除重產**，以補上 H3／H4 需要的 T0 分組。
- **對照心跳** `heartbeat_2026-10-04.md`（台北 05:39 生成；sha256 `e651fc2c…`）：

| 項 | T0 manifest | 心跳 | 一致 |
|---|---|---|---|
| 事件監看總數／已收／已觸發 | 171／44／1 | 171／44／1 | ✅ |
| 語意條件 active＋fired（反證在盯） | 36＋1＝37 | 在盯 37 | ✅ |
| pq2 池中未結案 | 1（[586] manual） | 1 | ✅ |
| lead：triaged_go／triaged_no_go | 23／617 | pq1 可做 23／triaged_no_go 617 | ✅ |
| 結構讀圖現行（層／插槽） | 4（2／2） | 4（層 2／插槽 2） | ✅ |
| 候選序列（可開／缺 X／等回落／不要／已持有／非倍率／無敘事） | 0／0／1／0／2／1／72 | 同 | ✅ |
| 被點名未登記 | 111 | 111 | ✅ |
| thesis active／revised | 2／1 | 2／1 | ✅ |
| 帳號 tier | probation 1 | probation 1 | ✅ |
| 主題等權組 | `tc_35b0d5cd521656ea` | 同 | ✅ |
| 層節點（技術／產品／材料） | 186（單供應商 118） | 「凍結 186 個節點」 | ✅ |

- **「T0 之後的紀錄被算進 T0」的核對**（plan §1 L11-6 ④）：各 ledger 最後一筆都早於生成時刻——讀圖 2026-10-03T05:14:29Z、敘事 2026-10-03T05:22:54Z、
  watch 2026-10-03T05:22:52Z、lead `first_seen` 2026-10-03T21:30:20Z（registry 檔 mtime 21:31:45Z，早於心跳 21:39:15Z）、assertion `updated_at` 2026-10-03T15:38:27Z、
  候選序列最後一列 2026-10-03T21:38:12Z。心跳之後到 manifest 之間沒有任何 authority 被寫：lead registry、watch registry、pq2 池、截圖假說、
  `thesis/lifecycle.json`、名冊、讀圖與敘事 ledger、候選序列的檔案修改時間全部早於心跳（最晚的是候選序列 21:38:12Z）；心跳之後的兩個 commit
  （`ca987163`、`9a81cb78`）只動 docs。
- **凍結雜湊**（評估時與 T1 比對；任何不同都要歸因到 `cohort-changes.md` 的事件）：

| 項 | sha256 |
|---|---|
| `config/company_identity.json`（名冊 103 家；id 集合） | `e53e7235…aca71`（id 集合 `bc655349…cd8d6a`） |
| 被點名未登記代號集合（111） | `70414bac…92368f` |
| `library/leads/pending_leads.json`（1,212 則） | `126275b1…13270a` |
| lead id：applied 88／parked 484／triaged_go 23／triaged_no_go 617 | `c9272c1c…40a3`／`2f7099f1…0625`／`6ffda427…222e`／`0af988c7…6553` |
| `crons/harvest_config.json`／`config/signal_sources.json`／`config/themes.txt` | `1a2a4aa6…dda2`／`8f3c9263…1613`／`898c9813…2556` |
| EdgeAssertion id 集合（697；最大 `updated_at` 2026-10-03T15:38:27Z） | `c1c6e706…caedb3` |
| SourceDoc id 集合（220；有日期 207） | `777cb442…6607` |
| 逐邊證據等級（534 條：外部印證 236、自報·filing 107、供應商自報 105、媒體轉述 70、雙方聯合 11、待判定 5） | `cb37499d…50779` |
| 讀圖 ledger：InP／ELS／SuperNova／CW DFB | `e19a44b3…839f`／`edf2b719…78be`／`064f1b40…b0f`／`8167d9de…d852` |
| 敘事 ledger：AXTI／COHR／LITE／SIVE.ST（共 20 行） | `e1e7d26b…6f9d`／`7cdfe156…eda0`／`7477042f…a062`／`83aeb5f3…0908` |
| `thesis/lifecycle.json` | `a7a65fc8…579e` |
| memo：axt_inp_v1／coherent_cpo_v2／sivers_v4 | `7e7b8616…7c9`／`8ae04f78…2b59`／`fa593f0d…0c3` |
| `library/leads/hypotheses.json`（7 則） | `0f398f71…8fdb5` |
| `library/leads/event_watches.json`（171；逐列 id／kind／status／expires） | `c130b9e4…694c`（逐列 `7d255e8e…9c2f`） |
| `library/leads/todo_pool.json` | `8a7991ff…0a7` |
| 候選狀態序列（3 行） | `4285ad5f…c13` |
| S1 框架（40 則） | `2f12fc28…94e0` |
| 舊店 `backup_pre_v8…db`／`backup_pre_v9…db`／`decision_lab.db` | `e887b3d4…e350`／`af3dc690…9d39`／`e99d1c79…1810`（與 Phase 6 結案逐字相同） |
| `library/trades/trade_log.jsonl` | `861d2008…b8d5` |

（完整 64 位雜湊在 manifest 裡；本表截短只為可讀。）

---

## 附錄 A：T0 manifest 產生程式碼（逐字；scratchpad 會消失，評估要能重算）

用法：`.venv\Scripts\python.exe t0_manifest.py T0 heartbeat_2026-10-04.md`（T1 照用，換 label 與當天心跳檔名）。

```python
"""Phase 7 T0 manifest（唯讀；Step 7.0a）。

只讀本機 authority 檔、READ 模式 Cypher 與既有 CLI；唯一的寫入是 manifest 本身
（library/private/measurement/phase7/T<n>-<日期>.json，private、不進 Git）。
用法：python t0_manifest.py <label> <heartbeat 檔名>   例：python t0_manifest.py T0 heartbeat_2026-10-04.md
"""
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from alpha.narrative.contracts import parse_brief_record, select_brief  # noqa: E402
from alpha.structure_reading.contracts import parse_structure_reading_record, select_readings  # noqa: E402

LABEL, HEARTBEAT = sys.argv[1], sys.argv[2]
NOW = datetime.now(timezone.utc)
TODAY_TPE = (NOW + timedelta(hours=8)).date()


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_lines(items):
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()


def mtime(path):
    return datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cli_json(*args):
    out = subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


m = {"label": LABEL, "generated_at": NOW.isoformat(), "generated_on_taipei": TODAY_TPE.isoformat(),
     "heartbeat": {"file": HEARTBEAT, "sha256": sha_file(ROOT / "library/private/heartbeat" / HEARTBEAT),
                   "mtime": mtime(ROOT / "library/private/heartbeat" / HEARTBEAT)}}

# 1. 名冊與被點名未登記
reg = load("config/company_identity.json")
companies = reg.get("companies", reg)
ids = sorted(companies) if isinstance(companies, dict) else sorted(c["company_id"] for c in companies)
m["registry"] = {"sha256": sha_file("config/company_identity.json"), "count": len(ids), "ids_sha256": sha_lines(ids), "ids": ids}
onb = cli_json("-m", "engine_b.cli", "onboard-candidates")
onb_t = sorted(str(x["ticker"]) for x in onb)
m["onboard_candidates"] = {"count": len(onb_t), "tickers_sha256": sha_lines(onb_t), "tickers": onb_t}

# 2. lead registry
leads = load("library/leads/pending_leads.json")["leads"]
leads = list(leads.values()) if isinstance(leads, dict) else leads
by_status = {}
for x in leads:
    by_status.setdefault(x.get("status"), []).append(x["lead_id"])
parked = [x for x in leads if x.get("status") == "parked"]
m["leads"] = {"sha256": sha_file("library/leads/pending_leads.json"), "mtime": mtime("library/leads/pending_leads.json"),
              "count": len(leads), "max_first_seen": max(x.get("first_seen") or "" for x in leads),
              "by_status": {s: {"count": len(v), "ids_sha256": sha_lines(sorted(v))} for s, v in sorted(by_status.items())},
              "parked_by_trace_status": dict(Counter((x.get("refs") or {}).get("trace_status") for x in parked).most_common()),
              "triaged_go_ids": sorted(by_status.get("triaged_go", [])),
              "parked_original_obtained_ids": sorted(x["lead_id"] for x in parked
                                                     if (x.get("refs") or {}).get("trace_status") == "original_obtained")}

# 3. 監看來源與主題
m["sources_config"] = {p: sha_file(p) for p in ("crons/harvest_config.json", "config/signal_sources.json", "config/themes.txt")}
m["account_tiers"] = {s["source_id"]: {"tier": s["tier"], "tier_since": s.get("tier_since"), "status": s.get("status")}
                      for s in load("config/signal_sources.json")["sources"]}

# 4. 圖（READ 模式；不 dump 整張圖）
from dotenv import load_dotenv  # noqa: E402
from neo4j import READ_ACCESS, GraphDatabase  # noqa: E402

load_dotenv(ROOT / ".env")
drv = GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                           auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]))
with drv.session(default_access_mode=READ_ACCESS) as s:
    a = [r.data() for r in s.run("MATCH (a:EdgeAssertion) RETURN a.id AS id, a.updated_at AS u")]
    d = [r.data() for r in s.run("MATCH (d:SourceDoc) RETURN d.id AS id, d.published_at AS p")]
    edges = s.run("MATCH ()-[r]->() WHERE r.edge_key IS NOT NULL RETURN count(r) AS n").single()["n"]
    cos = s.run("MATCH (n) WHERE n.type = 'Company' RETURN count(n) AS n").single()["n"]
    single = [r.data() for r in s.run(
        "MATCH (t) WHERE t.type IN ['TechNode','Product','Material'] "
        "OPTIONAL MATCH (c)-[:SUPPLIES_TO|DEVELOPS]->(t) WHERE c.type='Company' "
        "WITH t, count(DISTINCT c) AS ns RETURN ns, count(*) AS n ORDER BY ns")]
    # 逐邊證據等級：與走圖／心跳同一條路（query.graph_walk：fetch_assertions＋fetch_all_quotes → _classify_edges）
    from query.bottleneck import fetch_assertions  # noqa: E402
    from query.sub_language import fetch_all_quotes  # noqa: E402
    rows_a, quotes_a = s.execute_read(lambda tx: (fetch_assertions(tx), fetch_all_quotes(tx)))
drv.close()
from query.structure import _classify_edges  # noqa: E402

canon = _classify_edges(rows_a, quotes_a)
canon = list(canon.values()) if isinstance(canon, dict) else list(canon)
edge_rows = sorted([[f"{e.src} {e.relation} {e.dst}", e.evidence, e.substitutability, e.sole_source,
                     e.qualification_status, e.documents,
                     min((str(p) for p in (e.source_docs or {}).values() if p), default=None)] for e in canon])
m["graph"] = {"assertions": {"count": len(a), "ids_sha256": sha_lines(sorted(x["id"] for x in a)),
                             "max_updated_at": max(x["u"] or "" for x in a)},
              "source_docs": {"count": len(d), "dated": sum(1 for x in d if x["p"]),
                              "ids_sha256": sha_lines(sorted(x["id"] for x in d))},
              "canonical_edges": edges, "company_nodes": cos,
              "supplier_count_distribution": {str(r["ns"]): r["n"] for r in single},
              # 欄位：[邊, 證據等級, substitutability, sole_source, qualification_status, 文件數, 最早 published_at]
              "classified_edges": {"count": len(edge_rows),
                                   "by_evidence": dict(Counter(r[1] for r in edge_rows).most_common()),
                                   "rows_sha256": sha_lines([json.dumps(r, ensure_ascii=False) for r in edge_rows]),
                                   "rows": edge_rows}}

# 5. 讀圖與敘事 ledger
rd = {}
for p in sorted((ROOT / "library/private/alpha/structure_readings").glob("*.jsonl")):
    recs = [parse_structure_reading_record(json.loads(line)) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    cur = select_readings(recs, today=TODAY_TPE)
    rd[p.name] = {"sha256": sha_file(p), "lines": len(recs), "last_created_at": max(r.created_at for r in recs).isoformat(),
                  "current": {u: {"id": r.reading_id, "kind": r.kind, "created_at": r.created_at.isoformat(),
                                  "disproof": len(r.disproof)} for u, r in cur.items()}}
m["structure_readings"] = rd
br = {}
for p in sorted((ROOT / "library/private/alpha/briefs").glob("*.jsonl")):
    recs = [parse_brief_record(json.loads(line)) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    cur = select_brief(recs, as_of=None, today=TODAY_TPE)
    v2 = sorted((r for r in recs if r.record_version.endswith("/v2")), key=lambda r: (r.created_at, r.brief_id))
    br[p.name] = {"sha256": sha_file(p), "lines": len(recs), "last_created_at": max(r.created_at for r in recs).isoformat(),
                  "brief_ids": [r.brief_id for r in recs],
                  "first_v2": v2[0].brief_id if v2 else None,
                  "current": {"id": cur.brief_id, "created_at": cur.created_at.isoformat(),
                              "candidate_state": cur.candidate_state.state if cur.candidate_state else None,
                              "watch_id": cur.candidate_state.watch_id if cur.candidate_state else None,
                              "rides": [[x.node, x.unit] for x in cur.rides], "disproof": len(cur.disproof)} if cur else None}
m["briefs"] = br

# 6. thesis
m["thesis"] = {"lifecycle_sha256": sha_file("thesis/lifecycle.json"),
               "entries": {k: {kk: v.get(kk) for kk in ("status", "memo", "last_checked", "next_check", "check_interval_days")}
                           for k, v in load("thesis/lifecycle.json").items()},
               "memos": {p.name: sha_file(p) for p in sorted((ROOT / "thesis").glob("*_memo.md"))}}

# 7. 截圖假說、watch、pq2
hyp = load("library/leads/hypotheses.json")
hyp_items = hyp.get("hypotheses", hyp) if isinstance(hyp, dict) else hyp
hyp_items = list(hyp_items.values()) if isinstance(hyp_items, dict) else hyp_items
m["hypotheses"] = {"sha256": sha_file("library/leads/hypotheses.json"),
                   "items": sorted([[h.get("hypothesis_id") or h.get("id"), h.get("status"), h.get("expires")] for h in hyp_items],
                                   key=lambda r: str(r[0]))}
ew = load("library/leads/event_watches.json")["watches"]
ew = list(ew.values()) if isinstance(ew, dict) else ew
rows = sorted([[w.get("watch_id"), w.get("kind"), w.get("status"), w.get("expires")] for w in ew], key=lambda r: str(r[0]))
m["watches"] = {"sha256": sha_file("library/leads/event_watches.json"), "count": len(rows),
                "rows_sha256": sha_lines([json.dumps(r, ensure_ascii=False) for r in rows]),
                "by_kind_status": {f"{k}/{s}": n for (k, s), n in sorted(Counter((r[1], r[2]) for r in rows).items())},
                "max_created_at": max(w.get("created_at") or "" for w in ew), "rows": rows}
todo = load("library/leads/todo_pool.json")
items = todo.get("items") or todo
items = list(items.values()) if isinstance(items, dict) else items
m["pq2_pool"] = {"sha256": sha_file("library/leads/todo_pool.json"), "count": len(items), "next_n": todo.get("next_n"),
                 "open": sorted([i.get("n"), i.get("type")] for i in items if not i.get("resolved_at"))}

# 8. 候選狀態序列、主題等權組、追蹤表名單
series = (ROOT / "library/private/measurement/candidate_state_series.jsonl").read_text(encoding="utf-8").splitlines()
m["candidate_state_series"] = {"sha256": sha_file("library/private/measurement/candidate_state_series.jsonl"),
                               "lines": len(series), "last": json.loads(series[-1])}
m["theme_cohorts"] = cli_json("-m", "alpha", "theme-cohort", "--format", "json")
pos = load("library/private/app/state/positions.json")
m["tracking_lanes"] = {"history": [[r.get("ticker"), r.get("company_id"), r.get("anchor_date")] for r in pos.get("rows") or []],
                       "paper": [[r.get("ticker"), r.get("company_id"), r.get("anchor_date"), r.get("brief_id")]
                                 for r in pos["lanes"]["paper"].get("rows") or []],
                       "positions_generated_at": pos.get("generated_at")}

# 9. S1 抽樣框架（帳號計分表 stamps：每個 symbol 最早一則；只取框架欄位，不讀報酬）
sc = load("library/private/app/state/account_scorecard.json")
frame = {}
for acct in sc["accounts"]:
    for st in acct["stamps"]:
        key = (acct["source_id"], st["symbol"])
        cand = (st["called_on"], st["lead_id"])
        if key not in frame or cand < frame[key][:2]:
            frame[key] = (st["called_on"], st["lead_id"], st.get("company_id"))
s1 = sorted([[src, sym, v[0], v[1], v[2]] for (src, sym), v in frame.items()], key=lambda r: (r[2], r[1]))
m["s1_frame"] = {"scorecard_as_of": sc.get("as_of"), "count": len(s1),
                 "rows_sha256": sha_lines([json.dumps(r, ensure_ascii=False) for r in s1]), "rows": s1}

# 10. 檢查點另核對的凍結檔
m["frozen_files"] = {p: sha_file(p) for p in (
    "library/private/decision_lab/backup_pre_v8_20260818T021452.db",
    "library/private/decision_lab/backup_pre_v9_20260902T032020Z.db",
    "library/private/decision_lab/decision_lab.db",
    "library/trades/trade_log.jsonl")}

out = ROOT / "library/private/measurement/phase7" / f"{LABEL}-{TODAY_TPE.isoformat()}.json"
out.parent.mkdir(parents=True, exist_ok=True)
if out.exists():
    sys.exit(f"已存在，不覆寫：{out}")
out.write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
print(out, sha_file(out))
```

## 附錄 B：S1 框架（40 則；`[source_id, symbol, called_on, lead_id, company_id]`，依 `called_on`、symbol 排序）

```
aleabitoreddit  AAOI       2026-06-29  lead_476bd1f07c60e2995ad96640688707ee  co:applied_optoelectronics
aleabitoreddit  MU         2026-06-29  lead_476bd1f07c60e2995ad96640688707ee  co:micron_technology
aleabitoreddit  SNDK       2026-06-29  lead_476bd1f07c60e2995ad96640688707ee  co:sandisk
aleabitoreddit  AXTI       2026-06-30  lead_b75a2feb576f619129330908245b248a  co:axt
aleabitoreddit  CCXI       2026-06-30  lead_1d29da0283f3c7f84f5ee2cfdb7ee8d0  co:churchill_capital_xi
aleabitoreddit  GFS        2026-06-30  lead_2cb82f4c0c7b93fbf18be123045d671e  co:globalfoundries
aleabitoreddit  GOOGL      2026-06-30  lead_401029a4e651dfda8b38277e5ff97db5  co:google
aleabitoreddit  JBL        2026-06-30  lead_b75a2feb576f619129330908245b248a  co:jabil
aleabitoreddit  META       2026-06-30  lead_401029a4e651dfda8b38277e5ff97db5  co:meta
aleabitoreddit  NBIS       2026-06-30  lead_b556950618d8a8f969895cc45a2a506a  co:nebius
aleabitoreddit  NVDA       2026-06-30  lead_1d29da0283f3c7f84f5ee2cfdb7ee8d0  co:nvidia
aleabitoreddit  SIVE.ST    2026-06-30  lead_2cb82f4c0c7b93fbf18be123045d671e  co:sivers_semiconductors
aleabitoreddit  TSLA       2026-06-30  lead_c95925a7449580e24cce7512ebad08b4  co:tesla
aleabitoreddit  XFAB.PA    2026-06-30  lead_b75a2feb576f619129330908245b248a  co:x_fab
aleabitoreddit  AEVA       2026-07-01  lead_6ac3699094b2106a3af12848febb87f3  co:aeva
aleabitoreddit  CRWV       2026-07-01  lead_b72df36ba871db77a524b7178d3b4944  co:coreweave
aleabitoreddit  TSM        2026-07-01  lead_2fb91876b881e2393f73b030a188ffa5  co:tsmc
aleabitoreddit  XPEV       2026-07-01  lead_56c00023183b77584494c96d3ff61ed2  co:xpeng
aleabitoreddit  AEHR       2026-07-02  lead_f7882130d1f1e8a992a0de76cf4b19fd  co:aehr_test_systems
aleabitoreddit  AMAT       2026-07-02  lead_cc5e07e8ced6ce59f302397d8583de9c  co:applied_materials
aleabitoreddit  AMD        2026-07-02  lead_f3cf03ef3623277171d343ff96e81a95  co:amd
aleabitoreddit  COHR       2026-07-02  lead_8838f7b84c0dd94f7e0b8a037085e35f  co:coherent
aleabitoreddit  GLW        2026-07-02  lead_f7882130d1f1e8a992a0de76cf4b19fd  co:corning
aleabitoreddit  INTC       2026-07-02  lead_9c307b5e44b4cd9b129d36163d450b50  co:intel
aleabitoreddit  IREN       2026-07-02  lead_6d1adf0b8604fa090d3511191a19f7e4  co:iren
aleabitoreddit  LITE       2026-07-02  lead_f3cf03ef3623277171d343ff96e81a95  co:lumentum
aleabitoreddit  MRVL       2026-07-02  lead_cc5e07e8ced6ce59f302397d8583de9c  co:marvell_technology
aleabitoreddit  POET       2026-07-02  lead_6d6393468a44e9d39e518ee6cb700d20  co:poet_technologies
aleabitoreddit  MSFT       2026-07-04  lead_e7d012889c91027f839151169ba60e6d  co:microsoft
aleabitoreddit  FN         2026-07-06  lead_3a46a020555dc48189780ff7686f778b  co:fabrinet
aleabitoreddit  IQE.L      2026-07-06  lead_8088f665e358a7744d9b6bc1646bccbf  co:iqe
aleabitoreddit  AAPL       2026-07-07  lead_586d4451effd3b1206f2076b29aab69a  co:apple
aleabitoreddit  ORCL       2026-07-07  lead_d95d26c1e9be71f3422d0b4d10ee6ad8  co:oracle
aleabitoreddit  AVGO       2026-07-13  lead_0c4d787d641296115df7d94fdddb0c3e  co:broadcom
aleabitoreddit  MTSI       2026-07-13  lead_62327c9dc121465c4438192595499d27  co:macom
aleabitoreddit  TSEM       2026-07-13  lead_b1e793c560334131dfe7c1619715784d  co:tower_semiconductor
aleabitoreddit  000660.KS  2026-07-17  lead_cb2644d6e095834e6f0d38ff5348f862  co:sk_hynix
aleabitoreddit  SOI.PA     2026-07-17  lead_f8b105284a2de000d25fbd902912ae77  co:soitec
aleabitoreddit  SHA0.DE    2026-09-01  lead_26bd4214b4b0434765071f14a7a955e4  co:schaeffler
aleabitoreddit  LYC.AX     2026-09-04  lead_fc1f6fddc45c93d06a7ee0e5a3e723ad  co:lynas
```

## 附錄 C：R2 抽樣程式碼與樣本（36 則）

```python
"""Phase 7 R2 parked 回查的抽樣（預先登記；只用 lead id 與 source，不讀內容與結果）。

母體＝T0 manifest 的 parked × trace_status=original_obtained（353），排除 P3 的五則 800VDC decompose。
分層＝下面 family()；X／公司新聞 feed／EDGAR 三層照配額取，其餘層全取；
層內順序＝sha256("phase7-R2|" + lead_id) 由小到大（確定、可重算、不看內容）。
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
T0 = json.loads((ROOT / "library/private/measurement/phase7/T0-2026-10-04.json").read_text(encoding="utf-8"))
POP = set(T0["leads"]["parked_original_obtained_ids"])
P3 = {"lead_18be6b7764b40d7cb853925a0a4836eb", "lead_3e0ba028986066e33b30d7c97c0a33b9",
      "lead_4c2881be9b2f66a3b2b54291e26985aa", "lead_a4c2e14392aec9ce92ee74d1f1b6e81d",
      "lead_fa672a299978b3f3ec2b0cf8ae1d4130"}
QUOTA = {"X": 10, "公司／新聞 feed": 8, "EDGAR": 10}
FEED_PREFIXES = ("mfn:", "sivers:", "yahoo:", "mops:", "official", "prnewswire:", "globenewswire:",
                 "businesswire:", "reuters")


def family(source: str) -> str:
    s = (source or "").lower()
    if s.startswith("x:") or "aleabitoreddit" in s:
        return "X"
    if s.startswith(("edgar:", "sec:")):
        return "EDGAR"
    if "decompose" in s:
        return "decompose"
    if "weekly" in s or "theme_scan" in s:
        return "題材掃描"
    if "graph_walk" in s or "coverage-gap" in s or "gap" in s or "loop" in s:
        return "圖內部"
    if s.startswith(FEED_PREFIXES) or ":" in s:
        return "公司／新聞 feed"
    return "互動點名／其他"


leads = json.loads((ROOT / "library/leads/pending_leads.json").read_text(encoding="utf-8"))["leads"]
leads = list(leads.values()) if isinstance(leads, dict) else leads
src = {x["lead_id"]: x.get("source") for x in leads}
strata: dict[str, list[str]] = {}
for lid in sorted(POP - P3):
    strata.setdefault(family(src[lid]), []).append(lid)
key = lambda lid: hashlib.sha256(f"phase7-R2|{lid}".encode()).hexdigest()  # noqa: E731
sample = {f: sorted(ids, key=key)[:QUOTA.get(f, len(ids))] for f, ids in sorted(strata.items())}
print(json.dumps({"population": {f: len(v) for f, v in strata.items()}, "sample_sizes": {f: len(v) for f, v in sample.items()},
                  "total": sum(len(v) for v in sample.values()), "sample": sample}, ensure_ascii=False, indent=1))
```

T0 執行結果（母體 EDGAR 237／X 67／公司與新聞 feed 36／decompose 4／題材掃描 2／圖內部 2；樣本 36）：

| 層 | 樣本（層內順序） |
|---|---|
| EDGAR（10／237） | `lead_8449bc608af931881de4f3306385d5ab`、`lead_6648e5f5705f5070f8c3dba5cec65f10`、`lead_51262d0814ea1b61ea98ccdc976793d8`、`lead_f1b02f22ff8bbd9fe54d886a7da65f9e`、`lead_e590eca752d976cef58be766a5b17d62`、`lead_7f15a5aa15464587e916e17c059086ee`、`lead_29afe4c0a51033dc69959a4c05534d55`、`lead_91a73c290d7257f4102c49d31d1b3c19`、`lead_06a8ab213ca272d827b9843386179945`、`lead_79e1eada7e7dadf7d71a2ee36d68315d` |
| X（10／67） | `lead_1b7d39ebcb3b8ede4b381cb38eedc6c2`、`lead_6e6000e197e77903a63354c48ebe2d2c`、`lead_043e94a0e70f703a76115cf09f96b438`、`lead_ba473b6b6bca2ceba19958fee04b0fa2`、`lead_3df060cf842783e4709ae6cd86b1be74`、`lead_2c0614883bf6ec94c3032ccda5c7ff70`、`lead_798000da36c2b1aa3070ddf51bdd6019`、`lead_5b6c52c2bed7adba87c1d45940ca44c6`、`lead_cb2644d6e095834e6f0d38ff5348f862`、`lead_7bbf1d134806b235e07a8de3130ac5db` |
| 公司與新聞 feed（8／36） | `lead_0e0197f7c6c42939f7b285e7485f8aa7`、`lead_8610653924d5d66801d50a14f07414ce`、`lead_a6a00003eb1ad0fefdd1ed3e77d93233`、`lead_a7ab5e10e98df1235415c697e5c1ece3`、`lead_27625bd16af9f120f0ea459c102ad987`、`lead_2e5d8c3fee25947f81b5d4ea4aa373e6`、`lead_697707f81d2c1aaa1467741b18f19fe8`、`lead_299f984635431d6b8702ba9406cbf8e8` |
| decompose（4／4） | `lead_55bd36e6cab9fdd81f0668215af10431`、`lead_95b0d3624dfaf66bc5022912310661c4`、`lead_1446a653c191897aeddb8b84419e4456`、`lead_bc427a52cef3692d38154ba5ff5ea9b3` |
| 圖內部（2／2） | `lead_905b49498f1e740b063317c65b214410`、`lead_5087a6570af0c525743b6f2d96e17d9a` |
| 題材掃描（2／2） | `lead_fcc4ddc4ac5a29b00466bd580c5d4e6a`、`lead_2cdf807d54bf8f6febf46cb966914c41` |

---

## 更正與追加（append-only；本檔 commit 之後只能在這一行之後追加）

### 2026-10-05｜R3 母體追加：IC 載板類 6 檔（pq2 [711]，使用者 2026-10-05 go）

- **改什麼**：§5.2 觀察名單之後追加一類「IC 載板」，從**第二個窗口（2026-10-01 →）**起進 R3 分母；第一個窗口（2026 Q3）不追溯（§5.3 第 2 點：看得到價格之後才選的不進已過的窗口）。

| # | 代號 | 公司 | 類別 | 為什麼在名單上 |
|---|---|---|---|---|
| 44 | ATS.VI | AT&S | IC 載板 | AI 伺服器／加速器用的高階 IC 載板；Kulim 擴產由 AMD 與 Marvell 的長期承諾出資（圖上 [681]） |
| 45 | 009150.KS | 三星電機 Samsung Electro-Mechanics | IC 載板 | AI 伺服器用 FCBGA；世宗與越南擴產含客戶出資（圖上 [681]） |
| 46 | 4062.T | Ibiden | IC 載板 | 高階 FCBGA 載板的主要廠之一（不在名冊；比對以代號與公司名字串） |
| 47 | 3037.TW | 欣興 Unimicron | IC 載板 | ABF 載板的主要廠之一；月營收（不在名冊） |
| 48 | 3189.TW | 景碩 Kinsus | IC 載板 | ABF／BT 載板；月營收（不在名冊） |
| 49 | 8046.TW | 南電 Nan Ya PCB | IC 載板 | ABF 載板；月營收（不在名冊） |

- **為什麼**：research-drain 段 5（2026-10-05）發現 AT&S、三星電機 2026 年各漲約 20 倍（Engine C 日線），而 43 檔觀察名單有「先進封裝／測試」類、沒有 IC 載板類——
  第一窗結構上看不到這一組贏家（cases X3 2026-10-05）。追加的理由是「這一類本來就屬於 AI 基礎設施」，**不是看好的理由**；名單上的公司不因此進任何研究佇列。
- **影響哪些量測**：R3 第二窗起分母 58 → 64；排名與前四分之一照 §5.3 的機械規則。記進 `cohort-changes.md` 同日一筆。

### 2026-10-05｜新假說 H11：月營收「量的拐點」作為 lead 的找法——預先登記，先於任何計算（使用者 2026-10-05 R2 go）

- **為什麼加**：個股頁 schema 的獨立審查（brainstorm `2026-10-05-stock-page-schema.md` §12，F22）指出規律 2「轉折來自量的第一個硬證據」在庫內無法否證——
  有月營收的台股只有 12 檔、全是 AI 贏家。使用者要把它當未來 lead 放量時的找法，所以先用全市場的基準率測，再決定能不能用。**它不是買點**（F17：會假起步）。
- **一句話**：台股某檔的月營收「連續三個月年增都 > 40%」第一次成立之後，它接下來 12 個月相對全市場的超額報酬，高於沒有成立的月份。
- **母體**：MOPS 歷史月營收（`fetchers/mops_open_data.py::fetch_monthly_revenue_month`，上市＋上櫃、國內＋國外公司兩份頁），資料月 2023-01 到 2026-08；
  每一個（代號 × 月）一列。去年同月營收 < 1,000 萬元（10,000 千元）的月份不算成立也不算不成立（基期太小），計數照印。
- **事件**：月 m 成立＝m−2、m−1、m 三個月年增都 > 40%（用頁上的「去年同月增減(%)」，缺就用 當月 ÷ 去年當月 − 1）。**事件月＝成立、而且 m−1 不成立**（一段連續成立只算第一個月）。
  看得到的日子＝法定期限（m+1 月 10 日）。**進場價＝m+1 月最後一個交易日收盤**；出場＝再 12 個月的月底收盤。事件月範圍：2024-01 到 2025-09（讓 12 個月走得完）。
- **對照組**：同一範圍裡「不成立」的（代號 × 月），同一套進出場規則。
- **價格**：yfinance 月線、還原權息（`auto_adjust=True`）；代號照 `ticker_for`（上市 `.TW`、上櫃 `.TWO`）。抓不到價格的列剔除並計數。
- **量法**：超額＝個股 12 個月報酬 − 同一進場月全體樣本 12 個月報酬的中位數。兩組各算超額中位數、平均、「12 個月內曾達 2 倍」的比例、「6 個月內先跌 30% 以上」的比例（假起步）。
- **削弱（殺死條件）**：**事件組 n ≥ 30，而且事件組的超額中位數 ≤ 對照組的超額中位數** → H11 削弱（這條找法作廢，不進 lead triage）。
- **支持**：事件組 n ≥ 30，超額中位數高於對照組，**而且**「曾達 2 倍」比例也高於對照組。
- **不足**：事件組 n < 30。
- **另印（不進判讀線）**：門檻改 30%、50% 的敏感度；依進場年分開（2024、2025）；三檔錨點自己的事件月落在哪。
- **偏差標註**：①沒有 discovery lookahead（純機械規則、全市場）②選樣：用各月歷史頁當時上市櫃的公司，已下市的也在（價格抓不到的照計數）③價格是 yfinance 還原價，不是 Engine C 的取價層（全市場只在這裡抓）
  ④這一段期間是 AI 多頭（2024–2026），結論只適用這個環境。**只測量的拐點，不測「報告後」**——全市場沒有覆蓋資料，F16 的報告那一半仍未量。
- **量在哪一層**：追蹤表（基準率回放）；計算腳本與結果在下一筆追加（結果出來之前，本條不改）。
### 2026-10-05｜H11 結果：**削弱**（照上一筆預先登記的殺死條件；登記 commit 2e18b832 早於計算）

- **判讀**：事件組 n＝537，12 個月超額中位數 **−1.2%**；對照組 n＝36,127，**0.0%** → 事件組 ≤ 對照組 → H11 削弱：「連三個月年增 > 40%」單獨當 lead 的找法，作廢，不進 lead triage。
- **另印（不進判讀線）**：曾達 2 倍——事件組 15.1%、對照組 9.3%；6 個月內先跌 30% 以上——事件組 14.0%、對照組 7.2%；超額平均——事件組 +26.0%、對照組 +16.7%。
  門檻 30%（n＝740）、50%（n＝395）與分年（2024、2025）方向都一樣：中位數不贏、兩邊尾巴都更肥。三檔錨點的事件月：聯亞 2024-09（12 個月 +32%）與 2025-04（+789%）、高力 2025-04（+361%）、華星光 2025-03（+301%）。
- **讀法**：量的拐點挑出的是「波動大」的股票，不是「中位數會贏」的股票。「右尾比較肥」是看到結果之後才出現的說法——**不能用同一份資料改判**；要測，得另外預先登記新假說、用新的期間（例：2025-10 之後的事件月，12 個月後才看得到結果）。
- **計數**：代號 1,980、都有價格；判斷列 36,664；基期太小（去年同月 < 1,000 萬元）不判的列 4,485；月營收抓取失敗 0。
- **腳本與結果**：逐字收在同目錄 [`replay-h11-volume-inflection.md`](replay-h11-volume-inflection.md)（scratchpad 會消失，評估要能重算）。

### 2026-10-06｜新假說 H12：量的拐點＋毛利率同時往上，比「只有量」更常翻倍、而且不更常先崩——預先登記，先於任何計算（使用者 2026-10-06「H11 登記」）

- **為什麼加**：H11 削弱，但兩邊尾巴都更肥（曾達 2 倍 15% vs 9%、先跌 30% 14% vs 7%）；「右尾」是看完結果才有的說法，不能用同一份資料改判（上一筆的讀法）。
  power-law 目標（小賠多檔、一檔補回）要的是**能把翻倍的和先崩的分開的條件**。候選條件取自個股頁 schema「量 → 錢 → 價」的第二步：量變多**而且**毛利率往上，
  才像「一層薄的供應商被灌量」；只有量、毛利沒動，可能只是景氣循環或接單代工（brainstorm `2026-10-05-stock-page-schema.md` §8 回饋 #37）。**它不是買點**（F17）。
- **一句話**：在 H11 定義的事件裡，「事件當時已知的最近一季，單季毛利率比去年同一季高 ≥ 3 個百分點」的那一組（A），12 個月內曾達 2 倍的比例高於其餘事件（B），
  而且 6 個月內先跌 30% 以上的比例不高於 B。
- **期間（新的、沒看過）**：事件月 2015-01 到 2022-12。H11 的事件月是 2024-01 到 2025-09；H12 最後一個事件的出場是 2024-01 月底，早於 H11 第一個進場（2024-02 月底）——
  兩段的結果窗不重疊。登記前只做過一件事：探測損益表彙總端點（2013Q3、2019Q1、2019Q2 的表頭與台積電、聯發科兩列，確認是累計數）；**沒有看任何毛利率分布、事件數或報酬**。
- **事件（照 H11 逐字）**：月 m 成立＝m−2、m−1、m 三個月年增都 > 40%（頁上的「去年同月增減(%)」，缺就用 當月 ÷ 去年當月 − 1）；**事件月＝成立而且 m−1 不成立**；
  去年同月營收 < 1,000 萬元（10,000 千元）的月份不判（計數照印）。進場＝m+1 月最後一個交易日收盤；出場＝再 12 個月的月底收盤。同一段連續成立的後續月份不進任何一組。
  月營收來源同 H11（`fetchers/mops_open_data.py::fetch_monthly_revenue_month`，上市＋上櫃、國內＋國外兩份頁），資料月 2014-10 到 2022-12；
  **以公司代號串起來**（期間內由上櫃轉上市的公司前後接成一條，H11 以帶後綴的代號串，兩年內幾乎沒有轉板，八年會有）。
- **毛利率（新增的條件）**：MOPS 綜合損益表彙總 `https://mopsov.twse.com.tw/mops/web/ajax_t163sb04`（POST，一季一份，上市與上櫃各一）。
  - 只取同時有「營業收入」與「營業毛利（毛損）」欄的一般業版型，**以欄名對齊、不按位置**（2013 年 28 欄、2019 年 30 欄）；金融、保險、證券、異業版型 → 「沒有毛利率」。
  - 彙總表是**累計數**（2019Q2 那列＝上半年）：單季＝本季累計 − 上一季累計（Q1 不減）；缺任一季累計 → 「沒有毛利率」。單季毛利率＝營業毛利（毛損）÷ 營業收入。
  - **看得到的日子＝法定期限**（`engine_c.tw_share_capital.statutory_deadline`：Q1 5/15、Q2 8/14、Q3 11/14、年報次年 3/31）；**期限嚴格早於進場日**的最近一季才算「事件當時已知」
    （同一天不算，免得收盤後才公告）。
  - **毛利率變化**＝該季單季毛利率 − 去年同一季單季毛利率（百分點）；兩季的單季營收都要 ≥ 3,000 萬元（30,000 千元），否則「毛利率基期太小」不分組。
- **分組**：A＝事件且毛利率變化 ≥ +3 個百分點；B＝事件且毛利率變化 < +3（含下降）。沒有毛利率或基期太小的事件不分組，計數照印。
- **價格**：yfinance 月線、還原權息（`auto_adjust=True`），2014-12 到 2024-02；代號先試上市（`.TW`）、抓不到或缺進場月再試上櫃（`.TWO`）。抓不到價格的列剔除並計數。
- **量法（同 H11）**：超額＝個股 12 個月報酬 − 同一進場月全體樣本（事件＋非事件）12 個月報酬的中位數；各組算「12 個月內曾達 2 倍」比例（月底收盤 ≥ 2 × 進場價）、
  「6 個月內先跌 30% 以上」比例（月底收盤 ≤ 0.7 × 進場價）、超額中位數與平均。
- **支持（四條全部成立）**：① A、B 各 ≥ 30 ② 曾達 2 倍：A > B ③ 先跌 30% 以上：A ≤ B ④ 前後兩段（事件月 2015–2018、2019–2022）各自的 ② 方向都一樣（A > B；
  某段 A 或 B 不到 15 → ④ 不成立）。
- **削弱（殺死條件）**：① 成立，而且 ② 或 ③ 不成立 →「毛利同時往上」分不開翻倍與先崩，不進 lead triage 的問句。
- **不足**：① 不成立；或 ①②③ 成立但 ④ 不成立（方向不穩）。
- **另印（不進判讀線）**：門檻改 0、+5 個百分點的敏感度；H11 的定義在新期間的重現（事件 vs 非事件的超額中位數、曾達 2 倍、先跌 30%）；A、B 的超額中位數與平均；
  各年的 n；沒有毛利率、基期太小、抓不到價格的計數。
- **偏差標註**：①已下市與改板的公司 yfinance 常抓不到，剔除並計數——存活者偏差，兩組都受影響、方向不一定相同 ②KY（外國）公司的季報期限照一般業算，可能提早幾天看到
  ③回補拿到的是 MOPS **現在**的版本——重編或逾期申報的季仍照原期限當可知（同 `tw_share_capital` 的已知限制）④「事件當時已知的最近一季」可能早於量的拐點
  （例：3 月成立的事件，已知的是前一年第四季）——這是「當時看得到什麼」的代價，不改 ⑤毛利率是合併報表全公司，不分押的那一塊（F18 的「看押的那一塊」全市場做不到）
  ⑥月底收盤算「曾達 2 倍／先跌 30%」，不看盤中 ⑦2015–2022 含 2020–2021 多頭與 2022 空頭，結論只適用這段環境。
- **量在哪一層**：追蹤表（基準率回放）；腳本與結果在下一筆追加（結果出來之前本條不改）。

### 2026-10-06｜H12 結果：**削弱**（照上一筆預先登記的判讀線；登記 commit 45e9453a 早於計算）

- **判讀**：① A（量＋毛利率 ≥ +3pp）n＝709、B n＝1,071，各 ≥ 30 ✓；② 12 個月內曾達 2 倍——A **9.0%** ≤ B **9.2%** ✗；
  ③ 6 個月內先跌 30% 以上——A **12.0%** > B **8.8%** ✗ → H12 削弱：「量的拐點＋毛利率同時往上」分不開翻倍與先崩，不進 lead triage 的問句。
- **另印（不進判讀線）**：前後兩段的②——2015–2018 A 7.2% vs B 7.3%、2019–2022 A 9.8% vs B 10.3%（④也不成立）。
  門檻 0：曾達 2 倍 A 9.9% vs B 7.9%、先跌 30% A 10.6% vs B 9.3%；門檻 +5pp：A 8.2% vs B 9.5%、先跌 12.6% vs 8.9%。超額中位數 A −8.7%、B −3.3%。
  **H11 定義在新期間的重現**：事件 n＝2,079，超額中位數 −4.4% vs 對照 n＝145,744 的 0.0%；曾達 2 倍 10.2% vs 8.1%、先跌 30% 9.9% vs 7.2%——
  方向與 2023–2025（H11）相同：中位數不贏、兩邊尾巴都更肥。
- **讀法**：毛利率往上越多，先崩越多；毛利率大升常是週期高點，不是「一層薄」的定價權（個股頁 brainstorm F36：聯亞 2021Q1 54% → 2021Q4 24%、2023Q3 −20%；
  AXT 2022Q3 42.0% → 2023Q3 10.7%）。要從量的拐點裡挑出右尾，**財務數字的條件到這裡為止**——量（H11）與量＋毛利（H12）都在全市場測過、都分不開；
  剩下的候選是圖的條件（一層薄、需求錨），只能前向測（圖是 2026 年才建的，回頭測等於先知道答案）。
- **計數**：代號 1,870、有價格 1,862；判斷列 147,823；事件 2,079（抓不到價剔除 50 列）、對照 145,744（剔除 1,603 列）；毛利率：有 1,780、
  基期太小 23、沒有 276；月營收基期太小不判 7,862 列；月營收與損益表抓取失敗 0。
  ⚠ 月線第一輪被 yfinance 限流、600 個代號兩個後綴都沒價——補抓分清楚「限流」與「Yahoo 沒有」後找回 592 個代號×後綴、只剩 8 個代號真的沒有資料。
  沒補抓就照用，會把近三分之一的公司當成「沒有價格」剔除（L13：失敗與「真的沒有」同形）。
- **可知日抽查**：2,079 個事件裡，用到的那一季法定期限不早於進場月月底的 0 個；一筆手算與腳本一致（`h12_pit_check.py`）。
- **腳本與結果**：逐字收在同目錄 [`replay-h12-volume-margin.md`](replay-h12-volume-margin.md)（抓取、補抓、計算三支）。

### 2026-10-06｜新 case B1：AI 生醫的上游實驗量（使用者選題，pq2 [723]）——預先登記，先於本鏈任何研究產出

- **為什麼加**：使用者 2026-10-06 選 AI 生醫為新 field，起點是 qinbafrank 轉述 Freda Duan〈AI Drug Discovery Is Becoming a Bottleneck Trade〉
  （lead `lead_7cb87fe0d59de4b7cf175f5a47be602a`，tier 4、二手）。plan §0 第 2 項：新增 case 也是 append，開題日＝本段的 commit 日。

| 欄 | 內容 |
|---|---|
| 類型 | 使用者從 SNS 帶進來、**開題當下已被認為擁擠**的新鏈（使用者原話「好像已經開始擁擠了」；原文直接點名 TWST、GenScript、ILMN、TXG、實驗自動化廠、CRO） |
| 測 | H1、H5、H9；H6 只另印（使用者帶入的 SNS 主張的證實率；**不進 H6 判讀線**——判讀線只吃 S1 預先抽的 40 則） |
| 開題時已知 | 圖：`library/private/app/state/graph_walk.json` 的 3,066 個節點裡生醫相關 0 個（2026-10-06）；名冊 0 家生醫公司；lead registry 命中 `aibio` 主題 0 則（主題 2026-10-06 才加）；沒有主題等權組；系統對這條鏈沒有任何先前結論。原文的主張（二手、未追源）：TWST 預期 AI 藥物發現訂單 FY26、FY27 連兩年三位數成長；GenScript AIDD 業務 1H26 年增一倍，通路調查約 8,000 設計／日、年底往 16,000；Anthropic 設計 1,320 個 binder、Adaptyv 測出 354 個結合；猴價接近前高、CRO 產能緊 |
| 預期會暴露的 failure mode | ①開題來源點名的公司被當成答案（L8：點名不是瓶頸證據；「通路調查」是第三方二手）；②生醫的「層」賣的多半是服務與產能（設計／日、猴隻、CRO 床位），L4 的「節點 vs 時變觀測」與 INV-1 的身分（港股、A 股、未上市的 Adaptyv）會撞新形狀；③被點名的幾檔若已定價，研究火力被吸去寫「不要」 |
| 支持／削弱的判準 | **H1／H5**：拆層後讀圖若找到坐在薄層上、**不在開題原文點名清單裡**的邊緣公司，記一列（以第一次接觸日為錨的追高＝否 → 支持；＝是 → 削弱）。結論若是「點名的那幾家就是薄層、而且已定價」→ 記 H9 一列，不算 H1 的正反；結論若是「這條鏈沒有薄層」（讀圖或 Abstention）→ 照實記 |
| 2×2 | 錨＝本鏈第一份 v2 敘事日；欄＝對 AI 生醫主題等權組超額（等權組在第一份敘事之前定義，決定紀錄 §6.7） |
| 裁決點 | TWST 下一次財報（FY26 Q4；日期在第一份敘事前查實並登 watch）；GenScript 2026 年報（2027 年 3 月）；原文的里程碑「Isomorphic 首批藥物 2026 年底到 2027 年進人體」；7.5 檢查點只印進度 |

- **R3 母體不追加**：R3 是 AI 基礎設施的漏網稽核母體（§5）；AI 生醫是另一個需求錨，要另定母體，列進 plan §14 待決，不在本段順手擴。
- **影響哪些量測**：H1、H5、H9 的 case 清單多 B1；H6 的判讀線不變；主題標記 `aibio` 只對 2026-10-06 之後新登記的 lead 生效、不回溯（cohort-changes 同日一筆）。

### 2026-10-07｜新假說 H13：量的拐點裡，「價在自家三年頂端＋毛利在自家前高」的那一組更常先崩、不更常翻倍——預先登記，先於任何計算（使用者 2026-10-07 go，pq2 [731]）

- **為什麼加**：個股頁 schema 負錨點時光機頁（brainstorm `2026-10-05-stock-page-schema.md` §15）——兩檔負錨點 T 當天「價」（自家三年股價營收比百分位）99、100，
  「錢」的位置（單季毛利率在自家歷史）第 93、100 百分位；三檔贏家沒有一檔兩格同時在頂端。§15.3 第 2 點據此提出讀法「毛利在自家前高、價在三年頂端 → 寫『週期頂點的形狀』」，
  但那五張頁是看結果挑的、n＝2 對 3（INV-5：未量測不得默認信任）。要知道它是不是真的分得開，只能預先登記後在 H12 的事件全集上測。**它不是買點、不是 filter**（F17、G10）。
- **一句話**：在 H12 的事件全集（量的拐點，事件月 2015-01 到 2022-12）裡，T 當天「自家三年股價營收比百分位 ≥ 95」**而且**「最近一季單季毛利率 ≥ 自家前高的九成」的那一組（P），
  6 個月內先跌 30% 以上的比例高於其餘事件（R），而且 12 個月內曾達 2 倍的比例不高於 R。
- **期間與已看過的東西（照實寫）**：期間同 H12，**不是沒看過的期間**——H12 已公布這段期間「毛利率年增 ≥ +3pp 那組先崩較多」（12.0% 對 8.8%）；H13 加的是兩個 H12 沒有的格：
  價在自家三年頂端、毛利在自家前高（位置，不是年變化）。兩檔負錨點（合晶 6182 事件月 2021-10、矽創 8016 事件月 2021-06）是從 H12 的 A 組裡照結果挑的，
  **從判讀線剔除**（含它們的版本另印）。登記前只做過一件事：列出 H12 抓取快取的檔名（月營收 2014-10..2022-12、損益表 2013Q1..2022Q4、月線兩個後綴）；
  **沒有算過任何事件的股價營收比、毛利位置、分組人數或報酬**。
- **事件、進出場、結果（照 H12 逐字）**：事件＝H11 定義（m−2、m−1、m 三個月年增都 > 40%、事件月＝成立而且 m−1 不成立、去年同月 < 1,000 萬元不判），
  事件月 2015-01 到 2022-12，以公司代號串；進場＝m+1 月最後一個交易日收盤（還原權息月線），出場＝再 12 個月；「12 個月內曾達 2 倍」＝m+2..m+13 的月底收盤任一 ≥ 2 × 進場價；
  「6 個月內先跌 30% 以上」＝前 6 個月底收盤任一 ≤ 0.7 × 進場價。**月營收、損益表（營收、毛利）、還原權息月線一律用 H12 的抓取快取原檔**——H13 的事件集合與結果欄跟 H12 逐筆相同。
- **價（新增的條件一）**：T＝進場日。月底 d 的股價營收比＝市值 ÷ TTM 營收。
  - 市值＝d 那個月最後一個交易日的**原始收盤**（yfinance 未還原權息的 Close，再乘回 d 之後的 Yahoo 分割比例，還原成當時的價）× d 時已知的最新一季股數。
  - 股數＝那一季損益表彙總「淨利（淨損）歸屬於母公司業主 ÷ 基本每股盈餘（元）」（年初至今累計 → 加權平均股數；歸屬母公司欄缺就用「本期淨利（淨損）」；
    |EPS| < 0.3 的季不用、沿用前一個可用季）——同 §15。季報可知日＝法定期限（`engine_c.tw_share_capital.statutory_deadline`），**嚴格早於 d** 才算已知。
  - TTM 營收＝d 之前已過法定期限（次月 10 日，嚴格早於 d）的最近 12 個連續月營收合計（同 `alpha/three_questions.py` 台股口徑）；缺任一個月 → 那一點沒有值。
  - 窗＝T 與 T 之前 36 個月底（≤ 37 點）；**百分位＝窗內股價營收比 ≤ T 的點數 ÷ 窗內有值的點數 × 100**（含 T，同 §15 的算法）；有值的點 < 24 或 T 沒有值 →「沒有三年價位」不分組。
  - 條件：百分位 ≥ 95（月底取樣時，約等於「T 是三年來前兩高的月底」）。
  - 價格序列：先用 H12 給這個事件選的後綴；那個後綴缺的月份用另一個後綴補（轉板前後接起來）。
- **錢（新增的條件二）**：最近一季＝法定期限嚴格早於 T 的最新一季（同 H12 `gm_change`；那一季缺就是缺，不往前找）；單季毛利率＝累計相減的單季營業毛利 ÷ 單季營業收入（同 H12）。
  - **自家前高**＝那一季之前（不含那一季）自家所有單季毛利率的最大值，歷史從 2013Q1 起，只算單季營收 ≥ 3,000 萬元的季。
  - 那一季單季營收 < 3,000 萬元 →「毛利率基期太小」；之前合格的季 < 8 或前高 ≤ 0 →「沒有前高」——都不分組。
  - 條件：那一季單季毛利率 ≥ 0.9 × 自家前高。
- **分組**：P＝事件、兩格都有值、兩個條件都成立；R＝事件、兩格都有值、至少一個條件不成立。任一格沒有值的事件不分組，計數照印。
- **支持（四條全部成立）**：① P、R 各 ≥ 30 ② 6 個月內先跌 30% 以上：P > R ③ 12 個月內曾達 2 倍：P ≤ R
  ④ 前後兩段（事件月 2015–2018、2019–2022）各自的 ② 方向一樣（P > R；某段 P 或 R 不到 15 → ④ 不成立）。
- **削弱（殺死條件）**：① 成立，而且 ② 或 ③ 不成立。
- **不足**：① 不成立；或 ①②③ 成立但 ④ 不成立。
- **各結果的後果（先寫定）**：結果只進假說帳，**不改任何頁面元素、filter、排序、候選狀態前提或 lead triage 問句**。
  支持 → S4 把 §15.3 第 2 點的讀法寫進研究 skill rubric 時標「全市場量過（H13 支持）」，仍是讀法、不是門檻；
  削弱 → S4 的 rubric 不寫「週期頂點的形狀」這句，兩格照留在頁上當脈絡，§15.3 第 1 點加註「五張頁的示意，全市場沒有重現」；不足 → 照 v1.0，讀法標「未量」。
- **另印（不進判讀線）**：①只看價（≥ 95 對 < 95）、只看錢（≥ 前高九成對未達）各自的先跌與曾達 2 倍 ②增量：毛利在前高的事件裡價 ≥ 95 對 < 95；價 ≥ 95 的事件裡毛利 ≥ 前高九成對未達
  ③門檻敏感度：價 90、80；錢 80%、100%（超過前高）④P、R 的超額中位數與平均（超額同 H12）⑤H12 的 A（毛利年增 ≥ +3pp）在 P、R 各占多少
  ⑥含兩檔負錨點的版本；兩檔負錨點在 H13 口徑下的兩格值（對照 §15 的日線＋四季損益表口徑）⑦非事件月（H12 的對照列）同一個分組的先跌與曾達 2 倍——看「兩格同時在頂端」是不是量的拐點特有
  ⑧各年的 n；沒有三年價位、沒有股數、沒有前高、基期太小、抓不到價的計數。
- **新抓的資料（只有這三樣，其餘用 H12 快取）**：① MOPS 月營收 2012-04..2014-09（三年窗最早的點要 TTM；`fetch_monthly_revenue_month`）
  ② 損益表彙總 2013Q1..2022Q4 重抓一次，只取「基本每股盈餘（元）」與兩個淨利欄推股數（毛利仍用 H12 快取）③ yfinance 月線未還原權息（`auto_adjust=False`、`actions=True`）2013-01..2023-02，
  每個代號兩個後綴；限流照 H12 補抓的做法分清楚「限流」與「Yahoo 沒有」（`yfinance.shared._ERRORS`）。
- **偏差標註**：①不是沒看過的期間，兩檔負錨點已剔除，但 H12 的 A 組先崩較多是已知——P 若大半落在 A 裡，P 先崩較多可能只是 A 的重現，「價」那一格的增量看另印 ②、⑤ ②股數是 EPS 推的加權平均、不是期末股數，
  有四捨五入誤差 ③原始價靠 Yahoo 記的分割還原；台股配股 Yahoo 沒記成分割時 Close 本來就是原始價，兩種都跟當時的股數一致；Yahoo 配股比例記錯會讓序列跳一階（不查，計數不了）
  ④月營收 TTM 與 §15 的四季損益表 TTM 是不同口徑，月底取樣與 §15 的每日取樣不同——兩檔負錨點兩種都印 ⑤自家前高的歷史長度隨事件年份變（2015 年的事件約 8 季、2022 年約 36 季）
  ⑥H12 的 ①–⑦ 全部照舊（存活者、KY 期限、MOPS 現行版本、已知季可能早於拐點、全公司毛利、月底收盤、2015–2022 的環境）。
- **量在哪一層**：追蹤表（基準率回放）；腳本與結果在下一筆追加（結果出來之前本條不改）。

### 2026-10-07｜H13 結果：**削弱**（照上一筆預先登記的判讀線；登記 commit 8d8043df 早於計算）

- **判讀**：① P（價 ≥ 95 且毛利 ≥ 前高九成）n＝123、R n＝1,531，各 ≥ 30 ✓；② 6 個月內先跌 30% 以上——P **14.6%** > R **8.7%** ✓；
  ③ 12 個月內曾達 2 倍——P **16.3%** > R **8.4%** ✗（登記要 P ≤ R）；④ 前後兩段的 ②——2015–2018 P 19.2% 對 R 9.8%（P n＝26）、2019–2022 13.4% 對 8.2% ✓
  → H13 削弱：兩格同時在頂端分得出「先崩較多」，但也分出「翻倍較多」——挑出的是兩邊尾巴都肥的事件，不是週期頂點。
- **另印（不進判讀線）**：只看價（≥ 95 對 < 95）先跌 18.1% 對 7.1%、曾達 2 倍 13.8% 對 9.0%；只看錢（≥ 前高九成對未達）12.0% 對 8.2%、10.9% 對 8.4%；
  毛利在前高的事件裡價 ≥ 95 對 < 95：先跌 14.6% 對 10.7%、曾達 2 倍 16.3% 對 9.2%。門檻改價 90／80、錢 80%／100% 方向都一樣（P 曾達 2 倍 12.6–14.8% 對 R 8.3–8.8%；
  先跌 13.4–23.4% 對 8.1–8.6%）。超額中位數 P −15.6%、R −4.8%。P 有 71.5% 是 H12 的 A 組（R 38.0%）。非事件月同一分組：先跌 7.0% 對 6.0%、曾達 2 倍 9.5% 對 8.1%（同向、小得多）。
  P 集中在 2020–2021（88／123）。兩檔負錨點在 H13 口徑下價百分位都是 100、毛利對前高 0.93、1.22，落在 P；含它們判讀不變。
- **讀法**：「價在自家三年頂端」是這一組最有分量的一格，但它量到的是**波動**（兩邊尾巴一起肥，和 H11 的量的拐點同形），不是方向。
  看完結果才有的說法（**不能用同一份資料改判**）：價 ≥ 95 而毛利**沒有**跟到前高九成的那組（n＝134）先跌 30% 是 23.1%、曾達 2 倍 11.2%——「價跑在錢前面」比「兩格都在頂端」更像會崩的形狀；
  要當真得另外預先登記、換一段期間測。
- **後果（照登記）**：結果只進假說帳。S4 把讀法寫進研究 skill rubric 時**不寫「週期頂點的形狀」**；兩格照留在個股頁上當脈絡；brainstorm §15.3 第 1、2、3 點已加註。
  不改任何頁面元素、filter、排序、候選狀態前提或 lead triage 問句。
- **計數**：判讀的事件 2,077（剔除兩檔負錨點）、兩格都有值 1,654；價不分組 266（窗內點 < 24：196、T 沒有值：70）、錢不分組 392（沒有毛利率 213、沒有前高 175、基期太小 4）；
  有股數的代號 1,920、有未還原月線的代號×後綴 1,847（H12 有、這次窗內 Yahoo 沒有 15，非限流）；新抓的月營收、損益表、月線失敗 0。
  H12 重現：事件 2,079、A 709／B 1,071 的兩個比例與 H12 報告逐位相同。
- **可知日抽查**：腳本對每一個用到的股數季與毛利季檢查法定期限嚴格早於該點——違規 0；一筆手算（合晶 6182，T＝2021-11-30）與腳本一致（股價營收比 4.3231）。
- **腳本與結果**：逐字收在同目錄 [`replay-h13-priced-margin-top.md`](replay-h13-priced-margin-top.md)（抓取、計算、手算、年分查證四支）。

### 2026-10-07｜新 case G1：IC 載板上游的低膨脹玻纖布（T-glass）——二階瓶頸（SNS 先點名、系統 park 兩次、走圖走回來），預先登記，先於本層任何讀圖與敘事

- **為什麼加**：Phase 7 Step 7.1 續工 ①，層深讀入口「下一層 0 條」——IC 載板層讀圖 `sr_229707b4d4cd4f82` 判量，上游沒有任何邊。研究 session 讀了主供應商日東紡的說明會（自述）與買方景碩的年報（一手），組成入圖包 pq2 [733]（`ra_5dc9439157d8eb9d1b13a9f9d16558b5`；directed lead `lead_2d4195f84bee1e416fb7b1be5297bfaf`）。
  plan §0 第 2 項：新增 case 也是 append，開題日＝本段的 commit 日；本層的讀圖、層說明 ledger 與日東紡的第一份敘事都要等 [733] 入圖後才寫，所以都晚於本段。

| 欄 | 內容 |
|---|---|
| 類型 | **二階瓶頸，SNS 先點名、系統 park 兩次、10-07 走圖自己走回來**：第一次接觸 2026-07-25（lead `lead_ffdc392c947397e9a649b634ed41f0c8`，X 帳號 aleabitoreddit，原文逐字「Nittobo / glass fiber/cloth」，parked）；2026-09-04 再點名（`lead_d8fee64e0334807bb0f1af3c5dee0bc8`，原文逐字「Nittobo T-Glass」，parked）；2026-09-29 一份研究結論寫「可能的薄層在上游（玻纖布、ABF 膜），目前未驗證」（`lead_9a65a3ce681c46f375e8c211e3d18463`，之後沒人接）。主供應商用系統口徑是邊緣（日東紡 3110.T：yfinance 2026-10-07 市值約 6,690 億日圓、分析師 9 家）；52 週 1,412 → 6,580 → 約 3,675 日圓（分割後）的大漲大跌發生在第一次接觸之前；收盤 2026-07-24 3,195、09-04 3,060、09-29 3,040、10-06 3,640 |
| 測 | H1：第一次接觸（07-25）早於 T0，照 H1 原文進「T0 之前接觸的列」**另列、不進判讀線**（入圖並讀圖判 volume／moat，或 undecided 且供給側 ≤ 3 家，才成列；追高照 §0.1）；H5 只另印（判讀線只吃 P2、O1-U、O6——本 case 的 (i)(ii) 照 H5 的兩部分寫，但不進判讀線）；H6、H9 另印（X 帳號早於系統點名；第一份敘事的已定價判斷）；X2 旁證（兩則 park 的 lead 不在 R2 固定的 36 則樣本裡，只記在 cases X2 段） |
| 開題時已知 | pq2 [733] 的兩份一手（日東紡 2026-08-05 說明資料與主要質疑応答：T ガラス需求「引き続き非常に強い」、增強計畫到 2028、在漲價、承認客戶在評估別家；景碩 2025 年報：2H25 起玻纖布缺料、2026 持續、要找新供應商）；讀了不入包的：建榮（日東紡持股 47.65%，T 布 FY2027 量產）、台玻（自述 Low CTE 玻布量產，用途寫 5G 高頻高速材料）、欣興與南電（沒點名玻纖布）；層說明草稿 `library/private/research_notes/layer_notes/mat_ic_substrate_glass_cloth.md`；向使用者要的文件 pq2 [734]；媒體（「日東紡 T ガラス 9 割」、2026 缺口一到兩成）未追源 |
| 預期會暴露的 failure mode | ①價格已先走：系統接觸時最大的那一段漲幅已經發生（H1 的追高）；②缺口有到期日：日東紡擴產到 2028、第二來源在成形（日東紡自己承認）——讀成「量」的時間窗可能只剩一年多；③份額只有媒體數字，被當成一手；④買方那句（景碩）沒寫是哪一種玻纖布，被讀成「T-glass 缺」 |
| 支持／削弱的判準 | **H1**：照 H1 原文（本 case 只多一列，不改判讀線）。**H5 另印**：(i) 擋住研究的是什麼——今天的答案是「表示法」（上游沒建層），入圖後照實寫；(ii) 上游有沒有比第一層更不擁擠、可投資的公司——日東紡若在入圖後讀圖判 volume／moat，記「有」（列敘事 id）；若讀圖判 neither 或第二來源在一手被證實已合格量產，記「沒有」或「有但已不薄」，照實寫 |
| 2×2 | 錨＝日東紡第一份 v2 敘事日；欄＝對主題等權組的超額——**本鏈沒有主題等權組**，要在第一份敘事之前定義（成分是判斷，走 pq2），定不了就照實寫「2×2 欄缺」 |
| 裁決點 | 日東紡 2026 年度第 2 季決算說明會（2026-11 上旬，日期在第一份敘事前查實並登 watch）；景碩 2026 Q3 法說；日東紡 FY2026 決算（2027-05）；7.5 檢查點只印進度 |

- **R3 母體不追加**：日東紡不在 §5 的 AI 基礎設施觀察名單（10-05 追加的 IC 載板類 6 檔是載板廠，不是材料）；要不要把載板材料加進 R3 母體，列進 plan §14 待決，不在本段順手擴。
- **影響哪些量測**：H1 多一列候選（入圖並讀圖後才算）；H5、H9 另印多一列；cohort-changes 同日一筆。
