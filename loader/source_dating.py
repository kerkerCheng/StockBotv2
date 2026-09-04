"""SourceDoc 定日 metadata 的 **mechanical 回填走廊**。

## 這條走廊為什麼不需要 pq2

2026-09-04 使用者定案把「可否確定性重導」的判準從 Engine C 延伸到圖的 metadata 回填：
替既有 SourceDoc 補 `published_at`／`retrieved_at` 這類**印在文件上的事實**是
`mechanical`，**不需 pq2**。它不是 graph admission——admission 是讓**新的 claim／邊**
進圖（那是新的知識主張），這裡只是把一份已經在圖裡的文件的出版日補上，
而那個日期本來就印在文件上，任何人重讀都得到同一個數。

## ⚠ 放行與收緊必須同時發生（L15）

拿掉 pq2 的**補償控制**有四道，缺一這條走廊就變成繞過 admission 的後門：

1. **屬性白名單。** 只有 `published_at`／`retrieved_at` 寫得進來。任何 claim、
   邊、`substitutability`、`sole_source`、`evidence_tier` 一律拒絕——那些是
   判讀，仍走 pq2。
2. **`--basis` 必填且落地。** 每一筆回填都在節點上留下 `published_at_basis`
   （一手出處與定位）與 `published_at_method`（封閉字彙）。
3. **寫入值本身被記下來**（`published_at_backfilled`）。之後若有任何東西
   （例如 loader 重跑）把 `published_at` 改成別的值，audit 就會看到
   「基準說 A、現值是 B」——**basis 與值脫鉤是可偵測的**，不必相信它不會發生。
4. **`url_path` 方法由 audit 實際重導。** 宣稱「日期印在 URL 裡」的，
   audit 會拿當下的 `url` 再導一次；導不出同一個值就是 FAIL。

## ⚠ 沒有任何一個 method 代表「抓到的那天」

`retrieved_at` 是我們抓到它的時間，不是世界知道它的時間（F-27 就是這兩者被壓成
一個欄位造成的）。拿 ingest 日期冒充 `published_at` 會讓**所有東西看起來都是最近
才發表的**，而回測會因此在每個歷史時點都看到全部證據——那是 lookahead 的最壞形式。
所以字彙裡刻意沒有這個選項；要寫下它必須在一個會被稽核的欄位裡主動說謊。

## 推不出來就留 null

L11-5：**「我找不到日期」與「它沒有日期」是兩個不同的 claim。**
留 null 的後果是那份證據在 as-of 篩選時被排除**並計數**（`EvidenceSelection`
的 `excluded_undated`），這是誠實的降級；填一個猜的日期則是靜默的污染。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

#: 可由本走廊回填的屬性。**這是白名單不是黑名單**——沒列出的一律拒絕。
#: 擴充前先問：這個值是「印在文件上、任何人重讀都得到同一個數」嗎？
#: 不是的話它是判讀，走 pq2。
BACKFILLABLE_PROPERTIES: tuple[str, ...] = ("published_at", "retrieved_at")

#: 日期怎麼來的（封閉字彙）。⚠ **刻意沒有「ingest／retrieval date」這一項**，
#: 理由見模組 docstring。新增一個 method 等於新增一種「可以被接受的證據來源」，
#: 要同時想清楚 audit 怎麼抽查它。
DATING_METHODS: Mapping[str, str] = {
    "url_path": "日期印在 URL 路徑裡，可由 url 機械重導（audit 會實際重導一次）",
    "filing_metadata": "申報 metadata（SEC accession／filing date、交易所公告編號）",
    "document_masthead": "文件本身印的日期（新聞稿 dateline、年報封面、期刊 published 欄位）",
    "event_date": "具名公開活動的日期（法說會、OFC/ECOC 議程），活動日期本身公開可查",
}

#: URL 裡可被**無歧義**解析成完整日期的三種形狀。
#: ⚠ 刻意不解析 `/2026/jun/` 這種只有月份的路徑：月份不是日期，
#: 補一個「1 號」進去就是編造精度。那類文件要改用其他 method（實際讀文件上的日期）。
_URL_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/(?P<y>20\d{2})/(?P<m>0[1-9]|1[0-2])/(?P<d>0[1-9]|[12]\d|3[01])(?:/|$)"),
    re.compile(r"(?<!\d)(?P<y>20\d{2})-(?P<m>0[1-9]|1[0-2])-(?P<d>0[1-9]|[12]\d|3[01])(?!\d)"),
    re.compile(r"(?<!\d)(?P<y>20\d{2})(?P<m>0[1-9]|1[0-2])(?P<d>0[1-9]|[12]\d|3[01])(?!\d)"),
)


class DatingRejected(ValueError):
    """回填被拒。**訊息必須說清楚拒絕的理由與正確的路徑**，不只說「不合法」。"""


@dataclass(frozen=True, slots=True)
class DatingProposal:
    """一筆已通過驗證的回填。"""

    doc_id: str
    prop: str
    value: date
    method: str
    basis: str

    @property
    def properties(self) -> dict[str, str]:
        """要寫進節點的欄位。`*_backfilled` 是給 audit 比對用的基準值。"""
        return {
            self.prop: self.value.isoformat(),
            f"{self.prop}_method": self.method,
            f"{self.prop}_basis": self.basis,
            f"{self.prop}_backfilled": self.value.isoformat(),
            f"{self.prop}_backfilled_at": datetime.now(timezone.utc).isoformat(),
        }


def dates_in_url(url: str | None) -> tuple[date, ...]:
    """URL 裡所有可無歧義解析的完整日期。

    這是 `url_path` 方法的**確定性重導函式**——走廊寫入時用它驗一次，
    audit 事後再用它驗一次。兩次用同一支，才叫「可被重導核對」。
    """
    if not url:
        return ()
    found: list[date] = []
    for pattern in _URL_DATE_PATTERNS:
        for match in pattern.finditer(str(url)):
            try:
                parsed = date(int(match["y"]), int(match["m"]), int(match["d"]))
            except ValueError:
                continue
            if parsed not in found:
                found.append(parsed)
    return tuple(found)


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(str(text).strip()[:10])
    except ValueError as exc:
        raise DatingRejected(f"不是合法的 ISO 日期：{text!r}") from exc


def validate_proposal(
    *,
    doc_id: str,
    prop: str,
    value: str,
    method: str,
    basis: str,
    node: Mapping[str, Any] | None,
    supersede: bool = False,
    today: date | None = None,
) -> DatingProposal:
    """把一筆回填請求驗成 `DatingProposal`，驗不過就拋 `DatingRejected`。

    `node` 是圖上該 SourceDoc 的現值（`None` 代表節點不存在）。
    純函式，不碰 Neo4j——所以測試不需要資料庫。
    """
    if prop not in BACKFILLABLE_PROPERTIES:
        raise DatingRejected(
            f"`{prop}` 不在回填白名單內。本走廊只補**印在文件上的事實**："
            f"{', '.join(BACKFILLABLE_PROPERTIES)}。\n"
            "  新的 claim／邊、evidence_tier、substitutability 這類判讀"
            "仍需 graph admission（pq2 `ra_admission` 編號），一個字都不放寬。"
        )
    if method not in DATING_METHODS:
        raise DatingRejected(
            f"`{method}` 不是已登記的定日方法。可用：\n  "
            + "\n  ".join(f"{k} — {v}" for k, v in DATING_METHODS.items())
            + "\n  ⚠ 沒有「抓到的那天」這個選項：ingest 日期冒充 published_at "
              "會讓所有東西看起來都是最近才發表的，回測會因此看到未來。"
        )
    if not str(basis).strip():
        raise DatingRejected(
            "`basis` 必填——它是拿掉 pq2 的補償控制，不是註解。"
            "寫出一手出處與定位（URL、SEC accession、議程頁、年報封面）。"
        )
    if node is None:
        raise DatingRejected(
            f"圖裡沒有 SourceDoc `{doc_id}`。本走廊只補**既有節點**的 metadata；"
            "建立新文件節點屬於 ingest，走既有 extract → validate → load 管線。"
        )

    parsed = _parse_date(value)
    today = today or datetime.now(timezone.utc).date()
    if parsed > today:
        raise DatingRejected(f"{parsed} 在未來（今天 {today}）——不可能已經發表。")

    # 已有值：回填不是改寫。改一個既有日期是在推翻一筆已被下游消費的事實，
    # 必須看得見，所以走 `--supersede` 並留下舊值，不從這裡默默通過。
    existing = node.get(prop)
    basis_text = str(basis).strip()
    if existing:
        if not supersede:
            raise DatingRejected(
                f"`{doc_id}` 的 {prop} 已經是 {existing}。回填只補空的；"
                "要更正既有值請用 --supersede，它會把舊值留在 basis 裡。"
            )
        basis_text = f"{basis_text}｜supersede 舊值 {existing}"

    # published_at 不得晚於 retrieved_at：抓到它的時候它就已經存在了。
    # ⚠ 這是真的不變式，不是格式檢查——它抓得到「把 ingest 日期填成出版日」
    # 以外的多數手滑（打錯年份、月日顛倒）。
    if prop == "published_at":
        retrieved = node.get("retrieved_at")
        if retrieved:
            try:
                retrieved_date = _parse_date(str(retrieved))
            except DatingRejected:
                retrieved_date = None
            if retrieved_date and parsed > retrieved_date:
                raise DatingRejected(
                    f"published_at={parsed} 晚於 retrieved_at={retrieved_date}——"
                    "我們不可能在它發表之前就抓到它。先確認是哪一個填錯了。"
                )

    if method == "url_path":
        candidates = dates_in_url(node.get("url"))
        if not candidates:
            raise DatingRejected(
                f"method=url_path 但 `{doc_id}` 的 url 裡導不出任何完整日期"
                f"（url={node.get('url')!r}）。\n"
                "  ⚠ 只有月份的路徑（如 /2026/jun/）**不算**——補一個「1 號」"
                "進去是編造精度。改用實際讀到日期的 method。"
            )
        if parsed not in candidates:
            raise DatingRejected(
                f"method=url_path 但 {parsed} 不在 url 導出的日期裡："
                f"{[d.isoformat() for d in candidates]}。"
                "宣稱可機械重導就必須真的重導得出來。"
            )

    return DatingProposal(doc_id=str(doc_id), prop=prop, value=parsed,
                          method=method, basis=basis_text)


# ---------------------------------------------------------------------------
# Neo4j 存取（唯一會碰 DB 的兩支）
# ---------------------------------------------------------------------------

_FETCH = """
MATCH (d:SourceDoc {id: $doc_id})
RETURN d.id AS id, d.url AS url, d.title AS title,
       d.published_at AS published_at, d.retrieved_at AS retrieved_at,
       d.origin_entity AS origin_entity, d.source_type AS source_type
