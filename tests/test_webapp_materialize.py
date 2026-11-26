"""Materialization contract：artifact 的形狀、atomic write、fail closed、遮蔽、overview 投影。

刻意**不依賴 Neo4j／Engine C**：這一層的責任是「一份 AnalystView 字典 → 一份 artifact」，
把它綁在真實資料上只會讓測試在 DB 沒開時變成綠色的空跑（L13-2）。
真實四檔的端到端結果記在 `docs/reports/2026-09-07-webapp-mvp.md`。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from alpha.absence import SETTLED_ABSENCE_KINDS
from webapp.contracts import (
    ARTIFACT_SCHEMA_VERSION, ArtifactUnavailable, REQUIRED_FIELDS, canonical_digest,
    freshness_identity, freshness_of, validate_artifact,
)
from webapp.materialize import build_overview, materialize_view, redact_private_paths
from webapp.store import ArtifactStore


def _datum(key, label, value=None, status="available", basis="deterministic", **kw):
    return {"key": key, "label": label, "value": value, "status": status, "basis": basis,
            "authority": kw.get("authority"), "method": None, "unit": kw.get("unit"),
            "as_of": kw.get("as_of"), "reason": kw.get("reason"),
            "evidence_refs": [], "dependencies": kw.get("dependencies"),
            "absence_kind": kw.get("absence_kind")}


def _line(key, datum, role="headline_number"):
    return {"key": key, "display_label": datum["label"], "datum": datum, "role": role}


def fake_view(ticker="TEST", *, fair_value=100.0, absence_kind=None, reason=None,
              readiness_state="ready", blockers=(), price=50.0, quote_unit="USD",
              currency="USD", stance=None):
    """一份最小但形狀正確的 `AnalystView.to_dict()`。

    `stance` 給定時，fundamental panel 會帶一條 `opinion_stance` line——形狀與 production
    一致（值由模型層宣告，呈現層只讀）。不給就是「這份 view 沒有這一格」，也是合法狀態。
    """
    has_fv = fair_value is not None
    lines = [
        _line("current_price", _datum("current_price", "現價", price, unit="quote_unit（%s）" % quote_unit,
                                      basis="observation", as_of="2026-09-04",
                                      dependencies={"quote_unit": quote_unit})),
        _line("fair_value", _datum(
            "fair_value", "Fair value", fair_value if has_fv else None,
            status="available" if has_fv else "missing", basis="deterministic" if has_fv else "none",
            unit="currency_per_share" if has_fv else None, reason=reason,
            absence_kind=None if has_fv else (absence_kind or "not_yet_recorded"),
            dependencies={"currency": currency} if has_fv else None)),
        _line("value_date", _datum("value_date", "value date", "2027-06-30" if has_fv else None,
                                   status="available" if has_fv else "missing",
                                   basis="session_judgment" if has_fv else "none", unit="date",
                                   absence_kind=None if has_fv else "upstream_unavailable")),
        _line("price_return", _datum("price_return", "隱含報酬", -0.2 if has_fv else None,
                                     status="available" if has_fv else "missing",
                                     basis="deterministic" if has_fv else "none", unit="ratio",
                                     absence_kind=None if has_fv else (absence_kind or "not_yet_recorded"))),
        _line("annualized_price_return", _datum(
            "annualized_price_return", "年化", -0.25 if has_fv else None,
            status="available" if has_fv else "missing",
            basis="deterministic" if has_fv else "none", unit="ratio",
            absence_kind=None if has_fv else (absence_kind or "not_yet_recorded"))),
    ]
    panel = {"key": "headline", "title": "頭條", "questions": ["q4_implied_return"],
             "status": "available" if has_fv else "missing", "optional": False,
             "source_sections": ["implied_return"], "source_statuses": {"implied_return": "available"},
             "source_absence_kinds": {}, "lines": lines, "weak_inputs": [], "catalysts": [],
             "checkpoints": [], "disproofs": [], "evidence": [], "attention": [],
             "attention_scope": None, "attention_total": 0, "risks": [], "notes": [],
             "context": {"accounting_basis": "gaap", "period": "FY2027"}, "reason": reason,
             "absence_kind": None if has_fv else (absence_kind or "not_yet_recorded"),
             # 與 production 同一份判準（`AnalystPanel.absence_is_settled`），不在 fixture 裡
             # 自己寫死一組——那會讓測試守著一份與實作不同的規則。
             "absence_is_settled": absence_kind in SETTLED_ABSENCE_KINDS}
    empty = dict(panel, key="other", lines=[], status="available", absence_kind=None,
                 absence_is_settled=False)
    fundamental = dict(empty, key="fundamental")
    if stance is not None:
        fundamental = dict(fundamental, lines=[_line("opinion_stance", _datum(
            "opinion_stance", "我們有沒有形成自己的觀點", stance,
            status="available", basis="deterministic"))])
    return {
        "schema_version": "analyst-view/1", "source_schema_version": "alpha-investment-view/v1",
        "ticker": ticker, "company_id": "co:test", "company_label": "Test Corp.",
        "as_of": None, "point_in_time_mode": "current", "generated_on": "2026-09-07",
        "research_context_digest": "sha256:abc",
        "headline": panel, "fundamental": fundamental, "why": empty, "research": empty,
        "entry": empty,
        "readiness": {"state": readiness_state, "core_panels": ["headline"], "optional_panels": ["entry"],
                      "flags": [], "blockers": list(blockers), "optional_unavailable": ["entry：missing"],
                      "rule": "rule", "blocker_details": [
                          {"panel": "headline", "status": "missing", "absence_kind": absence_kind,
                           "settled": absence_kind in SETTLED_ABSENCE_KINDS, "reason": reason}
                      ] if blockers else [], "flag_details": []},
        "refresh": {"overall": "current", "counts": {}, "change_detection": "policy",
                    "judged_context_matches": True, "attention": [], "notes": []},
        "limits": [], "warnings": [], "questions": {}, "panel_order": ["headline"],
    }


# ---------------------------------------------------------------------------
# artifact 形狀
# ---------------------------------------------------------------------------

def test_artifact_carries_every_required_field() -> None:
    payload = materialize_view(fake_view())
    for field in REQUIRED_FIELDS:
        assert field in payload, field
    assert payload["schema_version"] == ARTIFACT_SCHEMA_VERSION


def test_content_digest_detects_any_post_write_mutation() -> None:
    payload = dict(materialize_view(fake_view()))
    validate_artifact("TEST", payload)
    payload["view"]["headline"]["lines"][1]["datum"]["value"] = 999.0
    with pytest.raises(ArtifactUnavailable, match="content_digest"):
        validate_artifact("TEST", payload)


def test_freshness_identity_ignores_price_but_tracks_cognition() -> None:
    """價格動了不算「認知變了」；context digest 或 readiness 動了才算（L12：兩種語意分開）。"""
    base = dict(ticker="T", as_of=None, point_in_time_mode="current",
                research_context_digest="sha256:a", source_schema_version="v1",
                readiness_state="ready", refresh_overall="current")
    assert freshness_identity(**base) == freshness_identity(**base)
    assert freshness_identity(**{**base, "research_context_digest": "sha256:b"}) != freshness_identity(**base)
    assert freshness_identity(**{**base, "readiness_state": "blocked"}) != freshness_identity(**base)


def test_missing_required_field_is_rejected_not_patched() -> None:
    payload = dict(materialize_view(fake_view()))
    del payload["overview"]
    with pytest.raises(ArtifactUnavailable, match="缺必要欄位"):
        validate_artifact("TEST", payload)


def test_schema_version_mismatch_fails_closed() -> None:
    payload = dict(materialize_view(fake_view()))
    payload["schema_version"] = "stockbot-app/analyst-view/999"
    payload["content_digest"] = canonical_digest(payload)
    with pytest.raises(ArtifactUnavailable, match="schema"):
        validate_artifact("TEST", payload)


def test_filename_and_content_ticker_must_agree() -> None:
    payload = materialize_view(fake_view("AAA"))
    with pytest.raises(ArtifactUnavailable, match="檔名與內容不一致"):
        validate_artifact("BBB", payload)


# ---------------------------------------------------------------------------
# overview 是選取不是計算
# ---------------------------------------------------------------------------

def test_overview_copies_values_verbatim_and_never_converts_units() -> None:
    view = fake_view(price=47.518, quote_unit="GBp", fair_value=0.05, currency="GBP")
    overview = build_overview(view)
    # GBp（便士）與 GBP（英鎊）差 100 倍。overview **原樣帶著兩個單位**，不換算、不合併。
    assert overview["price"]["value"] == 47.518
    assert overview["price"]["quote_unit"] == "GBp"
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：`future_target` 退役（那把尺）。**判準一字未改**
    # ——GBp 與 GBP 差 100 倍，overview 原樣帶單位不換算；現在唯一帶單位的那一格是現價。
    for retired in ("future_target", "implied_return", "payoff", "sell_side_target", "target_reached"):
        assert retired not in overview, retired


def test_overview_absence_keeps_none_not_zero() -> None:
    overview = build_overview(fake_view(fair_value=None, readiness_state="blocked"))
    # ⚠ 2026-09-23（Step 0b.1）：那三個鍵退役。**Missing != Zero 沒有放寬**——改問仍在的兩格：
    # 缺席要說得出是哪一種，且不得被補成 0。
    assert overview["readiness"]["state"] == "blocked"
    assert overview["gap_closure"]["value"] is None
    assert overview["price"]["value"] is not None, "現價是觀測，它不該跟著上游缺席消失"
    for retired in ("future_target", "implied_return", "payoff", "target_reached"):
        assert retired not in overview, retired


def test_overview_carries_the_absence_kind_so_the_ui_never_parses_prose() -> None:
    overview = build_overview(fake_view(
        fair_value=None, absence_kind="deliberate_abstention", readiness_state="blocked",
        blockers=["headline：missing"], reason="刻意不主張目標倍數：無法錨定"))
    # ⚠ 2026-09-23（Step 0b.1）：`future_target` 退役；`primary_attention` 是缺席語意的載體。
    assert overview["primary_attention"]["absence_kind"] == "deliberate_abstention"
    assert overview["primary_attention"]["settled"] is True


def test_overview_contains_no_arithmetic_on_the_numbers() -> None:
    """空跑檢查：overview 若自己算 gap／百分比，這裡的值就不會與來源逐格相等。"""
    view = fake_view(price=50.0, fair_value=100.0)
    overview = build_overview(view)
    lines = {line["key"]: line["datum"] for line in view["headline"]["lines"]}
    # ⚠ 2026-09-23（Step 0b.1）：兩個鍵退役。**「overview 不自己算」沒有放寬**——
    # 現價這一格仍必須是 headline line 的**同一個物件**（`is` 相等，不是數值相等）。
    assert overview["price"]["value"] is lines["current_price"]["value"]


# ---------------------------------------------------------------------------
# 遮蔽
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "找不到 session 判斷檔（library/private/alpha/judgments/IQE.L.json）",
    r"寫入 C:\Users\someone\code\StockBotv2\library\private\alpha\valuation\COHR.jsonl",
    "library/private/engine_c/engine_c.db 讀取失敗",
])
def test_private_paths_never_survive_materialization(text: str) -> None:
    redacted = redact_private_paths({"reason": text})["reason"]
    assert "library/private" not in redacted
    assert "library\\private" not in redacted
    assert "C:\\" not in redacted
    assert "«private-authority»" in redacted


def test_redaction_keeps_the_rest_of_the_sentence() -> None:
    out = redact_private_paths("找不到 session 判斷檔（library/private/alpha/judgments/X.json）——請先寫判斷")
    assert out.startswith("找不到 session 判斷檔")
    assert out.endswith("請先寫判斷")


def test_redaction_walks_nested_structures() -> None:
    payload = redact_private_paths({"a": [{"b": "see library/private/x.json"}]})
    assert "library/private" not in json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# atomic write ／ fail closed read
# ---------------------------------------------------------------------------

def test_write_is_atomic_and_leaves_no_temp_files(tmp_path) -> None:
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("AAA")))
    assert [p.name for p in tmp_path.iterdir()] == ["AAA.json"]


def test_half_written_json_is_rejected_not_partially_served(tmp_path) -> None:
    store = ArtifactStore(tmp_path)
    path = store.write(materialize_view(fake_view("AAA")))
    text = path.read_text(encoding="utf-8")
    path.write_text(text[: len(text) // 2], encoding="utf-8")   # 模擬非 atomic 的半份寫入
    with pytest.raises(ArtifactUnavailable, match="JSON 解析失敗"):
        store.read("AAA")


def test_broken_artifact_surfaces_in_read_all_instead_of_vanishing(tmp_path) -> None:
    """INV-3：查不到了不是合法 lifecycle——壞掉的 artifact 必須帶著理由現形。"""
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("GOOD")))
    (tmp_path / "BAD.json").write_text("{", encoding="utf-8")
    rows = {t: (payload, reason) for t, payload, _f, reason in store.read_all()}
    assert set(rows) == {"GOOD", "BAD"}
    assert rows["GOOD"][0] is not None
    assert rows["BAD"][0] is None and rows["BAD"][1]


def test_meta_file_is_not_mistaken_for_a_stock(tmp_path) -> None:
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("AAA")))
    (tmp_path / ".meta.json").write_text("{}", encoding="utf-8")
    assert store.tickers() == ["AAA"]


@pytest.mark.parametrize("bad", ["../secrets", "..", "a/b", "C:/x", "AA*", ""])
def test_ticker_slug_is_an_allowlist_not_a_filter(tmp_path, bad: str) -> None:
    store = ArtifactStore(tmp_path)
    with pytest.raises(ArtifactUnavailable):
        store.path_for(bad)


def test_stale_is_a_state_not_an_error() -> None:
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    fresh = freshness_of(datetime.now(timezone.utc))
    stale = freshness_of(old)
    assert fresh.state == "fresh" and stale.state == "stale"
    assert stale.age_seconds > 0
    assert "不會觸發重建" in stale.to_dict()["rule"]

# ---------------------------------------------------------------- 故事頁（Phase 8 Step 8.2）
# 全部用合成的範例頁（tests/fixtures/story_page/ZZZZ）與 tmp 目錄；不讀真的故事頁帳、敘事帳、等待 registry。

_STORY_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "story_page" / "ZZZZ"


def _story_brief(created: datetime):
    from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record

    ev = ["graph://x"]
    slots = {"demand": {"text": "買方擴產。", "evidence_refs": ev},
             "position": {"text": "坐在檢測層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
             "bottleneck": {"text": "卡的是高階機台的量。", "evidence_refs": ev},
             "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
             "our_bet": {"text": "賭高階機台。", "evidence_refs": ev},
             "what_must_be_true": {"text": "買方照計畫擴產。", "evidence_refs": ev},
             "when": {"text": "{next_checkpoint_date} 檢核點。", "evidence_refs": ev}}
    return parse_brief_record(brief_record(
        company_id="co:zzzz_example", ticker="ZZZZ", slots=slots, record_version=RECORD_VERSION_V2,
        rides=[{"node": "tech:zzzz_inspection", "unit": "layer", "reading_id": "sr_" + "a" * 16}],
        answers={"priced_in": "yes", "in_numbers": "yes"},
        candidate_state={"state": "pass", "watch_id": None, "reason": "理由的依據"}, created_at=created))


_BRIEF = _story_brief(datetime(2026, 11, 25, tzinfo=timezone.utc))
_NEWER = _story_brief(datetime(2026, 11, 26, 1, 0, tzinfo=timezone.utc))
_WATCHES = {"watches": [{"watch_id": "ew_9001_2026-11-26", "status": "active", "until": "2027-02-01",
                         "expires": "2027-03-01"}]}


def _story_record(tmp_path, html: bytes | None = None, *, brief_id: str | None = None) -> dict:
    """帳上一列（與 `story_pages.add_page` 寫的同形）＋片段檔，放在 tmp 根目錄下。"""
    import hashlib

    data = (_STORY_FIXTURE / "page.html").read_bytes() if html is None else html
    decl = json.loads((_STORY_FIXTURE / "page.json").read_text(encoding="utf-8"))
    decl["brief_id"] = brief_id or _BRIEF.brief_id
    target = tmp_path / "library" / "private" / "story_pages" / "ZZZZ" / "sp_0123456789abcdef.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"page_id": "sp_0123456789abcdef", "company_id": "co:zzzz_example", "ticker": "ZZZZ",
            "brief_id": decl["brief_id"], "created_at": "2026-11-26T14:00:00+00:00", "author": "session", "kind": "page",
            "html_sha256": hashlib.sha256(data).hexdigest(),
            "html_path": "library/private/story_pages/ZZZZ/sp_0123456789abcdef.html", "visible_chars": 1259,
            "warnings": [], "declaration": decl, "rebind_note": None, "supersedes_id": None}


def _story(tmp_path, record, *, briefs=(_BRIEF,), event_ctx=_WATCHES, as_of=None, loaded=None):
    from webapp.materialize import _page_story

    return _page_story("ZZZZ", "co:zzzz_example", loaded or {"pages": {"co:zzzz_example": record}}, event_ctx,
                       as_of, root=tmp_path, brief_loader=lambda t: (list(briefs), []))


def test_story_page_carries_the_fragment_and_the_registry_state(tmp_path) -> None:
    record = _story_record(tmp_path)
    story = _story(tmp_path, record)
    assert story["html"].encode("utf-8") == (_STORY_FIXTURE / "page.html").read_bytes()
    assert story["stale"] is False and story["current_brief_id"] == _BRIEF.brief_id
    waits = {w["key"]: w for w in story["waits"]}
    assert waits["w1"]["status"] == "active" and waits["w1"]["wake_on"] == "2027-02-01"
    assert waits["w1"]["expires"] == "2027-03-01"
    assert waits["w2"]["status"] == "unregistered" and waits["w2"]["watch_id"] is None
    # 範例頁：w2 還沒登記、圖上缺的那一層沒有線索——對不上的兩種；押的節點和敘事一樣，不算
    assert [g["kind"] for g in story["gaps"]] == ["unregistered_wait", "ride_mismatch"]
    assert story["written_on"] == "2026-11-26" and story["checklist_version"] == "v3"
    artifact = materialize_view(fake_view(), story_page=story)
    validate_artifact("TEST", artifact)
    assert artifact["story_page"]["html"] == story["html"]


def test_story_page_is_stale_when_the_brief_moved_on(tmp_path) -> None:
    story = _story(tmp_path, _story_record(tmp_path), briefs=(_BRIEF, _NEWER))
    assert story["stale"] is True and story["current_brief_on"] == "2026-11-26"
    assert story["gaps"][0]["kind"] == "stale" and "2026-11-26 換版" in story["gaps"][0]["text"]


def test_watch_missing_from_the_registry_is_a_reading_problem_not_a_pass(tmp_path) -> None:
    story = _story(tmp_path, _story_record(tmp_path), event_ctx={"watches": []})
    assert {w["key"]: w["status"] for w in story["waits"]} == {"w1": "missing", "w2": "unregistered"}
    unread = _story(tmp_path, _story_record(tmp_path), event_ctx=None)
    assert {w["key"]: w["status"] for w in unread["waits"]} == {"w1": "unread", "w2": "unregistered"}


def test_no_story_page_is_null(tmp_path) -> None:
    from webapp.materialize import _page_story

    assert _page_story("ZZZZ", "co:zzzz_example", {"pages": {}}, _WATCHES, None, root=tmp_path) is None
    assert materialize_view(fake_view())["story_page"] is None


@pytest.mark.parametrize("snippet, needle", [
    ("<script>alert(1)</script>", "E1"),
    ("<p onclick=\"alert(1)\">字</p>", "E1"),
    ("<p style=\"color:red\">字</p>", "E1"),
    ("<p><a href=\"javascript:alert(1)\">連結</a></p>", "E1"),
    ("<p>https://claude.ai/artifact/abc</p>", "E4"),
])
def test_a_broken_fragment_is_an_absence_and_the_artifact_is_still_written(tmp_path, snippet, needle) -> None:
    html = (_STORY_FIXTURE / "page.html").read_text(encoding="utf-8").replace("</header>", snippet + "\n</header>", 1)
    story = _story(tmp_path, _story_record(tmp_path, html.encode("utf-8")))
    assert story["absence"]["kind"] == "invalidated" and needle in story["absence"]["reason"]
    assert "html" not in story
    store = ArtifactStore(tmp_path / "views")
    store.write(materialize_view(fake_view(), story_page=story))        # 整份物化檔照寫
    payload, _fresh = store.read("TEST")
    assert payload["story_page"]["absence"]["kind"] == "invalidated"


def test_a_tampered_fragment_file_is_an_absence(tmp_path) -> None:
    record = _story_record(tmp_path)
    (tmp_path / record["html_path"]).write_bytes(b"<article class=\"story-page\"></article>")
    story = _story(tmp_path, record)
    assert story["absence"]["kind"] == "invalidated" and "被改過" in story["absence"]["reason"]


def test_story_page_refuses_as_of_and_passes_ledger_absence_through(tmp_path) -> None:
    from datetime import date

    record = _story_record(tmp_path)
    assert _story(tmp_path, record, as_of=date(2026, 11, 1))["absence"]["kind"] == "point_in_time_unavailable"
    down = {"absence": {"kind": "upstream_unavailable", "reason": "故事頁的帳沒讀到"}}
    assert _story(tmp_path, record, loaded=down)["absence"] == down["absence"]


def test_vocabularies_carry_the_one_story_page_whitelist(tmp_path) -> None:
    """前端重建片段用的白名單、網址規則、對不上的三種與等待徽章的字只有一份（`.meta.json`；app.js 不另抄）。"""
    import re

    from alpha.narrative import story_page as rules
    from alpha.providers.story_pages import STORY_PAGE_GAP_KINDS, WAIT_STATUS_LABELS
    from engine_b.event_watch import WATCH_STATUSES
    from webapp.materialize import write_vocabularies

    meta = json.loads(write_vocabularies(ArtifactStore(tmp_path)).read_text(encoding="utf-8"))["story_page"]
    assert meta["html_tags"] == sorted(rules.HTML_TAGS) and "viewbox" in meta["svg_attrs"]
    assert meta["svg_text_only"] == ["desc", "title"]           # 前端缺這一條就不印片段（storyRules）
    assert meta["gap_kinds"] == list(STORY_PAGE_GAP_KINDS)
    assert set(WATCH_STATUSES) <= set(meta["wait_status_labels"]) == set(WAIT_STATUS_LABELS)
    for name, pattern in meta["patterns"].items():
        assert pattern and "\\w" not in pattern, name          # Python 與 JavaScript 對 \w 的意思不一樣
        re.compile(pattern)
    assert re.fullmatch(meta["patterns"]["href"], "https://example.com/a")
    assert not re.fullmatch(meta["patterns"]["href"], "javascript:alert(1)")
