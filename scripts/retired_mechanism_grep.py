"""退役機制的殭屍 grep（ROADMAP Phase 0 驗收；2026-09-22）。

**不是 linter、不進 CI 或 hook**（L16-4）：Phase 0 結案時跑一次，之後每季跑一次。
八組 regex（A～H）對應 ROADMAP「Phase 0 退役清單」；驗收＝code／static／skills／tests／config 全部命中 0。
第九組 I（遠端 Graph MCP，2026-09-25 Phase 2 Step 2.1）掃**所有 tracked 檔**（`git ls-files`，含每一個 .md），
keep-list 只准 historical_record；A～H 的驗收範圍維持 Phase 0 的定義不動（改它等於事後改 Phase 0 的驗收）。
排除 docs/archive、docs/lessons-incidents.md、library/。`livedocs`（OPERATIONS／ARCHITECTURE／CONCEPTS）的命中要在 STEP_RESULT 逐句列出，
禁止句（「不做 X」「X 已退役」）可留；`docs` 那一列只供參考，不計入驗收。

    python scripts/retired_mechanism_grep.py
"""
import os,re,io,collections
AREAS={'code':['alpha','briefing','webapp','engine_b','engine_c','decision_lab','thesis','query','crons','scripts','shared','portfolio','risk','loader','identity','audit'],
       'skills':['skills'],'tests':['tests'],'docs':['docs','CONCEPTS.md','README.md'],'config':['config','.codex','.claude/settings.json','.agents'],'static':['webapp/static'],
       'livedocs':['docs/OPERATIONS.md','docs/ARCHITECTURE.md','CONCEPTS.md']}
GROUPS={
 'A 排序當驅動／首選':r'rank_bottlenecks|top_pick|首選|可行動排序|actionable_rows|structural_rows',
 'B 籃子 filter':r'basket|籃子|FILTER_REASONS|payoff_not_positive|market_cap_above_max|analyst_count_above_max',
 'C 估值／隱含報酬／尺':r'implied_return|future_target|sell_side_target|target_reached|q4_implied_return|q7_payoff|隱含報酬|market_implied_eps|required_eps|目標倍數|calibrat',
 'D 多年反向橋／要幾倍':r'alpha\.reverse|from \.reverse|build_reverse_bridge|multi_year|multiple_horizon|要幾倍|倍率射程|要翻倍需要什麼為真|RETURN_MULTIPLE_LADDER',
 'E 賭注四價／variant overlay':r'variant\.overlay|variant_overlay|payoff\b|沒賭對|賭對了值|判斷錯了值|bet_state',
 'F entry criterion':r'EntryCriterion|entry_criterion|alpha\.entry|from \.entry',
 'G decision_lab 鑄號／reassess':r'decision_lab|decision_review|reassess|DecisionContext|assessment_gap',
 'H 估值模型 valuation/fundamental':r'alpha\.valuation|from \.valuation|alpha\.fundamental|from \.fundamental|FundamentalsSnapshot|ValuationMethod|pe_forward',
}
skip=re.compile(r'(\.venv|__pycache__|\.pytest_cache|\.pytest_tmp|node_modules|docs[\/]archive|library[\/]|retired_mechanism_grep\.py|lessons-incidents\.md)')
def files():
    for area,roots in AREAS.items():
        for r in roots:
            if os.path.isfile(r): yield area,r; continue
            for dp,dn,fn in os.walk(r):
                if skip.search(dp): continue
                for f in fn:
                    fp=os.path.join(dp,f)
                    if skip.search(fp): continue
                    if f.endswith(('.py','.md','.js','.html','.json','.toml','.txt')): yield area,fp
idx=collections.defaultdict(lambda:collections.defaultdict(dict))
for area,p in files():
    if area=='code' and p.startswith('webapp'+os.sep+'static'): area='static'
    try: t=io.open(p,encoding='utf-8',errors='ignore').read()
    except: continue
    for g,pat in GROUPS.items():
        n=len(re.findall(pat,t))
        if n: idx[g][area][p]=n
