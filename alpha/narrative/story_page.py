"""個股故事頁的純規則（Phase 8 plan `docs/plans/2026-11-26-001-feat-phase8-story-page-app-plan.md` §2.1–2.4）。

故事頁＝研究 session 照 `skills/stock-story` 寫的一頁長故事（敘事的長版），一版對一版敘事；APP 個股頁把它印在
「系統裡的它」前面。本模組**只有規則**——不讀檔、不連圖、不讀別的帳：

- 片段的白名單（標籤、屬性、網址）：**唯一一份**。APP 經 `.meta.json` 拿同一份（`whitelist_payload`；L16），
  物化時再核一次（`fragment_problems`），前端照它重建節點——寫入、物化、畫面三道。
- 節序與結構、看得到的字、W 類寫法檢查、宣告（`page.json`）的形狀。

讀帳、核現行敘事、核等待 registry 與圖上節點的在 `alpha.providers.story_pages`。

檢查只決定「這一頁收不收進故事頁的帳」：**不是 authority**——不決定候選狀態、不擋任何別的寫入、不入圖。
ERROR（E1–E6）拒收；WARN（W1–W10）照印、記進帳的那一列，由寫的人逐條看過。

⚠ `html.parser` 會把標籤與屬性名轉小寫：SVG 的 `viewBox`、`preserveAspectRatio` 在這裡一律用小寫比對；
前端重建時保留瀏覽器解析出的大小寫（plan §5 已知陷阱）。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from typing import Any, Iterator, Mapping, Sequence

# ---------------------------------------------------------------- 契約：節序

#: 節序（`id` 是契約）。`system-gap` 選填，其餘都要有、順序固定。
SECTION_IDS: tuple[str, ...] = ("hero", *(f"q{i}" for i in range(1, 13)), "bet-kind", "system", "system-gap",
                                "self-eval", "sources")
OPTIONAL_SECTION_IDS: frozenset[str] = frozenset({"system-gap"})
QUESTION_IDS: tuple[str, ...] = tuple(f"q{i}" for i in range(1, 13))
#: 節用哪個標籤（沒列的是 section）。
SECTION_TAGS: Mapping[str, str] = {"hero": "header", "sources": "details"}
#: 頁首的段落數（一個 h1＋三到四段故事）。
HERO_PARAGRAPHS: tuple[int, int] = (3, 4)

# ---------------------------------------------------------------- 契約：白名單（唯一一份）

HTML_TAGS: frozenset[str] = frozenset((
    "article header section h1 h2 h3 h4 p ul ol li table thead tbody tr th td caption figure figcaption "
    "details summary blockquote strong em b i sup sub br hr span div a small code").split())
SVG_TAGS: frozenset[str] = frozenset("svg g path line polyline polygon rect circle ellipse text tspan title desc defs marker"
                                     .split())
VOID_TAGS: frozenset[str] = frozenset({"br", "hr"})
GLOBAL_ATTRS: frozenset[str] = frozenset({"id", "class", "title", "lang", "data-slot", "data-wait", "data-src", "data-label"})
TAG_ATTRS: Mapping[str, frozenset[str]] = {
    "a": frozenset({"href"}),
    "th": frozenset({"colspan", "rowspan", "scope"}),
    "td": frozenset({"colspan", "rowspan", "scope"}),
    "details": frozenset({"open"}),
}
#: SVG 的幾何與呈現屬性（小寫比對）。plan 原列之外補了 marker 的六個與 text 的 dx／dy——都是數字或關鍵字，畫箭頭與標字用得到。
SVG_ATTRS: frozenset[str] = frozenset((
    "viewbox width height x y x1 y1 x2 y2 cx cy r rx ry dx dy d points transform fill stroke stroke-width "
    "stroke-dasharray stroke-linecap stroke-linejoin opacity fill-opacity stroke-opacity text-anchor dominant-baseline "
    "font-size font-weight marker-start marker-end markerwidth markerheight refx refy orient markerunits "
    "preserveaspectratio role aria-label aria-hidden xmlns").split())
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
#: 只是給人讀的字的屬性：不核網址（「data: 2026」寫在 title 裡不會被執行）。
_TEXT_ATTRS: frozenset[str] = frozenset({"title", "aria-label", "data-label", "class", "id", "lang"})

#: 每句的來源等級（`<span class="src" data-src="…">`）：封閉字彙。
SOURCE_LEVELS: tuple[str, ...] = ("自述", "買方", "第三方", "推一步", "網路")
#: 頁上等待的種類（宣告 `waits[].kind`）。
WAIT_KINDS: tuple[str, ...] = ("disproof", "confirm", "date")
#: 自評的三個值（十二題各一個）。
SELF_EVAL_VALUES: tuple[str, ...] = ("full", "half", "none")
#: 看得到的字的合理範圍（skill：1.1 到 1.5 萬為度；低於八千多半是缺節）。只 WARN。
VISIBLE_CHARS_RANGE: tuple[int, int] = (8_000, 15_000)
#: 片段大小上限（一頁 1.5 萬字加幾張圖約 0.2 MB；超過十倍多半是貼錯檔）。
MAX_HTML_BYTES = 2_000_000

_ID = re.compile(r"^[A-Za-z][\w\-:.]{0,63}$")
_CLASS = re.compile(r"^[A-Za-z0-9_\- ]{1,120}$")
_WAIT_KEY = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")
_SAFE_HREF = re.compile(r"^(?:https://[^\s\"'<>\\]+|#[A-Za-z][\w\-:.]*)$")
_LOCAL_URL_REF = re.compile(r"^url\(\s*#[A-Za-z][\w\-:.]*\s*\)$")
_BAD_SCHEME = re.compile(r"(?:javascript|vbscript|data|file|blob):|http://")
#: E4：頁上不得出現的私有字串（私有網頁網址、本機路徑）。
PRIVATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("私有網頁網址", re.compile(r"claude\.ai/artifact", re.I)),
    ("本機私有資料夾路徑", re.compile(r"library[\\/]+private", re.I)),
    ("本機磁碟路徑", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")),
    ("本機檔案網址", re.compile(r"file:/", re.I)),
)

# ---------------------------------------------------------------- 契約：W 類寫法檢查的字表

#: W2：頁首指向後面或別處的寫法。
HERO_FORWARD_REF = re.compile(r"見第|見下|如下表|如下圖|下一節|第\s*[0-9０-９一二三四五六七八九十]+\s*[題節]")
#: W3：帶單位的數字（年、月、日、季不算——日期重複出現是正常的）。
_NUMBER_UNIT = re.compile(
    r"(?<![\d.,])(\d[\d,]*(?:\.\d+)?)\s*"
    r"(百萬美元|億美元|萬美元|美元|億元|萬元|元|億|萬|%|％|倍|個月|週|天|千瓦|瓦|顆|台|片|張|家|位|筆|則|吋|奈米|nm|GW|MW|kW)")
REPEAT_LIMIT = 4
#: W5：系統的詞不直接上頁（「系統裡的它」由程式填；`#system-gap` 那一節可以用）。
SYSTEM_WORD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("會死嗎", re.compile("會死嗎")),
    ("起始門", re.compile("起始門")),
    ("缺 X", re.compile(r"缺\s?X(?![A-Za-z])")),
    ("neither", re.compile(r"(?<![A-Za-z])neither(?![A-Za-z])", re.I)),
    ("judgment", re.compile(r"(?<![A-Za-z])judgment(?![A-Za-z])", re.I)),
    ("co:／tech: 節點代號", re.compile(r"(?<![A-Za-z])(?:co|tech):[a-z]")),
    ("系統紀錄 id", re.compile(r"(?<![A-Za-z0-9])(?:ew|ib|sr|lead|sp|st)_[0-9a-z]{3,}")),
)
#: W6：長引號（中文 13 字以上；英文 6 個詞以上）。
_ZH_QUOTE = re.compile(r"「([^「」]{13,})」")
_EN_QUOTE = re.compile(r"[\"“]([^\"“”]{3,}?)[\"”]")
_EN_WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")
EN_QUOTE_MIN_WORDS = 6
#: W9：等待登記了沒由程式印，頁上不手寫。
_HAND_REGISTERED = re.compile(r"已登記|沒登記|未登記")
_SENTENCE_SPLIT = re.compile(r"[。！？!?；;\n]")

TEXT = "#text"

# ---------------------------------------------------------------- 結果

@dataclass(frozen=True)
class Finding:
    """一條檢查結果。`code`：E1–E6 拒收；W1–W10 照印。`samples`：命中的句子或數（最多十筆）。"""

    code: str
    message: str
    samples: tuple[str, ...] = ()

    @property
    def is_error(self) -> bool:
        return self.code.startswith("E")

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "samples": list(self.samples)}

    def line(self) -> str:
        """帳上那一列記的摘要（一行）。"""
        more = f"（{len(self.samples)} 處）" if self.samples else ""
        return f"{self.code} {self.message}{more}"


@dataclass
class PageCheck:
    findings: list[Finding]
    visible_chars: int
    text: str
    wait_keys: frozenset[str] = frozenset()

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.is_error]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if not f.is_error]


def _sample(items: Sequence[str], limit: int = 10, width: int = 80) -> tuple[str, ...]:
    out = []
    for item in list(items)[:limit]:
        text = " ".join(str(item).split())
        out.append(text if len(text) <= width else text[:width] + "…")
    return tuple(out)

# ---------------------------------------------------------------- 解析

@dataclass(eq=False)
class Node:
    tag: str
    attrs: tuple[tuple[str, str | None], ...] = ()
    children: list["Node"] = field(default_factory=list)
    text: str = ""
    line: int = 0
    svg: bool = False          # 在 svg 裡（含 svg 自己）

    def attr(self, name: str) -> str | None:
        for key, value in self.attrs:
            if key == name:
                return value
        return None

    def has_attr(self, name: str) -> bool:
        return any(key == name for key, _value in self.attrs)

    @property
    def elements(self) -> list["Node"]:
        return [c for c in self.children if c.tag != TEXT]

    def iter(self) -> Iterator["Node"]:
        for child in self.children:
            yield child
            yield from child.iter()


class _Builder(HTMLParser):
    """容錯的樹：不認得的照樣建進樹裡（交給白名單擋），結構錯記成 E2，註解與宣告記成 E1。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack: list[Node] = [self.root]
        self.problems: list[Finding] = []

    def _here(self) -> int:
        return self.getpos()[0]

    def _open(self, tag: str, attrs: list[tuple[str, str | None]], *, closed: bool) -> None:
        parent = self.stack[-1]
        node = Node(tag, tuple(attrs), line=self._here(), svg=parent.svg or tag == "svg")
        parent.children.append(node)
        if closed:
            if not node.svg and tag not in VOID_TAGS:
                self.problems.append(Finding("E2", f"第 {node.line} 行 <{tag}/> 自閉合——HTML 標籤要寫成對（瀏覽器不認 HTML 的自閉合）"))
            return
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs, closed=False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs, closed=True)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                skipped = [n.tag for n in self.stack[depth + 1:]]
                if skipped:
                    self.problems.append(Finding(
                        "E2", f"第 {self._here()} 行 </{tag}> 之前有沒閉合的 " + "、".join(f"<{t}>" for t in skipped)))
                del self.stack[depth:]
                return
        self.problems.append(Finding("E2", f"第 {self._here()} 行多出來的 </{tag}>"))

    def handle_data(self, data: str) -> None:
        parent = self.stack[-1]
        if parent.children and parent.children[-1].tag == TEXT:
            parent.children[-1].text += data
        else:
            parent.children.append(Node(TEXT, text=data, line=self._here(), svg=parent.svg))

    def handle_comment(self, data: str) -> None:
        self.problems.append(Finding("E1", f"第 {self._here()} 行有註解——片段不收註解"))

    def handle_decl(self, decl: str) -> None:
        self.problems.append(Finding("E1", f"第 {self._here()} 行有 <!{decl[:20]}> 宣告——片段只要 <article>，不要整份 HTML"))

    def handle_pi(self, data: str) -> None:
        self.problems.append(Finding("E1", f"第 {self._here()} 行有處理指令 <?…>"))

    def unknown_decl(self, data: str) -> None:
        self.problems.append(Finding("E1", f"第 {self._here()} 行有 <![…]> 區段"))

    def finish(self) -> None:
        self.close()
        if len(self.stack) > 1:
            self.problems.append(Finding(
                "E2", "沒閉合：" + "、".join(f"<{n.tag}>（第 {n.line} 行）" for n in self.stack[1:])))


