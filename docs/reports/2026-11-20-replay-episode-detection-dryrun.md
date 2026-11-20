# 歷史劇本回放——選案規則乾跑（2026-11-20）

> **性質：設計審查的證據（評估檔）。** 起因：設計稿 [`docs/brainstorms/2026-11-20-historical-playbook-replay-design.md`](../brainstorms/2026-11-20-historical-playbook-replay-design.md)
> R2 第一輪方法論審查 M-B1——「簽核前先跑一次零抽取、零報酬的偵測乾跑」，並寫了條件：ABF 偵測不到或起點晚於 2021-10 時 §5.3 重寫。
> 只讀公開資料：櫃買中心產業價值鏈資訊平台 47 條產業鏈頁（節點與成員；**今天的版本**）、MOPS 歷史月營收 2014-11～2023-12（上市＋上櫃）。
> **零 LLM、零價格、零報酬**；只寫暫存區，不改任何 ledger、不寫 Engine C。事件定義逐字沿用 H11（連三個月營收年增 > 40%、去年同月 ≥ 1,000 萬元）。

## 一句話

**設計稿 §5.3 的選案規則不能用。** 照原文偵測出 687 段（加「同節點隔 30 個月」後 338 段），451 個節點裡 198 個有段；
26 個超過 50 家的節點全部有段，71 個 3–5 家的節點只有 8 個有段；201 段的起點在 2021 年。**ABF 沒有被偵測成一段**：
欣興第一個拐點起始月是 2022-06，南電與景碩在 2019–2022 沒有任何一次連三個月年增 > 40%，而且景碩在另一條產業鏈的節點（半導體／基板，11 家），
欣興與南電在印刷電路板／硬板・軟板・IC 載板製造（45 家）。改成「≥ 3 家且過半成員」後剩 52 段，其中 40 段在 2021 年，
以鋼鐵（14）、紡織（5）、石化（4）這類景氣循環為主——月營收選出來的是「全面景氣」，不是「集中需求灌進一層薄的供應商」。

## 讀法

- ABF 三家的營收是「溫和但連續」的型：南電 2020-06 到 2022-03 連 22 個月年增高於 20%（最高 58%），沒有一次連三個月過 40%。產能受限的層量出不來——
  這正是審查者說這條規則最會漏的型。
- 絕對家數門檻讓大節點恆亮（L14-4：恆亮的機制不算量測），薄節點幾乎不亮；拐點成員比例的中位數只有 0.158（多數「段」是二十幾家裡的三家）。
- 節點的切法對不上層：一層被切在兩條產業鏈（ABF），一個節點混了三種板（硬板、軟板、載板）。層成員名單不能只靠節點。
- 月營收裡沒有「需求錨」這個變數。要選到我們要的那一型，選案得從需求側出發。

## 輸出（逐字）

### detect.py

