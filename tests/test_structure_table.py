"""結構表（`query/bottleneck.py::structure_table`）：鎖住 2026-08-18 起實際踩過的缺陷。

⚠ 2026-09-23（Phase 0 Step 0b.3）：本檔原名 `test_bottleneck_ranking.py`，守的是 `rank_bottlenecks()`。
排序、兩份序、門檻與產業分組退役後，守排序鍵／門檻／落差註記的 5 條隨機制退役；其餘判準一字未改，
只是主詞換成結構表——去重不放大、屬性逐條取最佳、需求鏈方向、證據分級、母體定義的 INV-3 計數、anchor gap 診斷。
新增 3 條守退役後的形狀：沒有門檻、順序是索引不是名次、markdown 沒有名次欄與首選。
每個 test 對應一個**跑出來才發現**的缺陷，不是假想的。
"""
from __future__ import annotations

import json

from query.bottleneck import (
    DEMAND_ANCHORS,
    build_upward_index,
    classify_evidence,
    collapse_assertions,
    demand_chain,
    is_entity_id,
    structure_table,
)


class _FakeRegistry:
    """只實作 bottleneck.py 用到的 registry surface。

    ⚠ 公司物件的形狀必須與真的 `CompanyIdentity` 一致：只有 `display_name` 與 `aliases`，
    **沒有 `name`**。2026-09-16 事發：這裡曾給假公司一個 `name` 欄位，解析器就照著讀
    `name`——測試全綠，production 100 家 0 家解析得到（L17：機制只認得當初那個案例）。
    """

    class _C:
        def __init__(self, cid, display_name, ticker):
            self.company_id, self.display_name, self.research_ticker_ = cid, display_name, ticker
            self.aliases = ()

    def __init__(self):
        self._c = [
            self._C("co:axt", "AXT", "AXTI"),
            self._C("co:coherent", "Coherent", "COHR"),
            self._C("co:nvidia", "NVIDIA", "NVDA"),
        ]

    @property
    def companies(self):
        return tuple(self._c)

    def company_id_for_ticker(self, ticker):
        for c in self._c:
            if c.research_ticker_ == ticker.strip().upper():
                return c.company_id
        return None

    def has_company(self, cid):
        return any(c.company_id == cid for c in self._c)

    def research_ticker(self, cid):
        for c in self._c:
            if c.company_id == cid:
                return c.research_ticker_
        return None


def _row(src, rel, dst, *, conf, attrs=None, origin=None):
    return {
        "src": src,
        "relation": rel,
        "dst": dst,
        "confidence": conf,
        "attributes": json.dumps(attrs or {}),
        "origin": origin,
    }


def test_same_edge_from_many_documents_collapses_and_does_not_inflate_score() -> None:
    """排名分數不得是「我們讀了幾份文件」的函數。

    實測：`co:axt → mat:inp_substrate` 有 4 條 EdgeAssertion 來自 4 份文件。
    若數邊，再 ingest 五份 InP 報導分數就會上升，而世界沒有任何改變。
    """
    rows = [
        _row("co:axt", "supplies_to", "co:coherent", conf=0.5,
             attrs={"substitutability": 4}, origin=f"Doc{i}")
        for i in range(4)
    ]
    canonical = collapse_assertions(rows)
    assert len(canonical) == 1
    edge = next(iter(canonical.values()))
    assert edge.documents == 4          # 份數保留，作注意力指標
    assert edge.substitutability == 4   # 但值不累加、不放大


def test_attribute_survives_when_top_confidence_assertion_omits_it() -> None:
    """逐屬性取最佳 confidence，不是整條邊只看一份 assertion。

    首版對整條邊只取「confidence 最高那份」的全部屬性，於是若該份沒填
    `substitutability`，整條邊的值就被丟掉——**co:axt 因此整個從排名消失**，
    覆蓋率也從 22% 假掉到 16%。
    """
    rows = [
        # 最高 confidence 的那份沒有 substitutability
        _row("co:axt", "supplies_to", "co:coherent", conf=0.9,
             attrs={"qualification_status": "qualified"}),
        _row("co:axt", "supplies_to", "co:coherent", conf=0.5,
             attrs={"substitutability": 4}),
    ]
    edge = next(iter(collapse_assertions(rows).values()))
    assert edge.substitutability == 4, "低 confidence 但唯一有值的那份不得被丟掉"
    assert edge.qualification_status == "qualified"


