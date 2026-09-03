"""Golden fixtures：refactor 前的 expected semantic behavior。

## 這一組測試守什麼

`historical-failure-matrix.md` §8 的 dual run 要求「**同一 frozen input**、
舊新兩條 pipeline、每個差異都被分類」。golden fixtures 就是那個 frozen input——
而 **B1（Portfolio/Risk 搬家）一動，「舊行為長什麼樣」就補不回來了**。

所以這裡的斷言不是「值是多少」（那會隨資料成長而漂移，是正常的），
而是三件**結構性**的事：
1. 14 類全部在場——少一類代表某個歷史事故的 frozen input 不存在。
2. 每一類都指得回它守的事故——沒有指向的 fixture 是裝飾品。
3. **tracked 的那份不含任何金額**——private authority 永不進 Git。

漂移偵測由 `python scripts/capture_golden_fixtures.py --verify` 負責（digest 比對），
不放進單元測試：它需要 Neo4j／Sheet／Decision Store，是 integration 層的事。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

GOLDEN = Path(__file__).resolve().parent / "fixtures" / "golden"
MANIFEST = GOLDEN / "manifest.json"

#: 14 類與它們守的歷史事故。**這張表是契約**——改它等於改 dual run 的涵蓋範圍。
EXPECTED_CLASSES: dict[str, str] = {
    "normal_company": "baseline",
    "symbol_layers": "F-05",
    "minor_unit_quotes": "F-02",
    "unlisted_company": "F-03",
    "structural_bottleneck": "—",
    "multiple_substitutes": "—",
    "watch_states": "F-15",
    "cohort_lifecycle": "F-06",
    "blocked_states": "F-24",
    "stale_observations": "—",
    "edge_conflicts": "—",
    "point_in_time_boundary": "F-31",
    "truncation_boundary": "F-20",
    "multi_account_holding": "F-21",
}

#: tracked fixture 裡出現「欄位名: 數字」即視為金額洩漏。
_MONEY = re.compile(
    r'"(market_value_base|nav_base|nav_pct|cash_pct|selected_weight|shares|'
    r'price|amount|balance|equity)"\s*:\s*[\d.]'
)

pytestmark = pytest.mark.skipif(
    not MANIFEST.exists(),
    reason="golden fixtures 未擷取；跑 scripts/capture_golden_fixtures.py 產生",
)


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]


def test_all_fourteen_classes_are_present() -> None:
    """少一類 ＝ 某個歷史事故的 frozen input 不存在，dual run 就有盲區。"""
    assert set(_manifest()) == set(EXPECTED_CLASSES)


@pytest.mark.parametrize("key", sorted(EXPECTED_CLASSES))
def test_each_class_names_the_failure_it_guards(key: str) -> None:
    """沒有指向歷史事故的 fixture 是裝飾品。"""
    entry = _manifest()[key]
    assert entry["guards"] == EXPECTED_CLASSES[key]
    assert entry["digest"].startswith("sha256:")


def test_public_fixtures_have_a_file_and_private_ones_do_not() -> None:
    """private 的完整內容只在 gitignored 的 `library/private/golden/`。"""
    for key, entry in _manifest().items():
        path = GOLDEN / f"{key}.json"
        if entry["private"]:
            assert not path.exists(), f"{key} 是 private，完整內容不得進 Git"
            assert "summary" in entry, f"{key} 至少要留可讀摘要，不能只有 digest"
        else:
            assert path.exists(), f"{key} 缺 fixture 檔"


def test_tracked_fixtures_carry_no_monetary_values() -> None:
    """**private authority 永不進 Git。**

    Decision Store 與 Google Sheet 是 append-only／外部真相；把 NAV、部位金額
    寫進 tracked fixture 等於把 `.gitignore` 的邊界打開一個洞。
    """
    leaks: list[str] = []
    for path in sorted(GOLDEN.glob("*.json")):
        for match in _MONEY.finditer(path.read_text(encoding="utf-8")):
            leaks.append(f"{path.name}: {match.group(0)}")
    assert not leaks, "tracked golden fixture 含金額：\n" + "\n".join(leaks)


def test_point_in_time_fixture_records_the_dated_coverage_baseline() -> None:
    """Phase 6 的驗收基準：assertion 可定日比例要從現況推到 ≥95%。

    ⚠ 這條**不斷言具體數字**（資料會長），只確保欄位在——
    baseline 數字本身寫在 `current-architecture.md` §4.2，那裡有查證命令。
    """
    payload = json.loads((GOLDEN / "point_in_time_boundary.json")
                         .read_text(encoding="utf-8"))
    coverage = payload["assertion_dated_coverage"]
    assert {"assertions", "dated"} <= set(coverage)
    assert coverage["assertions"] > 0
    assert coverage["dated"] < coverage["assertions"], (
        "若 dated == assertions，代表 published_at 已補齊——"
        "那是 Phase 6 的目標，達成時請更新 current-architecture §4.2 的數字"
    )


def test_truncation_fixture_has_a_row_beyond_the_limit() -> None:
    """F-20 的 frozen input：**必須真的有第 N+1 名**，否則測不到截斷邊界。"""
    payload = json.loads((GOLDEN / "truncation_boundary.json")
                         .read_text(encoding="utf-8"))
    assert payload["full_id_count"] > payload["limit"]
    assert payload["first_beyond_limit"], "沒有第 N+1 名的話這個 fixture 守不到任何東西"
