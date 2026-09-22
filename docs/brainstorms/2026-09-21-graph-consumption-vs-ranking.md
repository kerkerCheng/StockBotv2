# 圖的消費 vs 排序——方向性重審的素材（2026-09-21）

> ⚠ **已封存（2026-09-22）：不要再讀。** 本檔的決定已被 [`2026-09-22-graph-first-direction-decision.md`](2026-09-22-graph-first-direction-decision.md) 整併或取代，只為歷史稽核保留；分類與理由見 [`README.md`](README.md)。

> **這份文件不是結論，是待審查的素材。** 它把 2026-09-21 一次互動 session 的討論與實測整理成
> **可以被攻擊的形式**，供下一個乾淨 session 做獨立審查。
>
> ⚠ **本文所有診斷都是「待否證」，不是已確認。** 作者是同一個 session，而該 session 在同一天
> **犯了兩次引用錯誤**（見第五節）——所以本文的可信度本身就該被打折。
>
> ⚠ **每個數字都附查證命令。引用前先跑**（`AGENTS.md`「現況數字會過期，判準不會」）。

## 怎麼用這份文件

1. **不要先讀我的診斷（第三節）。** 先跑第二節的查證命令，自己看數字。
2. 第四節列出**該攻擊哪裡**——那是我自己看得到的弱點，一定還有我看不到的。
3. 審查分兩種 profile，本文的問題**跨了兩邊**，別用錯：
   - **research profile**（`skills/blind-spot-audit/SKILL.md`）→ 第三節的 D3／D4（投資邏輯主張）
   - **development／operational profile**（`skills/development-flow/SKILL.md`）→ D1／D2／D5／D6（機制是否生效、責任重疊）

---

## 一、使用者的原始擔心（逐字，不要改寫）

這輪討論由使用者的四段話推動，按時間順序：

1. 「我們蓋了很多機制來預估 但我們怎麼可能預估的這麼準確 只要有一個值我們做的假設太強 或是做了跟市場一樣的假設 是不是後面的東西都白做了 或是把圖的重要性就大福降低了 感覺這一層太重了」
2. 「每一檔股票 用同一個架構去填 不可能能找到一個共同架構敘事來描述所有股票吧⋯⋯我們改越多 會不會就是維度用越多然後就越容易overfitting?」
3. 「像sivers，他真的就用一個CWB laser能代表嗎? 這題目感覺太大了 是不是有可能再往下decompose」
4. 「有排序這件事情就蠻 tricky的，這東西真的能排序出來嗎?⋯⋯這些共通點真的能用一套邏輯排出來嗎?」
5. 「我們就是建好圖，想辦法消費它，花token補強它，這樣而已」
6. 「你走訪的過程中，看到當時入圖的紀錄，也會有疑問想深挖，看到raw再讀一次又有其他見解，然後再回來修改。這也是一個讀圖內化的loop⋯⋯現在應該是純交給LLM，看它有沒有幸運往下一層讀?」

---

## 二、實測清單（跑過的，附查證命令）

### 2.1 估值層的輸出值域

五檔的基準隱含報酬：

| AXTI | AEHR | LITE | COHR | SIVE.ST |
|---|---|---|---|---|
| +0.01% | +0.34% | +4.43% | −5.01% | −20.35% |

AXTI 的 `future_target` 是 70.038，現價 70.03，**差 0.008 美元**。

```bash
python -c "import json;[print(t, json.load(open(f'library/private/app/analyst_view/{t}.json',encoding='utf-8'))['overview']['implied_return']['simple']['value']) for t in ['AXTI','COHR','LITE','AEHR','SIVE.ST']]"
```

⚠ **不要把這讀成「數學恆等於零」**——SIVE 的 −20.4% 是反例。正確陳述是**值域落在 −21%~+6%**，
而目標區（2–10 倍）是 +100%~+900%。

### 2.2 有賭注的檔數與首屏短評的內容

`payoff.simple` 有值的只有 3 檔（AXTI／COHR／LITE）。COHR 的首屏短評逐字：

> 「我們賭的不是營收，是獨家地位會在獲利率上現形：明年營益率的增幅取 **+4.5%**，而不是保守版的 **+2.5%**。」

```bash
python -c "import json;d=json.load(open('library/private/app/analyst_view/COHR.json',encoding='utf-8'));print(d['overview']['brief']['our_bet']['value'])"
```

### 2.3 逐字到不了決策路徑

`extractions/` 有 **1,114 段 quote、193,580 字元**；quote 中位數 162 字，**37% ≥190 字**，最長 676。

```bash
grep -c quote query/bottleneck.py query/graph_context.py query/structure.py
# 實測：bottleneck 0｜graph_context 0｜structure 15
```

### 2.4 排序的覆蓋率與前 31 名

