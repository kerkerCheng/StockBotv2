"""「我們有沒有形成自己的觀點」——三層各自的守門測試（2026-09-10）。

## 為什麼需要這一層

2026-09-10 實測 9 檔 ready 標的：其中 5 檔的隱含報酬是 ±0.01%。那個 0 **不是**「我們算完
覺得它合理定價」，而是代數上的必然——EPS 由同期共識反解、目標倍數校準到現價，兩個桿都被
構造成 1.0，於是 fair value 恆等於現價。

而畫面上它和「我們真的算過、結論接近共識」長得一模一樣（L12：一個表示承載兩種語意，
下游被迫二選一而兩邊都錯）。

## 既有的 gate 為什麼擋不住

每一條「由共識 EPS 逆推」的假設都**完整滿足** v2 的 provenance gate：基期觀測標
`supporting`、同期共識標 `calibration`，兩個標記都誠實。那道 gate 問的是「共識有沒有被
當成支持證據」，而逆推根本不需要那樣標（L15-1：這個 gate 攔下的不是它想攔的東西）。
所以 `derivation` 是一個真正缺失的維度，不是 `dependency_roles` 的重造品（L16）。
"""
from __future__ import annotations

from alpha.fundamental.contracts import (
    ASSUMPTION_DERIVATIONS, OPINION_BEARING_DRIVERS, OPINION_STANCES, opinion_stance,
)
from briefing.analyst_view.contracts import PLAIN_STANCE


class _Fake:
    """只帶 stance 需要的三個欄位——刻意不用真的 OperatingAssumption，避免測試綁死建構細節。"""

    def __init__(self, driver: str, derivation: str, retracted: bool = False) -> None:
        self.driver, self.derivation, self.retracted = driver, derivation, retracted


# ---------------------------------------------------------------------------
# 1. 模型層：聚合規則
# ---------------------------------------------------------------------------

def test_any_independent_core_driver_means_we_have_a_view() -> None:
    assert opinion_stance([_Fake("revenue_growth", "independent"),
                           _Fake("operating_margin_delta", "consensus_inverted")]) == "independent"


def test_all_inverted_core_drivers_is_not_an_opinion() -> None:
    assert opinion_stance([_Fake("revenue_growth", "consensus_inverted"),
                           _Fake("operating_margin_delta", "consensus_inverted")]) == "consensus_inverted"


def test_mechanical_drivers_never_decide_the_stance() -> None:
    """沿用基期實績的 tax／shares／NCI／interest 不參與。

    把它們算進來，每一家公司都會被判成沒有觀點——一個恆亮的判準等於零鑑別力（L14-4）。
    反過來也一樣：它們也不能讓一家沒做研究的公司看起來像有觀點。
    """
    mechanical = [_Fake("tax_rate", "carried_forward"), _Fake("diluted_shares", "carried_forward"),
                  _Fake("nci_attribution", "carried_forward"),
                  _Fake("interest_and_other_net", "carried_forward")]
    assert opinion_stance(mechanical) == "no_opinion_bearing_assumptions"
    assert opinion_stance(mechanical + [_Fake("revenue_growth", "consensus_inverted")]) \
        == "consensus_inverted"


def test_guidance_outranks_inverted_because_it_can_actually_differ_from_consensus() -> None:
    """優先序是「哪一種結構上可能產生預期差」，不是「哪個聽起來比較強」。

    實測（2026-09-10，LITE）：營收取共識成長、營益率取公司 Q1 指引持平外推而共識沒這樣做——
    那一條假設貢獻了 +8.92% 的 EPS 差異。若把 `consensus_inverted` 排在前面，這一檔會被
    標成「還沒形成觀點」，而它其實有一個明確的立場：相信公司，不相信分析師。
    """
    assert opinion_stance([_Fake("revenue_growth", "consensus_inverted"),
                           _Fake("operating_margin_delta", "company_guidance")]) == "company_guidance"
    # 但 independent 仍然最優先——自己的分析勝過採信別人。
    assert opinion_stance([_Fake("revenue_growth", "company_guidance"),
                           _Fake("operating_margin_delta", "independent")]) == "independent"


