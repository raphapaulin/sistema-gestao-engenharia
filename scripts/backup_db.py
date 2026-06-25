import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _sqlite_path_from_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None

    raw_path = database_url.removeprefix("sqlite:///")
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def main() -> None:
    _load_env_file()
    parser = argparse.ArgumentParser(description="Cria backup do banco SQLite.")
    parser.add_argument(
        "--database",
        help="Caminho do banco SQLite. Se omitido, usa DATABASE_URL ou data/demo.db.",
    )
    parser.add_argument(
        "--output-dir",
        default="backups",
        help="Pasta de destino dos backups. Padrão: backups",
    )
    args = parser.parse_args()

    if args.database:
        source_path = Path(args.database)
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path
    else:
        database_url = os.getenv("DATABASE_URL", "sqlite:///data/demo.db")
        source_path = _sqlite_path_from_url(database_url)

    if source_path is None:
        raise SystemExit("Backup automático disponível apenas para SQLite.")
    if not source_path.exists():
        raise SystemExit(f"Banco não encontrado: {source_path}")

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = output_dir / f"backup_{timestamp}.db"

    with sqlite3.connect(source_path) as source:
        with sqlite3.connect(backup_path) as destination:
            source.backup(destination)

    print(f"Backup criado com sucesso: {backup_path}")


if __name__ == "__main__":
    main()
