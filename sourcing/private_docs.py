"""私有文件索引：使用者交來的券商報告與文件，按名冊公司建「哪幾頁點名它」（failure log #141；
ROADMAP「私有券商報告建索引、讀某檔時列出點名它的報告」，2026-11-10）。

## 為什麼

事發兩次：①磷化銦基板層讀圖與 AXTI 敘事一路引用 Reuters 不具名人士的說法，一份 10-20 就讀過的私有券商報告（凱基 08-18）
對同一件事有不同的寫法，從沒進判讀；②1519.TW 的 [897] 向使用者要的東西，私有區早有一份（元大 09-11 的華城段）。私有報告
沒有按公司索引，而 Grep 工具（ripgrep）預設略過 gitignore 的 `library/private/`——查證時 0 命中。

## 做什麼、不做什麼

- 掃 `library/private/broker_reports/` 與 `library/private/inbox/`（`engine_b.todo` 叫使用者放文件的地方）的 PDF 與文字檔；
  同一個資料夾裡同名的 .pdf／.txt 算一份——頁碼取 PDF（pypdf 逐頁抽字），抽不出字才退回文字檔的 `=== PAGE N ===`。
- 名字比對用 `query.bottleneck.quote_names_company`（名字比對的唯一 owner：名稱、去法律尾綴的核心名、別名；單字分大小寫；
  兩家共用的寫法不算）；另加券商寫法「名稱(代號 TT)」的台股代號——名冊別名常是全名（全新光電），報告寫簡稱＋代號。
- **不抄內容**：索引只有日期、券商、檔名、頁數、每家公司被點名的頁碼與檔案指紋；索引檔住 `library/private/`，不進 repo。
- 券商只指路、不當證據（L8）：列出來是讓研究去讀那幾頁，讀到的主張照舊要一手印證。
- 抽不出字的（掃描檔、檔案壞掉）照實記在索引裡、每次查詢都印（INV-3）——那幾份是「沒核」，不是「沒點名」。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "library" / "private"
#: 掃哪幾個目錄：整理過的券商報告，與使用者交來的文件。
ROOTS: tuple[Path, ...] = (PRIVATE / "broker_reports", PRIVATE / "inbox")
#: 索引檔（只有指紋與頁碼，不抄內容）。
INDEX_PATH = PRIVATE / "private_docs_index.json"
#: 改了 `describe`／`mentions`／`pages_of` 的規則就加 1——舊索引整份重掃（指紋沒變的文件也一樣）。
INDEX_VERSION = 1
DOC_SUFFIXES = frozenset({".pdf", ".txt"})
#: 抽好的文字檔的分頁記號；沒有記號整份算第 1 頁。
PAGE_MARK = re.compile(r"^=== PAGE (\d+) ===[ \t]*$", re.MULTILINE)
#: 檔名慣例：`YYYY-MM-DD_券商_公司-代號_類型_標題_語言.pdf`；產業報告沒有「公司-代號」。
_NAMED = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<broker>[^_]+)_(?P<rest>.+)$")
#: 資料夾名只有「日期_券商」（`2026-08-18_kgi/kgi_20260818.pdf`）。
_FOLDER = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<broker>[^_]+)(?:_.*)?$")
_SUBJECT = re.compile(r"^(?P<name>[^_]+?)-(?P<code>\d{4,6})(?:_|$)")
_COMPACT_DATE = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")


def code_pattern(code: str) -> re.Pattern[str]:
    """券商寫台股代號的樣子：「(2455 TT)」「（2455）」「2455 TT」「2455.TW」——裸數字不算（年份、金額）。"""
    return re.compile(r"(?:[（(]\s*" + code + r"(?:[\s.]*[A-Z]{2,3})?\s*[)）])"
                      r"|(?:(?<![\d.])" + code + r"(?:\s*(?:TT|TW|TWO)|\.TWO?)(?![A-Za-z0-9]))")


def _numeric_code(company: Any) -> str | None:
    base = str(getattr(company, "research_ticker", None) or "").split(".", 1)[0]
    return base if base.isdigit() and len(base) >= 4 else None


def discover(roots: Sequence[Path] = ROOTS) -> list[tuple[Path, Path | None, Path]]:
    """(文件, 同名文字檔, 根目錄)：同一個資料夾裡同名的 .pdf 與 .txt 算一份；只有 .txt 的文件就是它自己。"""
    found: dict[Path, dict[str, Path]] = {}
    owner: dict[Path, Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in DOC_SUFFIXES:
                stem = path.with_suffix("")
                found.setdefault(stem, {})[path.suffix.lower()] = path
                owner.setdefault(stem, root)
    return [(by.get(".pdf") or by[".txt"], by.get(".txt"), owner[stem]) for stem, by in sorted(found.items())]


def _text_pages(path: Path) -> list[tuple[int, str]]:
    body = path.read_text(encoding="utf-8", errors="ignore")
    marks = list(PAGE_MARK.finditer(body))
    if not marks:
        return [(1, body)]
    return [(int(m.group(1)), body[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(body))])
            for i, m in enumerate(marks)]


def _pdf_pages(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader

    logging.getLogger("pypdf").setLevel(logging.ERROR)          # 字典重複定義之類的警告不是讀不到
    return [(n, page.extract_text() or "") for n, page in enumerate(PdfReader(str(path)).pages, 1)]


def pages_of(doc: Path, text: Path | None) -> tuple[list[tuple[int, str]] | None, str | None, str | None]:
    """(頁, 抽不出字的理由, 字從哪來)：PDF 優先（頁碼準），抽不出字才用同名文字檔；文件本身是 .txt 就讀它。"""
    reasons = []
    if doc.suffix.lower() == ".txt":
        text = doc
    elif doc.suffix.lower() == ".pdf":
        try:
            pages = _pdf_pages(doc)
            if any(body.strip() for _n, body in pages):
                return pages, None, "pdf"
            reasons.append("PDF 每一頁都抽不出字（多半是掃描檔）")
        except Exception as exc:  # noqa: BLE001 — 壞檔照實記，不帶走整批
            reasons.append(f"PDF 讀不到（{type(exc).__name__}）")
    if text is not None:
        try:
            pages = _text_pages(text)
            if any(body.strip() for _n, body in pages):
                return pages, None, "txt"
            reasons.append("文字檔是空的")
        except OSError as exc:
            reasons.append(f"文字檔讀不到（{type(exc).__name__}）")
    return None, "；".join(reasons) or "沒有可讀的字", None


def describe(doc: Path) -> dict[str, Any]:
    """檔名（或資料夾名）上的日期、券商、主題公司代號；讀不出的留 null，不猜。"""
    m = _NAMED.match(doc.stem)
    if m:
        subject = _SUBJECT.match(m["rest"])
        return {"date": m["date"], "broker": m["broker"], "title": m["rest"],
                "subject_code": subject["code"] if subject else None}
    folder = _FOLDER.match(doc.parent.name)
    compact = _COMPACT_DATE.search(doc.stem)
    date = folder["date"] if folder else (f"{compact[1]}-{compact[2]}-{compact[3]}" if compact else None)
    return {"date": date, "broker": folder["broker"] if folder else None, "title": doc.stem, "subject_code": None}


def mentions(pages: Iterable[tuple[int, str]], registry: Any, *, shared: frozenset[str] | None = None
             ) -> dict[str, list[int]]:
    """每家名冊公司被點名的頁碼（名字照 `quote_names_company`；台股另認券商的代號寫法）。"""
    from query.bottleneck import quote_names_company, shared_name_forms

    shared = shared_name_forms(registry) if shared is None else shared
    codes = {cid: code_pattern(code) for cid, code in
             ((c.company_id, _numeric_code(c)) for c in registry.companies) if code}
    out: dict[str, list[int]] = {}
    for number, body in pages:
        for company in registry.companies:
            cid = company.company_id
            code = codes.get(cid)
            if quote_names_company(body, company, shared=shared) or (code is not None and code.search(body)):
                out.setdefault(cid, []).append(number)
    return out


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _names_digest(registry: Any) -> str:
    """名冊的名字與代號一變，整份重掃（新登記的公司要能回頭找到舊報告）。"""
    from query.bottleneck import company_name_forms

    payload = sorted((str(c.company_id), list(company_name_forms(c)), _numeric_code(c)) for c in registry.companies)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def load_index(path: Path = INDEX_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def refresh(*, roots: Sequence[Path] = ROOTS, index_path: Path = INDEX_PATH, registry: Any = None,
            now: datetime | None = None) -> dict[str, Any]:
    """增量重建索引：指紋（大小＋修改時間）沒變、名冊名字沒變的就沿用；寫回 `index_path`。"""
    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    from query.bottleneck import shared_name_forms

    digest = _names_digest(registry)
    old = load_index(index_path)
    reusable = ({d["path"]: d for d in old.get("docs") or () if isinstance(d, dict) and d.get("path")}
                if old.get("version") == INDEX_VERSION and old.get("names_digest") == digest else {})
    shared = shared_name_forms(registry)
    by_code: dict[str, list[str]] = {}
    for company in registry.companies:
        code = _numeric_code(company)
        if code:
            by_code.setdefault(code, []).append(company.company_id)
    docs = []
    for doc, text, _root in discover(roots):
        sibling = text if text is not None and text != doc else None
        fingerprint = ":".join(str(v) for v in (doc.stat().st_size, doc.stat().st_mtime_ns)) + (
            f"|{sibling.stat().st_size}:{sibling.stat().st_mtime_ns}" if sibling is not None else "")
        rel = _rel(doc)
        previous = reusable.get(rel)
        if previous is not None and previous.get("fingerprint") == fingerprint:
            docs.append(previous)
            continue
        meta = describe(doc)
        pages, why, text_from = pages_of(doc, sibling)
        docs.append({"path": rel, "text_path": _rel(sibling) if sibling is not None else None,
                     "fingerprint": fingerprint, "sha256": _sha256(doc), **meta,
                     "subject_ids": sorted(by_code.get(str(meta["subject_code"]), ())) if meta.get("subject_code") else [],
                     "pages": len(pages) if pages is not None else None, "text_from": text_from, "unreadable": why,
                     "mentions": mentions(pages, registry, shared=shared) if pages is not None else {}})
    index = {"version": INDEX_VERSION, "names_digest": digest,
             "generated_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
             "roots": [_rel(r) for r in roots], "docs": docs}
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = index_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(index_path)
    return index


def docs_for(index: Mapping[str, Any], company_id: str) -> list[dict[str, Any]]:
    """點名這家公司（或檔名主題是它）的文件，新的在前；同一份檔（sha256 相同）放在不同資料夾只列一次、其餘路徑附在 `also`。"""
    picked: dict[str, dict[str, Any]] = {}
    for doc in index.get("docs") or ():
        pages = (doc.get("mentions") or {}).get(company_id) or []
        subject = company_id in (doc.get("subject_ids") or ())
        if not pages and not subject:
            continue
        key = str(doc.get("sha256") or doc.get("path"))
        if key in picked:
            picked[key]["also"].append(doc["path"])
            continue
        picked[key] = {**doc, "hit_pages": pages, "is_subject": subject, "also": []}
    return sorted(picked.values(), key=lambda d: (str(d.get("date") or ""), str(d.get("path"))), reverse=True)


def unreadable(index: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [d for d in index.get("docs") or () if d.get("unreadable")]


def _pages_text(pages: Sequence[int]) -> str:
    return "第 " + "、".join(str(p) for p in pages) + " 頁" if pages else "內文沒點名（檔名主題）"


def render(company_id: str, label: str, docs: Sequence[Mapping[str, Any]], index: Mapping[str, Any]) -> list[str]:
    lines = [f"# {label}：私有文件裡點名它的 {len(docs)} 份（券商只指路、不當證據——讀那幾頁、主張照舊要一手印證；內容不進 repo）"]
    for d in docs:
        bits = [str(d.get("date") or "日期不明"), str(d.get("broker") or "券商不明"), str(d.get("title") or d["path"])]
        where = _pages_text(d.get("hit_pages") or ()) + (f"（共 {d['pages']} 頁）" if d.get("pages") else "")
        also = f"（同一份另在：{'、'.join(d['also'])}）" if d.get("also") else ""
        lines.append(f"- {'｜'.join(bits)}｜{where}{'｜報告主題' if d.get('is_subject') else ''}｜{d['path']}{also}")
    bad = unreadable(index)
    total = len(index.get("docs") or ())
    lines.append(f"索引 {total} 份" + (f"；抽不出字 {len(bad)} 份沒核（不是沒點名）：" + "、".join(d["path"] for d in bad)
                                       if bad else "；全部讀得到字"))
    return lines


def _resolve(raw: str, registry: Any) -> tuple[str, str] | None:
    """代號或 co:* → (company_id, 印出來的名字)；名冊沒有就 None（不猜，INV-1）。"""
    if raw.startswith("co:"):
        return (raw, raw) if registry.has_company(raw) else None
    cid = registry.company_id_for_ticker(raw.strip().upper())
    return (cid, f"{raw.strip().upper()}（{cid}）") if cid else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sourcing.private_docs",
                                     description="私有文件裡點名某家公司的報告與頁碼（先增量重建索引；唯讀於報告本身）")
    parser.add_argument("targets", nargs="+", help="研究代號或 co:*")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    from identity.registry import get_registry

    registry = get_registry()
    index = refresh(registry=registry)
    failed = 0
    payload: dict[str, Any] = {}
    for raw in args.targets:
        resolved = _resolve(raw, registry)
        if resolved is None:
            print(f"✗ {raw}：名冊沒有（「找不到」與「不存在」是兩個 claim——先確認要不要 onboard）", file=sys.stderr)
            failed += 1
            continue
        cid, label = resolved
        docs = docs_for(index, cid)
        payload[raw] = {"company_id": cid, "docs": docs}
        if args.format == "markdown":
            print("\n".join(render(cid, label, docs, index)))
    if args.format == "json":
        payload["_index"] = {"docs": len(index.get("docs") or ()), "unreadable": [d["path"] for d in unreadable(index)]}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
