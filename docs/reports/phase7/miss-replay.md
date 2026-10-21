# 漏抓回放追蹤表（雷達精進 C 驗收 1）

> **append-only。** 每列一個**使用者點名**的事件（「今天有搜到這個嗎？」那一類）：事件日、第一次進 lead registry 的管道與日期、
> 雷達有沒有收、`python -m engine_b.impact --lead <id>` 列出的對照（讀圖／在盯條件／敘事哪一格）。
> 目的：數「雷達比別的管道晚、或根本沒收」的事件，以及收進來之後對照有沒有接到該接的讀圖。
> **泛化判準**：往後只有 `config/daily_routine.json` 的 `market_topics` **沒點名**的事件才算泛化證據——為了某個事件加的題目，
> 再抓到同一類事件不算。計畫：`docs/plans/2026-10-21-001-feat-radar-impact-mapping-plan.md`。

| # | 事件 | 事件日 | 第一次進 registry（管道、台北時間、lead） | 雷達 | C1 對照（讀圖／在盯／敘事格） | 備註 |
|---|---|---|---|---|---|---|
| 1 | Microsoft 退出 Nscale 英國 Essex 資料中心合作（電網延誤） | 2026-10-18（Reuters／FT／Guardian） | 使用者點名 `directed:user_2026_10_19`，10-19 23:04，lead_9afbd2f6；X 帳號（aleabitoreddit、carrioresearch）10-20 05:30 | 10-19 daily **沒收**（failure log #88）；10-20 補跑收 lead_7d9a55ad（`web_radar:new`，市場層；同日加了第 5 題「需求反轉與延誤」——不算泛化） | 讀圖 `tech:large_power_transformer`；在盯反證 5 條（ew_1088、ew_1089、ew_1090、ew_1109、ew_1363）；敘事 AAON.demand、AEVA.demand（具名 Microsoft）；另經 NVIDIA 只計數 | 計畫原列的 MSFT、NBIS、IREN 敘事已於 10-20 撤回（非邊緣，第 2 題），照記 |
| 2 | Samsung 接受 NVIDIA 要求，NVHBM 的 base die 交台積電 3 奈米代工 | 2026-10-18（韓國媒體） | X `x:jukan05`，10-19 05:30，lead_d1ac2004（停放）；另 `x:dnystedt` 10-20 05:30（lead_9c5c08d7） | 10-18～10-20 **沒收**；10-21 收 lead_aaf6f852（`web_radar:new`，市場層第 6 題「供應鏈分工」10-21 才加——不算泛化） | 讀圖 `tech:hbm`、`tech:cpo`；在盯反證 8 條（含 HBM 讀圖的 ew_0762；dnystedt 那則另含 ew_0763）；敘事 3163.TWO.demand、3363.TWO.bottleneck／our_bet、FORM.demand 等（具名台積電）；另經 NVIDIA 只計數 | 10-21 回放時 jukan05 那則**對不到 `tech:hbm`**：節點名比對要求兩側字界，「NVHBM」「HBM4E」都不算 HBM——當下修（L17）：全大寫縮寫左邊准兩個大寫字母前綴、右邊准數字或複數 s；全庫 1,941 則回放多對到 9 處、全部正確、0 處漏掉（放寬到任意大寫前綴會誤報 EPIC→PIC、CHANNELS→ELS，所以只放到兩字母） |
