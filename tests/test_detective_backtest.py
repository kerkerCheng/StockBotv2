"""偵探回溯（起漲點前看）的純規則與命令列（plan docs/plans/2026-11-18-001-dev-detective-backtest-plan.md §3）。

變異：每一條規則拿掉一個條件都要有一條測試變紅——起漲點的 182 天窗與 2 倍、對照的 1.3 倍與附近起漲點、
湊滿不說誰是誰、遮名殘留掃描、偏多強度的抽屜與信心、回溯日當時的鄰居。
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from alpha import detective_backtest as bt
from alpha.cli import main


def _series(start: date, closes: list[float], step: int = 1) -> list[tuple[date, float]]:
    return [(start + timedelta(days=i * step), c) for i, c in enumerate(closes)]


D0 = date(2026, 1, 5)


def _rise(n_flat: int, low: float, top: float, n_rise: int) -> list[float]:
    return [100.0] * n_flat + [low] + [low + (top - low) * (i + 1) / n_rise for i in range(n_rise)]


# ---- 起漲點 ---------------------------------------------------------------------------------------
def test_rally_start_is_the_lowest_close_of_the_qualifying_run() -> None:
    bars = _series(D0, _rise(30, 95.0, 200.0, 100))
    assert bt.rally_starts(bars) == [D0 + timedelta(days=30)]


def test_just_below_double_is_not_a_rally() -> None:
    bars = _series(D0, _rise(30, 100.0, 199.0, 100))
    assert bt.rally_starts(bars) == []


def test_double_beyond_182_days_is_not_a_rally() -> None:
    # 每 3 天一根、130 根＝390 天才到 2 倍：任何一天往後 182 天內都到不了 2 倍
    bars = _series(D0, [100.0 + i * (100.0 / 129) for i in range(130)], step=3)
    assert bt.rally_starts(bars) == []


def test_two_separate_runs_give_two_starts() -> None:
    first = _rise(10, 90.0, 200.0, 40)
    crash = [100.0] * 220                       # 跌回、橫盤超過 182 天：中間沒有合格日
    second = [80.0] + [80.0 + 100.0 * (i + 1) / 40 for i in range(40)]
    bars = _series(D0, first + crash + second)
    starts = bt.rally_starts(bars)
    assert len(starts) == 2
    assert starts[0] == D0 + timedelta(days=10)
    assert starts[1] == D0 + timedelta(days=len(first) + len(crash))


def test_unusable_closes_are_ignored() -> None:
    bars = _series(D0, _rise(30, 95.0, 200.0, 100))
    bars[50] = (bars[50][0], float("nan"))
    bars[51] = (bars[51][0], None)              # type: ignore[assignment]
    assert bt.rally_starts(bars) == [D0 + timedelta(days=30)]


# ---- 對照 -----------------------------------------------------------------------------------------
def test_control_window_flat_is_ok_and_reports_observed_days() -> None:
    bars = _series(D0, [100.0] * 120)
    ok, observed, why = bt.control_window(bars, D0 + timedelta(days=10), lead_days=56)
    assert ok and why == ""
    assert observed == 109                      # 窗口沒走完：照實回天數


def test_control_window_rejects_a_rise_over_ceiling() -> None:
    bars = _series(D0, [100.0] * 20 + [131.0] * 20)
    ok, _observed, why = bt.control_window(bars, D0 + timedelta(days=5), lead_days=56)
    assert not ok and "門檻" in why


def test_control_window_length_follows_the_group_lead() -> None:
    # 回溯日 +28+182=210 天之後才漲：清淨組（4 週）窗口外、算對照；遮名組（8 週，238 天）窗口內、不算
    bars = _series(D0, [100.0] * 220 + [140.0] * 30)
    assert bt.control_window(bars, D0, lead_days=28)[0] is True
    assert bt.control_window(bars, D0, lead_days=56)[0] is False


def test_control_needs_a_close_on_or_shortly_before_as_of() -> None:
    bars = _series(D0, [100.0] * 10) + _series(D0 + timedelta(days=40), [100.0] * 10)
    ok, _observed, why = bt.control_window(bars, D0 + timedelta(days=30), lead_days=56)
    assert not ok and "沒有收盤" in why


# ---- 找案例、封存順序、湊滿 ---------------------------------------------------------------------------
S0 = date(2025, 12, 1)


def _universe_and_bars():
    winner = _series(S0, _rise(160, 95.0, 200.0, 60))                # 起漲點 2026-05-10 → 遮名組、回溯日 03-15
    clean_winner = _series(S0, [100.0] * 302 + [90.0] + [90.0 + 100.0 * (i + 1) / 20 for i in range(20)])  # 09-29 → 清淨組 09-01
    both = _series(S0, _rise(92, 95.0, 200.0, 60) + [200.0] * 200)    # 03-03 起漲（遮名組贏家），之後橫盤（清淨組對照）
    flat = _series(S0, [100.0] * 352)
    members = [
        bt.UniverseMember("WIN", "co:win", frozenset({"c1"})),
        bt.UniverseMember("CLN", "co:cln", frozenset({"c1"})),
        bt.UniverseMember("BOTH", "co:both", frozenset({"c1"})),
        bt.UniverseMember("FLT", "co:flt", frozenset({"c1"})),
        bt.UniverseMember("Q3W", "co:q3w", frozenset({"c1"})),
        bt.UniverseMember("NOB", "co:nob", frozenset({"c1"})),
        bt.UniverseMember("OUT", "co:out", frozenset({"c2"})),
    ]
    bars = {"WIN": winner, "CLN": clean_winner, "BOTH": both, "FLT": flat, "Q3W": winner, "NOB": [], "OUT": flat}
    return members, bars


def test_find_cases_labels_groups_and_counts() -> None:
    members, bars = _universe_and_bars()
    cases, counts = bt.find_cases(members, bars, excluded=["q3w"])
    assert counts["excluded"] == 1 and counts["no_bars"] == 1
    winners = {c["ticker"]: c for c in cases if c["label"] == "winner"}
    assert set(winners) == {"WIN", "CLN", "BOTH"}
    assert winners["WIN"]["group"] == "masked" and winners["CLN"]["group"] == "clean"
    start = date.fromisoformat(winners["WIN"]["rally_start"])
    assert winners["WIN"]["as_of"] == (start - timedelta(days=56)).isoformat(), "遮名組提前 8 週"
    start = date.fromisoformat(winners["CLN"]["rally_start"])
    assert winners["CLN"]["as_of"] == (start - timedelta(days=28)).isoformat(), "清淨組提前 4 週"
    controls = {(c["ticker"], c["group"]) for c in cases if c["label"] == "control"}
    # CLN 到 09-29 才起漲：BOTH 那一段（回溯日 1 月）的窗口裡它沒動，是遮名組的對照
    assert controls == {("FLT", "masked"), ("FLT", "clean"), ("BOTH", "clean"), ("CLN", "masked")}, \
        "對照只從同一個主題等權組挑（OUT 在別組）；另一段的贏家可以當這一段的對照"
    for c in cases:
        if c["label"] == "control":
            paired = winners[c["paired_with"]]
            gap = abs((date.fromisoformat(c["as_of"]) - date.fromisoformat(paired["as_of"])).days)
            assert gap <= bt.CONTROL_JITTER_DAYS or c["as_of"] == bt.CLEAN_FROM.isoformat()
            if c["group"] == "clean":
                assert date.fromisoformat(c["as_of"]) >= bt.CLEAN_FROM


def test_case_as_of_boundary() -> None:
    assert bt.case_as_of(date(2026, 7, 29)) == ("clean", date(2026, 7, 1))
    assert bt.case_as_of(date(2026, 7, 28)) == ("masked", date(2026, 6, 2))
    assert bt.group_of(date(2026, 7, 1)) == "clean"
    assert bt.group_of(date(2026, 6, 30)) == "masked"


def test_order_key_and_jitter_are_deterministic() -> None:
    a = bt.order_key("AXTI", date(2026, 9, 1))
    assert a == bt.order_key("AXTI", date(2026, 9, 1)) and a != bt.order_key("AXTI", date(2026, 9, 2))
    js = {bt.jitter_days(t, date(2026, 9, 1)) for t in ("A", "B", "C", "D", "E", "F", "G", "H")}
    assert all(-14 <= j <= 14 for j in js) and len(js) > 1


def _case(label: str, key: str, group: str = "clean", status: str | None = None) -> dict:
    c = {"case_id": key, "ticker": key.upper(), "label": label, "group": group, "key": key, "as_of": "2026-09-01"}
    if status:
        c["status"] = status
    return c


def test_next_case_fills_quota_without_revealing_label() -> None:
    cases = [_case("winner", k) for k in ("a1", "a2", "a3", "a4")] + [_case("control", k) for k in ("b1", "b2", "b3")]
    picked = []
    while (c := bt.next_case(cases, "clean")) is not None:
        c["status"] = "accepted"
        picked.append(c["key"])
    assert picked == ["a1", "a2", "a3", "b1", "b2"], "照雜湊順序、贏家滿了就跳過"
    assert bt.still_needed(cases, "clean") == 0


def test_same_ticker_is_taken_once_per_group() -> None:
    cases = [_case("winner", "a1"), {**_case("control", "a2"), "ticker": "A1"}, _case("control", "b1")]
    cases[0]["status"] = "accepted"
    assert bt.next_case(cases, "clean")["key"] == "b1", "A1 已經以贏家收過，同組不再以對照收"


def test_skipped_case_is_replaced_by_the_next_one() -> None:
    cases = [_case("winner", "a1", status="skipped"), _case("winner", "a2")]
    assert bt.next_case(cases, "clean")["key"] == "a2"
    assert bt.still_needed(cases, "clean") == 5


# ---- 遮名 -----------------------------------------------------------------------------------------
ENTRIES = [
    bt.MaskEntry("co:axt", "A", ("AXT", "AXT Inc", "AXT Inc."), ("AXTI",)),
    bt.MaskEntry("co:yunnan_germanium", "B", ("雲南鍺業", "Yunnan Germanium"), ("002428.SZ",)),
]
TEXT = ("AXT Inc. (NASDAQ: AXTI) and its subsidiary sell InP. axt's Tongmei plant ships to 雲南鍺業（002428）."
        " See co:axt and co:yunnan_germanium; ＡＸＴ guidance.")


def test_mask_text_replaces_names_tickers_ids_and_fullwidth() -> None:
    out = bt.mask_text(TEXT, ENTRIES)
    assert bt.residual_forms(out, ENTRIES) == {}
    assert "公司A" in out and "代號A" in out and "公司B" in out and "代號B" in out
    assert "InP" in out, "產品名不遮（plan §6：遮不住產品是要量的記憶份量）"


def test_residual_scan_catches_a_missed_alias() -> None:
    # 變異：遮名時漏了一個別名（雲南鍺業），掃描用完整名冊 → 必須抓到
    partial = [ENTRIES[0], bt.MaskEntry("co:yunnan_germanium", "B", ("Yunnan Germanium",), ("002428.SZ",))]
    out = bt.mask_text(TEXT, partial)
    assert bt.residual_forms(out, ENTRIES) == {"雲南鍺業": 1}


def test_mask_does_not_eat_words_that_merely_contain_a_name() -> None:
    entries = [bt.MaskEntry("co:iqe", "A", ("IQE",), ("IQE.L",))]
    out = bt.mask_text("UNIQUE tech; IQE plc (IQE.L) grows", entries)
    assert out.startswith("UNIQUE tech; 公司A plc (代號A) grows")


def test_derive_stems_cjk_and_ascii() -> None:
    ascii_stems, cjk = bt.derive_stems(["大量科技", "大量科技股份有限公司", "Ta Liang Technology Co., Ltd.",
                                        "臻鼎", "臻鼎-KY", "Zhen Ding Technology Holding Limited", "Lumentum Holdings"])
    assert cjk == ("大量",), "臻鼎本身就是登記的寫法，不另列"
    assert set(ascii_stems) == {"Ta Liang", "Zhen Ding"}, "單字本體（Lumentum）不收"


def test_subsidiary_names_are_caught_by_stems() -> None:
    # 2026-11-18 3167.TW 遮名包實測：名冊只有「大量科技」，財報裡的子公司「南京大量數控科技有限公司」漏網
    names = ("大量科技", "大量科技股份有限公司")
    _a, stems = bt.derive_stems(names)
    text = "本公司之子公司南京大量數控科技有限公司、大量科技股份有限公司"
    without = bt.mask_text(text, [bt.MaskEntry("co:tl", "A", names)])
    assert "大量" in without, "變異：沒有本體就漏網"
    entry = bt.MaskEntry("co:tl", "A", names, stems=stems)
    assert bt.residual_forms(without, [entry]) == {"大量": 1}, "殘留掃描用本體抓得到"
    out = bt.mask_text(text, [entry])
    assert out == "本公司之子公司南京〔A〕數控科技有限公司、公司A"
    assert bt.residual_forms(out, [entry]) == {}


def test_names_match_across_extra_spaces() -> None:
    # PDF 轉文字：「Zhen  Ding  Technology」兩格空白（2026-11-18 3167.TW 遮名包實測漏網）
    entry = bt.MaskEntry("co:zd", "B", ("Zhen Ding Technology", "Zhen Ding"))
    text = "更名為 Zhen  Ding  Technology Holding；Zhen\nDing"
    assert bt.residual_forms(text, [entry]), "掃描要抓得到多格空白的寫法"
    assert bt.residual_forms(bt.mask_text(text, [entry]), [entry]) == {}


def test_cjk_names_match_with_spaces_between_characters() -> None:
    # 財報表頭 PDF 轉文字：「臻 鼎 科 技 控 股」（2026-11-18 遮名組偵探點出來）
    entry = bt.MaskEntry("co:zd", "B", ("臻鼎科技控股股份有限公司", "臻鼎"))
    text = "公司B\n臻 鼎 科 技 控 股 股 份 有 限 公 司 及 子 公 司"
    assert bt.residual_forms(text, [entry]), "掃描要抓得到字間空格"
    out = bt.mask_text(text, [entry])
    assert bt.residual_forms(out, [entry]) == {}
    assert "臻" not in out


def test_mask_letters() -> None:
    assert [bt.mask_letter(i) for i in (0, 1, 25, 26, 27)] == ["A", "B", "Z", "AA", "AB"]


def test_mask_with_real_registry_leaves_no_name(monkeypatch) -> None:
    from alpha.detective import Neighbor
    from alpha.providers.detective_backtest import leak_check, mask_entries
    from identity.registry import get_registry

    reg = get_registry()
    target = reg.company_id_for_ticker("AXTI")
    peer = reg.company_id_for_ticker("002428.SZ")
    if not target or not peer:
        pytest.skip("名冊沒有 AXTI 或 002428.SZ")
    entries = mask_entries(target, [Neighbor(peer, "雲南鍺業", {"competitor"})])
    names = [n for e in entries for n in e.names]
    text = "；".join(names) + f"；{target}；AXTI；002428"
    out = bt.mask_text(text, entries)
    assert leak_check({"doc": out}, entries) == {}
    assert leak_check({"doc": text}, entries), "沒遮的原文必須被抓到（殘留掃描不是空轉）"


# ---- 偏多強度與配對 ---------------------------------------------------------------------------------
REPORT = """# 回報
### 線索（4 條）
#### 1
- 抽屜：量超前
- 信心：高（兩方文件對得起來）
#### 2
- **抽屜**：漲價
- **信心**：**高**——合約單價
#### 3｜撐更久
- 觀察：「…」
- 信心：中
#### 4
- 抽屜：窗口提早關
- 信心：高
### 逐題回答
- 信心：高（這一段不是線索，不算）
"""


def test_lean_tally_counts_drawers_and_confidence() -> None:
    t = bt.lean_tally(REPORT)
    assert t["clues"] == 4 and t["unparsed"] == 0
    assert t["lean_high"] == 1, "高：量超前＋漲價 − 窗口提早關"
    assert t["lean_mid"] == 1, "中：撐更久（抽屜寫在標題）"


def test_lean_tally_reports_unparsed_and_missing_section() -> None:
    assert bt.lean_tally("沒有線索段")["section_found"] is False
    t = bt.lean_tally("### 線索\n- 觀察：沒寫抽屜\n- 信心：高\n")
    assert t["clues"] == 1 and t["unparsed"] == 1


def test_pair_wins_and_verdict_lines() -> None:
    wins, total = bt.pair_wins([3, 2, 1], [0, 1])
    assert (wins, total) == (5.5, 6)
    assert bt.separation_verdict(wins, total).startswith("有分辨的跡象")
    assert bt.separation_verdict(3, 6) == "看不出分辨"
    assert bt.separation_verdict(4, 6) == "不確定"
    assert bt.separation_verdict(0, 0).startswith("沒有配對")


# ---- 回溯日當時的鄰居 ---------------------------------------------------------------------------------
def test_known_rows_needs_every_edge_known_by_as_of() -> None:
    dates = {"old": date(2025, 1, 1), "new": date(2026, 10, 1), "nodate": None}
    rows = [
        {"nid": "co:a", "edge_docs": [["old"]]},
        {"nid": "co:b", "edge_docs": [["new"]]},                    # 回溯日之後才有來源
        {"nid": "co:c", "edge_docs": [["old"], ["new"]]},           # 第二跳：兩條都要
        {"nid": "co:d", "edge_docs": [["nodate", "old"]]},          # 一條邊有一份當時的來源就算
        {"nid": "co:e", "edge_docs": [[]]},                         # 沒有來源：不算
        {"nid": "co:f"},                                            # 舊格式沒有 edge_docs：不算
    ]
    kept, dropped = bt.known_rows(rows, dates, date(2026, 7, 1))
    assert [r["nid"] for r in kept] == ["co:a", "co:d"]
    assert dropped == 4


# ---- 命令列：不印價格、不說誰是贏家 ---------------------------------------------------------------------
def test_next_and_mark_print_no_label(tmp_path, monkeypatch, capsys) -> None:
    from alpha.providers import detective_backtest as pbt

    sealed = tmp_path / "cases_sealed.json"
    cases = [{**_case("winner", "a1"), "rally_start": "2026-10-27", "case_id": "C-aaaaaa", "ticker": "WINR"},
             {**_case("control", "b1"), "case_id": "C-bbbbbb", "ticker": "CTRL", "paired_with": "WINR"}]
    sealed.write_text(json.dumps({"counts": {}, "cases": cases}), encoding="utf-8")
    monkeypatch.setattr(pbt, "SEALED", sealed)
    monkeypatch.setattr(pbt.read_sealed, "__defaults__", (sealed,))
    monkeypatch.setattr(pbt.write_sealed, "__defaults__", (sealed,))
    monkeypatch.setattr(pbt.next_for, "__kwdefaults__", {"path": sealed})
    monkeypatch.setattr(pbt.mark, "__kwdefaults__", {"path": sealed})
    assert main(["detective", "next", "--group", "clean"]) == 0
    out = capsys.readouterr().out
    assert "C-aaaaaa" in out and "WINR" in out
    for secret in ("winner", "贏家", "rally_start", "2026-10-27", "CTRL"):
        assert secret not in out, secret
    assert main(["detective", "mark", "C-aaaaaa", "--pass", "--reason", "鄰居 3、文件 40"]) == 0
    out = capsys.readouterr().out
    assert "winner" not in out and "贏家" not in out
    data = json.loads(sealed.read_text(encoding="utf-8"))
    assert data["cases"][0]["status"] == "accepted"


def test_q3w_list_parses_the_frozen_list() -> None:
    from alpha.providers.detective_backtest import q3w_tickers

    tickers = q3w_tickers()
    assert len(tickers) == 28 and "AXTI" in tickers and "002428.SZ" in tickers


def test_cli_has_backtest_actions() -> None:
    from alpha.cli import build_parser

    parser = build_parser()
    for argv in (["detective", "rallies"], ["detective", "next", "--group", "clean"],
                 ["detective", "mark", "C-1", "--pass"], ["detective", "backfill", "C-1"],
                 ["detective", "tally", "R.md"], ["detective", "score", "--group", "masked"],
                 ["detective", "pack", "AXTI", "--as-of", "2026-07-01", "--case", "C-1", "--mask"]):
        assert parser.parse_args(argv).action == argv[1]


def test_mask_requires_case(capsys) -> None:
    assert main(["detective", "pack", "AXTI", "--as-of", "2026-07-01", "--mask"]) == 2
    assert "--case" in capsys.readouterr().err
