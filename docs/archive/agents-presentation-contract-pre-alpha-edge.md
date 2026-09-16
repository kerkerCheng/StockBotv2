# AGENTS.md 呈現契約——2026-09-16 轉向前的逐字封存

> **性質：** 歷史封存，不是 current-state truth。2026-09-16 依決定紀錄
> [`../brainstorms/2026-09-16-alpha-edge-discovery-requirements.md`](../brainstorms/2026-09-16-alpha-edge-discovery-requirements.md)
> D0 整章重寫 `AGENTS.md`「呈現契約」；本檔保留 2026-09-16 當天 `master`（commit `c810588`）版本的整章原文，一字未改。
> 每一句的去向見 [`../refactor/alpha-edge-step0-migration.md`](../refactor/alpha-edge-step0-migration.md)。
> 現行契約只在 [`../../AGENTS.md`](../../AGENTS.md)；本檔的任何句子與它衝突時，以它為準。

---

# 呈現契約

## Alpha 呈現契約：候選＋事件追蹤，不是部位尺寸

**系統只負責兩件使用者自己做不動的事：哪些標的值得看、它們有什麼新事件。**
買多少、什麼時候買由使用者決定。

理由是實測而非偏好（**以下為 2026-08-15／08-28 定案當時的實測值，非現況**）：
6 個 ELIGIBLE cohort 每檔 target 固定 0.1% NAV、合計 0.6%（每檔約 30 美元），
而該尺寸來自當時從未被 outcome 驗證的 `axis_ceiling`（`measured_outcomes` 0/8）。
2026-08-28 再測：21 個 operational cohort 有 20 個 `live_supported_range` 是 `[0,0]`，
排序第一名 COHR 的三個資本風控**沒有一個 binding**，唯一 binding 的是 `weakest_axis`
的 0.002——**一個從未被驗證的機制在決定資本**，正是 L14 明文禁止的事。
使用者的原話：「繞了這麼久只得到我很早就看到的幾間公司、都等於 0.2%，我會不知道我到底
做了什麼」——**產出若無法讓人分辨做了什麼與沒做，它就不算產出**。

**因此資本表達層已整組移除：** `live_supported_range`、`axis_ceiling`、`paper_target`、
probe cap 與四動作（`NO_ACTION`／`REVIEW`／`TRADE`／`HEDGE`）都不再產生。
~~系統終點是**瓶頸度排序**，注意力狀態只剩 `MONITOR`／`REVIEW`。~~
**修正（2026-09-15 使用者定案 D1）：籃子層的排序權威仍是瓶頸度排序，但個股頁的中心改為「賭注」**
——base case（依 09-09 原則收斂到共識的校準基準）照印，旁邊必須答得出**「如果我們的差異看法對了，
值多少、靠哪幾條假設、各自有什麼證據」**。載體是假設 ledger 的 `scenario=variant` overlay
（只寫有差異的核心 driver，其餘沿用 base；同一條橋、同一套估值與報酬算術），payoff ＝ variant fair value
對現價的隱含報酬。**它是條件句不是機率加權**：沒有 bull／bear、沒有機率；每條 variant 假設型別層強制
independent ＋ 至少一條 supporting 證據（說不出證據的差異是偏差，不是賭注）。**沒寫賭注是 optional 缺席**，
不讓 readiness 變差、不得補一個 bull case。舊句劃線不刪：安靜消失擋不住下次回填。
查證：`python -c "import json;d=json.load(open('library/private/app/analyst_view/COHR.json',encoding='utf-8'));b=d['view']['bet'];print(b['status'],[l['key'] for l in b['lines'] if l['role']=='override'])"`
**outcome 量測改為等權重報酬追蹤**：只記「哪天推薦了這檔、當時股價、之後報酬率」，
不含部位大小或 NAV 佔比。

> **查證（別相信這段文字，跑一次）：**
> `python -c "import json;p=json.load(open('config/investment_policy.json'));print(sorted(p['probe_lane']), p['single_position_nav_cap'])"`
> `probe_lane` 不該再有 `axis_ceilings`／`probe_book_nav_cap`／`single_probe_nav_cap`／
> `live_adv_fraction_cap`；`single_position_nav_cap` 應仍是 0.05。

**真正的風控完全不變。** 拿掉的是憑空的建議尺寸，不是煞車；live choice／fill 仍然
100% 人工，系統不連 broker。**NAV 比例呈現是純呈現、零門檻**——不判斷好壞、不告警、
不阻擋任何動作。

