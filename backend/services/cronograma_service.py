from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.atividades_service import STATUS_LABELS, format_duration


STATUS_COLORS = {
    "planejada": "#087f8c",
    "em andamento": "#1f6feb",
    "concluida": "#1f9d66",
    "cancelada": "#c2410c",
}


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _date_filter(value: str | None) -> str:
    candidate = _clean(value)[:10]
    if not candidate:
        return ""

    try:
        date.fromisoformat(candidate)
    except ValueError:
        return ""

    return candidate


def _optional_int(value: str | None) -> int | None:
    value = _clean(value)
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _event_time(value: str) -> str:
    value = _clean(value)
    if len(value) == 5:
        return f"{value}:00"
    return value


def list_calendar_events(
    db: Session,
    start: str = "",
    end: str = "",
    id_colaborador: str = "",
    id_cliente: str = "",
    status: str = "",
) -> list[dict]:
    filters = []
    params: dict[str, str | int] = {}

    start_date = _date_filter(start)
    end_date = _date_filter(end)
    colaborador_id = _optional_int(id_colaborador)
    cliente_id = _optional_int(id_cliente)
    status = _clean(status)

    if start_date:
        filters.append("a.data_atividade >= :start_date")
        params["start_date"] = start_date

    if end_date:
        filters.append("a.data_atividade < :end_date")
        params["end_date"] = end_date

    if colaborador_id:
        filters.append("a.id_colaborador = :id_colaborador")
        params["id_colaborador"] = colaborador_id

    if cliente_id:
        filters.append("a.id_cliente = :id_cliente")
        params["id_cliente"] = cliente_id

    if status in STATUS_LABELS:
        filters.append("a.status = :status")
        params["status"] = status

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(
            f"""
            SELECT
                a.id_atividade,
                a.titulo,
                a.descricao,
                a.data_atividade,
                a.hora_inicio,
                a.hora_fim,
                a.duracao_minutos,
                a.status,
                a.id_ordem,
                col.nome AS colaborador,
                c.nome AS cliente,
                s.nome AS servico
            FROM Atividade a
            JOIN Colaborador col ON col.id_colaborador = a.id_colaborador
            LEFT JOIN Cliente c ON c.id_cliente = a.id_cliente
            LEFT JOIN Servico s ON s.id_servico = a.id_servico
            {where_clause}
            ORDER BY a.data_atividade, a.hora_inicio, a.id_atividade
            """
        ),
        params,
    ).mappings()

    events = []
    for row in rows:
        atividade = dict(row)
        status_value = atividade["status"]
        status_label = STATUS_LABELS.get(status_value, status_value)
        color = STATUS_COLORS.get(status_value, "#667085")
        start_datetime = f"{atividade['data_atividade']}T{_event_time(atividade['hora_inicio'])}"
        end_datetime = f"{atividade['data_atividade']}T{_event_time(atividade['hora_fim'])}"

        events.append(
            {
                "id": str(atividade["id_atividade"]),
                "title": f"{atividade['titulo']} · {atividade['colaborador']}",
                "start": start_datetime,
                "end": end_datetime,
                "backgroundColor": color,
                "borderColor": color,
                "textColor": "#ffffff",
                "extendedProps": {
                    "titulo": atividade["titulo"],
                    "descricao": atividade["descricao"] or "-",
                    "data": atividade["data_atividade"],
                    "horario": f"{atividade['hora_inicio']} - {atividade['hora_fim']}",
                    "duracao": format_duration(atividade["duracao_minutos"]),
                    "colaborador": atividade["colaborador"],
                    "cliente": atividade["cliente"] or "-",
                    "servico": atividade["servico"] or "-",
                    "ordem": f"#{atividade['id_ordem']}" if atividade["id_ordem"] else "-",
                    "status": status_value,
                    "statusLabel": status_label,
                    "editUrl": f"/atividades/{atividade['id_atividade']}/editar",
                },
            }
        )

    return events
