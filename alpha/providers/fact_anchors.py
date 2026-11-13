"""敘事事實句的逐字錨點紀錄（2026-11-13 使用者「照你推薦做吧」；plan `docs/plans/2026-11-13-001-dev-fact-anchor-plan.md`
Step A；failure log #163）：`library/private/alpha/fact_anchors.jsonl`（append-only）。

**一列＝一個事實**：它撐的句子指紋（可以多句——七格與故事裡講同一件事的句子都指向它，同一個事實只寫一處）、一手引用、逐字原文、
選填的衍生數字。規則（指紋、比對）住 `alpha.narrative.anchors`；這裡做三件事：

1. **寫入前驗證**（`validate_items`）：句子在現行那一版（敘事＋現行故事）、引用是一手或自家紀錄（`ANCHOR_REF_KINDS`）、
   原文逐字找得到（只正規化全半形、大小寫、繁簡、空白與換行，不跳字）、一手引用不是我們自己寫的字（節錄檔的 NOTE、改寫、
   Boundary——`SourceLine.own`）、衍生數字的數照原字在原文裡——任一條不過整批拒收。自家紀錄（使用者 11-13「自家句 A」）：
   讀圖的 quote 逐字在那份讀圖裡（判讀文字也算——自家句靠的就是它）；authority 的 quote 寫這句哪幾個數靠它（不驗逐字、
   不收衍生數字），引用要是這一檔自己的。
2. **讀**（`read_records`、`anchor_index`）：壞行回在第二個 list（INV-3）；被 `supersedes` 取代的錨點不算。
3. **還沒錨點的**（`anchor_gaps`）：⑤「事實句還沒錨點」與 `python -m alpha brief-anchor --gaps` 的唯一判定（L16）——宣告可開
   （含前提失效）與已持有的現行敘事裡，事實句沒全部綁錨點的那幾版（使用者 11-13 ②：其餘狀態換版時才補）。

它不 gate 任何東西、不改候選狀態、不寫 watch（③：先只印、量過再談）。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from alpha.errors import ContractViolation
from alpha.narrative.anchors import ANCHOR_REF_KINDS, DERIVE_OPS, Anchor, derive_problems, fingerprint
from alpha.narrative.fact_check import ResolvedRef, Sentence, classify_ref, squash

_ROOT = Path(__file__).resolve().parents[2]
FACT_ANCHORS_PATH = _ROOT / "library" / "private" / "alpha" / "fact_anchors.jsonl"
_REQUIRED = ("anchor_id", "company_id", "ticker", "created_at", "ref", "quote")
_FINGERPRINT = re.compile(r"[0-9a-f]{16}")
#: ⑤ 管哪幾種現行敘事（使用者 11-13 ②；涵蓋登記表從這裡列舉——L16）：已持有、宣告可開（含前提失效、邊緣無法量）。
ANCHOR_SCOPE: tuple[str, ...] = ("held", "open")
#: 這條規則從哪一天起算：之前寫的敘事等的天數從這天算。
ANCHOR_SINCE = date(2026, 11, 13)
#: 宣告可開的狀態字（`priced_wait` 是 11-03 之前的舊紀錄，讀成可開）。
_OPEN_STATES = ("open", "priced_wait")
QUOTE_MIN_CHARS = 4


def read_records(*, path: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """全部錨點；壞行回在第二個 list（不靜默丟，INV-3）。"""
    target = path or FACT_ANCHORS_PATH
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
            fps = raw.get("fingerprints")
            if not isinstance(fps, list) or not fps or not all(isinstance(f, str) and _FINGERPRINT.fullmatch(f) for f in fps):
                raise ValueError("fingerprints 要是非空的 16 碼 list")
            derive = raw.get("derive")
            if derive is not None and (not isinstance(derive, dict) or derive.get("op") not in DERIVE_OPS):
                raise ValueError("derive 的 op 不在封閉字彙")
            if not isinstance(raw.get("supersedes") or [], list):
                raise ValueError("supersedes 要是 list")
            records.append(raw)
        except ValueError as exc:
            errors.append(f"{target.name}:{number}: {str(exc)[:120]}")
    return records, errors


def anchor_index(company_id: str, records: Iterable[Mapping[str, Any]]) -> dict[str, list[Anchor]]:
    """這一家：句子指紋 → 錨點（照寫的順序；被 `supersedes` 取代的不算）。"""
    rows = sorted((r for r in records if r.get("company_id") == company_id), key=lambda r: str(r.get("created_at")))
    retired = {str(s) for r in rows for s in r.get("supersedes") or ()}
    out: dict[str, list[Anchor]] = {}
    for r in rows:
        if r["anchor_id"] in retired:
            continue
        anchor = Anchor(str(r["anchor_id"]), str(r["ref"]), str(r["quote"]), r.get("derive"))
        for fp in r["fingerprints"]:
            out.setdefault(str(fp), []).append(anchor)
    return out


# ---------------------------------------------------------------------------
# 寫入前驗證
# ---------------------------------------------------------------------------

def _blocks(resolved: ResolvedRef) -> tuple[list[str], list[str]]:
    """(一手原文的連續段, 我們自己寫的行)，都 `squash` 過。同一檔相鄰的行（含長行切開的那幾段）接成一段——原文跨行（PDF 斷行）
    的 quote 才找得到；中間隔了空行、標示行或我們的段落就斷開。逐字引文（`doc（locator）`）與引號內那一行各自一段。"""
    primary: list[str] = []
    own: list[str] = []
    current: list[str] = []
    last: int | None = None

    def flush() -> None:
        if current:
            primary.append("".join(current))
            current.clear()

    for line in resolved.lines:
        if line.own:
            own.append(squash(line.text))
            flush()
            last = None
            continue
        m = re.search(r":(\d+)$", line.label)
        number = int(m.group(1)) if m else None
        # 行號跳號（中間有空行、標示行）或倒退（同一條引用接了另一個檔）就斷開；同一行切開的幾段（行號相同）接著
        if number is None or last is None or number - last not in (0, 1):
            flush()
        current.append(squash(line.text))
        last = number
        if number is None:
            flush()
    flush()
    return primary, own


def quote_problem(quote: str, resolved: ResolvedRef, *, own_ok: bool = False) -> str | None:
    """這段字是不是逐字在這條引用裡；是＝None。`own_ok`：讀圖錨點——判讀文字（我們寫的）也算，整份接起來比（長段落切成好幾塊，
    quote 可以跨塊）。"""
    q = squash(quote)
    if len(q) < QUOTE_MIN_CHARS:
        return f"quote 太短（去掉空白後至少 {QUOTE_MIN_CHARS} 個字）"
    if resolved.problem:
        return f"引用讀不到：{resolved.problem}"
    primary, own = _blocks(resolved)
    if any(q in block for block in primary) or (own_ok and q in "".join(own)):
        return None
    # 我們自己寫的：段落續行（`own`）與標示行（NOTE、出處、標題——`file_lines` 不收、`meta` 照留）
    if any(q in line for line in own) or any(q in squash(m) for m in resolved.meta):
        return "這段字只在我們自己寫的段落或標示行裡（NOTE、改寫、Boundary、出處）——錨點要一手原文"
    return "原文裡找不到這段字（只正規化全半形、大小寫、繁簡、空白與換行；不跳字、不改字）"


def authority_problem(ref: str, quote: str, *, ticker: str) -> str | None:
    """authority 錨點：引用是這一檔自己的（路徑裡有代號）、quote 寫了靠它的是哪幾個數；是＝None。"""
    if ticker and not re.search(rf"(?<![A-Za-z0-9.]){re.escape(ticker.upper())}(?![A-Za-z0-9])", ref.upper()):
        return f"authority 引用要是 {ticker} 自己的（收到 {ref}）"
    if len(squash(quote)) < QUOTE_MIN_CHARS:
        return f"authority 錨點的 quote 寫這句哪幾個數靠它（去掉空白後至少 {QUOTE_MIN_CHARS} 個字）"
    return None


def validate_items(items: Any, *, company_id: str, sentences: Sequence[Sentence], resolve: Callable[[str], ResolvedRef],
                   known_ids: Iterable[str] = (), ticker: str = "") -> tuple[list[dict[str, Any]], list[str]]:
    """spec（`[{sentences, ref, quote, derive?, supersedes?}]`）→ (整理好的項目, 錯誤)。有任何錯誤＝整批不收（回空 list）。
    `sentences`：現行那一版的句子（`fact_check.build_sentences`，含現行故事）；`known_ids`：這一家已有的錨點 id（supersedes 用）；
    `ticker`：authority 引用要是這一檔自己的。"""
    if not isinstance(items, list) or not items:
        return [], ["spec 要是非空的 list：[{\"sentences\": [句子原文…], \"ref\": …, \"quote\": …}]"]
    current = {fingerprint(company_id, s.text) for s in sentences}
    known = set(known_ids)
    out: list[dict[str, Any]] = []
    errors: list[str] = []
    for i, item in enumerate(items, 1):
        where = f"第 {i} 項"
        if not isinstance(item, Mapping):
            errors.append(f"{where}：不是 object")
            continue
        texts = item.get("sentences")
        texts = [texts] if isinstance(texts, str) else texts
        if not isinstance(texts, list) or not texts or not all(isinstance(t, str) and t.strip() for t in texts):
            errors.append(f"{where}：sentences 要是非空的句子 list（照現行那一版一字不差）")
            continue
        fps = []
        for text in texts:
            fp = fingerprint(company_id, text)
            if fp not in current:
                errors.append(f"{where}：「{text[:40]}」不在現行那一版（句子要一字不差；改過的句子先換版再綁）")
            fps.append(fp)
        ref = str(item.get("ref") or "").strip()
        quote = str(item.get("quote") or "").strip()
        kind = classify_ref(ref)
        if kind not in ANCHOR_REF_KINDS:
            errors.append(f"{where}：引用要是一手原文（library/raw/…、graph://source/…）或自家紀錄（讀圖 sr_…、alpha://…、"
                          f"engine_c://…）；收到的是 {kind}")
        else:
            problem = (authority_problem(ref, quote, ticker=ticker) if kind == "authority"
                       else quote_problem(quote, resolve(ref), own_ok=kind == "reading"))
            if problem:
                errors.append(f"{where}：{problem}")
        derive = item.get("derive")
        if derive is not None and kind == "authority":
            errors.append(f"{where}：authority 錨點不收衍生數字（quote 不是原文，沒有數可算）")
        elif derive is not None:
            errors += [f"{where}：{p}" for p in derive_problems(derive, quote=quote, sentences=texts)]
        supersedes = item.get("supersedes") or []
        supersedes = [supersedes] if isinstance(supersedes, str) else supersedes
        if not isinstance(supersedes, list) or any(str(s) not in known for s in supersedes):
            errors.append(f"{where}：supersedes 要指這一家已有的錨點 id")
        out.append({"fingerprints": list(dict.fromkeys(fps)), "sentences": [t.strip()[:200] for t in texts], "ref": ref,
                    "quote": quote, **({"derive": dict(derive)} if isinstance(derive, Mapping) else {}),
                    **({"supersedes": [str(s) for s in supersedes]} if supersedes else {})})
    return ([] if errors else out), errors


def build_record(item: Mapping[str, Any], *, company_id: str, ticker: str, now: datetime | None = None,
                 author: str = "session") -> dict[str, Any]:
    """一筆錨點（不寫檔）。`item`：`validate_items` 整理好的一項。"""
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    body = {"company_id": company_id, "ticker": ticker, **{k: item[k] for k in ("fingerprints", "sentences", "ref", "quote")},
            **({"derive": item["derive"]} if item.get("derive") else {}),
            **({"supersedes": item["supersedes"]} if item.get("supersedes") else {})}
    canonical = json.dumps({**body, "created_at": stamp}, ensure_ascii=False, sort_keys=True)
    return {"anchor_id": "fa_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16], "created_at": stamp,
            "author": author, **body}


def append_records(records: Sequence[Mapping[str, Any]], *, path: Path | None = None) -> None:
    from shared.redaction import sensitive_payload_path

    for record in records:
        if sensitive_payload_path(dict(record), "fact_anchors") is not None:
            raise ContractViolation("內容像密鑰，拒收")
    target = path or FACT_ANCHORS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# 還沒錨點的那幾版（⑤「事實句還沒錨點」的唯一判定）
# ---------------------------------------------------------------------------

def anchor_gaps(briefs: Iterable[Any], *, stories: Mapping[str, Mapping[str, Any]], records: Iterable[Mapping[str, Any]],
                held: Iterable[str], names: Mapping[str, Sequence[str]]) -> list[dict[str, Any]]:
    """已持有與宣告可開的現行 v2 敘事裡，事實句（`SentenceClaims.is_fact`）沒全部綁錨點的那幾版。`held`：已持有的代號
    （候選板的持股——讀不到由呼叫端報未讀到，不在這裡猜）；`stories`：`current_stories()`。依代號字母列。"""
    from alpha.narrative.fact_check import brief_text_from_record, build_sentences, sentence_claims
    from alpha.providers.fact_checks import self_names

    rows = list(records)
    held_set = {str(t).upper() for t in held}
    floor = datetime(ANCHOR_SINCE.year, ANCHOR_SINCE.month, ANCHOR_SINCE.day, tzinfo=timezone.utc)
    out = []
    for brief in briefs:
        if brief is None:
            continue
        state = getattr(getattr(brief, "candidate_state", None), "state", None)
        scope = "held" if str(brief.ticker).upper() in held_set else ("open" if state in _OPEN_STATES else None)
        if scope is None:
            continue
        text = brief_text_from_record(brief)
        mine = self_names(str(brief.company_id), str(brief.ticker), names)
        facts = [s for s in build_sentences(text, story=stories.get(brief.brief_id))
                 if sentence_claims(s, self_names=mine, as_of=text.as_of).is_fact]
        index = anchor_index(str(brief.company_id), rows)
        missing = [s for s in facts if fingerprint(str(brief.company_id), s.text) not in index]
        if not missing:
            continue
        out.append({"ticker": str(brief.ticker), "company_id": str(brief.company_id), "brief_id": brief.brief_id,
                    "scope": scope, "facts": len(facts), "missing": len(missing),
                    "since": max(brief.created_at.astimezone(timezone.utc), floor).isoformat()})
    return sorted(out, key=lambda r: (r["ticker"], str(r["brief_id"])))


def held_from_board(board: Mapping[str, Any] | None) -> list[str] | None:
    """候選板上已持有的代號；板沒讀到或那一版持股沒讀到＝None（未讀到，不是 0——INV-3）。"""
    if board is None or ((board.get("holdings") or {}).get("status") or "ok") != "ok":
        return None
    return [str(r.get("ticker")) for r in (board.get("groups") or {}).get("held") or () if r.get("ticker")]


def held_now() -> list[str] | None:
    """現在這一塊候選板上已持有的代號（`brief-anchor --gaps` 用；心跳直接傳它讀到的板子）。讀不到＝None。"""
    try:
        from webapp.store import StateArtifactStore

        board, _freshness = StateArtifactStore().read("candidates")
    except Exception:  # noqa: BLE001 — 讀不到就說讀不到
        return None
    return held_from_board(board)


def gaps_now(*, held: Iterable[str], today: date | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    """現在還沒錨點的（⑤ 與 `python -m alpha brief-anchor --gaps` 共用，L16）。紀錄有壞行就 raise——讀不懂哪幾句綁過，
    計數就是未讀到，不是 0（INV-3）。"""
    from alpha.providers.fact_checks import company_names
    from alpha.providers.stories import current_stories, current_v2_briefs

    records, errors = read_records(path=path)
    if errors:
        raise ContractViolation(f"錨點紀錄有 {len(errors)} 行讀不懂：{errors[0]}")
    stories, _story_errors = current_stories()
    return anchor_gaps(current_v2_briefs(today=today), stories=stories, records=records, held=held, names=company_names())


__all__ = ["ANCHOR_SCOPE", "ANCHOR_SINCE", "FACT_ANCHORS_PATH", "QUOTE_MIN_CHARS", "anchor_gaps", "anchor_index",
           "append_records", "build_record", "gaps_now", "held_from_board", "held_now", "quote_problem", "read_records",
           "validate_items"]
