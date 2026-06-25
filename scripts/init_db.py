import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _database_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inicializa um banco SQLite limpo com o schema do sistema."
    )
    parser.add_argument(
        "--database",
        default="data/demo.db",
        help="Caminho do banco SQLite a ser criado. Padrao: data/demo.db",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove o banco existente antes de recriar. Use com cuidado.",
    )
    args = parser.parse_args()

    database_path = Path(args.database)
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    if database_path.exists() and not args.force:
        raise SystemExit(
            f"Banco já existe: {database_path}\n"
            "Use outro caminho ou rode com --force se tiver certeza."
        )

    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists() and args.force:
        database_path.unlink()

    os.environ["DATABASE_URL"] = _database_url(database_path)

    from backend.database import init_db

    init_db()
    print(f"Banco inicializado com sucesso: {database_path}")


if __name__ == "__main__":
    main()
