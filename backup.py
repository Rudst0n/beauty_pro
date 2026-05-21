from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"
DEFAULT_UPLOADS_DIR = PROJECT_ROOT / "app" / "static" / "uploads"
DEFAULT_SQLITE_DB = PROJECT_ROOT / "instance" / "beauty_catalog.db"


def load_env_file(env_path: Path) -> None:
    """Carrega variáveis simples do .env sem depender de biblioteca externa."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def sqlite_path_from_database_url(database_url: str | None) -> Path | None:
    if not database_url:
        return None

    if not database_url.startswith("sqlite:///"):
        return None

    raw_path = database_url.replace("sqlite:///", "", 1)
    raw_path = unquote(raw_path)

    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    return db_path.resolve()


def resolve_database_path(custom_db: str | None = None) -> Path:
    if custom_db:
        return Path(custom_db).resolve()

    load_env_file(PROJECT_ROOT / ".env")
    db_from_env = sqlite_path_from_database_url(os.getenv("DATABASE_URL"))

    if db_from_env:
        return db_from_env

    return DEFAULT_SQLITE_DB.resolve()


def validate_sqlite_database(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"Banco de dados não encontrado: {db_path}")

    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        connection.execute("PRAGMA schema_version;").fetchone()
        connection.close()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Arquivo encontrado, mas não parece ser um SQLite válido: {db_path}") from exc


def add_file_to_zip(zip_file: zipfile.ZipFile, source: Path, destination: str) -> None:
    if source.exists() and source.is_file():
        zip_file.write(source, destination)


def add_directory_to_zip(zip_file: zipfile.ZipFile, directory: Path, destination_prefix: str) -> int:
    if not directory.exists() or not directory.is_dir():
        return 0

    total_files = 0
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(directory)
            zip_file.write(file_path, str(Path(destination_prefix) / relative_path))
            total_files += 1

    return total_files


def remove_old_backups(backup_dir: Path, keep: int) -> None:
    if keep <= 0:
        return

    backups = sorted(
        backup_dir.glob("beauty_pro_backup_*.zip"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[keep:]:
        old_backup.unlink(missing_ok=True)


def create_backup(
    db_path: Path,
    uploads_dir: Path,
    backup_dir: Path,
    keep: int,
) -> Path:
    validate_sqlite_database(db_path)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"beauty_pro_backup_{timestamp}.zip"

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        db_copy = temp_dir / db_path.name
        shutil.copy2(db_path, db_copy)

        metadata = {
            "project": "Beauty Pro",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "database_source": str(db_path),
            "uploads_source": str(uploads_dir),
            "contains_env_file": False,
            "contains_venv": False,
        }

        metadata_file = temp_dir / "backup_info.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            add_file_to_zip(zip_file, db_copy, f"database/{db_path.name}")
            uploaded_files = add_directory_to_zip(zip_file, uploads_dir, "uploads")
            add_file_to_zip(zip_file, metadata_file, "backup_info.json")

    remove_old_backups(backup_dir, keep)

    print("Backup criado com sucesso.")
    print(f"Arquivo: {backup_path}")
    print(f"Banco: {db_path}")
    print(f"Uploads: {uploads_dir if uploads_dir.exists() else 'pasta não encontrada'}")
    print(f"Manter últimos backups: {keep}")

    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera backup do Beauty Pro.")
    parser.add_argument("--db", help="Caminho do banco SQLite. Padrão: instance/beauty_catalog.db")
    parser.add_argument("--uploads", default=str(DEFAULT_UPLOADS_DIR), help="Pasta de uploads. Padrão: app/static/uploads")
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Pasta de destino dos backups. Padrão: backups")
    parser.add_argument("--keep", type=int, default=10, help="Quantidade de backups antigos para manter. Padrão: 10")

    args = parser.parse_args()

    try:
        db_path = resolve_database_path(args.db)
        uploads_dir = Path(args.uploads).resolve()
        backup_dir = Path(args.backup_dir).resolve()
        create_backup(db_path, uploads_dir, backup_dir, args.keep)
        return 0
    except Exception as exc:
        print(f"Erro ao gerar backup: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
