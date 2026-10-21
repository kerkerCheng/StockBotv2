"""
edinet.py — 金融庁 EDINET API v2 的讀取端（日韓財報來源 S2，2026-10-21；計畫 `docs/plans/2026-10-21-002-feat-jp-kr-filings-plan.md`）。

**它只做三件事：** 列某一天交了哪些定期報告（書類一覧 type=2）、下載一份報告的 XBRL→CSV（書類取得 type=5）、
把那份 CSV 解成列。哪個元素是營收、哪個 context 是當期、能不能寫進 Engine C——全部在
`engine_c/edinet_history.py`，這一層不判斷。

## key 的四條收緊（計畫風險②；R2 trigger security・credentials）

1. key 只從環境變數 `EDINET_API_KEY` 讀（`.env` 由 CLI 入口載入），**不收參數、不寫檔**。
2. key 在 URL query 裡（`Subscription-Key`）——`requests` 的例外訊息會帶出整條 URL，所以**每一條離開本模組的
   字串都先過 `redact()`**；不用 `raise_for_status`（它的訊息也帶 URL），不把 `response.url` 存到任何地方。
3. 只送官方主機 `api.edinet-fsa.go.jp`；コードリスト（`disclosure2dl.edinet-fsa.go.jp`）不需要 key、也不帶 key。
4. 不進 daily（`tests/test_codex_daily_permissions.py` 鎖住）：漏抓補得回來（EDINET 保存 10 年，L10）。

## 節流（計畫風險①：規約禁止「短時間における大量のアクセス」）

每次呼叫至少間隔 `MIN_INTERVAL_SECONDS`；429／503 依 `BACKOFF_SECONDS` 退避重試，退完仍失敗就 raise
`EdinetRateLimited`——呼叫端整輪中止並計數沒掃的日期（INV-3），不硬撐。

內容依 PDL1.0 授權；原檔不進 repo（公開）——只在 `library/private/` 留解析後的白名單列。
"""
from __future__ import annotations

import csv
import io
import os
import time
import zipfile
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

BASE = "https://api.edinet-fsa.go.jp/api/v2"
CODELIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
USER_AGENT = "StockBotv2 research (contact via repo owner)"
MIN_INTERVAL_SECONDS = 2.0
BACKOFF_SECONDS = (60, 120, 240)
TIMEOUT_SECONDS = 120
#: 有價證券報告書 120、訂正 130；四半期報告書 140、訂正 150；半期報告書 160、訂正 170。
PERIODIC_DOC_TYPES = ("120", "130", "140", "150", "160", "170")
#: 書類一覧快取只留這幾欄（全市場、定期報告）——名冊之後加一檔不必重掃。
LIST_FIELDS = ("docID", "edinetCode", "secCode", "docTypeCode", "submitDateTime", "parentDocID",
               "withdrawalStatus", "docInfoEditStatus", "xbrlFlag", "csvFlag")
#: type=5 CSV 的九欄（UTF-16、TSV）；表頭不是這九欄就拒收，不猜欄位位置。
CSV_COLUMNS = ("要素ID", "項目名", "コンテキストID", "相対年度", "連結・個別", "期間・時点", "ユニットID", "単位", "値")
REDACTED = "<REDACTED>"


class EdinetUnavailable(RuntimeError):
    """抓不到（網路、HTTP、回應形狀不對）。訊息一律已遮罩。"""


class EdinetAuthError(EdinetUnavailable):
    """key 沒設或被拒（401／403）——整輪中止。"""


class EdinetRateLimited(EdinetUnavailable):
    """429／503 退避後仍失敗——整輪中止，計數沒掃的部分。"""


class EdinetDocMissing(EdinetUnavailable):
    """書類取得回 404（取下、或該 docID 沒有 CSV）。"""


def api_key() -> str:
    key = (os.environ.get("EDINET_API_KEY") or "").strip()
    if not key:
        raise EdinetAuthError("EDINET_API_KEY 沒設（.env）——EDINET 回填需要 key")
    return key


def redact(text: Any, key: str | None) -> str:
    text = str(text)
    return text.replace(key, REDACTED) if key else text


@dataclass(frozen=True)
class CsvRow:
    element: str
    label: str
    context: str
    relative: str
    consolidation: str
    period_kind: str
    unit: str
    unit_label: str
    value: str