def parse_fragment(html: str) -> tuple[Node, list[Finding]]:
    """片段 → 樹與解析時的問題。不丟例外：讀不懂的地方都變成問題。"""
    builder = _Builder()
    builder.feed(html)
    builder.finish()
    return builder.root, builder.problems

# ---------------------------------------------------------------- E1–E4

def _squash(value: str) -> str:
    """拿掉空白與控制字元再小寫——「java\\tscript:」在瀏覽器照樣是 javascript:。"""
    return "".join(ch for ch in value if not (ch.isspace() or unicodedata.category(ch) in ("Cc", "Cf"))).lower()


def _forbidden_attribute(name: str) -> str | None:
    """不管白名單怎麼寫都拒收的屬性（第二道；白名單本來就沒有它們）。"""
    if name.startswith("on"):
        return "事件屬性一律拒收"
    if name == "style":
        return "style 屬性拒收——樣式用 class（APP 的安全標頭也擋行內樣式）"
    return None


def _attr_problems(node: Node, name: str, value: str | None, allowed: frozenset[str]) -> list[Finding]:
    where = f"第 {node.line} 行 <{node.tag} {name}>"
    reason = _forbidden_attribute(name)
    if reason:
        return [Finding("E1", f"{where}：{reason}")]
    if name not in allowed:
        return [Finding("E1", f"{where}：屬性不在白名單")]
    raw = value or ""
    if name == "xmlns":
        if node.tag == "svg" and raw.strip() == SVG_NAMESPACE:
            return []
        return [Finding("E1", f"{where}：xmlns 只准寫在 svg 上、值是 {SVG_NAMESPACE}")]
    if name not in _TEXT_ATTRS:
        squashed = _squash(raw)
        if _BAD_SCHEME.search(squashed):
            return [Finding("E1", f"{where}：不收 javascript:、data:、http://、file: 這類網址")]
        if ("url(" in squashed or "expression(" in squashed) and not _LOCAL_URL_REF.fullmatch(raw.strip()):
            return [Finding("E1", f"{where}：url(…) 只准指向頁內的 #id")]
    if name == "href" and not _SAFE_HREF.fullmatch(raw.strip()):
        return [Finding("E1", f"{where}：連結只准 https:// 或頁內 #錨點")]
    if name == "id" and not _ID.fullmatch(raw):
        return [Finding("E1", f"{where}：id 只用英數與 - _ : .，英文字母開頭")]
    if name == "class" and not _CLASS.fullmatch(raw):
        return [Finding("E1", f"{where}：class 只用英數、- 與 _")]
    if name == "data-src" and raw not in SOURCE_LEVELS:
        return [Finding("E1", f"{where}：來源等級只有 {'／'.join(SOURCE_LEVELS)}（收到 {raw!r}）")]
    if name == "data-slot" and not (raw == "system" and node.attr("id") == "system"):
        return [Finding("E1", f"{where}：data-slot 只用在 <section id=\"system\" data-slot=\"system\">")]
    if name == "data-wait" and not _WAIT_KEY.fullmatch(raw):
        return [Finding("E1", f"{where}：data-wait 的 key 只用英數、- 與 _（32 字內）")]
    return []


