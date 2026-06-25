from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@dataclass
class ClientForm:
    nome: str = ""
    empresa: str = ""
    telefone: str = ""
    email: str = ""


def _clean(value: str | None) -> str:
    return (value or "").strip()


def normalize_client_form(
    nome: str | None,
    empresa: str | None,
    telefone: str | None,
    email: str | None,
) -> ClientForm:
    return ClientForm(
        nome=_clean(nome),
        empresa=_clean(empresa),
        telefone=_clean(telefone),
        email=_clean(email),
    )


def list_clients(db: Session, search: str = "") -> list[dict]:
    search = _clean(search)
    if not search:
        rows = db.execute(
            text(
                """
                SELECT id_cliente, nome, empresa, telefone, email
                FROM Cliente
                ORDER BY nome
                """
            )
        ).mappings()
    else:
        rows = db.execute(
            text(
                """
                SELECT id_cliente, nome, empresa, telefone, email
                FROM Cliente
                WHERE
                    LOWER(nome) LIKE :search
                    OR LOWER(COALESCE(empresa, '')) LIKE :search
                    OR LOWER(COALESCE(email, '')) LIKE :search
                ORDER BY nome
                """
            ),
            {"search": f"%{search.lower()}%"},
        ).mappings()

    return [dict(row) for row in rows]


def get_client(db: Session, client_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id_cliente, nome, empresa, telefone, email
            FROM Cliente
            WHERE id_cliente = :client_id
            """
        ),
        {"client_id": client_id},
    ).mappings().first()
    return dict(row) if row else None


def validate_client_form(
    db: Session,
    form: ClientForm,
    client_id: int | None = None,
) -> list[str]:
    errors = []

    if not form.nome:
        errors.append("Informe o nome do cliente.")

    if not form.email:
        errors.append("Informe o e-mail do cliente.")
    elif email_exists(db, form.email, client_id):
        errors.append("Já existe um cliente cadastrado com este e-mail.")

    return errors


def email_exists(db: Session, email: str, client_id: int | None = None) -> bool:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Cliente
            WHERE LOWER(email) = LOWER(:email)
              AND (:client_id IS NULL OR id_cliente != :client_id)
            """
        ),
        {"email": email, "client_id": client_id},
    ).mappings().first()
    return bool(row and row["total"])


def create_client(db: Session, form: ClientForm) -> int:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO Cliente (nome, empresa, telefone, email)
                VALUES (:nome, :empresa, :telefone, :email)
                """
            ),
            {
                "nome": form.nome,
                "empresa": form.empresa or None,
                "telefone": form.telefone or None,
                "email": form.email,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar. Verifique se o e-mail já existe.")

    return int(result.lastrowid)


def update_client(db: Session, client_id: int, form: ClientForm) -> None:
    try:
        db.execute(
            text(
                """
                UPDATE Cliente
                SET
                    nome = :nome,
                    empresa = :empresa,
                    telefone = :telefone,
                    email = :email
                WHERE id_cliente = :client_id
                """
            ),
            {
                "client_id": client_id,
                "nome": form.nome,
                "empresa": form.empresa or None,
                "telefone": form.telefone or None,
                "email": form.email,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar. Verifique se o e-mail já existe.")


def delete_client(db: Session, client_id: int) -> None:
    total_orders = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Ordem_Servico
            WHERE id_cliente = :client_id
            """
        ),
        {"client_id": client_id},
    ).scalar()

    if total_orders:
        raise ValueError("Cliente possui ordens de serviço e não pode ser excluído.")

    try:
        db.execute(
            text("DELETE FROM Cliente WHERE id_cliente = :client_id"),
            {"client_id": client_id},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível excluir este cliente.")
