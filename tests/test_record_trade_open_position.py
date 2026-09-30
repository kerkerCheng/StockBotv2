"""首次建倉走對話＋兩個小修（2026-09-30 使用者定案；資本路徑）。

使用者說一句「我買了 X 股、成本 Y」→ `record_trade.py --open-position` 在 Sheet **新增一列**。這張表的市值與
`nav_base` 是公式、`nav_base` 的加總範圍寫死（`=SUM($I$2:$I$25)`）——新列接在最後一列之後，NAV 就不會算到它，
5% 硬擋用錯分母。所以這裡守：插在範圍內部、公式從標準列複製、只寫新插的那一列、寫完回讀不過就刪掉還原。
另兩件：同一筆成交重跑 `--apply` 一律 fail closed（原本會把 Sheet 再算一次）；一筆成交只讀一次 Sheet。
**全部用假的 Sheet；不寫真的 Sheet 與 trade_log。**
"""
from __future__ import annotations

import json

import pytest

from fetchers import gsheets
from tests.test_record_trade import _BUY, _present_inputs, _sheet_rows, _wire_sheet

HEAD = ["broker", "bucket", "symbol", "shares", "avg_cost", "currency", "cash_usd", "market_usd",
        "notes", "company", "market_value_base", "nav_base", "base_currency"]
MKT = '=IF($B{r}="CASH",N($G{r}),IF($D{r}="","",N($D{r})*IFERROR(GOOGLEFINANCE($C{r},"price"),0)))'


def _grid(*, nav_end: int | None = None, manual_row: int | None = None, cash: bool = True):
    """持股 2–6 列（IB×3、TAISHIN×2）＋ CASH 7–8 列；回（values, formulas）。"""
    body = [("IB", "觀察", "FRA:2DG"), ("IB", "觀察", "7803.T"), ("IB", "CORE", "NVDA"),
            ("TAISHIN", "大盤", "0050.TW"), ("TAISHIN", "CORE", "2330.TW")]
    if cash:
        body += [("IB", "CASH", "—"), ("TAISHIN", "CASH", "—")]
    last = len(body) + 1
    end = nav_end or last
    values, formulas = [HEAD], [HEAD]
    for r, (broker, bucket, symbol) in enumerate(body, start=2):
        is_cash = bucket == "CASH"
        base = [broker, bucket, symbol, "" if is_cash else "10", "" if is_cash else "100", "USD",
                "5000" if is_cash else "", None, "", ""]
        market = MKT.format(r=r) if r != manual_row else "=400*347"
        values.append([*base[:7], "1000", "", "", "1000", "20000", "USD"])
        formulas.append([*base[:7], market, "", "", f"=H{r}", f"=SUM($H$2:$H${end})", "USD"])
    return values, formulas


# ---------------------------------------------------------------------------
# 1. 規劃（純函式）
# ---------------------------------------------------------------------------

def test_the_plan_inserts_inside_the_nav_range_after_the_same_broker() -> None:
    values, formulas = _grid(manual_row=3)
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI")
    assert plan["insert_at"] == 5 and plan["template"] == 4          # IB 最後一列持股（第 4 列）的下一列
    assert plan["manual_exceptions"] == {3: ["market_usd"]}          # 手寫公式照實列出、不當範本
    assert plan["nav_range"] == ("H", 2, 8)
    assert {"market_usd", "market_value_base", "nav_base"} <= set(plan["formula_columns"])
    other = gsheets.plan_new_position(values, formulas, broker="CATHAY", symbol="2455.TW")
    assert other["insert_at"] == 7                                    # 沒有同券商持股 → 第一個 CASH 列上面


def test_a_manual_row_is_never_the_template() -> None:
    values, formulas = _grid(manual_row=4)                            # IB 最後一列是手寫公式
    assert gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI")["template"] == 3


@pytest.mark.parametrize("kw, symbol, message", [
    ({}, "NVDA", "不是首次建倉"),
    ({"nav_end": 6}, "AXTI", "NAV 本來就漏列"),
    ({"cash": False}, "AXTI", "找不到 CASH 列"),
])
def test_the_plan_refuses_instead_of_guessing(kw, symbol, message) -> None:
    values, formulas = _grid(**kw)
    with pytest.raises(ValueError, match=message):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol=symbol)


def test_the_plan_refuses_when_no_formula_shape_is_a_clear_majority() -> None:
    values, formulas = _grid()
    for r in (2, 3, 4):
        formulas[r - 1][7] = f"=N($D{r})*{r}"                         # 三種不同手寫 → 沒有一種占三分之二
    with pytest.raises(ValueError, match="三分之二"):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI")


# ---------------------------------------------------------------------------
# 2. 寫入只碰新插的那一列；3. 回讀驗證；4. 還原先確認列
# ---------------------------------------------------------------------------

class _FakeService:
    def __init__(self):
        self.bodies = []

    def spreadsheets(self):
        return self

    def get(self, **_):
        return self

    def batchUpdate(self, *, spreadsheetId, body):  # noqa: N802 — Google API 的名字
        self.bodies.append(body)
        return self

    def execute(self):
        return {"sheets": [{"properties": {"sheetId": 7, "title": gsheets.SHEET_NAME}}]}


def test_open_writes_one_atomic_request_touching_only_the_new_row(monkeypatch) -> None:
    fake = _FakeService()
    monkeypatch.setattr(gsheets, "_get_service", lambda *, writable=False: fake)
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI")
    out = gsheets.open_position_row(plan, {"broker": "IB", "bucket": "觀察", "symbol": "AXTI", "shares": 10.0,
                                           "avg_cost": 12.5, "currency": "USD", "base_currency": "USD"})
    assert len(fake.bodies) == 1                                      # 一個 batchUpdate＝原子
    requests = fake.bodies[0]["requests"]
    assert requests[0]["insertDimension"]["range"]["startIndex"] == plan["insert_at"] - 1
    paste = requests[1]["copyPaste"]
    assert paste["source"]["startRowIndex"] == plan["template"] - 1
    assert paste["destination"]["startRowIndex"] == plan["insert_at"] - 1
    cells = [r["updateCells"] for r in requests[2:]]
    assert cells and all(c["range"]["startRowIndex"] == plan["insert_at"] - 1
                         and c["range"]["endRowIndex"] == plan["insert_at"] for c in cells)
    touched = {HEAD[c["range"]["startColumnIndex"]] for c in cells}
    assert not touched & set(plan["formula_columns"])                 # 公式欄只從範本貼、不覆寫
    assert out["row"] == plan["insert_at"]


