"""結構表：**已研究過的公司**逐邊的結構事實——卡在哪條邊、那條邊多難繞過、往上接到誰在花錢。

⚠ 2026-09-23（Phase 0 Step 0b.3）：本檔原本是「瓶頸鏈排序」（`rank_bottlenecks()`，唯一排序權威）。
排序、兩份序（可行動／純結構）、top-N、`min_substitutability` 門檻與 `--by-sector` 分組整組退役
（ROADMAP Phase 0／G1、L19：排序讓研究火力去補格子把某一檔推上第一名）。**留下的是逐邊的事實**：
證據等級、`substitutability`（含未填）、`sole_source` 三態、`qualification_status`、自報／外部印證、
走不走得到需求錨、`anchor_gaps` 診斷、以及母體定義的 INV-3 計數。列的順序是 `(company_id, relation, bottleneck)`
字典序——**那是索引，不是名次**。

設計依據 `docs/brainstorms/2026-08-18-alpha-live-user-sized-requirements.md` §8 的三個問句仍在：

> CPO 是 AI SERVER 的瓶頸，InP 是 CPO 的瓶頸，瓶頸相連要能連到真的市場有在放 CapEx 的地方。

因此每一列回答三件事：**卡在哪條邊、那條邊多難繞過、往上接到誰在花錢**。

## 三個刻意的設計限制（排序退役後仍成立）

1. **不算加權綜合分數，也不排序。** 綜合分數是未經量測的新機制（D6），且會把「證據強度」與
   「瓶頸強度」壓成一個數字（L12）。這裡只攤開所有成分；「該看誰」由讀圖與敘事回答（Phase 2／3）。

2. **先以 `(src, relation, dst)` 去重，每組取最高 confidence，不加總。**
   實測 `co:axt → mat:inp_substrate` 有 4 條 EdgeAssertion 來自 4 份文件；
   若數邊，任何量都會變成「我們讀了幾份文件」的函數。`documents` 欄位保留該計數，但它只作**注意力**指標。

3. **證據等級是獨立的一欄，不是乘數。** 只有供應商自評 sub=5 的邊，與有客戶端印證的 sub=4，在表上是兩列
   各自可讀的事實；把它們合成一個序正是退役的那個機制。

## 已知限制（隨輸出常駐，不得只寫在文件裡）

- `substitutability` 有值的邊是少數；沒填的邊在表上是 `None`（未填≠否），coverage 欄印出比例。
- `structural_lead_time_weeks` 實質為空。**語意已限定為 qualification lead time**
  （換供應商合格週期，2026-09-02 定案）：交貨週期另住 `delivery_lead_time_weeks`，
  不得混入——當年唯一的「真值」（GF 52 週）就是交貨週期誤標，已改標。
  「難替代」與「換掉要多久」是兩件事，**本表不含後者**。
"""
from __future__ import annotations

import calendar
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

# 向下（找瓶頸）的邊型：只有這些的 substitutability 有意義。
DOWNSTREAM_RELATIONS = ("depends_on", "supplies_to", "constrained_by")
# 向上（找需求端）的邊型：這些邊的 substitutability 恆為 None，本來就不該有。
#
# ⚠ **`enables` 於 2026-09-18 移出本表**（pq2 [607]／[608]／[609] 資料歸位之後）。
# 抽取 prompt 的逐字定義是 `enables` — **A's adoption drives demand for B**
# ⇒ B 被 A 需要，方向與本表（`upward[src].add(dst)` ＝ A 被 B 需要）**相反**。
# 圖裡先前兩種寫法並存，而程式實作了沒寫下來的那一種，於是兩個錯互相抵銷、長期沒人發現。
# 資料已逐條對來源逐字重判並改正（29 條），所以這裡才能改——**順序不可換**：
# 只改程式不改資料，實測 `no_demand_edge` 會由 51 打到 67。
UPSTREAM_RELATIONS = ("is_component_of",)

#: 「A 的採用帶動 B 的需求」⇒ **B 被 A 需要**，需求沿 dst → src 往上傳，與
#: `DEPENDENCY_RELATIONS` 同向。之所以自成一表而不併進去，是因為兩者的**證據性質不同**：
#: `depends_on`／`constrained_by` 說的是「沒有它就不能運作」，`enables` 說的是
#: 「它的採用把需求拉過來」——合併會讓兩種主張在下游分不開。
DEMAND_PULL_RELATIONS = ("enables",)

#: 「src 需要 dst」的邊型——**dst 是被需要的那一端**，所以需求要沿著 dst → src 往上傳。
#:
#: ⚠ `constrained_by` 與 `depends_on` 的差別在**證據性質**，不在**方向**：
#: 前者是 documented limitation／counter path、後者是 technical dependency
#: （`prompts/extract_system.md` 的逐字定義），而「A 受限於 B」與「A 依賴 B」對
#: 「誰需要誰」給的是同一個答案。另外兩處獨立登記處也都把 dst 當被需要的一端：
#: `DOWNSTREAM_RELATIONS` 上面那一行、`schema/vocab.json` 的
#: `sole_source_beneficiary_end`（`constrained_by: "dst"`，與 `depends_on` 同格）。
#:
#: 事發（2026-09-18 量測）：`build_upward_index` 原本只認 `depends_on`，於是
#: `co:coherent --constrained_by--> tech:inp_dfb_laser` 與
#: `tech:cpo --constrained_by--> tech:cpo_full_stack_test` 這兩條**圖裡已經有的邊**
#: 走不到需求錨。ROADMAP 當時的提案是「把 `constrained_by` 加進 `UPSTREAM_RELATIONS`」
#: ——**實測推翻：那個方向是反的**（`upward[src].add(dst)` ＝「A 被 B 需要」），
#: 它會把 `co:iqe` 那條 accepted 列的鏈路從 5 節點靜默改成 4 節點，語意變成
#: 「IQE 被 InP 基板需要」。放進本常數（dst → src）才與 `depends_on` 同形。
#:
#: 放閘當下的實測（L14-3 先量測後放閘）：**accepted 37 列排序位移 0 列**、
#: accepted 鏈路改變 0 列、filtered 185 列中 **2 列**由「走不到錨」變成走得到
#: （`co:aehr_test_systems → tech:cpo_full_stack_test`、`co:macom → tech:inp_dfb_laser`）。
#: 今天不動任何排名，改變的是**那兩個研究工單值不值得做**：假設補上 `substitutability=4`，
#: 放閘前 AEHR 落在無錨區第 37 名，放閘後是第 27 名（錨 `tech:ai_switch`、3 跳）。
#:
#: ⚠ **`enables` 刻意不進來。** 它的官方定義是「A's adoption drives demand for B」
#: （需求驅動，方向與本常數相反），但圖裡也被當成元件使能用——那是 ROADMAP 記在案的
#: 未解 L12（一表兩義），修法是先分開再各自定規則。在它有答案之前把整張方向表泛化出來，
#: 得到的會是一格憑空填上的答案（L17-4：general 到資料支持的那一格為止）。
DEPENDENCY_RELATIONS = ("depends_on", "constrained_by")

# ⚠ 2026-09-23（Step 0b.3）：`MIN_SUBSTITUTABILITY = 4`（向下邊 sub ≥ 4 才進排序）隨排序退役。
# 結構表不設門檻：sub 2 的邊與未填的邊都在表上，各自帶著自己的值。要「難替代」的子集由消費端自己說
# 它用了什麼判準（`alpha/providers/graph_neo4j.py::get_bottlenecks` 的 `min_substitutability` 是 provider
# 自己宣告的 bottleneck 定義，不是本表的門檻）。

# 需求錨點（封閉字彙，會隨圖成長而擴充——擴充改這裡，不要改演算法）。
#
# ⚠ 首版用「往上走最長路徑，端點即錨點」的啟發式，**產出是垃圾**：圖裡有環，
# 最長路徑會繞回目標本身（實測 co:lumentum 的鏈走成
# `… → tech:ai_compute_buildout → co:lumentum`，真正的需求端出現在中間），
# 而且端點常是 `tech:semicon_manuf_equipment` 這種上游設備，不是需求。
# **看起來很結構化、實際無意義的欄位比沒有這一欄危險**，所以改成明確列舉 ＋ 最短路徑。
#
# 判準（使用者 2026-08-18）：「要是真的市場有在投資的點，不然一個沒人用的技術的瓶頸，
# 好像也沒用。」所以錨點必須是**有人在花錢買的終端需求**，不是任何上游節點。
# ⚠ 這裡只是 config 讀不到時的最後防線，**不是 SSOT**。真正的白名單是
# `config/sector_anchors.json` 的所有 anchors（[323]，2026-08-31）。
#
# 事發：白名單原本硬編在這裡（4 個，全屬 AI 光互連），而 config 宣告了 12 個分屬五個
# 產業——**交集只有 2 個**。後果是產業分組永遠只長得出光互連：其他產業的邊走不到任何
# 被認可的錨，一律落入「🔴 無需求錨」並被標成「資金不在鏈上、非候選」。實測 GF 那 6 條
# 成熟製程晶片的邊就是這樣被誤判的——車用／工業 MCU 當然有人花錢買。
# 同一個分類有兩份且已偏離（L16）；SSOT 收斂到 config 後，新增產業只改 config。
_ANCHOR_FALLBACK = frozenset(
    {
        "tech:ai_compute_buildout",
        "tech:ai_switch",
        "tech:scale_up_network",
        "tech:optical_scale_up",
    }
)


