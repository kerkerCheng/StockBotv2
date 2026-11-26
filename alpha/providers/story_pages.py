"""故事頁的帳（Phase 8 plan `docs/plans/2026-11-26-001-feat-phase8-story-page-app-plan.md` §2.3）。

- 帳：`library/private/alpha/story_pages.jsonl`，一列一版、只追加。**現行頁＝這家公司在帳上的最後一列。**
- 片段原文：`library/private/story_pages/<代號>/<page_id>.html`，寫入後不改。
- 一列：`page_id`、`company_id`、`ticker`、`brief_id`、`created_at`、`author`、`kind`（`page`｜`rebind`）、`html_sha256`、
  `html_path`、`visible_chars`、`warnings`（檢查的 WARN 摘要）、`declaration`（宣告全文）、`rebind_note`、`supersedes_id`。
- `rebind`＝同一份片段、綁到新的一版敘事，必附一句「新舊敘事差在哪、這一頁為什麼還站得住」（skill 的「對版」）。

它**不是 authority**：不決定候選狀態、不擋任何別的寫入、不入圖、不寫 watch。檢查只決定這一頁收不收進這本帳。
規則在 `alpha.narrative.story_page`（純）；這裡只讀寫檔、做需要讀別的帳的核對——現行敘事、等待 registry、圖上節點，
**都用各自現成的讀取函式**，不自己打開別人的 jsonl。壞行不靜默丟（INV-3）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from alpha.errors import ContractViolation
from alpha.narrative.story_page import Finding, PageCheck, check_page, normalize_for_match

_ROOT = Path(__file__).resolve().parents[2]
STORY_PAGES_PATH = _ROOT / "library" / "private" / "alpha" / "story_pages.jsonl"
STORY_PAGE_DIR = _ROOT / "library" / "private" / "story_pages"
PAGE_FILE = "page.html"
DECLARATION_FILE = "page.json"
RECORD_KINDS: tuple[str, ...] = ("page", "rebind")
_REQUIRED = ("page_id", "company_id", "ticker", "brief_id", "created_at", "kind", "html_sha256", "html_path")
#: 對版一句的最短字數（「差在哪、為什麼還站得住」寫不到這麼短）。
REBIND_NOTE_MIN = 12

BriefLoader = Callable[[str], tuple[Sequence[Any], Sequence[str]]]
WatchLoader = Callable[[], Mapping[str, Any]]
GraphChecker = Callable[[Sequence[str]], "set[str] | None"]


def page_id(company_id: str, brief_id: str, html_sha256: str) -> str:
    canonical = json.dumps({"company_id": company_id, "brief_id": brief_id, "html_sha256": html_sha256},
                           sort_keys=True)
    return "sp_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _safe_slug(ticker: str) -> str:
    """代號當資料夾名：只留英數與 `._-`，開頭的點拿掉（`..` 不能變成上一層）。"""
    slug = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(ticker).strip())
    return slug.lstrip(".") or "_"

# ---------------------------------------------------------------- 讀帳

def read_records(*, path: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """全部紀錄（檔案順序）；壞行回在第二個 list（不靜默丟）。"""
    target = path or STORY_PAGES_PATH
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
            if raw["kind"] not in RECORD_KINDS:
                raise ValueError(f"kind 不認得：{raw['kind']}")
            if not isinstance(raw.get("declaration"), dict):
                raise ValueError("缺 declaration")
            records.append(raw)
        except ValueError as exc:
            errors.append(f"{target.name}:{number}: {str(exc)[:120]}")
    return records, errors


def current_pages(*, path: Path | None = None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """每家公司的現行頁（帳上最後一列）與壞行。"""
    records, errors = read_records(path=path)
    out: dict[str, dict[str, Any]] = {}
    for rec in records:
        out[rec["company_id"]] = rec
    return out, errors


def history(company_id: str, *, path: Path | None = None) -> list[dict[str, Any]]:
    """一家公司的版本史（舊到新）。"""
    records, _errors = read_records(path=path)
    return [r for r in records if r["company_id"] == company_id]


def html_file(record: Mapping[str, Any], *, root: Path | None = None) -> Path:
    raw = Path(str(record["html_path"]))
    return raw if raw.is_absolute() else (root or _ROOT) / raw


def read_html(record: Mapping[str, Any], *, root: Path | None = None) -> str:
    """一列的片段原文。檔不見或內容被改過（sha256 對不上）就 raise——不回半份、不回別的版本。"""
    target = html_file(record, root=root)
    if not target.is_file():
        raise ContractViolation(f"故事頁片段不見了：{record['html_path']}")
    data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != record["html_sha256"]:
        raise ContractViolation(f"故事頁片段被改過（sha256 對不上帳）：{record['html_path']}")
    return data.decode("utf-8")

# ---------------------------------------------------------------- 跨帳的讀取（預設用現成的函式；測試注入）

def graph_nodes_exist(ids: Sequence[str]) -> set[str] | None:
    """圖上有哪幾個節點（與物化查節點名同一條查詢）。圖連不上回 None——呼叫端印「沒核」，不當成通過。"""
    if not ids:
        return set()
    try:
        from query.structure import _graph_driver

        driver = _graph_driver()
        try:
            with driver.session() as session:
                return {str(r["id"]) for r in session.run("MATCH (n) WHERE n.id IN $ids RETURN n.id AS id",
                                                           ids=list(ids))}
        finally:
            driver.close()
    except Exception:  # noqa: BLE001 — 圖連不上是「沒核」，不是「不存在」
        return None


def _default_watches() -> Mapping[str, Any]:
    from engine_b.event_watch import load_watches

    return load_watches()


def _current_brief(ticker: str, *, brief_loader: BriefLoader | None, today: date | None) -> tuple[Any, list[str]]:
    from alpha.narrative.contracts import RECORD_VERSION_V2, select_brief

    from .briefs import read_brief_records

    records, errors = (brief_loader or read_brief_records)(str(ticker))
    brief = select_brief(list(records), as_of=None, today=today or date.today())
    if brief is None or brief.record_version != RECORD_VERSION_V2:
        return None, list(errors)
    return brief, list(errors)


def company_names(registry: Any) -> dict[str, list[str]]:
    """名冊上每家公司的名字（顯示名＋別名）——W4 比對用。`companies` 是 `IdentityRegistry` 的唯讀屬性。

    不用 `fact_checks.company_names`：那份把代號也當名字（給檔名比對），拿來掃散文會被短代號誤報。"""
    out: dict[str, list[str]] = {}
    for company in registry.companies:
        names = [n for n in (getattr(company, "display_name", None), *getattr(company, "name_aliases", ())) if n]
        if names:
            out[str(company.company_id)] = [str(n) for n in names]
    return out


def _quote_corpus(patterns: Sequence[str], root: Path) -> tuple[str | None, str | None, list[str]]:
    """`quote_sources` 的檔全文（正規化過）。回 (corpus, 沒核的理由, 對到的檔)。"""
    if not patterns:
        return None, "宣告的 quote_sources 是空的", []
    resolved_root = root.resolve()
    files: list[Path] = []
    for pattern in patterns:
        for found in sorted(root.glob(str(pattern).replace("\\", "/"))):
            real = found.resolve()
            if found.is_file() and resolved_root in real.parents and real not in files:
                files.append(real)
    if not files:
        return None, "quote_sources 一個檔都沒對到", []
    corpus = "".join(normalize_for_match(f.read_text(encoding="utf-8", errors="replace")) for f in files)
    return corpus, None, [f.relative_to(resolved_root).as_posix() for f in files]

# ---------------------------------------------------------------- 資料夾的檢查

@dataclass
class FolderReport:
    folder: Path
    ticker: str
    company_id: str | None
    current_brief_id: str | None
    html: str
    html_bytes: bytes
    declaration: Any
    check: PageCheck
    extra: list[Finding] = field(default_factory=list)
    quote_files: list[str] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        return [*self.check.findings, *self.extra]

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.is_error]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if not f.is_error]

    @property
    def html_sha256(self) -> str:
        return hashlib.sha256(self.html_bytes).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {"folder": str(self.folder), "ticker": self.ticker, "company_id": self.company_id,
                "current_brief_id": self.current_brief_id, "visible_chars": self.check.visible_chars,
                "html_sha256": self.html_sha256, "quote_files": self.quote_files,
                "errors": [f.as_dict() for f in self.errors], "warnings": [f.as_dict() for f in self.warnings]}


def load_folder(folder: Path) -> tuple[bytes, Any, list[Finding]]:
    """讀 `page.html` 與 `page.json`。讀不到或不是 JSON 就變成問題，不丟例外。"""
    problems: list[Finding] = []
    html_bytes = b""
    decl: Any = None
    page = Path(folder) / PAGE_FILE
    if page.is_file():
        html_bytes = page.read_bytes()
        try:
            html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(Finding("E2", f"{PAGE_FILE} 不是 UTF-8"))
            html_bytes = b""
    else:
        problems.append(Finding("E2", f"資料夾裡沒有 {PAGE_FILE}"))
    target = Path(folder) / DECLARATION_FILE
    if target.is_file():
        try:
            decl = json.loads(target.read_text(encoding="utf-8"))
        except ValueError as exc:
            problems.append(Finding("E5", f"{DECLARATION_FILE} 不是 JSON：{str(exc)[:80]}"))
    else:
        problems.append(Finding("E5", f"資料夾裡沒有 {DECLARATION_FILE}"))
    return html_bytes, decl, problems


def check_folder(folder: Path, *, registry: Any = None, brief_loader: BriefLoader | None = None,
                 watch_loader: WatchLoader | None = None, graph_checker: GraphChecker | None = None,
                 root: Path | None = None, today: date | None = None) -> FolderReport:
    """一個故事頁資料夾的全部檢查（純規則＋跨帳核對）。不寫任何東西。"""
    folder = Path(folder)
    root = root or _ROOT
    html_bytes, decl, load_problems = load_folder(folder)
    html = html_bytes.decode("utf-8") if html_bytes else ""
    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    ticker = str(decl.get("ticker") or "").strip() if isinstance(decl, Mapping) else ""
    patterns = list(decl.get("quote_sources") or []) if isinstance(decl, Mapping) and isinstance(
        decl.get("quote_sources"), list) else []
    corpus, quote_note, quote_files = _quote_corpus([p for p in patterns if isinstance(p, str)], root)
    check = check_page(html, decl, company_names=company_names(registry),
                       quote_corpus=corpus, quote_note=quote_note) if html else PageCheck([], 0, "")
    extra: list[Finding] = list(load_problems)
    company_id = registry.company_id_for_ticker(ticker) if ticker else None
    current_brief_id: str | None = None
    if ticker and company_id is None:
        extra.append(Finding("E5", f"{ticker} 不在名冊（config/company_identity.json）——先補名冊，不從公司名猜（INV-1）"))
    if ticker:
        brief, errors = _current_brief(ticker, brief_loader=brief_loader, today=today)
        if brief is None:
            extra.append(Finding("E5", f"{ticker} 沒有現行的 v2 敘事——故事頁綁一版敘事，先寫敘事"
                                 + (f"（敘事帳有 {len(errors)} 行解析失敗）" if errors else "")))
        else:
            current_brief_id = str(brief.brief_id)
            if isinstance(decl, Mapping) and decl.get("brief_id") != current_brief_id:
                extra.append(Finding("E5", f"brief_id 要是現行那一版敘事 {current_brief_id}（宣告寫的是 {decl.get('brief_id')}）"))
    if isinstance(decl, Mapping):
        waits = [w for w in (decl.get("waits") or []) if isinstance(w, Mapping)]
        wanted = sorted({str(w["watch_id"]) for w in waits if isinstance(w.get("watch_id"), str)})
        if wanted:
            data = (watch_loader or _default_watches)()
            known = {str(w.get("watch_id")) for w in data.get("watches") or [] if isinstance(w, Mapping)}
            missing = [w for w in wanted if w not in known]
            if missing:
                extra.append(Finding("E5", "waits 的 watch_id 在等待 registry 找不到：" + "、".join(missing)))
        rides = [r for r in (decl.get("rides") or []) if isinstance(r, str) and r.strip()]
        if rides:
            found = (graph_checker or graph_nodes_exist)(rides)
            if found is None:
                extra.append(Finding("W10", "rides 的節點沒核（圖連不上）——不是通過，圖回來再跑一次 check", tuple(rides[:10])))
            else:
                missing = [r for r in rides if r not in found]
                if missing:
                    extra.append(Finding("E5", "rides 的節點在圖上找不到：" + "、".join(missing)))
        cold = decl.get("cold_read")
        if isinstance(cold, Mapping) and isinstance(cold.get("report"), str) and "skipped" not in cold:
            report = (folder / cold["report"]).resolve()
            if folder.resolve() not in report.parents or not report.is_file():
                extra.append(Finding("E6", f"冷讀回報 {cold['report']} 不在這個資料夾裡"))
    return FolderReport(folder=folder, ticker=ticker, company_id=company_id, current_brief_id=current_brief_id,
                        html=html, html_bytes=html_bytes, declaration=decl, check=check, extra=extra,
                        quote_files=quote_files)

# ---------------------------------------------------------------- 寫入

def _append(record: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _stored_path(target: Path, root: Path) -> str:
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return target.resolve().as_posix()


def add_page(folder: Path, *, path: Path | None = None, page_dir: Path | None = None, root: Path | None = None,
             registry: Any = None, brief_loader: BriefLoader | None = None, watch_loader: WatchLoader | None = None,
             graph_checker: GraphChecker | None = None, now: datetime | None = None, today: date | None = None,
             author: str = "session") -> tuple[dict[str, Any], FolderReport]:
    """唯一的寫入入口：先 `check_folder`；有 ERROR 就整筆拒收（什麼都不寫）。沒有才把片段複製進私有區、帳追加一列。"""
    from shared.redaction import sensitive_payload_path

    root = root or _ROOT
    report = check_folder(folder, registry=registry, brief_loader=brief_loader, watch_loader=watch_loader,
                          graph_checker=graph_checker, root=root, today=today)
    if report.errors:
        raise ContractViolation("故事頁拒收（沒寫）：\n  - " + "\n  - ".join(f.line() for f in report.errors))
    decl = dict(report.declaration)
    ledger = path or STORY_PAGES_PATH
    current, _errors = current_pages(path=ledger)
    head = current.get(str(report.company_id))
    sha = report.html_sha256
    if head is not None and head["html_sha256"] == sha and head["brief_id"] == decl["brief_id"]:
        raise ContractViolation(f"跟現行那一頁（{head['page_id']}）一樣——不必再寫")
    pid = page_id(str(report.company_id), str(decl["brief_id"]), sha)
    target = (page_dir or STORY_PAGE_DIR) / _safe_slug(report.ticker) / f"{pid}.html"
    if target.exists() and target.read_bytes() != report.html_bytes:
        raise ContractViolation(f"{target} 已經存在、內容不同——片段寫入後不改，先查是怎麼回事")
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "page_id": pid, "company_id": report.company_id, "ticker": report.ticker, "brief_id": decl["brief_id"],
        "created_at": stamp, "author": author, "kind": "page", "html_sha256": sha,
        "html_path": _stored_path(target, root), "visible_chars": report.check.visible_chars,
        "warnings": [f.line() for f in report.warnings], "declaration": decl, "rebind_note": None,
        "supersedes_id": head["page_id"] if head else None,
    }
    if sensitive_payload_path(record, "story_pages") is not None:
        raise ContractViolation("內容像密鑰，拒收")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(report.html_bytes)
    _append(record, ledger)
    return record, report


def rebind_page(ticker: str, note: str, *, path: Path | None = None, root: Path | None = None, registry: Any = None,
                brief_loader: BriefLoader | None = None, now: datetime | None = None, today: date | None = None,
                author: str = "session") -> dict[str, Any]:
    """對版：現行頁（同一份片段）綁到現行那一版敘事。必附一句「新舊敘事差在哪、這一頁為什麼還站得住」。"""
    root = root or _ROOT
    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    company = registry.company_id_for_ticker(str(ticker).strip())
    if company is None:
        raise ContractViolation(f"{ticker} 不在名冊——先補名冊，不從公司名猜（INV-1）")
    brief, _errors = _current_brief(str(ticker), brief_loader=brief_loader, today=today)
    if brief is None:
        raise ContractViolation(f"{ticker} 沒有現行的 v2 敘事——沒有東西可以對版")
    ledger = path or STORY_PAGES_PATH
    head = current_pages(path=ledger)[0].get(company)
    if head is None:
        raise ContractViolation(f"{ticker} 還沒有故事頁——先寫（python -m alpha story-page add <資料夾>）")
    if head["brief_id"] == brief.brief_id:
        raise ContractViolation(f"{ticker} 的故事頁已經對著現行那一版敘事（{brief.brief_id}）——不必對版")
    text = " ".join(str(note or "").split())
    if len(text) < REBIND_NOTE_MIN:
        raise ContractViolation(f"對版要寫一句（{REBIND_NOTE_MIN} 字以上）：新舊兩版敘事差在哪、這一頁為什麼還站得住")
    read_html(head, root=root)            # 片段還在、沒被改過才對版
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    record = {**{k: head.get(k) for k in ("company_id", "ticker", "html_sha256", "html_path", "visible_chars",
                                         "warnings", "declaration")},
              "page_id": page_id(company, str(brief.brief_id), str(head["html_sha256"])),
              "brief_id": str(brief.brief_id), "created_at": stamp, "author": author, "kind": "rebind",
              "rebind_note": text, "supersedes_id": head["page_id"]}
    _append(record, ledger)
    return record


def page_status(record: Mapping[str, Any], current_brief_id: str | None) -> str:
    """一頁對現行敘事的狀態：`current`／`stale`（敘事換版了，還沒對版）／`no_brief`（現在沒有現行的 v2 敘事）。"""
    if current_brief_id is None:
        return "no_brief"
    return "current" if record.get("brief_id") == current_brief_id else "stale"


def current_brief_ids(tickers: Iterable[str], *, brief_loader: BriefLoader | None = None,
                      today: date | None = None) -> dict[str, str | None]:
    """代號 → 現行 v2 敘事的 id（沒有＝None）。"""
    out: dict[str, str | None] = {}
    for ticker in tickers:
        brief, _errors = _current_brief(ticker, brief_loader=brief_loader, today=today)
        out[ticker] = str(brief.brief_id) if brief is not None else None
    return out


__all__ = [
    "DECLARATION_FILE", "FolderReport", "PAGE_FILE", "RECORD_KINDS", "STORY_PAGES_PATH", "STORY_PAGE_DIR", "add_page",
    "check_folder", "company_names", "current_brief_ids", "current_pages", "graph_nodes_exist", "history", "html_file",
    "load_folder", "page_id", "page_status", "read_html", "read_records", "rebind_page",
]