#: keep-list：合法提及的白名單，鍵是（檔案 posix 路徑, 組字母），值是「類別: 一句理由」。
#: 類別是封閉字彙（五類）；驗收數字＝「命中但不在本表的（檔，組）數」；本表本身會腐壞，所以同時印「已列但不再命中」。
#: 由執行 Phase 0 的人逐條填，結案 R2 逐條審理由。範例：
#:   ("decision_lab/store.py","G"): "kept_file: 舊 Decision Store 凍結唯讀，檔名本身命中；寫入方法無呼叫端（grep record_live_choice( 呼叫端＝0）",
#:   ("engine_b/todo.py","G"): "legacy_key: decision_review 是 legacy 封閉字彙 key，池裡歷史項目仍是此 type，讀取要認得；producer 已刪",
KEEP_CLASSES=frozenset({"kept_file","legacy_key","retirement_note","boundary_sentence","guard_assertion"})
KEEP: dict[tuple[str,str],str] = {
    # ---- A 排序當驅動／首選（0b.3 結案時填；跨檔排序已退役，剩下的是註記、禁止句、資料與守門斷言）----
    ("query/bottleneck.py","A"): "retirement_note: 檔頭與 structure_table docstring 寫明 rank_bottlenecks 退役且名稱不留 alias；STRUCTURE_TABLE_TITLE 是禁止句「不排序、不設門檻、不給首選」",
    ("alpha/providers/graph_neo4j.py","A"): "retirement_note: 檔頭／_bottleneck_rows／counter_paths 三處寫明上游由 rank_bottlenecks 改 structure_table",
    ("alpha/closure.py","A"): "retirement_note: BacklogRow.has_structure_edge 註記寫明前身是可行動排序名次",
    ("briefing/alpha_view/builder.py","A"): "retirement_note: 結構段拿掉「可行動排序名次」兩格的註記",
    ("briefing/alpha_view/contracts.py","A"): "retirement_note: StructuralThesisSection.ranking 退役註記",
    ("briefing/alpha_view/sources.py","A"): "retirement_note: _ranking_position／tickers_from_ranking 退役註記",
    ("crons/heartbeat.py","A"): "retirement_note: 段 4 需求錨集中度改讀 structure_table 的註記（原讀可行動排序列）",
    ("engine_b/cli.py","A"): "retirement_note: _chokepoint 註記寫明前身 rank_bottlenecks，且明寫「不是任何排序或首選」",
    ("scripts/capture_golden_fixtures.py","A"): "retirement_note: cap_structural_bottleneck 註記寫明原本擷取可行動排序前三名",
    ("webapp/materialize.py","A"): "retirement_note: structure_table 區塊註記寫明原 ranking kind 的首選／兩份序；THIS_IS_NOT 第一句是禁止句",
    ("webapp/contracts.py","A"): "retirement_note: STATE_SCHEMA_VERSIONS 註記 ranking → structure_table",
    ("webapp/api.py","A"): "boundary_sentence: meta not_offered／group_note 寫明跨檔排序與首選已退役；handler docstring「沒有首選」",
    ("webapp/__main__.py","A"): "boundary_sentence: --structure-table 的 help「不排序、沒有首選」",
    ("webapp/static/app.js","A"): "retirement_note: 結構表區塊檔頭註記寫明原本是首選／兩份序／產業分組",
    ("skills/alpha-status/SKILL.md","A"): "boundary_sentence: 「不輸出跨檔全序、不輸出首選」「不得宣稱那是優先序」與 2026-09-22 退役註記",
    ("skills/daily-brief/SKILL.md","A"): "boundary_sentence: 「不印首選、不印名次」「首選換人已不是變動項」「排序不再是任何佇列或頁面的輸入」",
    ("skills/system-decompose/SKILL.md","A"): "boundary_sentence: 分工表「結構表；不排序、無首選」",
    (".agents/skills/alpha-status/SKILL.md","A"): "boundary_sentence: 由 skills/alpha-status 同步產生的 description（sync_agent_skills.py）",
    ("config/alpha_screen.json","A"): "boundary_sentence: _not_this「跨檔排序已於 2026-09-23 退役」",
    ("thesis/lifecycle.json","A"): "legacy_key: append-only thesis lifecycle ledger 的歷史 rationale 與 authority ref（query://bottleneck/rank_bottlenecks@2026-09-21），不得改寫",
    ("tests/fixtures/golden/structural_bottleneck.json","A"): "legacy_key: 2026-08 凍結的 golden input，manifest digest 鎖住；note 是當時的說法，重擷取會報漂移（預期）",
    ("tests/test_structure_table.py","A"): "guard_assertion: 守 markdown 沒有首選／可行動排序／純結構排序、result 沒有 structural_rows",
    ("tests/test_webapp_structure_table.py","A"): "guard_assertion: 守 artifact 與前端沒有 top_pick／structural_rows／actionable_rank",
    ("tests/test_alpha_view_brief.py","A"): "guard_assertion: 斷言 structural_thesis 沒有 ranking 欄位",
    ("tests/test_webapp_api.py","A"): "boundary_sentence: docstring「不得輸出跨檔全序或首選」",
    ("tests/test_daily_brief_skill.py","A"): "retirement_note: 註記寫明 pane 1 由「現在要投哪一檔」改為結構＋候選狀態",
    # ---- B 籃子 filter（籃子 filter 已退役；「籃子」另有 AGENTS 量測用語「籃子總報酬」「主題籃子」，regex 分不開）----
    ("scripts/outcome_if_settled_today.py","B"): "kept_file: positions kind 唯一 producer（plan §0.6 #32）；命中的是 AGENTS 量測三量的「籃子總報酬」，不是籃子 filter",
    ("crons/heartbeat.py","B"): "retirement_note: 段 2／段 4 籃子退役的缺席宣告（not_yet_recorded／upstream_unavailable）；「power-law：籃子總報酬」是 AGENTS 量測用語",
    ("webapp/materialize.py","B"): "retirement_note: materialize_basket 退役註記；positions 的 power_law note 用「籃子總報酬」量測用語",
    ("webapp/contracts.py","B"): "retirement_note: basket kind 退役註記（0a.2）",
    ("webapp/api.py","B"): "retirement_note: /basket 路由退役註記（0a.2）",
    ("webapp/static/app.js","B"): "retirement_note: 結構表區塊註記寫明籃子頁移除；positions 頁「籃子總報酬」量測用語",
    ("alpha/gap_closure.py","B"): "boundary_sentence: 引 AGENTS「籃子總報酬＝最大單檔＋其餘」的量測取捨",
    ("alpha/abstention/contracts.py","B"): "kept_file: ABSTENTION_SUBJECTS 的 bet 字彙是 append-only abstention ledger 的 subject（資料留，L10）；第 49／53 行的籃子註記是歷史消費端的說明，Phase 0 未改寫（R2 2026-09-24 指出，屬註記非機制）",
    ("alpha/providers/market_normalization.py","B"): "retirement_note: 寫明 --basket 與 alpha_screen_check 已退役、Phase 3 候選板接手",
    ("briefing/analyst_view/compose.py","B"): "boundary_sentence: AGENTS 判準句「主題籃子只當脈絡、不設門檻」",
    ("config/alpha_screen.json","B"): "kept_file: 覆蓋厚薄門檻留給 Phase 3 候選板（plan 批 3 明寫留）",
    ("config/sector_anchors.json","B"): "retirement_note: _doc 寫明籃子頁「同一個賭注的群」隨排序退役",
    ("skills/alpha-status/SKILL.md","B"): "boundary_sentence: 「主題籃子只當脈絡、不設門檻」",
    ("skills/daily-brief/SKILL.md","B"): "retirement_note: --basket 移除註記；「基準含主題等權籃子」是 AGENTS 量測用語",
    ("skills/lead-intake/SKILL.md","B"): "boundary_sentence: 「主題籃子只當脈絡、不設門檻」",
    ("tests/test_opinion_stance.py","B"): "kept_file: outcome 腳本 power-law 量測的測試（basket_total_return 是量測鍵）",
    ("tests/test_webapp_positions.py","B"): "kept_file: positions artifact 的 power_law 夾具（basket_total_return 量測鍵）",
    ("tests/test_wipeout_flags.py","B"): "guard_assertion: 斷言心跳段 4 仍印「power-law：籃子總報酬」；其餘是籃子退役註記",
    ("tests/test_heartbeat.py","B"): "retirement_note: 0a.2 籃子退役後換主詞的註記",
    ('tests/test_daily_task.py','G'): 'guard_assertion: 斷言 daily 的封閉步驟清單不含 reassess-stale 等使用者動詞（原守在 Codex prompt／rules，2026-09-24 改主詞）',
    ("tests/test_webapp_coverage_watches.py","B"): "retirement_note: STATE_KINDS 斷言旁的 0a.2 退役註記",
    ("tests/test_webapp_structure_table.py","B"): "retirement_note: STATE_KINDS 斷言旁的 0a.2 退役註記",
    ("tests/test_absence_semantics.py","B"): "retirement_note: 事發紀錄提到籃子的 bet_state（消費端已退役）",
    ("tests/test_market_quote_unit.py","B"): "retirement_note: 事發紀錄用語「本籃子裡」指研究宇宙，非籃子 filter",
    ("tests/test_nav_exposure.py","B"): "kept_file: regex 誤命中——「籃子」在此是 bucket 的普通名詞",
    # ---- C～H 組（0b.4 3/3 結案時填；C 估值鏈、D 多年橋、E 四價、F entry、G decision_lab、H 估值模型）----
    ('alpha/abstention/contracts.py','C'): 'boundary_sentence: 估值層 abstention 的「不是第二份 ValuationAssumption authority」「隱含倍數錨不住目標倍數」是禁止句，字彙留作 append-only 紀錄的 subject（L10）',
    ('alpha/cli.py','C'): 'legacy_key: `alpha assumptions --add` 的 spec 欄位 calibration_refs（假設 ledger 的 ref 角色，活的 ledger 邏輯，plan §0.6 #28）',
    ('alpha/closure.py','C'): 'retirement_note: score_quality／render_quality（隱含報酬正負分布等三個估值品質數）退役註記（0b.1b-C/H 1/2）',
    ('alpha/fundamental/assumptions.py','C'): 'kept_file: 假設 ledger 解析／選取（plan §0.6 #28 留）；calibration_refs 是 ledger 的 ref 角色欄位',
    ('alpha/fundamental/contracts.py','C'): 'kept_file: 資料契約（plan §0.6 #28 留）；ASSUMPTION_REF_ROLES 的 calibration 是 ledger 封閉字彙',
    ('alpha/gap_closure.py','C'): 'retirement_note: target_reached 隨估值鏈退役的註記（V2 市場承認量測本身留）',
    ('alpha/models/session_assessor.py','C'): 'legacy_key: 短評 placeholder {sell_side_target}（賣方目標價均值，A2 觀測）留在封閉字彙（plan §0.6 #26）',
    ('alpha/narrative/contracts.py','C'): 'legacy_key: 短評 placeholder 字彙（sell_side_target 照填、其餘印「尚無」）與首屏禁字表（「隱含報酬」是禁字），plan §0.6 #26',
    ('alpha/providers/assumptions.py','C'): 'retirement_note: 註解記 2026-09 overlay scope 事故時的假隱含報酬數字（歷史事發，不是機制）',
    ('alpha/refresh/artifacts.py','C'): 'retirement_note: artifacts_from_valuation／_implied_return 刪除註記；ROLE_CALIBRATION 是假設 ref 角色（活）；market_implied_eps_growth artifact 留（plan §0.6 #30）',
    ('alpha/refresh/contracts.py','C'): 'legacy_key: ARTIFACT_IMPLIED_RETURN／ROLE_CALIBRATION 是 refresh 字彙常數，既有 refresh state 紀錄引用（plan §0.6 #30「refresh 字彙常數」）',
    ('alpha/refresh/policy.py','C'): 'legacy_key: refresh policy 表仍列 implied_return 的依賴（字彙常數保留以讀舊 refresh 紀錄，plan §0.6 #30）',
    ('alpha/refresh/resolver.py','C'): 'legacy_key: 假設 ref 角色 calibration 的 resolver 訊息（活的 ledger 邏輯）',
    ('briefing/alpha_view/builder.py','C'): 'retirement_note: 六個估值 section 與 _implied_return_section 的退役註記（0b.1b-C/H 2/2）',
    ('briefing/alpha_view/contracts.py','C'): 'retirement_note: CAP_*／ImpliedReturnSection／multiple_derivation 退役註記',
    ('briefing/alpha_view/render.py','C'): 'retirement_note: render_implied_return_lines 與兩個子命令退役註記',
    ('briefing/alpha_view/sources.py','C'): 'retirement_note: _implied_return_model 等取數退役註記',
    ('briefing/analyst_view/compose.py','C'): 'retirement_note: headline 那把尺（現價 → future target → 隱含報酬）退役註記；「沒有目標價、沒有隱含報酬」是禁止句',
    ('briefing/analyst_view/contracts.py','C'): 'retirement_note: q4_implied_return／q7_payoff／headline_context 退役註記；hint「這裡沒有目標價、沒有隱含報酬」是禁止句',
    ('briefing/cli.py','C'): 'retirement_note: cmd_valuation／cmd_implied_return 子命令退役註記',
    ('config/engine_c_observation_fields.json','C'): 'retirement_note: fx_rate 欄位 why 的歷史脈絡（原 alpha/valuation units_comparable；已標「估值鏈已退役」）',
    ('crons/heartbeat.py','C'): 'retirement_note: 目標倍數背離計數器退役、FX 兩行主詞改「換算依據過期」的註記（plan §0.6 #20）',
    ('scripts/realign_assumption_refs.py','C'): 'kept_file: 假設 ledger 的 ref 對齊工具，calibration 是 ref 角色',
    ('scripts/sync_fx_observations.py','C'): 'retirement_note: docstring 記 2026-09-19 事發時「隱含報酬印不出來」（歷史事發數字）',
    ('scripts/verify_test_nonvacuity.py','C'): 'retirement_note: 指向 alpha/valuation 等退役模組的突變已移除的註記',
    ('skills/alpha-status/SKILL.md','C'): 'retirement_note: 估值／隱含報酬「刻意不再有」的退役註記',
    ('skills/research-drain/SKILL.md','C'): 'retirement_note: closure-gate 三個估值品質數退役註記',
    ('tests/test_alpha_investment_view.py','C'): 'guard_assertion: 斷言 implied_return／valuation 等 section 不得回來',
    ('tests/test_alpha_view_fundamental.py','C'): 'guard_assertion: 斷言退役 section 鍵不在 view',
    ('tests/test_alpha_view_refresh.py','C'): 'legacy_key: refresh 測試用 market_implied_eps_growth artifact（plan §0.6 #30 留的 proxy）',
    ('tests/test_analyst_view.py','C'): 'guard_assertion: 斷言 consumer 不 import 估值模組、不含 build_valuation 等 token、q4／q7 不在問句',
    ('tests/test_closure.py','C'): 'retirement_note: 五條估值品質測試退役註記',
    ('tests/test_full_chain_acceptance.py','C'): 'guard_assertion: 斷言估值鏈四組數字退役後不再出現；檔頭是退役註記',
    ('tests/test_fx_sync.py','C'): 'retirement_note: docstring 記事發（隱含報酬印不出來）',
    ('tests/test_gap_closure.py','C'): 'retirement_note: target_reached 退役註記，gap_closure 量測留',
    ('tests/test_heartbeat.py','C'): 'boundary_sentence: 「跨幣別標的會失去隱含報酬——這件事必須每天自己說話」是心跳 FX 缺席宣告的判準（主詞已改換算依據）',
    ('tests/test_investor_brief.py','C'): 'legacy_key: 短評 placeholder 夾具（sell_side_target 照填）與禁字表測試（「隱含報酬」是禁字）',
    ('tests/test_opinion_stance.py','C'): 'retirement_note: 檔頭記 2026-09-10 事發（隱含報酬 ±0.01%），活的斷言守 overlay ledger 閘門',
    ('tests/test_overlay_scope_gate.py','C'): 'retirement_note: docstring 記事發時的假隱含報酬數字',
    ('tests/test_refresh_engine.py','C'): 'legacy_key: 假設 ref 角色 calibration 與 market_implied_eps_growth artifact 的 refresh 測試',
    ('tests/test_thesis_realized.py','C'): 'guard_assertion: 守「repo 裡不得有程式把 status 寫成 realized」；target_reached 只是註記',
    ('tests/test_webapp_api.py','C'): 'guard_assertion: 斷言 future_target／implied_return 等鍵不得回到 overview',
    ('tests/test_webapp_materialize.py','C'): 'guard_assertion: 斷言退役鍵不得回到 artifact；夾具含歷史 headline 形狀',
    ('tests/test_webapp_request_path.py','C'): 'guard_assertion: request path 不得 import alpha.valuation.model 等退役模組',
    ('thesis/lifecycle.json','C'): 'legacy_key: thesis 複查 rationale 逐字（append-only 資料，內含「校準」字樣）',
    ('webapp/__main__.py','C'): 'retirement_note: quality 前五個鍵退役註記',
    ('webapp/materialize.py','C'): 'retirement_note: overview 五個鍵（future_target／implied_return／payoff／sell_side_target／target_reached）退役註記',
    ('webapp/static/app.js','C'): 'retirement_note: stance／appendReturnBlock／兩格退役註記',
    ('alpha/contracts.py','D'): 'retirement_note: multiple_horizon 退役註記（判斷檔資料留，plan §0.6 #31）',
    ('alpha/models/session_assessor.py','D'): 'retirement_note: multiple_horizon 隨多年反向橋退役註記',
    ('briefing/alpha_view/contracts.py','D'): 'retirement_note: 倍率射程「刻意不印」註記',
    ('briefing/alpha_view/render.py','D'): 'retirement_note: 倍率射程那一句的歷史註記',
    ('briefing/alpha_view/sources.py','D'): 'retirement_note: 多年視角整組退役註記',
    ('briefing/analyst_view/compose.py','D'): 'retirement_note: 「要翻倍需要什麼為真」那一句退役註記',
    ('briefing/cli.py','D'): 'retirement_note: cmd_multi_year 子命令退役註記',
    ('crons/heartbeat.py','D'): 'retirement_note: 段 4「要幾倍」明示缺席宣告（not_yet_recorded，五段永遠出現）',
    ('tests/test_investor_brief.py','D'): 'retirement_note: multiple_question 退役註記',
    ('tests/test_webapp_coverage_watches.py','D'): 'guard_assertion: kind 數 9 → 7 的封閉字彙相等斷言',
    ('tests/test_webapp_structure_table.py','D'): 'guard_assertion: kind 數 9 → 7 的封閉字彙相等斷言',
    ('webapp/contracts.py','D'): 'retirement_note: multi_year kind 從封閉字彙 de-register 的註記',
    ('webapp/materialize.py','D'): 'retirement_note: materialize_multi_year 移除註記',
    ('webapp/static/app.js','D'): 'retirement_note: 首屏「要翻倍需要什麼為真」計算框退役註記',
    ('alpha/abstention/contracts.py','E'): 'legacy_key: ABSTENTION_SUBJECTS 的 bet/variant.overlay、downside.overlay 是 append-only abstention ledger 的 subject 字彙（資料留，L10）',
    ('alpha/evidence_quality.py','E'): 'retirement_note: docstring 對照舊五軸（valuation_payoff）與新五 score 的說明',
    ('alpha/fundamental/contracts.py','E'): 'legacy_key: ASSUMPTION_SCENARIOS（variant／downside）是 overlay 假設紀錄的型別驗證字彙（plan §0.6 #22）',
    ('alpha/legacy_axes.py','E'): 'legacy_key: 舊五軸 → 新五 score 的轉換表（valuation_payoff → expectation_gap），讀凍結 decision payload 用',
    ('alpha/models/session_assessor.py','E'): 'legacy_key: 短評 placeholder {payoff}／{bet_target} 留在封閉字彙（印「尚無」，plan §0.6 #26）',
    ('alpha/narrative/contracts.py','E'): 'legacy_key: 短評七格的 placeholder 字彙含 {payoff}（append-only 短評紀錄引用，plan §0.6 #26）',
    ('briefing/alpha_view/builder.py','E'): 'retirement_note: 四價 overlay 退役、bet/variant.overlay ledger 資料留的註記',
    ('briefing/alpha_view/contracts.py','E'): 'boundary_sentence: wipeout 面板與「判斷錯了值多少」的分界句（歸零 vs thesis 錯）',
    ('briefing/alpha_view/render.py','E'): 'retirement_note: 13b「判斷錯了值多少」整節退役註記',
    ('briefing/alpha_view/sources.py','E'): 'retirement_note: 估值鏈再跑兩次（variant／downside）退役註記',
    ('briefing/analyst_view/compose.py','E'): 'retirement_note: 那把尺（現價／沒賭對／賭對／判斷錯了）退役註記；反證那一端沒退役的分界句',
    ('briefing/analyst_view/contracts.py','E'): 'retirement_note: q7_payoff 與 downside 四價渲染退役註記；panel 留',
    ('config/decision_blockers.json','E'): 'legacy_key: assessment_context_mismatch:valuation_payoff 與 market_stale 的歷史 next_step（五軸退役，碼只在凍結 payload 出現）',
    ('config/engine_c_observation_fields.json','E'): 'retirement_note: _authority_contract 標明五軸（valuation_payoff）已退役、對照留作歷史說明',
    ('scripts/capture_alpha_fixtures.py','E'): 'legacy_key: 舊軸 → score 對照（valuation_payoff → expectation_gap）供擷取歷史夾具',
    ('shared/assessment_axes.py','E'): 'legacy_key: 舊五軸 AXES 字彙（valuation_payoff）——已凍進所有既有 decision payload，讀歷史要認得',
    ('skills/alpha-status/SKILL.md','E'): 'boundary_sentence: AGENTS「系統只負責…賭對了值多少、判斷錯了值多少」的判準句原文',
    ('skills/research-drain/SKILL.md','E'): 'retirement_note: 五軸 authority 對照（valuation_payoff）退役註記',
    ('tests/fixtures/alpha/cohr_alpha_signal.json','E'): 'legacy_key: 凍結夾具（source_axis: valuation_payoff）',
    ('tests/fixtures/alpha/cohr_axis_assessment.json','E'): 'legacy_key: 凍結夾具（舊五軸 assessment）',
    ('tests/fixtures/decision_lab/empty_graph_company.json','E'): 'legacy_key: 凍結夾具（舊五軸）',
    ('tests/fixtures/decision_lab/sive_reference_design.json','E'): 'legacy_key: 凍結夾具（舊五軸）',
    ('tests/test_absence_semantics.py','E'): 'guard_assertion: ABSTENTION_SUBJECTS["bet"] 封閉字彙相等斷言（variant.overlay／downside.overlay 是 ledger subject）',
    ('tests/test_alpha_legacy_conversion.py','E'): 'legacy_key: 舊軸 → 新 score 轉換測試（valuation_payoff）',
    ('tests/test_analyst_view.py','E'): 'guard_assertion: 斷言 q7_payoff 不在 consumer 問句',
    ('tests/test_decision_blockers.py','E'): 'legacy_key: registry 前綴比對測試用 assessment_context_mismatch:valuation_payoff（歷史碼）',
    ('tests/test_investor_brief.py','E'): 'legacy_key: 短評 placeholder 夾具（{payoff} 印值或「尚無」）',
    ('tests/test_webapp_api.py','E'): 'guard_assertion: 斷言 payoff 鍵不得回到 overview',
    ('tests/test_webapp_materialize.py','E'): 'guard_assertion: 斷言 payoff 鍵不得回到 artifact',
    ('thesis/axt_inp_v1_lane_memo.md','E'): 'legacy_key: lane memo 逐字（append-only 資料）提到 bet/variant.overlay 的 Abstention 終局',
    ('thesis/lifecycle.json','E'): 'legacy_key: thesis lifecycle note 逐字（append-only 資料）',
    ('webapp/__main__.py','E'): 'retirement_note: overview.payoff 退役、「有賭注」改數 our_bet 的註記',
    ('webapp/api.py','E'): 'retirement_note: overview.payoff 退役註記',
    ('webapp/materialize.py','E'): 'retirement_note: 那把尺兩端（payoff）退役註記',
    ('webapp/static/app.js','E'): 'retirement_note: 卡片「沒賭對／賭注對了」兩格退役註記',
    ('alpha/cli.py','F'): 'retirement_note: cmd_entry_criterion 子命令退役註記（ledger 檔案留）',
    ('alpha/refresh/contracts.py','F'): 'legacy_key: ENTRY_CRITERION change class／artifact 字彙常數（既有 refresh 紀錄引用，plan §0.6 #30）',
    ('briefing/alpha_view/builder.py','F'): 'retirement_note: 註解記原本由 alpha.implied_return／alpha.entry 組裝',
    ('scripts/verify_test_nonvacuity.py','F'): 'retirement_note: 突變條目的 guards 句仍寫「EntryCriterion 不是 gate」（該突變指向活的 readiness 測試）',
    ('tests/test_webapp_request_path.py','F'): 'retirement_note: alpha.entry.model 從禁 import 清單移除的註記',
    ('alpha/__init__.py','G'): 'boundary_sentence: alpha/ 不 import decision_lab.store 的邊界句',
    ('alpha/catalyst.py','G'): 'kept_file: 呼叫端注入 decision_lab.coverage_queries.latest_coverage_assessments（凍結歷史的唯讀 SQL）',
    ('alpha/cli.py','G'): 'retirement_note: docstring 對照已退役的 decision_lab assessment-scaffold → reassess 流程',
    ('alpha/contracts.py','G'): 'boundary_sentence: ResearchContext ≠ DecisionContext 兩者不得合併',
    ('alpha/models/session_assessor.py','G'): 'retirement_note: 檔頭流程圖對照已退役的 decision_lab assessment-scaffold／reassess',
    ('alpha/position_events.py','G'): 'retirement_note: B6 搬家紀錄（原住 decision_lab/alpha_event_monitor.py）',
    ('alpha/refresh/contracts.py','G'): 'legacy_key: REVIEW_REQUIRED 的 required_action 字串「reassess in a session」是 refresh state 字彙（既有紀錄引用）',
    ('audit/__init__.py','G'): 'boundary_sentence: FORBIDDEN_IN_ALPHA 禁 alpha/ 依賴 decision_lab',
    ('audit/checks.py','G'): 'retirement_note: 段 2 reassess 退役註記（0a.1）',
    ('audit/sources.py','G'): 'kept_file: audit 唯讀開舊 Decision Store（decision_lab.bootstrap）做跨層 invariant',
    ('briefing/__init__.py','G'): 'retirement_note: today brief 組裝隨 decision_lab 研究側退役的註記',
    ('briefing/alpha_view/builder.py','G'): 'legacy_key: A_COVERAGE 等 authority 字串 decision_lab://…（read model 的 authority 標籤，指向凍結歷史）',
    ('briefing/alpha_view/contracts.py','G'): 'legacy_key: authority 字串 decision_lab://coverage_assessments 的契約說明；attention 由已退役 today 計算的註記',
    ('briefing/alpha_view/sources.py','G'): 'kept_file: 唯讀 mode=ro 讀 decision_lab.coverage_queries.company_decision_facts（research 面板的 catalyst／disproof／expiry）',
    ('briefing/render.py','G'): 'retirement_note: render_today_markdown 退役註記',
    ('briefing/sources.py','G'): 'kept_file: outcome_aggregate.json 住 library/private/decision_lab/（檔案路徑，量測層 Phase 5 前不動）',
    ('config/authority_tokens.json','G'): 'retirement_note: _history 與 _frozen_mapping_note 記 AXIS_REFERENCE_AUTHORITIES 已隨五軸退役',
    ('config/decision_blockers.json','G'): 'legacy_key: blocker 碼字彙只服務讀凍結 payload；next_step 已標 reassess 退役',
    ('config/engine_c_observation_fields.json','G'): 'retirement_note: _authority_contract 與 runway why 標明 decision_lab 消費端已退役（derive_runway 搬 shared）',
    ('config/standing_authorization.json','G'): 'legacy_key: decision_review 列在 never（ITEM_TYPES 封閉性要求每種都明寫，0a.1）',
    ('decision_lab/__init__.py','G'): 'kept_file: 舊 Decision Store 的唯讀歷史檔案館（frozen 2026-09-22）',
    ('decision_lab/bootstrap.py','G'): 'kept_file: open_readonly_store（舊店唯讀入口；mode=ro，Phase 1 Step 1.1）',
    ('decision_lab/cli.py','G'): 'kept_file: python -m decision_lab status／history 唯讀窗',
    ('decision_lab/store.py','G'): 'kept_file: 舊 Decision Store 凍結唯讀，檔名本身命中；寫入方法無呼叫端（grep record_live_choice( 呼叫端＝0），record_live_choice 直接拒絕',
    ('engine_b/cli.py','G'): 'retirement_note: drain 的 Decision work order／assessment-gap 退役註記',
    ('engine_b/queue_segments.py','G'): 'retirement_note: 段 2 reassess_stale 退役註記（0a.1）',
    ('engine_b/routine_config.py','G'): 'kept_file: tracked ticker 來源之一唯讀開舊店讀 cohort（frozen 歷史，讀取合法）',
    ('engine_b/disproof.py','G'): 'kept_file: 心跳的「凍結歷史 N（不盯）」以 open_readonly_store（mode=ro）讀舊店 coverage_assessments 的反證家數——只印數，不登記、不盯（Phase 1 定案 #1）',
    ('engine_b/signal_source_registry.py','G'): 'retirement_note: STATUSES 原借自 decision_lab.intake 的註記（現為 SSOT）',
    ('engine_b/todo.py','G'): 'legacy_key: decision_review／sheet_only_holding 是 legacy 封閉字彙 key，池裡歷史項目仍是此 type，go 一律拒絕；producer 已刪',
    ('engine_c/pending_observations.py','G'): 'retirement_note: 檔頭記事發（decision_lab 的 gap research packet）',
    ('identity/authority_tokens.py','G'): 'retirement_note: 檔頭記 token 字彙收斂時 Engine C 與 Decision Lab 兩個消費端的歷史',
    ('portfolio/brief.py','G'): 'retirement_note: build_sheet_only_items 隨研究側退役註記',
    ('risk/hard_caps.py','G'): 'retirement_note: 硬擋前身 decision_lab/store.py::_assert_user_sized_within_capital_caps 的搬家註記',
    ('risk/snapshot.py','G'): 'retirement_note: 為什麼住 risk/ 而不是 decision_lab/sizing.py 的搬遷紀錄',
    ('scripts/backup_private.py','G'): 'kept_file: 備份 library/private/decision_lab/decision_lab.db（檔案路徑）',
    ('scripts/capture_alpha_fixtures.py','G'): 'kept_file: 擷取歷史夾具時唯讀開舊店',
    ('scripts/capture_golden_fixtures.py','G'): 'kept_file: golden fixture 唯讀開舊店',
    ('scripts/catalyst_watch.py','G'): 'kept_file: daily 固定入口，mode=ro 讀 decision_lab.coverage_queries（凍結歷史）',
    ('scripts/daily_beta_snapshot.py','G'): 'kept_file: portfolio_risk_snapshots.jsonl 住 library/private/decision_lab/（檔案路徑）',
    ('scripts/dualrun_axis_conversion.py','G'): 'kept_file: 唯讀 dual-run 分析腳本（舊軸→新 score），只讀舊店',
    ('scripts/migrate_decision_store_v8.py','G'): 'kept_file: 歷史 schema migration（已套用，留作稽核；舊店 schema 不動）',
    ('scripts/migrate_decision_store_v9.py','G'): 'kept_file: 歷史 schema migration（已套用，留作稽核；舊店 schema 不動）',
    ('scripts/outcome_if_settled_today.py','G'): 'kept_file: positions kind 與心跳 power-law 三量的唯一 producer（plan §0.6 #32），唯讀舊店的 live fill 與 outcome',
    ('scripts/repricing_check.py','G'): 'kept_file: 唯讀舊店的判斷日做股價變化分解（plan §0.6 #31）',
    ('scripts/verify_test_nonvacuity.py','G'): 'kept_file: 空跑檢查指向仍存在的 decision_lab/bootstrap.py／store.py／coverage_queries.py 突變',
    ('shared/__init__.py','G'): 'retirement_note: 檔頭記為何從 decision_lab/ 搬到 shared/',
    ('shared/assessment_axes.py','G'): 'retirement_note: 檔頭記軸名三份拷貝的收斂歷史',
    ('shared/buckets.py','G'): 'retirement_note: 檔頭記 decision_lab ↔ portfolio 相依環的歷史',
    ('shared/catalyst_state.py','G'): 'retirement_note: 檔頭記消費端之一是 decision_lab/store.py::_work_order_lifecycle（仍在，唯讀）',
    ('shared/evidence_levels.py','G'): 'retirement_note: 檔頭記與 decision_lab/sizing.py::LEVELS 逐字同步的歷史',
    ('shared/private_export.py','G'): 'kept_file: redacted export 目錄 diagnostics/decision_lab（路徑），port 形狀註記',
    ('shared/runway.py','G'): 'retirement_note: derive_runway 由 decision_lab/context.py 搬來的註記',
    ('skills/alpha-status/SKILL.md','G'): 'retirement_note: decision_lab today 那條路已退役的註記',
    ('skills/daily-brief/SKILL.md','G'): 'retirement_note: decision_lab today／reassess-stale／decision_review go／get_decision_brief 四處退役註記',
    ('skills/investment-research/SKILL.md','G'): 'kept_file: 指向舊店唯讀歷史 python -m decision_lab history／status（活的入口）',
    ('skills/lead-intake/SKILL.md','G'): 'retirement_note: evaluate-signal／reassess 那條路已退役的註記；history／status 是活入口',
    ('skills/research-drain/SKILL.md','G'): 'retirement_note: decision_lab references 退役註記',
    ('tests/test_account_scorecard.py','G'): 'retirement_note: STATUSES 原借自 decision_lab.intake 的註記',
    ('tests/test_alpha_view_as_of_cohr.py','G'): 'kept_file: 需要本機舊店存在才跑的 as-of 整合測試（路徑）',
    ('tests/test_audit_waiting.py','G'): 'guard_assertion: 斷言 audit Lifecycle 不再開舊 Decision Store（凍結資料恆 PASS＝不會滅；Phase 1 Step 1.10）',
    ('tests/test_alpha_view_brief.py','G'): 'kept_file: company_decision_facts 唯讀查詢測試（SQL 夾具直寫 tmp store）',
    ('tests/test_alpha_view_render.py','G'): 'guard_assertion: render 不得 import decision_lab；authority 標籤字串 decision_lab://coverage_assessments',
    ('tests/test_analyst_view.py','G'): 'legacy_key: refresh required_action 字串「reassess in a session」（refresh 字彙）',
    ('tests/test_backup_entrypoint.py','G'): 'kept_file: 備份 zip 成員測試用 decision_lab/decision_lab.db 路徑',
    ('tests/test_config_tracking.py','G'): 'retirement_note: 登記表三列（sizing／workflow／context）搬進已移除段的註記',
    ('tests/test_daily_brief_skill.py','G'): 'guard_assertion: 斷言 decision_review 那條 go 路已退役',
    ('tests/test_decision_store.py','G'): 'kept_file: 舊店 schema／idempotency／private root fail-closed 測試（storage 邊界，store 檔留）',
    ('tests/test_decision_store_readonly.py','G'): 'kept_file: 舊店唯讀入口測試（mode=ro 擋寫、缺席不建庫、不 checkpoint WAL；Phase 1 Step 1.1）',
    ('tests/test_engine_b_cli.py','G'): 'retirement_note: limit=0 測試 docstring 記 Decision work order 退役',
    ('tests/test_engine_b_todo.py','G'): 'guard_assertion: legacy kind 的 go 一律被拒的斷言；夾具改用 manual',
    ('tests/test_engine_c_observation_fields.py','G'): 'retirement_note: 五軸消費端退役、兩條守門斷言退役的註記',
    ('tests/test_engine_c_observation_gate.py','G'): 'retirement_note: 檔頭記事發（decision_lab 的 gap research packet）',
    ('tests/test_full_chain_acceptance.py','G'): 'guard_assertion: consumer 不得 import decision_lab.store 的 IO 禁止清單；skip 條件用舊店路徑',
    ('tests/test_graph_preservation.py','G'): 'guard_assertion: decision_lab 不得有 graph write 能力、source tree 不得 import graph writers',
    ('tests/test_identity_registry.py','G'): 'guard_assertion: decision_lab 不得反向 import identity authority',
    ('tests/test_layer_separation.py','G'): 'guard_assertion: decision_lab 不得 import alpha／portfolio／briefing、上游層不得 import decision_lab、凍結後不得碰 engine_c／fetchers／neo4j',
    ('tests/test_no_llm_api_dependency.py','G'): 'guard_assertion: production 套件（含 decision_lab）不得 import LLM SDK；檔頭記舊流程',
    ('tests/test_opinion_stance.py','G'): 'kept_file: outcome_aggregate.jsonl 住 library/private/decision_lab/（路徑）',
    ('tests/test_private_backup_restore.py','G'): 'kept_file: 備份還原測試（plan 批 4 明列「留且必須綠」）',
    ('tests/test_private_export.py','G'): 'kept_file: redacted export 測試（diagnostics/decision_lab 路徑）',
    ('tests/test_queue_segments.py','G'): 'guard_assertion: 斷言 reassess_stale 段不在封閉字彙、reassess_only 參數已移除',
    ('tests/test_refresh_engine.py','G'): 'guard_assertion: refresh 引擎不得 import decision_lab 等（禁止清單）',
    ('tests/test_skill_decision_contract.py','G'): 'guard_assertion: 斷言 skill 可執行行不含 evaluate-signal／decision_lab reassess 等',
    ('tests/test_standing_authorization.py','G'): 'guard_assertion: 斷言 decision_review 在 never、standing-go 不再對它動手',
    ('tests/test_storage_boundary.py','G'): 'kept_file: private root 測試用 decision_lab/decision_lab.db 路徑',
    ('tests/test_today_first_screen.py','G'): 'retirement_note: _evidence_gap_order 三條隨研究側退役的註記',
    ('tests/test_webapp_request_path.py','G'): 'guard_assertion: request path 不得 import decision_lab',
    ('thesis/catalyst_calendar.json','G'): 'legacy_key: _comment 記 Engine D 有 16 個 cohort（歷史數字，append-only 資料）',
    ('thesis/generate_lane_memo.py','G'): 'kept_file: lane memo 唯讀舊店的 variant perception（frozen 歷史）',
    ('webapp/api.py','G'): 'boundary_sentence: request path 不得 import decision_lab 的禁止句',
    ('webapp/materialize.py','G'): 'kept_file: positions kind 唯讀開舊店取 capital_expression_counters（plan 批 4 L11-6 第④問確認只用讀取方法）',
    ('alpha/__init__.py','H'): 'kept_file: FundamentalsSnapshot 是 alpha 資料契約（plan §0.6 #28）',
    ('alpha/cli.py','H'): 'kept_file: alpha assumptions 子命令讀 alpha.fundamental.assumptions（ledger 邏輯留）',
    ('alpha/context.py','H'): 'kept_file: FundamentalsSnapshot 資料契約；pe_forward 是 Engine C 欄位名（PE 比值 proxy，plan §0.6 #30）',
    ('alpha/contracts.py','H'): 'kept_file: FundamentalsSnapshot 資料契約與 ASSUMPTION_DRIVERS lazy import',
    ('alpha/providers/__init__.py','H'): 'kept_file: EngineCFundamentalsProvider（Engine C 取數層）',
    ('alpha/providers/fundamentals.py','H'): 'kept_file: ROADMAP H 列明寫留（只供三題與稽核區原始數字）',
    ('alpha/refresh/contracts.py','H'): 'retirement_note: 註解記 price/pe_forward 推代理量的年度陷阱（Engine C 欄位名）',
    ('alpha/refresh/resolver.py','H'): 'retirement_note: docstring 記事發（price/pe_forward 推出來的年度）',
    ('briefing/alpha_view/builder.py','H'): 'kept_file: 讀 alpha.fundamental.assumptions／compare（ledger 邏輯與口徑核實留）；檔頭退役註記',
    ('briefing/alpha_view/changes.py','H'): 'kept_file: 變更偵測用 price/pe_forward（Engine C 欄位）推 forward EPS 的 consensus 事件',
    ('briefing/alpha_view/sources.py','H'): 'kept_file: 讀 alpha.fundamental.compare.verify_consensus_basis（口徑核實留）',
    ('engine_c/checklist.py','H'): 'kept_file: Engine C 資料層，pe_forward 是欄位名',
    ('engine_c/db.py','H'): 'kept_file: Engine C schema，pe_forward 欄位',
    ('engine_c/estimates.py','H'): 'kept_file: Engine C 資料層（ROADMAP H 列明寫留），pe_forward 欄位',
    ('engine_c/etl_yfinance.py','H'): 'kept_file: Engine C ETL 寫 pe_forward 欄位',
    ('engine_c/market_data.py','H'): 'kept_file: Engine C 市場快照含 pe_forward 欄位',
    ('scripts/closure_probe.py','H'): 'kept_file: 唯讀探測，docstring 提口徑核實與 FundamentalsSnapshot（plan §0.6 #31）',
    ('scripts/realign_assumption_refs.py','H'): 'kept_file: 假設 ledger 的 ref 對齊工具，讀 alpha.fundamental.assumptions',
    ('scripts/repricing_check.py','H'): 'kept_file: 股價變化分解讀 Engine C pe_forward（plan §0.6 #31）',
    ('scripts/verify_test_nonvacuity.py','H'): 'kept_file: 突變條目用 pe_forward 變化（Engine C 欄位）',
    ('tests/fixtures_fundamental.py','H'): 'kept_file: 資料夾具（基期觀測／假設／共識）供存活測試（plan §0.6 #24）',
    ('tests/test_absence_semantics.py','H'): 'retirement_note: 註解記主詞 alpha.valuation.build_valuation 退役、判準沒退役',
    ('tests/test_alpha_investment_view.py','H'): 'kept_file: FundamentalsSnapshot 資料契約夾具',
    ('tests/test_alpha_point_in_time.py','H'): 'kept_file: FundamentalsSnapshot 資料契約夾具',
    ('tests/test_alpha_vertical_slice.py','H'): 'kept_file: FundamentalsSnapshot 資料契約夾具',
    ('tests/test_alpha_view_fundamental.py','H'): 'kept_file: ASSUMPTION_BASES 字彙測試（ledger 邏輯留）；檔頭退役註記',
    ('tests/test_alpha_view_refresh.py','H'): 'kept_file: 假設 ledger 夾具與 pe_forward 快照欄位',
    ('tests/test_analyst_view.py','H'): 'guard_assertion: 斷言 consumer 不 import alpha.valuation／alpha.implied_return／alpha.fundamental 模型',
    ('tests/test_consensus_coverage_collapse.py','H'): 'kept_file: 共識覆蓋測試用 FiscalPeriod／ConsensusEstimate 契約與 pe_forward 欄位',
    ('tests/test_coverage_pilot_generalization.py','H'): 'kept_file: 口徑核實（reconcile_consensus_base／verify_consensus_basis）測試',
    ('tests/test_engine_c_bar_date.py','H'): 'kept_file: Engine C 欄位清單含 pe_forward',
    ('tests/test_engine_c_coverage.py','H'): 'kept_file: Engine C 夾具含 pe_forward',
    ('tests/test_engine_c_probe_financial.py','H'): 'kept_file: Engine C 夾具含 pe_forward',
    ('tests/test_estimate_revision.py','H'): 'kept_file: 估計修正測試用 pe_forward 序列（Engine C 欄位）',
    ('tests/test_opinion_stance.py','H'): 'kept_file: overlay ledger 閘門測試讀 alpha.fundamental.contracts 字彙',
    ('tests/test_overlay_scope_gate.py','H'): 'kept_file: overlay scope 閘門測試讀 alpha.fundamental.assumptions／contracts',
    ('tests/test_refresh_engine.py','H'): 'kept_file: refresh 測試讀 alpha.fundamental.assumptions（ledger 邏輯留）',
    ('tests/test_refresh_fiscal_year_scope.py','H'): 'retirement_note: docstring 記事發（price/pe_forward 推年度）',
    ('tests/test_webapp_request_path.py','H'): 'guard_assertion: request path 不得 import alpha.valuation.model／alpha.fundamental.model',
}
ACCEPT_AREAS=("code","static","skills","tests","config")

