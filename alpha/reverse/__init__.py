"""Reverse Bridge：從現價反推市場隱含的營運假設（ROADMAP Post-MVP Alpha Edge §B）。

正向的 `alpha/fundamental` 問「我們的假設推出什麼 EPS」；這裡問**反過來的那題**：
「現價要成立，某個 driver 必須是多少」。它不新增任何倍數自由度，也不需要 peer 樣本。
"""
from .contracts import (
    EQUAL_REL_TOL, REVERSE_STATUSES, SOLVE_STATUSES, DriverSolution, ReverseBridgeResult,
)
from .model import build_reverse_bridge, solve_driver

__all__ = ["EQUAL_REL_TOL", "REVERSE_STATUSES", "SOLVE_STATUSES", "DriverSolution",
           "ReverseBridgeResult", "build_reverse_bridge", "solve_driver"]
