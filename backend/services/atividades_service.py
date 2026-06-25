from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


STATUS_OPTIONS = [
    {"value": "planejada", "label": "Planejada"},
    {"value": "em andamento", "label": "Em andamento"},
    {"value": "concluida", "label": "Concluída"},
    {"value": "cancelada", "label": "Cancelada"},
]

STATUS_LABELS = {item["value"]: item["label"] for item in STATUS_OPTIONS}


@dataclass
class AtividadeForm:
    titulo: str = ""
    descricao: str = ""
    data_atividade: str = ""
    hora_inicio: str = ""
    hora_fim: str = ""
    status: str = "planejada"
    id_colaborador: str = ""
    id_cliente: str = ""
    id_servico: str = ""
    id_ordem: str = ""
    observacoes: str = ""


def _clean(value: str | None) -> str:
    return (value or "").strip()


def today_iso() -> str:
    return date.today().isoformat()


def normalize_atividade_form(
    titulo: str | None,
    descricao: str | None,
    data_atividade: str | None,
    hora_inicio: str | None,
    hora_fim: str | None,
    status: str | None,
    id_colaborador: str | None,
    id_cliente: str | None,
    id_servico: str | None,
    id_ordem: str | None,
    observacoes: str | None,
) -> AtividadeForm:
    return AtividadeForm(
        titulo=_clean(titulo),
        descricao=_clean(descricao),
        data_atividade=_clean(data_atividade) or today_iso(),
        hora_inicio=_clean(hora_inicio),
        hora_fim=_clean(hora_fim),
        status=_clean(status) or "planejada",
        id_colaborador=_clean(id_colaborador),
        id_cliente=_clean(id_cliente),
        id_servico=_clean(id_servico),
        id_ordem=_clean(id_ordem),
        observacoes=_clean(observacoes),
    )


def format_duration(minutes: int | None) -> str:
    if minutes is None:
        return "-"

    hours, remaining_minutes = divmod(int(minutes), 60)
    if hours and remaining_minutes:
        return f"{hours}h{remaining_minutes:02d}"
    if hours:
        return f"{hours}h"
    return f"{remaining_minutes} min"


def _parse_time(value: str, label: str, errors: list[str]):
    if not value:
        errors.append(f"Informe {label}.")
        return None

    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        errors.append(f"Informe {label} em formato válido.")
        return None


def _parse_optional_int(value: str, label: str, errors: list[str]) -> int | None:
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        errors.append(f"Seleção inválida para {label}.")
        return None


def _parse_required_int(value: str, label: str, errors: list[str]) -> int | None:
    if not value:
        errors.append(f"Selecione {label}.")
        return None
    return _parse_optional_int(value, label, errors)


def validate_atividade_form(db: Session, form: AtividadeForm) -> tuple[list[str], dict]:
    errors: list[str] = []

    if not form.titulo:
        errors.append("Informe o título da atividade.")

    if not form.data_atividade:
        errors.append("Informe a data da atividade.")
    else:
        try:
            date.fromisoformat(form.data_atividade)
        except ValueError:
            errors.append("Informe uma data válida.")

    start_time = _parse_time(form.hora_inicio, "a hora de início", errors)
    end_time = _parse_time(form.hora_fim, "a hora de fim", errors)
    duracao_minutos = None
    if start_time and end_time:
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        duracao_minutos = end_minutes - start_minutes
        if duracao_minutos <= 0:
            errors.append("A hora de fim deve ser maior que a hora de início.")

    if form.status not in STATUS_LABELS:
        errors.append("Selecione um status válido.")

    id_colaborador = _parse_required_int(form.id_colaborador, "um colaborador", errors)
    id_cliente = _parse_optional_int(form.id_cliente, "cliente", errors)
    id_servico = _parse_optional_int(form.id_servico, "serviço", errors)
    id_ordem = _parse_optional_int(form.id_ordem, "ordem de serviço", errors)

    if id_colaborador and not _exists_active_colaborador(db, id_colaborador):
        errors.append("Colaborador selecionado não foi encontrado.")

    if id_cliente and not _exists(db, "Cliente", "id_cliente", id_cliente):
        errors.append("Cliente selecionado não foi encontrado.")

    if id_servico and not _exists(db, "Servico", "id_servico", id_servico):
        errors.append("Serviço selecionado não foi encontrado.")

    if id_ordem and not _exists(db, "Ordem_Servico", "id_ordem", id_ordem):
        errors.append("Ordem de serviço selecionada não foi encontrada.")

    data = {
        "titulo": form.titulo,
        "descricao": form.descricao or None,
        "data_atividade": form.data_atividade,
        "hora_inicio": form.hora_inicio,
        "hora_fim": form.hora_fim,
        "duracao_minutos": duracao_minutos,
        "status": form.status,
        "id_colaborador": id_colaborador,
        "id_cliente": id_cliente,
        "id_servico": id_servico,
        "id_ordem": id_ordem,
        "observacoes": form.observacoes or None,
    }
    return errors, data


def _exists(db: Session, table: str, column: str, value: int) -> bool:
    row = db.execute(
        text(f"SELECT COUNT(*) AS total FROM {table} WHERE {column} = :value"),
        {"value": value},
    ).mappings().first()
    return bool(row and row["total"])


def _exists_active_colaborador(db: Session, colaborador_id: int) -> bool:
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


