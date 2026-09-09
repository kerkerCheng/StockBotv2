"""materialize 的兩種宇宙（2026-09-09 研究閉環 P4）。

`--tracked` 沿用 pq1 的導出權威（不手寫清單）；`--registry-listed` 是 registry 裡所有有
research_ticker 的公司。守兩件事：①第二種宇宙**不改** `discover_tracked_tickers`（那會連帶擴大
EDGAR harvest 與稀釋 priority 加分）；②它只列上市者、去重、排序，未上市的 `research_ticker=None`
不會變成字串 "None" 混進去。
"""
from __future__ import annotations

from webapp.__main__ import _registry_listed_tickers, build_parser


def test_registry_listed_universe_is_every_listed_company_once_and_sorted() -> None:
    from identity import get_registry

    tickers = _registry_listed_tickers()
    listed = {c.research_ticker.strip().upper() for c in get_registry().companies if c.research_ticker}
    assert tickers == sorted(listed)
    assert len(tickers) == len(set(tickers))
    assert "NONE" not in tickers and "" not in tickers
    assert len(tickers) < len(get_registry().companies)          # 未上市的不在裡面


def test_registry_listed_flag_does_not_touch_the_pq1_tracked_derivation() -> None:
    """第二種宇宙是 materialize 自己的參數；pq1 的 tracked 來源仍只有 config 裡那三個。"""
    import json
    from pathlib import Path

    config = json.loads(Path("config/daily_routine.json").read_text(encoding="utf-8"))
    assert set(config["pq1"]["tracked_ticker_sources"]) == {
        "thesis_lifecycle", "decision_cohorts", "theme_core_companies",
    }
    parser = build_parser()
    args = parser.parse_args(["materialize", "--registry-listed"])
    assert args.registry_listed is True and args.tracked is False
    args = parser.parse_args(["materialize", "--tracked"])
    assert args.tracked is True and args.registry_listed is False