def _after(values, formulas, plan, fill, *, market="1500", nav_end=None):
    """模擬 Sheets 插列後的樣子：新列在 insert_at、下面的列下移、SUM 範圍撐大。"""
    r = plan["insert_at"]
    end = nav_end or len(values) + 1
    new_v = [fill["broker"], fill["bucket"], fill["symbol"], str(fill["shares"]), str(fill["avg_cost"]),
             fill["currency"], "", market, "", "", market, "20000", "USD"]
    new_f = [*new_v[:7], MKT.format(r=r), "", "", f"=H{r}", f"=SUM($H$2:$H${end})", "USD"]

    def shift(grid, new, is_formula):
        out = [grid[0]]
        for i, row in enumerate(grid[1:], start=2):
            if i == r:
                out.append(new)
            n = i + 1 if i >= r else i
            row = list(row)
            if is_formula and i >= r:
                row[7] = MKT.format(r=n) if str(row[7]).startswith("=IF") else row[7]
                row[10] = f"=H{n}"
            if is_formula:
                row[11] = f"=SUM($H$2:$H${end})"
            out.append(row)
        return out
    return shift(values, new_v, False), shift(formulas, new_f, True)


FILL = {"broker": "IB", "bucket": "觀察", "symbol": "AXTI", "shares": 10.0, "avg_cost": 12.5, "currency": "USD"}


@pytest.mark.parametrize("kw, expected", [
    ({}, []),
    ({"market": "0"}, ["市值是 0"]),
    ({"nav_end": 8}, ["NAV 加總範圍沒有涵蓋"]),
])
def test_verify_reads_back_and_names_what_failed(monkeypatch, kw, expected) -> None:
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI")
    after_v, after_f = _after(values, formulas, plan, FILL, **kw)
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas=False, sheet=None: after_f if formulas else after_v)
    problems = gsheets.verify_new_position(plan, FILL, attempts=2, sleep=lambda s: None)
    assert all(any(e in p for p in problems) for e in expected) and bool(problems) == bool(expected)


def test_verify_retries_while_prices_are_loading(monkeypatch) -> None:
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI")
    loading_v, after_f = _after(values, formulas, plan, FILL, market="Loading...")
    ready_v, _ = _after(values, formulas, plan, FILL)
    seen = iter([loading_v, ready_v])
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas=False, sheet=None: after_f if formulas else next(seen))
    naps = []
    assert gsheets.verify_new_position(plan, FILL, attempts=3, sleep=naps.append) == [] and len(naps) == 1


def test_rollback_refuses_to_delete_a_row_that_is_not_ours(monkeypatch) -> None:
    fake = _FakeService()
    monkeypatch.setattr(gsheets, "_get_service", lambda *, writable=False: fake)
    values, _ = _grid()
    monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas=False, sheet=None: values)
    with pytest.raises(ValueError, match="不刪"):
        gsheets.delete_position_row({"row": 3, "sheet_id": 7}, {"symbol": "AXTI", "broker": "IB", "shares": 10.0})
    assert fake.bodies == []                                          # 第 3 列是 7803.T
    gsheets.delete_position_row({"row": 3, "sheet_id": 7}, {"symbol": "7803.T", "broker": "IB", "shares": 10.0})
    assert fake.bodies[0]["requests"][0]["deleteDimension"]["range"]["startIndex"] == 2


# ---------------------------------------------------------------------------
# 5. record_trade 主流程
# ---------------------------------------------------------------------------

def _wire_open(monkeypatch, tmp_path, *, verify=(), cash_fails=False, open_fails=False, verify_raises=False,
               inputs=None, rows=None, cash_network=False):
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=rows or _sheet_rows(), inputs=inputs or _present_inputs())
    module.ABSENT_RECHECK_SECONDS = 0
    values, formulas = _grid()
    calls["reads"] = []
    monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas_=None, formulas=False, sheet=None:
                        calls["reads"].append(formulas) or (_grid()[1] if formulas else values))
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None:
                        [{"a1": "Portfolio!G7", "current": "5000"}])
    calls.update(opened=[], deleted=[])

    def open_row(plan, fill):
        calls["opened"].append((plan["insert_at"], dict(fill)))
        if open_fails:
            raise TimeoutError("client 逾時")
        return {"status": "opened", "row": plan["insert_at"], "sheet_id": 7, "written": [{"a1": "new", "to": 1}]}

    def write(writes):
        if cash_fails:
            raise gsheets.StaleCellError("現值不符")
        if cash_network:
            raise cash_network if isinstance(cash_network, BaseException) else TimeoutError("讀取回應逾時")
        calls["writes"].append(writes)
        return {"written": [w["a1"] for w in writes]}

    monkeypatch.setattr(gsheets, "open_position_row", open_row)
    def verify_fn(plan, fill):
        if verify_raises:
            raise ConnectionResetError("回讀時斷線")
        return list(verify)

    monkeypatch.setattr(gsheets, "verify_new_position", verify_fn)
    def delete(opened, fill, expect=None):
        calls["deleted"].append(opened["row"])
        calls["delete_expect"] = expect
        return {"verified": True, "detail": "測試"}

    monkeypatch.setattr(gsheets, "delete_position_row", delete)
    monkeypatch.setattr(gsheets, "new_row_state", lambda plan, fill: calls.get("landed", "absent"))
    monkeypatch.setattr(gsheets, "read_cell_value", lambda a1: calls.get("cash_now", "5000"))
    monkeypatch.setattr(gsheets, "write_portfolio_cells", write)
    return module, calls