class Client:
    """帶 key、節流、遮罩的呼叫端。`sleep`／`clock`／`get` 可注入（測試不連網、不真的睡）。"""

    def __init__(self, key: str, *, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, get: Callable[..., Any] | None = None,
                 min_interval: float = MIN_INTERVAL_SECONDS, backoff: tuple[float, ...] = BACKOFF_SECONDS) -> None:
        self._key = key
        self._sleep = sleep
        self._clock = clock
        self._get_impl = get
        self._min_interval = min_interval
        self._backoff = backoff
        self._last: float | None = None
        self.calls = 0

    def _http_get(self, url: str, params: dict[str, Any]) -> Any:
        get = self._get_impl
        if get is None:
            import requests

            get = requests.get
        return get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        if not path.startswith("/"):
            raise ValueError(path)
        attempt = 0
        while True:
            if self._last is not None:
                wait = self._min_interval - (self._clock() - self._last)
                if wait > 0:
                    self._sleep(wait)
            self._last = self._clock()
            self.calls += 1
            try:
                response = self._http_get(BASE + path, {**params, "Subscription-Key": self._key})
            except Exception as exc:  # noqa: BLE001 — 例外訊息可能帶 URL（含 key）：只留型別＋遮罩後的訊息
                raise EdinetUnavailable(f"{type(exc).__name__}: {redact(exc, self._key)}") from None
            status = int(getattr(response, "status_code", 0) or 0)
            if status in (429, 503):
                if attempt < len(self._backoff):
                    self._sleep(self._backoff[attempt])
                    attempt += 1
                    continue
                raise EdinetRateLimited(f"HTTP {status}：退避 {len(self._backoff)} 次仍被限流——整輪中止")
            if status in (401, 403):
                raise EdinetAuthError(f"HTTP {status}：key 被拒（{redact(_body_hint(response), self._key)}）")
            if status == 404:
                raise EdinetDocMissing(f"HTTP 404（{redact(_body_hint(response), self._key)}）")
            if status != 200:
                raise EdinetUnavailable(f"HTTP {status}（{redact(_body_hint(response), self._key)}）")
            return response

    def list_documents(self, day: date) -> dict[str, Any]:
        """某一天的書類一覧 → `{"count_all": 全部份數, "results": [定期報告、只留 LIST_FIELDS]}`。"""
        response = self._get("/documents.json", {"date": day.isoformat(), "type": 2})
        try:
            body = response.json()
        except ValueError:
            raise EdinetUnavailable(f"{day} 書類一覧不是 JSON") from None
        _raise_for_body(body, self._key, what=f"{day} 書類一覧")
        meta = body.get("metadata") or {}
        if str(meta.get("status")) != "200":
            raise EdinetUnavailable(f"{day} 書類一覧 status={redact(meta.get('status'), self._key)}："
                                    f"{redact(meta.get('message'), self._key)}")
        results = body.get("results")
        if not isinstance(results, list):
            raise EdinetUnavailable(f"{day} 書類一覧沒有 results 陣列")
        kept = [{k: r.get(k) for k in LIST_FIELDS} for r in results
                if isinstance(r, dict) and str(r.get("docTypeCode") or "") in PERIODIC_DOC_TYPES]
        return {"count_all": len(results), "results": kept}

    def fetch_csv_zip(self, doc_id: str) -> bytes:
        if not doc_id or not doc_id.isalnum():
            raise ValueError(f"docID 不合法：{doc_id!r}")
        response = self._get(f"/documents/{doc_id}", {"type": 5})
        ctype = str((getattr(response, "headers", None) or {}).get("Content-Type") or "")
        if ctype.startswith(("application/octet-stream", "application/zip", "application/x-zip")):
            return bytes(response.content)
        try:
            body = response.json()
        except ValueError:
            raise EdinetUnavailable(f"{doc_id} 回應不是 zip（Content-Type {ctype}）") from None
        _raise_for_body(body, self._key, what=doc_id)
        status = str(((body or {}).get("metadata") or {}).get("status") or "")
        if status == "404":
            raise EdinetDocMissing(f"{doc_id}：書類取得回 404（取下或沒有 CSV）")
        raise EdinetUnavailable(f"{doc_id} 回應不是 zip（status={redact(status, self._key)}）")


def _body_hint(response: Any) -> str:
    try:
        return str(getattr(response, "text", "") or "")[:200]
    except Exception:  # noqa: BLE001
        return ""