`rank_bottlenecks` 自己的輸出第一段：`substitutability` 覆蓋 **89／525（17%）**，
並自陳「覆蓋率 17%——排名必然偏向已被抽取過的邊，**沒填的邊是隱形的**」。

前 31 名：COHR×6、LITE×5、GFS×5、AVGO、TSM、MU、TSEM、MP、IQE、Soitec、AXTI……
**Sivers／Aehr／聯亞／華星光／全新／英特磊一個都沒有。**

```bash
python -m query.bottleneck | head -45
```

### 2.5 沒填 sub 的邊怎麼離開排序

```python
# query/bottleneck.py:655
if (edge.substitutability or 0) < min_substitutability:
```

`None` 被 `or 0` 壓成 0。而**同一個檔案裡 `sole_source` 已經在 2026-09-05 修過一模一樣的問題**，
註解還在（「⚠ 三態：True／False／None⋯⋯**不是** False」）。

另：`structural_rows`（註解說它回答「該去補誰的證據」）是從 `scored` 排序的，
而 `scored` 已被 `min_substitutability` 過濾——**所以它看不到那 436 條沒填 sub 的邊。**

```bash
sed -n '645,700p' query/bottleneck.py
```

### 2.6 節點粒度：Sivers 掛在三個粒度上，競爭地位相反

| 節點 | 供給側幾家 | Sivers sub | 合格狀態 | 需求錨 |
|---|---|---|---|---|
| `tech:cw_dfb_laser` | **6 家** | 2 | sampling | ✅ 2 跳 |
| `tech:dwdm_laser_array` | **1 家（只有它）** | 2 | sampling | ✅ 3 跳 |
| `tech:wdm_laser_16ch` | **1 家（只有它）** | 未填 | **qualifying** | 🔴 **走不到** |

```bash
python -m query.structure tech:cw_dfb_laser --quotes
python -m query.structure tech:dwdm_laser_array --quotes
python -m query.structure tech:wdm_laser_16ch --quotes
```

同形問題：laser 類節點 **33 個**；`tech:eml`／`tech:eml_laser`／`tech:inp_eml` 三個並存；
ELS 層四個節點有兩個接不到需求錨（`tech:module_integrated_laser_source`、`tech:internal_laser_module`）。

### 2.7 圖健康的兩個指標互相矛盾

| 檢查 | 結果 | 它量的是 |
|---|---|---|
| `python -m query.health_audit` | 14 項綠、1 項紅 | schema 一致性 |
| `python -m query.duplicate_nodes` | **28 對候選｜39／188 節點（20.7%）｜23 對沒人提過** | 概念一致性 |

而重複偵測自陳 20.7% 是**下限**（「名字完全不同的重複抓不到」）。

### 2.8 公司節點在結構讀圖裡幾乎是空的

| 節點 | 結構讀圖看得到 | 但 extractions 裡實際有 |
|---|---|---|
| `co:sivers_semiconductors` | **2 條** | **75 條邊、18 份抽取** |
| `co:aehr_test_systems` | 1 條 | 2 份抽取、6 段逐字 |
| `co:unitree` | **0 條，需求錨走不到** | — |

Sivers 那 75 條大量掛在 `enables`／`develops`／`partnership_with`，
**而五個角度的走訪清單只收 `supplies_to`／`depends_on`／`is_component_of`／`competes_with`。**

⚠ 走訪清單被改過至少一次：`mat:inp_substrate` 第 4 筆讀圖逐字記著，把 `constrained_by`
加進需求側後，需求側從 15 變 16，而**圖一條邊都沒動**。

### 2.9 三檔候選的財務對照

| | Sivers | Aehr | Unitree |
|---|---|---|---|
| 市值 | 91.6 億 SEK | 30.5 億 USD | 2,083 億 CNY |
| 營收 TTM | 2.78 億 SEK | 5,000 萬 USD | 20.8 億 CNY |
| **EV/Rev** | **33.9** | **58.9** | **89.4** |
| 毛利／營益 | −7.6%／−217% | 35.3%／−6.4% | **57.3%／+37.6%** |
| 分析師 | 3 | 5 | 4 |

對照排序前幾名：**COHR EV/Rev 9.0、LITE 27.4**。

```bash
python -c "
import sqlite3;con=sqlite3.connect('library/private/engine_c/stockbot-engine-c-private-v1-458db5270ee2.db')
con.row_factory=sqlite3.Row
for t in ['688836.SS','SIVE.ST','AEHR','COHR','LITE']:
    r=con.execute('select * from financial_snapshots where ticker=? order by snapshot_date desc limit 1',(t,)).fetchone()
    if r: print(t, dict(r)['ev_revenue'], dict(r)['analyst_target_count'])
"
```

### 2.10 Sivers 的歸零旗標已經亮了兩盞紅燈