```
== 基本量
產業鏈頁 47 節點 451
月營收代號 1927 判斷列 173930 事件列（H11 cond 為真的公司月） 7962 比例 0.0458 起始月（前一月不為真） 2387
節點名單的公司 2470 其中月營收頁有資料 1882 一家屬於的節點數中位 1.0

== 偵測結果（照設計稿 §5.3 原文）
段數 687 有段的節點 198 ／ 451
各年段數（起點年） {2015: 56, 2016: 23, 2017: 67, 2018: 57, 2019: 47, 2020: 88, 2021: 201, 2022: 89, 2023: 59}
起點→第三家事件月的間隔（月）分布 {0: 68, 1: 118, 2: 141, 3: 102, 4: 143, 5: 115}
節點家數分桶：桶｜節點數｜有段的節點數｜段數
     1-2｜  93｜   0｜   0
     3-5｜  71｜   8｜   8
    6-10｜  86｜  33｜  40
   11-20｜  83｜  59｜ 137
   21-50｜  92｜  72｜ 262
     >50｜  26｜  26｜ 240
拐點成員比例（觸發家數／當時有資料的成員）：中位 0.158 ≥25% 的段 188 ≥50% 的段 49
加「同節點兩段起點至少隔 30 個月」後段數 338 各年 {2015: 39, 2016: 7, 2017: 37, 2018: 24, 2019: 20, 2020: 58, 2021: 104, 2022: 18, 2023: 31}
其中節點 ≤10 家的段 45
    3000:3130 汽車 ／ 鈑金 2021-02 3/5/6 ['2241', '2248', '3685']
    3000:3140 汽車 ／ 鋁合金鋼圈 2021-01 3/4/5 ['1563', '2248', '4502']
    3000:3160 汽車 ／ 保險桿 2023-05 3/5/6 ['2239', '2241', '2248']
    5100:51B0 區塊鏈 ／ 元件裝置 2017-07 3/3/3 ['2399', '3515', '6150']
    5300:5380 人工智慧 ／ 移動控制 2021-03 3/6/9 ['2357', '3227', '8374']
    A100:A130 太陽能產業 ／ 太陽能電池 2019-04 3/7/8 ['3576', '4768', '6443']
    A100:A130 太陽能產業 ／ 太陽能電池 2022-08 4/7/8 ['3576', '4768', '4934', '6443']
    AB20:AB27 風力發電 ／ 電纜 2021-03 3/5/6 ['1605', '1609', '9958']
    AB20:AB28 風力發電 ／ 其他配件 2020-12 4/8/10 ['2031', '2072', '3023', '9958']
    AB20:AB2G 風力發電 ／ 風場開發 2021-11 3/6/7 ['3712', '6869', '6873']
    AB20:AB2H 風力發電 ／ 發電營運 2021-11 3/5/7 ['3712', '6869', '6873']
    B000:B100 休閒娛樂 ／ 高爾夫球具業 2021-01 5/6/6 ['6670', '8924', '8928', '8938', '9960']
    D000:D800 半導體 ／ 導線架 2017-04 4/9/9 ['3310', '5285', '6548', '8070']
    F000:F400 電腦及週邊設備 ／ 顯示器模組 2021-08 4/9/9 ['2376', '3516', '5386', '6167']
    F000:FC00 電腦及週邊設備 ／ 輸出入模組/介面卡 2021-03 3/5/6 ['2357', '2377', '3577']
    F000:FT00 電腦及週邊設備 ／ 機構樞紐 2020-11 3/7/8 ['3230', '4999', '6805']
    G000:G500 平面顯示器 ／ 塑膠框 2023-06 3/6/6 ['2371', '6120', '6577']
    H000:HJ00 觸控面板 ／ 工業用設備 2015-02 4/7/9 ['3498', '5386', '5490', '5493']
    H000:HJ00 觸控面板 ／ 工業用設備 2021-12 3/8/9 ['3088', '4542', '5386']
    I000:I100 通信網路 ／ 網路IC 2015-03 3/4/5 ['3169', '6470', '8096']
    L000:L100 印刷電路板 ／ 玻璃纖維/玻纖布 2021-03 4/6/6 ['1303', '1802', '1815', '5475']
    L000:L400 印刷電路板 ／ 銅箔 2021-05 3/4/4 ['1303', '4989', '8358']
    N000:N100 石化及塑橡膠 ／ 石化上游原料及相關鑽探設備 2021-05 3/3/4 ['1303', '1723', '6505']
    N000:N600 石化及塑橡膠 ／ 人造纖維 2021-05 5/6/7 ['1301', '1303', '1326', '1409', '4714']
    O000:O100 紡織 ／ 石化原料(例如純對苯二甲酸、乙二醇、己內醯胺、丙烯&#33096;等) 2021-05 4/6/6 ['1301', '1303', '1314', '1326']
    P000:P100 電機機械 ／ 鋼鑄鐵元件 2021-04 3/7/8 ['1532', '2067', '4538']
    Q000:Q200 鋼鐵 ／ 鋼胚 2021-05 5/5/5 ['2002', '2006', '2015', '2028', '5009']
    Q000:Q400 鋼鐵 ／ 不鏽鋼胚 2021-06 3/3/4 ['1605', '2035', '5009']
    Q000:Q500 鋼鐵 ／ 冷熱軋鋼板捲 2021-05 8/9/9 ['2002', '2008', '2009', '2010', '2014', '2023', '2029', '2073']
    Q000:Q600 鋼鐵 ／ 鋼筋 2018-02 3/6/7 ['2006', '2017', '2038']
    Q000:Q600 鋼鐵 ／ 鋼筋 2021-05 7/7/7 ['2006', '2007', '2015', '2017', '2028', '2038', '2073']
    Q000:Q700 鋼鐵 ／ 線材盤元 2021-05 7/8/9 ['2002', '2007', '2012', '2017', '2028', '2064', '2073']
    Q000:Q800 鋼鐵 ／ 棒鋼盤元(捲狀條鋼) 2021-05 7/7/7 ['2002', '2007', '2010', '2015', '2028', '2064', '2073']
    Q000:Q900 鋼鐵 ／ 冷熱軋不鏽鋼板捲 2021-03 4/7/9 ['1605', '2010', '2034', '2069']
    Q000:QA00 鋼鐵 ／ 不鏽鋼棒線 2021-05 6/6/6 ['1605', '2010', '2063', '2064', '4950', '5009']
    Q000:QC00 鋼鐵 ／ 裁剪加工 2021-03 4/8/8 ['2010', '2031', '2034', '2069']
    Q000:QD00 鋼鐵 ／ 製管 2017-08 3/8/8 ['2008', '2027', '8936']
    Q000:QD00 鋼鐵 ／ 製管 2021-03 7/8/8 ['1605', '2008', '2014', '2027', '2030', '2034', '8936']
    Q000:QH00 鋼鐵 ／ 模具 2021-04 4/6/6 ['2010', '2012', '5007', '5243']
    Q000:QJ00 鋼鐵 ／ 鋼線鋼纜 2021-05 4/6/6 ['1605', '2012', '2017', '2024']

== ABF 檢查（3037 欣興、8046 南電、3189 景碩）
3037 所在節點 [('L000:L610', '硬板、軟板、IC載板製造', 45)]
   2019-2022 月營收年增最大 51.5 ｜>40% 的月份 ['2021-11', '2022-01', '2022-02', '2022-04', '2022-05', '2022-06', '2022-09'] ｜拐點起始月 ['2022-06']
8046 所在節點 [('L000:L610', '硬板、軟板、IC載板製造', 45)]
   2019-2022 月營收年增最大 58.1 ｜>40% 的月份 ['2020-02', '2020-03', '2021-01', '2021-04', '2021-05', '2021-07', '2021-10'] ｜拐點起始月 []
3189 所在節點 [('D000:D700', '基板', 11)]
   2019-2022 月營收年增最大 56.2 ｜>40% 的月份 ['2020-02', '2020-05', '2020-06', '2021-08', '2021-09', '2022-02'] ｜拐點起始月 []
   含三家之一的段： L000:L610 硬板、軟板、IC載板製造 2022-04 第三家 2022-07 4/42/45 ['2367', '3037', '3229', '3276']
印刷電路板鏈的段： [('L000:L100', '玻璃纖維/玻纖布', '2021-03', 4, 6), ('L000:L400', '銅箔', '2021-05', 3, 4), ('L000:L610', '硬板、軟板、IC載板製造', '2015-01', 4, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2015-10', 3, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2017-04', 5, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2017-10', 4, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2018-06', 5, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2019-11', 3, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2020-08', 3, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2021-02', 6, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2021-08', 3, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2022-04', 4, 45), ('L000:L610', '硬板、軟板、IC載板製造', '2023-05', 5, 45), ('L000:L620', '基板組裝加工及相關製造', '2021-01', 5, 15), ('L000:L630', '銅箔基板', '2021-02', 6, 18), ('L000:L700', '生產製程及檢測設備', '2016-06', 4, 27), ('L000:L700', '生產製程及檢測設備', '2017-03', 8, 27), ('L000:L700', '生產製程及檢測設備', '2017-09', 5, 27), ('L000:L700', '生產製程及檢測設備', '2018-04', 6, 27), ('L000:L700', '生產製程及檢測設備', '2020-10', 5, 27), ('L000:L700', '生產製程及檢測設備', '2021-05', 6, 27), ('L000:L700', '生產製程及檢測設備', '2021-11', 3, 27), ('L000:L700', '生產製程及檢測設備', '2022-05', 3, 27), ('L000:L700', '生產製程及檢測設備', '2022-11', 3, 27)]
DETECT_DONE
```

