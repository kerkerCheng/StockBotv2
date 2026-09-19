# 抽取 review — `coherent_q3fy26_cpo.json`

- **reviewer：** Claude Code session 2026-09-19（pq2 [577] 研究／[627] 寫入核准）
- **判準依據：** AGENTS.md L8②（`sole_source` 需客戶端或第三方印證）／L11-1（措辭精度本身
  就是一個 claim）／L18（label 必須指得回逐字）。
- ⚠ **本 `.json` 在 `.gitignore` 內**（Seeking Alpha transcript 衍生，`storage_permission:
  local_only`），所以本檔是這份抽取的判讀在 Git 裡的唯一痕跡。下一個 agent 若發現圖與抽取檔
  對不上，先讀本檔。

> `loader/validate.py` 對本項回報通過——它驗的是 schema 形狀，不是 claim 是否有原文支持（L15）。

## 狀態：**已寫入**（2026-09-19，pq2 [627] 核准）

追源在 [577] 完成（packet：`library/private/alpha/sole_source_rejudge/coherent_nvidia.json`，
⚠ 該檔在 `.gitignore` 內），寫入在 [627]。三步都跑過：
抽取層改判 → `python -m loader.load_to_neo4j <檔> --allow-dup-url` → `python -m loader.edge_resolution project`。
查證：`python -m query.structure co:nvidia` 的供給側，COHR 那列 `sole` 欄現在是 ✗。

**L14 量測：** `python -m query.bottleneck --top-n 60` 中
`co:coherent supplies_to co:nvidia` 由 **#2 → #5**（與 [626] 的 LITE 同型位移，也是 #2→#5）。
籃子不變（通過 1、首選 LITE）。

## 修正：邊 `e10`（`co:coherent -supplies_to-> co:nvidia`）的 `sole_source`：`true` → `false`

兩段逐字留在 `sources` 一字不動；問題在 label 不是引文：

| source | 逐字 | 支持 sole_source 嗎 |
|---|---|---|
| `..._s7` | 「a strategic partnership with NVIDIA … NVIDIA's $2 billion equity investment … **a multiyear supply agreement** extending through the end of the decade」 | ✗ 多年供應協議 ≠ 唯一供應商 |
| `..._s8` | 「The agreement covers **multiple CPO-related products**, including our high-power CW laser」 | ✗ 只講產品範圍與能見度 |

兩段的 `origin_entity` 都是 Coherent 自己，依 L8② 供應商自報本來就到不了獨家主張。

## 五條反證——**全部已經在圖裡**，其中一條就在同一條 canonical edge 上

1. **tier 1 法定文件，而且是 Coherent 自己說的**：`cohr_10_q_20260506` `_s3` 逐字
   「**The non-exclusive agreement** includes a multi…」。這份 10-Q 已經掛在同一條 canonical
   edge 的 6 份文件裡，圖卻仍投影 `sole_source=true`。
2. **客戶端具名，正面回答 hint 要的產品範圍**：`nvidia_sipho_blog_partner_roles` `_s5`，
   群組標題是「**Lumentum, Sumitomo, and Coherent**」，角色句「These vendors provide ELS
   assembly, optical alignment, and test with the silicon photonics engine」——**ELS 模組這一層
   NVIDIA 自己列了三家**。
3. **客戶端 PR，同日同規模的第二家**：`nvda_lumentum_partnership_pr_2026_03_02` `_s2`
   「**The nonexclusive agreement** includes an NVIDIA multibillion purchase commitment…」。
4. **第三方，命中雷射晶片那一層**：`gsr_cpo_not_delayed_2026_06_10` `_s4`「Nvidia's guidance
   to **Coherent and Lumentum** for high-power CW lasers climbed from roughly 40 million units…」
   ——連 `_s8` 自己點名的 high-power CW laser 也是兩家。
5. **客戶端生態系名單**：`nvidia_photonics_pr_2025_03_18` `_s1` 11 家並列，Coherent、Lumentum、
   Sumitomo Electric 同列。

⚠ **最可能被誤讀的那一句**：`nvidia_blog_coherent_texas_2026_06_16` `_s1`「Coherent supplies the
external laser module that plugs into the switch's front plate」——那是「**有供**」，不是「**只有它供**」。

## 刻意不動的

- `substitutability=5`：「難替換」與「唯一供應商」是兩件事。NVIDIA 的 20 億美元投資＋
  through-2030 產能協議反而支持高切換成本。
- `qualification_status=designed_in`、`ramp_execution=4`、`confidence=0.9`、全部 `sources[].quote`。
- **不寫 `sole_source_verification=verified_by_absence`**：hint 原文如此建議，但
  `schema/graph_schema.md` §7 把 `verified_by_absence` 定義成 **`sole_source=true` 時的弱驗證
  模式**，與 `false` 並存會反轉語意；而本案是**找到正面反證**，比 absence 強。這與 [626] 收尾
  留下的同一個待決問題（啟動 prompt ②b）合併處理。

## 真正屬於 Coherent 的差異化不在這條邊上

`nvidia_blog_coherent_texas_2026_06_16` `_s2`／`_s3`：「the world's first 6-inch indium phosphide
fab」「the most advanced 6-inch indium phosphide line in the world」——那是**產能規模領先**，不是
**唯一來源**，而且圖裡已由 `co:coherent depends_on tech:inp_6inch_fab`（排序 #4）承載。
推測原判讀把這種「世界唯一一條」的語氣挪到了供應關係上。

## 同時做的與另鑄的

- **首屏第三句已改寫**（[627] 範圍內）：原文「目前只有它一家被 NVIDIA 設計進去」→
  改成「它不是 NVIDIA 唯一的外部光源供應商——NVIDIA 自己的技術部落格把三家並列…」
  （brief `ib_37dfb9b27153eba8`）。第六句一併做了最小事實更正：它列的兩個錯誤訊號其中一條
  （「出現第二家拿到 NVIDIA 外部光源訂單的供應商」）**已經成真**，留著一句被自己的追源推翻的話，
  比改它更違反誠實。
- **[628] 已執行**：`co:sumitomo_electric supplies_to co:nvidia` 補進圖
  （同一份 partner blog 的 `_s5` 逐字，先前只在抽取檔裡、沒有被生成任何邊）。
- ⚠ **[629] 待核准（thesis mutation，四個人工 gate 之一）**：COHR 的
  `disproof_conditions[1]` 逐字就是「出現第二家取得 NVIDIA CPO 外部光源 design win 的供應商」，
  其 48 小時動作是「把該邊的 sole_source 降級並重跑 Q1；**需重新評估整條 thesis**」——
  **前半已在 [627] 做完，後半要人核准。**
