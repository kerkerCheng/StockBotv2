"""入圖包隨機抽查（盲點修法第 20 條③④，2026-11-03；使用者 11-02：「隨機抽查 開subagent這件事 其實你就當成我是開綠燈吧」）。

守的事：①抽不抽中由編號決定——可重現、誰都挑不了，加密時集合只變大；②規則起算日前的包不在母體；③計數器讀 pool 既有欄位
（照建議／偏離／沒寫建議）＋帳上的缺陷；④上個月有缺陷而沒有偏離 → 這個月加密；⑤帳的形狀封閉、壞行不靜默丟、
同一包抽查只一列；⑥`record` 的抽查只收抽中的包（常規 opt-in 只涵蓋抽中的）；⑦抽中待核是 ⑤ 一格，帳讀不懂是未讀到、不是 0。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from engine_b import admission_audit as aa

TODAY = date(2026, 11, 20)


def _stamp(day: str) -> str:
    return f"{day}T12:00:00+00:00"            # 正午 UTC：UTC−11 到 UTC+11 都是同一天（本機日期換算不跨日）


def _ns(every: int, *, hit: bool, start: int = 1000, count: int = 1, also_hit_at: int | None = None) -> list[int]:
    """找出在「每 every 抽 1」下抽中（或沒抽中）的編號；also_hit_at 給了就另外要求在那個比例下相反。"""
    out = []
    n = start
    while len(out) < count:
        ok = aa.sampled(n, every) == hit
        if also_hit_at is not None:
            ok = ok and aa.sampled(n, also_hit_at) != hit
        if ok:
            out.append(n)
        n += 1
    return out


def _item(n: int, *, added: str = "2026-11-10", resolved: str | None = None, resolution: str | None = None,
          verb: str | None = None, kind: str = "ra_admission") -> dict:
    item = {"n": n, "type": kind, "title": f"包 {n}", "added_at": _stamp(added)}
    if resolved:
        item.update(resolved_at=_stamp(resolved), resolution=resolution)
    if verb:
        item["recommendation"] = {"verb": verb, "reason": "x", "at": _stamp(added)}
    return item


def _row(n: int, *, day: str = "2026-11-12", found_by: str = "抽查", verdict: str = "乾淨", defects=(), note="核了逐字 5 段"):
    return aa.parse_row({"n": n, "date": day, "found_by": found_by, "verdict": verdict, "defects": list(defects),
                         "note": note})


# ---------------------------------------------------------------------------
# 抽樣
# ---------------------------------------------------------------------------

def test_sampling_is_reproducible_nested_and_about_one_in_ten() -> None:
    """種子是編號：同一個編號永遠同一個答案；每 10 抽中的每 5 一定也抽中（加密不換人）；比例約 1/10、1/5。
    變異：random() 不帶種子 → 第一條紅；種子帶比例（每個比例各抽一次、加密時換人）→ 巢狀那條紅。"""
    assert [aa.sampled(n, 10) for n in range(1, 200)] == [aa.sampled(n, 10) for n in range(1, 200)]
    ten = {n for n in range(1, 20001) if aa.sampled(n, 10)}
    five = {n for n in range(1, 20001) if aa.sampled(n, 5)}
    assert ten <= five
    assert 0.08 < len(ten) / 20000 < 0.12 and 0.17 < len(five) / 20000 < 0.23


def test_packets_minted_before_the_rule_start_are_not_in_the_population() -> None:
    """規則從 2026-11-03 起算：之前的包不回溯（不在母體、不會跑進 ⑤）。"""
    old, new = _ns(10, hit=True, count=2)
    states = aa.audit_states([_item(old, added="2026-11-02"), _item(new, added="2026-11-03"),
                              _item(_ns(10, hit=True, start=new + 1)[0], kind="manual")], [])
    assert [(s["n"], s["state"]) for s in states] == [(new, "sampled_unreviewed")]


def test_each_packet_has_one_of_four_states_and_a_dropped_packet_needs_no_review() -> None:
    hit_a, hit_b, hit_c = _ns(10, hit=True, count=3)
    miss = _ns(10, hit=False)[0]
    items = [_item(hit_a), _item(hit_b, resolved="2026-11-11", resolution="drop", verb="drop"),
             _item(hit_c, resolved="2026-11-11", resolution="go", verb="go"), _item(miss)]
    states = {s["n"]: s["state"] for s in aa.audit_states(items, [_row(hit_c)])}
    assert states == {hit_a: "sampled_unreviewed", hit_b: "dropped", hit_c: "reviewed", miss: "not_sampled"}
    assert set(states.values()) == set(aa.AUDIT_STATES)


# ---------------------------------------------------------------------------
# 計數器與加密
# ---------------------------------------------------------------------------

def test_month_counts_read_existing_pool_fields_and_defects_from_the_ledger() -> None:
    """照建議／偏離／沒寫建議讀 pool 既有欄位（零 schema 變更）、算當月結案的全部入圖包（不限母體——規則前鑄的也算）；
    缺陷是帳上當月有缺陷的列。別的類型、別的月份不算。"""
    items = [_item(1, added="2026-10-01", resolved="2026-11-05", resolution="go", verb="go"),
             _item(2, resolved="2026-11-06", resolution="drop", verb="go"),
             _item(3, resolved="2026-11-07", resolution="go"),
             _item(4, resolved="2026-10-30", resolution="go", verb="go"),
             _item(5, resolved="2026-11-07", resolution="go", verb="go", kind="manual"),
             _item(6)]
    rows = [_row(7, day="2026-10-31", found_by="事後", verdict="有缺陷", defects=["日期用了抓取日"]),
            _row(8, day="2026-11-02", found_by="事後", verdict="有缺陷", defects=["引文不逐字"]),
            _row(9, day="2026-11-03")]
    assert aa.month_counts(items, rows, "2026-11") == {"followed": 1, "deviated": 1, "unrecommended": 1, "defects": 1}
    assert aa.month_counts(items, rows, "2026-10") == {"followed": 1, "deviated": 0, "unrecommended": 0, "defects": 1}


def test_a_month_with_defects_and_no_deviation_densifies_the_next_month() -> None:
    """上個月抓到缺陷、使用者卻每包都照建議（M=0）→ 這個月每 5 包抽 1；有偏離或沒缺陷就維持每 10。
    加密只改當月鑄的包：12 月鑄、只在每 5 抽中的那一包變成待核；11 月的不變。變異：拿掉 M=0 的條件 → 第二段紅。"""
    followed = _item(1, added="2026-11-04", resolved="2026-11-05", resolution="go", verb="go")
    defect = _row(1, day="2026-11-20", found_by="事後", verdict="有缺陷", defects=["L8 來源只有兩個 origin"])
    assert aa.every_for("2026-12", [followed], [defect]) == aa.EVERY_DENSE
    assert aa.every_for("2026-12", [followed], []) == aa.EVERY
    deviated = _item(2, added="2026-11-04", resolved="2026-11-06", resolution="drop", verb="go")
    assert aa.every_for("2026-12", [followed, deviated], [defect]) == aa.EVERY
    assert aa.every_for("2027-01", [followed], [defect]) == aa.EVERY      # 只看上一個月
    dense_only = _ns(5, hit=True, also_hit_at=10, start=2000)[0]           # 每 5 抽中、每 10 沒抽中
    nov = _item(dense_only + 0, added="2026-11-25")
    states = {s["n"]: s for s in aa.audit_states([followed, nov], [defect])}
    assert states[dense_only]["state"] == "not_sampled" and states[dense_only]["every"] == 10
    dec = _item(dense_only, added="2026-12-02")
    states = {s["n"]: s for s in aa.audit_states([followed, dec], [defect])}
    assert states[dense_only]["state"] == "sampled_unreviewed" and states[dense_only]["every"] == 5


def test_the_status_line_always_prints_and_says_when_the_ledger_is_broken() -> None:
    hit = _ns(10, hit=True)[0]
    items = [_item(hit), _item(1, resolved="2026-11-05", resolution="go", verb="go")]
    report = aa.status(items, [], today=TODAY)
    assert aa.status_line(report) == ("入圖包 11 月：照建議 1｜偏離 0｜沒寫建議 0｜事後抓到包內缺陷 0｜"
                                      f"每 10 包抽 1、抽中待核 1（[{hit}]）")
    empty = aa.status([], [], today=TODAY)
    assert aa.status_line(empty) == "入圖包 11 月：照建議 0｜偏離 0｜沒寫建議 0｜事後抓到包內缺陷 0｜每 10 包抽 1、抽中待核 0"
    assert "⚠ 抽查帳有 1 個問題" in aa.status_line(empty, ["第 2 行：壞了"])


# ---------------------------------------------------------------------------
# 帳：合約與寫入
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("over, message", [
    ({"extra": 1}, "形狀封閉"),
    ({"n": 0}, "正整數"),
    ({"n": True}, "正整數"),
    ({"date": "2026/11/12"}, "YYYY-MM-DD"),
    ({"found_by": "reviewer"}, "found_by"),
    ({"verdict": "pass"}, "verdict"),
    ({"verdict": "有缺陷"}, "不一致"),
    ({"defects": ["引文不逐字"]}, "不一致"),
    ({"defects": [""]}, "每條非空"),
    ({"note": "  "}, "note 不得是空的"),
])
def test_each_field_is_checked_and_the_message_names_it(over, message) -> None:
    raw = {"n": 905, "date": "2026-11-12", "found_by": "抽查", "verdict": "乾淨", "defects": [], "note": "核了"}
    raw.update(over)
    with pytest.raises(ValueError, match=message):
        aa.parse_row(raw)


def test_bad_lines_backward_dates_and_double_audits_are_reported_not_dropped(tmp_path) -> None:
    """壞行不是「少一列」（INV-3）；日期倒退、同一包抽查兩次都紅。檔案不存在是問題，不是空帳。"""
    path = tmp_path / "audit.jsonl"
    good = {"n": 905, "date": "2026-11-12", "found_by": "抽查", "verdict": "乾淨", "defects": [], "note": "核了"}
    lines = [json.dumps(good, ensure_ascii=False), "{壞掉",
             json.dumps({**good, "date": "2026-11-10"}, ensure_ascii=False)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows, problems = aa.load_ledger(path)
    assert [r.n for r in rows] == [905, 905]
    assert any(p.startswith("第 2 行") for p in problems)
    assert any("早於前一列" in p for p in problems)
    assert any("抽查記了兩次" in p for p in problems)
    assert aa.load_ledger(tmp_path / "nope.jsonl") == ([], ["nope.jsonl 不存在"])


def test_record_takes_audits_only_for_sampled_packets_and_appends_one_valid_line(tmp_path) -> None:
    """常規 opt-in 只涵蓋抽中的包：沒抽中的包記「抽查」拒收（要 reviewer 是另一次委派）；事後發現的缺陷任何入圖包都收；
    不是入圖包的編號拒收；同一包抽查第二次拒收。變異：拿掉「沒抽中拒收」→ 紅。"""
    path = tmp_path / "audit.jsonl"
    path.write_text("", encoding="utf-8")
    hit, miss = _ns(10, hit=True)[0], _ns(10, hit=False)[0]
    items = [_item(hit), _item(miss), _item(1, kind="manual")]
    with pytest.raises(ValueError, match="沒有抽中"):
        aa.record(n=miss, found_by="抽查", verdict="乾淨", defects=[], note="核了", today=TODAY, items=items, path=path)
    with pytest.raises(ValueError, match="不是入圖包"):
        aa.record(n=1, found_by="事後", verdict="乾淨", defects=[], note="核了", today=TODAY, items=items, path=path)
    aa.record(n=hit, found_by="抽查", verdict="有缺陷", defects=["  引文  不逐字 "], note="[906] 取代", today=TODAY,
              items=items, path=path)
    with pytest.raises(ValueError, match="已經抽查過"):
        aa.record(n=hit, found_by="抽查", verdict="乾淨", defects=[], note="再核", today=TODAY, items=items, path=path)
    aa.record(n=miss, found_by="事後", verdict="有缺陷", defects=["日期用了抓取日"], note="failure log #130",
              today=TODAY, items=items, path=path)
    rows, problems = aa.load_ledger(path)
    assert problems == [] and [(r.n, r.found_by) for r in rows] == [(hit, "抽查"), (miss, "事後")]
    assert rows[0].defects == ("引文 不逐字",)
    assert {s["n"]: s["state"] for s in aa.audit_states(items, rows)}[hit] == "reviewed"


def test_the_ledger_in_the_repo_passes_the_contract() -> None:
    """真的那一本（2026-11-03 起，起始是空的）：每一列過合約、日期不倒退。"""
    rows, problems = aa.load_ledger()
    assert problems == [], problems
    assert all(r.date >= aa.RULE_START for r in rows)


# ---------------------------------------------------------------------------
# ⑤ 一格
# ---------------------------------------------------------------------------

def test_sampled_unreviewed_packets_are_a_todo_cell_and_an_unreadable_ledger_is_not_zero() -> None:
    from engine_b import todo_ledger as tl

    hit = _ns(10, hit=True)[0]
    items = [_item(hit, added="2026-11-10"), _item(_ns(10, hit=False)[0])]

    def collect(loader):
        return {row.key: row for row in tl.collect(
            today=TODAY, leads_store={"leads": {}}, watches=[], todo_items=items, hypotheses=[], briefs=[],
            reading_needs_reread=0, layer_note_reread=0,
            candidates={"counts": {}, "new_edges_check": {"status": "ok"},
                        "reading_change_check": {"status": "ok", "unchecked": 0}}, thesis_due=[],
            loaders={"classification_gaps": lambda: [], "undisposed": lambda: [], "parked_without_expiry": lambda: [],
                     "stale_lead_entities": lambda: 0, "story_gaps": lambda: [], "admission_audit_ledger": loader})}

    cell = collect(lambda: ([], []))["todo.admission_audit"]
    assert (cell.count, cell.work, cell.oldest_days) == (1, f"[{hit}]", 10)
    assert collect(lambda: ([_row(hit)], []))["todo.admission_audit"].count == 0
    broken = collect(lambda: ([], ["admission-audit.jsonl 不存在"]))["todo.admission_audit"]
    assert broken.count is None and "不存在" in broken.reason