def _raise_for_body(body: Any, key: str, *, what: str) -> None:
    """EDINET 對 key 錯誤可能回 HTTP 200＋`{"StatusCode": 401, "message": ...}`——照 HTTP 401 處理。"""
    if isinstance(body, dict) and "StatusCode" in body:
        code = str(body.get("StatusCode"))
        message = redact(body.get("message"), key)
        if code in ("401", "403"):
            raise EdinetAuthError(f"{what}：key 被拒（{code} {message}）")
        if code in ("429", "503"):
            raise EdinetRateLimited(f"{what}：限流（{code} {message}）")
        raise EdinetUnavailable(f"{what}：StatusCode {code} {message}")


def parse_csv_zip(data: bytes) -> list[CsvRow]:
    """type=5 zip → 列（純函式）。只讀 `jpcrp` 開頭的那份（本文）；`jpaud`（監査報告）跳過。"""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise EdinetUnavailable("type=5 回應不是合法的 zip") from None
    names = [n for n in archive.namelist() if n.rsplit("/", 1)[-1].startswith("jpcrp") and n.endswith(".csv")]
    if not names:
        raise EdinetUnavailable("zip 裡沒有 jpcrp 的 CSV")
    rows: list[CsvRow] = []
    for name in names:
        raw = archive.read(name)
        text = raw.decode("utf-16")
        table = list(csv.reader(io.StringIO(text), delimiter="\t"))
        if not table or tuple(c.strip() for c in table[0]) != CSV_COLUMNS:
            raise EdinetUnavailable(f"{name.rsplit('/', 1)[-1]}：表頭不是預期的九欄——不猜欄位位置")
        rows.extend(CsvRow(*r[:9]) for r in table[1:] if len(r) >= 9)
    return rows


def fetch_codelist(*, get: Callable[..., Any] | None = None) -> bytes:
    """EDINET コードリスト（不需 key、不帶 key）。"""
    if get is None:
        import requests

        get = requests.get
    try:
        response = get(CODELIST_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001
        raise EdinetUnavailable(f"コードリスト：{type(exc).__name__}") from None
    if int(getattr(response, "status_code", 0) or 0) != 200:
        raise EdinetUnavailable(f"コードリスト HTTP {getattr(response, 'status_code', '?')}")
    return bytes(response.content)


def codelist_rows(codelist_zip: bytes) -> list[dict[str, str]]:
    """コードリスト zip（cp932 CSV；第一行是下載日、第二行是表頭）→ 每列一個 dict。"""
    archive = zipfile.ZipFile(io.BytesIO(codelist_zip))
    names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
    if len(names) != 1:
        raise EdinetUnavailable(f"コードリスト zip 應只有一份 CSV（實際 {len(names)}）")
    lines = archive.read(names[0]).decode("cp932").splitlines()
    table = list(csv.reader(lines[1:]))
    if not table or "証券コード" not in table[0] or "ＥＤＩＮＥＴコード" not in table[0]:
        raise EdinetUnavailable("コードリストの表頭に 証券コード／ＥＤＩＮＥＴコード がない")
    header = [h.strip() for h in table[0]]
    return [dict(zip(header, (c.strip() for c in row))) for row in table[1:] if row]


def edinet_code_for(sec4: str, rows: list[dict[str, str]]) -> str:
    """名冊代號（4 碼，新制可能含英文字母）→ EDINET コード。**0 筆或多筆就 raise**（INV-1：不猜）。

    コードリスト的証券コード是 5 碼＝名冊代號＋"0"；用字串比對，不轉整數。
    """
    sec5 = f"{sec4}0"
    hits = sorted({r["ＥＤＩＮＥＴコード"] for r in rows if r.get("証券コード") == sec5 and r.get("ＥＤＩＮＥＴコード")})
    if len(hits) != 1:
        raise LookupError(f"証券コード {sec5} 在コードリスト命中 {len(hits)} 筆（{', '.join(hits) or '無'}）——不猜")
    return hits[0]


__all__ = [
    "BASE", "CODELIST_URL", "CSV_COLUMNS", "Client", "CsvRow", "EdinetAuthError", "EdinetDocMissing",
    "EdinetRateLimited", "EdinetUnavailable", "LIST_FIELDS", "MIN_INTERVAL_SECONDS", "PERIODIC_DOC_TYPES",
    "api_key", "codelist_rows", "edinet_code_for", "fetch_codelist", "parse_csv_zip", "redact",
]
