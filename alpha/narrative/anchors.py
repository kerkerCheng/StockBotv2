"""敘事事實句綁逐字錨點（2026-11-13 使用者「照你推薦做吧」；plan `docs/plans/2026-11-13-001-dev-fact-anchor-plan.md` Step A；
failure log #163）——**純規則，不讀不寫任何檔**：錨點紀錄的讀寫、引用解析由呼叫端注入（`alpha.providers.fact_anchors`）。

## 為什麼

逐句核對（`fact_check`）在那一格的整份引用裡**猜**哪一行對得上，猜錯就核錯：11-13 回頭核 27 份現行敘事，工具重放只標到改掉的
135 句裡的 56%，沒改的 1,888 句也標 27%（命中率約 13%）。寫的人在寫的當下知道自己靠的是哪一段原文——把那一段記下來，比對就
不必猜（L18：根解是拿掉資訊落差）。

## 它做什麼

1. **句子指紋**（`fingerprint`）：公司＋句子正規化之後的字，**不含引用**——同一句話換版不變、錨點跟著走；句子改了就對不到，
   要重看原文（這正是要的）。
2. **拿一句比它自己的錨點**（`compare`）：數字、引號、名稱、限定詞——`fact_check` 同一批函式，只是原文換成錨點那幾段；
   加三種只有錨點才比得準的：
   - 保留語氣被拿掉：原文有 expected／may／committed to／預計……，句子寫成已發生（AXTI「committed to pay」寫成「付了」）；
   - 衍生數字：錨點宣告的算法（`DERIVE_OPS`）從原文的數算出來，與句子寫的對不上；句子有原文沒有的分數（AXTI「三分之二」——
     原文第二季約 79%、第三季約 87%）照數字旗標；
   - 同語言的詞不在原文：原文是中文時，句子裡連續三個字以上、原文裡沒有的詞（3110.T 半年報寫「特种电子布」，敘事收窄成
     「低熱膨脹布」）。原文不是中文時不比——翻譯過來的句子沒有字可比。

## 它不做什麼

不擋寫入、不改候選狀態、不寫 watch（使用者 11-13 ③：先只印、量過再談——plan Step C 重放量命中率）。判定一句對不對的是讀的人：
旗標是要先看的句子，沒有旗標不等於對（L18）。
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from .fact_check import (_CJK, _EN_NUMBER_WORDS, CheckContext, CheckResult, Flag, Sentence, SentenceClaims, SourceLine,
                         _latin_in, _line_feat, fold, fraction_claims, number_claims, number_found, qualifier_problems, quote_problems,
                         registry_name_problems, sentence_claims, source_facts, squash, strip_placeholders, where_label)

#: 錨點比對的旗標（封閉字彙；輸出、紀錄、測試都從這裡列舉——L16）。前四種與逐句核對同名同義，原文換成錨點那幾段。
ANCHOR_FLAG_KINDS: Mapping[str, str] = {
    "quote_missing": "引號裡的字不在錨點原文",
    "number_missing": "數字對不回錨點原文",
    "name_missing": "名稱不在錨點原文",
    "qualifier_missing": "限定詞在錨點原文找不到對應字",
    "term_missing": "句子裡的詞不在同語言的錨點原文（主詞收窄或放寬？）",
    "hedge_dropped": "錨點原文有保留語氣，句子寫成已發生",
    "derived_mismatch": "衍生數字與錨點的數算出來的不符",
}
#: 錨點只收一手原文：`library/raw` 節錄、圖的來源文件（逐字引文與同名節錄）。讀圖判讀、自家筆記、Engine C、外部網址不收。
ANCHOR_REF_KINDS: tuple[str, ...] = ("raw", "graph_source")
#: 衍生數字的算法（封閉字彙）；`of` 照順序、寫原文的寫法（單位要一致）。
DERIVE_OPS: Mapping[str, str] = {
    "ratio": "a ÷ b（倍）",
    "share": "a ÷ b × 100（%）",
    "growth": "(a − b) ÷ b × 100（%）",
    "diff": "a − b",
    "sum": "全部相加",
}
_DERIVE_ARITY: Mapping[str, int] = {"ratio": 2, "share": 2, "growth": 2, "diff": 2}


def fingerprint(company_id: str, text: str) -> str:
    """句子指紋：公司＋`squash` 過的句子（全半形、大小寫、繁簡、空白都正規化掉），**不含引用**——現行核對的 digest 含引用，
    一格多一條引用那一格每一句都要重綁，錨點就一直掉。"""
    payload = f"{company_id}|{squash(text)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    ref: str
    quote: str
    derive: Mapping[str, Any] | None = None


# ---------------------------------------------------------------------------
# 保留語氣
# ---------------------------------------------------------------------------

#: 原文的保留或未來語氣（`fold` 之後：簡體、小寫）。英文以詞界比；`may` 另比（後面接數字是月份）。「plan」「target」只收動詞
#: 用法（名詞的 business plan、target market 不是語氣）；中文的「将」只收未來用法（「将其」「将近」不是）。
_EN_SOURCE_HEDGES: tuple[str, ...] = (
    "expect", "expects", "expected", "expecting", "anticipate", "anticipates", "anticipated", "plans to", "plan to",
    "planned", "planning to", "targets", "targeted", "targeting", "aim to", "aims to", "intend", "intends", "intended",
    "guidance", "outlook", "forecast", "forecasts", "estimate", "estimates", "estimated", "might", "could", "would", "will",
    "should", "potential", "potentially", "committed to", "commit to", "commits to", "subject to", "pending", "projected",
    "on track to", "likely", "believe", "believes", "seek to", "seeks to")
_EN_MAY = re.compile(r"(?<![a-z])may(?![a-z])(?!\s*\d)")
_CJK_SOURCE_HEDGES: tuple[str, ...] = (
    "预计", "预期", "预估", "预测", "估计", "可望", "有望", "计划", "规划", "目标", "将于", "将在", "将会", "将可", "即将", "拟",
    "争取", "预定", "可能", "或将", "承诺", "展望", "指引", "希望",
    "予定", "见込", "见通", "计画", "予想", "方针",
    "예정", "계획", "목표", "전망", "예상")
#: 句子裡算「有保留語氣」的寫法（`squash` 之後）——比原文那一側寬：中文的未來、條件、尚未發生的說法很多。單字「会」「要」不收
#: （董事会、主要）。
SENTENCE_HEDGES: tuple[str, ...] = (
    "预计", "预期", "预估", "预测", "估计", "可望", "有望", "计划", "规划", "目标", "将于", "将在", "将会", "将可", "将是", "将有",
    "即将", "会在", "会再", "会是", "可能", "或许", "也许", "拟", "打算", "争取", "预定", "承诺", "答应", "同意", "展望", "指引",
    "希望", "尚未", "还没", "未来", "之后", "以后", "明年", "下一季", "下季", "若", "如果", "只要", "条件")
_EN_SENTENCE_HEDGES: tuple[str, ...] = ("expect", "plan", "target", "guid", "may", "might", "could", "would", "will", "aim",
                                        "intend", "forecast", "outlook", "commit")
#: 含語氣字、卻不是語氣的詞——比之前拿掉
_NOT_HEDGE = ("将近", "模拟", "虚拟")


def _scrub(squashed: str) -> str:
    for word in _NOT_HEDGE:
        squashed = squashed.replace(word, "")
    return squashed


def source_hedges(text: str) -> list[str]:
    """原文裡的保留語氣字（照出現的種類列，最多三個）。"""
    folded = fold(text)
    spaced = " ".join(folded.split())
    sq = _scrub(re.sub(r"\s+", "", folded))
    found = [w for w in _EN_SOURCE_HEDGES if _latin_in(w, spaced)]
    if _EN_MAY.search(spaced):
        found.append("may")
    found += [w for w in _CJK_SOURCE_HEDGES if w in sq]
    return found[:3]


def sentence_hedged(text: str) -> bool:
    folded = fold(strip_placeholders(text))
    spaced = " ".join(folded.split())
    sq = _scrub(re.sub(r"\s+", "", folded))
    return any(w in sq for w in SENTENCE_HEDGES) or any(re.search(r"(?<![a-z])" + w, spaced) for w in _EN_SENTENCE_HEDGES)


# ---------------------------------------------------------------------------
# 分數與衍生數字
# ---------------------------------------------------------------------------

_EN_FRACTIONS: tuple[tuple[str, float], ...] = (
    ("two-thirds", 200 / 3), ("two thirds", 200 / 3), ("one-third", 100 / 3), ("one third", 100 / 3), ("a third", 100 / 3),
    ("three-quarters", 75.0), ("three quarters", 75.0), ("one-quarter", 25.0), ("one quarter of", 25.0),
    ("a quarter of", 25.0), ("one-half", 50.0), ("half of", 50.0))


def source_fraction_pcts(text: str) -> list[float]:
    """原文裡的分數（中文「三分之二」與英文 two-thirds）→ 百分比。"""
    spaced = " ".join(fold(text).split())
    out = [v for _raw, v in fraction_claims(text)]
    out += [v for word, v in _EN_FRACTIONS if _latin_in(word, spaced)]
    return out


def _fraction_tol(value: float) -> float:
    return max(2.0, value * 0.05)


def value_of(text: str) -> tuple[float, float] | None:
    """一個數的寫法 → (值, 容許差)。分數照百分比；其餘走 `number_claims`（「約」放寬到一成）。讀不出回 None。"""
    fractions = fraction_claims(text)
    if fractions:
        return fractions[0][1], _fraction_tol(fractions[0][1])
    claims = number_claims(text)
    return (claims[0].value, claims[0].tol) if claims else None


def derive_value(op: str, values: Sequence[float]) -> float | None:
    try:
        if op == "ratio":
            return values[0] / values[1]
        if op == "share":
            return values[0] / values[1] * 100
        if op == "growth":
            return (values[0] - values[1]) / values[1] * 100
        if op == "diff":
            return values[0] - values[1]
        if op == "sum":
            return float(sum(values))
    except (IndexError, ZeroDivisionError):
        return None
    return None


def derive_problems(derive: Any, *, quote: str, sentences: Sequence[str]) -> list[str]:
    """寫入前驗 `derive`：算法在封閉字彙、`of` 的每個數照原字出現在錨點原文、`shown` 照原字出現在句子裡、都讀得出數字。"""
    if not isinstance(derive, Mapping):
        return ["derive 要是 {op, of, shown}"]
    op, of, shown = derive.get("op"), derive.get("of"), derive.get("shown")
    out = []
    if op not in DERIVE_OPS:
        out.append(f"derive.op 只收 {'／'.join(DERIVE_OPS)}")
    if not isinstance(of, list) or not of or not all(isinstance(v, str) and v.strip() for v in of):
        out.append("derive.of 要是原文寫法的 list（例如 [\"79%\", \"87%\"]）")
    else:
        need = _DERIVE_ARITY.get(str(op))
        if (need and len(of) != need) or (op == "sum" and len(of) < 2):
            out.append(f"derive.of 的個數不對（{op} 要 {need or '至少 2'} 個）")
        for v in of:
            if value_of(v) is None:
                out.append(f"derive.of「{v}」讀不出數字")
            elif squash(v) not in squash(quote):
                out.append(f"derive.of「{v}」不在 quote 裡（照原文的寫法抄）")
    if not isinstance(shown, str) or not shown.strip():
        out.append("derive.shown 要寫句子裡的那個數（原字）")
    else:
        if value_of(shown) is None:
            out.append(f"derive.shown「{shown}」讀不出數字")
        if not any(squash(shown) in squash(s) for s in sentences):
            out.append(f"derive.shown「{shown}」不在句子裡")
    return out


def _derived(anchors: Sequence[Anchor]) -> tuple[list[str], list[Flag]]:
    """(宣告為衍生的那幾個數的寫法, 算不回來的旗標)。"""
    shown_all: list[str] = []
    bad: list[Flag] = []
    for a in anchors:
        d = a.derive
        if not d:
            continue
        shown = str(d.get("shown") or "")
        shown_all.append(shown)
        values = [value_of(str(v)) for v in d.get("of") or ()]
        target = value_of(shown)
        op = str(d.get("op"))
        computed = derive_value(op, [v[0] for v in values]) if values and all(values) else None
        if computed is None or target is None:
            bad.append(Flag("derived_mismatch", f"「{shown}」算不出來（{op}：{'、'.join(map(str, d.get('of') or ()))}）"))
            continue
        value, tol = target
        if abs(computed - value) > max(tol, abs(computed) * 0.01) + 1e-9:
            bad.append(Flag("derived_mismatch", f"寫「{shown}」；{DERIVE_OPS.get(op, op)} 算出來是 {computed:,.4g}"))
    return shown_all, bad


# ---------------------------------------------------------------------------
# 同語言的詞
# ---------------------------------------------------------------------------

#: 句子裡比原文不必有的字：我們自己的框架與出處說法、單字虛詞（`squash` 之後的簡體）。蓋掉它們，剩下的才是「原文裡沒有的詞」。
_FRAMING: tuple[str, ...] = (
    "也就是说", "换句话说", "这代表", "意味着", "也就是", "代表", "所以", "因此", "因为", "但是", "不过", "而且", "并且", "同时",
    "另外", "此外", "例如", "比如", "包括", "以及", "其中", "目前", "已经", "这一", "那一", "这家", "该公司", "公司", "它们", "他们",
    "我们", "表示", "指出", "提到", "写道", "写着", "根据", "依据", "显示", "看来", "这是", "就是", "还是", "只是", "半年报",
    "年报", "季报", "财报", "法说会", "法说", "新闻稿", "公告", "简报", "说明会", "原文", "节录",
    "说", "写", "的", "了", "在", "是", "有", "和", "与", "及", "或", "也", "都", "就", "还", "又", "再", "被", "把", "对", "向",
    "从", "到", "给", "让", "使", "由", "为", "因", "而", "但", "则", "即", "且", "并", "之", "其", "此", "该", "这", "那", "它",
    "个", "家", "种", "年", "月", "日", "季", "约", "近", "逾", "超过", "左右", "多", "已", "将", "会", "能", "可", "要", "不",
    "没", "未", "很", "更", "最", "较", "比", "等", "中", "上", "下", "内", "外", "前", "后", "间")
TERM_MIN_CHARS = 3
_KANA_HANGUL = re.compile(r"[぀-ヿ가-힯]")


def _folded_index(text: str) -> tuple[str, list[int]]:
    """`squash` 的結果與每個字在原句的位置（印回原字用）。"""
    chars: list[str] = []
    index: list[int] = []
    for i, ch in enumerate(text):
        for f in fold(ch):
            if not f.isspace():
                chars.append(f)
                index.append(i)
    return "".join(chars), index


def term_problems(sentence: str, quotes: Sequence[str], *, skip: Iterable[str] = ()) -> list[str]:
    """原文是中文時：句子裡連續 `TERM_MIN_CHARS` 個字以上、原文的兩字詞一個都蓋不到的詞（原字）。`skip`：這一檔自己的名字。"""
    joined = "".join(quotes)
    if not _CJK.search(joined) or _KANA_HANGUL.search(joined):
        return []
    q = squash(joined)
    pairs = {q[i:i + 2] for i in range(len(q) - 1)}
    text = strip_placeholders(sentence)
    s, index = _folded_index(text)
    covered = [not _CJK.match(ch) for ch in s]
    for i in range(len(s) - 1):
        if s[i:i + 2] in pairs:
            covered[i] = covered[i + 1] = True
    for word in (*_FRAMING, *(squash(w) for w in skip if w and _CJK.search(str(w)))):
        start = s.find(word)
        while word and start >= 0:
            for k in range(start, start + len(word)):
                covered[k] = True
            start = s.find(word, start + 1)
    out: list[str] = []
    run: list[int] = []
    for k, ok in enumerate([*covered, True]):
        if not ok:
            run.append(k)
            continue
        if len(run) >= TERM_MIN_CHARS:
            piece = text[index[run[0]]:index[run[-1]] + 1]
            if piece not in out:
                out.append(piece)
        run = []
    return out


# ---------------------------------------------------------------------------
# 一句比它自己的錨點
# ---------------------------------------------------------------------------

_EN_ARTICLE = re.compile(r"(?<![a-z])an?(?![a-z.])")
_EN_PLURAL_COUNTS = tuple(w for n, words in _EN_NUMBER_WORDS.items() if n > 1 for w in words)


def singular_in(quotes: Sequence[str]) -> bool:
    """英文原文的單數不寫 one：「另有一家…客戶」綁 "a market-leading … customer"（2026-11-13 COHR 第一個真錨點）。
    錨點原文全是英文、有冠詞 a／an、而且沒寫別的數（two、both、three…）時，句子的數量 1 算對得上；
    原文寫了別的數就照標——數錯（300757.SZ「一家」）不放過。"""
    text = fold(" ".join(quotes))
    if not text or _CJK.search(text):
        return False
    if any(re.search(rf"(?<![a-z]){w}(?![a-z])", text) for w in _EN_PLURAL_COUNTS):
        return False
    return bool(_EN_ARTICLE.search(text))


def compare(sentence: Sentence, anchors: Sequence[Anchor], *, self_company: str, self_names: Sequence[str] = (),
            names: Sequence[tuple[str, Sequence[tuple[str, str, bool]]]] = (), as_of: date | None = None,
            claims: SentenceClaims | None = None) -> tuple[Flag, ...]:
    """一句比它綁的錨點原文（沒有錨點＝沒有旗標，「還沒錨點」另算）。`names`：`CheckContext.folded_names()`。"""
    if not anchors:
        return ()
    claims = claims or sentence_claims(sentence, self_names=self_names, as_of=as_of)
    lines = [SourceLine(a.ref, a.quote) for a in anchors]
    facts = source_facts(lines)
    quotes = [a.quote for a in anchors]
    flags: list[Flag] = []
    missing_q = quote_problems(sentence.text, facts)
    if missing_q:
        flags.append(Flag("quote_missing", "、".join(f"「{q}」" for q in missing_q)))
    shown, derived_bad = _derived(anchors)
    shown_sq = [squash(s) for s in shown if s]

    def declared(raw: str) -> bool:
        r = squash(raw)
        return any(r in s or s in r for s in shown_sq)

    singular = singular_in(quotes)
    missing_n = [c.raw.strip() for c in claims.numbers if not number_found(c, facts, facts) and not declared(c.raw)
                 and not (singular and c.kind == "count" and c.value == 1)]
    pcts = facts.pcts + source_fraction_pcts(" ".join(quotes))
    for raw, value in claims.fractions:
        if declared(raw) or squash(raw) in facts.squashed:
            continue
        if not any(abs(value - p) <= _fraction_tol(value) for p in pcts):
            missing_n.append(raw)
    if missing_n:
        flags.append(Flag("number_missing", "、".join(missing_n)))
    labels = " ".join(fold(a.ref) for a in anchors)
    missing_names = [n for n in claims.names if not (_latin_in(n, facts.spaced) or _latin_in(n, labels))]
    if not claims.schedule_like:
        missing_names += registry_name_problems(sentence.text, facts, names=names, self_company=self_company, labels=labels)
    if missing_names:
        flags.append(Flag("name_missing", "、".join(missing_names)))
    if not claims.schedule_like:
        missing_qual = qualifier_problems(sentence.text, [_line_feat(line) for line in lines])
        if missing_qual:
            flags.append(Flag("qualifier_missing", "、".join(f"「{q}」" for q in missing_qual)))
        terms = term_problems(sentence.text, quotes, skip=self_names)
        if terms:
            flags.append(Flag("term_missing", "、".join(f"「{t}」" for t in terms)))
        hedges = source_hedges(" ".join(quotes))
        if hedges and not sentence_hedged(sentence.text):
            flags.append(Flag("hedge_dropped", "原文有「" + "」「".join(hedges) + "」，句子沒有保留語氣"))
    flags += derived_bad
    return tuple(flags)


@dataclass(frozen=True)
class AnchorCheck:
    sentence: Sentence
    fingerprint: str
    fact: bool                         # 事實句（要綁錨點；`SentenceClaims.is_fact`）
    anchors: tuple[Anchor, ...]        # 對到這一句指紋的錨點（空＝還沒綁）
    flags: tuple[Flag, ...]


def check_anchors(result: CheckResult, index: Mapping[str, Sequence[Anchor]], *, ctx: CheckContext,
                  self_names: Sequence[str] = ()) -> list[AnchorCheck]:
    """一版敘事（＋故事）每一句：事實句嗎、綁了哪些錨點、比出什麼。`index`：指紋 → 錨點（`fact_anchors.anchor_index`）。"""
    brief = result.brief
    out = []
    for c in result.checks:
        s = c.sentence
        fp = fingerprint(brief.company_id, s.text)
        claims = sentence_claims(s, self_names=self_names, as_of=brief.as_of)
        found = tuple(index.get(fp) or ())
        flags = compare(s, found, self_company=brief.company_id, self_names=self_names, names=ctx.folded_names(),
                        as_of=brief.as_of, claims=claims) if found else ()
        out.append(AnchorCheck(s, fp, claims.is_fact, found, flags))
    return out


# ---------------------------------------------------------------------------
# 呈現
# ---------------------------------------------------------------------------

def _short(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def anchor_summary(checks: Sequence[AnchorCheck]) -> str:
    facts = [c for c in checks if c.fact]
    anchored = [c for c in facts if c.anchors]
    extra = [c for c in checks if c.anchors and not c.fact]
    return (f"錨點：事實句 {len(facts)}｜有錨點 {len(anchored)}｜還沒錨點 {len(facts) - len(anchored)}"
            f"｜錨點旗標 {sum(1 for c in checks if c.flags)}" + (f"｜非事實句也綁了 {len(extra)}" if extra else ""))


def render_markdown(checks: Sequence[AnchorCheck], *, ticker: str) -> list[str]:
    """`brief-check` 的「錨點比對」一段：只列綁了錨點的句子（猜行那一段照舊在上面），還沒錨點的事實句列編號。"""
    lines = ["", "## 錨點比對（句子對它自己綁的那段原文；只印、不擋）", anchor_summary(checks)]
    for c in checks:
        if not c.anchors:
            continue
        lines.append(f"{c.sentence.n}.（{where_label(c.sentence.where)}）{c.sentence.text}")
        for a in c.anchors:
            lines.append(f"   ⚓ {a.anchor_id}｜{a.ref}｜「{_short(a.quote, 160)}」"
                         + (f"｜衍生 {a.derive.get('op')}：{'、'.join(map(str, a.derive.get('of') or ()))} → "
                            f"{a.derive.get('shown')}" if a.derive else ""))
        for f in c.flags:
            lines.append(f"   ⚑{ANCHOR_FLAG_KINDS[f.kind]}：{f.detail}")
    missing = [c for c in checks if c.fact and not c.anchors]
    if missing:
        lines.append("還沒錨點的事實句：" + "、".join(str(c.sentence.n) for c in missing)
                     + f"（`python -m alpha brief-anchor {ticker} --draft` 列出來，附候選原文行）")
    return lines


def as_dict(checks: Sequence[AnchorCheck]) -> dict[str, Any]:
    return {"summary": anchor_summary(checks),
            "fact_sentences": sum(1 for c in checks if c.fact),
            "anchored": sum(1 for c in checks if c.fact and c.anchors),
            "checks": [{"n": c.sentence.n, "where": c.sentence.where, "fingerprint": c.fingerprint, "fact": c.fact,
                        "anchors": [{"anchor_id": a.anchor_id, "ref": a.ref, "quote": a.quote, "derive": a.derive}
                                    for a in c.anchors],
                        "flags": [{"kind": f.kind, "detail": f.detail} for f in c.flags]}
                       for c in checks if c.fact or c.anchors]}


__all__ = ["ANCHOR_FLAG_KINDS", "ANCHOR_REF_KINDS", "Anchor", "AnchorCheck", "DERIVE_OPS", "SENTENCE_HEDGES",
           "TERM_MIN_CHARS", "anchor_summary", "as_dict", "check_anchors", "compare", "derive_problems", "derive_value",
           "fingerprint", "render_markdown", "sentence_hedged", "source_fraction_pcts",
           "source_hedges", "term_problems", "value_of"]
