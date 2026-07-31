"""Lead 具名標的擷取與確定性關聯的迴歸測試。

在此之前 lead 之間唯一的鍵是正規化 URL hash——同一篇文章重抓會去重，但「不同 URL、
同一個標的」沒有任何連結。parked lead 與新進 lead 的關聯完全靠 agent 每個 session
重讀 `trace-backlog` 自由文字並以語意注意到，漏掉時是靜默的。

這裡的擷取刻意只做確定性比對（cashtag 逐字出現、結構化 source ticker、registry 反查），
不做語意推論也不呼叫 LLM，因此可預測、可測試、規模成長時不退化。
"""
from __future__ import annotations

from engine_b.entities import (
    backfill_entities,
    extract_cashtags,
    extract_entities,
    extract_source_ticker,
    lead_entities,
    related_leads,
)


def test_cashtags_are_extracted_and_normalised() -> None:
    assert extract_cashtags("看好 $aaoi 與 $CCXI") == ("AAOI", "CCXI")


def test_dollar_amounts_are_not_mistaken_for_cashtags() -> None:
    """US$71.3M、$22,288,500 這類金額不得被當成標的。"""
    assert extract_cashtags("prepayment of US$22,288,500 and US$71.3M") == ()
    assert extract_cashtags("cash of $107.1M") == ()


def test_cashtag_dedup_preserves_first_seen_order() -> None:
    assert extract_cashtags("$TSLA $CCXI", "$CCXI again $TSLA") == ("TSLA", "CCXI")


def test_structured_source_ticker_is_extracted() -> None:
    """EDGAR lead 標題沒有 cashtag，只靠文字會整批漏掉。"""
    assert extract_source_ticker("edgar:AXTI") == "AXTI"
    assert extract_source_ticker("x:aleabitoreddit") is None
    assert extract_source_ticker(None) is None


def test_entities_combine_source_and_text_without_duplication() -> None:
    result = extract_entities(
        title="AXTI 8-K filed 2026-07-08",
        raw_text="see also $AXTI and $CCXI",
        source="edgar:AXTI",
    )
    assert result["tickers"].count("AXTI") == 1
    assert set(result["tickers"]) == {"AXTI", "CCXI"}


def test_registered_tickers_resolve_to_company_ids() -> None:
    result = extract_entities(title="$AXTI", source=None)
    assert "co:axt" in result["company_ids"]


def test_unregistered_ticker_is_kept_but_not_resolved() -> None:
    """未登記的 ticker 仍可用於 lead 間比對，但不冒充 company_id。"""
    result = extract_entities(title="$ZZZZQQ")
    assert "ZZZZQQ" in result["tickers"]
    assert result["company_ids"] == []


def _store() -> dict:
    return {
        "leads": {
            "lead_new": {
                "lead_id": "lead_new",
                "status": "pending",
                "title": "AXTI 8-K filed 2026-07-08",
                "source": "edgar:AXTI",
            },
            "lead_parked_same": {
                "lead_id": "lead_parked_same",
                "status": "parked",
                "title": "舊的 $AXTI 追源未果",
                "source": "x:someone",
                "url": "https://example.com/a",
            },
            "lead_parked_other": {
                "lead_id": "lead_parked_other",
                "status": "parked",
                "title": "無關的 $TSLA 貼文",
                "source": "x:someone",
                "url": "https://example.com/b",
            },
            "lead_go_same": {
                "lead_id": "lead_go_same",
                "status": "triaged_go",
                "title": "AXTI 8-K filed 2026-07-29",
                "source": "edgar:AXTI",
                "url": "https://example.com/c",
            },
        }
    }


def test_related_leads_finds_shared_entities_only() -> None:
    matches = related_leads(_store(), "lead_new")
    assert [m["lead_id"] for m in matches] == ["lead_parked_same"]
    assert "AXTI" in matches[0]["shared"]


def test_related_leads_can_search_other_statuses() -> None:
    """漏掉的不只是 parked——同一標的的 triaged_go 也該被看見。"""
    matches = related_leads(
        _store(), "lead_new", statuses=("parked", "triaged_go")
    )
    assert {m["lead_id"] for m in matches} == {"lead_parked_same", "lead_go_same"}


def test_related_leads_returns_empty_when_no_entities() -> None:
    store = {
        "leads": {
            "a": {"lead_id": "a", "status": "pending", "title": "沒有標的的貼文"},
            "b": {"lead_id": "b", "status": "parked", "title": "$TSLA"},
        }
    }
    assert related_leads(store, "a") == []


def test_lead_entities_falls_back_to_deriving_when_not_stored() -> None:
    lead = {"title": "$AAOI", "source": "edgar:AXTI"}
    assert {"AAOI", "AXTI"} <= lead_entities(lead)


def test_backfill_is_idempotent() -> None:
    store = _store()
    first = backfill_entities(store)
    assert first == len(store["leads"])
    assert backfill_entities(store) == 0
