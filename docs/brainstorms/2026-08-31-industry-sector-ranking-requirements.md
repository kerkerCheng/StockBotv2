# 產業別分排序（brainstorm，2026-08-31）

> 使用者原話：「我看我們現在有碰到稀土了，我們現在有哪些產業別，是不是要分產業別做排序？
> 這樣才有機會看到光通訊以外的東西？」
> 狀態：**方向討論，未成為政策**——實作前不得改動 `rank_bottlenecks()` 唯一排序權威的地位。

## 問題

`query/bottleneck.py` 輸出單一全域排序。實測（2026-08-31）可行動排序前 23 名全部是
AI 光互連鏈（LITE/COHR/AXT/Tower/POET/AVGO），第 24 名以後才出現 GFS，機器人鏈
（HDS/Agility/Nabtesco）與剛 onboard 的稀土鏈（MP）完全擠不進可視範圍。原因不是它們
不卡，是**證據覆蓋密度不同**：光互連鏈被研究了兩個月、邊有 evidence 升級；稀土鏈昨天
才入圖。單一排序在跨產業比較時，實際上排的是「我們研究了多久」——這正是 AGENTS.md
「已知會失焦的指標」那一節警告過的形狀（指標隨研究量單調上升）。

## 現有產業別盤點（2026-08-31 實況，會過期；查證：`python -m query.coverage_gaps` 看節點分布）

1. **AI 光互連／CPO**（絕對多數）：LITE、COHR、AXT、Tower、POET、AVGO、MRVL、FOCI、
   LuxNet、Fabrinet、Sivers、IQE、AAOI…
2. **記憶體**：MU（＋SKH/Samsung 反路徑）、AMAT/LRCX 設備側
3. **機器人**：HDS、Nabtesco、Agility、Boston Dynamics、Schaeffler、Leaderdrive/雙環（反路徑）
4. **稀土磁材**（新）：MP（[296]）、Lynas（[299] 提案中）
5. **成熟製程／特殊製程**：GFS、Tower（跨光互連）、UMC（線索）

## 判準（先立在前面）

1. **分產業排序解決的是可視性，不是可比性。** 不同產業的分數不可跨組比較（證據密度
   不同），所以正確產出是「每個產業各自的 top-N＋各自的最弱軸」，不是把五個產業混成
   一張加權表——後者會重新發明單一分數的補償性問題。
2. **產業標籤是封閉字彙**，適用 closed-vocabulary-registry 判準：世界會長出新產業
   （taxonomy）→ 字彙放 config、留鬆；但**每個 chokepoint 節點的產業歸屬要可推導**，
   優先從既有結構推（demand anchor 的根節點），不手工維護第二份清單（清單會腐壞）。
3. **相關性警告要跟著分組走**：分組後「N 個產業 ≠ N 個獨立賭注」仍然成立——AI 光互連
   與記憶體共享同一個 AI capex 需求錨；機器人與稀土共享人形需求。分組呈現必附
   需求錨重疊標註。
4. **不改資本語意**：分組是呈現層，不產生 per-sector 配額、不影響 5% 單筆上限，
   不得演化成 sleeve。

## 三個候選作法

- **A. demand anchor 聚類（推薦起點）**：`rank_bottlenecks` 已對每條邊算 demand_chain；
  以需求錨根節點（tech:ai_switch／tech:optical_scale_up／tech:humanoid_robot_systems…）
  分組即是產業別，零新資料。缺點：一邊多錨會重複出現（如 Tower）；🔴 無錨者自成一組
  （這其實是 feature——「有結構沒需求錨」正是該補研究的）。
- **B. config 產業對照表**：`config/sector_taxonomy.json` 把 chokepoint 節點映射到產業。
  精準但要維護，且違反「清單會腐壞」的教訓，除非做成 CI 檢查（未映射節點報警）。
- **C. 混合**：預設 A 自動聚類；A 分不動的（多錨/無錨）才進 B 的少量人工 override。

## 開放問題

- 展示層：daily brief 是「每產業前 3」還是「全域前 10＋產業欄」？（使用者用法傾向前者：
  「才有機會看到光通訊以外的東西」）
- 純結構排序（structural_rows）要不要同樣分組？（傾向要——研究 ROI 本來就該按產業看）
- 跨產業公司（Tower 同時在光互連與特殊製程）的歸屬呈現。

## 下一步（需 pq2 核准才動工）

1. 原型：`query/bottleneck.py` 加 `--by-sector`（A 案聚類），不動預設輸出。
2. 實測後決定 brief 版面；把「N 產業≠N 獨立賭注」寫進呈現契約。
