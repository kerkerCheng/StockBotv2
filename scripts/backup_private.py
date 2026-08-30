"""Private authority 備份唯一入口（ROADMAP「private authority 備份沒有可執行入口」）。

備份對象是「今天重新取一次拿不回來」的 private authority（L10 判準）：
- Decision Store：``library/private/decision_lab/decision_lab.db``（SQLite 一致性快照）
- Engine C：``library/private/runtime_pointer.json`` 指向的 SQLite（一致性快照）
- Neo4j 圖：邏輯匯出（全部 nodes＋relationships JSON，附 counts 自我驗證）
- 其餘 private 檔案：打包 ``files.zip``（assessments、source_trace、research_actions…）

明確排除（拿得回來、暫存、或刻意不出境）：
- ``models/``（可重新下載）、``lead_media/``（ROADMAP 分類為可回復）
- ``backups/``（本模組自己的輸出）與 ``backups_verify_tmp/``（restore 驗證暫存）
- ``gdrive_oauth/``（OAuth client secret 與 refresh token——備份會上傳到 Drive，
  把開 Drive 的鑰匙放進備份等於把鑰匙鎖進它自己開的保險箱；遺失時重跑 auth 即可）
- 兩顆 live SQLite 與所有 ``-wal``/``-shm``（已由一致性快照涵蓋，直接拷貝會撕裂）

子命令：
  auth            一次性 OAuth 瀏覽器授權（Desktop client），存 refresh token
  run             跑完整備份；有 token 就上傳 Drive，沒有標 ``not_configured``
  upload          重新打包最新一份本機備份並上傳 Drive（auth 修好後補上傳用）
  verify-restore  restore 到暫存位置＋checksum／integrity 驗證（沒驗證過的備份不算備份）
  status          印出 ``last_backup.json``

Drive 上傳失敗不回滾本機備份，但 exit code 非零且寫入 status——daily brief 首屏的
「最後一次備份」計數器會現形（L14：真正的防呆是會自己出現的常駐計數器）。
refresh token 若因 consent screen 停在 Testing 模式而 7 天過期，會以
``auth_expired`` 現形，不會安靜停掉。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from decision_lab.backup import (  # noqa: E402
    BackupError,
    create_private_backup,
    restore_private_backup,
)

PRIVATE = ROOT / "library" / "private"
BACKUPS = PRIVATE / "backups"
STATUS_PATH = BACKUPS / "last_backup.json"
VERIFY_TMP = PRIVATE / "backups_verify_tmp"
OAUTH_DIR = PRIVATE / "gdrive_oauth"
CLIENT_SECRET_PATH = OAUTH_DIR / "client_secret.json"
TOKEN_PATH = OAUTH_DIR / "token.json"

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_FOLDER_NAME = "StockBotv2-backups"
DRIVE_ZIP_PREFIX = "stockbotv2_backup_"
DRIVE_RETENTION = 8
LOCAL_RETENTION = 3

# files.zip 的排除清單。頂層目錄整包排除；-wal/-shm 與 restore 暫存檔一律排除。
EXCLUDE_TOP_DIRS = {"models", "lead_media", "backups", "backups_verify_tmp", "gdrive_oauth"}
EXCLUDE_SUFFIXES = ("-wal", "-shm", ".restore.tmp", ".restore.rollback")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


def _sha256(path: Path) -> str:
    import hashlib

    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _engine_c_authority() -> Path:
    pointer = json.loads((PRIVATE / "runtime_pointer.json").read_text(encoding="utf-8"))
    relative = str(pointer["engine_c"])
    path = (PRIVATE / relative).resolve()
    if not path.is_file():
        raise BackupError(f"runtime_pointer 指向的 Engine C authority 不存在：{relative}")
    return path


# ---------------------------------------------------------------------------
# Neo4j 邏輯匯出


def export_neo4j_payload() -> dict:
    """匯出全圖 nodes＋relationships；counts 直接來自匯出結果供自我驗證。

    圖是單一 writer 的小圖（本專案 scale），全量抓進記憶體可行；
    temporal 型別以 str 序列化。密碼不落任何輸出。
    """
    from neo4j import GraphDatabase

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            nodes = [
                {
                    "id": record["id"],
                    "labels": list(record["labels"]),
                    "properties": dict(record["properties"]),
                }
                for record in session.run(
                    "MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels,"
                    " properties(n) AS properties"
                )
            ]
            relationships = [
                {
                    "id": record["id"],
                    "type": record["type"],
                    "start": record["start"],
                    "end": record["end"],
                    "properties": dict(record["properties"]),
                }
                for record in session.run(
                    "MATCH (a)-[r]->(b) RETURN elementId(r) AS id, type(r) AS type,"
                    " elementId(a) AS start, elementId(b) AS end,"
                    " properties(r) AS properties"
                )
            ]
    finally:
        driver.close()
    return {
        "exported_at": _utc_now().isoformat(),
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "nodes": nodes,
        "relationships": relationships,
    }


def verify_neo4j_export(path: Path) -> tuple[int, int]:
    """匯出檔自我一致性：宣告 counts 必須等於實際列數。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    nodes = payload.get("nodes")
    rels = payload.get("relationships")
    if not isinstance(nodes, list) or not isinstance(rels, list):
        raise BackupError("neo4j export 缺 nodes/relationships 陣列")
    if payload.get("node_count") != len(nodes) or payload.get(
        "relationship_count"
    ) != len(rels):
        raise BackupError("neo4j export 宣告 counts 與實際列數不符")
    if not nodes:
        raise BackupError("neo4j export 沒有任何節點——不像是活的圖，拒絕當作有效備份")
    return len(nodes), len(rels)


