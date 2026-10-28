"""首頁卡片的短名與一句「做什麼」（2026-10-28 使用者：「10 字左右的介紹吧。不然我也不會點進去」）。

研究 session 寫、只 append、一個檔（`library/private/alpha/taglines.jsonl`）；每家公司最新一筆是現行。
一筆＝短名（使用者叫得出的名字，例如「華星光」）＋一句做什麼（≤ `TAGLINE_MAX` 字）。**只寫做什麼，不寫判斷**：
不寫好壞、不寫數字（數字由 authority 填，首屏規則）；禁字表與敘事同一張（`alpha.narrative.contracts.FORBIDDEN_TERMS`，L16）。
它不 gate 任何東西、不寫 watch、不進圖；APP 首頁卡片照抄——沒寫就印押的層的中文名，再沒有就印「還沒寫介紹」。

**唯一的寫入入口是 `write_taglines`**：整批核對，任一筆不過就整批拒收、逐條說原因。壞行不靜默丟棄（INV-3）。
代號一律經名冊解析成 `co:*`（INV-1：不從公司名猜）；換名字或換一句就再 append 一筆，舊的留著。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from alpha.errors import ContractViolation

_ROOT = Path(__file__).resolve().parents[2]
TAGLINES_PATH = _ROOT / "library" / "private" / "alpha" / "taglines.jsonl"
#: 一句做什麼最多幾個字（使用者說「10 字左右」；留到 14 讓「CW DFB 雷射磊晶片」這類型號放得下）。
TAGLINE_MAX = 14
#: 短名最多幾個字（「聯亞」「華星光」「Sivers」；超過就是全名，卡片上已有）。
SHORT_NAME_MAX = 10
#: 一句裡不准出現的字元：placeholder 的括號（數字由 authority 填）、百分比、換行。
_BANNED_CHARS = ("{", "}", "%", "％", "\n", "\r")


def _text_problems(label: str, value: Any, limit: int) -> list[str]:
    from alpha.narrative.contracts import FORBIDDEN_TERMS

    if not isinstance(value, str) or not value.strip():
        return [f"{label} 必須是非空字串"]
    text = value.strip()
    out = []
    if len(text) > limit:
        out.append(f"{label}「{text}」有 {len(text)} 字，上限 {limit}")
    for ch in _BANNED_CHARS:
        if ch in text:
            out.append(f"{label}「{text}」含 {ch!r}——只寫做什麼，數字與 placeholder 不放這裡")
    for term in FORBIDDEN_TERMS:
        if term.lower() in text.lower():
            out.append(f"{label}「{text}」含首屏禁字 {term!r}")
    return out


def tagline_id(company_id: str, short_name: str, text: str, created_at: str) -> str:
    digest = hashlib.sha256("|".join((company_id, short_name, text, created_at)).encode("utf-8")).hexdigest()
    return "tl_" + digest[:16]


def read_records(*, path: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """全部紀錄；壞行回在第二個 list（不靜默丟）。"""
    target = path or TAGLINES_PATH
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
            for key in ("tagline_id", "company_id", "ticker", "short_name", "text", "created_at"):
                if not isinstance(raw.get(key), str) or not raw[key].strip():
                    raise ValueError(f"缺 {key}")
            records.append(raw)
        except ValueError as exc:
            errors.append(f"{target.name}:{number}: {str(exc)[:120]}")
    return records, errors


def current_taglines(*, path: Path | None = None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """每家公司（`co:*`）現行那一筆＝最新的一筆（created_at，同時刻比 id）；與壞行。"""
    records, errors = read_records(path=path)
    out: dict[str, dict[str, Any]] = {}
    for rec in records:
        cid = str(rec["company_id"])
        head = out.get(cid)
        if head is None or (rec["created_at"], rec["tagline_id"]) > (head["created_at"], head["tagline_id"]):
            out[cid] = rec
    return out, errors


def write_taglines(specs: Iterable[Mapping[str, Any]], *, path: Path | None = None, registry: Any = None,
                   now: datetime | None = None, author: str = "session") -> list[dict[str, Any]]:
    """唯一的寫入入口。`specs`：每筆 `ticker`、`short_name`、`text`（可帶 `company_id`，要與名冊解析一致）。

    整批核對：名冊解析得到、字數與禁字過、同一批不重複同一家、跟現行那一筆不完全一樣；任一筆不過就整批拒收。"""
    from shared.redaction import sensitive_payload_path

    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    current, _errors = current_taglines(path=path)
    problems: list[str] = []
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for i, spec in enumerate(specs, 1):
        where = f"第 {i} 筆"
        if not isinstance(spec, Mapping):
            problems.append(f"{where} 不是 object")
            continue
        ticker = str(spec.get("ticker") or "").strip()
        cid = registry.company_id_for_ticker(ticker) if ticker else None
        if cid is None:
            problems.append(f"{where}：{ticker or '（沒寫 ticker）'} 不在名冊（config/company_identity.json）——先補名冊，不從公司名猜（INV-1）")
            continue
        where = f"{where}（{ticker}）"
        if spec.get("company_id") and str(spec["company_id"]) != cid:
            problems.append(f"{where}：company_id {spec['company_id']} 與名冊解析的 {cid} 不一致")
            continue
        if cid in seen:
            problems.append(f"{where}：同一批裡同一家寫了兩次")
            continue
        seen.add(cid)
        bad = _text_problems("短名", spec.get("short_name"), SHORT_NAME_MAX) + \
            _text_problems("做什麼", spec.get("text"), TAGLINE_MAX)
        if bad:
            problems += [f"{where}：{b}" for b in bad]
            continue
        short_name, text = str(spec["short_name"]).strip(), str(spec["text"]).strip()
        head = current.get(cid)
        if head is not None and head["short_name"] == short_name and head["text"] == text:
            problems.append(f"{where}：跟現行那一筆（{head['tagline_id']}）一樣——不必再寫")
            continue
        record = {"tagline_id": tagline_id(cid, short_name, text, stamp), "company_id": cid, "ticker": ticker,
                  "short_name": short_name, "text": text, "created_at": stamp, "author": author}
        if head is not None:
            record["supersedes_id"] = head["tagline_id"]
        if sensitive_payload_path(dict(record), "taglines") is not None:
            problems.append(f"{where}：內容像密鑰，拒收")
            continue
        out.append(record)
    if problems:
        raise ContractViolation("介紹拒收（整批都沒寫）：\n  - " + "\n  - ".join(problems))
    target = path or TAGLINES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for record in out:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return out


__all__ = ["SHORT_NAME_MAX", "TAGLINES_PATH", "TAGLINE_MAX", "current_taglines", "read_records", "tagline_id",
           "write_taglines"]
