"""敘事逐句核對（2026-11-12 使用者「先修吧」）——**純規則，不讀不寫任何檔**：引用解析、名冊、上一版的核對紀錄都由呼叫端注入
（`alpha.providers.fact_checks`）。

## 為什麼

事實抽樣①（registration 2026-11-03）累積 11 份、8 份至少一句與它引用的一手不符（73%，過了 ≥ 30% 的判讀線）。錯的形狀：
把引用收窄或放寬一格（主詞、數量、出處歸屬）、日期錯、數字過精。寫的當下沒有一步逐句對過原文——這支補那一步。

## 它做什麼

把一版敘事（七格、候選理由、深挖清單）與它的故事切成句，每一句：

1. 列出它引用的原文裡**對得上的那幾行**（檔名：行號）——讀的人一句一句並排對，不必自己翻檔；
2. 標出機械看得出的疑點（`FLAG_KINDS`）：引號裡的字不在原文、數字（年份、日期、月份、季、百分比、金額、數量詞）對不回原文、
   英文名稱或名冊公司名不在原文、限定詞（主要、多數、唯一、首家……）在對到的那幾行找不到對應字、整句沒對到任何一行、
   句子有數字或名稱但引用全是這裡核不了的種類（Engine C、三題、外部網址）；2026-11-13 起另一種：對得上的只有我們自己寫的字
   （節錄檔的 NOTE 段與改寫、讀圖判讀、自家筆記——`SourceLine.own`；列出來的那一行也標「自家文字」）。
   保留語氣被拿掉（expected 寫成已發生）量過、機械查不準，不在這裡（`qualifier_problems` 之後的註記）。

## 它不做什麼

**判定一句對不對的是讀的人**——機械偵測器的用途是自動生出問句，不是自動修（L18）。沒有旗標不等於對：主詞收窄（「多數相關業者」
寫成「主要半導體廠多數」）字面上每個詞都對得到，只有把句子和列出的原文行並排讀才看得出來。它不擋寫入、不改候選狀態、不寫 watch。

反證與加碼條件是對未來的條件（寫入即登記成 watch），不在逐句核對範圍——輸出開頭照寫，不靜默略過（INV-3）。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Iterable, Mapping, Sequence

from .hanzi_fold import T2S_TABLE

#: 旗標（封閉字彙；輸出、紀錄、測試都從這裡列舉——L16）。
FLAG_KINDS: Mapping[str, str] = {
    "quote_missing": "引號裡的字不在引用的原文",
    "number_missing": "數字對不回引用的原文",
    "name_missing": "名稱不在引用的原文",
    "qualifier_missing": "限定詞在對到的原文行找不到對應字",
    "own_text_only": "只對到我們自己寫的字（註記、改寫、讀圖判讀、筆記），一手原文沒對到",
    "no_match": "沒對到引用原文的任何一行",
    "unverifiable": "有數字或名稱，但引用全是這裡核不了的種類",
}
#: 引用的種類（`classify_ref`）。前四種讀成原文行；後三種這裡核不了，照數（INV-3：核不了不是核過）。
REF_KINDS: Mapping[str, str] = {
    "raw": "一手節錄（library/raw）",
    "graph_source": "圖的來源文件（逐字引文與同名節錄）",
    "reading": "讀圖（判讀文字與它引用的逐字）",
    "note": "自家筆記（library/private、thesis；不是一手）",
    "authority": "authority 數字（Engine C、三題）",
    "url": "外部網址（離線核不了）",
    "other": "其他（核不了）",
}
READABLE_REF_KINDS: tuple[str, ...] = ("raw", "graph_source", "reading", "note")
#: 對到的行最多印幾行；整句覆蓋率低於這個數算「沒對到」（2026-11-12 以事實抽樣抽過的 11 份校準）。
TOP_LINES = 2
NO_MATCH_BELOW = 0.12
SHOW_LINE_ABOVE = 0.05
LINE_WINDOW = 220

_PLACEHOLDER = re.compile(r"\{[^{}]*\}")
_CJK_CHAR = "㐀-鿿぀-ヿ豈-﫿"
_CJK = re.compile(f"[{_CJK_CHAR}]")


#: 商標符號先換成空白：NFKC 會把「™」變成「TM」黏在字尾（POET 20-F「Blazar™」→ blazartm，名稱對不到；SIVE.ST 11-12）。
#: 圈號同理：NFKC 把「④」變成「4」，「④2028 年以後」讀成 42028（002428.SZ 11-12）
_MARKS = str.maketrans({"™": " ", "®": " ", "©": " ", "℠": " ", **{chr(c): " " for c in range(0x2460, 0x2474)}})


def fold(text: Any) -> str:
    """比對用：NFKC（全形→半形）、小寫、繁體與日文新字體→簡體（`hanzi_fold`）。不改寫任何輸出。"""
    return unicodedata.normalize("NFKC", str(text or "").translate(_MARKS)).lower().translate(T2S_TABLE)


def squash(text: Any) -> str:
    """`fold` 再去掉所有空白——中日文引文的比對單位。"""
    return re.sub(r"\s+", "", fold(text))


def spaced(text: Any) -> str:
    """`fold` 再把空白收成一格——英文詞要靠空白分界。"""
    return " ".join(fold(text).split())


def _plain(text: Any) -> str:
    """NFKC＋小寫，不折疊字形：抽數字與名稱用（印回去的是句子原本的字）。"""
    return unicodedata.normalize("NFKC", str(text or "").translate(_MARKS)).lower()


def strip_placeholders(text: Any) -> str:
    """`{placeholder}` 由 authority 填，不是寫的人的主張——比對與抽數字前拿掉。"""
    return _PLACEHOLDER.sub(" ", str(text or ""))


# ---------------------------------------------------------------------------
# 切句
# ---------------------------------------------------------------------------

_OPEN = "（(「『“【["
_CLOSE = "）)」』”】]"


def _split(text: str, *, respect_brackets: bool) -> list[str] | None:
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if respect_brackets:
            if ch in _OPEN:
                depth += 1
            elif ch in _CLOSE:
                depth = max(0, depth - 1)
        buf.append(ch)
        if ch == "\n" or (ch in "。；" and depth == 0):
            piece = "".join(buf).strip()
            if piece.strip("。；"):
                out.append(piece)
            buf = []
    piece = "".join(buf).strip()
    if piece.strip("。；"):
        out.append(piece)
    if respect_brackets and depth > 0:
        return None
    return out


def split_sentences(text: Any) -> list[str]:
    """以「。」「；」與換行切句（事實抽樣①同一個切法）；括號與引號裡的不切——引文裡的句號不是我們的句子。
    括號沒收好時退回不看括號，不讓一個漏掉的右括號吞掉後面整段。"""
    raw = str(text or "")
    out = _split(raw, respect_brackets=True)
    return out if out is not None else (_split(raw, respect_brackets=False) or [])


# ---------------------------------------------------------------------------
# 要核的句子
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BriefText:
    """要核的那一版：寫入後的紀錄或還沒寫的 spec 都轉成這個形狀（`brief_text_from_record`／`brief_text_from_spec`）。"""

    ticker: str
    company_id: str
    brief_id: str | None                      # None＝草稿（還沒寫入）
    slots: tuple[tuple[str, str, tuple[str, ...]], ...]   # (格, 正文, 引用)
    candidate_reason: str = ""
    depth_check: tuple[tuple[str, str], ...] = ()
    #: 寫的那天：之後的日子（自己設的到期、未來的排程）不核。None＝不分（全部核）
    as_of: date | None = None

    @property
    def all_refs(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for _key, _text, refs in self.slots:
            for r in refs:
                seen.setdefault(r, None)
        return tuple(seen)


def brief_text_from_record(brief: Any) -> BriefText:
    state = getattr(brief, "candidate_state", None)
    return BriefText(
        ticker=str(brief.ticker), company_id=str(brief.company_id), brief_id=str(brief.brief_id),
        slots=tuple((s.key, s.text, tuple(s.evidence_refs)) for s in brief.slots),
        candidate_reason=str(getattr(state, "reason", None) or ""),
        depth_check=tuple(getattr(brief, "depth_check", ()) or ()), as_of=brief.created_at.date())


def brief_text_from_spec(spec: Mapping[str, Any], *, ticker: str, company_id: str, as_of: date | None = None) -> BriefText:
    """`python -m alpha brief <T> --add` 的 spec（`{"slots": {格: {"text", "evidence_refs"}}, "candidate_state", "depth_check"}`）。"""
    from .contracts import SLOT_KEYS_V2

    slots_raw = spec.get("slots") or {}
    if not isinstance(slots_raw, Mapping):
        raise ValueError("spec.slots 必須是 {格: {text, evidence_refs}}")
    order = [k for k in SLOT_KEYS_V2 if k in slots_raw] + [k for k in slots_raw if k not in SLOT_KEYS_V2]
    slots = []
    for key in order:
        body = slots_raw[key] or {}
        slots.append((str(key), str(body.get("text") or ""), tuple(str(r) for r in body.get("evidence_refs") or ())))
    state = spec.get("candidate_state") or {}
    depth = spec.get("depth_check") or {}
    return BriefText(ticker=str(ticker), company_id=str(company_id), brief_id=None, slots=tuple(slots),
                     candidate_reason=str(state.get("reason") or "") if isinstance(state, Mapping) else "",
                     depth_check=tuple((str(k), str(v)) for k, v in depth.items()) if isinstance(depth, Mapping) else (),
                     as_of=as_of)


@dataclass(frozen=True)
class Sentence:
    n: int
    where: str                    # 格：slot key／candidate／depth:<鍵>／story:<格>／story:candidate
    text: str
    refs: tuple[str, ...]         # 先對這幾條（那一格的引用；深挖清單寫在值裡的；故事兩格自帶的）
    fallback_refs: tuple[str, ...] = ()   # 自己那幾條對不到時再看整份敘事的引用（引用指偏，事實抽樣 688020.SS）
    #: 「錯的訊號…：」清單裡的一條（同一格裡那一句與它之後的句子）——對未來的條件，只核引號（COHR 11-12：第二條沒有
    #: 「錯的訊號」開頭也沒有「第 N 條」，被當成事實句標「沒對到」）
    condition: bool = False

    @property
    def digest(self) -> str:
        """同一句話對同一組引用＝同一個 digest；上一版核過的這一句不必再核（`carried`）。"""
        payload = squash(self.text) + "|" + "|".join(sorted(self.refs))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


#: 全形「：」不收進引用（「…_excerpt.txt：H 股規模…」：檔名後面接說明）；行號用的半形「:」照收
_INLINE_REF = re.compile(r"(?:library/(?:raw|private)/|thesis/)[^\s，,；;（(）)、：]+|sr_[0-9a-f]{16}|graph://source/[^\s，,；;（(）)、：]+"
                         r"|https?://[^\s，,；;（(）)、：]+|(?:alpha|engine_c)://[^\s，,；;（(）)、：]+")
#: 檔名本身可能帶逗號（券商報告標題「…MEMS進入高速成長期，CPO蓄勢待發_中文.pdf」，300757.SZ 11-12）：路徑停在逗號、還沒有副檔名時，
#: 逗號後面那一段（不跨斜線）以副檔名收尾就接回去——否則前半段被報成「找不到這個檔」、後半段混進要核的字
_FILE_EXT = re.compile(r"\.(?:txt|pdf|md|json|jsonl|html?|csv|xlsx?)$", re.IGNORECASE)
_COMMA_TAIL = re.compile(r"[，,][^\s；;（(）)、：/]*?\.(?:txt|pdf|md|json|jsonl|html?|csv|xlsx?)(?![^\s，,；;（(）)、：])",
                         re.IGNORECASE)
_ADDON_ONLY = re.compile(r"^加碼條件：c\d+\s*$")


def _inline_ref_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for m in _INLINE_REF.finditer(text):
        start, end = m.span()
        if text.startswith(("library/", "thesis/"), start) and not _FILE_EXT.search(text[start:end]):
            tail = _COMMA_TAIL.match(text, end)
            end = tail.end() if tail else end
        spans.append((start, end))
    return spans


def _depth_items(entries: Iterable[tuple[str, str]]) -> list[tuple[str, str, tuple[str, ...]]]:
    """深挖清單的每一項：(鍵, 去掉引用之後的字, 寫在值裡的引用)。只寫「加碼條件：c<n>」或「缺…」的不核（沒有主張）。"""
    out = []
    for key, value in entries:
        text = str(value or "").strip()
        if not text or _ADDON_ONLY.match(text) or text.startswith("缺"):
            continue
        spans = _inline_ref_spans(text)
        refs = tuple(dict.fromkeys(text[a:b].rstrip("。.") for a, b in spans))
        rest = text
        for a, b in reversed(spans):
            rest = rest[:a] + " " + rest[b:]
        rest = rest.strip(" ＋+、，,；;（）()：:")
        if len(squash(rest)) < 4:
            continue
        out.append((key, rest, refs))
    return out


def build_sentences(brief: BriefText, *, story: Mapping[str, Any] | None = None) -> list[Sentence]:
    """一版敘事（與它的故事；None＝不核故事）切成句，順序＝七格、候選理由、深挖清單、故事各格、故事的候選理由。"""
    from .story import STORY_ONLY_KEYS, STORY_SLOT_KEYS

    every = brief.all_refs
    by_slot = {key: refs for key, _text, refs in brief.slots}
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    for key, text, refs in brief.slots:
        rows += [(key, s, refs) for s in split_sentences(text)]
    rows += [("candidate", s, every) for s in split_sentences(brief.candidate_reason)]
    for key, text, refs in _depth_items(brief.depth_check):
        rows += [(f"depth:{key}", s, refs or every) for s in split_sentences(text)]
    if story is not None:
        slots = story.get("slots") or {}
        evidence = story.get("evidence") or {}
        for key in STORY_SLOT_KEYS:
            if key not in slots:
                continue
            refs = tuple(evidence.get(key) or ()) if key in STORY_ONLY_KEYS else tuple(by_slot.get(key) or ())
            rows += [(f"story:{key}", s, refs or every) for s in split_sentences(slots[key])]
        cand = (story.get("candidate") or {}).get("story")
        rows += [("story:candidate", s, every) for s in split_sentences(cand)]
    out = []
    listing: str | None = None            # 正在「錯的訊號」清單裡的那一格
    for n, (where, text, refs) in enumerate(rows, 1):
        if _WRONG_SIGNALS.match(text):
            listing = where
        elif listing != where:
            listing = None
        fallback = tuple(r for r in every if r not in refs)
        out.append(Sentence(n=n, where=where, text=text, refs=tuple(refs), fallback_refs=fallback,
                            condition=listing == where))
    return out


_WRONG_SIGNALS = re.compile(r"^\s*(?:錯的訊號|错的讯号)")


# ---------------------------------------------------------------------------
# 引用
# ---------------------------------------------------------------------------

def classify_ref(ref: str) -> str:
    text = str(ref or "").strip()
    if text.startswith("library/raw/"):
        return "raw"
    if text.startswith(("library/", "thesis/")):
        return "note"
    if text.startswith("graph://source/"):
        return "graph_source"
    if re.fullmatch(r"sr_[0-9a-f]{16}", text):
        return "reading"
    if text.startswith(("engine_c:", "alpha://")):
        return "authority"
    if text.startswith(("http://", "https://")):
        return "url"
    return "other"


@dataclass(frozen=True)
class SourceLine:
    label: str          # 印出來的出處（檔名:行號、doc#引文 id、讀圖 id）
    text: str           # 原字
    #: 我們自己寫的字（節錄檔的 NOTE 段與 Research excerpt 改寫、讀圖判讀、自家筆記）：照樣比對、列出來對照（標「自家文字」），
    #: 但一句只對得上這種行時標 `own_text_only`（2026-11-13）。數字、引文、名稱、限定詞**不**改成只對一手：27 份的基準上
    #: 那樣多標的句子邊際命中率低於亂猜（多數錯是改寫一手時寫錯，不是從自家筆記抄來的）
    own: bool = False


@dataclass(frozen=True)
class ResolvedRef:
    ref: str
    kind: str
    lines: tuple[SourceLine, ...] = ()
    problem: str | None = None          # 該讀得到卻讀不到的理由（檔不在、讀圖找不到）
    #: 檔裡宣告的金額單位（「金額單位新台幣仟元」常寫在我們自己的註記行，那一行不算原文、單位照收）：表格的數乘上它也算數
    units: tuple[float, ...] = ()
    #: 文件自己的標示（檔名、出處與日期那幾行）：「11 月上修」「第一季說明資料」講的是文件本身的日期與季別——
    #: 只拿來核日期、月份、季、年份，不拿來核數字、引文、名稱
    meta: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# 原文的特徵（每條引用算一次）
# ---------------------------------------------------------------------------

_EN_STOP = frozenset("""the and of in for with that this from are was were has have its our we to on by as at be or an a
not but also which their they these those than other into more most such been will would could should may can over under per
all any each both only same new year years quarter quarters company companies million billion thousand percent""".split())
_NUM_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?")
_LATIN_TOKEN = re.compile(r"[a-z][a-z0-9\-]{2,}")

#: 中文常用詞 → 英文詞（只用來在英文原文裡找「這句從哪幾行來」，不判對錯）。鍵是 `squash` 之後的簡體。
EN_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("营收", ("revenue", "sales")), ("营业收入", ("revenue", "sales")), ("销售", ("sales", "sold")),
    ("订单", ("order", "booking", "backlog")), ("在手", ("backlog",)), ("毛利", ("gross margin", "gross profit")),
    ("营益", ("operating income", "operating margin")), ("净利", ("net income", "net profit")), ("亏损", ("loss",)),
    ("客户", ("customer", "client")), ("供应商", ("supplier", "vendor")), ("供货", ("suppl",)), ("产能", ("capacity",)),
    ("扩产", ("expan", "capacity")), ("扩厂", ("expan", "facility", "plant")), ("量产", ("mass production", "volume production", "ramp")),
    ("出货", ("ship",)), ("认证", ("qualif", "certif")), ("验证", ("qualif", "validat")), ("数据中心", ("data center", "datacenter")),
    ("资料中心", ("data center", "datacenter")), ("伺服器", ("server",)), ("服务器", ("server",)), ("电源", ("power",)),
    ("电力", ("power", "electric")), ("变压器", ("transformer",)), ("电网", ("grid", "utilit")), ("液冷", ("liquid cool",)),
    ("散热", ("thermal", "cool")), ("雷射", ("laser",)), ("激光", ("laser",)), ("光通讯", ("optical",)), ("晶片", ("chip",)),
    ("芯片", ("chip",)), ("晶圆", ("wafer",)), ("封装", ("packag",)), ("测试", ("test",)), ("设备", ("equipment", "tool", "system")),
    ("材料", ("material",)), ("基板", ("substrate",)), ("载板", ("substrate",)), ("玻璃", ("glass",)), ("铜箔", ("copper foil",)),
    ("合约", ("contract", "agreement")), ("合同", ("contract", "agreement")), ("协议", ("agreement",)), ("框架", ("framework",)),
    ("收购", ("acqui",)), ("并购", ("acqui", "merger")), ("合并", ("merger", "acqui", "consolidat")), ("稀释", ("dilut",)),
    ("增发", ("offering", "issuance")), ("可转债", ("convertible",)), ("负债", ("debt", "liabilit")), ("现金", ("cash",)),
    ("资本支出", ("capital expenditure", "capex")), ("指引", ("guidance", "outlook")), ("展望", ("outlook",)),
    ("价格", ("price", "pricing")), ("涨价", ("price increase", "pricing")), ("短缺", ("shortage", "tight")), ("交期", ("lead time",)),
    ("库存", ("inventor",)), ("稼动率", ("utilization",)), ("利用率", ("utilization",)), ("良率", ("yield",)),
    ("成长", ("growth", "grew", "increase")), ("增长", ("growth", "grew", "increase")), ("年增", ("year-over-year", "increase")),
    ("下滑", ("decline", "decrease")), ("减少", ("decrease", "decline")), ("部门", ("segment",)), ("年报", ("annual report",)),
    ("季报", ("quarterly",)), ("法说", ("call",)), ("竞争", ("compet",)), ("对手", ("competitor",)), ("市占", ("market share",)),
    ("燃气", ("gas",)), ("发电", ("generation", "power")), ("核能", ("nuclear",)), ("涡轮", ("turbine",)), ("氢", ("hydrogen",)),
    ("燃料电池", ("fuel cell",)), ("电池", ("batter",)), ("排放", ("emission",)), ("排气", ("exhaust",)), ("开发", ("develop",)),
    ("研发", ("research", "develop")), ("专利", ("patent",)), ("员工", ("employee",)), ("股东", ("shareholder", "stockholder")),
    ("氮化镓", ("gan",)), ("碳化硅", ("sic", "silicon carbide")), ("电动车", ("ev", "electric vehicle")), ("汽车", ("automotive",)),
    ("工业", ("industrial",)), ("消费", ("consumer",)), ("通讯", ("communication",)), ("交换器", ("switch",)), ("交换机", ("switch",)),
    ("网通", ("network",)), ("光纤", ("fiber", "fibre")), ("模组", ("module",)), ("马达", ("motor",)), ("机器人", ("robot",)),
    ("卫星", ("satellite",)), ("航太", ("aerospace",)), ("国防", ("defense", "defence")), ("医疗", ("medical",)),
    ("储能", ("energy storage", "storage")), ("太阳能", ("solar",)), ("风电", ("wind",)), ("半导体", ("semiconductor",)),
    ("代工", ("foundry", "contract manufactur")), ("记忆体", ("memory",)), ("存储", ("memory", "storage")),
    ("高频", ("high-frequency", "high frequency")), ("高速", ("high-speed", "high speed")), ("天线", ("antenna",)),
    ("射频", ("rf",)), ("功率", ("power",)), ("电感", ("inductor",)), ("电容", ("capacitor",)), ("连接器", ("connector",)),
    ("线缆", ("cable",)), ("铝", ("alumin",)), ("钨", ("tungsten",)), ("稀土", ("rare earth",)), ("锗", ("germanium",)),
    ("铟", ("indium",)), ("磷化铟", ("indium phosphide", "inp")), ("砷化镓", ("gallium arsenide", "gaas")),
    ("硅光", ("silicon photonic",)), ("共封装", ("co-packaged", "cpo")), ("收发", ("transceiver",)), ("导线", ("wire", "conductor")),
    ("绕组线", ("winding wire",)), ("出口", ("export",)), ("进口", ("import",)), ("关税", ("tariff",)), ("补助", ("grant", "subsid")),
    ("政府", ("government",)), ("董事会", ("board",)), ("毛利率", ("gross margin",)), ("营业利益", ("operating income", "operating profit")),
    ("营业现金流", ("operating cash flow", "cash from operations")), ("自由现金流", ("free cash flow",)), ("借款", ("borrowing", "loan", "debt")),
    ("利息", ("interest",)), ("股利", ("dividend",)), ("回购", ("repurchase", "buyback")), ("认股", ("warrant", "option")),
    ("员工认股", ("esop", "stock option")), ("上市", ("listing", "ipo", "listed")), ("交货", ("deliver",)), ("产品", ("product",)),
    ("技术", ("technolog",)), ("路线图", ("roadmap",)), ("样品", ("sample",)), ("试产", ("pilot",)), ("良品", ("yield",)),
)


@dataclass
class _LineFeat:
    line: SourceLine
    squashed: str
    spaced: str
    bigrams: frozenset[str]
    latin: frozenset[str]
    numbers: frozenset[str]


def _bigrams(folded: str) -> frozenset[str]:
    s = re.sub(r"\W+", "", folded)
    return frozenset(s[i:i + 2] for i in range(len(s) - 1) if _CJK.match(s[i]) and _CJK.match(s[i + 1]))


def _latin(folded_spaced: str) -> frozenset[str]:
    return frozenset(t for t in _LATIN_TOKEN.findall(folded_spaced) if t not in _EN_STOP)


def _numbers(folded: str) -> frozenset[str]:
    return frozenset(n for n in (m.group(0).replace(",", "") for m in _NUM_TOKEN.finditer(folded)) if len(n) >= 2)


def _line_feat(line: SourceLine) -> _LineFeat:
    f = fold(line.text)
    return _LineFeat(line=line, squashed=re.sub(r"\s+", "", f), spaced=" ".join(f.split()), bigrams=_bigrams(f),
                     latin=_latin(" ".join(f.split())), numbers=_numbers(f))


@dataclass
class SourceFacts:
    """一組引用的原文：比對用的整串與每一行的特徵、數字類事實（年份、日期、季、百分比、金額）。"""

    lines: list[_LineFeat]
    squashed: str
    spaced: str
    years: set[int] = field(default_factory=set)
    months: set[int] = field(default_factory=set)
    dates: set[tuple[int, int]] = field(default_factory=set)
    quarters: set[int] = field(default_factory=set)
    pcts: list[float] = field(default_factory=list)
    values: list[float] = field(default_factory=list)


_MONTHS_EN = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
              "november", "december")
_MONTH_EN_RE = re.compile(r"(?<![a-z])(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?(?:\s+(\d{1,2})(?!\d))?")
_DAY_MONTH_EN_RE = re.compile(r"(?<!\d)(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*")
_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_NUM = "一二两兩三四五六七八九十"
_EN_NUMBER_WORDS = {1: ("one", "single", "sole", "only"), 2: ("two", "both", "pair"), 3: ("three",), 4: ("four",), 5: ("five",),
                    6: ("six",), 7: ("seven",), 8: ("eight",), 9: ("nine",), 10: ("ten",), 11: ("eleven",), 12: ("twelve",)}
_MULT = {"万亿": 1e12, "千亿": 1e11, "百亿": 1e10, "亿": 1e8, "千万": 1e7, "百万": 1e6, "万": 1e4, "千": 1e3, "仟": 1e3,
         "兆": 1e12, "trillion": 1e12, "billion": 1e9, "billions": 1e9, "million": 1e6, "millions": 1e6, "thousand": 1e3,
         "thousands": 1e3, "'000": 1e3, "tn": 1e12, "bn": 1e9, "mn": 1e6, "b": 1e9, "m": 1e6, "k": 1e3,
         "crore": 1e7, "crores": 1e7, "cr": 1e7, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5}
#: 原文的數字：原值與乘上單位後的值都收（「1.6t」「800g」的 t、g 不是單位，原值照收；多收一個值只會少一個旗標）。
_SRC_NUMBER = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*(万亿|千亿|百亿|亿|千万|百万|万|千|仟|兆|trillion|billion|"
                         r"million|thousand|crores?|lakhs?|lac|tn|bn|mn|cr|b|m|k)?")
_SRC_PCT = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:%|percent|个百分点|百分点|pp)")
_SPACE_THOUSANDS = re.compile(r"(?<![\d.,])(\d{1,3}(?: \d{3})+)(?![\d])")
_SRC_TENTH = re.compile(r"(?<![\d.])(\d+|[" + _CN_NUM + r"]{1,3})\s*(?:成(?![本功长立员为交品果])|割)")
#: 「四成二」＝42%（成後面再接一個個位數）
_TENTH_ONES = re.compile(r"(?<![\d." + _CN_NUM + r"])([1-9]|[一二两兩三四五六七八九])\s*成\s*([1-9一二三四五六七八九])"
                         r"(?![\d十百千万萬亿億个個月年家倍季日号號])")
#: 表頭宣告的單位（數字本身沒帶單位）：「单位：新台币仟元」「in millions」「(inr mn)」「₹ in crore」「(百万円)」
#: 「£'000」「$m」「in msek」。
_TABLE_UNIT = re.compile(r"单位[:：]?\s*[^\d\n]{0,8}?(千|仟|万|百万|亿)|in\s+(?:inr|rs\.?|₹|usd|us\$|\$|eur|€)?\s*"
                         r"(thousands|millions|billions|crores?|lakhs?|'000)|\((百万|千|仟)(?:円|圆|元)\)|(百万|千)(?:円|圆)|"
                         r"(?:inr|rs\.?|₹|usd|us\$|eur|€)\s*\(?\s*(mn|bn|million|billion|crores?|cr|lakhs?|'000)\b|"
                         r"(?:£|\$|€|gbp|usd|eur|sek|chf|cad|aud)\s*(['’]000|mn|bn|m)(?![a-z0-9])|"
                         r"in\s+(?:(m|t|k)(?:sek|eur|nok|dkk|chf)|(?:sek|eur|nok|dkk|chf)\s*(m|k|'000))\b")


def _unit_mult(unit: str) -> float:
    """表頭單位 → 乘數（「tsek」的 t 是千）。"""
    u = unit.replace("’", "'")
    return 1e3 if u == "t" else _MULT.get(u, 1.0)


def cn_to_int(text: str) -> int | None:
    """「一」到「九十九」（一、十、十二、二十、三十五）；不是這種寫法回 None。"""
    s = str(text or "")
    if not s:
        return None
    if len(s) == 1 and s in _CN_DIGIT:
        return _CN_DIGIT[s]
    if "十" in s:
        head, _, tail = s.partition("十")
        tens = _CN_DIGIT.get(head) if head else 1
        ones = _CN_DIGIT.get(tail) if tail else 0
        if tens is None or ones is None or len(head) > 1 or len(tail) > 1:
            return None
        return tens * 10 + ones
    return None


def _num_value(token: str) -> int | None:
    return int(token) if token.isdigit() else cn_to_int(token)


def declared_units(text: Any) -> tuple[float, ...]:
    """一段字裡宣告的金額單位（`单位：仟元`、`in thousands`、`(INR Mn)`、`百万円`）→ 乘數。"""
    f = fold(text)
    return tuple(sorted({_unit_mult(u) for m in _TABLE_UNIT.finditer(f) for u in m.groups() if u}))


def source_facts(lines: Sequence[SourceLine], *, units: Iterable[float] = ()) -> SourceFacts:
    feats = [_line_feat(line) for line in lines]
    text = "\n".join(f.line.text for f in feats)
    f = fold(text)
    facts = SourceFacts(lines=feats, squashed=re.sub(r"\s+", "", f), spaced=" ".join(f.split()))
    squashed = facts.squashed
    for m in re.finditer(r"(?<!\d)((?:19|20)\d{2})(?!\d)", f):
        facts.years.add(int(m.group(1)))
    for m in re.finditer(r"(?<!\d)(\d{2,3})\s*年", f):              # 民國年（115 年＝2026）
        if 90 <= int(m.group(1)) <= 130:
            facts.years.add(int(m.group(1)) + 1911)
    for m in re.finditer(r"令和\s*(\d{1,2})\s*年", f):
        facts.years.add(int(m.group(1)) + 2018)
    for m in re.finditer(r"(?<![a-z])fy\s*'?(\d{2}|\d{4})(?!\d)", f):
        y = int(m.group(1))
        facts.years.add(y if y > 1900 else 2000 + y)
    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*日", squashed):
        facts.dates.add((int(m.group(1)), int(m.group(2))))
    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*月", squashed):
        facts.months.add(int(m.group(1)))
    for m in re.finditer(r"(?<![" + _CN_NUM + r"])([" + _CN_NUM + r"]{1,3})月", squashed):
        v = cn_to_int(m.group(1))
        if v:
            facts.months.add(v)
    for m in re.finditer(r"(?<!\d)(?:19|20)\d{2}[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)", f):
        facts.dates.add((int(m.group(1)), int(m.group(2))))
        facts.months.add(int(m.group(1)))
    for m in re.finditer(r"(?<!\d)(\d{1,2})/(\d{1,2})/(?:\d{2}|\d{4})(?!\d)", f):
        facts.dates.add((int(m.group(1)), int(m.group(2))))
        facts.months.add(int(m.group(1)))
    for m in re.finditer(r"(?<![\d/])(\d{2,3})/(\d{1,2})/(\d{1,2})(?!\d)", f):     # 民國日期 115/08/14
        if 90 <= int(m.group(1)) <= 130:
            facts.years.add(int(m.group(1)) + 1911)
            facts.dates.add((int(m.group(2)), int(m.group(3))))
            facts.months.add(int(m.group(2)))
    for m in re.finditer(r"(?<![\d\-/.])(\d{1,2})-(\d{1,2})(?![\d\-])", f):     # 月-日（法定期限 11-14）
        month, day = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            facts.dates.add((month, day))
    spaced_text = facts.spaced
    for m in _MONTH_EN_RE.finditer(spaced_text):
        month = next(i for i, name in enumerate(_MONTHS_EN, 1) if name.startswith(m.group(1)[:3]))
        facts.months.add(month)
        if m.group(2):
            facts.dates.add((month, int(m.group(2))))
    for m in _DAY_MONTH_EN_RE.finditer(spaced_text):
        month = next(i for i, name in enumerate(_MONTHS_EN, 1) if name.startswith(m.group(2)[:3]))
        facts.months.add(month)
        facts.dates.add((month, int(m.group(1))))
    for pattern in (r"第\s*([1-4一二三四])\s*(?:季|四半期)", r"(?<![a-z0-9])q\s*([1-4])(?!\d)", r"(?<![\d.])([1-4])\s*q(?![a-z])"):
        for m in re.finditer(pattern, f):
            facts.quarters.add(_num_value(m.group(1)) or 0)
    for word, q in (("first", 1), ("second", 2), ("third", 3), ("fourth", 4)):
        if re.search(rf"{word}[- ](?:fiscal )?quarter", spaced_text):
            facts.quarters.add(q)
    for m in _SRC_PCT.finditer(f):
        facts.pcts.append(float(m.group(1)))
    for m in _SRC_TENTH.finditer(squashed):
        v = _num_value(m.group(1))
        if v is not None:
            facts.pcts.append(v * 10.0)
    for m in _TENTH_ONES.finditer(squashed):
        tens, ones = _num_value(m.group(1)), _num_value(m.group(2))
        if tens is not None and ones is not None:
            facts.pcts.append(tens * 10.0 + ones)
    declared = set(declared_units(text)) | set(units)
    for m in _SRC_NUMBER.finditer(f):
        raw = float(m.group(1).replace(",", "") + (f".{m.group(2)}" if m.group(2) else ""))
        facts.values.append(raw)
        if m.group(3):
            facts.values.append(raw * _MULT[m.group(3)])
        facts.values += [raw * mult for mult in declared]
    # 空白當千分位（瑞典、法國的報告：「12 280 701 shares」；SIVE.ST 11-12）——合起來的值另外收，分開的值照留
    for m in _SPACE_THOUSANDS.finditer(f):
        raw = float(m.group(1).replace(" ", ""))
        facts.values += [raw] + [raw * mult for mult in declared]
    return facts


# ---------------------------------------------------------------------------
# 句子的主張：數字、引號、名稱、限定詞
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NumberClaim:
    raw: str              # 句子裡的寫法
    kind: str             # year／date／month／quarter／pct／amount／count
    value: float
    tol: float = 0.0
    unit: str = ""        # count 的量詞（簡體）
    day: int | None = None
    pos: int = 0          # 在句子裡的位置（月份找前面最近的年份用）
    year: int | None = None   # 日期、月份的年（句子裡寫了的；沒寫＝None）

    def is_future(self, as_of: date) -> bool:
        """寫的那天之後的日子（我們自己設的到期日、未來的排程）——原文裡本來就不會有，不核。
        月份帶「上旬、下旬、底」時 `day` 記那一段的起點（「11 月下旬前再看」寫在 11-12 是未來）。"""
        if self.kind not in ("date", "month"):
            return False
        year = self.year or as_of.year
        month = int(self.value)
        if self.kind == "date" or self.day:
            try:
                day = date(year, month, int(self.day or 1))
                # 寫的當天（「第一份敘事，2026-11-12」）是我們自己的戳記，也不核
                return day > as_of or (self.kind == "date" and day == as_of)
            except ValueError:
                return False
        return (year, month) > (as_of.year, as_of.month)


#: 數量詞的量詞。「條、項、份、檔」不收——多半是我們自己的字（反證五條、起始門四項、文件三份、可開十檔）；
#: 「大」只算「三大客戶、兩大廠」那種（「一大段」不是數量）；「個」後面接「半」是「一個半年」，不是數量。
_CLS = ("家|個(?!\\s*半)|个(?!\\s*半)|款|種|种|座|間|间|位|名|代|批|筆|笔|國|国|廠|厂|部門|部门|"
        "大(?=[客廠厂股供買买主競竞同顧顾])|年|倍|季")
#: 中文數字前面是這些字就不是數量（前一年、近四季、最新一季、最後一筆、最大一家、翻一倍、某一家）。
_NOT_COUNT_BEFORE = "唯第同統统單单另每任逐其之前近上下這这那某家新翻後后大"
_APPROX = re.compile(r"(约|約|近|逾|超过|超過|将近|將近|大约|大約|不到|超|接近|上看|左右|多)\s*$")
_PART_OF_MONTH = (("上旬", 1), ("初", 1), ("中旬", 11), ("下旬", 21), ("底", 25), ("末", 25))


def _part_of_month(after: str) -> int | None:
    """「11 月下旬」「6 月底」→ 那一段的起日（給 `NumberClaim.is_future`）；沒寫回 None。"""
    s = after.lstrip()
    return next((day for word, day in _PART_OF_MONTH if s.startswith(word)), None)
#: 不是數字主張的數：自己反證的編號（第 2 條、c1）、待辦編號（[805]）、申報表單名（10-Q、20-F、8-K、S-1、424B4、13F、DEF 14A）。
_REF_NUMBERS = re.compile(r"(?:读图|讀圖)?\s*第\s*\d+(?:\s*[、,，及和与與]\s*第?\s*\d+)*\s*[条條]|(?<![a-z])c\d+(?!\d)|\[\s*\d{1,4}\s*\]|"
                          r"(?<![a-z0-9])(?:10-k|10-q|20-f|40-f|8-k|6-k|[sf]-[1-4]|424b\d?|(?:sc\s*)?13[dfg]|(?:def\s*)?14a)"
                          r"(?:/a)?(?![a-z0-9])")
_Q_WORDS = re.compile(r"第\s*([1-4一二三四])\s*季(?:度)?|(?<![a-z0-9])q\s*([1-4])(?!\d)|(?<![\d.])([1-4])\s*q(?![a-z])")


def _tol(int_part: str, frac: str | None, mult: float, approx: bool, value: float) -> float:
    tol = 0.5 * (10 ** -len(frac) if frac else 1.0) * mult
    return max(tol, abs(value) * 0.1) if approx else tol


def number_claims(sentence: str) -> list[NumberClaim]:
    """句子裡寫的數字（`{placeholder}` 已拿掉；「第 N 條」這種指自己反證編號的不算）。順序抽、抽過的遮掉不重抽。"""
    text = _REF_NUMBERS.sub(lambda m: " " * len(m.group(0)), _plain(strip_placeholders(sentence)))
    out: list[NumberClaim] = []

    def take(pattern: str | re.Pattern[str], build: Callable[[re.Match[str]], NumberClaim | None]) -> None:
        nonlocal text
        regex = re.compile(pattern) if isinstance(pattern, str) else pattern
        spans = []
        for m in regex.finditer(text):
            claim = build(m)
            if claim is not None:
                out.append(NumberClaim(**{**claim.__dict__, "pos": m.start()}))
                spans.append(m.span())
            elif build is _MASK_ONLY:
                spans.append(m.span())
        for a, b in reversed(spans):
            text = text[:a] + " " * (b - a) + text[b:]

    def approx_before(m: re.Match[str]) -> bool:
        return bool(_APPROX.search(text[max(0, m.start() - 4):m.start()]))

    # 順序有意義：日期 → 帶單位的金額與百分比（「2000 萬」不是年份）→ 年份 → 月、季 → 數量詞 → 其餘的數
    take(r"(?<!\d)((?:19|20)\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)",
         lambda m: NumberClaim(m.group(0), "date", int(m.group(2)), day=int(m.group(3)), year=int(m.group(1))))
    take(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*日", lambda m: NumberClaim(m.group(0), "date", int(m.group(1)), day=int(m.group(2))))
    take(r"(?<![\d\-/.:])(\d{1,2})-(\d{1,2})(?![\d\-/.:%年月日倍成家個个萬万億亿])",       # 月-日（「11-04 員工認股」）
         lambda m: NumberClaim(m.group(0), "date", int(m.group(1)), day=int(m.group(2)))
         if 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31 else None)
    take(r"(?<![a-z])fy\s*'?(\d{2}|\d{4})(?!\d)",
         lambda m: NumberClaim(m.group(0), "year", (lambda y: y if y > 1900 else 2000 + y)(int(m.group(1)))))
    # 「1.5 到 2.5 億」：前一個數借後一個數的單位（後一個數留給下一條照常抽）
    take(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*(?=(?:到|至|–|~|～)\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*"
         r"(萬億|万亿|千億|千亿|百億|百亿|億|亿|千萬|千万|百萬|百万|萬|万|兆))",
         lambda m: (lambda v, mult: NumberClaim(m.group(0).rstrip(), "amount", v * mult,
                                                tol=_tol(m.group(1), m.group(2), mult, approx_before(m), v * mult)))(
             float(m.group(1).replace(",", "") + (f".{m.group(2)}" if m.group(2) else "")), _MULT[fold(m.group(3))]))
    take(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*(萬億|万亿|千億|千亿|百億|百亿|億|亿|千萬|千万|百萬|百万|萬|万|兆)",
         lambda m: (lambda v, mult: NumberClaim(m.group(0), "amount", v * mult,
                                                tol=_tol(m.group(1), m.group(2), mult, approx_before(m), v * mult)))(
             float(m.group(1).replace(",", "") + (f".{m.group(2)}" if m.group(2) else "")), _MULT[fold(m.group(3))]))
    take(r"(?<![\d.])(\d+)(?:\.(\d+))?\s*(?:%|個百分點|个百分点|百分點|百分点|pp)",
         lambda m: (lambda v: NumberClaim(m.group(0), "pct", v, tol=_tol(m.group(1), m.group(2), 1.0, approx_before(m), v)))(
             float(m.group(1) + (f".{m.group(2)}" if m.group(2) else ""))))
    take(_TENTH_ONES, lambda m: (lambda t, o: NumberClaim(m.group(0), "pct", t * 10.0 + o, tol=0.5)
                                 if t is not None and o is not None else None)(_num_value(fold(m.group(1))), _num_value(fold(m.group(2)))))
    take(r"(?<![\d.])(\d+|[" + _CN_NUM + r"]{1,3})\s*成(?![本功長长立員员為为交品果])",
         lambda m: (lambda v: NumberClaim(m.group(0), "pct", v * 10.0, tol=5.0) if v is not None else None)(_num_value(m.group(1))))
    take(r"(?<![\d.])((?:19|20)\d{2})(?!\d)", lambda m: NumberClaim(m.group(0), "year", int(m.group(1))))
    # 「4–9 月」「4 月至 9 月」是一段期間（日本的上半期、台灣的第二三季）——原文多半寫成「第 2 四半期」「上半年」，不逐月核
    take(r"(?<!\d)(\d{1,2})\s*月?\s*[–\-~～至到]\s*(\d{1,2})\s*月", _MASK_ONLY)
    take(r"一\s*[個个]\s*月\s*比\s*一\s*[個个]\s*月", _MASK_ONLY)              # 「一個月比一個月」是說法，不是期間
    take(r"(?<![\d.a-z])(\d+)\s*(?:個|个)\s*月|(?<![" + _NOT_COUNT_BEFORE + _CN_NUM + r"])([" + _CN_NUM + r"]{1,3})\s*(?:個|个)\s*月",
         lambda m: (lambda v: NumberClaim(m.group(0), "count", v, unit="个月") if v is not None else None)(
             _num_value(fold(m.group(1) or m.group(2)))))
    take(r"(?<![\d.])(\d{1,2})\s*月(?!\s*\d)",
         lambda m: NumberClaim(m.group(0), "month", int(m.group(1)), day=_part_of_month(text[m.end():m.end() + 3]))
         if 1 <= int(m.group(1)) <= 12 else None)
    take(r"(?<![" + _CN_NUM + r"第])([一二三四五六七八九十]{1,3})月",
         lambda m: (lambda v: NumberClaim(m.group(0), "month", v) if v and v <= 12 else None)(cn_to_int(m.group(1))))
    take(_Q_WORDS, lambda m: NumberClaim(m.group(0), "quarter",
                                         _num_value(next(g for g in m.groups() if g)) or 0))
    # 「1H27 年增」的 27 不是年數（前面是字母）
    take(r"(?<![\d.a-z])(\d+)\s*(" + _CLS + r")",
         lambda m: NumberClaim(m.group(0), "count", int(m.group(1)), unit=fold(m.group(2))) if int(m.group(1)) < 1000 else None)
    # 「前一年同期」「近四季」「上一季」「最新一季」「最後一筆」「最大一家」「這一家」「某一家」「翻一倍」「自家三年（百分位）」
    # 不是數量的主張；「一年」多半是「每年、一整年」（美國一年約占…、上市不到一年）；只有「一年內／一年後」是時間窗的主張
    take(r"(?<![" + _NOT_COUNT_BEFORE + _CN_NUM + r"])([" + _CN_NUM + r"]{1,3})\s*(" + _CLS + r")",
         lambda m: (lambda v, unit: NumberClaim(m.group(0), "count", v, unit=unit)
                    if v is not None and not (v == 1 and unit == "年" and text[m.end():m.end() + 1] not in "內内後后") else None)(
             cn_to_int(fold(m.group(1))), fold(m.group(2))))
    take(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\d])",
         lambda m: (lambda v: NumberClaim(m.group(0), "amount", v,
                                          tol=_tol(m.group(1), m.group(2), 1.0, approx_before(m), v)) if v >= 10 or m.group(2) else None)(
             float(m.group(1).replace(",", "") + (f".{m.group(2)}" if m.group(2) else ""))))
    # 月份、日期的年＝句子裡寫在它前面最近的年份（「2027 年 2 月的第三季決算」）；沒寫就 None（`is_future` 當作同一年）
    years = sorted((c.pos, int(c.value)) for c in out if c.kind == "year")
    out = [NumberClaim(**{**c.__dict__, "year": next((y for p, y in reversed(years) if p < c.pos), None)})
           if c.kind in ("date", "month") and c.year is None else c for c in out]
    return sorted(out, key=lambda c: c.pos)


def _MASK_ONLY(_m: re.Match[str]) -> NumberClaim | None:
    """`number_claims` 的 `take` 用：只遮掉、不當主張（期間「4–9 月」）。"""
    return None


def _count_found(claim: NumberClaim, near: SourceFacts) -> bool:
    """數量詞只在**對到的那幾行**裡找（2026-11-12 校準：查整份原文，6234 的「兩個部門」被節錄別處的「兩個」放過）。"""
    n = int(claim.value)
    unit = claim.unit
    cn = [k for k, v in _CN_DIGIT.items() if v == n] if n < 10 else []
    if 10 <= n < 100:
        tens, ones = divmod(n, 10)
        tens_cn = "" if tens == 1 else next(k for k, v in _CN_DIGIT.items() if v == tens and k not in "〇零兩")
        ones_cn = "" if ones == 0 else next(k for k, v in _CN_DIGIT.items() if v == ones and k not in "〇零兩")
        cn = [tens_cn + "十" + ones_cn]
    forms = [f"{n}{unit}"] + [f"{c}{unit}" for c in cn]
    if unit == "个月":
        forms += [f"{n}个月", f"{n}months", f"{n}-month"]
    if unit == "年":
        forms += [f"{n}-year", f"{n}years", f"{n}年期", f"{n}年间"]
    if unit == "倍":
        forms += [f"{n}x", f"{n}times", f"{n}-fold"]
    if any(form in near.squashed for form in forms):
        return True
    # 兩位數以上的阿拉伯數字單獨出現在對到的那幾行也算（海關彙整站的 JSON「"total_shipments":131」、英文「131 shipments」）——
    # 前後不能黏著別的數字、小數點、千分位，後面不能是 %、百萬十億或中文的萬億
    if n >= 10 and re.search(rf"(?<!\d)(?<!\d[.,]){n}(?!\d|[.,]\d|[a-z])"
                             r"(?!\s*(?:%|percent|million|billion|thousand|trillion|bn\b|mn\b|[亿億万萬千百]))", near.spaced):
        return True
    # 英文原文認數字的英文字（two、five）；只有阿拉伯數字（「2」）不算——任何一行都有個 2（「2,826」）
    words = _EN_NUMBER_WORDS.get(n, ())
    return any(re.search(rf"(?<![a-z]){w}(?![a-z])", near.spaced) for w in words)


def number_found(claim: NumberClaim, facts: SourceFacts, near: SourceFacts, meta: SourceFacts | None = None) -> bool:
    """`facts`：這一句引用的整份原文；`near`：對到的那幾行；`meta`：這幾份文件自己的標示（檔名、日期行）。
    年份、百分比、金額查整份（精確的數很少撞號）；日期、月份、數量詞只查對到的那幾行——它們跟著一件事走（KSHINTL.NS
    「8 月簽約」：整份原文別處有 8 月的法說）；日期、月份、季、年份另外認文件自己的日期（「11 月上修」講的是 11 月那份文件）。"""
    doc = meta or SourceFacts(lines=[], squashed="", spaced="")
    if claim.kind == "year":
        return int(claim.value) in facts.years or int(claim.value) in doc.years
    if claim.kind == "date":
        day = (int(claim.value), int(claim.day or 0))
        return day in near.dates or day in doc.dates
    if claim.kind == "month":
        month = int(claim.value)
        return any(month in f.months or any(m == month for m, _d in f.dates) for f in (near, doc))
    if claim.kind == "quarter":
        return int(claim.value) in facts.quarters or int(claim.value) in doc.quarters
    if claim.kind == "pct":
        if any(abs(claim.value - p) <= claim.tol + 1e-9 for p in facts.pcts):
            return True
        # 表格裡的百分比常常沒有 % 號（「丁客戶 88,743 18.56」「營收比重 41」）：帶小數的拿整份原文的數比；
        # 整數太容易撞到別的數，只拿對到的那幾行比
        pool = facts.values if "." in claim.raw else near.values
        return any(abs(claim.value - v) <= claim.tol + 1e-9 for v in pool)
    if claim.kind == "count":
        return _count_found(claim, near)
    return any(abs(claim.value - v) <= claim.tol + 1e-9 for v in facts.values)


_QUOTE = re.compile(r"「([^「」]+)」|『([^『』]+)』|“([^“”]+)”")
#: 「某份文件寫了什麼」的句子（`squash` 之後的簡體）：這種句子是事實句，對不到原文就要標。
_ATTRIBUTION = re.compile(r"说|写(?!成|进|入|下|法|一句)|自述|表示|指出|公告|揭露|提到|点名|宣布|称|列出|年报|季报|财报|法说|"
                          r"新闻稿|简报|纪要|招股书|有报|决算|10-k|10-q|20-f|8-k|6-k|说明会|电话会议|投资者关系")
#: 條件句：反證與錯的訊號（帶「第 N 條」）——講的是之後會不會發生，數字是我們設的門檻，不核數字。
_CONDITION_SENTENCE = re.compile(r"第\s*\d+(?:\s*[、,，及和与與]\s*第?\s*\d+)*\s*[條条]|^\s*錯的訊號|^\s*错的讯号")
#: 「必須為真」格裡的門檻數：前面是「低於、跌回、守在、至少……」或後面是「以下、以上」的數。
_TARGET_BEFORE = re.compile(r"(低於|低于|高於|高于|跌回|跌破|守在|至少|最多|站上|跌到|走到|超過|超过|達到|达到|不掉回|回到)\s*約?\s*$")
_TARGET_AFTER = re.compile(r"^\s*[^\d，。；,;]{0,4}?(以下|以上|以內|以内|之下|之上)")
#: 「必須為真」那幾格（敘事與故事）：數字可能是門檻，不是事實。
TARGET_WHERES: tuple[str, ...] = ("what_must_be_true", "story:what_must_be_true")
#: 系統自己的字（候選狀態、讀圖判讀）被加引號不是引文。
_SYSTEM_QUOTES = frozenset(squash(w) for w in ("可開", "缺 X", "不要", "已持有", "量", "價", "neither", "moat", "量的賭注",
                                               "價的賭注", "反證", "加碼條件", "讀到邊", "已定價", "前提失效", "會死嗎",
                                               "已定價嗎", "出現在數字裡了嗎", "邊緣", "邊緣無法量", "非邊緣"))


def quote_problems(sentence: str, facts: SourceFacts) -> list[str]:
    """引號裡的字（刪節號分段）每一段都要在原文裡（去空白、折疊字形後的子字串）。回不在的那幾段（原字）。"""
    out = []
    for m in _QUOTE.finditer(strip_placeholders(sentence)):
        body = next(g for g in m.groups() if g is not None)
        if squash(body) in _SYSTEM_QUOTES:
            continue
        for part in re.split(r"…+|⋯+|\.{3,}|（略）|\(略\)", body):
            if len(squash(part)) >= 3 and squash(part) not in facts.squashed:
                out.append(part.strip())
    return out


_LATIN_NAME = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*(?:[-.&'+][A-Za-z0-9]+)*)")
#: 不當名稱核的英文（通用縮寫與單位）——要核的是公司名與型號。
_NAME_STOP = frozenset("""ai gpu gpus cpu cpus hbm pcb pcbs ccl ccls asic asics ic ics oem oems odm odms ev evs led leds ceo cfo coo cto
fy yoy qoq capex opex etf nav eps adr ipo ir usd twd ntd rmb cny jpy eur krw inr hkd gbp cad aud chf sek us uk eu vs ok ttm
gaap ebitda cagr mou nre po sec mops sse szse hkex tse nse bse asx otc nasdaq nyse xbrl pdf id kpi roi roe gm op dc ac
q1 q2 q3 q4 h1 h2 the and of for kg km mm nm um ghz mhz gw mw kw tw gwh mwh kwh gb tb pb ton tons inc ltd co corp llc plc
ag se sa nv bv gmbh kk oy ab asa spa mr ms dr no pp bps bp pt xx edinet tdnet cninfo dart edgar sedar hkexnews
yuho""".split())
#: 不當名稱核的寫法：財年、季、半年（由數字那一關核）、加碼條件編號（c1）。
_NAME_SKIP = re.compile(r"fy\d{2,4}(?:q[1-4]|h[12])?|cy\d{2,4}|q[1-4]|h[12]|[1-4][qh]|c\d{1,2}", re.IGNORECASE)


def latin_names(sentence: str, *, skip: Iterable[str] = ()) -> list[str]:
    """句子裡要核的英文名稱：含數字的型號（MI355X）、大寫開頭接小寫的專有名詞（Hitachi）、三個字母以上的全大寫（AAON）。"""
    skipped = {t for s in skip for t in re.findall(r"[a-z0-9]+", fold(s))} | {fold(s) for s in skip}
    out: list[str] = []
    for m in _LATIN_NAME.finditer(unicodedata.normalize("NFKC", strip_placeholders(sentence).translate(_MARKS))):
        tok = m.group(1).strip(".-/'")
        low = tok.lower()
        if len(tok) < 2 or low in _NAME_STOP or low in skipped or _NAME_SKIP.fullmatch(tok):
            continue
        has_digit = any(ch.isdigit() for ch in tok)
        proper = tok[0].isupper() and any(ch.islower() for ch in tok[1:])
        acronym = tok.isupper() and len(tok) >= 3
        if (has_digit or proper or acronym) and tok not in out:
            out.append(tok)
    return out


def _latin_in(token: str, spaced_text: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(fold(token)) + r"(?![a-z0-9])", spaced_text))


#: 限定詞：(句子裡的寫法…, 原文裡算對應的字…)。對應字查**對到的那幾行**，不是整份——「major」在一份 10-Q 裡隨處都有。
#: 「多半」不當限定詞——它也是「大概」（「華明多半不是主力」），那是我們的推論口氣，不是原文的量。
QUALIFIERS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("唯一", "獨家", "独家", "獨占", "独占", "單一來源", "单一来源"),
     ("唯一", "独家", "独占", "单一", "sole", "only", "exclusive", "exclusively", "single", "唯一の", "유일", "독점", "단독")),
    (("首家", "首批", "首個", "首个", "第一家", "率先"), ("首家", "首批", "首个", "第一家", "率先", "首次", "first", "初めて", "最初")),
    (("主要",), ("主要", "主力", "主に", "major", "main", "mainly", "primary", "primarily", "principal", "principally", "largely",
                "주요", "주로")),
    (("多數", "多数", "大多", "過半", "过半", "大部分"),
     ("多数", "大多", "多半", "过半", "大部分", "大半", "majority", "most", "mostly", "多く", "대부분", "과반")),
    (("全部", "全數", "全数", "全都"), ("全部", "所有", "全数", "全都", "全て", "すべて", "all", "every", "entire", "entirely",
                                       "전부", "모든", "전량")),
    (("最大",), ("最大", "最高", "largest", "biggest", "top", "首位", "第一", "최대")),
    (("龍頭", "龙头", "領先", "领先"), ("龙头", "领先", "领导", "leading", "leader", "leadership", "top", "首位", "トップ", "선두", "1위")),
    (("幾年", "几年", "數年", "数年"), ("几年", "数年", "several years", "multi-year", "multiyear", "few years", "coming years")),
)


def qualifier_problems(sentence: str, matched: Sequence[_LineFeat]) -> list[str]:
    plain = _plain(strip_placeholders(sentence))
    near_squashed = "".join(f.squashed for f in matched)
    near_spaced = " ".join(f.spaced for f in matched)
    out = []
    for triggers, counterparts in QUALIFIERS:
        hit = next((t for t in triggers if t in plain), None)
        if hit is None:
            continue
        found = any((_latin_in(c, near_spaced) if re.fullmatch(r"[a-z\- ]+", c) else squash(c) in near_squashed)
                    for c in counterparts)
        if not found:
            out.append(hit)
    return out


#: 保留或未來語氣（expected、may、plan、預計……原文有、句子沒有）**量過、不上線**（2026-11-13）：回頭核的 27 份裡改掉的敘事句 135 句、
#: 核過沒改的 1,888 句當基準，三種寫法——對到的整個窗、只看對到最多字的那一句、再只查寫成已發生的句子——命中率都只比亂猜好
#: 約 1.4 倍（原文一行常有好幾句，語氣字落在別句）。這一類錯要等句子綁逐字原文（ROADMAP「敘事事實句綁逐字錨點」）才查得準。


def registry_name_problems(sentence: str, facts: SourceFacts, *,
                           names: Sequence[tuple[str, Sequence[tuple[str, str, bool]]]], self_company: str,
                           labels: str = "") -> list[str]:
    """名冊公司（不含這一檔自己）的中日文名稱出現在句子裡，原文裡卻沒有那家的任何一個名稱。回句子裡的寫法。
    `names`：`CheckContext.folded_names()`。值可以含代號（`1802`）：公司自己的年報不寫自己的名字（「本公司」），
    檔名寫著它的代號就算它的文件。"""
    sq = squash(sentence)
    out = []
    for company, aliases in names:
        if company == self_company:
            continue
        hit = next((raw for raw, folded, cjk in aliases if cjk and len(folded) >= 2 and folded in sq), None)
        if hit is None:
            continue
        present = any((folded in facts.squashed) if cjk else (_latin_in(raw, facts.spaced) or _latin_in(raw, labels))
                      for raw, folded, cjk in aliases)
        if not present and hit not in out:
            out.append(hit)
    return out


# ---------------------------------------------------------------------------
# 一句的核對
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Match:
    label: str
    text: str            # 印出來的那一段（長行取對到的那附近）
    coverage: float
    elsewhere: bool = False   # 對到的是別格的引用（引用指偏）
    own: bool = False         # 對到的是我們自己寫的字（`SourceLine.own`）：對照用，不算原文


@dataclass(frozen=True)
class Flag:
    kind: str
    detail: str


@dataclass(frozen=True)
class SentenceCheck:
    sentence: Sentence
    matches: tuple[Match, ...]
    flags: tuple[Flag, ...]
    ref_kinds: tuple[str, ...]           # 這一句自己的引用各是哪一種（`REF_KINDS`）
    carried: str | None = None           # 上一版核過、一字不差的這一句：那一筆核對紀錄的 id

    @property
    def flagged(self) -> bool:
        return bool(self.flags) and self.carried is None


def _sentence_tokens(sentence: str) -> tuple[frozenset[str], frozenset[str], frozenset[str], list[tuple[str, ...]]]:
    f = fold(strip_placeholders(sentence))
    sq = re.sub(r"\s+", "", f)
    hints = [stems for key, stems in EN_HINTS if key in sq]
    return _bigrams(f), _latin(" ".join(f.split())), _numbers(f), hints


def _window(line: str, needles: Iterable[str]) -> str:
    if len(line) <= LINE_WINDOW:
        return line
    low = fold(line)
    pos = min((p for p in (low.find(n) for n in needles if n) if p >= 0), default=0)
    start = max(0, pos - LINE_WINDOW // 3)
    end = min(len(line), start + LINE_WINDOW)
    return ("…" if start else "") + line[start:end] + ("…" if end < len(line) else "")


def rank_lines(sentence: str, lines: Sequence[_LineFeat]) -> list[tuple[float, _LineFeat, list[str]]]:
    """每一行對這句的覆蓋率（共同的中日文兩字詞、英文詞、數字、中英對照詞）；由高到低。"""
    bigrams, latin, numbers, hints = _sentence_tokens(sentence)
    denom = len(bigrams) + 2 * len(latin) + 3 * len(numbers) + 1.5 * len(hints)
    if denom == 0:
        return []
    ranked = []
    for feat in lines:
        common_n = numbers & feat.numbers
        common_l = latin & feat.latin
        common_b = bigrams & feat.bigrams
        hint_hits = [next(s for s in stems if s in feat.spaced) for stems in hints if any(s in feat.spaced for s in stems)]
        score = len(common_b) + 2 * len(common_l) + 3 * len(common_n) + 1.5 * len(hint_hits)
        if score:
            ranked.append((score / denom, feat, [*common_n, *common_l, *hint_hits, *sorted(common_b)]))
    ranked.sort(key=lambda r: -r[0])
    return ranked


@dataclass
class CheckContext:
    """呼叫端注入的東西：引用怎麼讀（`resolve`）、名冊名稱、上一版核過的句子。"""

    resolve: Callable[[str], ResolvedRef]
    names: Mapping[str, Sequence[str]] = field(default_factory=dict)
    carried: Mapping[str, str] = field(default_factory=dict)     # 句子 digest → 核過它的紀錄 id
    #: 每份原文的特徵只算一次；批次核很多份時傳同一個 dict 進來共用（`--gaps` 全量估工作量）
    cache: dict[Any, Any] = field(default_factory=dict)

    def ref_facts(self, ref: str) -> SourceFacts:
        key = ("ref", ref)
        if key not in self.cache:
            resolved = self.resolve(ref)
            self.cache[key] = source_facts(resolved.lines, units=resolved.units)
        return self.cache[key]

    def facts(self, refs: Sequence[str]) -> SourceFacts:
        key = ("refs", tuple(refs))
        if key not in self.cache:
            self.cache[key] = _merge_all([self.ref_facts(r) for r in refs])
        return self.cache[key]

    def meta_facts(self, refs: Sequence[str]) -> SourceFacts:
        """這幾份文件自己的標示（檔名、日期行）裡的年份、日期、月份、季。"""
        key = ("meta", tuple(refs))
        if key not in self.cache:
            texts = [t for ref in refs for t in self.resolve(ref).meta]
            self.cache[key] = source_facts([SourceLine("meta", t.replace("_", " ")) for t in texts])
        return self.cache[key]

    def folded_names(self) -> list[tuple[str, list[tuple[str, str, bool]]]]:
        """名冊名稱折疊一次：[(company, [(原字, squash, 是不是中日文)])]。"""
        key = ("names", id(self.names))
        if key not in self.cache:
            self.cache[key] = [(company, [(a, squash(a), bool(_CJK.search(a))) for a in aliases if a])
                               for company, aliases in self.names.items()]
        return self.cache[key]


#: 講之後會發生什麼的格（何時知道）：只核引號裡的字。
SCHEDULE_WHERES: tuple[str, ...] = ("when", "story:when")


#: 月份、日期緊挨著一份文件（「11 月的財報稿」「科創板日報 2026-08-22」「8-K 2026-11-10」「11-11 重讀」）：講的是文件的日子，
#: 對到文件自己的日期就算。旁邊沒有文件（「8 月和 Hitachi Energy 簽了」）卻只對到文件日期——可能是把文件的月份寫成事件的
#: 月份（KSHINTL.NS 那一句的形狀），照標、附一句問句。
_DOC_WORDS = re.compile(r"财报|季报|年报|月报|法说|公告|新闻稿|简报|说明会|电话会议|决算|营收|报告|重讯|讯息|股东会|董事会|文件|节录|"
                        r"纪要|访谈|采访|投资者关系|调研|日报|报导|报道|新闻|媒体|提示|稿|刊登|刊出|刊载|发布|公布|揭露|重读|重写|读过|"
                        r"读成|重答|换版|改判|改读|读图|判读|叙事|入图|登记|"
                        r"10-q|10-k|8-k|6-k|20-f|filing|q&a|presentation|transcript|release|call|letter|deck")
_DOC_BEFORE_CHARS = 10
_DOC_AFTER_CHARS = 14
META_ONLY_NOTE = "（只對到文件日期——是事件的月份還是文件的月份？）"
#: 列出來對照的那一行是我們自己寫的
OWN_LABEL = "（自家文字，不算原文）"


def _names_document(claim: NumberClaim, sentence: str) -> bool:
    if claim.kind == "month" and claim.day == 25:
        return True                       # 「6 月底」「9 月底」是報表的期末日，就是那份文件的日子
    plain = _plain(strip_placeholders(sentence))
    start, end = claim.pos, claim.pos + len(claim.raw)
    around = fold(plain[max(0, start - _DOC_BEFORE_CHARS):start]) + " " + fold(plain[end:end + _DOC_AFTER_CHARS])
    return bool(_DOC_WORDS.search(around))


#: 括號裡引用自己命令的那一段（「系統口徑邊緣（python -m alpha edge ESI，2026-11-12：市值約…、分析師 12 家）」）：數字是那條命令
#: 當天的輸出（authority），不是引用原文的事實——不核，輸出開頭照寫。
_COMMAND = re.compile(r"python\s+-m\s+[a-z_.]+")


def _command_spans(sentence: str) -> list[tuple[int, int]]:
    plain = _plain(strip_placeholders(sentence))
    spans = []
    for m in _COMMAND.finditer(plain):
        start = max(plain.rfind("（", 0, m.start()), plain.rfind("(", 0, m.start()))
        ends = [p for p in (plain.find("）", m.end()), plain.find(")", m.end())) if p >= 0]
        spans.append((start if start >= 0 else m.start(), min(ends) if ends else len(plain)))
    return spans


def _is_target(claim: NumberClaim, sentence: str) -> bool:
    """「必須為真」格裡的門檻數（「跌回 75,000 盧比以下」「守在約 90,000」「45,000–50,000 噸」的區間）。"""
    plain = _plain(strip_placeholders(sentence))
    start = claim.pos
    end = start + len(claim.raw)
    if _TARGET_BEFORE.search(plain[max(0, start - 8):start]) or _TARGET_AFTER.search(plain[end:end + 8]):
        return True
    # 區間（「45,000–50,000 噸」「2–2.5 倍」）是推估的範圍，不是原文的一個數
    return bool(re.match(r"\s*[–\-~～至到]\s*\d", plain[end:end + 4]) or re.search(r"\d\s*[–\-~～至到]\s*$", plain[max(0, start - 4):start]))


#: 分數（「三分之二」）→ 百分比。`number_claims` 不抽：在整份原文裡比不準（「約三分之二」對不到哪一個百分比），逐句核對不核它；
#: 但它是數字主張——算進事實句，錨點比對另核（`alpha.narrative.anchors`；AXTI 11-13：原文第二季約 79%、第三季約 87%）。
_FRACTION = re.compile(r"(\d+|[一二两兩三四五六七八九十]{1,3})\s*分之\s*(\d+|[一二两兩三四五六七八九十]{1,3})")


def fraction_claims(text: Any) -> list[tuple[str, float]]:
    """句子裡的分數 → (原字, 百分比)。"""
    out = []
    for m in _FRACTION.finditer(strip_placeholders(text)):
        den, num = _num_value(fold(m.group(1))), _num_value(fold(m.group(2)))
        if den and num is not None and 0 < num <= den:
            out.append((m.group(0), num / den * 100))
    return out


@dataclass(frozen=True)
class SentenceClaims:
    """一句要核的主張——逐句核對（`check_sentence`）與錨點比對（`alpha.narrative.anchors`）共用：事實句的定義只有這一份（L16）。"""

    numbers: tuple[NumberClaim, ...]
    quotes: bool                  # 有引號裡的字
    names: tuple[str, ...]        # 要核的英文名稱
    attribution: str | None       # 「某份文件寫了什麼」的那個字（說、寫、年報……）
    schedule_like: bool           # 何時格或條件句：只核引號
    fractions: tuple[tuple[str, float], ...] = ()   # 分數（`fraction_claims`）：逐句核對不核，錨點比對核

    @property
    def is_fact(self) -> bool:
        """事實句：有數字（含分數）、引號、英文名稱，或說某份文件寫了什麼；何時格與條件句（反證、錯的訊號）不算。"""
        return (bool(self.numbers or self.fractions or self.quotes or self.names or self.attribution)
                and not self.schedule_like)


def sentence_claims(sentence: Sentence, *, self_names: Sequence[str], as_of: date | None = None) -> SentenceClaims:
    # 寫的那天之後的日子（自己設的到期、未來的排程）原文裡本來就沒有，不核
    commands = _command_spans(sentence.text)
    numbers = [c for c in number_claims(sentence.text) if (as_of is None or not c.is_future(as_of))
               and not any(a <= c.pos < b for a, b in commands)]
    condition = sentence.condition or bool(_CONDITION_SENTENCE.search(sentence.text))
    if sentence.where in TARGET_WHERES:
        numbers = [c for c in numbers if not _is_target(c, sentence.text)]
    quotes_present = bool(_QUOTE.search(strip_placeholders(sentence.text)))
    names = latin_names(sentence.text, skip=self_names)
    attribution = _ATTRIBUTION.search(squash(strip_placeholders(sentence.text)))
    schedule_like = sentence.where in SCHEDULE_WHERES or condition
    if schedule_like:
        # 何時格講的是之後會發生什麼（下一份財報、法說、到期）；反證與錯的訊號是我們設的條件——都只核引號裡的字。
        # 何時格的日期由裁決點那一套核（候選板「裁決點過了」）
        numbers, names, attribution = [], [], None
    return SentenceClaims(numbers=tuple(numbers), quotes=quotes_present, names=tuple(names),
                          attribution=attribution.group(0) if attribution else None, schedule_like=schedule_like,
                          fractions=() if schedule_like else tuple(fraction_claims(sentence.text)))


def check_sentence(sentence: Sentence, ctx: CheckContext, *, self_company: str, self_names: Sequence[str],
                   as_of: date | None = None) -> SentenceCheck:
    kinds = tuple(ctx.resolve(r).kind for r in sentence.refs)
    readable = [r for r in sentence.refs if ctx.resolve(r).kind in READABLE_REF_KINDS and ctx.resolve(r).lines]
    facts = ctx.facts(readable)
    ranked = rank_lines(sentence.text, facts.lines)
    best = ranked[0][0] if ranked else 0.0
    # 對到的行是我們自己寫的（`SourceLine.own`）照列、標出來；一手原文最好的一行另算——「只對到自家文字」用
    best_primary = next((cov for cov, f, _n in ranked if not f.line.own), 0.0)
    matches = [Match(f.line.label, _window(f.line.text, needles), cov, own=f.line.own)
               for cov, f, needles in ranked[:TOP_LINES] if cov >= SHOW_LINE_ABOVE]
    matched_feats = [f for cov, f, _n in ranked[:3] if cov >= SHOW_LINE_ABOVE]
    elsewhere_feats: list[_LineFeat] = []
    elsewhere_facts: SourceFacts | None = None
    if best < NO_MATCH_BELOW and sentence.fallback_refs:
        other = [r for r in sentence.fallback_refs if ctx.resolve(r).kind in READABLE_REF_KINDS and ctx.resolve(r).lines]
        if other:
            elsewhere_facts = ctx.facts(other)
            more = rank_lines(sentence.text, elsewhere_facts.lines)
            if more and more[0][0] >= NO_MATCH_BELOW:
                matches += [Match(f.line.label, _window(f.line.text, needles), cov, elsewhere=True, own=f.line.own)
                            for cov, f, needles in more[:TOP_LINES] if cov >= NO_MATCH_BELOW]
                elsewhere_feats = [f for cov, f, _n in more[:3] if cov >= NO_MATCH_BELOW]
                matched_feats += elsewhere_feats
    flags: list[Flag] = []
    claims = sentence_claims(sentence, self_names=self_names, as_of=as_of)
    numbers, quotes_present, names, attribution = list(claims.numbers), claims.quotes, list(claims.names), claims.attribution
    schedule_like = claims.schedule_like
    if not readable:
        if numbers or quotes_present or names or attribution:
            what = [*(c.raw.strip() for c in numbers), *names][:6]
            flags.append(Flag("unverifiable", "、".join(what) if what else (
                "引號裡的字" if quotes_present else f"「{attribution}」說的內容")))
        return SentenceCheck(sentence, tuple(matches), tuple(flags), kinds, ctx.carried.get(sentence.digest))
    union = facts if elsewhere_facts is None else _merge(facts, elsewhere_facts)
    missing_q = quote_problems(sentence.text, union)
    if missing_q:
        flags.append(Flag("quote_missing", "、".join(f"「{q}」" for q in missing_q)))
    near = source_facts([f.line for f in matched_feats])
    doc_meta = ctx.meta_facts(readable + ([r for r in sentence.fallback_refs if r not in readable]
                                          if elsewhere_facts is not None else []))
    missing_n = []
    for c in numbers:
        if number_found(c, union, near):
            continue
        if number_found(c, union, near, doc_meta):
            if c.kind not in ("date", "month") or _names_document(c, sentence.text):
                continue
            missing_n.append(c.raw.strip() + META_ONLY_NOTE)
            continue
        missing_n.append(c.raw.strip())
    if missing_n:
        flags.append(Flag("number_missing", "、".join(missing_n)))
    labels = " ".join(fold(f.line.label) for f in union.lines)
    missing_names = [n for n in names if not (_latin_in(n, union.spaced) or _latin_in(n, labels))]
    if not schedule_like:
        missing_names += registry_name_problems(sentence.text, union, names=ctx.folded_names(), self_company=self_company,
                                                labels=labels)
    if missing_names:
        flags.append(Flag("name_missing", "、".join(missing_names)))
    # 限定詞查「跟這句對得上的那幾行」：長句一句講好幾件事，前三行常常只對到其中一件（KSHINTL.NS「印度最大、唯一核准」）；
    # 別格引用對到的行另外接上（原本用 matched_feats[3:] 切，自己那格對到不滿三行時把它們切掉了；11-12 R1）
    qual_lines = [f for cov, f, _n in ranked[:8] if cov >= max(SHOW_LINE_ABOVE, best * 0.5)] + elsewhere_feats
    missing_qual = qualifier_problems(sentence.text, qual_lines) if not schedule_like else []
    if missing_qual:
        flags.append(Flag("qualifier_missing", "、".join(f"「{q}」" for q in missing_qual)))
    # 「沒對到」只對事實句標（`SentenceClaims.is_fact`）。判斷句（「還不賭，缺一件事」）本來就不在原文裡——
    # 標了是恆亮的燈（L14-4），照樣要讀，但不是這一種問題
    fact = claims.is_fact
    if fact and best < NO_MATCH_BELOW and not any(m.elsewhere for m in matches):
        flags.append(Flag("no_match", f"最好的一行只對到 {best:.0%}"))
    elif fact and best >= NO_MATCH_BELOW and best_primary < NO_MATCH_BELOW:
        # 對得上的只有我們自己寫的字（2026-11-13）：以前這種句子不標——工具拿我們的改寫當原文，等於替自己背書（L18）
        flags.append(Flag("own_text_only", f"一手原文最好的一行只對到 {best_primary:.0%}，我們自己寫的字對到 {best:.0%}"))
    return SentenceCheck(sentence, tuple(matches), tuple(flags), kinds, ctx.carried.get(sentence.digest))


def _merge(a: SourceFacts, b: SourceFacts) -> SourceFacts:
    return _merge_all([a, b])


def _merge_all(parts: Sequence[SourceFacts]) -> SourceFacts:
    out = SourceFacts(lines=[f for p in parts for f in p.lines], squashed="\n".join(p.squashed for p in parts),
                      spaced=" ".join(p.spaced for p in parts))
    for p in parts:
        out.years |= p.years
        out.months |= p.months
        out.dates |= p.dates
        out.quarters |= p.quarters
        out.pcts += p.pcts
        out.values += p.values
    return out


@dataclass(frozen=True)
class CheckResult:
    brief: BriefText
    story_id: str | None
    checks: tuple[SentenceCheck, ...]
    ref_counts: Mapping[str, int]           # 各種引用幾條（整份；`REF_KINDS`）
    ref_problems: tuple[str, ...]           # 該讀得到卻讀不到的引用

    @property
    def flagged(self) -> list[SentenceCheck]:
        return [c for c in self.checks if c.flagged]

    @property
    def carried(self) -> list[SentenceCheck]:
        return [c for c in self.checks if c.carried]

    @property
    def digests(self) -> list[str]:
        return [c.sentence.digest for c in self.checks]


def check_brief(brief: BriefText, ctx: CheckContext, *, story: Mapping[str, Any] | None = None,
                self_names: Sequence[str] = ()) -> CheckResult:
    sentences = build_sentences(brief, story=story)
    refs = list(dict.fromkeys([*brief.all_refs, *(r for s in sentences for r in s.refs)]))
    counts: dict[str, int] = {}
    problems = []
    for ref in refs:
        resolved = ctx.resolve(ref)
        counts[resolved.kind] = counts.get(resolved.kind, 0) + 1
        if resolved.problem:
            problems.append(f"{ref}：{resolved.problem}")
    checks = tuple(check_sentence(s, ctx, self_company=brief.company_id, self_names=self_names, as_of=brief.as_of)
                   for s in sentences)
    return CheckResult(brief=brief, story_id=str(story.get("story_id")) if story and story.get("story_id") else None,
                       checks=checks, ref_counts=counts, ref_problems=tuple(problems))


# ---------------------------------------------------------------------------
# 呈現
# ---------------------------------------------------------------------------

def where_label(where: str) -> str:
    from .contracts import SLOT_LABELS_V2
    from .depth_check import DEPTH_CHECK_ITEMS
    from .story import STORY_SLOT_LABELS

    if where == "candidate":
        return "候選理由"
    if where == "story:candidate":
        return "故事：候選理由"
    if where.startswith("depth:"):
        return "深挖清單：" + dict(DEPTH_CHECK_ITEMS).get(where[6:], where[6:])
    if where.startswith("story:"):
        return "故事：" + STORY_SLOT_LABELS.get(where[6:], where[6:])
    return SLOT_LABELS_V2.get(where, where)


def summary_line(result: CheckResult) -> str:
    kinds = "、".join(f"{REF_KINDS[k].split('（')[0]} {n}" for k, n in result.ref_counts.items() if n)
    return (f"句數 {len(result.checks)}｜沿用上一版已核 {len(result.carried)}｜有旗標 {len(result.flagged)}｜引用：{kinds or '無'}"
            + (f"｜⚠ 讀不到的引用 {len(result.ref_problems)}" if result.ref_problems else ""))


def render_markdown(result: CheckResult, *, flags_only: bool = False) -> list[str]:
    b = result.brief
    head = f"# {b.ticker} 逐句核對（{b.brief_id or '草稿，還沒寫入'}" + (f"；故事 {result.story_id}" if result.story_id else "") + "）"
    lines = [head, summary_line(result),
             "反證與加碼條件是對未來的條件，不在逐句核對範圍；括號裡引用 `python -m …` 命令的數字是那條命令當天的輸出，這裡不核。"
             "旗標是要先看的句子，不是判定——沒有旗標不等於對（主詞收窄機器看不出來）；每一句都要跟列出的原文行並排讀。"]
    if result.ref_problems:
        lines.append("⚠ 讀不到的引用：" + "；".join(result.ref_problems))
    current = None
    for c in result.checks:
        if c.sentence.where != current:
            current = c.sentence.where
            lines.append(f"\n## {where_label(current)}")
        s = c.sentence
        if c.carried:
            lines.append(f"{s.n}. （上一版已核 {c.carried}）{s.text}")
            continue
        if flags_only and not c.flags:
            lines.append(f"{s.n}. {s.text}")
            continue
        flag_text = "｜".join(f"⚑{FLAG_KINDS[f.kind]}：{f.detail}" for f in c.flags)
        lines.append(f"{s.n}. {s.text}" + (f"\n   {flag_text}" if flag_text else ""))
        if not any(k in READABLE_REF_KINDS for k in c.ref_kinds):
            lines.append("   （這一句的引用是 " + "、".join(sorted({REF_KINDS[k].split('（')[0] for k in c.ref_kinds})) + "，這裡不核）")
        for m in c.matches:
            lines.append(f"   ↳ {m.label}{'（別格的引用）' if m.elsewhere else ''}{OWN_LABEL if m.own else ''}｜{m.text}")
    return lines


def as_dict(result: CheckResult) -> dict[str, Any]:
    return {"ticker": result.brief.ticker, "brief_id": result.brief.brief_id, "story_id": result.story_id,
            "sentences": len(result.checks), "carried": len(result.carried), "flagged": len(result.flagged),
            "ref_counts": dict(result.ref_counts), "ref_problems": list(result.ref_problems),
            "checks": [{"n": c.sentence.n, "where": c.sentence.where, "text": c.sentence.text, "digest": c.sentence.digest,
                        "carried": c.carried, "flags": [{"kind": f.kind, "detail": f.detail} for f in c.flags],
                        "matches": [{"label": m.label, "text": m.text, "coverage": round(m.coverage, 3),
                                     "elsewhere": m.elsewhere, "own": m.own} for m in c.matches]} for c in result.checks]}


__all__ = ["BriefText", "CheckContext", "CheckResult", "FLAG_KINDS", "Flag", "Match", "NumberClaim", "QUALIFIERS",
           "READABLE_REF_KINDS", "REF_KINDS", "ResolvedRef", "Sentence", "SentenceCheck", "SentenceClaims", "SourceFacts",
           "SourceLine", "fraction_claims", "sentence_claims",
           "as_dict", "brief_text_from_record", "brief_text_from_spec", "build_sentences", "check_brief", "check_sentence",
           "classify_ref", "cn_to_int", "fold", "latin_names", "number_claims", "number_found", "qualifier_problems",
           "quote_problems", "rank_lines", "registry_name_problems", "render_markdown", "source_facts", "split_sentences",
           "squash", "strip_placeholders", "summary_line", "where_label"]