# ---------------------------------------------------------------------------
# files.zip：其餘不可回復檔案


def iter_files_zip_members(private_root: Path, live_dbs: set[Path]):
    for path in sorted(private_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(private_root)
        if rel.parts[0] in EXCLUDE_TOP_DIRS:
            continue
        if path.name.endswith(EXCLUDE_SUFFIXES):
            continue
        if path.resolve() in live_dbs:
            continue
        yield path, rel


def build_files_zip(destination: Path, live_dbs: set[Path]) -> int:
    count = 0
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, rel in iter_files_zip_members(PRIVATE, live_dbs):
            archive.write(path, rel.as_posix())
            count += 1
    if count == 0:
        raise BackupError("files.zip 沒收到任何檔案——排除清單或 private root 有問題")
    return count


def _append_manifest_entries(backup_dir: Path, filenames: list[str]) -> None:
    """把非 SQLite 產物補進 manifest，讓既有 rotation 的 checksum 驗證涵蓋它們。"""
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for filename in filenames:
        manifest["files"][filename] = {
            "filename": filename,
            "sha256": _sha256(backup_dir / filename),
        }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Google Drive（OAuth user credentials；service account 已實測無 quota，不要走回頭路）


def run_auth() -> int:
    """一次性瀏覽器授權。前置：使用者已在 Cloud Console 建 Desktop OAuth client
    並把 JSON 放到 CLIENT_SECRET_PATH；consent screen 必須發布 Production，
    否則 refresh token 7 天過期。"""
    if not CLIENT_SECRET_PATH.is_file():
        print(f"缺 OAuth client secret：{CLIENT_SECRET_PATH}")
        print("到 Google Cloud Console → 憑證 → 建立 OAuth 用戶端 ID（電腦版應用程式），")
        print("下載 JSON 後放到上面那個路徑再重跑。")
        return 1
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH), scopes=DRIVE_SCOPES
    )
    creds = flow.run_local_server(port=0)
    if not creds.refresh_token:
        print("⚠ 沒拿到 refresh token——這通常代表之前授權過；到"
              " https://myaccount.google.com/permissions 移除本 app 的存取權後重跑。")
        return 1
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"OAuth token 已存：{TOKEN_PATH}")
    print("提醒：consent screen 若停在 Testing 模式，這把 refresh token 7 天後過期。")
    return 0


def _drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), DRIVE_SCOPES)
    return build("drive", "v3", credentials=creds), creds