### abf_variants.py

```
== ABF 三家：不同門檻下連三月年增的起始月（2019-2022）
3037 欣興 {'>40%': ['2022-06'], '>30%': ['2022-01'], '>20%': ['2021-12'], '>15%': ['2020-04', '2021-08']}
   逐月年增% 19-01:0 19-02:4 19-03:9 19-04:11 19-05:23 19-06:9 19-07:6 19-08:8 19-09:8 19-10:4 19-11:6 19-12:24 20-01:11 20-02:21 20-03:26 20-04:16 20-05:7 20-06:7 20-07:6 20-08:-6 20-09:2 20-10:1 20-11:-4 20-12:2 21-01:9 21-02:6 21-03:3 21-04:8 21-05:9 21-06:16 21-07:19 21-08:28 21-09:19 21-10:27 21-11:42 21-12:39 22-01:41 22-02:44 22-03:38 22-04:42 22-05:51 22-06:51 22-07:29 22-08:27 22-09:43 22-10:33 22-11:23 22-12:4
8046 南電 {'>40%': [], '>30%': ['2021-06', '2021-12'], '>20%': ['2020-04', '2020-08'], '>15%': ['2020-04', '2020-08', '2022-10']}
   逐月年增% 19-01:9 19-02:-3 19-03:-2 19-04:6 19-05:11 19-06:9 19-07:7 19-08:2 19-09:10 19-10:7 19-11:7 19-12:27 20-01:1 20-02:43 20-03:41 20-04:26 20-05:10 20-06:24 20-07:22 20-08:32 20-09:20 20-10:22 20-11:31 20-12:24 21-01:58 21-02:31 21-03:25 21-04:41 21-05:40 21-06:31 21-07:44 21-08:30 21-09:29 21-10:42 21-11:30 21-12:32 22-01:34 22-02:34 22-03:35 22-04:7 22-05:28 22-06:30 22-07:13 22-08:22 22-09:31 22-10:18 22-11:25 22-12:17
3189 景碩 {'>40%': [], '>30%': ['2021-08', '2022-03'], '>20%': ['2021-05'], '>15%': ['2020-07', '2020-12', '2021-05']}
   逐月年增% 19-01:3 19-02:-17 19-03:-9 19-04:2 19-05:-21 19-06:-12 19-07:-10 19-08:-8 19-09:-1 19-10:-9 19-11:2 19-12:7 20-01:-11 20-02:56 20-03:34 20-04:10 20-05:44 20-06:42 20-07:19 20-08:11 20-09:14 20-10:23 20-11:25 20-12:16 21-01:33 21-02:12 21-03:22 21-04:33 21-05:22 21-06:31 21-07:32 21-08:48 21-09:47 21-10:34 21-11:36 21-12:26 22-01:34 22-02:43 22-03:40 22-04:37 22-05:32 22-06:25 22-07:21 22-08:17 22-09:17 22-10:10 22-11:-14 22-12:-11

== 門檻 >40%、≥3 家且過半成員：段數 52 各年 {2015: 2, 2017: 1, 2018: 1, 2020: 3, 2021: 40, 2022: 2, 2023: 3}
   依產業鏈 [('鋼鐵', 14), ('紡織', 5), ('風力發電', 4), ('休閒娛樂', 4), ('石化及塑橡膠', 4), ('汽車', 3), ('太陽能產業', 2), ('電腦及週邊設備', 2), ('印刷電路板', 2), ('建材營造', 2), ('交通運輸及航運', 2), ('區塊鏈', 1), ('人工智慧', 1), ('智慧電網', 1)]
    D000:DC00 半導體 ／ IP設計/IC設計代工服務 2020-11 8/15
    F000:FC00 電腦及週邊設備 ／ 輸出入模組/介面卡 2021-03 3/5
    F000:FD00 電腦及週邊設備 ／ 顯示卡 2021-01 7/11
    G000:G500 平面顯示器 ／ 塑膠框 2023-06 3/6
    H000:HJ00 觸控面板 ／ 工業用設備 2015-02 4/7
    I000:I100 通信網路 ／ 網路IC 2015-03 3/4
    L000:L100 印刷電路板 ／ 玻璃纖維/玻纖布 2021-03 4/6
    L000:L400 印刷電路板 ／ 銅箔 2021-05 3/4

== 門檻 >20%、≥3 家且過半成員：段數 190 各年 {2015: 3, 2016: 1, 2017: 11, 2018: 8, 2019: 5, 2020: 46, 2021: 86, 2022: 20, 2023: 10}
   依產業鏈 [('鋼鐵', 22), ('電腦及週邊設備', 16), ('汽車', 12), ('電機機械', 12), ('平面顯示器', 11), ('休閒娛樂', 9), ('石化及塑橡膠', 8), ('紡織', 8), ('印刷電路板', 7), ('交通運輸及航運', 7), ('風力發電', 6), ('觸控面板', 6), ('被動元件', 6), ('電子商務', 6)]
    D000:DC00 半導體 ／ IP設計/IC設計代工服務 2020-11 8/15
    D000:D800 半導體 ／ 導線架 2021-02 6/9
    D000:D900 半導體 ／ IC封裝測試 2021-02 16/30
    D000:DA00 半導體 ／ IC模組 2021-01 10/19
    D000:DB00 半導體 ／ IC通路 2021-01 17/34
    F000:F400 電腦及週邊設備 ／ 顯示器模組 2020-11 5/9
    F000:F400 電腦及週邊設備 ／ 顯示器模組 2021-07 5/9
    F000:F500 電腦及週邊設備 ／ 記憶體 2021-01 7/13
    F000:F600 電腦及週邊設備 ／ 主機板 2021-01 9/17
    F000:FA00 電腦及週邊設備 ／ 電池 2015-01 4/7
    F000:FA00 電腦及週邊設備 ／ 電池 2020-11 5/8
    F000:FB00 電腦及週邊設備 ／ 散熱片、風扇馬達、散熱模組 2020-09 11/22
    F000:FC00 電腦及週邊設備 ／ 輸出入模組/介面卡 2020-06 3/5
    F000:FC00 電腦及週邊設備 ／ 輸出入模組/介面卡 2021-01 3/5
    F000:FD00 電腦及週邊設備 ／ 顯示卡 2020-11 7/11
    F000:FG00 電腦及週邊設備 ／ 磁碟儲存系統 2022-07 3/6
    F000:FO00 電腦及週邊設備 ／ 隨身碟、記憶卡讀卡機 2020-07 6/12
    F000:FO00 電腦及週邊設備 ／ 隨身碟、記憶卡讀卡機 2021-02 6/12
    F000:FP00 電腦及週邊設備 ／ 多功能視訊卡 2020-05 3/4
    F000:FT00 電腦及週邊設備 ／ 機構樞紐 2019-07 3/6
    F000:FT00 電腦及週邊設備 ／ 機構樞紐 2020-05 4/7
    G000:G100 平面顯示器 ／ 化學品(如光阻劑、靶材等) 2021-03 7/12
    G000:G400 平面顯示器 ／ 背光源(發光二極體、冷陰極管) 2021-03 5/9
    G000:G500 平面顯示器 ／ 塑膠框 2022-09 3/6
    G000:G600 平面顯示器 ／ 稜鏡片 2020-05 3/4
    G000:G600 平面顯示器 ／ 稜鏡片 2023-07 3/4
    G000:G800 平面顯示器 ／ 背光模組 2020-12 4/8
    G000:G900 平面顯示器 ／ 驅動IC 2021-04 3/4
    G000:GB00 平面顯示器 ／ 面板 2020-10 9/13
    G000:GC00 平面顯示器 ／ 顯示器模組 2020-10 13/20
VARIANTS_DONE
```

