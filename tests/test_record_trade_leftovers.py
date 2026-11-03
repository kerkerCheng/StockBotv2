"""成交紀錄遺留八項（2026-11-03 批次三 D；ROADMAP「成交紀錄遺留八項」；原列逐字封存於 archive/roadmap-backlog-log.md）。

R2 覆核 non-blocking 的八個小洞，都不會寫錯 Sheet 金額，但會讓「寫了沒有」「是不是同一檔」「這個數字可不可信」說不清：
①既有列寫到一半丟網路例外——回讀每一格決定（沒寫／全寫／寫一半就補寫其餘格／認不得就請人看），不再只印「請手動核對」；
②5% 單筆上限的已持有加總、③beta 判別——同一檔的兩種寫法（`TYO:7803` 與 `7803.T`、`TPE:0050` 與 `0050.TW`）當同一檔；
④分數股在 Sheet 四捨五入顯示時，開列失敗後的回讀認得出自己那一列；⑥那一列的市值是手寫值（不是公式）時拒絕改股數；
⑧`--fx-to-base` 用同一列「市值 ÷ 股數 ÷ 成交價」反推的匯率核對（差兩倍以上拒收）；⑨使用者自己刪了列之後用
`--log-only --row-deleted` 補記；⑩`--log-only` 不再印股數與成本的「舊 → 新」對照。
"""
from __future__ import annotations

import json

import pytest

from fetchers import gsheets
from tests.test_record_trade import _BUY, _present_inputs, _sheet_rows, _wire_sheet

# ---------------------------------------------------------------------------
# ① 既有列寫到一半丟網路例外：回讀決定
# ---------------------------------------------------------------------------


def _wire_partial(monkeypatch, tmp_path, *, mode: str, readback: dict | None = None, second_fails: bool = False,
                  late_after_reads: int | None = None, recheck: float = 0.0):
    """既有列 --apply：假 Sheet 有狀態——寫入照 mode 寫幾格後丟例外，回讀讀狀態（`readback` 可蓋掉某一格）。

    `late_after_reads`：伺服器更晚才套用——第一次寫入丟例外時一格都沒落地，回讀滿這麼多格之後才整批套用（R2 覆核 B2）。
    `recheck`：`ABSENT_RECHECK_SECONDS`（預設 0＝不再讀，測試不睡）；`time.sleep` 換成記下秒數。"""
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=1_000.0))
    module.ABSENT_RECHECK_SECONDS = recheck
    cells = {"B2": "10.0", "C2": "100", "D5": "50000"}
    calls["write_calls"], calls["slept"], calls["late"] = [], [], []
    import time as _time

    monkeypatch.setattr(_time, "sleep", lambda s: calls["slept"].append(s))

    def write(writes):
        calls["write_calls"].append([dict(w) for w in writes])
        if len(calls["write_calls"]) > 1:                     # 補寫那一次
            if second_fails:
                raise ConnectionError("補寫也斷線")
            for w in writes:
                assert cells[w["a1"]] == w["expected"], "補寫要以寫入前的值當 expected（逐格重讀照舊）"
                cells[w["a1"]] = str(w["value"])
            return {"status": "written", "written": [{"a1": w["a1"], "from": w["expected"], "to": w["value"]}
                                                     for w in writes]}
        landed = {"none": 0, "first": 1, "all": len(writes)}[mode]
        for w in writes[:landed]:
            cells[w["a1"]] = str(w["value"])
        if late_after_reads is not None:
            calls["late"] = [dict(w) for w in writes]
        raise ConnectionError("回應中斷")

    reads = []

    def read(a1):
        reads.append(a1)
        if calls["late"] and late_after_reads is not None and len(reads) > late_after_reads:
            for w in calls["late"]:
                cells[w["a1"]] = str(w["value"])
            calls["late"] = []
        return (readback or {}).get(a1, cells[a1])

    monkeypatch.setattr(gsheets, "write_portfolio_cells", write)
    monkeypatch.setattr(gsheets, "read_cell_value", read)
    calls["cells"], calls["reads_cells"] = cells, reads
    return module, calls


