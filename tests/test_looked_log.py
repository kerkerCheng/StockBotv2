"""看了沒買（盲點修法第 17 條，2026-11-03；AGENTS「沒買也是決定」）——A5 的第二本：`library/trades/looked_log.jsonl`。

守的事：①寫入端拒收缺理由、缺敘事版本、不在封閉字彙的選擇、解析不到的公司；②與成交同一支入口、同一種收據
（`record_trade.py looked`，`side`＝看了沒買）；③append-only：重寫同一筆被擋、壞行與重複不靜默丟；④讀者只有計數——
「你的決定」三格（進＝alpha 成交買進、不要、等到條件），0 也印。全部用暫存檔、假 Sheet——不讀真的 Sheet、不寫真的 log。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from portfolio import looked_log as ll
from tests.test_record_trade_receipt import SIVERS, TODAY, env  # noqa: F401 — env 是 fixture

RECEIPT = {"version": "research-receipt/v1", "side": "看了沒買", "narrative": "present", "narrative_label": "有現行 v2 敘事",
           "company_id": "co:aaa", "research_ticker": "AAA",
           "declared": {"brief_id": "ib_aaa1", "candidate_state": {"state": "open"}}}


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
    with pytest.raises(ValueError, match="INV-1"):
        _entry(receipt={**RECEIPT, "company_id": None})


def test_the_log_is_append_only_and_bad_or_repeated_lines_are_reported(tmp_path) -> None:
    path = tmp_path / "looked.jsonl"
    assert ll.load(path) == ([], [])                         # 不存在＝還沒有任何一次決定
    first = _entry()
    ll.append(first, path)
    ll.append(_entry(choice="等到條件", why="等客戶 10-K 具名第二家"), path)
    entries, problems = ll.load(path)
    assert problems == [] and [e.choice for e in entries] == ["不要", "等到條件"]
    assert ll.already_recorded(first, path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{壞掉\n" + json.dumps(first, ensure_ascii=False) + "\n")
    entries, problems = ll.load(path)
    assert any("第 3 行" in p for p in problems) and any("重複" in p for p in problems)
    with pytest.raises(ValueError, match="形狀封閉"):
        ll.parse_entry({**first, "size": 100})               # 不收尺寸、不收任何額外欄


def test_your_decisions_count_alpha_buys_from_the_trade_log_and_both_choices_from_this_log() -> None:
    """進＝帶研究收據的買進（beta 不帶收據、賣出不算）；不要／等到條件＝這本。只數當月。變異：進改成數全部買進 → 紅。"""
    events = [{"side": "buy", "executed_at": "2026-11-02T10:00:00-04:00", "research_receipt": {"narrative": "present"}},
              {"side": "buy", "executed_at": "2026-11-02T10:00:00-04:00"},                       # beta
              {"side": "sell", "executed_at": "2026-11-02T10:00:00-04:00", "research_receipt": {}},
              {"side": "buy", "executed_at": "2026-10-20T10:00:00-04:00", "research_receipt": {}}]
    entries = [ll.parse_entry(_entry()), ll.parse_entry(_entry(choice="等到條件", why="等 10-K")),
               ll.parse_entry(_entry(today=date(2026, 10, 30)))]
    assert ll.month_counts(entries, events, "2026-11") == {"進": 1, "不要": 1, "等到條件": 1}
    line = ll.status_line({"進": 0, "不要": 0, "等到條件": 0}, month="2026-11")
    assert line.startswith("你的決定 11 月：進 0｜不要 0｜等到條件 0")
    assert "⚠ 帳有 1 個問題" in ll.status_line({}, month="2026-11", problems=["第 2 行壞了"])


def test_short_line_reads_both_logs(tmp_path) -> None:
    looked, trade = tmp_path / "looked.jsonl", tmp_path / "trade.jsonl"
    ll.append(_entry(), looked)
    trade.write_text(json.dumps({"side": "buy", "executed_at": "2026-11-03T09:00:00+08:00",
                                 "research_receipt": {"narrative": "present"}}) + "\n", encoding="utf-8")
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
    receipt = raw["research_receipt"]
    assert receipt["side"] == "看了沒買" and receipt["declared"]["candidate_state"]["state"] == "missing"
    assert env["writes"] == []                                                # 不碰 Sheet
    assert module.main([*args, "--apply"]) == 0 and len(ll.load(path)[0]) == 1   # 同一筆不重寫
    assert not (env["tmp"] / "trade_log.jsonl").exists()                      # 不寫成交紀錄


def test_record_trade_looked_refuses_beta_an_empty_reason_and_a_missing_narrative(env) -> None:  # noqa: F811
    module, path = env["module"], env["tmp"] / "looked.jsonl"
    module.LOOKED_LOG = path
    assert module.main(["looked", "--symbol", "QQQ", "--choice", "不要", "--why", "x"]) == 2
    assert module.main(["looked", "--symbol", "SIVE.ST", "--choice", "不要", "--why", "  "]) == 2
    assert module.main(["looked", "--symbol", "7803.T", "--choice", "不要", "--why", "沒敘事"]) == module.EXIT_NARRATIVE
    assert not path.exists()
