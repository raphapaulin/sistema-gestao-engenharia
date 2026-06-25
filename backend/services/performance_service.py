from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.atividades_service import STATUS_LABELS, STATUS_OPTIONS, format_duration


STATUS_ORDER = ["planejada", "em andamento", "concluida", "cancelada"]


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _parse_optional_int(value: str, errors: list[str], label: str) -> int | None:
    value = _clean(value)
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        errors.append(f"Seleção inválida para {label}.")
        return None


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


def _empty_summary() -> dict:
    return {
        "total_colaboradores": 0,
        "total_atividades": 0,
        "total_minutos": 0,
        "total_horas": 0,
        "total_horas_display": format_duration(0),
        "atividades_concluidas": 0,
        "atividades_pendentes": 0,
        "colaborador_mais_horas": None,
        "colaborador_mais_concluidas": None,
        "colaborador_maior_taxa": None,
    }


def _empty_status_counts() -> dict[str, int]:
    return {status: 0 for status in STATUS_ORDER}


def _format_percent(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def _colaborador_base(row: dict) -> dict:
    return {
        "id_colaborador": row["id_colaborador"],
        "nome": row["nome"],
        "cargo": row["cargo"] or "-",
        "total_atividades": 0,
        "status_counts": _empty_status_counts(),
        "planejadas": 0,
        "em_andamento": 0,
        "concluidas": 0,
        "canceladas": 0,
        "pendentes": 0,
        "total_minutos": 0,
        "total_horas": 0,
        "total_horas_display": format_duration(0),
        "tempo_medio_minutos": 0,
        "tempo_medio_display": format_duration(0),
        "percentual_conclusao": 0,
        "percentual_conclusao_display": _format_percent(0),
    }


def _list_colaboradores(db: Session, colaborador_id: int | None = None) -> list[dict]:
    filters = ["ativo = 1"]
    params = {}

    if colaborador_id:
        filters.append("id_colaborador = :colaborador_id")
        params["colaborador_id"] = colaborador_id

    rows = db.execute(
        text(
            f"""
            SELECT id_colaborador, nome, cargo
            FROM Colaborador
            WHERE {' AND '.join(filters)}
            ORDER BY nome
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def _list_activities(
    db: Session,
    colaborador_id: int | None,
    data_inicio: str,
    data_fim: str,
    status: str,
) -> list[dict]:
    filters = []
    params: dict[str, int | str] = {}

    if colaborador_id:
        filters.append("a.id_colaborador = :colaborador_id")
        params["colaborador_id"] = colaborador_id

    if data_inicio:
        filters.append("a.data_atividade >= :data_inicio")
        params["data_inicio"] = data_inicio

    if data_fim:
        filters.append("a.data_atividade <= :data_fim")
        params["data_fim"] = data_fim

    if status:
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
                a.id_colaborador,
                a.id_cliente,
                a.id_servico,
                a.id_ordem,
                col.nome AS colaborador,
                col.cargo AS cargo,
                c.nome AS cliente,
                s.nome AS servico
            FROM Atividade a
            JOIN Colaborador col ON col.id_colaborador = a.id_colaborador
            LEFT JOIN Cliente c ON c.id_cliente = a.id_cliente
            LEFT JOIN Servico s ON s.id_servico = a.id_servico
            {where_clause}
            ORDER BY col.nome, a.data_atividade DESC, a.hora_inicio DESC, a.id_atividade DESC
            """
        ),
        params,
    ).mappings()

    activities = []
    for row in rows:
        activity = dict(row)
        duration = int(activity["duracao_minutos"] or 0)
        activity["duracao_display"] = format_duration(duration)
        activity["horario_display"] = (
            f"{activity['hora_inicio']} - {activity['hora_fim']}"
            if activity.get("hora_inicio") and activity.get("hora_fim")
            else "-"
        )
        activity["status_label"] = STATUS_LABELS.get(activity["status"], activity["status"])
        activities.append(activity)
    return activities


def _validate_filters(
    id_colaborador: str,
    data_inicio: str,
    data_fim: str,
    status: str,
) -> tuple[list[str], int | None, str, str, str]:
    errors: list[str] = []
    colaborador_id = _parse_optional_int(id_colaborador, errors, "colaborador")
    start_date = _parse_date(data_inicio, errors, "data inicial")
    end_date = _parse_date(data_fim, errors, "data final")
    status = _clean(status)

    if start_date and end_date and start_date > end_date:
        errors.append("A data inicial não pode ser maior que a data final.")

    if status and status not in STATUS_LABELS:
        errors.append("Selecione um status válido.")
        status = ""

    return errors, colaborador_id, start_date, end_date, status


def _build_performance_rows(colaboradores: list[dict], activities: list[dict]) -> list[dict]:
    rows_by_id = {
        colaborador["id_colaborador"]: _colaborador_base(colaborador)
        for colaborador in colaboradores
    }

    for activity in activities:
        colaborador_id = activity["id_colaborador"]
        if colaborador_id not in rows_by_id:
            rows_by_id[colaborador_id] = _colaborador_base(
                {
                    "id_colaborador": colaborador_id,
                    "nome": activity["colaborador"],
                    "cargo": activity["cargo"],
                }
            )

        row = rows_by_id[colaborador_id]
        status = activity["status"]
        duration = int(activity["duracao_minutos"] or 0)

        row["total_atividades"] += 1
        row["total_minutos"] += duration
        if status in row["status_counts"]:
            row["status_counts"][status] += 1

    performance_rows = []
    for row in rows_by_id.values():
        row["planejadas"] = row["status_counts"]["planejada"]
        row["em_andamento"] = row["status_counts"]["em andamento"]
        row["concluidas"] = row["status_counts"]["concluida"]
        row["canceladas"] = row["status_counts"]["cancelada"]
        row["pendentes"] = row["planejadas"] + row["em_andamento"]
        row["total_horas"] = round(row["total_minutos"] / 60, 2)
        row["total_horas_display"] = format_duration(row["total_minutos"])
        row["tempo_medio_minutos"] = (
            round(row["total_minutos"] / row["total_atividades"])
            if row["total_atividades"]
            else 0
        )
        row["tempo_medio_display"] = format_duration(row["tempo_medio_minutos"])
        row["percentual_conclusao"] = (
            round((row["concluidas"] / row["total_atividades"]) * 100, 1)
            if row["total_atividades"]
            else 0
        )
        row["percentual_conclusao_display"] = _format_percent(row["percentual_conclusao"])
        performance_rows.append(row)

    return sorted(
        performance_rows,
        key=lambda item: (-item["total_minutos"], item["nome"]),
    )


def _summary(performance_rows: list[dict]) -> dict:
    total_atividades = sum(row["total_atividades"] for row in performance_rows)
    total_minutos = sum(row["total_minutos"] for row in performance_rows)
    total_concluidas = sum(row["concluidas"] for row in performance_rows)
    total_pendentes = sum(row["pendentes"] for row in performance_rows)

    rows_with_hours = [row for row in performance_rows if row["total_minutos"] > 0]
    rows_with_activities = [row for row in performance_rows if row["total_atividades"] > 0]

    top_hours = max(
        rows_with_hours,
        key=lambda row: (row["total_minutos"], row["total_atividades"]),
        default=None,
    )
    top_completed = max(
        rows_with_activities,
        key=lambda row: (row["concluidas"], row["total_atividades"], row["total_minutos"]),
        default=None,
    )
    top_completion_rate = max(
        rows_with_activities,
        key=lambda row: (row["percentual_conclusao"], row["concluidas"], row["total_atividades"]),
        default=None,
    )

    return {
        "total_colaboradores": len(performance_rows),
        "total_atividades": total_atividades,
        "total_minutos": total_minutos,
        "total_horas": round(total_minutos / 60, 2),
        "total_horas_display": format_duration(total_minutos),
        "atividades_concluidas": total_concluidas,
        "atividades_pendentes": total_pendentes,
        "colaborador_mais_horas": top_hours,
        "colaborador_mais_concluidas": top_completed if top_completed and top_completed["concluidas"] else None,
        "colaborador_maior_taxa": top_completion_rate,
    }


def _charts(performance_rows: list[dict]) -> dict:
    status_distribution = [
        {
            "label": STATUS_LABELS[status],
            "value": sum(row["status_counts"][status] for row in performance_rows),
        }
        for status in STATUS_ORDER
    ]

    return {
        "hours_by_colaborador": [
            {"label": row["nome"], "value": row["total_horas"]}
            for row in performance_rows
        ],
        "activities_by_colaborador": [
            {"label": row["nome"], "value": row["total_atividades"]}
            for row in performance_rows
        ],
        "completion_by_colaborador": [
            {
                "label": row["nome"],
                "concluidas": row["concluidas"],
                "pendentes": row["pendentes"],
            }
            for row in performance_rows
        ],
        "status_distribution": status_distribution,
    }


def _empty_result(errors: list[str]) -> dict:
    return {
        "errors": errors,
        "summary": _empty_summary(),
        "performance_rows": [],
        "activities": [],
        "charts": _charts([]),
    }


def get_performance_data(
    db: Session,
    id_colaborador: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    status: str = "",
) -> dict:
    errors, colaborador_id, start_date, end_date, status = _validate_filters(
        id_colaborador,
        data_inicio,
        data_fim,
        status,
    )
    if errors:
        return _empty_result(errors)

    colaboradores = _list_colaboradores(db, colaborador_id)
    activities = _list_activities(db, colaborador_id, start_date, end_date, status)
    performance_rows = _build_performance_rows(colaboradores, activities)

    return {
        "errors": [],
        "summary": _summary(performance_rows),
        "performance_rows": performance_rows,
        "activities": activities,
        "charts": _charts(performance_rows),
    }


def get_colaborador_performance_detail(
    db: Session,
    colaborador_id: int,
    data_inicio: str = "",
    data_fim: str = "",
    status: str = "",
) -> dict | None:
    data = get_performance_data(
        db,
        id_colaborador=str(colaborador_id),
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status,
    )

    if data["errors"]:
        return data

    if not data["performance_rows"]:
        return None

    row = data["performance_rows"][0]
    status_chart = [
        {"label": STATUS_LABELS[status], "value": row["status_counts"][status]}
        for status in STATUS_ORDER
    ]

    return {
        **data,
        "colaborador": row,
        "status_chart": status_chart,
    }
