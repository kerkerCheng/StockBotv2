# 段 4 走圖：10-27 新命中逐筆終局（2026-10-27）

> 主 session 讀節點自己的逐字與 lead 狀態後處置（沒有開判定 workflow）。**point-in-time 紀錄，不是 current-state truth**（AGENTS）；現值以 `python -m query.graph_walk` 為準。終局字彙同 [10-17 那份](graph-walk-terminals-2026-10-17.md)。

**今天九型的命中：** 第 4 型（讀圖該重讀）4 → 0，四份讀圖當天換版（下面第二張表）；其餘八型的命中逐筆對過 [10-17](graph-walk-terminals-2026-10-17.md)、[10-22](graph-walk-terminals-2026-10-22.md) 兩份終局表，主體都已有終局。只有下面 6 筆是新的，都是 [857]（robotaxi）與 [859]–[872]（表後燃氣電）入圖帶進來的。

| 型 | 命中 | 終局 | 理由（摘要） | 處置／指標 |
|---|---|---|---|---|
| 6 供貨走不到錨 | `co:ftai` | intentional | FTAI 只供航改燃機這一層（`tech:aeroderivative_gas_turbine`），這一層只經 `is_variant_of tech:gas_turbine_genset` 接到燃機機組層；is_variant_of 刻意不進任何走訪（[613]）。GE Vernova、杰瑞也供這一層，但另有走得到錨的供貨邊，所以只剩 FTAI 被報。FTAI 非邊緣（161.7 億美元、11 家，2026-10-27），不是倍率候選。 | 不動。要讓變體繼承需求錨是走訪規則的開發項，不是補邊 |
| 7 沒人供應 | `tech:automotive_camera_module` | already_terminal | [857] 的 R0 包建了相機模組層，供給側沒有一手具名。R4（模組與鏡頭）`lead_feb4131f` 已 park（not_pursued）：NVIDIA 三份一手都沒具名 Hyperion 的相機模組或鏡頭廠，要等量產車（Lucid、VW ID. Buzz AD）拆解或供應商申報。R3（影像感測器）`lead_c6cfa830` 已 park：Sony、豪威都非邊緣，部落格也沒寫合格的是哪一種感測器。 | 照 park；不為消命中補供應商 |
| 7 沒人供應 | `tech:automotive_radar` | already_terminal | R7 `lead_34ef9086` 已走到入圖包：pq2 **[881]**（Arbe 成像雷達晶片組、經緯恒润）。 | 等 [881] 的 `go`；核准入圖後這一筆自然消失 |
| 7 沒人供應 | `tech:automotive_ultrasonic_sensor` | already_terminal | R10 `lead_074793e1` 已 park（not_pursued）：一手只有每套 12 顆的規格，沒有具名供應商、沒有可等的具名文件；不由記憶列候選。 | 照 park |
| 7 沒人供應 | `tech:onsite_fuel_gas_conditioning` | already_terminal | 走圖 lead `lead_4fc46ee3`（10-27 登記）有界搜尋一輪後 park（awaiting_named_disclosure）：只找到未上市的 Croft Systems 自述；Ohio EPA 許可寫 22 台 line heaters 沒寫供應商；Enerflex、Wärtsilä、CECO 的一手都沒把燃料調壓／加熱撬的具名供應商接到資料中心表後電廠。等待有到期。 | 等 Enerflex、CECO 或 Wärtsilä 具名專案或客戶 |
| 7 沒人供應 | `tech:robotaxi_fleet` | intentional | 這是需求端節點（[852] 核准的錨、[857] 入圖），下面的 Thor、相機、雷達、光達、超音波五層 is_component_of 它；「誰供應車隊」不是供給層的問句。它刻意不登記進 `config/sector_anchors.json`：demand_chain 經 co:nvidia 樞紐會把 16 個節點改判成 robotaxi 產業（failure log #104，10-27 第二次）。 | 不動；錨的登記等 #104 修法 |

## 第 4 型：四份讀圖當天換版

| 節點［單位］ | 舊 → 新 | 判讀 | 觸發 | 連到的敘事 |
|---|---|---|---|---|
| `prod:bloom_energy_server`［socket］ | sr_682f9a95 → **sr_db33dc55** | undecided（不改） | [860] 補的反向路徑 `tech:gas_reciprocating_genset competes_with`。反證 #2 沒成立：唯一一手是 Bloom 自己 10-K 的競爭者清單，不是買方改用；#2 補一句排除在位者自述（否則恆亮）。需求側改寫成「繞得過、Bloom 被選的原文理由是對手交期」；新增 #5（渦輪與引擎 OEM 交期縮短）。 | MTARTECH.NS 換騎（改兩句）；高力騎的是 CDU／分歧管層，不受影響 |
| `tech:cw_dfb_laser`［layer］ | sr_37be3779 → **sr_14af7e97** | volume（不改） | [873] Broadcom（法說：InP 雷射廠年增三倍以上）、[876] 仕佳光子（100mW 自 2026-06 起批量出貨）。兩件都觸及反證①的實質部分；照①的 48 小時動作逐項答：沒有⑧的價格或稼動率訊號、方向相反，不改判。①改寫基準、①②⑧補兩家。 | 六份換騎：SIVE.ST、3081.TWO、4979.TWO、3234.TWO、2455.TW、COHR（各改一到三句窗口句） |
| `tech:external_laser_source`［layer］ | sr_62e2a48a → **sr_6d26d3c8** | neither（不改） | [875] 天孚自述 ELS「稳定量产交付」。反證 #2 要的是集中，這份方向相反；改一句「這一格還在量產前」。 | 9856.HK、SIVE.ST 只換 id |
| `tech:large_power_transformer`［layer］ | sr_a784972d → **sr_63c81a98** | volume（不改） | [869] 華城（供給側第九家、台中擴建 2027Q2 投產）、[874] Anthropic S-1（需求側第六家，第一家逐字寫 allocation constraints）。①補 Anthropic、③補華城。 | 沒有敘事騎這一層；華城（1519.TW）是邊緣、敘事還沒寫 |