def test_demand_chain_returns_none_instead_of_a_nearest_node_fallback() -> None:
    """走不到需求錨點就回 None——不得用「最接近的節點」充數。

    首版用「往上走最長路徑、端點即錨點」，在有環的圖上會繞回目標本身，
    產出看起來結構化但無意義。依使用者判準，連不到有人花錢的地方的瓶頸
    不該被當投資標的看待，所以這裡必須誠實回 None。
    """
    edges = list(
        collapse_assertions(
            [
                _row("co:axt", "supplies_to", "co:coherent", conf=0.5),
                _row("co:coherent", "supplies_to", "tech:cpo", conf=0.5),
                _row("tech:cpo", "is_component_of", "tech:ai_switch", conf=0.5),
                # 與需求端完全無關的一條
                _row("co:orphan", "supplies_to", "mat:nothing", conf=0.5),
            ]
        ).values()
    )
    upward = build_upward_index(edges)

    assert "tech:ai_switch" in DEMAND_ANCHORS
    chain = demand_chain("co:axt", upward)
    assert chain == ["tech:ai_switch", "tech:cpo", "co:coherent", "co:axt"]
    assert demand_chain("co:orphan", upward) is None


def test_supplies_to_carries_demand_upward() -> None:
    """`A supplies_to B` ⇒ B 需要 A，需求要能沿著它往上傳。

    首版的向上索引漏了 `supplies_to`，於是任何「瓶頸目標是一家公司」的列都
    走不到需求錨點——實測 co:axt 顯示「無錨點」，但鏈其實是通的。
    """
    edges = list(
        collapse_assertions(
            [
                _row("co:coherent", "supplies_to", "tech:ai_switch", conf=0.5),
            ]
        ).values()
    )
    assert demand_chain("co:coherent", build_upward_index(edges)) == [
        "tech:ai_switch",
        "co:coherent",
    ]


def test_constrained_by_carries_demand_upward_in_the_depends_on_direction() -> None:
    """`A constrained_by B` ⇒ B 被 A 需要，方向與 `depends_on` 同。

    事發（2026-09-18）：向上索引只認 `depends_on`，於是
    `tech:cpo --constrained_by--> tech:cpo_full_stack_test` 這條**圖裡已經有的邊**
    走不到需求錨——Aehr 那一列因此被當成「走不到有人花錢的地方」。
    當時 ROADMAP 的提案是「把 `constrained_by` 加進 `UPSTREAM_RELATIONS`」，
    而那個方向是反的；本測試鎖的是**方向**，不只是「有沒有被走訪」。
    """
    edges = list(
        collapse_assertions(
            [
                _row("co:aehr", "supplies_to", "tech:cpo_full_stack_test", conf=0.5),
                _row("tech:cpo", "constrained_by", "tech:cpo_full_stack_test", conf=0.5),
                _row("tech:cpo", "is_component_of", "tech:ai_switch", conf=0.5),
            ]
        ).values()
    )
    upward = build_upward_index(edges)

    # dst → src：測試層是誰在需要它 ＝ CPO。反過來寫會讓下面那條鏈走不通。
    assert upward["tech:cpo_full_stack_test"] == {"tech:cpo"}
    assert "tech:cpo_full_stack_test" not in upward.get("tech:cpo", set())
    assert demand_chain("co:aehr", upward) == [
        "tech:ai_switch",
        "tech:cpo",
        "tech:cpo_full_stack_test",
        "co:aehr",
    ]


