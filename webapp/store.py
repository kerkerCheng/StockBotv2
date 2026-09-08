"""Artifact store：atomic write ＋ fail-closed read。**本檔不 import 任何模型模組。**

這是 serve 端唯一碰到的 I/O。它只會做三件事：列目錄、讀檔、解析 JSON。
沒有 DB 連線、沒有 HTTP client、沒有 LLM、沒有寫入端點（`write()` 只給 materialize 用，
而 materialize 不在 request path 上——`tests/test_webapp_request_path.py` 逐條守著）。
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from .contracts import (
    STATE_KINDS, ArtifactUnavailable, Freshness, freshness_of, validate_artifact,
    validate_state_artifact,
)

_ROOT = Path(__file__).resolve().parents[1]

#: artifact 住在 **ignored** 的 `library/private/` 底下——它是由 private ledger 導出的衍生物，
#: 進 Git 等於把 private authority 的內容推上去。`.gitignore` 的 `library/private/` 涵蓋它。
DEFAULT_APP_DIR = _ROOT / "library" / "private" / "app"
DEFAULT_ARTIFACT_DIR = DEFAULT_APP_DIR / "analyst_view"
#: 跨標的的 state artifact（ranking／…）住 analyst view 的**旁邊**，不混在同一個目錄：
#: 它們不是股票，`tickers()` 不該看到它們，而且每種 kind 只有一份。
DEFAULT_STATE_DIR = DEFAULT_APP_DIR / "state"


def artifact_dir() -> Path:
    """artifact 目錄。`STOCKBOT_APP_ARTIFACT_DIR` 可覆寫（測試與多視角快照用）。"""
    raw = os.environ.get("STOCKBOT_APP_ARTIFACT_DIR")
    return Path(raw) if raw else DEFAULT_ARTIFACT_DIR


def state_dir() -> Path:
    """state artifact 目錄。`STOCKBOT_APP_STATE_DIR` 可覆寫。"""
    raw = os.environ.get("STOCKBOT_APP_STATE_DIR")
    return Path(raw) if raw else DEFAULT_STATE_DIR


def resolve_state_dir(analyst_dir: Path | None, explicit: Path | None) -> Path:
    """state 目錄的**唯一**解析規則（serve、materialize、status 都走這一條，不各自猜）：

    1. 明示的 state 目錄 → 用它；
    2. 否則若 analyst view 目錄被明示（`--dir`、測試的 tmp dir）→ 用它底下的 `state/`。
       這讓「指了一個 analyst 目錄」自動隔離：測試與 `--dir` 快照不會讀到真實機器上的 state；
    3. 否則 → 環境變數／預設（`library/private/app/state`）。
    """
    if explicit is not None:
        return Path(explicit)
    if analyst_dir is not None:
        return Path(analyst_dir) / "state"
    return state_dir()


def _safe_slug(ticker: str) -> str:
    """ticker → 檔名。**只允許已知安全字元**——這是 arbitrary file access 的第一道閘門。

    ⚠ 不是「過濾掉危險字元」而是「只放行安全字元」：前者要窮舉攻擊面，後者不用。
    """
    slug = "".join(ch for ch in ticker.strip().upper() if ch.isalnum() or ch in "._-")
    if not slug or slug != ticker.strip().upper() or slug.startswith(".") or ".." in slug:
        raise ArtifactUnavailable(ticker, "ticker 含不允許的字元——只接受英數與 . _ -")
    return slug


class ArtifactStore:
    """一個目錄裡的 materialized artifacts。"""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory is not None else artifact_dir()

    # ---- read path（HTTP request 只會走到這裡）---------------------------------

    def path_for(self, ticker: str) -> Path:
        path = (self.directory / f"{_safe_slug(ticker)}.json").resolve()
        root = self.directory.resolve()
        # 第二道閘門：解析後仍必須在目錄底下。slug 已經擋掉 `..`，這裡擋掉 symlink 逃逸。
        if root not in path.parents:
            raise ArtifactUnavailable(ticker, "artifact 路徑逃出 artifact 目錄——拒絕")
        return path

    def tickers(self) -> list[str]:
        if not self.directory.is_dir():
            return []
        # `.meta.json`（字彙表）與寫入中的 `.<name>.tmp` 都以點開頭——它們不是股票。
        return sorted(p.stem for p in self.directory.glob("*.json")
                      if p.is_file() and not p.name.startswith("."))

    def read(self, ticker: str) -> tuple[Mapping[str, Any], Freshness]:
        """讀一份 artifact。任何不完整／版本不符／digest 不合都 raise——**不回半份、不重建**。"""
        path = self.path_for(ticker)
        if not path.is_file():
            raise ArtifactUnavailable(ticker, "尚未 materialize（請跑 `python -m webapp materialize`）")
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ArtifactUnavailable(ticker, f"artifact 讀取失敗：{type(exc).__name__}") from None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ArtifactUnavailable(ticker, f"artifact JSON 解析失敗（行 {exc.lineno}）——很可能是半份寫入") from None
        payload = validate_artifact(ticker, payload)
        generated = _parse_instant(payload.get("generated_at"))
        if generated is None:
            raise ArtifactUnavailable(ticker, "artifact 的 generated_at 不是合法時戳")
        return payload, freshness_of(generated)

    def read_all(self) -> Iterator[tuple[str, Mapping[str, Any] | None, Freshness | None, str | None]]:
        """全部 artifact。壞掉的**不靜默丟棄**——以 `(ticker, None, None, reason)` 現形（INV-3）。"""
        for ticker in self.tickers():
            try:
                payload, freshness = self.read(ticker)
            except ArtifactUnavailable as exc:
                yield ticker, None, None, exc.reason
            else:
                yield ticker, payload, freshness, None

    # ---- write path（只有 materialize 會呼叫；**不在 request path 上**）----------

    def write(self, payload: Mapping[str, Any]) -> Path:
        """atomic write：先寫暫存檔再 `os.replace`。讀取端永遠看不到半份 JSON。"""
        ticker = str(payload.get("ticker") or "")
        path = self.path_for(ticker)
        _atomic_write(self.directory, path, payload)
        return path


def _atomic_write(directory: Path, path: Path, payload: Mapping[str, Any]) -> None:
    """先寫暫存檔再 `os.replace`。讀取端永遠看不到半份 JSON。兩個 store 共用這一份。"""
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(directory), prefix=f".{path.stem}.", suffix=".tmp",
        delete=False, newline="\n")
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


class StateArtifactStore:
    """跨標的的 state artifact（每種 kind 一份）。與 `ArtifactStore` 同一套讀寫紀律：
    atomic write、fail-closed read、stale 只是狀態、**request path 絕不重建**。"""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory is not None else state_dir()

    def path_for(self, kind: str) -> Path:
        # kind 是封閉字彙（`contracts.STATE_KINDS`），所以檔名不需要 slug 過濾：不在字彙裡就拒絕。
        if kind not in STATE_KINDS:
            raise ArtifactUnavailable(kind, f"未登記的 state kind {kind!r}——封閉字彙只有 {list(STATE_KINDS)}")
        return self.directory / f"{kind}.json"

    def kinds(self) -> list[str]:
        """目前**存在檔案**的 kind。缺席的由 `missing_kinds()` 現形，不混在一起。"""
        return [kind for kind in STATE_KINDS if self.path_for(kind).is_file()]

    def missing_kinds(self) -> list[str]:
        return [kind for kind in STATE_KINDS if not self.path_for(kind).is_file()]

    def read(self, kind: str) -> tuple[Mapping[str, Any], Freshness]:
        path = self.path_for(kind)
        if not path.is_file():
            raise ArtifactUnavailable(kind, f"尚未 materialize（請跑 `python -m webapp materialize --{kind}`）")
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ArtifactUnavailable(kind, f"artifact 讀取失敗：{type(exc).__name__}") from None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ArtifactUnavailable(kind, f"artifact JSON 解析失敗（行 {exc.lineno}）——很可能是半份寫入") from None
        payload = validate_state_artifact(kind, payload)
        generated = _parse_instant(payload.get("generated_at"))
        if generated is None:
            raise ArtifactUnavailable(kind, "artifact 的 generated_at 不是合法時戳")
        return payload, freshness_of(generated)

    def read_all(self) -> Iterator[tuple[str, Mapping[str, Any] | None, Freshness | None, str | None]]:
        """存在檔案的每一種 kind。壞掉的**不靜默丟棄**（INV-3）。"""
        for kind in self.kinds():
            try:
                payload, freshness = self.read(kind)
            except ArtifactUnavailable as exc:
                yield kind, None, None, exc.reason
            else:
                yield kind, payload, freshness, None

    def write(self, payload: Mapping[str, Any]) -> Path:
        """只有 materialize 會呼叫；**不在 request path 上**。"""
        path = self.path_for(str(payload.get("kind") or ""))
        _atomic_write(self.directory, path, payload)
        return path


def _parse_instant(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


__all__ = ["ArtifactStore", "DEFAULT_APP_DIR", "DEFAULT_ARTIFACT_DIR", "DEFAULT_STATE_DIR",
           "StateArtifactStore", "artifact_dir", "resolve_state_dir", "state_dir"]
