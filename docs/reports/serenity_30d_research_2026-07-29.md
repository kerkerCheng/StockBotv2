# Serenity 過去 30 天方向研究（2026-07-29）

## 結論先行

Serenity 這 30 天真正的新主線是 humanoid robotics，但目前最能被一手證據支持的版本不是「人形機器人即將全面爆量」，而是：**倉儲／製造的物料搬運已進入少量商用；下一個決勝點是安全、uptime、部署整合與 actuator 工業化，通用 dexterity 與大規模 unit economics 尚未證明。**

現有領域沒有被推翻。Photonics 的 SIVE／AXT／AAOI／Tower 仍有可查的資本與產能事件；memory 的結構性供需證據反而變強；AI infrastructure 的合約數字很大，但 circular financing、counterparty funding 與同一需求重複計數風險也升高。這些應走 delta-only pq1，不必重做整張既有 thesis。

## Campaign receipt

| 項目 | 結果 |
|---|---:|
| 完整時間窗 | 2026-06-29 23:01 UTC ～ 2026-07-28 22:52 UTC |
| 貼文 | 279 |
| replies／thread continuations | 96 |
| `raw_text` 缺漏 | 0 |
| 含 media 的貼文 | 126 |
| 已快取 media items | 187／187 |
| 新 campaign PASS | 42 |
| 舊 PASS 保留 | 5 |
| 初始 FILTER | 229 |
| 初始 PARKED | 3 |
| 舊 no-go receipt 被保留後重審 | 20 |
| X Post read 估算成本 | 約 US$1.395 |
| daily `since_id` | 未改動（`2082230983487803755`） |

47 個 pq1 代表 leads 中，15 個是 robotics；其餘新選出的 27 個事件分為 photonics 12、memory／packaging 8、AI infrastructure 7，另有 5 個既有 PASS。229 個 FILTER 大多是短回覆、績效／價格敘事、無法拆成 atomic claim，或同一事件的重複貼文。完成本報告後，15 個 robotics leads 已由 `researching` checkpoint 成 `parked` 等 pq2 [61]，所以 current state 是 32 `triaged_go`、229 `triaged_no_go`、18 `parked`。

## Robotics：已確認與尚未確認

### 已確認

