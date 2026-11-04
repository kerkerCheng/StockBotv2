"""看了沒買（盲點修法第 17 條，2026-11-03；AGENTS「沒買也是決定」）——A5 的第二本：`library/trades/looked_log.jsonl`。

守的事：①寫入端拒收缺理由、缺敘事版本、不在封閉字彙的選擇、解析不到的公司；②與成交同一支入口、同一種收據
（`record_trade.py looked`，`side`＝看了沒買）；③append-only：重寫同一筆被擋、壞行與重複不靜默丟；④讀者只有計數——
「你的決定」三格（進＝alpha 成交買進、不要、等到條件），0 也印。全部用暫存檔、假 Sheet——不讀真的 Sheet、不寫真的 log。

2026-11-04 R2 補的：⑤記下的版本必須是候選板上那一版（板舊了、板上沒有、版本對不上一律拒收；INV-6）；⑥等到條件有到期
（不給＝30 天後；INV-2）；⑦重記只擋「同一版、同一個選擇、還在生效」（隔天重跑、改一個標點不再多一列）；⑧重複的列只算一次、
檔尾半行不吞下一列；⑨「你的決定」只數當時是可開的，其餘另列；trade_log 讀不懂的行報出來。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from portfolio import looked_log as ll
from tests.test_record_trade_receipt import SIVERS, TODAY, env  # noqa: F401 — env 是 fixture

BOARD_ROW = {"ticker": "AAA", "company_id": "co:aaa", "brief_id": "ib_aaa1", "group": "open", "derived": "open"}
RECEIPT = {"version": "research-receipt/v1", "side": "看了沒買", "narrative": "present", "narrative_label": "有現行 v2 敘事",
           "company_id": "co:aaa", "research_ticker": "AAA",
           "declared": {"brief_id": "ib_aaa1", "candidate_state": {"state": "open"}},
           "derived": {"candidate_as_of": "2026-11-03", "candidate": BOARD_ROW, "status": "available"}}


def _receipt(*, row=BOARD_ROW, **over):
    derived = {**RECEIPT["derived"], "candidate": row}
    return {**RECEIPT, "derived": derived, **over}


def _entry(**over):
    params = dict(symbol="AAA", choice="不要", why="已定價、翻倍條件太遠", today=date(2026, 11, 3),
                  recorded_at="2026-11-03T02:00:00+00:00", receipt=RECEIPT)
    params.update(over)
    return ll.build_entry(**params)


def test_the_writer_refuses_a_missing_reason_a_missing_narrative_and_an_unknown_choice() -> None:
    """變異：拿掉「缺敘事版本」那一道 → 第二條紅。"""
    entry = _entry()
    assert (entry["kind"], entry["choice"], entry["brief_id"], entry["company_id"]) == ("看了沒買", "不要", "ib_aaa1", "co:aaa")
    assert entry["decision_id"].startswith("lk_") and entry["research_receipt"]["side"] == "看了沒買"
    with pytest.raises(ValueError, match="缺理由"):
        _entry(why="   ")
    with pytest.raises(ValueError, match="缺敘事版本"):
        _entry(receipt={**RECEIPT, "narrative": "absent", "narrative_label": "沒有敘事", "declared": None})
    with pytest.raises(ValueError, match="record_trade"):
        _entry(choice="進")                                  # 進走成交，不寫這本
    with pytest.raises(ValueError, match="INV-1"):           # 解析不到公司先說名冊，不說成缺敘事（L12）
        _entry(receipt={**RECEIPT, "company_id": None, "narrative": "unresolved", "declared": None})


def test_the_version_recorded_is_the_one_on_the_board() -> None:
    """11-04 R2 B1（INV-6）：板上那一列的版本 ≠ 現行、板上沒有這一檔、板不是今天的 → 一律拒收。
    變異：拿掉版本比對 → 第一條不紅。"""
    with pytest.raises(ValueError, match="你讀到的是舊版"):
        _entry(receipt=_receipt(row={**BOARD_ROW, "brief_id": "ib_old"}))
    with pytest.raises(ValueError, match="候選板上找不到你讀的那一版（候選板上沒有這一檔"):
        _entry(receipt={**RECEIPT, "derived": {"candidate_as_of": "2026-11-03", "candidate": None,
                                               "candidate_note": "候選板上沒有這一檔"}})
    with pytest.raises(ValueError, match="不是今天的"):
        _entry(receipt={**RECEIPT, "derived": {"status": "upstream_unavailable",
                                               "reason": "候選板 artifact 是 2026-11-02 的，不是今天"}})
    assert _entry()["brief_id"] == "ib_aaa1"                 # 同一版照收


def test_a_wait_has_an_expiry_and_a_no_does_not() -> None:
    """11-04 R2（INV-2）：等到條件不給日子＝30 天後；不要帶日子、日子不在今天之後都拒收；讀回來也驗。"""
    wait = _entry(choice="等到條件", why="等客戶 10-K 具名第二家")
    assert wait["until"] == "2026-12-03" and ll.parse_entry(wait).until == date(2026, 12, 3)
    assert _entry(choice="等到條件", why="等法說", until=date(2026, 11, 20))["until"] == "2026-11-20"
    assert _entry()["until"] is None
    with pytest.raises(ValueError, match="只給等到條件"):
        _entry(until=date(2026, 11, 20))
    with pytest.raises(ValueError, match="之後"):
        _entry(choice="等到條件", why="等法說", until=date(2026, 11, 3))
    with pytest.raises(ValueError, match="INV-2"):
        ll.parse_entry({**wait, "until": None})
    with pytest.raises(ValueError, match="null"):
        ll.parse_entry({**_entry(), "until": "2026-12-01"})


def test_the_log_is_append_only_and_bad_or_repeated_lines_are_reported(tmp_path) -> None:
    path = tmp_path / "looked.jsonl"
    assert ll.load(path) == ([], [])                         # 不存在＝還沒有任何一次決定
    first = _entry()
    ll.append(first, path)
    ll.append(_entry(choice="等到條件", why="等客戶 10-K 具名第二家"), path)
    entries, problems = ll.load(path)
    assert problems == [] and [e.choice for e in entries] == ["不要", "等到條件"]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{壞掉\n" + json.dumps(first, ensure_ascii=False) + "\n")
    entries, problems = ll.load(path)
    assert any("第 3 行" in p for p in problems) and any("重複" in p and "只算一次" in p for p in problems)
    assert [e.choice for e in entries] == ["不要", "等到條件"]       # 重複那一列不進計數（變異：照收 → 紅）
    with pytest.raises(ValueError, match="形狀封閉"):
        ll.parse_entry({**first, "size": 100})               # 不收尺寸、不收任何額外欄


def test_a_half_written_last_line_does_not_swallow_the_next_entry(tmp_path) -> None:
    """11-04 R2：斷電留下沒有換行的半行，下一次 append 先收尾——半行照樣報出來，新的一列完整。"""
    path = tmp_path / "looked.jsonl"
    path.write_text(json.dumps(_entry(), ensure_ascii=False)[:40], encoding="utf-8")
    ll.append(_entry(choice="等到條件", why="等法說"), path)
    entries, problems = ll.load(path)
    assert [e.choice for e in entries] == ["等到條件"] and len(problems) == 1 and "第 1 行" in problems[0]


def test_a_repeat_is_the_same_version_the_same_choice_still_standing(tmp_path) -> None:
    """11-04 R2（L17：key 真的唯一嗎）：隔天重跑、改一個標點 → 已記過；換選擇、等到條件到期、明給不同日子 → 照寫。"""
    no = ll.parse_entry(_entry())
    again = _entry(why="已定價，翻倍條件太遠。", today=date(2026, 11, 4), recorded_at="2026-11-04T02:00:00+00:00")
    assert ll.repeat_of(again, [no], today=date(2026, 11, 4)) == no
    switch = _entry(choice="等到條件", why="等法說", today=date(2026, 11, 4), recorded_at="2026-11-04T02:00:00+00:00")
    assert ll.repeat_of(switch, [no], today=date(2026, 11, 4)) is None
    wait = ll.parse_entry(_entry(choice="等到條件", why="等法說", until=date(2026, 11, 20)))
    rerun = _entry(choice="等到條件", why="等法說", today=date(2026, 11, 5), recorded_at="2026-11-05T02:00:00+00:00")
    assert ll.repeat_of(rerun, [wait], today=date(2026, 11, 5)) == wait       # 預設日子不算改日子
    redated = _entry(choice="等到條件", why="等法說", today=date(2026, 11, 5), until=date(2026, 12, 1),
                     recorded_at="2026-11-05T02:00:00+00:00")
    assert ll.repeat_of(redated, [wait], today=date(2026, 11, 5), until_given=True) is None
    asked = _entry(choice="等到條件", why="再等一季", today=date(2026, 11, 20), recorded_at="2026-11-20T02:00:00+00:00")
    assert ll.repeat_of(asked, [wait], today=date(2026, 11, 20)) is None      # 到期那天起是重問
    other = _entry(receipt=_receipt(row={**BOARD_ROW, "brief_id": "ib_aaa2"},
                                    declared={"brief_id": "ib_aaa2", "candidate_state": {"state": "open"}}))
    assert ll.repeat_of(other, [no], today=date(2026, 11, 3)) is None         # 敘事換版是新的一題


def test_standing_and_hides_drive_the_open_choice_list() -> None:
    no = ll.parse_entry(_entry())
    wait = ll.parse_entry(_entry(choice="等到條件", why="等法說", until=date(2026, 11, 20),
                                 recorded_at="2026-11-03T03:00:00+00:00"))
    assert ll.standing([wait, no])[("co:aaa", "ib_aaa1")] == wait              # 最後一次算數（照 recorded_at）
    assert ll.hides(no, today=date(2027, 1, 1))
    assert ll.hides(wait, today=date(2026, 11, 19)) and not ll.hides(wait, today=date(2026, 11, 20))


def test_your_decisions_count_only_what_was_open_at_the_time() -> None:
    """進＝帶研究收據的買進（beta 不帶收據、賣出不算）；不要／等到條件＝這本。只數當月、只數當時是可開的——加碼買進與對缺 X
    的不要另列，收據沒有候選板那一列的分不出（11-04 R2）。變異：進改成數全部買進、或不分可開 → 紅。"""
    def buy(group, day="2026-11-02"):
        derived = {"candidate": {"group": group}} if group else {"status": "upstream_unavailable"}
        return {"side": "buy", "executed_at": f"{day}T10:00:00-04:00", "research_receipt": {"derived": derived}}

    events = [buy("open"), buy("held"), buy(None),
              {"side": "buy", "executed_at": "2026-11-02T10:00:00-04:00"},                      # beta
              {"side": "sell", "executed_at": "2026-11-02T10:00:00-04:00", "research_receipt": {}},
              buy("open", day="2026-10-20")]
    missing = _receipt(row={**BOARD_ROW, "group": "missing", "derived": "missing"})
    entries = [ll.parse_entry(_entry()), ll.parse_entry(_entry(choice="等到條件", why="等 10-K")),
               ll.parse_entry(_entry(today=date(2026, 10, 30))), ll.parse_entry(_entry(receipt=missing))]
    counts = ll.month_counts(entries, events, "2026-11")
    assert counts.decided == {"進": 1, "不要": 1, "等到條件": 1}
    assert counts.not_open == {"進": 1, "不要": 1, "等到條件": 0} and counts.unknown == {"進": 1, "不要": 0, "等到條件": 0}
    line = ll.status_line(counts, month="2026-11")
    assert line.startswith("你的決定 11 月：進 1｜不要 1｜等到條件 1（只數當時是可開的")
    assert "另 2 筆當時不是可開（買進 1、不要 1）" in line and "1 筆分不出當時是不是可開" in line
    empty = ll.month_counts([], [], "2026-11")
    assert ll.status_line(empty, month="2026-11").startswith("你的決定 11 月：進 0｜不要 0｜等到條件 0")
    assert "另" not in ll.status_line(empty, month="2026-11")
    assert "⚠ 帳有 1 個問題" in ll.status_line(empty, month="2026-11", problems=["第 2 行壞了"])


def test_unreadable_trade_rows_are_reported_not_skipped(tmp_path) -> None:
    """11-04 R2（INV-3）：trade_log 不是 object 的行、讀不懂 executed_at 的買進——都報出來，不靜默不算。"""
    trade = tmp_path / "trade.jsonl"
    trade.write_text("\n".join([json.dumps([1, 2]), json.dumps({"side": "buy", "executed_at": "昨天",
                                                                  "research_receipt": {}})]) + "\n", encoding="utf-8")
    line = ll.short_line(today=date(2026, 11, 3), looked_path=tmp_path / "none.jsonl", trade_path=trade)
    assert "⚠ 帳有 2 個問題（trade_log 第 1 行不是 object）" in line


def test_short_line_reads_both_logs(tmp_path) -> None:
    looked, trade = tmp_path / "looked.jsonl", tmp_path / "trade.jsonl"
    ll.append(_entry(), looked)
    trade.write_text(json.dumps({"side": "buy", "executed_at": "2026-11-03T09:00:00+08:00",
                                 "research_receipt": {"narrative": "present",
                                                      "derived": {"candidate": {"group": "open"}}}}) + "\n",
                     encoding="utf-8")
    assert ll.short_line(today=date(2026, 11, 3), looked_path=looked, trade_path=trade).startswith(
        "你的決定 11 月：進 1｜不要 1｜等到條件 0")
    assert ll.short_line(today=date(2026, 11, 3), looked_path=tmp_path / "none.jsonl",
                         trade_path=tmp_path / "none2.jsonl").startswith("你的決定 11 月：進 0｜不要 0｜等到條件 0")


# ---------------------------------------------------------------------------
# 入口：record_trade.py looked（與成交同一支、同一種收據）
# ---------------------------------------------------------------------------

def test_record_trade_looked_writes_the_same_receipt_and_is_dry_run_by_default(env) -> None:  # noqa: F811
    module, path = env["module"], env["tmp"] / "looked.jsonl"
    module.LOOKED_LOG = path
    args = ["looked", "--symbol", "SIVE.ST", "--choice", "等到條件", "--why", "等客戶端一手具名"]
    assert module.main(args) == 0 and not path.exists()                        # 預設 dry-run：不寫
    assert module.main([*args, "--apply"]) == 0
    entries, problems = ll.load(path)
    assert problems == [] and len(entries) == 1
    raw = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    from alpha.providers.briefs import read_brief_records

    current = read_brief_records("SIVE.ST")[0][-1]
    assert (raw["company_id"], raw["brief_id"], raw["date"]) == (SIVERS, current.brief_id, TODAY.isoformat())
    assert raw["until"] == "2026-10-30"                                       # 不給日子＝30 天後
    receipt = raw["research_receipt"]
    assert receipt["side"] == "看了沒買" and receipt["declared"]["candidate_state"]["state"] == "missing"
    assert env["writes"] == []                                                # 不碰 Sheet
    assert module.main([*args, "--apply"]) == 0 and len(ll.load(path)[0]) == 1   # 同一筆不重寫
    assert module.main([*args, "--why", "等客戶端一手具名。", "--apply"]) == 0 and len(ll.load(path)[0]) == 1
    assert module.main([*args, "--until", "2026-11-15", "--apply"]) == 0 and len(ll.load(path)[0]) == 2  # 改日子
    assert not (env["tmp"] / "trade_log.jsonl").exists()                      # 不寫成交紀錄


def test_record_trade_looked_refuses_a_board_older_than_the_narrative(env) -> None:  # noqa: F811
    """11-04 R2 B1：候選板上那一列是舊版 → exit 2、不寫（先重跑 materialize）。"""
    module, path = env["module"], env["tmp"] / "looked.jsonl"
    module.LOOKED_LOG = path
    env["board_brief"] = "ib_" + "0" * 16
    assert module.main(["looked", "--symbol", "SIVE.ST", "--choice", "不要", "--why", "x", "--apply"]) == 2
    env["candidates_today"] = None                                             # 板讀不到也一樣
    assert module.main(["looked", "--symbol", "SIVE.ST", "--choice", "不要", "--why", "x", "--apply"]) == 2
    assert not path.exists()


def test_record_trade_looked_refuses_beta_an_empty_reason_and_a_missing_narrative(env, capsys) -> None:  # noqa: F811
    module, path = env["module"], env["tmp"] / "looked.jsonl"
    module.LOOKED_LOG = path
    assert module.main(["looked", "--symbol", "QQQ", "--choice", "不要", "--why", "x"]) == 2
    assert module.main(["looked", "--symbol", "SIVE.ST", "--choice", "不要", "--why", "  "]) == 2
    assert module.main(["looked", "--symbol", "AXTI", "--choice", "不要", "--why", "沒敘事"]) == module.EXIT_NARRATIVE
    capsys.readouterr()
    assert module.main(["looked", "--symbol", "7803.T", "--choice", "不要", "--why", "解析不到"]) == 2   # 名冊的事
    assert "INV-1" in capsys.readouterr().err
    assert module.main(["looked", "--symbol", "SIVE.ST", "--choice", "不要", "--why", "x", "--until", "11/20"]) == 2
    assert not path.exists()
