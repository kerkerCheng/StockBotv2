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
