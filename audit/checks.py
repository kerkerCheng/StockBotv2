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
from datetime import date, datetime, timezone
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

        # 同 URL 且**同 section** 的 SourceDoc。
        # ⚠ 同 URL 不同 section 是**設計**（一份年報拆 photonics／financials 兩節）。
        # 第一版忽略 section，12 組命中全是合法分段——同上，攔到的是格式。
        try:
            rows = sources.graph_rows(
                "MATCH (sd:SourceDoc) WHERE sd.url IS NOT NULL AND sd.url <> '' "
                "WITH sd.url AS url, coalesce(sd.section, '') AS section, "
                "     collect(sd.id) AS ids WHERE size(ids) > 1 "
                "RETURN url, section, ids")
            examined += len(rows)
            for row in rows:
                findings.append(
                    f"URL {row['url']} 的 section={row['section'] or '（無）'} "
                    f"有 {len(row['ids'])} 份 SourceDoc：{', '.join(row['ids'][:4])}"
                    "——同一份文件的同一節被入庫兩次")
        except SourceUnavailable as exc:
            findings.append(f"⚠ SourceDoc 面向未檢查：{exc}")

        hard = [f for f in findings if not f.startswith("⚠")]
        if hard:
            return fail("Duplicates", f"{len(hard)} 組識別符碰撞",
                        _clip(findings), examined)
        return ok("Duplicates", f"registry {len(reg.companies)} 家無 ticker／alias 碰撞",
                  examined, _clip(findings))

    return _guard("Duplicates", run)


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

def check_lifecycle() -> AuditResult:
    """terminal 狀態與 outcome 必須同進退；已 resolve 的 pq2 不得仍是 active。

    兩個來源：Decision Store 既有的 `lifecycle_invariant_violations()`
    （terminal 卻無 outcome／非 terminal 卻有 outcome），以及待辦池本身的
    resolution／resolved_at 一致性。
    """
    def run() -> AuditResult:
        findings: list[str] = []
        examined = 0

        with sources.decision_store() as store:
            violations = store.lifecycle_invariant_violations()
            rows = store._conn.execute(  # noqa: SLF001
                "select count(*) n from probe_lifecycle_epochs").fetchone()
            examined += int(rows["n"])
        for item in violations:
            findings.append(f"Decision lifecycle：{item}")

        items = sources.todo_items()
        examined += len(items)
        for item in items:
            n = item.get("n")
            has_resolution = bool(item.get("resolution"))
            has_time = bool(item.get("resolved_at"))
            if has_resolution != has_time:
                findings.append(
                    f"[{n}] resolution={item.get('resolution')!r} 與 "
                    f"resolved_at={item.get('resolved_at')!r} 不一致"
                    "（一個說結案了、一個說沒有）")

        if findings:
            return fail("Lifecycle", f"{len(findings)} 筆生命週期狀態自相矛盾",
                        _clip(findings), examined)
        return ok("Lifecycle", "lifecycle epoch 與待辦池結案狀態一致", examined)

    return _guard("Lifecycle", run)


def check_expiry() -> AuditResult:
    """**每一個等待都必須有到期。** 沒有到期的等待就是沉底。

    這是 [321] 定案的直接執行：`stalled`／`expired`／`unwatched` 之所以要被撈出來，
    是因為原本的 consumed-marker 沒有到期兜底，標的用完即靜默沉底
    （實測 50 筆有 10 筆已不可能再被喚醒）。
    """
    def run() -> AuditResult:
        watches = sources.event_watches()
        findings: list[str] = []
        now = _now()
        examined = 0
        expired_active = 0

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
            elif expires < now:
                expired_active += 1

        # 到期未處置：不算 FAIL（那是待辦，不是不變式違反），但必須現形
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
        if expired_active:
            soft.append(f"另有 {expired_active} 個 active watch 已過期待處置——"
                        "有到期就不算違反不變式，但等下去不會有事發生"
                        "（`engine_b.cli trace-backlog --needs-attention`）")
        if hard:
            return fail("Expiry", f"{len(hard)} 個等待沒有到期日",
                        _clip(hard + soft), examined)
        return ok("Expiry", f"{examined} 個進行中的等待全部有到期日",
                  examined, _clip(soft))

    return _guard("Expiry", run)


# ---------------------------------------------------------------------------
# INV-3 — Orphans
# ---------------------------------------------------------------------------

def check_orphans() -> AuditResult:
    """指標活著、被指的東西死了——而**沒有任何東西會叫**。

    2026-09-04 實測抓到的第一筆真實問題：daily 的 pq1 追源把證據寫進
    `library/raw/`、把路徑寫進 leads state，但 `publish_daily_state.py` 的
    pathset 只有四個 leads JSON。於是引用推上 origin、檔案留在本機，之後就沒了
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

        # ② watch → pq2 編號
        numbers = {item.get("n") for item in sources.todo_items()}
        for watch in sources.event_watches():
            wake = watch.get("wake_pq2")
            if wake is None:
                continue
            examined += 1
            if int(wake) not in numbers:
                findings.append(
                    f"watch {watch.get('watch_id')} 要喚醒 pq2 [{wake}]，"
                    "但待辦池裡沒有這個編號——醒了也沒有東西會接")

        # ③ 假設 → watch
        watch_ids = {w.get("watch_id") for w in sources.event_watches()}
        for hypothesis in sources.hypotheses():
            wid = hypothesis.get("watch_id")
            if not wid:
                continue
            examined += 1
            if wid not in watch_ids:
                findings.append(
                    f"假設 {hypothesis.get('hypothesis_id')} 綁的 watch {wid} 不存在"
                    "——沒有任何機制在等它被驗證")

        if findings:
            return fail("Orphans", f"{len(findings)} 個引用指向不存在的東西",
                        _clip(findings), examined)
        return ok("Orphans", f"{examined} 個跨檔引用全部解析得到", examined)

    return _guard("Orphans", run)


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
            # 等待中卻沒有等待條件：等於沒有人會叫醒它
            waiting = item.get("waiting_on")
            if waiting and not isinstance(waiting, (str, list, dict)):
                findings.append(f"[{n}] waiting_on 型別異常：{type(waiting).__name__}")

        # 線索側：triaged_go 卻長期沒有前進
        leads = sources.leads()
        stuck_leads = 0
        for lead_id, lead in leads.items():
            if lead.get("status") != "triaged_go":
                continue
            seen = _parse_dt(lead.get("first_seen"))
            if seen and (now - seen).days > _STALLED_DAYS:
                stuck_leads += 1
                findings.append(
                    f"線索 {lead_id[:22]}（{lead.get('source')}）triaged_go 已 "
                    f"{(now - seen).days} 天未進 pq1——PASS 了但沒有人取")

        examined = len(active) + sum(1 for l in leads.values()
                                     if l.get("status") == "triaged_go")
        if findings:
            return fail("QueueLiveness",
                        f"{len(findings)} 項在佇列中失聯超過 {_STALLED_DAYS} 天"
                        f"（待辦 {stalled}／線索 {stuck_leads}）",
                        _clip(findings), examined)
        return ok("QueueLiveness",
                  f"{examined} 項進行中工作全部在 {_STALLED_DAYS} 天內有進展", examined)

    return _guard("QueueLiveness", run)


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