def test_dependency_relations_stay_consistent_with_the_other_two_direction_tables() -> None:
    """方向表之間的三條不變式——下次新增 relation 時漏掉一邊，這裡要先紅。

    ①「src 需要 dst」必然蘊含「dst 是 src 的向下瓶頸」，所以
    `DEPENDENCY_RELATIONS` ⊆ `DOWNSTREAM_RELATIONS`；
    ② 同一個 relation 不得同時列進兩個方向相反的表（那就是 L12 一表兩義）；
    ③ `schema/vocab.json` 的 `sole_source_beneficiary_end` 是獨立的第三份登記處，
    它對這一族的答案必須也是 `dst`——三份不一致時，先問哪一份錯了，不要各自改。
    """
    import json as _json
    from pathlib import Path as _Path

    from query.bottleneck import (
        DEPENDENCY_RELATIONS,
        DOWNSTREAM_RELATIONS,
        UPSTREAM_RELATIONS,
    )

    assert set(DEPENDENCY_RELATIONS) <= set(DOWNSTREAM_RELATIONS)
    assert not set(DEPENDENCY_RELATIONS) & set(UPSTREAM_RELATIONS)

    vocab = _json.loads(
        (_Path(__file__).resolve().parent.parent / "schema" / "vocab.json").read_text(
            encoding="utf-8"
        )
    )
    beneficiary = vocab["sole_source_beneficiary_end"]
    for relation in DEPENDENCY_RELATIONS:
        assert beneficiary.get(relation) == "dst", relation


def test_evidence_is_three_way_and_unresolved_origin_does_not_auto_pass() -> None:
    """`None` 同時是「真第三方」與「沒解析出的別名」，不得壓成布林（L12）。"""
    reg = _FakeRegistry()
    assert classify_evidence("co:coherent", ["Coherent"], reg) == "self_reported"
    assert (
        classify_evidence("co:coherent", ["Coherent", "NVIDIA"], reg)
        == "externally_corroborated"
    )
    # 唯一的非本人 origin 無法解析 → 待人工判定，不得自動當成外部佐證
    assert (
        classify_evidence("co:coherent", ["Coherent", "The Next Platform"], reg)
        == "needs_review"
    )


def test_claim_nodes_are_excluded_from_the_table() -> None:
    """188 個 Claim 節點貼著 `:Entity` 標籤；真 Entity 一律有 `前綴:slug`。

    Claim 在 `collapse_assertions` 就不成為 canonical edge（它不是 Entity），所以它不進母體計數；
    「是 Entity 但不是公司」的排除（`not_company_source`）由母體報告那條測試守。"""
    assert is_entity_id("co:axt")
    assert not is_entity_id("axti_10_k_20260317_cl1")

    result = structure_table(
        [
            _row("axti_10_k_20260317_cl1", "supplies_to", "co:coherent", conf=0.9,
                 attrs={"substitutability": 5}),
            _row("co:axt", "supplies_to", "co:coherent", conf=0.5,
                 attrs={"substitutability": 4}),
        ],
        _FakeRegistry(),
    )
    assert [r["company_id"] for r in result["rows"]] == ["co:axt"]
    assert result["coverage"]["canonical_edges"] == 1 and result["population"]["input"] == 1


def test_coverage_limits_are_always_reported() -> None:
    """已知限制必須隨輸出常駐，不得只寫在文件裡（L14）。"""
    result = structure_table(
        [_row("co:axt", "supplies_to", "co:coherent", conf=0.5,
              attrs={"substitutability": 4})],
        _FakeRegistry(),
    )
    cov = result["coverage"]
    for key in (
        "substitutability_coverage",
        "self_reported_share",
        "edges_with_lead_time",
        "duplicate_collapse",
    ):
        assert key in cov


