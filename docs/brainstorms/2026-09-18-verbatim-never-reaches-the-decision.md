# zoom-out：逐字證據到不了做判斷的那一層（2026-09-18）

> ℹ **設計來源仍有效（2026-09-22 確認）：** [`2026-09-22-graph-first-direction-decision.md`](2026-09-22-graph-first-direction-decision.md) 擴充本檔，實作前要讀；衝突時以決定紀錄為準。

> **起因（使用者原話）：** 「像你這次遇到的 我們深入看圖才發現的問題 是不是以後每一檔要產 bet 都會遇到？
> 我們該怎麼定義 skill 或 prompt，確保 LLM 會去深挖，不要只看現有 python 怎麼定義 io 就怎麼做…
> **但你一開始就太相信程式，那你根本不會有後面的事情**。」
>
> ⚠ **本檔的現況數字會腐壞**（AGENTS「現況數字會過期，判準不會」）。每個數字都附了查證命令，引用前先跑。

---

## 0. 先回答那一問：是的，每一檔都會遇到，而且有 base rate

今天只重判了**一個** relation（`enables`，82 條），結果：

| 判決 | 條數 | 占比 |
|---|---|---|
| 逐字支持，不動 | 47 | 57% |
| **需要改**（翻方向／改型別／刪重複） | **29** | **35%** |
| **逐字根本不支持任何關係** | **8** | **10%** |

查證：`library/private/alpha/enables_rejudge/classification.json`（pq2 [607] 的產物）。

**35% 不是「偶爾」。** 而且這 82 條是圖裡 530 條 canonical 邊中的一種關係；
沒有任何理由相信別的關係更乾淨——`tech:external_laser_source is_component_of tech:isolator`
（[606] 查到的那條）就是 `is_component_of` 上的同型錯誤。

---

## 1. Goal

**讓「寫下一個 bet」這件事，結構上不可能只靠 label 完成。**

不是「讓 LLM 更勤奮」——今天證明了勤奮不是變數，**手上有沒有可挖的東西才是**。

---

## 2. Current architecture：逐字在載入那一刻被丟掉

```
文件 → extract.py → 中介 JSON（**含 1,105 段 quote**）→ loader/validate.py（**檢查 quote**）
     → loader/load_to_neo4j.py → Neo4j（**quote 沒了**）→ 所有讀路徑（**只有 label**）
```

**四個實測（2026-09-18）：**

| 事實 | 數字 | 查證 |
|---|---|---|
| `extractions/` 裡的逐字 | **1,105 段、192,055 字元** | 掃 `extractions/*.json` 的 `sources[].quote` |
| 進到圖裡的逐字 | **0 段** | `MATCH (n:SourceDoc) RETURN keys(n)` — 只有 metadata，無 quote／excerpt |
| `EdgeAssertion.source_ids` 在圖裡指得到的 | **0 個**（懸空參照） | `MATCH (e:EdgeAssertion) ... MATCH (n) WHERE n.id IN e.source_ids RETURN count(n)` |
| 三個主要讀路徑提到 `quote` 的次數 | **0**（`query/structure.py`、`query/bottleneck.py`、`query/graph_context.py`） | `grep -c quote` |

**`loader/load_to_neo4j.py` 有 `MERGE_NODE`／`MERGE_EDGE`／`MERGE_SOURCE_DOC`／
`MERGE_EDGE_ASSERTION`／`MERGE_NODE_CLAIM`／`MERGE_EDGE_CLAIM`——唯獨沒有 sources。**
`quote` 在 `schema/intermediate_format.schema.json` 裡有定義、抽取端有產出、
`validate.py` 會檢查，**然後在 MERGE 那一步被靜默丟掉**。

⚠ `Chunk` 這個 label **存在於 `db.labels()` 但有 0 個節點**——schema 曾經為這件事留過位置。

---

## 3. 為什麼沒有任何東西會擋住：迴圈是封閉的

```
抽取時 LLM 給一個 label → 程式照 label 做 → 測試驗「程式有沒有照 label 做」→ 回到 label
```

**逐字是唯一在這個迴圈外面的東西，而它沒有任何一條路回得來。**

所以：