_OPEN = _BUY + ["--open-position", "--bucket", "觀察", "--company", "AXT Inc", "--currency", "USD",
                "--cash-column", "cash_usd"]


@pytest.mark.parametrize("argv", [
    _BUY + ["--open-position"],                                                  # 沒有 bucket
    _BUY + ["--open-position", "--bucket", "CASH"],
    _BUY + ["--bucket", "觀察"],                                                  # 沒有 --open-position
    [a if a != "buy" else "sell" for a in _BUY] + ["--open-position", "--bucket", "觀察"],
    _BUY + ["--open-position", "--bucket", "觀察", "--log-only"],
])
def test_open_position_flag_misuse_is_rejected_before_any_sheet_access(monkeypatch, tmp_path, argv) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path)
    assert module.main(argv) == 2
    assert calls["reads"] == [] and calls["opened"] == [] and not module.TRADE_LOG.exists()


def test_open_position_dry_run_prints_the_new_row_and_writes_nothing(monkeypatch, tmp_path, capsys) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path)
    assert module.main(_OPEN) == 0
    out = capsys.readouterr().out
    assert "新增一列" in out and "Portfolio!G8" in out                # 現金列在插入點下面 → 下移一列
    assert calls["opened"] == [] and calls["writes"] == [] and not module.TRADE_LOG.exists()
    assert calls["reads"] == [False, True]                            # 值讀一次＋公式讀一次（只比對形狀）


def test_open_position_apply_writes_the_row_then_cash_then_the_event(monkeypatch, tmp_path) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path)
    assert module.main(_OPEN + ["--apply"]) == 0
    (row, fill), = calls["opened"]
    assert row == 5 and fill["symbol"] == "AXTI" and fill["shares"] == 10.0 and fill["avg_cost"] == 200.0
    assert fill["bucket"] == "觀察" and fill["company"] == "AXT Inc"
    assert calls["writes"] == [[{"a1": "Portfolio!G8", "expected": "5000", "value": 3000.0}]]
    entry = json.loads(module.TRADE_LOG.read_text(encoding="utf-8").splitlines()[0])
    assert entry["sheet_opened_row"] == 5 and entry["research_receipt"]["derived"]["sheet"]["held_before_this_row"] is False


@pytest.mark.parametrize("kw", [{"verify": ("新列市值是 0",)}, {"cash_fails": True}, {"verify_raises": True}])
def test_a_failed_check_after_opening_rolls_the_row_back_and_logs_nothing(monkeypatch, tmp_path, kw) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path, **kw)
    assert module.main(_OPEN + ["--apply"]) == 2
    assert calls["deleted"] == [5] and not module.TRADE_LOG.exists()


def test_a_missing_row_without_the_flag_points_at_open_position(monkeypatch, tmp_path, capsys) -> None:
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows())
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None: (_ for _ in ()).throw(
        ValueError("比對條件 {'symbol': 'AXTI', 'broker': 'IB'} 命中 0 列，必須恰好 1 列才可寫入")))
    assert module.main(_BUY) == 2
    assert "--open-position" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 6. 重跑 --apply fail closed；7. 一筆成交只讀一次 Sheet
# ---------------------------------------------------------------------------

def test_reapplying_a_recorded_trade_is_refused_and_never_rewrites_the_sheet(monkeypatch, tmp_path, capsys) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows())
    assert module.main(_BUY + ["--apply"]) == 0
    assert len(calls["writes"]) == 1
    assert module.main(_BUY + ["--apply"]) == 2                       # 原本：印警告、照寫 Sheet（股數現金重複）
    assert len(calls["writes"]) == 1
    assert len(module.TRADE_LOG.read_text(encoding="utf-8").splitlines()) == 1
    assert "重跑 --apply" in capsys.readouterr().err
    assert module.main(_BUY) == 0                                     # dry-run 照樣看得到


def test_one_trade_reads_the_sheet_once_and_every_stage_gets_that_copy(monkeypatch, tmp_path) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows())
    seen = []
    monkeypatch.setattr(gsheets, "fetch_portfolio", lambda *, strict_operational=False, values=None:
                        seen.append(values) or _sheet_rows())
    assert module.main(_BUY + ["--apply"]) == 0
    assert calls["reads"] == [False]                                  # 值只讀一次
    assert seen == [[["symbol"]]] and calls["located_with"] == [[["symbol"]]]   # 解析與定位拿的是同一份


# ---------------------------------------------------------------------------
# 8. R2 覆核（2026-09-30）補的：兩條 blocking ＋ 會碰錢的 non-blocking
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("drop", ["--currency", "--cash-column"])
def test_open_position_needs_currency_and_cash_column_spelled_out(monkeypatch, tmp_path, drop) -> None:
    """blocking #2：新列沒有既有列可以核對，預設的 USD／cash_usd 會被照寫進 Sheet、灌進 NAV 公式。"""
    module, calls = _wire_open(monkeypatch, tmp_path)
    argv = list(_OPEN)
    i = argv.index(drop)
    del argv[i:i + 2]
    assert module.main(argv) == 2
    assert calls["reads"] == [] and calls["opened"] == []


def test_open_position_needs_the_broker_spelled_out(monkeypatch, tmp_path) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path)
    argv = [a for a in _OPEN]
    i = argv.index("--broker")
    del argv[i:i + 2]
    assert module.main(argv) == 2 and calls["reads"] == []


def test_cash_column_currency_must_match_the_trade(monkeypatch, tmp_path) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path)
    argv = [a if a != "cash_usd" else "cash_twd" for a in _OPEN]
    assert module.main(argv) == 2 and calls["reads"] == []


