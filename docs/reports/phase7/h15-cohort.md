# H15 成分凍結（2026-11-03）

> 登記：`registration.md`「2026-11-03｜新假說 H15」（commit `bb0a0c39`，2026-11-03 15:37 +08:00）。**成分之後不改**（之後翻組不換組）；
> 更正只在本檔尾 append（日期、改什麼、為什麼）。**沒有計算、沒有看任何報酬**——分組只用凍結那一份 artifact 的市值與分析師家數。

- **凍結來源**：登記 commit 之後第一次重算的候選板——2026-11-03 16:43（+08:00）`python -m webapp materialize --candidates`（整板重算；
  登記之後到這一刻沒有其他寫入者：daily 只在清晨跑、writer lock 空著）。同一次重算也寫了 `candidate_state_series.jsonl` 的 11-03 那一行
  （第一次帶 `priced_only`：count 1、unknown 0）。
- **分組（照登記原文）**：邊緣組＝市值 < 10B 美元且分析師 ≤ 12 家；鄰組＝市值 < 10B 美元且分析師 13–20 家；其餘不進判讀線。
  市值與家數照候選板每列的邊緣判定欄（`edge.market_cap_usd`、`edge.analyst_count`，與 `python -m alpha edge` 同一個判定與口徑）。
  系統的邊緣門檻寫成「≤ 10B」、本條寫「< 10B」——沒有任何一列恰在 10B 上，兩種寫法分組相同。
- **期間**：凍結日之後的第一個月底收盤起＝**2026-11-30 收盤**（該市場那天不開盤就取之前最後一個交易日）；12 個月窗到 2027-11-30
  （登記時程寫「凍結後第 13 個月底，約 2027-12」），24 個月窗到 2028-11-30。
- **判讀 n**：邊緣組 80（線 ≥ 30）、鄰組 16（線 ≥ 15）——兩組都達標；鄰組只多 1 檔，有一檔取不到價就落到「不足」（照登記印 n，不補）。
- **重產**：讀 `library/private/app/state/candidates.json` 的 groups＋side_groups＋no_narrative，以 co:* 去重，照上面兩條線分組
  （暫存腳本 `library/private/tmp/h15_freeze.py`，只讀 artifact）；下面第一行的 `content_digest` 對得上那一份 artifact。

## 成分

- artifact `generated_at`：`2026-11-03T08:43:56.209381+00:00`｜`content_digest`：`sha256:e6da64a93d6f44faa8c0bc59d11a3fb145750c2523b46d74b2deb78efa040302`｜`today`：2026-11-03
- 板上列數 196（groups＋side_groups＋no_narrative，以 co:* 去重）：邊緣組 80｜鄰組 16｜其餘 91｜量不到 9

### 邊緣組（市值 < 100 億美元 且 分析師 ≤ 12 家）