def _log(module) -> list[dict]:
    if not module.TRADE_LOG.exists():
        return []
    return [json.loads(line) for line in module.TRADE_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_nothing_landed_says_so_records_nothing_and_does_not_promise_a_safe_rerun(monkeypatch, tmp_path, capsys) -> None:
    """R2 覆核 B2：原本說「照原命令重跑……不會重複寫」——錯：重跑會重讀 Sheet，伺服器更晚才套用時就算兩次。
    現在隔幾秒再讀一次（同建倉路徑），仍全舊才說沒寫進去，而且叫人重跑前先核對那幾格、列出寫入前的值。"""
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="none", recheck=3.0)
    assert module.main(_BUY + ["--apply"]) == 2
    assert _log(module) == [] and len(calls["write_calls"]) == 1
    assert calls["slept"] == [3.0] and len(calls["reads_cells"]) == 6            # 讀兩輪、每輪三格
    err = capsys.readouterr().err
    assert "三格回讀（第一次與隔 3 秒再讀）都還是寫入前的值" in err
    assert "重跑 --apply 之前先看一眼 Sheet" in err and "B2＝10.0" in err and "不會重複寫" not in err


def test_a_write_the_server_applies_a_few_seconds_late_is_found_by_the_second_read(monkeypatch, tmp_path) -> None:
    """B2 的對稱面：第一輪回讀三格都還是舊值、伺服器幾秒後才套用——第二輪讀到全新，照常記事件（不叫人重跑、不算兩次）。"""
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="none", late_after_reads=3, recheck=3.0)
    assert module.main(_BUY + ["--apply"]) == 0
    entry, = _log(module)
    assert "隔 3 秒再讀" in entry["sheet_write_note"] and "三格都是新值" in entry["sheet_write_note"]
    assert calls["cells"] == {"B2": "20.0", "C2": "150.0", "D5": "48000.0"} and len(calls["write_calls"]) == 1


def test_without_a_recheck_the_message_says_it_only_read_once(monkeypatch, tmp_path, capsys) -> None:
    module, _calls = _wire_partial(monkeypatch, tmp_path, mode="none")
    assert module.main(_BUY + ["--apply"]) == 2
    assert "（只讀了一次）" in capsys.readouterr().err


def test_everything_landed_is_recorded_with_a_readback_note(monkeypatch, tmp_path, capsys) -> None:
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="all")
    assert module.main(_BUY + ["--apply"]) == 0
    entry, = _log(module)
    assert "回讀確認已套用" in entry["sheet_write_note"] and len(entry["sheet_writes"]) == 3
    assert all(w.get("confirmed_by_readback") for w in entry["sheet_writes"])
    assert len(calls["write_calls"]) == 1


def test_half_landed_is_completed_from_the_old_values_and_then_recorded(monkeypatch, tmp_path) -> None:
    """寫一半＝補寫其餘格（以寫入前的值當 expected、照舊逐格重讀），回讀全是新值才記事件——不用顯示值還原
    （Sheet 讀回的是格式化後的字串，分數股寫回會失真）。"""
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="first")
    assert module.main(_BUY + ["--apply"]) == 0
    second = calls["write_calls"][1]
    assert [w["a1"] for w in second] == ["C2", "D5"] and [w["expected"] for w in second] == ["100", "50000"]
    assert calls["cells"] == {"B2": "20.0", "C2": "150.0", "D5": "48000.0"}
    entry, = _log(module)
    assert "補寫其餘 2 格" in entry["sheet_write_note"] and len(entry["sheet_writes"]) == 3


def test_a_cell_that_reads_back_as_neither_value_stops_without_writing_more(monkeypatch, tmp_path, capsys) -> None:
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="first", readback={"C2": "999"})
    assert module.main(_BUY + ["--apply"]) == 2
    assert _log(module) == [] and len(calls["write_calls"]) == 1, "認不得的格不補寫"
    err = capsys.readouterr().err
    assert "C2" in err and "999" in err and "請手動核對" in err


