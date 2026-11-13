"""敘事事實句綁逐字錨點（2026-11-13 使用者「照你推薦做吧」；plan 2026-11-13-001 Step A；failure log #163）。

逐句核對猜行、命中率約 13%；寫的人綁一段逐字原文，句子就只比它自己那一段。這裡驗：#163 點名的五種錯法（3110.T 主詞收窄、
LPK.DE「主要」、ATS「NVIDIA 專用」、AXTI「三分之二」與「committed to pay」寫成「付了」）各被它那一種旗標標到、改對的那一句不標；
寫入前驗證整批拒收；⑤ 那一格只數已持有與宣告可開、讀不到持股不是 0。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.narrative import anchors as anc
from alpha.narrative import fact_check as fcm
from alpha.providers import fact_anchors as fa
from alpha.providers import fact_checks as fc


def _sentence(text: str, *, where: str = "position", refs: tuple[str, ...] = ("library/raw/a.txt",)) -> fcm.Sentence:
    return fcm.Sentence(n=1, where=where, text=text, refs=refs)


def _kinds(flags) -> dict[str, str]:
    return {f.kind: f.detail for f in flags}


def _compare(text: str, anchor: anc.Anchor, **kw) -> dict[str, str]:
    return _kinds(anc.compare(_sentence(text), [anchor], self_company="co:self", self_names=kw.pop("self_names", ()), **kw))


def _resolver(files: dict[str, str], tmp_path: Path) -> fc.RefResolver:
    for rel, body in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return fc.RefResolver(root=tmp_path, readings={})


# ---------------------------------------------------------------------------
# 指紋
# ---------------------------------------------------------------------------

def test_the_fingerprint_ignores_refs_and_spacing_but_not_the_company_or_the_words() -> None:
    fp = anc.fingerprint("co:a", "營收 年增 30%。")
    assert fp == anc.fingerprint("co:a", "营收年增３０%。")          # 全半形、繁簡、空白
    assert fp != anc.fingerprint("co:b", "營收 年增 30%。")
    assert fp != anc.fingerprint("co:a", "營收年增 31%。")
    # 引用不進指紋：同一句換了引用，錨點照樣對得到（現行核對的 digest 會變）
    a, b = _sentence("營收年增 30%。", refs=("library/raw/a.txt",)), _sentence("營收年增 30%。", refs=("library/raw/b.txt",))
    assert a.digest != b.digest and anc.fingerprint("co:a", a.text) == anc.fingerprint("co:a", b.text)


# ---------------------------------------------------------------------------
# #163 點名的五種錯法
# ---------------------------------------------------------------------------

FIVE = [
    pytest.param("term_missing", "library/raw/hh.txt", "公司2025年开始批量供应特种电子布给下游CCL客户",
                 "宏和半年報說它 2025 年開始批量供應低熱膨脹布給下游 CCL 客戶。",
                 "宏和半年報說它 2025 年開始批量供應特種電子布給下游 CCL 客戶。", id="3110.T 主詞收窄"),
    pytest.param("qualifier_missing", "library/raw/lpkf.txt",
                 "The majority of the relevant players in the semiconductor market are already using this technology in "
                 "development and qualification.",
                 "年報說主要半導體廠多數已在開發與認證階段使用這項技術。",
                 "年報說半導體市場多數相關業者已在開發與認證階段使用這項技術。", id="LPK.DE 主要"),
    pytest.param("name_missing", "library/raw/ats.txt", "The new substrate line is dedicated to AI accelerator customers.",
                 "這條新的載板產線是 NVIDIA 專用。", "這條新的載板產線專供 AI 加速器客戶。", id="ATS NVIDIA 專用"),
    pytest.param("number_missing", "library/raw/axti.txt",
                 "Indium phosphide accounted for approximately 79% of revenue in the second quarter and approximately 87% "
                 "in the third quarter.",
                 "磷化銦約占營收三分之二。", "磷化銦第二季約占營收 79%、第三季約 87%。", id="AXTI 三分之二"),
    pytest.param("hedge_dropped", "library/raw/axti8k.txt", "The customer has committed to pay a $10.0 million prepayment.",
                 "客戶付了 1,000 萬美元預付款。", "客戶承諾付 1,000 萬美元預付款。", id="AXTI committed to pay"),
]


@pytest.mark.parametrize("kind, ref, quote, wrong, fixed", FIVE)
def test_each_named_shape_is_flagged_by_its_own_kind_and_the_fixed_sentence_is_not(kind, ref, quote, wrong, fixed) -> None:
    anchor = anc.Anchor("fa_x", ref, quote)
    assert kind in _compare(wrong, anchor, self_names=("宏和",))
    assert _compare(fixed, anchor, self_names=("宏和",)) == {}


def test_no_anchor_means_no_anchor_flags_and_conditions_only_check_quotes() -> None:
    assert anc.compare(_sentence("營收年增 30%。"), [], self_company="co:self") == ()
    anchor = anc.Anchor("fa_x", "library/raw/a.txt", "We expect revenue to grow.")
    # 何時格與條件句：只核引號（同逐句核對）——不比數字、名稱、語氣、詞
    cond = anc.compare(_sentence("錯的訊號：Q3 營收沒有年增 30%。", where="what_must_be_true"), [anchor], self_company="co:self")
    assert not {f.kind for f in cond} & {"number_missing", "hedge_dropped", "name_missing"}


# ---------------------------------------------------------------------------
# 保留語氣、分數、衍生數字、同語言的詞
# ---------------------------------------------------------------------------

def test_hedges_are_not_triggered_by_nouns_months_or_object_markers() -> None:
    assert anc.source_hedges("The 2026 business plan was approved on May 5.") == []
    assert anc.source_hedges("公司将其产能提高到每月 3 万片，将近翻倍。") == []
    assert "may" in anc.source_hedges("Shipments may slip.") and "预计" in anc.source_hedges("公司預計明年量產")
    assert anc.sentence_hedged("公司預計明年量產") and anc.sentence_hedged("要等下一季財報")
    assert not anc.sentence_hedged("董事會通過主要客戶的訂單")      # 「會」「要」單字不算


def test_one_against_an_english_singular_is_found_but_a_different_count_is_still_flagged() -> None:
    # 2026-11-13 COHR 第一個真錨點：「另有一家…客戶」綁 "a market-leading … customer"——英文單數不寫 one
    sentence = "另有一家領先的 AI 資料中心客戶下了一張特大的 CPO 訂單，裡面包含它的高功率 CW 雷射。"
    real = anc.Anchor("fa_x", "graph://source/coherent_q2fy26_cpo",
                      "we recently secured an exceptionally large purchase order from a market-leading AI data center "
                      "customer for a CPO solution that includes our new high-power CW laser")
    assert "number_missing" not in _compare(sentence, real)
    two = anc.Anchor("fa_x", "graph://source/x", "we secured large purchase orders from two AI data center customers "
                                                "for a CPO solution")
    assert _compare(sentence, two).get("number_missing") == "一家"
    # 中文原文照舊要寫出「一家」
    cn = anc.Anchor("fa_x", "library/raw/a.txt", "公司与多家数据中心客户签订了订单")
    assert "number_missing" in _compare("另有一家客戶下了訂單。", cn)


def test_fractions_are_checked_against_the_anchor_percentages_and_words() -> None:
    assert fcm.fraction_claims("約占三分之二") == [("三分之二", pytest.approx(200 / 3))]
    # 只寫分數的句子也是事實句（要綁錨點）；逐句核對照舊不核它
    assert fcm.sentence_claims(_sentence("磷化銦約占營收三分之二。"), self_names=()).is_fact
    two_thirds = anc.Anchor("fa_x", "library/raw/a.txt", "Two-thirds of revenue came from data centers.")
    assert "number_missing" not in _compare("資料中心占營收三分之二。", two_thirds)
    cn = anc.Anchor("fa_x", "library/raw/a.txt", "数据中心约占三分之二")
    assert "number_missing" not in _compare("資料中心約占三分之二。", cn)


def test_a_derived_number_is_computed_from_the_anchor_and_not_flagged_as_missing() -> None:
    quote = "Revenue was $120 million, of which $90 million came from data centers."
    good = anc.Anchor("fa_x", "library/raw/a.txt", quote, {"op": "share", "of": ["$90 million", "$120 million"], "shown": "75%"})
    assert _compare("資料中心占營收 75%。", good) == {}
    wrong = anc.Anchor("fa_x", "library/raw/a.txt", quote,
                       {"op": "share", "of": ["$90 million", "$120 million"], "shown": "三分之二"})
    assert "75" in _compare("資料中心占營收三分之二。", wrong)["derived_mismatch"]
    # 沒宣告 derive 的 75%：原文沒有這個數＝數字旗標
    assert "number_missing" in _compare("資料中心占營收 75%。", anc.Anchor("fa_x", "library/raw/a.txt", quote))
    assert anc.derive_value("growth", [120, 100]) == pytest.approx(20.0) and anc.derive_value("ratio", [1, 0]) is None


def test_derive_is_validated_at_write_time() -> None:
    quote = "Revenue was $120 million, of which $90 million came from data centers."
    ok = {"op": "share", "of": ["$90 million", "$120 million"], "shown": "75%"}
    assert anc.derive_problems(ok, quote=quote, sentences=["資料中心占營收 75%。"]) == []
    problems = anc.derive_problems({"op": "avg", "of": ["$95 million"], "shown": "80%"}, quote=quote,
                                   sentences=["資料中心占營收 75%。"])
    joined = "；".join(problems)
    assert "derive.op" in joined and "不在 quote 裡" in joined and "不在句子裡" in joined


def test_the_term_check_only_compares_chinese_sources_and_skips_our_framing_words() -> None:
    english = anc.Anchor("fa_x", "library/raw/a.txt", "We started volume shipments of special glass fabric in 2025.")
    assert "term_missing" not in _compare("它 2025 年開始量產出貨低熱膨脹布。", english)
    japanese = anc.Anchor("fa_x", "library/raw/a.txt", "2025年から特殊ガラスクロスの量産出荷を開始した")
    assert "term_missing" not in _compare("它 2025 年開始量產出貨低熱膨脹布。", japanese)
    chinese = anc.Anchor("fa_x", "library/raw/a.txt", "公司2025年开始批量供应特种电子布给下游CCL客户")
    assert _compare("這代表公司 2025 年開始批量供應特種電子布給下游 CCL 客戶。", chinese) == {}
    # 印回句子原本的字（繁體），不是折疊後的簡體
    assert _compare("2025 年開始批量供應低熱膨脹布給下游 CCL 客戶。", chinese)["term_missing"] == "「低熱膨脹」"
    # 中英混合的錨點不比（2026-11-13 COHR：「連續波雷射」對的是英文那一段 "CW laser"，中文那一段只講基板）
    laser = anc.Anchor("fa_y", "library/raw/b.txt", "a CPO solution that includes our new high-power CW laser")
    substrate = anc.Anchor("fa_z", "library/raw/c.txt", "先锐科技在 2027–2029 年期间提供 6 英寸磷化铟衬底")
    mixed = anc.compare(_sentence("它做 CPO 用的連續波雷射，基板向先锐買 2027–2029 的六吋磷化銦。"), [laser, substrate],
                        self_company="co:self")
    assert "term_missing" not in _kinds(mixed)


# ---------------------------------------------------------------------------
# 寫入前驗證
# ---------------------------------------------------------------------------

RAW = ("RETRIEVED: 2026-11-13\n"
       "Indium phosphide accounted for approximately 79% of revenue in the second\n"
       "quarter and approximately 87% in the third quarter.\n"
       "\n"
       "NOTE: our reading — InP is about two-thirds of revenue.\n"
       "this line is still our note\n")


def test_a_quote_must_be_verbatim_first_hand_text_not_our_own_note(tmp_path: Path) -> None:
    resolve = _resolver({"library/raw/axti.txt": RAW}, tmp_path)
    resolved = resolve("library/raw/axti.txt")
    # 跨行（PDF 斷行）照收：同一檔相鄰的行接起來比
    assert fa.quote_problem("approximately 79% of revenue in the second quarter", resolved) is None
    assert "自己寫的段落" in fa.quote_problem("InP is about two-thirds of revenue", resolved)
    assert "找不到" in fa.quote_problem("approximately 80% of revenue", resolved)
    assert "太短" in fa.quote_problem("79%", resolved)


def test_validate_rejects_the_whole_batch_and_needs_the_current_sentences(tmp_path: Path) -> None:
    resolve = _resolver({"library/raw/axti.txt": RAW, "library/private/notes.md": "79% of revenue\n"}, tmp_path)
    sentences = [_sentence("磷化銦第二季約占營收 79%。")]
    good = {"sentences": ["磷化銦第二季約占營收 79%。"], "ref": "library/raw/axti.txt",
            "quote": "approximately 79% of revenue in the second quarter"}
    cleaned, errors = fa.validate_items([good], company_id="co:axt", sentences=sentences, resolve=resolve)
    assert errors == [] and cleaned[0]["fingerprints"] == [anc.fingerprint("co:axt", "磷化銦第二季約占營收 79%。")]
    stale = dict(good, sentences=["磷化銦約占營收三分之二。"])
    note = dict(good, ref="library/private/notes.md", quote="79% of revenue")
    cleaned, errors = fa.validate_items([good, stale, note], company_id="co:axt", sentences=sentences, resolve=resolve)
    assert cleaned == [] and len(errors) == 2
    assert "不在現行那一版" in errors[0] and "一手原文" in errors[1]
    assert fa.validate_items([], company_id="co:axt", sentences=sentences, resolve=resolve)[1]
    unknown = dict(good, supersedes=["fa_nope"])
    assert "supersedes" in fa.validate_items([unknown], company_id="co:axt", sentences=sentences, resolve=resolve)[1][0]


def test_records_round_trip_and_a_superseded_anchor_stops_counting(tmp_path: Path) -> None:
    path = tmp_path / "fact_anchors.jsonl"
    item = {"fingerprints": [anc.fingerprint("co:axt", "句子一。")], "sentences": ["句子一。"], "ref": "library/raw/a.txt",
            "quote": "the original words"}
    first = fa.build_record(item, company_id="co:axt", ticker="AXTI", now=datetime(2026, 11, 13, tzinfo=timezone.utc))
    fa.append_records([first], path=path)
    second = fa.build_record(dict(item, quote="the better words", supersedes=[first["anchor_id"]]), company_id="co:axt",
                             ticker="AXTI", now=datetime(2026, 11, 14, tzinfo=timezone.utc))
    fa.append_records([second], path=path)
    records, errors = fa.read_records(path=path)
    assert errors == [] and [r["anchor_id"] for r in records] == [first["anchor_id"], second["anchor_id"]]
    index = fa.anchor_index("co:axt", records)
    assert [a.quote for a in index[item["fingerprints"][0]]] == ["the better words"]
    assert fa.anchor_index("co:other", records) == {}
    path.write_text(path.read_text(encoding="utf-8") + '{"anchor_id": "fa_bad"}\n[]\n', encoding="utf-8")
    assert len(fa.read_records(path=path)[1]) == 2                        # 壞行報出來，不靜默丟（INV-3）


# ---------------------------------------------------------------------------
# 整版比對、呈現、核對紀錄
# ---------------------------------------------------------------------------

def test_a_brief_check_prints_the_anchor_section_apart_from_the_guessed_lines(tmp_path: Path) -> None:
    resolve = _resolver({"library/raw/axti.txt": RAW}, tmp_path)
    brief = fcm.BriefText(ticker="AXTI", company_id="co:axt", brief_id="ib_x", as_of=date(2026, 11, 13), slots=(
        ("revenue", "磷化銦約占營收三分之二。營收在第三季成長。還不賭，缺一件事。", ("library/raw/axti.txt",)),))
    ctx = fcm.CheckContext(resolve=resolve)
    result = fcm.check_brief(brief, ctx)
    index = {anc.fingerprint("co:axt", "磷化銦約占營收三分之二。"): [anc.Anchor(
        "fa_1", "library/raw/axti.txt", "approximately 79% of revenue in the second quarter and approximately 87%")]}
    checks = anc.check_anchors(result, index, ctx=ctx)
    assert [c.fact for c in checks] == [True, True, False]              # 判斷句不是事實句
    assert anc.anchor_summary(checks) == "錨點：事實句 2｜有錨點 1｜還沒錨點 1｜錨點旗標 1"
    text = "\n".join(anc.render_markdown(checks, ticker="AXTI"))
    assert "## 錨點比對" in text and "⚑數字對不回錨點原文：三分之二" in text and "還沒錨點的事實句：2" in text
    payload = anc.as_dict(checks)
    assert (payload["fact_sentences"], payload["anchored"]) == (2, 1)
    record = fc.build_record(result, company_id="co:axt", changed=0, note="逐句對過", anchor_counts=(2, 1))
    assert (record["fact_sentences"], record["anchored"]) == (2, 1)
    assert "anchored" not in fc.build_record(result, company_id="co:axt", changed=0, note="逐句對過")


# ---------------------------------------------------------------------------
# ⑤「事實句還沒錨點」
# ---------------------------------------------------------------------------

def _brief(ticker: str, state: str, text: str, *, created=datetime(2026, 11, 1, tzinfo=timezone.utc)):
    return SimpleNamespace(ticker=ticker, company_id=f"co:{ticker.lower()}", brief_id=f"ib_{ticker.lower()}",
                           candidate_state=SimpleNamespace(state=state, reason=""), depth_check=(), created_at=created,
                           slots=(SimpleNamespace(key="revenue", text=text, evidence_refs=("library/raw/a.txt",)),))


def test_gaps_count_only_held_and_declared_open_and_only_fact_sentences() -> None:
    briefs = [_brief("OPEN", "open", "營收年增 30%。還不賭。"), _brief("HELD", "pass", "年報說它是主要客戶。"),
              _brief("MISS", "missing", "營收年增 30%。"), _brief("DONE", "open", "營收年增 30%。"),
              _brief("JUDGE", "open", "還不賭，缺一件事。")]
    done = {"anchor_id": "fa_1", "company_id": "co:done", "ticker": "DONE", "created_at": "2026-11-13T00:00:00+00:00",
            "ref": "library/raw/a.txt", "quote": "revenue grew 30%", "fingerprints": [anc.fingerprint("co:done", "營收年增 30%。")]}
    gaps = fa.anchor_gaps(briefs, stories={}, records=[done], held=["held"], names={})
    assert [(g["ticker"], g["scope"], g["facts"], g["missing"]) for g in gaps] == [("HELD", "held", 1, 1), ("OPEN", "open", 1, 1)]
    assert gaps[0]["since"].startswith("2026-11-13")                    # 規則起算日之前寫的從起算日算
    assert fa.held_from_board(None) is None
    assert fa.held_from_board({"holdings": {"status": "error"}, "groups": {"held": [{"ticker": "X"}]}}) is None
    assert fa.held_from_board({"holdings": {"status": "ok"}, "groups": {"held": [{"ticker": "X"}]}}) == ["X"]


def test_the_cli_has_the_command_and_the_gaps_listing_uses_the_same_function(monkeypatch, capsys) -> None:
    from alpha import cli

    args = cli.build_parser().parse_args(["brief-anchor", "AXTI", "--draft"])
    assert args.func is cli.cmd_brief_anchor
    monkeypatch.setattr(fa, "held_now", lambda: ["HELD"])
    monkeypatch.setattr(fa, "gaps_now", lambda *, held: [
        {"ticker": "HELD", "scope": "held", "facts": 3, "missing": 2}, {"ticker": "OPEN", "scope": "open", "facts": 5, "missing": 5}])
    assert cli.main(["brief-anchor", "--gaps"]) == 0
    out = capsys.readouterr().out
    assert "事實句還沒錨點 2 版（事實句 8 句、沒錨點 7 句）" in out and "已持有 1：HELD（2/3）" in out
    assert json.loads(_run_json(cli, capsys))[1]["ticker"] == "OPEN"


def _run_json(cli, capsys) -> str:
    assert cli.main(["brief-anchor", "--gaps", "--format", "json"]) == 0
    return capsys.readouterr().out