def test_table_order_is_an_index_not_a_signal() -> None:
    """列的順序是 `(company_id, relation, bottleneck)` 字典序——**沒有任何一格參與**。

    ⚠ 2026-09-23（Step 0b.3）：這裡原本守「純結構排序與可行動排序分離」（2026-08-21 使用者指出
    研究筆數多→證據強≠瓶頸性強）。兩份序都退役後，那個坑的新形狀是「第一列被讀成第一名」，
    所以這條反過來鎖：把 sub、證據、sole_source 全部反轉，順序一格都不動。
    """

    class _Reg:
        def research_ticker(self, company_id):
            return {"co:a": "AAA", "co:b": "BBB"}.get(company_id)

    strong_b = {"src": "co:b", "relation": "supplies_to", "dst": "tech:ai_switch",
                "substitutability": 5, "sole_source": True, "qualification_status": "designed_in",
                "confidence": 0.8, "origin_entity": "co:b", "doc_id": "d1"}
    weak_a = {"src": "co:a", "relation": "supplies_to", "dst": "co:b",
              "substitutability": 2, "sole_source": False, "qualification_status": "sampling",
              "confidence": 0.8, "origin_entity": "third_party", "doc_id": "d2"}
    forward = structure_table([strong_b, weak_a], _Reg())
    flipped = structure_table([dict(weak_a, substitutability=5, sole_source=True),
                               dict(strong_b, substitutability=2, sole_source=False)], _Reg())
    assert [r["company_id"] for r in forward["rows"]] == ["co:a", "co:b"]
    assert [r["company_id"] for r in flipped["rows"]] == ["co:a", "co:b"]
    assert "structural_rows" not in forward and "filter" not in forward


def test_evidence_five_level_costly_and_joint() -> None:
    """[270] 五級分級：filing 自報升 costly、聯合公告複合 origin 升 counterparty_joint。

    設計動機（2026-08-30 使用者定案）：三級制過度懲罰自報——已收預付款／審計客戶%
    這類金流事實與敘述性自報不同級；聯合公告先前整級掉到 needs_review。
    """
    reg = _FakeRegistry()
    # 自報＋出自 filing → costly
    assert (
        classify_evidence(
            "co:coherent", ["Coherent"], reg, filing_origins={"Coherent"}
        )
        == "self_reported_costly"
    )
    # 自報＋非 filing 維持最低級
    assert classify_evidence("co:coherent", ["Coherent"], reg) == "self_reported"
    # 聯合公告：單串含 subject 與另一家 registry 公司 → counterparty_joint
    assert (
        classify_evidence(
            "co:coherent", ["Coherent / NVIDIA (joint announcement)"], reg
        )
        == "counterparty_joint"
    )
    # 外部印證仍最高：同時有他公司單獨 origin 時勝過 joint 與 costly
    assert (
        classify_evidence(
            "co:coherent",
            ["NVIDIA", "Coherent / NVIDIA (joint announcement)"],
            reg,
            filing_origins={"Coherent"},
        )
        == "externally_corroborated"
    )


def test_presentation_text_has_one_home_and_the_markdown_prints_it() -> None:
    """限制文字、表的註記與順序說明只有一份（L16）：markdown 從常數印，
    APP artifact（`webapp/materialize.py`）從同一批常數拿。抄第二份的那天起，後改的那份
    不會回頭更新前一份。"""
    from query.bottleneck import (
        ORDER_NOTE, STRUCTURE_TABLE_NOTE, STRUCTURE_TABLE_TITLE, known_limitations,
        render_markdown, structure_table,
    )

    rows = [
        _row("co:coherent", "supplies_to", "co:nvidia", conf=0.9,
             attrs={"substitutability": 5, "sole_source": True}, origin="NVIDIA"),
        _row("co:nvidia", "supplies_to", "tech:ai_switch", conf=0.9, origin="NVIDIA"),
        _row("co:axt", "supplies_to", "co:coherent", conf=0.8,
             attrs={"substitutability": 4}, origin="AXT"),
    ]
    result = structure_table(rows, _FakeRegistry())
    md = render_markdown(result)
    assert STRUCTURE_TABLE_TITLE in md
    for text in known_limitations(result["coverage"]):
        assert text in md
    assert STRUCTURE_TABLE_NOTE in md
    assert ORDER_NOTE in md