def test_a_failed_completion_stops_and_names_every_cell(monkeypatch, tmp_path, capsys) -> None:
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="first", second_fails=True)
    assert module.main(_BUY + ["--apply"]) == 2
    assert _log(module) == [] and len(calls["write_calls"]) == 2
    err = capsys.readouterr().err
    assert "補寫失敗" in err and "B2" in err and "請手動核對" in err


_SELL_ALL = ["--symbol", "AXTI", "--side", "sell", "--shares", "10", "--price", "200",
             "--executed-at", "2026-09-23T14:00:00-04:00", "--broker", "IB", "--why", "測試：清倉"]


def test_a_cell_whose_old_and_new_values_are_equal_counts_either_way(monkeypatch, tmp_path) -> None:
    """賣出不改成本：成本格新舊同值（same）——寫沒寫都一樣，不擋「寫一半就往前補」，也不讓它被當成沒寫進去。"""
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="first")
    assert module.main(_SELL_ALL + ["--apply"]) == 0
    assert [w["a1"] for w in calls["write_calls"][1]] == ["D5"]                     # 同值的成本格不必補
    assert calls["cells"]["B2"] == "0.0" and calls["cells"]["D5"] == "52000.0"
    module, calls = _wire_partial(monkeypatch, tmp_path / "b", mode="none")
    assert module.main(_SELL_ALL + ["--apply"]) == 2 and len(calls["write_calls"]) == 1


def test_a_rounded_display_that_fits_both_values_is_not_guessed(monkeypatch, tmp_path, capsys) -> None:
    """分數股：舊 10、新 10.3，Sheet 顯示 0 位小數時讀回「10」——新舊都對得上、數值不同＝分不出寫了沒，請人看、不補寫。"""
    module, calls = _wire_partial(monkeypatch, tmp_path, mode="none", readback={"B2": "10"})
    buy = list(_BUY)
    buy[buy.index("--shares") + 1] = "0.3"
    assert module.main(buy + ["--apply"]) == 2
    assert _log(module) == [] and len(calls["write_calls"]) == 1
    assert "回讀認不得" in capsys.readouterr().err


def test_log_only_can_record_a_sale_the_user_already_zeroed(monkeypatch, tmp_path) -> None:
    """--log-only 的 Sheet 已是成交後：清倉後把股數改成 0 再補記，原本被「會變負數」擋下（⑩ 同一件事）。"""
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=0.0), held_shares=0.0)
    assert module.main(_SELL_ALL + ["--log-only"]) == 0
    assert calls["writes"] == [] and len(_log(module)) == 1
    module, calls = _wire_sheet(monkeypatch, tmp_path / "b", rows=_sheet_rows(AXTI=0.0), held_shares=0.0)
    assert module.main(_SELL_ALL + ["--apply"]) == 2 and calls["writes"] == []       # 要寫 Sheet 的路徑照擋


@pytest.mark.parametrize("display, value, expected", [
    ("20.0", 20.0, True), ("1,234.56", 1234.56, True), ("0.33", 0.3333, True), ("0.34", 0.3333, False),
    ("100", 100.4, True), ("100", 100.6, False), ("", 0.0, False), ("Loading...", 1.0, False),
])
def test_display_matches_allows_only_the_rounding_the_sheet_shows(display, value, expected) -> None:
    assert gsheets.display_matches(display, value) is expected


# ---------------------------------------------------------------------------
# ②③ 同一檔的兩種寫法
# ---------------------------------------------------------------------------


def test_the_five_percent_cap_adds_up_both_spellings_of_the_same_listing() -> None:
    from risk.hard_caps import check_trade_hard_caps

    rows = _sheet_rows(**{"TYO:7803": 4_000.0})
    verdict = check_trade_hard_caps(rows, symbol="7803.T", side="buy", gross_base=2_000.0)
    assert verdict.status == "blocked" and verdict.measures["held_base"] == 4_000.0      # 原本 held 0 → 2% 放行
    rows = _sheet_rows(**{"7803.T": 4_000.0})
    assert check_trade_hard_caps(rows, symbol="TYO:7803", side="buy", gross_base=2_000.0).status == "blocked"


