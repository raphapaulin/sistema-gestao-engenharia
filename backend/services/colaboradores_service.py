from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


CARGO_OPTIONS = [
    "Engenheiro Responsável",
    "Estagiário de Engenharia",
    "Técnico",
    "Administrativo",
    "Supervisor",
]

TIPO_VINCULO_OPTIONS = [
    "Equipe Técnica",
    "Estágio",
    "Administrativo",
    "Prestador de Serviço",
    "Outro",
]


@dataclass
class ColaboradorForm:
    nome: str = ""
    cargo: str = ""
    email: str = ""
    telefone: str = ""
    tipo_vinculo: str = ""
    registro_profissional: str = ""


def _clean(value: str | None) -> str:
    return (value or "").strip()


def normalize_colaborador_form(
    nome: str | None,
    cargo: str | None,
    email: str | None,
    telefone: str | None,
    tipo_vinculo: str | None,
    registro_profissional: str | None,
) -> ColaboradorForm:
    return ColaboradorForm(
        nome=_clean(nome),
        cargo=_clean(cargo),
        email=_clean(email),
        telefone=_clean(telefone),
        tipo_vinculo=_clean(tipo_vinculo),
        registro_profissional=_clean(registro_profissional),
    )


def list_colaboradores(db: Session, search: str = "") -> list[dict]:
    search = _clean(search)
    if not search:
        rows = db.execute(
            text(
                """
                SELECT
                    id_colaborador,
                    nome,
                    cargo,
                    email,
                    telefone,
                    tipo_vinculo,
                    registro_profissional
                FROM Colaborador
                WHERE ativo = 1
                ORDER BY nome
                """
            )
        ).mappings()
    else:
        rows = db.execute(
            text(
                """
                SELECT
                    id_colaborador,
                    nome,
                    cargo,
                    email,
                    telefone,
                    tipo_vinculo,
                    registro_profissional
                FROM Colaborador
                WHERE ativo = 1
                  AND (
                    LOWER(nome) LIKE :search
                    OR LOWER(COALESCE(cargo, '')) LIKE :search
                    OR LOWER(COALESCE(email, '')) LIKE :search
                    OR LOWER(COALESCE(telefone, '')) LIKE :search
                    OR LOWER(COALESCE(tipo_vinculo, '')) LIKE :search
                    OR LOWER(COALESCE(registro_profissional, '')) LIKE :search
                  )
                ORDER BY nome
                """
            ),
            {"search": f"%{search.lower()}%"},
        ).mappings()

    return [dict(row) for row in rows]


def get_colaborador(db: Session, colaborador_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT
                id_colaborador,
                nome,
                cargo,
                email,
                telefone,
                tipo_vinculo,
                registro_profissional
            FROM Colaborador
            WHERE id_colaborador = :colaborador_id
              AND ativo = 1
            """
        ),
        {"colaborador_id": colaborador_id},
    ).mappings().first()
    return dict(row) if row else None


def validate_colaborador_form(
    db: Session,
    form: ColaboradorForm,
    colaborador_id: int | None = None,
) -> list[str]:
    errors = []

    if not form.nome:
        errors.append("Informe o nome do colaborador.")

    if not form.cargo:
        errors.append("Informe a função ou cargo do colaborador.")

    if form.email and email_exists(db, form.email, colaborador_id):
        errors.append("Já existe um colaborador cadastrado com este e-mail.")

    return errors


def email_exists(db: Session, email: str, colaborador_id: int | None = None) -> bool:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Colaborador
            WHERE ativo = 1
              AND LOWER(email) = LOWER(:email)
              AND (:colaborador_id IS NULL OR id_colaborador != :colaborador_id)
            """
        ),
        {"email": email, "colaborador_id": colaborador_id},
    ).mappings().first()
    return bool(row and row["total"])


def create_colaborador(db: Session, form: ColaboradorForm) -> int:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO Colaborador (
                    nome,
                    cargo,
                    email,
                    telefone,
                    tipo_vinculo,
                    registro_profissional
                )
                VALUES (
                    :nome,
                    :cargo,
                    :email,
                    :telefone,
                    :tipo_vinculo,
                    :registro_profissional
                )
                """
            ),
            {
                "nome": form.nome,
                "cargo": form.cargo,
                "email": form.email or None,
                "telefone": form.telefone or None,
                "tipo_vinculo": form.tipo_vinculo or None,
                "registro_profissional": form.registro_profissional or None,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar. Verifique se o e-mail já existe.")

    return int(result.lastrowid)


def update_colaborador(
    db: Session,
    colaborador_id: int,
    form: ColaboradorForm,
) -> None:
    try:
        db.execute(
            text(
                """
                UPDATE Colaborador
                SET
                    nome = :nome,
                    cargo = :cargo,
                    email = :email,
                    telefone = :telefone,
                    tipo_vinculo = :tipo_vinculo,
                    registro_profissional = :registro_profissional,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id_colaborador = :colaborador_id
                  AND ativo = 1
                """
            ),
            {
                "colaborador_id": colaborador_id,
                "nome": form.nome,
                "cargo": form.cargo,
                "email": form.email or None,
                "telefone": form.telefone or None,
                "tipo_vinculo": form.tipo_vinculo or None,
                "registro_profissional": form.registro_profissional or None,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar. Verifique se o e-mail já existe.")


def delete_colaborador(db: Session, colaborador_id: int) -> None:
    db.execute(
        text(
            """
            UPDATE Colaborador
            SET ativo = 0,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id_colaborador = :colaborador_id
            """
        ),
        {"colaborador_id": colaborador_id},
    )
    db.commit()
