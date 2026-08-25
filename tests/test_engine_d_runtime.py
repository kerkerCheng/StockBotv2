from __future__ import annotations

import ast
from pathlib import Path
from zoneinfo import ZoneInfo

from decision_lab.adapters.graph import Neo4jReadOnlyQueryPort
from decision_lab.workflow_ports import WorkflowDataProvider
from engine_d_runtime.adapters import DefaultRuntimeProvider
from engine_d_runtime.adapters import bounded_evidence_query


NOW = "2026-07-22T02:00:00+00:00"


def test_bounded_graph_query_does_not_read_undefined_claim_type() -> None:
    assert "claim.claim_type" not in bounded_evidence_query()


class _GraphPort:
    def __init__(self, evidence_row=None, *, company_rows=None, error=False):
        self.evidence_row = evidence_row
        self.company_rows = company_rows or []
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def query(self, cypher: str, **params):
        self.calls.append((cypher, params))
        if self.error:
            raise RuntimeError("C:/private/neo4j canary-password")
        if "company_name" in params:
            return list(self.company_rows)
        return [self.evidence_row] if self.evidence_row is not None else []


def _financial(status="observed"):
    if status != "observed":
        return {"ticker": "SIVE.ST", "status": status}
    return {
        "ticker": "SIVE.ST",
        "status": "observed",
        "as_of": "2026-07-20",
        "fetched_at": "2026-07-20T01:00:00+00:00",
        "source": "fixture://engine-c",
        "cash_and_equivalents": 100.0,
        "total_debt": 20.0,
        "free_cash_flow_ttm": -40.0,
    }


def _checklist(*, manual=False, ticker="SIVE.ST"):
    item_status = "manual_required" if manual else "manual_reviewed"
    items = {
        "gross_margin_trend": {"status": "ok", "value": [1, 2]},
        "customer_concentration": {"status": item_status},
        "backlog": {"status": item_status},
        "dilution": {"status": "ok"},
        "valuation_pressure": {"status": "ok"},
    }
    return {
        "ticker": ticker,
        "engine_c_available": True,
        "items": items,
        "gate_pass": not manual,
    }


def _market(ticker: str, currency: str):
    return {
        "status": "observed",
        "ticker": ticker,
        "price": 2.5,
        "currency": currency,
        "adv20": 1_000_000.0,
        "as_of": "2026-07-22T01:00:00+00:00",
        "fetched_at": "2026-07-22T01:01:00+00:00",
        "unit_status": "ok",
        "source": "fixture://market",
        "blockers": [],
    }


def _sheet_rows():
    return [
        {
            "ticker": "FRA:2DG",
            "neo4j_id": "co:sivers_semiconductors",
            "shares": 10.0,
            "currency": "EUR",
            "market_value_base": "25.0",
            "nav_base": "10000.0",
            "base_currency": "USD",
            "avg_cost": 999.0,
            "notes": "must not leave adapter",
        }
    ]


def _evidence_row(*, graph_count=10, focus_id="co:sivers_semiconductors"):
    return {
        "graph_node_count": graph_count,
        "focus_id": focus_id,
        "focus_name": "Sivers Semiconductors AB",
        "edges": [
            {
                "edge_key": "edge:laser",
                "src_id": focus_id,
                "dst_id": "comp:laser",
                "relation": "SUPPLIES",
                "confidence": 0.8,
                "source_ids": ["s1"],
            },
            {
                "edge_key": "edge:alternative",
                "src_id": "co:other",
                "dst_id": "comp:laser",
                # counter path 改為明列後，relation 必須是 vocab 真的有的那些。
                # 舊值 SUBSTITUTES 只是子字串比對時代的產物：vocab 裡沒有它，
                # loader 會擋掉，圖裡不可能存在這種 relation。
                "relation": "COMPETES_WITH",
                "confidence": 0.5,
                "source_ids": ["s2"],
            },
        ],
        # 註：Neo4j 的 type(rel) 是大寫；判定端 casefold 後比對 vocab。
        "claims": [{"id": "claim:1", "statement": "bounded"}],
        "assertions": [{"id": "ea:1", "edge_key": "edge:laser"}],
        "claim_sources": [
            {
                "id": "doc:customer",
                "origin_entity": "GlobalFoundries",
                "evidence_tier": 2,
                "source_type": "filing",
            }
        ],
        "assertion_sources": [],
    }