def whitelist_problems(root: Node) -> list[Finding]:
    """E1：白名單外的標籤、屬性、網址；svg 裡只准 SVG 標籤，SVG 標籤只准在 svg 裡。"""
    out: list[Finding] = []
    for node in root.iter():
        if node.tag == TEXT:
            continue
        if node.svg:
            if node.tag not in SVG_TAGS:
                out.append(Finding("E1", f"第 {node.line} 行 svg 裡有 <{node.tag}>——svg 裡只准 SVG 的白名單標籤"))
                continue
            allowed = GLOBAL_ATTRS | SVG_ATTRS
        else:
            if node.tag not in HTML_TAGS:
                out.append(Finding("E1", f"第 {node.line} 行 <{node.tag}> 不在白名單"
                                   + ("（SVG 標籤要包在 <svg> 裡）" if node.tag in SVG_TAGS else "")))
                continue
            allowed = GLOBAL_ATTRS | TAG_ATTRS.get(node.tag, frozenset())
        for name, value in node.attrs:
            out.extend(_attr_problems(node, name, value, allowed))
    return out


def _article(root: Node) -> Node | None:
    elements = root.elements
    if len(elements) == 1 and elements[0].tag == "article" and "story-page" in (elements[0].attr("class") or "").split():
        return elements[0]
    return None