def test_beta_is_recognised_in_any_spelling_and_the_leverage_cap_sees_it() -> None:
    from risk.hard_caps import beta_instrument_for, check_trade_hard_caps, is_beta_symbol
    from portfolio.policy import load_beta_policy
    from risk.snapshot import build_portfolio_components

    policy = load_beta_policy()
    assert is_beta_symbol("TPE:0050") and is_beta_symbol("0050") and is_beta_symbol("0050.TW")
    assert beta_instrument_for("TPE:00631L", policy)["ticker"] == "00631L.TW"
    assert not is_beta_symbol("TPE:3363")
    verdict = check_trade_hard_caps(_sheet_rows(AXTI=1_000.0), symbol="TPE:00631L", side="buy", gross_base=1_000.0)
    assert verdict.measures["rule"] == "etf_leverage_caps"                     # 原本當 alpha、只比 5%，槓桿 cap 沒比
    rows = _sheet_rows(**{"TPE:00631L": 10_000.0})
    assert build_portfolio_components(rows, policy)["leveraged_nominal_base"] == pytest.approx(10_000.0)


def test_a_policy_alias_that_collides_only_after_normalisation_is_refused() -> None:
    """判別走正規化之後，「一個別名只歸一檔」也要在正規化之後成立：`TPE:0050` 掛到 006208 底下，原字串不撞、正規化後撞 0050。"""
    import copy

    from portfolio.policy import DEFAULT_POLICY_PATH, BetaPolicyError, validate_beta_policy

    source = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    validate_beta_policy(source)
    broken = copy.deepcopy(source)
    next(i for i in broken["instruments"] if i["ticker"] == "006208.TW")["sheet_aliases"].append("TPE:0050")
    with pytest.raises(BetaPolicyError, match="multiple instruments"):
        validate_beta_policy(broken)


def test_the_sheet_rule_and_the_risk_rule_are_one_function() -> None:
    from identity.symbols import canonical_symbol

    assert gsheets.canonical_symbol is canonical_symbol
    assert canonical_symbol("tpe:2330") == "2330.TW" and canonical_symbol("TYO:7803") == "7803.T"


# ---------------------------------------------------------------------------
# ④ 分數股四捨五入顯示：回讀認得出自己那一列
# ---------------------------------------------------------------------------


def test_our_row_is_recognised_when_the_sheet_rounds_fractional_shares() -> None:
    values = [["symbol", "broker", "shares"], ["QQQ", "IB", "5"], ["AXTI", "IB", "0.33"]]
    assert gsheets._is_our_row(values, 3, {"symbol": "AXTI", "broker": "IB", "shares": 0.3333})
    assert not gsheets._is_our_row(values, 3, {"symbol": "AXTI", "broker": "IB", "shares": 0.3456})
    assert not gsheets._is_our_row(values, 3, {"symbol": "AXTI", "broker": "FUBON", "shares": 0.3333})


# ---------------------------------------------------------------------------
# ⑥ 手寫市值的列：改股數之前拒絕
# ---------------------------------------------------------------------------

_HEAD = ["symbol", "broker", "bucket", "shares", "market_value_base", "nav_base"]


def _grids(*, hand_written_row2: bool):
    values = [_HEAD, ["AXTI", "IB", "觀察", "10", "1000", "100000"], ["QQQ", "IB", "CORE", "5", "3000", "100000"],
              ["SOXX", "IB", "CORE", "1", "2000", "100000"], ["CASH", "IB", "CASH", "", "94000", "100000"]]
    formulas = [_HEAD,
                ["AXTI", "IB", "觀察", "10", "1000" if hand_written_row2 else "=D2*1", "=SUM($E$2:$E$5)"],
                ["QQQ", "IB", "CORE", "5", "=D3*1", "=SUM($E$2:$E$5)"],
                ["SOXX", "IB", "CORE", "1", "=D4*1", "=SUM($E$2:$E$5)"],
                ["CASH", "IB", "CASH", "", "94000", "=SUM($E$2:$E$5)"]]
    return values, formulas


