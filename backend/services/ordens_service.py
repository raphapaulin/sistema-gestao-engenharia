from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


STATUS_OPTIONS = [
    {"value": "aberta", "label": "Aberta"},
    {"value": "em andamento", "label": "Em andamento"},
    {"value": "concluida", "label": "Concluída"},
]

STATUS_LABELS = {item["value"]: item["label"] for item in STATUS_OPTIONS}


@dataclass
class OrdemForm:
    data_abertura: str = ""
    id_cliente: str = ""
    id_colaborador: str = ""
    id_servico: str = ""
    status: str = "aberta"


def _clean(value: str | None) -> str:
    return (value or "").strip()


def today_iso() -> str:
    return date.today().isoformat()


def normalize_ordem_form(
    data_abertura: str | None,
    id_cliente: str | None,
    id_colaborador: str | None,
    id_servico: str | None,
    status: str | None,
) -> OrdemForm:
    return OrdemForm(
        data_abertura=_clean(data_abertura) or today_iso(),
        id_cliente=_clean(id_cliente),
        id_colaborador=_clean(id_colaborador),
        id_servico=_clean(id_servico),
        status=_clean(status) or "aberta",
    )


def _parse_required_int(value: str, field_label: str, errors: list[str]) -> int | None:
    if not value:
        errors.append(f"Selecione {field_label}.")
        return None

    try:
        return int(value)
    except ValueError:
        errors.append(f"Seleção inválida para {field_label}.")
        return None


def validate_ordem_form(db: Session, form: OrdemForm) -> tuple[list[str], dict]:
    errors: list[str] = []

    if not form.data_abertura:
        errors.append("Informe a data de abertura.")
    else:
        try:
            date.fromisoformat(form.data_abertura)
        except ValueError:
            errors.append("Informe uma data de abertura válida.")

    if form.status not in STATUS_LABELS:
        errors.append("Selecione um status válido.")

    id_cliente = _parse_required_int(form.id_cliente, "um cliente", errors)
    id_colaborador = _parse_required_int(form.id_colaborador, "um colaborador", errors)
    id_servico = _parse_required_int(form.id_servico, "um serviço", errors)

    if id_cliente and not _exists(db, "Cliente", "id_cliente", id_cliente):
        errors.append("Cliente selecionado não foi encontrado.")

    if id_colaborador and not _active_colaborador_exists(db, id_colaborador):
        errors.append("Colaborador selecionado não foi encontrado.")

    if id_servico and not _exists(db, "Servico", "id_servico", id_servico):
        errors.append("Serviço selecionado não foi encontrado.")

    data = {
        "data_abertura": form.data_abertura,
        "status": form.status,
        "id_cliente": id_cliente,
        "id_colaborador": id_colaborador,
        "id_servico": id_servico,
        "id_engenheiro": _legacy_engenheiro_id(db, id_colaborador),
    }
    return errors, data


def _exists(db: Session, table: str, column: str, value: int) -> bool:
    row = db.execute(
        text(f"SELECT COUNT(*) AS total FROM {table} WHERE {column} = :value"),
        {"value": value},
    ).mappings().first()
    return bool(row and row["total"])


