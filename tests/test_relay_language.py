"""轉述字表（`config/relay_language.json`，Phase 6 Step 6.4）：形狀、比對規則、L19 守門。

1. 正式字表讀得到、記名（`label`），版本規則與 sub 字表同一個 loader（`query.sub_language.load_language`）。
2. 比對：ASCII 整詞、不分大小寫；中日韓字整串出現即算。
3. L19：字表不得出現在 `prompts/`、`skills/`——抽取端讀得到字表，就會挑不含這些字的引文，轉述旗標恆滅、
   發布者的轉述句全被當成它自己的數據（plan 不可越線 7）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from query.origin_resolution import RELAY_LANGUAGE_PATH, get_relay_language
from query.sub_language import LanguageConfigError, load_language, matched_terms

ROOT = Path(__file__).resolve().parents[1]


def test_real_relay_vocabulary_loads_and_names_the_version_in_use() -> None:
    relay = get_relay_language()
    assert relay.label == "v1·base"
    assert set(relay.terms) == {"announced", "announces", "said", "says", "stated", "states", "according to",
                                "表示", "宣布"}
    data = json.loads(RELAY_LANGUAGE_PATH.read_text(encoding="utf-8"))
    assert any(h.get("version") == data["version"] for h in data["_history"]), "改字表要在 _history 記一行"


def test_relay_vocabulary_follows_the_same_versioning_rule(tmp_path) -> None:
    """升 version 卻沒記 `_history` → 整份拒收（與 sub 字表同一條規則、同一個 loader）。"""
    data = json.loads(RELAY_LANGUAGE_PATH.read_text(encoding="utf-8"))
    data["version"] = data["version"] + 1
    path = tmp_path / "relay_language.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(LanguageConfigError, match="_history"):
        load_language(path)


@pytest.mark.parametrize("quote, expected", [
    ("Lumentum announced a 1.6T module", ["announced"]),
    ("LUMENTUM SAID IT SHIPPED", ["said"]),
    ("according to the company, volumes doubled", ["according to"]),
    ("華星光表示出貨倍增", ["表示"]),
    ("Coherent's statement on volumes", []),                 # statement 不是 stated／states（整詞）
    ("unannounced", []),                                       # 前綴不算
    ("Lumentum ships EML lasers to NVIDIA", []),
])
def test_relay_matching_is_whole_word_case_insensitive_and_cjk_substring(quote, expected) -> None:
    assert matched_terms(quote, language=get_relay_language()) == expected


# ---------------------------------------------------------------------------
# L19：字表不得出現在 prompts／skills
# ---------------------------------------------------------------------------

#: 一行裡同時出現幾個**不同**的轉述詞就算「字表被抄進來」。2026-10-03 實測 prompts／skills 每行最多 1 個
#: （docs 的 plan 與 baseline 報告各有一行列全表——那是給執行者讀的開發文件，不是抽取端）。字表只有 9 個詞，所以門檻 4。
PASTED_LIST_MIN_TERMS = 4


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


def test_no_prompt_or_skill_points_at_the_relay_vocabulary_file() -> None:
    offenders = [str(p.relative_to(ROOT)) for p in _agent_facing_files()
                 if RELAY_LANGUAGE_PATH.stem in p.read_text(encoding="utf-8", errors="replace")]
    assert offenders == [], "抽取端與研究 skill 不得讀得到轉述字表（L19）"


def test_no_prompt_or_skill_line_carries_a_pasted_relay_term_list() -> None:
    terms = get_relay_language().terms
    offenders = []
    for path in _agent_facing_files():
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            found = _terms_in(line, terms)
            if len(found) >= PASTED_LIST_MIN_TERMS:
                offenders.append(f"{path.relative_to(ROOT)}:{number} {sorted(found)}")
    assert offenders == [], offenders


def test_the_pasted_relay_list_detector_itself_fires() -> None:
    """gate 本身也要驗（L14-2）：把字表前幾個詞抄成一行，偵測器必須抓得到。"""
    terms = get_relay_language().terms
    pasted = "、".join(terms[:PASTED_LIST_MIN_TERMS])
    assert len(_terms_in(pasted, terms)) >= PASTED_LIST_MIN_TERMS