@pytest.mark.parametrize("symbol, currency, message", [
    ("2330.TW", "USD", "台股代號"),
    ("3081.TWO", "TWD", "上櫃"),
    ("SIVE.ST", "SEK", "只換算"),
    ("6324.T", "USD", "日股代號"),
    ("2330", "USD", "寫成 Sheet 既有的寫法 2330.TW"),       # R2 覆核：裸 4 碼會被公式當台股
    ("0050", "TWD", "寫成"),
    ("LON:VWRA", "USD", "認不得"),                          # LON: 的 GBX 股票配 USD 高估百倍
    ("SOI.PA", "EUR", "認不得"),
    ("AXTI", "JPY", "美股代號"),
    ("TPE:2330", "TWD", "寫成 Sheet 既有的寫法 2330.TW"),   # 第二次覆核：TPE: 會被當成另一檔
    ("VOD.L", "USD", "認不得"),                              # 美股後綴只收 .A／.B
    ("TYO:6324", "JPY", "寫成公司名冊的寫法 6324.T"),        # 2026-09-30 定案：Sheet 用名冊寫法，TYO: 改寫
])
def test_symbol_and_currency_are_checked_before_anything_is_written(symbol, currency, message) -> None:
    values, formulas = _grid()
    with pytest.raises(ValueError, match=message):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol=symbol, currency=currency)


def test_a_symbol_held_at_another_broker_is_refused_unless_explicit() -> None:
    values, formulas = _grid()
    with pytest.raises(ValueError, match="TAISHIN.*--broker 給錯"):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol="2330.TW", currency="TWD")
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="2330.TW", currency="TWD",
                                     allow_other_broker=True)
    assert plan["other_brokers"] == ["TAISHIN"]


def test_the_missing_row_hint_names_the_brokers_that_hold_it(monkeypatch, tmp_path, capsys) -> None:
    rows = [{**r, "broker": "TAISHIN"} for r in _sheet_rows(AXTI=1_000.0)]
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=rows)
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None: (_ for _ in ()).throw(
        ValueError("比對條件 {'symbol': 'AXTI', 'broker': 'IB'} 命中 0 列，必須恰好 1 列才可寫入")))
    assert module.main(_BUY) == 2
    err = capsys.readouterr().err
    assert "TAISHIN" in err and "--broker" in err and "--open-position" not in err


def test_bucket_is_a_closed_vocabulary(monkeypatch, tmp_path) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path)
    argv = [a if a != "觀察" else "隨手新格" for a in _OPEN]
    assert module.main(argv) == 2 and calls["opened"] == []


def test_a_company_already_held_under_another_symbol_cannot_be_opened_again(monkeypatch, tmp_path) -> None:
    """5% 上限按代號加總：換一個掛牌建倉會繞過它——建倉這條路 fail closed。"""
    module, calls = _wire_open(monkeypatch, tmp_path, inputs={**_present_inputs(), "held_company": True})
    assert module.main(_OPEN + ["--apply"]) == 2
    assert calls["opened"] == [] and not module.TRADE_LOG.exists()


@pytest.mark.parametrize("landed, deleted", [("landed", [5]), ("absent", []), ("unknown", [])])
def test_an_open_request_that_errors_is_read_back_before_claiming_nothing_changed(
        monkeypatch, tmp_path, capsys, landed, deleted) -> None:
    """client 逾時不等於伺服器沒套用：回讀發現已套用就還原，沒套用才說「沒被改動」。"""
    module, calls = _wire_open(monkeypatch, tmp_path, open_fails=True)
    calls["landed"] = landed
    assert module.main(_OPEN + ["--apply"]) == 2
    assert calls["deleted"] == deleted and not module.TRADE_LOG.exists()
    err = capsys.readouterr().err
    if landed == "absent":
        assert "目前讀回未套用" in err and "重跑前先看一眼" in err
    if landed == "unknown":
        assert "無法確認新列有沒有套用" in err and "股數可能重複" in err


def test_open_position_still_hits_the_five_percent_cap(monkeypatch, tmp_path) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path, rows=_sheet_rows(nav=20_000.0))   # 2000／20000＝10%
    assert module.main(_OPEN) == module.EXIT_HARD_CAP
    assert module.main(_OPEN + ["--apply"]) == module.EXIT_HARD_CAP
    assert calls["opened"] == [] and not module.TRADE_LOG.exists()


def test_the_template_is_never_below_the_insertion_point() -> None:
    """同券商持股全是手寫例外時，範本不得挑到插入點下面那一列（插列後 API 照字面取來源，會差一列）。"""
    head = HEAD
    rows = [("X", "CORE", "AAA"), ("X", "CORE", "BBB"), ("X", "CORE", "CCC"), ("IB", "觀察", "DDD"),
            ("Y", "CORE", "EEE"), ("IB", "CASH", "—"), ("Y", "CASH", "—")]
    values, formulas = [head], [head]
    for r, (broker, bucket, symbol) in enumerate(rows, start=2):
        cash = bucket == "CASH"
        base = [broker, bucket, symbol, "" if cash else "10", "" if cash else "100", "USD", "5000" if cash else ""]
        values.append([*base, "1000", "", "", "1000", "20000", "USD"])
        formulas.append([*base, "=400*347" if symbol == "DDD" else MKT.format(r=r), "", "", f"=H{r}",
                         "=SUM($H$2:$H$8)", "USD"])
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="ZZZ", currency="USD")
    assert plan["insert_at"] == 6 and plan["template"] < plan["insert_at"]


def test_a_nav_range_that_starts_below_the_first_row_is_refused_up_front() -> None:
    values, formulas = _grid()
    for row in formulas[1:]:
        row[11] = "=SUM($H$3:$H$8)"
    with pytest.raises(ValueError, match="NAV 本來就漏列"):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI", currency="USD")