def _provider(*, graph=None, **overrides):
    defaults = {
        "graph_port": graph or _GraphPort(_evidence_row()),
        "financial_fetcher": lambda _ticker: _financial(),
        "checklist_fetcher": lambda _ticker: _checklist(),
        "market_fetcher": _market,
        "fx_fetcher": lambda pair, _at: {
            "status": "observed",
            "pair": pair,
            "rate": 0.1,
            "as_of": "2026-07-22T01:00:00+00:00",
            "fetched_at": "2026-07-22T01:01:00+00:00",
            "source": "fixture://fx",
        },
        "holdings_fetcher": _sheet_rows,
    }
    defaults.update(overrides)
    return DefaultRuntimeProvider(**defaults)


def test_provider_implements_injectable_workflow_port_and_exact_identity() -> None:
    graph = _GraphPort(
        _evidence_row(),
        company_rows=[{"company_id": "co:sivers_semiconductors"}],
    )
    provider = _provider(graph=graph)

    by_ticker = provider.resolve_identity(ticker_hint="sive.st")
    by_name = provider.resolve_identity(company_hint="Sivers Semiconductors AB")
    graph.company_rows = []
    unknown = provider.resolve_identity(company_hint="Not A Company")

    assert isinstance(provider, WorkflowDataProvider)
    assert by_ticker.status == "resolved"
    assert by_ticker.company_id == "co:sivers_semiconductors"
    assert by_name.company_id == "co:sivers_semiconductors"
    assert unknown.status == "unresolved_identity"
    assert "unresolved_identity" in unknown.blockers


def test_graph_empty_and_company_missing_are_distinct_and_bounded() -> None:
    identity = _provider().resolve_identity(ticker_hint="SIVE.ST")
    empty = _provider(graph=_GraphPort(_evidence_row(graph_count=0))).snapshot(
        identity=identity,
        evaluation_at=NOW,
    )
    missing = _provider(
        graph=_GraphPort(_evidence_row(focus_id=None))
    ).snapshot(identity=identity, evaluation_at=NOW)

    assert empty.evidence["status"] == "graph_empty"
    assert missing.evidence["status"] == "graph_company_missing"
    assert empty.evidence["causal_paths"] == []
    assert any(order.code == "graph_empty" for order in empty.work_orders)
    assert any(order.code == "graph_company_missing" for order in missing.work_orders)


def test_graph_provider_failure_is_redacted_to_stable_status() -> None:
    provider = _provider(graph=_GraphPort(error=True))
    identity = provider.resolve_identity(ticker_hint="SIVE.ST")

    snapshot = provider.snapshot(identity=identity, evaluation_at=NOW)

    assert snapshot.evidence["status"] == "graph_unavailable"
    assert "canary" not in repr(snapshot)
    assert "private" not in repr(snapshot)


def test_financial_missing_and_cohr_manual_required_are_preserved() -> None:
    missing_provider = _provider(
        financial_fetcher=lambda _ticker: {"status": "missing"}
    )
    sive = missing_provider.resolve_identity(ticker_hint="SIVE.ST")
    missing = missing_provider.snapshot(identity=sive, evaluation_at=NOW)

    cohr_provider = _provider(
        financial_fetcher=lambda ticker: _financial() | {"ticker": ticker},
        checklist_fetcher=lambda ticker: _checklist(manual=True, ticker=ticker),
    )
    cohr = cohr_provider.resolve_identity(ticker_hint="COHR")
    cohr_snapshot = cohr_provider.snapshot(identity=cohr, evaluation_at=NOW)

    assert missing.financial["status"] == "missing"
    codes = {order.code for order in cohr_snapshot.work_orders}
    assert "financial_checklist_manual_required:customer_concentration" in codes
    assert "financial_checklist_manual_required:backlog" in codes
    assert cohr_snapshot.financial["checklist"]["backlog"]["status"] == "manual_required"


