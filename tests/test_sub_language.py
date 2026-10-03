"""`sub_language_in_quote` 旗標的唯一 owner（`query/sub_language.py`）與字表（Phase 4 Step 4.4a／b）。

守四件事：
1. 字表形狀與版本化：寬窄兩版都存、只用 `active`、改字表要記 `_history`、重複的詞拒收。
2. 比對規則：ASCII 整詞、不分大小寫；中日韓字整串；沒有引文＝False（沒有措辭撐住 sub）。
3. 只印、不放閘：結構表多一格 id 列表與一段總數，沒給旗標時是 None（沒核對 ≠ 0 筆缺，INV-3），其餘格子不動。
4. L19：字表不得出現在 `prompts/`、`skills/`——抽取端讀得到字表，就會挑含這些字的引文，旗標恆亮。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from query.sub_language import (
    LANGUAGE_PATH, LanguageConfigError, SubLanguage, get_language, load_language, matched_terms,
    quote_has_sub_language, sub_language_flags,
)

ROOT = Path(__file__).resolve().parent.parent
LANG = SubLanguage(version=1, variant="test", terms=("second source", "qualified", "sole supplier", "唯一", "替代"))


def _write(tmp_path: Path, **overrides) -> Path:
    data = {"schema_version": 1, "version": 2, "active": "narrow",
            "_history": [{"version": 2, "date": "2026-10-01", "change": "test"}],
            "variants": {"narrow": {"a": ["replace", "唯一"]}, "wide": {"extends": "narrow", "b": ["market share"]}}}
    data.update(overrides)
    path = tmp_path / "lang.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1｜字表
# ---------------------------------------------------------------------------

def test_real_vocabulary_loads_with_both_variants_and_names_the_one_in_use() -> None:
    narrow = get_language()
    wide = load_language(variant="wide")
    assert narrow.label == "v1·narrow" and narrow.variant == "narrow"
    assert set(narrow.terms) < set(wide.terms), "寬版＝窄版＋集中度措辭"
    assert "market share" in wide.terms and "market share" not in narrow.terms


def test_variant_extends_and_versioning_rules(tmp_path) -> None:
    assert load_language(_write(tmp_path), variant="wide").terms == ("replace", "唯一", "market share")
    with pytest.raises(LanguageConfigError, match="_history"):
        load_language(_write(tmp_path, _history=[{"version": 1}]))           # 改了 version 卻沒記一筆
    with pytest.raises(LanguageConfigError, match="重複"):
        load_language(_write(tmp_path, variants={"narrow": {"a": ["Replace", "replace"]}}))
    with pytest.raises(LanguageConfigError, match="成環"):
        load_language(_write(tmp_path, variants={"narrow": {"extends": "wide"}, "wide": {"extends": "narrow"}}))
    with pytest.raises(LanguageConfigError, match="沒有"):
        load_language(_write(tmp_path), variant="nope")


# ---------------------------------------------------------------------------
# 2｜比對
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("quote, expected", [
    ("Customers would need a Second Source qualified over 18 months", True),   # 不分大小寫
    ("AXT is the sole supplier of 6-inch substrates", True),
    ("華星光是唯一量產 CW DFB 的台廠", True),                                     # 中日韓字整串
    ("目前沒有可替代的方案", True),
    ("The company disqualified the bid", False),                               # 整詞：disqualified 不是 qualified
    ("secondsource", False),
    ("Revenue grew 40% on strong AI demand", False),
])
def test_matching_is_whole_word_case_insensitive_and_cjk_substring(quote, expected) -> None:
    assert quote_has_sub_language(quote, language=LANG) is expected


def test_no_quote_is_no_language() -> None:
    assert quote_has_sub_language(None, language=LANG) is False
    assert quote_has_sub_language([], language=LANG) is False
    assert quote_has_sub_language(["", None], language=LANG) is False
    assert matched_terms("a sole supplier and a second source", language=LANG) == ["second source", "sole supplier"]


def test_flags_only_cover_assertions_that_carry_a_sub() -> None:
    rows = [
        {"assertion_id": "a1", "attributes": json.dumps({"substitutability": 4})},
        {"assertion_id": "a2", "attributes": {"substitutability": 5}},
        {"assertion_id": "a3", "attributes": {"qualification_status": "qualified"}},   # 沒有 sub → 不在母體
        {"assertion_id": "a4", "attributes": {"substitutability": True}},              # 布林不是 sub
        {"assertion_id": None, "attributes": {"substitutability": 3}},                # 沒有 id 無從對引文
        {"assertion_id": "a6", "attributes": {"substitutability": 2}},                # 沒有任何逐字
    ]
    quotes = {"a1": ["AXT is the sole supplier"], "a2": ["Revenue grew"]}
    assert sub_language_flags(rows, quotes, language=LANG) == {"a1": True, "a2": False, "a6": False}


# ---------------------------------------------------------------------------
# 3｜只印、不放閘
# ---------------------------------------------------------------------------

class _Registry:
    companies = ()

    def company_id_for_ticker(self, ticker):
        return None

    def has_company(self, cid):
        return False

    def research_ticker(self, cid):
        return None

    def company(self, cid):
        return None


def _rows():
    return [
        {"assertion_id": "e1", "src": "co:a", "relation": "supplies_to", "dst": "mat:x", "confidence": 0.8,
         "attributes": json.dumps({"substitutability": 4}), "origin": "A Corp", "source_doc_id": "d1"},
        {"assertion_id": "e2", "src": "co:a", "relation": "supplies_to", "dst": "mat:x", "confidence": 0.6,
         "attributes": json.dumps({"substitutability": 4}), "origin": "A Corp", "source_doc_id": "d2"},
        {"assertion_id": "e3", "src": "co:b", "relation": "supplies_to", "dst": "mat:x", "confidence": 0.7,
         "attributes": json.dumps({"substitutability": 3}), "origin": "B Corp", "source_doc_id": "d3"},
    ]


def test_structure_table_lists_ids_and_changes_no_other_cell() -> None:
    from query.bottleneck import render_markdown, structure_table

    plain = structure_table(_rows(), _Registry(), quotes_by_assertion={})
    flagged = structure_table(_rows(), _Registry(), quotes_by_assertion={},
                              sub_language_flags={"e1": True, "e2": False, "e3": True}, sub_language_label="v1·test")
    assert plain["sub_language"] is None
    assert all(r["assertions_without_sub_language"] is None for r in plain["rows"])      # 沒核對＝None，不是 []
    by_company = {r["company_id"]: r["assertions_without_sub_language"] for r in flagged["rows"]}
    assert by_company == {"co:a": ["e2"], "co:b": []}
    assert flagged["sub_language"]["checked"] == 3 and flagged["sub_language"]["without"] == 1
    # Phase 6 Step 6.5：canonical 那一格＝贏得 sub 值那一筆的旗標（co:a 的值是 confidence 0.8 的 e1 給的，不是 e2）
    canonical = {r["company_id"]: r["sub_language_in_quote"] for r in flagged["rows"]}
    assert canonical == {"co:a": True, "co:b": True}
    assert all(r["sub_language_in_quote"] is None for r in plain["rows"])                # 沒核對＝None，不是 False
    # 其餘每一格一字不動（只印、不放閘）——兩個旗標格都是同一份旗標的消費端，其餘不得跟著變
    flag_cells = {"assertions_without_sub_language", "sub_language_in_quote"}
    strip = lambda result: [{k: v for k, v in r.items() if k not in flag_cells}  # noqa: E731
                            for r in result["rows"]]
    assert strip(plain) == strip(flagged) and plain["coverage"] == flagged["coverage"]
    md = render_markdown(flagged)
    assert "sub 引文不含可替代性語言：1／3" in md and "`e2`" in md
    assert "未核對" in render_markdown(plain)


# ---------------------------------------------------------------------------
# 4｜L19：字表不得出現在 prompts／skills
# ---------------------------------------------------------------------------

#: 一行裡同時出現幾個**不同**的詞就算「字表被抄進來」。2026-10-01 實測 prompts／skills 每行最多 3 個（docs 最多 4）——
#: 正常的散文會提到幾個詞，抄進來的字表會擠在一行／一段。
PASTED_LIST_MIN_TERMS = 5


def _terms_in(text: str, terms) -> set[str]:
    found = set()
    for term in terms:
        if re.search(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]", term):
            if term in text:
                found.add(term)
        elif re.search(r"(?<![A-Za-z0-9_])" + re.escape(term) + r"(?![A-Za-z0-9_])", text, re.IGNORECASE):
            found.add(term)
    return found


def _agent_facing_files():
    for base in ("prompts", "skills"):
        for path in sorted((ROOT / base).rglob("*")):
            if path.is_file() and path.suffix in (".md", ".txt", ".json", ".py", ".yaml", ".yml"):
                yield path


def test_no_prompt_or_skill_points_at_the_vocabulary_file() -> None:
    offenders = [str(p.relative_to(ROOT)) for p in _agent_facing_files()
                 if LANGUAGE_PATH.stem in p.read_text(encoding="utf-8", errors="replace")]
    assert offenders == [], "抽取端與研究 skill 不得讀得到字表（L19）"


def test_no_prompt_or_skill_line_carries_a_pasted_term_list() -> None:
    terms = load_language(variant="wide").terms
    offenders = []
    for path in _agent_facing_files():
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            found = _terms_in(line, terms)
            if len(found) >= PASTED_LIST_MIN_TERMS:
                offenders.append(f"{path.relative_to(ROOT)}:{number} {sorted(found)}")
    assert offenders == [], offenders


def _sub_extraction(doc_id: str, quotes: dict[str, str]) -> dict:
    """兩條帶 sub 的邊（一條引文談排他性、一條只講出貨）＋一條沒有 sub 的邊（不在母體）。"""
    from test_layer_enumerations import BASIS

    sources = [{"id": f"{doc_id}_{key}", "locator": key, "quote": text} for key, text in quotes.items()]
    nodes = [{"id": n, "type": "Company" if n.startswith("co:") else "Material", "name": n,
              "abstraction_level": "materials_substrate", "confidence": 0.9, "source_ids": [f"{doc_id}_s1"]}
             for n in ("co:axt", "co:sumitomo_electric", "mat:test_layer")]
    edges = [
        {"id": "e1", "src_id": "co:axt", "dst_id": "mat:test_layer", "relation": "supplies_to", "confidence": 0.8,
         "attributes": {"substitutability": 4}, "source_ids": [f"{doc_id}_s1"]},
        {"id": "e2", "src_id": "co:sumitomo_electric", "dst_id": "mat:test_layer", "relation": "supplies_to",
         "confidence": 0.8, "attributes": {"substitutability": 3}, "source_ids": [f"{doc_id}_s2"]},
        {"id": "e3", "src_id": "co:axt", "dst_id": "mat:test_layer", "relation": "supplies_to", "confidence": 0.8,
         "source_ids": [f"{doc_id}_s2"]},
    ]
    return {"schema_version": "0.1",
            "source_doc": {"doc_id": doc_id, "title": "Sub doc", "source_type": "industry_report", "evidence_tier": 3,
                           "origin_entity": "Global Semi Research", "storage_permission": "repo_full",
                           "permission_basis": BASIS, "url": "https://example.com/sub"},
            "sources": sources, "nodes": nodes, "edges": edges, "claims": []}


def test_packet_warns_but_does_not_reject_a_sub_whose_quote_does_not_discuss_replaceability(tmp_path) -> None:
    from intake import actions as research_actions
    from test_layer_enumerations import _payload

    extraction = _sub_extraction("sub_doc", {"s1": "AXT is the sole supplier qualified for 6-inch wafers",
                                             "s2": "Sumitomo shipped more wafers this quarter"})
    record = research_actions.create_action(_payload(extraction, None), root=tmp_path)    # 不拒收
    check = record["sub_language_check"]
    assert [e["edge_id"] for e in check["edges"]] == ["e1", "e2"]                         # 沒有 sub 的 e3 不在母體
    assert [e["has_language"] for e in check["edges"]] == [True, False]
    assert len(check["warnings"]) == 1 and "co:sumitomo_electric" in check["warnings"][0]
    packet = research_actions.render_review_packet(record)
    assert "## sub 引文核對（只警告、不拒收）" in packet and "co:sumitomo_electric" in packet
    assert "## sub 引文核對" in research_actions._full_report(record)                    # 報告與 packet 同一節
    # 沒有帶 sub 的邊 → 不加這一欄（舊形狀的 packet 不變）
    plain = _sub_extraction("plain_doc", {"s1": "x", "s2": "y"})
    for edge in plain["edges"]:
        edge.pop("attributes", None)
    assert "sub_language_check" not in research_actions.create_action(_payload(plain, None), root=tmp_path)


def test_the_pasted_list_detector_itself_fires() -> None:
    """gate 本身也要驗（L14-2）：把字表前幾個詞抄成一行，偵測器必須抓得到。"""
    terms = get_language().terms
    pasted = "、".join(terms[:PASTED_LIST_MIN_TERMS])
    assert len(_terms_in(pasted, terms)) >= PASTED_LIST_MIN_TERMS
