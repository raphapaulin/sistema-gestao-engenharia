from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.atividades_service import STATUS_LABELS, STATUS_OPTIONS, format_duration


WORKDAY_START_MINUTES = 8 * 60
WORKDAY_END_MINUTES = 18 * 60


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _parse_date(value: str, errors: list[str], label: str) -> str:
    value = _clean(value)
    if not value:
        return ""

    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(f"Informe uma data válida para {label}.")
        return ""

    return value


def _parse_optional_int(value: str, errors: list[str], label: str) -> int | None:
    value = _clean(value)
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        errors.append(f"Seleção inválida para {label}.")
        return None


def _parse_duration(value: str, errors: list[str]) -> int:
    value = _clean(value) or "60"
    try:
        duration = int(value)
    except ValueError:
        errors.append("Informe a duração estimada em minutos.")
        return 60

    if duration <= 0:
        errors.append("A duração estimada deve ser maior que zero.")
        return 60

    return duration


def _time_to_minutes(value: str | None) -> int | None:
    value = _clean(value)
    for time_format in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, time_format).time()
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            continue
    return None


def _minutes_to_time(minutes: int) -> str:
    hours, remaining_minutes = divmod(minutes, 60)
    return f"{hours:02d}:{remaining_minutes:02d}"


def _interval(start_minutes: int, end_minutes: int) -> dict:
    return {
        "inicio": _minutes_to_time(start_minutes),
        "fim": _minutes_to_time(end_minutes),
        "duracao_minutos": max(end_minutes - start_minutes, 0),
        "duracao_display": format_duration(max(end_minutes - start_minutes, 0)),
        "label": f"{_minutes_to_time(start_minutes)} - {_minutes_to_time(end_minutes)}",
    }


def _get_colaborador_name(db: Session, colaborador_id: int) -> str | None:
    row = db.execute(
        text(
            """
            SELECT nome
            FROM Colaborador
            WHERE id_colaborador = :colaborador_id
              AND ativo = 1
            """
        ),
        {"colaborador_id": colaborador_id},
    ).mappings().first()
    return row["nome"] if row else None


