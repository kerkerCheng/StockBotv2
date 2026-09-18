"""重複節點候選偵測——「圖裡有沒有兩個節點其實在講同一個東西」。

L18 的 L2 層（顯形）。與 `query/coverage_gaps.py` 的分工：後者問「這個節點有沒有人供應它」，
本模組問**更前面的一題**——「這個節點是不是根本就是旁邊那個節點」。兩題必須分開，因為
重複節點正是 coverage 那一頁的誤報來源：孤立的重複節點會被判成「🔴 沒有任何公司連到它」，
於是研究被派去挖一個**已經有供應商**的東西（`config/entity_aliases.json` 的 `_readme` 逐字記過
這個後果）。

## 為什麼這個偵測器要等 V1（逐字入圖）之後才做得了

2026-09-18 之前，`tech:inp_eml` 與 `tech:eml` 是不是同一個東西，**沒有任何工具答得出來**——
圖裡只有 id 與 name，而 id 是抽取時 LLM 取的、name 也是。用它們判重複，等於用 label 驗 label
（L18 的封閉迴圈）。那天真正推翻「inp_eml 是 InP 材質特指，不併」這個舊註記的，是那條邊自己的
逐字：同一份 Coherent OFC 文件在一句話裡用兩個詞指同一個東西。

所以本模組的每一對候選都**帶著兩個節點各自的逐字**。判斷「是不是同一個」仍然是人的事（研究
判斷，載體是 pq2 的 `ra_admission`），但他不必為此繞過自己的工具——而**深挖若需要繞過自己的
工具，它就不會例行發生**（L18-4）。

## 它只提名，不合併

合併是 graph write，走既有那條路：pq2 `ra_admission` → `config/entity_aliases.json` 登記
（`semantic_reviewed` 必須帶 `approval_receipt`）→ migration。本模組**不寫任何檔案、不改圖、
不解析 canonical id**——解析的唯一 owner 是 `identity/entities.py`（L16：分類有 SSOT 時要走它，
重造一份會立刻開始偏離）。

## 兩條規則，都是純字串比對

- `id_token_subset`：id 去前綴後以 `_` 切 token，一組是另一組的**真子集**。
  `tech:eml` ⊂ `tech:inp_eml`、`tech:nand` ⊂ `tech:nand_flash` 都是這一型。
- `name_identical`：`name` 正規化（小寫、非英數字轉空白）後逐字相同。這與
  `identity/entities.py` 的 `name_identical` basis 是同一個判準。

⚠ **刻意只有這兩條。** 2026-09-18 實測過第三條「同 token 數、只差一個 token」（想抓
`dram_manufacturing`／`dram_production` 那型），結果**所有單 token 的 id 互相全配**——
`prod:reliant` 配上 `mat:photoresist`。那不是門檻沒調好，是規則本身沒有鑑別力。
因此本模組明說自己抓不到那一型（見 `THIS_IS_NOT`），而不是用一條會誤報的規則假裝抓得到
（L17-4：general 到資料支持的那一格為止；L16-4：做一個會誤報的防呆本身就是過度工程）。

## 為什麼不自己判「這一對已經決定不併了」

`config/entity_aliases.json` 的 note 裡確實有「刻意不併」的決定（`tech:advanced_packaging_gf`
是 GF Fab 8 特指、`tech:3d_nand_manufacturing` 是證據不足的幻覺節點）。但那些話寫在**自由文字**
裡，而自由文字只能機械回答「有沒有提到這兩個 id」，不能機械回答「它說了什麼」——同一個 note
裡「留待研究判斷」與「刻意不併」長得一模一樣。

所以本模組只做前者：**把 note 逐字端出來，讓人自己讀**，並把這類候選與「從來沒人提過」的分開
（`mentioned`／`unmentioned`）。標成「已決定不併」會是宣稱 authority 沒有的東西。
⚠ 這也代表清單**只會因為真的合併而變短**——「刻意不併」目前沒有結構化登記處，那個缺口列在
ROADMAP，因為要決定「不併要不要 receipt」是使用者的題目，不是這裡能補的。
"""
from __future__ import annotations

