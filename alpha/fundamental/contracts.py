"""Causal Fundamental Model 的型別契約。**只有型別與驗證，零外部相依。**

## 四個一等公民

| 型別 | 誰擁有它 | 可變性 |
|---|---|---|
| `FiscalPeriod` | 共同語言 | 身分是 `end` 日期，`FY2027` 只是呈現慣例 |
| `OperatingAssumption` | A3 研究判斷（private append-only ledger） | 可重算；改假設＝append 新紀錄 |
| `FiscalYearActuals`／`ConsensusEstimate`／`GuidanceObservation` | A2 Engine C 觀測 | 由 provider 唯讀取出 |
| `ModeledMetric`／`ExpectationComparison` | A3 模型輸出 | 由 `bridge.py`／`compare.py` 確定性算出 |

## 三條在型別層強制的規則

1. **假設必須帶 basis、rationale、evidence、created_at。** 沒有 provenance 的假設不得存在
   （INV-6）；retracted 紀錄例外，它只是一個「撤回」標記。
2. **driver 是封閉字彙（contract）。** 每個 driver 對應 `bridge.py` 的一段算術；多一個 driver
   就要多一段算術，所以打開它是改程式不是改設定。
3. **模型輸出分兩層標：`calculation="deterministic"` 與 `input_dependency`（最弱輸入的
   知識種類）。** 前者說「算法確定」，後者說「輸入是判斷」，兩者不得壓成一個欄位（L12）。
"""
from __future__ import annotations

import calendar
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef
from ..errors import ContractViolation

MODEL_VERSION = "causal-fundamental-model/v1"
BRIDGE_VERSION = "fundamental-bridge/v1"

# ---------------------------------------------------------------------------
# 0. 會計期間（身分是日期）
# ---------------------------------------------------------------------------

FISCAL_PERIOD_KINDS: tuple[str, ...] = ("fiscal_year",)

#: 兩個會計期間視為「同一期」的容忍天數。52／53 週制的年度結束日會在同一週內浮動
#: （NVDA 1 月最後一個週日：2026-01-25 vs 2027-01-31），嚴格相等會把同一年判成不同年。
PERIOD_MATCH_TOLERANCE_DAYS = 10


def _add_years(value: date, years: int) -> date:
    year = value.year + years
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return date(year, value.month, day)


@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    """一個會計期間。**`end` 是身分**；`label` 只是結束年命名的呈現慣例。"""

    end: date
    kind: str = "fiscal_year"

    def __post_init__(self) -> None:
        if self.kind not in FISCAL_PERIOD_KINDS:
            raise ContractViolation(
                f"FiscalPeriod.kind 未登記：{self.kind!r}；已知 {FISCAL_PERIOD_KINDS}")
        if not isinstance(self.end, date) or isinstance(self.end, datetime):
            raise ContractViolation("FiscalPeriod.end 必須是 date")

    @property
    def label(self) -> str:
        return f"FY{self.end.year}"

    @property
    def start(self) -> date:
        return _add_years(self.end, -1) + timedelta(days=1)

    def same_as(self, other: "FiscalPeriod", *,
                tolerance_days: int = PERIOD_MATCH_TOLERANCE_DAYS) -> bool:
        return (self.kind == other.kind
                and abs((self.end - other.end).days) <= tolerance_days)

    def shifted(self, years: int) -> "FiscalPeriod":
        return FiscalPeriod(end=_add_years(self.end, years), kind=self.kind)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "label": self.label,
                "start": self.start.isoformat(), "end": self.end.isoformat()}


# ---------------------------------------------------------------------------
# 1. 封閉字彙
# ---------------------------------------------------------------------------

#: 會計口徑。`not_applicable`＝這個量沒有口徑之分（營收）；`unverified`＝provider 沒宣告、
#: 也沒能用一手數字核對出來——**不得**與任何口徑相減。
ACCOUNTING_BASES: tuple[str, ...] = ("gaap", "non_gaap", "not_applicable", "unverified")