def _ensure_drive_folder(service) -> str:
    query = (
        f"name = '{DRIVE_FOLDER_NAME}' and mimeType ="
        " 'application/vnd.google-apps.folder' and trashed = false"
    )
    found = service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = found.get("files") or []
    if files:
        return files[0]["id"]
    created = (
        service.files()
        .create(
            body={
                "name": DRIVE_FOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        )
        .execute()
    )
    return created["id"]


def upload_backup_to_drive(zip_path: Path) -> dict:
    """上傳一份 zip 並做雲端 rotation。回傳寫進 status 的 drive dict。"""
    if not TOKEN_PATH.is_file():
        return {"status": "not_configured"}
    try:
        from google.auth.exceptions import RefreshError
    except ImportError:  # pragma: no cover - google-auth 是既有相依
        RefreshError = ()  # type: ignore[assignment]
    try:
        service, creds = _drive_service()
        folder_id = _ensure_drive_folder(service)
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(
            str(zip_path), mimetype="application/zip", resumable=True
        )
        uploaded = (
            service.files()
            .create(
                body={"name": zip_path.name, "parents": [folder_id]},
                media_body=media,
                fields="id,name,size",
            )
            .execute()
        )
        # 雲端 rotation：只動自己命名前綴的檔案，超過保留數的移到垃圾桶（30 天可救）。
        listing = (
            service.files()
            .list(
                q=(
                    f"'{folder_id}' in parents and trashed = false"
                    f" and name contains '{DRIVE_ZIP_PREFIX}'"
                ),
                fields="files(id,name,createdTime)",
                orderBy="createdTime desc",
                pageSize=100,
            )
            .execute()
        )
        trashed = []
        for stale in (listing.get("files") or [])[DRIVE_RETENTION:]:
            service.files().update(fileId=stale["id"], body={"trashed": True}).execute()
            trashed.append(stale["name"])
        # 存回可能已 refresh 的 access token；refresh token 不變。
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        return {
            "status": "uploaded",
            "file_id": uploaded["id"],
            "name": uploaded["name"],
            "bytes": int(uploaded.get("size") or 0),
            "uploaded_at": _utc_now().isoformat(),
            "rotated_out": trashed,
        }
    except RefreshError as exc:
        return {
            "status": "auth_expired",
            "error": str(exc)[:500],
            "hint": "重跑 python scripts/backup_private.py auth；若一週內重複發生，"
            "檢查 consent screen 是否停在 Testing 模式",
        }
    except Exception as exc:  # 網路／API 失敗：現形但不回滾本機備份
        return {"status": "delivery_failed", "error": str(exc)[:500]}


def _build_outer_zip(backup_dir: Path) -> Path:
    """把整個備份目錄打成單一 zip 供上傳；上傳後即刪，本機真相仍是目錄本身。"""
    zip_path = BACKUPS / f"{DRIVE_ZIP_PREFIX}{backup_dir.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(backup_dir.iterdir()):
            # 讀取 WAL 模式的快照會在旁邊長出空 -shm/-wal，不屬於備份內容。
            if path.is_file() and not path.name.endswith(EXCLUDE_SUFFIXES):
                archive.write(path, f"{backup_dir.name}/{path.name}")
    return zip_path


# ---------------------------------------------------------------------------
# status 檔（daily brief 首屏計數器的資料源）


def _load_status() -> dict:
    if not STATUS_PATH.is_file():
        return {}
    try:
        loaded = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(status, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 子命令


def run_backup(*, drive: bool = True) -> int:
    _load_env()
    decision_db = PRIVATE / "decision_lab" / "decision_lab.db"
    engine_c_db = _engine_c_authority()

    # Neo4j 先抓：它失敗就整份備份不成立，不留下「看起來完整」的部分產物。
    graph = export_neo4j_payload()

    backup_id = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    backup_dir = create_private_backup(
        sources={"decision_lab": decision_db, "engine_c": engine_c_db},
        backup_id=backup_id,
        private_root=PRIVATE,
        repo_root=ROOT,
        retention=LOCAL_RETENTION,
    )
    try:
        export_path = backup_dir / "neo4j_export.json"
        export_path.write_text(
            json.dumps(graph, ensure_ascii=False, default=str), encoding="utf-8"
        )
        nodes, rels = verify_neo4j_export(export_path)

        files_zip = backup_dir / "files.zip"
        member_count = build_files_zip(
            files_zip, live_dbs={decision_db.resolve(), engine_c_db.resolve()}
        )
        _append_manifest_entries(backup_dir, ["neo4j_export.json", "files.zip"])
    except BaseException:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise

    drive_result: dict = {"status": "skipped"}
    if drive:
        outer_zip = _build_outer_zip(backup_dir)
        try:
            drive_result = upload_backup_to_drive(outer_zip)
        finally:
            outer_zip.unlink(missing_ok=True)

    previous = _load_status()
    status = {
        "backup_id": backup_id,
        "created_at": _utc_now().isoformat(),
        "backup_dir": str(backup_dir.relative_to(PRIVATE).as_posix()),
        "artifacts": {
            name: {"sha256": _sha256(backup_dir / name), "bytes": (backup_dir / name).stat().st_size}
            for name in ("decision_lab.db", "engine_c.db", "neo4j_export.json", "files.zip")
        },
        "neo4j": {"nodes": nodes, "relationships": rels},
        "files_zip_members": member_count,
        "drive": drive_result,
        # 「至少驗證過一次 restore」的紀錄跨 run 保留；當前備份是否驗過另看 backup_id。
        "restore_verification": previous.get("restore_verification"),
    }
    _write_status(status)

    print(f"本機備份完成：{backup_dir}")
    print(f"  decision_lab.db＋engine_c.db（SQLite 快照）＋neo4j_export.json"
          f"（{nodes} nodes／{rels} rels）＋files.zip（{member_count} 檔）")
    drive_status = drive_result.get("status")
    if drive_status == "uploaded":
        print(f"Drive 上傳完成：{drive_result.get('name')}（file_id={drive_result.get('file_id')}）")
    elif drive_status == "skipped":
        print("Drive：本次明確跳過（--no-drive）")
    elif drive_status == "not_configured":
        print("Drive 🔴 未設定 OAuth——跑 python scripts/backup_private.py auth")
    else:
        print(f"Drive 🔴 {drive_status}：{drive_result.get('error', '')}")
        print(f"  修好後補上傳：python scripts/backup_private.py upload")
        return 3
    return 0


def run_upload() -> int:
    """重新打包 status 指到的最新本機備份並上傳（auth 修好後的補救路徑）。"""
    _load_env()
    status = _load_status()
    backup_rel = status.get("backup_dir")
    if not backup_rel:
        print("沒有可上傳的本機備份——先跑 run")
        return 1
    backup_dir = PRIVATE / backup_rel
    if not backup_dir.is_dir():
        print(f"status 指向的備份目錄不存在：{backup_dir}——先跑 run")
        return 1
    outer_zip = _build_outer_zip(backup_dir)
    try:
        result = upload_backup_to_drive(outer_zip)
    finally:
        outer_zip.unlink(missing_ok=True)
    status["drive"] = result
    _write_status(status)
    if result.get("status") == "uploaded":
        print(f"Drive 上傳完成：{result.get('name')}（file_id={result.get('file_id')}）")
        return 0
    print(f"Drive 🔴 {result.get('status')}：{result.get('error', '')}")
    return 3


def _table_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
                " AND name NOT LIKE 'sqlite_%'"
            )
        ]
        return {
            table: conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }
    finally:
        conn.close()