def structure_problems(root: Node) -> list[Finding]:
    """E2：根元素、節序、每節的標題、頁首的段落數、id 不重複。"""
    out: list[Finding] = []
    article = _article(root)
    if article is None:
        got = "、".join(f"<{e.tag}>" for e in root.elements) or "沒有元素"
        return [Finding("E2", f"根元素必須剛好一個 <article class=\"story-page\">（收到 {got}）")]
    if any(c.tag == TEXT and c.text.strip() for c in root.children):
        out.append(Finding("E2", "<article> 外面有字"))
    if any(c.tag == TEXT and c.text.strip() for c in article.children):
        out.append(Finding("E2", "<article> 底下直接有字——字要寫在節裡"))
    kids = article.elements
    ids = [k.attr("id") or f"<{k.tag}>" for k in kids]
    expected = [sid for sid in SECTION_IDS if sid not in OPTIONAL_SECTION_IDS or sid in ids]
    if ids != expected:
        missing = [sid for sid in expected if sid not in ids]
        extra = [i for i in ids if i not in SECTION_IDS]
        bits = []
        if missing:
            bits.append("少了 " + "、".join(missing))
        if extra:
            bits.append("多了 " + "、".join(extra))
        if not bits:
            bits.append("順序不對")
        out.append(Finding("E2", "節序不對：" + "；".join(bits) + f"——要 {' → '.join(expected)}", _sample(ids, 30, 30)))
    for kid in kids:
        sid = kid.attr("id") or ""
        want = SECTION_TAGS.get(sid, "section")
        if sid in SECTION_IDS and kid.tag != want:
            out.append(Finding("E2", f"#{sid} 要用 <{want}>（收到 <{kid.tag}>）"))
    by_id = {k.attr("id"): k for k in kids}
    hero = by_id.get("hero")
    h1s = [n for n in root.iter() if n.tag == "h1"]
    if len(h1s) != 1 or hero is None or h1s[0] not in hero.elements:
        out.append(Finding("E2", f"整頁要剛好一個 <h1>，而且是頁首的第一個元素（收到 {len(h1s)} 個）"))
    if hero is not None:
        tags = [e.tag for e in hero.elements]
        paragraphs = tags.count("p")
        low, high = HERO_PARAGRAPHS
        if not tags or tags[0] != "h1" or set(tags[1:]) != {"p"} or not low <= paragraphs <= high:
            out.append(Finding("E2", f"頁首只放一個 <h1> 加 {low} 到 {high} 段 <p>（收到 {' '.join(tags) or '空的'}）"))
    for sid in (*QUESTION_IDS, "bet-kind", "system-gap", "self-eval"):
        node = by_id.get(sid)
        if node is not None and (not node.elements or node.elements[0].tag != "h2"):
            out.append(Finding("E2", f"#{sid} 的第一個元素要是 <h2>（那一節的結論句）"))
    sources = by_id.get("sources")
    if sources is not None and (not sources.elements or sources.elements[0].tag != "summary"):
        out.append(Finding("E2", "#sources 的第一個元素要是 <summary>"))
    seen: dict[str, int] = {}
    for node in root.iter():
        if node.tag != TEXT and node.attr("id"):
            seen[node.attr("id") or ""] = seen.get(node.attr("id") or "", 0) + 1
    dup = sorted(i for i, n in seen.items() if n > 1)
    if dup:
        out.append(Finding("E2", "id 重複：" + "、".join(dup)))
    return out


def system_slot_problems(root: Node) -> list[Finding]:
    """E3：`#system` 必須是空的（APP 用個股物化檔填；手抄的隔天就過期）。"""
    article = _article(root)
    node = next((k for k in (article.elements if article else []) if k.attr("id") == "system"), None)
    if node is None:
        return []
    out = []
    if node.elements or any(c.tag == TEXT and c.text.strip() for c in node.children):
        out.append(Finding("E3", "#system 裡有內容——「系統裡的它」由 APP 填，頁上只留空位；對不上的地方寫在 #system-gap"))
    if node.attr("data-slot") != "system":
        out.append(Finding("E3", "#system 要帶 data-slot=\"system\""))
    return out