# ---- I 遠端 Graph MCP（Phase 2 Step 2.1，2026-09-25；ROADMAP 旁支「Graph MCP 退役」）----
# 與 A～H 不同：範圍是**所有 tracked 檔（含每一個 .md、AGENTS.md、prompts/、deploy/、.claude/skills）**，
# keep-list 的理由**只准 historical_record**（ROADMAP 驗收②）。鍵以 `/` 結尾代表整個目錄（歷史目錄才用）。
# ⚠ 邊界用 ASCII lookaround、不用 `\b`：Python 的 `\b` 把中文字算成 word 字元，「與MCP」會漏抓，
#   而 ROADMAP 的盤點命令（git grep -P）會抓到——兩邊不一致就是 L16 說的重造品開始偏離。
# ⚠ 只抓**本專案的** Graph MCP：`_apply_research_action_impl`／`_load_extraction_impl` 是本機 intake domain（留），
#   `--strict-mcp-config`、`mcp_servers` 是 Claude／Codex CLI **擋掉** MCP 的設定（守門，不是殘留），都不算命中。
def _w(tok): return r'(?<![A-Za-z0-9_])'+tok+r'(?![A-Za-z0-9_])'
MCP_GROUP='I 遠端 Graph MCP'
MCP_PATTERN=re.compile('|'.join([
    _w('mcp_server'), 'graph_mcp', 'GRAPH_MCP', _w('MCP'), r'stockbotv2-graph(?!-services)', r'mcp\.minatoyukina',
    _w('record_lead_decision'), _w('apply_research_action'), _w('load_extraction'), _w(r'mcp>='),
    r'^[ \t]*(?:from|import) mcp(?![A-Za-z0-9_])']),re.M)
