# Extraction Instructions — 各類文件的 AI 抽取指引

> 這份文件記錄「給 AI 一份原始文件時，怎麼下 instruction 讓它配合 extract.py 的格式抽取」。
> 隨做隨補，不求完整。

---

## 共用前置說明（每次都貼）

```
你是一個供應鏈知識圖譜的資料抽取助手。
請從下方文件中，抽取出 nodes（實體）、edges（關係）、claims（主張）。
格式請嚴格按照 extract.py 的輸出 schema（nodes/edges/claims/sources）。
規則：
- 具體產品/公司名稱必須逐字出現在原文中，不可從類別詞推斷
- 每個 node/edge/claim 必須標注 source_ids（對應 sources 陣列的 id）
- confidence 請根據文件性質給（法說會 = 0.85–0.95，媒體報導 = 0.55–0.70）
- 若資訊不確定，寧可壓低 confidence，不要捏造
```

---

## 法說會 Transcript（Earnings Call）

**來源型態：** Tier 1（prepared remarks）/ Tier 2（Q&A 段落）

**給 AI 的 instruction：**

```
文件類型：法說會逐字稿（Earnings Call Transcript）
公司：[公司名]  季度：[Q? FY??]  doc_id：[命名，例如 cohr_q2fy26]

重點抽取範圍（跳過財務數字的例行說明）：
1. CEO/CFO 在 prepared remarks 中提到的產品線、客戶關係、供應鏈安排
2. Q&A 中分析師追問的技術細節或供應商具名
3. 明確提到的時間軸 / 出貨時程 / 認證進度

請特別注意：
- 「我們是唯一供應商」類主張 → 標注 sole_source=true，但 confidence 不超過 0.6（自我報告偏誤，L8）
- 放量時程（ramp）主張 → demand_proof_level 填 "guided"
- 法說會本身即為 origin_event，格式：{公司ticker}_{季度}_earnings，例如 cohr_q2fy26_earnings
```

---

## SEC EDGAR 8-K（Earnings Press Release）

**來源型態：** Tier 1

**給 AI 的 instruction：**

```
文件類型：SEC 8-K Exhibit 99.1（季度業績新聞稿）
公司：[公司名]  日期：[YYYY-MM-DD]  doc_id：[命名]

注意：
- press release 的 prepared remarks 與法說會 transcript 通常高度重疊，若兩者都有，
  source_ids 需分開記，但 origin_event 相同（同一季度法說會事件）
- 財務數字（EPS、Revenue）抽成 Claim，不要抽成 node
- 前瞻性陳述（forward-looking statement）的 confidence 上限 0.75
```

---

## 學術論文 / arXiv

**來源型態：** Tier 1（技術事實）/ Tier 2（市場主張）

**給 AI 的 instruction：**

```
文件類型：學術論文
來源：[arXiv ID 或期刊名]  doc_id：[命名]

重點：
- 技術參數（良率、功耗、線寬、製程節點）→ 抽成 node.attributes 或 edge.attributes
- 論文作者的機構（大學/公司實驗室）→ 注意有些技術論文作者就是供應商員工，需標注
- demand_proof_level 一律填 "inferred"（論文不等於商業需求）
- 技術 claim 的 confidence 可到 0.85，市場預測 claim 不超過 0.65
```

---

## 產業報導 / 券商研究摘要

**來源型態：** Tier 3

**給 AI 的 instruction：**

```
文件類型：產業媒體報導 / 券商研究摘要
來源：[媒體名 / 券商名]  doc_id：[命名]

注意：
- confidence 上限 0.65
- 若報導引用的資訊可追溯到一手來源（法說會/filing），
  標注「需交叉驗證」，不直接升格 confidence
- 禁止從報導標題推斷具體公司/型號（L6 幻覺防護規則）
```

---

## 備注區（隨手記）

<!-- 在這裡隨便記，不用格式 -->
擷取指引(本次觀察 / 供下次內化)