def test_render_markdown_has_no_rank_column_and_no_top_pick() -> None:
    """退役後的形狀：表頭沒有 `#`、沒有首選、沒有兩份序；母體報告有印（INV-3 的可見面）。"""
    from query.bottleneck import render_markdown

    rows = [
        _row("co:axt", "supplies_to", "co:nvidia", conf=0.9, attrs={"substitutability": 4}, origin="AXT"),
        _row("co:nvidia", "supplies_to", "tech:ai_switch", conf=0.9, origin="NVIDIA"),
        _row("co:coherent", "supplies_to", "mat:nowhere", conf=0.9,
             attrs={"substitutability": 5, "sole_source": True}, origin="NVIDIA"),
    ]
    md = render_markdown(structure_table(rows, _FakeRegistry()))
    body = md.split(chr(10), 1)[1]                 # 標題那一句「不給首選」是禁止句，不算
    assert "| # |" not in body
    for banned in ("首選", "可行動排序", "純結構排序", "排序鍵", "現在要投"):
        assert banned not in body, banned
    assert "母體定義排除了誰（INV-3）" in md
    assert "input 3｜accepted 3｜excluded 0" in md
    # 走不到錨的列在表上（不是被濾掉），且讀法跟著印
    assert "co:coherent（COHR）" in md and "🔴 無" in md and "無需求錨列的讀法" in md


class _NamedRegistry(_FakeRegistry):
    """登記名稱是財報封面印的法律名稱（真 registry 的樣子），不是短名。"""

    def __init__(self):
        self._c = [
            self._C("co:iqe", "IQE plc", "IQE.L"),
            self._C("co:tower_semiconductor", "Tower Semiconductor Ltd.", "TSEM"),
            self._C("co:coherent", "Coherent Corp.", "COHR"),
            self._C("co:schaeffler", "Schaeffler AG", "SHA0.DE"),
            self._C("co:macom", "MACOM Technology Solutions Holdings, Inc.", "MTSI"),
        ]


def test_origin_resolution_reads_the_registry_field_that_exists() -> None:
    """2026-09-16 事發：解析讀 `name`，而 `CompanyIdentity` 只有 `display_name`——100 家 0 家
    解析得到，IQE 的自家年報被當成解析不到的第三方。法律型態尾綴與尾端括號註解只是格式。"""
    from query.bottleneck import company_id_for_origin

    reg = _NamedRegistry()
    assert company_id_for_origin("Tower Semiconductor Ltd.", reg) == "co:tower_semiconductor"
    assert company_id_for_origin("Tower Semiconductor", reg) == "co:tower_semiconductor"
    assert company_id_for_origin("MACOM Technology Solutions", reg) == "co:macom"
    assert company_id_for_origin("MACOM Technology Solutions Inc.", reg) == "co:macom"
    assert company_id_for_origin("Coherent（發行人官方新聞稿）", reg) == "co:coherent"
    assert classify_evidence("co:coherent", ["Coherent（發行人官方新聞稿）"], reg) == "self_reported"
    assert (
        classify_evidence(
            "co:coherent", ["Coherent（發行人官方新聞稿）"], reg,
            filing_origins={"Coherent（發行人官方新聞稿）"},
        )
        == "self_reported_costly"
    )


def test_joint_announcement_is_detected_through_core_names() -> None:
    """IQE×Tower 聯合公告的 origin 不會逐字印 `Tower Semiconductor Ltd.`；核心名稱要算具名。"""
    reg = _NamedRegistry()
    assert (
        classify_evidence("co:iqe", ["IQE plc / Tower Semiconductor (joint announcement)"], reg)
        == "counterparty_joint"
    )
    # 解析得到主詞、但同一字串另具名他家 → 仍是聯合，不得因為「解析成功」就降成自報
    assert (
        classify_evidence(
            "co:coherent", ["Coherent（官方 PR，內含 Tower Semiconductor 具名引述）"], reg
        )
        == "counterparty_joint"
    )
    # 只具名主詞自己（Hexagon 不在 registry）→ 仍待判定，不得升級
    assert (
        classify_evidence(
            "co:schaeffler", ["Hexagon AB, with named Schaeffler management statements"], reg
        )
        == "needs_review"
    )