MCP_SKIP=re.compile(r'^scripts/retired_mechanism_grep\.py$')
KEEP_MCP: dict[str,str] = {
    # ---- 整個目錄都是歷史（ROADMAP 旁支列 ④ 點名）----
    'docs/archive/': 'historical_record: 逐字封存區（含 2026-09-25 封存的遠端存取架構、connector solution、遠端 intake 協定）',
    'docs/brainstorms/': 'historical_record: 當時的需求與決策討論，不改寫',
    'docs/refactor/': 'historical_record: 2026-09 重構時的現況／目標架構盤點（當時 mcp_server 仍在）',
    'docs/reports/': 'historical_record: 帶日期的報告與基準快照（含本 Phase 基準的盤點命令與命中數）',
    'library/raw/': 'historical_record: 一手原文存檔（第三方文件逐字，L10 不改寫）；命中的是該文件自己的用語，與本專案遠端入口無關',
    # ---- 已 completed／superseded 的 dated plans（逐檔；plans/ 目錄裡有 active plan，所以不整個放）----
    'docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md': 'historical_record: superseded plan（→008）',
    'docs/plans/2026-07-14-007-feat-remote-intake-provenance-plan.md': 'historical_record: superseded plan（→008），遠端入圖 provenance 的設計紀錄',
    'docs/plans/2026-07-14-007-feat-source-trace-upgrade-plan.md': 'historical_record: superseded plan（→008）',
    'docs/plans/2026-07-15-008-feat-unified-workplan-plan.md': 'historical_record: completed plan',
    'docs/plans/2026-07-16-001-feat-mobile-research-action-launch-plan.md': 'historical_record: completed plan（遠端 Research Action 兩段式協定的交付紀錄）',
    'docs/plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md': 'historical_record: completed plan',
    'docs/plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md': 'historical_record: completed plan',
    'docs/plans/2026-07-22-002-feat-daily-approval-loop-plan.md': 'historical_record: completed plan',
    'docs/plans/2026-07-24-001-feat-daily-approval-loop-v1-1-plan.md': 'historical_record: completed plan',
    'docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md': 'historical_record: completed plan（Phase 0；get_decision_brief 遠端工具退役的紀錄）',
    'docs/plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md': 'historical_record: completed plan（Phase 1；C5 停用遠端入口的決定）',
    'docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md': 'historical_record: 本次退役的決定紀錄（§0.4 A6 五欄、Step 2.1）',
    # ---- 活文件裡的紀錄列 ----
    'docs/ROADMAP.md': 'historical_record: 旁支「Graph MCP 退役 ✅」列與 Phase 2 列是這次退役的決定與交付紀錄；Phase 0 退役清單的盤點範圍（2026-09-22）；硬約束 12 的改寫註記',
    'docs/plans/README.md': 'historical_record: plan 索引列的主題描述（2026-07-24 v1.1 的 leads 同步、Phase 2 的退役項）',
}

