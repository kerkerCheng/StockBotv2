"""主題等權組 ledger 的 I/O：`library/private/alpha/theme_cohorts/<題材 slug>.jsonl`（Phase 3 Step 3.3）。

與 `briefs.py`／`structure_readings.py` 同一套規則：private、append-only、content-addressed id 拒絕重複、
secret 拒絕、`supersedes_id` 必須指到既有紀錄。純邏輯在 `alpha/theme_cohort.py`；這裡讀寫檔並做**身分解析**
（成員必須 registry 解析得到，且 ticker 與 company_id 互相指得到——INV-1：ticker 不是 identity）。

⚠ 寫入入口**只有** `python -m engine_b.todo complete-theme-cohort <n>`（讀凍結 spec、比對 digest）；
`python -m alpha theme-cohort` 只讀。

**以題材認組，不以檔名認組**（多主題等權組 S1，plan 2026-10-05-002）：`slug()` 把非英數字一律換成 `_`，
「電力」「散熱」都是 `__`——先前以檔名當題材時，兩組一建就寫進同一個檔、`current_cohorts` 每個檔只挑一份，
其中一組會被安靜蓋掉（INV-3）。現在讀取掃全部檔、以紀錄自己的 `theme` 分組；寫入時題材已有 ledger 就沿用那個檔，
新題材的檔名加題材雜湊。既有檔不搬、不改名。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from shared.redaction import sensitive_payload_path

from ..errors import ContractViolation
from ..theme_cohort import ThemeCohort, parse_cohort_record, select_current, validate_spec

_ROOT = Path(__file__).resolve().parents[2]
THEME_COHORT_DIR = _ROOT / "library" / "private" / "alpha" / "theme_cohorts"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def slug(theme: str) -> str:
    """題材 → 檔名（沿用讀圖 ledger 的 `_slug` 慣例：`:`／`/` 等換成 `_`；Windows 的 `:` 會變 NTFS 資料流）。"""
    text = _UNSAFE.sub("_", str(theme).strip())
    if not text:
        raise ContractViolation("theme 正規化後是空字串——檔名推不出來")
    return text


def _theme_of_lines(path: Path) -> set[str]:
    """一個 ledger 檔裡出現過的題材（只讀 `theme` 欄；壞行略過——壞行由 `_read_path` 計數）。"""
    themes: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            theme = json.loads(line).get("theme") if line.strip() else None
        except (ValueError, AttributeError):
            continue
        if theme:
            themes.add(str(theme).strip())
    return themes


def ledger_path(theme: str, *, directory: Path | None = None) -> Path:
    """題材 → 寫入的檔。這個題材已有 ledger 就沿用那個檔（既有檔不搬）；新題材＝`slug` ＋ `_` ＋ 題材 sha1 前 8 碼，
    兩個題材不會再因為 slug 相同而共用一個檔。"""
    root = directory or THEME_COHORT_DIR
    wanted = str(theme).strip()
    if root.is_dir():
        for path in sorted(root.glob("*.jsonl")):
            if wanted in _theme_of_lines(path):
                return path
    digest = hashlib.sha1(wanted.encode("utf-8")).hexdigest()[:8]
    return root / f"{slug(theme)}_{digest}.jsonl"


def _read_all(root: Path) -> tuple[list[ThemeCohort], list[str]]:
    records: list[ThemeCohort] = []
    errors: list[str] = []
    for path in sorted(root.glob("*.jsonl")):
        recs, errs = _read_path(path)
        records.extend(recs)
        errors.extend(errs)
    return records, errors


def read_cohort_records(theme: str, *, directory: Path | None = None) -> tuple[list[ThemeCohort], list[str]]:
    """這個題材的全部紀錄：掃全部 ledger 檔、以紀錄的 `theme` 過濾（不以檔名認題材）。壞行全部帶回（INV-3）。"""
    root = directory or THEME_COHORT_DIR
    if not root.is_dir():
        return [], []
    records, errors = _read_all(root)
    wanted = str(theme).strip()
    return [r for r in records if r.theme == wanted], errors


def _read_path(path: Path) -> tuple[list[ThemeCohort], list[str]]:
    if not path.is_file():
        return [], []
    records: list[ThemeCohort] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_cohort_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def current_cohorts(*, directory: Path | None = None, as_of: date | None = None
                    ) -> tuple[list[ThemeCohort], list[str]]:
    """每個**題材** as-of 生效的那一份（依題材名排序）。以紀錄的 `theme` 分組、不以檔名——兩個題材就算擠在同一個檔，
    也各自挑得出現行組，不會有一組被安靜蓋掉。壞行計數回在第二個 list（INV-3）。"""
    root = directory or THEME_COHORT_DIR
    if not root.is_dir():
        return [], []
    records, errors = _read_all(root)
    by_theme: dict[str, list[ThemeCohort]] = {}
    for record in records:
        by_theme.setdefault(record.theme, []).append(record)
    cohorts: list[ThemeCohort] = []
    for theme in sorted(by_theme):
        current = select_current(by_theme[theme], as_of=as_of)
        if current is not None:
            cohorts.append(current)
    return cohorts, errors


def resolve_members(spec: Mapping[str, Any], *, registry: Any = None) -> list[str]:
    """成員身分核對 → 問題清單（空＝全部解析得到）。**嚴格**：ticker 必須以 registry 的嚴格比對
    （`company_id_for_ticker`）解析到同一個 company_id——寬鬆的去後綴規則只給 lead 關聯用。"""
    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    problems = []
    for m in validate_spec(spec)["members"]:
        if not registry.has_company(m["company_id"]):
            problems.append(f"{m['ticker']}：{m['company_id']} 不在 registry")
            continue
        resolved = registry.company_id_for_ticker(m["ticker"])
        if resolved != m["company_id"]:
            problems.append(f"{m['ticker']}：registry 解析成 {resolved!r}，與 spec 的 {m['company_id']} 不符")
    return problems


def append_cohort_record(record: Mapping[str, Any], *, directory: Path | None = None, registry: Any = None) -> Path:
    """append 一筆（已由 `cohort_record()` 驗證過的）紀錄；只 append，永不改寫既有行。"""
    parsed = parse_cohort_record(record)
    sensitive = sensitive_payload_path(dict(record), "theme_cohort")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing theme cohort rejected at {sensitive}")
    problems = resolve_members({k: record.get(k) for k in ("theme", "members", "excluded", "reason",
                                                            "supersedes_id")}, registry=registry)
    if problems:
        raise ContractViolation("成員身分解析不到：" + "；".join(problems))
    path = ledger_path(parsed.theme, directory=directory)
    existing, _ = read_cohort_records(parsed.theme, directory=directory)
    if any(r.cohort_id == parsed.cohort_id for r in existing):
        raise ContractViolation(f"theme cohort {parsed.cohort_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.cohort_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在「{parsed.theme}」這個題材的紀錄裡")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def memberships(ticker: str, cohorts: list[ThemeCohort]) -> list[ThemeCohort]:
    t = ticker.strip().upper()
    return [c for c in cohorts if t in c.tickers]


__all__ = ["THEME_COHORT_DIR", "append_cohort_record", "current_cohorts", "ledger_path", "memberships",
           "read_cohort_records", "resolve_members", "slug"]