def test_verify_catches_a_formula_pointing_at_the_wrong_row_and_a_displaced_symbol(monkeypatch) -> None:
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI")
    after_v, after_f = _after(values, formulas, plan, FILL)
    wrong = [list(r) for r in after_f]
    wrong[plan["insert_at"] - 1][7] = MKT.format(r=plan["template"])       # 公式沒調相對列號 → 指向範本列
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas=False, sheet=None: wrong if formulas else after_v)
    assert any("公式形狀" in p for p in gsheets.verify_new_position(plan, FILL, attempts=1, sleep=lambda s: None))
    displaced = [list(r) for r in after_v]
    displaced[plan["insert_at"] - 1][2] = "OTHER"
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas=False, sheet=None: after_f if formulas else displaced)
    assert any("不是剛寫的" in p for p in gsheets.verify_new_position(plan, FILL, attempts=1, sleep=lambda s: None))


def test_a_cash_cell_exactly_at_the_insertion_row_moves_down() -> None:
    module = _module_for_shift()
    assert module._shifted_a1("Portfolio!H13", 13) == "Portfolio!H14"
    assert module._shifted_a1("Portfolio!H12", 13) == "Portfolio!H12"


def _module_for_shift():
    from tests.test_record_trade import _module
    return _module()


@pytest.mark.parametrize("variant", [
    lambda argv: [a if a != "AXTI" else "axti" for a in argv],
    lambda argv: [a if a != "2026-09-23T14:00:00-04:00" else "2026-09-23T18:00:00+00:00" for a in argv],
])
def test_reapply_is_caught_even_when_the_same_trade_is_spelled_differently(monkeypatch, tmp_path, variant) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows())
    assert module.main(_BUY + ["--apply"]) == 0
    assert module.main(variant(_BUY) + ["--apply"]) == 2
    assert len(calls["writes"]) == 1


# ---------------------------------------------------------------------------
# 9. R2 覆核（2026-09-30 第二輪）
# ---------------------------------------------------------------------------

OTHER = {"symbol": "0050.TW", "broker": "FUBON", "shares": 1000.0}


def test_another_brokers_row_with_the_same_symbol_is_never_taken_for_ours(monkeypatch) -> None:
    """blocking #1：只比代號時，插入點正是別家券商的同代號既有列（第 5 列 TAISHIN 0050.TW）會被當成新列刪掉。"""
    values, formulas = _grid()
    fake = _FakeService()
    monkeypatch.setattr(gsheets, "_get_service", lambda *, writable=False: fake)
    monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas=False, sheet=None: values)
    plan = {"insert_at": 5, "last_row": len(values)}
    assert gsheets.new_row_state(plan, OTHER) != "landed"
    with pytest.raises(ValueError, match="不刪"):
        gsheets.delete_position_row({"row": 5, "sheet_id": 7}, OTHER)
    assert fake.bodies == []


def test_our_row_is_recognised_only_when_symbol_broker_and_shares_all_match(monkeypatch) -> None:
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI", currency="USD")
    after_v, _ = _after(values, formulas, plan, FILL)
    monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas=False, sheet=None: after_v)
    assert gsheets.new_row_state(plan, FILL) == "landed"
    assert gsheets.new_row_state(plan, {**FILL, "shares": 11.0}) != "landed"
    assert gsheets.new_row_state(plan, {**FILL, "broker": "TAISHIN"}) != "landed"


def test_delete_says_it_could_not_confirm_when_the_readback_does_not_match(monkeypatch) -> None:
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI", currency="USD")
    after_v, after_f = _after(values, formulas, plan, FILL)
    fake = _FakeService()
    monkeypatch.setattr(gsheets, "_get_service", lambda *, writable=False: fake)
    reads = iter([after_v, after_v, after_f])                       # 刪前確認、刪後值、刪後公式（假：沒真的刪掉）
    monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas=False, sheet=None: next(reads))
    check = gsheets.delete_position_row({"row": plan["insert_at"], "sheet_id": 7}, FILL, expect=plan)
    assert check["verified"] is False and "寫入前" in check["detail"]


def test_rollback_passes_the_plan_so_the_readback_can_be_checked(monkeypatch, tmp_path) -> None:
    module, calls = _wire_open(monkeypatch, tmp_path, verify=("x",))
    assert module.main(_OPEN + ["--apply"]) == 2
    assert calls["delete_expect"] is not None and calls["delete_expect"]["insert_at"] == 5


@pytest.mark.parametrize("cash_now, code, deleted, logged", [
    ("3000", 0, [], True),            # 回讀已是新值：整筆其實寫完了 → 照常記事件
    ("5000", 2, [5], False),          # 回讀仍是舊值：現金沒動 → 刪新列
    ("4321", 2, [], False),           # 都不是：不刪、不記，大聲說
])
def test_a_cash_write_that_errors_is_read_back_before_deciding(monkeypatch, tmp_path, cash_now, code, deleted,
                                                                logged) -> None:
    """blocking #3：伺服器已套用後 client 才逾時，原本只刪列、現金沒還原，還印「回到寫入前」。"""
    module, calls = _wire_open(monkeypatch, tmp_path, cash_network=True)
    calls["cash_now"] = cash_now
    assert module.main(_OPEN + ["--apply"]) == code
    assert calls["deleted"] == deleted and module.TRADE_LOG.exists() is logged
    if logged:
        entry = json.loads(module.TRADE_LOG.read_text(encoding="utf-8").splitlines()[0])
        assert "回讀確認已套用" in entry["sheet_write_note"]


@pytest.mark.parametrize("argv", [
    [a if a != "IB" else "" for a in _BUY],
    [a if a != "2026-09-23T14:00:00-04:00" else "2026-09-23T14:00:00" for a in _BUY],
])
def test_blank_flags_and_timezone_less_times_are_refused_before_the_sheet(monkeypatch, tmp_path, argv) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows())
    assert module.main(argv) == 2 and calls["reads"] == []