def private_string_problems(html: str, root: Node | None = None) -> list[Finding]:
    """E4：頁上（原始碼與解出來的字）不得出現私有網頁網址、本機路徑。"""
    texts = [html]
    if root is not None:
        texts.append("".join(n.text for n in root.iter() if n.tag == TEXT))
        texts.extend(v or "" for n in root.iter() if n.tag != TEXT for _k, v in n.attrs)
    out = []
    for label, pattern in PRIVATE_PATTERNS:
        hits = [m.group(0) for text in texts for m in pattern.finditer(text)]
        if hits:
            out.append(Finding("E4", f"頁上有{label}——私有的東西不上頁", _sample(sorted(set(hits)))))
    return out


def fragment_problems(html: str) -> list[Finding]:
    """E1–E4（物化時的第二道；不需要宣告、不讀別的帳）。空清單＝可以上畫面。"""
    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        return [Finding("E2", f"片段超過 {MAX_HTML_BYTES:,} bytes")]
    root, problems = parse_fragment(html)
    return [*problems, *whitelist_problems(root), *structure_problems(root), *system_slot_problems(root),
            *private_string_problems(html, root)]

# ---------------------------------------------------------------- 看得到的字

_BLOCK: frozenset[str] = frozenset(
    "article h1 h2 h3 h4 p ul ol li table tr caption figure figcaption summary blockquote div br hr svg".split())
#: 節的邊界：前後各空一行。
_SECTION_BLOCK: frozenset[str] = frozenset({"header", "section", "details"})
_CELL: frozenset[str] = frozenset({"th", "td"})
_INVISIBLE_SVG: frozenset[str] = frozenset({"title", "desc"})
_NL, _TAB, _GAP = "\x00", "\x01", "\x02"


def _walk_text(node: Node, out: list[str], *, include_details: bool) -> None:
    for child in node.children:
        if child.tag == TEXT:
            out.append(child.text)
            continue
        if child.svg and child.tag in _INVISIBLE_SVG:
            continue
        if child.tag in _SECTION_BLOCK:
            out.append(_NL + _GAP + _NL)
        elif child.tag in _BLOCK:
            out.append(_NL)
        if child.tag == "details" and not include_details:
            summary = next((e for e in child.elements if e.tag == "summary"), None)
            if summary is not None:
                _walk_text(summary, out, include_details=include_details)
            out.append(_NL + _GAP + _NL)
            continue
        if child.tag in _CELL:
            out.append(_TAB)
        if child.has_attr("data-src"):          # 來源等級：畫面上是一個小標，文字版寫成（買方）
            out.append("（")
        _walk_text(child, out, include_details=include_details)
        if child.has_attr("data-src"):
            out.append("）")
        if child.tag in _SECTION_BLOCK:
            out.append(_NL + _GAP + _NL)
        elif child.tag in _BLOCK:
            out.append(_NL)
        elif child.svg and child.tag == "text":
            out.append(" ")


def _tidy(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).replace(_TAB, " ｜ ")
    out: list[str] = []
    for line in text.split(_NL):
        line = line.strip(" ｜")
        if line == _GAP:
            if out and out[-1]:
                out.append("")
        elif line:
            out.append(line)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n" if out else ""


def visible_text(node: Node) -> str:
    """看得到的字：摺疊（`<details>`）只算它的 `<summary>`；SVG 的 title／desc 不算。區塊之間換行，表格儲存格以「｜」隔開。
    量字數、冷讀、W 類檢查共用這一個函式。"""
    out: list[str] = []
    _walk_text(node, out, include_details=False)
    return _tidy("".join(out))


def all_text(node: Node) -> str:
    """全部的字（含摺疊裡的出處與原話）——W6 核引號用。"""
    out: list[str] = []
    _walk_text(node, out, include_details=True)
    return _tidy("".join(out))


def visible_chars(text: str) -> int:
    """看得到的字數＝不含空白的字元數。"""
    return sum(1 for ch in text if not ch.isspace() and ch != "｜")

# ---------------------------------------------------------------- 引號

def normalize_for_match(text: str) -> str:
    """比對引號用：全半形（NFKC）、彎引號、空白一律拿掉。不跳字、不做語意比對。"""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", "", t)


def quotes_in(text: str) -> list[str]:
    """長引號：中文「…」13 字以上、英文 "…" 6 個詞以上。"""
    out = [m.group(1) for m in _ZH_QUOTE.finditer(text)]
    out += [m.group(1) for m in _EN_QUOTE.finditer(text) if len(_EN_WORD.findall(m.group(1))) >= EN_QUOTE_MIN_WORDS]
    return out


def quote_found(quote: str, corpus: str) -> bool:
    """`corpus` 是 `normalize_for_match` 過的出處全文。引號裡的「…」是刪節：每一段（4 字以上）各自要找得到。"""
    parts = [p for p in re.split(r"…|\.\.\.|⋯", quote) if len(normalize_for_match(p)) >= 4]
    return all(normalize_for_match(p) in corpus for p in parts)

# ---------------------------------------------------------------- 宣告

DECLARATION_KEYS: tuple[str, ...] = (
    "ticker", "brief_id", "checklist_version", "written_on", "evidence_pack", "quote_sources", "prices_seen",
    "price_as_of", "self_eval", "key_question", "rides", "graph_gaps", "waits", "cold_read")


