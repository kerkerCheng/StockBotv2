"""「錯的訊號」逐條對反證（2026-11-10；failure log #140；使用者「#140 … 照推薦做」）。

AXTI 11-07 版「必須為真」格寫了「通美融資沒能交割」，disproof[] 卻沒有這一條——2026-12-20 的交割期限沒有任何 watch。
寫法沿用研究 session 已在用的「（第 N 條）」：N＝disproof[] 的順序、從 1 起算；「讀圖第 N 條」指讀圖自己的反證（本來就有 watch）。

守的事：
①切條：段落從「錯的訊號…：」起到括號外的第一個「。」，括號外的「；」切條；括號裡的「；」「。」不切；
②寫入端 ⑭：標的編號指不到 disproof[] 的那一條 → 拒收（宣稱有 watch 在盯、其實沒有）；
③沒標編號的條目只印、不擋（從文字切條會誤切，L16）——印在寫入收據，條目原文照列；
④回放：11-07 那一版會印出「通美融資沒能交割」。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import wrong_signal_items
from alpha.providers.briefs import v2_write_notices, write_brief, wrong_signal_ref_problems

from test_narrative_literals import _ctx as _write_ctx, _record as _write_record
from test_open_two_gates import CO, DISPROOF, READ, T, _slots

SECOND = {**DISPROOF, "condition": "若通美私募在 2026-12-20 前沒有交割，子公司的擴產資金要回到母公司身上"}


def _brief(must: str, disproof=(DISPROOF, SECOND)):
    slots = _slots()
    slots["what_must_be_true"] = {"text": must, "evidence_refs": ["graph://x"]}
    record = brief_record(company_id=CO, ticker=T, slots=slots, record_version=RECORD_VERSION_V2,
                          rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], disproof=list(disproof),
                          answers={"priced_in": "yes", "in_numbers": "yes"},
                          candidate_state={"state": "open", "watch_id": None, "reason": None},
                          created_at=datetime(2026, 11, 10, 3, tzinfo=timezone.utc))
    return parse_brief_record(record)


# ---------------------------------------------------------------------------
# ① 切條
# ---------------------------------------------------------------------------

def test_items_are_cut_by_semicolons_outside_brackets_and_stop_at_the_first_full_stop() -> None:
    text = ("必須為真：擴產沒提前。錯的訊號（括號是對應的反證）：毛利率跌回三成以下（第 1 條；以年報為準）；"
            "私募沒交割（第 2 條，逾期型：12-20）；出口管制解除（讀圖第 5 條）；客戶退出產能協議。（AXT 自己的擴產不算。）")
    items = wrong_signal_items(text)
    assert [i[0][:6] for i in items] == ["毛利率跌回三", "私募沒交割（", "出口管制解除", "客戶退出產能"]
    assert [i[1] for i in items] == [(1,), (2,), (), ()]
    assert [i[2] for i in items] == [False, False, True, False]


def test_a_full_stop_inside_brackets_does_not_end_the_paragraph() -> None:
    items = wrong_signal_items("錯的訊號：毛利率跌回三成以下（第 1 條。以年報為準）；私募沒交割（第 2 條）。之後的句子不算。")
    assert [i[1] for i in items] == [(1,), (2,)]


def test_refs_take_lists_and_ignore_other_numbered_things() -> None:
    items = wrong_signal_items("錯的訊號：A 或 B（第 1、2 條）；8-K 第 3.02 項的增資；公告 2025 年第 10 號的品項解禁")
    assert [i[1] for i in items] == [(1, 2), (), ()]


def test_no_wrong_signal_paragraph_means_nothing_to_check() -> None:
    assert wrong_signal_items("要推翻它：客戶具名第二家供應商。") == []
    assert wrong_signal_items("") == []


# ---------------------------------------------------------------------------
# ② 編號指不到 → 拒收；③ 沒標 → 只印
# ---------------------------------------------------------------------------

def test_a_ref_beyond_disproof_is_rejected() -> None:
    bad = _brief("錯的訊號：擴產提前（第 1 條）；私募沒交割（第 3 條）。")
    problems = wrong_signal_ref_problems(bad)
    assert len(problems) == 1 and "第 3 條不在 disproof[]（共 2 條）" in problems[0] and "私募沒交割" in problems[0]
    assert wrong_signal_ref_problems(_brief("錯的訊號：私募沒交割（第 0 條）。"))
    assert wrong_signal_ref_problems(_brief("錯的訊號：擴產提前（第 1 條）；私募沒交割（第 2 條）。")) == []


def test_untagged_items_are_printed_not_rejected() -> None:
    brief = _brief("錯的訊號：擴產提前（第 1 條）；通美融資沒能交割；出口管制解除（讀圖第 5 條）。")
    assert wrong_signal_ref_problems(brief) == []
    notices = [n for n in v2_write_notices(brief) if "錯的訊號" in n]
    assert len(notices) == 1 and "「通美融資沒能交割」" in notices[0]
    assert "擴產提前" not in notices[0] and "出口管制解除" not in notices[0]
    tagged = _brief("錯的訊號：擴產提前（第 1 條）；通美融資沒能交割（第 2 條）。")
    assert not [n for n in v2_write_notices(tagged) if "錯的訊號" in n]


# ---------------------------------------------------------------------------
# ④ 回放：AXTI 11-07 版（`ib_5a2398613c6e7598`）的錯的訊號段落（原文節錄，五條都沒標）
# ---------------------------------------------------------------------------

AXTI_1107 = ("錯的訊號：第四季營收低於第三季的 7,340 萬美元或毛利率跌回第二季的 44.9% 以下；任一家宣布擴產提前或再加碼；"
             "中國出口管制解除或恢復對美國出貨許可（量的窗口會縮短，要重估）；客戶終止產能協議或要回預付款；"
             "通美融資沒能交割、或三年後投資人行使贖回而 AXT 以增發股票代買。")


def test_the_write_path_refuses_a_dangling_ref_and_returns_the_bare_notice(tmp_path: Path) -> None:
    """寫入端整條：⑭ 接在 `v2_write_problems`、提醒接在寫入結果的 notices（夾具那份敘事沒有 disproof[]）。"""
    ctx, wid = _write_ctx()
    with pytest.raises(ContractViolation, match="第 1 條不在 disproof"):
        write_brief(_write_record(wid, what_must_be_true="錯的訊號：擴產提前（第 1 條）。"), ctx=ctx,
                    directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    ctx, wid = _write_ctx()
    out = write_brief(_write_record(wid, what_must_be_true="擴產沒提前。錯的訊號：通美融資沒能交割。"), ctx=ctx,
                      directory=tmp_path / "c", watches_path=tmp_path / "w2.json")
    assert [n for n in out["notices"] if "錯的訊號" in n and "通美融資沒能交割" in n]


def test_replay_of_the_1107_version_prints_the_unwatched_signal() -> None:
    notices = [n for n in v2_write_notices(_brief(AXTI_1107)) if "錯的訊號" in n]
    assert len(notices) == 1 and "通美融資沒能交割" in notices[0]
    assert len(wrong_signal_items(AXTI_1107)) == 5
