"""退役機制的殭屍 grep（ROADMAP Phase 0 驗收；2026-09-22）。

**不是 linter、不進 CI 或 hook**（L16-4）：Phase 0 結案時跑一次，之後每季跑一次。
八組 regex 對應 ROADMAP「Phase 0 退役清單」；驗收＝code／static／skills／tests／config 全部命中 0。
排除 docs/archive、docs/lessons-incidents.md、library/。`livedocs`（OPERATIONS／ARCHITECTURE／CONCEPTS）的命中要在 STEP_RESULT 逐句列出，
禁止句（「不做 X」「X 已退役」）可留；`docs` 那一列只供參考，不計入驗收。

    python scripts/retired_mechanism_grep.py
"""
import os,re,io,collections
AREAS={'code':['alpha','briefing','webapp','engine_b','engine_c','decision_lab','thesis','query','crons','scripts','mcp_server','shared','portfolio','risk','loader','identity','audit'],
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
    ("crons/daily_brief_prompt.md","A"): "boundary_sentence: 「只印條數，不印首選、不印名次」「首選換人已不是變動項」",
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
    ("alpha/abstention/contracts.py","B"): "kept_file: abstention kind `bet` 的字彙註記提到籃子（原消費端）；ledger 資料留（L10），註記待 0b.4 E 組收尾改寫",
    ("alpha/providers/market_normalization.py","B"): "retirement_note: 寫明 --basket 與 alpha_screen_check 已退役、Phase 3 候選板接手",
    ("briefing/analyst_view/compose.py","B"): "boundary_sentence: AGENTS 判準句「主題籃子只當脈絡、不設門檻」",
    ("crons/daily_brief_prompt.md","B"): "retirement_note: --basket 已於 0a.1 移除的註記",
    ("config/alpha_screen.json","B"): "kept_file: 覆蓋厚薄門檻留給 Phase 3 候選板（plan 批 3 明寫留）",
    ("config/sector_anchors.json","B"): "retirement_note: _doc 寫明籃子頁「同一個賭注的群」隨排序退役",
    ("skills/alpha-status/SKILL.md","B"): "boundary_sentence: 「主題籃子只當脈絡、不設門檻」",
    ("skills/daily-brief/SKILL.md","B"): "retirement_note: --basket 移除註記；「基準含主題等權籃子」是 AGENTS 量測用語",
    ("skills/lead-intake/SKILL.md","B"): "boundary_sentence: 「主題籃子只當脈絡、不設門檻」",
    ("tests/test_opinion_stance.py","B"): "kept_file: outcome 腳本 power-law 量測的測試（basket_total_return 是量測鍵）",
    ("tests/test_webapp_positions.py","B"): "kept_file: positions artifact 的 power_law 夾具（basket_total_return 量測鍵）",
    ("tests/test_wipeout_flags.py","B"): "guard_assertion: 斷言心跳段 4 仍印「power-law：籃子總報酬」；其餘是籃子退役註記",
    ("tests/test_heartbeat.py","B"): "retirement_note: 0a.2 籃子退役後換主詞的註記",
    ("tests/test_routine_prompts.py","B"): "guard_assertion: 守 daily prompt 的 materialize 行不帶 --basket",
    ("tests/test_webapp_coverage_watches.py","B"): "retirement_note: STATE_KINDS 斷言旁的 0a.2 退役註記",
    ("tests/test_webapp_structure_table.py","B"): "retirement_note: STATE_KINDS 斷言旁的 0a.2 退役註記",
    ("tests/test_absence_semantics.py","B"): "retirement_note: 事發紀錄提到籃子的 bet_state（消費端已退役）",
    ("tests/test_market_quote_unit.py","B"): "retirement_note: 事發紀錄用語「本籃子裡」指研究宇宙，非籃子 filter",
    ("tests/test_nav_exposure.py","B"): "kept_file: regex 誤命中——「籃子」在此是 bucket 的普通名詞",
}
ACCEPT_AREAS=("code","static","skills","tests","config")

def _verdict(idx):
    bad=[(k,v) for k,v in KEEP.items() if v.split(":",1)[0] not in KEEP_CLASSES]
    hits=set(); unlisted=[]
    for g in GROUPS:
        letter=g.split()[0]
        for area in ACCEPT_AREAS:
            for p,n in idx[g].get(area,{}).items():
                key=(p.replace(os.sep,'/'),letter); hits.add(key)
                if key not in KEEP: unlisted.append((letter,area,key[0],n))
    stale=[k for k in KEEP if k not in hits]
    print("\n## 驗收（差集；Phase 0 結案要三個數字都是 0）")
    print(f"  未列 keep-list 的命中（檔，組）數：{len(unlisted)}")
    for letter,area,p,n in sorted(unlisted): print(f"    {letter} {area} {p} ({n})")
    print(f"  已列但不再命中（腐壞條目）數：{len(stale)}")
    for k in stale: print(f"    {k}")
    print(f"  keep-list 條目數：{len(KEEP)}｜理由類別不合法：{len(bad)}")
    for k,v in bad: print(f"    {k}: {v}")
    return 0 if (not unlisted and not stale and not bad) else 1

for g in GROUPS:
    print(f"\n## {g}")
    for area in ('code','static','skills','crons','tests','config','livedocs','docs'):
        d=idx[g].get(area,{})
        if not d: continue
        top=sorted(d.items(),key=lambda x:-x[1])[:8]
        print(f"  {area}: {len(d)} 檔｜"+"、".join(f"{p.replace(os.sep,'/')}({n})" for p,n in top))
raise SystemExit(_verdict(idx))
