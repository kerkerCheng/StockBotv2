# 讀圖考試 v1 規格（草稿，待使用者簽）：寫死的記號，分不分得出讀圖判「繞不過」與「繞得過」的層

> 2026-11-24｜載體：Phase 8 目標重定（[決定紀錄](../../brainstorms/2026-11-24-playbook-replay-regoal.md) D7、步驟 1a）。
> 狀態：**DRAFT，還沒登記、還沒算任何東西**。使用者簽了之後，本檔 §2–§6 逐字登記進 [`registration.md`](../phase7/registration.md)（先於任何逐節點的計算），再凍結考卷、一次計分。
> 這是研究量測：不改任何讀圖、敘事、候選狀態、排序、門檻；不入圖、不寫任何 authority。

## 1. 它回答哪一句話、它不是什麼

**回答**：使用者 2026-11-24 問的「瓶頸感覺都是要讀圖或是偵探挖個一兩層比較容易拿到？純讀文件可以嗎」——
不經任何判斷、只用寫死的詞表從文件裡抄出來的記號，分不分得出我們自己的讀圖判「需求側繞不過」（量、換不掉）與「繞得過」（都不是）的層。

**它不是什麼**：
- 不是讀圖對不對的測驗（不碰股價；記號與讀圖可能一起錯）。
- 不是兩手走法的測驗（這裡讀的是我們已經挑進庫的文件，不是照規則全收的）。
- 及格只是必要條件：階段 A 讀的是抽取時模型挑過的引文，是上界；及格只代表值得往下做原始文件版（階段 B），不代表回放會像。
- 有判讀的節點只有 37 個、同一條鏈的層彼此相關：小樣本，照實寫。

## 2. 考卷

- 讀圖 ledger 裡每個節點取**最新一份、沒撤回的**讀圖；計分前把名單（節點、讀圖 id、判讀、寫下的日子）凍結、記 digest。
- 2026-11-24 的快照（凍結時以當下為準）：87 個節點——量 23、換不掉 2（合稱**繞不過** 25）；都不是 12（**繞得過**）；判不出 50（不計分、只印）。
  查證：`python -c "from alpha.providers.structure_readings import known_nodes, read_reading_records as r; from collections import Counter; print(Counter(x[-1].kind for x in (r(n)[0] for n in known_nodes()) if x))"`

## 3. 給它讀什麼

- **階段 A（本規格）**：那個節點在圖上五個角度（需求側、供給側、下一層、對手路徑、開發者）每條邊的逐字引文，只收**來源文件發布日不晚於那份讀圖寫下的日子**的；沒有發布日的排除並計數。
- **誰說的**（每段引文各判一次，沿用既有的發布者解析）：來源文件的發布者坐在這個節點的供給側＝**供應商**；在需求側＝**買方**；其餘解析得到的＝**第三方**；解析不到的另計，不算進任何「買方或第三方才算」的記號。
- **階段 B（及格才做，另登記）**：同一批文件的原始全文，用固定的取句規則，不靠抽取當時挑的引文。

## 4. 記號

| 記號 | 定義 | 誰說的才算 | 進主規則 |
|---|---|---|---|
| 買家說缺 | 引文命中「缺」詞表 | 買方、第三方 | 是 |
| 供應商自己說缺 | 同一張詞表 | 供應商 | 否，只印（供應商自述是弱證據） |
| 買家拿錢綁產能 | 引文命中「綁」詞表 | 不限（合約兩邊都會揭露）；按誰說的分開印 | 是 |
| 只有幾家做 | 引文命中「少數來源」詞表 | 買方、第三方 | 是 |
| 只有幾家做（用數的） | 快照供給側的公司數 ≤ 3 | — | 否，只印（家數跟我們讀多深有關） |
| 反向：買方寫明不只一家 | 引文命中「多源」詞表 | 買方、第三方 | 否，只印 |

## 5. 詞表（寫死；登記後不改）

比對方式沿用 `query/sub_language.py`：ASCII 詞整詞、不分大小寫；中日韓字整串出現即算。

