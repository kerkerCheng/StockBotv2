"""API 契約：**九種缺席語意不得被壓成一句 unavailable**，以及錯誤回應不吐任何內部資訊。

這裡守的是 Step 5 最容易失守的一條：APP 為了畫面好看，把
`available／partial／missing／not_modeled／not_applicable／review_required／stale／blocked／
刻意不主張` 全部 flatten 成「無資料」。那會讓使用者失去**唯一**能分辨「該去補」與
「這已經是答案」的資訊，而那正是這一層存在的理由。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from webapp.api import create_app
from webapp.materialize import materialize_view, write_vocabularies
from webapp.store import ArtifactStore

from test_webapp_materialize import fake_view

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path):
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("READY", price=281.86, quote_unit="USD",
                                           fair_value=223.6034, currency="USD")))
    store.write(materialize_view(fake_view(
        "ABSTAIN", price=5970.0, quote_unit="JPY", fair_value=None,
        absence_kind="deliberate_abstention", readiness_state="blocked",
        blockers=["headline：missing"], reason="刻意不主張目標倍數：126x 錨不住")))
    store.write(materialize_view(fake_view(
        "NOTAPPLIC", price=10.0, quote_unit="GBp", fair_value=None,
        absence_kind="method_not_applicable", readiness_state="blocked",
        blockers=["headline：missing"], reason="本益比法對非正 EPS 無定義")))
    store.write(materialize_view(fake_view(
        "UPSTREAM", price=47.518, quote_unit="GBp", fair_value=None,
        absence_kind="upstream_unavailable", readiness_state="blocked",
        blockers=["headline：missing"], reason="內部 EPS 缺席")))
    write_vocabularies(store)
    return TestClient(create_app(tmp_path))


# ---------------------------------------------------------------------------
# list / overview
# ---------------------------------------------------------------------------

def test_list_returns_the_fields_the_card_needs(client) -> None:
    body = client.get("/api/v1/stocks").json()
    assert body["count"] == 4
    row = next(r for r in body["stocks"] if r["ticker"] == "READY")
    assert row["price"]["value"] == 281.86
    assert row["price"]["quote_unit"] == "USD"
    assert row["future_target"]["value"] == 223.6034
    assert row["implied_return"]["simple"]["value"] == -0.2
    assert row["readiness"]["state"] == "ready"
    assert row["generated_at"] and row["freshness"]["state"] in {"fresh", "stale"}


def test_list_never_flattens_the_four_absences_into_one_word(client) -> None:
    """四檔各自的缺席理由必須互相可分辨——這是整個 Step 5 語意債的驗收條件。"""
    body = client.get("/api/v1/stocks").json()
    kinds = {r["ticker"]: r["future_target"]["absence_kind"] for r in body["stocks"]}
    assert kinds["ABSTAIN"] == "deliberate_abstention"
    assert kinds["NOTAPPLIC"] == "method_not_applicable"
    assert kinds["UPSTREAM"] == "upstream_unavailable"
    assert kinds["READY"] is None
    assert len({k for k in kinds.values() if k}) == 3        # 三種語意，三個值


def test_settled_absence_is_marked_so_the_ui_can_stop_asking_for_more_work(client) -> None:
    body = {r["ticker"]: r for r in client.get("/api/v1/stocks").json()["stocks"]}
    assert body["ABSTAIN"]["primary_attention"]["settled"] is True
    assert body["NOTAPPLIC"]["primary_attention"]["settled"] is True
    assert body["UPSTREAM"]["primary_attention"]["settled"] is False   # 這一個**該**去補上游


def test_settled_absence_does_not_make_readiness_better(client) -> None:
    """「刻意不主張」是答案，但它**不讓 blocked 變成 ready**——那是兩件事。"""
    for ticker in ("ABSTAIN", "NOTAPPLIC", "UPSTREAM"):
        assert client.get(f"/api/v1/stocks/{ticker}").json()["readiness"]["state"] == "blocked"


def test_missing_is_never_rendered_as_zero(client) -> None:
    for ticker in ("ABSTAIN", "NOTAPPLIC", "UPSTREAM"):
        row = client.get(f"/api/v1/stocks/{ticker}").json()["overview"]
        assert row["future_target"]["value"] is None
        assert row["implied_return"]["simple"]["value"] is None
        assert row["implied_return"]["annualized"]["value"] is None


def test_quote_units_are_carried_not_normalised(client) -> None:
    """GBp（便士）與 GBP（英鎊）差 100 倍。API 原樣帶單位，**不換算、不省略**。"""
    row = next(r for r in client.get("/api/v1/stocks").json()["stocks"] if r["ticker"] == "UPSTREAM")
    assert row["price"]["value"] == 47.518
    assert row["price"]["quote_unit"] == "GBp"


def test_correlation_warning_appears_on_both_surfaces(client) -> None:
    """相關性警語每天都要講一次——清單與明細都要，不因每天一樣而省略。"""
    assert "同一個賭注" in client.get("/api/v1/stocks").json()["correlation_warning"]
    assert "同一個賭注" in client.get("/api/v1/stocks/READY").json()["correlation_warning"]


# ---------------------------------------------------------------------------
# detail
# ---------------------------------------------------------------------------

def test_detail_returns_the_whole_materialized_analyst_view(client) -> None:
    body = client.get("/api/v1/stocks/READY").json()
    for key in ("headline", "fundamental", "why", "research", "entry", "readiness", "refresh"):
        assert key in body["view"], key


def test_blocker_details_say_which_layer_and_why(client) -> None:
    readiness = client.get("/api/v1/stocks/ABSTAIN").json()["readiness"]
    detail = readiness["blocker_details"][0]
    assert detail["panel"] == "headline"
    assert detail["absence_kind"] == "deliberate_abstention"
    assert detail["settled"] is True
    assert "錨不住" in detail["reason"]
    assert len(readiness["blocker_details"]) == len(readiness["blockers"])


def test_entry_is_optional_and_never_counts_as_a_blocker(client) -> None:
    readiness = client.get("/api/v1/stocks/READY").json()["readiness"]
    assert readiness["state"] == "ready"
    assert readiness["blockers"] == []
    assert readiness["optional_unavailable"] == ["entry：missing"]


# ---------------------------------------------------------------------------
# meta：字彙不是 APP 自己維護的第二份
# ---------------------------------------------------------------------------

def test_meta_serves_the_materialized_vocabulary(client) -> None:
    body = client.get("/api/v1/meta").json()
    vocab = body["vocabularies"]
    assert "deliberate_abstention" in vocab["absence_kinds"]
    assert "deliberate_abstention" in vocab["settled_absence_kinds"]
    assert set(vocab["accounting_basis_display"]) >= {"gaap", "non_gaap"}


def test_accounting_basis_label_never_claims_a_standard_the_authority_cannot_support(client) -> None:
    """澳洲／日本／英國公司在 ledger 裡都寫 `gaap`。label **不得**讓人以為系統宣稱它們用 US GAAP。"""
    display = client.get("/api/v1/meta").json()["vocabularies"]["accounting_basis_display"]
    label = display["gaap"]["label"]
    for forbidden in ("US GAAP", "美國會計準則", "IFRS", "AASB", "日本基準"):
        assert forbidden not in label, (forbidden, label)
    assert "as reported" in label.lower() or "法定" in label
    assert "不主張" in display["gaap"]["note"]


def test_meta_is_honest_when_the_vocabulary_was_never_materialized(tmp_path) -> None:
    body = TestClient(create_app(tmp_path)).get("/api/v1/meta").json()
    assert body["vocabularies"] is None
    assert "materialize" in body["vocabularies_reason"]


def test_meta_declares_what_the_app_does_not_do(client) -> None:
    body = client.get("/api/v1/meta").json()
    joined = "".join(body["not_offered"])
    for promise in ("寫入端點", "runtime LLM", "部位尺寸", "排序"):
        assert promise in joined, promise


# ---------------------------------------------------------------------------
# security / error shape
# ---------------------------------------------------------------------------

def test_errors_never_leak_paths_tracebacks_or_credentials(client) -> None:
    for path in ("/api/v1/stocks/NOPE", "/nope", "/static/../api.py", "/static/secrets"):
        response = client.get(path)
        assert response.status_code in (404, 503)
        text = response.text
        for leak in ("Traceback", "library/private", "library\\private", "C:\\", "/Users/",
                     "site-packages", "password", "token"):
            assert leak not in text, (path, leak)


def test_an_unexpected_exception_returns_a_fixed_shape_not_its_message(client, monkeypatch) -> None:
    """未預期例外的訊息可能含檔案路徑或查詢內容——**一律不得回給用戶端**。

    這條同時是上面那條的補集：`/nope` 走的是 `HTTPException` 處理器，這裡走的是
    catch-all 處理器。少了它，catch-all 那一段就沒有任何測試看得到（L14：未量測的機制）。
    """
    from webapp.store import ArtifactStore

    secret = "boom at " + str(ROOT / "library" / "private" / "alpha" / "valuation" / "COHR.jsonl")

    def explode(self):
        raise RuntimeError(secret)

    monkeypatch.setattr(ArtifactStore, "tickers", explode)
    # `raise_server_exceptions=False` ＝ 用真實用戶端會看到的行為。Starlette 的
    # `ServerErrorMiddleware` 會先把 handler 產出的回應送出去、再把例外往上丟給 server 記 log；
    # TestClient 預設把那個 re-raise 也丟給測試，於是看不到使用者實際收到的東西。
    client = TestClient(client.app, raise_server_exceptions=False)
    response = client.get("/api/v1/stocks", headers={"accept": "application/json"})
    assert response.status_code == 500
    body = response.json()["error"]
    assert body == {"kind": "internal_error", "status": 500, "message": "request failed"}
    assert "boom" not in response.text and "library" not in response.text


def test_static_assets_are_an_allowlist(client) -> None:
    for name in ("index.html", "app.js", "styles.css"):
        assert client.get(f"/static/{name}").status_code == 200
    for name in ("api.py", "..%2fapi.py", "secrets.json", ".meta.json"):
        assert client.get(f"/static/{name}").status_code == 404


def test_security_headers_are_present_on_every_response(client) -> None:
    for path in ("/", "/static/app.js", "/api/v1/stocks", "/api/v1/stocks/READY"):
        headers = client.get(path).headers
        assert headers["cache-control"] == "no-store"
        assert headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_no_response_ever_contains_a_private_path(client) -> None:
    for path in ("/api/v1/stocks", "/api/v1/stocks/READY", "/api/v1/meta"):
        text = client.get(path).text
        assert "library/private" not in text
        assert "library\\\\private" not in text


def test_public_bind_requires_an_explicit_opt_in(monkeypatch) -> None:
    from webapp.api import bind_host

    monkeypatch.setenv("STOCKBOT_APP_HOST", "0.0.0.0")
    monkeypatch.delenv("STOCKBOT_APP_ALLOW_PUBLIC_BIND", raising=False)
    with pytest.raises(RuntimeError, match="裸露 origin"):
        bind_host()
    monkeypatch.setenv("STOCKBOT_APP_ALLOW_PUBLIC_BIND", "1")
    assert bind_host() == "0.0.0.0"
    monkeypatch.delenv("STOCKBOT_APP_HOST")
    assert bind_host() == "127.0.0.1"


# ---------------------------------------------------------------------------
# 前端：只改資訊階層，不產生新的 summary judgment
# ---------------------------------------------------------------------------

def test_frontend_contains_no_arithmetic_on_research_numbers() -> None:
    """UI 不得自己算 gap／報酬／年化。允許的只有排版（toLocaleString）與 ×100 的百分比呈現。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    for token in ("fair_value /", "/ price", "* target", "Math.pow", "365.25", "** (",
                  "value - ", "value / "):
        assert token not in source, token