def load_demand_anchors(path: str = "config/sector_anchors.json") -> frozenset[str]:
    """需求錨白名單（SSOT：config/sector_anchors.json 的所有 anchors）。

    判準不變（使用者 2026-08-18）：錨必須是**有人在花錢買的終端需求**，不是任何上游
    節點。新增產業＝在 config 加一組錨，不改演算法。
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return _ANCHOR_FALLBACK
    anchors = {
        str(anchor)
        for anchor_list in (data.get("sectors") or {}).values()
        for anchor in anchor_list
    }
    return frozenset(anchors) or _ANCHOR_FALLBACK


DEMAND_ANCHORS = load_demand_anchors()

# 五級（2026-08-30，使用者核准 [270]）。設計動機：三級制**過度懲罰自報**——客戶端印證
# 常與重定價事件同日到達（COHR 實測 Shadow 42.76 → 印證日 68+），等印證＝系統性遲到；
# 而「已收預付款」「審計客戶%」這類自報的金流／審計事實難以偽造，不該與敘述性自報同級。
# `self_reported_costly` 用「出自 filing（審計／法律責任文件）」當確定性 proxy：
# filing 裡也有行銷語，但法律責任使其系統性更貴——proxy 的限制明講，不假裝是語意判斷。
# `counterparty_joint`：聯合公告的複合 origin（"IQE plc / Tower Semiconductor"）單一字串
# 解析必然失敗，先前整級掉到 needs_review——雙方具名的公告證據力僅次於純客戶端，修正之。
# `media_relay`（2026-10-01 Phase 4 Step 4.3）：origin 是登記的媒體（`config/publishers.json`）、或任何發布者
# 宣告 `origin_linkage=same_origin` 的轉述文件。**與 needs_review 同級**——它不是升級，只是把 None 的兩義拆開（L12）：
# 「不知道是誰」與「知道是誰、但它是轉述」是兩件事，後者再追也不會變成第三方印證，要找的是它轉述的那份一手。
# ⚠ 任何列舉等級的表（`EVIDENCE_LABEL`、`alpha.narrative.argument.EVIDENCE_CLASS_PLAIN`、
# `alpha.evidence_quality.EVIDENCE_CLASS_TO_LEVEL`、`alpha.providers.graph_neo4j._EVIDENCE_CLASS_TIER`）key 集合必須等於本表
# （`tests/test_origin_resolution.py` 守著）；`query.graph_walk.CORROBORATED_EVIDENCE` 是子集、不含它。
EVIDENCE_RANK = {
    "externally_corroborated": 4,
    "counterparty_joint": 3,
    "self_reported_costly": 2,
    "needs_review": 1,
    "media_relay": 1,
    "self_reported": 0,
}
EVIDENCE_LABEL = {
    "externally_corroborated": "外部印證",
    "counterparty_joint": "雙方聯合",
    "self_reported_costly": "自報·filing",
    "needs_review": "待判定",
    "media_relay": "媒體轉述",
    "self_reported": "供應商自報",
}
#: 同級時誰勝出（只有 needs_review／media_relay 同級）：一條邊同時有「解析不到」與「媒體轉述」的 origin 時印**待判定**——
#: 還有一個沒認出來的來源，它仍可能是獨立第三方；印媒體轉述會讓人以為已經知道每一份是誰。
#: 結果不得取決於 origin 字串的迭代順序（新增一份文件不該讓標籤來回翻）。
_TIE_WINS = frozenset({"needs_review"})
QUALIFICATION_RANK = {"qualified": 3, "qualifying": 2, "designed_in": 2, "sampling": 1}


def parse_attributes(raw: Any) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    return raw if isinstance(raw, dict) else {}


def is_entity_id(node_id: Any) -> bool:
    """真 Entity 的 id 是 `前綴:slug`。

    ⚠ 圖裡有 188 個 Claim 節點貼著 `:Entity` 標籤（id 形如 `<doc_id>_cl1`），
    任何 `MATCH (n:Entity)` 都會多撈到它們。真 Entity 有 223 個且 100% 有前綴，
    所以用前綴過濾是可靠的（2026-08-18 實測）。
    """
    return ":" in str(node_id or "")


#: 公司名稱尾端的法律型態 token（封閉清單）。**只在比對時去掉**，不改任何呈現。
#: 比對前每個 token 先去掉非字母數字（"Inc." → "inc"、"Co.," → "co"、"S.A." → "sa"）。
#: ⚠ general 到資料支持的那一格為止（L17-4）：2026-09-16 實測 69 個解析不到的 origin 字串裡，
#: 約 20 個只差這些尾綴或尾端一段括號註解；再泛化（模糊比對、縮寫）就會開始誤中。
_LEGAL_SUFFIX_TOKENS = frozenset({
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
    "llc", "plc", "ag", "ab", "sa", "nv", "gmbh", "kk", "holding", "holdings", "group",
})
_TRAILING_ANNOTATION = re.compile(r"\s*[（(][^（）()]*[）)]\s*$")
#: 逗號接 `with …` 的註解（「Sivers Semiconductors, with a named Tachyon Networks quotation」）——與尾端括號同一種東西：
#: 研究者寫給人看的脈絡，不是發布者身分。2026-10-01 實測 3 個字串（Sivers ×2、Hexagon ×1）。
_TRAILING_WITH = re.compile(r",\s*with\b.*$", re.IGNORECASE)


def _strip_annotation(text: str) -> str:
    """去掉 origin 尾端的註解：括號一組（`Coherent（發行人官方新聞稿）` → `Coherent`）與逗號接 `with …`。

    括號裡是研究者寫給人看的脈絡（發行人／客戶端／轉載），不是發布者身分的一部分；
    留著它會讓一份公司自家文件被當成解析不到的第三方（2026-09-16 實測 20 筆）。
    只去尾端一組；名稱中段的括號不動。
    """
    stripped = _TRAILING_ANNOTATION.sub("", str(text or "")).strip()
    return _TRAILING_WITH.sub("", stripped).strip()


def _core_name(text: str) -> str:
    """比對用的核心名稱：casefold、去掉尾端的法律型態 token、去頭尾標點。

    `Lumentum Holdings Inc.` 與 `Lumentum` 是同一家；`MACOM Technology Solutions Holdings, Inc.`
    與 `MACOM Technology Solutions` 也是。呈現層不用它——`display_name` 印的仍是登記名稱。
    """
    tokens = str(text or "").casefold().split()
    while tokens:
        tail = re.sub(r"[^0-9a-z]", "", tokens[-1])
        if not tail or tail in _LEGAL_SUFFIX_TOKENS:
            tokens.pop()
            continue
        break
    return " ".join(tokens).strip(" ,.;:-")


def _core_name_cased(text: str) -> str:
    """與 `_core_name` 同一套尾綴規則，但**保留原本的大小寫**——引文比對要分大小寫（見 `quote_names_company`）。"""
    tokens = str(text or "").split()
    while tokens:
        tail = re.sub(r"[^0-9a-z]", "", tokens[-1].casefold())
        if not tail or tail in _LEGAL_SUFFIX_TOKENS:
            tokens.pop()
            continue
        break
    return " ".join(tokens).strip(" ,.;:-")


def company_name_forms(company) -> tuple[str, ...]:
    """一家公司**被具名**時可能出現的寫法——名字比對的唯一來源（2026-10-01 Phase 4 Step 4.1b）。

    ＝ 登記名稱 `display_name`、它去掉法律尾綴的核心名稱（保留大小寫）、`name_aliases`（短名、中文名）。
    ⚠ **不含 `aliases`**：那是交易代號、住 `by_ticker`（`company_id_for_ticker` 的事），不是名字。
    ⚠ 讀的是 registry 真有的欄位。2026-09-16 之前這裡讀 `name`，而 `CompanyIdentity`
    從來沒有這個欄位（100 家 0 家有）——測試的假登記表有，所以測試全綠、production
    一家都解析不到（L17：機制只認得當初那個案例）。
    """
    forms: set[str] = set()
    display = str(getattr(company, "display_name", None) or "").strip()
    if display:
        forms.add(display)
        forms.add(_core_name_cased(display))
    for alias in getattr(company, "name_aliases", None) or ():
        forms.add(str(alias).strip())
    return tuple(sorted(f for f in forms if f))


#: 中日韓字元：這類名字沒有空白分詞，「整詞」比對會被前後的字擋掉（「穩懋半導體股份有限公司」裡的「穩懋半導體」）。
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]")


def _form_pattern(form: str) -> re.Pattern[str]:
    """一個寫法的比對式。

    - 含中日韓字元 → 完整字串出現即算（沒有分詞可依）。
    - 其餘 → **ASCII 整詞**（`(?<![A-Za-z0-9_])…(?![A-Za-z0-9_])`；不用 `\\b`——Python 把中文字算 word 字元，
      「與AXT合作」會漏抓）；**單一個詞分大小寫**（`Coherent` 不比到「coherent optics」、`Humanoid` 不比到
      「humanoid robots」），多個詞不分（`Tower Semiconductor` 在聯合公告裡常改寫大小寫，多詞也不會撞到普通名詞）。
    """
    if _CJK.search(form):
        return re.compile(re.escape(form))
    flags = 0 if len(form.split()) == 1 else re.IGNORECASE
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(form) + r"(?![A-Za-z0-9_])", flags)


def shared_name_forms(registry) -> frozenset[str]:
    """registry 裡**兩家以上共用**的寫法（casefold）——同一段字對到兩家時誰都不算（不猜，L15）。

    例：`Foo Inc.` 與 `Foo Ltd.` 的核心名稱都是 `Foo`；引文裡的「Foo」不能同時算兩家具名
    （那會把一個含糊的字抬成「雙方聯合」）。
    """
    owners: dict[str, set[str]] = defaultdict(set)
    for company in registry.companies:
        for form in company_name_forms(company):
            owners[form.casefold()].add(company.company_id)
    return frozenset(form for form, ids in owners.items() if len(ids) > 1)


def quote_names_company(quote: str | None, company, *, registry=None, shared: frozenset[str] | None = None) -> bool:
    """這段文字（引文或 origin 字串）有沒有**具名**這家公司——名字比對的唯一 owner。

    用在四處（同一個函式，不各寫一份——L16）：`_origin_mentions`（聯合公告偵測）、
    RA packet 的 `layer_enumerations` 核對（Step 4.2a）、層文件計數器（Step 4.4）、證據等級的逐來源具名
    （`query.origin_resolution.corroboration`，Phase 6 Step 6.4；含它的違反數計數器）。
    名字只來自 `company_name_forms`；registry 沒有名字的公司一律 False——**呼叫端要把
    「名冊無名可比」與「引文真的沒具名」分開報**（`company_name_forms` 回空 tuple 就是前者）。
    給了 `registry` 時，與另一家共用的寫法不算（`shared_name_forms`）。
    ⚠ 2026-10-01 之前 `_origin_mentions` 用 casefold 子字串＋長度 ≥4 防誤中：會讓單字公司名撞到普通名詞，
    又會讓 `AXT`／`IQE` 這種三個字母的名字永遠比不到。
    `shared`：呼叫端預先算好的 `shared_name_forms(registry)`（大量比對時不必每次重算；給了就不看 `registry`）。
    """
    text = str(quote or "")
    if not text:
        return False
    if shared is None:
        shared = shared_name_forms(registry) if registry is not None else frozenset()
    return _named_by(text, company, shared)


def usable_name_forms(company, shared: frozenset[str]) -> tuple[str, ...]:
    """這家公司**比得到**的寫法：`company_name_forms` 扣掉與另一家共用的（`shared_name_forms`）。

    回空 tuple＝「名冊無名可比」——沒有任何寫法，或每個寫法都與另一家共用（同一家公司兩個 id：2026-10-03 的
    `co:openlight`／`co:openlight_photonics`）。兩種補救都是名冊／身分，不是讀原文（Phase 6 Step 6.4 的 `no_name_forms`）。
    """
    return tuple(form for form in company_name_forms(company) if form.casefold() not in shared)


def _named_by(text: str, company, shared: frozenset[str]) -> bool:
    """比對本體（`quote_names_company` 與 `_origin_mentions` 共用；`shared` 由呼叫端算一次）。"""
    return any(_form_pattern(form).search(text) for form in usable_name_forms(company, shared))


def _name_variants(company) -> set[str]:
    """`company_id_for_origin` 的**整串相等**比對用：名字寫法（`company_name_forms`）＋ registry 明列的 ticker alias。

    與 `quote_names_company`（「有沒有提到」）是兩個問題：這裡問「整個 origin 是不是就是這家」，
    所以多收 ticker（origin 寫成代號時也算）；比較端（`company_id_for_origin`）對每個寫法套 `_core_name`
    去掉大小寫與法律尾綴。
    """
    variants: set[str] = set(company_name_forms(company))
    variants |= {str(a) for a in (getattr(company, "aliases", None) or ()) if str(a)}
    return {v for v in variants if v}


def company_id_for_origin(origin: str | None, registry) -> str | None:
    """把 SourceDoc 的 `origin_entity`（人類公司名）解析成 `co:*`。

    ⚠ 解析失敗一律回 None，**不得當成「不同源」**——那會讓供應商自報悄悄通過檢查，
    正是 L8／L11 要防的 laundering。順序由嚴到寬，兩個以上候選就不猜（L15）。
    比對前先去掉尾端括號註解與法律型態尾綴（`_strip_annotation`／`_core_name`）；
    去掉的只是格式，不是身分——`Foo Inc.` 與 `Foo Ltd.` 兩家並存時 `Foo` 仍回 None。
    """
    if not origin:
        return None
    text = _strip_annotation(str(origin).strip())
    if not text:
        return None
    by_ticker = registry.company_id_for_ticker(text)
    if by_ticker:
        return by_ticker
    slug = "co:" + text.lower().replace(" ", "_").replace(".", "").replace(",", "")
    if registry.has_company(slug):
        return slug
    # 整串就是某家的一個名字寫法（大小寫不計）——中文名走這條：`_core_name` 只認 ASCII，
    # 會把「穩懋半導體股份有限公司」整個當標點丟掉（2026-10-01 Phase 4 Step 4.1b）。只增不減：
    # 比不到才往下走核心名稱；兩家以上都比到就不猜。
    exact = {c.company_id for c in registry.companies
             if any(text.casefold() == str(v).casefold() for v in _name_variants(c))}
    if len(exact) == 1:
        return exact.pop()
    if len(exact) > 1:
        return None
    needle = _core_name(text)
    if not needle:
        return None
    hits = {
        c.company_id
        for c in registry.companies
        if any(needle == _core_name(v) for v in _name_variants(c))
    }
    return hits.pop() if len(hits) == 1 else None


def _origin_mentions(origin: str, registry) -> set[str]:
    """origin 字串中被具名的 registry 公司集合——比對規則就是 `quote_names_company`（唯一 owner）。

    供聯合公告偵測用：複合 origin（"IQE plc / Tower Semiconductor (joint announcement)"）
    無法整串解析成單一公司，但其中的具名仍是確定性可比對的。核心名稱（去尾綴）也算具名：
    `Tower Semiconductor Ltd.` 的登記名稱不會逐字出現在聯合公告的 origin 裡。
    """
    text = str(origin or "")
    if not text:
        return set()
    shared = shared_name_forms(registry)
    return {company.company_id for company in registry.companies if _named_by(text, company, shared)}


def origin_docs(entries: Iterable[tuple[Any, Any, Any]],
                quotes_by_assertion: Mapping[str, Iterable[str]]) -> tuple:
    """一個 origin 在一條邊上的 `(assertion_id, source_doc_id, origin_linkage)` 列 → 逐份文件的 `OriginDoc`（含逐字）。

    逐字只認 assertion id 對得到的（`query.sub_language.fetch_all_quotes`）；沒有 id 的列只帶出文件與宣告、沒有逐字
    （沒有引文就沒有具名——不是「不知道」）。文件與引文都排序：結果不得取決於圖的回傳順序。
    """
    from query.origin_resolution import OriginDoc

    by_doc: dict[tuple[str | None, str | None], set[str]] = {}
    for assertion_id, doc_id, linkage in entries:
        bucket = by_doc.setdefault((str(doc_id) if doc_id else None, linkage or None), set())
        if assertion_id:
            bucket.update(str(q) for q in quotes_by_assertion.get(str(assertion_id)) or () if q)
    return tuple(OriginDoc(doc_id=doc, linkage=linkage, quotes=tuple(sorted(quotes)))
                 for (doc, linkage), quotes in sorted(by_doc.items(), key=lambda kv: (str(kv[0][0] or ""),
                                                                                    str(kv[0][1] or ""))))


def edge_corroborations(
    subject: str,
    origins: Iterable[str | None],
    registry,
    filing_origins: frozenset | set = frozenset(),
    *,
    quotes_by_assertion: Mapping[str, Iterable[str]],
    origin_assertions: Mapping[str, Iterable[tuple[Any, Any, Any]]],
    publishers=None,
    relay=None,
    shared: frozenset[str] | None = None,
) -> list:
    """一條邊每個 origin 的判定（`query.origin_resolution.Corroboration`，依 origin 字串排序）——`classify_evidence`
    取它們的最高等級；`query.layer_stats` 讀 `withheld`（沒升的理由）。判定本身只在 `corroboration`（唯一 owner）。

    `quotes_by_assertion`、`origin_assertions` **必填**（Phase 6 Step 6.4；plan §5）：呼叫端沒給逐字就丟例外——
    靜默當成「沒有引文」會把全部邊降級，而那與「規則真的降了它們」同形（L13）。
    `origin_assertions`：`CanonicalEdge.origin_assertions`（origin → 引用這條邊的 `(assertion_id, doc, linkage)`）。
    """
    from query.origin_resolution import corroboration, get_publishers

    if quotes_by_assertion is None or origin_assertions is None:
        raise TypeError("classify_evidence／edge_corroborations 需要 quotes_by_assertion 與 origin_assertions"
                        "（逐來源具名核對讀逐字；沒給就丟例外，不得靜默把全部邊降級——L13）")
    pubs = publishers if publishers is not None else get_publishers()
    return [corroboration(origin, subject, origin_docs(origin_assertions.get(origin) or (), quotes_by_assertion),
                          registry, filing=origin in filing_origins, publishers=pubs, relay=relay, shared=shared)
            for origin in sorted({str(o) for o in origins if o})]


def best_evidence(levels: Iterable[str]) -> str:
    """取最高等級（同級時 `_TIE_WINS` 勝出——結果不得取決於迭代順序）；一個都沒有＝供應商自報。"""
    best = "self_reported"
    for level in levels:
        if (EVIDENCE_RANK[level], level in _TIE_WINS) > (EVIDENCE_RANK[best], best in _TIE_WINS):
            best = level
    return best


def classify_evidence(
    subject: str,
    origins: Iterable[str | None],
    registry,
    filing_origins: frozenset | set = frozenset(),
    *,
    quotes_by_assertion: Mapping[str, Iterable[str]],
    origin_assertions: Mapping[str, Iterable[tuple[Any, Any, Any]]],
    publishers=None,
    relay=None,
    shared: frozenset[str] | None = None,
) -> str:
    """六分（五個等級＋與 needs_review 同級的 media_relay），取各 origin 所能支持的最高等級。

    每個 origin 的等級只由 `query.origin_resolution.corroboration`（唯一 owner）判——先經 `resolve_origin` 分成三態：
    - **名冊公司**：是主詞 → 自報（filing 出身為 costly）；不是主詞 → 主詞是公司時，**這個 origin 自己的引文**要
      逐字具名主詞才是外部印證（否則待判定，Phase 6 Step 6.4）；主詞不是公司 → 外部印證。
    - **登記的發布者**（`config/publishers.json`）：`publisher_lifts` 逐份說算的那幾份文件裡，主詞是公司時要有一段
      具名主詞、不是轉述句（宣告 `independent` 的文件不套轉述）的引文 → 外部印證；否則 → 媒體轉述。
    - **解析不到**：再過一道聯合公告偵測（**去註解後**的字串具名 ≥2 家名冊公司且含主詞以外者）→ 雙方聯合；
      否則待判定。`None` 同時可能是「真第三方」與「沒解析出來的別名」，不得壓成布林（L12）——
      所以未登記就留在待判定，不猜。
    `filing_origins`：來自 source_type=='filing' 文件的 origin 集合（costly proxy）。
    `quotes_by_assertion`、`origin_assertions`：**必填**（見 `edge_corroborations`）。
    `publishers`、`relay`：測試用；預設讀正式設定與正式轉述字表。

    ⚠ 解析到主詞的 origin **一律是自報**（filing 出身才是 costly）——2026-10-01 Phase 4 Step 4.1a
    （使用者定案 Q8b 替代案 B）拿掉了「解析到主詞、但同一字串另具名他家 → counterparty_joint」那支抬升：
    「客戶高管在供應商新聞稿裡具名」仍是供應商發的稿，不是獨立的客戶端印證（L8）。
    ⚠ 聯合公告偵測讀**去掉尾端註解**的字串（Step 4.3）：註解是研究者寫的脈絡（「轉載 A／B 聯合新聞稿」
    「內含 X 具名引述」），不是發布者身分——讀原字串會讓註解驅動證據等級（R2-b 轉來的 non-blocking）。
    """
    return best_evidence(c.level for c in edge_corroborations(
        subject, origins, registry, filing_origins, quotes_by_assertion=quotes_by_assertion,
        origin_assertions=origin_assertions, publishers=publishers, relay=relay, shared=shared))


@dataclass
class CanonicalEdge:
    src: str
    relation: str
    dst: str
    substitutability: int | None = None
    sole_source: bool | None = None
    qualification_status: str | None = None
    ramp_execution: int | None = None
    lead_time_weeks: int | None = None
    confidence: float = 0.0
    documents: int = 0
    origins: set = field(default_factory=set)
    filing_origins: set = field(default_factory=set)
    #: origin → 引用這條邊的 assertion：`[(assertion_id, source_doc_id, origin_linkage), …]`（缺＝None）。
    #: 逐來源具名核對要知道每個 origin 的逐字（逐字掛在 assertion 上）與各出自哪份文件——`publisher_lifts` 與轉述檢查的
    #: 豁免都是**文件層級**的宣告：同一家媒體的兩份文件可能一份 independent、一份 same_origin（Step 4.3、Phase 6 Step 6.4）。
    #: ⚠ 2026-10-03 之前這裡是 `origin_linkages`（origin → 宣告集合）：逐 origin 收成一個集合，就分不出是哪一份宣告的。
    origin_assertions: dict = field(default_factory=dict)
    #: 贏得 `substitutability` 值的那筆 assertion（逐屬性取最高 confidence；同分時先到者贏——與值的決定同一步）。
    #: sub 旗標跟著**值**走（Phase 6 Step 6.5）：這條邊印的 sub 是哪一筆給的，就印那一筆的引文撐不撐得住。
    sub_assertion_id: str | None = None
    #: 撐住這個 sub 值的那段引文有沒有在談可替代性（`query.sub_language.canonical_sub_language`）。
    #: None＝這條邊沒有 sub、這次沒核對、或贏家那筆沒有 id——**不是 False**。只印、不改值、不進讀圖 digest。
    sub_language_in_quote: bool | None = None
    evidence: str = "self_reported"
    #: 引用到的 SourceDoc id → 它的 `published_at`（字串或 None）。
    #: ⚠ 這是 point-in-time 的唯一時間線索：canonical edge 本身沒有時間欄位，
    #: 「這條邊在 T 那天存不存在」只能由「引用它的文件在 T 之前發表過沒有」回答。
    source_docs: dict = field(default_factory=dict)


def collapse_assertions(rows: Iterable[Mapping[str, Any]]) -> dict[tuple, CanonicalEdge]:
    """把 EdgeAssertion 收斂成 canonical edge。

    同一條 (src, relation, dst) 可能有多份文件各講一次。**取最高 confidence 那一份的
    屬性值，不加總、不平均**——加總會讓分數變成 ingestion 量的函數；平均會讓一份低品質
    文件稀釋一份一手 filing。`documents` 記下份數但不參與排序。
    """
    grouped: dict[tuple, CanonicalEdge] = {}
    # ⚠ **逐屬性**記最佳 confidence，不是整條邊記一個。首版對整條邊只取
    # 「confidence 最高那份 assertion」的全部屬性，於是若該份剛好沒填
    # `substitutability`，整條邊的值就被丟掉——實測 co:axt 因此整個從排名消失，
    # 覆蓋率也從 22%（assertion 層）假掉到 16%（edge 層）。
    # 正確語意是「對這個屬性發言過的文件裡，最可信的那一份怎麼說」。
    attr_conf: dict[tuple, dict[str, float]] = defaultdict(dict)

    def _take(key: tuple, edge: CanonicalEdge, name: str, value: Any, conf: float) -> bool:
        """這一筆贏得這個屬性就寫進邊、回 True（呼叫端據此記下是哪一筆贏的）。"""
        if value is None:
            return False
        if conf <= attr_conf[key].get(name, -1.0):
            return False
        attr_conf[key][name] = conf
        setattr(edge, name, value)
        return True

    for row in rows:
        src, rel, dst = row.get("src"), row.get("relation"), row.get("dst")
        if not (is_entity_id(src) and is_entity_id(dst)):
            continue
        key = (str(src), str(rel), str(dst))
        attrs = parse_attributes(row.get("attributes"))
        conf = float(row.get("confidence") or 0.0)
        edge = grouped.get(key)
        if edge is None:
            edge = CanonicalEdge(src=str(src), relation=str(rel), dst=str(dst))
            grouped[key] = edge
        edge.documents += 1
        edge.confidence = max(edge.confidence, conf)
        doc_id = row.get("source_doc_id")
        if doc_id:
            # ⚠ 同一份文件可能被多條 assertion 引用；後者的 published_at 若為 None
            # 不得覆蓋已知值（`or` 而不是直接指派）。
            edge.source_docs[str(doc_id)] = (
                row.get("published_at") or edge.source_docs.get(str(doc_id)))
        if row.get("origin"):
            edge.origins.add(str(row["origin"]))
            if str(row.get("source_type") or "") == "filing":
                edge.filing_origins.add(str(row["origin"]))
            edge.origin_assertions.setdefault(str(row["origin"]), []).append(
                (row.get("assertion_id") or None, doc_id or None, row.get("origin_linkage") or None))

        sub = attrs.get("substitutability")
        if _take(key, edge, "substitutability",
                 int(sub) if isinstance(sub, (int, float)) and not isinstance(sub, bool) else None,
                 conf):
            edge.sub_assertion_id = str(row["assertion_id"]) if row.get("assertion_id") else None
        ramp = attrs.get("ramp_execution")
        _take(key, edge, "ramp_execution",
              int(ramp) if isinstance(ramp, (int, float)) and not isinstance(ramp, bool) else None,
              conf)
        lt = attrs.get("structural_lead_time_weeks")
        _take(key, edge, "lead_time_weeks",
              int(lt) if isinstance(lt, (int, float)) and not isinstance(lt, bool) else None,
              conf)
        _take(key, edge, "qualification_status", attrs.get("qualification_status"), conf)
        if attrs.get("sole_source") is not None:
            _take(key, edge, "sole_source", bool(attrs["sole_source"]), conf)
    return grouped


def build_upward_index(edges: Iterable[CanonicalEdge]) -> dict[str, set[str]]:
    """node → 誰需要它（需求方向）。

    向上與向下是不同邊型，這個不對稱是刻意的、不需要改 schema：
    `A depends_on B` ⇒ B 被 A 需要；`A is_component_of B` ⇒ A 被 B 需要；
    `A enables B` ⇒ A 被 B 需要。向上的邊沒有也不該有 `substitutability`。

    ⚠ 「src 需要 dst」那一族的**唯一登記處是 `DEPENDENCY_RELATIONS`**，不要在這裡
    直接寫 relation 名字——`query/structure.py` 的需求側判定讀的是同一份，
    2026-09-18 之前兩邊各硬編一份 `depends_on`，於是 `constrained_by` 在兩處同時缺席（L16）。
    """
    upward: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        if e.relation in DEPENDENCY_RELATIONS:
            # A depends_on／constrained_by B ⇒ B 被 A 需要
            upward[e.dst].add(e.src)
        elif e.relation == "supplies_to":
            # A supplies_to B ⇒ A 被 B 需要。
            # ⚠ 這條首版漏了，於是任何「瓶頸目標是一家公司」的列都走不到需求錨點
            # （實測 co:axt supplies_to co:coherent 顯示「無錨點」，但 Coherent 供 CPO、
            # CPO 供 ai_switch，鏈其實是通的）。`supplies_to` 同時出現在向下（帶
            # substitutability）與向上（需求傳遞）兩個索引裡是正確的——它本來就是
            # 一條有方向的供需邊，兩邊問的問題不同。
            upward[e.src].add(e.dst)
        elif e.relation in UPSTREAM_RELATIONS:
            # A is_component_of B ⇒ A 被 B 需要
            upward[e.src].add(e.dst)
        elif e.relation in DEMAND_PULL_RELATIONS:
            # A enables B ⇒ **B 被 A 需要**（抽取定義逐字：A's adoption drives demand for B）
            upward[e.dst].add(e.src)
    return upward


def demand_chain(
    target: str,
    upward: Mapping[str, set[str]],
    anchors: Iterable[str] | None = None,
    max_depth: int = 8,
) -> list[str] | None:
    """從 `target` 往上走到**明確登記的需求錨點**，回傳最短的一條鏈；走不到回 None。

    ⚠ **`target` 傳誰，決定了這條鏈在回答哪個問題。** `structure_table` 一律傳**公司**
    （`edge.src`），所以輸出的 `demand_anchor` 是「這家公司的產出有沒有人在花錢買」，
    **同一家公司的每一列都相同**；傳瓶頸節點（`edge.dst`）問的是另一件事。
    2026-09-18 實測過換成 dst 的後果：accepted 列有一批會失去錨（圖裡沒有人記錄過誰需要那些節點），
    排序因此變差。這個欄位的名字容易被讀成後者——讀法已寫進 `render_markdown` 的表後註。

    用 BFS 取最短路徑而非 DFS 取最長：最短路徑是「這個瓶頸離錢最近有幾層」，
    可解釋；最長路徑在有環的圖上只是亂走（首版的教訓，見 DEMAND_ANCHORS 註解）。

    **走不到就是走不到，回 None。** 依使用者判準，連不到有人花錢的地方的瓶頸，
    不該被當成投資標的看待——這裡不得用「最接近的節點」充數。
    """
    # ⚠ 不用預設參數綁定（`anchors=DEMAND_ANCHORS`）：那會在函式定義時就凍結當時的值，
    # config 之後怎麼改都讀不到。同一個陷阱在 event_watch.load_watches 也踩過。
    anchor_set = set(anchors) if anchors is not None else set(load_demand_anchors())
    if target in anchor_set:
        return [target]
    queue: list[tuple[str, list[str]]] = [(target, [target])]
    visited = {target}
    while queue:
        node, path = queue.pop(0)
        if len(path) > max_depth:
            continue
        for parent in sorted(upward.get(node, ())):
            if parent in visited:
                continue
            visited.add(parent)
            new_path = path + [parent]
            if parent in anchor_set:
                return list(reversed(new_path))
            queue.append((parent, new_path))
    return None


#: 被門檻濾掉的理由（封閉字彙）。**「未填」與「填了但低於門檻」刻意分開**——
#: 前者是我們還沒研究，後者是研究過而答案是否定的，兩者的下一步完全不同：
#: 一個要去補研究，一個要去問「那這檔還值得看嗎、憑什麼」。壓成一句就同形了（L12）。
#: 結構表的**母體**是「公司→向下」的 canonical edge。不在母體裡的邊要報得出為什麼（INV-3：
#: 每個 filter 都能報 input／accepted／filtered／reasons）。
#: ⚠ 2026-09-23（Step 0b.3）之前這裡是門檻的兩種理由（`substitutability_unfilled`／`_below_threshold`）；
#: 門檻退役後那兩種邊**都在表上**，剩下的排除只剩母體定義本身——而它們先前是靜默 `continue`。
EXCLUSION_REASONS: Mapping[str, str] = {
    "not_company_source": "邊的 src 不是公司（`co:*`）——技術層／材料層之間的邊不是「誰卡在哪」的列",
    "not_downstream_relation": "relation 不是向下（depends_on／supplies_to／constrained_by）——上游與需求拉動邊另有用途",
}


#: 「**瓶頸節點自己**走不到需求錨」的成因（封閉字彙）。
#:
#: ⚠ **這不是 `EXCLUSION_REASONS`，兩者問的不是同一件事。** 後者講的是
#: 「這條邊為什麼不在母體裡」；本字彙講的是「這個**節點**接不接得到有人花錢的地方」。
#: 列上的 `demand_anchor` 是從**公司**側走的（見 `demand_chain` 的 docstring），
#: 所以一條列可以同時「公司側有錨」而「瓶頸節點側沒有錨」——後者是診斷，不改列上任何一格。
#:
#: ⚠ **三種成因刻意不壓成一句「走不到錨」**（ROADMAP Phase 4 驗收條件逐字要求）：
#: 它們的下一步完全不同——一個要先拆封閉字彙、一個是研究、一個要等前兩個解完。
#: 壓成一句就同形了（L12），而同形的那一刻，「去補研究」與「去改程式」變成同一格。
#:
#: ⚠ **已經修掉的成因刻意不留空格子**——修掉之後它們**結構上不可能再被觀測到**
#: （那些節點現在走得到上游，根本不進母體），留一個恆為 0 的格子就是 L14-4 的
#: 「不會滅＝那是牆不是閘門」。目前已退場兩種，各由一條方向測試守著迴歸：
#:   ①`constrained_by` 沒有被走訪（2026-09-18 修）→
#:     `tests/test_structure_table.py::test_constrained_by_carries_demand_upward_in_the_depends_on_direction`
#:   ②`enables` 走訪方向與抽取定義相反（2026-09-18 資料歸位＋程式歸位後修）→
#:     `::test_enables_carries_demand_from_the_adopter_to_what_it_pulls_in`
#:     ⚠ 它退場的前提是**資料先改對**：29 條誤植的邊由 pq2 [607]／[608]／[609] 逐條重判改正，
#:     之後才翻走訪方向。只翻程式不改資料，實測 `no_demand_edge` 會由 51 打到 67。
ANCHOR_GAP_CAUSES: Mapping[str, str] = {
    "no_demand_edge": (
        "圖裡**根本沒有人記錄過「誰需要它」**——沒有任何一條需求方邊指向它。"
        "**這是真研究缺口**（pq2 [606]：找一手文件回答「誰在買它、為了做什麼」）"
    ),
    "upstream_dead_end": (
        "**有**人需要它，但那些人自己也走不到需求錨——鏈斷在上游而不是斷在它身上。"
        "前兩種解掉之後這一種會自己縮小，所以它是結果不是原因"
    ),
}


def classify_anchor_gaps(
    edges: Iterable[CanonicalEdge],
    upward: Mapping[str, set[str]],
    anchors: Iterable[str] | None = None,
) -> dict[str, Any]:
    """哪些**瓶頸節點**自己走不到需求錨，以及各是哪一種成因。

    ⚠ **純診斷，不參與排序、不產生尺寸、不改 `rows` 一個字。** 加這一段的理由是
    ROADMAP Phase 4 的驗收條件逐字寫著「四種成因要分得開（不得壓成一句走不到錨）」，
    而在此之前**沒有任何地方數過它們**——`demand_anchor` 只在表格裡呈現成一格「🔴 無」，
    那是呈現不是計數（L14：會自己出現的常駐計數器，不是要人讀的段落）。
    現況數字不寫在這裡（會腐壞）：跑 `python -m query.bottleneck` 看那一段。

    ⚠ **走訪一律消費既有的 `build_upward_index`／`demand_chain`／`DEPENDENCY_RELATIONS`**，
    本函式不自己判「誰需要誰」——否則就是 L16 說的「每個消費端重造一份，而重造品會
    立刻開始偏離」。本函式唯一自己看的是 `enables` 的**存在**（不是方向）。
    """
    edges = list(edges)
    anchor_set = set(anchors) if anchors is not None else set(load_demand_anchors())

    # 母體＝所有出現在「公司→向下」邊裡的瓶頸節點，也就是結構表真的問過的那些。
    population = sorted({e.dst for e in edges if e.relation in DOWNSTREAM_RELATIONS})

    by_cause: dict[str, list[dict[str, Any]]] = {k: [] for k in ANCHOR_GAP_CAUSES}
    for node in population:
        if demand_chain(node, upward, anchors=anchor_set):
            continue
        parents = sorted(upward.get(node) or ())
        cause, detail = ("upstream_dead_end", parents) if parents else ("no_demand_edge", [])
        by_cause[cause].append({"node": node, "blocked_by": detail})

    return {
        "population": len(population),
        "without_anchor": sum(len(v) for v in by_cause.values()),
        "counts": {k: len(v) for k, v in by_cause.items()},
        # ⚠ **前綴分佈是刻意報出來的，不是裝飾。** `no_demand_edge` 裡有一批 `co:` 節點是
        # **需求終點**（`co:apple`／`co:google`／`co:meta`——有人供應它們，而「誰需要 Apple」
        # 不會有人去記，因為它賣給消費者，不在錨的字彙裡），對它們做研究永遠不會有答案；
        # 另一批 `co:` 卻是真缺口（`co:ayar_labs`／`co:lumilens` 這種小供應商）。
        # **今天沒有任何 SSOT 分得出這兩種**，所以這裡不發明一個過濾器去猜——在沒有事實
        # 支撐的地方泛化，得到的是會誤報的分類（L17-4）。報出分佈讓讀的人自己看見它。
        "by_id_prefix": {
            cause: dict(
                sorted(Counter(n["node"].split(":")[0] for n in v).items())
            )
            for cause, v in by_cause.items()
        },
        "nodes": by_cause,
        "cause_labels": dict(ANCHOR_GAP_CAUSES),
        "this_is_not": (
            "這**不是**列上的欄位，也不是排除理由。列上的 `demand_anchor` 是從**公司**側走的，"
            "問「這家公司的產出有沒有人在花錢買」；本段問的是「這個**瓶頸節點**接不接得到錢」。"
            "兩者是不同問題，2026-09-18 實測過把列上的錨改成後者會讓多數列失去錨。"
        ),
    }


def _table_row(edge, registry, upward, *, without_sub_language: list[str] | None = None,
               sub_language_in_quote: bool | None = None) -> dict[str, Any]:
    """一條邊的結構事實。**每一格都是圖上的值或由圖上的值走出來的路徑**，沒有任何評分。

    `without_sub_language`：這條邊上帶 sub、但引文不含可替代性語言的 assertion id（Phase 4 Step 4.4b；
    `query.sub_language` 是唯一 owner）。None＝這次沒有核對（呼叫端沒給旗標），**不是**「全部都有」。
    `sub_language_in_quote`：**贏得這一列 sub 值的那筆**引文撐不撐得住（Phase 6 Step 6.5；
    `query.sub_language.canonical_sub_language`）。None＝沒有 sub 或沒核對（看結果的 `sub_language` 是不是 None 分得出）。
    """
    # ⚠ 從**公司**往上走，不是從瓶頸節點。這一列問的是「這家公司的產出有沒有人
    # 在花錢買」，不是「這個材料有沒有人要」。首版從 `edge.dst` 走，於是
    # co:lumentum 那列的鏈路繞經 co:coherent——對 `mat:inp_substrate` 而言正確，
    # 但那不是這一列在問的問題。
    chain = demand_chain(edge.src, upward)
    return {
        "company_id": edge.src,
        "ticker": registry.research_ticker(edge.src),
        "relation": edge.relation,
        "bottleneck": edge.dst,
        # 未填是 None（未填≠否），不補 0、不補門檻。
        "substitutability": edge.substitutability,
        # ⚠ 三態：True／False／None。None＝圖上沒有任何文件對這條邊的 sole_source
        # 發言過（未填），**不是** False。2026-09-05 之前這裡是 `bool(...)`，把
        # 「不知道」壓成「否」，下游（read model、Q1 佐證）就再也分不出兩者。
        "sole_source": edge.sole_source,
        "qualification_status": edge.qualification_status,
        "ramp_execution": edge.ramp_execution,
        "lead_time_weeks": edge.lead_time_weeks,
        "evidence": edge.evidence,
        "confidence": edge.confidence,
        "documents": edge.documents,
        # provenance：`documents` 只是計數（注意力指標），`sources` 才讓下游列得出
        # **是哪幾份**。`published_at` 取所有已知引用日期中最早的一個——它回答
        # 「這條邊最早什麼時候說得出來」。
        "sources": sorted(edge.source_docs),
        "source_dates": {k: (str(v) if v else None)
                         for k, v in sorted(edge.source_docs.items())},
        "published_at": min(
            (str(v) for v in edge.source_docs.values() if v), default=None),
        "chain": chain,
        "demand_anchor": chain[0] if chain else None,
        "demand_hops": (len(chain) - 1) if chain else None,
        # 列表不是布林（plan §5 b）：讀的人要能指回是哪幾筆 assertion 的引文沒在談可替代性。
        "assertions_without_sub_language": without_sub_language,
        # 這一列印的 sub 是哪一筆給的、那一筆的引文撐不撐得住（只印、不改 sub、不改順序）。
        "sub_assertion_id": edge.sub_assertion_id,
        "sub_language_in_quote": sub_language_in_quote,
    }


def structure_table(
    rows: Iterable[Mapping[str, Any]],
    registry,
    *,
    quotes_by_assertion: Mapping[str, Iterable[str]],
    sub_language_flags: Mapping[str, bool] | None = None,
    sub_language_label: str | None = None,
) -> dict[str, Any]:
    """輸出「公司 × 向下邊」的結構表，附鏈路、需求錨點與證據等級。**不排序、不設門檻、不給首選。**

    ⚠ 2026-09-23（Step 0b.3）：這裡原本是 `rank_bottlenecks()`——同一批列、外加排序鍵、
    `min_substitutability` 門檻、兩份序與 top-N。那些整組退役；列上的每一格與 `anchor_gaps`／
    `coverage` 一字未動。名稱不留 alias：誰還在 import `rank_bottlenecks` 就該在這裡紅。

    列的順序是 `(company_id, relation, bottleneck)` 字典序——**索引，不是名次**。消費端不得把
    第一列讀成「最值得看」；要比較請看各自的格子。

    `sub_language_flags`（Phase 4 Step 4.4b）：`query.sub_language.sub_language_flags` 的輸出（assertion id →
    引文含不含可替代性語言）。給了，每列多一格 `assertions_without_sub_language`（id 列表）、結果多一段
    `sub_language` 總數；沒給就是 None（沒核對）。**只印、不放閘**：不改任何一格、不改收斂、不改順序。
    `quotes_by_assertion`（**必填**，Phase 6 Step 6.4）：`query.sub_language.fetch_all_quotes` 的輸出——證據等級的
    逐來源具名核對讀它（`classify_evidence`）。
    給了 `sub_language_flags`，每列另多一格 `sub_language_in_quote`：**贏得這一列 sub 值的那筆**引文撐不撐得住
    （Phase 6 Step 6.5；旗標跟著值走，不挑同一條邊上另一筆好看的）。
    """
    from query.sub_language import canonical_sub_language

    rows = list(rows)
    canonical = collapse_assertions(rows)
    without_by_edge: dict[tuple, list[str]] | None = None
    if sub_language_flags is not None:
        without_by_edge = defaultdict(list)
        for row in rows:
            aid = str(row.get("assertion_id") or "")
            if aid and sub_language_flags.get(aid) is False:
                without_by_edge[(str(row.get("src")), str(row.get("relation")), str(row.get("dst")))].append(aid)
    edges = list(canonical.values())
    shared = shared_name_forms(registry)
    for edge in edges:
        edge.evidence = classify_evidence(
            edge.src, edge.origins, registry, filing_origins=edge.filing_origins,
            quotes_by_assertion=quotes_by_assertion, origin_assertions=edge.origin_assertions, shared=shared,
        )

    upward = build_upward_index(edges)
    table: list[dict[str, Any]] = []
    #: 不在母體裡的邊**逐條帶理由**（INV-3）。門檻退役之前這兩種是靜默 `continue`；
    #: 現在母體定義本身就是唯一的 filter，所以它也要報 input／accepted／excluded／reasons。
    excluded: list[dict[str, Any]] = []
    for edge in edges:
        if edge.relation not in DOWNSTREAM_RELATIONS:
            excluded.append({"company_id": edge.src, "relation": edge.relation,
                             "bottleneck": edge.dst, "reasons": ["not_downstream_relation"]})
            continue
        if not edge.src.startswith("co:"):
            excluded.append({"company_id": edge.src, "relation": edge.relation,
                             "bottleneck": edge.dst, "reasons": ["not_company_source"]})
            continue
        table.append(_table_row(
            edge, registry, upward,
            without_sub_language=(sorted(without_by_edge.get((edge.src, edge.relation, edge.dst), ()))
                                  if without_by_edge is not None else None),
            sub_language_in_quote=canonical_sub_language(edge, sub_language_flags)))

    # 索引序：公司、關係、節點。**不是排序鍵**——沒有任何一格參與。
    table.sort(key=lambda r: (str(r["company_id"]), str(r["relation"]), str(r["bottleneck"])))

    with_sub = [e for e in edges if e.substitutability is not None]
    reason_counts: dict[str, int] = {}
    for row in excluded:
        for reason in row["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "rows": table,
        # INV-3：母體定義是一個 filter，所以它必須報得出 input／accepted／excluded／reasons。
        "population": {
            "input": len(table) + len(excluded),
            "accepted": len(table),
            "excluded": len(excluded),
            "rule": "母體＝src 為公司（co:*）且 relation 為向下（depends_on／supplies_to／constrained_by）的 canonical edge。"
                    "沒有門檻：substitutability 未填或很低的邊都在表上，各自帶著自己的值。",
            "reasons": reason_counts,
            "reason_labels": dict(EXCLUSION_REASONS),
            "excluded_rows": excluded,
        },
        # ⚠ **診斷輸出，不是列上的欄位**：它回答的是 ROADMAP Phase 4 ②③④「瓶頸節點走不到錨」
        # 的成因分佈，母體與表的母體相同但問的是另一個方向（見 `this_is_not`）。
        "anchor_gaps": classify_anchor_gaps(edges, upward),
        "coverage": {
            "assertions": len(rows),
            "canonical_edges": len(canonical),
            "edges_with_substitutability": len(with_sub),
            "substitutability_coverage": (
                len(with_sub) / len(canonical) if canonical else 0.0
            ),
            "edges_with_lead_time": sum(
                1 for e in edges if e.lead_time_weeks is not None
            ),
            "self_reported_share": (
                sum(1 for e in with_sub if e.evidence == "self_reported") / len(with_sub)
                if with_sub
                else 0.0
            ),
            "duplicate_collapse": len(rows) - len(canonical),
        },
        # sub 引文核對的總數（Phase 4 Step 4.4b）。None＝這次沒核對——與「核對了、0 筆缺」不得同形（INV-3）。
        "sub_language": (None if sub_language_flags is None else {
            "language": sub_language_label,
            "checked": len(sub_language_flags),
            "without": sum(1 for v in sub_language_flags.values() if v is False),
            "note": "帶 sub 的 assertion 裡，引文沒有任何一個字在談可替代性／替代品認證／排他性的筆數——"
                    "量的是引文措辭，不是 sub 對不對；只印、不放閘（query/sub_language.py）。",
        }),
    }


def fetch_assertions(session) -> list[dict[str, Any]]:
    return session.run(
        """
        MATCH (e:EdgeAssertion)
        OPTIONAL MATCH (d:SourceDoc {id: e.source_doc_id})
        RETURN e.src_id AS src, e.relation AS relation, e.dst_id AS dst,
               e.attributes AS attributes, e.confidence AS confidence,
               d.origin_entity AS origin, d.source_type AS source_type,
               d.origin_linkage AS origin_linkage,
               e.source_doc_id AS source_doc_id, d.published_at AS published_at,
               e.id AS assertion_id
        """
    ).data()


# ---------------------------------------------------------------------------
# Point-in-time：as-of 投影（Phase 6）
# ---------------------------------------------------------------------------

def latest_possible_date(text: Any) -> date | None:
    """把 `published_at` 字串讀成「**它最晚可能是哪一天**」。

    ⚠ 圖上的 `published_at` 有兩種精度：完整日期（`2026-06-02`）與只有年月
    （`2025-12`，實測 2 筆）。字串比大小會讓 `2025-12` 在 `2025-12-01` 就可見，
    而它其實可能是 12/31 發表的——那是 lookahead。同一個欄位承載兩種精度是
    L12 的形狀，修法不是排除它，是**讓兩邊各自有正確的規則**：年月精度一律
    取當月最後一天（保守），完整日期照用。

    讀不懂就回 `None`，由呼叫端當成「未定日」排除並計數，不猜。
    """
    if not text:
        return None
    raw = str(text).strip()
    if len(raw) >= 10:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{4})-(\d{2})", raw)
    if not match:
        return None
    year, month = int(match[1]), int(match[2])
    if not 1 <= month <= 12:
        return None
    last = calendar.monthrange(year, month)[1]
    return date(year, month, last)


@dataclass(frozen=True)
class AsOfProjection:
    """`as_of` 那天看得到的 assertion，**以及被排除的計數**。

    計數不是裝飾：沒有它，「as-of 之後證據變少」與「本來就沒有證據」在下游同形
    （INV-3 no silent drop／L13）。
    """

    as_of: date
    rows: tuple[Mapping[str, Any], ...]
    excluded_future: int = 0
    excluded_undated: int = 0
    dated_total: int = 0

    @property
    def input_count(self) -> int:
        return len(self.rows) + self.excluded_future + self.excluded_undated

    def reasons(self) -> dict[str, int]:
        return {"published_after_as_of": self.excluded_future,
                "undated": self.excluded_undated}


def project_assertions_as_of(
    rows: Iterable[Mapping[str, Any]], as_of: date
) -> AsOfProjection:
    """只留下「`as_of` 當天已經有人發表過」的 assertion。

    **未定日一律排除並計數**——「我找不到日期」不等於「它在 T 之前」（L11-5）。
    把未定日當成可用等於讓回測看到未來，而那是回測最沒有價值的失敗方式：
    它會給出一個好看且完全不可信的結果。
    """
    kept: list[Mapping[str, Any]] = []
    future = undated = dated = 0
    for row in rows:
        published = latest_possible_date(row.get("published_at"))
        if published is None:
            undated += 1
            continue
        dated += 1
        if published > as_of:
            future += 1
            continue
        kept.append(row)
    return AsOfProjection(as_of=as_of, rows=tuple(kept), excluded_future=future,
                          excluded_undated=undated, dated_total=dated)


# ---------------------------------------------------------------------------
# 呈現用的固定文字與判準：**跟著資料走**（L16）。
# markdown（本檔）與 APP artifact（`webapp/materialize.py`）都從這裡拿，不各自抄一份——
# 抄第二份的那天起，後改的那份就不會回頭更新前一份（AGENTS「清單會腐壞，判準不會」）。
# ---------------------------------------------------------------------------

STRUCTURE_TABLE_TITLE = "結構表（已研究過的公司逐邊的結構事實；不排序、不設門檻、不給首選）"

STRUCTURE_TABLE_NOTE = (
    "⚠ **本表不含「瓶頸業務占該公司多少」**。同為 `sub=5`，大型多角化公司的"
    "單一瓶頸邊對其整體營收影響可能很小（研究它接近研究 beta），小型專業廠則"
    "接近純曝險。判斷投資意義時必須另看市值、營收結構與分析師覆蓋度——"
    "那些資料在 Engine C，不在本表內。"
)

NO_ANCHOR_CHAIN_NOTE = (
    "🔴 **走不到任何已登記的需求錨點**——可能是鏈路真的斷了，"
    "也可能是 `DEMAND_ANCHORS` 還沒登記到這個領域。不得當作已錨定使用。"
)

NO_ANCHOR_READING = (
    "🔴 **無需求錨列的讀法**：這些邊「難替代」但「不知服務誰」。三種可能："
    "①需求端在圖裡但缺中間的邊 → 補邊；②它服務的市場還沒登記成錨 → "
    "在 `config/sector_anchors.json` 補錨（**可能要開新產業群**）；"
    "③真的沒有終端需求 → 不是投資標的。**不得預設是第③種**。"
)

#: 表的順序是什麼、不是什麼——供消費端原樣呈現，讓「第一列」永遠不被讀成「第一名」。
ORDER_NOTE = "列依 (company_id, relation, bottleneck) 字典序——**索引，不是名次**；沒有任何一格參與順序。"


def known_limitations(coverage: Mapping[str, Any]) -> list[str]:
    """結構表的三條已知限制，**隨輸出常駐**（模組 docstring 的要求）。任何消費端都從這裡拿。"""
    return [
        f"覆蓋率 {coverage['substitutability_coverage']:.0%}——表必然偏向已被抽取過的邊，"
        "沒填的邊在表上是「未填」，不是「不是瓶頸」。",
        "**本表不含 lead time**（換掉一個供應商要多久）。「難替代」與「換掉要多久」"
        "是兩件事：第二供應商若半年可合格，sub=5 也很脆。",
        "`documents` 是注意力指標，**不是結構事實**——它量的是我們讀了幾份文件。",
    ]


def render_markdown(result: Mapping[str, Any]) -> str:
    cov = result["coverage"]
    out = [f"# {STRUCTURE_TABLE_TITLE}\n"]
    out.append(
        f"- EdgeAssertion {cov['assertions']} → canonical edge {cov['canonical_edges']}"
        f"（去重收斂 {cov['duplicate_collapse']} 筆）"
    )
    out.append(
        f"- `substitutability` 覆蓋 {cov['edges_with_substitutability']}"
        f"/{cov['canonical_edges']}（{cov['substitutability_coverage']:.0%}）"
        f"｜其中僅供應商自報 {cov['self_reported_share']:.0%}"
    )
    out.append(f"- `structural_lead_time_weeks` 有值：{cov['edges_with_lead_time']} 條")
    sub_language = result.get("sub_language")
    out.append(
        "- sub 引文不含可替代性語言：未核對（沒有給旗標）" if not sub_language else
        f"- sub 引文不含可替代性語言：{sub_language['without']}／{sub_language['checked']} 筆帶 sub 的 assertion"
        f"（字表 {sub_language['language']}；只印、不放閘——量的是措辭，不是 sub 對不對）"
    )
    out.append(
        "\n🔴 **已知限制，解讀前必讀：**\n"
        + "".join(f"{i}. {text}\n" for i, text in enumerate(known_limitations(cov), 1))
    )
    if not result["rows"]:
        out.append("\n（母體為空：沒有任何公司→向下的邊）")
        out.extend(render_population_report(result))
        return "\n".join(out)

    out.append(f"\n> {ORDER_NOTE}\n")
    out.append("| 標的 | 卡在哪 | 替代難度 | 證據 | 合格狀態 | 文件 | 公司側需求錨 |")
    out.append("|---|---|---|---|---|---|---|")
    for r in result["rows"]:
        ticker = r["ticker"] or "—"
        sole = "｜sole_source" if r["sole_source"] else ""
        sub = "未填" if r["substitutability"] is None else f"{r['substitutability']}/5"
        # 這個值本身（贏得值的那一筆）撐不撐得住——Phase 6 Step 6.5；跟逐筆清單分開說（一個是值、一個是全部帶 sub 的筆數）
        if r.get("sub_language_in_quote") is False:
            sub += "｜⚠這個值的引文沒談可替代性"
        if r.get("assertions_without_sub_language"):
            sub += f"｜引文無可替代性語言 {len(r['assertions_without_sub_language'])} 筆"
        out.append(
            f"| {r['company_id']}（{ticker}） | {r['relation']} → `{r['bottleneck']}` "
            f"| {sub}{sole} | {EVIDENCE_LABEL[r['evidence']]} "
            f"| {r['qualification_status'] or '—'} | {r['documents']} "
            f"| {r['demand_anchor'] or '🔴 無'} |"
        )

    # ⚠ 這一欄的讀法必須跟著表走，否則每個讀者都會重造一份自己的理解（L16 的形狀）。
    out.append(
        "\n> **「公司側需求錨」是從標的公司往上走最短路徑找到的，不是從「卡在哪」那個節點走。**"
        "所以**同一家公司的每一列都是同一個錨**——它回答「這家公司的產出有沒有人在花錢買」，"
        "不回答「這條邊的瓶頸節點接不接得到錢」。"
        "\n> ⚠ 改成從瓶頸節點走**已經量過是錯的**（2026-09-18）：多數列（`tech:isolator`、"
        "`tech:eml`、`tech:ocs` 等）會**直接失去錨**，因為圖裡沒有人記錄過「誰需要它們」。"
        "**那個「瓶頸節點走不到錨」是研究缺口訊號**（同 ROADMAP Phase 4 成因③「真的沒有需求方邊」），"
        "不是一個該加進列上的欄位。"
    )
    if any(not r["demand_anchor"] for r in result["rows"]):
        out.append("\n> " + NO_ANCHOR_READING)
    out.append("\n" + STRUCTURE_TABLE_NOTE)
    flagged = [r for r in result["rows"] if r.get("assertions_without_sub_language")]
    if flagged:
        out.append("\n## sub 引文不含可替代性語言的 assertion（逐條；只印、不放閘）\n")
        for r in flagged:
            out.append(f"- {r['company_id']} {r['relation']} `{r['bottleneck']}`（sub {r['substitutability']}）："
                       + "、".join(f"`{aid}`" for aid in r["assertions_without_sub_language"]))

    # ⚠ 條件是 `population` 不是 `without_anchor`：用後者會讓「**全部都走得到錨**」與
    # 「**這段根本沒跑**」在輸出上同形，而那正是 L13-2 說的「成功與失敗在同一個訊號上」。
    # 母體為 0 才是真的沒東西可算（圖空或查詢失敗），那時才不印。
    gaps = result.get("anchor_gaps") or {}
    if gaps.get("population"):
        out.append(
            f"\n## 瓶頸節點走不到需求錨：{gaps['without_anchor']}／{gaps['population']} 個"
            "（診斷，**不改上面任何一格**）\n"
        )
        out.append(f"> {gaps['this_is_not']}")
    if gaps.get("population") and not gaps.get("without_anchor"):
        out.append(
            "\n✅ **母體裡每一個瓶頸節點都走得到需求錨。**"
            "（這一行會出現，就代表這個檢查真的跑過了——不是它消失了）"
        )
    elif gaps.get("population"):
        out.append(
            "\n| 成因 | 幾個 | 節點型別 | 下一步屬於哪一類 | 例 |")
        out.append("|---|---|---|---|---|")
        _next_step = {
            "no_demand_edge": "研究（pq2 [606]）",
            "upstream_dead_end": "等 `no_demand_edge` 解完（結果不是原因）",
        }
        for cause, count in sorted(
            gaps.get("counts", {}).items(), key=lambda kv: -kv[1]
        ):
            if not count:
                continue
            sample = [n["node"] for n in gaps["nodes"][cause][:3]]
            prefixes = gaps.get("by_id_prefix", {}).get(cause, {})
            out.append(
                f"| `{cause}` | **{count}** "
                f"| {'／'.join(f'{k} {v}' for k, v in prefixes.items()) or '—'} "
                f"| {_next_step.get(cause, '—')} "
                f"| {'、'.join(f'`{s}`' for s in sample)}… |"
            )
        out.append(
            "\n> ⚠ **節點型別要看一眼**：`no_demand_edge` 裡的 `co:` 節點有兩種，"
            "而**今天沒有任何登記處分得出它們**——`co:apple`／`co:google`／`co:meta` 是**需求終點**"
            "（有人供應它們，但「誰需要 Apple」不會有人記，它賣給消費者、不在錨的字彙裡），"
            "對它們做研究永遠不會有答案；`co:ayar_labs`／`co:lumilens` 這種小供應商才是真缺口。"
            "**這裡刻意不猜**——在沒有事實支撐的地方泛化會得到會誤報的分類（L17-4）。"
        )
        for cause, count in sorted(
            gaps.get("counts", {}).items(), key=lambda kv: -kv[1]
        ):
            if count:
                out.append(f"> **`{cause}`** — {gaps['cause_labels'][cause]}")

    out.extend(render_population_report(result))

    out.append("\n## 需求鏈（誰在花錢 → 這家公司）\n")
    for r in result["rows"]:
        out.append(
            f"- **{r['company_id']}** {r['relation']} `{r['bottleneck']}`"
        )
        if r["chain"]:
            out.append(f"   {' → '.join(r['chain'])}　（距需求端 {r['demand_hops']} 跳）")
        else:
            out.append("   " + NO_ANCHOR_CHAIN_NOTE)
    return "\n".join(out)


def render_population_report(result: Mapping[str, Any]) -> list[str]:
    """母體定義排除了誰——**INV-3 的可見面**。

    ⚠ 沒有這一段的話，`structure_table` 的 `population.excluded_rows` 就是一個沒有 consumer 的
    producer（INV-4）。它存在的意義不是「多印幾行」，是讓「這條邊不在表上」有一個查得到的理由。
    """
    report = result.get("population")
    if not report:
        return []
    out = [
        "\n## 母體定義排除了誰（INV-3）\n",
        f"`input {report['input']}｜accepted {report['accepted']}｜excluded {report['excluded']}`"
        f"——{report['rule']}\n",
    ]
    labels = report.get("reason_labels") or {}
    for reason, count in sorted(report.get("reasons", {}).items(), key=lambda kv: -kv[1]):
        out.append(f"- **{reason}：{count} 條**——{labels.get(reason, '')}")
    out.append(
        "\n⚠ **本段沒有門檻**：2026-09-23 之前這裡印的是 `substitutability ≥ 4` 濾掉了誰；"
        "門檻隨排序退役，未填與低分的邊現在都在上表裡、各自帶著自己的值。"
    )
    return out


def render_what_if(
    baseline: Mapping[str, Any], overlaid: Mapping[str, Any],
    hypothesis_rows: list,
) -> str:
    """what-if 結構 diff：**只比表上的事實**（新邊、錨可達性、替代難度），不比名次。

    「若為真」問的是陳述的真值，不是證據狀態——假設永不參與 evidence 分級（硬邊界）。
    ⚠ 2026-09-23（Step 0b.3）：原本比的是純結構排序的名次；排序退役後，「若為真結構會變嗎」
    改問三件事：多了哪些列、哪些公司從走不到錨變成走得到（或反過來）、哪些邊的 sub 變了。
    輸出必標「若為真」。
    """

    def rows_by_key(result: Mapping[str, Any]) -> dict[tuple, Mapping[str, Any]]:
        return {(r["company_id"], r["relation"], r["bottleneck"]): r
                for r in (result.get("rows") or ())}

    before, after = rows_by_key(baseline), rows_by_key(overlaid)
    lines = [
        "# What-if 結構 diff（若為真——不是證據判斷，不進任何預設輸出）",
        "",
        f"疊加假設邊 {len(hypothesis_rows)} 條（origin 固定 `(hypothesis)`）。",
        "",
    ]
    changed: list[tuple[tuple, str]] = []
    for key, row in sorted(after.items()):
        prev = before.get(key)
        if prev is None:
            changed.append((key, "（新進結構表）"))
            continue
        notes: list[str] = []
        if (prev.get("demand_anchor") is None) != (row.get("demand_anchor") is None):
            notes.append("走不到錨 → 走得到" if row.get("demand_anchor") else "走得到錨 → 走不到")
        if prev.get("substitutability") != row.get("substitutability"):
            notes.append(f"sub {prev.get('substitutability')} → {row.get('substitutability')}")
        if notes:
            changed.append((key, "；".join(notes)))
    if not changed:
        lines.append("**結構表無變化**——若為真也不多一列、不改任何錨可達性；安心 park，不值得花力氣追平行證據。")
    else:
        lines.append("| 標的→瓶頸 | 若為真的變化 |")
        lines.append("|---|---|")
        for (company, _relation, bottleneck), delta in changed:
            lines.append(f"| {company} → `{bottleneck}` | {delta} |")
        lines.append("")
        lines.append("表有動＝值得投入平行驗證（B1 免費一手／B2 fact-check trigger）；入圖仍走原檔 admission。")
    return "\n".join(lines)


def main() -> int:
    import argparse
    import sys
    import warnings
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    warnings.filterwarnings("ignore")
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    from identity.registry import get_registry

    parser = argparse.ArgumentParser(description="結構表（逐邊的結構事實；不排序）")
    parser.add_argument(
        "--what-if", metavar="HYP_ID", nargs="*", default=None,
        help="疊加截圖假設層（engine_b/hypotheses.py）輸出結構表 diff；"
             "不帶 id＝全部 active 假設。永不影響預設輸出。",
    )
    # ⚠ 2026-09-23（Step 0b.3）：`--by-sector`（產業別分組 top-N）與 `--top-n` 隨排序退役。
    args = parser.parse_args()

    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("請設 NEO4J_PASSWORD", file=sys.stderr)
        return 2
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    from query.sub_language import fetch_all_quotes, get_language, sub_language_flags

    try:
        with driver.session() as session:
            # 邊與逐字在同一個唯讀 transaction（證據等級的逐來源具名核對要對同一份快照——Phase 6 Step 6.4）。
            rows, quotes = session.execute_read(lambda tx: (fetch_assertions(tx), fetch_all_quotes(tx)))
    finally:
        driver.close()
    language = get_language()
    result = structure_table(rows, get_registry(), quotes_by_assertion=quotes,
                             sub_language_flags=sub_language_flags(rows, quotes, language=language),
                             sub_language_label=language.label)
    if args.what_if is not None:
        from engine_b.hypotheses import load_store, overlay_assertions

        hyp_rows = overlay_assertions(load_store(), hypothesis_ids=args.what_if or None)
        if not hyp_rows:
            print("（沒有 active 假設可疊加；先用 python -m engine_b.hypotheses add 建立）")
            return 0
        overlaid = structure_table(list(rows) + hyp_rows, get_registry(), quotes_by_assertion=quotes)
        print(render_what_if(result, overlaid, hyp_rows))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