import itertools
import os
import re
from typing import Any, Iterable, Mapping, Sequence

#: scope 與 `identity/entities.py` 對齊——公司走 `config/company_identity.json`（INV-1），
#: 兩套 identity authority 混在一起就會出現「同一家公司在兩個地方有不同答案」。
#: ⚠ 從 registry import，不在這裡抄一份字串（L16）。
from identity.entities import ENTITY_PREFIXES

#: 命中規則是封閉字彙：每一對候選都必須指得出「它為什麼被提名」。
MATCH_RULES: tuple[str, ...] = ("id_token_subset", "name_identical")

RULE_LABELS: dict[str, str] = {
    "id_token_subset": "id token 真子集",
    "name_identical": "name 逐字相同",
}

#: 每個節點最多端幾段逐字。多於此的在 CLI 提示「還有 N 段」，不靜默截斷（INV-3）。
QUOTES_PER_NODE = 2

TITLE = "重複節點候選（只提名，不合併）"

THIS_IS_NOT = (
    "不是「這兩個是同一個東西」的判定——那是研究判斷，載體是 pq2 的 `ra_admission`；"
    "本頁只說「這兩個名字重疊，而且它們的逐字就在下面」。",
    "不是完整的重複清單：兩條規則都是純字串比對，**名字完全不同的重複抓不到**"
    "（`tech:ocs`／`tech:optical_circuit_switch` 那型只能靠人讀逐字發現）。",
    "也抓不到「同 head、不同尾綴」那型（`dram_manufacturing`／`dram_production`）——"
    "試過的規則會讓所有單 token id 互相全配，誤報比漏報更貴。",
    "`mentioned` 不等於「已決定不併」：registry 的 note 是自由文字，"
    "機械只讀得出「有沒有提到這兩個 id」，讀不出它說了什麼。逐字附在旁邊，由讀的人判斷。",
    "不排序、不評分：`邊` 與 `逐字` 是脈絡（哪一端是碎片），不是分數。",
)

#: 兩個節點都存在才有「重複」這個問題，所以 `QUOTES` 要 OPTIONAL；degree 排除 `QUOTES`
#: 自己——它是 V1 新增的證據邊，算進結構度數會讓「證據多」看起來像「邊多」（兩件事）。
SCAN_CYPHER = """
MATCH (n:Entity)
WHERE n.id IS NOT NULL AND NOT n:Company
  AND any(p IN $prefixes WHERE n.id STARTS WITH p)
OPTIONAL MATCH (n)-[e]-() WHERE type(e) <> 'QUOTES'
WITH n, count(DISTINCT e) AS degree
OPTIONAL MATCH (n)-[:QUOTES]->(s:Source)
WHERE s.quote IS NOT NULL
WITH n, degree, collect({quote: s.quote, locator: s.locator, doc: s.source_doc_id}) AS quotes
RETURN n.id AS node, n.name AS name, n.abstraction_level AS abstraction_level,
       degree, quotes
ORDER BY node
"""


def _tokens(node_id: str) -> frozenset[str]:
    """id 去前綴後的 token 集合。`tech:inp_eml` → {inp, eml}。"""
    local = node_id.split(":", 1)[1] if ":" in node_id else node_id
    return frozenset(t for t in local.split("_") if t)


def _normalised_name(name: Any) -> str:
    """小寫、非英數字轉單一空白。與 `identity/entities.py` 的 `name_identical` 同判準。"""
    return re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()