#: **共識口徑的核實結果**——與 `ACCOUNTING_BASES` 刻意分開的第二個封閉字彙（2026-09-11）。
#:
#: `ACCOUNTING_BASES` 是三本 private append-only ledger 每筆紀錄**身分**的一部分（L10），
#: 動它等於動既有紀錄；而這一組是**每次跑都重算**的判定結果，可以有自己的字彙。
#:
#: 拆它的理由是 L12（一個表示兩種語意）：`unverified` 原本同時承載
#: ①「provider 的數字對不上任何一個候選」＝真的會計口徑不同，與
#: ②「對得上，但換算匯率不同」＝同一個口徑、不同 FX 慣例。
#: 兩者的處置完全相反——①要補 `non_gaap` 區塊，②要的是承認換算差或用同一條 FX 路徑重算。
#: 壓在一格時下游只能取兩者的下限：全部拒絕比較，於是非美股那一批的
#: **兩欄拆解（EPS 桿／倍數桿）永遠缺席**，而那兩欄正是回答「全負是方法偏空還是市場太貴」
#: 的唯一證據。
#:
#: ⚠ `*_fx_tolerated` **不是** `gaap`／`non_gaap` 的同義詞，呈現層不得把它壓回去講：
#: 它明說「口徑認出來了，但這個數字帶著一個已知的換算誤差」。
CONSENSUS_BASES: tuple[str, ...] = (
    "gaap", "non_gaap",
    "gaap_fx_tolerated", "non_gaap_fx_tolerated",
    "unverified", "not_applicable",
)


def consensus_basis_stem(value: str) -> str:
    """`gaap_fx_tolerated` → `gaap`。未知值原樣回傳，由呼叫端的封閉性檢查去擋。"""
    return value[: -len("_fx_tolerated")] if value.endswith("_fx_tolerated") else value

#: 假設的知識種類。**與 read model 的 `Basis` 字彙同名同義**（`tests` 斷言它是子集）：
#: `observation`＝值直接取自同期觀測；`heuristic_proxy`＝機械規則（如「沿用上一年」）；
#: `session_judgment`＝session／LLM 的判斷。刻意沒有 `deterministic`——輸入假設不會是
#: 確定性事實，確定性的是橋的算術。
ASSUMPTION_BASES: tuple[str, ...] = ("observation", "heuristic_proxy", "session_judgment")

#: 由弱到強的次序，用來算 `input_dependency`（最弱輸入）。
_BASIS_STRENGTH: Mapping[str, int] = {"session_judgment": 0, "heuristic_proxy": 1, "observation": 2}


def weakest_basis(bases: Sequence[str]) -> str | None:
    known = [b for b in bases if b in _BASIS_STRENGTH]
    if not known:
        return None
    return min(known, key=lambda b: _BASIS_STRENGTH[b])


@dataclass(frozen=True, slots=True)
class DriverSpec:
    unit: str
    scope_kind: str            # segment_or_total／component／total
    description: str
    lower: float | None = None
    upper: float | None = None


TOTAL_SCOPE = "total"

#: **contract，不是 taxonomy**：每個 driver 對應 `bridge.py` 的一段算術。
ASSUMPTION_DRIVERS: Mapping[str, DriverSpec] = {
    "revenue_growth": DriverSpec(
        "ratio", "segment_or_total",
        "基期營收成長率；scope 是分部名稱或 total（兩者不得並存）", lower=-1.0, upper=5.0),
    "operating_margin_delta": DriverSpec(
        "ratio", "component",
        "相對基期營益率的變化量（小數，+0.025 ＝ +2.5 個百分點）；scope 是成分標籤（mix／utilization／pricing…），可多條相加",
        lower=-1.0, upper=1.0),
    "interest_and_other_net": DriverSpec(
        "currency", "total", "利息與其他（收益）費用淨額，絕對金額（正值＝費用）"),
    "tax_rate": DriverSpec("ratio", "total", "有效稅率（小數）", lower=-1.0, upper=1.0),
    "nci_attribution": DriverSpec(
        "currency", "total", "歸屬母公司前的非控制權益調整，絕對金額（正值＝加回母公司）"),
    "diluted_shares": DriverSpec("shares", "total", "稀釋加權平均股數（絕對股數）", lower=0.0),
}

#: 比較不成立的每一種原因各有自己的名字，**不合併成一個 unavailable**。
#: `unreconciled_base`（2026-09-07 Coverage Pilot 補）＝ provider 的 `year_ago_actual` 與我們的
#: 基期實際值對不上，也就是這串共識量的不是我們基期量的那個東西——它既不是缺料也不是口徑不同。
COMPARISON_STATUSES: tuple[str, ...] = (
    "comparable", "internal_missing", "consensus_missing",
    "incompatible_period", "incompatible_basis", "incompatible_unit", "unreconciled_base",
)


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractViolation(f"{label} 必須是數值：{value!r}")
    if not math.isfinite(float(value)):
        raise ContractViolation(f"{label} 必須是有限數：{value!r}")
    return float(value)


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractViolation(f"{label} 必須是非空字串")
    return value


