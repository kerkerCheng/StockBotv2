"""Materialization contract：artifact 的形狀、atomic write、fail closed、遮蔽、overview 投影。

刻意**不依賴 Neo4j／Engine C**：這一層的責任是「一份 AnalystView 字典 → 一份 artifact」，
把它綁在真實資料上只會讓測試在 DB 沒開時變成綠色的空跑（L13-2）。
真實四檔的端到端結果記在 `docs/reports/2026-09-07-webapp-mvp.md`。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from alpha.absence import SETTLED_ABSENCE_KINDS
from webapp.contracts import (
    ARTIFACT_SCHEMA_VERSION, ArtifactUnavailable, REQUIRED_FIELDS, canonical_digest,
    freshness_identity, freshness_of, validate_artifact,
)
from webapp.materialize import build_overview, materialize_view, redact_private_paths
from webapp.store import ArtifactStore


def _datum(key, label, value=None, status="available", basis="deterministic", **kw):
    return {"key": key, "label": label, "value": value, "status": status, "basis": basis,
            "authority": kw.get("authority"), "method": None, "unit": kw.get("unit"),
            "as_of": kw.get("as_of"), "reason": kw.get("reason"),
            "evidence_refs": [], "dependencies": kw.get("dependencies"),
            "absence_kind": kw.get("absence_kind")}


def _line(key, datum, role="headline_number"):
    return {"key": key, "display_label": datum["label"], "datum": datum, "role": role}


def fake_view(ticker="TEST", *, fair_value=100.0, absence_kind=None, reason=None,
              readiness_state="ready", blockers=(), price=50.0, quote_unit="USD",
              currency="USD"):
    """一份最小但形狀正確的 `AnalystView.to_dict()`。"""
    has_fv = fair_value is not None
    lines = [
        _line("current_price", _datum("current_price", "現價", price, unit="quote_unit（%s）" % quote_unit,
                                      basis="observation", as_of="2026-09-04",
                                      dependencies={"quote_unit": quote_unit})),
        _line("fair_value", _datum(
            "fair_value", "Fair value", fair_value if has_fv else None,
            status="available" if has_fv else "missing", basis="deterministic" if has_fv else "none",
            unit="currency_per_share" if has_fv else None, reason=reason,
            absence_kind=None if has_fv else (absence_kind or "not_yet_recorded"),
            dependencies={"currency": currency} if has_fv else None)),
        _line("value_date", _datum("value_date", "value date", "2027-06-30" if has_fv else None,
                                   status="available" if has_fv else "missing",
                                   basis="session_judgment" if has_fv else "none", unit="date",
                                   absence_kind=None if has_fv else "upstream_unavailable")),
        _line("price_return", _datum("price_return", "隱含報酬", -0.2 if has_fv else None,
                                     status="available" if has_fv else "missing",
                                     basis="deterministic" if has_fv else "none", unit="ratio",
                                     absence_kind=None if has_fv else (absence_kind or "not_yet_recorded"))),
        _line("annualized_price_return", _datum(
            "annualized_price_return", "年化", -0.25 if has_fv else None,
            status="available" if has_fv else "missing",
            basis="deterministic" if has_fv else "none", unit="ratio",
            absence_kind=None if has_fv else (absence_kind or "not_yet_recorded"))),
    ]
    panel = {"key": "headline", "title": "頭條", "questions": ["q4_implied_return"],
             "status": "available" if has_fv else "missing", "optional": False,
             "source_sections": ["implied_return"], "source_statuses": {"implied_return": "available"},
             "source_absence_kinds": {}, "lines": lines, "weak_inputs": [], "catalysts": [],
             "checkpoints": [], "disproofs": [], "evidence": [], "attention": [],
             "attention_scope": None, "attention_total": 0, "risks": [], "notes": [],
             "context": {"accounting_basis": "gaap", "period": "FY2027"}, "reason": reason,
             "absence_kind": None if has_fv else (absence_kind or "not_yet_recorded"),
             # 與 production 同一份判準（`AnalystPanel.absence_is_settled`），不在 fixture 裡
             # 自己寫死一組——那會讓測試守著一份與實作不同的規則。
             "absence_is_settled": absence_kind in SETTLED_ABSENCE_KINDS}
    empty = dict(panel, key="other", lines=[], status="available", absence_kind=None,
                 absence_is_settled=False)
    return {
        "schema_version": "analyst-view/1", "source_schema_version": "alpha-investment-view/v1",
        "ticker": ticker, "company_id": "co:test", "company_label": "Test Corp.",
        "as_of": None, "point_in_time_mode": "current", "generated_on": "2026-09-07",
        "research_context_digest": "sha256:abc",
        "headline": panel, "fundamental": empty, "why": empty, "research": empty, "entry": empty,
        "readiness": {"state": readiness_state, "core_panels": ["headline"], "optional_panels": ["entry"],
                      "flags": [], "blockers": list(blockers), "optional_unavailable": ["entry：missing"],
                      "rule": "rule", "blocker_details": [
                          {"panel": "headline", "status": "missing", "absence_kind": absence_kind,
                           "settled": absence_kind in SETTLED_ABSENCE_KINDS, "reason": reason}
                      ] if blockers else [], "flag_details": []},
        "refresh": {"overall": "current", "counts": {}, "change_detection": "policy",
                    "judged_context_matches": True, "attention": [], "notes": []},
        "limits": [], "warnings": [], "questions": {}, "panel_order": ["headline"],
    }


# ---------------------------------------------------------------------------
# artifact 形狀
# ---------------------------------------------------------------------------

def test_artifact_carries_every_required_field() -> None:
    payload = materialize_view(fake_view())
    for field in REQUIRED_FIELDS:
        assert field in payload, field
    assert payload["schema_version"] == ARTIFACT_SCHEMA_VERSION


def test_content_digest_detects_any_post_write_mutation() -> None:
    payload = dict(materialize_view(fake_view()))
    validate_artifact("TEST", payload)
    payload["view"]["headline"]["lines"][1]["datum"]["value"] = 999.0
    with pytest.raises(ArtifactUnavailable, match="content_digest"):
        validate_artifact("TEST", payload)


def test_freshness_identity_ignores_price_but_tracks_cognition() -> None:
    """價格動了不算「認知變了」；context digest 或 readiness 動了才算（L12：兩種語意分開）。"""
    base = dict(ticker="T", as_of=None, point_in_time_mode="current",
                research_context_digest="sha256:a", source_schema_version="v1",
                readiness_state="ready", refresh_overall="current")
    assert freshness_identity(**base) == freshness_identity(**base)
    assert freshness_identity(**{**base, "research_context_digest": "sha256:b"}) != freshness_identity(**base)
    assert freshness_identity(**{**base, "readiness_state": "blocked"}) != freshness_identity(**base)


def test_missing_required_field_is_rejected_not_patched() -> None:
    payload = dict(materialize_view(fake_view()))
    del payload["overview"]
    with pytest.raises(ArtifactUnavailable, match="缺必要欄位"):
        validate_artifact("TEST", payload)


def test_schema_version_mismatch_fails_closed() -> None:
    payload = dict(materialize_view(fake_view()))
    payload["schema_version"] = "stockbot-app/analyst-view/999"
    payload["content_digest"] = canonical_digest(payload)
    with pytest.raises(ArtifactUnavailable, match="schema"):
        validate_artifact("TEST", payload)


def test_filename_and_content_ticker_must_agree() -> None:
    payload = materialize_view(fake_view("AAA"))
    with pytest.raises(ArtifactUnavailable, match="檔名與內容不一致"):
        validate_artifact("BBB", payload)


# ---------------------------------------------------------------------------
# overview 是選取不是計算
# ---------------------------------------------------------------------------

def test_overview_copies_values_verbatim_and_never_converts_units() -> None:
    view = fake_view(price=47.518, quote_unit="GBp", fair_value=0.05, currency="GBP")
    overview = build_overview(view)
    # GBp（便士）與 GBP（英鎊）差 100 倍。overview **原樣帶著兩個單位**，不換算、不合併。
    assert overview["price"]["value"] == 47.518
    assert overview["price"]["quote_unit"] == "GBp"
    assert overview["future_target"]["value"] == 0.05
    assert overview["future_target"]["currency"] == "GBP"


def test_overview_absence_keeps_none_not_zero() -> None:
    overview = build_overview(fake_view(fair_value=None, readiness_state="blocked"))
    assert overview["future_target"]["value"] is None
    assert overview["implied_return"]["simple"]["value"] is None
    assert overview["future_target"]["status"] == "missing"


def test_overview_carries_the_absence_kind_so_the_ui_never_parses_prose() -> None:
    overview = build_overview(fake_view(
        fair_value=None, absence_kind="deliberate_abstention", readiness_state="blocked",
        blockers=["headline：missing"], reason="刻意不主張目標倍數：無法錨定"))
    assert overview["future_target"]["absence_kind"] == "deliberate_abstention"
    assert overview["primary_attention"]["absence_kind"] == "deliberate_abstention"
    assert overview["primary_attention"]["settled"] is True


def test_overview_contains_no_arithmetic_on_the_numbers() -> None:
    """空跑檢查：overview 若自己算 gap／百分比，這裡的值就不會與來源逐格相等。"""
    view = fake_view(price=50.0, fair_value=100.0)
    overview = build_overview(view)
    lines = {line["key"]: line["datum"] for line in view["headline"]["lines"]}
    assert overview["price"]["value"] is lines["current_price"]["value"]
    assert overview["future_target"]["value"] is lines["fair_value"]["value"]
    assert overview["implied_return"]["simple"]["value"] is lines["price_return"]["value"]


# ---------------------------------------------------------------------------
# 遮蔽
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "找不到 session 判斷檔（library/private/alpha/judgments/IQE.L.json）",
    r"寫入 C:\Users\someone\code\StockBotv2\library\private\alpha\valuation\COHR.jsonl",
    "library/private/engine_c/engine_c.db 讀取失敗",
])
def test_private_paths_never_survive_materialization(text: str) -> None:
    redacted = redact_private_paths({"reason": text})["reason"]
    assert "library/private" not in redacted
    assert "library\\private" not in redacted
    assert "C:\\" not in redacted
    assert "«private-authority»" in redacted


def test_redaction_keeps_the_rest_of_the_sentence() -> None:
    out = redact_private_paths("找不到 session 判斷檔（library/private/alpha/judgments/X.json）——請先寫判斷")
    assert out.startswith("找不到 session 判斷檔")
    assert out.endswith("請先寫判斷")


def test_redaction_walks_nested_structures() -> None:
    payload = redact_private_paths({"a": [{"b": "see library/private/x.json"}]})
    assert "library/private" not in json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# atomic write ／ fail closed read
# ---------------------------------------------------------------------------

def test_write_is_atomic_and_leaves_no_temp_files(tmp_path) -> None:
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("AAA")))
    assert [p.name for p in tmp_path.iterdir()] == ["AAA.json"]


def test_half_written_json_is_rejected_not_partially_served(tmp_path) -> None:
    store = ArtifactStore(tmp_path)
    path = store.write(materialize_view(fake_view("AAA")))
    text = path.read_text(encoding="utf-8")
    path.write_text(text[: len(text) // 2], encoding="utf-8")   # 模擬非 atomic 的半份寫入
    with pytest.raises(ArtifactUnavailable, match="JSON 解析失敗"):
        store.read("AAA")


def test_broken_artifact_surfaces_in_read_all_instead_of_vanishing(tmp_path) -> None:
    """INV-3：查不到了不是合法 lifecycle——壞掉的 artifact 必須帶著理由現形。"""
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("GOOD")))
    (tmp_path / "BAD.json").write_text("{", encoding="utf-8")
    rows = {t: (payload, reason) for t, payload, _f, reason in store.read_all()}
    assert set(rows) == {"GOOD", "BAD"}
    assert rows["GOOD"][0] is not None
    assert rows["BAD"][0] is None and rows["BAD"][1]


def test_meta_file_is_not_mistaken_for_a_stock(tmp_path) -> None:
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("AAA")))
    (tmp_path / ".meta.json").write_text("{}", encoding="utf-8")
    assert store.tickers() == ["AAA"]


@pytest.mark.parametrize("bad", ["../secrets", "..", "a/b", "C:/x", "AA*", ""])
def test_ticker_slug_is_an_allowlist_not_a_filter(tmp_path, bad: str) -> None:
    store = ArtifactStore(tmp_path)
    with pytest.raises(ArtifactUnavailable):
        store.path_for(bad)


def test_stale_is_a_state_not_an_error() -> None:
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    fresh = freshness_of(datetime.now(timezone.utc))
    stale = freshness_of(old)
    assert fresh.state == "fresh" and stale.state == "stale"
    assert stale.age_seconds > 0
    assert "不會觸發重建" in stale.to_dict()["rule"]
