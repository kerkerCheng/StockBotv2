# 抽取 review — `lumentum_q3fy26_cpo.json`

- **reviewer：** Claude Code session 2026-09-19（pq2 [617] 研究／[626] 核准）
- **判準依據：** AGENTS.md L8／L11-1／L18。詳細論證見同目錄
  [`lumentum_q2fy26_cpo.review.md`](lumentum_q2fy26_cpo.review.md)（同一條 canonical edge）。
- ⚠ **本 `.json` 在 `.gitignore` 內**，圖的判讀改動只有本檔會進 Git。

## 修正（2026-09-19，pq2 [626] 核准）

- **邊 `e5`（`co:lumentum -supplies_to-> tech:uhp_laser`）的 `sole_source`：`true` → `false`。**

  本份只有一條逐字 `lumentum_q3fy26_cpo_s2`：

  > Our ultra-high-power laser chip manufacturing ramp for CPO applications is also proceeding
  > according to plan. We achieved sequential growth this quarter and are on schedule to both
  > deliver meaningful revenue in our December quarter and fulfill the multi-hundred million
  > dollar purchase order slated for the first half of calendar year 2027.

  **這段完全沒有提到獨家性**——它只講 ramp 進度與訂單履行。`sole_source: true` 在本份的
  逐字支撐是**零**，比 q2 那份（至少還有「few can deliver」可爭辯）更薄。
  這正是 L18 的形狀：抽取當下給了 label，逐字退出系統後沒有任何下游看得到它不成立。

## 刻意不動的

- `substitutability=5`、`qualification_status=qualifying`、`ramp_execution=4`、`confidence=0.9`。
- 全部 `sources[].quote`。
- ⚠ canonical edge 的 `qualification_status` 仍投影為 `designed_in`，由既有 resolution
  `resolution_0d8672af...a3d7b845e644`（2026-07-18 核准）決定，本次未動。

## 狀態

- 已重載入圖＋重投影；`python -m audit invariants` FAIL 0／PASS 13。
