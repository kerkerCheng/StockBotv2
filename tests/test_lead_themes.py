"""主題字彙比對的迴歸測試（lead 關聯的第二層）。

第一層（`entities.py`）要求共用具名標的，精準但召回有限。這一層只要求落在同一個
已註冊主題，能接上「同主題但沒提到同一家公司」的關聯——例如「FCC 禁中國 humanoid
進口」對上「Agility 透過 CCXI 上市」。

仍然是確定性比對：關鍵字逐字出現才算，不呼叫模型、不做模糊比對。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine_b.themes import (
    ThemeRegistryError,
    backfill_themes,
    load_themes,
    match_themes,
    related_by_theme,
)

ROOT = Path(__file__).resolve().parent.parent


def test_shipped_themes_parse() -> None:
    themes = load_themes()
    assert themes, "config/themes.txt 應至少有一個主題"
    for slug, theme in themes.items():
        assert theme.slug == slug
        assert theme.keywords or theme.tickers, f"{slug} 需至少有關鍵字或核心公司"


def test_robotics_theme_covers_the_parked_backlog() -> None:
    """parked backlog 集中在 robotics；字彙沒覆蓋等於機制白做。"""
    themes = load_themes()
    assert "robotics" in themes
    lowered = {k.lower() for k in themes["robotics"].keywords}
    assert {"humanoid", "digit"} <= lowered


def test_keyword_match_is_case_insensitive_for_ascii() -> None:
    hits = match_themes("HUMANOID robots are coming")
    assert "robotics" in hits
    assert "humanoid" in [t.lower() for t in hits["robotics"]["terms"]]


def test_ascii_keywords_require_word_boundaries() -> None:
    """InP 不得命中 input／printing 這類子字串。"""
    assert "cpo" not in match_themes("the input printer was inoperable")
    assert "cpo" in match_themes("6-inch InP wafer substrates")


def test_counter_keywords_still_tag_the_theme_but_are_flagged() -> None:
    """反證詞命中同樣算該主題——反面證據要找得到，不是被過濾掉（L7）。"""
    hits = match_themes("linear pluggable optics may replace it entirely")
    assert "cpo" in hits
    assert hits["cpo"]["counter_only"] is True
    assert hits["cpo"]["terms"] == []
    assert hits["cpo"]["counter_terms"]


def test_overlapping_counter_term_does_not_suppress_the_positive_hit() -> None:
    """反證詞若本身含正向詞（robot deployment delay ⊃ robot deployment），
    兩者都會命中而 counter_only=False。這是刻意的：該 lead 確實屬於此主題，
    同時帶有反面訊號，兩個資訊都該保留而不是互相抵銷。"""
    hits = match_themes("robot deployment delay at the pilot site")
    assert hits["robotics"]["terms"] == ["robot deployment"]
    assert hits["robotics"]["counter_terms"] == ["robot deployment delay"]
    assert hits["robotics"]["counter_only"] is False


def test_positive_and_counter_hits_coexist() -> None:
    hits = match_themes("CPO versus LPO in the same deployment")
    assert hits["cpo"]["terms"] and hits["cpo"]["counter_terms"]
    assert hits["cpo"]["counter_only"] is False


def test_empty_text_matches_nothing() -> None:
    assert match_themes(None, "") == {}


def _store() -> dict:
    return {
        "leads": {
            "lead_fcc": {
                "lead_id": "lead_fcc",
                "status": "pending",
                "title": "FCC set to ban Chinese imports of humanoid and quadruped robots",
            },
            "lead_digit": {
                "lead_id": "lead_digit",
                "status": "parked",
                "title": "GXO deploys Digit for tote transfer",
                "url": "https://example.com/a",
            },
            "lead_cpo": {
                "lead_id": "lead_cpo",
                "status": "parked",
                "title": "co-packaged optics external laser demand",
                "url": "https://example.com/b",
            },
            # 只以反證詞命中：teleoperation required 不含任何正向關鍵字
            "lead_counter": {
                "lead_id": "lead_counter",
                "status": "parked",
                "title": "teleoperation required for every task in the trial",
                "url": "https://example.com/c",
            },
        }
    }


def test_related_by_theme_bridges_leads_without_shared_tickers() -> None:
    """FCC 那則沒提 Digit，Digit 那則沒提 FCC，但同屬 robotics。"""
    matches = related_by_theme(_store(), "lead_fcc")
    ids = {m["lead_id"] for m in matches}
    assert "lead_digit" in ids
    assert "lead_cpo" not in ids, "不同主題不得誤連"


def test_counter_only_matches_are_surfaced_separately() -> None:
    matches = related_by_theme(_store(), "lead_fcc")
    counter = [m for m in matches if m["counter_only_themes"]]
    assert [m["lead_id"] for m in counter] == ["lead_counter"]


def test_related_by_theme_returns_empty_when_no_theme() -> None:
    store = {
        "leads": {
            "a": {"lead_id": "a", "status": "pending", "title": "完全無關的貼文"},
            "b": {"lead_id": "b", "status": "parked", "title": "humanoid"},
        }
    }
    assert related_by_theme(store, "a") == []


def test_backfill_is_idempotent() -> None:
    store = _store()
    assert backfill_themes(store) == len(store["leads"])
    assert backfill_themes(store) == 0


def test_malformed_theme_line_is_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "themes.txt"
    bad.write_text("這行沒有 slug 分隔\n", encoding="utf-8")
    load_themes.cache_clear()
    try:
        with pytest.raises(ThemeRegistryError):
            load_themes(str(bad))
    finally:
        load_themes.cache_clear()
