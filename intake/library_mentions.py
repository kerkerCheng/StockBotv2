"""入圖包的「庫內已有幾份」——prepare 當下由機器數（盲點修法 plan 2026-11-02-001 §1 第 20a 條；failure log #58）。

事發（2026-10-08，[750] Freiberger）：入圖包的「搜尋過程摘要」寫「自家庫先 grep：library/raw 與圖上都沒有 Freiberger（0）」，
實際有 8 份（AXT 自己的 10-K 與兩份 10-Q 的競爭者名單、全新／穩懋／英特磊年報的基板供應商名單），使用者據此 go。
「自家庫查過了」是寫的人自己宣告的數字，沒有任何機械核對（L18：標籤指不回原始證據）。

這裡只數、不放閘：focus 公司在名冊上的名稱與別名，在 `library/raw` 命中幾份。用途是自動生出問句（L18 末句）——
報告寫的份數跟這裡不同，寫的人要說明差在哪。比對寧可多算、附例子給人看，不可少算（少算正是事發的方向）。
名冊或目錄讀不到記 `upstream_unavailable`——那不是 0（L13：成功與失敗不得同形）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "library" / "raw"
#: 掃哪些副檔名（pdf 是二進位，抽成 txt 的那份會被掃到）。
TEXT_SUFFIXES = frozenset({".txt", ".md", ".htm", ".html", ".json"})
#: 審查文字最多列幾份例子（其餘寫總數）。
MAX_EXAMPLES = 8
#: 英數字詞短於這個長度時大小寫要一致（`AXT` 不比對 `axt`）；中日韓文名照子字串比對。
CASE_SENSITIVE_BELOW = 6
STATUSES = frozenset({"checked", "upstream_unavailable"})


def mention_terms(identity: Any) -> list[str]:
    """名冊名稱、別名與純英文字母的研究代號（≥3 字；數字代號太泛，不比）。"""
    terms = {str(identity.display_name or "").strip(), *(str(a).strip() for a in identity.name_aliases or ())}
    ticker = str(identity.research_ticker or "").split(".", 1)[0]
    if ticker.isascii() and ticker.isalpha() and len(ticker) >= 3:
        terms.add(ticker)
    return sorted(t for t in terms if len(t) >= 2)


def _pattern(term: str) -> re.Pattern[str]:
    if term.isascii():
        flags = 0 if len(term) < CASE_SENSITIVE_BELOW else re.IGNORECASE
        return re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", flags)
    return re.compile(re.escape(term))


def receipt(focus_company_id: str | None, *, raw_dir: Path | None = None, registry: Any = None) -> dict[str, Any]:
    """prepare 當下的收據：{status, company_id, terms, scanned, files, examples}；讀不到 {status, company_id, reason}。"""
    company_id = str(focus_company_id or "")
    try:
        if registry is None:
            from identity.registry import get_registry

            registry = get_registry()
        identity = registry.company(company_id)
    except Exception as exc:  # noqa: BLE001 — 名冊讀不到＝沒數，不是 0
        return {"status": "upstream_unavailable", "company_id": company_id,
                "reason": f"名冊讀不到（{type(exc).__name__}）"}
    if identity is None:
        return {"status": "upstream_unavailable", "company_id": company_id, "reason": "名冊沒有這個 co:*"}
    terms = mention_terms(identity)
    directory = raw_dir or RAW_DIR
    try:
        files = sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES)
    except OSError as exc:
        return {"status": "upstream_unavailable", "company_id": company_id,
                "reason": f"{directory.name} 讀不到（{type(exc).__name__}）"}
    if not files or not terms:
        reason = "沒有可比對的名稱" if not terms else f"{directory.name} 沒有任何文字檔"
        return {"status": "upstream_unavailable", "company_id": company_id, "reason": reason}
    patterns = [_pattern(t) for t in terms]
    hits: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(p.search(text) for p in patterns):
            hits.append(path.relative_to(directory).as_posix())
    return {"status": "checked", "company_id": company_id, "terms": terms, "scanned": len(files),
            "files": len(hits), "examples": hits[:MAX_EXAMPLES]}


def valid(check: object) -> bool:
    """紀錄上的收據形狀（`intake.actions._validate_record` 用）。"""
    if not isinstance(check, dict) or check.get("status") not in STATUSES:
        return False
    if check["status"] == "upstream_unavailable":
        return isinstance(check.get("reason"), str)
    return (isinstance(check.get("files"), int) and check["files"] >= 0 and isinstance(check.get("scanned"), int)
            and isinstance(check.get("terms"), list) and isinstance(check.get("examples"), list))


def render_lines(check: dict | None) -> list[str]:
    """審查文字的一節（只進決策區塊與乾跑；公開入圖報告不印——例子是 library/raw 的檔名，有些沒有追蹤）。"""
    if not check:
        return []
    lines = ["", "## 庫內已有幾份（prepare 當下機器數 library/raw；只印、不放閘）", ""]
    who = f"`{check.get('company_id')}`"
    if check.get("status") != "checked":
        lines.append(f"- {who}：**沒數到**（{check.get('reason')}）——這不是 0，報告裡的庫內份數沒有東西核對")
        return lines
    terms = "、".join(check["terms"])
    head = f"- {who}（名冊名稱與別名：{terms}）：掃 {check['scanned']} 份，**命中 {check['files']} 份**"
    if check["examples"]:
        rest = check["files"] - len(check["examples"])
        head += "——" + "、".join(check["examples"]) + (f"…另 {rest} 份" if rest > 0 else "")
    lines.append(head)
    lines.append("- 「搜尋過程摘要」寫的庫內份數跟這裡不同，以這裡為準、在報告裡說明差在哪（L18：標籤要指得回原始證據）。")
    return lines
