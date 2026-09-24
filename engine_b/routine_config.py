"""Daily routine 的 deterministic budget 與 tracked-universe 設定。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "daily_routine.json"
DEFAULT_LIFECYCLE = ROOT / "thesis" / "lifecycle.json"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1":
        raise ValueError("daily routine config schema_version 必須是 1")
    pq1 = payload.get("pq1")
    if not isinstance(pq1, dict):
        raise ValueError("daily routine config 缺少 pq1")
    limit = pq1.get("drain_limit_per_run")
    # ⚠ **0 自 2026-09-17（Phase 2 Step 2.2／D12）起合法，意思是「daily 不做研究」。**
    # 它原本被拒絕，理由是「0 會被讀成無上限」——那是一個表示承載兩種語意（L12）。
    # 修法不是放寬也不是收緊，是**先分開再各自定規則**：
    #   0        → 研究層關閉（研究只在互動 session；D12）
    #   1..20    → daily 每輪最多做幾件研究
    #   其餘     → 仍然拒絕（負數、布林、非整數、>20）
    # 「0 不得被讀成無上限」這道保護沒有消失，只是從「拒絕這個值」換成**證明它選不出任何工作**
    # ——見 `tests/test_engine_b_cli.py::test_drain_limit_zero_selects_nothing_of_every_kind`。
    # 那比原本強：原本只擋住寫下 0，擋不住任何一個把 limit 當「沒有上限」用的消費端。
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 20:
        raise ValueError("pq1.drain_limit_per_run 必須是 0..20 的整數（0＝daily 不做研究）")
    # 分類層（D12 三層的中間那層）的每日硬上限（Phase 2 Step 2.3，2026-09-19）。
    # ⚠ **缺 `triage` 整段是合法的**：它是後加的，舊 config 仍要能載入——
    # 消費端拿不到就用 `DEFAULT_TRIAGE_LIMIT`。但**寫了就要合法**，
    # 打錯的數字比沒有更危險（它看起來像有 cap）。
    triage = payload.get("triage")
    if triage is not None:
        if not isinstance(triage, dict):
            raise ValueError("daily routine config 的 triage 必須是 object")
        limit = triage.get("daily_limit")
        # 0 ＝ daily 不做分類（與 pq1.drain_limit_per_run 的 0 同形，理由見上）。
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 200:
            raise ValueError("triage.daily_limit 必須是 0..200 的整數（0＝daily 不做分類）")
    sources = pq1.get("tracked_ticker_sources")
    if not isinstance(sources, dict):
        raise ValueError("pq1.tracked_ticker_sources 必須是 object")
    for key in ("thesis_lifecycle", "decision_cohorts", "theme_core_companies"):
        if not isinstance(sources.get(key), bool):
            raise ValueError(f"tracked_ticker_sources.{key} 必須是 boolean")
    return payload


def _positive_number(block: Mapping[str, Any], key: str, where: str, *, allow_zero: bool = False) -> float:
    value = block.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where}.{key} 必須是數字")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{where}.{key} 必須 {'≥' if allow_zero else '>'} 0")
    return float(value)


def load_theme_scan(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """`theme_scan` 區塊（Phase 1 Step 1.8）：`nudge_after_days` 必須是 1..60 的整數。缺整段 → 預設 7。"""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    block = payload.get("theme_scan")
    if block is None:
        return {"nudge_after_days": 7}
    if not isinstance(block, dict):
        raise ValueError("daily routine config 的 theme_scan 必須是 object")
    days = block.get("nudge_after_days")
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 60:
        raise ValueError("theme_scan.nudge_after_days 必須是 1..60 的整數")
    return {"nudge_after_days": days}


def load_schedule(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """`schedule` 區塊——**排程時間的唯一來源**（Phase 1 Step 1.2a，A1）。

    Windows 工作由 `scripts/register_daily_task.py` 從這裡導出，`crons/daily_task.py` 每次開跑
    再拿實際註冊值與這裡比對（2026-09-12 事故：兩個 SSOT 沒有機械連結，只改了排程器）。
    寫錯就 raise——打錯的時間比沒有更危險，它看起來像有排程。
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    schedule = payload.get("schedule")
    if not isinstance(schedule, dict):
        raise ValueError("daily routine config 缺 schedule 區塊")
    tz = schedule.get("timezone")
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(str(tz))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"schedule.timezone 不是合法時區：{tz!r}") from exc
    raw = str(schedule.get("daily_local_time") or "")
    parts = raw.split(":")
    if len(parts) != 2 or not all(p.isdigit() and len(p) == 2 for p in parts) \
            or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
        raise ValueError(f"schedule.daily_local_time 必須是 HH:MM：{raw!r}")
    if not str(schedule.get("task_name") or "").strip():
        raise ValueError("schedule.task_name 不可為空")
    limit = schedule.get("execution_time_limit_minutes")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 30 <= limit <= 720:
        raise ValueError("schedule.execution_time_limit_minutes 必須是 30..720 的整數")
    _positive_number(schedule, "expected_duration_minutes", "schedule")
    _positive_number(schedule, "guard_margin_minutes", "schedule", allow_zero=True)
    _positive_number(schedule, "harvest_stale_hours", "schedule")
    return schedule


