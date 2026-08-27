"""pq1 注意力排序：字典序，不做加權總分。

**為什麼不是加權總分（2026-08-21 改）**

原本七項權重相加。2026-08-21 實測：Micron 內部人 Form 4 以
``tier 4.0 + holdings_impact 4.0 + thesis_impact 4.0 = 12.0`` 佔掉每日 5 個 pq1
slot 中的 **3 個**，而且是 7 週前的、公司還是 `AGENTS.md`「主題範圍」明文降範圍的
Micron；90 個候選裡 Form 4 佔 36 筆、前 20 名佔 16 筆。

三項加分理由**單獨看都成立**——它確實是一手來源、確實持有 MU、MU 確實在追蹤中。
錯的是三個各自成立的弱理由相加，就能壓過一則講「誰掏 122 億綁誰」的資本承諾事件
（後者只是命中的軸比較少）。**這個病叫補償性：很多個弱理由可以合成一個假的強理由。**

2026-08-12 那次「12 檔財報季總評擠掉 tier-1 8-K」修的是稀釋係數
（`FOCUS_TICKER_CAP`），沒有動到加法本身，所以同一個病換一種面貌又長出來了。
字典序沒有補償性——這是結構保證，不是參數調校。

同一個判斷 `query/bottleneck.py` 已經做過：「排序鍵是明確優先序，不是加權綜合分數」。
本模組改為與它一致。

**分工（`AGENTS.md` L15）**

語意判斷（這則是什麼、誰付錢給誰、答案回來會改變什麼）由 `skills/signal-triage`
在 triage 當下產生，寫回 ``lead["triage"]["classification"]``；本模組只做確定性排序。
LLM 可以解析與提議，不可以授權——本模組不影響 evidence tier、graph admission、
pq2 核准或任何資本 gate，只排注意力順序。

**為什麼分類寫在 triage 而不是 drain**：在 drain 分類等於每輪重跑全部候選、結果會飄、
佇列不可重現；在 triage 分類則每則只算一次、可稽核、drain 是純函數。

一個實測發現支持這個設計：舊 triage 只有 ``go``／``no_go`` 二選一，於是 agent 判定
「MU 官方 SEC Form 4……**低優先**但可作 insider／稀釋時變觀測」時，那句「低優先」只能
寫進自由文字 ``reason``，排序讀不到。**判斷一直都在，只是無處落腳。**
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "lead_classification.json"

_EDGAR_SOURCE = re.compile(r"^edgar:([A-Z0-9.^_-]+)$")
_CASHTAG = re.compile(r"(?<![A-Z0-9_])\$([A-Z][A-Z0-9.]{0,9})\b", re.IGNORECASE)


class ClassificationVocabularyError(RuntimeError):
    """字彙檔缺失或損毀。fail closed，不猜預設值。"""


class ClassificationValidationError(ValueError):
    """分類資料缺欄位或使用字彙外值；不得靜默降級成 unknown。"""


@lru_cache(maxsize=1)
def vocabulary() -> dict[str, Any]:
    """載入封閉字彙。缺檔一律 fail closed。

    `AGENTS.md` 已記過同型事故：新增 `config/*.json` 若忘了在 `.gitignore` 補
    `!config/<name>.json`，fresh clone 與另一個 agent 會缺檔而**靜默失效**。
    這裡不提供 fallback 預設值，就是為了讓那種缺檔立刻現形。
    """

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - 環境問題
        raise ClassificationVocabularyError(
            f"找不到 {CONFIG_PATH}；請確認 .gitignore 有 !config/lead_classification.json"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ClassificationVocabularyError(f"{CONFIG_PATH} 不是合法 JSON：{exc}") from exc
    for key in ("decision_impact", "content_type", "payment_direction"):
        if not isinstance(raw.get(key), Mapping) or "_order" not in raw[key]:
            raise ClassificationVocabularyError(f"{CONFIG_PATH} 缺少 {key}._order")
    return raw


def _rank_of(axis: str, value: Any, *, fallback: str = "unknown") -> int:
    """字彙值 → 名次（0 最優先）。未登記的值排在最後，不猜、不報錯。"""

    order = list(vocabulary()[axis]["_order"])
    name = str(value) if value is not None else fallback
    if name in order:
        return order.index(name)
    if fallback in order:
        return order.index(fallback)
    return len(order)


def validate_classification(
    raw: Mapping[str, Any] | None,
    *,
    allow_unknown: bool = False,
    require_receipt: bool = False,
) -> dict[str, Any]:
    """驗證並複製一筆結構化 pq1 分類。

    排序器仍能讀歷史 ``unknown``，但任何新 triage／backfill 都應以
    ``allow_unknown=False`` 寫入完整字彙。``require_receipt`` 用於檢查已落盤
    authority，確保語意結論不只剩兩個排序欄位而沒有時間、來源與理由。
    """

    if not isinstance(raw, Mapping):
        raise ClassificationValidationError("PASS 必須附結構化 classification")
    record = dict(raw)
    vocab = vocabulary()
    for axis in ("content_type", "decision_impact"):
        value = str(record.get(axis) or "").strip()
        if not value:
            raise ClassificationValidationError(f"classification 缺少 {axis}")
        if value not in vocab[axis]["_order"]:
            raise ClassificationValidationError(
                f"{axis}={value!r} 不在 config/lead_classification.json 的字彙內"
            )
        if value == "unknown" and not allow_unknown:
            raise ClassificationValidationError(
                f"新 classification 不得寫入 {axis}=unknown"
            )
        record[axis] = value

    payment_direction = str(record.get("payment_direction") or "").strip()
    if record["content_type"] == "capital_commitment":
        if payment_direction not in vocab["payment_direction"]["_order"]:
            raise ClassificationValidationError(
                "capital_commitment 必須填合法的 payment_direction"
            )
        record["payment_direction"] = payment_direction
    elif payment_direction:
        if payment_direction not in vocab["payment_direction"]["_order"]:
            raise ClassificationValidationError(
                f"payment_direction={payment_direction!r} 不在封閉字彙內"
            )
        record["payment_direction"] = payment_direction
    else:
        record.pop("payment_direction", None)

    if require_receipt:
        for field in ("classified_by", "classified_at", "reason"):
            if not str(record.get(field) or "").strip():
                raise ClassificationValidationError(
                    f"已落盤 classification 缺少 {field} receipt"
                )
    return record


def lead_tickers(lead: Mapping[str, Any]) -> frozenset[str]:
    """這則 lead 提到的**所有** ticker（大寫）。

    先前只取標題第一個 cashtag，於是一則同時點名五家的推文只用第一家判定重要性。
    2026-08-08 實例：「gem after gem in $AAOI earnings for $SIVE + other laser
    player readthrough」——第一個是 $AAOI，但該則的實質重點是使用者實際持有的
    SIVE。而 `engine_b/entities.py` 的抽取**早就把五家都解析出來了**：抽取抓到
    五個，排序只用一個。

    優先用抽取結果（`entities.tickers`）；沒有時退回舊的單一 ticker 推導。
    """

    entities = lead.get("entities") or {}
    tickers = entities.get("tickers") if isinstance(entities, Mapping) else None
    if tickers:
        return frozenset(str(t).upper() for t in tickers if t)
    single = lead_ticker(lead)
    return frozenset({single}) if single else frozenset()


def lead_company_ids(lead: Mapping[str, Any]) -> frozenset[str]:
    """這則 lead 解析出的 `co:*` company_id。"""

    entities = lead.get("entities") or {}
    ids = entities.get("company_ids") if isinstance(entities, Mapping) else None
    return frozenset(str(c) for c in (ids or []) if c)


def lead_ticker(lead: Mapping[str, Any]) -> str | None:
    """單一 ticker 推導（`entities` 尚未處理過的舊 lead 的相容路徑）。"""

    source = str(lead.get("source") or "")
    match = _EDGAR_SOURCE.match(source)
    if match:
        return match.group(1).upper()
    title = str(lead.get("title") or "")
    cashtag = _CASHTAG.search(title)
    return cashtag.group(1).upper() if cashtag else None


def classification(lead: Mapping[str, Any]) -> dict[str, Any]:
    """取 lead 上由 triage 寫入的分類；沒有就回空 dict（排序視為 unknown）。"""

    triage = lead.get("triage") or {}
    found = triage.get("classification") if isinstance(triage, Mapping) else None
    return dict(found) if isinstance(found, Mapping) else {}


@dataclass(frozen=True)
class LeadRank:
    """一則 lead 的字典序名次。**每個欄位都是離散等級，數值越小越優先。**

    刻意不提供合併後的單一分數：那正是本次要移除的東西。呼叫端要顯示時用
    :attr:`label`，它同時說明了「為什麼排在這裡」——任何會改變輸出的輸入，
    都應該出現在該輸出自己的證據欄位裡（L12 的推論）。
    """

    user_authority: int
    decision_impact: int
    content_type: int
    payment_direction: int
    chokepoint: int
    relevance: int
    tier: int
    independent_source: int
    novelty: int
    lead_id: str

    def sort_key(self) -> tuple:
        return (
            self.user_authority,
            self.decision_impact,
            self.content_type,
            self.payment_direction,
            self.chokepoint,
            self.relevance,
            self.tier,
            self.independent_source,
            self.novelty,
            self.lead_id,
        )

    @property
    def label(self) -> str:
        vocab = vocabulary()

        def name(axis: str, index: int) -> str:
            order = list(vocab[axis]["_order"])
            if index >= len(order):
                return "?"
            key = order[index]
            entry = vocab[axis].get(key) or {}
            return str(entry.get("label") or key)

        parts = [
            name("decision_impact", self.decision_impact),
            name("content_type", self.content_type),
        ]
        if self.user_authority == 0:
            parts.insert(0, "使用者指定")
        if self.chokepoint == 0:
            parts.append("瓶頸")
        return "·".join(parts)


def rank_lead(
    lead: Mapping[str, Any],
    *,
    thesis_impact: bool = False,
    holdings_impact: bool = False,
    chokepoint_impact: bool = False,
) -> LeadRank:
    """單則 lead 的字典序名次。

    `thesis_impact`／`holdings_impact`／`chokepoint_impact` 由呼叫端注入而非在此
    查圖或查持股，讓本模組不依賴 Neo4j／Engine C／Engine D。
    """

    triage = lead.get("triage") or {}
    flags = triage.get("priority_flags") or {}
    tags = classification(lead)

    try:
        tier = int(triage.get("tier"))
    except (TypeError, ValueError):
        tier = 4
    tier = min(4, max(1, tier))

    user_authority = 0 if (
        flags.get("user_requested")
        or (lead.get("refs") or {}).get("campaign_focus") == "primary"
    ) else 1

    # 反證仍是最高優先——舊 `contradiction` 權重 5.0 的理由（可能推翻 thesis）
    # 在新字彙裡對應 `exit_condition`。旗標存在時直接視為該級，讓舊 lead 不必等
    # backfill 就保有原本的急迫性。
    impact_value = tags.get("decision_impact")
    if flags.get("contradiction") and not impact_value:
        impact_value = "exit_condition"

    if holdings_impact:
        relevance = 0
    elif thesis_impact:
        relevance = 1
    else:
        relevance = 2

    return LeadRank(
        user_authority=user_authority,
        decision_impact=_rank_of("decision_impact", impact_value),
        content_type=_rank_of("content_type", tags.get("content_type")),
        payment_direction=_rank_of(
            "payment_direction", tags.get("payment_direction"), fallback="unclear"
        ),
        chokepoint=0 if chokepoint_impact else 1,
        relevance=relevance,
        tier=tier,
        independent_source=0 if flags.get("independent_source") else 1,
        novelty=0 if flags.get("novelty") else 1,
        lead_id=str(lead.get("lead_id") or ""),
    )


def rank_leads(
    leads: Iterable[Mapping[str, Any]],
    *,
    tracked_tickers: frozenset[str] = frozenset(),
    held_tickers: frozenset[str] = frozenset(),
    held_company_ids: frozenset[str] = frozenset(),
    chokepoint_tickers: frozenset[str] = frozenset(),
    chokepoint_company_ids: frozenset[str] = frozenset(),
) -> list[tuple[LeadRank, dict[str, Any]]]:
    """回 [(LeadRank, lead)]，字典序由優先到不優先。

    比對用 lead 提到的**所有** ticker，不是第一個。

    `tracked_tickers`（有在追）與 `held_tickers`／`held_company_ids`（真的有部位）
    分開注入：兩者語意不同，先前只有前者，導致實際持股在排序上零加權。
    `chokepoint_tickers`／`chokepoint_company_ids` 由 caller 從
    `query/bottleneck.py` 的排序結果導出；本模組不查圖。
    """

    ranked: list[tuple[LeadRank, dict[str, Any]]] = []
    for lead in leads:
        tickers = lead_tickers(lead)
        company_ids = lead_company_ids(lead)
        ranked.append(
            (
                rank_lead(
                    lead,
                    thesis_impact=bool(tickers & tracked_tickers),
                    holdings_impact=bool(tickers & held_tickers)
                    or bool(company_ids & held_company_ids),
                    chokepoint_impact=bool(tickers & chokepoint_tickers)
                    or bool(company_ids & chokepoint_company_ids),
                ),
                dict(lead),
            )
        )
    ranked.sort(key=lambda item: item[0].sort_key())
    return ranked