- **測試永遠不會紅。** 測試問的是「程式對不對」，不是「label 對不對」。
- **`audit invariants` 也不會紅。** 六條 invariant 管的是 identity／lifecycle／no-silent-drop／
  queue liveness／measured gate／point-in-time——**沒有一條管「這個 label 的逐字支不支持它」**。
- **它只會安靜地偏**，而且偏的方向固定：朝「看起來有洞察力的結論」（L11-6 已經記過這個方向）。

**今天所有發現的共同形狀一句話：名字承諾的語意 ≠ 內容實際承載的語意，而兩者之間沒有任何比對點。**

| 今天的發現 | 名字承諾 | 內容其實是 |
|---|---|---|
| `external_laser_source is_component_of isolator` | A 是 B 的零件 | 逐字只是**列舉 Coherent 做的兩樣東西** |
| `tech:inp_eml` | 一個獨立實體 | 與 `tech:eml` **同一個東西** |
| `enables` | A 的採用帶動 B 的需求 | 圖裡**兩種相反的用法並存**，程式實作了沒寫下來的那一種 |
| `graph_context` 的輸出 | 這是證據 | **13% 的證據**（20／154） |
| `Claim.source_ids` | 來源 id | **片段 id**，join 文件會全空 |
| `demand_anchor` | 這條邊的瓶頸錨 | **這家公司的**錨 |
| `counter_path_relation` | 一個問題的答案 | **兩個消費端問了兩個不同問題** |

---

## 4. Local-optimum trap：prompt 層修不動，而且兩個理由

**直覺解是在 skill 裡寫「請深入思考、不要只看 python 的 IO」。它會失敗：**

1. **它靠自律，不靠程式**（`development-flow` Step 3 第②問）。
   AGENTS 已經有 L11-6（「落地前跑一條試圖讓結論變成假的命令」）——**判準早就在，今天照樣發生**。
   這正是 L16 的形狀：**分類有 SSOT，但它沒有跟著資料走到需要它的地方。**
2. **更硬的那個：就算 LLM 想挖，手上也沒有可挖的東西。**
   我今天挖得到，是因為我**繞過自己的工具**直接 `grep extractions/`。
   `python -m query.structure mat:inp_substrate` 的輸出裡**一段逐字都沒有**——
   用那個工具讀圖的人，結構上不可能發現今天這些問題。

⚠ **這是本輪最該記住的一句：深挖今天需要繞過工具，所以它不會例行發生。**

⚠ 另一個 trap：**「多加一個檢查清單」也是加機制**（Step 3 第③問）。
真正的根解是**拿掉那個資訊落差**，不是在落差上面加一層提醒。

---

## 5. Possible new architecture：把逐字放回決策路徑上（三層，由硬到軟）

### L1 — 根除：逐字入圖，`source_ids` 從懸空變成指得到

`sources` 進圖（1,105 段），`EdgeAssertion`／`Claim`／`Entity` 的 `source_ids` 真的解析得到。
**這一層不改任何既有行為，純新增**，但它是 L2／L3 的前提。

### L2 — 顯形：零 LLM 的機械偵測（今天三種毛病都測得到）

| 偵測 | 現在跑會得到什麼 | 狀態 |
|---|---|---|
| **稱呼重疊的重複節點**（`inp_eml`／`eml` 那型） | **37 對候選、31 對同 `abstraction_level`、涉及 43／297 個節點（14.5%）**——一個 30 行純字串比對 | ○ 待做 |
| **relation 與定義方向矛盾** | 已交付：239 份抽取命中 2 份（0.8%），0 誤傷 | ✅ 2026-09-18 |
| **有界讀取不報上界** | 已交付：`graph_context` 六段全部印 `N／M` | ✅ 2026-09-18 |

⚠ **L2 的偵測器不是為了自動修**，是為了**自動產生「這裡看起來不對」的問句**——
今天真正觸發深挖的是使用者問「Sivers 的需求錨怎麼會是成熟製程」。
**系統要能自己生出那種問句。**

### L3 — 紀律：bet 的輸入契約改成「引用逐字，不引用欄位」

