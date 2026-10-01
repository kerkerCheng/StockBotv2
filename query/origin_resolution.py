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
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parent.parent
PUBLISHERS_PATH = ROOT / "config" / "publishers.json"

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