# ---------------------------------------------------------------------------
# 2. OperatingAssumption
# ---------------------------------------------------------------------------

#: 假設 provenance 的語意版本。`v2`＝每條 ref 都宣告角色；`legacy`＝v1 紀錄，未宣告角色
#: （讀取時 fail safe：未分類 ref 當 supporting，同期共識 ref 依前綴機械歸為 calibration）。
PROVENANCE_SEMANTICS: tuple[str, ...] = ("v2", "legacy")

#: 假設 evidence ref 的角色（與 `alpha.refresh.contracts.DEPENDENCY_ROLES` 的假設子集同名同義）。
#: `supporting`＝支持這個假設為真；`calibration`＝校準數字的脈絡（例：市場隱含 +67% → 內部選 +60%）；
#: `comparison`＝拿來比較的對象。**同期分析師共識不得是 supporting**——那是 provenance 循環：
#: 共識支持假設 → 假設推出內部預測 → 內部預測拿去跟共識比。
ASSUMPTION_REF_ROLES: tuple[str, ...] = ("supporting", "calibration", "comparison", "legacy_unclassified")

#: 由 ref 前綴機械判定「這是同期共識」——它是可重導的字串規則，不是判斷。
CONSENSUS_REF_PREFIX = "engine_c://consensus_estimate/"

#: 這條假設的**值是怎麼決定的**——與 `dependency_roles`（每條證據扮演什麼角色）正交。
#:
#: ⚠ 為什麼 `dependency_roles` 擋不住這件事（2026-09-10 實測 14 本 ledger）：每一條
#: 「由共識 EPS 逆推」的假設都**完整滿足** v2 的 provenance gate——基期觀測標
#: `supporting`、同期共識標 `calibration`，兩個標記都誠實，而循環照樣發生。原因是那道
#: gate 問的是「共識有沒有被當成支持證據」，**而逆推根本不需要那樣標**：共識不支持
#: 「成長率是 11.59%」，它只是被反解出這個值（L15-1：這個 gate 攔下的不是它想攔的東西）。
#: 基期觀測 supporting 的是「基期是多少」，不是「成長率該是多少」。
#:
#: - `independent`：值由我們自己的分析決定（結論接不接近共識由 `eps_contribution` 自己說，
#:   **不在這裡再標一次**——那會變成兩個地方講同一件事）。
#: - `consensus_inverted`：值由同期共識反解得出。**這不是觀點，是佔位**。
#: - `company_guidance`：採公司自家指引（6324.T／LYC.AX 的形狀）。
#: - `carried_forward`：沿用基期實績（tax_rate／nci／shares／interest 的常見且正確做法）。
#: - `unclassified`：舊紀錄的 fail safe；**寫入端一律拒絕**。
#:
#: ⚠ 刻意**沒有** `consensus_convergent`（「獨立算過剛好接近共識」）：今天 14 本 ledger
#: 沒有任何一筆是那個形狀，在沒有資料支撐的地方泛化只會得到會誤報的分類（L17-4）。
ASSUMPTION_DERIVATIONS: tuple[str, ...] = (
    "independent", "consensus_inverted", "company_guidance", "carried_forward", "unclassified",
)

#: `derivation` 屬於「我們有沒有形成觀點」這一題的**核心 driver**。其餘四個 driver
#: （tax_rate／nci_attribution／diluted_shares／interest_and_other_net）沿用基期實績是正確做法，
#: 把它們算進來會讓每一家公司都被判成沒有觀點——那個判準會恆亮，也就等於沒有鑑別力（L14-4）。
OPINION_BEARING_DRIVERS: frozenset[str] = frozenset({"revenue_growth", "operating_margin_delta"})

