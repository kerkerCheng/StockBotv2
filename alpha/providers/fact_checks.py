"""敘事逐句核對的取數與紀錄（2026-11-12 使用者「先修吧」）：`library/private/alpha/fact_checks.jsonl`。

規則（切句、比對、旗標）住 `alpha.narrative.fact_check`；這裡只做三件事：

1. **把引用讀成原文行**（`RefResolver`）：`library/raw/` 的一手節錄、`graph://source/<doc>` 的逐字引文（`extractions/<doc>.json`）
   與同名節錄、讀圖（判讀文字＋它引用的逐字）、自家筆記。Engine C、三題、外部網址這裡核不了，照數不讀。
2. **核對紀錄**（append-only）：一筆＝研究 session 對**一版敘事（＋它當時的故事）**逐句對過原文的收據——句子 digest、
   核完時還留著的旗標、因為這次核對改了幾句（`changed`）、一句註記。它不 gate 任何東西、不改候選狀態、不寫 watch。
3. **還沒核的那幾版**（`gaps`）：⑤「敘事還沒逐句核對」的唯一判定（L16）。現行 v2 敘事沒有這一版的紀錄＝`brief`；
   有，但故事在那之後換了＝`story`。敘事換版就要再核——上一版核過、一字不差且引用相同的句子自動沿用（`carried`），
   重述只改兩句就只要對兩句。

量測：事實抽樣①（registration 2026-11-03）自 2026-11-13 起每一列記抽中那一版有沒有核對紀錄；核過的那幾份仍錯 ≥ 30%
→ 這個修法沒用（registration 2026-11-12 追加）。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from alpha.errors import ContractViolation
from alpha.narrative.fact_check import ResolvedRef, SourceLine, classify_ref

_ROOT = Path(__file__).resolve().parents[2]
FACT_CHECKS_PATH = _ROOT / "library" / "private" / "alpha" / "fact_checks.jsonl"
EXTRACTIONS_DIR = _ROOT / "extractions"
#: 這條規則從哪一天起算（使用者 2026-11-12「先修吧」）：之前寫的敘事等的天數從這天算，不從寫的那天算。
FACT_CHECK_SINCE = date(2026, 11, 12)
#: 還沒核的兩種（`gaps` 的 kind；⑤ 涵蓋登記表從這裡列舉——L16）：這一版沒核／核過但故事在那之後換了。
FACT_CHECK_GAP_KINDS: tuple[str, ...] = ("brief", "story")
_REQUIRED = ("check_id", "brief_id", "company_id", "ticker", "created_at", "note")
#: 一行原文超過這麼長就照句號再切（決算短信、10-K 一段常常一行到底）。
_LONG_LINE = 300
#: 讀得了的引用檔：文字節錄與筆記。PDF、圖片照數「核不了」，不硬讀。
TEXT_SUFFIXES: frozenset[str] = frozenset({".txt", ".md", ".json", ".jsonl", ".csv", ".tsv", ".html", ".htm", ".xml"})
MAX_TEXT_BYTES = 2_000_000


def _chunks(text: str) -> list[str]:
    if len(text) <= _LONG_LINE:
        return [text]
    parts = [p for p in re.split(r"(?<=[。！？!?；;])|(?<=\.)\s+", text) if p and p.strip()]
    out: list[str] = []
    buf = ""
    for p in parts:
        if buf and len(buf) + len(p) > _LONG_LINE:
            out.append(buf)
            buf = ""
        buf += p
    if buf:
        out.append(buf)
    return out


#: 節錄檔裡**我們自己寫的**行（出處、日期、註記、標題摘要、段名）——不是原文，不拿來對（2026-11-12 校準：CECO 那句錯字
#: 「10-Q 說增加主要來自大型燃氣發電專案」正是從節錄檔的 `[EXCERPT …]` 標題抄來的，工具拿它當原文就對上了；L18）。
#: 鍵是 library/raw 實際用過的寫法（2026-11-12 全目錄盤點：RETRIEVED 913、Source URL 848、Excerpt 832、NOTE 776……）。
#: ⚠ 只收大寫 `NOTE`（2026-11-13 全目錄：`NOTE:` 792 行 791 檔都是我們的；`Note:` 20 行有 19 行是年報與簡報的原文附註——
#: 「Note: The identities of these suppliers are represented by code names…」原本被當標示行丟掉）。`來源：` 11 行都是我們的檔頭。
META_LINE = re.compile(r"^\s*(?:\[(?:EXCERPT|CURATED EXCERPTS?)\b.*|(?:RETRIEVED|Retrieved|Source URL|Excerpt|EXCERPT|NOTE|"
                       r"DATE|PUBLISHED|Published|URL|SOURCE|Source|STORAGE|Storage|Title|TITLE|Publisher|PUBLISHER|"
                       r"Research excerpt|Filed|來源|来源)\s*(?:[（(][^）)\n]{0,20}[）)])?\s*[:：].*|【[^】]*】\s*)$")
#: 我們自己寫的**段落**（2026-11-13，回頭核 27 份：錯從自家改寫抄進敘事，工具又拿改寫當原文對上）：
#: `NOTE:` 之後到空行為止是我們的註記（`META_LINE` 只排掉第一行；全目錄 30 段 93 行續行抽 25 段都是我們的話）、
#: `Research excerpt…:` 之後到空行為止是我們的改寫——兩種段落裡引號內的字照慣例是逐字原文（NVTS、ARBE 的 NOTE 段引了
#: 8-K 原句），另收一行（`_QUOTED`），其餘是我們的話。
_NOTE_HEAD = re.compile(r"^\s*NOTE\s*(?:[（(][^）)\n]{0,20}[）)])?\s*[:：]")
_PARAPHRASE_HEAD = re.compile(r"^\s*Research excerpt\b[^:：\n]{0,40}[:：]")
#: 一整行都是我們的話（2026-11-13 全目錄核過：`Boundary:` 15 行都是我們寫的；「說明：」33 行有 30 行是年報原文，不收）。
_OWN_LINE = re.compile(r"^\s*Boundary\s*[:：]")
#: 檔頭宣告整份是改寫（2026-11-13 只有 lumentum_q2fy26_cpo.txt 一份）：整份都算我們的話。
_PARAPHRASED_FILE = re.compile(r"paraphrased,?\s+not\s+verbatim|非逐字", re.IGNORECASE)
_QUOTED = re.compile(r"“([^“”]{3,})”|\"([^\"]{3,})\"|「([^「」]{3,})」|『([^『』]{3,})』")


def file_lines(path: Path, label: str, *, own: bool = False) -> tuple[SourceLine, ...]:
    """一個檔的每一行（長行照句號再切，行號照原行）；空行與我們自己寫的標示行（`META_LINE`）略過。

    我們自己寫的段落與行（NOTE 段的續行、Research excerpt 的改寫、`Boundary:`）照收、標 `own`——列出來給人對照，
    不算原文；改寫段裡引號內的字另收一行原文。`own=True`：整個檔都是我們寫的（自家筆記）。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    whole_own = own or any(_PARAPHRASED_FILE.search(line) for line in lines[:12])
    out: list[SourceLine] = []
    block = False                               # 現在在不在我們自己寫的段落（NOTE 段、Research excerpt 改寫）裡
    para: list[tuple[int, str]] = []

    def flush() -> None:
        if para and not whole_own:
            joined = " ".join(t.strip() for _n, t in para)
            for m in _QUOTED.finditer(joined):
                body = next(g for g in m.groups() if g)
                out.append(SourceLine(f"{label}:{para[0][0]}（引號內）", body.strip()))
        para.clear()

    for number, line in enumerate(lines, 1):
        if not line.strip():
            flush()
            block = False
            continue
        if META_LINE.match(line):
            flush()
            block = bool(_NOTE_HEAD.match(line) or _PARAPHRASE_HEAD.match(line))
            continue
        if block:
            para.append((number, line))
        mine = whole_own or block or bool(_OWN_LINE.match(line))
        out += [SourceLine(f"{label}:{number}", chunk.strip(), own=mine) for chunk in _chunks(line.strip())]
    flush()
    return tuple(out)


