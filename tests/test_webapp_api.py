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
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：`future_target`／`implied_return` 兩個鍵退役（那把尺）。
    # 卡片現在要的是：現價、短評那一句、readiness。**不得有退役的鍵殘留。**
    for retired in ("future_target", "implied_return", "payoff", "sell_side_target", "target_reached"):
        assert retired not in row, retired
    assert "brief" in row and "our_bet" in row["brief"]
    assert row["readiness"]["state"] == "ready"
    assert row["generated_at"] and row["freshness"]["state"] in {"fresh", "stale"}


def test_list_never_flattens_the_four_absences_into_one_word(client) -> None:
    """四檔各自的缺席理由必須互相可分辨——這是整個 Step 5 語意債的驗收條件。"""
    body = client.get("/api/v1/stocks").json()
    # ⚠ 2026-09-23（Step 0b.1）：`future_target` 退役。四種缺席語意的載體改成 `primary_attention`
    # ——**同一個主張**（四種缺席不得被壓成一句 unavailable），只是換了它現在住的那一格。
    kinds = {r["ticker"]: (r["primary_attention"] or {}).get("absence_kind") for r in body["stocks"]}
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
        # ⚠ 2026-09-23（Step 0b.1）：三個退役的鍵不得以 0 復活，也不得以空 dict 殘留。
        for retired in ("future_target", "implied_return", "payoff", "target_reached"):
            assert retired not in row, retired
        # 缺席仍然要說得出是哪一種（Missing != Zero 的正面斷言）。
        assert (row["primary_attention"] or {}).get("absence_kind")


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
    # ⚠ 2026-10-08：`VOCAB.accounting_basis_display`（共識的口徑名）隨「完整細節」與「市場預測什麼」拿掉——個股頁不再印
    # 共識的原始數字（使用者：「給機器看的不用顯示出來」）；字彙留在 API 給 artifact 的消費者，前端不留第二份。
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