### 「哪些標的值得看」的交付要求（違反即視為未完成）

判準四維度（瓶頸地位／需求錨點／客戶端資本承諾／標的純度）住
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)；這裡是對輸出的硬要求。

- 必須輸出**有序清單與明確的首選**，並直接回答「現在要加碼哪一檔」。
- 若因證據不足而無法排序，必須指出**缺哪一項具體證據**，不得以「未經 outcome 驗證」搪塞。
- **「outcome 還沒驗證」不是拒絕排序的理由，不論當下比值是多少。** 不出手就沒有 outcome，
  沒 outcome 就不敢排序，是死循環；L14 要求的是「不得讓未量測機制**決定資本尺寸**」，
  不是「不得表達研究判斷」。判斷與尺寸是兩件事，尺寸仍然不給。
  ⚠ 這條刻意**不寫死比值**——把判準綁在會變的數字上，數字一變讀者就以為判準失效。
- 排序是**研究判斷**，必須明標它不是回測或統計勝率，並附各候選的 disproof。
- 必須點明候選之間的**相關性**：本圖標的高度集中於 AI 光互連，列出 N 檔不等於 N 個獨立
  機會。全買是同一賭注下 N 次，不是分散。

**進場靠判斷，出場靠 disproof。** 反證的用途是決定何時承認判斷錯了，不是進場的前置條件；
混用會產生「永遠不出手、只累積反證」的無效產出。

### 隱含報酬的兩個桿：EPS 與倍數適用同一條原則（2026-09-09 使用者定案）

**沒有 re-rating 證據時，目標倍數預設等於校準用的市場倍數**；任何折價或溢價必須指得出證據並寫進
rationale——這與 ROADMAP「沒有 differentiated evidence 時 EPS 收斂到 consensus 是健康的」是同一條
原則，只是先前沒寫到倍數。**隱含報酬必須拆成兩欄呈現：EPS 差異貢獻、倍數差異貢獻。**
事發（2026-09-08 實測，數字為當時快照）：僅有的兩檔 ready 標的 COHR／LYC.AX 隱含報酬為 −20.7%／
−36.3%，其中倍數折價貢獻約 −16%／−20%，來源是「較市場折價約 17%」這個習慣，不是任何證據。
兩個桿都往保守壓，任何公司都會是負的；30 檔全負時仍分不出「方法偏空」與「市場太貴」。
判準一句話：**一個保守選擇若說不出證據，它是偏差，不是審慎。** 把量拉大只在有這兩欄對照時才有資訊。

### ⚠ 已知會失焦的指標——不得單獨用作瓶頸性證據

- **`evidence` 等級**：最高級必須靠研究找到客戶端文件才拿得到，它是**研究深度的函數**。
- **同一 chokepoint 的供應商計數**：反映的是**我們研究了幾家**，不是世界上有幾家。
- **`documents` 計數**：`bottleneck.py` 已排除，否則分數會變成「我們讀了幾份文件」。

**判別法：這個指標會隨我們多讀一份文件而單調上升嗎？** 會 → 它測的是研究量。

**首選＝filter 不是分數（2026-09-15 使用者定案 D2）。** 籃子頁的「現在該加碼哪一檔」在排序權威的順序上套三條可機械驗證的條件
（有賭注、payoff 為正、至少一條指名假設的催化劑落在目標價日期之前），INV-3 逐檔報 input／accepted／filtered／reasons；
沒有一檔通過就沒有首選，**不得為了讓籃子非空而放寬條件**——讓它非空的路是研究（寫賭注與催化劑）。
**唯一排序權威是 `query/bottleneck.py::rank_bottlenecks()`。** alpha 排序必須**消費**它，
不得重算結構分，也不得繞過它自建第二套結構評分。（`axis_ceiling`／paper target 曾被誤當
排序代理，它們是資本閘門不是選股判準；`research_status` 是研究完整度，也不得拿來排序。）

## Beta 呈現契約：只回答「距目標多遠」與「現在在什麼水位」

使用者的實際行為是定期投入而非擇時，每次真正要決定的只有「這次投哪一檔」。
**呈現層不得以任何名義復刻擇時語言**（今天是否投入、本輪上限、節奏、可評估／暫停新增）。

- **目標配置比例的 `band` 是容忍區間不是 gate**——落在區間內即視為到位、沒有偏好。
  **再平衡只用新投入的錢往低於目標的格子補，不賣出**；此表只給差距，**不給金額、
  不排名、不產生部位尺寸**。貸款 tranche 不適用配置建議。
