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
    body = [("IB", "觀察", "FRA:2DG"), ("IB", "觀察", "TYO:7803"), ("IB", "CORE", "NVDA"),
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
        gsheets.delete_position_row({"row": 3, "sheet_id": 7}, "AXTI")   # 第 3 列是 TYO:7803
    assert fake.bodies == []
    gsheets.delete_position_row({"row": 3, "sheet_id": 7}, "TYO:7803")
    assert fake.bodies[0]["requests"][0]["deleteDimension"]["range"]["startIndex"] == 2


# ---------------------------------------------------------------------------
# 5. record_trade 主流程
# ---------------------------------------------------------------------------

def _wire_open(monkeypatch, tmp_path, *, verify=(), cash_fails=False):
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(), inputs=_present_inputs())
    values, formulas = _grid()
    calls["reads"] = []
    monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas_=None, formulas=False, sheet=None:
                        calls["reads"].append(formulas) or (_grid()[1] if formulas else values))
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None:
                        [{"a1": "Portfolio!G7", "current": "5000"}])
    calls.update(opened=[], deleted=[])

    def open_row(plan, fill):
        calls["opened"].append((plan["insert_at"], dict(fill)))
        return {"status": "opened", "row": plan["insert_at"], "sheet_id": 7, "written": [{"a1": "new", "to": 1}]}

    def write(writes):
        if cash_fails:
            raise ValueError("現值不符")
        calls["writes"].append(writes)
        return {"written": [w["a1"] for w in writes]}

    monkeypatch.setattr(gsheets, "open_position_row", open_row)
    monkeypatch.setattr(gsheets, "verify_new_position", lambda plan, fill: list(verify))
    monkeypatch.setattr(gsheets, "delete_position_row", lambda opened, symbol: calls["deleted"].append(opened["row"]))
    monkeypatch.setattr(gsheets, "write_portfolio_cells", write)
    return module, calls


_OPEN = _BUY + ["--open-position", "--bucket", "觀察", "--company", "AXT Inc"]


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


@pytest.mark.parametrize("kw", [{"verify": ("新列市值是 0",)}, {"cash_fails": True}])
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