逐字：現金跑道 **red**「手上現金撐不到一個 going-concern 評估期」；
負債 **red**「淨負債而且在燒錢——還本得靠再融資」。稀釋與 going concern 是灰的（未量）。

但 `payoff` 與 `brief` 都是 **missing**——**四塊材料都在，沒有人把它們組成一句話。**

### 2.11 讀圖 ledger 不是 0 筆，是 8 筆

`library/private/alpha/structure_readings/` 有 `tech_cw_dfb_laser.jsonl`（3 筆）
與 `mat_inp_substrate.jsonl`（5 筆）。

`mat:inp_substrate` 那 5 筆是一個自我修正序列：判 undecided → 指名缺口 → **鑄 pq2 [596]／[597]**
→ 補完改判 volume → **發現前一筆的論據「在寫下的時候已經錯了六週」** → 發現 staleness 一表兩義
→ 逐字第一次到得了讀圖。

**這 8 筆讀圖沒有一筆用到排序。**

### 2.12 深挖路徑的長度

`library/raw/` 有 445 檔，extractions 241 檔，**同名對得上 189／241＝78%**。
但**沒有任何工具把「讀圖看到一條邊」接到「讀它的 extraction／raw」**——兩段手動。

```bash
python -c "
import glob,os
ext={os.path.splitext(os.path.basename(p))[0] for p in glob.glob('extractions/*.json')}
raws={os.path.splitext(p)[0] for p in os.listdir('library/raw')}
print(len(ext), len(raws), len(ext&raws))
"
```

---

## 三、我提出的診斷（**全部待否證**）

### D1｜估值層的輸出值域結構性受限，而它正在當 gate
兩個桿（EPS、目標倍數）在沒有 differentiated evidence 時都預設等於市場，
所以輸出擠在 ±20% 帶內。而籃子的 `payoff_not_positive` 用它決定「值不值得看」。
**攻擊點：** 這是「規則正確但用途錯配」，還是我把個別參數選擇誤讀成結構？

### D2｜排序存在正回饋環，而根因是 `or 0`
排序只看得見已填 sub 的 17% → 研究補排序排得高的 → 那是大公司 → 大公司的邊被填得更滿。
**攻擊點：** 研究方向真的由排序決定嗎？pq1／pq2 的實際選題紀錄能否證這一點？

### D3｜排序排得越準，排出來的越是已被定價的（**最弱的一條，但影響最大**）
六個排序鍵全是「證據充分度」的代理，而證據充分度與市場定價充分度高度相關。
**支持證據只有一組 EV/Rev 對比**（2.9）。
**攻擊點：** 這是真的結構性關係，還是我從 5 個樣本編出來的故事？有沒有反例？

### D4｜三檔候選的不確定性不在同一量尺上，所以排不出順序
Sivers＝時間風險（現金燒完前拿不拿得到 qualified）；Aehr＝事實風險（那個瓶頸存不存在）；
Unitree＝持續性風險（37.6% 營益率能不能維持）。
**攻擊點：** 這個三分法是不是我事後編的？換三檔還成立嗎？

### D5｜節點粒度決定 substitutability，而 substitutability 是排序鍵第二位
**攻擊點：** 粒度分裂是 taxonomy 問題（字彙留鬆）還是 contract 問題（打開它是 bug）？
先讀 `docs/solutions/architecture-patterns/closed-vocabulary-registry.md`。

### D6｜深挖靠運氣，因為它需要繞過自己的工具
L18-4／L18-5 已經寫下這件事，但沒解。
**攻擊點：** 加機械訊號會不會變成 L16-4 警告的「會誤報的 linter」？
ROADMAP 已實測的限制：逐字是節錄，**「不在 quote 裡」≠「不在文件裡」**。

### D7｜Phase 1 結案理由有疑點（**窄版，未確認**）
Phase 1 的理由是「各家在自己年報裡逐字互相指認對方是同層競爭者」。
但聯亞 sub=3（`lmoc_cw_sub1`，conf 0.85）的三段 source 裡，兩段與可替代性無關，
唯一相關那段的後半句是「該類同業多以 **MBE** 技術為主⋯⋯本公司為全球少數⋯⋯以 **MOCVD** 為核心製程」。

窄版診斷：L8 該降級的是「全球少數」這個**評價**，不是「MBE vs MOCVD」這個**技術事實**；
系統只有一個 sub 數字，沒有能力區分。

**否證命令（先跑再決定採不採信）：**
```bash
python -m query.structure mat:inp_substrate --quotes | grep -i "mocvd\|mbe"
grep -rl "MOCVD" extractions/*.json
```

---

## 四、該攻擊哪裡（我自己看得到的弱點）

1. **D3 是整條推理的承重牆，而它只有一組 EV/Rev 對比支撐。** 如果 D3 倒了，
   「不要改進排序」這個建議就失去主要理由。