公司↔技術核心關聯(Lumentum):InP 雷射晶片(EML / CW / UHP)是主軸。EML=transceiver 光源(100G→200G lane speed);CW laser=矽光子 transceiver 與自家垂直整合;UHP laser(400mW)=CPO/scale-out/scale-up。抓取時凡出現這幾個雷射類別,幾乎都是關鍵段落。
四大成長引擎命名要記牢:cloud transceivers、OCS、CPO(scale-out)、新增第四項 optical scale-up(取代 copper,首批出貨 late CY2027)。「scale-up vs scale-out」是本季新框架,下次同業(Coherent、Marvell、Broadcom、NVIDIA)transcript 若出現這對詞,值得對照。
新縮寫/新主題:ELS(External Light Source)=可插拔光源模組,content 較單顆雷射高 2–2.5×,是本次首度重點提出的 TAM 擴張訊號;differential 200G EML=新產品,ASP/毛利雙 tailwind。這兩個是下次要追的新命名。
量化技術訊號(可直接進知識庫):200G lane 佔 5% 量卻貢獻 10% 晶片營收(≈2:1 ASP)、目標年底 25% mix;EML 供需缺口 ~30% 且加產後仍未收斂;InP 40% 擴產已 front-load 過半(Q2 >20%);OCS backlog >$400M / 三客戶 / $10M 里程碑提前一季。
公司↔公司/地點關聯:三座 fab(Sagamihara 日本、Caswell 英國、Takao 日本);後段轉向 contract manufacturing,新主管來自 Jabil;新增 fab 可能走 acquisition——這些是供應鏈與併購線索。
判斷取捨方式:純財務(revenue、EPS、operating margin、guidance、CapEx、股數)整段略過;但當財務數字「綁定技術 mix 因果」(如毛利上升來自 200G mix / 1.6T 較 800G 毛利高)則保留,因為它同時是技術訊號。本次 Wajid 的純財務段落全數捨棄,只留與 LTA 定價機制、mix 相關的因果敘述。
下次注意的邊界訊號:1.6T vs 800G 的 WDM(EML 主導)/ parallel-fiber(SiPh 主導)分流邏輯,是判斷 EML 需求持續性的關鍵;subsea 可靠度背書被用來解釋 CPO 客戶信心——「可靠度來源」這類論證是技術護城河線索,建議保留。

這是「產業技術 review 論文」而非 earnings call,但你的擷取規則完全適用:所有出現「技術↔公司」「公司↔公司↔技術」「規格/里程碑」關聯的段落照抄。純方法論定義(DIP、SMT、BGA、QFN、QFP、SOT、FC 這類 conventional package 教科書式定義)沒有公司或量化訊號,已整段略過。
CPO(Co-Packaged Optics)是本篇主軸,是 AI datacenter 互連的核心主題,建議列為長期追蹤關鍵字。關聯到的公司/機構:TSMC(InFO / COUPE / CoWoS-S)、Samsung(I-Cube4 / X-Cube)、Intel(Foveros / 3D glass CPO)、Broadcom(3D Silicon CPO)、Corning(glass CPO + IOX 玻璃波導)、IME of Chinese Academy(silicon CPO)。
可操作量化訊號(值得建 watch list):Broadcom 3D Si CPO 用 4 顆 CPO 封裝支援 12.8 Tb/s、功耗與成本降 40%;Intel 宣示 2030 年單封裝 1 兆(1 trillion)電晶體,並押注玻璃基板;IME silicon CPO 的 RDL line/space < 10 µm。這些是可回頭跨來源交叉驗證的硬指標。
新縮寫 / 命名整理:TIV(Through InFO Via)、TGV(Through-Glass Via)vs TSV、IOX(ion exchange,離子交換玻璃波導製程)、PIC/EIC(光子/電子 IC)、HBM、InFO 家族(PoP / B / OS / LSI / MS / AiP)。「glass substrate + femtosecond laser」是本篇獨特的技術賭注,和純 silicon 路線區隔,下次遇到玻璃基板/飛秒雷射封裝可歸此脈絡。
判斷邊界案例:CoWoS-S vs I-Cube4、Foveros vs X-Cube 這兩段是「公司 A 技術 vs 公司 B 技術」的比較段,雖偏敘述性、無數字,但含明確技術差異定位(誰強調 thermal、誰強調 interconnect scalability),符合「公司↔技術關聯」故保留。EDA co-simulation 段點名 Cadence、Ansys Lumerical(工具↔製程關聯)也保留;Author Contributions / Funding / Conflicts 這類非技術行政段落全數略過。