| # | 代號 | co:* | 市值（億美元） | 分析師家數 |
|---|---|---|---|---|
| 1 | 002270.SZ | `co:huaming` | 25.0 | 11 |
| 2 | 002428.SZ | `co:yunnan_germanium` | 70.7 | 2 |
| 3 | 002837.SZ | `co:envicool` | 73.6 | 12 |
| 4 | 1519.TW | `co:fortune_electric` | 58.8 | 9 |
| 5 | 1802.TW | `co:taiwan_glass` | 56.5 | 1 |
| 6 | 1815.TWO | `co:fulltech_fiber_glass` | 26.0 | 1 |
| 7 | 2455.TW | `co:vpec` | 25.6 | 10 |
| 8 | 2768.T | `co:sojitz` | 67.7 | 7 |
| 9 | 300395.SZ | `co:feilihua_quartz_glass` | 52.0 | 2 |
| 10 | 300398.SZ | `co:phichem` | 23.9 | 2 |
| 11 | 300570.SZ | `co:t_and_s_communications` | 38.9 | 3 |
| 12 | 301511.SZ | `co:defu_technology` | 49.8 | 5 |
| 13 | 3081.TWO | `co:landmark_optoelectronics` | 68.1 | 10 |
| 14 | 3110.T | `co:nitto_boseki` | 32.6 | 9 |
| 15 | 3363.TWO | `co:foci` | 15.9 | 3 |
| 16 | 4971.TWO | `co:intelliepi` | 5.3 | 2 |
| 17 | 4979.TWO | `co:luxnet` | 18.5 | 2 |
| 18 | 4991.TWO | `co:gcs_holdings` | 14.5 | 5 |
| 19 | 5411.T | `co:jfe_holdings` | 71.7 | 9 |
| 20 | 5706.T | `co:mitsui_kinzoku` | 72.5 | 10 |
| 21 | 600105.SS | `co:jiangsu_etern` | 49.6 | 1 |
| 22 | 600118.SS | `co:china_spacesat` | 98.7 | 1 |
| 23 | 600703.SS | `co:sanan_optoelectronics` | 67.7 | 3 |
| 24 | 6213.TW | `co:iteq` | 72.7 | 10 |
| 25 | 6268.T | `co:nabtesco` | 31.3 | 11 |
| 26 | 6324.T | `co:harmonic_drive_systems` | 31.2 | 10 |
| 27 | 6680.HK | `co:jl_mag` | 4.3 | 10 |
| 28 | 6805.TW | `co:fositek` | 49.1 | 9 |
| 29 | 8358.TWO | `co:co_tech` | 32.1 | 4 |
| 30 | 8996.TW | `co:kaori` | 42.8 | 7 |
| 31 | 9856.HK | `co:ligent` | 24.2 | 1 |
| 32 | AAOI | `co:applied_optoelectronics` | 53.1 | 6 |
| 33 | AAON | `co:aaon` | 56.1 | 6 |
| 34 | ACLN.SW | `co:accelleron` | 75.4 | 10 |
| 35 | AEHR | `co:aehr_test_systems` | 16.8 | 5 |
| 36 | AEVA | `co:aeva` | 6.0 | 5 |
| 37 | AMKR | `co:amkor_technology` | 91.6 | 10 |
| 38 | ARBE | `co:arbe_robotics` | 0.5 | 2 |
| 39 | ATS.VI | `co:ats` | 56.8 | 5 |
| 40 | AXTI | `co:axt` | 31.6 | 5 |
| 41 | BW | `co:babcock_wilcox` | 6.1 | 4 |
| 42 | CECO | `co:ceco_environmental` | 28.5 | 7 |
| 43 | CLF | `co:cleveland_cliffs` | 81.4 | 10 |
| 44 | COHU | `co:cohu` | 22.9 | 8 |
| 45 | EFXT | `co:enerflex` | 27.1 | 10 |
| 46 | ENS | `co:enersys` | 57.7 | 5 |
| 47 | EROC | `co:erock` | 3.8 | 8 |
| 48 | FORM | `co:formfactor` | 68.2 | 10 |
| 49 | FRMI | `co:fermi` | 14.1 | 8 |
| 50 | HIMX | `co:himax` | 18.2 | 2 |
| 51 | HPS-A.TO | `co:hammond_power_solutions` | 14.4 | 8 |
| 52 | IQE.L | `co:iqe` | 5.8 | 3 |
| 53 | JMAT.L | `co:johnson_matthey` | 40.4 | 9 |
| 54 | KLIC | `co:kulicke_and_soffa` | 37.3 | 3 |
| 55 | KSHINTL.NS | `co:ksh_international` | 6.8 | 1 |
| 56 | LIDR | `co:aeye` | 0.4 | 2 |
| 57 | LPK.DE | `co:lpkf` | 2.9 | 2 |
| 58 | MOD | `co:modine` | 65.6 | 9 |
| 59 | MTARTECH.NS | `co:mtar_technologies` | 21.1 | 5 |
| 60 | MTRS.ST | `co:munters` | 26.5 | 8 |
| 61 | MXL | `co:maxlinear` | 55.6 | 11 |
| 62 | NOVT | `co:novanta` | 55.3 | 3 |
| 63 | NVTS | `co:navitas` | 20.8 | 7 |
| 64 | OUST | `co:ouster` | 20.4 | 6 |
| 65 | POET | `co:poet_technologies` | 8.3 | 1 |
| 66 | POWI | `co:power_integrations` | 25.1 | 5 |
| 67 | PRECWIRE.NS | `co:precision_wires_india` | 7.8 | 1 |
| 68 | PSIX | `co:power_solutions_international` | 10.7 | 3 |
| 69 | SHA0.DE | `co:schaeffler` | 63.2 | 10 |
| 70 | SILEX.ST | `co:silex_microsystems` | 16.2 | 4 |
| 71 | SIVE.ST | `co:sivers_semiconductors` | 6.2 | 2 |
| 72 | SLNG | `co:stabilis_solutions` | 0.8 | 1 |
| 73 | SPB.TO | `co:superior_plus` | 10.5 | 11 |
| 74 | STLTECH.NS | `co:sterlite_technologies` | 42.5 | 3 |
| 75 | TTMI | `co:ttm` | 80.7 | 5 |
| 76 | USAR | `co:usa_rare_earth` | 33.2 | 8 |
| 77 | VIAV | `co:viavi_solutions` | 68.4 | 8 |
| 78 | VNP.TO | `co:5n_plus` | 16.8 | 8 |
| 79 | VSH | `co:vishay` | 36.1 | 7 |
| 80 | XFAB.PA | `co:x_fab` | 7.7 | 7 |