def test_manual_formula_columns_names_the_hand_written_cell_of_that_row() -> None:
    values, formulas = _grids(hand_written_row2=True)
    assert gsheets.manual_formula_columns(values, formulas, row=2) == ["market_value_base"]
    assert gsheets.manual_formula_columns(values, formulas, row=3) == []
    assert gsheets.manual_formula_columns(values, formulas, row=9) is None                # 這一列不在表裡：沒能確認


@pytest.mark.parametrize("extra, code", [(["--apply"], 2), ([], 2), (["--log-only"], 0)])
def test_a_hand_written_market_value_row_refuses_a_share_change(monkeypatch, tmp_path, capsys, extra, code) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=1_000.0))
    values, formulas = _grids(hand_written_row2=True)
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas_=None, formulas=False, sheet=None: _grids(hand_written_row2=True)[bool(formulas)])
    assert module.main(_BUY + extra) == code
    assert calls["writes"] == []
    if code:
        assert "market_value_base 是手寫值" in capsys.readouterr().err


def test_a_row_inserted_between_the_two_reads_is_not_mistaken_for_a_clean_row(monkeypatch, tmp_path, capsys) -> None:
    """R2 覆核 N3：值與公式是兩次讀取，中間有人插一列——公式表的第 2 列已是別的列。原本照比、回 []（漏擋）；現在代號／券商
    對不上就是「沒能確認」（印出來、照常進行，與公式讀不到同一個出口）。"""
    values, formulas = _grids(hand_written_row2=True)
    shifted = [formulas[0], ["NEW", "IB", "觀察", "1", "=D2*1", "=SUM($E$2:$E$6)"]] + formulas[1:]
    assert gsheets.manual_formula_columns(values, shifted, row=2) is None
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=1_000.0))
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas=False, sheet=None: shifted if formulas else values)
    assert module.main(_BUY) == 0
    assert "沒能確認市值是不是公式" in capsys.readouterr().out


def test_a_hand_written_cell_off_the_market_value_chain_is_named_as_such(monkeypatch, tmp_path, capsys) -> None:
    """R2 覆核 N4：偵測範圍是所有多數是公式的欄（fail closed 不縮）；訊息照實說是哪幾欄，不在市值鏈上就不說 NAV 會錯。"""
    head = _HEAD + ["company"]
    values, formulas = _grids(hand_written_row2=False)
    values = [head] + [r + [f"name{i}"] for i, r in enumerate(values[1:])]
    formulas = [head] + [r + ([f"=X{i}"] if i else ["AXT 手寫"]) for i, r in enumerate(formulas[1:])]
    assert gsheets.manual_formula_columns(values, formulas, row=2) == ["company"]
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=1_000.0))
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas_=None, formulas_grid=None, formulas=False, sheet=None, v=values, f=formulas: f if formulas else v)
    assert module.main(_BUY) == 2
    err = capsys.readouterr().err
    assert "company 是手寫值" in err and "不在市值鏈上" in err and "NAV 會量錯" not in err


def test_an_unreadable_formula_grid_is_said_and_the_trade_goes_on(monkeypatch, tmp_path, capsys) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=1_000.0))

    def read(*, formulas=False, sheet=None):
        if formulas:
            raise TimeoutError("公式讀不到")
        return [["symbol"]]

    monkeypatch.setattr(gsheets, "read_portfolio_values", read)
    assert module.main(_BUY + ["--apply"]) == 0 and len(calls["writes"]) == 1
    assert "沒能確認市值是不是公式" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# ⑧ --fx-to-base 的合理性：同一列反推的匯率
# ---------------------------------------------------------------------------