#: 一家公司在**這一期**有沒有形成自己的觀點。由 `derivation` 聚合而來，是**模型層的宣告**，
#: 不是呈現層 parse 理由句猜出來的（APP 呈現契約：`absence_kind` 那條同理）。
#:
#: 優先序刻意 fail safe 到「沒有觀點」：`unclassified` 永遠不會被算成 independent。
#: - `independent`：至少一條核心 driver 由我們自己決定 → **這一格有內容可讀**。
#: - `consensus_inverted`：核心 driver 沒有一條是自己的，且至少一條由共識反解 → **這是佔位，
#:   隱含報酬的 0 不攜帶資訊**。
#: - `company_guidance`：核心 driver 全部採公司指引 → 既不是我們的觀點，也不是共識循環。
#: - `undeclared`：只有舊紀錄（未宣告）。
#: - `no_opinion_bearing_assumptions`：連核心 driver 的假設都沒有 → 還沒開始。
OPINION_STANCES: tuple[str, ...] = (
    "independent", "consensus_inverted", "company_guidance", "undeclared",
    "no_opinion_bearing_assumptions",
)


def opinion_stance(assumptions: Sequence["OperatingAssumption"]) -> str:
    """一組 accepted 假設 → 這家公司這一期的 opinion stance。**純函式**。

    只看 `OPINION_BEARING_DRIVERS`：沿用基期實績的 tax／shares／NCI／interest 不參與，
    否則每一家公司都會被判成沒有觀點，而一個恆亮的判準等於零鑑別力（L14-4）。
    """
    live = [a for a in assumptions
            if a.driver in OPINION_BEARING_DRIVERS and not a.retracted]
    if not live:
        return "no_opinion_bearing_assumptions"
    kinds = {a.derivation for a in live}
    # ⚠ 順序不是「哪個聽起來比較強」，是**哪一種結構上可能產生預期差**（2026-09-10 實測後修正）：
    # `consensus_inverted` 的值就是從共識反解的，所以它**結構上不可能**與共識不同；
    # `company_guidance` 的值來自公司指引，而公司指引與共識**可以**不同、而且常常不同。
    # 實例：LITE 的營益率取自公司 Q1 指引持平外推，共識沒這樣做——那條假設一條就貢獻了
    # +8.92% 的 EPS 差異。把它壓成「還沒形成觀點」會把一個真實的立場說成空白。
    for stance in ("independent", "company_guidance", "consensus_inverted"):
        if stance in kinds:
            return stance
    return "undeclared"