### 鄰組（市值 < 100 億美元 且 分析師 13–20 家）

| # | 代號 | co:* | 市值（億美元） | 分析師家數 |
|---|---|---|---|---|
| 1 | 002472.SZ | `co:shuanghuan_driveline` | 54.3 | 18 |
| 2 | 0522.HK | `co:asmpt` | 57.6 | 18 |
| 3 | 3105.TWO | `co:win_semiconductor` | 76.0 | 15 |
| 4 | 3324.TWO | `co:auras_technology` | 39.6 | 16 |
| 5 | 6481.T | `co:thk` | 40.6 | 13 |
| 6 | 688017.SS | `co:leaderdrive` | 73.9 | 13 |
| 7 | APLD | `co:applied_digital` | 49.0 | 16 |
| 8 | GXO | `co:gxo_logistics` | 59.8 | 17 |
| 9 | IREN | `co:iren` | 89.1 | 18 |
| 10 | KGS | `co:kodiak_gas_services` | 45.0 | 14 |
| 11 | LBRT | `co:liberty_energy` | 24.0 | 14 |
| 12 | LYC.AX | `co:lynas` | 85.1 | 13 |
| 13 | MP | `co:mp_materials` | 68.3 | 16 |
| 14 | PUMP | `co:propetro` | 8.6 | 13 |
| 15 | SEI | `co:solaris_energy_infrastructure` | 43.1 | 14 |
| 16 | SOI.PA | `co:soitec` | 49.8 | 19 |

### 其餘（不進判讀線：市值 ≥ 100 億美元，或分析師 > 20 家）

000660.KS、000725.SZ、002353.SZ、002463.SZ、005930.KS、009150.KS、012330.KS、034020.KS、2301.TW、2308.TW、2383.TW、2449.TW、267260.KS、298040.KS、300308.SZ、300394.SZ、300502.SZ、3008.TW、3017.TW、3037.TW、3189.TW、3653.TW、4062.T、5016.T、5801.T、5802.T、6274.TWO、6501.T、6594.T、688498.SS、688818.SS、688836.SS、8046.TW、AAPL、ALFA.ST、AMAT、AMD、AMZN、ANET、APO、AVGO、BE、BKR、BX、CAT、CDNS、CMI、COHR、CORZ、CRDO、CRWV、DOV、ECL、ENR.DE、FN、FTAI、GEV、GFS、GLW、GOOGL、HEXA-B.ST、HWM、INIO、INTC、JBL、JSWSTEEL.NS、LITE、LRCX、META、MRVL、MSFT、MTSI、MU、NBIS、NOK、NVDA、ORCL、PH、RKLB、SMTC、SNDK、TER、TSEM、TSLA、TSM、TXN、UMC、WMB、WRT1V.HE、WWD、XPEV

### 量不到（不進任何一組；逐列寫缺什麼）

- 300102.SZ（`co:changelight`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- 300489.SZ（`co:optics_technology_holding`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- 300943.SZ（`co:zhejiang_chunhui_intelligent_control`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- 3163.TWO（`co:browave`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- 3234.TWO（`co:truelight`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- 688020.SS（`co:fangbang_electronics`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- 688313.SS（`co:shijia_photons`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- CCXI（`co:churchill_capital_xi`）：缺分析師家數（coverage_unavailable；邊緣無法量）
- ENA.V（`co:enablence_technologies`）：缺分析師家數（coverage_unavailable；邊緣無法量）

## 更正（append）

- （尚無）