def _active_colaborador_exists(db: Session, colaborador_id: int) -> bool:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Colaborador
            WHERE id_colaborador = :colaborador_id
              AND ativo = 1
            """
        ),
        {"colaborador_id": colaborador_id},
    ).mappings().first()
    return bool(row and row["total"])


def _legacy_engenheiro_id(db: Session, colaborador_id: int | None) -> int | None:
    if not colaborador_id:
        return None

    return db.execute(
        text(
            """
            SELECT legacy_engenheiro_id
            FROM Colaborador
            WHERE id_colaborador = :colaborador_id
            """
        ),
        {"colaborador_id": colaborador_id},
    ).scalar()


def list_clientes_options(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id_cliente AS id, nome AS label
            FROM Cliente
            ORDER BY nome
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def list_colaboradores_options(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id_colaborador AS id, nome AS label, cargo
            FROM Colaborador
            WHERE ativo = 1
            ORDER BY nome
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def list_servicos_options(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id_servico AS id, nome AS label
            FROM Servico
            ORDER BY nome
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def _ordens_base_sql(where_clause: str = "") -> str:
    return f"""
        SELECT
            os.id_ordem,
            os.data_abertura,
            os.status,
            os.id_cliente,
            os.id_colaborador,
            os.id_servico,
            c.nome AS cliente,
            COALESCE(col.nome, e.nome, 'Sem responsável') AS colaborador,
            s.nome AS servico
        FROM Ordem_Servico os
        JOIN Cliente c ON c.id_cliente = os.id_cliente
        LEFT JOIN Colaborador col ON col.id_colaborador = os.id_colaborador
        LEFT JOIN Engenheiro e ON e.id_engenheiro = os.id_engenheiro
        JOIN Servico s ON s.id_servico = os.id_servico
        {where_clause}
        ORDER BY os.data_abertura DESC, os.id_ordem DESC
    """


def _with_display_fields(ordem: dict) -> dict:
    ordem["status_label"] = STATUS_LABELS.get(ordem["status"], ordem["status"])
    return ordem


def list_ordens(db: Session, search: str = "") -> list[dict]:
    search = _clean(search)
    if not search:
        rows = db.execute(text(_ordens_base_sql())).mappings()
    else:
        rows = db.execute(
            text(
                _ordens_base_sql(
                    """
                    WHERE
                        LOWER(c.nome) LIKE :search
                        OR LOWER(COALESCE(col.nome, e.nome, '')) LIKE :search
                        OR LOWER(s.nome) LIKE :search
                        OR LOWER(os.status) LIKE :search
                        OR LOWER(
                            CASE os.status
                                WHEN 'aberta' THEN 'Aberta'
                                WHEN 'em andamento' THEN 'Em andamento'
                                WHEN 'concluida' THEN 'Concluída'
                                ELSE os.status
                            END
                        ) LIKE :search
                    """
                )
            ),
            {"search": f"%{search.lower()}%"},
        ).mappings()

    return [_with_display_fields(dict(row)) for row in rows]


def get_ordem(db: Session, ordem_id: int) -> dict | None:
    row = db.execute(
        text(_ordens_base_sql("WHERE os.id_ordem = :ordem_id")),
        {"ordem_id": ordem_id},
    ).mappings().first()
    return _with_display_fields(dict(row)) if row else None


def create_ordem(db: Session, data: dict) -> int:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO Ordem_Servico (
                    data_abertura,
                    status,
                    id_cliente,
                    id_engenheiro,
                    id_servico,
                    id_colaborador
                )
                VALUES (
                    :data_abertura,
                    :status,
                    :id_cliente,
                    :id_engenheiro,
                    :id_servico,
                    :id_colaborador
                )
                """
            ),
            data,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar esta ordem de serviço.")

    return int(result.lastrowid)


def update_ordem(db: Session, ordem_id: int, data: dict) -> None:
    try:
        db.execute(
            text(
                """
                UPDATE Ordem_Servico
                SET
                    data_abertura = :data_abertura,
                    status = :status,
                    id_cliente = :id_cliente,
                    id_engenheiro = :id_engenheiro,
                    id_servico = :id_servico,
                    id_colaborador = :id_colaborador
                WHERE id_ordem = :ordem_id
                """
            ),
            {"ordem_id": ordem_id, **data},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar esta ordem de serviço.")


def update_ordem_status(db: Session, ordem_id: int, status: str) -> None:
    if status not in STATUS_LABELS:
        raise ValueError("Selecione um status válido.")

    db.execute(
        text(
            """
            UPDATE Ordem_Servico
            SET status = :status
            WHERE id_ordem = :ordem_id
            """
        ),
        {"ordem_id": ordem_id, "status": status},
    )
    db.commit()


def delete_ordem(db: Session, ordem_id: int) -> None:
    total_pagamentos = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Pagamento
            WHERE id_ordem = :ordem_id
            """
        ),
        {"ordem_id": ordem_id},
    ).scalar()

    if total_pagamentos:
        raise ValueError("Ordem possui pagamento vinculado e não pode ser excluída.")

    try:
        db.execute(
            text("DELETE FROM Ordem_Servico WHERE id_ordem = :ordem_id"),
            {"ordem_id": ordem_id},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível excluir esta ordem de serviço.")