def run_verify_restore() -> int:
    """把最新備份 restore 到暫存位置並驗證。驗證面：
    ① restore 路徑本身會重驗 manifest 全部 checksum（含 neo4j export 與 files.zip）；
    ② restore 出來的 SQLite 過 integrity_check（restore 內建）＋逐表筆數與備份一致；
    ③ files.zip 全成員 CRC；④ neo4j export counts 自我一致。"""
    status = _load_status()
    backup_rel = status.get("backup_dir")
    if not backup_rel:
        print("沒有備份可驗——先跑 run")
        return 1
    backup_dir = PRIVATE / backup_rel
    if VERIFY_TMP.exists():
        shutil.rmtree(VERIFY_TMP)
    VERIFY_TMP.mkdir(parents=True)
    try:
        targets = {
            "decision_lab": VERIFY_TMP / "decision_lab.db",
            "engine_c": VERIFY_TMP / "engine_c.db",
        }
        restore_private_backup(
            backup_dir, targets=targets, private_root=PRIVATE, repo_root=ROOT
        )
        for name, restored in targets.items():
            original = backup_dir / f"{name}.db"
            restored_counts = _table_counts(restored)
            original_counts = _table_counts(original)
            if restored_counts != original_counts:
                raise BackupError(f"restore 後逐表筆數不一致：{name}")
            print(f"  {name}：restore＋integrity ok，"
                  f"{sum(restored_counts.values())} rows／{len(restored_counts)} tables")
        with zipfile.ZipFile(backup_dir / "files.zip") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise BackupError(f"files.zip CRC 失敗：{bad}")
            print(f"  files.zip：{len(archive.namelist())} 成員 CRC ok")
        nodes, rels = verify_neo4j_export(backup_dir / "neo4j_export.json")
        print(f"  neo4j_export.json：{nodes} nodes／{rels} rels counts 一致")
    finally:
        shutil.rmtree(VERIFY_TMP, ignore_errors=True)
    status["restore_verification"] = {
        "backup_id": status.get("backup_id"),
        "verified_at": _utc_now().isoformat(),
    }
    _write_status(status)
    print(f"restore 驗證完成：{status.get('backup_id')}")
    return 0


def run_status() -> int:
    status = _load_status()
    if not status:
        print("從未備份（library/private/backups/last_backup.json 不存在或無法解讀）")
        return 1
    print(json.dumps(status, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("auth", help="一次性 OAuth 瀏覽器授權")
    run_parser = sub.add_parser("run", help="跑完整備份（預設含 Drive 上傳）")
    run_parser.add_argument(
        "--no-drive", action="store_true", help="只做本機備份，明確跳過 Drive"
    )
    sub.add_parser("upload", help="重新上傳最新一份本機備份")
    sub.add_parser("verify-restore", help="restore 到暫存位置並驗證 checksum")
    sub.add_parser("status", help="印出 last_backup.json")
    args = parser.parse_args(argv)
    if args.command == "auth":
        return run_auth()
    if args.command == "run":
        return run_backup(drive=not args.no_drive)
    if args.command == "upload":
        return run_upload()
    if args.command == "verify-restore":
        return run_verify_restore()
    return run_status()


if __name__ == "__main__":
    raise SystemExit(main())