def test_single_stock_page_is_the_header_and_the_thirteen_blocks_only(client) -> None:
    """2026-10-08 使用者：「舊有的資訊非必要的就拿掉，除非是給我看的；給機器看的不用顯示出來」。單檔頁＝頁首（現價、
    哪天產生）＋十三塊；頁尾四張卡（基本數字／憑什麼這樣想／讀圖／錯了怎麼知道）與「稽核」「完整細節」兩個大展開拿掉——
    不是收起來，是拿掉；人讀的內容搬進對應的塊，給查核用的留在 artifact 與 API。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    block = source.split("async function renderDetail", 1)[1]
    block = re.split(r"\n(?:async )?function ", block, maxsplit=1)[0]
    assert "briefCard(payload, view)" in block and "headerLine(payload, view)" in block
    assert "drill(" not in block, "頁面層不再有大展開（稽核／完整細節）"
    for gone in ("numbersStrip", "argumentCard", "readingsCard", "downsideCard", "conclusionCard", "blockerCard",
                 "threeQuestionsCard", "versusMarketCard", "pageFillCard", "blockCells", "renderHeadline", "renderBet",
                 "renderFundamental", "renderResearch", "renderReadiness", "renderFreshness", "priceCard"):
        assert f"function {gone}(" not in source, f"{gone} 應已拿掉"
    # 人讀的內容搬進對應的塊（論證、坐的層、反證、時間表、三題的數字與出處）
    detail = source.split("function blockDetail", 1)[1].split("\nfunction ", 1)[0]
    for owner in ("chainDetail(view)", "seatsDetail(payload, view)", "'priced_in'", "'in_numbers'", "downsideDetail(view)",
                  "'will_it_die'", "timelineDetail(view)"):
        assert owner in detail, f"塊的展開少了 {owner}"
    # 走勢圖住在「怎麼被定價」那一塊（脈絡不是訊號）；首屏卡片不再自己掛走勢
    visuals = source.split("function blockVisuals", 1)[1].split("\nfunction ", 1)[0]
    assert "priceFigure(payload)" in visuals
    # 沒有短評的頁也照十三塊排（不再有第二套舊版面）
    brief_fn = source.split("function briefCard", 1)[1].split("\nfunction ", 1)[0]
    assert "schemaFirstScreen(payload, view, available ? panel : null)" in brief_fn


def test_price_series_is_context_not_a_signal(client) -> None:
    """單檔頁的走勢圖是脈絡：不得出現任何動能指標或買賣語言。"""
    from briefing.analyst_view.contracts import PRICE_SERIES_NOTE

    assert "脈絡不是訊號" in PRICE_SERIES_NOTE
    assert "不用它排序" in PRICE_SERIES_NOTE and "不用它決定買多少" in PRICE_SERIES_NOTE
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    block = source.split("function priceFigure", 1)[1]
    block = re.split(r"\n(?:async )?function ", block, maxsplit=1)[0]
    for banned in ("sma", "SMA", "rsi", "RSI", "macd", "MACD", "均線", "突破"):
        assert banned not in block, f"走勢圖不得帶動能指標：{banned}"


def test_no_row_ever_defers_to_an_expansion_that_does_not_exist() -> None:
    """「見下方展開」是這一輪回饋的正中紅心：那句話什麼都沒說，**而且假裝有下文**。

    2026-09-08 使用者原話：「感覺很多地方你就只是收乾淨而寫『見展開』」。事發位置是
    `renderRow`——值是結構化物件時它印「見下方展開」，而底下並沒有那個展開。

    ⚠ 2026-10-08：`renderRow`／`structuredText`（完整細節的逐格列）隨那個大展開拿掉；結構化的值現在只出現在三題的
    「數字與出處」——`tqNumbers` 用 `detailList` 印成人話：認得的鍵給中文名，**認不得的鍵照原名印**（不濾掉，INV-3），
    巢狀明細印筆數。所以仍然**沒有任何一條路徑會產生「請看別處」**。

    ⚠ 禁的是它**當成畫面文字**（單引號字串），不是提到這四個字——註解裡刻意留著
    這段歷史，那正是防止它被寫回來的剎車。
    """
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "'見下方展開'" not in source, "又出現「見下方展開」——那是把問題推給一個不存在的展開"
    tq = source.split("function tqNumbers(view, question)", 1)[1]
    tq = re.split(r"\n(?:async )?function ", tq, maxsplit=1)[0]
    assert "detailList(d.value)" in tq and "detailList(deps.detail)" in tq, "結構化的值必須被翻成人話"
    detail = source.split("function detailList(detail)", 1)[1]
    detail = re.split(r"\n(?:async )?function ", detail, maxsplit=1)[0]
    assert "TQ_DETAIL_LABELS[key] || key" in detail, "認不得的鍵要照原名印，不能留白或濾掉"


def test_market_numbers_on_the_page_are_only_what_the_market_says() -> None:
    """⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：「我們估／市場共識／我們比市場」四欄表——內部預測與相減隨 FY+1
    因果橋退役，表跟著退役。⚠ 2026-10-08：「市場預測什麼」卡（`versusMarketCard`）隨稽核區拿掉；人要看的兩個本益比住
    「怎麼被定價」的數字與出處（`marketMultiples`）——只印市場說了什麼、標明是別人的數字。**不得再長出「我們估」「我們比市場」。**
    """
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    block = source.split("function marketMultiples(view)", 1)[1]
    block = re.split(r"\n(?:async )?function ", block, maxsplit=1)[0]
    for token in ("trailing_pe", "forward_pe", "別人的"):
        assert token in block, f"市場的數字少了 {token}"
    for retired in ("COMPARE_ROWS", "'我們估'", "'我們比市場'", "reverseBridgeBlock", "opinion_stance"):
        assert retired not in block, f"退役的比較表不得復活：{retired}"
    assert "const COMPARE_ROWS" not in source and "function reverseBridgeBlock" not in source


def test_each_block_has_at_most_one_expansion_and_none_is_nested() -> None:
    """2026-09-08 使用者原話：「太多展開」——展開裡不得再套展開。2026-10-08 起頁面層沒有大展開（稽核、完整細節拿掉），
    展開只住在塊底下：每個塊的展開函式各一個 `drill()`，展開裡用的 helper 一個都不開展開（有標題就用 `group-title`）。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")

    def body(name: str) -> str:
        part = source.split(f"function {name}(", 1)[1]
        return re.split(r"\n(?:async )?function ", part, maxsplit=1)[0]

    for fn in ("chainDetail", "seatsDetail", "numbersDrill", "downsideDetail", "timelineDetail"):
        assert body(fn).count("drill(") == 1, f"{fn} 只准有一個展開"
    for helper in ("argumentSection", "tqNumbers", "detailList", "tqPoint", "layerNoteLinks", "marketMultiples"):
        assert "drill(" not in body(helper), f"{helper} 在展開裡，不得再開展開"
    assert "drill(" not in body("renderDetail")


# ---------------------------------------------------------------------------
# 分段與常駐計數器（2026-09-10）
# ---------------------------------------------------------------------------