- **相對水位只呈現、不參與排序、不換算金額**，且必須寫明「長期上漲的標的多數時間落在
  高位是正確資訊，不是該等回檔的訊號」（2026-07-31 回測：等回檔對 30 年終值是負貢獻）。
  **一旦有人拿它排序或調整尺寸，它就變回訊號。**
- **燈號只表達行情資料狀態，不表達投入建議。** 舊語意（可評估／冷卻／暫停新增）
  已於 2026-08-29 明文**廢止**——安靜消失擋不住下次回填，所以廢止必須寫出來。
- **逐檔行情表與目標配置表住 APP（2026-09-08 使用者定案）。** 兩者由每日 materialize 更新、
  在 `#/beta` 隨時可看；**Daily 只印門檻跨越與狀態翻轉**（sleeve 進出容忍區間、某檔行情降級、
  風控門檻被跨過）。
  ⚠ **舊規則「即使沒有配置缺口，逐檔表仍不得省略」到此廢止**——它成立的前提是「Daily 是唯一
  會更新的 surface」，而 APP 每天被 materialize 之後那個前提不再成立。**廢止必須寫出來：
  安靜消失擋不住下次回填。**
  ⚠ **不變的是 invariant 本身：逐檔心跳必須永遠看得到，每列明示商品自身的最新完整交易日。**
  改的是它住在哪裡，不是它可不可以消失。**APP 當天沒被 materialize 時，Daily 必須把這件事印出來**
  ——否則「看不到」與「沒發生」又同形了（L12）。
- **兩條相關性警告改由 APP 常駐呈現**（每個畫面的頁尾），不再要求 Daily 每天複述。
  內容一字不改：（a）**alpha 與 beta 是同一個賭注**——兩個 sleeve 的目標比例分開寫**不代表**
  它們是兩個獨立風險來源；（b）**TSMC look-through 約 28%**，高於 `issuer_concentration_warning`
  0.25，且系統算不出精確值（`issuer_loads` 覆蓋恆為 `partial`）。
  ⚠ 這不是放寬：「每天講一次」變成「每次看都看得到」，後者不依賴使用者當天有沒有讀 brief。

呈現細節（欄位、燈號文字、台股 freshness、槓桿商品序列）見
[`ARCHITECTURE.md`](docs/ARCHITECTURE.md) §8。

## APP 呈現契約：**LLM changes cognition; APP reads cognition**（2026-09-07 Step 5 定案）

**APP 讀的是已經形成的判讀，不是在點擊時形成判讀。** HTTP request path **不得**：跑 LLM、
寫任何 authority、抓外部資料（現價／共識）、跑任何金融模型、重算隱含報酬、或因為 cache miss／stale
就偷偷重建。要更新判讀只有一條路：明確跑一次 materialize。
**這不是效能考量**——一旦 request path 有能力重建，它就有能力改變（或看起來改變）系統對一家公司的
認知，而「使用者剛才看到的是哪一版判斷」就再也答不出來。查證：
`python -m pytest tests/test_webapp_request_path.py`（四種互相獨立的證明）。

**首屏的單位是「句」不是「格」（2026-09-15 使用者定案）。** 個股頁第一屏只有投資人短評：七格前因後果
（什麼在放量／這家公司供什麼／為什麼卡在它／市場怎麼看／我們賭什麼／對了或錯了會怎樣／什麼時候知道）
＋一把尺（現價／沒賭對／賭對）＋一顆狀態燈；第二層是**論證**（六段分析師報告體：這條鏈怎麼走／數字怎麼算出來／
和市場差在哪／賭注／風險與認錯條件／時間表，可長文、直接攤開，段後附研究時寫的長文與圖裡的 claim 引文）；
**第三層才是格**（稽核區，一個展開，明標「給查核用，不是給你讀的」）。判準一句話（2026-09-15 使用者定案，Z3）：
**消費層的單位是句與段；格只住稽核層。** 算術與圖的敘述由封閉句型組（`alpha/narrative/argument.py`），判斷的長文逐字
照抄 session 寫的；「跳」「邊」「sub=5」「tier」這類詞不進論證層，只講「誰說的、有沒有別人印證」。三條不可退讓：
**文字由研究 session 寫進 append-only ledger（`alpha/narrative`）、數字由 authority 填 placeholder、
首屏禁字表（session_judgment、隱含報酬、sole_source 之類的內部名詞）型別層拒收。** 沒寫短評印「還沒寫短評」，
不拿 thesis 硬截——那些句子是分析師欄位。事發：V0 賭注上線後首屏約 30 個數字，使用者原話「一堆數字跟內部名詞
堆起來的東西根本看不懂」。查證：`python -m alpha brief COHR --list`。

