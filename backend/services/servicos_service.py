from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@dataclass
class ServicoForm:
    nome: str = ""
    descricao: str = ""
    preco_base: str = ""


def _clean(value: str | None) -> str:
    return (value or "").strip()


def normalize_servico_form(
    nome: str | None,
    descricao: str | None,
    preco_base: str | None,
) -> ServicoForm:
    return ServicoForm(
        nome=_clean(nome),
        descricao=_clean(descricao),
        preco_base=_clean(preco_base),
    )


def _format_currency(value: float | None) -> str:
    if value is None:
        return "-"

    formatted = f"R$ {value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_price_input(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def parse_preco_base(value: str) -> float | None:
    value = _clean(value)
    if not value:
        return None

    normalized = value.replace("R$", "").replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")

    try:
        preco_base = float(normalized)
    except ValueError:
        raise ValueError("Preço base deve ser numérico.")

    if preco_base < 0:
        raise ValueError("Preço base não pode ser negativo.")

    return preco_base


def _with_display_fields(servico: dict) -> dict:
    servico["preco_base_display"] = _format_currency(servico.get("preco_base"))
    servico["preco_base_form"] = _format_price_input(servico.get("preco_base"))
    return servico


def list_servicos(db: Session, search: str = "") -> list[dict]:
    search = _clean(search)
    if not search:
        rows = db.execute(
            text(
                """
                SELECT id_servico, nome, descricao, preco_base
                FROM Servico
                ORDER BY nome
                """
            )
        ).mappings()
    else:
        rows = db.execute(
            text(
                """
                SELECT id_servico, nome, descricao, preco_base
                FROM Servico
                WHERE
                    LOWER(nome) LIKE :search
                    OR LOWER(COALESCE(descricao, '')) LIKE :search
                ORDER BY nome
                """
            ),
            {"search": f"%{search.lower()}%"},
        ).mappings()

    return [_with_display_fields(dict(row)) for row in rows]


def get_servico(db: Session, servico_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id_servico, nome, descricao, preco_base
            FROM Servico
            WHERE id_servico = :servico_id
            """
        ),
        {"servico_id": servico_id},
    ).mappings().first()
    return _with_display_fields(dict(row)) if row else None


def validate_servico_form(form: ServicoForm) -> tuple[list[str], float | None]:
    errors = []
    preco_base = None

    if not form.nome:
        errors.append("Informe o nome do serviço.")

    try:
        preco_base = parse_preco_base(form.preco_base)
    except ValueError as exc:
        errors.append(str(exc))

    return errors, preco_base


def create_servico(db: Session, form: ServicoForm, preco_base: float | None) -> int:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO Servico (nome, descricao, preco_base)
                VALUES (:nome, :descricao, :preco_base)
                """
            ),
            {
                "nome": form.nome,
                "descricao": form.descricao or None,
                "preco_base": preco_base,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar este serviço.")

    return int(result.lastrowid)


def update_servico(
    db: Session,
    servico_id: int,
    form: ServicoForm,
    preco_base: float | None,
) -> None:
    try:
        db.execute(
            text(
                """
                UPDATE Servico
                SET
                    nome = :nome,
                    descricao = :descricao,
                    preco_base = :preco_base
                WHERE id_servico = :servico_id
                """
            ),
            {
                "servico_id": servico_id,
                "nome": form.nome,
                "descricao": form.descricao or None,
                "preco_base": preco_base,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar este serviço.")


def delete_servico(db: Session, servico_id: int) -> None:
    total_ordens = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Ordem_Servico
            WHERE id_servico = :servico_id
            """
        ),
        {"servico_id": servico_id},
    ).scalar()

    total_vinculos_tecnicos = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Engenheiro_Servico
            WHERE id_servico = :servico_id
            """
        ),
        {"servico_id": servico_id},
    ).scalar()

    if total_ordens:
        raise ValueError("Serviço possui ordens de serviço vinculadas e não pode ser excluído.")

    if total_vinculos_tecnicos:
        raise ValueError("Serviço possui vínculos técnicos cadastrados e não pode ser excluído.")

    try:
        db.execute(
            text("DELETE FROM Servico WHERE id_servico = :servico_id"),
            {"servico_id": servico_id},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível excluir este serviço.")
