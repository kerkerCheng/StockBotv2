# 抽取 review — `lumentum_q2fy26_cpo.json`

- **reviewer：** Claude Code session 2026-09-19（pq2 [617] 研究／[626] 核准）
- **判準依據：** AGENTS.md L8（`sole_source` 需客戶端或第三方印證，供應商自報最高只算
  `verified_by_absence`）／L11-1（措辭精度本身就是一個 claim）／L18（label 必須指得回逐字）。
- ⚠ **本 `.json` 在 `.gitignore` 內**（transcript 衍生內容），所以圖的判讀改動只有本檔會進 Git。
  下一個 agent 若發現圖與抽取檔對不上，先讀本檔。

> `loader/validate.py` 對本項回報通過——它驗的是 schema 形狀，不是 claim 是否有原文支持（L15）。

## 修正（2026-09-19，pq2 [626] 核准）

- **邊 `e9`（`co:lumentum -supplies_to-> tech:uhp_laser`）的 `sole_source`：`true` → `false`。**

  三條逐字全部留在 `sources` 一字未動；問題出在 label 不是引文：

  | source | 逐字 | 支持 sole_source 嗎 |
  |---|---|---|
  | `..._s14` | 「secured an additional multi-$100 million purchase order for ultra-high-power lasers」 | ✗ 只講訂單規模 |
  | `..._s15` | 「the 400-milliwatt power level required is something **few can deliver**」 | ✗ **few ≠ only one**（L11-1） |
  | `..._s27` | 「Existing initial CPO orders remain on track for material UHP shipment inflection」 | ✗ 只講出貨節奏 |

  三條的 `origin_entity` 全是 Lumentum 自己，依 L8 最高只能到 `verified_by_absence`（弱）。
  另有兩條互相獨立的反證：①圖內 `co:coherent -supplies_to-> tech:uhp_laser` 的逐字
  （`cignal_cpo_elsfp_1q26_2026_04_01`，tier 3 第三方）寫著「Coherent announced a PO for its
  high-power laser for **the same application**」；②圖外 AAOI 官方新聞稿 2025-12-18
  （`library/raw/aaoi_400mw_cpo_pump_laser_pr_2025_12_18.txt`）逐字 400mW narrow-linewidth pump
  laser、over 400mW at 50°C——**直接命中 Lumentum 獨家論據所依賴的那個 400mW 門檻**。

## 刻意不動的

- `substitutability=5`：「難以替換」與「唯一供應商」是兩件事，前者未被本輪證據推翻。
- `qualification_status=designed_in`：AAOI 那份的 boundary 逐字載明「does not name a customer,
  disclose a design win, or confirm commercial revenue」——它證明**產品存在**，不證明**取得設計導入**。
- `ramp_execution=4`、`confidence=0.9`、全部 `sources[].quote`。
- `sole_source_evidence_quality`：本檔不帶此屬性；圖上該值由
  `nvda_lumentum_partnership_pr_2026_03_02_cov14_1` 提供（已是 `weak`），本次未動。

## 狀態

- 已重載入圖（`python -m loader.load_to_neo4j ... --allow-dup-url`）＋重投影
  （`python -m loader.edge_resolution project`）。
- `python -m audit invariants`：FAIL 0／PASS 13。
- 下游實測：`rank_bottlenecks()` 中該列由 **#2 → #5**，basket 列序 2 → 3，LITE 仍是 `top_pick`。
