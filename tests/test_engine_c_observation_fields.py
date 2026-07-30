"""Engine C 人工觀測欄位 registry 與其兩條硬契約的迴歸測試。

契約一：gate 凍結——`gate_member=true` 僅限 L9 前置條件 #3 的五項，且必須與
`engine_c/checklist.py` 實際產出的 items 完全一致。新增欄位若誤設 gate_member=true，
會讓所有既有標的的 Watchlist 升格 gate 退化，這個測試就是那道剎車。

契約二：拒絕未登記欄位——防同義詞漂移（contingent_claims vs
contingent_liquidity_claims 被當成兩個欄位，使查詢與引用都失效）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_c.checklist import _extended_observations
from engine_c.observation_fields import (
    KNOWN_AUTHORITIES,
    ObservationFieldError,
    ObservationFieldRegistry,
    authorities_for,
    get_observation_field_registry,
    validate_field_name,
)

ROOT = Path(__file__).resolve().parent.parent

# L9 前置條件 #3 的財務核驗清單。這五個名字是凍結契約，不是實作細節。
FROZEN_GATE_FIELDS = frozenset(
    {
        "gross_margin_trend",
        "customer_concentration",
        "backlog",
        "dilution",
        "valuation_pressure",
    }
)


def test_registry_loads_and_is_internally_consistent() -> None:
    registry = get_observation_field_registry()
    assert registry.version >= 1
    assert registry.fields, "registry 不得為空"
    for name, spec in registry.fields.items():
        assert spec.field_name == name
        assert spec.category in registry.categories
        assert spec.label.strip()
        assert spec.authorities, f"{name} 必須宣告 authorities"
        assert set(spec.authorities) <= KNOWN_AUTHORITIES


def test_gate_membership_is_frozen_to_the_five_l9_items() -> None:
    """新增欄位一律 gate_member=false；這道測試阻止 gate 語意漂移。"""
    registry = get_observation_field_registry()
    assert set(registry.gate_field_names) == FROZEN_GATE_FIELDS


def test_gate_fields_match_checklist_items_exactly() -> None:
    """registry 的 gate 欄位必須與 checklist 真正產出的 items 一致。

    checklist 的 gate_pass 對 items 全體取 all()，兩邊若漂移，
    registry 就會謊報哪些欄位會影響升格 gate。
    """
    source = (ROOT / "engine_c" / "checklist.py").read_text(encoding="utf-8")
    marker = "    items = {\n"
    start = source.index(marker) + len(marker)
    block = source[start : source.index("    }", start)]
    declared = {
        line.split('"')[1]
        for line in block.splitlines()
        if line.strip().startswith('"')
    }
    registry = get_observation_field_registry()
    assert declared == set(registry.gate_field_names)


def test_extended_fields_are_not_gate_members() -> None:
    registry = get_observation_field_registry()
    extended = registry.extended_field_names
    assert extended, "應至少有一個可自由擴充的非 gate 欄位"
    for name in extended:
        assert not registry.fields[name].gate_member


def test_unregistered_field_name_is_rejected() -> None:
    """同義詞漂移防線：未登記就 raise，且錯誤訊息要指出去哪裡新增。"""
    with pytest.raises(ObservationFieldError) as excinfo:
        validate_field_name("contingent_claims")  # 近似但未登記的同義詞
    message = str(excinfo.value)
    assert "config/engine_c_observation_fields.json" in message
    assert "contingent_liquidity_claims" in message, "訊息應列出已登記欄位供比對"


def test_registered_field_returns_its_authorities() -> None:
    assert authorities_for("contingent_liquidity_claims") == (
        "engine_c_financial",
        "engine_c_manual",
    )
    assert authorities_for("channel_structure") == (
        "engine_c_customer",
        "engine_c_manual",
    )


def test_extended_observations_skips_gate_and_unprovenanced_rows() -> None:
    """開放表面只收「已登記、非 gate、且有 provenance」的觀測。"""
    manual = {
        # gate 欄位不重複出現在 observations
        "customer_concentration": ("Top-5 32%", "AXT Q1 2026 earnings call"),
        # 合格
        "contingent_liquidity_claims": ("US$71.3M 上限", "AXT 8-K 2026-07-08"),
        # 沒有 provenance → 略過，避免無來源的值被 Confidence 軸引用
        "debt_maturity_and_covenants": ("2028 到期", None),
        # 未登記 → 略過
        "some_unregistered_field": ("值", "來源"),
    }
    result = _extended_observations(manual)
    assert set(result) == {"contingent_liquidity_claims"}
    row = result["contingent_liquidity_claims"]
    assert row["status"] == "manual_reviewed"
    assert row["category"] == "liquidity_and_capital"
    assert row["authorities"] == ["engine_c_financial", "engine_c_manual"]


def _payload(**field_overrides: object) -> dict:
    field = {
        "field_name": "f",
        "category": "c",
        "label": "F",
        "gate_member": False,
        "authorities": ["engine_c_manual"],
    }
    field.update(field_overrides)
    return {
        "version": 1,
        "categories": {"c": {"label": "C"}},
        "fields": [field],
    }


def test_registry_rejects_unknown_authority() -> None:
    with pytest.raises(ObservationFieldError, match="unknown authorities"):
        ObservationFieldRegistry.from_payload(_payload(authorities=["totally_made_up"]))


def test_registry_rejects_unknown_category() -> None:
    with pytest.raises(ObservationFieldError, match="unknown category"):
        ObservationFieldRegistry.from_payload(_payload(category="nope"))


def test_registry_rejects_field_without_authorities() -> None:
    with pytest.raises(ObservationFieldError, match="must declare authorities"):
        ObservationFieldRegistry.from_payload(_payload(authorities=[]))


def test_registry_round_trips_the_shipped_config() -> None:
    """from_payload 與 from_path 對同一份 config 必須等價。"""
    path = ROOT / "config" / "engine_c_observation_fields.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert (
        ObservationFieldRegistry.from_payload(payload).gate_field_names
        == ObservationFieldRegistry.from_path(path).gate_field_names
    )


# ── authority 字彙的跨模組一致性 ────────────────────────────────────────────────
# Engine C 的 authority token 目前存在三份：本模組的 KNOWN_AUTHORITIES、
# decision_lab/context.py 的 _ENGINE_C_AUTHORITIES、以及 decision_lab/sizing.py 的
# AXIS_REFERENCE_AUTHORITIES。刻意不合併成一份是為了避免 decision_lab 反向依賴
# Engine C（AGENTS.md 的 workflow_ports 分層契約），代價是三者可能漂移。
# 漂移的後果是靜默的：欄位的 authority 被過濾掉 → 軸悄悄 fallback → Confidence 歸零
# 而沒有任何錯誤訊息。以下兩個測試就是這個代價的剎車。


def _engine_c_tokens_from_axes() -> set[str]:
    from decision_lab.sizing import AXIS_REFERENCE_AUTHORITIES

    return {
        token
        for tokens in AXIS_REFERENCE_AUTHORITIES.values()
        for token in tokens
        if token.startswith("engine_c_")
    }


def test_engine_c_authority_vocabulary_agrees_across_all_three_copies() -> None:
    from decision_lab.context import _ENGINE_C_AUTHORITIES

    assert set(KNOWN_AUTHORITIES) == _engine_c_tokens_from_axes()
    assert set(KNOWN_AUTHORITIES) == set(_ENGINE_C_AUTHORITIES)


def test_every_registered_field_is_citable_by_at_least_one_axis() -> None:
    """防死角登記：欄位宣告的 authority 若沒有任何軸接受，該欄位永遠無法被引用。"""
    from decision_lab.sizing import AXIS_REFERENCE_AUTHORITIES

    registry = get_observation_field_registry()
    for name, spec in registry.fields.items():
        citable_by = [
            axis
            for axis, allowed in AXIS_REFERENCE_AUTHORITIES.items()
            if set(spec.authorities) & set(allowed)
        ]
        assert citable_by, f"{name} 宣告的 authorities {spec.authorities} 沒有任何軸接受"