def _eu(argv, broker="TAISHIN"):
    """把 _OPEN 換成 FRA:2DG（alpha）在別家券商建倉：歐元、現金欄 none、給匯率。"""
    out = [a if a != "AXTI" else "FRA:2DG" for a in argv]
    out = [a if a not in ("USD", "cash_usd", "IB") else {"USD": "EUR", "cash_usd": "none", "IB": broker}[a] for a in out]
    return out + ["--fx-to-base", "1.1"]


def test_main_really_passes_the_currency_and_the_other_broker_flag_to_the_plan(monkeypatch, tmp_path, capsys) -> None:
    """R2 覆核 non-blocking（N5／N6 變異存活）：純函式有測，但主流程的接線沒測。"""
    module, calls = _wire_open(monkeypatch, tmp_path)
    wrong = [a if a != "EUR" else "USD" for a in _eu(_OPEN)]
    wrong = [a if a != "none" else "cash_usd" for a in wrong]
    assert module.main(wrong) == 2
    assert "歐元區交易所代號" in capsys.readouterr().err                 # 主流程把幣別傳進規劃
    assert module.main(_eu(_OPEN)) == 2
    assert "--also-at-other-broker" in capsys.readouterr().err          # FRA:2DG 已在 IB → 預設拒收
    assert module.main(_eu(_OPEN) + ["--also-at-other-broker"]) == 0     # 明說才放（dry-run）
    assert calls["opened"] == []


def test_the_same_symbol_held_at_another_broker_is_not_called_a_different_symbol(monkeypatch, tmp_path) -> None:
    held_same = [{**r, "ticker": "FRA:2DG", "shares": 5.0} if r["ticker"] == "AXTI" else r for r in _sheet_rows(AXTI=1_000.0)]
    module, _calls = _wire_open(monkeypatch, tmp_path, rows=held_same,
                                inputs={**_present_inputs(), "held_company": True, "company_held_symbols": ["FRA:2DG"]})
    assert module.main(_eu(_OPEN) + ["--also-at-other-broker"]) == 0      # 同代號：硬擋本來就跨券商按代號加總
    held_other = _sheet_rows(AXTI=1_000.0)                              # 同公司、另一個代號 → 擋
    module, _calls = _wire_open(monkeypatch, tmp_path, rows=held_other,
                                inputs={**_present_inputs(), "held_company": True, "company_held_symbols": ["SIVE.ST"]})
    assert module.main(_eu(_OPEN) + ["--also-at-other-broker"]) == 2


def test_a_bare_code_missing_row_hint_still_finds_the_dot_tw_row(monkeypatch, tmp_path, capsys) -> None:
    rows = [{**r, "ticker": "0050.TW", "broker": "TAISHIN"} for r in _sheet_rows(X=1.0)]
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=rows)
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None: (_ for _ in ()).throw(
        ValueError("比對條件 {'symbol': '0050', 'broker': 'IB'} 命中 0 列，必須恰好 1 列才可寫入")))
    argv = [a if a != "AXTI" else "0050" for a in _BUY]
    argv = argv[:argv.index("--why")]                                   # 0050 是 beta：不收研究旗標
    assert module.main(argv) == 2
    assert "TAISHIN" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 10. R2 第二次覆核（2026-09-30）
# ---------------------------------------------------------------------------

def test_the_readback_after_an_open_error_has_three_answers(monkeypatch) -> None:
    """blocking：只給兩值時，已套用又碰上使用者同時加列會被說成「沒改動」——新列留在 Sheet、現金沒扣。"""
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="AXTI", currency="USD")
    after_v, _ = _after(values, formulas, plan, FILL)
    user_added = after_v + [["IB", "CASH", "—", "", "", "USD", "1", "1", "", "", "1", "1", "USD"]]
    ins = plan["insert_at"]
    user_deleted_below = after_v[:ins] + after_v[ins + 1:]              # 已套用、同時刪了下面一列：列數剛好回到原樣
    for grid, want in ((after_v, "landed"), (user_added, "landed"), (values, "absent"),
                       (values + [values[-1]], "unknown"), (user_deleted_below, "unknown")):
        monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas=False, sheet=None, g=grid: g)
        assert gsheets.new_row_state(plan, FILL) == want


@pytest.mark.parametrize("cash_now", ["$3,000", RuntimeError("讀不到")])
def test_a_cash_readback_that_is_not_a_number_or_fails_never_records_the_trade(monkeypatch, tmp_path, cash_now) -> None:
    """第二次覆核 non-blocking（X3-d／X3-e 變異存活）：回讀到非數字或讀不到，都不得當成「已寫進去」而記事件。"""
    module, calls = _wire_open(monkeypatch, tmp_path, cash_network=True)
    if isinstance(cash_now, BaseException):
        monkeypatch.setattr(gsheets, "read_cell_value", lambda a1: (_ for _ in ()).throw(cash_now))
    else:
        calls["cash_now"] = cash_now
    assert module.main(_OPEN + ["--apply"]) == 2
    assert calls["deleted"] == [] and not module.TRADE_LOG.exists()


def test_only_a_stale_cell_error_means_nothing_was_written(monkeypatch, tmp_path) -> None:
    """其他 ValueError（例：伺服器已套用、回應本體不是 JSON 的 JSONDecodeError）都要回讀，不能直接刪列。"""
    import json as _json

    module, calls = _wire_open(monkeypatch, tmp_path, cash_network=_json.JSONDecodeError("x", "doc", 0))
    calls["cash_now"] = "3000"
    assert module.main(_OPEN + ["--apply"]) == 0
    assert calls["deleted"] == [] and module.TRADE_LOG.exists()
    assert issubclass(gsheets.StaleCellError, ValueError)


