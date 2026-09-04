"""`python -m alpha <sub>` 的每個子命令都必須真的派得出去。

## 為什麼需要這一支（2026-09-04）

`alpha audit invariants` 從 commit `5b11c85` 寫下起，**每一次呼叫都是
ModuleNotFoundError**——它 import 的 `alpha.audit` 在同一輪重構裡已被搬到
top-level `audit/`，而 caller 沒跟著改。它活了下來的原因很簡單：

- handler 是 `lambda a: __import__("alpha.audit", ...)`，**import 錯誤要到呼叫
  當下才會發生**，parser 建得起來、`--help` 印得出來、任何只驗「子命令存在」的
  測試都會綠。
- 沒有任何測試呼叫過它。

這是 L13 的標準形狀：**元件會動 ≠ 端到端有產出**。`--help` 列得出 `audit`
這一項，正是那個「成功與失敗同形」的訊號——使用者看到它以為這條路通。

⚠ 修法不是把 import 改指 `audit`：`tests/test_layer_separation.py::
test_nothing_imports_audit` 守著「`audit/` 站在所有層之上、不被任何層 import」，
改指過去會在 runtime 反轉那個依賴方向。所以 `alpha audit` 只指路、不執行。
"""
from __future__ import annotations

import argparse
import types

import pytest

from alpha import cli


def _subcommand_actions(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:  # noqa: SLF001 — argparse 沒有公開 API 列子命令
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return dict(action.choices)
    raise AssertionError("alpha CLI 應該有子命令")


def test_every_subcommand_handler_is_a_named_function_in_this_module() -> None:
    """**handler 一律是 `alpha.cli` 裡的具名函式，不得是 lazy `__import__` 的 lambda。**

    這條擋的不是風格，是**延後到呼叫當下才會炸的 import**——那正是 `alpha audit`
    壞了整段時間沒人發現的機制。具名函式在 import `alpha.cli` 的當下就必須存在。

    空跑檢查：把 `audit.set_defaults` 改回
    `lambda a: __import__("alpha.audit", fromlist=["main"]).main([])` → 這條會紅。
    """
    offenders: list[str] = []
    for name, sub in _subcommand_actions(cli.build_parser()).items():
        func = sub.get_default("func")
        assert func is not None, f"子命令 {name} 沒有 handler"
        if not isinstance(func, types.FunctionType) or func.__name__ == "<lambda>":
            offenders.append(f"{name} → {func!r}（lambda／非具名函式）")
            continue
        if getattr(func, "__module__", None) != cli.__name__:
            offenders.append(f"{name} → {func.__module__}.{func.__name__}（不在 alpha.cli）")
    assert not offenders, (
        "子命令 handler 必須是 alpha.cli 的具名函式，否則 import 錯誤會延後到呼叫當下：\n"
        + "\n".join(offenders)
    )


def test_audit_subcommand_redirects_instead_of_crashing(capsys: pytest.CaptureFixture[str]) -> None:
    """`alpha audit invariants` 必須**明確指路並 fail**，不得 traceback。

    非零回傳值是刻意的：它是「你跑錯入口了」，不是「audit 通過了」——
    兩者在同一個訊號上同形就是 L13 記過的坑。
    """
    rc = cli.main(["audit", "invariants"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "python -m audit invariants" in err


def test_the_moved_audit_package_is_the_one_that_actually_exists() -> None:
    """指路指的那個入口要真的在——否則只是把死路換個講法。

    只驗 import 得到與有 `main`，**不實跑**：真正的 audit 要連 Neo4j
    與 private authority，那是收尾驗證的事，不是單元測試的事。
    """
    import audit

    assert callable(audit.main)
    with pytest.raises(ModuleNotFoundError):
        __import__("alpha.audit")
