"""名冊候選分層與批次登記 A（2026-10-08，ROADMAP 同名列；plan 2026-10-08-001 D7）。

①人打字串先剝交易所前綴、去後綴唯一對應、比名冊名字——10-08 的 32 個裡 11 個其實已登記（failure log #45）；
②名冊批次比照主題組：系統起草、凍結 spec＋digest 進 pq2、go 之後 complete 才寫名冊（整批重新驗證）；
③寫入同一個動作重算 lead 身分與停放等待；④心跳那一行的分格與「名冊變動後未重算的 lead」。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_b import leads, registry_batch as rb, todo
from engine_b.entities import manual_name_tickers, resolve_manual_name
from identity.registry import get_registry


# --- ① 人打字串 -----------------------------------------------------------------

@pytest.mark.parametrize("raw, tickers", [
    ("Fabrinet (NYSE: FN)", ("FN",)),
    ("ASE Technology 日月光 (TWSE: 3711 / NYSE: ASX)", ("3711.TW", "ASX")),
    ("LuxNet 華星光通 (TPEx: 4979)", ("4979.TWO",)),
    ("Advantest (TSE: 6857)", ("6857.T",)),
    ("TFC Communication 天孚通信 (SZSE: 300394)", ("300394.SZ",)),
    ("FOCI 上詮 (3363.TW)", ("3363.TW",)),
    ("AIXTRON SE（德國 MOCVD 設備商，AIXA.DE；雷射磊晶上游）", ("AIXA.DE",)),
    ("Alcoa Corporation (AA)", ("AA",)),
    ("ASMPT", ()),                                         # 沒寫代號 → 不猜市場
    ("ESMT (Elite Semiconductor Memory Technology, TWSE 3006)", ("3006.TW",)),
])
def test_manual_strings_yield_only_the_tickers_they_write(raw: str, tickers: tuple[str, ...]) -> None:
    assert manual_name_tickers(raw) == tickers


def test_registered_companies_written_differently_resolve_to_the_registry() -> None:
    registry = get_registry()
    assert resolve_manual_name("Fabrinet (NYSE: FN)", registry)[0] == "co:fabrinet"
    assert resolve_manual_name("FOCI 上詮 (3363.TW)", registry)[0] == "co:foci"          # 後綴寫錯也對得到 .TWO
    assert resolve_manual_name("某光纖陣列廠 (TWSE: 3363)", registry)[0] == "co:foci"     # 只有代號、沒有名字可對
    assert resolve_manual_name("LuxNet 華星光通 (TPEx: 4979)", registry)[0] == "co:luxnet"
    # 寫出的代號比名字具體：名字「Samsung」也對得到三星電子，代號只對得到三星電機
    assert resolve_manual_name("Samsung Electro-Mechanics (009150.KS)", registry)[0] == "co:samsung_electro_mechanics"
    assert resolve_manual_name("ASMPT", registry) == (None, ())


def test_onboard_candidates_no_longer_counts_registered_manual_strings() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="x:a", url="https://x.com/a/1", title="FAU suppliers")
    leads.triage(store, lead_id, go=True, tier=3, reason="r")
    leads.annotate_refs(store, lead_id, refs={"onboard_candidate_names": ["FOCI 上詮 (3363.TW)", "ASMPT"]})
    names = [r["ticker"] for r in leads.onboard_candidates(store)]
    assert names == ["ASMPT"]
    full = {r["ticker"]: r for r in leads.onboard_candidates(store, include_resolved=True)}
    assert full["FOCI 上詮 (3363.TW)"]["resolved_to"] == "co:foci"
    assert full["ASMPT"]["suggested_tickers"] == []                  # 代號寫法待人工


# --- 分層、標記、起草 -------------------------------------------------------------

def _info(ticker: str) -> dict:
    return {"AIXA.DE": {"longName": "AIXTRON SE", "currency": "EUR", "exchange": "GER", "quoteType": "EQUITY",
                        "marketCap": 1_500_000_000, "numberOfAnalystOpinions": 6}}.get(ticker, {})


def test_tier_mark_and_draft_build_an_entry_that_the_registry_loader_accepts(monkeypatch) -> None:
    monkeypatch.setattr("alpha.providers.edge.adhoc_edge_states",
                        lambda tickers, fetch_info=None, **_k: {t: (fetch_info(t), {"state": "edge", "reasons": [],
                                                                               "missing": [],
                                                                               "market_cap_usd": 1.6e9,
                                                                               "analyst_count": 6})[1]
                                                               for t in tickers})
    data = rb.tier(["AIXA.DE"], fetch_info=_info, tiers={"as_of": None, "rows": {}})
    assert data["rows"]["AIXA.DE"]["edge_state"] == "edge" and data["rows"]["AIXA.DE"]["name"] == "AIXTRON SE"
    with pytest.raises(rb.RegistryBatchError, match="理由"):
        rb.mark_supply(data, ["AIXA.DE"], note="")
    with pytest.raises(rb.RegistryBatchError, match="還沒分層"):
        rb.mark_supply(data, ["XXXX"], note="n")
    rb.mark_supply(data, ["AIXA.DE"], note="lead_x：MOCVD 設備供給 InP 磊晶廠")
    assert rb.tier_summary([{"suggested_tickers": ["AIXA.DE"]}, {"suggested_tickers": []}], data) == {
        "edge_supply": 1, "edge_other": 0, "not_edge": 0, "unmeasurable": 0, "untiered": 1}
    # 重判邊緣不洗掉人的標記
    data = rb.tier(["AIXA.DE"], fetch_info=_info, tiers=data)
    assert data["rows"]["AIXA.DE"]["supply_side"]["value"] is True

    entry = rb.draft_entry("AIXA.DE", data["rows"]["AIXA.DE"], cashtag="AIXA", why="InP 磊晶上游")
    assert entry["company_id"] == "co:aixtron" and entry["name_aliases"] == [] and "aliases" not in entry   # AIXA＝代號去後綴，不另列別名
    assert entry["market_currency"] == "EUR" and "yfinance longName" in entry["_display_name_source"]
    assert rb.validate_batch([entry]) == []


def test_validation_catches_collisions_and_bad_currency() -> None:
    entry = {"company_id": "co:new_co", "research_ticker": "AXTI", "market_currency": "USD",
             "display_name": "New Co", "_display_name_source": "test", "_note": "n", "name_aliases": []}
    assert any("拒收" in p for p in rb.validate_batch([entry]))                  # AXTI 已是 co:axt 的代號
    bad = dict(entry, research_ticker="NEWCO", market_currency="XYZp")
    assert any("幣別" in p or "拒收" in p for p in rb.validate_batch([bad]))
    assert any("_display_name_source" in p for p in rb.validate_batch([dict(entry, _display_name_source="")]))


# --- ② 批次 pq2 與 ③ 寫入後重算 --------------------------------------------------------

def _registry_copy(tmp_path: Path) -> Path:
    target = tmp_path / "company_identity.json"
    target.write_bytes((Path(rb.REGISTRY_PATH)).read_bytes())
    return target


def test_registry_batch_is_written_only_by_complete_after_the_frozen_spec_matches(tmp_path, monkeypatch) -> None:
    registry_path = _registry_copy(tmp_path)
    entry = {"company_id": "co:test_newco", "research_ticker": "TNCO", "market_currency": "USD",
             "display_name": "Test Newco Inc.", "_display_name_source": "test", "_note": "n", "name_aliases": []}
    pool = todo.empty_pool()
    with pytest.raises(todo.TodoError, match="reason"):
        todo.propose_registry_batch(pool, {"entries": [entry]}, registry_path=registry_path)
    item = todo.propose_registry_batch(pool, {"reason": "測試", "entries": [entry]}, registry_path=registry_path)
    assert item["frozen_spec"]["kind"] == "registry_batch"
    assert "co:test_newco" not in registry_path.read_text(encoding="utf-8")     # 鑄號不寫名冊

    # 鑄號之後 spec 被改 → 拒收、一行都不寫
    item["frozen_spec"]["spec"]["entries"][0]["research_ticker"] = "EVIL"
    with pytest.raises(todo.TodoError, match="digest"):
        todo.complete_registry_batch(pool, item["n"], registry_path=registry_path)
    item["frozen_spec"]["spec"]["entries"][0]["research_ticker"] = "TNCO"

    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="x:a", url="https://x.com/a/2", title="$TNCO ships lasers")
    leads_path = tmp_path / "leads.json"
    leads.save(store, leads_path)
    from engine_b.registry_batch import write_entries as real_write
    from identity import registry as registry_module

    def _write(entries, registry_path=None):
        out = real_write(entries, registry_path=registry_path)
        monkeypatch.setattr(registry_module, "_DEFAULT_REGISTRY_PATH", out)   # 重算讀新名冊
        return out

    monkeypatch.setattr(rb, "write_entries", _write)
    result = todo.complete_registry_batch(pool, item["n"], registry_path=registry_path, leads_path=leads_path,
                                          watch_path=tmp_path / "watches.json")
    registry_module.get_registry.cache_clear()
    assert result["registered"] == ["co:test_newco"] and result["receipt"].startswith("authority:registry_batch;ref:")
    assert "co:test_newco" in json.loads(registry_path.read_text(encoding="utf-8"))["companies"][-1]["company_id"]
    assert "co:test_newco" in leads.load(leads_path)["leads"][lead_id]["entities"]["company_ids"]   # 同一個動作重算
    with pytest.raises(todo.TodoError, match="不存在或已處理"):
        todo.complete_registry_batch(pool, item["n"], registry_path=registry_path)


def test_stale_lead_entities_counts_leads_computed_with_an_older_registry() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="x:a", url="https://x.com/a/3", title="$AXTI news")
    assert rb.stale_lead_entities(store) == 0
    store["leads"][lead_id]["entities"] = {"tickers": ["AXTI"], "company_ids": []}   # 舊名冊算的
    assert rb.stale_lead_entities(store) == 1