def test_the_same_symbol_exemption_does_not_cover_another_symbol_of_the_same_company(monkeypatch, tmp_path) -> None:
    held_same = [{**r, "ticker": "FRA:2DG", "shares": 5.0} if r["ticker"] == "AXTI" else r
                 for r in _sheet_rows(AXTI=1_000.0)]
    both = {**_present_inputs(), "held_company": True, "company_held_symbols": ["FRA:2DG", "SIVE.ST"]}
    module, _calls = _wire_open(monkeypatch, tmp_path, rows=held_same, inputs=both)
    assert module.main(_eu(_OPEN) + ["--also-at-other-broker"]) == 2      # 還有 SIVE.ST 在持有 → 照擋
    only_same = {**_present_inputs(), "held_company": True, "company_held_symbols": ["FRA:2DG"]}
    module, _calls = _wire_open(monkeypatch, tmp_path, rows=held_same, inputs=only_same)
    assert module.main(_eu(_OPEN) + ["--also-at-other-broker"]) == 0


def test_tpe_and_bare_codes_are_the_same_listing_as_dot_tw() -> None:
    assert gsheets.canonical_symbol("TPE:2330") == gsheets.canonical_symbol("2330") == "2330.TW"
    assert gsheets.canonical_symbol("00981A") == "00981A.TW" and gsheets.canonical_symbol("AXTI") == "AXTI"
    values, formulas = _grid()
    with pytest.raises(ValueError, match="第 6 列已經是"):
        gsheets.plan_new_position(values, formulas, broker="TAISHIN", symbol="2330")     # 不給幣別：只看同一檔


def test_the_hint_names_the_sheet_spelling_when_the_broker_is_right(monkeypatch, tmp_path, capsys) -> None:
    rows = [{**r, "ticker": "0050.TW", "broker": "IB"} for r in _sheet_rows(X=1.0)]
    module, _calls = _wire_sheet(monkeypatch, tmp_path, rows=rows)
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None: (_ for _ in ()).throw(
        ValueError("比對條件 {'symbol': '0050', 'broker': 'IB'} 命中 0 列，必須恰好 1 列才可寫入")))
    argv = [a if a != "AXTI" else "0050" for a in _BUY]
    assert module.main(argv[:argv.index("--why")]) == 2
    assert "代號請寫成 Sheet 的寫法 0050.TW" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 11. R2 第三次覆核（2026-09-30）
# ---------------------------------------------------------------------------

def test_japanese_spellings_are_the_same_listing_like_taiwanese_ones() -> None:
    """blocking（台股修法的對稱面）：公式把 `7803.T`（JPY）轉成 TYO:7803——同一檔，比對也要當同一檔。
    2026-09-30 使用者定案：Sheet 用公司名冊的寫法——正規化方向是名冊的 `XXXX.T`（不為 Sheet 另做別名）。"""
    assert gsheets.canonical_symbol("TYO:7803") == gsheets.canonical_symbol("7803.t") == "7803.T"
    assert gsheets.canonical_symbol("TPE:ABC") == "TPE:ABC"            # TPE: 後面不是數字碼就不剝（不會併進美股 ABC）
    assert gsheets.canonical_symbol("TYO:ABC") == "TYO:ABC"            # 同理：TYO: 後面不是數字碼就不動
    values, formulas = _grid()
    with pytest.raises(ValueError, match="第 3 列已經是"):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol="TYO:7803")


def test_a_registry_spelled_japanese_listing_plans_like_any_other() -> None:
    """名冊寫法的日股（6324.T＝Harmonic Drive，registry 的 research ticker）配 JPY 過得了白名單、規劃得出插入點；
    `TYO:` 寫法拒收並提示名冊寫法。（收據解析得到公司由下一條用真名冊守。）"""
    values, formulas = _grid()
    plan = gsheets.plan_new_position(values, formulas, broker="IB", symbol="6324.T", currency="JPY")
    assert plan["insert_at"] == 5                                       # IB 最後一列持股（第 4 列 NVDA）的下一列
    with pytest.raises(ValueError, match="寫成公司名冊的寫法 6324.T"):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol="TYO:6324", currency="JPY")


def test_an_absent_readback_is_read_again_before_saying_so(monkeypatch, tmp_path) -> None:
    """第三次覆核 non-blocking：伺服器可能稍後才套用——判成「此刻沒套用」前隔幾秒再讀一次。"""
    module, calls = _wire_open(monkeypatch, tmp_path, open_fails=True)
    module.ABSENT_RECHECK_SECONDS = 0.001
    answers = iter(["absent", "landed"])
    monkeypatch.setattr(gsheets, "new_row_state", lambda plan, fill: next(answers))
    assert module.main(_OPEN + ["--apply"]) == 2
    assert calls["deleted"] == [5] and not module.TRADE_LOG.exists()


def test_company_held_symbols_come_from_the_real_resolution_path(monkeypatch) -> None:
    """第三次覆核 non-blocking（M13 存活）：測試原本都直接注入 company_held_symbols，正式路徑沒人守——
    它壞掉，「同公司換代號建倉」的 fail closed 就失效。"""
    import alpha.providers.briefs as briefs_mod
    import engine_b.disproof as disproof
    import identity.registry as reg
    import portfolio.holdings as holdings
    import webapp.store as store
    from engine_b import event_watch as ew
    from tests.test_record_trade import _module

    rows = [{"ticker": "FRA:2DG", "broker": "IB", "shares": 100.0, "bucket": "觀察"},
            {"ticker": "SIVE.ST", "broker": "FUBON", "shares": 50.0, "bucket": "觀察"}]
    monkeypatch.setattr(reg, "get_registry", lambda: object())
    monkeypatch.setattr(holdings, "resolve_holding", lambda row, registry=None: {
        "company_id": "co:sivers_semiconductors", "research_ticker": "SIVE.ST", "source": "test"})
    monkeypatch.setattr(holdings, "resolve_holdings", lambda rows_, registry=None: {"rows": [
        {"ticker": r["ticker"], "company_id": "co:sivers_semiconductors", "shares": r["shares"], "cash": False}
        for r in rows_]})
    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([], []))
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: {"watches": []})
    monkeypatch.setattr(disproof, "load_lifecycle", lambda *a, **k: {})
    monkeypatch.setattr(store.StateArtifactStore, "read", lambda self, kind: (None, None))
    monkeypatch.setattr(store.ArtifactStore, "read", lambda self, t: (None, None))
    from datetime import date

    out = _module()._research_inputs("TPE:9999", today=date(2026, 9, 30), sheet_rows=rows)
    assert out["held_company"] is True and out["company_held_symbols"] == ["FRA:2DG", "SIVE.ST"]