2. **我全程只看了 5–6 檔**，而且全在光通訊／CPO 這一條鏈上。
   `AGENTS.md` 明文要求點明相關性：**N 檔不等於 N 個獨立機會。**
3. **我提的每個修法都是「加一個機制」**（走訪清單加 relation、輸出加命令、輸出加訊號）。
   development-flow Step 3 第③問要求回答「為什麼不能用拿掉的方式達成」——**我沒有認真回答過。**
4. **「消費圖」這個循環我說它有效，證據是 8 筆讀圖。** 但那 8 筆全在 2 個厚節點上，
   而目標區是薄節點。**有效性可能不可遷移。**
5. **我沒有查過 pq1／pq2 的實際選題紀錄**，卻斷言研究方向由排序決定（D2）。

---

## 五、⚠ 作者在同一天犯的兩次錯（不要重蹈）

兩次都是**引用自家文件而沒跑查證命令**，而 `AGENTS.md`「現況數字會過期，判準不會」
整節逐字就在警告這件事：

1. **說「Q5 的讀圖 ledger 現在 0 筆」** —— 引用 ROADMAP 裡 2026-09-17 的快照。
   實際是 **8 筆**，而且內容品質高於我當輪的產出。
2. **說「`AGENTS.md` 明文：humanoid 的機會在零組件不在整機」** —— `grep` 回傳空。
   那句話在 **`ROADMAP.md` 的「研究主題範圍」**，而那是正確的位置。

3. **說「[558] co:unitree 的 blocker 已經腐壞」** —— 理由是 Engine C 有 688836.SS 的
   17 筆 `financial_snapshots`、56 筆 `consensus_estimates`。**實際跑 reassess 之後仍是
   `valuation_payoff_unknown`**，而 decision 自己的理由逐字說得很清楚：
   「凍結 context 裡這一軸只有 `yfinance://fx/CNYUSD=X`（fx authority）——**沒有 market
   價格序列**，所以連校準倍數都算不出來」。
   **「Engine C 有資料」≠「凍結 context 的那一軸有 authority」**，而我把兩者當成同一件事。

   ```bash
   python -m decision_lab reassess dc_1322bfc1c743fa746b76e280c1b27b28 --intent research --format markdown
   ```

另有一次**過度推廣**：從 AXTI 一個樣本推出「目標價恆等於現價」的恆等式，
被自己的驗證命令抓到（SIVE 的 −20.4% 是反例），已降級為「值域受限」。

**四次的共同形狀：錯誤朝「有洞察力的結論」偏**——與 ROADMAP「已撤回的診斷」那節記載的形狀相同。
⚠ 其中第 3 次與那一次過度推廣，**都是被一條可執行命令當場抓到的**；
另外兩次（引用錯檔案、引用過期快照）**只因為使用者起疑才被發現**。
這個對比本身就是 L18-5 的證據：**有可執行檢查的診斷活不過幾分鐘，沒有的全靠當下願不願意多查一步。**

---

## 六、待決的問題（使用者還沒決定）

1. **Unitree 的需求錨走不到**，是圖漏建，還是圖正確反映了 ROADMAP「humanoid 的機會在零組件不在整機」？
   **兩者在圖上完全同形**——這是 `absence_kind` 該管而沒管的事。Unitree 要不要當候選看？

   ⚠ **2026-09-21 補充（已查）：** 池子裡本來就有 **[558] co:unitree**（`decision_review`，
   ref `dc_1322bfc1c743fa746b76e280c1b27b28`，當日 01:27 defer）。當日重跑 reassess，
   結論**未變**：`valuation_payoff_unknown`，理由是凍結 context 的那一軸只有 fx authority、
   **沒有 market 價格序列**（公司 2026-08-19 才上市，交易歷史不足）。
   **所以它不是被忽略，是卡在一個真實的上游缺口。**
   但這**不回答**需求錨那題——需求錨走不到與估值軸缺 authority 是兩件事，
   **而目前沒有任何東西在追前者**。
2. 走訪清單要不要收 `enables`／`develops`／`partnership_with`？
   （代價：會讓所有讀圖變 stale，而 staleness 目前分不出「圖變了」vs「走訪清單變了」）
3. 財務層的地位——ROADMAP Phase 4b 正在把 `payoff_not_positive` 接進籃子當 gate，
   而使用者的方向是**把財務縮小成「方向感與買賣時間」**。這兩個方向相反。

---

## 硬邊界（審查與後續都不放寬）

- 不入圖、不改 thesis、不寫 Engine C、不動資本 → 要寫 authority 就鑄 pq2 等核准
- `rank_bottlenecks()` 仍是唯一排序權威（要改這條是改 `AGENTS.md` 判準句，**必須停下等人**）
- 不得為了讓籃子非空而放寬條件
- 任何診斷落地前，先跑一條**試圖讓它變成假**的命令