1. **Agility 的商用部署是真實的，但規模仍小。** GXO 客戶端確認與 Agility 簽訂多年 RaaS 協議，Digit 已在 live warehouse 搬運 totes；Agility 的 SEC investor deck 列出 9 個 committed facilities 與 65,000 小時運作。來源：[GXO 客戶公告](https://investors.gxo.com/news-releases/news-release-details/gxo-signs-industry-first-multi-year-agreement-agility-robotics/)、[Agility SEC investor presentation](https://www.sec.gov/Archives/edgar/data/2074973/000121390026071287/ea029548401ex99-2.htm)。

2. **`$300M orders` 不能當成 current revenue／普通 backlog。** SEC deck 的 footnote 說明它對應 1,000 台 Digit v5、三年 RaaS、含 purchaser warrants，且要通過 contractual milestones；deck 明寫不是當期營收。這是最重要的 Serenity 敘事校正。

3. **RoboFab 的 10,000 台是設計產能，不是已達產量。** 同一 deck 披露現行 v4 BOM 約 US$125k；v5 在 1k／10k 年產量下的降本曲線是 management illustrative target。`~75% U.S.-sourced parts` 也是公司自報，尚未有 supplier-level manifest。

4. **Actuator 是目前最有一手訂單證據的可投資 layer。** Schaeffler Q1 2026 資料列出約 30 個 prototype orders、5 份合約與 2026 年 series SOP；Hyundai Mobis 則被 Boston Dynamics 官方確認為 Atlas actuator supplier。來源：[Schaeffler Q1 2026](https://www.schaeffler.com/remotemedien/media/_shared_media_rwd/08_investor_relations/presentations/2026_q1_schaeffler_conference_call_presentation_zdi81v.pdf)、[Hyundai Mobis／Boston Dynamics](https://bostondynamics.com/news/hyundai-mobis-forms-strategic-collaboration-framework-with-boston-dynamics/)。

5. **Harmonic Drive 有 robotics exposure，但不是已證實的 humanoid winner。** 公司把 AI robots 列為成長領域，同時坦承實際導入速度已偏離舊中期計畫假設；目前沒有找到 Serenity 所暗示的 Agility／Optimus named design win。來源：[Harmonic Drive 管理層訊息](https://www.hds.co.jp/english/ir/management_policy/top_message/)。

### 尚未確認／不得入圖

- Goldman／IBK 的 supplier maps 屬 tier 3 discovery；除 Hyundai Mobis→Atlas 外，Hwashin、LG Energy、Harmonic Drive、Vishay Precision、LeaderDrive 等 named mappings 尚未取得客戶端確認。
- Serenity 自己揭露最大集中部位在 Agility／CCXI；其貼文是 lead source，也是明確利益衝突來源，不能提供獨立佐證。
- 「FCC 即將禁止中國 humanoid／quadruped imports」只追回 Reuters 二手敘事；截至本輪搜尋未找到 FCC Covered List、rule、public notice 或 Federal Register 原文，維持 `unverified_policy_signal`。
- Tesla Q2 的高 TAM 語句是 management conviction，不是 supplier nomination。Tesla filing 只支持公司正在為 Optimus 大規模生產做準備與投資，不能反推任何 Serenity 點名供應商。

## 方向性 thesis

### 需求與最早 use case

最早可重複商用的是結構化環境內的 material handling：tote transfer、line feeding、structured pick-and-place。它的價值不是取代所有人類工作，而是接入既有 conveyor／AMR／WMS 並維持 uptime。GXO、Schaeffler 與 Agility 的披露彼此支持這一點。

### 可能的瓶頸排序

1. Functional／cooperative safety 與現場 certification。
2. Actuator、gear、motor、encoder、force／torque sensor 的整合與量產良率。
3. Battery runtime、charging、maintenance 與 fleet orchestration。
4. Dexterous manipulation 與 task learning。
5. BOM 降本與供應鏈成熟度。

Serenity 把焦點放在 harmonic gear 很合理，但**「BOM 高」不等於「供應商有議價權」**。若 OEM 改用 planetary／cycloidal 架構、垂直整合 actuator，或多家合格供應商快速出現，component content 仍高但 chokepoint alpha 會消失。

### 可投資 read-through（證據強到弱）

| 層 | 標的／路徑 | 現況判斷 |
|---|---|---|
| Robot OEM | Agility／CCXI→AGLT | 商用與客戶證據最好，但 SPAC closing、redemption、v5 milestone、customer concentration 與 unit economics 風險最高 |
| Actuator platform | Schaeffler | 已披露 prototype orders、contracts、SOP；但 humanoid 對集團營收占比仍小 |
| Named supplier | Hyundai Mobis | Atlas actuator 關係由客戶端確認；曝險被大型汽車零組件業務稀釋 |
| Precision reducer | Harmonic Drive | 產業 exposure 真實；named humanoid design win 與導入節奏不足 |
| Sensor／China reducer | Vishay Precision／LeaderDrive | 目前只有 analyst／Serenity discovery，留 pq1，不升格 |

## 現有三領域的增量判讀

### Photonics

Sivers 的 SEK 700m 增資與「未來幾季完成美國 listing process」可由公司公告確認；但 57 SEK 發行價不是永久 price floor。來源：[Sivers 官方公告](https://www.sivers-semiconductors.com/press/sivers-semiconductors-has-resolved-on-a-directed-share-issue-of-shares-amounting-to-approximately-sek-700-million/)。這組貼文最值得做 delta-only source trace 的是 Innolight component shortage scope、SIVE listing、Tower／AAOI expansion，其他多數已被現有 CPO／SIVE／AXT 研究覆蓋。

### Memory／packaging

Serenity 的結構性 shortage 方向有一手支撐：Micron Q3 10-Q 說 DRAM／NAND demand 超過 supply，並披露多年度 take-or-pay strategic customer agreements；這比券商價格預測更有證據力。來源：[Micron Q3 2026 10-Q](https://investors.micron.com/static-files/23023765-dfef-4e7e-845b-cd744fc20d93)。但 TrendForce／券商的單季漲價幅度與個股 beneficiaries 仍是 time-varying observation，應進 Engine C／Decision context，不是 Engine A 靜態 edge。

### AI infrastructure／neocloud

方向仍是 capex 與供應受限，但大額 LTA／lease／financing 不能相加成獨立終端需求。需要拆清：誰出資、誰保證、最低採購義務、可取消條款、資本是否 circular，以及同一 GPU 是否在多份 headline contract 被重複計數。這批更適合做 counterparty／financing packet，而不是把合約金額直接當 demand proof。

## Triage 調鬆建議

不改 daily 全域規則，只加 **scoped exploration**：

- 放寬一項：未在 `themes.txt`／`TICKER_MAP` 不再視為無關。
- 仍要求：具名公司／產品／機制，外加可追查的動作、數字、連結或圖片至少一項。
- 不放寬：quotability、source-trace、evidence tier、prepared RA、pq2 graph admission。
- 先把 replies／thread／同事件重複貼文折成 candidate events；對去重 candidate events 以 50–70% PASS 作 audit band，不是 quota。279 raw posts 的 47 PASS（16.8%）不能用來判定太嚴，因分母含 96 replies 與大量重複敘事。
- 使用者 campaign 可加 pq1 scheduling priority；不提高 evidence tier，也不吃掉全域規則。

## PQ1／PQ2 routing

- Robotics 的 15 個代表 leads 已完成 campaign-level pq1 source trace，研究 receipt 是本報告；raw／parked lead 不會逐條占用 pq2。
- 使用者已核准 **pq2 [61]**。Schema 只新增 `deployment_workflow → robot_system → robot_subsystem`、`robot_oem／robot_operator／robot_component_supplier`，以及 `develops／deploys／offered_under`；沒有藉機把 IBK／Goldman 截圖的整張 supplier map 加進 ontology。
- Agility SEC、GXO、Schaeffler、Boston Dynamics 四個 origin 已完成 extraction 與 server-side validation，凍結成 Research Action `ra_155541bb6c18e49d0d58140b242c8331`（digest `856df9b6939a8664c1f515c77bd0e255d6f86fd1af08c8cfded6bbaa02d9d243`）。真正入圖是新的 **ra_admission pq2 [62]**，仍需使用者對 exact action 明確核准。
- 15 個代表 leads 仍保留 `parked` 作 provenance：1 個主要 Agility lead 綁定 prepared action，其他維持 `trace_backlog_or_lead_only_after_robotics_bundle`。這些 parked 不會再各自重生為 15 個 pq2；只有新的完整 Research Action／authority packet 才能進池。
- Photonics 12、memory／packaging 8、AI infrastructure 7 保留 delta-only pq1；不因本 campaign 自動入圖或寫 Engine C manual observation。

## 截圖／paywall 判讀

Robotics 15 個代表 leads 共快取 33 個 media items，X metadata 的 `alt_text` 全部為空。這些圖片的資訊強度差很多，不能一概當假，也不能一概當報告原文：

- Agility 簡報截圖可逐頁對回 SEC Exhibit 99.2，因此以 SEC 文件抽取，不以推文圖片抽取。
- IBK 那組圖片實際是英文 `Translated value chain`／`The report's …` 的二次整理頁，沒有 IBK 報告封面、作者、日期或原頁版式；它只能證明「Serenity 展示了一份自稱轉譯自 IBK 的摘要」，不能證明 Hwashin／LG Energy／Hyundai AutoEver 等 mapping 真在原報告。
- Goldman 圖有 `Goldman Sachs Global Investment Research` footer，來源指向比無標記截圖強，但未取得合法可核對的完整報告、日期與上下文前，仍只是 tier 3 discovery；不得用來確認 named design win。
- FT／Nikkei 截圖有標題、日期與 paywall 標記，可用 canonical article metadata＋有限可見 excerpt 登記；付費牆外看不到的其餘敘事不能推定。
- Reuters 截圖片段可由 dateline／exact phrase 追報導，但報導聲稱的 FCC rule 尚無 FCC／Federal Register 原文；所以只能記 Reuters 報導存在，不能把禁令當已生效政策。
- SVRC／IT桔子等 branded 圖仍需找到 canonical report/index 與 methodology；品牌字樣或 watermark 不是來源真實性與數字方法的充分條件。

可承受風險的 routing 是把圖片用作 **attention prior**，而不是 evidence multiplier：

1. `original_obtained`：取得官方／原作者文件與 quote，才可 extract。
2. `paywall_excerpt_verified`：只核到 canonical metadata＋合法有限 excerpt，留 Engine B／local-only；不建立 named supplier edge。
3. `direction_independently_corroborated`：截圖的廣義方向被其他一手來源支持，可研究 sector／mechanism，但 exact beneficiary 仍標 speculative。
4. `screenshot_only`：無 canonical URL、作者、日期、頁碼或可反搜 quote，lead-only；只在新增 metadata／官方事件時重跑，避免無限搜尋。

資本邊界：截圖可以提高 pq1 priority，不能單獨擴大 Engine D funded range。若 broad thesis 已有獨立一手證據，截圖可成為 research timing／paper hypothesis；若 named supplier mapping 只剩截圖支持，維持 research-only。使用者合法持有付費報告時，只在本機保存 canonical URL、報告 metadata、頁碼與必要 excerpt；不保存或上傳 cookie、帶 token URL或整份未授權報告。

## Disproof conditions

- Agility 的 v5 orders 未通過 milestones、SPAC 延遲／終止、redemptions 顯著稀釋可用現金。
- 2027 前後 committed facilities、active robots／site、operating hours 或 RaaS revenue 沒有持續成長。
- Customer-side disclosure 顯示 downtime、safety、integration cost 使 ROI 不成立。
- Actuator／reducer 快速多供應商化或 OEM 垂直整合，使 content value 未轉成 supplier margin。
- 中國政策保護論沒有正式規則，或規則只涵蓋通訊模組／政府採購而非一般商用 robots。