# ---------------------------------------------------------------------------
# 12. R2 覆核（2026-09-30，日股改用名冊寫法 ca4b012：GO＋順手修）
# ---------------------------------------------------------------------------

def test_registry_spelled_japanese_holdings_resolve_and_every_registry_listing_passes_the_whitelist() -> None:
    """這次定案要守的效果（T2）：名冊寫法 `6324.T` 解析得到公司、舊寫法 `TYO:6324` 解析不到——Sheet 改成名冊寫法
    才有意義；而且名冊裡每一檔日股的 research ticker 都要過得了建倉白名單（名冊加一檔公式抓不到的寫法時這裡先紅）。"""
    from pathlib import Path

    from identity.registry import get_registry
    from portfolio.holdings import resolve_holding

    registry = get_registry()
    assert resolve_holding({"ticker": "6324.T"}, registry=registry)["company_id"] == "co:harmonic_drive_systems"
    assert resolve_holding({"ticker": "TYO:6324"}, registry=registry)["company_id"] is None
    companies = json.loads((Path(__file__).resolve().parents[1] / "config" / "company_identity.json")
                           .read_text(encoding="utf-8"))["companies"]
    japanese = [c["research_ticker"] for c in companies if c.get("execution_currency") == "JPY" and c.get("research_ticker")]
    assert japanese, "名冊裡沒有日股——這條測試失去意義"
    for ticker in japanese:
        assert gsheets._symbol_currency_problem(ticker, "JPY") is None, ticker
        assert gsheets.canonical_symbol(ticker) == ticker, ticker          # 名冊寫法就是比對的正規形


def test_a_legacy_tyo_row_still_blocks_a_duplicate_registry_spelled_open() -> None:
    """T1：使用者若照舊習慣手寫一列 `TYO:6324`，用名冊寫法 `6324.T` 在同券商建倉仍要判成同一檔、拒收（不開重複列）。"""
    values, formulas = _grid()
    values[2][2] = formulas[2][2] = "TYO:6324"
    with pytest.raises(ValueError, match="第 3 列已經是"):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol="6324.T", currency="JPY")


@pytest.mark.parametrize("symbol, currency, message", [
    ("12345.T", "JPY", "認不得"),          # T3：白名單只收 4 碼數字（公式的 ^[0-9]+\.T$ 轉得出，但東證是 4 碼）
    ("123.T", "JPY", "認不得"),
    ("130A.T", "JPY", "認不得"),           # 東證英數代號：公式轉不出 TYO:，抓不到價
    ("ABC.T", "JPY", "認不得"),
    ("TYO:12345", "JPY", "認不得"),        # C4：不再提示一個又會被拒收的寫法
    ("6324", "JPY", "寫成公司名冊的寫法 6324.T"),   # C4：裸 4 碼配 JPY 提示日股寫法，不是 .TW
    ("tyo:6324", "JPY", "寫成公司名冊的寫法 6324.T"),
    ("6324.t", "JPY", "大寫"),             # JP-CASE-1：公式分大小寫，小寫轉不成 TYO:
    ("2330.tw", "TWD", "大寫"),            # 同一個洞的台股面（公式會拿到 TPE:2330.tw）
    ("nvda", "USD", "大寫"),
    (" NVDA", "USD", "大寫"),              # 寫進 Sheet 的是原字串：前後空白也讓 REGEXMATCH 失手
])
def test_whitelist_edges_and_case_are_rejected_before_anything_is_written(symbol, currency, message) -> None:
    values, formulas = _grid()
    with pytest.raises(ValueError, match=message):
        gsheets.plan_new_position(values, formulas, broker="IB", symbol=symbol, currency=currency)


@pytest.mark.parametrize("extra, currency", [([], "EUR"), (["--cash-column", "cash_twd"], "USD"), ([], "JPY")])
def test_existing_row_path_also_refuses_a_cash_column_in_another_currency(monkeypatch, tmp_path, extra, currency) -> None:
    """C1（R2 覆核，既有問題）：既有列加碼原本不檢查現金欄幣別——歐股／日股沒給 --cash-column 時，預設 cash_usd
    會把外幣金額當美元扣掉。現在兩條路徑都擋，而且在讀 Sheet 之前。"""
    from tests.test_record_trade import _module

    from fetchers import gsheets as gs

    reads = []
    monkeypatch.setattr(gs, "read_portfolio_values", lambda **k: reads.append(k) or [["symbol"]])
    module = _module()
    module.TRADE_LOG = tmp_path / "trade_log.jsonl"
    argv = ["--symbol", "FRA:2DG", "--side", "buy", "--shares", "10", "--price", "3", "--executed-at",
            "2026-09-30T10:00:00+02:00", "--broker", "IB", "--currency", currency, "--why", "x", *extra]
    assert module.main(argv) == 2 and reads == [] and not module.TRADE_LOG.exists()
    ok = argv + ["--cash-column", "none"] if not extra else [a if a != "cash_twd" else "none" for a in argv]
    reached = []

    def stop(**kwargs):
        reached.append(kwargs)
        raise RuntimeError("stop here")

    monkeypatch.setattr(gs, "read_portfolio_values", stop)
    module.main(ok)
    assert reached, "給 --cash-column none 要過得了幣別檢查、走到讀 Sheet"