"""

_UNDATED = """
MATCH (d:SourceDoc) WHERE d.published_at IS NULL
OPTIONAL MATCH (a:EdgeAssertion)-[:CITES]->(d)
RETURN d.id AS id, d.url AS url, d.title AS title,
       d.origin_entity AS origin_entity, d.retrieved_at AS retrieved_at,
       count(DISTINCT a) AS assertions
ORDER BY assertions DESC, id
"""

_BACKFILLED = """
MATCH (d:SourceDoc) WHERE d.published_at_method IS NOT NULL
RETURN d.id AS id, d.url AS url, d.published_at AS published_at,
       d.published_at_method AS method, d.published_at_basis AS basis,
       d.published_at_backfilled AS backfilled
ORDER BY d.id
"""


def fetch_document(session: Any, doc_id: str) -> dict[str, Any] | None:
    record = session.run(_FETCH, doc_id=doc_id).single()
    return dict(record) if record else None


def undated_documents(session: Any) -> list[dict[str, Any]]:
    """尚未定日的 SourceDoc，附它擋住幾條 EdgeAssertion（決定回填順序）。"""
    return [dict(r) for r in session.run(_UNDATED)]


def backfilled_documents(session: Any) -> list[dict[str, Any]]:
    """由本走廊回填過的 SourceDoc。audit 用它做事後抽查。"""
    return [dict(r) for r in session.run(_BACKFILLED)]


def apply_proposal(session: Any, proposal: DatingProposal) -> dict[str, Any]:
    """寫入。**只 SET 白名單欄位**，不建節點、不建關係。"""
    props = proposal.properties
    assignments = ", ".join(f"d.{k} = ${k}" for k in props)
    record = session.run(
        f"MATCH (d:SourceDoc {{id: $doc_id}}) SET {assignments} "
        f"RETURN d.id AS id, d.{proposal.prop} AS value",
        doc_id=proposal.doc_id, **props,
    ).single()
    if record is None:
        raise DatingRejected(f"寫入時找不到 SourceDoc `{proposal.doc_id}`")
    return dict(record)


def audit_backfills(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """事後抽查已回填的節點，回傳違規描述（空 list ＝ 全部指得到東西）。

    三件事：method 在字彙內、現值仍等於回填當時寫下的值、`url_path` 重導得出來。
    第二項是為了偵測「loader 重跑把值蓋掉、basis 卻還留著」——
    **basis 與值脫鉤必須看得見**，不能靠相信它不會發生。
    """
    problems: list[str] = []
    for row in rows:
        doc_id = str(row.get("id"))
        method = str(row.get("method") or "")
        value = str(row.get("published_at") or "")
        recorded = str(row.get("backfilled") or "")
        if method not in DATING_METHODS:
            problems.append(f"{doc_id} 的 published_at_method={method!r} 不在封閉字彙內")
            continue
        if not str(row.get("basis") or "").strip():
            problems.append(f"{doc_id} 有 method 卻沒有 basis——指不回一手出處")
        if recorded and value != recorded:
            problems.append(
                f"{doc_id} 的 published_at 現為 {value}，但回填當時寫下的是 {recorded}"
                "——有東西改過它，basis 已不描述現值")
        if method == "url_path":
            candidates = dates_in_url(row.get("url"))
            if not value:
                problems.append(f"{doc_id} 宣稱 url_path 卻沒有 published_at")
            elif _parse_or_none(value) not in candidates:
                problems.append(
                    f"{doc_id} 宣稱 published_at={value} 印在 url 裡，"
                    f"但重導得到 {[d.isoformat() for d in candidates]}")
    return problems


def _parse_or_none(text: str) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None