def test_ambiguous_core_name_does_not_guess() -> None:
    """兩家的核心名稱相同時（`Foo Inc.`／`Foo Ltd.`），`Foo` 必須回 None——不猜（L15）。"""
    from query.bottleneck import company_id_for_origin

    reg = _FakeRegistry()
    reg._c = [reg._C("co:foo_a", "Foo Inc.", "FOOA"), reg._C("co:foo_b", "Foo Ltd.", "FOOB")]
    assert company_id_for_origin("Foo", reg) is None
    assert classify_evidence("co:foo_a", ["Foo"], reg) == "needs_review"


def test_single_stray_mention_cannot_lift_evidence() -> None:
    """`Coherent Market Insights`（研究機構）含 registry 公司的核心名稱：不得解析成該公司，
    單一具名也不得升級——升級要嘛靠解析到另一家、要嘛靠 ≥2 家具名。"""
    from query.bottleneck import company_id_for_origin

    reg = _NamedRegistry()
    assert company_id_for_origin("Coherent Market Insights", reg) is None
    assert classify_evidence("co:iqe", ["Coherent Market Insights"], reg) == "needs_review"
    assert classify_evidence("co:coherent", ["Coherent Market Insights"], reg) == "needs_review"


# ---------------------------------------------------------------------------
# 母體定義是一個 filter，所以它必須報得出 input／accepted／excluded／reasons（INV-3）
# ---------------------------------------------------------------------------

def _sub_edge(src, dst, sub, relation="supplies_to", **extra):
    row = {
        "src": src, "relation": relation, "dst": dst,
        "attributes": {"substitutability": sub} if sub is not None else {},
        "confidence": 0.8, "origin": "Someone", "source_type": "filing",
        "source_doc_id": f"doc_{src}_{dst}", "published_at": "2026-01-01",
    }
    row["attributes"].update(extra)
    return row


def test_no_threshold_low_and_unfilled_substitutability_stay_on_the_table() -> None:
    """**門檻退役**（2026-09-23）：sub 5、sub 2、未填三條邊都在表上，各自帶著自己的值。

    2026-09-17 之前 sub<4 是靜默 `continue`，之後是帶理由的 `filtered_rows`；兩者都讓
    「不是瓶頸」與「還沒研究」在下游只能靠另一張表分辨。現在它們就在同一張表上：
    `substitutability` 是 2 還是 None，讀的人自己看得到。
    空跑檢查：把 `_table_row` 前面加回 `if (sub or 0) < 4: continue` → 這條會紅。
    """
    rows = [
        _sub_edge("co:axt", "tech:x", 5),
        _sub_edge("co:coherent", "tech:x", 2),
        _sub_edge("co:nvidia", "tech:x", None),
    ]
    result = structure_table(rows, _FakeRegistry())
    by_company = {r["company_id"]: r["substitutability"] for r in result["rows"]}
    assert by_company == {"co:axt": 5, "co:coherent": 2, "co:nvidia": None}
    assert result["population"] == {**result["population"], "input": 3, "accepted": 3, "excluded": 0}
    assert "threshold" not in result["rows"][0]


def test_population_rule_reports_input_accepted_excluded_and_reasons() -> None:
    """**先前這兩種排除是靜默 `continue`**——不是公司的 src、不是向下的 relation。

    空跑檢查：把 `excluded.append(...)` 改回單純 `continue` → 這條會紅。
    """
    rows = [
        _sub_edge("co:axt", "tech:x", 5),                                   # 母體
        _sub_edge("tech:x", "tech:y", 4, relation="is_component_of"),       # 不是向下
        _sub_edge("tech:cpo", "tech:ai_switch", 5),                          # src 不是公司
    ]
    result = structure_table(rows, _FakeRegistry())

    report = result["population"]
    assert report["input"] == 3 and report["accepted"] == 1 and report["excluded"] == 2
    # ⚠ 兩種理由**必須分得開**：一個是關係方向，一個是節點型別（L12）。
    assert report["reasons"] == {"not_downstream_relation": 1, "not_company_source": 1}
    excluded = {(r["company_id"], r["relation"]): r["reasons"][0] for r in report["excluded_rows"]}
    assert excluded == {("tech:x", "is_component_of"): "not_downstream_relation",
                        ("tech:cpo", "supplies_to"): "not_company_source"}
    assert set(report["reasons"]) <= set(report["reason_labels"])
    for key in ("company_id", "relation", "bottleneck", "reasons"):
        assert key in report["excluded_rows"][0], key


