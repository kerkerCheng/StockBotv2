"""用**真實資料**驗證契約（Phase 1 的 T2／T5 驗收）。

## 為什麼不能只用手寫 fixture

手寫假資料只會證明「契約與我對契約的想像一致」。真正會撞出設計缺口的，是圖裡
那些長得很醜的 `evidence_refs`——同一個欄位裡混著 doc id（`cohr_10_q_20260506`）、
URI（`yfinance://history/COHR`）、entity id（`co:coherent`）、edge key（`edge:b0ec…`），
以及**整段帶逐字引文的散文**（`COHR Q3 FY2026 8-K EX-99.1（filed 2026-05-06,
accession 000119312526208972）Business Outlook 逐字：…`）。

那正是 F-22 的世界：一個少了 ticker 後綴的引用字串，讓整筆決策的資本歸零 22 次。

fixture 由 `scripts/capture_alpha_fixtures.py` 從真實 authority 擷取並 scrub
（NAV／持股／部位永不進 Git）。重跑那支腳本即可更新。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha.contracts import EvidenceRef
from alpha.errors import ContractViolation

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "alpha"

pytestmark = pytest.mark.skipif(
    not (FIXTURES / "evidence_refs_real.json").exists(),
    reason="真實 fixture 未擷取；跑 scripts/capture_alpha_fixtures.py 產生",
)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# T2：EvidenceRef 裝得下真實引用
# ---------------------------------------------------------------------------

def test_every_real_axis_reference_fits_the_contract() -> None:
    """10/10 條真實 evidence_ref 都必須能建成 `EvidenceRef`。

    ⚠ 這條若紅，代表契約設計錯了，**要改的是契約不是資料**。
    """
    payload = _load("evidence_refs_real.json")
    raw_refs = payload["raw_axis_refs"]
    assert raw_refs, "fixture 沒有真實引用可驗"
    failures: list[str] = []
    for raw in raw_refs:
        try:
            EvidenceRef(ref=raw, kind="external_document")
        except ContractViolation as exc:
            failures.append(f"{raw[:60]} → {exc}")
    assert not failures, "契約裝不下真實引用：\n" + "\n".join(failures)


def test_graph_and_engine_c_refs_carry_distinct_time_fields() -> None:
    """F-27 的實證：**取得時間與事實時間必須分開存**。

    Engine C 的觀測用 `as_of`（資產負債表日）→ `published_at`，
    `recorded_at`（寫入日）另存；圖的用 SourceDoc `published_at` ＋ `retrieved_at`。
    三個欄位若被壓成一個，這條會抓不到差異。
    """
    payload = _load("evidence_refs_real.json")
    engine_c = payload["engine_c"]
    assert engine_c, "fixture 沒有 Engine C 觀測"
    for ref in engine_c:
        assert ref["published_at"], "人工觀測必須有事實生效日（as_of）"
        assert ref["recorded_at"], "人工觀測必須有寫入時間（recorded_at）"
        assert ref["published_at"] != ref["recorded_at"], (
            "事實生效日與寫入日相同代表兩者被當成同一件事（F-27）"
        )


def test_real_reference_strings_are_heterogeneous() -> None:
    """記錄現況：真實引用**不是**同一種形狀。

    這條不是在守什麼，而是在**防止一個錯誤的簡化**——若未來有人假設
    `evidence_ref` 都是 doc id 而寫一個 exact match 的 resolver，
    F-22（22 次資本歸零）就會原樣重演。
    """
    payload = _load("evidence_refs_real.json")
    classification = payload["classification"]
    assert len(classification) >= 3, (
        f"真實引用至少橫跨 3 種形狀，實測：{classification}"
    )
    # 散文型引用確實存在——它們有 accession 但沒有結構化 id
    assert classification.get("external_document", 0) > 0, (
        "若這個數字變成 0，代表引用格式已被統一，"
        "屆時可以簡化 resolver——但要先確認不是 fixture 過期"
    )


# ---------------------------------------------------------------------------
# T5：AlphaSignal 裝得下真實 cohort
# ---------------------------------------------------------------------------

def test_real_cohort_produces_a_valid_alpha_signal() -> None:
    """COHR 的真實五軸能組成合法 `AlphaSignal`（含 trace 與 evidence）。"""
    payload = _load("cohr_alpha_signal.json")
    signal = payload["signal"]
    assert signal["ticker"] == "COHR"
    assert signal["company_id"] == "co:coherent"
    assert signal["disproof_conditions"], "L7：可證偽是一等公民"
    for axis in ("structural", "value_capture", "earnings_exposure", "expectation_gap"):
        score = signal[f"{axis}_score"]
        assert score is not None, f"{axis} 應由既有五軸映射得到"
        assert score["trace_id"] in signal["model_components"]


def test_real_signal_is_incomplete_because_catalyst_has_no_source() -> None:
    """**Q5 catalyst 在舊系統沒有任何軸**——它住在 `coverage_assessments.catalyst`
    的自由文字裡。

    所以真實 signal 是 `incomplete`，而 `catalyst_score` 是 `None` 不是 `0.0`。
    這一條同時驗到 `None ≠ 0` 的路徑**在真實資料上**成立，不只在手寫案例上。
    """
    payload = _load("cohr_alpha_signal.json")
    assert payload["is_incomplete"] is True
    assert payload["signal"]["catalyst_score"] is None
    assert len(payload["known_axes"]) == 4
    assert "catalyst" not in payload["known_axes"]


def test_contract_gaps_are_recorded_not_swallowed() -> None:
    """裝不下的東西要**現形**，不是靜默忽略（INV-3 的精神）。

    現況兩個缺口：
    1. `source_reliability` 是 meta 軸，不對應任何 score——它限定所有
       `EvidenceRef` 的品質，是輸入不是維度。
    2. Q5 catalyst 沒有結構化來源。
    """
    payload = _load("cohr_alpha_signal.json")
    gaps = payload["contract_gaps"]
    assert gaps, "缺口清單為空代表映射被假裝成完美"
    joined = " ".join(gaps)
    assert "source_reliability" in joined
    assert "catalyst" in joined


def test_ordering_key_puts_incomplete_last_on_real_data() -> None:
    """真實 signal 的排序鍵第一位必須是 `1`（incomplete），不論其他維度多強。"""
    payload = _load("cohr_alpha_signal.json")
    assert payload["ordering_key"][0] == "1"
    assert "inf" in payload["ordering_key"], "None 維度必須以 inf 現形，不得變成 0"


# ---------------------------------------------------------------------------
# 隱私邊界
# ---------------------------------------------------------------------------

FORBIDDEN_IN_FIXTURES = ("live_current_position", "selected_weight", "cash_floor",
                         "credit_facility", "nav_base", "paper_capacity_snapshot")


@pytest.mark.parametrize("name", ["evidence_refs_real.json", "cohr_axis_assessment.json",
                                  "cohr_alpha_signal.json"])
def test_fixtures_carry_no_private_authority_fields(name: str) -> None:
    """private authority（NAV／持股／部位／貸款）**永不進 Git**。

    fixture 來自 Decision Store，那是 append-only 的私有真相；
    這條是把 `.gitignore` 的邊界延伸到 fixture 內容上。
    """
    text = (FIXTURES / name).read_text(encoding="utf-8")
    for token in FORBIDDEN_IN_FIXTURES:
        assert token not in text, f"{name} 含 private authority 欄位：{token}"
