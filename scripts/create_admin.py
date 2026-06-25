import argparse
import getpass
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _database_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria um usuário administrador.")
    parser.add_argument("--nome", default="Administrador", help="Nome do usuário.")
    parser.add_argument("--email", required=True, help="E-mail de login.")
    parser.add_argument(
        "--perfil",
        default="Administrador",
        choices=["Administrador", "Colaborador", "Visualizador"],
        help="Perfil do usuário.",
    )
    parser.add_argument(
        "--database",
        help="Caminho do banco SQLite. Se informado, define DATABASE_URL para este comando.",
    )
    parser.add_argument(
        "--password",
        help="Senha inicial. Se omitida, usa ADMIN_PASSWORD ou solicita no terminal.",
    )
    args = parser.parse_args()

    if args.database:
        database_path = Path(args.database)
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path
        os.environ["DATABASE_URL"] = _database_url(database_path)

    password = args.password or os.getenv("ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Senha do usuário: ")
        confirm = getpass.getpass("Confirme a senha: ")
        if password != confirm:
            raise SystemExit("As senhas não conferem.")

    from backend.database import init_db, SessionLocal
    from backend.services.auth_service import create_user

    init_db()
    with SessionLocal() as db:
        try:
            user_id = create_user(
                db,
                nome=args.nome,
                email=args.email,
                password=password,
                perfil=args.perfil,
            )
        except ValueError as exc:
            raise SystemExit(str(exc))

    print(f"Usuário criado com sucesso: {args.email} (id {user_id})")


if __name__ == "__main__":
    main()
