"""origin 解析唯一 owner（`query/origin_resolution.py`）與發布者登記（`config/publishers.json`）——Phase 4 Step 4.3。

守五件事：
1. **三態**：名冊公司 → 登記的發布者 → 解析不到；解析不到不得被當成「不同源」（L8／L11 的 laundering）。
2. **媒體不得整類升級**（L11-3）：設定檔裡把一筆媒體改成 `corroborates: true` 會在載入時失敗；媒體文只有宣告
   `origin_linkage=independent` 的那份算印證；任何發布者宣告 `same_origin` 的文件是轉述。
3. **同一個 origin 在邊的證據等級（`classify_evidence`）與讀圖引用核對（`verify_citations`）結論相同**——兩處問同一個函式。
4. **列舉證據等級的五張表 key 集合相等**；`media_relay` 與 `needs_review` 同級、各表取值也相同（只拆兩義，不是升降級）。
5. 登記清單本身：每一筆都真的對得到庫內某份文件的 origin（打錯字＝永遠比不到的死設定）、沒有一筆被名冊公司遮住。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

import pytest

from query.bottleneck import EVIDENCE_LABEL, EVIDENCE_RANK, _strip_annotation, classify_evidence, collapse_assertions
from query.origin_resolution import (
    PUBLISHER_KINDS, PublisherConfigError, get_publishers, load_publishers, publisher_lifts, resolve_origin,
)

ROOT = Path(__file__).resolve().parent.parent


class _Company:
    def __init__(self, cid: str, display_name: str, *, name_aliases=(), aliases=()):
        self.company_id, self.display_name = cid, display_name
        self.name_aliases, self.aliases = tuple(name_aliases), tuple(aliases)


class _Registry:
    """形狀與真的 `CompanyIdentity` 名冊一致：`display_name`、`name_aliases`、`aliases`（ticker），沒有 `name`。"""

    def __init__(self):
        self._c = [
            _Company("co:sivers_semiconductors", "Sivers Semiconductors AB", name_aliases=("Sivers",)),
            _Company("co:ayar_labs", "Ayar Labs, Inc."),
            _Company("co:coherent", "Coherent Corp.", name_aliases=("Coherent",)),
            _Company("co:sumitomo_electric", "Sumitomo Electric Industries, Ltd.", name_aliases=("Sumitomo",)),
        ]

    @property
    def companies(self):
        return tuple(self._c)

    def company_id_for_ticker(self, ticker):
        return None

    def has_company(self, cid):
        return any(c.company_id == cid for c in self._c)


def _write_publishers(tmp_path: Path, entries: list[dict], *, kinds: dict | None = None) -> Path:
    path = tmp_path / "publishers.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "kinds": kinds if kinds is not None else {k: {"corroborates": v} for k, v in PUBLISHER_KINDS.items()},
        "publishers": entries,
    }, ensure_ascii=False), encoding="utf-8")
    return path


def _pubs(tmp_path: Path):
    return load_publishers(_write_publishers(tmp_path, [
        {"origin": "TrendForce", "kind": "industry_research", "corroborates": True, "seen_in": "tf_doc"},
        {"origin": "Reuters", "kind": "media", "corroborates": False, "seen_in": "reuters_doc"},
    ]))


# ---------------------------------------------------------------------------
# 1｜三態
# ---------------------------------------------------------------------------

def test_resolve_origin_has_three_states_and_company_comes_first(tmp_path) -> None:
    reg, pubs = _Registry(), _pubs(tmp_path)
    company = resolve_origin("Ayar Labs（客戶端新聞稿）", reg, publishers=pubs)
    assert (company.kind, company.id, company.corroborates) == ("company", "co:ayar_labs", None)
    research = resolve_origin("TrendForce", reg, publishers=pubs)
    assert (research.kind, research.id, research.corroborates, research.publisher_kind) == (
        "publisher", "TrendForce", True, "industry_research")
    media = resolve_origin("reuters (轉載 Coherent 新聞稿)", reg, publishers=pubs)
    assert (media.kind, media.id, media.corroborates) == ("publisher", "Reuters", False), \
        "去尾端註解、大小寫不計後整串比對"
    unknown = resolve_origin("Some Blog", reg, publishers=pubs)
    assert (unknown.kind, unknown.id, unknown.corroborates) == ("unresolved", None, False)
    # 子字串不算：未登記就是解析不到，不猜（L17-4）
    assert resolve_origin("Reuters Breakingviews", reg, publishers=pubs).kind == "unresolved"
    assert resolve_origin(None, reg, publishers=pubs).kind == "unresolved"


def test_publisher_lifts_reads_each_documents_declaration(tmp_path) -> None:
    reg, pubs = _Registry(), _pubs(tmp_path)
    research = resolve_origin("TrendForce", reg, publishers=pubs)
    media = resolve_origin("Reuters", reg, publishers=pubs)
    assert publisher_lifts(research) and publisher_lifts(research, [None])
    assert not publisher_lifts(research, ["same_origin"]), "研究機構轉述供應商新聞稿也是轉述"
    assert publisher_lifts(research, ["same_origin", None]), "另一份沒宣告的文件是它自己的資料"
    assert not publisher_lifts(media) and not publisher_lifts(media, [None, "same_origin"])
    assert publisher_lifts(media, ["independent"]) and publisher_lifts(media, [None, "independent"])
    with pytest.raises(ValueError):
        publisher_lifts(resolve_origin("Ayar Labs", reg, publishers=pubs))


# ---------------------------------------------------------------------------
# 2｜設定檔核對：媒體不得整類升級（變異：media corroborates=true → 紅）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entry, message", [
    ({"origin": "Reuters", "kind": "media", "corroborates": True, "seen_in": "d"}, "媒體不得整類升級"),
    ({"origin": "TrendForce", "kind": "industry_research", "corroborates": False, "seen_in": "d"}, "一律是 True"),
    ({"origin": "TrendForce", "kind": "industry_research", "seen_in": "d"}, "corroborates=None"),
    ({"origin": "Some Think Tank", "kind": "think_tank", "corroborates": True, "seen_in": "d"}, "封閉字彙"),
    ({"origin": "Reuters (轉載)", "kind": "media", "corroborates": False, "seen_in": "d"}, "尾端註解"),
    ({"origin": "  ", "kind": "media", "corroborates": False, "seen_in": "d"}, "空的"),
    ({"origin": "Reuters", "kind": "media", "corroborates": False}, "seen_in"),
])
def test_bad_publisher_entries_fail_closed(tmp_path, entry, message) -> None:
    with pytest.raises(PublisherConfigError, match=message):
        load_publishers(_write_publishers(tmp_path, [entry]))


def test_duplicate_origin_and_drifted_kinds_section_fail_closed(tmp_path) -> None:
    twice = [{"origin": "Reuters", "kind": "media", "corroborates": False, "seen_in": "a"},
             {"origin": "reuters", "kind": "media", "corroborates": False, "seen_in": "b"}]
    with pytest.raises(PublisherConfigError, match="重複"):
        load_publishers(_write_publishers(tmp_path, twice))
    drifted = {k: {"corroborates": v} for k, v in PUBLISHER_KINDS.items()}
    drifted["media"] = {"corroborates": True}
    with pytest.raises(PublisherConfigError, match="kinds"):
        load_publishers(_write_publishers(tmp_path, [], kinds=drifted))


def test_real_config_loads_and_media_never_corroborates() -> None:
    data = json.loads((ROOT / "config" / "publishers.json").read_text(encoding="utf-8"))
    load_publishers()   # 正式設定必須通過核對（把任何一筆媒體改成 true，這裡就紅）
    for entry in data["publishers"]:
        assert entry["corroborates"] is PUBLISHER_KINDS[entry["kind"]], entry["origin"]
    assert {e["kind"] for e in data["publishers"] if not e["corroborates"]} == {"media"}


def test_registered_media_origin_stays_a_relay_on_the_real_config() -> None:
    """真設定上的 Reuters（InP 基板層那兩條邊的來源之一）：沒宣告 independent 就是媒體轉述，不升級（plan §9 第 1 項）。"""
    from identity.registry import get_registry

    reg = get_registry()
    assert classify_evidence("co:sumitomo_electric", ["Reuters"], reg) == "media_relay"
    assert classify_evidence("co:sumitomo_electric", ["Reuters"], reg,
                             origin_linkages={"Reuters": {"independent"}}) == "externally_corroborated"
    assert classify_evidence("co:sumitomo_electric", ["Global Semi Research"], reg) == "externally_corroborated"


# ---------------------------------------------------------------------------
# 3｜邊的證據等級
# ---------------------------------------------------------------------------

def test_classify_evidence_uses_the_publisher_registry(tmp_path) -> None:
    reg, pubs = _Registry(), _pubs(tmp_path)
    s = "co:sivers_semiconductors"
    assert classify_evidence(s, ["TrendForce"], reg, publishers=pubs) == "externally_corroborated"
    assert classify_evidence(s, ["TrendForce"], reg, publishers=pubs,
                             origin_linkages={"TrendForce": {"same_origin"}}) == "media_relay"
    assert classify_evidence(s, ["Reuters"], reg, publishers=pubs) == "media_relay"
    assert classify_evidence(s, ["Reuters"], reg, publishers=pubs,
                             origin_linkages={"Reuters": {"independent"}}) == "externally_corroborated"
    assert classify_evidence(s, ["Reuters"], reg, publishers=pubs,
                             origin_linkages={"Reuters": {"same_origin"}}) == "media_relay"
    # 自報·filing（rank 2）仍高於媒體轉述（rank 1）
    assert classify_evidence(s, ["Sivers", "Reuters"], reg, publishers=pubs,
                             filing_origins={"Sivers"}) == "self_reported_costly"


def test_unknown_origin_wins_the_tie_with_a_media_relay_regardless_of_order(tmp_path) -> None:
    """同級（rank 1）時印待判定：還有一個沒認出來的來源，它仍可能是獨立第三方。結果不得隨迭代順序翻。"""
    reg, pubs = _Registry(), _pubs(tmp_path)
    for origins in (["Reuters", "Some Blog"], ["Some Blog", "Reuters"], ["Zeta Blog", "Reuters"]):
        assert classify_evidence("co:coherent", origins, reg, publishers=pubs) == "needs_review", origins


def test_joint_detection_reads_the_origin_without_its_annotation(tmp_path) -> None:
    """註解是研究者寫的脈絡，不是發布者身分：「某部落格（轉述 Sivers 與 Ayar Labs）」不是聯合公告（R2-b 轉來）。"""
    reg, pubs = _Registry(), _pubs(tmp_path)
    assert classify_evidence("co:sivers_semiconductors", ["Some Blog（轉述 Sivers 與 Ayar Labs）"], reg,
                             publishers=pubs) == "needs_review"
    assert classify_evidence("co:sivers_semiconductors", ["Sivers / Ayar Labs (joint announcement)"], reg,
                             publishers=pubs) == "counterparty_joint"


def test_collapse_keeps_each_documents_linkage_per_origin() -> None:
    rows = [{"src": "co:a", "relation": "supplies_to", "dst": "tech:x", "confidence": 0.5, "attributes": "{}",
             "origin": "Reuters", "origin_linkage": linkage, "source_doc_id": doc}
            for doc, linkage in (("d1", "independent"), ("d2", None), ("d3", "same_origin"))]
    edge = collapse_assertions(rows)[("co:a", "supplies_to", "tech:x")]
    assert edge.origin_linkages == {"Reuters": {"independent", None, "same_origin"}}


# ---------------------------------------------------------------------------
# 4｜五張表
# ---------------------------------------------------------------------------

def test_every_evidence_table_has_the_same_keys_and_media_relay_sits_with_needs_review() -> None:
    from alpha.evidence_quality import EVIDENCE_CLASS_TO_LEVEL
    from alpha.narrative.argument import EVIDENCE_CLASS_PLAIN, WEAK_CLASSES
    from alpha.providers.graph_neo4j import _EVIDENCE_CLASS_TIER
    from query.graph_walk import CORROBORATED_EVIDENCE

    keys = set(EVIDENCE_RANK)
    for name, table in (("EVIDENCE_LABEL", EVIDENCE_LABEL), ("EVIDENCE_CLASS_PLAIN", EVIDENCE_CLASS_PLAIN),
                        ("EVIDENCE_CLASS_TO_LEVEL", EVIDENCE_CLASS_TO_LEVEL),
                        ("_EVIDENCE_CLASS_TIER", _EVIDENCE_CLASS_TIER)):
        assert set(table) == keys, name
    for table in (EVIDENCE_RANK, EVIDENCE_CLASS_TO_LEVEL, _EVIDENCE_CLASS_TIER):
        assert table["media_relay"] == table["needs_review"], "同級：只拆兩義，不是升降級"
    assert CORROBORATED_EVIDENCE <= keys and "media_relay" not in CORROBORATED_EVIDENCE
    assert WEAK_CLASSES == {k for k, r in EVIDENCE_RANK.items() if r <= EVIDENCE_RANK["needs_review"]}


# ---------------------------------------------------------------------------
# 3'｜同一個 origin，邊的等級與讀圖引用核對結論相同
# ---------------------------------------------------------------------------

LAYER = "tech:cw_dfb_laser"
SUPPLIER = "co:sivers_semiconductors"
DEMAND_Q = "Every 1.6T transceiver needs a continuous-wave DFB laser as its light source"
SUPPLY_Q = "Sivers ships continuous-wave DFB laser arrays to transceiver makers in volume"


def _layer_record(origin_doc: str):
    from alpha.structure_reading.contracts import structure_reading_record

    structure = {"node": LAYER, "result_digest": "e" * 64, "anchor_chain": None, "angles": {
        "demand_side": [{"src": "tech:transceiver_1_6t", "relation": "depends_on", "dst": LAYER,
                         "substitutability": 5, "sole_source": None, "qualification_status": None,
                         "evidence": "needs_review", "documents": 1}],
        "supply_side": [{"src": SUPPLIER, "relation": "supplies_to", "dst": LAYER, "substitutability": None,
                         "sole_source": None, "qualification_status": None, "evidence": "needs_review",
                         "documents": 1}],
        "next_layer": [], "counter_path": []}}
    citations = [
        {"angle": "demand_side", "edge": ["tech:transceiver_1_6t", "depends_on", LAYER], "quote": DEMAND_Q,
         "source_id": "doc_demand", "independent": False},
        {"angle": "supply_side", "edge": [SUPPLIER, "supplies_to", LAYER], "quote": SUPPLY_Q,
         "source_id": origin_doc, "independent": True},
    ]
    disproof = [{"condition": "任一 1.6T 光模組廠在正式文件宣布改用不需要 CW DFB 雷射的光源並量產",
                 "entities": [SUPPLIER], "check_frequency": "每季", "action_48h": "重讀這一層", "source": "self"}]
    return structure_reading_record(
        node=LAYER, structure=structure, unit="layer", kind="moat",
        reading="一致性測試：同一個 origin，邊的等級與引用核對要給同一個答案。",
        expires=date(2026, 12, 24), created_at=datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc), author="test",
        citations=citations, disproof=disproof)


@pytest.mark.parametrize("origin, linkage", [
    ("Ayar Labs", None),                       # 名冊公司、不是主詞
    ("Sivers Semiconductors AB", None),        # 主詞自己
    ("TrendForce", None),                      # 自產資料的發布者
    ("TrendForce", "same_origin"),             # …宣告為轉述
    ("Reuters", None),                         # 媒體、沒宣告
    ("Reuters", "independent"),                # 媒體、宣告自己採訪
    ("Reuters", "same_origin"),                # 媒體、宣告轉述
    ("Reuters（轉載 Coherent 新聞稿）", None),   # 帶註解
    ("Some Blog", None),                       # 解析不到
])
def test_edge_class_and_citation_check_agree_on_the_same_origin(tmp_path, origin, linkage) -> None:
    from alpha.providers.structure_readings import verify_citations

    reg, pubs = _Registry(), _pubs(tmp_path)
    quotes = {
        ("tech:transceiver_1_6t", "depends_on", LAYER): [
            {"quote": DEMAND_Q, "doc": "doc_demand", "origin": "Ayar Labs", "origin_linkage": None}],
        (SUPPLIER, "supplies_to", LAYER): [
            {"quote": SUPPLY_Q, "doc": "doc_x", "origin": origin, "origin_linkage": linkage}],
    }
    problems = verify_citations(_layer_record("doc_x"), quotes, registry=reg, publishers=pubs)
    citation_ok = not any("independent" in p for p in problems)
    edge_class = classify_evidence(SUPPLIER, [origin], reg, publishers=pubs,
                                   origin_linkages={origin: {linkage}})
    assert citation_ok == (edge_class == "externally_corroborated"), (origin, linkage, edge_class, problems)


# ---------------------------------------------------------------------------
# 插槽視角：算印證的發布者是「可解析第三方」，媒體轉述不是
# ---------------------------------------------------------------------------

def test_socket_view_lists_a_corroborating_publisher_but_not_a_media_relay(tmp_path) -> None:
    from query.bottleneck import CanonicalEdge
    from query.structure import SOCKET_NO_CUSTOMER_QUOTE, build_socket_view, render_socket_markdown

    reg, pubs = _Registry(), _pubs(tmp_path)
    socket = "prod:supernova"
    edges = [CanonicalEdge(src=SUPPLIER, relation="supplies_to", dst=socket)]
    research = {(SUPPLIER, "supplies_to", socket): [
        {"quote": "Sivers is the laser array supplier for SuperNova", "doc": "tf_note", "tier": 3,
         "origin": "TrendForce", "origin_linkage": None}]}
    view = build_socket_view(socket, edges, research, registry=reg, publishers=pubs)
    assert [(q["company"], q["publisher"]) for q in view.customer_quotes] == [(None, "TrendForce")]
    assert "第三方 TrendForce" in render_socket_markdown(view)

    relay = {(SUPPLIER, "supplies_to", socket): [
        {"quote": "Sivers is the laser array supplier for SuperNova", "doc": "reuters_story", "tier": 3,
         "origin": "Reuters", "origin_linkage": None}]}
    view = build_socket_view(socket, edges, relay, registry=reg, publishers=pubs)
    assert view.customer_quotes == [] and view.customer_absence == SOCKET_NO_CUSTOMER_QUOTE
    assert "｜媒體轉述" in render_socket_markdown(view)


# ---------------------------------------------------------------------------
# 手動 L8 稽核：逐個 origin 走同一個 owner
# ---------------------------------------------------------------------------

def test_sole_source_audit_sorts_origins_with_the_same_owner(monkeypatch, tmp_path) -> None:
    import query.origin_resolution as owner
    from scripts.audit_sole_source_independence import _sort_origins

    monkeypatch.setattr(owner, "get_publishers", lambda: _pubs(tmp_path))
    groups = _sort_origins({"Sivers": {None}, "TrendForce": {None}, "Reuters": {None}, "Some Blog": {None},
                            "Ayar Labs": {None}}, SUPPLIER, _Registry())
    assert groups == {"external": ["co:ayar_labs", "TrendForce"], "relay": ["Reuters"],
                      "unresolved": ["Some Blog"], "self": ["Sivers"]}


# ---------------------------------------------------------------------------
# 5｜登記清單本身
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _library_origins_by_doc() -> dict[str, set[str]]:
    """本 checkout 的抽取檔：doc_id → 去註解、casefold 後的 origin 集合（同一個 doc_id 可能有 base＋addendum 多份檔）。"""
    out: dict[str, set[str]] = {}
    for path in sorted((ROOT / "extractions").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        source_doc = (doc.get("source_doc") or {}) if isinstance(doc, dict) else {}
        if source_doc.get("doc_id") and source_doc.get("origin_entity"):
            out.setdefault(str(source_doc["doc_id"]), set()).add(
                _strip_annotation(str(source_doc["origin_entity"])).casefold())
    return out


@pytest.mark.parametrize("publisher", sorted(get_publishers().by_key.values(), key=lambda p: p.origin),
                         ids=lambda p: p.origin)
def test_every_registration_spells_the_origin_of_the_document_it_came_from(publisher) -> None:
    """打錯字的登記永遠比不到（死設定、而且是靜默的：那幾條邊會一直待判定）。`seen_in` 指的那份抽取檔的 origin
    去註解後必須就是登記的字串。⚠ 有 10 份抽取檔刻意不進 Git（私有來源，`.gitignore`）：不在這個 checkout 的就 skip，
    skip 數印在 pytest 摘要裡，不靜默略過。"""
    library = _library_origins_by_doc()
    if publisher.seen_in not in library:
        pytest.skip(f"{publisher.seen_in} 的抽取檔不在這個 checkout（私有檔刻意不進 Git）")
    assert publisher.origin.casefold() in library[publisher.seen_in], (
        f"{publisher.origin}：seen_in={publisher.seen_in} 那份的 origin 是 {sorted(library[publisher.seen_in])}")


def test_no_registered_publisher_is_shadowed_by_a_registry_company() -> None:
    """名冊公司優先：被它遮住的登記永遠用不到；那個 origin 是公司自己的文件，不是發布者。"""
    from identity.registry import get_registry
    from query.bottleneck import company_id_for_origin

    reg = get_registry()
    shadowed = [p.origin for p in get_publishers().by_key.values() if company_id_for_origin(p.origin, reg)]
    assert shadowed == []
