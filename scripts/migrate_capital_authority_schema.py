"""把 Capital Authority 收斂為 cash floor＋貸款兩列。

Apply 前備份舊表的公式版與值版到 ignored ``library/private/gsheets_backups``；
只修改 ``Capital Authority`` tab，不碰 Portfolio 或其他工作表。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fetchers.gsheets import CAPITAL_AUTHORITY_HEADERS


WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
OLD_HEADERS = (
    "record_id",
    "as_of",
    "confirmation_status",
    "capital_type",
    "description",
    "currency",
    "limit_amount",
    "drawn_amount",
    "annual_rate_pct",
    "rate_status",
    "interest_accrual",
    "availability",
    "collateral",
    "maturity",
    "include_in_net_investable_capital",
    "include_in_deployable_cash",
    "source",
    "notes",
    "facility_term_years",
    "repayment_structure",
    "minimum_payment_status",
    "minimum_payment_terms",
    "amount",
    "amount_source",
    "allowed_asset_scope",
    "deployment_mode",
    "tranche_policy",
    "automatic_deployment",
)


def _rows_as_records(rows: Sequence[Sequence[Any]], headers: Sequence[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        padded = list(row) + [""] * (len(headers) - len(row))
        if not any(str(value).strip() for value in padded):
            continue
        records.append(dict(zip(headers, padded)))
    return records


def _normalized_cells(rows: Sequence[Sequence[Any]], width: int) -> list[list[str]]:
    normalized: list[list[str]] = []
    for row in rows:
        padded = list(row) + [""] * (width - len(row))
        cells: list[str] = []
        for value in padded[:width]:
            if isinstance(value, bool):
                cells.append("TRUE" if value else "FALSE")
            elif isinstance(value, (int, float)):
                cells.append(format(value, ".15g"))
            else:
                cells.append(str(value or ""))
        normalized.append(cells)
    return normalized


def build_migration_matrix(rows: Sequence[Sequence[Any]]) -> Mapping[str, Any]:
    if not rows:
        raise ValueError("Capital Authority 工作表是空的")
    headers = tuple(str(value).strip().lower() for value in rows[0])
    if headers == CAPITAL_AUTHORITY_HEADERS:
        return {"already_migrated": True, "matrix": [list(row) for row in rows]}
    if headers != OLD_HEADERS:
        raise ValueError("Capital Authority 既不是舊 schema，也不是 shared-cash-pool schema")

    records = _rows_as_records(rows, headers)
    floors = [row for row in records if row.get("capital_type") == "operating_floor"]
    credits = [
        row
        for row in records
        if row.get("capital_type") == "contingent_liquidity_credit_facility"
    ]
    if len(floors) != 1:
        raise ValueError("舊表必須剛好有一筆 operating_floor 才能遷移")
    if not credits:
        raise ValueError("舊表缺少貸款額度列，拒絕猜測")

    floor = floors[0]
    matrix: list[list[Any]] = [list(CAPITAL_AUTHORITY_HEADERS)]
    matrix.append(
        [
            str(floor.get("record_id") or "cash_floor_01").replace("operating_floor", "cash_floor"),
            floor.get("as_of", ""),
            "cash_floor",
            floor.get("currency", ""),
            floor.get("amount", ""),
            "",
            "",
            "",
            "",
            "",
            "",
            "Cash floor 以下不投資；以上全部為 Alpha／Beta 共用可投資現金。",
        ]
    )
    for credit in credits:
        matrix.append(
            [
                credit.get("record_id", ""),
                credit.get("as_of", ""),
                "credit_facility",
                credit.get("currency", ""),
                "",
                credit.get("limit_amount", ""),
                credit.get("drawn_amount", ""),
                credit.get("annual_rate_pct", ""),
                credit.get("interest_accrual", ""),
                credit.get("facility_term_years", ""),
                credit.get("repayment_structure", ""),
                "貸款不算自有現金；提款金額、標的與批次另案人工核准並另計利息。",
            ]
        )
    return {
        "already_migrated": False,
        "matrix": matrix,
        "before_rows": len(records),
        "after_rows": len(matrix) - 1,
        "before_columns": len(headers),
        "after_columns": len(CAPITAL_AUTHORITY_HEADERS),
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
    path = backup_dir / f"capital_authority_{stamp}.json"
    payload = {
        "schema_version": "1",
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
        "sheet_name": sheet_name,
        "formula_rows": formula_rows,
        "value_rows": value_rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _sheet_properties(service, spreadsheet_id: str, sheet_name: str) -> Mapping[str, Any]:
    metadata = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(sheetId,title,gridProperties))",
        )
        .execute()
    )
    matches = [
        sheet["properties"]
        for sheet in metadata.get("sheets", [])
        if sheet.get("properties", {}).get("title") == sheet_name
    ]
    if len(matches) != 1:
        raise ValueError(f"找不到唯一的工作表：{sheet_name}")
    return matches[0]


def migrate(*, apply: bool) -> Mapping[str, Any]:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    spreadsheet_id = os.environ.get("GSHEETS_SPREADSHEET_ID", "")
    service_account_file = os.environ.get("GSHEETS_SERVICE_ACCOUNT_JSON", "")
    sheet_name = os.environ.get("GSHEETS_CAPITAL_SHEET_NAME", "Capital Authority")
    if not spreadsheet_id or not service_account_file:
        raise ValueError("缺少 GSHEETS_SPREADSHEET_ID 或 GSHEETS_SERVICE_ACCOUNT_JSON")

    service = _service(service_account_file)
    properties = _sheet_properties(service, spreadsheet_id, sheet_name)
    sheet_id = int(properties["sheetId"])
    column_count = int(properties.get("gridProperties", {}).get("columnCount", 0))
    old_range = f"{sheet_name}!A:{'L' if column_count <= 12 else 'AB'}"
    formula_rows = _read(service, spreadsheet_id, old_range, "FORMULA")
    plan = build_migration_matrix(formula_rows)
    if plan["already_migrated"]:
        return {
            "status": "already_migrated",
            "sheet": sheet_name,
            "rows": max(len(formula_rows) - 1, 0),
            "columns": column_count,
        }
    if not apply:
        return {
            "status": "dry_run",
            "sheet": sheet_name,
            "before_rows": plan["before_rows"],
            "after_rows": plan["after_rows"],
            "before_columns": plan["before_columns"],
            "after_columns": plan["after_columns"],
        }

    value_rows = _read(service, spreadsheet_id, old_range, "UNFORMATTED_VALUE")
    backup_path = _backup(
        sheet_name=sheet_name,
        formula_rows=formula_rows,
        value_rows=value_rows,
    )
    (
        service.spreadsheets()
        .values()
        .clear(spreadsheetId=spreadsheet_id, range=old_range, body={})
        .execute()
    )
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:L{len(plan['matrix'])}",
            valueInputOption="USER_ENTERED",
            body={"values": plan["matrix"]},
        )
        .execute()
    )

    requests: list[dict[str, Any]] = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(CAPITAL_AUTHORITY_HEADERS),
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.88, "green": 0.93, "blue": 0.98},
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat.bold)",
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": len(CAPITAL_AUTHORITY_HEADERS),
                }
            }
        },
    ]
    if column_count > len(CAPITAL_AUTHORITY_HEADERS):
        requests.insert(
            0,
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": len(CAPITAL_AUTHORITY_HEADERS),
                        "endIndex": column_count,
                    }
                }
            },
        )
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    target_range = f"{sheet_name}!A1:L{len(plan['matrix'])}"
    after = _read(service, spreadsheet_id, target_range, "FORMULA")
    width = len(CAPITAL_AUTHORITY_HEADERS)
    if _normalized_cells(after, width) != _normalized_cells(plan["matrix"], width):
        raise RuntimeError(f"遷移後 read-back 不一致；請用備份復核：{backup_path}")
    return {
        "status": "migrated",
        "sheet": sheet_name,
        "rows": len(plan["matrix"]) - 1,
        "columns": len(CAPITAL_AUTHORITY_HEADERS),
        "backup": str(backup_path),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="備份後實際精簡 Capital Authority")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(migrate(apply=args.apply), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