def test_missing_price_and_fx_or_wrong_fx_direction_fail_closed() -> None:
    no_price = _provider(
        market_fetcher=lambda _ticker, _currency: {"status": "missing"},
        fx_fetcher=None,
    )
    identity = no_price.resolve_identity(ticker_hint="SIVE.ST")
    missing = no_price.snapshot(identity=identity, evaluation_at=NOW)

    wrong = _provider(
        fx_fetcher=lambda _pair, _at: {
            "status": "observed",
            "pair": "USD/SEK",
            "rate": 10.0,
            "as_of": "2026-07-22T01:00:00+00:00",
            "fetched_at": "2026-07-22T01:01:00+00:00",
            "source": "fixture://wrong-direction",
        }
    ).snapshot(identity=identity, evaluation_at=NOW)

    assert missing.market["status"] == "missing"
    assert missing.fx["status"] == "missing"
    assert wrong.fx["pair"] == "USD/SEK"
    assert any(order.code == "fx_direction_mismatch" for order in wrong.work_orders)


def test_same_currency_is_the_only_implicit_one_to_one_fx() -> None:
    provider = _provider()

    same, same_orders = provider._read_fx("USD", "USD", NOW)
    foreign_without_provider = DefaultRuntimeProvider(
        fx_fetcher=None,
        holdings_fetcher=lambda: [],
    )._read_fx("SEK", "USD", NOW)

    assert same["rate"] == 1.0
    assert same["pair"] == "USD/USD"
    assert same_orders == []
    assert foreign_without_provider[0]["status"] == "missing"


def test_sheet_adapter_only_emits_strict_mark_to_market_minimum() -> None:
    provider = _provider()

    holdings = provider.current_holdings(evaluation_at=NOW)
    malformed = _provider(
        holdings_fetcher=lambda: [
            {
                "ticker": "FRA:2DG",
                "shares": 10.0,
                "avg_cost": 2.0,
                "currency": "EUR",
            }
        ]
    ).current_holdings(evaluation_at=NOW)

    assert holdings["status"] == "available"
    assert holdings["nav_base"] == 10_000.0
    assert holdings["base_currency"] == "USD"
    assert holdings["rows"] == [
        {
            "ticker": "FRA:2DG",
            "company_id": "co:sivers_semiconductors",
            "shares": 10.0,
            "currency": "EUR",
            "market_value_base": 25.0,
        }
    ]
    assert "avg_cost" not in holdings["rows"][0]
    assert "notes" not in holdings["rows"][0]
    assert malformed == {
        "status": "malformed",
        "rows": [],
        "blockers": ["holdings_malformed"],
    }


def test_runtime_graph_query_uses_existing_read_only_port_without_write_surface() -> None:
    class Result:
        def data(self):
            return [_evidence_row()]

    class Session:
        def __init__(self):
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def run(self, cypher, **params):
            self.queries.append((cypher, params))
            return Result()

    class Driver:
        def __init__(self):
            self.kwargs = None
            self.session_value = Session()

        def session(self, **kwargs):
            self.kwargs = kwargs
            return self.session_value

    driver = Driver()
    graph = Neo4jReadOnlyQueryPort(driver)
    provider = _provider(graph=graph)
    identity = provider.resolve_identity(ticker_hint="SIVE.ST")

    snapshot = provider.snapshot(identity=identity, evaluation_at=NOW)

    assert snapshot.evidence["status"] == "available"
    assert driver.kwargs == {"default_access_mode": "READ"}
    assert not hasattr(graph, "write")
    cypher = driver.session_value.queries[0][0].upper()
    assert "CALL " not in cypher
    assert "CREATE " not in cypher
    assert "MERGE " not in cypher
    assert " DELETE " not in cypher


def test_decision_lab_does_not_import_concrete_current_state_authorities() -> None:
    root = Path(__file__).resolve().parents[1] / "decision_lab"
    forbidden = ("engine_c", "fetchers", "neo4j")
    findings: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            if any(name == prefix or name.startswith(prefix + ".") for name in names for prefix in forbidden):
                findings.append(f"{path.name}:{names}")
    assert findings == []


def test_manual_runway_reaches_the_frozen_financial_snapshot() -> None:
    """人工補的 runway 輸入值必須一路傳到決策層。

    yfinance 在財報後常暫時清空 free_cash_flow_ttm，runway 因此變成
    manual_required 並讓 coverage gate 歸零。derive_runway 早就接受
    manual_runway 並自行驗證 timestamp，但先前沒有任何地方提供它——
    這個測試守的就是那條走廊。
    """
    baseline = _financial() | {
        "status": "manual_required",
        "free_cash_flow_ttm": None,
        "manual_runway": {
            "cash_and_equivalents": 412.0,
            "total_debt": 85.0,
            "free_cash_flow_ttm": -25.0,
            "source": "fixture://q2-cash-flow-statement",
            "as_of": "2026-07-20",
        },
    }
    provider = _provider(financial_fetcher=lambda _ticker: baseline)
    identity = provider.resolve_identity(ticker_hint="SIVE.ST")

    snapshot = provider.snapshot(identity=identity, evaluation_at=NOW)

    assert snapshot.financial["manual_runway"]["free_cash_flow_ttm"] == -25.0
    assert snapshot.financial["manual_runway"]["source"] == "fixture://q2-cash-flow-statement"


