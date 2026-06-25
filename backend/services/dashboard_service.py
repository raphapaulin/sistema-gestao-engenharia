from sqlalchemy import text
from sqlalchemy.orm import Session


ORDER_STATUS_OPTIONS = [
    ("aberta", "Aberta"),
    ("em andamento", "Em andamento"),
    ("concluida", "Concluída"),
]

ACTIVITY_STATUS_OPTIONS = [
    ("planejada", "Planejada"),
    ("em andamento", "Em andamento"),
    ("concluida", "Concluída"),
    ("cancelada", "Cancelada"),
]

PAYMENT_STATUS_OPTIONS = [
    ("pago", "Pago"),
    ("pendente", "Pendente"),
]

ORDER_STATUS_DISPLAY = dict(ORDER_STATUS_OPTIONS)
ACTIVITY_STATUS_DISPLAY = dict(ACTIVITY_STATUS_OPTIONS)
PAYMENT_STATUS_DISPLAY = dict(PAYMENT_STATUS_OPTIONS)


def _scalar(db: Session, sql: str):
    value = db.execute(text(sql)).scalar()
    return value or 0


def _format_duration(minutes: int | float | None) -> str:
    if not minutes:
        return "0h"

    hours, remaining_minutes = divmod(int(minutes), 60)
    if hours and remaining_minutes:
        return f"{hours}h{remaining_minutes:02d}"
    if hours:
        return f"{hours}h"
    return f"{remaining_minutes} min"


def _status_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        text(
            """
            SELECT status, COUNT(*) AS total
            FROM Ordem_Servico
            GROUP BY status
            """
        )
    ).mappings()
    return {row["status"]: int(row["total"] or 0) for row in rows}


def _payment_totals(db: Session) -> dict[str, float]:
    rows = db.execute(
        text(
            """
            SELECT status, COALESCE(SUM(valor), 0) AS total
            FROM Pagamento
            GROUP BY status
            """
        )
    ).mappings()
    return {row["status"]: float(row["total"] or 0) for row in rows}


def _payment_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        text(
            """
            SELECT status, COUNT(*) AS total
            FROM Pagamento
            GROUP BY status
            """
        )
    ).mappings()
    return {row["status"]: int(row["total"] or 0) for row in rows}


def _activity_status_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        text(
            """
            SELECT status, COUNT(*) AS total
            FROM Atividade
            GROUP BY status
            """
        )
    ).mappings()
    return {row["status"]: int(row["total"] or 0) for row in rows}


def _hours_by_colaborador(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                col.nome AS label,
                COALESCE(SUM(a.duracao_minutos), 0) AS total_minutos
            FROM Atividade a
            JOIN Colaborador col ON col.id_colaborador = a.id_colaborador
            GROUP BY col.id_colaborador, col.nome
            ORDER BY total_minutos DESC, col.nome
            LIMIT 8
            """
        )
    ).mappings()
    return [
        {
            "label": row["label"],
            "value": round(float(row["total_minutos"] or 0) / 60, 2),
            "minutes": int(row["total_minutos"] or 0),
        }
        for row in rows
    ]


def _services_most_requested(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                s.nome AS label,
                COUNT(os.id_ordem) AS total
            FROM Ordem_Servico os
            JOIN Servico s ON s.id_servico = os.id_servico
            GROUP BY s.id_servico, s.nome
            ORDER BY total DESC, s.nome
            LIMIT 8
            """
        )
    ).mappings()
    return [
        {"label": row["label"], "value": int(row["total"] or 0)}
        for row in rows
    ]


def _top_colaborador_by_hours(db: Session) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT
                col.nome,
                COALESCE(SUM(a.duracao_minutos), 0) AS total_minutos
            FROM Atividade a
            JOIN Colaborador col ON col.id_colaborador = a.id_colaborador
            GROUP BY col.id_colaborador, col.nome
            ORDER BY total_minutos DESC, col.nome
            LIMIT 1
            """
        )
    ).mappings().first()
    if not row:
        return None

    total_minutos = int(row["total_minutos"] or 0)
    return {
        "nome": row["nome"],
        "total_minutos": total_minutos,
        "horas": round(total_minutos / 60, 2),
        "duracao_display": _format_duration(total_minutos),
    }


def _top_service(db: Session) -> dict | None:
    services = _services_most_requested(db)
    if not services:
        return None
    return {
        "nome": services[0]["label"],
        "total": services[0]["value"],
    }


def _top_client(db: Session) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT
                c.nome,
                COUNT(os.id_ordem) AS total
            FROM Ordem_Servico os
            JOIN Cliente c ON c.id_cliente = os.id_cliente
            GROUP BY c.id_cliente, c.nome
            ORDER BY total DESC, c.nome
            LIMIT 1
            """
        )
    ).mappings().first()
    if not row:
        return None
    return {
        "nome": row["nome"],
        "total": int(row["total"] or 0),
    }