## 偏差標註

1. 節點名單是 2026-11-20 的版本：當年已下市或已轉型的公司不在名單上（名單 2,470 家裡 1,882 家在月營收頁有資料）。
2. 一家公司可屬多個節點（中位 1）；段的計數沒有跨節點去重。
3. 起始月的定義＝「cond 為真、前一個月不為真」；事件列比例 4.58% 是「cond 為真的公司月」，起始月 2,387 件 ÷ 判斷列 173,930＝1.37%，與 H12 的 1.41% 同量級。
4. 沒有看任何價格或報酬——這份報告不能用來說哪一段「擠成」。

## 腳本（逐字）

### fetch.py

```python
"""選案規則乾跑——只抓資料（設計稿 2026-11-20 審查 B1）。零 LLM、零價格、零報酬。
1. 櫃買產業價值鏈平台：47 條產業鏈頁 → tpex/<ic>.html
2. MOPS 歷史月營收 2014-11..2023-12（上市＋上櫃）→ rev/rev_<market>_<YYYY-MM>.json
只寫 scratchpad，不寫 repo。對外請求用一般瀏覽器 UA，不帶任何個人資訊。"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
REPO = sys.argv[1]
sys.path.insert(0, REPO)
from fetchers.mops_open_data import fetch_monthly_revenue_month  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def log(*a):
    print(*a, flush=True)


# ---------- 1. 產業鏈頁 ----------
index = (HERE / "tpex" / "index.html").read_text(encoding="utf-8", errors="replace")
chains = sorted(set(re.findall(r"introduce\.php\?ic=([A-Z0-9]+)", index)))
chain_fail = []
for ic in chains:
    f = HERE / "tpex" / f"{ic}.html"
    if f.exists() and f.stat().st_size > 2000:
        continue
    url = f"https://ic.tpex.org.tw/introduce.php?ic={ic}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=30).read()
            f.write_bytes(body)
            break
        except Exception as exc:  # noqa: BLE001
            if attempt == 2:
                chain_fail.append(f"{ic}: {exc}")
            time.sleep(2 * (attempt + 1))
    time.sleep(0.8)
log("產業鏈頁", len(chains), "失敗", chain_fail)

# ---------- 2. 月營收 ----------
MONTHS = [(y, m) for y in range(2014, 2024) for m in range(1, 13) if (y, m) >= (2014, 11)]
fails = []
for market in ("twse", "tpex"):
    for y, m in MONTHS:
        f = HERE / "rev" / f"rev_{market}_{y}-{m:02d}.json"
        if f.exists():
            continue
        for attempt in range(3):
            try:
                rows = fetch_monthly_revenue_month(market, y, m)
                f.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    fails.append(f"{market} {y}-{m:02d}: {exc}")
                time.sleep(3 * (attempt + 1))
        time.sleep(1.0)
    log(market, "done")
log("月營收抓取失敗：", fails)
log("FETCH_DONE")
```

