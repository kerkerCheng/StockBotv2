"""個股頁的故事層 ledger（2026-10-29；ROADMAP 旁支「個股頁：故事層與依據層」B 段）：`library/private/alpha/stories.jsonl`。

一筆＝**一版敘事（`brief_id`）**的故事：敘事七格各一句、只有故事的兩格（營收從哪來、最近發生什麼）、候選理由一句、
缺 X 的短標。規則在 `alpha.narrative.story`（純規則）；這裡只讀寫檔、核對寫給的是哪一版敘事。

- **依據不搬家**：原文、日期、出處照舊住敘事那一格（首屏的展開裡照印）；故事只是那一格的人話。
- **故事對的是一版敘事**：敘事換版，舊故事就不算數——首屏退回印依據，待做清單 ⑤「故事還沒寫」多一檔。
  故事過期因此是一個會自己出現的計數，不是要人記得的事（L14）。
- 只 append；同一版敘事最新一筆是現行（改字就再寫一筆，舊的留著）。壞行不靜默丟（INV-3）。
- 它不 gate 任何東西、不寫 watch、不改候選狀態——狀態照舊由敘事宣告。

**唯一的寫入入口是 `write_story`**：任一條不過就整筆拒收、逐條說原因。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from alpha.errors import ContractViolation

_ROOT = Path(__file__).resolve().parents[2]
STORIES_PATH = _ROOT / "library" / "private" / "alpha" / "stories.jsonl"
_REQUIRED = ("story_id", "brief_id", "company_id", "ticker", "created_at")
#: 缺故事的兩種（`story_gaps` 的 kind；⑤ 涵蓋登記表從這裡列舉——L16）：從沒寫過／敘事換版、故事過期。
STORY_GAP_KINDS: tuple[str, ...] = ("never", "stale")


def story_id(brief_id: str, created_at: str, body: Mapping[str, Any]) -> str:
    canonical = json.dumps({"brief_id": brief_id, "created_at": created_at, **body}, ensure_ascii=False, sort_keys=True)
    return "st_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def read_records(*, path: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """全部紀錄；壞行回在第二個 list（不靜默丟）。"""
    target = path or STORIES_PATH
    if not target.is_file():
        return [], []
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("這一行不是 object")
            for key in _REQUIRED:
                if not isinstance(raw.get(key), str) or not raw[key].strip():
                    raise ValueError(f"缺 {key}")
            if not isinstance(raw.get("slots"), dict):
                raise ValueError("缺 slots")
            records.append(raw)
        except ValueError as exc:
            errors.append(f"{target.name}:{number}: {str(exc)[:120]}")
    return records, errors


def current_stories(*, path: Path | None = None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """每一版敘事（`brief_id`）現行那一筆＝最新的一筆（created_at，同時刻比 id）；與壞行。"""
    records, errors = read_records(path=path)
    out: dict[str, dict[str, Any]] = {}
    for rec in records:
        head = out.get(rec["brief_id"])
        if head is None or (rec["created_at"], rec["story_id"]) > (head["created_at"], head["story_id"]):
            out[rec["brief_id"]] = rec
    return out, errors


def story_at(brief_id: str, *, as_of: date | None = None, path: Path | None = None) -> dict[str, Any] | None:
    """一版敘事在 `as_of` 那天收盤時現行的故事（INV-6：回看過去不得拿之後才寫的故事）；`as_of` None＝現在。
    沒有就 None。"""
    records, _errors = read_records(path=path)
    head: dict[str, Any] | None = None
    for rec in records:
        if rec["brief_id"] != brief_id:
            continue
        if as_of is not None and rec["created_at"][:10] > as_of.isoformat():
            continue
        if head is None or (rec["created_at"], rec["story_id"]) > (head["created_at"], head["story_id"]):
            head = rec
    return head


def _raw_ref_problem(ref: str) -> str | None:
    """`library/raw/` 的一手節錄要真的在（與敘事 ⑨ 同一條：引用指得回它從哪來）；其他引用（packet 的 evidence key）只查非空。"""
    from alpha.narrative.contracts import RAW_EXCERPT_PREFIX

    if not ref.startswith(RAW_EXCERPT_PREFIX):
        return None
    raw_root = (_ROOT / RAW_EXCERPT_PREFIX).resolve()
    target = (_ROOT / ref).resolve()
    if raw_root not in target.parents or not target.is_file():
        return f"{ref} 在 library/raw 找不到（或跳出了 library/raw）"
    return None


def story_spec_problems(spec: Mapping[str, Any], brief: Any) -> list[str]:
    """一筆故事對一版敘事的全部問題（空＝可以寫）。`brief`：那一版 `InvestorBrief`（v2、現行）。純函式。"""
    from alpha.narrative.story import (CANDIDATE_STORY_MAX, STORY_ONLY_KEYS, STORY_SLOT_KEYS, missing_label_problems,
                                       story_problems)

    problems: list[str] = []
    slots = spec.get("slots")
    if not isinstance(slots, Mapping):
        return ["slots 必須是 {格名: 一句故事}"]
    wanted = [s.key for s in brief.slots] + list(STORY_ONLY_KEYS)
    unknown = sorted(set(slots) - set(STORY_SLOT_KEYS))
    if unknown:
        problems.append(f"slots 有不認得的格 {unknown}；認得的是 {list(STORY_SLOT_KEYS)}")
    missing = [key for key in wanted if key not in slots]
    if missing:
        problems.append(f"slots 少了 {missing}——一版敘事的故事每一格都要寫（沒寫的格首屏會退回印依據）")
    for key in wanted:
        if key in slots:
            problems += story_problems(key, slots[key])
    evidence = spec.get("evidence") or {}
    if not isinstance(evidence, Mapping):
        problems.append("evidence 必須是 {格名: [引用…]}")
        evidence = {}
    for key in STORY_ONLY_KEYS:
        refs = evidence.get(key)
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or not r.strip() for r in refs):
            problems.append(f"evidence.{key} 必須是非空的引用清單——這一格在敘事裡沒有依據可以指回，故事自己帶出處")
            continue
        problems += [f"evidence.{key}：{p}" for p in (_raw_ref_problem(str(r)) for r in refs) if p]
    extra = sorted(set(evidence) - set(STORY_ONLY_KEYS))
    if extra:
        problems.append(f"evidence 只給 {list(STORY_ONLY_KEYS)} 兩格（其他格的出處在敘事那一格）；多了 {extra}")
    candidate = spec.get("candidate")
    state = getattr(getattr(brief, "candidate_state", None), "state", None)
    if not isinstance(candidate, Mapping):
        problems.append("candidate 必須是 {story: 候選理由的一句故事, missing_label: 缺 X 的短標（只有缺 X 才寫）}")
    else:
        problems += story_problems("candidate", candidate.get("story"), limit=CANDIDATE_STORY_MAX)
        if state == "missing":
            problems += missing_label_problems(candidate.get("missing_label"))
        elif candidate.get("missing_label") is not None:
            problems.append(f"這版敘事宣告的是 {state}，不是缺 X——不寫 missing_label（一個欄位不承載兩種意思，L12）")
    return problems


def write_story(ticker: str, spec: Mapping[str, Any], *, path: Path | None = None, registry: Any = None,
                now: datetime | None = None, today: date | None = None, author: str = "session",
                brief_loader: Callable[[str], tuple[Sequence[Any], Sequence[str]]] | None = None) -> dict[str, Any]:
    """唯一的寫入入口。`spec`：`brief_id`（必須是這一檔**現行**那一版）、`slots`、`evidence`、`candidate`。
    任一條不過就整筆拒收。回寫入的那一筆。"""
    record, problems = prepare_story(ticker, spec, path=path, registry=registry, now=now, today=today,
                                     author=author, brief_loader=brief_loader)
    if problems:
        raise ContractViolation(f"{ticker} 的故事拒收（沒寫）：\n  - " + "\n  - ".join(problems))
    target = path or STORIES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def prepare_story(ticker: str, spec: Mapping[str, Any], *, path: Path | None = None, registry: Any = None,
                  now: datetime | None = None, today: date | None = None, author: str = "session",
                  brief_loader: Callable[[str], tuple[Sequence[Any], Sequence[str]]] | None = None
                  ) -> tuple[dict[str, Any], list[str]]:
    """寫入前的全部核對（不寫檔）：回 `(要寫的那一筆, 問題清單)`——`write_story` 與乾跑（`--check`）共用同一份。
    名冊查不到、沒有現行 v2 敘事、`brief_id` 不是現行那一版：直接 raise（那一筆根本沒有對象）。"""
    from shared.redaction import sensitive_payload_path

    from alpha.narrative.contracts import RECORD_VERSION_V2, select_brief

    from .briefs import read_brief_records

    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    company = registry.company_id_for_ticker(str(ticker).strip())
    if company is None:
        raise ContractViolation(f"{ticker} 不在名冊（config/company_identity.json）——先補名冊，不從公司名猜（INV-1）")
    records, errors = (brief_loader or read_brief_records)(str(ticker))
    brief = select_brief(list(records), as_of=None, today=today or date.today())
    if brief is None or brief.record_version != RECORD_VERSION_V2:
        raise ContractViolation(f"{ticker} 沒有現行的 v2 敘事——故事寫給一版敘事，先寫敘事"
                                + (f"（ledger 有 {len(errors)} 行解析失敗）" if errors else ""))
    if str(spec.get("brief_id") or "") != brief.brief_id:
        raise ContractViolation(f"故事要寫給現行那一版敘事 {brief.brief_id}（spec 寫的是 {spec.get('brief_id') or '空的'}）")
    problems = story_spec_problems(spec, brief)
    current, _errors = current_stories(path=path)
    body = {"slots": {k: str(v).strip() for k, v in (spec.get("slots") or {}).items()},
            "evidence": {k: [str(r).strip() for r in v] for k, v in (spec.get("evidence") or {}).items()},
            "candidate": {k: str(v).strip() for k, v in (spec.get("candidate") or {}).items() if v is not None}}
    head = current.get(brief.brief_id)
    if head is not None and all(head.get(k) == body[k] for k in body):
        problems.append(f"跟現行那一筆（{head['story_id']}）一樣——不必再寫")
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    record = {"story_id": story_id(brief.brief_id, stamp, body), "brief_id": brief.brief_id, "company_id": company,
              "ticker": str(brief.ticker), "created_at": stamp, "author": author, **body}
    if head is not None:
        record["supersedes_id"] = head["story_id"]
    if sensitive_payload_path(dict(record), "stories") is not None:
        problems.append("內容像密鑰，拒收")
    return record, problems


def story_gaps(briefs: Iterable[Any], *, stories: Mapping[str, Mapping[str, Any]],
               all_story_briefs: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    """現行敘事裡還沒有故事的那幾版（⑤「故事還沒寫」的唯一判定，L16）。`briefs`：各檔**現行**的 v2 敘事；
    `stories`：`current_stories()`；`all_story_briefs`：寫過故事的 brief_id → company_id（分「從沒寫過」與「敘事換版、
    故事過期」——下一步一樣是寫故事，但後者可以照舊故事改）。依 ticker 字母列（索引，不是名次）。"""
    written_companies = set((all_story_briefs or {}).values())
    out = []
    for brief in briefs:
        if brief is None or brief.brief_id in stories:
            continue
        out.append({"ticker": str(brief.ticker), "company_id": str(brief.company_id), "brief_id": brief.brief_id,
                    "kind": "stale" if str(brief.company_id) in written_companies else "never"})
    return sorted(out, key=lambda r: (r["ticker"], r["brief_id"]))


def current_v2_briefs(*, today: date | None = None) -> list[Any]:
    """每檔現行的 v2 敘事——與個股頁同一個選法（`select_brief`；L16：「現行那一版」只有一個定義）。"""
    from alpha.narrative.contracts import RECORD_VERSION_V2, select_brief

    from .briefs import BRIEF_DIR, read_brief_records

    out: list[Any] = []
    if not BRIEF_DIR.is_dir():
        return out
    for ledger in sorted(BRIEF_DIR.glob("*.jsonl")):
        records, _errors = read_brief_records(ledger.stem)
        brief = select_brief(records, as_of=None, today=today or date.today())
        if brief is not None and brief.record_version == RECORD_VERSION_V2:
            out.append(brief)
    return out


def gaps_now(*, today: date | None = None, path: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """現在還沒有故事的現行敘事（⑤「故事還沒寫」與 `python -m alpha stories --gaps` 共用，L16）與故事 ledger 的壞行。"""
    records, errors = read_records(path=path)
    current, _errors = current_stories(path=path)
    written = {str(r["brief_id"]): str(r["company_id"]) for r in records}
    return story_gaps(current_v2_briefs(today=today), stories=current, all_story_briefs=written), errors


__all__ = ["STORIES_PATH", "STORY_GAP_KINDS", "current_stories", "current_v2_briefs", "gaps_now", "prepare_story", "read_records",
           "story_at", "story_gaps", "story_id", "story_spec_problems", "write_story"]