```text
缺：
shortage, shortages, short supply, supply constraint, supply constraints, supply constrained, supply-constrained,
capacity constraint, capacity constraints, capacity constrained, capacity-constrained, constrained supply, tight supply,
supply tightness, sold out, on allocation, allocation basis, extended lead times, longer lead times, lead time extension,
price increase, price increases, price hike, price hikes, raised prices, backlog
缺貨, 缺货, 供不應求, 供不应求, 吃緊, 吃紧, 緊缺, 紧缺, 短缺, 滿載, 满载, 產能不足, 产能不足, 交期拉長, 交期拉长,
交期延長, 交期延长, 漲價, 涨价, 調漲, 调涨, 積壓訂單, 积压订单
逼迫, 品薄, 供給不足, 値上げ, 受注残
공급 부족, 쇼티지, 가격 인상, 수주잔고

綁：
prepayment, prepayments, prepaid, prepay, advance payment, advance payments, customer deposit, customer deposits,
long-term supply agreement, long-term supply agreements, long-term agreement, long-term agreements,
long-term purchase agreement, multi-year supply agreement, multi-year agreement, capacity reservation,
capacity reservations, reserved capacity, capacity commitment, capacity commitments, take-or-pay,
purchase commitment, purchase commitments, purchase obligation, purchase obligations, non-cancellable, non-cancelable,
noncancelable, warrant, warrants, equity investment, strategic investment, co-investment
預付, 预付, 預收, 预收, 長約, 长约, 長期供貨, 长期供货, 長期合約, 长期合同, 長期供應, 长期供应, 包產能, 包产能,
產能保證, 产能保证, 保障產能, 保障产能, 鎖定產能, 锁定产能, 入股, 認股權, 认股权, 策略投資, 战略投资,
採購承諾, 采购承诺, 合約負債, 合同负债
長期供給契約, 前受金, 資本参加, 出資
장기공급계약, 선수금, 선급금, 지분 투자

少數來源：
sole source, sole-source, sole sourced, sole supplier, single source, single-source, single sourced, single supplier,
only supplier, only source, only qualified, limited number of suppliers, limited number of sources, limited sources,
limited source, few suppliers, exclusive supplier, exclusively from, no alternative, no alternatives, no other supplier,
no other suppliers, no second source, qualification period, requalification, re-qualification, lengthy qualification
獨家, 独家, 唯一供應, 唯一供应, 單一供應, 单一供应, 單一來源, 单一来源, 少數供應商, 少数供应商, 少數幾家, 少数几家,
寡占, 寡头, 無替代, 无替代, 難以替代, 难以替代, 認證期, 認證時間, 认证周期, 验证周期
独占, 唯一, 寡占
독점, 단독 공급, 유일

多源（只印）：
second source, second-source, second sourcing, dual source, dual-source, dual sourcing, multi-source, multi-sourcing,
multiple sources, multiple suppliers, alternative supplier, alternative suppliers, alternative source,
alternative sources, qualified a second, additional supplier, additional suppliers, switch suppliers,
diversify suppliers, supplier diversification
第二供應, 第二供应, 第二來源, 第二来源, 雙供應, 双供应, 多家供應, 多家供应, 替代供應, 替代供应, 分散供應, 分散供应,
導入第二, 导入第二
```

這四張表不得出現在 `prompts/`、`skills/`（抽取端讀得到就會挑含這些字的引文，記號恆亮；與 `config/substitutability_language.json` 同一條規矩）。

## 6. 判讀

- **主規則**：一個節點只要有「買家說缺」「買家拿錢綁產能」「只有幾家做（買方或第三方寫的）」任一個，就判**繞不過**；三個都沒有，判**繞得過**。
- **計分**只在有判讀的節點上：
  - 抓到率＝讀圖判繞不過的節點裡，主規則也判繞不過的比例。
  - 放掉率＝讀圖判繞得過的節點裡，主規則也判繞得過的比例。
- **及格線**（三個都過才及格，不設中間地帶）：抓到率 ≥ 70%；放掉率 ≥ 70%；Fisher 精確檢定單尾 p < 0.05。
  以 2026-11-24 的快照算＝25 個裡至少 18 個、12 個裡至少 9 個。
- **一次計分**。看過結果想改詞表或規則＝另登記一版，而且要用新的考卷（之後才寫的讀圖），不得改了重跑同一份。
- **只印、不進判讀**：每個記號各自的 2×2；層與插槽分開；判不出的那些被主規則判成什麼；全部節點被判繞不過的比例（恆亮檢查）；
  每個節點命中的詞與那一句原文（標籤要指得回原文）；被時點排除、沒有發布日、解析不到發布者、日韓文的引文各幾段。

## 7. 事後知識與偏差從哪裡漏

| 漏點 | 怎麼處理 |
|---|---|
| 引文是抽取時模型挑的，讀圖的引用也出自同一批引文 | 階段 A 當上界讀；及格只放行階段 B |
| 詞表是寫規格的同一個模型寫的 | 寫之前沒有讀任何一份讀圖的內文與引用，只看過判讀種類的計數；規格與登記的 commit 早於任何逐節點的計算 |
| 讀圖與記號可能一起錯 | 這場考試只回答「像不像」，不回答「對不對」；對不對只能往前量 |
| 小樣本、同一條鏈的層相關 | 報告第一段寫明；不把比例當成別處可以引用的基準率 |

## 8. 流程與後果

1. 使用者簽 → 本檔 §2–§6 逐字登記（commit）→ 凍結考卷、記 digest（commit）→ 計分一次 → 報告（第一段寫它不是什麼）。
2. 程式放 `library/private/measurement/exam_reading_v1/`，唯讀（讀圖 ledger、圖的唯讀查詢）。
3. **及格**：寫 1b（回放規則規格），階段 B 併進 1b 的乾跑。
4. **不及格**：回放停。交使用者選：Phase 8 改成只做前向；或另登記一版記號、用新的考卷再考。

## 9. 要使用者定的

| # | 題目 | 建議 |
|---|---|---|
| 1 | 及格線 | 兩個比例都 ≥ 70%，加 p < 0.05（跟標旗器考卷同一條七成線） |
| 2 | 主規則 | 三個買家端記號任一；供應商自己說缺只印 |
| 3 | 階段 B（原始文件版）什麼時候登記 | 及格才做 |