#: `llm.executor` 的封閉字彙。一個開關同時管 triage 與語意預篩，也是 R2-a 的回滾開關。
LLM_EXECUTORS = ("none", "claude")


def load_llm(path: Path = DEFAULT_CONFIG, *, repo_root: Path = ROOT) -> dict[str, Any]:
    """`llm` 區塊（C6）：daily 裡 LLM 步驟的執行者、模型、timeout 與 cwd。

    ⚠ `cwd` 必須在 repo 之外（第 4 輪 N4-2）：cwd 在 git 工作樹裡時 CLI 會往上找到 `.git` 跑 git
    取 gitStatus、並載入使用者的自動記憶——那些是沒記進收據、卻會影響輸出的輸入（L12）。
    `library/private/` 也在工作樹內，不算。違反就 raise（fail closed），不自動改到別處。
    回傳的 dict 另帶解析好的 `cwd_path`／`claude_path_resolved`。
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    llm = payload.get("llm")
    if not isinstance(llm, dict):
        raise ValueError("daily routine config 缺 llm 區塊")
    executor = llm.get("executor")
    if executor not in LLM_EXECUTORS:
        raise ValueError(f"llm.executor 必須是 {LLM_EXECUTORS} 之一：{executor!r}")
    model = llm.get("claude_model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("llm.claude_model 不可為空（模型只住這裡）")
    for key in ("triage_timeout_minutes", "prescreen_timeout_minutes"):
        _positive_number(llm, key, "llm")
    for key in ("triage_chunk_size", "prescreen_chunk_size"):
        chunk = llm.get(key)
        if isinstance(chunk, bool) or not isinstance(chunk, int) or chunk < 1:
            raise ValueError(f"llm.{key} 必須是 ≥1 的整數")
    import os

    raw_cwd = llm.get("cwd")
    if raw_cwd is None:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        cwd = Path(base) / "StockBotv2" / "llm_cwd"
    elif isinstance(raw_cwd, str) and raw_cwd.strip():
        cwd = Path(os.path.expandvars(raw_cwd))
    else:
        raise ValueError("llm.cwd 必須是 null 或非空字串")
    cwd = cwd.resolve()
    repo = repo_root.resolve()
    if cwd == repo or repo in cwd.parents:
        raise ValueError(f"llm.cwd 必須在 repo 之外（現為 {cwd}）——工作樹內 CLI 會跑 git、載入自動記憶")
    raw_claude = llm.get("claude_path")
    if raw_claude is None:
        claude = Path.home() / ".local" / "bin" / "claude.exe"
    elif isinstance(raw_claude, str) and raw_claude.strip():
        claude = Path(os.path.expandvars(raw_claude))
    else:
        raise ValueError("llm.claude_path 必須是 null 或非空字串")
    resolved = dict(llm)
    resolved["cwd_path"] = cwd
    resolved["claude_path_resolved"] = claude
    return resolved


#: 分類層每日上限的預設值——**config 沒寫 `triage` 整段時用它**。
#: ⚠ 刻意不是「無上限」：拿不到設定時退回無上限，等於在最不確定的時候拆掉煞車。
DEFAULT_TRIAGE_LIMIT = 30


def triage_daily_limit(path: Path = DEFAULT_CONFIG) -> int:
    """分類層每輪最多 triage 幾則。讀不到設定檔或沒寫 `triage` 就回 `DEFAULT_TRIAGE_LIMIT`。

    ⚠ **讀不到不等於沒有上限**（見上）。config 寫了但不合法時 `load_config` 會 raise，
    那是對的——打錯的數字比沒有更危險，因為它看起來像有 cap。
    """
    try:
        payload = load_config(path)
    except (OSError, ValueError):
        return DEFAULT_TRIAGE_LIMIT
    triage = payload.get("triage")
    if not isinstance(triage, dict):
        return DEFAULT_TRIAGE_LIMIT
    limit = triage.get("daily_limit")
    if isinstance(limit, bool) or not isinstance(limit, int):
        return DEFAULT_TRIAGE_LIMIT
    return limit


def lifecycle_tickers(path: Path = DEFAULT_LIFECYCLE) -> frozenset[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    tickers: set[str] = set()
    for entry in payload.values() if isinstance(payload, dict) else ():
        if not isinstance(entry, Mapping) or entry.get("status") == "retired":
            continue
        ticker = str(entry.get("ticker") or "").strip().upper()
        if ticker:
            tickers.add(ticker)
    return frozenset(tickers)


def theme_core_tickers() -> frozenset[str]:
    """`config/themes.txt` 每個主題的「核心公司」。

    加這個來源的理由：先前 tracked 只由 thesis lifecycle ＋ 未結案 cohort 導出，
    於是 COHR／LITE 這種「已列為 cpo 主題核心公司、EDGAR watch 也在抓它們的 filing」
    的標的，因為沒有 active cohort 而在排序上等於未追蹤——2026-08-12 實測，Lumentum
    當日的 tier-1 8-K 因此只拿到 6 分，被一則已兩度判定無用的總體評論（12 分）擠出
    當輪 pq1。harvest 花錢抓進來、排序又把它壓下去，是兩個 authority 互相矛盾。
    """
    try:
        from engine_b.themes import load_themes

        return frozenset(
            ticker.strip().upper()
            for theme in load_themes().values()
            for ticker in theme.tickers
            if ticker.strip()
        )
    except Exception:
        # themes.txt 缺失或格式錯誤時安全降級；其餘來源仍可提供 tracked universe。
        return frozenset()


def us_edgar_candidates(tickers: Iterable[str]) -> frozenset[str]:
    """從 tracked universe 篩出「SEC EDGAR 可能有申報」的 ticker。

    EDGAR 只有美國註冊人；外國發行人（IQE.L、SIVE.ST、2330.TW）放進 watch 只會每天
    產生一筆找不到 CIK 的 fetch_failed。兩個確定性排除訊號：

    1. 交易所後綴（含 `.`）——Yahoo／provider 對非美國掛牌一律加後綴。
    2. registry 的 `market_currency` 非 USD。

    刻意不用 `execution_venue`：registry 中 AVGO／NVDA／TSLA／CCXI 等美股該欄皆為
    None，拿它當判準會把真正的美股全部濾掉。

    已知限制：美股本身帶 `.` 的（如 BRK.B）會被誤排除。目前 universe 沒有這種標的；
    真的需要時走 `extra_tickers` 手動補，而不是放寬這條規則。
    """
    from identity.registry import get_registry

    registry = get_registry()
    out: set[str] = set()
    for raw in tickers:
        ticker = str(raw or "").strip().upper()
        if not ticker or "." in ticker:
            continue
        company_id = registry.company_id_for_ticker(ticker)
        company = registry.company(company_id) if company_id else None
        currency = str(getattr(company, "market_currency", None) or "").upper()
        if currency and currency != "USD":
            continue
        out.add(ticker)
    return frozenset(out)


def edgar_watch_tickers(
    watch: Mapping[str, Any],
    *,
    tracked: frozenset[str] = frozenset(),
) -> list[str]:
    """EDGAR watch 的實際監看清單。

    `derive_from_tracked` 開啟時，把 tracked universe 中的美股**併入**手動清單，而不是
    取代它。理由是 fail-safe：derivation 的上游（thesis lifecycle、Decision store、
    themes.txt）任何一個暫時讀不到都會讓 tracked 縮小，若採取代語意就會靜默停止監看
    既有標的——而漏掉的 filing 不會有人發現。手動清單因此是**下限**，derivation 只補
    「已追蹤卻沒 watcher」這一側的漂移（CCXI 與 META 就是這樣漏掉的，見 §10.11）。
    """
    manual = {str(t).strip().upper() for t in (watch.get("tickers") or []) if str(t).strip()}
    if not watch.get("derive_from_tracked"):
        return sorted(manual)
    return sorted(manual | us_edgar_candidates(tracked))


def mops_watch_tickers(
    watch: Mapping[str, Any],
    *,
    registry_tickers: frozenset[str] = frozenset(),
) -> list[str]:
    """MOPS 重訊 watch 的實際監看清單（ROADMAP Phase 6）。

    與 `edgar_watch_tickers` 同一個 fail-safe 語意：手動清單是**下限**，derivation 只補
    「registry 有這家台股、卻沒人在看它的重訊」這一側的漂移。

    ⚠ 這裡的 derivation 來源刻意是 **registry 而不是 tracked universe**：tracked 會因為
    thesis lifecycle／cohort 讀不到而縮小，而**重訊漏抓一天就永久漏**（MOPS 的
    opendata 只有前一營業日那一批），所以監看範圍不該跟著會縮的東西走。
    """
    manual = {str(t).strip().upper() for t in (watch.get("tickers") or []) if str(t).strip()}
    if not watch.get("derive_from_registry"):
        return sorted(manual)
    taiwan = {
        ticker for ticker in registry_tickers
        if str(ticker).strip().upper().endswith((".TW", ".TWO"))
    }
    return sorted(manual | taiwan)


def cohort_tickers(rows: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    terminal = {"promoted", "rejected", "expired"}
    return frozenset(
        ticker
        for row in rows
        if str(row.get("lifecycle_status") or "") not in terminal
        if (ticker := str(row.get("research_ticker") or "").strip().upper())
    )


def discover_tracked_tickers(
    config: Mapping[str, Any],
    *,
    lifecycle_path: Path = DEFAULT_LIFECYCLE,
) -> frozenset[str]:
    sources = config["pq1"]["tracked_ticker_sources"]
    tickers: set[str] = set()
    if sources["thesis_lifecycle"]:
        tickers.update(lifecycle_tickers(lifecycle_path))
    if sources["decision_cohorts"]:
        try:
            from decision_lab.bootstrap import open_readonly_store

            store = open_readonly_store()
            try:
                rows = store.list_operational_cohorts(
                    as_of=datetime.now(timezone.utc).isoformat()
                )
            finally:
                store.close()
            tickers.update(cohort_tickers(rows))
        except Exception:
            # Private store 尚未建立或暫時不可讀時，lifecycle 仍可提供安全降級。
            pass
    if sources["theme_core_companies"]:
        tickers.update(theme_core_tickers())
    return frozenset(tickers)
