"""Engine C 人工觀測欄位 registry 與其兩條硬契約的迴歸測試。

契約一：gate 凍結——`gate_member=true` 僅限 L9 前置條件 #3 的五項，且必須與
`engine_c/checklist.py` 實際產出的 items 完全一致。新增欄位若誤設 gate_member=true，
會讓所有既有標的的 Watchlist 升格 gate 退化，這個測試就是那道剎車。

契約二：拒絕未登記欄位——防同義詞漂移（contingent_claims vs
contingent_liquidity_claims 被當成兩個欄位，使查詢與引用都失效）。
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from engine_c.checklist import _extended_observations, _parse_runway_inputs
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

    比對走 AST 而非原始碼文字：先前的實作逐行抓行首字串，任何讓 label 或
    續行落在行首的純格式調整都會被誤判成契約漂移，而真正該擋的是 items
    鍵集合本身的變化。
    """
    tree = ast.parse((ROOT / "engine_c" / "checklist.py").read_text(encoding="utf-8"))
    dicts = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Dict)
        and any(isinstance(t, ast.Name) and t.id == "items" for t in node.targets)
    ]
    assert len(dicts) == 1, "checklist.py 應只有一處 items dict 賦值"
    declared = {
        key.value for key in dicts[0].keys if isinstance(key, ast.Constant)
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


# ── authority 字彙的單一權威 ────────────────────────────────────────────────────
# 2026-07-31 之前這份字彙有三份寫死副本，靠測試防漂移。現已收斂成
# config/authority_tokens.json 一份，Engine C 與 decision_lab 都由
# identity/authority_tokens.py 讀取。以下測試確認收斂沒有回退，
# 並確認凍結的軸對照表只用已登記的 token。


def _engine_c_tokens_from_axes() -> set[str]:
    from decision_lab.sizing import AXIS_REFERENCE_AUTHORITIES

    return {
        token
        for tokens in AXIS_REFERENCE_AUTHORITIES.values()
        for token in tokens
        if token.startswith("engine_c_")
    }


def test_engine_c_vocabulary_comes_from_the_single_neutral_registry() -> None:
    from decision_lab.context import _ENGINE_C_AUTHORITIES
    from identity.authority_tokens import tokens_for_owner

    canonical = tokens_for_owner("engine_c")
    assert set(KNOWN_AUTHORITIES) == set(canonical)
    assert set(_ENGINE_C_AUTHORITIES) == set(canonical)
    assert _engine_c_tokens_from_axes() <= set(canonical)


def test_frozen_axis_mapping_only_uses_registered_tokens() -> None:
    """AXIS_REFERENCE_AUTHORITIES 刻意維持寫死（評分骨架已凍進舊 decision），
    但它用到的每個 token 都必須在中立 registry 裡登記。"""
    from decision_lab.sizing import AXIS_REFERENCE_AUTHORITIES
    from identity.authority_tokens import all_authority_tokens

    used = {t for tokens in AXIS_REFERENCE_AUTHORITIES.values() for t in tokens}
    unknown = sorted(used - all_authority_tokens())
    assert not unknown, f"軸對照表用了未登記的 token：{unknown}"


def test_graph_and_engine_c_whitelists_do_not_overlap() -> None:
    """owner 分群的意義就是防 over-claim；兩群不得相交。"""
    from identity.authority_tokens import tokens_for_owner

    assert not (tokens_for_owner("engine_a") & tokens_for_owner("engine_c"))


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


def test_runway_inputs_require_all_three_numbers_and_provenance() -> None:
    """runway 是除法，部分推導只會給出看似精確的錯誤答案。

    因此三個數值缺一、或缺 source／as_of，一律視為未提供而非部分接受。
    """
    complete = json.dumps(
        {
            "cash_and_equivalents": 412_167_000,
            "total_debt": 85_397_000,
            "free_cash_flow_ttm": -25_000_000,
            "note": "取自 Q2 10-Q 現金流量表",
        }
    )

    parsed = _parse_runway_inputs(complete, "AXT Q2 2026 10-Q", "2026-06-30T00:00:00+00:00")
    assert parsed == {
        "cash_and_equivalents": 412_167_000.0,
        "total_debt": 85_397_000.0,
        "free_cash_flow_ttm": -25_000_000.0,
        "source": "AXT Q2 2026 10-Q",
        "as_of": "2026-06-30T00:00:00+00:00",
    }

    partial = json.dumps({"cash_and_equivalents": 1, "total_debt": 2})
    assert _parse_runway_inputs(partial, "src", "2026-06-30") is None
    assert _parse_runway_inputs("not json at all", "src", "2026-06-30") is None
    assert _parse_runway_inputs(complete, None, "2026-06-30") is None
    assert _parse_runway_inputs(complete, "src", None) is None
    # 布林是 int 的子類，不得被當成金額。
    bool_value = json.dumps(
        {"cash_and_equivalents": True, "total_debt": 2, "free_cash_flow_ttm": -1}
    )
    assert _parse_runway_inputs(bool_value, "src", "2026-06-30") is None


def test_runway_inputs_field_is_registered_and_not_a_gate_member() -> None:
    registry = get_observation_field_registry()
    spec = registry.get("runway_inputs")

    assert spec is not None, "runway_inputs 必須登記，否則 set_manual_field 會拒寫"
    assert spec.gate_member is False
    assert "engine_c_manual" in spec.authorities