def test_absent_manual_runway_does_not_fabricate_the_key() -> None:
    provider = _provider(financial_fetcher=lambda _ticker: _financial())
    identity = provider.resolve_identity(ticker_hint="SIVE.ST")

    snapshot = provider.snapshot(identity=identity, evaluation_at=NOW)

    assert "manual_runway" not in snapshot.financial


def test_counter_path_relations_are_enumerated_not_substring_guessed() -> None:
    """counter path 的判定必須是明列，不是對 relation 名稱做子字串比對。

    舊寫法比對 substitut／alternative／compete／counter 四個 token：既猜不到
    constrained_by（真正表達「限定／反證」的關係），未來也會誤命中任何名字裡剛好
    含 counter 的 relation。改成明列後，新增 relation 時必須順便回答「它算不算
    反向路徑」——那正是應該被強迫回答的問題。
    """

    import json

    from engine_d_runtime.adapters import counter_path_relations

    relations = counter_path_relations()
    root = Path(__file__).resolve().parent.parent
    vocab = json.loads(
        (root / "schema" / "vocab.json").read_text(encoding="utf-8")
    )

    # 唯一權威是 vocab，不是程式裡的字面值。
    assert relations == frozenset(
        value.casefold() for value in vocab["counter_path_relation"]
    )
    # 每個 counter path relation 都必須是合法 relation，否則 loader 根本寫不進圖。
    assert set(vocab["counter_path_relation"]) <= set(vocab["relation"])
    # 名字裡含 counter 不再等於是 counter path。
    assert "counterfeits" not in relations
    assert "constrained_by" in relations


def test_counter_paths_are_not_crowded_out_by_the_edge_limit() -> None:
    """反證不得因為無關的邊變多而被取樣上限擠掉。

    事發（2026-08-06）：evidence bound 從 1 hop 放寬到 2 hop 後，co:axt 的
    COMPETES_WITH（confidence 0.5）被遠處高信心的邊擠出 edge_limit=24，coverage
    gate 因此從 available 退回 graph_coverage_deficit——gate 結果被與 thesis 無關
    的邊翻轉。查詢改成 counter path 優先佔位。
    """

    from engine_d_runtime.adapters import bounded_evidence_query

    query = bounded_evidence_query()
    tail = query[query.index("ORDER BY"):]

    assert query.count("ORDER BY") == 1
    # is_counter 必須排在 confidence 之前。
    assert tail.index("is_counter") < tail.index("confidence")
    assert "$counter_relations" in query


def test_focus_direct_edges_outrank_distant_neighbours() -> None:
    """焦點公司自己的邊不得被遠處鄰居擠出取樣上限。

    事發（2026-08-06）：evidence bound 放寬到 2 hop 後，co:axt 自己 8 條直接因果邊
    被遠處高信心的邊擠掉，該 cohort 的 assessment evidence_refs 因此集體失效。距離
    不是靠 hop 上限控制，是靠排序：反證 > 直接關係 > 信心。
    """

    from engine_d_runtime.adapters import bounded_evidence_query

    query = bounded_evidence_query()
    tail = query[query.index("ORDER BY"):]

    assert "is_direct" in tail
    assert tail.index("is_counter") < tail.index("is_direct") < tail.index("confidence")


def test_evidence_hops_is_policy_driven_and_bounded() -> None:
    """hop 數是相關性的代理指標；它必須登記在 policy，而且不得無上限放大。"""

    import json

    from engine_d_runtime.adapters import evidence_hops

    root = Path(__file__).resolve().parent.parent
    policy = json.loads(
        (root / "config" / "investment_policy.json").read_text(encoding="utf-8")
    )

    assert policy["probe_lane"]["evidence_hops"] == evidence_hops()
    assert 1 <= evidence_hops() <= 3


