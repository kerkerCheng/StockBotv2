"""「這個 origin 對這條邊算不算外部印證」的唯一 owner（`query.origin_resolution.corroboration`，Phase 6 Step 6.4）。

plan 2026-10-02-002 §5 的九個夾具：
①客戶 origin 引文具名 → 外部印證；②客戶 origin 引文不具名 → 待判定＋`unnamed`；③主詞名冊無寫法 → `no_name_forms`；
④產業研究「Lumentum announced…」→ 媒體轉述＋`relay`；⑤同一 origin 一段轉述、一段具名非轉述 → 外部印證；
⑥媒體宣告 independent、引文具名 → 外部印證（轉述檢查不套）；⑦技術節點之間的邊不套具名 → 照舊；
⑧呼叫端沒給逐字 → 例外；⑨`verify_citations` 對②④的 independent 引用拒收、理由分開。
另：Sivers→CW DFB（華星光年報那段沒提 Sivers）——舊口徑「這條邊任何一段引文具名」會放行，新口徑逐來源 → 自報·filing。

registry 用**真的** `IdentityRegistry`／`CompanyIdentity`（假名冊的形狀漂移就是 2026-09-16 的事發，見 test_structure_table）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from identity.registry import CompanyIdentity, IdentityRegistry
from query.bottleneck import classify_evidence, collapse_assertions, edge_corroborations, structure_table
from query.origin_resolution import (INDEPENDENT, PUBLISHER_KINDS, WITHHELD_REASONS, OriginDoc, corroboration,
                                     load_publishers)

SUPPLIER = "co:lumentum"


def _registry() -> IdentityRegistry:
    return IdentityRegistry(version=1, companies=(
        CompanyIdentity("co:lumentum", "LITE", display_name="Lumentum Holdings Inc.", name_aliases=("Lumentum",)),
        CompanyIdentity("co:nvidia", "NVDA", display_name="NVIDIA Corporation", name_aliases=("NVIDIA", "Nvidia")),
        CompanyIdentity("co:sivers_semiconductors", "SIVE.ST", display_name="Sivers Semiconductors AB",
                        name_aliases=("Sivers",)),
        CompanyIdentity("co:luxnet", "4979.TWO", display_name="LuxNet Corporation", name_aliases=("華星光",)),
        CompanyIdentity("co:nameless", None),                                   # 名冊沒有任何寫法
        CompanyIdentity("co:twin_a", None, display_name="Twin"),                # 兩個代號共用同一個寫法
        CompanyIdentity("co:twin_b", None, display_name="Twin"),
    ))


@pytest.fixture()
def pubs(tmp_path: Path):
    path = tmp_path / "publishers.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "kinds": {k: {"corroborates": v} for k, v in PUBLISHER_KINDS.items()},
        "publishers": [
            {"origin": "TrendForce", "kind": "industry_research", "corroborates": True, "seen_in": "tf_doc"},
            {"origin": "Reuters", "kind": "media", "corroborates": False, "seen_in": "reuters_doc"},
        ],
    }), encoding="utf-8")
    return load_publishers(path)


def _verdict(origin, subject, quotes, pubs, *, linkage=None, filing=False, doc="d1"):
    return corroboration(origin, subject, [OriginDoc(doc_id=doc, linkage=linkage, quotes=tuple(quotes))],
                         _registry(), filing=filing, publishers=pubs)


# ---------------------------------------------------------------------------
# ①–⑦：owner 本身
# ---------------------------------------------------------------------------

def test_1_customer_quote_that_names_the_supplier_corroborates(pubs) -> None:
    v = _verdict("NVIDIA", SUPPLIER, ["NVIDIA will purchase lasers from Lumentum under a multiyear agreement"], pubs)
    assert (v.level, v.withheld) == ("externally_corroborated", None)
    assert v.quote and "Lumentum" in v.quote and v.docs == ("d1",)


def test_2_customer_quote_that_does_not_name_the_supplier_is_withheld_as_unnamed(pubs) -> None:
    v = _verdict("NVIDIA", SUPPLIER, ["The nonexclusive agreement includes an NVIDIA multibillion purchase commitment"],
                 pubs)
    assert (v.level, v.withheld, v.docs) == ("needs_review", "unnamed", ("d1",))
    # 產品名不算具名（§0.1 #3）：寫法只來自名冊
    assert _verdict("NVIDIA", SUPPLIER, ["NVIDIA buys 200G EML lasers"], pubs).withheld == "unnamed"


def test_3_subject_without_usable_name_forms_is_no_name_forms_not_unnamed(pubs) -> None:
    v = _verdict("NVIDIA", "co:nameless", ["NVIDIA buys from someone"], pubs)
    assert (v.level, v.withheld) == ("needs_review", "no_name_forms")
    # 每個寫法都與另一家共用（同一家公司兩個 id）＝同樣無名可比；引文就算寫了 Twin 也比不到（不猜）
    shared = _verdict("NVIDIA", "co:twin_a", ["NVIDIA buys from Twin"], pubs)
    assert (shared.level, shared.withheld) == ("needs_review", "no_name_forms")
    # 發布者那一支同一個理由，落在媒體轉述
    assert _verdict("TrendForce", "co:nameless", ["x"], pubs).withheld == "no_name_forms"


def test_4_research_publisher_relaying_the_supplier_is_media_relay_with_the_terms(pubs) -> None:
    v = _verdict("TrendForce", SUPPLIER, ["Lumentum announced a 1.6T ELS module at OFC"], pubs)
    assert (v.level, v.withheld, v.relay_terms) == ("media_relay", "relay", ("announced",))
    # 有具名、不是轉述 → 外部印證；沒具名 → 媒體轉述＋unnamed（三種分開）
    assert _verdict("TrendForce", SUPPLIER, ["Lumentum holds 60% share of EML lasers"], pubs).level == \
        "externally_corroborated"
    assert _verdict("TrendForce", SUPPLIER, ["EML laser supply is tight"], pubs).withheld == "unnamed"


def test_5_one_relay_quote_and_one_named_own_quote_in_the_same_origin_corroborates(pubs) -> None:
    v = _verdict("TrendForce", SUPPLIER, ["Lumentum said demand doubled", "Lumentum holds 60% share of EML lasers"],
                 pubs)
    assert (v.level, v.withheld, v.quote) == ("externally_corroborated", None, "Lumentum holds 60% share of EML lasers")


def test_6_media_document_declared_independent_corroborates_without_the_relay_check(pubs) -> None:
    # 宣告 independent 的文件不套轉述（plan §0.6 #2：ROADMAP「翻案靠逐份宣告」）；具名照樣要
    v = _verdict("Reuters", SUPPLIER, ["Lumentum is the only qualified supplier, the person said"], pubs,
                 linkage=INDEPENDENT)
    assert (v.level, v.withheld) == ("externally_corroborated", None)
    assert _verdict("Reuters", SUPPLIER, ["Supply is tight, the person said"], pubs,
                    linkage=INDEPENDENT).withheld == "unnamed"
    # 沒宣告的媒體照舊不升（不是這條規則擋的 → withheld 是 None）
    plain = _verdict("Reuters", SUPPLIER, ["Lumentum is the only qualified supplier"], pubs)
    assert (plain.level, plain.withheld) == ("media_relay", None)


def test_6b_relay_exemption_is_per_document_not_per_origin(pubs) -> None:
    """同一家媒體：宣告 independent 的那份沒具名、沒宣告的那份具名 → 不升（具名的那份根本沒過 publisher_lifts）。"""
    v = corroboration("Reuters", SUPPLIER, [
        OriginDoc(doc_id="own", linkage=INDEPENDENT, quotes=("Supply is tight, sources said",)),
        OriginDoc(doc_id="relay", linkage=None, quotes=("Lumentum is the only qualified supplier",)),
    ], _registry(), publishers=pubs)
    assert (v.level, v.withheld, v.docs) == ("media_relay", "unnamed", ("own",))


def test_7_edges_whose_subject_is_not_a_company_keep_the_old_rule(pubs) -> None:
    assert _verdict("NVIDIA", "tech:cpo", ["CPO cuts power"], pubs).level == "externally_corroborated"
    assert _verdict("TrendForce", "tech:cpo", ["CPO adoption announced"], pubs).level == "externally_corroborated"
    assert _verdict("Some Blog", "tech:cpo", ["x"], pubs).level == "needs_review"


def test_subject_itself_and_joint_announcements_are_unchanged(pubs) -> None:
    assert _verdict("Lumentum", SUPPLIER, ["Lumentum ships"], pubs).level == "self_reported"
    assert _verdict("Lumentum", SUPPLIER, ["Lumentum ships"], pubs, filing=True).level == "self_reported_costly"
    joint = _verdict("Lumentum / NVIDIA (joint announcement)", SUPPLIER, [], pubs)
    assert (joint.level, joint.withheld) == ("counterparty_joint", None)


def test_withheld_reasons_are_a_closed_vocabulary() -> None:
    assert WITHHELD_REASONS == ("unnamed", "no_name_forms", "relay")


# ---------------------------------------------------------------------------
# 邊層級：classify_evidence／collapse_assertions（資料流）
# ---------------------------------------------------------------------------

def _row(aid, origin, *, src=SUPPLIER, relation="supplies_to", dst="tech:cw_dfb_laser", source_type="press_release",
         linkage=None, doc=None):
    return {"src": src, "relation": relation, "dst": dst, "attributes": {}, "confidence": 0.8, "origin": origin,
            "source_type": source_type, "origin_linkage": linkage, "source_doc_id": doc or f"doc_{aid}",
            "published_at": None, "assertion_id": aid}


def _classify(rows, quotes, pubs):
    edge = next(iter(collapse_assertions(rows).values()))
    return classify_evidence(edge.src, edge.origins, _registry(), filing_origins=edge.filing_origins,
                             quotes_by_assertion=quotes, origin_assertions=edge.origin_assertions, publishers=pubs)


def test_sivers_old_any_quote_scope_would_pass_but_per_origin_scope_does_not(pubs) -> None:
    """華星光年報撐的外部印證：那段沒提 Sivers；Sivers 自己的年報有提——舊口徑（任何一段）會放行。"""
    rows = [_row("a1", "Sivers Semiconductors", src="co:sivers_semiconductors", source_type="filing"),
            _row("a2", "LuxNet (華星光通科技)", src="co:sivers_semiconductors")]
    quotes = {"a1": ["Sivers ships CW DFB lasers to a Taiwanese module maker"],
              "a2": ["本公司 CW 雷射晶片來源分散，主要為海外供應商"]}
    assert _classify(rows, quotes, pubs) == "self_reported_costly"
    quotes["a2"] = ["本公司向 Sivers 採購 CW 雷射晶片"]
    assert _classify(rows, quotes, pubs) == "externally_corroborated"


def test_collapse_records_which_document_each_origin_cites(pubs) -> None:
    rows = [_row("a1", "Reuters", linkage=INDEPENDENT, doc="r_own"), _row("a2", "Reuters", doc="r_relay")]
    edge = next(iter(collapse_assertions(rows).values()))
    assert edge.origin_assertions == {"Reuters": [("a1", "r_own", INDEPENDENT), ("a2", "r_relay", None)]}
    verdicts = edge_corroborations(edge.src, edge.origins, _registry(), quotes_by_assertion={
        "a1": ["Lumentum is the only qualified supplier, the person said"]},
        origin_assertions=edge.origin_assertions, publishers=pubs)
    assert [(v.origin, v.level, v.docs) for v in verdicts] == [("Reuters", "externally_corroborated", ("r_own",))]


# ---------------------------------------------------------------------------
# ⑧：呼叫端沒給逐字 → 例外（不得靜默把全部降級，L13）
# ---------------------------------------------------------------------------

def test_8_callers_that_do_not_pass_quotes_fail_loudly(pubs) -> None:
    from query.structure import _classify_edges

    rows = [_row("a1", "NVIDIA")]
    edge = next(iter(collapse_assertions(rows).values()))
    with pytest.raises(TypeError):
        classify_evidence(edge.src, edge.origins, _registry(), origin_assertions=edge.origin_assertions)
    with pytest.raises(TypeError):
        classify_evidence(edge.src, edge.origins, _registry(), quotes_by_assertion=None,
                          origin_assertions=edge.origin_assertions)
    with pytest.raises(TypeError):
        structure_table(rows, _registry())
    with pytest.raises(TypeError):
        _classify_edges(rows)


# ---------------------------------------------------------------------------
# ⑨：讀圖引用核對問同一個 owner，理由分開寫
# ---------------------------------------------------------------------------

def test_9_verify_citations_rejects_unnamed_and_relayed_independent_citations_with_separate_reasons(tmp_path) -> None:
    """讀圖寫入端（真名冊、真 publishers）：標 independent 的引用，被引用的那段要具名主詞、發布者的不得是轉述句。"""
    from alpha.errors import ContractViolation
    from alpha.providers.structure_readings import append_reading_record
    from test_structure_reading_v3 import CUSTOMER_Q, DEMAND_Q, SIVERS, SOCKET, _cite, _quotes, _v3

    unnamed_q = "Ayar Labs selected a single laser array supplier for the SuperNova light source"
    relay_q = "Sivers announced volume shipments of laser arrays for the SuperNova light source"
    quotes = _quotes(SOCKET)
    quotes[(SIVERS, "supplies_to", SOCKET)] += [
        {"quote": unnamed_q, "doc": "doc_unnamed", "origin": "Ayar Labs"},
        {"quote": relay_q, "doc": "doc_relay", "origin": "TrendForce"},
    ]

    def moat(quote: str, doc: str) -> dict:
        return _v3(kind="moat", citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET),
                                           _cite("supply_side", quote, doc, SOCKET, independent=True)])

    with pytest.raises(ContractViolation, match=f"沒有具名 {SIVERS}") as unnamed:
        append_reading_record(moat(unnamed_q, "doc_unnamed"), directory=tmp_path, quotes=quotes)
    with pytest.raises(ContractViolation, match="轉述句（announced）") as relayed:
        append_reading_record(moat(relay_q, "doc_relay"), directory=tmp_path, quotes=quotes)
    assert "轉述" not in str(unnamed.value) and "沒有具名" not in str(relayed.value)     # 理由分開，不壓成一格
    append_reading_record(moat(CUSTOMER_Q, "doc_customer"), directory=tmp_path, quotes=quotes)  # 具名的客戶端照收