def _recent_orders(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                os.id_ordem,
                os.data_abertura,
                os.status,
                c.nome AS cliente,
                COALESCE(col.nome, e.nome, 'Sem responsável') AS colaborador,
                s.nome AS servico,
                p.valor,
                p.status AS status_pagamento
            FROM Ordem_Servico os
            JOIN Cliente c ON c.id_cliente = os.id_cliente
            LEFT JOIN Colaborador col ON col.id_colaborador = os.id_colaborador
            LEFT JOIN Engenheiro e ON e.id_engenheiro = os.id_engenheiro
            JOIN Servico s ON s.id_servico = os.id_servico
            LEFT JOIN Pagamento p ON p.id_ordem = os.id_ordem
            ORDER BY os.data_abertura DESC, os.id_ordem DESC
            LIMIT 5
            """
        )
    ).mappings()
    orders = []
    for row in rows:
        order = dict(row)
        order["status_label"] = ORDER_STATUS_DISPLAY.get(order["status"], order["status"])
        order["status_pagamento_label"] = PAYMENT_STATUS_DISPLAY.get(
            order["status_pagamento"],
            "Sem pagamento",
        )
        order["status_pagamento"] = order["status_pagamento"] or "pendente"
        orders.append(order)
    return orders


def _recent_activities(db: Session) -> list[dict]:
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
                col.nome AS colaborador
            FROM Atividade a
            JOIN Colaborador col ON col.id_colaborador = a.id_colaborador
            ORDER BY a.data_atividade DESC, a.hora_inicio DESC, a.id_atividade DESC
            LIMIT 6
            """
        )
    ).mappings()

    activities = []
    for row in rows:
        activity = dict(row)
        activity["status_label"] = ACTIVITY_STATUS_DISPLAY.get(
            activity["status"],
            activity["status"],
        )
        activity["horario_display"] = (
            f"{activity['hora_inicio']} - {activity['hora_fim']}"
            if activity.get("hora_inicio") and activity.get("hora_fim")
            else "-"
        )
        activity["duracao_display"] = _format_duration(activity.get("duracao_minutos"))
        activities.append(activity)
    return activities


def get_dashboard_data(db: Session) -> dict:
    status_counts = _status_counts(db)
    payment_totals = _payment_totals(db)
    payment_counts = _payment_counts(db)
    activity_status_counts = _activity_status_counts(db)
    hours_by_colaborador = _hours_by_colaborador(db)
    services_most_requested = _services_most_requested(db)
    total_activity_minutes = int(
        _scalar(db, "SELECT COALESCE(SUM(duracao_minutos), 0) FROM Atividade")
    )

    metrics = {
        "total_clientes": _scalar(db, "SELECT COUNT(*) FROM Cliente"),
        "total_colaboradores": _scalar(
            db,
            "SELECT COUNT(*) FROM Colaborador WHERE ativo = 1",
        ),
        "total_servicos": _scalar(db, "SELECT COUNT(*) FROM Servico"),
        "total_ordens": _scalar(db, "SELECT COUNT(*) FROM Ordem_Servico"),
        "ordens_abertas": status_counts.get("aberta", 0),
        "ordens_em_andamento": status_counts.get("em andamento", 0),
        "ordens_concluidas": status_counts.get("concluida", 0),
        "total_recebido": payment_totals.get("pago", 0),
        "total_pendente": payment_totals.get("pendente", 0),
        "pagamentos_pagos": payment_counts.get("pago", 0),
        "pagamentos_pendentes": payment_counts.get("pendente", 0),
    }

    orders_by_status = [
        {
            "label": label,
            "value": status_counts.get(status, 0),
        }
        for status, label in ORDER_STATUS_OPTIONS
    ]

    payment_chart = [
        {"label": label, "value": payment_counts.get(status, 0)}
        for status, label in PAYMENT_STATUS_OPTIONS
    ]

    activities_by_status = [
        {"label": label, "value": activity_status_counts.get(status, 0)}
        for status, label in ACTIVITY_STATUS_OPTIONS
    ]

    operational_summary = {
        "total_atividades": _scalar(db, "SELECT COUNT(*) FROM Atividade"),
        "total_horas": round(total_activity_minutes / 60, 2),
        "total_horas_display": _format_duration(total_activity_minutes),
        "colaborador_mais_horas": _top_colaborador_by_hours(db),
        "servico_mais_solicitado": _top_service(db),
        "cliente_mais_ordens": _top_client(db),
    }

    return {
        "metrics": metrics,
        "operational_summary": operational_summary,
        "orders_by_status": orders_by_status,
        "payment_chart": payment_chart,
        "activities_by_status": activities_by_status,
        "hours_by_colaborador": hours_by_colaborador,
        "services_most_requested": services_most_requested,
        "recent_orders": _recent_orders(db),
        "recent_activities": _recent_activities(db),
    }
