"""Read-only HTTP API ＋ static Web App。**這一支是 request path 的全部。**

## 為什麼是 Starlette

repo 已經有 `starlette` 與 `uvicorn`（`mcp>=1.28` 的相依），所以這一層**沒有新增任何套件**。
不引 FastAPI／Flask／React 的理由是同一條：APP 要做的事是「讀一份已經算好的 JSON 並排版」，
不需要 ORM、不需要 pydantic 驗證層（artifact 的驗證住 `contracts.validate_artifact`）、
也不需要前端建置工具鏈——那些只會多一套要維護的平行架構。

## request path 的四條禁令（`tests/test_webapp_request_path.py` 逐條斷言）

1. **不 import 任何模型模組。** 本檔的 import 清單只有 stdlib ＋ starlette ＋ `.contracts`／`.store`。
   `alpha.*`、`briefing.*`、`neo4j`、`yfinance`、`anthropic`、`engine_c`、`decision_lab`
   一個都不在——所以「HTTP 時重跑研究」在 import 層就不可能。
2. **不寫任何東西。** 沒有 POST／PUT／PATCH／DELETE 路由；`ArtifactStore.write` 不被本檔呼叫。
3. **cache miss／stale 不重建。** 讀不到就回 503 ＋ 「請跑 materialize」；過期就標 stale 照回。
4. **不吐 stack trace／credential／private path。** 錯誤回應是固定形狀的 JSON；
   private 路徑早在 materialize 端就被遮蔽過一次。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from .contracts import ARTIFACT_SCHEMA_VERSION, ArtifactUnavailable, max_age_hours
from .store import ArtifactStore, StateArtifactStore, resolve_state_dir

API_VERSION = "v1"
STATIC_DIR = Path(__file__).resolve().parent / "static"

#: 這些 header 讓私人研究內容不被中介／瀏覽器快取或被別的站嵌入。
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy":
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
}


def _json(payload: Any, status: int = 200) -> JSONResponse:
    response = JSONResponse(payload, status_code=status)
    for key, value in _SECURITY_HEADERS.items():
        response.headers[key] = value
    return response


def _store(request: Request) -> ArtifactStore:
    return request.app.state.store


def _state(request: Request) -> StateArtifactStore:
    return request.app.state.state_store


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

async def health(request: Request) -> Response:
    """存活探針。**不透露任何研究內容、不透露 artifact 目錄路徑。**"""
    store = _store(request)
    return _json({
        "status": "ok",
        "api_version": API_VERSION,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "materialized_count": len(store.tickers()),
        "state_kinds": _state(request).kinds(),
        "request_path": "read-only：no LLM、no authority write、no external fetch、no model execution",
    })


async def meta(request: Request) -> Response:
    """字彙表與契約說明——**由 materialize 端寫下的那一份**，APP 不自己維護第二份（L16）。"""
    store = _store(request)
    vocab = _read_vocabularies(store)
    payload: dict[str, Any] = {
        "api_version": API_VERSION,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "freshness_rule": f"artifact 年齡 > {max_age_hours()} 小時 ＝ stale；"
                          "**stale 不會觸發重建**——重建是 materialize 的責任，不是 HTTP request 的。",
        "endpoints": [
            f"GET /api/{API_VERSION}/health",
            f"GET /api/{API_VERSION}/meta",
            f"GET /api/{API_VERSION}/stocks",
            f"GET /api/{API_VERSION}/stocks/{{ticker}}",
            f"GET /api/{API_VERSION}/ranking",
            f"GET /api/{API_VERSION}/beta",
        ],
        "not_offered": [
            "沒有任何寫入端點：不下單、不記錄選擇、不改 thesis、不入圖、不核准 pq2。",
            "沒有 runtime LLM：APP 讀已經形成的判讀，不在點擊時產生新判斷。",
            "不重算排序：/api/v1/ranking 照抄 materialize 當下 rank_bottlenecks() 的輸出（唯一排序權威）；"
            "APP 不重排、不加權、不自建第二套結構評分。",
            "沒有部位尺寸：買多少、什麼時候買由使用者自行判斷並手動下單。",
        ],
    }
    payload.update(vocab)
    return _json(payload)


async def stocks(request: Request) -> Response:
    """清單／總覽。壞掉的 artifact **不靜默丟棄**——以 `unavailable` 一併回報（INV-3）。"""
    store = _store(request)
    items: list[dict[str, Any]] = []
    unavailable: list[dict[str, str]] = []
    for ticker, payload, freshness, reason in store.read_all():
        if payload is None or freshness is None:
            unavailable.append({"ticker": ticker, "reason": reason or "unknown",
                                "remedy": "重跑 `python -m webapp materialize`（artifact 是可重建的 cache）"})
            continue
        overview = dict(payload["overview"])
        overview["freshness"] = freshness.to_dict()
        overview["generated_at"] = payload["generated_at"]
        overview["research_context_digest"] = payload.get("research_context_digest")
        items.append(overview)
    items.sort(key=lambda row: str(row.get("ticker") or ""))
    return _json({
        "api_version": API_VERSION,
        "count": len(items),
        "stocks": items,
        "unavailable": unavailable,
        "correlation_warning": _CORRELATION_WARNING,
    })


async def stock_detail(request: Request) -> Response:
    """單檔完整 materialized Analyst View。**照抄 artifact，不重組、不重算。**"""
    store = _store(request)
    ticker = request.path_params["ticker"]
    try:
        payload, freshness = store.read(ticker)
    except ArtifactUnavailable as exc:
        return _json({"error": {"kind": "artifact_unavailable", "ticker": exc.ticker,
                                "reason": exc.reason,
                                "remedy": "跑 `python -m webapp materialize " + str(exc.ticker) + "`",
                                "note": "「artifact 讀不到」與「這檔沒有研究結論」是兩件事——"
                                        "後者會以 readiness=blocked ＋ blocker_details 回 200。"}},
                     status=503)
    body = dict(payload)
    body["freshness"] = freshness.to_dict()
    body["correlation_warning"] = _CORRELATION_WARNING
    return _json(body)


#: 每種 state kind 的「讀不到 vs 沒結論」說明——兩者不得同形，所以要各自講清楚。
_STATE_NOTES = {
    "ranking": ("跑 `python -m webapp materialize --ranking`",
                "「artifact 讀不到」與「排不出任何一列」是兩件事——後者會以 200 ＋ top_pick=null ＋ top_pick_absent_reason 回。"),
    "beta": ("跑 `python -m webapp materialize --beta`",
             "「artifact 讀不到」與「配置算不出來」是兩件事——後者會以 200 ＋ allocation.status=unavailable ＋ 理由回。"),
}


async def _serve_state(request: Request, kind: str) -> Response:
    """跨標的 state artifact 的共用讀法：**照抄 materialize 當下的輸出**——不重排、不重算。"""
    remedy, note = _STATE_NOTES[kind]
    try:
        payload, freshness = _state(request).read(kind)
    except ArtifactUnavailable as exc:
        return _json({"error": {"kind": "artifact_unavailable", "state_kind": kind,
                                "reason": exc.reason, "remedy": remedy, "note": note}}, status=503)
    body = dict(payload)
    body["freshness"] = freshness.to_dict()
    body["correlation_warning"] = _CORRELATION_WARNING
    # 哪幾檔有單檔判讀可以點進去：只是**列目錄**（與 /stocks 同一個動作），不讀檔、不重建。
    body["analyst_view_tickers"] = _store(request).tickers()
    return _json(body)


async def ranking(request: Request) -> Response:
    """跨標的瓶頸排序（`rank_bottlenecks()` 的輸出照抄）。"""
    return await _serve_state(request, "ranking")


async def beta(request: Request) -> Response:
    """資產配置：距目標多遠、現在在什麼水位（Engine D beta monitor 的輸出照抄）。"""
    return await _serve_state(request, "beta")


async def index(request: Request) -> Response:
    return _static_file("index.html")


async def static_asset(request: Request) -> Response:
    return _static_file(request.path_params["asset"])


_ALLOWED_ASSETS = {"index.html", "app.js", "styles.css"}


def _static_file(name: str) -> Response:
    """**allowlist**，不是路徑過濾——只有這三個檔名可以被讀到，沒有 arbitrary file access。"""
    if name not in _ALLOWED_ASSETS:
        raise HTTPException(status_code=404, detail="not found")
    path = STATIC_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=500, detail="static asset missing")
    media = {"html": "text/html; charset=utf-8", "js": "text/javascript; charset=utf-8",
             "css": "text/css; charset=utf-8"}[name.rsplit(".", 1)[1]]
    response = FileResponse(path, media_type=media)
    for key, value in _SECURITY_HEADERS.items():
        response.headers[key] = value
    return response


_CORRELATION_WARNING = (
    "這份圖的組成高度集中：列出 N 檔不等於 N 個獨立機會。全買很可能是同一個賭注下 N 次，"
    "不是分散。alpha 與 beta 也不是兩個獨立風險來源。"
)


def _read_vocabularies(store: ArtifactStore) -> dict[str, Any]:
    """字彙由 materialize 端寫成 `.meta.json`；讀不到就誠實說沒有，**不在這裡補一份**。"""
    path = store.directory / ".meta.json"
    if not path.is_file():
        return {"vocabularies": None,
                "vocabularies_reason": "尚未 materialize——字彙表由 `python -m webapp materialize` 寫下，"
                                       "APP 不自己維護第二份（第二份會立刻開始偏離）"}
    try:
        return {"vocabularies": json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError):
        return {"vocabularies": None, "vocabularies_reason": "字彙檔解析失敗——請重跑 materialize"}


# ---------------------------------------------------------------------------
# error handling：固定形狀，不吐 stack trace／路徑／credential
# ---------------------------------------------------------------------------

async def http_error(request: Request, exc: Exception) -> Response:
    status = exc.status_code if isinstance(exc, HTTPException) else 500
    known = {404: "not_found", 405: "method_not_allowed", 503: "unavailable"}
    return _json({"error": {"kind": known.get(status, "error"), "status": status,
                            "message": _SAFE_MESSAGES.get(status, "request failed")}}, status=status)


async def unhandled_error(request: Request, exc: Exception) -> Response:
    """任何未預期例外都回同一個固定形狀。**不回 `str(exc)`**——它可能含路徑或查詢內容。"""
    return _json({"error": {"kind": "internal_error", "status": 500,
                            "message": "request failed"}}, status=500)


_SAFE_MESSAGES = {
    404: "not found",
    405: "method not allowed（本 API 只接受 GET／HEAD——沒有任何寫入端點）",
    503: "artifact unavailable",
}


def create_app(directory: Path | None = None, state_directory: Path | None = None) -> Starlette:
    """建立 read-only app。`methods=["GET"]` 讓任何寫入動詞在路由層就是 405。

    state 目錄不另猜：`resolve_state_dir` 是唯一規則（明示 > analyst 目錄下的 `state/` > 預設）。
    """
    routes = [
        Route("/", index, methods=["GET"]),
        Route("/static/{asset}", static_asset, methods=["GET"]),
        Route(f"/api/{API_VERSION}/health", health, methods=["GET"]),
        Route(f"/api/{API_VERSION}/meta", meta, methods=["GET"]),
        Route(f"/api/{API_VERSION}/ranking", ranking, methods=["GET"]),
        Route(f"/api/{API_VERSION}/beta", beta, methods=["GET"]),
        Route(f"/api/{API_VERSION}/stocks", stocks, methods=["GET"]),
        Route(f"/api/{API_VERSION}/stocks/{{ticker}}", stock_detail, methods=["GET"]),
    ]
    app = Starlette(routes=routes, exception_handlers={
        HTTPException: http_error, Exception: unhandled_error})
    app.state.store = ArtifactStore(directory)
    app.state.state_store = StateArtifactStore(resolve_state_dir(directory, state_directory))
    return app


def bind_host() -> str:
    """預設只綁 127.0.0.1。要綁其他介面必須明示——**外部認證邊界是 Cloudflare Access，不是本程式**。"""
    host = os.environ.get("STOCKBOT_APP_HOST", "127.0.0.1")
    if host != "127.0.0.1" and os.environ.get("STOCKBOT_APP_ALLOW_PUBLIC_BIND") != "1":
        raise RuntimeError(
            f"拒絕綁定 {host}：APP 沒有自己的帳號密碼系統，裸露 origin 等於把 private 研究內容公開。"
            "正確做法是留在 127.0.0.1 並由 Cloudflare Tunnel 轉進來（見 deploy/cloudflare/README.md）；"
            "真的要綁其他介面請明示 STOCKBOT_APP_ALLOW_PUBLIC_BIND=1。")
    return host


def bind_port() -> int:
    raw = os.environ.get("STOCKBOT_APP_PORT", "8790")
    try:
        return int(raw)
    except ValueError:
        return 8790


__all__ = ["API_VERSION", "bind_host", "bind_port", "create_app"]