### detect.py

```python
"""選案規則乾跑——偵測（設計稿 2026-11-20 §5.3；審查 B1）。零 LLM、零價格、零報酬。
段＝同一節點在 6 個月窗內 >= 3 家出現量的拐點（連三個月營收年增 > 40%，去年同月 >= 1,000 萬；逐字沿用 H11 的 cond）。
只讀 scratchpad 的快取，只印統計。"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

HERE = Path(__file__).parent
MIN_BASE = 10_000
THR = 0.40
WINDOW = 6
EVENT_FROM, EVENT_TO = (2015, 1), (2023, 12)


def midx(y, m):
    return y * 12 + (m - 1)


def mstr(i):
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


# ---------- 節點名單 ----------
nodes = {}  # key -> {"chain":, "title":, "codes": [...]}
for f in sorted((HERE / "tpex").glob("*.html")):
    if f.stem == "index":
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    chain_title = (re.findall(r"<title>(.*?)</title>", t, flags=re.S) or [""])[0]
    chain_title = re.sub(r"\s+", " ", chain_title).replace("產業價值鏈資訊平台 >", "").replace("產業鏈簡介", "").strip()
    parts = re.split(r'<div id="companyList_', t)[1:]
    for part in parts:
        m = re.match(r'([A-Za-z0-9]+)" title="([^"]*)"', part)
        if not m:
            continue
        codes = sorted(set(re.findall(r"company_basic\.php\?stk_code=([0-9A-Za-z]+)", part)))
        nodes[f"{f.stem}:{m.group(1)}"] = {"chain": chain_title, "title": m.group(2), "codes": codes}

# ---------- 月營收 ----------
panel = defaultdict(dict)  # code -> {midx: (yoy, base)}
for f in sorted((HERE / "rev").glob("rev_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        code = r.get("company_code")
        if not code:
            continue
        cur, ya, yoy = r.get("revenue_current"), r.get("revenue_year_ago"), r.get("change_yoy_pct")
        if yoy is None and cur is not None and ya:
            yoy = (cur / ya - 1) * 100
        y, m = map(int, r["data_month"].split("-"))
        panel[code][midx(y, m)] = (None if yoy is None else yoy / 100, ya)


def cond(code, i):
    vals = []
    for k in (-2, -1, 0):
        rec = panel[code].get(i + k)
        if rec is None or rec[0] is None or rec[1] is None or rec[1] < MIN_BASE:
            return None
        vals.append(rec[0])
    return all(v > THR for v in vals)


lo, hi = midx(*EVENT_FROM), midx(*EVENT_TO)
onsets = defaultdict(list)  # code -> [midx]
judged_rows = event_rows = 0
for code in panel:
    for i in range(lo, hi + 1):
        c = cond(code, i)
        if c is None:
            continue
        judged_rows += 1
        if c:
            event_rows += 1
            if cond(code, i - 1) is not True:
                onsets[code].append(i)

print("== 基本量")
print("產業鏈頁", len({k.split(':')[0] for k in nodes}), "節點", len(nodes))
print("月營收代號", len(panel), "判斷列", judged_rows, "事件列（H11 cond 為真的公司月）", event_rows,
      f"比例 {event_rows / max(judged_rows, 1):.4f}", "起始月（前一月不為真）", sum(len(v) for v in onsets.values()))
all_codes = {c for n in nodes.values() for c in n["codes"]}
print("節點名單的公司", len(all_codes), "其中月營收頁有資料", len(all_codes & set(panel)),
      "一家屬於的節點數中位", median(Counter(c for n in nodes.values() for c in n["codes"]).values()))

# ---------- 偵測 ----------
episodes = []
for key, n in nodes.items():
    ev = sorted((i, c) for c in n["codes"] for i in onsets.get(c, ()))
    j = 0
    while j < len(ev):
        a = ev[j][0]
        win = [(i, c) for i, c in ev if a <= i <= a + WINDOW - 1]
        firsts = {}
        for i, c in win:
            firsts.setdefault(c, i)
        if len(firsts) >= 3:
            third = sorted(firsts.values())[2]
            eligible = [c for c in n["codes"] if any(a - 2 <= k <= a + WINDOW - 1 for k in panel.get(c, {}))]
            episodes.append({"node": key, "chain": n["chain"], "title": n["title"], "start": a, "third": third,
                             "members": sorted(firsts), "n_trig": len(firsts), "n_node": len(n["codes"]),
                             "n_eligible": len(eligible)})
            while j < len(ev) and ev[j][0] <= a + WINDOW - 1:
                j += 1
        else:
            j += 1

print("\n== 偵測結果（照設計稿 §5.3 原文）")
print("段數", len(episodes), "有段的節點", len({e['node'] for e in episodes}), "／", len(nodes))
print("各年段數（起點年）", dict(sorted(Counter(e["start"] // 12 for e in episodes).items())))
print("起點→第三家事件月的間隔（月）分布", dict(sorted(Counter(e["third"] - e["start"] for e in episodes).items())))


def bucket(n):
    for lim, name in ((2, "1-2"), (5, "3-5"), (10, "6-10"), (20, "11-20"), (50, "21-50")):
        if n <= lim:
            return name
    return ">50"


order = ["1-2", "3-5", "6-10", "11-20", "21-50", ">50"]
nb = Counter(bucket(len(n["codes"])) for n in nodes.values())
eb = Counter(bucket(e["n_node"]) for e in episodes)
hb = Counter(bucket(len(nodes[k]["codes"])) for k in {e["node"] for e in episodes})
print("節點家數分桶：桶｜節點數｜有段的節點數｜段數")
for b in order:
    print(f"  {b:>6}｜{nb.get(b, 0):>4}｜{hb.get(b, 0):>4}｜{eb.get(b, 0):>4}")
ratios = [e["n_trig"] / max(e["n_eligible"], 1) for e in episodes]
if ratios:
    print("拐點成員比例（觸發家數／當時有資料的成員）：中位", round(median(ratios), 3),
          "≥25% 的段", sum(r >= 0.25 for r in ratios), "≥50% 的段", sum(r >= 0.5 for r in ratios))

# 同節點起點至少隔 30 個月
kept = []
last = {}
for e in sorted(episodes, key=lambda e: (e["node"], e["start"])):
    if e["node"] in last and e["start"] - last[e["node"]] < 30:
        continue
    last[e["node"]] = e["start"]
    kept.append(e)
print("加「同節點兩段起點至少隔 30 個月」後段數", len(kept),
      "各年", dict(sorted(Counter(e["start"] // 12 for e in kept).items())))
thin = [e for e in kept if e["n_node"] <= 10]
print("其中節點 ≤10 家的段", len(thin))
for e in thin[:40]:
    print("   ", e["node"], e["chain"], "／", e["title"], mstr(e["start"]), f"{e['n_trig']}/{e['n_eligible']}/{e['n_node']}", e["members"])

# ---------- ABF 檢查 ----------
print("\n== ABF 檢查（3037 欣興、8046 南電、3189 景碩）")
for code in ("3037", "8046", "3189"):
    homes = [k for k, n in nodes.items() if code in n["codes"]]
    print(code, "所在節點", [(k, nodes[k]["title"], len(nodes[k]["codes"])) for k in homes])
    ys = {mstr(i): round(v[0] * 100, 1) for i, v in sorted(panel.get(code, {}).items())
          if midx(2019, 1) <= i <= midx(2022, 12) and v[0] is not None}
    print("   2019-2022 月營收年增最大", max(ys.values()) if ys else None,
          "｜>40% 的月份", [k for k, v in ys.items() if v > 40],
          "｜拐點起始月", [mstr(i) for i in onsets.get(code, []) if midx(2019, 1) <= i <= midx(2022, 12)])
for e in episodes:
    if any(c in e["members"] for c in ("3037", "8046", "3189")):
        print("   含三家之一的段：", e["node"], e["title"], mstr(e["start"]), "第三家", mstr(e["third"]),
              f"{e['n_trig']}/{e['n_eligible']}/{e['n_node']}", e["members"])
pcb = [e for e in episodes if e["node"].startswith("L000:")]
print("印刷電路板鏈的段：", [(e["node"], e["title"], mstr(e["start"]), e["n_trig"], e["n_node"]) for e in pcb])
print("DETECT_DONE")
```