L1 落地後才有意義。判準一句話：
**寫下 bet 時，你用到的每一格都要答得出「它的逐字是什麼」；答不出來就不能拿它下注。**
這是契約不是美德——因為 L1 之後，答不出來是**可機械偵測**的。

---

## 6. Migration phases

| Phase | 做什麼 | 驗收（哪個數字會變） |
|---|---|---|
| **V1** | `loader` 新增 sources MERGE；`source_ids` 指得到 | 圖裡逐字 **0 → 1,105 段**；`source_ids` 命中率 **0% → 100%**；既有 530 邊／409 claim **一個欄位都不變** |
| **V2** | 讀路徑加 `--quotes`（`query.structure` 優先，它是讀圖入口） | `python -m query.structure <node> --quotes` 每條邊印得出它的逐字；提到 quote 的讀路徑 **0 → 1** |
| **V3** | 重複節點偵測器落地，接進既有佇列段（**只提名，不合併**） | 37 對候選出現在某個人會看到的地方；合併仍逐筆 `ra_admission` |
| **V4** | bet／research skill 的輸入契約改寫（L3） | — |

⚠ **V1 之前不要做 V3／V4**：偵測器與契約都要指得回逐字，否則又是一層 label。

---

## 7. Proposed current Step：只做 V1

**做什麼：** `loader/load_to_neo4j.py` 新增 `MERGE_SOURCE` + `(EdgeAssertion|Claim)-[:QUOTES]->(Source)`，
把 `sources[].id/locator/quote` 載進圖。

**為什麼是它：** 它是唯一的前提，而且**純新增**——既有節點、邊、屬性、排序、artifact 一個都不動。

**驗收（必須逐條可否證）：**
1. 圖裡逐字 **0 → 1,105 段**（查證：`MATCH (s:Source) RETURN count(s)`）
2. `EdgeAssertion.source_ids` 圖裡命中率 **0% → 100%**
3. **既有輸出逐位不變**：`python -m query.bottleneck --top-n 60` 的 accepted 37 列位移 0、
   `audit invariants` 仍 FAIL 0／PASS 13、全套 pytest 不減
4. 重跑 loader 具冪等性（`MERGE` 不重複建）

**要使用者決定的：** 這動到 Engine A 的 loader 與圖的 schema（多一個 label ＋ 一種關係）。
依 L17-2「動 contract → Z2 給 proposal」，**到這裡停**。

---

## 8. 這一輪要沉澱的判準（建議寫進 `AGENTS.md`，需使用者核准）

> **L18 — 抽取之後逐字就退出系統，於是每個下游都只能相信 label**
>
> **Invariant：**
> 1. **任何「把原始證據換成一個標籤」的步驟，都必須讓那個標籤指得回原始證據。**
>    指不回去時，下游**結構上不可能**發現標籤錯了——而測試不會紅，因為測試問的是
>    「程式有沒有照標籤做」，不是「標籤對不對」。
> 2. **判別法：這個工具的輸出裡，有沒有任何一個字是「當初那份文件實際寫的」？**
>    沒有 → 用它的人挖不出今天這類問題，不論他多想挖。
> 3. **「請深入思考」型的 prompt 修法在這裡無效，兩個理由**：它靠自律；而且
>    **就算想挖也沒東西可挖**。根解是拿掉資訊落差，不是在落差上加一層提醒。
> 4. **深挖若需要繞過自己的工具，它就不會例行發生。**
>
> **事發（2026-09-18）：** 重判一個 relation 的 82 條邊，**29 條要改（35%）、
> 8 條逐字根本不支持任何關係（10%）**。全部靠直接讀 `extractions/*.json` 才發現——
> 因為 `loader` 有五個 `MERGE_*` 卻獨缺 sources，**1,105 段逐字（192K 字元）在載入那一刻被丟掉**，
> 三個主要讀路徑提到 `quote` 的次數是 **0**。
> 同一天另外找到：`tech:inp_eml` 與 `tech:eml` 是重複節點（同型候選現存 37 對）、
> `external_laser_source is_component_of isolator` 方向相反且其逐字只是列舉兩樣產品。
>
> **Implementation：** `loader/load_to_neo4j.py` 的 sources MERGE｜**可改？NO**（判準）／**YES**（實作）
