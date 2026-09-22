"""退役機制的殭屍 grep（ROADMAP Phase 0 驗收；2026-09-22）。

**不是 linter、不進 CI 或 hook**（L16-4）：Phase 0 結案時跑一次，之後每季跑一次。
八組 regex 對應 ROADMAP「Phase 0 退役清單」；驗收＝code／static／skills／tests／config 全部命中 0。
排除 docs/archive、docs/lessons-incidents.md、library/。docs 那一列只供參考，不計入驗收。

    python scripts/retired_mechanism_grep.py
"""
import os,re,io,collections
AREAS={'code':['alpha','briefing','webapp','engine_b','engine_c','decision_lab','thesis','query','crons','scripts','mcp_server','shared','portfolio','risk','loader','identity','audit'],
       'skills':['skills'],'tests':['tests'],'docs':['docs','CONCEPTS.md','README.md'],'config':['config','.codex','.claude/settings.json','.agents'],'static':['webapp/static']}
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
for g in GROUPS:
    print(f"\n## {g}")
    for area in ('code','static','skills','crons','tests','config','docs'):
        d=idx[g].get(area,{})
        if not d: continue
        top=sorted(d.items(),key=lambda x:-x[1])[:8]
        print(f"  {area}: {len(d)} 檔｜"+"、".join(f"{p.replace(os.sep,'/')}({n})" for p,n in top))
