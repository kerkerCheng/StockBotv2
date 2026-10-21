"""
opendart.py — 韓國金融監督院 OpenDART 的讀取端（日韓財報來源 S3，2026-10-21；計畫 `docs/plans/2026-10-21-002-feat-jp-kr-filings-plan.md`）。

**它只做四件事：** 公司代碼表（corpCode.xml）、某公司的定期報告清單（list.json，含更正版）、某一份定期報告的單一公司
全部財務科目（fnlttSinglAcntAll，連結 CFS）、股式總數現況（stockTotqySttus）。哪個科目是營收、第四季怎麼推、
能不能寫進 Engine C——全部在 `engine_c/dart_history.py`，這一層不判斷。

## key 的四條收緊（與 `fetchers/edinet.py` 同一組；R2 trigger security・credentials）

1. key 只從環境變數 `OPENDART_API_KEY` 讀，不收參數、不寫檔。
2. key 在 URL query 裡（`crtfc_key`）——每一條離開本模組的字串都先過 `redact()`；不用 `raise_for_status`、不存 `response.url`。
3. 只送官方主機 `opendart.fss.or.kr`。
4. 不進 daily（`tests/test_codex_daily_permissions.py` 鎖住）。

## 狀態碼 → 具名結局（`STATUS_OUTCOMES`）

OpenDART 一律 HTTP 200、在 JSON 的 `status` 回錯誤碼。`ABORT_RUN` 裡的結局（key 錯、**個人資料保留期滿 901**、IP 被擋、
限流、維護）整輪中止並計數沒做的部分（INV-3）；`013 no_data` 是「這一期沒有」的正常結局，不是錯誤。
901 每 2 年會發生一次（個人資料保留期滿，要到 opendart.fss.or.kr 重新同意）——落地時登記了一筆有到期的等待（INV-2）。
"""
from __future__ import annotations

import io
import os
import time
import zipfile
import xml.etree.ElementTree as ET
from typing import Any, Callable

BASE = "https://opendart.fss.or.kr/api"
USER_AGENT = "StockBotv2 research (contact via repo owner)"
MIN_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 60
#: 報告代碼：1 分기、반기、3 分기、사업보고서。
REPORT_CODES = {"Q1": "11013", "H1": "11012", "Q3": "11014", "FY": "11011"}
STATUS_OUTCOMES = {
    "000": "ok", "013": "no_data", "014": "file_missing",
    "010": "auth_failed", "011": "auth_failed", "901": "consent_expired", "012": "ip_blocked",
    "020": "rate_limited", "021": "request_invalid", "100": "request_invalid", "101": "request_invalid",
    "800": "maintenance", "900": "unknown_error",
}
ABORT_RUN = frozenset({"auth_failed", "consent_expired", "ip_blocked", "rate_limited", "maintenance"})
CONSENT_EXPIRED_HINT = "OpenDART 個人資料保留期滿（901），需到 opendart.fss.or.kr 重新同意後 key 才會恢復"
REDACTED = "<REDACTED>"


class DartUnavailable(RuntimeError):
    """抓不到（網路、HTTP、回應形狀不對、狀態碼不是 000／013）。`outcome` 是 `STATUS_OUTCOMES` 的值或 `network`。"""

    def __init__(self, message: str, *, outcome: str = "network") -> None:
        super().__init__(message)
        self.outcome = outcome

    @property
    def aborts_run(self) -> bool:
        return self.outcome in ABORT_RUN


def api_key() -> str:
    key = (os.environ.get("OPENDART_API_KEY") or "").strip()
    if not key:
        raise DartUnavailable("OPENDART_API_KEY 沒設（.env）——OpenDART 回填需要 key", outcome="auth_failed")
    return key


def redact(text: Any, key: str | None) -> str:
    text = str(text)
    return text.replace(key, REDACTED) if key else text