@dataclass(frozen=True, slots=True)
class OperatingAssumption:
    """StockBot 對某個未來 driver 的**明示**假設。

    ⚠ 它不是事實。`basis` 說它是哪一種知識；`rationale` 說為什麼；`evidence_refs` 指回
    ResearchContext／Engine C 的證據；`created_at` 決定 as-of 視角下它存不存在。

    Step 0.5（2026-09-06）補的三個欄位，全部 additive、舊紀錄照樣 parse：
    - `dependency_roles`：ref → supporting／calibration／comparison。「證據還在」≠「證據仍支持
      這個假設」，refresh 引擎要知道哪些 ref 是 supporting 才能判 review_required。
    - `review_conditions`：machine-readable 的觸發條件（不是 parser 讀 rationale）。
    - `provenance_semantics`：`legacy`＝舊紀錄，未宣告角色；讀取端 fail safe。
    """

    assumption_id: str
    company_id: str
    ticker: str
    period: FiscalPeriod
    driver: str
    scope: str
    value: float
    unit: str
    basis: str
    rationale: str
    evidence_refs: tuple[str, ...]
    created_at: datetime
    author: str = "session"
    accounting_basis: str = "not_applicable"
    supersedes_id: str | None = None
    retracted: bool = False
    dependency_roles: Mapping[str, str] = field(default_factory=dict)
    review_conditions: tuple[Any, ...] = ()
    provenance_semantics: str = "legacy"
    derivation: str = "unclassified"

    def __post_init__(self) -> None:
        _nonempty(self.assumption_id, "OperatingAssumption.assumption_id")
        if not self.assumption_id.startswith("oa_"):
            raise ContractViolation("assumption_id 必須以 oa_ 開頭（由 new_assumption_id 產生）")
        _nonempty(self.company_id, "OperatingAssumption.company_id")
        _nonempty(self.ticker, "OperatingAssumption.ticker")
        spec = ASSUMPTION_DRIVERS.get(self.driver)
        if spec is None:
            raise ContractViolation(
                f"driver 未登記：{self.driver!r}；已知 {sorted(ASSUMPTION_DRIVERS)}——"
                "driver 是 contract，多一個就要多一段橋的算術")
        if self.unit != spec.unit:
            raise ContractViolation(
                f"driver {self.driver} 的單位必須是 {spec.unit!r}，收到 {self.unit!r}")
        _nonempty(self.scope, "OperatingAssumption.scope")
        if spec.scope_kind == "total" and self.scope != TOTAL_SCOPE:
            raise ContractViolation(f"driver {self.driver} 的 scope 只能是 {TOTAL_SCOPE!r}")
        if self.basis not in ASSUMPTION_BASES:
            raise ContractViolation(
                f"basis 未登記：{self.basis!r}；已知 {ASSUMPTION_BASES}")
        if self.accounting_basis not in ACCOUNTING_BASES:
            raise ContractViolation(f"accounting_basis 未登記：{self.accounting_basis!r}")
        value = _finite(self.value, "OperatingAssumption.value")
        if spec.lower is not None and value < spec.lower:
            raise ContractViolation(f"{self.driver}={value} 低於下限 {spec.lower}")
        if spec.upper is not None and value > spec.upper:
            raise ContractViolation(f"{self.driver}={value} 高於上限 {spec.upper}")
        _nonempty(self.rationale, "OperatingAssumption.rationale")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須是帶時區的 datetime")
        if not self.retracted and not self.evidence_refs:
            raise ContractViolation(
                "OperatingAssumption 必須至少引用一條證據——沒有 provenance 的假設不得存在（INV-6）")
        if any(not isinstance(r, str) or not r.strip() for r in self.evidence_refs):
            raise ContractViolation("evidence_refs 每一項必須是非空字串")
        if self.provenance_semantics not in PROVENANCE_SEMANTICS:
            raise ContractViolation(
                f"provenance_semantics 未登記：{self.provenance_semantics!r}；已知 {PROVENANCE_SEMANTICS}")
        if self.derivation not in ASSUMPTION_DERIVATIONS:
            raise ContractViolation(
                f"derivation 未登記：{self.derivation!r}；已知 {ASSUMPTION_DERIVATIONS}")
        if self.derivation == "consensus_inverted" and not self.retracted:
            # 補償控制（放行與收緊同時發生）：宣告「由共識反解」就必須指得出被反解的那筆共識，
            # 否則這個宣告無法被交叉檢查，只是一個自由字串。
            if not any(r.startswith(CONSENSUS_REF_PREFIX) for r in self.evidence_refs):
                raise ContractViolation(
                    "derivation=consensus_inverted 必須引用被反解的那筆同期共識"
                    f"（{CONSENSUS_REF_PREFIX}...），否則這個宣告無從查證")
        for ref, role in self.dependency_roles.items():
            if role not in ASSUMPTION_REF_ROLES:
                raise ContractViolation(f"dependency_roles[{ref}] 未登記：{role!r}；已知 {ASSUMPTION_REF_ROLES}")
            if ref not in self.evidence_refs:
                raise ContractViolation(f"dependency_roles 指到不在 evidence_refs 的 ref：{ref!r}")
            if role == "supporting" and ref.startswith(CONSENSUS_REF_PREFIX):
                raise ContractViolation(
                    f"同期共識 {ref!r} 不得作為 supporting evidence——那是 provenance 循環"
                    "（共識支持假設→假設推出內部預測→再拿去比共識）；請改列 calibration_refs")
        if self.provenance_semantics == "v2" and not self.retracted:
            missing = [r for r in self.evidence_refs if r not in self.dependency_roles]
            if missing:
                raise ContractViolation(f"v2 假設每條 ref 都必須宣告角色；缺：{missing[:3]}")
            if not any(role == "supporting" for role in self.dependency_roles.values()):
                raise ContractViolation("v2 假設至少要有一條 supporting evidence（calibration 不算支持）")
        from ..refresh.contracts import ReviewCondition

        if any(not isinstance(c, ReviewCondition) for c in self.review_conditions):
            raise ContractViolation("review_conditions 每一項必須是 ReviewCondition")

    @property
    def key(self) -> tuple[str, str]:
        return (self.driver, self.scope)

    @property
    def created_on(self) -> date:
        return self.created_at.date()

    def role_of(self, ref: str) -> str:
        """一條 ref 的角色。legacy 紀錄：同期共識依前綴歸 calibration，其餘 `legacy_unclassified`
        （refresh 引擎把它當 supporting——fail safe 往「更容易被標 review」那邊倒）。"""
        declared = self.dependency_roles.get(ref)
        if declared is not None:
            return declared
        if ref.startswith(CONSENSUS_REF_PREFIX):
            return "calibration"
        return "legacy_unclassified"

    @property
    def supporting_refs(self) -> tuple[str, ...]:
        return tuple(r for r in self.evidence_refs if self.role_of(r) in ("supporting", "legacy_unclassified"))

    @property
    def calibration_refs(self) -> tuple[str, ...]:
        return tuple(r for r in self.evidence_refs if self.role_of(r) == "calibration")


