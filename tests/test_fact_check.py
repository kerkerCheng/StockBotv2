"""敘事逐句核對（2026-11-12 使用者「先修吧」；事實抽樣① 11 份 8 份有錯）。

每一條測試對到一種真實撞過的形狀（事實抽樣①的那幾份）：6234「兩個部門」、LPK.DE「主要半導體廠多數」、KSHINTL.NS「8 月簽約」、
CECO 錯句抄自節錄檔自己的標題、1802.TW 引用了券商 PDF。旗標是要先看的句子，不是判定——這裡驗的是「該標的標到、不該標的不標」。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import fact_check as fcm
from alpha.narrative.hanzi_fold import PAIR_TOKENS, T2S
from alpha.providers import fact_checks as fc


# ---------------------------------------------------------------------------
# 夾具
# ---------------------------------------------------------------------------

def _resolver(files: dict[str, str], tmp_path: Path, *, readings: dict | None = None) -> fc.RefResolver:
    for rel, body in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return fc.RefResolver(root=tmp_path, readings=readings or {})


def _check(text: str, refs: tuple[str, ...], resolver, *, where: str = "position", names=None, as_of=date(2026, 11, 12),
           company: str = "co:self") -> fcm.SentenceCheck:
    brief = fcm.BriefText(ticker="T", company_id=company, brief_id="ib_x", slots=((where, text, refs),), as_of=as_of)
    ctx = fcm.CheckContext(resolve=resolver, names=names or {})
    result = fcm.check_brief(brief, ctx)
    assert len(result.checks) == 1, [c.sentence.text for c in result.checks]
    return result.checks[0]


def _kinds(check: fcm.SentenceCheck) -> dict[str, str]:
    return {f.kind: f.detail for f in check.flags}


# ---------------------------------------------------------------------------
# 字形折疊與切句
# ---------------------------------------------------------------------------

def test_every_fold_pair_is_two_characters_and_the_simplified_side_is_not_folded_again() -> None:
    assert all(len(token) == 2 for token in PAIR_TOKENS), [t for t in PAIR_TOKENS if len(t) != 2]
    assert not [v for v in T2S.values() if T2S.get(v, v) != v]
    assert fcm.squash("營收　擴產 經済") == "营收扩产经济"


def test_sentences_split_on_full_stops_outside_quotes_and_fall_back_when_a_bracket_is_left_open() -> None:
    assert fcm.split_sentences("公司說「供不應求。交期拉長」；然後擴產。最後一句") == \
        ["公司說「供不應求。交期拉長」；", "然後擴產。", "最後一句"]
    assert fcm.split_sentences("（沒收好的括號。第二句。") == ["（沒收好的括號。", "第二句。"]


# ---------------------------------------------------------------------------
# 數字
# ---------------------------------------------------------------------------

def test_number_claims_read_years_dates_amounts_percentages_and_counts_but_not_our_own_vocabulary() -> None:
    claims = {(c.kind, c.raw.strip()) for c in fcm.number_claims(
        "2026 年 11 月 4 日營收 5.7 億元、年增 26%，兩家客戶，約三成；錯的訊號（第 2 條）；自家三年百分位；起始門四項都過")}
    assert {("year", "2026"), ("date", "11 月 4 日"), ("amount", "5.7 億"), ("pct", "26%"), ("count", "兩家"),
            ("pct", "三成")} <= claims
    assert not [c for c in claims if c[1] in ("2", "三年", "四項")]


def test_amounts_match_the_source_across_units_and_table_headers(tmp_path: Path) -> None:
    resolver = _resolver({
        "library/raw/a.txt": "合同预计总金额区间为57,008万元至85,512万元（含税）。\n",
        "library/raw/b.txt": "NOTE: 金額單位新台幣仟元。\n鑽頭部門 來自外部客戶收入 $ 234,797\n",
    }, tmp_path)
    ok = _check("合同下限約 5.7 億元。", ("library/raw/a.txt",), resolver)
    assert "number_missing" not in _kinds(ok)
    wrong = _check("合同下限 6.7 億元。", ("library/raw/a.txt",), resolver)
    assert _kinds(wrong)["number_missing"] == "6.7 億"
    # 單位寫在我們自己的註記行（那一行不算原文），表格的數乘上它照算
    table = _check("鑽頭部門上半年營收 2.35 億元。", ("library/raw/b.txt",), resolver)
    assert "number_missing" not in _kinds(table)


def test_a_count_word_is_checked_against_the_lines_the_sentence_came_from(tmp_path: Path) -> None:
    """6234.TWO 11-12 版：「兩個部門」——部門資訊是三欄；整份節錄別處有「兩個」不能放過它。"""
    resolver = _resolver({"library/raw/seg.txt": (
        "部門資訊：鑽頭部門、設備部門、其他部門、調整及銷除、合計\n"
        "鑽頭部門：上半年營收 2.35 億元，部門利益 2,826 萬元\n"
        "設備部門：上半年營收 4,163 萬元，部門損失 1,447 萬元\n"
        "其他部門：沒有對外營收，部門利益 1,881 萬元\n"
        "其他說明：兩個月內完成驗收\n")}, tmp_path)
    check = _check("兩個部門：鑽頭部門與設備部門。", ("library/raw/seg.txt",), resolver)
    assert _kinds(check)["number_missing"] == "兩個"


def test_a_month_is_checked_near_the_claim_or_against_the_document_date(tmp_path: Path) -> None:
    """KSHINTL.NS 11-10 版：「8 月和 Hitachi Energy 簽了框架」——簡報寫的是 during the quarter（Q1，4–6 月），
    8 月的是法說；整份原文別處有 August 不能放過它。文件自己的日期（PUBLISHED）講的月份照算。"""
    resolver = _resolver({
        "library/raw/q1.txt": ("PUBLISHED: 2026-08-14\n"
                               "During the quarter, we also signed a long-term framework agreement with a large Global "
                               "transformer OEM.\n"
                               "The earnings call was held on August 11.\n"),
        "library/raw/q2_2026_11_05.txt": "Q2 FY27 revenue grew 85% over the prior year.\n",
    }, tmp_path)
    flagged = _check("7 月簽了長期供貨框架協議。", ("library/raw/q1.txt",), resolver)
    assert _kinds(flagged)["number_missing"] == "7 月"
    by_document = _check("11 月的財報稿說營收年增 85%。", ("library/raw/q2_2026_11_05.txt",), resolver)
    assert "number_missing" not in _kinds(by_document)
    # 只對到文件自己的日期、旁邊卻不是文件而是事件（簽約）：照標、附一句問句——KSHINTL 那一句就是這個形狀
    event = _check("8 月簽了長期供貨框架協議。", ("library/raw/q1.txt",), resolver)
    assert _kinds(event)["number_missing"] == "8 月" + fcm.META_ONLY_NOTE
    period_end = _check("8 月底營收年增 85%。", ("library/raw/q1.txt",), resolver)
    assert "8 月" not in _kinds(period_end).get("number_missing", "")


def test_our_own_deadlines_conditions_and_schedule_are_not_checked_as_facts(tmp_path: Path) -> None:
    resolver = _resolver({"library/raw/a.txt": "Revenue grew 20% in fiscal 2026.\n"}, tmp_path)
    future = _check("到 2027-08-31 還沒公布就算錯。", ("library/raw/a.txt",), resolver)
    assert "number_missing" not in _kinds(future)
    condition = _check("每噸 EBITDA 跌回 75,000 盧比以下（第 4 條）。", ("library/raw/a.txt",), resolver,
                       where="what_must_be_true")
    assert not condition.flags
    target = _check("銷量要走到約 45,000–50,000 噸。", ("library/raw/a.txt",), resolver, where="what_must_be_true")
    assert "number_missing" not in _kinds(target)
    schedule = _check("12 月 10 日的月營收與 3 月的年報。", ("library/raw/a.txt",), resolver, where="when")
    assert not schedule.flags
    later_this_month = _check("11 月下旬前再看。", ("library/raw/a.txt",), resolver)
    assert "number_missing" not in _kinds(later_this_month)
    command = _check("系統口徑邊緣（python -m alpha edge T，2026-11-10：市值約 1.6 億美元、分析師 3 家）。",
                     ("library/raw/a.txt",), resolver)
    assert "number_missing" not in _kinds(command)


def test_every_item_of_a_wrong_signal_list_is_a_condition_and_file_refs_may_carry_an_anchor(tmp_path: Path) -> None:
    """COHR 11-12：「錯的訊號…：A（第 1 條）；B」——第二條沒有開頭也沒有編號，被當成事實句標「名稱不在、沒對到」；
    引用 `thesis/lifecycle.json#…` 帶段落錨，被當成找不到檔。"""
    resolver = _resolver({"library/raw/a.txt": "Revenue grew 20% in fiscal 2026.\n",
                          "thesis/lifecycle.json": "{\"coherent_cpo\": {\"catalyst_checkpoints\": [\"2026-12\"]}}\n"}, tmp_path)
    brief = fcm.BriefText(ticker="T", company_id="co:self", brief_id="ib_x", as_of=date(2026, 11, 12), slots=((
        "what_must_be_true", "營收要年增 20%。錯的訊號（兩條）：供應商寫出降價（第 1 條）；NVIDIA 寫出改回銅線。",
        ("library/raw/a.txt",)),))
    checks = fcm.check_brief(brief, fcm.CheckContext(resolve=resolver)).checks
    assert [c.sentence.condition for c in checks] == [False, True, True]
    assert not checks[2].flags
    anchored = resolver("thesis/lifecycle.json#coherent_cpo.catalyst_checkpoints")
    assert anchored.kind == "note" and not anchored.problem and anchored.lines


def test_words_that_look_like_numbers_but_are_not_claims() -> None:
    """2026-11-12 全量 99 份抽樣看到的系統性誤標：表單名、待辦編號、「最新一季」「翻一倍」「一大段」「一個半年」、1H27。"""
    text = ("10-Q 與 20-F 都寫了；[805] 那份；最新一季、最後一筆、最大一家、翻一倍、一大段、一個半年、一個月比一個月大；"
            "新產能預計 1H27 年增 1 萬噸")
    claims = [(c.kind, c.raw.strip()) for c in fcm.number_claims(text)]
    assert claims == [("amount", "1 萬")], claims
    assert [(c.kind, c.value) for c in fcm.number_claims("約占四成二")] == [("pct", 42.0)]
    assert [(c.kind, c.raw.strip()) for c in fcm.number_claims("三大客戶")] == [("count", "三大")]
    # 圈號不是數字（002428.SZ 11-12：「④2028 年以後」被 NFKC 讀成 42028）
    assert [(c.kind, c.value) for c in fcm.number_claims("①7 月那張單；④2028 年以後")] == [("month", 7), ("year", 2028)]


def test_trademarks_space_thousands_and_few_years_match_their_source(tmp_path: Path) -> None:
    """SIVE.ST 11-12：POET 20-F 寫「Blazar™」（NFKC 變 blazartm）、季報寫「12 280 701 shares」、年報寫「in the next few years」。"""
    resolver = _resolver({"library/raw/a.txt": (
        "we have named the “Blazar™”.\n"
        "a directed new issue of 12 280 701 shares\n"
        "Discussions with hyperscalers suggest a CW laser supply shortage in the next few years.\n")}, tmp_path)
    assert "name_missing" not in _kinds(_check("20-F 寫光源用自家的 Blazar 混合雷射。", ("library/raw/a.txt",), resolver))
    assert "number_missing" not in _kinds(_check("定向增發 12,280,701 股。", ("library/raw/a.txt",), resolver))
    assert "qualifier_missing" not in _kinds(_check("年報說未來幾年 CW 雷射會短缺。", ("library/raw/a.txt",), resolver))


def test_source_side_percentages_and_table_units(tmp_path: Path) -> None:
    assert fcm.declared_units("Revenue (£'000)") == (1000.0,)
    assert fcm.declared_units("營業收入(仟元):1,247,946") == (1000.0,)
    assert fcm.declared_units("Amounts in MSEK") == (1e6,)
    resolver = _resolver({"library/raw/a.txt": "客戶 營收比重 41\n上半年銅箔約佔四成二\n"}, tmp_path)
    table = _check("客戶營收比重 41%。", ("library/raw/a.txt",), resolver)
    assert "number_missing" not in _kinds(table)
    tenth = _check("上半年銅箔約四成二。", ("library/raw/a.txt",), resolver)
    assert "number_missing" not in _kinds(tenth)


def test_shared_range_units_korean_qualifiers_json_counts_and_a_colon_after_a_file_ref(tmp_path: Path) -> None:
    """002270.SZ 11-12：「回購 1.5 到 2.5 億」前一個數借後一個數的單位；HD 現代年報的「주요 매입처」對「主要」；
    海關彙整站的 JSON「"total_shipments_company":131」對「131 筆」；「…_excerpt.txt：H 股」的全形冒號不是檔名；
    「華明多半不是主力」的「多半」是推論口氣，不是限定詞。"""
    resolver = _resolver({"library/raw/a.txt": (
        "回购资金总额不低于人民币 15,000 万元且不超过人民币 25,000 万元\n"
        "| 주 요 매 입 처 | HD Hyundai Electric China, MASCHINENFABRIK REINHAUSEN GMBH, 럭스코 外 |\n"
        "{\"shipments_12m\":8,\"vendor_name\":\"Maschinenfabrik Reinhausen\",\"total_shipments_company\":131}\n")}, tmp_path)
    assert [(c.kind, c.value) for c in fcm.number_claims("回購 1.5 到 2.5 億")] == [("amount", 1.5e8), ("amount", 2.5e8)]
    assert "number_missing" not in _kinds(_check("回購 1.5 到 2.5 億元。", ("library/raw/a.txt",), resolver))
    korean = _check("HD Hyundai Electric 把 Reinhausen 列進主要買進對象。", ("library/raw/a.txt",), resolver)
    assert "qualifier_missing" not in _kinds(korean)
    counts = _check("Virginia Transformer 從 Reinhausen 累計進口 131 筆、近一季 8 筆。", ("library/raw/a.txt",), resolver)
    assert _kinds(counts)["number_missing"] == "8 筆"         # 個位數單獨出現不算（任何一行都有個 8）
    assert [m.group(0) for m in fcm._INLINE_REF.finditer("library/raw/x_excerpt.txt：H 股規模")] == ["library/raw/x_excerpt.txt"]
    assert "qualifier_missing" not in _kinds(_check("但華明多半不是 Reinhausen 的對手。", ("library/raw/a.txt",), resolver))


def test_a_file_name_with_a_comma_stays_one_ref() -> None:
    """300757.SZ 11-12：券商報告檔名「…成長期，CPO蓄勢待發_中文.pdf」——路徑停在全形逗號，前半段被報成找不到這個檔、後半段混進要核的字。"""
    path = "library/private/broker_reports/r/2026-08-20_元大投顧_旺矽-6223_更新報告_MEMS進入高速成長期，CPO蓄勢待發_中文.pdf"
    items = fcm._depth_items([("replaced_by", f"同站對手只有券商編號 ＋ {path}（元大預期旺矽與致茂 2027 年成為主要量產供應商）")])
    assert items[0][2] == (path,)
    assert "CPO蓄勢待發" not in items[0][1]
    # 兩個檔名用逗號隔開時不黏在一起；檔名有副檔名之後的逗號照舊斷開
    two = fcm._depth_items([("k", "library/raw/a.txt，library/raw/b.txt：兩份都寫了營收")])
    assert two[0][2] == ("library/raw/a.txt", "library/raw/b.txt")
    prose = fcm._depth_items([("k", "library/raw/a_excerpt.txt，第三季營收年增兩成")])
    assert prose[0][2] == ("library/raw/a_excerpt.txt",)


# ---------------------------------------------------------------------------
# 引號、名稱、限定詞
# ---------------------------------------------------------------------------

def test_quotes_must_be_verbatim_after_folding_simplified_and_traditional(tmp_path: Path) -> None:
    resolver = _resolver({"library/raw/a.txt": "公司2025年开始批量供应特种电子布给下游CCL客户。\n"}, tmp_path)
    ok = _check("半年報寫「公司2025年開始批量供應特種電子布」。", ("library/raw/a.txt",), resolver)
    assert "quote_missing" not in _kinds(ok)
    translated = _check("半年報寫「低熱膨脹布批量供應」。", ("library/raw/a.txt",), resolver)
    assert _kinds(translated)["quote_missing"] == "「低熱膨脹布批量供應」"


def test_a_qualifier_without_its_counterpart_in_the_matched_lines_is_flagged(tmp_path: Path) -> None:
    """LPK.DE 10-08 版：年報寫 the majority of the relevant players，敘事寫「主要半導體廠多數」——「多數」對得到、「主要」對不到。"""
    resolver = _resolver({"library/raw/lpkf.txt": (
        "The majority of the relevant players in the semiconductor market are already using this technology in "
        "development and qualification.\n")}, tmp_path)
    check = _check("年報說主要半導體廠多數已在開發與認證階段使用這項技術。", ("library/raw/lpkf.txt",), resolver)
    assert _kinds(check)["qualifier_missing"] == "「主要」"


def test_a_qualifier_found_only_in_another_slot_s_ref_is_not_flagged(tmp_path: Path) -> None:
    """自己那格的引用沒對到、別格的引用對到了：限定詞也查別格對到的那幾行（11-12 R1：自己那格對到不滿三行時被切片切掉）。"""
    resolver = _resolver({"library/raw/own.txt": "今天天氣晴朗。\n",
                          "library/raw/other.txt": "Acme 的主要客戶是 Bolt Electronics，占營收 40%。\n"}, tmp_path)
    brief = fcm.BriefText(ticker="T", company_id="co:self", brief_id="ib_x", as_of=date(2026, 11, 12), slots=(
        ("position", "Acme 的主要客戶是 Bolt Electronics。", ("library/raw/own.txt",)),
        ("revenue", "營收四成來自單一客戶。", ("library/raw/other.txt",))))
    check = fcm.check_brief(brief, fcm.CheckContext(resolve=resolver)).checks[0]
    assert any(m.elsewhere for m in check.matches)
    assert "qualifier_missing" not in _kinds(check)


def test_names_must_appear_in_the_source_and_a_company_own_filing_counts_by_its_code(tmp_path: Path) -> None:
    resolver = _resolver({
        "library/raw/q1.txt": "We signed a framework agreement with a large Global transformer OEM.\n",
        "library/raw/mops_1802_annual_report.txt": "本公司已成功開發低熱膨脹係數玻布並量產。\n",
    }, tmp_path)
    latin = _check("年報說它和 Hitachi Energy 簽了框架。", ("library/raw/q1.txt",), resolver)
    assert "Hitachi" in _kinds(latin)["name_missing"]
    names = {"co:taiwan_glass": ("台玻", "1802"), "co:self": ("自己",)}
    own_filing = _check("台玻年報自述低熱膨脹玻布已量產。", ("library/raw/mops_1802_annual_report.txt",), resolver, names=names)
    assert "name_missing" not in _kinds(own_filing)


def test_our_own_header_and_note_lines_are_not_source_text(tmp_path: Path) -> None:
    """CECO 10-31 版：錯句「10-Q 說增加主要來自大型燃氣發電專案」抄自節錄檔自己的 [EXCERPT] 標題——那一行不是原文。"""
    resolver = _resolver({"library/raw/ceco.txt": (
        "Source URL: https://www.sec.gov/x\nExcerpt:\n"
        "[EXCERPT — 有限逐字引文] CECO 10-Q：成長主要來自排放與排氣系統用於大型燃氣發電專案\n"
        "RETRIEVED: 2026-10-27\nNOTE: 我們的註記\n【MD&A】\n"
        "\"Orders increased 192% driven by large-scale natural gas power generation projects.\"\n")}, tmp_path)
    lines = resolver("library/raw/ceco.txt").lines
    assert [line.text for line in lines] == [
        "\"Orders increased 192% driven by large-scale natural gas power generation projects.\""]
    check = _check("10-Q 說營收增加主要來自大型燃氣發電專案。", ("library/raw/ceco.txt",), resolver)
    assert "qualifier_missing" in _kinds(check)


def test_binary_and_missing_files_are_counted_as_unreadable_not_parsed(tmp_path: Path) -> None:
    """1802.TW：引用了使用者給的券商 PDF——當文字讀是 1.4 MB 亂碼（11-12 全量核對卡住十分鐘）。"""
    resolver = _resolver({"library/private/inbox/report.pdf": "%PDF-1.4 binary"}, tmp_path)
    pdf = resolver("library/private/inbox/report.pdf")
    assert pdf.kind == "note" and not pdf.lines and "不是文字節錄" in pdf.problem
    assert resolver("library/raw/nope.txt").problem
    assert resolver("engine_c://financial_snapshot/T").kind == "authority"
    check = _check("快照上本益比約 45 倍。", ("engine_c://financial_snapshot/T",), resolver)
    assert _kinds(check)["unverifiable"] == "45 倍"


def test_graph_sources_read_extraction_quotes_and_readings_read_their_citations(tmp_path: Path) -> None:
    (tmp_path / "extractions").mkdir()
    (tmp_path / "extractions" / "doc_a.json").write_text(json.dumps({
        "source_doc": {"title": "公告", "published_at": "2026-07-24"},
        "sources": [{"id": "doc_a_s1", "locator": "一、合同签署概况", "quote": "合同履行期限为2026年8月1日至2027年12月31日"}]},
        ensure_ascii=False), encoding="utf-8")
    readings = {"sr_0123456789abcdef": {"reading_id": "sr_0123456789abcdef", "reading": "判讀：量。\n第二段。",
                                        "citations": [{"source_id": "doc_b", "quote": "供不應求的逐字"}]}}
    resolver = _resolver({}, tmp_path, readings=readings)
    source = resolver("graph://source/doc_a")
    assert source.kind == "graph_source" and "2027年12月31日" in source.lines[0].text and "2026-07-24" in " ".join(source.meta)
    reading = resolver("sr_0123456789abcdef")
    assert [line.text for line in reading.lines] == ["判讀：量。", "第二段。", "供不應求的逐字"]


# ---------------------------------------------------------------------------
# 草稿、紀錄、沿用、還沒核的
# ---------------------------------------------------------------------------

def _brief_obj(brief_id: str, text: str, *, created: str = "2026-11-12T08:00:00+00:00", state: str = "open",
               ticker: str = "T", company: str = "co:t") -> SimpleNamespace:
    slot = SimpleNamespace(key="demand", text=text, evidence_refs=("library/raw/a.txt",))
    return SimpleNamespace(brief_id=brief_id, ticker=ticker, company_id=company, slots=(slot,),
                           candidate_state=SimpleNamespace(state=state, reason="理由一句。"), depth_check=(),
                           created_at=datetime.fromisoformat(created))


def test_a_record_keeps_digests_and_the_next_version_only_rechecks_changed_sentences(tmp_path: Path) -> None:
    resolver = _resolver({"library/raw/a.txt": "營收年增 26%。客戶兩家。\n"}, tmp_path)
    first = fcm.brief_text_from_record(_brief_obj("ib_1", "營收年增 26%。客戶兩家。"))
    result = fcm.check_brief(first, fcm.CheckContext(resolve=resolver))
    record = fc.build_record(result, company_id="co:t", changed=1, note="改了一句",
                             now=datetime(2026, 11, 12, 9, tzinfo=timezone.utc))
    assert record["sentences"] == 3 and record["changed"] == 1 and record["check_id"].startswith("fc_")
    ledger = tmp_path / "fact_checks.jsonl"
    fc.append_record(record, path=ledger)
    records, errors = fc.read_records(path=ledger)
    assert not errors and records[0]["sentence_digests"] == result.digests
    second = fcm.brief_text_from_record(_brief_obj("ib_2", "營收年增 26%。客戶三家。"))
    carried = fc.carried_digests("co:t", records)
    again = fcm.check_brief(second, fcm.CheckContext(resolve=resolver, carried=carried))
    assert [c.carried is not None for c in again.checks] == [True, False, True]


def test_a_record_refuses_a_draft_a_negative_change_count_and_an_empty_note(tmp_path: Path) -> None:
    resolver = _resolver({"library/raw/a.txt": "x\n"}, tmp_path)
    draft = fcm.brief_text_from_spec({"slots": {"demand": {"text": "一句。", "evidence_refs": ["library/raw/a.txt"]}}},
                                     ticker="T", company_id="co:t")
    result = fcm.check_brief(draft, fcm.CheckContext(resolve=resolver))
    with pytest.raises(ContractViolation, match="草稿"):
        fc.build_record(result, company_id="co:t", changed=0, note="x")
    written = fcm.check_brief(fcm.brief_text_from_record(_brief_obj("ib_1", "一句。")), fcm.CheckContext(resolve=resolver))
    with pytest.raises(ContractViolation, match="changed"):
        fc.build_record(written, company_id="co:t", changed=-1, note="x")
    with pytest.raises(ContractViolation, match="note"):
        fc.build_record(written, company_id="co:t", changed=0, note="  ")


def test_gaps_are_the_unchecked_version_or_a_story_written_after_the_check() -> None:
    briefs = [_brief_obj("ib_a", "x", ticker="A", company="co:a", created="2026-11-01T00:00:00+00:00"),
              _brief_obj("ib_b", "x", ticker="B", company="co:b"), _brief_obj("ib_c", "x", ticker="C", company="co:c")]
    stories = {"ib_b": {"story_id": "st_new", "created_at": "2026-11-12T10:00:00+00:00"},
               "ib_c": {"story_id": "st_c", "created_at": "2026-11-12T07:00:00+00:00"}}
    records = [{"brief_id": "ib_b", "story_id": "st_old", "created_at": "2026-11-12T09:00:00+00:00"},
               {"brief_id": "ib_c", "story_id": "st_c", "created_at": "2026-11-12T09:00:00+00:00"}]
    gaps = fc.fact_check_gaps(briefs, stories=stories, records=records)
    assert [(g["ticker"], g["kind"]) for g in gaps] == [("A", "brief"), ("B", "story")]
    assert {g["kind"] for g in gaps} == set(fc.FACT_CHECK_GAP_KINDS)
    # 規則上線之前寫的敘事，等的天數從上線那天算（不從寫的那天）
    assert gaps[0]["since"].startswith(fc.FACT_CHECK_SINCE.isoformat())


def test_a_bad_ledger_line_makes_the_count_unreadable_not_zero(tmp_path: Path) -> None:
    ledger = tmp_path / "fact_checks.jsonl"
    ledger.write_text("{壞掉的一行\n", encoding="utf-8")
    records, errors = fc.read_records(path=ledger)
    assert records == [] and errors
    with pytest.raises(ContractViolation, match="讀不懂"):
        fc.gaps_now(path=ledger)


def test_the_cli_prints_the_gaps_grouped_by_declared_state(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from alpha import cli

    monkeypatch.setattr(fc, "gaps_now", lambda: [
        {"ticker": "A", "kind": "brief", "state": "open"}, {"ticker": "B", "kind": "story", "state": "pass"}])
    assert cli.main(["brief-check", "--gaps"]) == 0
    out = capsys.readouterr().out
    assert "還沒逐句核對 2 版" in out and "可開 1：A" in out and "不要 1：B（故事換了）" in out
