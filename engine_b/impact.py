"""一則 lead 碰到哪幾份敘事（哪一格）、哪幾份讀圖（結構角度）、哪幾條在盯的條件——確定性、零 LLM（雷達精進 C1，2026-10-21）。

使用者 2026-10-20：「拉進來的東西我也想要問他會怎麼影響到我們的敘事」。在這之前沒有任何 owner 回答「這則碰到誰」：
NVHBM 那則（X 帳號 10-18）停放時寫「圖上沒有讀圖可接」，其實 HBM 讀圖缺的兩格正是它碰到的（failure log #92 前後那一輪）。

**對照，不是判定。** 這裡只算「名字對到了哪裡」：
- 實體分兩欄、不混用（L12）：`given`＝lead 結構化欄位給的（`entities.company_ids`、雷達的 `radar_company_ids`），
  `scanned`＝用名冊名字在原文裡掃到的（名字比對的唯一 owner：`query.bottleneck.quote_names_company`）。
- 敘事三種連結：`own`（敘事的公司就是它）、`rides`（敘事騎的讀圖在結構角度上有它）、`slot`（哪一格原文具名了它）。
- 讀圖只認結構角度（supply_side／demand_side／counter_path／next_layer）；讀圖反證的實體改走 watch，不重複算。
- 在盯條件：語意 watch（active／fired）實體有交集；歸屬到哪份敘事一律問 `narrative_watches.attributed_watches`（SSOT）。
- **樞紐實體只計數不展開**：一個實體單獨就碰到 ≥ `HUB_SHARE` 的現行敘事、或 ≥ `HUB_WATCHES` 條在盯 watch，
  它帶來的連結只印數字——不做會恆亮（L14-4：原型 v1 回放 NVHBM 一則碰到 42 份敘事、41 條 watch）。
- 節點名只有英文：原文有中日韓字、卻一個節點名都沒對到，標 `language_gap`（計數現形，不靜默）。

不寫進 lead refs：對照會隨敘事與讀圖變動，可重建（L10）。互動用 `python -m engine_b.impact --lead <id>`。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
STRUCTURE_TABLE = ROOT / "library" / "private" / "app" / "state" / "structure_table.json"

STRUCT_ANGLES = frozenset({"supply_side", "demand_side", "counter_path", "next_layer"})
HUB_SHARE = 0.10
HUB_WATCHES = 15
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")


@dataclass
class Context:
    """一次載入、多則共用。`briefs` 是現行敘事（`InvestorBrief`；未撤回、v2）；`readings` 是 node → 現行讀圖（層優先）。"""
    briefs: list[Any]
    readings: dict[str, Any]
    watches: list[Mapping[str, Any]]
    companies: dict[str, Any]
    shared: frozenset[str]
    node_names: dict[str, str]
    lifecycle: Mapping[str, Any] | None = None
    brief_ids: dict[str, list[str]] = field(default_factory=dict)
    node_forms: dict[str, frozenset[str]] = field(default_factory=dict)
    reading_entities: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    watch_owner: dict[str, list[str]] = field(default_factory=dict)
    hubs: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        self.node_forms = _node_forms(self.node_names)
        self.reading_entities = {node: _reading_entities(r) for node, r in self.readings.items()}
        self.watch_owner = _watch_owner(self)
        self.hubs = _hubs(self)


def _node_forms(node_names: Mapping[str, str]) -> dict[str, frozenset[str]]:
    """節點名的寫法：全名（≥6 字）＋括號裡的縮寫（HBM、CoWoS、LPT、CDU…；≤2 字或全小寫的不收——誤報）。"""
    out: dict[str, set[str]] = defaultdict(set)
    for nid, name in node_names.items():
        if not name or str(nid).startswith("co:"):
            continue
        base = re.sub(r"[（(].*?[)）]", "", name).strip()
        if len(base) >= 6:
            out[nid].add(base)
        for abbr in re.findall(r"[（(]([^)）]{2,20})[)）]", name):
            abbr = abbr.strip()
            if len(abbr) >= 3 and not abbr.islower() and " " not in abbr:
                out[nid].add(abbr)
    return {k: frozenset(v) for k, v in out.items()}


def _reading_entities(reading: Any) -> dict[str, set[str]]:
    """讀圖結構角度上出現的 co:*（→ 哪些角度）。反證的實體不算在這裡（走 watch）。"""
    out: dict[str, set[str]] = defaultdict(set)
    for angle, edges in (getattr(reading, "angles", None) or {}).items():
        if angle not in STRUCT_ANGLES:
            continue
        for edge in edges or ():
            for end in (edge[0], edge[2]) if len(edge) >= 3 else ():
                if str(end).startswith("co:"):
                    out[str(end)].add(angle)
    return out


def _watch_owner(ctx: Context) -> dict[str, list[str]]:
    """watch_id → 歸屬的敘事 ticker（問 `narrative_watches.attributed_watches`，不自己解析 source_ref）。"""
    from engine_b.narrative_watches import attributed_watches

    owner: dict[str, list[str]] = defaultdict(list)
    for brief in ctx.briefs:
        ids = ctx.brief_ids.get(brief.ticker) or [brief.brief_id]
        for watch in attributed_watches(brief.company_id, brief.ticker, watches=ctx.watches, lifecycle=ctx.lifecycle,
                                        brief_ids=ids, current_brief=brief):
            owner[str(watch.get("watch_id"))].append(brief.ticker)
    return owner


def _hubs(ctx: Context) -> frozenset[str]:
    n_brief = max(len(ctx.briefs), 1)
    hubs = set()
    for cid in ctx.companies:
        narratives, watches, _ = _touch({cid}, [], ctx)
        if len(narratives) >= HUB_SHARE * n_brief or len(watches) >= HUB_WATCHES:
            hubs.add(cid)
    return frozenset(hubs)


def lead_text(lead: Mapping[str, Any]) -> str:
    refs = lead.get("refs") or {}
    return " ".join(str(x or "") for x in (lead.get("title"), lead.get("raw_text"), refs.get("radar_fact")))


def lead_entities(lead: Mapping[str, Any], ctx: Context) -> tuple[list[str], list[str]]:
    """(given, scanned)：結構化欄位給的；名冊名字在原文裡掃到、且不在 given 的。兩欄不混（L12）。"""
    from query.bottleneck import quote_names_company

    given = [str(c) for c in (lead.get("entities") or {}).get("company_ids") or ()]
    given += [str(c) for c in (lead.get("refs") or {}).get("radar_company_ids") or () if str(c) not in given]
    text = lead_text(lead)
    scanned = [cid for cid, company in ctx.companies.items()
               if cid not in given and quote_names_company(text, company, shared=ctx.shared)]
    return given, scanned


def _form_pattern(form: str) -> re.Pattern[str]:
    """全大寫縮寫（HBM、CPO、MLCC）左邊可接**恰好兩個**大寫字母的廠商前綴、右邊可接數字或複數 s——NVHBM、HBM4E、
    PICs 都是同一層（10-21 漏抓回放：韓媒寫「NVHBM base die」對不到 HBM 讀圖）。前綴放寬到任意大寫會誤報：全庫回放
    「EPIC」對到 PIC、「CHANNELS」對到 ELS——所以只放到資料支持的那一格（L17）。其餘寫法兩側都要字界。"""
    if form.isupper() and form.isalnum():
        return re.compile(r"(?<![A-Za-z0-9_])(?:[A-Z]{2})?" + re.escape(form) + r"s?(?![A-Za-z_])")
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(form) + r"(?![A-Za-z0-9_])", 0 if " " not in form else re.I)


def node_mentions(text: str, ctx: Context) -> list[str]:
    hits = []
    for nid, forms in ctx.node_forms.items():
        for form in forms:
            pattern = _form_pattern(form)
            if pattern.search(text):
                hits.append(nid)
                break
    return sorted(set(hits))


def _touch(entities: set[str], nodes_named: Sequence[str], ctx: Context):
    """(narratives, watches, readings)。narratives：ticker → 連結清單；readings：node → 理由；watches：watch dict 清單。"""
    from query.bottleneck import quote_names_company

    readings: dict[str, list[str]] = {}
    for node, ent_map in ctx.reading_entities.items():
        why = sorted({f"{c}@{a}" for c in entities & set(ent_map) for a in ent_map[c]})
        if node in nodes_named:
            why.append("name")
        if why:
            readings[node] = why
    narratives: dict[str, list[str]] = {}
    for brief in ctx.briefs:
        links = []
        if brief.company_id in entities:
            links.append("own")
        rides = [r.node for r in brief.rides or () if r.node in readings]
        if rides:
            links.append("rides:" + ",".join(rides))
        for slot in brief.slots or ():
            named = [c for c in sorted(entities) if c != brief.company_id and c in ctx.companies
                     and quote_names_company(slot.text, ctx.companies[c], shared=ctx.shared)]
            if named:
                links.append(f"slot:{slot.key}<{','.join(named)}>")
        if links:
            narratives[brief.ticker] = links
    # 排列（不是排名）：公司本身 → 騎的讀圖碰到 → 只有某一格具名；同級照 ticker
    rank = {t: (0 if "own" in v else 1 if any(x.startswith("rides:") for x in v) else 2) for t, v in narratives.items()}
    narratives = dict(sorted(narratives.items(), key=lambda kv: (rank[kv[0]], kv[0])))
    watches = [w for w in ctx.watches if entities & set(w.get("entities") or ())]
    return narratives, watches, readings


def _language_gap(text: str, nodes_named: Sequence[str]) -> bool:
    """原文主要是中日韓字（拉丁字詞少於 5 個）、又一個節點名都沒對到——節點名只有英文，這類比不到要現形。
    雷達的事實欄一律是繁中、標題多是英文，所以只看有沒有中日韓字會恆亮（10-21 第一次實跑 Nscale 那則就誤報）。"""
    return bool(_CJK.search(text)) and not nodes_named and len(re.findall(r"[A-Za-z]{3,}", text)) < 5


def impact(lead: Mapping[str, Any], ctx: Context) -> dict[str, Any]:
    given, scanned = lead_entities(lead, ctx)
    entities = set(given) | set(scanned)
    specific = entities - ctx.hubs
    hub_hit = entities & ctx.hubs
    text = lead_text(lead)
    nodes_named = node_mentions(text, ctx)
    narratives, watches, readings = _touch(specific, nodes_named, ctx)
    h_narr, h_watch, h_read = _touch(hub_hit, [], ctx) if hub_hit else ({}, [], {})
    if not entities and not nodes_named:
        absence = "no_entities"
    elif not (narratives or watches or readings):
        absence = "hub_only" if (h_narr or h_watch or h_read) else "untouched"
    else:
        absence = None
    return {
        "lead_id": lead.get("lead_id"), "title": str(lead.get("title") or "")[:160], "source": lead.get("source"),
        "entities_given": given, "entities_scanned": scanned, "hub_entities": sorted(hub_hit),
        "nodes_named": nodes_named, "language_gap": _language_gap(text, nodes_named),
        "narratives": narratives, "readings": readings,
        "watches": [{"watch_id": w.get("watch_id"), "role": "加碼條件" if w.get("condition_role") == "confirm" else "反證",
                     "source_ref": w.get("source_ref"), "owners": ctx.watch_owner.get(str(w.get("watch_id")), []),
                     "condition": str(w.get("condition") or "")} for w in watches],
        "hub_only_counts": {"narratives": len(set(h_narr) - set(narratives)),
                            "watches": len({w.get("watch_id") for w in h_watch} - {w.get("watch_id") for w in watches}),
                            "readings": len(set(h_read) - set(readings))},
        "absence_kind": absence,
    }


#: C4（2026-10-21 上線）：這天起停放的 lead，停放理由要逐條處置對照列出的在盯條件——寫出 watch id 與「不相關／等一手／已處理」。
#: 之前停放的不回溯（那時沒有對照可讀，回溯只會一次湧出幾百筆、恆亮）。
DISPOSITION_SINCE = "2026-10-21"
_WATCH_SHORT = re.compile(r"^(ew_\d+)")


def _parked_at(lead: Mapping[str, Any]) -> str | None:
    hits = [str(t.get("at") or "") for t in lead.get("transitions") or () if t.get("to") == "parked"]
    return hits[-1] if hits else None


def _instant(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def undisposed(store: Mapping[str, Mapping[str, Any]], ctx: Context | None = None, *,
               since: str = DISPOSITION_SINCE) -> list[dict[str, str]]:
    """`since` 起停放的 lead × 它對照出的在盯條件（樞紐只計數的不算）裡，停放理由沒寫到那個 watch id 的組合。
    寫 `ew_0762` 或完整 id 都算寫到（LLM 與人都常截掉日期尾綴——#92 同一件事）。常駐計數器：處置完就歸零、不恆亮。
    **停放之後才登記的 watch 不算**（2026-10-23 L17 當下修：一份新讀圖登三條條件，就讓每則碰到那家公司的舊停放各多三筆，
    計數器跟著我們多寫讀圖單調上升——量到的是研究量；停放理由寫不到停放時還不存在的條件）。再次停放以最後一次為準，那時就要處置。
    沒有 `since` 起停放的 lead 就不載入對照（`ctx` 給 None 時才自己載；心跳每天都跑，空的那天不必付載入成本）。"""
    out: list[dict[str, str]] = []
    recent = [(lid, lead) for lid, lead in store.items()
              if lead.get("status") == "parked" and (_parked_at(lead) or "")[:10] >= since]
    if not recent:
        return out
    ctx = ctx if ctx is not None else load_context()
    created = {str(w.get("watch_id")): _instant(w.get("created_at")) for w in ctx.watches}
    for lead_id, lead in recent:
        reason = str((lead.get("refs") or {}).get("parked_reason") or "")
        parked = _instant(_parked_at(lead))
        for watch in impact({**lead, "lead_id": lead_id}, ctx)["watches"]:
            wid = str(watch["watch_id"])
            born = created.get(wid)
            if parked and born and born > parked:                                    # 缺時戳的照算（不靜默放過）
                continue
            short = _WATCH_SHORT.match(wid)
            forms = {wid} | ({short.group(1)} if short else set())
            if any(re.search(re.escape(f) + r"(?!\d)", reason) for f in forms):     # ew_12 不算寫到 ew_1
                continue
            out.append({"lead_id": str(lead_id), "watch_id": wid})
    return out


def load_context() -> Context:
    """讀名冊、現行敘事與讀圖、在盯的語意 watch、structure_table artifact 的節點名（讀不到就沒有節點名比對，照常跑）。"""
    from alpha.providers.briefs import read_brief_records
    from engine_b import event_watch as ew
    from engine_b.disproof import current_briefs, current_readings, load_lifecycle
    from identity.registry import get_registry
    from query.bottleneck import shared_name_forms

    registry = get_registry()
    briefs = current_briefs()
    brief_ids = {}
    for brief in briefs:
        records, _errors = read_brief_records(brief.ticker)
        brief_ids[brief.ticker] = [r.brief_id for r in records]
    readings: dict[str, Any] = {}
    for (node, unit), reading in sorted(current_readings().items(), key=lambda kv: kv[0][1] != "layer"):
        readings.setdefault(node, reading)
    watches = [w for w in ew.load_watches().get("watches") or ()
               if w.get("kind") == ew.SEMANTIC_KIND and w.get("status") in ("active", "fired")]
    try:
        layers = json.loads(STRUCTURE_TABLE.read_text(encoding="utf-8")).get("layers") or ()
        node_names = {str(l["id"]): str(l.get("name") or "") for l in layers}
    except (OSError, ValueError):
        node_names = {}
    return Context(briefs=briefs, readings=readings, watches=watches,
                   companies={c.company_id: c for c in registry.companies}, shared=shared_name_forms(registry),
                   node_names=node_names, lifecycle=load_lifecycle(), brief_ids=brief_ids)


def render(row: Mapping[str, Any], *, limit: int = 3) -> list[str]:
    """人讀的幾行（互動 CLI 與心跳落檔共用）。"""
    lines = [f"{row.get('lead_id')}｜{row.get('title')}"]
    if row.get("absence_kind") == "no_entities":
        return lines + ["  ↳ 沒有點名任何名冊公司或節點" + ("（原文是中日韓字，節點名只有英文，比不到）" if row.get("language_gap") else "")]
    narr = row.get("narratives") or {}
    if narr:
        shown = [f"{t}（{'、'.join(v)}）" for t, v in list(narr.items())[:limit]]
        more = len(narr) - len(shown)
        lines.append("  ↳ 敘事：" + "；".join(shown) + (f"；另 {more} 份" if more > 0 else ""))
    if row.get("readings"):
        lines.append("  ↳ 讀圖：" + "、".join(list(row["readings"])[:limit])
                     + (f"；另 {len(row['readings']) - limit} 份" if len(row["readings"]) > limit else ""))
    ws = row.get("watches") or []
    if ws:
        lines.append(f"  ↳ 在盯：反證 {sum(w['role'] == '反證' for w in ws)}／加碼 {sum(w['role'] == '加碼條件' for w in ws)}："
                     + "、".join(w["watch_id"] for w in ws[:limit]) + (f"；另 {len(ws) - limit} 條" if len(ws) > limit else ""))
    hub = row.get("hub_only_counts") or {}
    if row.get("hub_entities") and any(hub.values()):
        lines.append(f"  ↳ 另經 {'、'.join(row['hub_entities'])} 碰到：敘事 {hub.get('narratives', 0)}、讀圖 {hub.get('readings', 0)}、"
                     f"在盯 {hub.get('watches', 0)}（樞紐實體只計數）")
    if row.get("absence_kind") in ("untouched", "hub_only") and len(lines) == 1:
        lines.append("  ↳ 沒有碰到任何現行敘事、讀圖或在盯條件")
    if row.get("language_gap"):
        lines.append("  ↳ ⚠ 原文是中日韓字、沒對到任何節點名（節點名只有英文）")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m engine_b.impact", description="一則 lead 碰到哪些敘事、讀圖、在盯條件（唯讀）")
    parser.add_argument("--lead", action="append", required=True, help="lead_id（可重複）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    from engine_b.leads import load as load_leads

    store = load_leads()["leads"]
    ctx = load_context()
    rows = []
    for lead_id in args.lead:
        lead = store.get(lead_id)
        if lead is None:
            print(f"✗ 找不到 {lead_id}", file=sys.stderr)
            return 2
        rows.append(impact({**lead, "lead_id": lead_id}, ctx))
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for row in rows:
            print("\n".join(render(row)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Context", "DISPOSITION_SINCE", "HUB_SHARE", "HUB_WATCHES", "STRUCT_ANGLES", "impact", "lead_entities", "lead_text",
           "load_context", "main", "node_mentions", "render", "undisposed"]