def test_frontend_reads_its_vocabulary_from_the_api() -> None:
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "VOCAB.absence_kinds" in source
    assert "VOCAB.accounting_basis_display" in source
    # 前端只允許一份**縮寫標籤**對照（畫面寬度所需），完整說明一律來自 API。
    assert source.count("ABSENCE_SHORT") <= 3


def test_frontend_never_hardcodes_a_hurdle_or_target_multiple() -> None:
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    for token in ("0.10", "0.15", "0.20", "target_pe", "hurdle =", "assumeMultiple"):
        assert token not in source, token


def test_index_html_loads_no_external_resource() -> None:
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    for token in ("http://", "https://", "cdn.", "googleapis"):
        assert token not in html, token


# ---------------------------------------------------------------------------
# 白話別名（2026-09-08 使用者：「全部是內部術語，基本上看不懂」）
# ---------------------------------------------------------------------------

def test_plain_labels_are_served_from_the_api_not_a_second_frontend_table(client) -> None:
    """白話別名的家只有一個：read model 的 contracts → `.meta.json` → API。

    ⚠ 先前 `absence_kind` 的短標籤是 app.js 裡的硬編碼表——那是 L16 說的重造品：
    字彙一改它就開始偏離，而且不會有東西報錯。
    """
    vocab = client.get("/api/v1/meta").json()["vocabularies"]
    for key in ("plain_panel_titles", "plain_line_labels", "plain_absence_short",
                "plain_readiness", "price_series_note"):
        assert key in vocab, key
    assert vocab["plain_absence_short"]["deliberate_abstention"] == "刻意不下判斷"
    assert set(vocab["plain_absence_short"]) == set(vocab["absence_kinds"]), (
        "短標籤與完整說明必須涵蓋同一組字彙——少一個就會有一格顯示裸 key"
    )
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    # ⚠ 禁的是「當成現行對照表使用」，不是提到這個名字——app.js 刻意留著一行移除紀錄，
    #    那正是防止它被重新加回來的剎車（同 AGENTS 對已拔除訊號字彙的處理）。
    for usage in ("const ABSENCE_SHORT", "ABSENCE_SHORT["):
        assert usage not in source, f"前端不得再維護第二份缺席字彙對照表：{usage}"
    assert "VOCAB.plain_absence_short" in source