# ---------------------------------------------------------------------------
# 3. Engine C 觀測（由 provider 唯讀取出；這裡只定型別）
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FiscalYearActuals:
    """某個**已報告**會計年度的損益骨架。全部來自 Engine C 人工 ledger（`fiscal_year_results`）。

    `gaap`／`non_gaap` 是印在財報／新聞稿上的數字（自由鍵，但橋只讀固定幾個）；
    `exit_quarter` 是最後一季的 run-rate 原料，明標為季度。
    """

    period: FiscalPeriod
    currency: str
    revenue: float
    segment_revenue: Mapping[str, float] | None
    gaap: Mapping[str, float]
    non_gaap: Mapping[str, float] | None
    evidence: tuple[EvidenceRef, ...]
    exit_quarter: Mapping[str, Any] | None = None
    source_filed_at: date | None = None
    recorded_at: datetime | None = None
    observation_id: str | None = None
    #: 基期作者寫下的「這一格為什麼是這樣、哪一格刻意留空、不准怎麼補」。
    #: 2026-09-11 之前 parser 直接丟掉它：46 筆基期觀測有 **40 筆**寫了，下游 **0 筆**看得到。
    #: 而其中好幾條是會咬人的——002472.SZ「共識口徑是扣非，已一手核實」、5802.T「股票分割
    #: 口徑」、000660.KS「非營業損益與稅率刻意未填，不得合併塞進 tax_rate（那會一格兩義）」。
    #: 寫下它的人已經做對了事，是管子只接了一頭（L13）。
    coverage_note: str | None = None
    #: parser 沒有對應欄位的其餘鍵，**原樣保留**。
    #: ⚠ 這是「不得靜默丟棄」的那一半：列舉式解析每多一個新鍵就多一次無聲遺失，
    #: 而作者不會知道自己寫的東西沒人收到（INV-3：查不到了不是合法 lifecycle）。
    author_notes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.currency, "FiscalYearActuals.currency")
        if _finite(self.revenue, "FiscalYearActuals.revenue") <= 0:
            raise ContractViolation("FiscalYearActuals.revenue 必須為正")
        if not self.evidence:
            raise ContractViolation("FiscalYearActuals 必須帶 evidence（INV-6）")
        if self.segment_revenue is not None:
            for name, value in self.segment_revenue.items():
                _finite(value, f"segment_revenue[{name}]")
        for name, block in (("gaap", self.gaap), ("non_gaap", self.non_gaap)):
            if block is None:
                continue
            for key, value in block.items():
                if value is not None:
                    _finite(value, f"{name}.{key}")

    def block(self, basis: str) -> Mapping[str, float] | None:
        if basis == "gaap":
            return self.gaap
        if basis == "non_gaap":
            return self.non_gaap
        return None

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(r.ref for r in self.evidence)


@dataclass(frozen=True, slots=True)
class ConsensusEstimate:
    """一筆會計期間別的分析師共識（Engine C `consensus_estimates`）。`value is None`＝缺料。"""

    metric: str
    period: FiscalPeriod
    value: float | None
    source: str
    evidence: tuple[EvidenceRef, ...]
    low: float | None = None
    high: float | None = None
    analyst_count: int | None = None
    year_ago_actual: float | None = None
    growth: float | None = None
    currency: str | None = None
    captured_at: date | None = None
    fetched_at: datetime | None = None
    relative_label: str | None = None

    def __post_init__(self) -> None:
        if self.metric not in ("eps", "revenue"):
            raise ContractViolation(f"ConsensusEstimate.metric 未登記：{self.metric!r}")
        if not self.evidence:
            raise ContractViolation("ConsensusEstimate 必須帶 evidence（INV-6）")

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(r.ref for r in self.evidence)