class Client:
    """帶 key、節流、遮罩的呼叫端。`sleep`／`clock`／`get` 可注入（測試不連網、不真的睡）。"""

    def __init__(self, key: str, *, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, get: Callable[..., Any] | None = None,
                 min_interval: float = MIN_INTERVAL_SECONDS) -> None:
        self._key = key
        self._sleep = sleep
        self._clock = clock
        self._get_impl = get
        self._min_interval = min_interval
        self._last: float | None = None
        self.calls = 0

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        if self._last is not None:
            wait = self._min_interval - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        self._last = self._clock()
        self.calls += 1
        get = self._get_impl
        if get is None:
            import requests

            get = requests.get
        try:
            response = get(f"{BASE}/{path}", params={**params, "crtfc_key": self._key},
                           headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001 — 例外訊息可能帶 URL（含 key）：只留型別＋遮罩後的訊息
            raise DartUnavailable(f"{type(exc).__name__}: {redact(exc, self._key)}") from None
        status = int(getattr(response, "status_code", 0) or 0)
        if status != 200:
            raise DartUnavailable(f"{path} HTTP {status}", outcome="rate_limited" if status == 429 else "network")
        return response

    def _json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self._get(path, params)
        try:
            body = response.json()
        except ValueError:
            raise DartUnavailable(f"{path} 回應不是 JSON") from None
        status = str(body.get("status") or "")
        outcome = STATUS_OUTCOMES.get(status, "unknown_error")
        if outcome == "ok":
            return body
        if outcome == "no_data":
            return {**body, "list": []}
        message = CONSENT_EXPIRED_HINT if outcome == "consent_expired" else redact(body.get("message"), self._key)
        raise DartUnavailable(f"{path} status {status}（{outcome}）：{message}", outcome=outcome)

    def corp_codes(self) -> bytes:
        """corpCode.xml（zip）。回原始 bytes，解析交給 `corp_code_rows`。"""
        response = self._get("corpCode.xml", {})
        content = bytes(response.content)
        if content[:2] != b"PK":
            try:
                body = response.json()
            except ValueError:
                body = {}
            status = str(body.get("status") or "")
            outcome = STATUS_OUTCOMES.get(status, "unknown_error")
            message = CONSENT_EXPIRED_HINT if outcome == "consent_expired" else redact(body.get("message"), self._key)
            raise DartUnavailable(f"corpCode.xml 不是 zip（status {status}：{message}）", outcome=outcome)
        return content

    def periodic_reports(self, corp_code: str, begin: str, end: str) -> list[dict[str, Any]]:
        """定期報告清單（`pblntf_ty=A`，含原件與更正版），自動翻頁。"""
        out: list[dict[str, Any]] = []
        page = 1
        while True:
            body = self._json("list.json", {"corp_code": corp_code, "bgn_de": begin, "end_de": end, "pblntf_ty": "A",
                                            "page_no": page, "page_count": 100})
            out += [{k: r.get(k) for k in ("report_nm", "rcept_no", "rcept_dt", "rm", "stock_code", "corp_code")}
                    for r in body.get("list") or ()]
            if page >= int(body.get("total_page") or 1):
                return out
            page += 1

    def single_account_all(self, corp_code: str, year: int, report_code: str) -> dict[str, Any]:
        """單一公司全部財務科目（連結 CFS）。`013` 回 `{"status": "013", "list": []}`。"""
        return self._json("fnlttSinglAcntAll.json", {"corp_code": corp_code, "bsns_year": str(year),
                                                     "reprt_code": report_code, "fs_div": "CFS"})

    def share_totals(self, corp_code: str, year: int, report_code: str) -> dict[str, Any]:
        return self._json("stockTotqySttus.json", {"corp_code": corp_code, "bsns_year": str(year),
                                                   "reprt_code": report_code})


def corp_code_rows(data: bytes) -> list[dict[str, str]]:
    archive = zipfile.ZipFile(io.BytesIO(data))
    names = archive.namelist()
    if len(names) != 1:
        raise DartUnavailable(f"corpCode zip 應只有一份 XML（實際 {len(names)}）", outcome="unknown_error")
    root = ET.fromstring(archive.read(names[0]))
    return [{child.tag: (child.text or "").strip() for child in entry} for entry in root.findall("list")]


def corp_code_for(stock_code: str, rows: list[dict[str, str]]) -> str:
    """名冊代號（6 碼）→ corp_code。**0 筆或多筆就 raise**（INV-1：不猜）。"""
    hits = sorted({r["corp_code"] for r in rows if r.get("stock_code") == stock_code and r.get("corp_code")})
    if len(hits) != 1:
        raise LookupError(f"stock_code {stock_code} 在 corpCode 命中 {len(hits)} 筆（{', '.join(hits) or '無'}）——不猜")
    return hits[0]


__all__ = [
    "ABORT_RUN", "BASE", "CONSENT_EXPIRED_HINT", "Client", "DartUnavailable", "MIN_INTERVAL_SECONDS", "REPORT_CODES",
    "STATUS_OUTCOMES", "api_key", "corp_code_for", "corp_code_rows", "redact",
]
