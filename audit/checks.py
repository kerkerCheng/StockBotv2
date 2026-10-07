"""十個 runtime invariant check 的實作。

每個 check 的形狀一致：**取資料 → 找違規 → 回 PASS/FAIL，取不到就 SKIPPED。**
`sources` 層保證第三種情況會以例外現身，所以這裡沒有辦法把「讀不到」寫成通過。

## 寫 check 時的三條紀律

1. **findings 必須指得回那一筆。** 「有 3 筆違規」對修的人沒用；
   「`lead_63bebdac` 的 trace_attempts_ref 指向不存在的 library/raw/mu_4_20260825.txt」才有用。
2. **只讀不寫。** Decision Store 與 Engine C ledger 是 append-only private authority（L10）。
3. **不要為了讓 check 通過而放寬它。** 真的抓到東西時，先假設是系統有問題，
   不是 check 太嚴（這是 L14 的反面：gate 要被驗證，但驗證方式是量它的鑑別力，
   不是把它調到不會響）。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from audit import AuditResult, fail, ok, skip
from audit.sources import ROOT, SourceUnavailable
from audit import sources

#: findings 最多列幾筆。超過只列總數——輸出要能讀完。
_MAX_FINDINGS = 12


def _clip(findings: list[str], total: int | None = None) -> tuple[str, ...]:
    total = len(findings) if total is None else total
    if len(findings) <= _MAX_FINDINGS:
        return tuple(findings)
    rest = total - _MAX_FINDINGS
    return (*findings[:_MAX_FINDINGS], f"…另有 {rest} 筆（用 --json 看完整清單）")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    for parse in (datetime.fromisoformat,):
        try:
            got = parse(text)
        except ValueError:
            continue
        return got if got.tzinfo else got.replace(tzinfo=timezone.utc)
    try:
        return datetime.combine(date.fromisoformat(text[:10]), datetime.min.time(),
                                tzinfo=timezone.utc)
    except ValueError:
        return None


def _guard(check: str, fn):
    """把 `SourceUnavailable` 轉成 SKIPPED——**這是唯一的轉換路徑**。"""
    try:
        return fn()
    except SourceUnavailable as exc:
        return skip(check, str(exc))


# ---------------------------------------------------------------------------
# INV-1 — Identity
# ---------------------------------------------------------------------------

def check_identity() -> AuditResult:
    """registry / graph 的 company 集合對齊。**圖∖registry 必須為 0。**

    圖裡有一個 registry 不認識的 `co:*`，代表有人繞過 registry 建了節點——
    之後任何 ticker→id 解析都會在那個 id 上失敗，而失敗的形狀是「查無此公司」
    （F-01：不要憑公司名猜 `co:*`）。

    ⚠ 反向（registry∖graph）**不是違規**：onboard 了但還沒抽取的公司本來就不在圖裡。
    把它算成 FAIL 會讓這個 check 恆亮，鑑別力歸零（L14）。
    """
    def run() -> AuditResult:
        reg = sources.registry()
        known = {c.company_id for c in reg.companies}
        rows = sources.graph_rows(
            "MATCH (company:Company) RETURN company.id AS company_id, company.name AS name")
        in_graph = {r["company_id"] for r in rows if r.get("company_id")}
        orphan = sorted(in_graph - known)
        examined = len(in_graph | known)
        if orphan:
            return fail("Identity", f"圖中有 {len(orphan)} 個 registry 不認識的 company_id",
                        _clip([f"圖有 registry 無：{cid}（ticker 解析會查無此公司，F-01）"
                               for cid in orphan]), examined)
        pending = len(known - in_graph)
        return ok("Identity",
                  f"圖 {len(in_graph)} 家全部在 registry 內"
                  f"（registry 另有 {pending} 家尚未入圖，屬正常）", examined)

    return _guard("Identity", run)


def check_duplicates() -> AuditResult:
    """同一個識別符被兩個實體宣稱。

    三個面向：registry 的 ticker／alias 碰撞、同公司多個 operational cohort、
    同 URL 多個 SourceDoc。前兩者是 identity 分裂（F-04），第三者是重複入庫。
    """
    def run() -> AuditResult:
        reg = sources.registry()
        findings: list[str] = []
        examined = 0

        by_ticker: dict[str, list[str]] = {}
        by_alias: dict[str, list[str]] = {}
        for company in reg.companies:
            examined += 1
            if company.research_ticker:
                by_ticker.setdefault(str(company.research_ticker).upper(), []).append(
                    company.company_id)
            for alias in getattr(company, "aliases", ()) or ():
                by_alias.setdefault(str(alias).upper(), []).append(company.company_id)
        for ticker, ids in sorted(by_ticker.items()):
            if len(ids) > 1:
                findings.append(f"ticker {ticker} 同時屬於 {', '.join(sorted(ids))}")
        for alias, ids in sorted(by_alias.items()):
            if len(set(ids)) > 1:
                findings.append(f"alias {alias} 同時屬於 {', '.join(sorted(set(ids)))}")

        # 同公司多個**非 terminal** cohort。
        # ⚠ 「同公司多 cohort」本身不是違規——第一版這樣寫，抓到 4 組全是
        # 「一個 rejected/expired ＋ 一個現行」，那正是 lifecycle 正常運作
        # （L15：gate 攔下的是形狀不是風險）。真正會重複計入排序的，是**同時有
        # 兩條活的**。
        try:
            rows = sources.decision_rows(
                "select c.company_id, group_concat(c.cohort_id) ids, count(*) n from ("
                "  select c.company_id, c.cohort_id, ("
                "    select e.status from probe_lifecycle_epochs e "
                "     where e.cohort_id = c.cohort_id order by e.epoch desc limit 1) status"
                "  from decision_cohorts c where c.company_id is not null) c "
                "where c.status is null or c.status not in "
                "      ('promoted','rejected','expired','revised') "
                "group by c.company_id having n > 1")
            examined += len(rows)
            for row in rows:
                findings.append(
                    f"{row['company_id']} 同時有 {row['n']} 條**未結束**的 decision 線："
                    f"{row['ids']}——排序會重複計入同一家公司")
        except SourceUnavailable as exc:
            findings.append(f"⚠ cohort 面向未檢查：{exc}")

        # 同一個（正規化）URL 的多份 SourceDoc，不是刻意拆段就是重複入庫。
        # ⚠ 同 URL 不同 section 是**設計**（一份年報拆 photonics／financials 兩節）。
        # 第一版忽略 section，12 組命中全是合法分段——同上，攔到的是格式。
        # ⚠ 2026-10-01（Phase 4 Step 4.2e）：拆段判準改用唯一的 `loader.is_legit_multi_section`（每份都有非空且
        # 兩兩互異的 section），URL 改用 `loader.normalize_url` 分組——原本這裡只擋「同 URL 且同 section」、用原始 URL，
        # 與 loader／健康審查互異（一份有 section、一份沒有時這裡不報、健康審查報紅）。
        try:
            from loader.load_to_neo4j import is_legit_multi_section, normalize_url

            rows = sources.graph_rows(
                "MATCH (sd:SourceDoc) WHERE sd.url IS NOT NULL AND sd.url <> '' "
                "RETURN sd.id AS id, sd.url AS url, sd.section AS section")
            examined += len(rows)
            groups: dict[str, list[tuple[str, str | None]]] = {}
            for row in rows:
                norm = normalize_url(row["url"])
                if norm:
                    groups.setdefault(norm, []).append((row["id"], row.get("section")))
            for norm, members in sorted(groups.items()):
                if len(members) > 1 and not is_legit_multi_section(sec for _, sec in members):
                    findings.append(
                        f"URL {norm} 有 {len(members)} 份 SourceDoc 而且不是刻意拆段"
                        f"（section：{', '.join(f'{sid}={sec or '（無）'}' for sid, sec in sorted(members))}）"
                        "——同一份文件被入庫兩次")
        except SourceUnavailable as exc:
            findings.append(f"⚠ SourceDoc 面向未檢查：{exc}")

        hard = [f for f in findings if not f.startswith("⚠")]
        if hard:
            return fail("Duplicates", f"{len(hard)} 組識別符碰撞",
                        _clip(findings), examined)
        return ok("Duplicates", f"registry {len(reg.companies)} 家無 ticker／alias 碰撞",
                  examined, _clip(findings))

    return _guard("Duplicates", run)


def check_sourcedoc_sync() -> AuditResult:
    """SourceDoc 的 `section`／`title`／`origin_entity` 從抽取 JSON 重建得回來（L10；Phase 4 Step 4.2e 的常駐計數器；
    `origin_entity` Phase 6 Step 6.3d 起，欄位清單與圖那一側的查詢都住 `loader.sourcedoc_sync`）。

    算法只有一份：`loader/sourcedoc_sync.py`（健康審查同一份）。
    - **FAIL**（`loader.sourcedoc_sync.is_red`，唯一判準）：重建會遺失或不確定——圖上有值、JSON 沒有；同一個 doc_id 的
      多份 JSON 彼此互異（載入順序決定結果）；圖上有、沒有任何抽取檔；抽取檔讀不了（R2-a N7）。
    - **不算 FAIL、照列**：圖落後 JSON（JSON 是對的、圖還沒重載；重載即對齊）——把它算 FAIL 會讓「修好了 JSON、
      等核准改圖」的那段時間整份 audit 變紅，紅的卻不是風險（L15：gate 攔下的必須是它想攔的東西）。
    """
    def run() -> AuditResult:
        from loader.sourcedoc_sync import GRAPH_CYPHER, drift, is_red, json_source_docs, summary_line

        rows = sources.graph_rows(GRAPH_CYPHER)
        result = drift(rows, json_source_docs(ROOT / "extractions"))
        danger = ([f"⛔ {d['doc_id']}.{d['field']}（{d['kind']}）：圖＝{d['graph']!r}；JSON＝{d['json']!r}"
                   for d in result["danger"]]
                  + [f"⛔ {doc_id}：圖上有、沒有任何抽取檔（重建不回來）" for doc_id in result["graph_without_json"]]
                  + [f"⛔ extractions/{name}：讀不了（重載時整份載不進去）" for name in result["unreadable_json"]])
        stale = [f"圖落後 JSON：{d['doc_id']}.{d['field']}：{d['graph']!r} → {d['json']!r}" for d in result["stale"]]
        if is_red(result):
            return fail("SourceDocSync", summary_line(result), _clip(danger + stale), len(rows))
        return ok("SourceDocSync", summary_line(result), len(rows), _clip(stale))

    return _guard("SourceDocSync", run)


def check_graph_financial_join() -> AuditResult:
    """A→C join key 兩側對齊。**部分缺漏必須現形，不得靜默關掉整條管線。**

    L9 定的 join key 是 registry 的 `research_ticker`。這裡量的是覆蓋率：
    圖裡有節點、registry 有 ticker，但 Engine C 從來沒有快照的公司——
    那些標的的財務軸永遠算不出來，而目前**沒有任何地方會說出來**。
    """
    def run() -> AuditResult:
        reg = sources.registry()
        rows = sources.graph_rows("MATCH (company:Company) RETURN company.id AS company_id")
        in_graph = {r["company_id"] for r in rows if r.get("company_id")}
        conn = sources.engine_c_conn()
        try:
            covered = {str(r[0]).upper() for r in
                       conn.execute("select distinct ticker from financial_snapshots")}
        finally:
            conn.close()

        missing_ticker: list[str] = []
        missing_snapshot: list[str] = []
        examined = 0
        for company in reg.companies:
            if company.company_id not in in_graph:
                continue
            examined += 1
            ticker = company.research_ticker
            if not ticker:
                missing_ticker.append(company.company_id)   # 私人公司，明確標記非缺漏
            elif str(ticker).upper() not in covered:
                missing_snapshot.append(f"{company.company_id}（{ticker}）")

        if missing_snapshot:
            return fail(
                "GraphFinancialJoin",
                f"圖中 {len(missing_snapshot)}/{examined} 家有 ticker 卻無 Engine C 快照",
                _clip([f"{item} 在圖裡但 Engine C 從無快照——"
                       "財務軸恆為 unknown，且目前沒有任何地方會說出來"
                       for item in missing_snapshot]),
                examined)
        return ok("GraphFinancialJoin",
                  f"圖中 {examined} 家可 join，另 {len(missing_ticker)} 家為私人公司"
                  "（ticker=None 是明確標記，不是缺漏）", examined)

    return _guard("GraphFinancialJoin", run)


# ---------------------------------------------------------------------------
# INV-2 — Lifecycle / Expiry
# ---------------------------------------------------------------------------

#: 到期／`until` 過了之後，處置要在多久內落地。機械處置（pq2／追源／讀圖型）與「列進複查／重讀／watch_decision」
#: 都在每天 `todo sync` 的同一輪完成——給一天餘裕是為了不在當天 sync 之前誤報。
_EXPIRY_GRACE = timedelta(days=1)
#: 判定觸及（thesis 來源）之後，C3 的接點（thesis 複查那一筆）必須在多久內出現（plan §11；第 2 輪 N-d）。
_TOUCHED_GRACE = timedelta(hours=48)


def _open_review_ids(items: list[dict]) -> set[str]:
    """未結案 `thesis_lifecycle` 項目涵蓋的 watch_id（到期與觸及的反證由這一筆接住；A7、C3）。"""
    return {str(wid) for item in items
            if item.get("type") == "thesis_lifecycle" and not item.get("resolution")
            for wid in (item.get("disproof_watch_ids") or ())}


def _label(watch: dict) -> str:
    from engine_b.event_watch import condition_label

    return condition_label(watch.get("condition") or watch.get("fact") or watch.get("note"), 30)


def _watch_lifecycle_findings(watches: list[dict]) -> list[str]:
    """watch 的狀態與收據同進退（Phase 1 Step 1.10）：狀態在封閉字彙內、fired 說得出誰叫醒它、
    終局（consumed／expired）帶收據、`expiry_resolution` 與狀態相符。"""
    from engine_b import event_watch as ew

    out: list[str] = []
    for watch in watches:
        wid = watch.get("watch_id", "?")
        status = watch.get("status")
        if status not in ew.WATCH_STATUSES:
            out.append(f"watch {wid} status={status!r} 不在封閉字彙 {ew.WATCH_STATUSES}——沒有任何 consumer 認得這個狀態")
            continue
        if status == "fired" and not watch.get("woken_by"):
            out.append(f"watch {wid} fired 卻沒有 woken_by——說不出是哪一份文件叫醒它，判定無從對照")
        if status == "expired" and _parse_dt(watch.get("expired_at")) is None:
            out.append(f"watch {wid} expired 卻沒有 expired_at——到期多久無從得知，重問的時限算不出來")
        if status == "consumed" and not any(watch.get(k) for k in ("woken_by", "judgment", "closed",
                                                                      "expiry_resolution")):
            out.append(f"watch {wid} consumed 卻沒有任何收據（woken_by／judgment／closed／expiry_resolution）"
                       "——說不出它為什麼結束")
        kind = (watch.get("expiry_resolution") or {}).get("kind")
        if not watch.get("expiry_resolution"):
            continue
        if kind not in ew.EXPIRY_RESOLUTION_KINDS:
            out.append(f"watch {wid} 的到期處置 kind={kind!r} 不在封閉字彙裡")
        elif status == "active":
            out.append(f"watch {wid} active 卻帶到期處置 {kind}——續等應清掉處置（renew），"
                       "否則下一次到期會被當成已處置")
        elif status in ("fired", "consumed") and kind != "touched":
            out.append(f"watch {wid} {status} 卻帶到期處置 {kind}——只有 touched（研究結論＝條件已被觸及）"
                       "會讓到期的 watch 離開 expired")
    return out


def check_lifecycle() -> AuditResult:
    """terminal 狀態與收據必須同進退：待辦池的 resolution／resolved_at、watch 的狀態與到期處置。

    ⚠ 2026-09-24（Phase 1 Step 1.10）：原本還讀舊 Decision Store 的 `probe_lifecycle_epochs`——那是凍結資料，
    永遠 PASS＝不會滅的檢查（L14-4）；凍結歷史由 `DecisionLineage` 照看。改讀等待 registry
    （`_watch_lifecycle_findings`）。
    """
    def run() -> AuditResult:
        findings: list[str] = []

        items = sources.todo_items()
        watches = sources.event_watches()
        examined = len(items) + len(watches)
        for item in items:
            n = item.get("n")
            has_resolution = bool(item.get("resolution"))
            has_time = bool(item.get("resolved_at"))
            if has_resolution != has_time:
                findings.append(
                    f"[{n}] resolution={item.get('resolution')!r} 與 "
                    f"resolved_at={item.get('resolved_at')!r} 不一致"
                    "（一個說結案了、一個說沒有）")
        findings.extend(_watch_lifecycle_findings(watches))

        if findings:
            return fail("Lifecycle", f"{len(findings)} 筆生命週期狀態自相矛盾",
                        _clip(findings), examined)
        return ok("Lifecycle", f"待辦池 {len(items)} 項結案狀態一致；watch {len(watches)} 筆狀態與收據相符",
                  examined)

    return _guard("Lifecycle", run)


#: 候選板 artifact 多舊就不拿來判「有去處」（daily 每天 materialize；超過這個時間代表它停更了，時間閘門會讓檢查恆 PASS）。
_BOARD_MAX_AGE_HOURS = 36


def _board_context(now: datetime) -> dict:
    """候選板 artifact（列、整板清單帶著的 watch id、產生時間）＋敘事 brief→公司對照；任一讀不到或板已停更，
    `note` 寫出理由——呼叫端記成「沒檢查」，不判失敗（3.6 覆核：ledger 讀不到原本被報成「公司不明」的 FAIL）。"""
    ctx: dict = {"rows": {}, "carried": set(), "at": None, "note": None, "company_of": {}}
    try:
        payload = sources.candidates_artifact()
    except Exception as exc:  # noqa: BLE001
        ctx["note"] = str(exc)
        return ctx
    for bucket in (*(payload.get("groups") or {}).values(), *(payload.get("side_groups") or {}).values()):
        for row in bucket or ():
            ctx["rows"][str(row.get("company_id"))] = row
    ctx["carried"] = {str(b.get("watch_id")) for b in payload.get("narrative_rewrite") or () if b.get("watch_id")}
    ctx["at"] = _parse_dt(payload.get("generated_at"))
    if ctx["at"] is None or (now - ctx["at"]).total_seconds() > _BOARD_MAX_AGE_HOURS * 3600:
        ctx["note"] = f"候選板 artifact 已超過 {_BOARD_MAX_AGE_HOURS} 小時沒更新（{payload.get('generated_at')}）"
        return ctx
    try:
        ledgers = sources.brief_ledgers()
    except Exception as exc:  # noqa: BLE001
        ctx["note"] = f"敘事 ledger 讀不到，對不到 watch 屬於哪一家（{exc}）"
        return ctx
    ctx["company_of"] = {f"brief:{r.brief_id}": r.company_id for entry in ledgers.values()
                         for r in entry.get("records") or ()}
    return ctx


def _rewrite_entered_at(watch: dict) -> datetime | None:
    """敘事來源 watch 進入「該重寫」的時間：醒來＝woken_by.at；觸及＝judgment.at；到期＝expired_at。"""
    from engine_b.queue_segments import narrative_rewrite_state

    state = narrative_rewrite_state(watch)
    if state == "fired":
        return _parse_dt((watch.get("woken_by") or {}).get("at"))
    if state == "touched":
        return _parse_dt((watch.get("judgment") or {}).get("at"))
    if state == "expired":
        return _parse_dt(watch.get("expired_at"))
    return None


def _board_misses(watch: dict, ctx: dict) -> str | None:
    """plan §5 第 6 點：rewrite 類「有去處」＝在 narrative_rewrite 段**且**候選板帶著它（那一列，或整板清單——
    現行敘事已撤回／是舊版／沒有敘事時沒有 v2 列，由整板清單帶）。只問在 artifact 產生之前就進入該重寫狀態的
    watch（之後才醒的，下一輪 materialize 才會帶）。"""
    entered = _rewrite_entered_at(watch)
    if ctx["at"] is None or entered is None or entered > ctx["at"]:
        return None
    wid = str(watch.get("watch_id"))
    company = str(watch.get("wake_brief") or ctx["company_of"].get(str(watch.get("source_ref") or "").split("#")[0], ""))
    row = ctx["rows"].get(company)
    if wid in ctx["carried"] or (row is not None and wid in (row.get("rewrite_watch_ids") or ())):
        return None
    return (f"watch {wid}（敘事來源，{company or '公司不明'}）在候選板產生之前就該重寫了，"
            "候選板卻沒帶著它（那一列與整板清單都沒有）——板上看不到那份敘事該重寫（plan §5 第 6 點）")


def check_expiry() -> AuditResult:
    """**每一個等待都必須有到期。** 沒有到期的等待就是沉底。

    這是 [321] 定案的直接執行：`stalled`／`expired`／`unwatched` 之所以要被撈出來，
    是因為原本的 consumed-marker 沒有到期兜底，標的用完即靜默沉底
    （實測 50 筆有 10 筆已不可能再被喚醒）。

    Phase 1 Step 1.10（A7）：**每一次到期也都必須有去處。** 到期未處置、`expired_at` 超過一天的，依
    `expiry_class` 驗它被接住了沒——thesis 來源列進未結案 thesis 複查的 `disproof_watch_ids`、讀圖來源列進
    節點的重讀理由、假設型等有未結案的 `watch_decision`；pq2／追源／讀圖型是同一輪 sync 的機械處置，
    超過一天沒處置＝處置沒跑。pq2 的 `waiting_on` 也是等待：`until` 過了還掛著、或既沒有 `until` 也沒有
    watch 會叫醒它 → FAIL（那個等待永遠不會被重問）。
    """
    def run() -> AuditResult:
        from engine_b import event_watch as ew

        watches = sources.event_watches()
        items = sources.todo_items()
        findings: list[str] = []
        now = _now()
        today = ew._today(now)   # 排程時區的今天（Step 2.9c）：與 watch 到期判斷同一個定義，寬限照舊
        examined = 0
        unchecked: list[str] = []
        board_state = None                 # 候選板 artifact（第一次需要時才讀；Step 3.6）
        board_note: str | None = None

        # ① 在等的 watch 必須有到期；過了到期日兩天還是 active＝轉到期（`mark_expired`）沒跑
        for watch in watches:
            if watch.get("status") != "active":
                continue
            examined += 1
            wid = watch.get("watch_id", "?")
            expires = _parse_dt(watch.get("expires"))
            if expires is None:
                findings.append(
                    f"watch {wid}（{watch.get('kind')}）status=active 但沒有 expires"
                    "——沒有到期的等待不會醒，也不會有人發現它沒醒")
            elif expires.date() < today - _EXPIRY_GRACE:
                findings.append(
                    f"watch {wid}（{_label(watch)}）過了到期日 {watch.get('expires')} 仍是 active"
                    "——轉到期（`todo sync` 的 `mark_expired`）沒跑，這個等待不會被重問")

        # ② 到期之後有沒有去處
        open_items = [i for i in items if not i.get("resolution")]
        by_n = {int(i["n"]): i for i in items if i.get("n") is not None}
        review_ids = _open_review_ids(items)
        decision_refs = {str(i.get("ref_id")) for i in open_items if i.get("type") == "watch_decision"}
        try:
            sources.thesis_lifecycle()
            lifecycle_note = None
        except SourceUnavailable as exc:
            lifecycle_note = str(exc)
        try:
            readings = sources.reading_ledgers()
            readings_note = None
        except SourceUnavailable as exc:
            readings, readings_note = {}, str(exc)
        layer_note_rows: dict[str, dict] | None = None     # 第一次遇到層說明主張才讀（S4a R2 C2）
        layer_note_note: str | None = None
        for watch in watches:
            if watch.get("status") != "expired":
                continue
            examined += 1
            wid = watch.get("watch_id", "?")
            cls = ew.expiry_class(watch)
            expired_at = _parse_dt(watch.get("expired_at"))
            if expired_at is None or now - expired_at <= _EXPIRY_GRACE:
                continue   # expired_at 缺席由 Lifecycle 報；一天內的還在同一輪 sync 的處置窗內
            if cls == "pq2":
                n = int(watch["wake_pq2"])
                item = by_n.get(n)
                waiting = (item or {}).get("waiting_on") or {}
                if item is not None and not item.get("resolution") and (waiting or item.get("deferred_at")):
                    set_at = _parse_dt(waiting.get("set_at") or item.get("deferred_at"))
                    if set_at is None or set_at <= expired_at:
                        findings.append(
                            f"watch {wid} 到期超過一天，它要叫回的 [{n}] 仍掛在等待"
                            "——到期沒有把編號翻回「球在你」")
                        continue
            if watch.get("expiry_resolution"):
                continue
            if cls == "thesis_review":
                if lifecycle_note:
                    unchecked.append(wid)
                elif wid not in review_ids:
                    findings.append(
                        f"watch {wid}（thesis 反證「{_label(watch)}」）到期超過一天，沒有列進任何未結案 thesis "
                        "複查的 disproof_watch_ids——到期被丟了（A7：重問＝併進那份 thesis 的複查）")
            elif cls == "reread" and str(watch.get("source_ref") or "").startswith("layer_note:"):
                # 層說明的主張（2026-10-07 S4a R2 C2）：去處是層說明自己的逐節點「該重讀」清單——不依賴結構讀圖
                # （轉換型節點永遠沒有讀圖；用讀圖判會一直紅、而且指向錯的補法）。重問＝換版那一份層說明。
                from alpha.providers.layer_notes import layer_note_reread_rows

                if layer_note_rows is None:
                    try:
                        notes = {n: led["current"] for n, led in sources.layer_note_ledgers().items() if led.get("current")}
                        layer_note_rows = {r["node"]: r for r in layer_note_reread_rows(notes, watches, today=today)}
                    except SourceUnavailable as exc:
                        layer_note_rows, layer_note_note = {}, str(exc)
                if layer_note_note:
                    unchecked.append(wid)
                    continue
                node = str(watch.get("node") or "")
                row = layer_note_rows.get(node) or {}
                if not any(ew.condition_label(watch.get("condition")) in reason for reason in row.get("reasons") or ()):
                    findings.append(
                        f"watch {wid}（層說明主張「{_label(watch)}」）到期超過一天，節點 {node or '（沒寫 node）'} 的"
                        "層說明該重讀清單裡沒有它——心跳不會叫你換版（補法：`python -m alpha layer-note <node> --add`，"
                        "spec 帶 supersedes_id；那一份若已不是現行，舊條件應該在換版時就收掉）")
            elif cls == "reread":
                if readings_note:
                    unchecked.append(wid)
                    continue
                from alpha.providers.structure_readings import reread_reasons

                node = str(watch.get("node") or "")
                current = ((readings.get(node) or {}).get("current") or {}) if node else {}
                reasons = reread_reasons(node, watches) if current else []
                if not any(ew.condition_label(watch.get("condition")) in reason for reason in reasons):
                    findings.append(
                        f"watch {wid}（讀圖反證「{_label(watch)}」）到期超過一天，節點 {node or '（沒寫 node）'}"
                        f"{'' if current else '沒有現行讀圖，'}的重讀理由裡沒有它——APP 與心跳都不會叫你重讀")
            elif cls == "rewrite":
                # Phase 3 Step 3.4：敘事型到期不鑄號——它的去處是佇列段 narrative_rewrite（consumer：research-drain），
                # 處置在下一次重寫的 acknowledged_touched。分不到那一段＝到期被丟了。
                # Step 3.6：去處的另一半是候選板那一列帶著它（plan §5 第 6 點）。
                from engine_b.queue_segments import classify_watch

                if classify_watch(watch) != "narrative_rewrite":
                    findings.append(
                        f"watch {wid}（敘事「{_label(watch)}」）到期超過一天，卻不在 narrative_rewrite 段"
                        "——沒有人會重寫那份敘事（INV-2：到期是重問不是丟）")
                else:
                    if board_state is None:
                        board_state = _board_context(now)
                    if board_state["note"]:
                        unchecked.append(wid)
                        board_note = board_state["note"]
                    else:
                        miss = _board_misses(watch, board_state)
                        if miss:
                            findings.append(miss)
            elif cls == "decision":
                ref = f"{wid}@{watch.get('expires')}"
                if ref not in decision_refs:
                    findings.append(
                        f"watch {wid}（{_label(watch)}）到期超過一天，既沒有未結案的 watch_decision（{ref}）"
                        "也沒有處置——到期被丟了（INV-2：到期是重問不是丟）")
            else:
                findings.append(
                    f"watch {wid}（{cls} 型）到期超過一天仍沒有處置——這一型由 `todo sync` 同一輪機械處置，"
                    "處置沒跑")

        # ③ pq2 的等待：`until` 過了還掛著；或既沒有 `until`、也沒有 watch 會叫醒它
        live_wakes = {int(w["wake_pq2"]) for w in watches
                      if w.get("wake_pq2") and w.get("status") in ("active", "fired")}
        for item in open_items:
            waiting = item.get("waiting_on")
            if not isinstance(waiting, dict):
                continue
            examined += 1
            n = item.get("n")
            until = str(waiting.get("until") or "")[:10]
            if until:
                try:
                    passed = date.fromisoformat(until) < today - _EXPIRY_GRACE
                except ValueError:
                    findings.append(f"[{n}] waiting_on.until={until!r} 讀不成日期——這個等待不會被重問")
                    continue
                if passed:
                    findings.append(
                        f"[{n}] 等到 {until} 的日期已過仍掛在「等事件」——叫回（`todo sync` 的 `_wake_passed_until`）沒跑")
            elif n is None or int(n) not in live_wakes:
                findings.append(
                    f"[{n}] 在等事件（{ew.condition_label(waiting.get('trigger') or waiting.get('reason'), 30)}）"
                    "卻沒有到期日、也沒有任何 watch 會叫醒它——這個等待永遠不會被重問"
                    "（修法：`todo resolve <n> --verb pending --until <日期> --trigger …` 或 drop）")

        # 舊店的 prepared actions（凍結唯讀）
        prepared_findings: list[str] = []
        try:
            rows = sources.decision_rows(
                "select action_id, action_type, expires_at, status from prepared_actions "
                "where status not in ('applied','expired','cancelled')")
            examined += len(rows)
            for row in rows:
                if not row.get("expires_at"):
                    prepared_findings.append(
                        f"prepared action {row['action_id']}（{row['action_type']}）"
                        f"status={row['status']} 但沒有 expires_at")
        except SourceUnavailable as exc:
            prepared_findings.append(f"⚠ prepared_actions 未檢查：{exc}")

        hard = findings + [f for f in prepared_findings if not f.startswith("⚠")]
        soft = [f for f in prepared_findings if f.startswith("⚠")]
        if unchecked:
            notes = "；".join(n for n in (lifecycle_note, readings_note, board_note) if n)
            soft.append(f"⚠ {len(unchecked)} 筆到期的反證沒檢查去處（{notes}）："
                        + "、".join(unchecked[:6]))
        if hard:
            return fail("Expiry", f"{len(hard)} 個等待沒有到期，或到期了沒有去處",
                        _clip(hard + soft, len(hard) + len(soft)), examined)
        return ok("Expiry", f"{examined} 個等待全部有到期，到期的都有去處",
                  examined, _clip(soft))

    return _guard("Expiry", run)


# ---------------------------------------------------------------------------
# INV-3 — Orphans
# ---------------------------------------------------------------------------

def check_orphans() -> AuditResult:
    """指標活著、被指的東西死了——而**沒有任何東西會叫**。

    2026-09-04 實測抓到的第一筆真實問題：daily 的 pq1 追源把證據寫進
    `library/raw/`、把路徑寫進 leads state；若備份只收四個 leads JSON，引用仍活著、
    被引用的檔案卻會留在備份外，之後就可能消失
    （3 筆 `trace_attempts_ref` 有 2 筆指向已不存在的檔案）。
    兩筆皆為 SEC `/Archives/` 不可變歸檔，已重抓還原並與 lead 的
    `research_outcome` 逐字核對；publisher 端的結構修法見 `_referenced_evidence`。
    **可不可以重抓取決於來源可不可變**，判準見 `docs/OPERATIONS.md`。

    ⚠ `library/private/` 底下的引用**刻意**不算違規——那些是設計上就不進 Git 的
    （X 附圖、ASR 逐字稿）。把它們算進來會讓這個 check 恆亮。
    """
    def run() -> AuditResult:
        findings: list[str] = []
        examined = 0

        # ① leads state 指向 tracked 區的檔案引用
        refs: list[tuple[str, str, str]] = []

        def walk(node: object, lead_id: str) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if (isinstance(value, str) and value.startswith("library/")
                            and "/private/" not in value and len(value.split()) == 1):
                        refs.append((lead_id, key, value))
                    else:
                        walk(value, lead_id)
            elif isinstance(node, list):
                for value in node:
                    walk(value, lead_id)

        for lead_id, lead in sources.leads().items():
            walk(lead, lead_id)
        examined += len(refs)
        for lead_id, key, ref in refs:
            if not (ROOT / ref).exists():
                findings.append(
                    f"{lead_id[:22]} 的 {key} 指向不存在的 {ref}"
                    "——引用已發布，被引用的檔案沒有")

        # ② watch → 喚醒目標。編號／lead 不存在是資料錯；存在但已結案（且它是唯一的喚醒目標）＝醒了也沒有
        #    東西會接——`todo sync` 應已收掉（NB2-12；`_close_orphaned_waits`）
        items = sources.todo_items()
        watches = sources.event_watches()
        leads_map = sources.leads()
        by_n = {int(item["n"]): item for item in items if item.get("n") is not None}
        for watch in watches:
            wid = watch.get("watch_id")
            only_target = not (watch.get("hypothesis_ref") or watch.get("wake_reading")
                               or watch.get("disproof_ref")) and not (watch.get("wake_pq2") and watch.get("wake_lead"))
            wake = watch.get("wake_pq2")
            if wake:
                examined += 1
                item = by_n.get(int(wake))
                if item is None:
                    findings.append(
                        f"watch {wid} 要喚醒 pq2 [{wake}]，"
                        "但待辦池裡沒有這個編號——醒了也沒有東西會接")
                elif item.get("resolution") and watch.get("status") == "active" and only_target:
                    findings.append(
                        f"watch {wid} 還在等，要喚醒的 pq2 [{wake}] 卻已 {item['resolution']}"
                        "——醒了也沒有東西會接（`todo sync` 應已收掉）")
            lead_id = watch.get("wake_lead")
            if lead_id and watch.get("status") in ("active", "fired"):
                examined += 1
                lead = leads_map.get(str(lead_id))
                if lead is None:
                    findings.append(f"watch {wid} 要排回 pq1 的 lead {str(lead_id)[:22]} 不存在")
                elif (lead.get("status") in ("applied", "triaged_no_go") and watch.get("status") == "active"
                      and only_target):
                    findings.append(
                        f"watch {wid} 還在等，要排回 pq1 的 lead {str(lead_id)[:22]} 卻已 {lead['status']}"
                        "——醒了也沒有東西會接（`todo sync` 應已收掉）")

        # ③ 假設 → watch
        watch_ids = {w.get("watch_id") for w in watches}
        for hypothesis in sources.hypotheses():
            wid = hypothesis.get("watch_id")
            if not wid:
                continue
            examined += 1
            if wid not in watch_ids:
                findings.append(
                    f"假設 {hypothesis.get('hypothesis_id')} 綁的 watch {wid} 不存在"
                    "——沒有任何機制在等它被驗證")

        # ④–⑦ 語意 watch 與讀圖喚醒 → 它們的來源
        more, soft, count = _semantic_source_orphans(watches)
        findings.extend(more)
        examined += count

        if findings:
            return fail("Orphans", f"{len(findings)} 個引用指向不存在或已不是現行的東西",
                        _clip(findings + soft), examined)
        return ok("Orphans", f"{examined} 個跨檔引用全部解析得到", examined, _clip(soft))

    return _guard("Orphans", run)


def _semantic_source_orphans(watches: list[dict]) -> tuple[list[str], list[str], int]:
    """語意 watch 與讀圖喚醒指回的來源（Phase 1 Step 1.10）：

    ④ 處理中的語意 watch 的 `disproof_ref` 解析得到——memo 的第 k 條存在且就是它的條件；讀圖的 reading_id 存在、
       第 k 條存在（對帳沒跑或壞了，舊 memo 還在時「指向不存在」抓不到，所以條件文字也要對上）
    ⑤ 在等的 `wake_reading` 指向有現行讀圖的節點（沒有的話醒了列進重讀也沒有畫面會顯示）
    ⑥ 在等的語意 watch 的來源是現行：thesis＝lifecycle 的現行 memo；讀圖＝節點現行讀圖（第 2 輪 X2）
    ⑦ 現行 memo 的 sidecar 有結構化反證且 hash 相符 → 在等的語意 watch 的條件在 sidecar 裡（第 4 輪 N4-12；
       sidecar 沒有結構化反證時不適用——1.6 手動登記的合法地不在任何 sidecar 裡）
    lifecycle 或讀圖 ledger 讀不到 → 那一半列 ⚠ 未檢查，不當通過也不當失敗。"""
    from engine_b import disproof
    from engine_b import event_watch as ew
    from thesis.memo_structure import disproof_items, memo_file_sha256

    findings: list[str] = []
    soft: list[str] = []
    examined = 0
    try:
        lifecycle = sources.thesis_lifecycle()
    except SourceUnavailable as exc:
        lifecycle = None
        soft.append(f"⚠ thesis 來源的反證 watch 未檢查：{exc}")
    try:
        ledgers = sources.reading_ledgers()
    except SourceUnavailable as exc:
        ledgers = None
        soft.append(f"⚠ 讀圖來源的反證與 wake_reading 未檢查：{exc}")
    try:
        briefs = sources.brief_ledgers()
    except SourceUnavailable as exc:
        briefs = None
        soft.append(f"⚠ 敘事來源的反證與 wake_brief 未檢查：{exc}")
    try:
        layer_notes = sources.layer_note_ledgers()
    except SourceUnavailable as exc:
        layer_notes = None
        soft.append(f"⚠ 層說明來源的主張 watch 未檢查：{exc}")
    brief_by_id = {r.brief_id: (t, r) for t, led in (briefs or {}).items() for r in led["records"]}
    current_brief_ids: set[str] = set()
    for _t, led in (briefs or {}).items():
        visible = sorted(led["records"], key=lambda r: (r.created_at, r.brief_id))
        if visible and not visible[-1].retracted:
            current_brief_ids.add(visible[-1].brief_id)
    current_memos = {str(e["memo"]) for e in (lifecycle or {}).values()
                     if isinstance(e, dict) and e.get("memo") and e.get("status") != "retired"}
    memo_items: dict[str, list[str] | None] = {}
    sidecar_sets: dict[str, set[str] | None] = {}

    def items_of(memo: str) -> list[str] | None:
        if memo not in memo_items:
            try:
                memo_items[memo] = [disproof.normalize(x) for x in
                                    disproof_items((ROOT / memo).read_text(encoding="utf-8"))]
            except OSError:
                memo_items[memo] = None
        return memo_items[memo]

    def sidecar_of(memo: str) -> set[str] | None:
        """現行 memo 的結構化反證集合；沒有結構化反證或 hash 不符 → None（不適用）。"""
        if memo not in sidecar_sets:
            sidecar_sets[memo] = None
            try:
                data = json.loads((ROOT / memo).with_suffix(".evidence.json").read_text(encoding="utf-8"))
                conditions = data.get("disproof_conditions") if isinstance(data, dict) else None
                if conditions and memo_file_sha256(ROOT / memo) == data.get("memo_sha256"):
                    sidecar_sets[memo] = {disproof.normalize(c.get("condition")) for c in conditions
                                          if isinstance(c, dict)}
            except (OSError, ValueError):
                pass
        return sidecar_sets[memo]

    for watch in watches:
        wid = watch.get("watch_id", "?")
        status = watch.get("status")
        waiting = status in ("active", "fired")
        if watch.get("wake_brief") and waiting:
            examined += 1
            from identity.registry import get_registry

            if not get_registry().has_company(str(watch["wake_brief"])):
                findings.append(f"watch {wid} 的 wake_brief 指向 registry 沒有的 {watch['wake_brief']}"
                                "——醒了也沒有哪一份敘事會重寫")
        if watch.get("wake_reading") and waiting and ledgers is not None:
            examined += 1
            node = str(watch["wake_reading"])
            if not (ledgers.get(node) or {}).get("current"):
                findings.append(f"watch {wid} 的 wake_reading 指向 {node}，那個節點沒有現行讀圖"
                                "——醒了列進重讀也沒有畫面會顯示")
        if watch.get("kind") != ew.SEMANTIC_KIND:
            continue
        in_process = waiting or (status == "expired" and not watch.get("expiry_resolution"))
        if not in_process:
            continue
        ref = str(watch.get("disproof_ref") or watch.get("source_ref") or "")
        base, _, index_text = ref.partition("#")
        try:
            index = int(index_text)
        except ValueError:
            index = 0
        text = disproof.normalize(watch.get("condition"))
        label = _label(watch)
        memo = disproof.memo_ref(ref)
        if memo is not None:
            if lifecycle is None:
                continue
            examined += 1
            items = items_of(memo)
            if items is None:
                findings.append(f"watch {wid}（「{label}」）的 disproof_ref 指向讀不到的 memo {memo}")
                continue
            if not 1 <= index <= len(items) or items[index - 1] != text:
                findings.append(f"watch {wid}（「{label}」）的 disproof_ref={ref} 在 memo「推翻」節對不到它的條件"
                                f"（該節 {len(items)} 條）——對帳（`todo sync`）沒跑或壞了")
            if waiting and memo not in current_memos:
                findings.append(f"watch {wid}（「{label}」）還在等，來源 memo {memo} 卻不是 lifecycle 的現行 memo"
                                "——換版後舊條件沒收（`todo sync` 的反證對帳）")
            elif waiting:
                structured = sidecar_of(memo)
                if structured is not None and text not in structured:
                    findings.append(f"watch {wid}（「{label}」）還在等，但現行 memo 的結構化反證（sidecar）裡沒有這條"
                                    "——memo 原地重產後舊條件沒收")
        elif base.startswith("brief:"):
            if briefs is None:
                continue
            examined += 1
            brief_id = base[len("brief:"):]
            owner = brief_by_id.get(brief_id)
            if owner is None:
                findings.append(f"watch {wid}（「{label}」）的 disproof_ref 指向敘事 {brief_id}，任何 ledger 裡都沒有這一份")
                continue
            if ew.is_confirm(watch):
                # 加碼條件（Phase 7 Step 7.0d）：來源鍵 `brief:<id>#c<n>`，對那份敘事的 confirm[]，不對 disproof[]
                entries = tuple(getattr(owner[1], "confirm", ()) or ())
                c_index = int(index_text[1:]) if index_text.startswith("c") and index_text[1:].isdigit() else 0
                if not 1 <= c_index <= len(entries) or disproof.normalize(entries[c_index - 1].condition) != text:
                    findings.append(f"watch {wid}（「{label}」）的 disproof_ref={ref} 在那份敘事的 confirm[] 對不到它的條件")
            else:
                entries = tuple(owner[1].disproof or ())
                if not 1 <= index <= len(entries) or disproof.normalize(entries[index - 1].condition) != text:
                    findings.append(f"watch {wid}（「{label}」）的 disproof_ref={ref} 在那份敘事的 disproof[] 對不到它的條件")
            # 還在等（active）卻不是現行敘事的＝換版／撤回沒收；fired／觸及／到期的舊版是「該重寫」的工作，合法地留著。
            if status == "active" and brief_id not in current_brief_ids:
                findings.append(f"watch {wid}（「{label}」）還在等，來源敘事 {brief_id} 卻不是 {owner[0]} 的現行敘事"
                                "——換版或撤回後舊條件沒收")
        elif base.startswith("reading:"):
            if ledgers is None:
                continue
            examined += 1
            reading_id = base[len("reading:"):]
            node = str(watch.get("node") or "")
            record = next((r for r in (ledgers.get(node) or {}).get("records", [])
                           if r.reading_id == reading_id), None)
            if record is None:
                findings.append(f"watch {wid}（「{label}」）的 disproof_ref 指向讀圖 {reading_id}，"
                                f"節點 {node or '（沒寫 node）'} 的 ledger 裡沒有這一份")
                continue
            entries = tuple(record.disproof or ())
            if not 1 <= index <= len(entries) or disproof.normalize(entries[index - 1].condition) != text:
                findings.append(f"watch {wid}（「{label}」）的 disproof_ref={ref} 在讀圖的 disproof[] 對不到它的條件")
            # 比的是**同一個單位**的現行那一份（v3：層與插槽各自現行；v1／v2 紀錄都是 layer）
            current = ((ledgers.get(node) or {}).get("current") or {}).get(getattr(record, "unit", "layer"))
            if waiting and getattr(current, "reading_id", None) != reading_id:
                findings.append(f"watch {wid}（「{label}」）還在等，來源讀圖 {reading_id} 卻不是 {node} 的現行讀圖"
                                "——重讀後舊條件沒收")
        elif base.startswith("layer_note:"):
            # 層說明的主張（2026-10-07 S4a）：與讀圖同一套三問——指得回那一份、第 k 條就是它的條件、還在等的是現行那一份
            if layer_notes is None:
                continue
            examined += 1
            note_id = base[len("layer_note:"):]
            node = str(watch.get("node") or "")
            record = next((r for r in (layer_notes.get(node) or {}).get("records", [])
                           if r.note_id == note_id), None)
            if record is None:
                findings.append(f"watch {wid}（「{label}」）的 disproof_ref 指向層說明 {note_id}，"
                                f"節點 {node or '（沒寫 node）'} 的 ledger 裡沒有這一份")
                continue
            claims = tuple(record.claims or ())
            if not 1 <= index <= len(claims) or disproof.normalize(claims[index - 1].condition) != text:
                findings.append(f"watch {wid}（「{label}」）的 disproof_ref={ref} 在層說明的 claims[] 對不到它的條件")
            current = (layer_notes.get(node) or {}).get("current")
            if waiting and getattr(current, "note_id", None) != note_id:
                findings.append(f"watch {wid}（「{label}」）還在等，來源層說明 {note_id} 卻不是 {node} 的現行層說明"
                                "——換版後舊條件沒收")
    return findings, soft, examined


# ---------------------------------------------------------------------------
# INV-4 — Queue liveness
# ---------------------------------------------------------------------------

#: 進行中狀態卡住多久算失聯。⚠ 這個門檻**本身**受 L14 約束：
#: 它若長期抓到 0 筆或抓到全部，就是恆滅／恆亮的閘門，該調整或拿掉。
_STALLED_DAYS = 14


def check_queue_liveness() -> AuditResult:
    """佇列裡的每一項都要有**下一個會動它的東西**。

    F-09～F-13 的共同形狀：東西進了佇列，但沒有任何 consumer 會取它，
    而佇列本身看起來很正常（L13 那次「78 筆 new 全躺在 pending」就是這個）。
    """
    def run() -> AuditResult:
        items = sources.todo_items()
        active = [i for i in items if not i.get("resolution")]
        # gate pointer 要解析得到「那個編號現在怎麼了」，所以查的是**全部**項目
        # （已 resolve 的正是我們要偵測的情況），不是只有 active。
        _todo_by_n = {int(i["n"]): i for i in items if i.get("n") is not None}
        findings: list[str] = []
        now = _now()
        stalled = 0

        for item in active:
            n = item.get("n")
            # 已 dispatch 但長期沒有進展
            status = item.get("dispatch_status")
            if status in {"queued", "researching"}:
                moved = _parse_dt(item.get("dispatch_updated_at")
                                  or item.get("dispatched_at"))
                if moved and (now - moved).days > _STALLED_DAYS:
                    stalled += 1
                    findings.append(
                        f"[{n}] dispatch_status={status} 已 {(now - moved).days} 天沒有更新"
                        "——它在佇列裡，但沒有東西在動它")
            # `awaiting_approval` 從前不在這個檢查裡，於是一張工單可以無限期停著
            # 而不被任何東西看見（2026-09-10 實測：[311]／[411] 的 gate 早已 resolve，
            # [129] 停了 28 天）。「在等人」不等於「可以無限期等」——INV-2 要求每個
            # 等待都有到期。判準跟著 pointer 走，不是跟著天數走：
            #   gate 還沒 resolve → 真的在等人，不報（人沒動不是系統失聯）
            #   gate 已 resolve   → 報：沒有東西會回頭動它
            #   說不出在等誰       → 報：沒有到期，也沒有 consumer（INV-4）
            if status == "awaiting_approval":
                from engine_b.todo import gate_pointer

                pointer = gate_pointer(item)
                gate = _todo_by_n.get(pointer["n"]) if pointer else None
                if pointer is None or gate is None:
                    findings.append(
                        f"[{n}] dispatch_status=awaiting_approval 但說不出在等哪個編號"
                        "——這個等待沒有到期，也沒有 consumer")
                elif gate.get("resolution"):
                    stalled += 1
                    findings.append(
                        f"[{n}] 等的 [{pointer['n']}] 已 {gate['resolution']}"
                        f"（{gate.get('resolved_at')}）——gate 已消失，工單卻還掛著")

            # 等待中卻沒有等待條件：等於沒有人會叫醒它
            waiting = item.get("waiting_on")
            if waiting and not isinstance(waiting, (str, list, dict)):
                findings.append(f"[{n}] waiting_on 型別異常：{type(waiting).__name__}")

        # 線索側：triaged_go 卻長期沒有前進。
        # 起算點是**最後一次進 pq1 的時間**（`leads.last_entered_pq1_at`：triage 與最後一次排回取較晚），
        # 不是 `first_seen`：fired watch 把 parked lead 重排回 pq1 時，lead 是「今天」才回到佇列的；
        # 用 first_seen 會把當天重排的 lead 全報成「27 天沒人取」（2026-09-09 實測 35 筆假警報）。
        # ⚠ 2026-09-26：原本讀 `triage.decided_at`，靠的是舊式排回會改寫它；2.9b 拿掉改寫後，今早排回的
        # `lead_55bd36e6…` 被報成「16 天沒人取」——改讀同一個定義。都沒有才退回 first_seen。
        from engine_b.leads import last_entered_pq1_at

        leads = sources.leads()
        stuck_leads = 0
        for lead_id, lead in leads.items():
            if lead.get("status") != "triaged_go":
                continue
            entered = (
                _parse_dt(last_entered_pq1_at(lead))
                or _parse_dt(lead.get("first_seen"))
            )
            if entered and (now - entered).days > _STALLED_DAYS:
                stuck_leads += 1
                findings.append(
                    f"線索 {lead_id[:22]}（{lead.get('source')}）triaged_go 已 "
                    f"{(now - entered).days} 天未進 pq1——PASS 了但沒有人取")

        # 等待 registry 側（Phase 1 Step 1.10）
        from engine_b import event_watch as ew
        from engine_b.todo import watch_id_of

        watches = sources.event_watches()
        watch_ids = {w.get("watch_id") for w in watches}
        review_ids = _open_review_ids(items)
        stuck_watches = 0
        for watch in watches:
            # T2 輪詢命中（2026-10-06）：daily 只掛、判定在互動——兩週沒人判定＝查了等於沒查（段 poll_hits_pending 沒有人取）
            for hit in ew.pending_hits(watch):
                hit_at = _parse_dt(hit.get("at"))
                if hit_at and (now - hit_at).days > _STALLED_DAYS:
                    stuck_watches += 1
                    findings.append(
                        f"watch {watch.get('watch_id', '?')} 的 T2 命中掛了 {(now - hit_at).days} 天還沒判定"
                        f"（{hit.get('title') or hit.get('url')}）——`python -m engine_b.watch_poll queue` → `judge`")
            if watch.get("kind") != ew.SEMANTIC_KIND:
                continue
            wid = watch.get("watch_id", "?")
            judgment = watch.get("judgment") or {}
            if watch.get("status") == "fired" and not judgment:
                woke = _parse_dt((watch.get("woken_by") or {}).get("at"))
                if woke and (now - woke).days > _STALLED_DAYS:
                    stuck_watches += 1
                    findings.append(
                        f"watch {wid}（「{_label(watch)}」）醒了 {(now - woke).days} 天還沒判定"
                        "——待檢沒有人取（`event_watch semantic-queue` → `judge`）")
            if (str(watch.get("source_ref") or "").startswith("brief:")
                    and judgment.get("touches") == "yes" and not judgment.get("handled")):
                # Phase 3 Step 3.4：敘事自己的反證被判觸及——接手的是 narrative_rewrite（research-drain）；
                # 兩週沒人重寫＝觸及後的等待消失了。
                touched_at = _parse_dt(judgment.get("at"))
                if touched_at and (now - touched_at).days > _STALLED_DAYS:
                    stuck_watches += 1
                    findings.append(
                        f"watch {wid}（敘事反證「{_label(watch)}」）判定觸及已 {(now - touched_at).days} 天，"
                        "那份敘事還沒重寫（narrative_rewrite 段沒有人取）")
            if (str(watch.get("source_ref") or "").startswith("thesis:")
                    and judgment.get("touches") == "yes" and not judgment.get("handled")):
                touched_at = _parse_dt(judgment.get("at"))
                if touched_at and now - touched_at > _TOUCHED_GRACE and wid not in review_ids:
                    stuck_watches += 1
                    findings.append(
                        f"watch {wid}（thesis 反證「{_label(watch)}」）判定觸及已 "
                        f"{int((now - touched_at).total_seconds() // 3600)} 小時，池裡沒有一筆未結案的 thesis 複查"
                        "接住它——觸及後的等待消失了（C3）")
        # Phase 3 Step 3.6（plan §5 第 6 點）：醒來／觸及的敘事來源 watch，「有去處」的另一半是候選板那一列帶著它。
        # 到期的那一種在 Expiry 查。候選板 artifact 讀不到＝沒檢查（照實寫），不是失敗。
        from engine_b.queue_segments import narrative_rewrite_state

        waiting = [w for w in watches if narrative_rewrite_state(w) in ("fired", "touched")]
        board_note = None
        if waiting:
            board_ctx = _board_context(now)
            board_note = board_ctx["note"]
            if board_note is None:
                for watch in waiting:
                    miss = _board_misses(watch, board_ctx)
                    if miss:
                        stuck_watches += 1
                        findings.append(miss)
        # 敘事連結斷了（來源收掉／觸及／到期）：它不是任何一筆 watch 的狀態，所以另查——斷了超過兩週還沒重寫
        # ＝那份敘事的反證依賴失聯；來源根本不存在＝連結指向沒有東西（INV-4：producer 指得出 consumer）。
        from engine_b.narrative_watches import link_breaks

        by_ref = {str(w.get("source_ref") or ""): w for w in watches}
        link_note = None
        try:
            briefs_now = sources.current_briefs()
        except Exception as exc:  # noqa: BLE001 — 讀不到＝沒檢查（照實寫），不是「沒有斷」
            briefs_now, link_note = [], f"敘事讀不到，連結斷沒檢查（{exc}）"
        for brk in link_breaks(briefs_now, watches=watches):
            source = by_ref.get(brk["link_source_ref"]) or {}
            since = (_parse_dt((source.get("closed") or {}).get("at")) or _parse_dt(source.get("expired_at"))
                     or _parse_dt((source.get("judgment") or {}).get("at")))
            if source.get("watch_id") and str(source.get("watch_id")) in review_ids:
                # 來源被判觸及／到期、而池裡有一筆未結案的 thesis 複查接著它——球在使用者手上，不是敘事沒人取
                # （與 C3、awaiting_approval 同一個原則；research-drain ⓑ′ 也說先看來源那一邊的處置）。
                continue
            if brk.get("reason") == "missing":
                stuck_watches += 1
                findings.append(f"{brk['ticker']} 的敘事 {brk['brief_id']} 第 {brk['index']} 條連到 "
                                f"{brk['link_source_ref']}，但沒有任何 watch 用這個來源鍵——連結指向沒有東西")
            elif since and (now - since).days > _STALLED_DAYS:
                stuck_watches += 1
                findings.append(f"{brk['ticker']} 的敘事連結 {brk['link_source_ref']}（{brk.get('label')}）已 "
                                f"{(now - since).days} 天，敘事還沒重寫（narrative_rewrite 段沒有人取）")
        for item in active:
            if item.get("type") == "watch_decision" and watch_id_of(item) not in watch_ids:
                findings.append(
                    f"[{item.get('n')}] watch_decision 指向不存在的 watch {watch_id_of(item)}"
                    "——go／drop／續等都沒有東西可寫")

        examined = len(active) + sum(1 for l in leads.values()
                                     if l.get("status") == "triaged_go") + len(watches)
        if findings:
            return fail("QueueLiveness",
                        f"{len(findings)} 項在佇列中失聯"
                        f"（待辦 {stalled}／線索 {stuck_leads}／等待 {stuck_watches}）",
                        _clip(findings), examined)
        unchecked_note = (f"｜⚠ {len(waiting)} 筆該重寫的敘事 watch 沒檢查候選板是否帶著（{board_note}）"
                          if waiting and board_note else "") + (f"｜⚠ {link_note}" if link_note else "")
        return ok("QueueLiveness",
                  f"{examined} 項進行中工作全部在 {_STALLED_DAYS} 天內有進展{unchecked_note}", examined)

    return _guard("QueueLiveness", run)


# ---------------------------------------------------------------------------
# INV-4 — Queue segments（佇列段序的封閉字彙）
# ---------------------------------------------------------------------------

def _graph_holes() -> tuple[int | None, str | None]:
    """走圖九型裡有命中的型別數（`graph_holes` 段；Phase 2 Step 2.6，Phase 3 Step 3.1a 改計數語意）。

    計數規則只住 `engine_b.queue_segments.graph_holes_count`——心跳讀 artifact 也呼叫同一個函式。

    ⚠ **直接跑走圖的 authority**（`query.graph_walk.collect()`：圖＋讀圖 ledger＋leads），不讀 `graph_walk`
    state artifact——那是 derived cache，稽核讀它等於讓結論取決於「有沒有人 materialize 過」
    （原 `coverage_gaps` 注入給 `None` 的同一個理由；那時是乾脆不讀，所以三段在稽核裡永遠「未讀到」）。
    圖沒開就回 `(None, 原因)`，不寫 0（INV-3）。
    """
    try:
        from query.graph_walk import collect
    except Exception as exc:  # noqa: BLE001
        return None, f"graph_holes：走圖載入失敗 {type(exc).__name__}"
    try:
        result = collect()
    except Exception as exc:  # noqa: BLE001 — 圖沒開不是「沒有洞」
        return None, f"graph_holes：讀不到圖（{type(exc).__name__}）"
    from engine_b.queue_segments import graph_holes_count

    absent = [q["key"] for q in result["questions"] if q.get("absence")]
    return (graph_holes_count(result["questions"]),
            (f"graph_holes：{'、'.join(absent)} 這次沒讀到（不計入）" if absent else None))


def _forward_view_backlog() -> tuple[int | None, str | None]:
    """tracked 標的中「單檔判讀 blocked 且仍有未 settled blocker」的檔數。

    authority 是 materialize 出來的 analyst view artifact（不是 request path 重算）。
    讀不到就回 `(None, 原因)`——寫 0 會把「沒讀到」偽裝成「沒有工作」（INV-3）。
    """
    try:
        from webapp.store import ArtifactStore

        rows = list(ArtifactStore().read_all())
    except Exception as exc:  # noqa: BLE001
        return None, f"analyst view artifact 讀不到：{type(exc).__name__}"
    if not rows:
        return None, "尚無 materialized analyst view"
    count = 0
    for _ticker, payload, _fresh, _reason in rows:
        if payload is None:
            continue
        readiness = payload.get("readiness") or {}
        if readiness.get("state") != "blocked":
            continue
        details = readiness.get("blocker_details") or []
        if any(not d.get("settled") for d in details):
            count += 1
    return count, None


def check_queue_segments() -> AuditResult:
    """佇列裡每一種「有工作」的狀態，都必須對得到一個登記了 consumer 的段。

    這是 QueueLiveness 的補集：那一條問「進了佇列的東西有沒有在動」，本條問
    「有工作的狀態**有沒有進任何佇列**」。2026-09-08 實測 39 個 fired watch 與 27 檔
    forward view backlog 都是第二種——佇列看起來很乾淨，因為它們根本不在佇列的定義裡。
    段序是封閉字彙（`engine_b/queue_segments.py`）；資料裡出現分不到段的狀態就 FAIL，
    修法是去那裡登記 consumer，不是在這裡放寬。
    """
    def run() -> AuditResult:
        from engine_b import queue_segments as qs

        leads_map = sources.leads()
        watches = sources.event_watches()
        items = sources.todo_items()
        forward, forward_note = _forward_view_backlog()
        # ⚠ 2026-09-22（Phase 0 Step 0a.1）：原本這裡還會開 Decision Store 算「只需 reassess」
        # 的 pq2 編號餵段 2。reassess 隨 decision_lab 研究側退役，段 2 已從封閉字彙移除，
        # 所以這裡連 Decision Store 都不必開——稽核不再依賴一個凍結中的 authority。
        holes, holes_note = _graph_holes()
        # Phase 3 Step 3.6：敘事連結的反證來源已換版——與心跳、候選推導同一個判定（`narrative_watches.link_breaks`）。
        from engine_b.narrative_watches import link_breaks

        try:
            breaks, breaks_note = link_breaks(sources.current_briefs(), watches=watches), None
        except Exception as exc:  # noqa: BLE001 — 讀不到＝未讀到（照實寫），不是 0
            breaks, breaks_note = [], f"敘事連結斷未讀到（{exc}），narrative_rewrite 不含它"
        observation = qs.observe(
            leads=leads_map,
            watches=watches,
            todo_items=items,
            forward_view_backlog=forward,
            graph_holes=holes,
            narrative_link_breaks=breaks,
        )
        examined = len(leads_map) + len(watches) + len(items)
        findings = list(observation["unmapped"])
        notes = [n for n in (forward_note, holes_note, breaks_note) if n]
        counts = "；".join(
            f"{seg['key']}={'未讀到' if seg['count'] is None else seg['count']}"
            for seg in observation["segments"]
        )
        if findings:
            return fail(
                "QueueSegments",
                f"{len(findings)} 筆狀態分不到任何段——新工作類型沒有 consumer（{counts}）",
                _clip(findings), examined,
            )
        summary = counts + (f"｜未讀到：{'；'.join(notes)}" if notes else "")
        return ok("QueueSegments", summary, examined)

    return _guard("QueueSegments", run)


# ---------------------------------------------------------------------------
# INV-6 — Provenance / Lineage
# ---------------------------------------------------------------------------

def check_evidence_provenance() -> AuditResult:
    """**每個非 None 的 score 都列得出 EvidenceRef。**

    F-36：分數有值但講不出憑什麼，等於把研究判斷洗成了無來源的數字。
    `AlphaSignal` 的契約在建構時就擋這件事；本 check 驗的是**落地的檔案**
    也仍然成立（契約在記憶體裡守得住，序列化後被人手改就不一定）。
    """
    def run() -> AuditResult:
        signals = sources.alpha_signals()
        if not signals:
            raise SourceUnavailable("library/private/alpha/ 下沒有已產出的 AlphaSignal")
        findings: list[str] = []
        examined = 0
        for name, payload in signals:
            components = payload.get("model_components") or {}
            scores = payload.get("scores") or {
                k.removesuffix("_score"): v for k, v in payload.items()
                if k.endswith("_score")
            }
            for axis, score in scores.items():
                if score is None:
                    continue
                examined += 1
                trace_id = score.get("trace_id") if isinstance(score, dict) else None
                if not trace_id:
                    findings.append(f"{name} 的 {axis} 有值但沒有 trace_id")
                    continue
                component = components.get(trace_id)
                if component is None:
                    findings.append(
                        f"{name} 的 {axis} 指向 trace {trace_id}，但檔案裡沒有這個 component")
                elif not (component.get("evidence_refs") or ()):
                    findings.append(
                        f"{name} 的 {axis} 有值（{score.get('effective')}）但 "
                        f"trace {trace_id} 的 evidence_refs 是空的")
        if findings:
            return fail("EvidenceProvenance", f"{len(findings)} 個分數講不出憑什麼",
                        _clip(findings), examined)
        return ok("EvidenceProvenance",
                  f"{len(signals)} 份 signal 的 {examined} 個分數全部指得回證據", examined)

    return _guard("EvidenceProvenance", run)


def check_alpha_lineage() -> AuditResult:
    """`research_context_digest` 必須解析得到實際的 ResearchContext。

    ⚠ 目前 ResearchContext **尚未持久化**——所以這個 check 能驗的只有
    「digest 欄位存在且格式正確」。那不是完整的 lineage，必須明說。
    L11-5：能驗到哪就說到哪，不得把「我只驗了格式」寫成「lineage 完整」。
    """
    def run() -> AuditResult:
        signals = sources.alpha_signals()
        if not signals:
            raise SourceUnavailable("library/private/alpha/ 下沒有已產出的 AlphaSignal")
        store = ROOT / "library" / "private" / "alpha" / "contexts"
        findings: list[str] = []
        examined = 0
        for name, payload in signals:
            digest = payload.get("research_context_digest")
            examined += 1
            if not digest:
                findings.append(f"{name} 沒有 research_context_digest——無從得知它是對哪份資料做的")
            elif not str(digest).startswith("sha256:"):
                findings.append(f"{name} 的 digest 格式異常：{digest!r}")
            elif store.exists() and not list(store.glob(f"*{str(digest)[7:19]}*")):
                findings.append(f"{name} 的 context {digest[:24]} 在 contexts/ 找不到")
        if findings:
            return fail("AlphaLineage", f"{len(findings)} 份 signal 追不回它的 context",
                        _clip(findings), examined)
        note = () if store.exists() else (
            "⚠ ResearchContext 尚未持久化（無 contexts/ 目錄），"
            "本次只驗了 digest 存在與格式——**不等於 lineage 完整**。"
            "⚠ 這個缺口與 as-of 投影無關（投影已於 Phase 6 落地並由 PointInTime "
            "check 驗證）：缺的是把 ResearchContext 落地成可解析的檔案。",)
        return ok("AlphaLineage", f"{examined} 份 signal 都帶 context digest", examined, note)

    return _guard("AlphaLineage", run)


def check_point_in_time() -> AuditResult:
    """**as-of 投影不得偷看未來**，且回填的日期指得回一手出處。

    三件會 FAIL 的事，全部是「邏輯上不可能」而不是「數字不夠好」：

    1. **投影漏出未來證據**——實跑一次 as-of 投影，若任何 `EvidenceRef` 的
       `published_at` 晚於 `as_of`，回測就在看未來。這是本 check 的核心，
       也是唯一在**活資料**上驗 anti-lookahead 的地方。
    2. **`published_at` 晚於 `retrieved_at`**——我們不可能在它發表前就抓到它。
    3. **回填的 basis 與現值脫鉤**——`url_path` 重導不出來，或有東西把值改掉了
       而 basis 還留著（`loader/source_dating.py::audit_backfills`）。

    ⚠ **覆蓋率只報告，不當 FAIL 條件。** 「published_at 覆蓋 ≥95%」是 ROADMAP 的
    交付目標，不是不變式：把它寫成 gate 等於新增一個從未被量測過的閘門（L14），
    而它擋下的會是「還沒補完」而不是「答錯了」。真正危險的是**填了但填錯**，
    那三件事上面都攔了。13 份未定日文件仍逐筆列出——沒有到期的等待會沉底，
    沒有現形的缺口也一樣。
    """
    def run() -> AuditResult:
        from loader.source_dating import audit_backfills

        findings: list[str] = []
        soft: list[str] = []
        examined = 0

        docs = sources.graph_rows(
            "MATCH (d:SourceDoc) RETURN count(d) AS total, "
            "count(d.published_at) AS dated")[0]
        assertions = sources.graph_rows("MATCH (a:EdgeAssertion) RETURN count(a) AS n")[0]
        datable = sources.graph_rows(
            "MATCH (a:EdgeAssertion)-[:CITES]->(d:SourceDoc) "
            "WHERE d.published_at IS NOT NULL RETURN count(DISTINCT a) AS n")[0]
        examined += int(docs["total"]) + int(assertions["n"])

        # ① 不可能的時間順序
        impossible = sources.graph_rows(
            "MATCH (d:SourceDoc) WHERE d.published_at IS NOT NULL "
            "  AND d.retrieved_at IS NOT NULL AND d.published_at > d.retrieved_at "
            "RETURN d.id AS id, d.published_at AS p, d.retrieved_at AS r")
        findings.extend(
            f"{row['id']} 的 published_at={row['p']} 晚於 retrieved_at={row['r']}"
            "——不可能在它發表之前就抓到它"
            for row in impossible)

        # ② 回填的 provenance 抽查
        backfilled = sources.graph_rows(
            "MATCH (d:SourceDoc) WHERE d.published_at_method IS NOT NULL "
            "RETURN d.id AS id, d.url AS url, d.published_at AS published_at, "
            "       d.published_at_method AS method, d.published_at_basis AS basis, "
            "       d.published_at_backfilled AS backfilled")
        examined += len(backfilled)
        findings.extend(audit_backfills(backfilled))

        # ③ 活資料上實跑一次 as-of 投影，驗它沒有漏出未來
        leaked = _projection_leaks()
        findings.extend(leaked)

        undated = sources.graph_rows(
            "MATCH (d:SourceDoc) WHERE d.published_at IS NULL "
            "OPTIONAL MATCH (a:EdgeAssertion)-[:CITES]->(d) "
            "RETURN d.id AS id, count(DISTINCT a) AS n ORDER BY n DESC, d.id")
        if undated:
            soft.append(
                f"⚠ {len(undated)} 份 SourceDoc 仍未定日，擋住 "
                f"{sum(int(r['n']) for r in undated)} 條 EdgeAssertion——"
                "它們在任何 as-of 查詢裡都會被排除並計為 undated（L11-5：留 null "
                "比猜一個日期誠實）。查證：python scripts/backfill_source_dating.py --list")
            soft.extend(f"未定日：{r['id']}（擋住 {r['n']} 條）" for r in undated[:6])

        summary = (
            f"SourceDoc published_at {docs['dated']}/{docs['total']}"
            f"（{int(docs['dated']) / max(int(docs['total']), 1):.1%}）"
            f"；EdgeAssertion 可定日 {datable['n']}/{assertions['n']}"
            f"（{int(datable['n']) / max(int(assertions['n']), 1):.1%}）"
            f"；已回填 {len(backfilled)} 份且 basis 全部指得回去"
        )
        if findings:
            return fail("PointInTime", f"{len(findings)} 筆 point-in-time 違規",
                        _clip(findings + soft), examined)
        return ok("PointInTime", summary, examined, _clip(soft))

    return _guard("PointInTime", run)


def _projection_leaks() -> list[str]:
    """實跑一次 as-of 投影，回傳漏出未來的證據（空 list ＝ 沒漏）。

    ⚠ 這裡刻意**不 mock**：型別與測試已經在 `tests/test_alpha_as_of_projection.py`
    守過純函式，本 check 要答的是另一個問題——**線上這份圖、這個 provider，
    今天真的沒有漏嗎**。L13：元件會動不等於端到端有效。
    """
    from datetime import timedelta

    from alpha.errors import PointInTimeUnsupported

    bounds = sources.graph_rows(
        "MATCH (d:SourceDoc) WHERE d.published_at IS NOT NULL "
        "RETURN min(d.published_at) AS lo, max(d.published_at) AS hi")[0]
    if not bounds.get("hi"):
        raise SourceUnavailable("圖上沒有任何 published_at——無從驗 as-of 投影")

    from query.bottleneck import latest_possible_date

    newest = latest_possible_date(bounds["hi"])
    oldest = latest_possible_date(bounds["lo"])
    if newest is None or oldest is None:
        raise SourceUnavailable(f"published_at 邊界讀不成日期：{bounds}")
    # 取一個**中間**的時點：太早會被保險絲擋下（那是正確行為但驗不到漏水），
    # 太晚則沒有未來證據可漏。
    as_of = max(oldest, newest - timedelta(days=60))

    from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider

    with sources.graph_session() as session:
        class _Driver:
            def session(self):  # noqa: D401 — 借用既有 session，不另開連線
                from contextlib import nullcontext
                return nullcontext(session)

        provider = Neo4jGraphResearchProvider(driver=_Driver())
        try:
            rows = provider.get_bottlenecks(as_of=as_of)
        except PointInTimeUnsupported as exc:
            raise SourceUnavailable(f"as-of 投影拒絕了 {as_of}：{exc}") from exc

    leaks: list[str] = []
    for row in rows:
        for ref in row.evidence:
            if ref.published_at is None:
                leaks.append(
                    f"as_of={as_of} 的投影裡有未定日證據 {ref.ref}"
                    "——未定日必須在投影前就被排除，留在裡面等於當成過去")
            elif ref.published_at > as_of:
                leaks.append(
                    f"as_of={as_of} 的投影漏出 {ref.ref}"
                    f"（published_at={ref.published_at}）——回測在看未來")
    return leaks


# ---------------------------------------------------------------------------
# INV-5 — GateDiscrimination
# ---------------------------------------------------------------------------

#: 恆亮門檻：觸發率高到這個地步的 gate 幾乎不鑑別任何東西（F-26 的「恆亮」）。
GATE_ALWAYS_ON = 0.95
#: 不會滅門檻：曾經響過、而且**之後還有過評估**的 cohort 裡，清除率低到這個地步
#: 就不是閘門是牆（F-26 的「不會滅」）。
GATE_NEVER_CLEARS = 0.05
#: 樣本地板。⚠ 這兩個數字是為了**不讓本 audit 自己變成恆亮閘門**：3 個 cohort 的
#: 0% 清除率什麼都不代表（2026-09-07 實測：identity_unresolved 的 9 個 cohort 有 6 個
#: 只被評估過一次，根本沒有清除的機會）。樣本不足一律報 insufficient_data，不判好壞。
GATE_MIN_ASSESSMENTS = 30
GATE_MIN_COHORTS = 5


def check_gate_discrimination() -> AuditResult:
    """每個 gate 的**觸發率**與**清除率**——偵測恆亮（近 100%）與不會滅（近 0%）。

    F-26 的教訓是 `axis_ceiling` 這種「從未被驗證卻在決定資本」的機制；那一層已整組
    移除，但 gate 本身沒有消失——現在真正在擋研究流程的是 coverage／paper／live 三條
    lane 的 blocker。它們有 269 份帶時戳的 assessment，**是可以被量的**。

    兩個率的分母刻意不同，因為它們問的是不同的問題：

    - **觸發率** = 出現在幾份 assessment 裡 ÷ 全部 assessment。近 100% ＝零鑑別力。
    - **清除率** = 曾經響過、**且之後還有過評估**的 cohort 裡有幾個後來不再響。
      ⚠ 分母必須是「有機會被清除的」——用「曾經響過」當分母會把「只被評估過一次」
      算成「從未清除」，那是把沒發生讀成失敗（L13-2）。

    ⚠ 本 check 自己也受 INV-5 約束：樣本不足的 gate 一律 `insufficient_data` 並列進
    findings，**不當作通過**；未登記在 `config/decision_blockers.json` 的 code 也是
    finding（L16：有行為後果的字彙必須被強制）。
    """
    def run() -> AuditResult:
        from shared.blockers import get_blocker_registry

        history = sources.coverage_gate_history()
        registry = get_blocker_registry()
        total = len(history)
        by_cohort: dict[str, list[dict]] = {}
        for row in history:
            by_cohort.setdefault(str(row["cohort_id"]), []).append(row)

        findings: list[str] = []
        thin: list[str] = []
        measured = 0
        for lane in ("coverage", "paper", "live"):
            fired: dict[str, int] = {}
            opportunity: dict[str, set[str]] = {}
            cleared: dict[str, set[str]] = {}
            for row in history:
                for gate in row["lanes"][lane]:
                    fired[gate] = fired.get(gate, 0) + 1
            for cohort, sequence in by_cohort.items():
                lanes = [r["lanes"][lane] for r in sequence]
                for index, gates in enumerate(lanes):
                    later = lanes[index + 1:]
                    if not later:
                        continue                       # 沒有後續評估＝沒有清除的機會
                    for gate in gates:
                        opportunity.setdefault(gate, set()).add(cohort)
                        if any(gate not in future for future in later):
                            cleared.setdefault(gate, set()).add(cohort)
            for gate, count in sorted(fired.items(), key=lambda kv: -kv[1]):
                measured += 1
                name = f"{lane}:{gate}"
                if not registry.is_registered(gate):
                    findings.append(
                        f"{name} 不在 config/decision_blockers.json——"
                        "有行為後果的字彙未登記，打錯不會報錯只會靜默沉底（L16）")
                trigger = count / total
                chances = len(opportunity.get(gate, ()))
                clears = len(cleared.get(gate, ()))
                if total >= GATE_MIN_ASSESSMENTS and trigger >= GATE_ALWAYS_ON:
                    findings.append(
                        f"{name} 恆亮：{count}/{total}（{trigger:.1%}）份 assessment 都在響"
                        "——零鑑別力，它不是閘門是行政流程")
                if chances >= GATE_MIN_COHORTS and (clears / chances) <= GATE_NEVER_CLEARS:
                    findings.append(
                        f"{name} 不會滅：{chances} 個有機會清除的 cohort 只清掉 {clears} 個"
                        f"（{clears / chances:.1%}）——那是牆不是閘門")
                if chances < GATE_MIN_COHORTS:
                    thin.append(f"{name}（觸發 {trigger:.1%}，只有 {chances} 個 cohort 有清除機會）")
        judged = measured - len(thin)
        if thin:
            findings.append(
                f"⚠ {len(thin)}/{measured} 個 gate 樣本不足，清除率無從判斷（"
                f"<{GATE_MIN_COHORTS} 個 cohort 有過後續評估）——**不當作通過也不當作失敗**："
                + "、".join(sorted(thin)[:8]) + ("…" if len(thin) > 8 else ""))
        real = [f for f in findings if not f.startswith("⚠ ")]
        if real:
            return fail("GateDiscrimination",
                        f"{len(real)} 個 gate 沒有鑑別力（恆亮／不會滅／未登記）",
                        _clip([*real, *[f for f in findings if f.startswith("⚠ ")]], len(findings)),
                        measured)
        if judged == 0:
            # ⚠ 模組 docstring ③ 的同一條規則：一個**一個 gate 都判不動**的鑑別力檢查，
            # 鑑別力自己就是零。它會在報表上顯示成綠色的 PASS——那正是本 audit 要防的形狀。
            return skip("GateDiscrimination",
                        f"{measured} 個 gate 全部樣本不足（都 <{GATE_MIN_COHORTS} 個 cohort 有過"
                        f"後續評估）——觸發率量得到，清除率一個都量不到，不足以宣稱通過")
        return ok("GateDiscrimination",
                  f"三條 lane {measured} 個 gate 量過觸發率、其中 {judged} 個樣本夠也量得出清除率"
                  f"（{total} 份 assessment、{len(by_cohort)} 個 cohort）："
                  f"沒有恆亮（≥{GATE_ALWAYS_ON:.0%}）也沒有不會滅（≤{GATE_NEVER_CLEARS:.0%}）的",
                  measured, _clip(findings))

    return _guard("GateDiscrimination", run)


def check_decision_lineage() -> AuditResult:
    """每一筆 decision 的 `context_digest` 都要在 `context_bundles` 裡找得到。

    這是 point-in-time contract 的骨幹：舊 decision 永遠引用原 digest，
    解析不到就代表那筆決策**當時用了什麼 context 已經無從得知**。
    """
    def run() -> AuditResult:
        rows = sources.decision_rows(
            "select d.decision_id, d.cohort_id, d.context_digest, "
            "       (select count(*) from context_bundles b "
            "         where b.context_digest = d.context_digest) AS found "
            "from system_decisions d")
        findings = [
            f"decision {row['decision_id']}（{row['cohort_id']}）的 context "
            f"{str(row['context_digest'])[:20]} 在 context_bundles 找不到"
            "——那筆決策當時用了什麼資料已無從得知"
            for row in rows
            if not row.get("context_digest") or not row["found"]
        ]
        if findings:
            return fail("DecisionLineage", f"{len(findings)}/{len(rows)} 筆決策追不回 context",
                        _clip(findings), len(rows))
        return ok("DecisionLineage", f"{len(rows)} 筆決策全部追得回凍結的 context bundle",
                  len(rows))

    return _guard("DecisionLineage", run)
