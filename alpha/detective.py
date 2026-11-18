"""偵探（計畫外線索組裝）第一版的純邏輯：鄰居的角色、文件的日期、回溯包的清理、問句、派工提示、核引文。

使用者 2026-11-18「都做吧 做出一版我們再繼續精進」；M0 的設計、預先登記的回溯評分與結果在
`docs/reports/phase7/detective-m0-2026-11-18.md`。流程住 `skills/detective/SKILL.md`：
`alpha detective pack`（機械組包）→ 強模型唯讀子代理照 PROMPT.md 回報 → 主 session 存成 REPORT.md →
`alpha detective verify`（核引文）→ 主 session 把核過的線索寫進敘事、每條登 watch。

**為什麼照圖組包、不叫模型「想深一點」**：M0 最有用的線索都來自兩份不同當事人的文件對在一起
（AOI 的 10-Q＋雲南鍺業的公告算出 2027 年 4 吋每片單價），那兩個當事人在圖上就是這家的鄰居
（L18：根解是拿掉資訊落差）。問句由鄰居的角色機械產生——機械的用途是生出問句，不是代答（L18）。

本模組沒有任何 I/O：讀圖、讀名冊、掃自家庫、讀共識、寫包都在 `alpha/providers/detective.py`。
不寫任何 authority、不跑 LLM、不對外連線、不碰價格。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Collection, Iterable, Mapping, Sequence

#: 鄰居的角色（圖上的邊 → 偵探要問它什麼）。順序＝清單與問句的順序。
ROLE_LABELS: Mapping[str, str] = {
    "customer": "客戶",
    "supplier": "供應商",
    "competitor": "對手",
    "layer_peer": "同層供應商",
    "layer_buyer": "同層買方",
    "rival_customer": "對手的客戶",
    "other": "其他關係",
}
#: 同一層的「買方」關係：吃這一層的公司（圖上 company -[rel]-> 層節點）。
LAYER_BUYER_RELS = frozenset({"DEPENDS_ON", "CONSTRAINED_BY", "USES", "CONSUMES"})
#: 四個抽屜（回報固定分類）；窗口提早關至少一條——只找好故事的偵探沒有用。
DRAWERS = ("量超前", "漲價", "撐更久", "窗口提早關")


def role_of(rel: str, outgoing: bool, via: str | None, hop: int = 1) -> str:
    """一條邊 → 角色。`outgoing`＝邊從目標公司出發；`via`＝經過的層節點（一跳時為 None）；
    `hop=2`＝同層對手（或直接對手）的客戶——`via` 是那家對手。
    M0：價格線索來自 AOI 的 10-Q 對上雲南鍺業的公告，AOI 不是 AXT 的鄰居、是同層對手雲南鍺業的客戶（第二跳）。"""
    rel = str(rel or "").upper()
    if hop == 2:
        return "rival_customer"
    if via is None:
        if rel == "SUPPLIES_TO":
            return "customer" if outgoing else "supplier"
        if rel == "COMPETES_WITH":
            return "competitor"
        return "other"
    if rel == "SUPPLIES_TO":
        return "layer_peer"
    if rel in LAYER_BUYER_RELS:
        return "layer_buyer"
    return "other"


@dataclass
class Neighbor:
    company_id: str
    name: str
    roles: set[str] = field(default_factory=set)
    vias: set[str] = field(default_factory=set)

    def role_text(self) -> str:
        return "、".join(ROLE_LABELS[r] for r in ROLE_LABELS if r in self.roles)


def neighbors_from_rows(target_id: str, rows: Iterable[Mapping[str, object]]) -> list[Neighbor]:
    """查圖的列（`rel`、`out`、`nid`、`name`、`via`）→ 合併後的鄰居。同一家多個角色併成一筆；目標自己不列。"""
    out: dict[str, Neighbor] = {}
    for row in rows:
        nid = str(row.get("nid") or "")
        if not nid or nid == target_id:
            continue
        via = row.get("via")
        via = str(via) if via else None
        nb = out.setdefault(nid, Neighbor(company_id=nid, name=str(row.get("name") or nid)))
        nb.roles.add(role_of(str(row.get("rel") or ""), bool(row.get("out")), via, int(row.get("hop") or 1)))
        if via:
            nb.vias.add(via)
    order = list(ROLE_LABELS)
    return sorted(out.values(), key=lambda n: (min(order.index(r) for r in n.roles), n.name))


# ---- 文件的日期（INV-6：答不出「T 時刻知道什麼」就不收進回溯包）------------------------------
_HEADER_DATE = re.compile(r"^(?:PUBLISHED|DATE|FILED)[^:：\n]*[:：]\s*(20\d{2})-(\d{2})-(\d{2})", re.M)
_ISO = re.compile(r"(?<!\d)(20\d{2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})(?!\d)")
_NAME_DATE = re.compile(r"(?<!\d)(20\d{2})[-_]?(\d{2})[-_]?(\d{2})(?!\d)")


def _valid(y: str, m: str, d: str) -> date | None:
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def _meta_date(meta: Mapping[str, object] | None) -> date | None:
    for key in ("published_at", "filed_date"):        # 不拿 retrieved_at 冒充（INV-6、L11-5）
        m = _ISO.search(str((meta or {}).get(key) or ""))
        if m and (d := _valid(*m.groups())):
            return d
    return None


def doc_date(name: str, head: str, meta: Mapping[str, object] | None = None) -> date | None:
    """發布日：旁邊 `.meta.json` 的 `published_at`／`filed_date` 優先（年報、逐字稿的日期多半只寫在那裡），
    其次檔頭 `PUBLISHED:`（或 DATE／FILED），再其次檔名裡第一個合法日期，
    最後是檔頭前兩行（「來源：…季度截至 2026-09-30，2026-11-05 申報…2026-11-06 取得」型）裡**最晚**的日期；都沒有回 None。
    ⚠ 檔名的「fy2026_20260817」會先撞到「2026_20…」——不合法的月日跳過、找下一個（M0 實測）。
    ⚠ 前兩行取最晚、不取第一個：第一個常是季度截止日，取它會讓回溯包收進回溯日之後才申報的檔（INV-6）；
    取最晚只會偏晚——偏晚在回溯被排除，不會洩漏。"""
    if d := _meta_date(meta):
        return d
    m = _HEADER_DATE.search(head or "")
    if m and (d := _valid(*m.groups())):
        return d
    for m in _NAME_DATE.finditer(name or ""):
        if d := _valid(*m.groups()):
            return d
    top = "\n".join((head or "").splitlines()[:2])
    found = [d for y, mo, dd in _ISO.findall(top) if (d := _valid(y, mo, dd))]
    return max(found) if found else None


_OUR_HEADER = re.compile(r"^(?:SOURCE|NOTE|RETRIEVED|STORAGE|Source URL|Excerpt|來源)\s*[:：]|\[EXCERPT|\bRetrieved\s*[:：]",
                         re.M | re.I)


def has_our_header(head: str) -> bool:
    """我們寫的節錄檔（檔頭有 SOURCE／Source URL／Excerpt／來源／[EXCERPT／Retrieved 之一）；EDGAR 等全文沒有這種檔頭。
    ⚠ 只認大寫 SOURCE 那一型會漏掉約 96 份（「Source URL:」「來源：」「Published: … | Retrieved: …」型；v1 實測）。"""
    return bool(_OUR_HEADER.search(head or ""))


# ---- 回溯包的清理：拿掉我們後來寫的字 ------------------------------------------------------------
_HEADER_DROP = re.compile(r"^(NOTE|RETRIEVED|STORAGE|CROSS-CHECK)\s*[:：]")
_OWN_MARKERS = re.compile(r"推一步|讀圖|敘事|我們|drain|\bew_\d|\bsr_[0-9a-f]{6}|\bib_[0-9a-f]{6}"
                          r"|re-verified|追加|更正|取得）|\bRetrieved\s*[:：]", re.I)
_CJK_YMD = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?")
_MD = re.compile(r"(?<![\d年\-/.])(\d{1,2})-(\d{1,2})(?![\d\-/.])")


def _mentions_after(line: str, as_of: date) -> bool:
    for y, m, d in _ISO.findall(line):
        if (day := _valid(y, m, d)) and day > as_of:
            return True
    for y, m, d in _CJK_YMD.findall(line):
        month_start = _valid(y, m, "1")
        if month_start and (month_start > as_of or (d and (day := _valid(y, m, d)) and day > as_of)):
            return True
    for m, d in _MD.findall(line):           # 「11-12」型（沒寫年份）：照回溯年份推
        if (day := _valid(str(as_of.year), m, d)) and day > as_of:
            return True
    return False


def sanitize_excerpt(text: str, as_of: date) -> tuple[str, int]:
    """我們寫的節錄檔 → 回溯包用的版本：拿掉檔頭的 NOTE 等、我們自己的評語、提到 as_of 之後日期的行。回（文字, 拿掉幾行）。
    只用在 `has_our_header` 為真的檔；EDGAR 等全文照抄（它們不含我們後來寫的字）。
    ⚠ 刻意偏保守：原文裡寫到 as_of 之後的日期（合約期間、到期日）也一起拿掉——分不出那一行是原文還是我們後來補的；
    回溯是拿來量偵探的，寧可少給、分數偏低，不可洩漏、分數虛高（INV-5）。現況包不清理。"""
    kept: list[str] = []
    dropped = 0
    for line in text.splitlines():
        if _HEADER_DROP.match(line) or _OWN_MARKERS.search(line) or _mentions_after(line, as_of):
            dropped += 1
            continue
        kept.append(line)
    return "\n".join(kept) + "\n", dropped


# ---- 問句（由鄰居的角色機械產生）--------------------------------------------------------------
@dataclass(frozen=True)
class DocInfo:
    name: str
    published: date | None
    named: tuple[str, ...]      # 這份文件點名了哪些公司（company_id）
    root: str | None = None     # 不在自家庫時的資料夾（回溯補抓）；None＝library/raw


def _docs_line(docs: Sequence[DocInfo]) -> str:
    if not docs:
        return "庫裡 0 份點名它的文件——這個洞本身就是線索：要什麼文件、去哪拿"
    dated = [d.published for d in docs if d.published]
    latest = max(dated).isoformat() if dated else "日期不明"
    return f"庫裡 {len(docs)} 份點名它的文件，最新 {latest}"


def build_questions(company: str, neighbors: Sequence[Neighbor], docs_by_company: Mapping[str, Sequence[DocInfo]],
                    consensus_lines: Sequence[str], *, with_narrative: bool) -> list[str]:
    """問句清單。每個鄰居照角色問一題（庫裡沒有它的文件也問——沒有本身是洞，INV-3）；另有固定的五題。"""
    qs: list[str] = []
    if consensus_lines:
        target = "敘事『量級』那一格的②（量的天花板）與計畫路徑" if with_narrative else "公司文件寫的擴產計畫"
        qs.append("共識：" + "；".join(consensus_lines) + f"。{target}和共識差多少？差出來的那一段是量、價還是時間？"
                  "哪些計畫外的東西還沒被寫進去，哪些會讓共識往下修？")
    else:
        qs.append("共識：沒有資料（Engine C 沒有這檔的會計年度共識）——分析師寫到哪裡判不出，回報要說出來。")
    for nb in neighbors:
        line = _docs_line(docs_by_company.get(nb.company_id) or ())
        if nb.roles & {"customer", "layer_buyer"}:
            qs.append(f"{nb.role_text()} {nb.name}（{line}）：它自己的擴產、採購承諾、長約、預付、庫存，換算成對 {company} 的量，"
                      f"超過 {company} 公告的計畫嗎？它給 {company} 的約與給別家的約，年限與金額差多少？它是在加需求還是在分散來源？")
        if nb.roles & {"competitor", "layer_peer"}:
            qs.append(f"{nb.role_text()} {nb.name}（{line}）：產能時程、合約金額 ÷ 數量（單價）、出口許可——能三角出單價或漲幅嗎？"
                      f"最早什麼時候、哪一件事讓 {company} 的量或價轉弱？")
        if nb.roles & {"supplier"}:
            qs.append(f"{nb.role_text()} {nb.name}（{line}）：它給 {company} 的設備或料的訂單、交期、擴產，能不能比 {company} "
                      "自己的公告更早看出產能？")
        if "rival_customer" in nb.roles:
            qs.append(f"{ROLE_LABELS['rival_customer']} {nb.name}（{line}）：它和對手的約——金額、數量、年限、交貨期——"
                      f"能不能和對手那一側的公告對起來算出單價或份額？它為什麼不是（或還不是）{company} 的客戶？"
                      f"它的採購轉向會讓 {company} 多拿還是少拿？")
        if nb.roles == {"other"}:
            qs.append(f"{nb.role_text()} {nb.name}（{line}）：這條關係（投資、合作）會讓 {company} 的量、價或時間變嗎？")
    qs.append(f"{company} 自己的融資、土地、資本支出、在建工程：用同層任何一份擴產案的「投資額 ÷ 新增產能」換算，超出公告計畫嗎？")
    qs.append("各買方長約的年限與金額分布：短缺撐到哪一年？"
              f"{company} 的份額有沒有跟著鎖到那一年，還是最大的單在別家？")
    qs.append("買方的庫存、多來源、預付說法：在手訂單裡有多少是保險性的量，供給鬆動時最先退？")
    return qs


# ---- 派工提示（唯一一份；skill 只說用它，不另抄——L16）----------------------------------------
PROMPT_TEMPLATE = """你是一位唯讀的研究偵探{as_of_role}。任務：把我們已經讀過的文件拼起來，找出 {company}（{ticker}）「公司已公告的計畫與分析師共識以外」的線索——還沒被寫進去、可能讓量或價比預期多（或少）的破口。

## 鐵則
- **只能讀這個線索包列出的檔案**：{read_scope}。清單外的檔一律不開，就算它在同一個資料夾。
{as_of_rule}- 唯讀：不寫任何檔案、不 commit、不跑會改資料的命令。用 Read／Grep／Glob；Bash 只准唯讀的 grep／sed。
- 不對外連線：不上網、不呼叫任何外部 API；任何對外請求都不得帶 email 或個人資訊（本任務根本不需要對外）。
- 不看價格與市場資料：不要開 library/private/app、library/private/engine_c、任何 *.db、docs/reports、library/private/broker_reports。
- 引文逐字照抄（保留原文語言），附「檔名:行號」。推論每一步標「推一步」。「我找不到」和「它不存在」分開寫——寫「沒有」之前先問：如果答案存在，它會在手上哪份文件的哪一節？
- 供應商自己說的是弱證據；最好的線索來自「兩份不同當事人的文件放在一起才看得出來」的地方（買方的擴產＋賣方的合約、設備商的訂單＋公司的資本支出、買賣雙方各寫一半的合約金額與數量）。
- 不給目標價、價格區間、報酬率、買賣建議、跨公司排序。
- 用繁體中文寫（引文保留原文）。

## 材料
{materials}

## 機械問句（由圖上鄰居的角色產生；逐題回答，答不了寫為什麼）
{questions}

## 回報格式（最終訊息就是交付物，不要寫檔）
### 線索（最多 8 條；四個抽屜：{drawers}——窗口提早關至少 1 條）
每條：
- 抽屜
- 觀察：逐字引文（檔名:行號），至少一條來自 {company} 以外的當事人
- 推論鏈：①②③（每步標「推一步」或指回引文）
- 這代表計畫外的什麼（公告計畫是什麼、這條多出或少掉什麼）
- 共識寫進去了沒（對照上面的共識；判不出就寫判不出）
- 最可能讓它錯的解釋
- 驗證：什麼文件、誰發、大約何時、去哪拿（使用者有元大、凱基、IB、嘉信帳號，可拿券商報告）
- 信心：高／中／低＋一句理由
### 逐題回答（每題 2–5 句）
### 偵探版敘事（≤ 400 字）：照計畫走的部分 vs 計畫外的部分；計畫外的每一句指回線索編號
### 答不了的問句：每題是「我找不到」（應該在哪份文件哪一節）還是「它不存在」
### 想要但庫裡沒有的文件（最多 5 份，寫清楚誰發、哪一期、為什麼）
"""


def render_prompt(*, company: str, ticker: str, read_scope: str, materials: str, questions: Sequence[str],
                  as_of: date | None) -> str:
    as_of_role = f"，身在 **{as_of.isoformat()}**" if as_of else ""
    as_of_rule = (f"- **不要用你自己對 {as_of.isoformat()} 之後的任何記憶**：如果你知道之後發生了什麼，當作不知道；"
                  "結論只能來自清單裡的文件。\n") if as_of else ""
    return PROMPT_TEMPLATE.format(
        as_of_role=as_of_role, company=company, ticker=ticker, read_scope=read_scope, as_of_rule=as_of_rule,
        materials=materials, questions="\n".join(f"Q{i} {q}" for i, q in enumerate(questions, 1)),
        drawers="／".join(DRAWERS))


# ---- 核引文 ------------------------------------------------------------------------------------
_REF = re.compile(r"([A-Za-z0-9_\-.]+\.(?:txt|jsonl|json|md)):(\d+)")
_QUOTE = re.compile(r"「([^」]{6,})」|“([^”]{6,})”|\"([^\"]{6,})\"")


def _norm(text: str) -> str:
    text = (text.replace("&#160;", " ").replace("&#8217;", "'").replace("’", "'").replace("‘", "'")
            .replace("“", '"').replace("”", '"'))
    return re.sub(r"[\s　]+", "", text)


@dataclass(frozen=True)
class QuoteCheck:
    status: str          # ok｜line_off｜missing｜no_file
    file: str
    line: int
    quote: str
    in_manifest: bool | None = None     # None＝沒給清單（不判）；False＝子代理讀了包外的檔（M0 現況越界一次）


def verify_report(report: str, read_lines: Callable[[str], Sequence[str] | None],
                  allowed: Collection[str] | None = None) -> list[QuoteCheck]:
    """回報裡每個「檔名:行號」往前找最近一段引號文字，看它（去空白後；「…」切段各自要在）是否逐字在那份檔、在不在標的行附近。
    `read_lines(檔名) -> 行 | None`（None＝找不到檔）由 provider 給。引文沒有引號包著的不核（只能人讀）。"""
    out: list[QuoteCheck] = []
    prev_end = 0
    for m in _REF.finditer(report):
        name, line = m.group(1), int(m.group(2))
        # 往前找引文不越過上一個「檔名:行號」：否則沒引號的引用會抓到上一條的引文、誤報原文沒有
        quotes = list(_QUOTE.finditer(report[max(prev_end, m.start() - 600):m.start()]))
        prev_end = m.end()
        if not quotes:
            continue
        quote = next(g for g in quotes[-1].groups() if g)
        listed = None if allowed is None else name in allowed
        lines = read_lines(name)
        if lines is None:
            out.append(QuoteCheck("no_file", name, line, quote, listed))
            continue
        parts = [_norm(p) for p in re.split(r"…|\.\.\.", quote) if len(_norm(p)) >= 6]
        whole = _norm("\n".join(lines))
        if not parts or not all(p in whole for p in parts):
            out.append(QuoteCheck("missing", name, line, quote, listed))
            continue
        near = _norm("".join(lines[max(0, line - 4):line + 3]))
        out.append(QuoteCheck("ok" if all(p in near for p in parts) else "line_off", name, line, quote, listed))
    return out