def _with_candidate(view, derived=None, label=None, absence_kind=None):
    """在 fake view 上掛一個候選面板（形狀照 production：`candidate:state` 那一格的值是 `derive_row` 的列）。"""
    if derived is not None:
        datum = {"key": "candidate:state", "value": {"derived": derived, "derived_label": label}, "status": "available"}
        panel = {"key": "candidate", "status": "available", "absence_kind": None,
                 "lines": [{"key": "candidate:state", "datum": datum}]}
    else:
        datum = {"key": "candidate:state", "value": None, "status": "missing", "absence_kind": absence_kind,
                 "reason": "沒有敘事、也沒有持有"}
        panel = {"key": "candidate", "status": "missing", "absence_kind": absence_kind,
                 "lines": [{"key": "candidate:state", "datum": datum}]}
    return {**view, "candidate": panel}


@pytest.fixture()
def grouped(tmp_path):
    """五檔、五種候選狀態，ticker 刻意與組序反著取——組序若被字母序蓋掉就看得出來。"""
    store = ArtifactStore(tmp_path)
    for ticker, derived, label, kind in (("AAA", "pass", "不要", None), ("BBB", "not_multiple", "非倍率候選", None),
                                         ("CCC", None, None, "not_yet_recorded"), ("DDD", "missing", "缺 X", None),
                                         ("EEE", "missing", "缺 X", None), ("ZZZ", "held", "已持有", None),
                                         ("YYY", None, None, "upstream_unavailable")):
        store.write(materialize_view(_with_candidate(fake_view(ticker), derived, label, kind)))
    write_vocabularies(store)
    return TestClient(create_app(tmp_path)), tmp_path


def test_list_is_grouped_by_candidate_state_and_the_order_inside_a_group_is_alphabetical(grouped) -> None:
    """2026-10-07 使用者指示：首頁照候選狀態分組——研究花最多時間的在上、判斷「不要」的在最後。

    分組**不是排序**：`AGENTS.md` 不得輸出跨檔全序或首選，所以組內一律字母序；組序是閱讀順序，順序與中文
    只有 `alpha.candidates.LIST_GROUPS` 那一份（經 `.meta.json`），API 不另抄。"""
    from alpha.candidates import LIST_GROUPS

    client, _ = grouped
    body = client.get("/api/v1/stocks").json()
    assert [g["key"] for g in body["groups"]] == [*LIST_GROUPS, "stale_artifact"]
    assert [r["ticker"] for r in body["stocks"]] == ["ZZZ", "DDD", "EEE", "CCC", "BBB", "AAA", "YYY"]
    # 沒寫敘事與這次沒讀到是兩組（L12）
    assert {r["ticker"]: r["group"] for r in body["stocks"]}["CCC"] == "no_narrative"
    assert {r["ticker"]: r["group"] for r in body["stocks"]}["YYY"] == "unavailable"
    for group in body["groups"]:
        tickers = [r["ticker"] for r in body["stocks"] if r["group"] == group["key"]]
        assert tickers == sorted(tickers), f"{group['key']} 組內順序被動過了"
        assert group["count"] == len(tickers)
    assert "不是投資排序" in body["group_note"]


def test_group_is_copied_from_the_candidate_panel_not_re_derived_in_the_app(grouped) -> None:
    """分組照抄候選面板（與候選板同一個推導；materialize 端寫進 overview）——APP 自己判就是 L16 的重造品。
    研究完整度不再分組，但每張卡照樣帶著（資訊不丟）。"""
    client, _ = grouped
    body = client.get("/api/v1/stocks").json()
    for row in body["stocks"]:
        assert row["group"] == row["candidate"]["list_group"], row["ticker"]
        assert row["closure_label"], row["ticker"]