_RETRIEVED = re.compile(r"^\s*(?:RETRIEVED|Retrieved)\s*:")


def name_meta(name: str) -> str:
    """檔名裡的日期與季別寫成看得懂的樣子：`…_2026_08_05.txt`／`…20260805…` → 2026-08-05；底線換空白。"""
    text = re.sub(r"(?<!\d)(20\d{2})[_-](\d{2})[_-](\d{2})(?!\d)", r" \1-\2-\3 ", name)
    text = re.sub(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", r" \1-\2-\3 ", text)
    return text.replace("_", " ")


def file_meta(path: Path) -> tuple[str, ...]:
    """文件自己的標示：檔名與我們寫的出處、日期、標題行（不含抓取日——那是我們哪天抓的，不是文件的日子）。
    只拿來核日期、月份、季、年份（`alpha.narrative.fact_check.ResolvedRef.meta`）。"""
    lines = [name_meta(path.name)]
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
        if META_LINE.match(line) and not _RETRIEVED.match(line):
            lines.append(line.strip())
    return tuple(lines)


def _local_day(stamp: Any) -> str:
    """ISO 時戳 → 台北日期（`2026-11-10T17:00Z` 是 11-11）；讀不出回空字串。"""
    try:
        moment = datetime.fromisoformat(str(stamp or ""))
    except ValueError:
        return ""
    if moment.tzinfo is None:
        return moment.date().isoformat()
    return moment.astimezone(timezone(timedelta(hours=8))).date().isoformat()


def file_units(path: Path) -> tuple[float, ...]:
    """整個檔（含我們自己寫的註記行）宣告的金額單位——單位是表格的機械事實，寫在哪一行都照收。"""
    from alpha.narrative.fact_check import declared_units

    return declared_units(path.read_text(encoding="utf-8", errors="replace"))


class RefResolver:
    """引用 → 原文行（`ResolvedRef`）。同一條引用只讀一次。測試可換掉 `root`、`readings`。"""

    def __init__(self, *, root: Path | None = None, readings: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self.root = root or _ROOT
        self._readings = readings
        self._cache: dict[str, ResolvedRef] = {}

    def readings(self) -> Mapping[str, Mapping[str, Any]]:
        """讀圖 id → 原始紀錄（JSON）。壞行略過——讀圖 ledger 的壞行由它自己的命令計數，這裡只要找得到引用的那一份。"""
        if self._readings is None:
            from alpha.providers.structure_readings import STRUCTURE_READING_DIR

            found: dict[str, Mapping[str, Any]] = {}
            for ledger in sorted(STRUCTURE_READING_DIR.glob("*.jsonl")) if STRUCTURE_READING_DIR.is_dir() else ():
                for line in ledger.read_text(encoding="utf-8").splitlines():
                    try:
                        raw = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(raw, dict) and str(raw.get("reading_id") or "").startswith("sr_"):
                        found[str(raw["reading_id"])] = raw
            self._readings = found
        return self._readings

    def __call__(self, ref: str) -> ResolvedRef:
        if ref not in self._cache:
            self._cache[ref] = self._resolve(str(ref).strip())
        return self._cache[ref]

    def _inside(self, rel: str, base: str) -> Path | None:
        target = (self.root / rel).resolve()
        top = (self.root / base).resolve()
        return target if (top in target.parents and target.is_file()) else None

    def _text_file(self, ref: str, kind: str, path: Path | None, missing: str) -> ResolvedRef:
        if path is None:
            return ResolvedRef(ref, kind, problem=missing)
        # 只讀文字檔：使用者給的券商 PDF（library/private/inbox）當文字讀是 1.4 MB 的亂碼（2026-11-12 1802.TW），要核就存成節錄
        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > MAX_TEXT_BYTES:
            return ResolvedRef(ref, kind, problem=f"不是文字節錄（{path.suffix or '無副檔名'}，{path.stat().st_size // 1024} KB）"
                                                 "——這裡核不了，要核就把那幾頁存成節錄再引用")
        # 自家筆記（library/private、thesis）整份是我們寫的：列出來對照，不算原文
        return ResolvedRef(ref, kind, file_lines(path, path.name, own=kind == "note"), units=file_units(path),
                           meta=file_meta(path))

    def _resolve(self, ref: str) -> ResolvedRef:
        kind = classify_ref(ref)
        # 檔案引用可以帶段落錨（`thesis/lifecycle.json#coherent_cpo.catalyst_checkpoints`）：讀整個檔（COHR 11-12）
        rel = ref.split("#", 1)[0]
        if kind == "raw":
            return self._text_file(ref, kind, self._inside(rel, "library/raw"), "library/raw 找不到這個檔")
        if kind == "note":
            base = "thesis" if ref.startswith("thesis/") else "library"
            return self._text_file(ref, kind, self._inside(rel, base), "找不到這個檔")
        if kind == "graph_source":
            return self._graph_source(ref)
        if kind == "reading":
            raw = self.readings().get(ref)
            if raw is None:
                return ResolvedRef(ref, kind, problem="找不到這份讀圖")
            # 判讀文字是我們寫的（列出來對照、不算原文）；它引用的逐字才是原文
            lines = [SourceLine(f"{ref}（讀圖判讀）", chunk.strip(), own=True) for para in str(raw.get("reading") or "").splitlines()
                     if para.strip() for chunk in _chunks(para.strip())]
            # 文件的日子：讀圖自己寫的那天（台北日期；「11-11 重讀」）與它引用的每份文件檔名裡的日期
            meta = [_local_day(raw.get("created_at"))]
            for c in raw.get("citations") or ():
                if isinstance(c, Mapping) and str(c.get("quote") or "").strip():
                    lines.append(SourceLine(f"{ref}→{c.get('source_id')}", str(c["quote"]).strip()))
                    meta.append(name_meta(str(c.get("source_id") or "")))
            return ResolvedRef(ref, kind, tuple(lines), meta=tuple(m for m in meta if m))
        return ResolvedRef(ref, kind)

    def _graph_source(self, ref: str) -> ResolvedRef:
        doc = ref.removeprefix("graph://source/").strip("/")
        lines: list[SourceLine] = []
        meta: list[str] = [name_meta(doc)]
        extraction = self.root / "extractions" / f"{doc}.json"
        if re.fullmatch(r"[A-Za-z0-9._-]+", doc or "") and extraction.is_file():
            try:
                payload = json.loads(extraction.read_text(encoding="utf-8"))
            except ValueError:
                payload = {}
            for s in payload.get("sources") or ():
                if isinstance(s, Mapping) and str(s.get("quote") or "").strip():
                    where = str(s.get("locator") or s.get("id") or "")
                    lines.append(SourceLine(f"{doc}（{where[:30]}）", str(s["quote"]).strip()))
            src = payload.get("source_doc") or {}
            if isinstance(src, Mapping):
                meta += [str(src[k]) for k in ("title", "published_at") if src.get(k)]
        raw_dir = self.root / "library" / "raw"
        units: set[float] = set()
        if re.fullmatch(r"[A-Za-z0-9._-]+", doc or "") and raw_dir.is_dir():
            for path in sorted(raw_dir.glob(f"{doc}.*")):
                lines += list(file_lines(path, path.name))
                units |= set(file_units(path))
                meta += list(file_meta(path))
        if not lines:
            return ResolvedRef(ref, "graph_source", problem="extractions 與 library/raw 都沒有這份文件的原文")
        return ResolvedRef(ref, "graph_source", tuple(lines), units=tuple(sorted(units)), meta=tuple(meta))


def company_names(registry: Any = None) -> dict[str, tuple[str, ...]]:
    """名冊每家公司的名字（`display_name`＋`name_aliases`）——句子裡提到別家公司時，原文裡要找得到那家的某一個名字。"""
    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    out: dict[str, tuple[str, ...]] = {}
    for c in registry.companies:
        # 代號（去掉交易所後綴）也收：公司自己的年報不寫自己的名字，檔名寫著代號（mops_1802_…）就是它的文件
        code = re.split(r"[.\-]", str(c.research_ticker or ""))[0]
        names = tuple(n for n in (c.display_name, *c.name_aliases, code) if n and str(n).strip())
        if names:
            out[c.company_id] = names
    return out


def self_names(company_id: str, ticker: str, names: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    """這一檔自己的名字與代號（不當成「別家公司」或「要核的英文名稱」）。"""
    base = re.split(r"[.\-]", str(ticker))[0]
    return (*names.get(company_id, ()), str(ticker), base)


# ---------------------------------------------------------------------------
# 核對紀錄
# ---------------------------------------------------------------------------

def check_id(brief_id: str, created_at: str, body: Mapping[str, Any]) -> str:
    canonical = json.dumps({"brief_id": brief_id, "created_at": created_at, **body}, ensure_ascii=False, sort_keys=True)
    return "fc_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def read_records(*, path: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """全部紀錄；壞行回在第二個 list（不靜默丟，INV-3）。"""
    target = path or FACT_CHECKS_PATH
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
            if not isinstance(raw.get("sentence_digests"), list):
                raise ValueError("缺 sentence_digests")
            records.append(raw)
        except ValueError as exc:
            errors.append(f"{target.name}:{number}: {str(exc)[:120]}")
    return records, errors


def carried_digests(company_id: str, records: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """這一家核過的句子：digest → 最早核過它的紀錄 id（同一句話對同一組引用，核過就是核過）。"""
    out: dict[str, str] = {}
    for rec in sorted((r for r in records if r.get("company_id") == company_id), key=lambda r: str(r.get("created_at"))):
        for digest in rec.get("sentence_digests") or ():
            out.setdefault(str(digest), str(rec["check_id"]))
    return out


def build_record(result: Any, *, company_id: str, changed: int, note: str, now: datetime | None = None,
                 author: str = "session", anchor_counts: tuple[int, int] | None = None) -> dict[str, Any]:
    """一筆核對紀錄（不寫檔）。`result`：`alpha.narrative.fact_check.CheckResult`（寫入後的那一版）。
    `anchor_counts`＝(事實句數, 有錨點的事實句數)（2026-11-13 起；plan 2026-11-13-001——重放與「有錨點的比例」從這裡數）。"""
    from alpha.narrative.fact_check import FLAG_KINDS

    if result.brief.brief_id is None:
        raise ContractViolation("草稿不能記核對紀錄——寫入敘事之後，對寫進去的那一版記（`--record`）")
    if isinstance(changed, bool) or not isinstance(changed, int) or changed < 0:
        raise ContractViolation(f"changed 是這次核對改了幾句（≥ 0 的整數；收到 {changed!r}）")
    if not str(note or "").strip():
        raise ContractViolation("note 必填：一句話說核了什麼、改了什麼（「逐句對過，沒有錯」也是一句）")
    left = [{"n": c.sentence.n, "where": c.sentence.where, "kinds": [f.kind for f in c.flags],
             "text": c.sentence.text[:200]} for c in result.flagged]
    for row in left:
        assert all(k in FLAG_KINDS for k in row["kinds"])
    body = {"story_id": result.story_id, "sentences": len(result.checks), "carried": len(result.carried),
            "flags_left": left, "changed": changed, "note": str(note).strip(),
            "sentence_digests": result.digests,
            **({"fact_sentences": anchor_counts[0], "anchored": anchor_counts[1]} if anchor_counts is not None else {})}
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    return {"check_id": check_id(str(result.brief.brief_id), stamp, body), "brief_id": str(result.brief.brief_id),
            "company_id": company_id, "ticker": result.brief.ticker, "created_at": stamp, "author": author, **body}


def append_record(record: Mapping[str, Any], *, path: Path | None = None) -> None:
    from shared.redaction import sensitive_payload_path

    if sensitive_payload_path(dict(record), "fact_checks") is not None:
        raise ContractViolation("內容像密鑰，拒收")
    target = path or FACT_CHECKS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# 還沒核的那幾版（⑤「敘事還沒逐句核對」的唯一判定）
# ---------------------------------------------------------------------------

def fact_check_gaps(briefs: Iterable[Any], *, stories: Mapping[str, Mapping[str, Any]],
                    records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """現行 v2 敘事裡還沒逐句核對的那幾版。`stories`：`current_stories()`（brief_id → 現行故事）。
    `since`＝這一筆從哪天開始等（敘事寫的那天與 `FACT_CHECK_SINCE` 取晚的；故事換了的取故事寫的那天）。依 ticker 字母列。"""
    latest: dict[str, Mapping[str, Any]] = {}
    for rec in records:
        head = latest.get(str(rec.get("brief_id")))
        if head is None or str(rec.get("created_at")) > str(head.get("created_at")):
            latest[str(rec.get("brief_id"))] = rec
    out = []
    for brief in briefs:
        if brief is None:
            continue
        story = stories.get(brief.brief_id)
        rec = latest.get(brief.brief_id)
        written = brief.created_at.astimezone(timezone.utc)
        floor = datetime(FACT_CHECK_SINCE.year, FACT_CHECK_SINCE.month, FACT_CHECK_SINCE.day, tzinfo=timezone.utc)
        if rec is None:
            kind, since = "brief", max(written, floor).isoformat()
        elif story is not None and str(rec.get("story_id") or "") != str(story.get("story_id")):
            kind, since = "story", max(str(story.get("created_at") or ""), floor.isoformat())
        else:
            continue
        out.append({"ticker": str(brief.ticker), "company_id": str(brief.company_id), "brief_id": brief.brief_id,
                    "kind": kind, "since": since,
                    "state": getattr(getattr(brief, "candidate_state", None), "state", None)})
    return sorted(out, key=lambda r: (r["ticker"], r["brief_id"]))


def gaps_now(*, today: date | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    """現在還沒核的現行敘事（⑤ 與 `python -m alpha brief-check --gaps` 共用，L16）。紀錄有壞行就 raise——
    讀不懂哪幾版核過，計數就是未讀到，不是 0（INV-3）。"""
    from alpha.providers.stories import current_stories, current_v2_briefs

    records, errors = read_records(path=path)
    if errors:
        raise ContractViolation(f"核對紀錄有 {len(errors)} 行讀不懂：{errors[0]}")
    stories, _story_errors = current_stories()
    return fact_check_gaps(current_v2_briefs(today=today), stories=stories, records=records)


__all__ = ["EXTRACTIONS_DIR", "FACT_CHECKS_PATH", "FACT_CHECK_GAP_KINDS", "FACT_CHECK_SINCE", "RefResolver", "append_record",
           "build_record", "carried_digests", "check_id", "company_names", "fact_check_gaps", "file_lines", "gaps_now",
           "read_records", "self_names"]