def _iso_day(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
        return isinstance(value, str)
    except ValueError:
        return False


def _relative_path_ok(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    v = value.replace("\\", "/")
    return not (v.startswith("/") or re.match(r"^[A-Za-z]:", v) or ".." in v.split("/"))


def cold_read_problems(cold: Any) -> list[Finding]:
    """E6：冷讀紀錄。`{"skipped": 理由}`，或 `{"report": 相對路徑, "restated_ok": bool, "asked": n, "asked_outside": n}`。"""
    if not isinstance(cold, Mapping):
        return [Finding("E6", "cold_read 要是 {\"report\": …} 或 {\"skipped\": 理由}——交稿前要跑冷讀，沒跑寫理由")]
    if "skipped" in cold:
        if set(cold) != {"skipped"} or not str(cold.get("skipped") or "").strip():
            return [Finding("E6", "cold_read 沒跑時只寫 {\"skipped\": 理由}，理由不能空")]
        return []
    out = []
    if not _relative_path_ok(cold.get("report")):
        out.append(Finding("E6", "cold_read.report 要是這個資料夾裡的相對路徑（例：coldread/REPORT.md）"))
    if not isinstance(cold.get("restated_ok"), bool):
        out.append(Finding("E6", "cold_read.restated_ok 要是 true／false（讀者五句重述對不對得上頁首）"))
    asked, outside = cold.get("asked"), cold.get("asked_outside")
    if not (isinstance(asked, int) and not isinstance(asked, bool) and asked >= 0):
        out.append(Finding("E6", "cold_read.asked 要是 0 以上的整數（讀者還想問的條數）"))
    elif not (isinstance(outside, int) and not isinstance(outside, bool) and 0 <= outside <= asked):
        out.append(Finding("E6", "cold_read.asked_outside 要是 0 到 asked 之間的整數（其中清單外的條數）"))
    extra = sorted(set(cold) - {"report", "restated_ok", "asked", "asked_outside"})
    if extra:
        out.append(Finding("E6", "cold_read 有不認得的欄位：" + "、".join(extra)))
    return out


def declaration_problems(decl: Any, *, page_wait_keys: frozenset[str] | None = None) -> list[Finding]:
    """E5（宣告的形狀；跨帳的核對在 provider）與 E6（冷讀）。`page_wait_keys`：頁上 `data-wait` 的集合（None＝不比）。"""
    if not isinstance(decl, Mapping):
        return [Finding("E5", "page.json 要是一個 JSON object")]
    out: list[Finding] = []
    missing = [k for k in DECLARATION_KEYS if k not in decl and k != "cold_read"]
    if missing:
        out.append(Finding("E5", "宣告少了 " + "、".join(missing)))
    extra = sorted(set(decl) - set(DECLARATION_KEYS))
    if extra:
        out.append(Finding("E5", "宣告有不認得的欄位 " + "、".join(extra) + "（拼錯會讓那一格安靜消失）"))
    if "ticker" in decl and not (isinstance(decl["ticker"], str) and decl["ticker"].strip()):
        out.append(Finding("E5", "ticker 不能空"))
    if "brief_id" in decl and not (isinstance(decl["brief_id"], str) and decl["brief_id"].startswith("ib_")):
        out.append(Finding("E5", "brief_id 要是敘事 id（ib_…）"))
    if "checklist_version" in decl and not (isinstance(decl["checklist_version"], str)
                                            and decl["checklist_version"].strip()):
        out.append(Finding("E5", "checklist_version 不能空（照哪一版問題清單寫的）"))
    if "written_on" in decl and not _iso_day(decl["written_on"]):
        out.append(Finding("E5", "written_on 要是日期（YYYY-MM-DD）"))
    if "evidence_pack" in decl and not isinstance(decl["evidence_pack"], str):
        out.append(Finding("E5", "evidence_pack 要是字串（沒有就空字串）"))
    if "quote_sources" in decl:
        qs = decl["quote_sources"]
        if not isinstance(qs, list) or not all(_relative_path_ok(q) for q in qs):
            out.append(Finding("E5", "quote_sources 要是 repo 裡的相對路徑清單（可用 *；不准 .. 與絕對路徑）"))
    if "prices_seen" in decl:
        seen = decl["prices_seen"]
        if not isinstance(seen, list) or not all(isinstance(s, str) and s.strip() for s in seen):
            out.append(Finding("E5", "prices_seen 要是代號清單（看過誰的股價；沒看就空清單）"))
        elif seen and not _iso_day(decl.get("price_as_of")):
            out.append(Finding("E5", "看過股價（prices_seen 不空）就要寫 price_as_of（看到哪一天）"))
    if decl.get("price_as_of") is not None and not _iso_day(decl.get("price_as_of")):
        out.append(Finding("E5", "price_as_of 要是日期或 null"))
    if "self_eval" in decl:
        ev = decl["self_eval"]
        want = {str(i) for i in range(1, 13)}
        if not isinstance(ev, Mapping) or set(ev) != want or any(v not in SELF_EVAL_VALUES for v in ev.values()):
            out.append(Finding("E5", "self_eval 要有 \"1\" 到 \"12\" 十二題，各是 " + "／".join(SELF_EVAL_VALUES)))
    if "key_question" in decl:
        kq = decl["key_question"]
        if not (isinstance(kq, int) and not isinstance(kq, bool) and 1 <= kq <= 12):
            out.append(Finding("E5", "key_question 要是 1 到 12（決定賭注的那一題：岔路型 5、訂單型 6）"))
    if "rides" in decl:
        rides = decl["rides"]
        if not isinstance(rides, list) or not all(isinstance(r, str) and r.strip() for r in rides):
            out.append(Finding("E5", "rides 要是圖上節點 id 的清單（故事押的那幾個；可以空）"))
    if "graph_gaps" in decl:
        gaps = decl["graph_gaps"]
        ok = isinstance(gaps, list) and all(
            isinstance(g, Mapping) and set(g) <= {"text", "lead_ids"} and isinstance(g.get("text"), str)
            and g["text"].strip() and isinstance(g.get("lead_ids"), list)
            and all(isinstance(i, str) and i.startswith("lead_") for i in g["lead_ids"]) for g in gaps)
        if not ok:
            out.append(Finding("E5", "graph_gaps 每項要是 {text: 圖上缺什麼, lead_ids: [登記的線索 lead_…]}（還沒登記就空清單）"))
    wait_keys: set[str] = set()
    if "waits" in decl:
        waits = decl["waits"]
        if not isinstance(waits, list):
            out.append(Finding("E5", "waits 要是清單"))
            waits = []
        for i, wait in enumerate(waits):
            if not isinstance(wait, Mapping) or set(wait) != {"key", "kind", "watch_id"}:
                out.append(Finding("E5", f"waits[{i}] 要是 {{key, kind, watch_id}}"))
                continue
            key = wait.get("key")
            if not (isinstance(key, str) and _WAIT_KEY.fullmatch(key)):
                out.append(Finding("E5", f"waits[{i}].key 只用英數、- 與 _"))
                continue
            if key in wait_keys:
                out.append(Finding("E5", f"waits 的 key 重複：{key}"))
            wait_keys.add(key)
            if wait.get("kind") not in WAIT_KINDS:
                out.append(Finding("E5", f"waits[{i}].kind 要是 {'／'.join(WAIT_KINDS)}"))
            watch = wait.get("watch_id")
            if watch is not None and not (isinstance(watch, str) and watch.startswith("ew_")):
                out.append(Finding("E5", f"waits[{i}].watch_id 要是 ew_… 或 null（null＝頁上寫了、系統還沒登記）"))
        if page_wait_keys is not None and set(page_wait_keys) != wait_keys:
            only_page = sorted(set(page_wait_keys) - wait_keys)
            only_decl = sorted(wait_keys - set(page_wait_keys))
            bits = ([f"頁上有、宣告沒有：{'、'.join(only_page)}"] if only_page else []) + (
                [f"宣告有、頁上沒有：{'、'.join(only_decl)}"] if only_decl else [])
            out.append(Finding("E5", "頁上的 data-wait 和宣告的 waits 對不起來——" + "；".join(bits)))
    if "cold_read" not in decl:
        out.append(Finding("E6", "宣告沒有 cold_read——交稿前要跑冷讀，沒跑寫 {\"skipped\": 理由}"))
    else:
        out.extend(cold_read_problems(decl["cold_read"]))
    return out

# ---------------------------------------------------------------- W 類

def _section_nodes(root: Node) -> dict[str, Node]:
    article = _article(root)
    return {k.attr("id") or "": k for k in (article.elements if article else [])}


def _company_name_pattern(company_names: Mapping[str, Sequence[str]]) -> tuple[re.Pattern[str], dict[str, str]] | None:
    forms: dict[str, str] = {}
    for company_id, names in company_names.items():
        for name in names:
            name = str(name or "").strip()
            if len(name) >= 2:
                forms.setdefault(name, company_id)
    if not forms:
        return None
    parts = []
    for name in sorted(forms, key=len, reverse=True):
        escaped = re.escape(name)
        parts.append(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])" if name.isascii() else escaped)
    return re.compile("|".join(parts)), forms


def writing_warnings(root: Node, *, decl: Mapping[str, Any] | None,
                     company_names: Mapping[str, Sequence[str]] | None = None,
                     quote_corpus: str | None = None, quote_note: str | None = None) -> list[Finding]:
    """W1–W9。`quote_corpus`：`normalize_for_match` 過的出處全文（None＝沒核，`quote_note` 說為什麼）。"""
    out: list[Finding] = []
    sections = _section_nodes(root)
    page_text = visible_text(root)
    chars = visible_chars(page_text)
    low, high = VISIBLE_CHARS_RANGE
    if not low <= chars <= high:
        out.append(Finding("W1", f"看得到的字 {chars:,}——以 {low:,} 到 {high:,} 為度"
                           + ("：超過先刪重複、再刪細節" if chars > high else "：太少多半是缺節或寫太簡略")))
    hero = sections.get("hero")
    if hero is not None:
        hits = [m.group(0) for m in HERO_FORWARD_REF.finditer(visible_text(hero))]
        if hits:
            out.append(Finding("W2", "頁首指向後面或別處——頁首只放故事、讀得懂不必往後翻", _sample(hits)))
    counts: dict[str, int] = {}
    for m in _NUMBER_UNIT.finditer(page_text):
        unit = "%" if m.group(2) in ("%", "％") else m.group(2)
        key = m.group(1).replace(",", "") + unit
        counts[key] = counts.get(key, 0) + 1
    repeated = sorted(((k, n) for k, n in counts.items() if n >= REPEAT_LIMIT), key=lambda kv: -kv[1])
    if repeated:
        out.append(Finding("W3", f"同一個數字出現 {REPEAT_LIMIT} 次以上——每個事實只有一個家",
                           _sample([f"{k} ×{n}" for k, n in repeated])))
    if company_names:
        compiled = _company_name_pattern(company_names)
        if compiled is not None:
            pattern, forms = compiled
            hits = []
            for sentence in _SENTENCE_SPLIT.split(page_text):
                if "它" in sentence and len({forms[m.group(0)] for m in pattern.finditer(sentence)}) >= 2:
                    hits.append(sentence)
            if hits:
                out.append(Finding("W4", "一句裡有兩家公司又有「它」——寫名字", _sample(hits)))
    scoped = "\n".join(visible_text(node) for sid, node in sections.items() if sid != "system-gap") \
        if sections else page_text
    words = [f"{label}：{m.group(0)}" for label, pattern in SYSTEM_WORD_PATTERNS for m in pattern.finditer(scoped)]
    if words:
        out.append(Finding("W5", "系統的詞直接上頁——寫它的意思；只有 #system-gap 可以用系統的名稱", _sample(words)))
    quotes = quotes_in(all_text(root))
    if quotes:
        if quote_corpus is None:
            out.append(Finding("W6", f"沒核引號（{quote_note or '宣告的 quote_sources 是空的'}）：頁上有 {len(quotes)} 段長引號",
                               _sample(quotes, 3)))
        else:
            missing = [q for q in quotes if not quote_found(q, quote_corpus)]
            if missing:
                out.append(Finding("W6", "引號裡的字在 quote_sources 的檔裡找不到——回原文核，或拿掉引號", _sample(missing)))
    bare = [sid for sid in QUESTION_IDS if sid in sections
            and not any(n.tag != TEXT and n.has_attr("data-src") for n in sections[sid].iter())]
    if bare:
        out.append(Finding("W7", "這幾節沒有任何來源等級標記（data-src）：" + "、".join(bare)))
    if isinstance(decl, Mapping):
        kq, ev = decl.get("key_question"), decl.get("self_eval")
        if isinstance(kq, int) and isinstance(ev, Mapping) and ev.get(str(kq)) not in (None, "full"):
            out.append(Finding("W8", f"決定賭注的第 {kq} 題自評是「{ev.get(str(kq))}」——先補查再交，不只是揭露"))
    hand = [m.group(0) for m in _HAND_REGISTERED.finditer(page_text)]
    if hand:
        out.append(Finding("W9", "頁上手寫了登記狀態——等待有沒有登記由 APP 照 registry 印（用 data-wait 標出那一條）",
                           _sample(hand)))
    return out

# ---------------------------------------------------------------- 入口

def page_wait_keys(root: Node) -> frozenset[str]:
    return frozenset(n.attr("data-wait") or "" for n in root.iter() if n.tag != TEXT and n.has_attr("data-wait"))


def check_page(html: str, decl: Any, *, company_names: Mapping[str, Sequence[str]] | None = None,
               quote_corpus: str | None = None, quote_note: str | None = None) -> PageCheck:
    """片段＋宣告的全部純檢查（E1–E6 的形狀部分、W1–W9）。跨帳的核對（現行敘事、registry、圖）在 provider。"""
    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        return PageCheck([Finding("E2", f"片段超過 {MAX_HTML_BYTES:,} bytes")], 0, "")
    root, problems = parse_fragment(html)
    keys = page_wait_keys(root)
    findings = [*problems, *whitelist_problems(root), *structure_problems(root), *system_slot_problems(root),
                *private_string_problems(html, root), *declaration_problems(decl, page_wait_keys=keys)]
    findings += writing_warnings(root, decl=decl if isinstance(decl, Mapping) else None, company_names=company_names,
                                 quote_corpus=quote_corpus, quote_note=quote_note)
    text = visible_text(root)
    return PageCheck(findings, visible_chars(text), text, keys)


def whitelist_payload() -> dict[str, Any]:
    """APP 前端重建節點用的白名單（`.meta.json`；只有這一份，app.js 不另抄——L16）。屬性名一律小寫比對。"""
    return {"html_tags": sorted(HTML_TAGS), "svg_tags": sorted(SVG_TAGS), "void_tags": sorted(VOID_TAGS),
            "global_attrs": sorted(GLOBAL_ATTRS), "tag_attrs": {k: sorted(v) for k, v in TAG_ATTRS.items()},
            "svg_attrs": sorted(SVG_ATTRS), "svg_namespace": SVG_NAMESPACE, "source_levels": list(SOURCE_LEVELS),
            "wait_kinds": list(WAIT_KINDS)}


__all__ = [
    "DECLARATION_KEYS", "Finding", "GLOBAL_ATTRS", "HTML_TAGS", "Node", "PageCheck", "QUESTION_IDS", "SECTION_IDS",
    "SELF_EVAL_VALUES", "SOURCE_LEVELS", "SVG_ATTRS", "SVG_TAGS", "TAG_ATTRS", "VISIBLE_CHARS_RANGE", "WAIT_KINDS",
    "all_text", "check_page", "cold_read_problems", "declaration_problems", "fragment_problems", "normalize_for_match",
    "page_wait_keys", "parse_fragment", "private_string_problems", "quote_found", "quotes_in", "structure_problems",
    "system_slot_problems", "visible_chars", "visible_text", "whitelist_payload", "whitelist_problems",
    "writing_warnings",
]