def test_old_artifacts_are_flagged_and_a_missing_vocabulary_means_no_grouping(grouped) -> None:
    """2026-10-07 之前 materialize 的頁沒有候選狀態——是 artifact 太舊，不得被歸進「沒寫敘事」；
    字彙表讀不到就不分組（整份字母序），不在 API 補一份字彙（L16）。"""
    client, directory = grouped
    path = directory / "AAA.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["overview"]["candidate"]
    from webapp.contracts import canonical_digest

    payload["content_digest"] = canonical_digest(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    body = client.get("/api/v1/stocks").json()
    assert {r["ticker"]: r["group"] for r in body["stocks"]}["AAA"] == "stale_artifact"
    assert body["stocks"][-1]["ticker"] == "AAA"
    (directory / ".meta.json").unlink()
    body = client.get("/api/v1/stocks").json()
    assert body["groups"] == [] and all(r["group"] is None for r in body["stocks"])
    assert [r["ticker"] for r in body["stocks"]] == sorted(r["ticker"] for r in body["stocks"])
    assert "字彙表讀不到" in body["group_note"]


def test_view_counter_is_always_on_the_first_screen(client) -> None:
    """常駐計數器必須自己出現（L14：真正的防呆是會自己出現的計數器，不是要人讀的段落）。

    ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：原名 `test_opinion_counter_is_always_on_the_first_screen`，
    印的是「有我們自己的看法 N 檔」（stance 分布）。stance 是 FY+1 模型對估值假設 derivation 的聚合，
    隨估值鏈退役；計數器本身不消失——剩「已有判讀／有賭注」兩個數，仍是純計數。
    """
    body = client.get("/api/v1/stocks").json()
    assert "opinion_counters" not in body, "退役的 stance 計數器不得復活"
    counters = body["view_counters"]
    assert "with_view" in counters and "with_bet" in counters
    assert counters["headline"] and "已有判讀" in counters["headline"]
    assert "by_stance" not in counters and "our_own_view" not in counters
    # 純計數：已有判讀＝研究完整度是 ready 的檔數，一檔都不能被吃掉或憑空多出（INV-3）。
    # （2026-10-07 起首頁改照候選狀態分組；研究完整度留在每張卡的 `closure_terminal`。）
    assert counters["with_view"] == sum(1 for r in body["stocks"] if r.get("closure_terminal") == "ready")


def test_counters_do_not_invent_a_bet_for_stocks_that_have_none(tmp_path) -> None:
    """沒寫 `our_bet` 的檔不算進 `with_bet`——「我沒讀到你的賭注」不等於「你有賭注」。"""
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("AAA")))
    store.write(materialize_view(fake_view("BBB")))
    write_vocabularies(store)
    body = TestClient(create_app(tmp_path)).get("/api/v1/stocks").json()
    counters = body["view_counters"]
    assert counters["with_bet"] == 0
    assert counters["with_view"] <= len(body["stocks"])



def test_layer_and_socket_are_explained_from_one_vocabulary(client) -> None:
    """2026-09-30 使用者回饋（「騎是什麼、插槽是什麼」）：白話說明只有一份（contracts → `.meta.json` → API），
    前端照抄；使用者看得到的字不再寫「騎」（較早的敘事原文照留——ledger 是 append-only）。"""
    vocab = client.get("/api/v1/meta").json()["vocabularies"]
    units = vocab["plain_bet_units"]
    assert set(units) == {"layer", "socket", "ride"}
    assert "量的賭注" in units["layer"] and "護城河賭注" in units["socket"] and "騎" in units["ride"]
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "VOCAB.plain_bet_units" in source and "騎" not in source


def test_priced_in_is_explained_from_one_string_in_one_place(client) -> None:
    """Phase 7 Step 7.0c（使用者 2026-10-04：「已定價」讀不懂）：白話只有一份（contracts → `.meta.json` → API），APP 不留
    第二份字串。2026-10-08（使用者：「非必要的就拿掉」）起首屏只留「已定價嗎 是」那個字，白話放進「怎麼被定價」那一塊的
    「數字與出處」——印一次，不在首屏每一頁重複一大段；字串裡也不帶內部編號。"""
    from briefing.analyst_view.contracts import PLAIN_PRICED_IN

    text = client.get("/api/v1/meta").json()["vocabularies"]["plain_priced_in"]
    assert text == PLAIN_PRICED_IN
    assert "不是「太貴」" in text and "目標價" in text and "自己過去三年" in text and "EV/S" in text and "P/S" in text
    assert "Phase" not in text and "R1" not in text and "稽核區" not in text, "給人看的白話不帶內部編號與已拿掉的區塊名"
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "VOCAB.plain_priced_in" in source and "太貴" not in source
    assert source.count("pricedInPlain()") == 2           # 函式定義一次、「怎麼被定價」的數字與出處一次
    detail = source.split("function blockDetail", 1)[1].split("\nfunction ", 1)[0]
    assert "numbersDrill(view, 'priced_in', () => [pricedInPlain()" in detail


def test_stock_page_three_words_jump_to_their_numbers_on_the_same_page() -> None:
    """2026-09-30 使用者回饋（「這三個字是要我去候選板看詳細嗎？」）：細節在同一頁——三個字可以點；
    2026-10-08 起每一題的數字住在那一題那一塊的「數字與出處」（錨點 `tq-<題>`），點了打開它。連到候選板的那一句不再暗示細節在那裡。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "jumpToNumbers(question)" in source and "node.id = 'tq-' + question" in source
    assert "audit-drill" not in source
    assert "看候選板 →" not in source and "和其他檔一起看（候選板）→" in source
    assert "candidateWatchLine(row.watch)" in source and "'理由：' + row.reason" in source