def _jpy_rows() -> list[dict]:
    return [{"ticker": "AXTI", "broker": "IB", "bucket": "觀察", "market_value_base": 1_000.0, "nav_base": 100_000.0,
             "base_currency": "USD", "currency": "JPY", "shares": 10.0},
            {"ticker": "CASH", "broker": "IB", "bucket": "CASH", "market_value_base": 99_000.0, "nav_base": 100_000.0,
             "base_currency": "USD", "currency": "USD", "shares": 0.0}]


_JPY_BUY = ["--symbol", "AXTI", "--side", "buy", "--shares", "1", "--price", "15000",
            "--executed-at", "2026-11-03T10:00:00+09:00", "--broker", "IB", "--why", "測試：加碼",
            "--currency", "JPY", "--cash-column", "none"]


@pytest.mark.parametrize("fx", ["150", "0.068", "0.00068"])
def test_a_rate_far_from_what_the_row_implies_is_refused(monkeypatch, tmp_path, capsys, fx) -> None:
    """同一列：市值 1,000 USD ÷ 10 股 ÷ 15,000 JPY ≈ 0.0067——倒數（150）或小數點位移（×10、÷10）都差兩倍以上。"""
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_jpy_rows(), row_currency="JPY")
    assert module.main(_JPY_BUY + ["--fx-to-base", fx, "--apply"]) == 2
    assert calls["writes"] == [] and not module.TRADE_LOG.exists()
    err = capsys.readouterr().err
    assert "反推" in err and "0.00667" in err


def test_a_plausible_rate_passes_and_the_implied_rate_is_printed(monkeypatch, tmp_path, capsys) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_jpy_rows(), row_currency="JPY")
    assert module.main(_JPY_BUY + ["--fx-to-base", "0.0068", "--apply"]) == 0
    assert "反推約 0.00667" in capsys.readouterr().out


def test_log_only_only_warns_about_the_rate(monkeypatch, tmp_path, capsys) -> None:
    """--log-only 的列是成交後、可能是很久以前的成交（價差大）——只警告，不擋。"""
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=_jpy_rows(), row_currency="JPY")
    assert module.main(_JPY_BUY + ["--fx-to-base", "150", "--log-only"]) == 0
    assert "反推" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# ⑨ 使用者自己刪了列：--log-only --row-deleted
# ---------------------------------------------------------------------------

_SELL = ["--symbol", "AXTI", "--side", "sell", "--shares", "10", "--price", "200",
         "--executed-at", "2026-11-02T14:00:00-05:00", "--broker", "IB", "--why", "測試：清倉"]


def test_a_deleted_row_can_be_logged_without_locating_it(monkeypatch, tmp_path) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(QQQ=5_000.0))
    located = []
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None: located.append(requests) or [])
    assert module.main(_SELL + ["--log-only", "--row-deleted", "--currency", "USD"]) == 0
    entry, = _log(module)
    assert entry["sheet_row"] == "deleted_by_user" and entry["sheet_update"] == "manual_by_user"
    assert entry["sheet_writes"] == [] and located == [] and calls["writes"] == []


@pytest.mark.parametrize("extra, message", [
    (["--row-deleted", "--currency", "USD"], "只配 --log-only"),
    (["--log-only", "--row-deleted"], "必須明給 --currency"),
])
def test_row_deleted_refuses_without_its_preconditions(monkeypatch, tmp_path, capsys, extra, message) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(QQQ=5_000.0))
    assert module.main(_SELL + extra) == 2 and not module.TRADE_LOG.exists()
    assert message in capsys.readouterr().err