def _tz(name: str) -> ZoneInfo:
    """可控的時區物件，取代先前的 process 全域切換。

    先前這裡是 `TZ` ＋ `time.tzset()` 的 contextmanager，而兩者只在 POSIX 有效——
    主要開發機是 Windows，於是這兩條測試**永遠 skip**。skip 不等於已驗證：
    date-only → 本機午夜這條路徑在唯一實際執行它的平台上沒有覆蓋，而它已經
    實測炸過兩次（2026-08-14、08-17），且台北 06:30 的 daily routine 正落在
    00:00–08:00 這個結構上必中的窗口內。

    改成注入時區之後，測試不碰 process 全域狀態，因此在任何平台都實際執行；
    `_safe_timestamp` 的預設行為（`local_tz=None` → `.astimezone()`）未改變。
    """

    return ZoneInfo(name)


def test_local_calendar_snapshot_date_is_not_pushed_into_the_future() -> None:
    """date-only 的 `snapshot_date` 是本機日曆日，不得貼 UTC 午夜。

    事發（2026-08-14、08-17 兩次實測）：`financial_snapshots.snapshot_date` 由
    `date.today()` 產生（本機時區），`_safe_timestamp` 卻貼 UTC 午夜。台北 06:30 的
    daily routine 因此拿到 as_of=今日 00:00Z、evaluation_at=昨日 22:xxZ，
    `_normalize_financial` 判 financial_timestamp_future 把整份財務 quarantine。
    台北 00:00–08:00 之間結構上必中——閘門攔下的是時區寫法，不是未來資料（L15）。
    """

    from decision_lab.context import _normalize_financial
    from engine_d_runtime.adapters import _safe_timestamp

    # 台北 2026-08-17 06:51 跑 routine：本機日曆日已跨日，UTC 還在前一天。
    evaluation_at = "2026-08-16T22:51:45+00:00"

    taipei = _tz("Asia/Taipei")

    def normalize(snapshot_date: str) -> dict:
        return _normalize_financial(
            {
                "status": "observed",
                "ticker": "AXTI",
                "as_of": _safe_timestamp(snapshot_date, local_tz=taipei),
                "fetched_at": _safe_timestamp("2026-08-16T22:30:00+00:00"),
                "source": "yfinance.info",
                "cash_and_equivalents": 100.0,
                "total_debt": 20.0,
                "free_cash_flow_ttm": -40.0,
            },
            expected_ticker="AXTI",
            evaluation_at=evaluation_at,
        )

    today = normalize("2026-08-17")
    assert "financial_timestamp_future" not in today["blockers"]
    assert today["status"] == "available"

    # 分開解釋不等於放寬：真正的未來日期仍必須 fail closed。
    tomorrow = normalize("2026-08-18")
    assert tomorrow["status"] == "quarantined"
    assert tomorrow["blockers"] == ["financial_timestamp_future"]

    # 本機日 00:00 比 UTC 午夜早一個時區位移，stale 窗因此更嚴、不是更鬆。
    assert normalize("2026-07-20")["status"] == "stale"


def test_date_only_timestamp_is_symmetric_with_date_today() -> None:
    """解釋端與產生端共用同一個本機時區：UTC 機器上行為不變。"""

    from engine_d_runtime.adapters import _safe_timestamp

    assert (
        _safe_timestamp("2026-08-17", local_tz=_tz("UTC"))
        == "2026-08-17T00:00:00+00:00"
    )
    assert (
        _safe_timestamp("2026-08-17", local_tz=_tz("Asia/Taipei"))
        == "2026-08-17T00:00:00+08:00"
    )
    # 完整 timestamp 不受影響——它本來就是精確 instant。
    assert (
        _safe_timestamp("2026-08-16T22:30:00+00:00", local_tz=_tz("Asia/Taipei"))
        == "2026-08-16T22:30:00+00:00"
    )


def test_injected_timezone_matches_process_default() -> None:
    """注入不得改變預設行為——否則測的是另一條路徑（L15：閘門要攔對東西）。

    這是上面兩條測試的效力前提：它們用注入時區驗證邏輯，但 production 走的是
    `local_tz=None`。兩者若不等價，測試通過也不代表 production 正確。
    """

    from datetime import datetime

    from engine_d_runtime.adapters import _safe_timestamp

    local_offset = datetime.now().astimezone().tzinfo
    assert _safe_timestamp("2026-08-17") == _safe_timestamp(
        "2026-08-17", local_tz=local_offset
    )