### abf_variants.py

```python
"""乾跑補充：ABF 三家在較低門檻下的拐點起始月；以及「節點過半成員」版本的段數。只讀快取、零價格。"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
MIN_BASE = 10_000


def midx(y, m):
    return y * 12 + (m - 1)


def mstr(i):
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


panel = defaultdict(dict)
for f in sorted((HERE / "rev").glob("rev_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        code = r.get("company_code")
        if not code:
            continue
        cur, ya, yoy = r.get("revenue_current"), r.get("revenue_year_ago"), r.get("change_yoy_pct")
        if yoy is None and cur is not None and ya:
            yoy = (cur / ya - 1) * 100
        y, m = map(int, r["data_month"].split("-"))
        panel[code][midx(y, m)] = (None if yoy is None else yoy / 100, ya)


def cond(code, i, thr):
    vals = []
    for k in (-2, -1, 0):
        rec = panel[code].get(i + k)
        if rec is None or rec[0] is None or rec[1] is None or rec[1] < MIN_BASE:
            return None
        vals.append(rec[0])
    return all(v > thr for v in vals)


def onsets(code, thr, lo, hi):
    out = []
    for i in range(lo, hi + 1):
        if cond(code, i, thr) and cond(code, i - 1, thr) is not True:
            out.append(i)
    return out


lo, hi = midx(2019, 1), midx(2022, 12)
print("== ABF 三家：不同門檻下連三月年增的起始月（2019-2022）")
for code, name in (("3037", "欣興"), ("8046", "南電"), ("3189", "景碩")):
    row = {f">{int(t * 100)}%": [mstr(i) for i in onsets(code, t, lo, hi)] for t in (0.4, 0.3, 0.2, 0.15)}
    print(code, name, row)
    ys = [(mstr(i), round(v[0] * 100)) for i, v in sorted(panel[code].items()) if lo <= i <= hi and v[0] is not None]
    print("   逐月年增%", " ".join(f"{k[2:]}:{v}" for k, v in ys))

# 節點過半版本
nodes = {}
for f in sorted((HERE / "tpex").glob("*.html")):
    if f.stem == "index":
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    chain = re.sub(r"\s+", " ", (re.findall(r"<title>(.*?)</title>", t, flags=re.S) or [""])[0])
    chain = chain.replace("產業價值鏈資訊平台 >", "").replace("產業鏈簡介", "").strip()
    for part in re.split(r'<div id="companyList_', t)[1:]:
        m = re.match(r'([A-Za-z0-9]+)" title="([^"]*)"', part)
        if m:
            nodes[f"{f.stem}:{m.group(1)}"] = (chain, m.group(2),
                                               sorted(set(re.findall(r"stk_code=([0-9A-Za-z]+)", part))))

LO, HI = midx(2015, 1), midx(2023, 12)
for thr in (0.4, 0.2):
    ons = {c: onsets(c, thr, LO, HI) for c in panel}
    eps = []
    for key, (chain, title, codes) in nodes.items():
        ev = sorted((i, c) for c in codes for i in ons.get(c, ()))
        j = 0
        while j < len(ev):
            a = ev[j][0]
            firsts = {}
            for i, c in ev:
                if a <= i <= a + 5:
                    firsts.setdefault(c, i)
            elig = [c for c in codes if any(a - 2 <= k <= a + 5 for k in panel.get(c, {}))]
            if len(firsts) >= 3 and len(firsts) >= 0.5 * max(len(elig), 1):
                eps.append((key, chain, title, a, len(firsts), len(elig)))
                while j < len(ev) and ev[j][0] <= a + 5:
                    j += 1
            else:
                j += 1
    print(f"\n== 門檻 >{int(thr * 100)}%、≥3 家且過半成員：段數", len(eps),
          "各年", dict(sorted(Counter(e[3] // 12 for e in eps).items())))
    by_chain = Counter(e[1] for e in eps)
    print("   依產業鏈", by_chain.most_common(14))
    tech = [e for e in eps if e[0].split(":")[0] in {"D000", "L000", "F000", "I000", "G000", "K000", "M000", "H000", "J000"}]
    for e in tech[:30]:
        print("   ", e[0], e[1], "／", e[2], mstr(e[3]), f"{e[4]}/{e[5]}")
print("VARIANTS_DONE")
```

產業鏈頁實際是用 curl 逐頁抓的（`https://ic.tpex.org.tw/introduce.php?ic=<代碼>`，一般瀏覽器 UA；`fetch.py` 裡的 urllib 版會卡住），`fetch.py` 只負責月營收那一段。