def test_row_deleted_takes_only_sales_because_a_buy_would_pass_the_caps_unmeasured(monkeypatch, tmp_path, capsys) -> None:
    """R2 覆核 B1：買進配 --row-deleted＝已持有 0＋log-only 不加成交額，5% 上限與槓桿 cap 恆判通過——超過上限的買進
    不用 override 就寫進 append-only 的 trade_log（探針：8% NAV、TQQQ 都 pass）。只收賣出；碰 Sheet 之前就擋。"""
    def boom(*a, **k):
        raise AssertionError("不該讀 Sheet")

    for symbol, shares, price in (("AXTI", "40", "200"), ("TQQQ", "400", "100")):
        module, _calls = _wire_sheet(monkeypatch, tmp_path / symbol, rows=_sheet_rows(QQQ=5_000.0))
        monkeypatch.setattr(gsheets, "read_portfolio_values", boom)
        argv = ["--symbol", symbol, "--side", "buy", "--shares", shares, "--price", price,
                "--executed-at", "2026-11-02T14:00:00-05:00", "--broker", "IB", "--currency", "USD",
                "--log-only", "--row-deleted"] + (["--why", "測試"] if symbol == "AXTI" else [])
        assert module.main(argv) == 2 and not module.TRADE_LOG.exists()
        assert "只收賣出" in capsys.readouterr().err


def test_row_deleted_needs_the_broker_spelled_out(monkeypatch, tmp_path, capsys) -> None:
    """R2 覆核 N1：沒有那一列可以讀券商——原本默默預設 IB 寫進 append-only 的 trade_log。"""
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(QQQ=5_000.0))
    argv = [a for i, a in enumerate(_SELL) if a != "--broker" and (i == 0 or _SELL[i - 1] != "--broker")]
    assert module.main(argv + ["--log-only", "--row-deleted", "--currency", "USD"]) == 2
    assert "必須明給 --broker" in capsys.readouterr().err and not module.TRADE_LOG.exists()


def test_row_deleted_refuses_when_the_row_is_still_there(monkeypatch, tmp_path, capsys) -> None:
    rows = _sheet_rows(QQQ=5_000.0) + [{"ticker": "AXTI", "broker": "IB", "bucket": "觀察", "market_value_base": 0.0,
                                        "nav_base": 100_000.0, "base_currency": "USD", "currency": "USD", "shares": 0.0}]
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=rows)
    assert module.main(_SELL + ["--log-only", "--row-deleted", "--currency", "USD"]) == 2
    assert "Sheet 還有" in capsys.readouterr().err and not module.TRADE_LOG.exists()


@pytest.mark.parametrize("argv, wanted, unwanted", [
    (_SELL, "--row-deleted --currency <成交幣別> --broker <券商>", "買進請先"),
    (_BUY, "買進請先在 Sheet 加好那一列", "--row-deleted"),
])
def test_log_only_without_the_row_points_sales_to_row_deleted_and_buys_to_the_sheet(monkeypatch, tmp_path, capsys,
                                                                                    argv, wanted, unwanted) -> None:
    """定位不到那一列時的指路跟著 B1 走：--row-deleted 只收賣出，買進不能指去那裡（指了只會再被擋一次）。"""
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(QQQ=5_000.0))

    def missing(requests, values=None):
        raise ValueError("symbol=AXTI、broker=IB 命中 0 列")

    monkeypatch.setattr(gsheets, "locate_portfolio_cells", missing)
    assert module.main(list(argv) + ["--log-only"]) == 2 and not module.TRADE_LOG.exists()
    err = capsys.readouterr().err
    assert wanted in err and unwanted not in err


# ---------------------------------------------------------------------------
# ⑩ --log-only 不印「舊 → 新」對照
# ---------------------------------------------------------------------------


def test_log_only_prints_the_current_values_not_a_diff(monkeypatch, tmp_path, capsys) -> None:
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=1_000.0))
    assert module.main(_BUY + ["--log-only"]) == 0
    out = capsys.readouterr().out
    assert "將變更的儲存格" not in out and "10 → 20" not in out and "100 → 150" not in out
    assert "Sheet 那一列現在：shares 10" in out and "avg_cost 100" in out


# ---------------------------------------------------------------------------
# R2 覆核 N7（使用者 11-03「負數價格一起擋」）：股數與成交價必須大於 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag, value", [("--price", "-200"), ("--price", "0"), ("--price", "nan"), ("--price", "inf"),
                                         ("--shares", "-10"), ("--shares", "0"), ("--shares", "nan")])