@dataclass(frozen=True, slots=True)
class GuidanceObservation:
    """公司公開指引（Engine C `company_guidance`）。它是「公司說了什麼」，不是本系統的假設。"""

    period_label: str
    period_kind: str
    period_end: date | None
    basis: str
    values: Mapping[str, float]
    issued_at: date | None
    evidence: tuple[EvidenceRef, ...]
    observation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ContractViolation("GuidanceObservation 必須帶 evidence（INV-6）")

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(r.ref for r in self.evidence)


# ---------------------------------------------------------------------------
# 4. 模型輸出
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BridgeStep:
    """橋上的一格。`kind`：observation（基期觀測）／assumption（輸入假設）／derived（算出）。"""

    key: str
    label: str
    kind: str
    value: float | None
    unit: str
    basis: str                       # observation／heuristic_proxy／session_judgment／deterministic／none
    formula: str | None = None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    reason: str | None = None
    scope: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("observation", "assumption", "derived"):
            raise ContractViolation(f"BridgeStep.kind 未登記：{self.kind!r}")
        if self.value is None and self.basis != "none":
            raise ContractViolation(f"BridgeStep[{self.key}] 沒有值就沒有 basis（missing != zero）")
        if self.value is not None and self.basis == "none":
            raise ContractViolation(f"BridgeStep[{self.key}] 有值必須說出知識種類")
        if self.value is not None:
            _finite(self.value, f"BridgeStep[{self.key}].value")


