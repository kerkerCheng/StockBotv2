"""Narrow read-only Engine D helper for the remote MCP surface（Daily Approval Loop U3）。

只曝露 `decision_lab today` 既有的 redacted public DTO——不重組 payload、不繞過
redaction（plan R8／KTD3）。這是 daily brief 的決策佇列在遠端（手機／雲端）唯一
的 live 視窗，因為 Decision Store 永不進 git，無法靠 pushed clone 讀取（KTD1）。

安全：Decision Store 路徑私有（`library/private/decision_lab/`）。開 store 或產生
brief 的 exception 可能夾帶該路徑，因此錯誤只回穩定 code 與 exception 型別名，
**絕不回 str(exc)**；最終 DTO 另過一次 `assert_safe_payload` 作為 belt-and-suspenders。

⚠ **B6 起住 `briefing/` 而不是 `decision_lab/`。** 它是組裝函式（開 store、建
runtime provider、組 brief），而組裝點必須看得到所有層。留在 Engine D 裡的後果是
它成為 pq2 收集鏈上第二條繞過組裝層的路徑——而 sheet-only 持股的覆蓋分類正好在
那條鏈上（`engine_b todo sync → 這裡 → build_today_brief`），繞過去就等於持股從
待辦池靜默消失。兩條路徑收斂成一條，那個失敗模式就不存在了。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from decision_lab.action_card import assert_safe_payload

from .today import build_today_brief


def get_decision_brief_core(
    *,
    as_of: str | None = None,
    store_factory: Callable[[], Any] | None = None,
    provider_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """回傳今日 Engine D 決策 brief 的 redacted public DTO。

    純讀：不 freeze context、不建 decision、不寫任何 authority。缺 runtime 時回
    明確 `unavailable` 狀態，不洩私有路徑，也不假裝有資料。
    """

    now = as_of or datetime.now(timezone.utc).isoformat()

    if store_factory is None:
        from decision_lab.bootstrap import open_default_store

        store_factory = open_default_store
    if provider_factory is None:
        from engine_d_runtime.bootstrap import build_default_runtime_provider

        provider_factory = build_default_runtime_provider

    try:
        store = store_factory()
    except Exception as exc:
        return {
            "status": "unavailable",
            "as_of": now,
            "note": (
                "Decision Store 目前不可用（本機 runtime 未就緒）："
                f"{type(exc).__name__}"
            ),
        }

    try:
        try:
            provider = provider_factory()
        except Exception:
            provider = None

        holdings: dict[str, Any] | None = None
        if provider is not None:
            try:
                holdings = dict(provider.current_holdings(evaluation_at=now))
            except Exception:
                holdings = {"status": "unavailable"}

        brief = build_today_brief(
            store,
            as_of=now,
            current_holdings=holdings,
            provider=provider,
        )
        # build_today_brief 已對輸入 assert_safe_payload 並以 _public_company 收斂；
        # 這裡再對輸出過一次，確保沒有任何私有 path／持股明細洩漏到遠端。
        assert_safe_payload(brief)
        return brief
    except Exception as exc:
        return {
            "status": "error",
            "as_of": now,
            "note": f"today brief 產生失敗：{type(exc).__name__}",
        }
    finally:
        close = getattr(store, "close", None)
        if callable(close):
            close()