**缺席不得被壓成一句「無資料」。** `absence_kind` 是與 `status` 正交的封閉字彙
（`alpha/absence.py`），由**產生缺席的那段程式自己宣告**；呈現層一律不得 parse 理由句去猜（L16）。
使用者必須分得出四件事：**還沒做**（去研究）／**刻意不主張**（這已經是答案，不用動作）／
**方法不適用**（補資料解不掉）／**上游缺料**（要補的是上游）。

⚠ **「刻意不主張」只能來自 append-only 的 `Abstention` 紀錄，不能在呈現層打一個標籤。**
它必須同時說出 `reason` 與 `revisit_when`（什麼證據出現才會改寫，L7），且**結構上不可能攜帶數字**。
宣告之後 fair value 仍然缺席、readiness 仍然 `blocked`——**settled 不讓 readiness 變好**，
它只回答「該不該花力氣去補」。

**`accounting_basis` 的面向使用者標籤不得宣稱 authority 沒有的東西。** 系統記錄的區別只有
「as reported（法定財報）vs 公司調整後」；它**沒有**任何欄位知道那是 US GAAP、IFRS、AASB 還是日本基準
（Lynas／HDS／IQE 在 ledger 裡全都寫 `gaap`）。**字彙不改**（它是三本 private ledger 每筆紀錄身分的一部分，
L10），改的是呈現別名，且 label 一律不含準則名稱。

**Daily 與 APP 的分工（2026-09-08 使用者定案）：** 判準一句話——**昨天和今天一樣的住 APP，
今天變了的＋要你決定的住 Daily**。所以 pq2 的**核准**留在 Daily（核准的載體是對話，APP 沒有寫入
端點）；瓶頸排序、資產配置、研究缺口、事件監看住 APP，Daily 只印它們的計數與變動。
**修正（2026-09-09 使用者定案）：「球在誰手上」的清單是持久狀態，也住 APP**——唯讀，固定四段：
卡在你／系統在做／在等世界／已完成待關，編號照印但不可操作；分段依據是 blocker registry 的
`resolution_mode` 與 dispatch 狀態，不是 pq2 類型。⚠ 09-08 原句「放 APP 只多一次摩擦」到此**廢止**：
唯讀清單不增加摩擦，省掉的是回捲 brief 找編號；安靜消失擋不住下次回填，所以廢止寫出來。
在 `python -m webapp status` 列得出 `queue` kind 之前，Daily 的四段照舊完整印出。⚠ **順序是 invariant：APP 先讀得到，Daily 才能不印。** 反過來做，使用者會打開看到
幾天前的數字，那是 L13（管子只接一頭）的形狀——所以「讓 APP 每天自動更新」必須先於「Daily 收斂」。
⚠ **還沒有 APP 畫面的段落一律留在 Daily**，不得因為「遲早會搬」而先砍。判準是機械的：`python -m webapp status` 列得出那個 kind 才算搬完。

**APP 沒有任何寫入端點，也沒有自己的帳號密碼系統。** 沒有 POST／PUT／PATCH／DELETE 路由；
不下單、不記錄選擇、不改 thesis、不入圖、不核准 pq2。外部認證邊界是 **Cloudflare Access**；
程式預設只綁 `127.0.0.1`，綁其他介面必須明示 `STOCKBOT_APP_ALLOW_PUBLIC_BIND=1`，否則拒絕啟動。
**四個人工 gate 不因為多了一個畫面而放寬。**

## 技術訊號的地位（2026-08-01 實測；2026-08-29 移除；**2026-09-10 拆開 scope**）

**實測記錄（歷史，不因後續移除而改寫，任何改寫都不得刪減它）：** 三次實測全部失敗——
以訊號 gate 現金投入使終值**輸給無腦定投 8.5%**（QQQ 91.5%、SOXX 91.9%）；訊號調節借款
提取**無可測得效果**；訊號決定投給哪個標的**輸給固定單押最佳標的 22%**，且三分之一時間
買進 CAGR 僅 7.2% 的弱標的——**「買跌最深的」會系統性把錢導向長期較弱的資產**。
`stretched_above_sma200` 同為未實測的推論。完整證據見
[`2026-07-31-leverage-glide-path-requirements.md`](docs/brainstorms/2026-07-31-leverage-glide-path-requirements.md)。

