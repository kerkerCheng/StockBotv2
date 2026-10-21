"""SourceDoc `origin_entity` 解析的唯一 owner（2026-10-01 Phase 4 Step 4.3）：公司／發布者／解析不到，三態。

為什麼要有它：`company_id_for_origin` 回 None 同時代表「真的第三方」與「沒解析出來的別名」（L12）。
2026-10-01 基準：needs_review 113 條邊裡，只有研究／政府／學術型 origin 45 條、只有媒體型 43 條——
研究機構自產的數字與媒體轉述的供應商新聞稿證據力相反，卻掛同一個標籤。`config/publishers.json`
把「已知是誰發的」登記起來；**未登記的仍是解析不到，不猜**。

順序：先名冊公司（`query.bottleneck.company_id_for_origin`），再發布者，否則解析不到——一個 origin
若解析得到公司，它就是那家公司自己的文件，不是發布者。發布者以 `_strip_annotation` 後的字串 casefold
整串比對（尾端括號註解是研究者寫給人看的脈絡，不是身分）；不做子字串、不做模糊比對（L17-4）。

消費端（同一個函式，不各寫一份——L16）：
- `query.bottleneck.classify_evidence`：邊的證據等級。
- `alpha.providers.structure_readings.verify_citations`：讀圖引用的 `independent` 核對。
- `query.structure.build_socket_view`：插槽的「客戶端或可解析第三方的原文」。
- `scripts/audit_sole_source_independence.py`：手動 L8 稽核。

**「這個 origin 對這條邊算不算外部印證」的唯一 owner 是 `corroboration`**（2026-10-03 Phase 6 Step 6.4；使用者定案
plan §0.1 #3、#4）：上面四個消費端、`query.layer_stats`、RA packet 全部問它。它在解析之上多問兩件事——
印證來源**自己的**引文有沒有逐字具名主詞（主詞是公司時）、發布者的那段引文是不是在轉述（`config/relay_language.json`）。
2026-10-03 落地時（6.0 凍結 250 條外部印證、6.3 的資料更正之後）：這條規則擋下 19 條——引文沒具名 13、名冊無名可比 4、
轉述句 2（baseline 報告 §18）；舊計數器只抓得到其中一部分，因為它認「這條邊任何一段引文具名」、連供應商自己的也算
（Sivers→CW DFB：撐它的是華星光年報，那段沒提 Sivers）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parent.parent
PUBLISHERS_PATH = ROOT / "config" / "publishers.json"
#: 轉述字表（版本化；形狀與比對規則同 `config/substitutability_language.json`，同一個 `load_language`）。
RELAY_LANGUAGE_PATH = ROOT / "config" / "relay_language.json"

#: 發布者類別 → 算不算外部印證。**封閉字彙，寫死在程式裡**：設定檔每一筆的 `corroborates` 必須等於這裡
#: （載入時核對），所以把一筆媒體改成 `corroborates: true` 會在載入時就失敗——**媒體不得整類升級**
#: （L11-3：多個二手都這樣說≠一手已證實）。媒體文要升級，那份 SourceDoc 必須宣告 `origin_linkage=independent`。
PUBLISHER_KINDS: Mapping[str, bool] = {
    "industry_research": True,
    "teardown_lab": True,
    "standards_body": True,
    "government_statistics": True,
    "academic": True,
    "media": False,
}

#: `source_doc.origin_linkage` 的兩個值（`schema/vocab.json`；Step 4.2c）。缺＝None＝沒宣告。
INDEPENDENT = "independent"
SAME_ORIGIN = "same_origin"

#: 三態（封閉）。
RESOLUTION_KINDS = ("company", "publisher", "unresolved")

#: 主詞是**需求方**的關係（2026-10-21 批次二 E9；failure log #11）：origin＝主詞時說話的是買方——「我靠它、繞不過」
#: 是需求側的一手，不是供應商自誇。只拆標籤、rank 照舊（`query.bottleneck.EVIDENCE_RANK`）。只收資料撐得住的兩個：
#: #11 的六個 case 全是這兩種；`deploys` 今天 origin＝主詞只有 1 條，撞到再加（L17）。
BUYER_SUBJECT_RELATIONS: frozenset[str] = frozenset({"depends_on", "constrained_by"})
#: 持股關係（E9；failure log #10）。**這兩種邊本身不套關係人判定**：被投資方說「某某投資了我」是對手方對持股這件事
#: 本身的陳述，與客戶說「我向它買」同形；拿持股邊去降它自己是循環。
HOLDING_RELATIONS: frozenset[str] = frozenset({"acquired", "invests_in"})
#: 關係人自述的兩格（`query.bottleneck.EVIDENCE_RANK` 的鍵）——插槽視角的客戶端原文、讀圖 independent 核對讀它。
RELATED_PARTY_CLASSES: frozenset[str] = frozenset({"related_party", "related_party_costly"})


def related_parties(edges: Iterable[Any]) -> dict[str, frozenset[str]]:
    """圖上的**控制**關係 → 每家公司的關係人（批次二 E9；failure log #10）。唯一 owner；`corroboration` 讀它。

    控制＝`CanonicalEdge.control`（`acquired` 一律是；`invests_in` 要有一筆 assertion 宣告 `attributes.control`）。
    雙方互為關係人；同一個控制方底下的兩家也是（同一母公司）。合資的兩個股東**不**因此互為關係人。
    ⚠ **少數股權不算**（2026-10-21 實測、L11-6）：圖上 16 條持股邊多半是策略或財務投資——NVIDIA 對 Coherent／Lumentum
    各 20 億美元、MACOM 對 IQE、誼虹對華星光 10.6%。若一律算關係人，NVIDIA 以**客戶**身分說的 9 條供貨／合作會從
    外部印證掉下來，而客戶端印證是 L8 最強的那一種。控制要由逐字寫得出比例或母子關係的那份文件宣告，不由關係名推。
    """
    related: dict[str, set[str]] = {}
    children: dict[str, set[str]] = {}
    for edge in edges:
        if edge.relation not in HOLDING_RELATIONS or not getattr(edge, "control", False):
            continue
        parent, child = str(edge.src), str(edge.dst)
        if parent == child or not (parent.startswith("co:") and child.startswith("co:")):
            continue
        related.setdefault(parent, set()).add(child)
        related.setdefault(child, set()).add(parent)
        children.setdefault(parent, set()).add(child)
    for kids in children.values():
        for kid in kids:
            related[kid].update(kids - {kid})
    return {company: frozenset(others) for company, others in related.items()}


class PublisherConfigError(ValueError):
    """`config/publishers.json` 形狀或內容不合規——fail closed，不帶著壞設定繼續分類。"""


@dataclass(frozen=True)
class Publisher:
    origin: str
    kind: str
    corroborates: bool
    #: 讓這筆被登記的那份 SourceDoc id——登記的出處（L18：標籤要指得回原始證據）。
    seen_in: str
    note: str = ""


@dataclass(frozen=True)
class PublisherRegistry:
    """登記的發布者，以 casefold 後的 origin 為鍵。"""

    by_key: Mapping[str, Publisher]

    def get(self, origin: str | None) -> Publisher | None:
        key = str(origin or "").strip().casefold()
        return self.by_key.get(key) if key else None

    def __len__(self) -> int:
        return len(self.by_key)


EMPTY_PUBLISHERS = PublisherRegistry(by_key={})


def load_publishers(path: Path | None = None) -> PublisherRegistry:
    """讀 `config/publishers.json` 並逐筆核對；任何一筆不合規整份拒收（`PublisherConfigError`）。

    核對：類別在封閉字彙裡；`corroborates` 等於該類別寫死的值；origin 非空、已經是去註解後的形式
    （帶尾端註解的鍵永遠比不到）、casefold 後不重複；`seen_in`（登記的出處）非空；設定檔的 `kinds` 段與
    程式的 `PUBLISHER_KINDS` 一致。
    """
    from query.bottleneck import _strip_annotation

    source = path or PUBLISHERS_PATH
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PublisherConfigError(f"{source}：讀不到或不是 JSON（{exc}）") from exc
    if not isinstance(data, Mapping) or data.get("schema_version") != 1:
        raise PublisherConfigError(f"{source}：schema_version 必須是 1")
    declared_kinds = data.get("kinds")
    if not isinstance(declared_kinds, Mapping) or {
        str(k): (v or {}).get("corroborates") for k, v in declared_kinds.items()
    } != dict(PUBLISHER_KINDS):
        raise PublisherConfigError(
            f"{source}：kinds 段必須與程式的封閉字彙相同（{dict(PUBLISHER_KINDS)}）——類別與它算不算印證只有一個來源")
    entries = data.get("publishers")
    if not isinstance(entries, list):
        raise PublisherConfigError(f"{source}：publishers 必須是 list")
    by_key: dict[str, Publisher] = {}
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, Mapping):
            raise PublisherConfigError(f"{source}：第 {index} 筆不是物件")
        origin = str(entry.get("origin") or "").strip()
        kind = entry.get("kind")
        corroborates = entry.get("corroborates")
        if not origin:
            raise PublisherConfigError(f"{source}：第 {index} 筆 origin 是空的")
        if kind not in PUBLISHER_KINDS:
            raise PublisherConfigError(
                f"{source}：第 {index} 筆（{origin}）kind={kind!r} 不在封閉字彙 {sorted(PUBLISHER_KINDS)}")
        if corroborates is not PUBLISHER_KINDS[kind]:
            raise PublisherConfigError(
                f"{source}：第 {index} 筆（{origin}）corroborates={corroborates!r}，但 {kind} 一律是 "
                f"{PUBLISHER_KINDS[kind]}——類別決定算不算印證，不能逐筆覆寫（媒體不得整類升級）")
        if _strip_annotation(origin) != origin:
            raise PublisherConfigError(
                f"{source}：第 {index} 筆 origin {origin!r} 帶尾端註解——鍵必須是去註解後的字串，否則永遠比不到")
        key = origin.casefold()
        if key in by_key:
            raise PublisherConfigError(f"{source}：origin {origin!r} 重複登記")
        seen_in = str(entry.get("seen_in") or "").strip()
        if not seen_in:
            raise PublisherConfigError(
                f"{source}：第 {index} 筆（{origin}）沒有 seen_in——登記必須指得回讓它被登記的那份 SourceDoc（L18）")
        by_key[key] = Publisher(origin=origin, kind=str(kind), corroborates=bool(corroborates), seen_in=seen_in,
                                note=str(entry.get("note") or ""))
    return PublisherRegistry(by_key=by_key)


@lru_cache(maxsize=1)
def get_publishers() -> PublisherRegistry:
    """正式設定（每個行程讀一次）。測試要換設定請把 `publishers=` 傳進消費端，不要改這裡。"""
    return load_publishers()


@dataclass(frozen=True)
class OriginResolution:
    """一個 origin 字串是誰。

    - `company`：`id`＝`co:*`；`corroborates`＝None（算不算印證取決於**主詞**是不是它，由呼叫端判）。
    - `publisher`：`id`＝登記的 origin 字串；`corroborates` 由類別決定；`publisher_kind` 是類別。
    - `unresolved`：`id`＝None、`corroborates`＝False。**不得當成「不同源」**（L8／L11 的 laundering）。
    """

    kind: str
    id: str | None
    corroborates: bool | None
    publisher_kind: str | None = None


def resolve_origin(origin: str | None, registry: Any, *,
                   publishers: PublisherRegistry | None = None) -> OriginResolution:
    """origin 解析的唯一 owner：先名冊公司，再登記的發布者，否則解析不到。"""
    from query.bottleneck import _strip_annotation, company_id_for_origin

    company = company_id_for_origin(origin, registry)
    if company:
        return OriginResolution(kind="company", id=company, corroborates=None)
    pubs = publishers if publishers is not None else get_publishers()
    publisher = pubs.get(_strip_annotation(str(origin or "").strip()))
    if publisher is not None:
        return OriginResolution(kind="publisher", id=publisher.origin, corroborates=publisher.corroborates,
                                publisher_kind=publisher.kind)
    return OriginResolution(kind="unresolved", id=None, corroborates=False)


def publisher_lifts(resolution: OriginResolution, linkages: Iterable[str | None] = ()) -> bool:
    """一個**發布者** origin，在引用它的那幾份文件各自的 `origin_linkage` 宣告下，算不算外部印證。

    `linkages`：同一個 origin、引用這條邊（或這段引文）的每一份 SourceDoc 的宣告（缺＝None）；空＝一份沒宣告的文件。
    - 宣告 `same_origin` 的文件是轉述——**不論類別都不算**（研究機構轉述供應商新聞稿也是轉述）。
    - 自產資料的類別（`corroborates=True`）：任一份不是 `same_origin` 的文件就算。
    - 媒體：只有宣告 `independent`（媒體自己採訪或統計）的文件算。
    `classify_evidence` 與 `verify_citations` 都問這個函式，所以同一份文件在兩處的結論一定相同。
    """
    if resolution.kind != "publisher":
        raise ValueError(f"publisher_lifts 只回答發布者（收到 {resolution.kind}）")
    declared = [value or None for value in linkages] or [None]
    if resolution.corroborates:
        return any(value != SAME_ORIGIN for value in declared)
    return any(value == INDEPENDENT for value in declared)


# ---------------------------------------------------------------------------
# 逐來源具名＋轉述（Phase 6 Step 6.4）
# ---------------------------------------------------------------------------

#: 沒升外部印證的三種理由（封閉；`query.layer_stats` 的 `corroboration_withheld` 三個鍵）。
#: **三種不得壓成一格**（L12；`quote_names_company` docstring）——補救各不相同：
#: - `unnamed`：主詞在名冊有寫法，但這個來源自己的引文沒有逐字具名它 → 從同一份文件補具名引文（RA，pq2）。
#: - `no_name_forms`：主詞在名冊**沒有比得到的寫法**（沒有任何寫法，或每個寫法都與另一家共用——同一家公司兩個 id）
#:   → 名冊補寫法或身分清理；讀原文補引文也比不到（`query.bottleneck.usable_name_forms`）。
#: - `relay`：發布者的引文有具名主詞，但每一段都是轉述句 → 找它轉述的那份一手，或那份文件確有自己的數據時
#:   逐份宣告 `origin_linkage=independent`（pq2）。
WITHHELD_REASONS: tuple[str, ...] = ("unnamed", "no_name_forms", "relay")
#: 三種理由給人看的字（插槽視角旁註、RA packet 的證據等級預告共用一份——L16）。
WITHHELD_LABELS: Mapping[str, str] = {
    "unnamed": "引文沒具名主詞",
    "no_name_forms": "名冊無名可比",
    "relay": "轉述句",
}


@lru_cache(maxsize=1)
def get_relay_language():
    """正式轉述字表（每個行程讀一次；唯一 loader）。測試要換字表請把 `relay=` 傳進消費端，不要改這裡。

    ⚠ L19：字表不得出現在 `prompts/`、`skills/`（`tests/test_relay_language.py` 守著）。
    """
    from query.sub_language import load_language

    return load_language(RELAY_LANGUAGE_PATH)


@dataclass(frozen=True)
class OriginDoc:
    """一個 origin 引用一條邊的**一份**文件：它的 `origin_linkage` 宣告（缺＝None）與它在這條邊上的逐字。

    逐份、不是逐 origin：轉述檢查的豁免（宣告 `independent`）與 `publisher_lifts` 都是文件層級的宣告
    （plan §0.6 #2：同一家媒體一份自己採訪、一份轉述，兩份的結論不同）。
    """

    doc_id: str | None
    linkage: str | None = None
    quotes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Corroboration:
    """一個 origin 對一條邊能支持的證據等級（`query.bottleneck.EVIDENCE_RANK` 的鍵），與沒升外部印證的理由。

    `withheld` 只在「本來會因為這個 origin 升外部印證、被具名或轉述規則擋下」時有值（`WITHHELD_REASONS`）；
    其餘一律 None（自報、媒體沒宣告、解析不到——那些照舊，不是這條規則擋的）。
    `docs`：判定讀的那幾份文件（`withheld` 時就是補引文要讀的清單——L18：指得回文件）。
    `quote`：撐住外部印證的那段具名引文（主詞是公司時才有）；`relay_terms`：判轉述憑的是哪幾個字。
    `publisher_lifted`：發布者至少一份文件過了 `publisher_lifts`（類別與逐份宣告）——**不等於**撐得住外部印證
    （過了之後仍可能因沒具名或轉述被擋）；非發布者一律 False。插槽視角的來源清單印「第三方·類別」還是「媒體轉述」讀它。
    """

    origin: str
    resolution: OriginResolution
    level: str
    withheld: str | None = None
    docs: tuple[str, ...] = ()
    quote: str | None = None
    relay_terms: tuple[str, ...] = ()
    publisher_lifted: bool = False


def corroboration(origin: str, subject: str, docs: Iterable[OriginDoc], registry: Any, *,
                  relation: str, related: Mapping[str, frozenset[str]],
                  filing: bool = False, publishers: PublisherRegistry | None = None,
                  relay: Any = None, shared: frozenset[str] | None = None) -> Corroboration:
    """「這個 origin 對這條邊算不算外部印證」的唯一 owner（Phase 6 Step 6.4）。

    `subject`：邊的主詞（`src`）；`docs`：這個 origin 引用這條邊的每一份文件（`OriginDoc`）；
    `filing`：這個 origin 有沒有 filing 出身的文件（costly proxy）；`relay`：轉述字表（預設正式字表）；
    `shared`：`shared_name_forms(registry)`（大量呼叫時由呼叫端算一次）。規則：

    - **名冊公司、是主詞** → 自報（filing 出身為自報·filing）。照舊；`relation` 在 `BUYER_SUBJECT_RELATIONS`
      （主詞是買方）時是買方自述（filing 另標），同 rank、只拆標籤（批次二 E9；#11）。
    - **名冊公司、是主詞的控制關係人**（`related`＝`related_parties` 的輸出；持股邊本身除外）→ 關係人自述
      （filing 另標）——母子公司、收購方、合資股東說的不是第三方印證（E9；#10、L8）。沒有 withheld：
      不是具名或轉述規則擋的，是說話的人本來就不獨立。
    - **名冊公司、不是主詞**：主詞是公司（`co:*`）時，這個 origin **自己的**引文至少一段逐字具名主詞
      （`query.bottleneck.quote_names_company`——名字比對的唯一 owner）才給外部印證；主詞在名冊沒有比得到的寫法
      （`usable_name_forms` 空）→ 待判定＋`no_name_forms`；有寫法但沒具名 → 待判定＋`unnamed`。主詞不是公司
      （技術節點之間的邊）→ 外部印證，照舊。
    - **登記的發布者**：只在過了 `publisher_lifts` 的那幾份文件裡找（逐份）；一份都沒過 → 媒體轉述（照舊）。
      主詞是公司時要有一段「具名主詞、而且不是轉述句」的引文才給外部印證——**那份文件宣告 `independent` 時不套
      轉述檢查**（具名照樣要；ROADMAP「翻案靠逐份宣告」，plan §0.6 #2）；否則媒體轉述＋`relay`（有具名、都是轉述）
      或 `unnamed`／`no_name_forms`。
    - **解析不到**：聯合公告偵測（去註解後的字串具名 ≥2 家名冊公司、含主詞以外者）→ 雙方聯合；否則待判定。照舊。

    ⚠ **只會讓標籤變保守**（plan 不可越線 2）：與 Phase 6 之前的規則相比，每一支要嘛照舊、要嘛多一個條件。
    ⚠ 轉述偵測只套發布者：公司 origin 轉述另一家的說法（「Coherent announced…」寫在 NVIDIA 部落格）今天沒有資料撐這一格
    （plan §0.3；L17：機制只 general 到資料支持的那一格）。
    """
    from query.bottleneck import (_origin_mentions, _strip_annotation, quote_names_company, shared_name_forms,
                                  usable_name_forms)
    from query.sub_language import matched_terms

    docs = tuple(sorted(docs, key=lambda d: str(d.doc_id or "")))
    resolution = resolve_origin(origin, registry, publishers=publishers)
    lifted = False

    def result(level: str, withheld: str | None = None, *, considered: Iterable[OriginDoc] = docs,
               quote: str | None = None, terms: Iterable[str] = ()) -> Corroboration:
        return Corroboration(origin=origin, resolution=resolution, level=level, withheld=withheld,
                             docs=tuple(sorted({str(d.doc_id) for d in considered if d.doc_id})),
                             quote=quote, relay_terms=tuple(sorted(set(terms))), publisher_lifted=lifted)

    if resolution.kind == "unresolved":
        mentions = _origin_mentions(_strip_annotation(origin), registry)
        return result("counterparty_joint" if len(mentions) >= 2 and (mentions - {subject}) else "needs_review")
    if resolution.kind == "company" and resolution.id == subject:
        if relation in BUYER_SUBJECT_RELATIONS:
            return result("buyer_self_reported_costly" if filing else "buyer_self_reported")
        return result("self_reported_costly" if filing else "self_reported")
    if (resolution.kind == "company" and relation not in HOLDING_RELATIONS
            and resolution.id in related.get(str(subject), ())):
        return result("related_party_costly" if filing else "related_party")

    if resolution.kind == "publisher":
        considered = tuple(d for d in (docs or (OriginDoc(None),)) if publisher_lifts(resolution, (d.linkage,)))
        if not considered:
            return result("media_relay")
        lifted = True
        fallback = "media_relay"
    else:
        considered = docs
        fallback = "needs_review"
    if not str(subject or "").startswith("co:"):
        return result("externally_corroborated", considered=considered)

    company = registry.company(subject) if registry.has_company(subject) else None
    if shared is None:
        shared = shared_name_forms(registry)
    if company is None or not usable_name_forms(company, shared):
        return result(fallback, "no_name_forms", considered=considered)
    relay_language = relay if relay is not None else get_relay_language()
    relay_terms: list[str] = []
    for doc in considered:
        for quote in doc.quotes:
            if not quote_names_company(quote, company, shared=shared):
                continue
            if resolution.kind == "company" or doc.linkage == INDEPENDENT:
                return result("externally_corroborated", considered=considered, quote=quote)
            terms = matched_terms(quote, language=relay_language)
            if not terms:
                return result("externally_corroborated", considered=considered, quote=quote)
            relay_terms.extend(terms)
    if relay_terms:
        return result(fallback, "relay", considered=considered, terms=relay_terms)
    return result(fallback, "unnamed", considered=considered)
