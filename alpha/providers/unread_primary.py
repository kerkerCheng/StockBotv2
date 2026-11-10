"""換版收據：上一版之後才進池、這一版沒指到的一手（failure log #32；plan 2026-11-10-001 G，使用者 11-10 選 A）。

**事發：** 缺 X 回掃（11-09）重寫 17 檔敘事時，有一手已經在手上卻沒被讀到——2455.TW、600105.SS 的那份在自家庫，寫的人沒想到要查。
重放推翻了「多半是手上有、沒引用」的前提（17 檔裡只有 2 檔是，其餘是根本沒抓進來，那一半由 H #148 補覆蓋），所以使用者選收窄版：
**只做個股敘事、只列上一版之後才進來的一手、最多 5 則、只印不擋**；讀圖那一半（#139）不做——同一層的檔太多，列出來恆亮（L14-4）。

**列什麼：** 窗＝（上一版寫入，這一版寫入〕。
- lead 池：來源宣告一手、不是持股申報（與語意 watch 的 T0 同一份排除清單）、實體有這家公司、**進池時間**在窗內——用進池不用發布日：
  回補（#148）與擴大監看範圍會把舊文件在今天登記，上一版的作者在池裡看不到它們。
- 自家庫（`library/raw` 的文字檔）：檔案時間在窗內、點名這家公司（名字比對的唯一來源 `query.bottleneck.quote_names_company`；
  台股另認代號寫法）——別家公司的文件點名它，正是 #32 的形狀。
- **「指到」**＝這一版的紀錄（整筆 JSON）裡出現它的指標：lead 的 id、網址、refs 記的一手位置；EDGAR lead 另認自家庫檔名
  「代號_表單_申報日（10-Q 換季別、10-K 換年度）」——節錄檔讀過就算指到；自家庫檔以主檔名比。指標比對是近似：列出來的
  是「沒指到」，不是「沒讀過」——讀過且無關就略過。

排序：非例行的先（例行重訊——注意交易、法說會、澄清——排後面，不丟），再照發布日新到舊。截斷必須說話（INV-3）：印「另有 N 則」。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "library" / "raw"
LIMIT = 5
TEXT_SUFFIXES = frozenset({".txt", ".md", ".htm", ".html"})
#: lead 的 refs 裡指向一手位置的鍵（`config/lead_ref_keys.json`）。
_POINTER_REFS = ("canonical_url", "primary_url", "source_doc", "mops_history_query")
_EDGAR_TITLE = re.compile(r"^(?P<ticker>\S+) (?P<form>.+?) filed (?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})")


@dataclass(frozen=True)
class UnreadItem:
    kind: str                 # "lead" | "raw"
    entered: datetime         # 進池（lead 的 first_seen）或進庫（檔案時間）
    published: str | None     # 發布日（lead）；自家庫沒有就 None
    label: str
    pointer: str              # lead_id（＋網址）或 library/raw/<檔名>
    routine: bool = False


def _when(value: Any) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def previous_written_at(records: Sequence[Any], brief_id: str) -> datetime | None:
    """這一版之前、還算數的最近一版的寫入時間——撤回紀錄本身與被撤回的那一版都不算。沒有就 None（第一版）。"""
    retracted = {str(r.supersedes_id) for r in records if getattr(r, "retracted", False) and r.supersedes_id}
    current = next((r for r in records if r.brief_id == brief_id), None)
    if current is None:
        return None
    earlier = [r.created_at for r in records
               if r.brief_id != brief_id and not r.retracted and r.brief_id not in retracted
               and r.created_at < current.created_at]
    return max(earlier, default=None)


def _edgar_raw_pattern(lead: Mapping[str, Any]) -> re.Pattern[str] | None:
    """EDGAR lead → 自家庫檔名的比對式（節錄讀過就算指到）：`<代號>_<表單>_<申報日｜季別｜年度>`。"""
    match = _EDGAR_TITLE.match(str(lead.get("title") or "").strip())
    if not match:
        return None
    ticker = match["ticker"].split(".")[0].lower()
    form = match["form"].strip().lower()
    forms = {re.sub(r"[-/ ]", "", form), re.sub(r"[-/ ]", "_", form)}
    year, month = int(match["y"]), int(match["m"])
    periods = {f"{match['y']}{match['m']}{match['d']}"}
    if form.startswith("10-q") and month > 2:
        periods.add(f"{year}q{(month - 2) // 3}")
    if form.startswith(("10-k", "20-f", "40-f")):
        periods.add(f"fy{year - 1}")
    return re.compile(r"library/raw/" + re.escape(ticker) + r"_(?:" + "|".join(map(re.escape, sorted(forms)))
                      + r")_[^\"]*?(?:" + "|".join(map(re.escape, sorted(periods))) + r")")


def lead_pointed(lead: Mapping[str, Any], blob: str) -> bool:
    refs = lead.get("refs") or {}
    tokens = [lead.get("lead_id"), lead.get("url"), *(refs.get(key) for key in _POINTER_REFS)]
    if any(token and str(token) in blob for token in tokens):
        return True
    pattern = _edgar_raw_pattern(lead)
    return bool(pattern and pattern.search(blob))


def unread_leads(company_id: str, start: datetime, end: datetime, blob: str, leads: Mapping[str, Mapping[str, Any]], *,
                 ownership_forms: Iterable[str], entities_of, category_of,
                 routine: frozenset[str] = frozenset()) -> tuple[list[UnreadItem], dict[str, int]]:
    """窗內進池、這一版沒指到的一手 lead。`entities_of`／`category_of`／`routine` 由呼叫端注入（`engine_b.entities.lead_entities`、
    `engine_b.announcement_category.lead_category`／`ROUTINE`）——本函式不自己 import engine_b，方便測試。"""
    excluded = {str(f).strip().upper() for f in ownership_forms}
    items: list[UnreadItem] = []
    counts = {"window": 0, "pointed": 0}
    for lead_id, lead in leads.items():
        if lead.get("source_class") != "primary" or str(lead.get("form_type") or "").strip().upper() in excluded:
            continue
        seen = _when(lead.get("first_seen"))
        if seen is None or not start < seen <= end:
            continue
        if lead.get("company_id") != company_id and company_id not in entities_of(lead):
            continue
        counts["window"] += 1
        if lead_pointed(lead, blob):
            counts["pointed"] += 1
            continue
        category = category_of(lead) or {}
        url = str(lead.get("url") or "")
        items.append(UnreadItem(
            kind="lead", entered=seen, published=str(lead.get("published_at") or "")[:10] or None,
            label=re.sub(r"\s+", " ", str(lead.get("title") or "")).strip()[:70],
            pointer=lead_id + (f" {url}" if url.startswith("https://www.sec.gov/") else ""),
            routine=category.get("category") in routine))
    return items, counts


def unread_raw(ticker: str, start: datetime, end: datetime, blob: str, *, raw_dir: Path = RAW_DIR,
               names) -> tuple[list[UnreadItem], dict[str, int]]:
    """窗內進庫、點名這家公司、這一版沒指到的自家庫檔。`names(text) -> bool`＝點名比對（呼叫端組好）。"""
    items: list[UnreadItem] = []
    counts = {"window": 0, "pointed": 0, "unchecked": 0}
    if not raw_dir.is_dir():
        return items, counts
    for path in raw_dir.iterdir():
        if not path.is_file() or path.name.endswith(".meta.json"):
            continue
        entered = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if not start < entered <= end:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            counts["unchecked"] += 1          # PDF 等：沒核，不是沒點名（INV-3）
            continue
        meta = path.with_name(path.stem + ".meta.json")
        own = False
        if meta.exists():
            try:
                own = str(json.loads(meta.read_text(encoding="utf-8")).get("ticker") or "").upper() == ticker.upper()
            except (OSError, ValueError):
                own = False
        try:
            body = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            counts["unchecked"] += 1
            continue
        if not own and not names(body):
            continue
        counts["window"] += 1
        if path.stem in blob:
            counts["pointed"] += 1
            continue
        items.append(UnreadItem(kind="raw", entered=entered, published=None, label=path.name,
                                pointer=f"library/raw/{path.name}"))
    return items, counts


def unread_primary(record: Mapping[str, Any], previous_at: datetime | None, *,
                   leads: Mapping[str, Mapping[str, Any]] | None = None,
                   raw_dir: Path = RAW_DIR) -> dict[str, Any]:
    """一筆剛寫好的敘事 → `{first, start, end, items, more, routine_more, counts}`。第一版（沒有上一版）不列，`first=True`。"""
    end = _when(record.get("created_at"))
    if previous_at is None or end is None:
        return {"first": True, "items": [], "more": 0, "counts": {}}
    from engine_b import event_watch as ew
    from engine_b.announcement_category import ROUTINE, lead_category
    from engine_b.entities import lead_entities
    from engine_b.leads import load as load_leads
    from identity.registry import get_registry
    from query.bottleneck import quote_names_company, shared_name_forms
    from sourcing.private_docs import _numeric_code, code_pattern

    start = previous_at if previous_at.tzinfo else previous_at.replace(tzinfo=timezone.utc)
    blob = json.dumps(record, ensure_ascii=False)
    company_id, ticker = str(record.get("company_id") or ""), str(record.get("ticker") or "")
    pool = load_leads()["leads"] if leads is None else leads
    lead_items, lead_counts = unread_leads(
        company_id, start, end, blob, pool, ownership_forms=ew.load_config()["ownership_forms_excluded"],
        entities_of=lead_entities, category_of=lead_category, routine=ROUTINE)
    registry = get_registry()
    company = registry.company(company_id) if company_id else None
    raw_items: list[UnreadItem] = []
    raw_counts = {"window": 0, "pointed": 0, "unchecked": 0}
    if company is not None:
        shared = shared_name_forms(registry)
        code = _numeric_code(company)
        pattern = code_pattern(code) if code else None

        def names(text: str) -> bool:
            return bool(quote_names_company(text, company, shared=shared) or (pattern and pattern.search(text)))

        raw_items, raw_counts = unread_raw(ticker, start, end, blob, raw_dir=raw_dir, names=names)
    ordered = sorted(lead_items + raw_items,
                     key=lambda item: (item.routine, -(_ordinal(item.published) or item.entered.toordinal())))
    shown = ordered[:LIMIT]
    rest = ordered[LIMIT:]
    return {"first": False, "start": start, "end": end, "items": shown, "more": len(rest),
            "routine_more": sum(1 for item in rest if item.routine),
            "counts": {"leads": lead_counts, "raw": raw_counts}}


def _ordinal(day: str | None) -> int | None:
    try:
        return date.fromisoformat(str(day)[:10]).toordinal() if day else None
    except ValueError:
        return None


def receipt_lines(result: Mapping[str, Any]) -> list[str]:
    """寫入收據的幾行。第一版照印一行（說明沒比，不是比了沒有）。"""
    if result.get("first"):
        return ["  一手（上一版之後進池）：這是第一版，沒有上一版可比——不列"]
    counts = result.get("counts") or {}
    leads, raw = counts.get("leads") or {}, counts.get("raw") or {}
    items = list(result.get("items") or ())
    total = len(items) + int(result.get("more") or 0)
    since = result["start"].astimezone(timezone.utc).date().isoformat()
    head = (f"  一手：上一版（{since}）之後進池、這一版沒指到的 {total} 則"
            f"（窗內 lead {leads.get('window', 0)}、指到 {leads.get('pointed', 0)}；"
            f"自家庫點名它的 {raw.get('window', 0)}、指到 {raw.get('pointed', 0)}"
            + (f"；非文字檔沒核 {raw['unchecked']}" if raw.get("unchecked") else "") + "）")
    if not total:
        return [head]
    lines = [head + "——讀過且無關就略過；只印、不擋（failure log #32）"]
    for item in items:
        when = item.entered.date().isoformat()
        if item.kind == "lead":
            lines.append(f"    · {item.published or '?'} 發布、{when} 進池｜{item.label}"
                         + ("（例行）" if item.routine else "") + f"｜{item.pointer}")
        else:
            lines.append(f"    · {when} 進庫｜{item.pointer}（點名這家公司）")
    if result.get("more"):
        lines.append(f"    另有 {result['more']} 則沒列" + (f"（其中例行重訊 {result['routine_more']}）"
                                                         if result.get("routine_more") else ""))
    return lines


__all__ = ["LIMIT", "UnreadItem", "lead_pointed", "previous_written_at", "receipt_lines", "unread_leads", "unread_primary",
           "unread_raw"]