def _node_view(row: Mapping[str, Any]) -> dict[str, Any]:
    quotes = [
        {"quote": " ".join(str(q.get("quote")).split()),
         "locator": q.get("locator"), "doc": q.get("doc")}
        for q in (row.get("quotes") or ())
        if q and q.get("quote")
    ]
    return {
        "node": row["node"],
        "name": row.get("name"),
        "abstraction_level": row.get("abstraction_level"),
        "degree": int(row.get("degree") or 0),
        # 逐字是本模組存在的理由，所以總數與樣本分開報——截斷要說話（INV-3）。
        "quote_count": len(quotes),
        "quotes": quotes[:QUOTES_PER_NODE],
    }


def pair_candidates(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """純函式：節點列 → 候選對。**不連 DB、不讀 registry。**

    同一對可能同時命中兩條規則（`rules` 是排序後的 list，不是單一值）——把它壓成一個值
    會讓「兩條規則都說是」與「只有一條」長得一樣。
    """
    views = [_node_view(r) for r in rows]
    out: list[dict[str, Any]] = []
    for a, b in itertools.combinations(views, 2):
        rules: list[str] = []
        ta, tb = _tokens(a["node"]), _tokens(b["node"])
        if ta < tb or tb < ta:
            rules.append("id_token_subset")
        na, nb = _normalised_name(a["name"]), _normalised_name(b["name"])
        if na and na == nb:
            rules.append("name_identical")
        if not rules:
            continue
        # 排序固定：token 少的（較通用的那一端）在前，等長取 id 字母序。任何人重跑得到同一組。
        left, right = (a, b) if (len(ta), a["node"]) <= (len(tb), b["node"]) else (b, a)
        out.append({
            "pair": (left["node"], right["node"]),
            "rules": sorted(rules),
            "same_abstraction_level": left["abstraction_level"] == right["abstraction_level"],
            "left": left,
            "right": right,
        })
    out.sort(key=lambda p: p["pair"])
    return out


def _mentions_id(text: str, node_id: str) -> bool:
    """note 裡有沒有**這個 id 本身**（不是它的前綴）。

    ⚠ 裸的 `in` 會假命中：`tech:nand` 是 `tech:nand_flash` 的子字串，於是 `tech:nand` 會
    被每一筆 nand 家族的 note「提到」。2026-09-18 首版就是這樣寫的，**被本模組自己的測試
    當場抓到**。所以用 id 邊界：前後都不得緊接 word 字元。
    """
    pattern = re.compile(r"(?<![\w:])" + re.escape(node_id) + r"(?!\w)")
    return pattern.search(text) is not None


def _belongs_to(node_id: str, canonical_id: str, entry: Mapping[str, Any]) -> bool:
    """這個 id 屬於這筆登記嗎——是 canonical、是 alias、或 note 逐字提過它。

    三者缺一不可：`tech:nand` 是 [505] 那筆的 **canonical**，它的 note 不會再寫一次自己的
    id；而 `tech:3d_nand_manufacturing` 只出現在 note 裡。只查 note 會漏掉前者，
    只查 canonical/alias 會漏掉後者——而那一對正是「已經有書面決定」的實例。
    """
    if node_id == canonical_id or node_id in (entry.get("aliases") or ()):
        return True
    return _mentions_id(str(entry.get("note") or ""), node_id)


def registry_mentions(pair: Sequence[str], canonical: Mapping[str, Mapping[str, Any]]
                      ) -> list[dict[str, Any]]:
    """registry 裡有哪幾筆登記**同時涵蓋這兩個 id**（canonical／alias／note 逐字）。

    ⚠ 只回答「有沒有提到」，不回答「它說了什麼」——後者要人讀，所以 note 原文一起回傳。
    """
    a, b = pair
    hits: list[dict[str, Any]] = []
    for canonical_id, entry in canonical.items():
        if _belongs_to(a, canonical_id, entry) and _belongs_to(b, canonical_id, entry):
            hits.append({
                "canonical": canonical_id,
                "basis": entry.get("basis"),
                "approval_receipt": entry.get("approval_receipt"),
                "note": str(entry.get("note") or ""),
            })
    return sorted(hits, key=lambda h: h["canonical"])


def bucketize(pairs: Iterable[Mapping[str, Any]],
              canonical: Mapping[str, Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """候選對 → `{"unmentioned": [...], "mentioned": [...]}`，每一對帶上 registry 命中。"""
    buckets: dict[str, list[dict[str, Any]]] = {"unmentioned": [], "mentioned": []}
    for pair in pairs:
        enriched = dict(pair)
        mentions = registry_mentions(pair["pair"], canonical)
        enriched["registry_mentions"] = mentions
        buckets["mentioned" if mentions else "unmentioned"].append(enriched)
    return buckets


def scan(session) -> list[dict[str, Any]]:
    """Neo4j → 節點列（raw）。分桶與比對都是純函式，方便測試與 artifact 共用。"""
    return [dict(r) for r in session.run(SCAN_CYPHER, prefixes=list(ENTITY_PREFIXES))]


def _fmt_node(view: Mapping[str, Any]) -> list[str]:
    out = [f"- `{view['node']}`　{view.get('name') or ''}"
           f"　〔{view.get('abstraction_level') or '—'}｜邊 {view['degree']}"
           f"｜逐字 {view['quote_count']} 段〕"]
    for q in view["quotes"]:
        locator = f"（{q['locator']}）" if q.get("locator") else ""
        out.append(f"    > {q['quote']}{locator}")
    hidden = view["quote_count"] - len(view["quotes"])
    if hidden > 0:
        out.append(f"    > …另有 {hidden} 段逐字（`python -m query.structure {view['node']} --quotes`）")
    if view["quote_count"] == 0:
        out.append("    > ⚠ **這個節點一段逐字都沒有**——它可能是抽取副產品，不是實體")
    return out


def render_markdown(pairs: Iterable[Mapping[str, Any]], *, node_total: int) -> list[str]:
    pairs = list(pairs)
    buckets: dict[str, list[Mapping[str, Any]]] = {"unmentioned": [], "mentioned": []}
    for pair in pairs:
        buckets["mentioned" if pair.get("registry_mentions") else "unmentioned"].append(pair)
    involved = {n for p in pairs for n in p["pair"]}
    same_level = sum(1 for p in pairs if p["same_abstraction_level"])

    out = ["", f"# {TITLE}", ""]
    out.append(
        f"候選 **{len(pairs)}** 對｜同層 {same_level}｜涉及節點 {len(involved)}／{node_total}"
        f"｜registry 提過 {len(buckets['mentioned'])}｜**沒人提過 {len(buckets['unmentioned'])}**"
    )
    out += ["", "> " + "\n> ".join(THIS_IS_NOT), ""]

    for key, heading in (
        ("unmentioned", "## 沒人提過（這些要人看）"),
        ("mentioned", "## registry 的 note 提過（先讀它說了什麼，再決定要不要重開）"),
    ):
        rows = buckets[key]
        if not rows:
            continue
        out += ["", heading, ""]
        for pair in rows:
            rules = "＋".join(RULE_LABELS[r] for r in pair["rules"])
            level = "同層" if pair["same_abstraction_level"] else "**不同層**"
            out.append(f"### `{pair['pair'][0]}` ↔ `{pair['pair'][1]}`　〔{rules}｜{level}〕")
            out += _fmt_node(pair["left"])
            out += _fmt_node(pair["right"])
            for hit in pair.get("registry_mentions") or ():
                receipt = hit.get("approval_receipt") or "無 receipt"
                out.append(f"  - 📄 `{hit['canonical']}`（{hit.get('basis')}／{receipt}）："
                           f"{hit['note']}")
            out.append("")
    return out


def main() -> int:
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    from identity import entities

    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("請設 NEO4J_PASSWORD")
        return 2
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    try:
        with driver.session() as session:
            rows = scan(session)
    finally:
        driver.close()
    pairs = pair_candidates(rows)
    buckets = bucketize(pairs, entities.load())
    print("\n".join(render_markdown(
        buckets["unmentioned"] + buckets["mentioned"], node_total=len(rows))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