def test_a_non_positive_price_or_share_count_is_refused_before_the_sheet_is_read(monkeypatch, tmp_path, capsys,
                                                                                  flag, value) -> None:
    """負的成交價讓成交額變負、硬擋的增量變負而判通過，Sheet 卻照加股數、現金反而變多（探針：已持有 4.9% 買 10 @ -200 → pass）。"""
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=4_900.0))
    argv = list(_BUY)
    argv[argv.index(flag) + 1] = value
    for extra in ([], ["--apply"], ["--log-only"]):
        assert module.main(argv + extra) == 2
    assert calls["reads"] == [] and calls["writes"] == [] and not module.TRADE_LOG.exists()
    assert "必須是大於 0 的有限數" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# R2 覆核 N5：建倉路徑的現金回讀改用同一個判定——新舊顯示分不出時不刪列、不記，請人看
# ---------------------------------------------------------------------------


def test_an_open_position_cash_readback_that_fits_both_values_is_not_rolled_back(monkeypatch, tmp_path, capsys) -> None:
    """建倉成功、現金寫入丟例外、現金格只顯示整數：寫入前 5000、要寫 4999.7，讀回「5,000」——兩個都對得上。原本判「舊值」並刪掉
    新列還原（現金其實可能已經扣了）；現在判分不出：不刪、不記、請人看。"""
    from tests.test_record_trade_open_position import _OPEN, _wire_open

    module, calls = _wire_open(monkeypatch, tmp_path, cash_network=True)
    calls["cash_now"] = "5,000"
    argv = list(_OPEN)
    argv[argv.index("--shares") + 1], argv[argv.index("--price") + 1] = "1", "0.3"
    assert module.main(argv + ["--apply"]) == 2
    assert calls["deleted"] == [] and not module.TRADE_LOG.exists()
    assert "無法確認" in capsys.readouterr().err
    # 對照：成交 2 元、要寫 4998，讀回「5000」——新值顯示會是 4998，分得出：照舊判「舊值」、刪列還原
    module, calls2 = _wire_open(monkeypatch, tmp_path / "b", cash_network=True)
    calls2["cash_now"] = "5000"
    argv[argv.index("--price") + 1] = "2"
    assert module.main(argv + ["--apply"]) == 2 and calls2["deleted"] != [] and not module.TRADE_LOG.exists()


def test_an_open_position_cash_readback_is_read_again_before_rolling_back(monkeypatch, tmp_path, capsys) -> None:
    """D 第二輪覆核 non-blocking（B2 的對稱面，L17）：建倉成功、現金寫入丟例外、第一次回讀還是寫入前的 5000——伺服器晚幾秒才套用。
    只讀一次就刪列，Sheet 會留下扣了現金卻沒有持股列；隔幾秒再讀到新值＝照常記、不刪。兩次都是舊值才刪，而且不說「現金沒動」。"""
    from tests.test_record_trade_open_position import _OPEN, _wire_open

    module, calls = _wire_open(monkeypatch, tmp_path, cash_network=True)
    module.ABSENT_RECHECK_SECONDS = 0.001
    answers = iter(["5000", "3000"])
    monkeypatch.setattr(gsheets, "read_cell_value", lambda a1: next(answers))
    assert module.main(_OPEN + ["--apply"]) == 0
    assert calls["deleted"] == [] and module.TRADE_LOG.exists()
    capsys.readouterr()
    module, calls = _wire_open(monkeypatch, tmp_path / "b", cash_network=True)
    module.ABSENT_RECHECK_SECONDS = 0.001
    reads = []
    monkeypatch.setattr(gsheets, "read_cell_value", lambda a1: reads.append(a1) or "5000")
    assert module.main(_OPEN + ["--apply"]) == 2
    assert calls["deleted"] == [5] and len(reads) == 2 and not module.TRADE_LOG.exists()
    err = capsys.readouterr().err
    assert "隔 0.001 秒再讀" in err and "重跑前先看一眼現金格" in err and "現金沒動" not in err