def test_unclassified_never_becomes_independent() -> None:
    """fail safe 的方向是「不知道」，不是「我們自己想的」——反過來會把佔位冒充成主張。"""
    assert opinion_stance([_Fake("revenue_growth", "unclassified")]) == "undeclared"
    assert opinion_stance([_Fake("revenue_growth", "unclassified"),
                           _Fake("operating_margin_delta", "consensus_inverted")]) == "consensus_inverted"


def test_retracted_assumptions_do_not_count() -> None:
    assert opinion_stance([_Fake("revenue_growth", "independent", retracted=True)]) \
        == "no_opinion_bearing_assumptions"


# ---------------------------------------------------------------------------
# 2. 措辭層：只有一份
# ---------------------------------------------------------------------------

def test_plain_wording_covers_every_stance_and_no_extras() -> None:
    """新增一個 stance 而忘了寫措辭，使用者會看到一個內部代號——這就是那道剎車。"""
    assert set(PLAIN_STANCE) == set(OPINION_STANCES)
    for stance, entry in PLAIN_STANCE.items():
        assert entry["short"] and entry["reason"], stance
        assert stance not in entry["short"], f"{stance} 的短標籤不該是內部代號本身"


def test_derivation_and_stance_vocabularies_stay_closed() -> None:
    assert "unclassified" in ASSUMPTION_DERIVATIONS       # 舊紀錄的 fail safe 必須存在
    assert "independent" in ASSUMPTION_DERIVATIONS
    assert OPINION_BEARING_DRIVERS == {"revenue_growth", "operating_margin_delta"}


# ---------------------------------------------------------------------------
# 3. 出門：字彙隨 materialize 走到 APP，前端不維護第二份
# ---------------------------------------------------------------------------

def test_stance_wording_ships_with_the_vocabulary_file(tmp_path) -> None:
    import json

    from webapp.materialize import write_vocabularies
    from webapp.store import ArtifactStore

    path = write_vocabularies(ArtifactStore(tmp_path))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload["plain_stance"]) == set(OPINION_STANCES)


def test_frontend_does_not_hardcode_a_second_stance_table() -> None:
    """app.js 必須從 VOCAB 讀措辭。硬編一份對照表就是 L16 記過的重造品。"""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(
        encoding="utf-8")
    assert "VOCAB.plain_stance" in source
    # 代號出現在分支邏輯是正常的（`stance === 'consensus_inverted'` 決定那一欄印不印數字）；
    # **不正常的是措辭**——一旦前端寫死一句中文，字彙改了它就開始偏離。
    # ⚠ 刻意**只檢查長句**。第一版連 short 一起檢查，結果「未宣告」這種常見詞在 app.js
    # 別處誤報——而 L16-4 明文：做一個會誤報的防呆來防止過度工程，本身就是過度工程。
    # 長句夠長到不可能巧合，短標籤不夠。
    for entry in PLAIN_STANCE.values():
        assert entry["reason"][:14] not in source, f"app.js 不該硬編措辭：{entry['reason'][:14]}"


def test_every_surface_that_prints_implied_return_consults_the_stance() -> None:
    """三個 surface 印同一個大數字，必須共用同一段判斷。

    事發（2026-09-10）：第一版只改了詳情頁「我們比市場」那一欄，而使用者最先看到的是
    **列表卡片與頭條的隱含報酬**——那兩處照樣印 `0.0%`。使用者的原話是「002472 明明
    missing 還是 0.0%」「5802.T AXTI ready without any comment」。

    這是 L13：驗收條件必須寫成「產出出現在下游消費者手上」，而當時驗的是 artifact 裡的
    欄位對不對——那一層早就對了。
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(
        encoding="utf-8")
    # 1 個定義 + 3 個呼叫（列表卡片／頭條／白話頭條）
    assert source.count("appendReturnBlock") == 4, "有 surface 沒有共用那段判斷"
    # 列表卡片要看得到 stance，否則 ready 會被讀成「有結論」
    assert "stanceBadge(cardStance)" in source
    # 解釋的那句話要跟大數字在同一張卡
    assert "stanceBanner(headStance)" in source
