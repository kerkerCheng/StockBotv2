"""為既有 Portfolio Sheet 新增 Engine D canonical mark-to-market 欄位。

只在現有欄位右側新增三個衍生欄位，所有 market value 直接引用既有
``market_usd``；不修改既有儲存格。Apply 前會把公式版與值版 snapshot 備份到
ignored ``library/private/gsheets_backups``。
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
CANONICAL_HEADERS = ("market_value_base", "nav_base", "base_currency")
WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def column_letter(index: int) -> str:
    """Zero-based column index → Google Sheets A1 column letters。"""
    if index < 0:
        raise ValueError("column index 必須非負")
    result = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(65 + remainder) + result
    return result


def build_update_matrix(rows: Sequence[Sequence[Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Portfolio Sheet 是空的")
    headers = [str(value).strip().lower() for value in rows[0]]
    if "market_usd" not in headers:
        raise ValueError("現有 Sheet 缺少 market_usd，不能做等值遷移")
    present = [header for header in CANONICAL_HEADERS if header in headers]
    if present:
        if len(present) == len(CANONICAL_HEADERS):
            return {"already_migrated": True, "headers": headers}
        raise ValueError("canonical operational 欄位只存在一部分，拒絕覆寫")

    first_new_index = len(headers)
    market_col = column_letter(headers.index("market_usd"))
    last_row = len(rows)
    matrix: list[list[Any]] = [list(CANONICAL_HEADERS)]
    for row_number in range(2, last_row + 1):
        matrix.append([
            f"={market_col}{row_number}",
            f"=SUM(${market_col}$2:${market_col}${last_row})",
            "USD",
        ])
    return {
        "already_migrated": False,
        "headers": headers,
        "matrix": matrix,
        "start_col": column_letter(first_new_index),
        "end_col": column_letter(first_new_index + len(CANONICAL_HEADERS) - 1),
        "existing_end_col": column_letter(len(headers) - 1),
        "last_row": last_row,
    }


def _service(service_account_file: str):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=[WRITE_SCOPE],
    )
    return build("sheets", "v4", credentials=credentials)


def _read(service, spreadsheet_id: str, range_name: str, render: str) -> list[list[Any]]:
    response = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption=render,
        )
        .execute()
    )
    return response.get("values", [])


def _backup(
    *,
    sheet_name: str,
    formula_rows: Sequence[Sequence[Any]],
    value_rows: Sequence[Sequence[Any]],
) -> Path:
    backup_dir = ROOT / "library" / "private" / "gsheets_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"portfolio_{stamp}.json"
    payload = {
        "schema_version": "1",
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
        "sheet_name": sheet_name,
        "formula_rows": formula_rows,
        "value_rows": value_rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def migrate(*, apply: bool) -> Mapping[str, Any]:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    spreadsheet_id = os.environ.get("GSHEETS_SPREADSHEET_ID", "")
    service_account_file = os.environ.get("GSHEETS_SERVICE_ACCOUNT_JSON", "")
    sheet_name = os.environ.get("GSHEETS_SHEET_NAME", "Portfolio")
    if not spreadsheet_id or not service_account_file:
        raise ValueError("缺少 GSHEETS_SPREADSHEET_ID 或 GSHEETS_SERVICE_ACCOUNT_JSON")

    service = _service(service_account_file)
    full_range = f"{sheet_name}!A:Z"
    formula_rows = _read(service, spreadsheet_id, full_range, "FORMULA")
    plan = build_update_matrix(formula_rows)
    if plan["already_migrated"]:
        return {"status": "already_migrated", "sheet": sheet_name}
    target_range = (
        f"{sheet_name}!{plan['start_col']}1:{plan['end_col']}{plan['last_row']}"
    )
    if not apply:
        return {
            "status": "dry_run",
            "sheet": sheet_name,
            "target_range": target_range,
            "rows": plan["last_row"] - 1,
        }

    value_rows = _read(service, spreadsheet_id, full_range, "UNFORMATTED_VALUE")
    backup_path = _backup(
        sheet_name=sheet_name,
        formula_rows=formula_rows,
        value_rows=value_rows,
    )
    existing_range = (
        f"{sheet_name}!A1:{plan['existing_end_col']}{plan['last_row']}"
    )
    existing_before = _read(service, spreadsheet_id, existing_range, "FORMULA")
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=target_range,
            valueInputOption="USER_ENTERED",
            body={"values": plan["matrix"]},
        )
        .execute()
    )
    existing_after = _read(service, spreadsheet_id, existing_range, "FORMULA")
    if existing_after != existing_before:
        raise RuntimeError(
            f"既有欄位在遷移期間發生變化；請用備份復核：{backup_path}"
        )
    canonical_after = _read(service, spreadsheet_id, target_range, "FORMULA")
    if canonical_after != plan["matrix"]:
        raise RuntimeError(
            f"canonical 公式驗證失敗；請用備份復核：{backup_path}"
        )
    return {
        "status": "migrated",
        "sheet": sheet_name,
        "target_range": target_range,
        "rows": plan["last_row"] - 1,
        "backup": str(backup_path),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="備份後實際新增 canonical 欄位")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(migrate(apply=args.apply), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
