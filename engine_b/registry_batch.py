"""名冊批次登記（2026-10-08，ROADMAP「名冊候選分層與批次登記」A；使用者選 A 半自動）。

事發：Phase 7 的名冊條目全是研究 session 手寫、隨包 staged（7 次、約 40 筆）；「被點名但未登記」累積上百個，
其中人打字串 32 個裡 11 個其實已登記（failure log #45）、Credo 晚登記 5 天讓 22 則 lead 沒對上（#13）。

**A 的邊界：系統起草、人核准。** 寫進 `config/company_identity.json`（INV-1 的 identity authority；代號別名會進
`company_id_for_ticker`＝資本歸屬路徑）只有一條路：`python -m engine_b.todo complete-registry-batch <n>`——使用者對那個
exact 編號 go 之後，讀凍結 spec、比對 digest、**整批**重新驗證（撞代號、撞別名、幣別不合法 → 一筆都不寫）。

1. **分層**（`tier`；互動、要連 yfinance）：被點名未登記的每一檔用系統口徑判邊緣（`alpha.providers.edge.adhoc_edge_states`
   ——與候選板同一個判定、同一份門檻），結果存在 `library/private/registry/onboard_tiers.json`（判定日寫在裡面）。
2. **供給側標記**（`mark-supply`）：「lead 把它放在供給側」是讀 lead 的語意判斷——研究 session 標、使用者 go 批次時確認
   （L15：可以解析、可以提議，不可以授權）。
3. **起草**（`draft`）：邊緣且標了供給側的，起草名冊條目（id、代號、幣別、display_name 附來源、cashtag 別名先驗不撞；
   **名字別名留空**等人補——名字比對會進證據等級，猜錯比漏掉貴）。
4. **寫入後重算**（`after_registry_change`）：lead 身分 `backfill_entities(rescan=True)`＋停放等待 `sync_trace_watches`——
   名冊多一個名字，lead 就多對上一家、觸發條件就多點名一家。名冊有變、沒重算的 lead 數由心跳常駐（`stale_lead_entities`）。
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = _ROOT / "config" / "company_identity.json"
TIERS_PATH = _ROOT / "library" / "private" / "registry" / "onboard_tiers.json"

#: 起草的條目只收這幾個欄位（其餘欄位由人手寫，不由系統猜）。
DRAFT_FIELDS = ("company_id", "research_ticker", "market_currency", "aliases", "display_name",
                "_display_name_source", "_note", "name_aliases")
_LEGAL_SUFFIX = re.compile(
    r"[,.\s]+(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|se|ag|sa|nv|ab|asa|oyj|gmbh|kk|"
    r"holdings?|group|technologies|technology)\.?$", re.IGNORECASE)


class RegistryBatchError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 分層與標記（私有 state；不是 authority——它只決定起草誰，寫名冊仍要 go）
# ---------------------------------------------------------------------------

def load_tiers(path: Path | None = None) -> dict[str, Any]:
    p = path or TIERS_PATH
    if not p.exists():
        return {"as_of": None, "rows": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def save_tiers(data: Mapping[str, Any], path: Path | None = None) -> None:
    p = path or TIERS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def tier(tickers: Iterable[str], *, fetch_info: Callable[[str], Mapping[str, Any]] | None = None,
         tiers: dict[str, Any] | None = None, today: date | None = None) -> dict[str, Any]:
    """系統口徑判邊緣（`adhoc_edge_states`），連同 yfinance 的名字／幣別／交易所存進分層表。

    `fetch_info`：代號 → yfinance `info`（測試的縫；預設真的去抓）。抓不到的照實寫 `unmeasurable` 與原因（不補 0）。
    保留既有的 `supply_side` 標記（重判邊緣不洗掉人的標記）。"""
    from alpha.providers.edge import adhoc_edge_states

    data = tiers if tiers is not None else load_tiers()
    seen: dict[str, Mapping[str, Any]] = {}

    def _fetch(ticker: str) -> Mapping[str, Any]:
        if fetch_info is not None:
            info = fetch_info(ticker)
        else:
            import yfinance as yf

            info = yf.Ticker(ticker).info or {}
        seen[ticker] = info
        return info

    wanted = [str(t).strip().upper() for t in tickers if str(t).strip()]
    states = adhoc_edge_states(wanted, fetch_info=_fetch)
    stamp = (today or date.today()).isoformat()
    rows = data.setdefault("rows", {})
    for ticker in wanted:
        state = states.get(ticker) or {}
        info = seen.get(ticker) or {}
        prior = rows.get(ticker) or {}
        rows[ticker] = {
            "edge_state": state.get("state"),
            "edge_reasons": state.get("reasons"),
            "missing": state.get("missing"),
            "market_cap_usd": state.get("market_cap_usd"),
            "analyst_count": state.get("analyst_count"),
            "name": info.get("longName") or info.get("shortName"),
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
            "quote_type": info.get("quoteType"),
            "tiered_on": stamp,
            **({"supply_side": prior["supply_side"]} if "supply_side" in prior else {}),
        }
    data["as_of"] = stamp
    return data


def mark_supply(data: dict[str, Any], tickers: Iterable[str], *, note: str, supply_side: bool = True) -> list[str]:
    """研究 session 讀過 lead 後標「它在供給側」（或標不是）。沒分層過的代號拒收（先 tier 再標）。"""
    text = " ".join(str(note or "").split())
    if not text:
        raise RegistryBatchError("標記要附一句理由（哪則 lead、它供什麼給誰）")
    rows = data.setdefault("rows", {})
    marked = []
    for raw in tickers:
        ticker = str(raw).strip().upper()
        if ticker not in rows:
            raise RegistryBatchError(f"{ticker} 還沒分層——先跑 onboard-candidates --tier {ticker}")
        rows[ticker]["supply_side"] = {"value": bool(supply_side), "note": text, "at": _now()}
        marked.append(ticker)
    return marked


def tier_summary(candidates: Iterable[Mapping[str, Any]], data: Mapping[str, Any]) -> dict[str, int]:
    """心跳那一行的分格：邊緣供給側／邊緣未標或非供給側／非邊緣／量不到／還沒分層（人打字串沒有代號的算還沒分層）。"""
    rows = data.get("rows") or {}
    out = {"edge_supply": 0, "edge_other": 0, "not_edge": 0, "unmeasurable": 0, "untiered": 0}
    for cand in candidates:
        tickers = cand.get("suggested_tickers") or ()
        row = next((rows[t] for t in tickers if t in rows), None)
        if row is None:
            out["untiered"] += 1
        elif row.get("edge_state") == "edge":
            supply = (row.get("supply_side") or {}).get("value")
            out["edge_supply" if supply else "edge_other"] += 1
        elif row.get("edge_state") == "not_edge":
            out["not_edge"] += 1
        else:
            out["unmeasurable"] += 1
    return out


# ---------------------------------------------------------------------------
# 起草與驗證
# ---------------------------------------------------------------------------

def company_id_for_name(name: str) -> str:
    """`AIXTRON SE` → `co:aixtron`：去法律尾綴、小寫、非英數換底線。不是身分判定——只是起草的 id，人可改。"""
    core = str(name or "").strip()
    for _ in range(3):
        stripped = _LEGAL_SUFFIX.sub("", core).strip()
        if stripped == core:
            break
        core = stripped
    slug = re.sub(r"[^a-z0-9]+", "_", core.lower()).strip("_")
    if not slug:
        raise RegistryBatchError(f"名字推不出 id：{name!r}——請手寫 company_id")
    return f"co:{slug}"


def draft_entry(ticker: str, row: Mapping[str, Any], *, cashtag: str | None = None, why: str = "",
                lead_ids: Iterable[str] = (), today: date | None = None) -> dict[str, Any]:
    """一筆名冊條目的草稿（`DRAFT_FIELDS`）。名字別名留空（名字比對會進證據等級，猜錯比漏掉貴——等人補）。"""
    name = str(row.get("name") or "").strip()
    if not name:
        raise RegistryBatchError(f"{ticker} 沒有名字（yfinance longName 讀不到）——請手寫 display_name")
    stamp = (today or date.today()).isoformat()
    cap = row.get("market_cap_usd")
    cap_text = f"約 {cap / 1e8:.1f} 億美元" if isinstance(cap, (int, float)) else "市值讀不到"
    entry: dict[str, Any] = {
        "company_id": company_id_for_name(name),
        "research_ticker": ticker,
        "market_currency": row.get("currency"),
        "display_name": name,
        "_display_name_source": f"yfinance longName（{stamp}）；交易所 {row.get('exchange') or '讀不到'}",
        "_note": (f"名冊批次草稿（{stamp}）：{why or '被點名未登記'}；系統口徑 {row.get('edge_state')}"
                  f"（{cap_text}、分析師 {row.get('analyst_count') if row.get('analyst_count') is not None else '讀不到'} 家）"
                  + (f"；lead：{'、'.join(list(lead_ids)[:5])}" if lead_ids else "")),
        "name_aliases": [],
    }
    alias = str(cashtag or "").strip().upper()
    if alias and alias != ticker.upper() and alias != ticker.upper().split(".", 1)[0]:
        entry["aliases"] = [alias]
    return entry


def spec_digest(spec: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def validate_batch(entries: list[Mapping[str, Any]], *, registry_path: Path | None = None) -> list[str]:
    """整批對**當下的名冊**驗一次：把條目接在名冊後面、用名冊自己的載入器讀（撞 id／代號／別名、幣別不合法都由它 raise）。
    回問題清單（空＝通過）。不寫任何檔（暫存檔在 tempdir）。"""
    from identity.registry import IdentityRegistry

    problems: list[str] = []
    if not entries:
        return ["批次是空的"]
    for index, entry in enumerate(entries):
        label = f"entries[{index}]（{entry.get('company_id')}）"
        unknown = sorted(set(entry) - set(DRAFT_FIELDS) - {"execution_currency", "execution_venue", "benchmark_symbol"})
        if unknown:
            problems.append(f"{label} 有起草範圍外的欄位 {unknown}")
        if not str(entry.get("company_id") or "").startswith("co:"):
            problems.append(f"{label} company_id 必須是 co:*")
        if not str(entry.get("display_name") or "").strip():
            problems.append(f"{label} display_name 必填")
        if not str(entry.get("_display_name_source") or "").strip():
            problems.append(f"{label} _display_name_source 必填（名字從哪裡來）")
    if problems:
        return problems
    payload = json.loads((registry_path or REGISTRY_PATH).read_text(encoding="utf-8"))
    payload["companies"] = list(payload["companies"]) + [dict(e) for e in entries]
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "company_identity.json"
        probe.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        try:
            registry = IdentityRegistry.from_path(probe)
        except (ValueError, KeyError) as exc:
            return [f"名冊載入器拒收：{exc}"]
    for entry in entries:
        company = registry.company(str(entry["company_id"]))
        if entry.get("market_currency") and company is not None and company.market_currency is None:
            problems.append(f"{entry['company_id']} 的幣別 {entry['market_currency']!r} 不是 ISO、也沒登記成報價單位（fail closed）")
    return problems


def write_entries(entries: list[Mapping[str, Any]], *, registry_path: Path | None = None) -> Path:
    """把條目接在名冊檔尾（保留原檔的 indent=2／換行慣例）。呼叫端已驗過；這裡只做「往返不變」的格式守門。"""
    path = registry_path or REGISTRY_PATH
    raw = path.read_bytes().decode("utf-8")
    data = json.loads(raw)
    newline = "\r\n" if "\r\n" in raw else "\n"
    trail = raw[len(raw.rstrip("\r\n")):]

    def dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2).replace("\n", newline)

    if dump(data) + trail != raw:
        raise RegistryBatchError("名冊檔不是 indent=2 的往返格式——寫入會改到別的條目，停（請先人工對齊格式）")
    existing = {str(c.get("company_id")) for c in data["companies"]}
    clash = [str(e["company_id"]) for e in entries if str(e["company_id"]) in existing]
    if clash:
        raise RegistryBatchError(f"已在名冊：{clash}")
    data["companies"].extend(dict(e) for e in entries)
    path.write_bytes((dump(data) + trail).encode("utf-8"))
    return path


# ---------------------------------------------------------------------------
# 寫入後重算（③）與常駐計數
# ---------------------------------------------------------------------------

def after_registry_change(store: dict[str, Any], watch_data: dict[str, Any], *, registry: Any = None) -> dict[str, Any]:
    """名冊變動之後同一個動作要做的兩件事：lead 身分重算、停放等待重算。只動 pq1 狀態；呼叫端存檔。"""
    from engine_b import leads
    from engine_b.entities import backfill_entities

    changed = backfill_entities(store, rescan=True)
    sync = leads.sync_trace_watches(store, watch_data, registry=registry)
    return {"lead_entities_changed": changed, "trace_watch_sync": sync["counts"]}


def stale_lead_entities(store: Mapping[str, Any]) -> int:
    """存著的 lead 實體跟用**當下的名冊**重算的不一樣的則數——名冊變了卻沒重算（應恆為 0）。零 token、不寫檔。"""
    from engine_b.entities import extract_entities

    count = 0
    for lead in (store.get("leads") or {}).values():
        stored = lead.get("entities")
        if not isinstance(stored, dict):
            continue
        fresh = extract_entities(title=lead.get("title"), raw_text=lead.get("raw_text"), source=lead.get("source"))
        if stored != fresh:
            count += 1
    return count


__all__ = [
    "DRAFT_FIELDS", "REGISTRY_PATH", "RegistryBatchError", "TIERS_PATH", "after_registry_change",
    "company_id_for_name", "draft_entry", "load_tiers", "mark_supply", "save_tiers", "spec_digest",
    "stale_lead_entities", "tier", "tier_summary", "validate_batch", "write_entries",
]