**⚠ 那三次測的是什麼（2026-09-10 使用者定案後補；上一段一字未刪）：** 三次的 scope
**全部是 beta sleeve 的定投擇時**——gate 自有現金投入、調節借款提取、在 QQQ／SOXX／EFA
之間選標的。**沒有一次測過 alpha 個股的進出場時機。** 而原本推出的禁令是全域的，
於是它攔的範圍大於它被驗證的範圍——那正是 L15-1 說的「這個 gate 攔下的不是它想攔的東西」。
強度也不齊：唯一做了 rolling start 的是測試二（88 個起點×20 年，看中位數與 5th pct），
結論是**無效果**；「有害 −8.5%」來自**單一路徑**，而該文件的「回測方法論約束」自己就寫著
「本輪多數測試為單一路徑。要據以調參數應先做 rolling start 看分布」。

**beta 定投擇時這條路已關，不是降級使用（commit `6aa31de`）。** RSI／MACD／`sma_50_slope`／
tier／pace／`campaign_budget_fraction_by_sleeve`／三態系統動作／「本輪可評估上限」這個概念
在 **beta sleeve** 全部拔除。**這些字彙不得以任何名義回到 beta 的文件或輸出**——包括改名成
「熱度」「節奏」，或借用「水位」之名讓動能指標重新參與 beta 的排序／尺寸。
查證：`python -c "import json;print(sorted(json.load(open('config/beta_policy.json'))))"`
不應出現 `signal`。

**其餘 scope 適用通則，不是封殺（2026-09-10 使用者定案）：** 未經量測的指標**不得參與任何
排序或尺寸決定**（＝INV-5／L14，本來就適用），但**可以被提出、被測**。要引進一個指標，
四個條件缺一不可：

1. **宣告 scenario**，且**不得跨 scenario 借用結論**——兩個方向都不行：beta 定投擇時的
   舊結論不能封殺 alpha 進場時機的新用途，alpha 的新結果也不能拿去翻案 beta 那三次。
2. **先量測，後放閘**（L14-3）。順序顛倒 ＝ 拆煞車不裝儀表板。
3. 過 L14-4 的三個**免 outcome** 測試：恆亮？不會滅？講不出因果機制？
4. 驗收寫成「**現有資料有幾筆真的變了**」，答案 0 就不算完成。

⚠ **前置條件是 outcome 追蹤：樣本太少時，任何指標的驗證都只會得到比 2026-07-31 更弱的結論。**
⚠ **這裡有兩個數字，不要混用**（2026-09-11 更正——前一版只給了後者，而它低估了實況）：

- **等權報酬追蹤**（現行 SSOT，`AGENTS.md`「outcome 量測改為等權重報酬追蹤」講的就是它）：
  `python -c "import json;print(json.load(open('library/private/decision_lab/outcome_aggregate.json')))"`
  時序在同目錄的 `.jsonl`（2026-09-11 起累積；**在那之前只有當天一個快照，覆寫制**）。
- **`measured_outcomes`**（Decision Store 的 `outcome_envelopes`，正式結算的決策）：
  `python -c "import json;print(json.load(open('library/private/app/state/positions.json'))['counters'])"`
  它衡量的是**另一件事**（人工 close 過幾筆），不是追蹤廣度。

判準一句話：**問「追蹤了幾檔、跑了多久」看等權那組；問「正式結算過幾筆」看 `measured_outcomes`。**

⚠ **一條該保留的機制性警告（與 scope 無關）：** 測試三的歸因是機制性的，不只是單一路徑的
運氣——**「買跌最深的」會系統性把錢導向長期較弱的資產**（EFA CAGR 7.2%，被選了 98 次）。
在 alpha 上更危險：本圖標的高度集中於 AI 光互連，同漲同跌，「哪檔跌最深」很可能只是
「哪檔 beta 最高」。

**須區分量測、訊號與脈絡：** 總曝險倍數、歸零門檻、追繳門檻、利息覆蓋屬**量測**，
有價值且應強化；RSI／MACD／tier／pace 屬**訊號**，**在 beta 定投擇時**三次受測皆未通過
（其他 scenario 是未測，不是已否決——兩者不同）。
位置指標是**呈現用的脈絡**——既不是量測也不是訊號，它不決定任何金額、不參與任何排序；
**一旦有人拿它排序或調整尺寸，它就變回訊號**，適用同一條實測紀律。

---