def test_anchor_gap_causes_are_separable_and_never_collapse_into_one_reason() -> None:
    """ROADMAP Phase 4 的驗收條件逐字要求「四種成因要分得開（不得壓成一句走不到錨）」。

    事發（2026-09-18 實測）：壓成一句的代價是具體的——pq2 [606] 點名的 6 個 accepted
    瓶頸節點裡，**只有 3 個是真研究缺口**；`tech:ocs` 是 `enables` 走訪方向未解（開發項，
    圖裡已經有兩條 `enables` 指向它），`tech:eml` 與 `prod:ph18da` 是上游斷點。
    對那 3 個去找一手文件是白做的——**而在分類之前，這件事在報表上完全看不出來**。

    本測試鎖三件事：三種成因互斥、合計等於走不到錨的總數、判準各自對得上自己的名字。
    """
    from query.bottleneck import ANCHOR_GAP_CAUSES, classify_anchor_gaps

    edges = list(
        collapse_assertions(
            [
                # 真的沒有需求方邊：只有人供它，沒有人記錄過誰需要它。
                _row("co:axt", "supplies_to", "tech:lonely", conf=0.5),
                # 有人需要它，但那個人自己也走不到錨。
                _row("co:axt", "supplies_to", "tech:deadend", conf=0.5),
                _row("tech:orphan", "depends_on", "tech:deadend", conf=0.5),
                # 對照組：走得到錨的不該進母體。
                _row("co:axt", "supplies_to", "tech:reachable", conf=0.5),
                _row("tech:reachable", "is_component_of", "tech:ai_switch", conf=0.5),
                # 對照組二：有 enables 指向它就有上游——**這一種已經不可能再出現**
                # （2026-09-18 資料歸位＋程式歸位後，`X enables N` ⇒ upward[N] += X）。
                _row("co:axt", "supplies_to", "tech:enabled", conf=0.5),
                _row("tech:ai_switch", "enables", "tech:enabled", conf=0.5),
            ]
        ).values()
    )
    gaps = classify_anchor_gaps(edges, build_upward_index(edges))

    assert gaps["counts"] == {"no_demand_edge": 1, "upstream_dead_end": 1}
    assert gaps["without_anchor"] == 2, "走得到錨的兩個對照組不得被算進來"
    assert sum(gaps["counts"].values()) == gaps["without_anchor"], "成因必須互斥且窮盡"

    where = {n["node"]: cause for cause, v in gaps["nodes"].items() for n in v}
    assert where["tech:lonely"] == "no_demand_edge"
    assert where["tech:deadend"] == "upstream_dead_end"
    assert "tech:reachable" not in where
    assert "tech:enabled" not in where, "有 enables 指向它就走得到上游"

    # 封閉字彙：計數的 key 不得長出字彙以外的值。
    assert set(gaps["counts"]) <= set(ANCHOR_GAP_CAUSES)
    assert set(gaps["nodes"]) <= set(ANCHOR_GAP_CAUSES)


def test_anchor_gap_diagnosis_does_not_touch_the_table() -> None:
    """診斷是**另一段輸出**，不改列上任何一格。

    「瓶頸節點接不接得到錢」與「這家公司的產出有沒有人在花錢買」是兩個問題——
    2026-09-18 實測過把列上的錨改成前者會讓多數列失去錨。本測試鎖住：加了診斷之後，
    列上一個欄位都沒有動。
    """
    from query.bottleneck import classify_anchor_gaps

    rows = [
        _row("co:axt", "supplies_to", "co:coherent", conf=0.9, attrs={"substitutability": 5}),
        _row("co:coherent", "is_component_of", "tech:ai_switch", conf=0.9),
        _row("co:nvidia", "depends_on", "tech:lonely", conf=0.9, attrs={"substitutability": 4}),
    ]
    result = structure_table(rows, _FakeRegistry())

    assert "anchor_gaps" in result
    # 表本身：rows 的每一列都還帶著公司側的錨，診斷沒有把它換成節點側的。
    for row in result["rows"]:
        assert "anchor_gap" not in row, "診斷不得滲進表的列"
    axt = [r for r in result["rows"] if r["company_id"] == "co:axt"]
    assert axt and axt[0]["demand_anchor"] == "tech:ai_switch"

    # 診斷自己算得出東西，但它的母體與表的列無關。
    edges = list(collapse_assertions(rows).values())
    standalone = classify_anchor_gaps(edges, build_upward_index(edges))
    assert standalone["counts"] == result["anchor_gaps"]["counts"]