def list_ordens_options(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                os.id_ordem AS id,
                os.data_abertura,
                os.status,
                c.nome AS cliente,
                s.nome AS servico
            FROM Ordem_Servico os
            JOIN Cliente c ON c.id_cliente = os.id_cliente
            JOIN Servico s ON s.id_servico = os.id_servico
            ORDER BY os.data_abertura DESC, os.id_ordem DESC
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def _base_atividades_sql(where_clause: str = "") -> str:
    return f"""
        SELECT
            a.id_atividade,
            a.titulo,
            a.descricao,
            a.data_atividade,
            a.hora_inicio,
            a.hora_fim,
            a.duracao_minutos,
            a.status,
            a.id_colaborador,
            a.id_cliente,
            a.id_servico,
            a.id_ordem,
            a.observacoes,
            col.nome AS colaborador,
            c.nome AS cliente,
            s.nome AS servico
        FROM Atividade a
        JOIN Colaborador col ON col.id_colaborador = a.id_colaborador
        LEFT JOIN Cliente c ON c.id_cliente = a.id_cliente
        LEFT JOIN Servico s ON s.id_servico = a.id_servico
        LEFT JOIN Ordem_Servico os ON os.id_ordem = a.id_ordem
        {where_clause}
        ORDER BY a.data_atividade DESC, a.hora_inicio DESC, a.id_atividade DESC
    """


def _with_display_fields(atividade: dict) -> dict:
    atividade["status_label"] = STATUS_LABELS.get(
        atividade["status"],
        atividade["status"],
    )
    atividade["duracao_display"] = format_duration(atividade.get("duracao_minutos"))
    atividade["horario_display"] = (
        f"{atividade['hora_inicio']} - {atividade['hora_fim']}"
        if atividade.get("hora_inicio") and atividade.get("hora_fim")
        else "-"
    )
    return atividade


def list_atividades(
    db: Session,
    id_colaborador: str = "",
    id_cliente: str = "",
    id_servico: str = "",
    status: str = "",
    data_inicio: str = "",
    data_fim: str = "",
) -> list[dict]:
    filters = []
    params = {}

    if _clean(id_colaborador):
        filters.append("a.id_colaborador = :id_colaborador")
        params["id_colaborador"] = int(id_colaborador)

    if _clean(id_cliente):
        filters.append("a.id_cliente = :id_cliente")
        params["id_cliente"] = int(id_cliente)

    if _clean(id_servico):
        filters.append("a.id_servico = :id_servico")
        params["id_servico"] = int(id_servico)

    if _clean(status) in STATUS_LABELS:
        filters.append("a.status = :status")
        params["status"] = status

    if _clean(data_inicio):
        filters.append("a.data_atividade >= :data_inicio")
        params["data_inicio"] = data_inicio

    if _clean(data_fim):
        filters.append("a.data_atividade <= :data_fim")
        params["data_fim"] = data_fim

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(text(_base_atividades_sql(where_clause)), params).mappings()
    return [_with_display_fields(dict(row)) for row in rows]


def get_atividade(db: Session, atividade_id: int) -> dict | None:
    row = db.execute(
        text(_base_atividades_sql("WHERE a.id_atividade = :atividade_id")),
        {"atividade_id": atividade_id},
    ).mappings().first()
    return _with_display_fields(dict(row)) if row else None


def create_atividade(db: Session, data: dict) -> int:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO Atividade (
                    titulo,
                    descricao,
                    data_atividade,
                    hora_inicio,
                    hora_fim,
                    duracao_minutos,
                    status,
                    id_colaborador,
                    id_cliente,
                    id_servico,
                    id_ordem,
                    observacoes
                )
                VALUES (
                    :titulo,
                    :descricao,
                    :data_atividade,
                    :hora_inicio,
                    :hora_fim,
                    :duracao_minutos,
                    :status,
                    :id_colaborador,
                    :id_cliente,
                    :id_servico,
                    :id_ordem,
                    :observacoes
                )
                """
            ),
            data,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar esta atividade.")

    return int(result.lastrowid)


def update_atividade(db: Session, atividade_id: int, data: dict) -> None:
    try:
        db.execute(
            text(
                """
                UPDATE Atividade
                SET
                    titulo = :titulo,
                    descricao = :descricao,
                    data_atividade = :data_atividade,
                    hora_inicio = :hora_inicio,
                    hora_fim = :hora_fim,
                    duracao_minutos = :duracao_minutos,
                    status = :status,
                    id_colaborador = :id_colaborador,
                    id_cliente = :id_cliente,
                    id_servico = :id_servico,
                    id_ordem = :id_ordem,
                    observacoes = :observacoes,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id_atividade = :atividade_id
                """
            ),
            {"atividade_id": atividade_id, **data},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar esta atividade.")


def update_atividade_status(db: Session, atividade_id: int, status: str) -> None:
    if status not in STATUS_LABELS:
        raise ValueError("Selecione um status válido.")

    db.execute(
        text(
            """
            UPDATE Atividade
            SET status = :status,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id_atividade = :atividade_id
            """
        ),
        {"atividade_id": atividade_id, "status": status},
    )
    db.commit()


def delete_atividade(db: Session, atividade_id: int) -> None:
    try:
        db.execute(
            text("DELETE FROM Atividade WHERE id_atividade = :atividade_id"),
            {"atividade_id": atividade_id},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível excluir esta atividade.")