def _day_activities(db: Session, colaborador_id: int, activity_date: str) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                a.id_atividade,
                a.titulo,
                a.data_atividade,
                a.hora_inicio,
                a.hora_fim,
                a.duracao_minutos,
                a.status,
                a.id_ordem,
                c.nome AS cliente,
                s.nome AS servico
            FROM Atividade a
            LEFT JOIN Cliente c ON c.id_cliente = a.id_cliente
            LEFT JOIN Servico s ON s.id_servico = a.id_servico
            WHERE a.id_colaborador = :colaborador_id
              AND a.data_atividade = :activity_date
            ORDER BY a.hora_inicio, a.hora_fim, a.id_atividade
            """
        ),
        {"colaborador_id": colaborador_id, "activity_date": activity_date},
    ).mappings()

    activities = []
    for row in rows:
        activity = dict(row)
        activity["status_label"] = STATUS_LABELS.get(activity["status"], activity["status"])
        activity["horario_display"] = (
            f"{activity['hora_inicio']} - {activity['hora_fim']}"
            if activity.get("hora_inicio") and activity.get("hora_fim")
            else "-"
        )
        activity["duracao_display"] = format_duration(activity["duracao_minutos"])
        activity["inicio_minutos"] = _time_to_minutes(activity["hora_inicio"])
        activity["fim_minutos"] = _time_to_minutes(activity["hora_fim"])
        activities.append(activity)
    return activities


def _availability_from_activities(activities: list[dict], duration_minutes: int) -> dict:
    busy_intervals = []
    free_intervals = []
    pointer = WORKDAY_START_MINUTES

    for activity in activities:
        if activity["inicio_minutos"] is None or activity["fim_minutos"] is None:
            continue

        start = max(activity["inicio_minutos"], WORKDAY_START_MINUTES)
        end = min(activity["fim_minutos"], WORKDAY_END_MINUTES)

        if end <= WORKDAY_START_MINUTES or start >= WORKDAY_END_MINUTES:
            continue

        if start > pointer:
            free_intervals.append(_interval(pointer, start))

        busy_intervals.append(_interval(start, end))
        pointer = max(pointer, end)

    if pointer < WORKDAY_END_MINUTES:
        free_intervals.append(_interval(pointer, WORKDAY_END_MINUTES))

    available_intervals = [
        interval
        for interval in free_intervals
        if interval["duracao_minutos"] >= duration_minutes
    ]
    next_available = available_intervals[0] if available_intervals else None

    if next_available:
        suggestion_start = _time_to_minutes(next_available["inicio"])
        if suggestion_start is None:
            suggestion = None
        else:
            suggestion = _interval(suggestion_start, suggestion_start + duration_minutes)
    else:
        suggestion = None

    return {
        "busy_intervals": busy_intervals,
        "free_intervals": free_intervals,
        "next_available": suggestion,
        "has_availability": bool(suggestion),
    }


def get_availability_analysis(
    db: Session,
    id_colaborador: str = "",
    data: str = "",
    duracao_minutos: str = "60",
) -> dict:
    errors: list[str] = []
    colaborador_id = _parse_optional_int(id_colaborador, errors, "colaborador")
    activity_date = _parse_date(data, errors, "a disponibilidade") or date.today().isoformat()
    duration_minutes = _parse_duration(duracao_minutos, errors)

    result = {
        "selected": bool(colaborador_id),
        "errors": errors,
        "colaborador_id": colaborador_id,
        "colaborador_nome": "",
        "data": activity_date,
        "duracao_minutos": duration_minutes,
        "duracao_display": format_duration(duration_minutes),
        "jornada_label": "08:00 - 18:00",
        "atividades": [],
        "busy_intervals": [],
        "free_intervals": [],
        "next_available": None,
        "has_availability": False,
        "message": "Selecione um colaborador para analisar a disponibilidade.",
        "message_type": "info",
    }

    if not colaborador_id or errors:
        if errors:
            result["message"] = "Corrija os campos destacados para analisar a disponibilidade."
            result["message_type"] = "danger"
        return result

    colaborador_nome = _get_colaborador_name(db, colaborador_id)
    if not colaborador_nome:
        result["errors"].append("Colaborador não encontrado.")
        result["message"] = "Não foi possível analisar este colaborador."
        result["message_type"] = "danger"
        return result

    activities = _day_activities(db, colaborador_id, activity_date)
    availability = _availability_from_activities(activities, duration_minutes)

    result.update(
        {
            "colaborador_nome": colaborador_nome,
            "atividades": activities,
            **availability,
        }
    )

    if not activities and availability["has_availability"]:
        result["message"] = "Nenhuma atividade agendada no dia. Colaborador disponível."
        result["message_type"] = "success"
    elif availability["has_availability"]:
        result["message"] = "Existe horário disponível para a duração informada."
        result["message_type"] = "success"
    else:
        result["message"] = "Não há disponibilidade suficiente nesse dia para a duração informada."
        result["message_type"] = "warning"

    return result


def get_hours_report(
    db: Session,
    id_colaborador: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    status: str = "",
) -> dict:
    errors: list[str] = []
    filters = []
    params: dict[str, int | str] = {}

    colaborador_id = _parse_optional_int(id_colaborador, errors, "colaborador")
    start_date = _parse_date(data_inicio, errors, "data inicial")
    end_date = _parse_date(data_fim, errors, "data final")
    status = _clean(status)

    if colaborador_id:
        filters.append("a.id_colaborador = :colaborador_id")
        params["colaborador_id"] = colaborador_id

    if start_date:
        filters.append("a.data_atividade >= :start_date")
        params["start_date"] = start_date

    if end_date:
        filters.append("a.data_atividade <= :end_date")
        params["end_date"] = end_date

    if status:
        if status in STATUS_LABELS:
            filters.append("a.status = :status")
            params["status"] = status
        else:
            errors.append("Selecione um status válido.")

    if errors:
        return {
            "errors": errors,
            "activities": [],
            "hours_by_colaborador": [],
            "summary": {
                "total_atividades": 0,
                "total_minutos": 0,
                "total_horas": 0,
                "total_horas_display": format_duration(0),
                "atividades_concluidas": 0,
                "atividades_pendentes": 0,
            },
            "status_options": STATUS_OPTIONS,
        }

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(
            f"""
            SELECT
                a.id_atividade,
                a.titulo,
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
            ORDER BY a.data_atividade DESC, a.hora_inicio DESC, a.id_atividade DESC
            """
        ),
        params,
    ).mappings()

    activities = []
    minutes_by_colaborador: dict[str, int] = {}
    count_by_colaborador: dict[str, int] = {}
    total_minutes = 0
    completed = 0
    pending_or_progress = 0

    for row in rows:
        activity = dict(row)
        duration = int(activity["duracao_minutos"] or 0)
        total_minutes += duration
        minutes_by_colaborador[activity["colaborador"]] = (
            minutes_by_colaborador.get(activity["colaborador"], 0) + duration
        )
        count_by_colaborador[activity["colaborador"]] = (
            count_by_colaborador.get(activity["colaborador"], 0) + 1
        )

        if activity["status"] == "concluida":
            completed += 1
        elif activity["status"] in {"planejada", "em andamento"}:
            pending_or_progress += 1

        activity["status_label"] = STATUS_LABELS.get(activity["status"], activity["status"])
        activity["horario_display"] = (
            f"{activity['hora_inicio']} - {activity['hora_fim']}"
            if activity.get("hora_inicio") and activity.get("hora_fim")
            else "-"
        )
        activity["duracao_display"] = format_duration(duration)
        activities.append(activity)

    hours_by_colaborador = [
        {
            "label": colaborador,
            "value": round(minutes / 60, 2),
            "minutes": minutes,
            "duracao_display": format_duration(minutes),
            "total_atividades": count_by_colaborador[colaborador],
        }
        for colaborador, minutes in sorted(
            minutes_by_colaborador.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    return {
        "errors": errors,
        "activities": activities,
        "hours_by_colaborador": hours_by_colaborador,
        "summary": {
            "total_atividades": len(activities),
            "total_minutos": total_minutes,
            "total_horas": round(total_minutes / 60, 2),
            "total_horas_display": format_duration(total_minutes),
            "atividades_concluidas": completed,
            "atividades_pendentes": pending_or_progress,
        },
        "status_options": STATUS_OPTIONS,
    }