@dataclass(frozen=True, slots=True)
class ModeledMetric:
    """一個內部估計。**沒有 naked number**：值、期間、單位、口徑、公式、依賴全在一起。"""

    metric: str
    period: FiscalPeriod
    value: float | None
    unit: str
    accounting_basis: str
    calculation: str = "deterministic"
    input_dependency: str | None = None    # 最弱輸入假設的 basis；None＝沒有值
    formula: str | None = None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.accounting_basis not in ACCOUNTING_BASES:
            raise ContractViolation(f"ModeledMetric.accounting_basis 未登記：{self.accounting_basis!r}")
        if self.value is not None:
            _finite(self.value, f"ModeledMetric[{self.metric}].value")
            if self.input_dependency is None:
                raise ContractViolation(
                    f"ModeledMetric[{self.metric}] 有值就必須說出輸入依賴的知識種類")
        elif self.input_dependency is not None:
            raise ContractViolation(f"ModeledMetric[{self.metric}] 沒有值就沒有輸入依賴")

    @property
    def is_known(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class Sensitivity:
    """一條假設動一格，輸出動多少。純確定性微擾，不是機率、不是情境。"""

    assumption_id: str
    driver: str
    scope: str
    bump: float
    bump_unit: str                      # absolute_ratio（+0.01）／relative（×1.01）
    delta_revenue: float | None
    delta_operating_income: float | None
    delta_eps: float | None
    eps_relative: float | None


@dataclass(frozen=True, slots=True)
class ExpectationComparison:
    """內部估計 vs 共識——**只在 `status == "comparable"` 時有數字**。"""

    metric: str
    status: str
    internal_period: FiscalPeriod | None
    consensus_period: FiscalPeriod | None
    internal: float | None
    consensus: float | None
    absolute_gap: float | None
    relative_gap: float | None
    unit: str | None
    accounting_basis_internal: str | None
    accounting_basis_consensus: str | None
    analyst_count: int | None
    consensus_captured_at: date | None
    reason: str | None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    consensus_refs: tuple[str, ...] = ()
    #: 共識口徑經**換算容差**認定時的殘差（provider ÷ 一手 − 1）。逐字相等或不可比時是 None。
    #: ⚠ 它是**這個 gap 的雜訊下限**：同一個換算差原樣進到 gap 裡，所以任何小於它的
    #: 差異都不具意義。結構化欄位而不是只寫在 `reason` 裡——下游要拿它做比較，
    #: 而呈現層不得 parse 理由句去猜（L16）。
    fx_translation_delta: float | None = None

    def __post_init__(self) -> None:
        if self.status not in COMPARISON_STATUSES:
            raise ContractViolation(f"ExpectationComparison.status 未登記：{self.status!r}")
        if self.status != "comparable" and (self.absolute_gap is not None or self.relative_gap is not None):
            raise ContractViolation(
                f"ExpectationComparison[{self.metric}] status={self.status} 不得帶 gap 數字——不能硬減")
        if self.status == "comparable" and (self.internal is None or self.consensus is None):
            raise ContractViolation("comparable 必須兩邊都有值")
        if self.fx_translation_delta is not None:
            _finite(self.fx_translation_delta, "ExpectationComparison.fx_translation_delta")
            if not str(self.accounting_basis_consensus or "").endswith("_fx_tolerated"):
                raise ContractViolation(
                    "fx_translation_delta 只屬於 *_fx_tolerated 的共識口徑——"
                    f"收到 {self.accounting_basis_consensus!r}")


@dataclass(frozen=True, slots=True)
class AssumptionSelection:
    """as-of／supersede／證據解析後的計數（INV-3：每個 filter 都能報 input／accepted／filtered／reasons）。"""

    input_count: int
    accepted_count: int
    reasons: Mapping[str, int]
    rejected: tuple[tuple[str, str], ...] = ()   # (assumption_id, reason)

    @property
    def filtered_count(self) -> int:
        return self.input_count - self.accepted_count


@dataclass(frozen=True, slots=True)
class FundamentalModelResult:
    """一次模型執行的完整輸出——read model 只選取，不重算。"""

    company_id: str
    ticker: str
    as_of: date | None
    target_period: FiscalPeriod | None
    base_period: FiscalPeriod | None
    accounting_basis: str
    status: str                             # available／partial／missing
    reason: str | None
    metrics: Mapping[str, ModeledMetric]
    steps: tuple[BridgeStep, ...]
    assumptions: tuple[OperatingAssumption, ...]
    selection: AssumptionSelection
    sensitivities: tuple[Sensitivity, ...]
    comparisons: Mapping[str, ExpectationComparison]
    consensus: tuple[ConsensusEstimate, ...]
    guidance: tuple[GuidanceObservation, ...]
    base_actuals: FiscalYearActuals | None
    #: 每筆共識的口徑核實結果，key＝`f"{metric}:{period_end}"`（見 `compare.verify_consensus_basis`）。
    consensus_bases: Mapping[str, str] = field(default_factory=dict)
    model_version: str = MODEL_VERSION
    bridge_version: str = BRIDGE_VERSION
    digest: str = ""
    warnings: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in ("available", "partial", "missing"):
            raise ContractViolation(f"FundamentalModelResult.status 未登記：{self.status!r}")
        if self.accounting_basis not in ACCOUNTING_BASES:
            raise ContractViolation(f"accounting_basis 未登記：{self.accounting_basis!r}")
        # 字彙一旦有行為後果就必須被強制（L16-3）：`consensus_bases` 的值決定
        # `compare_metric` 比不比較，先前是自由字串——打錯不會報錯，只會靜默變成不可比。
        for key, value in (self.consensus_bases or {}).items():
            if value not in CONSENSUS_BASES:
                raise ContractViolation(
                    f"consensus_bases[{key!r}] 未登記：{value!r}（合法值 {CONSENSUS_BASES}）")

    def metric(self, name: str) -> ModeledMetric | None:
        return self.metrics.get(name)

    @property
    def stance(self) -> str:
        """這一期我們有沒有形成自己的觀點（`OPINION_STANCES`）。

        ⚠ 它**不是** readiness 也不是 status：一份 `available` 的模型完全可能 stance 是
        `consensus_inverted`——每一格都有數字、每一個數字都是共識反解出來的。那正是
        2026-09-10 實測到的 5 檔（隱含報酬 ±0.01%，而那個 0 是代數上的必然，不是判斷）。
        """
        return opinion_stance(self.assumptions)


__all__ = [
    "ACCOUNTING_BASES", "CONSENSUS_BASES", "consensus_basis_stem", "ASSUMPTION_BASES", "ASSUMPTION_DRIVERS", "ASSUMPTION_REF_ROLES", "BRIDGE_VERSION",
    "CONSENSUS_REF_PREFIX", "PROVENANCE_SEMANTICS",
    "COMPARISON_STATUSES", "FISCAL_PERIOD_KINDS", "MODEL_VERSION",
    "PERIOD_MATCH_TOLERANCE_DAYS", "TOTAL_SCOPE", "AssumptionSelection", "BridgeStep",
    "ConsensusEstimate", "DriverSpec", "ExpectationComparison", "FiscalPeriod",
    "FiscalYearActuals", "FundamentalModelResult", "GuidanceObservation", "ModeledMetric",
    "OPINION_BEARING_DRIVERS", "OPINION_STANCES", "ASSUMPTION_DERIVATIONS",
    "OperatingAssumption", "Sensitivity", "opinion_stance", "weakest_basis",
]