def _tracked_files():
    import subprocess
    out=subprocess.run(['git','ls-files','-z'],capture_output=True,check=True).stdout.decode('utf-8','replace')
    return [p for p in out.split('\0') if p]

def _mcp_hits():
    hits={}
    for p in _tracked_files():
        if MCP_SKIP.search(p) or not os.path.isfile(p): continue
        try: t=io.open(p,encoding='utf-8').read()
        except (UnicodeDecodeError,OSError): continue
        n=len(MCP_PATTERN.findall(t))
        if n: hits[p]=n
    return hits

def _mcp_key(path):
    if path in KEEP_MCP: return path
    for k in KEEP_MCP:
        if k.endswith('/') and path.startswith(k): return k
    return None

def _verdict(idx):
    bad=[(k,v) for k,v in KEEP.items() if v.split(":",1)[0] not in KEEP_CLASSES]
    bad+=[((k,'I'),v) for k,v in KEEP_MCP.items() if v.split(":",1)[0]!='historical_record']
    hits=set(); unlisted=[]
    for g in GROUPS:
        letter=g.split()[0]
        for area in ACCEPT_AREAS:
            for p,n in idx[g].get(area,{}).items():
                key=(p.replace(os.sep,'/'),letter); hits.add(key)
                if key not in KEEP: unlisted.append((letter,area,key[0],n))
    used=set()
    for p,n in MCP_HITS.items():
        k=_mcp_key(p)
        if k is None: unlisted.append(('I','tracked',p,n))
        else: used.add(k)
    stale=[k for k in KEEP if k not in hits]+[(k,'I') for k in KEEP_MCP if k not in used]
    print("\n## 驗收（差集；Phase 0 結案要三個數字都是 0）")
    print(f"  未列 keep-list 的命中（檔，組）數：{len(unlisted)}")
    for letter,area,p,n in sorted(unlisted): print(f"    {letter} {area} {p} ({n})")
    print(f"  已列但不再命中（腐壞條目）數：{len(stale)}")
    for k in stale: print(f"    {k}")
    print(f"  keep-list 條目數：{len(KEEP)}＋I 組 {len(KEEP_MCP)}｜理由類別不合法：{len(bad)}")
    for k,v in bad: print(f"    {k}: {v}")
    return 0 if (not unlisted and not stale and not bad) else 1

for g in GROUPS:
    print(f"\n## {g}")
    for area in ('code','static','skills','crons','tests','config','livedocs','docs'):
        d=idx[g].get(area,{})
        if not d: continue
        top=sorted(d.items(),key=lambda x:-x[1])[:8]
        print(f"  {area}: {len(d)} 檔｜"+"、".join(f"{p.replace(os.sep,'/')}({n})" for p,n in top))
MCP_HITS=_mcp_hits()
print(f"\n## {MCP_GROUP}（所有 tracked 檔）")
by_top=collections.Counter(p.split('/')[0] if '/' in p else p for p in MCP_HITS)
print(f"  {len(MCP_HITS)} 檔｜"+"、".join(f"{k}({v})" for k,v in by_top.most_common()))
raise SystemExit(_verdict(idx))
