"""名字比對的唯一 owner：`query.bottleneck.quote_names_company`（Phase 4 Step 4.1b）。

它被三處共用——聯合公告偵測（`_origin_mentions`）、RA packet 的 `layer_enumerations` 核對、層文件計數器——
所以規則只能住一處（L16）。這裡釘住四件事：整詞、單字分大小寫、中日韓字整串、ticker 不是名字。
"""
from __future__ import annotations

from dataclasses import dataclass

from query.bottleneck import (
    _origin_mentions,
    _strip_annotation,
    company_id_for_origin,
    company_name_forms,
    quote_names_company,
)


@dataclass(frozen=True)
class _Co:
    company_id: str
    display_name: str | None = None
    aliases: tuple[str, ...] = ()
    name_aliases: tuple[str, ...] = ()
    research_ticker: str | None = None


class _Reg:
    def __init__(self, *companies: _Co):
        self.companies = tuple(companies)

    def company_id_for_ticker(self, ticker: str):
        key = ticker.strip().upper()
        for c in self.companies:
            if key == (c.research_ticker or "").upper() or key in {a.upper() for a in c.aliases}:
                return c.company_id
        return None

    def has_company(self, company_id: str) -> bool:
        return any(c.company_id == company_id for c in self.companies)


AXT = _Co("co:axt", "AXT, Inc.", research_ticker="AXTI")
NVDA = _Co("co:nvidia", "NVIDIA Corporation", research_ticker="NVDA")
COHR = _Co("co:coherent", "Coherent Corp.", research_ticker="COHR")
APOLLO = _Co("co:apollo", "Apollo Global Management, Inc.", research_ticker="APO")
WIN = _Co("co:win_semiconductor", "WIN Semiconductors Corp.", research_ticker="3105.TWO",
          name_aliases=("穩懋半導體股份有限公司", "穩懋"))
SIVERS = _Co("co:sivers_semiconductors", "Sivers Semiconductors AB", aliases=("SIVEF",), research_ticker="SIVE.ST")
NO_NAME = _Co("co:ayar_labs", None, aliases=("AYAR",))


def test_short_registered_name_matches_as_a_whole_word():
    assert quote_names_company("6-inch indium phosphide wafer substrates from AXT to Coherent", AXT)
    assert quote_names_company("與AXT合作量產", AXT)          # 前後是中文字也算整詞（ASCII 邊界）
    assert not quote_names_company("the AXTI ticker", AXT)     # 整詞，不是子字串


def test_legal_name_matches_its_brand_core():
    assert quote_names_company("NVIDIA AI Data Center Infrastructure", NVDA)
    assert "NVIDIA" in company_name_forms(NVDA)


def test_single_word_name_is_case_sensitive():
    """單字名稱撞普通名詞是真的會發生的事：`Coherent` 對「coherent optics」、`Humanoid` 對「humanoid robots」。"""
    assert quote_names_company("Coherent shipped 6-inch InP", COHR)
    assert not quote_names_company("ship over five million coherent photonic ICs", COHR)


def test_multi_word_name_is_case_insensitive():
    assert quote_names_company("APOLLO GLOBAL MANAGEMENT said", APOLLO)


def test_apollo_project_name_is_not_the_company():
    """plan §0.7 Q4 指出的假陽性：Google 自己的 Apollo OCS 專案不是 Apollo Global Management。"""
    reg = _Reg(APOLLO, NVDA)
    assert _origin_mentions("Google (Apollo/Palomar 團隊自著論文)", reg) == set()


def test_cjk_names_match_as_whole_string():
    assert quote_names_company("穩懋半導體股份有限公司表示", WIN)
    assert quote_names_company("本季穩懋營收", WIN)


def test_self_reference_names_nobody():
    reg = _Reg(AXT, NVDA, COHR, WIN, SIVERS)
    assert _origin_mentions("本公司為全球前三大供應商", reg) == set()
    assert not any(quote_names_company("we are the sole supplier", c) for c in reg.companies)


def test_ticker_alias_is_not_a_name():
    """`aliases` 是交易代號（住 by_ticker），名字比對不收；沒有名字的公司一律 False——呼叫端要報「名冊無名可比」。"""
    assert not quote_names_company("SIVEF shares rose", SIVERS)
    assert company_name_forms(NO_NAME) == ()
    assert not quote_names_company("Ayar Labs AYAR", NO_NAME)


def test_comma_annotation_is_stripped_and_resolves():
    for raw in ("Sivers Semiconductors, with a named ALL.SPACE customer quotation",
                "Sivers Semiconductors, with a named Tachyon Networks quotation"):
        assert _strip_annotation(raw) == "Sivers Semiconductors"
        assert company_id_for_origin(raw, _Reg(SIVERS, AXT)) == "co:sivers_semiconductors"
    assert _strip_annotation("Hexagon AB, with named Schaeffler management statements") == "Hexagon AB"
    # 括號註解照舊
    assert _strip_annotation("Coherent（發行人官方新聞稿）") == "Coherent"


def test_form_shared_by_two_companies_names_neither():
    """同一個寫法屬於兩家（`Foo Inc.`／`Foo Ltd.` 的核心都是 `Foo`）→ 給了 registry 時誰都不算（不猜）。"""
    a, b = _Co("co:foo_a", "Foo Inc."), _Co("co:foo_b", "Foo Ltd.")
    reg = _Reg(a, b)
    assert quote_names_company("Foo said", a)                      # 單看一家：比得到
    assert not quote_names_company("Foo said", a, registry=reg)    # 放回 registry：含糊，不算
    assert quote_names_company("Foo Inc. said", a, registry=reg)   # 完整登記名稱只屬於一家：算
    assert _origin_mentions("Foo", reg) == set()


def test_name_aliases_resolve_origin():
    assert company_id_for_origin("穩懋半導體股份有限公司", _Reg(WIN, AXT)) == "co:win_semiconductor"