def test_plain_labels_never_claim_more_than_the_vocabulary_does() -> None:
    """白話化**不得順手加上 authority 沒有的東西**（同 `accounting_basis` 那條）。"""
    from briefing.analyst_view.contracts import PLAIN_ABSENCE_SHORT, PLAIN_READINESS

    joined = " ".join(PLAIN_ABSENCE_SHORT.values()) + " ".join(
        f"{v['label']}{v['note']}" for v in PLAIN_READINESS.values())
    for overclaim in ("建議", "推薦", "安全", "值得買", "該買"):
        assert overclaim not in joined, f"白話別名不得宣稱 authority 沒有的東西：{overclaim}"
    # 「可以買」只准以否定形式出現——那句話正是這一欄最容易被誤讀的地方。
    assert "不是「可以買」的意思" in PLAIN_READINESS["ready"]["note"]
    assert joined.count("可以買") == joined.count("不是「可以買」")


def test_single_stock_page_leads_with_the_answer_then_the_price(client) -> None:
    """單檔頁的順序本身是回饋的修正：先結論、再價格，細節收成一個 details。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    block = source.split("async function renderDetail", 1)[1]
    block = re.split(r"\n(?:async )?function ", block, maxsplit=1)[0]
    order = [block.index(name) for name in
             ("conclusionCard(", "priceCard(", "blockerCard(", "完整細節")]
    assert order == sorted(order), "順序必須是：結論 → 價格 → 卡在哪 → 完整細節"
    # 細節一格都沒少：六個面板的 render 全都還在 details 裡
    for renderer in ("renderFundamental(view)", "renderWhy(view)", "renderResearch(view)",
                     "renderEntry(view)", "renderFreshness(payload)"):
        assert renderer in block, f"完整細節少了 {renderer}"


def test_price_series_is_context_not_a_signal(client) -> None:
    """單檔頁的走勢圖是脈絡：不得出現任何動能指標或買賣語言。"""
    from briefing.analyst_view.contracts import PRICE_SERIES_NOTE

    assert "脈絡不是訊號" in PRICE_SERIES_NOTE
    assert "不用它排序" in PRICE_SERIES_NOTE and "不用它決定買多少" in PRICE_SERIES_NOTE
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    block = source.split("function priceCard", 1)[1]
    block = re.split(r"\n(?:async )?function ", block, maxsplit=1)[0]
    for banned in ("sma", "SMA", "rsi", "RSI", "macd", "MACD", "均線", "突破"):
        assert banned not in block, f"走勢圖不得帶動能指標：{banned}"