def test_anchor_gap_section_prints_even_when_nothing_is_missing() -> None:
    """「全部走得到錨」與「這段沒跑」不得同形（L13-2）。

    R1 自查抓到的：條件原本寫 `if without_anchor:`，於是修好全部缺口的那一天，
    整段會安靜消失——而那正好與「查詢壞了」「母體算錯了」長得一模一樣。
    改成以 `population` 判斷，並在零缺口時**明講檢查跑過了**。
    """
    from query.bottleneck import render_markdown

    rows = [
        _row("co:axt", "supplies_to", "co:coherent", conf=0.9, attrs={"substitutability": 5}),
        _row("co:coherent", "is_component_of", "tech:ai_switch", conf=0.9),
    ]
    result = structure_table(rows, _FakeRegistry())
    assert result["anchor_gaps"]["without_anchor"] == 0
    assert result["anchor_gaps"]["population"] > 0

    text = render_markdown(result)
    assert "瓶頸節點走不到需求錨：0／" in text
    assert "每一個瓶頸節點都走得到需求錨" in text

    # 母體真的是 0（沒有任何向下邊）時才可以不印——那時是真的沒東西可算。
    empty = structure_table(
        [_row("co:axt", "is_component_of", "tech:ai_switch", conf=0.9)], _FakeRegistry()
    )
    assert empty["anchor_gaps"]["population"] == 0
    assert "瓶頸節點走不到需求錨" not in render_markdown(empty)


def test_enables_carries_demand_from_the_adopter_to_what_it_pulls_in() -> None:
    """`A enables B` ⇒ **B 被 A 需要**，需求沿 dst → src 上傳。

    抽取 prompt 的逐字定義是 `enables` — **A's adoption drives demand for B**，
    而 2026-09-18 之前 `build_upward_index` 把它放在 `UPSTREAM_RELATIONS`
    （`upward[src].add(dst)` ＝ A 被 B 需要）——**方向相反**。
    圖裡兩種寫法並存，而程式實作了沒寫下來的那一種，於是**兩個錯互相抵銷、長期沒人發現**。

    ⚠ 順序不可換，這條測試守的就是修完之後的那一半：資料先由 pq2 [607]／[608]／[609]
    逐條對來源逐字重判改正（29 條），程式才翻方向。只翻程式不改資料，實測
    `no_demand_edge` 會由 51 打到 67（把「誰需要它」的答案弄丟）。
    """
    from query.bottleneck import DEMAND_PULL_RELATIONS, UPSTREAM_RELATIONS

    assert "enables" in DEMAND_PULL_RELATIONS
    assert "enables" not in UPSTREAM_RELATIONS, "它與 is_component_of 方向相反，不得同表"

    edges = list(
        collapse_assertions([
            _row("tech:ai_switch", "enables", "tech:cpo", conf=0.9),
            _row("co:axt", "supplies_to", "tech:cpo", conf=0.9, attrs={"substitutability": 5}),
        ]).values()
    )
    upward = build_upward_index(edges)
    # dst → src：CPO 被 AI switch 需要（AI switch 的採用把 CPO 的需求拉過來）
    assert upward["tech:cpo"] == {"tech:ai_switch"}
    assert "tech:cpo" not in upward.get("tech:ai_switch", set())
    assert demand_chain("co:axt", upward) == ["tech:ai_switch", "tech:cpo", "co:axt"]
