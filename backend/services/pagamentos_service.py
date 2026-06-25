from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


STATUS_OPTIONS = [
    {"value": "pago", "label": "Pago"},
    {"value": "pendente", "label": "Pendente"},
]

STATUS_LABELS = {item["value"]: item["label"] for item in STATUS_OPTIONS}

ORDER_STATUS_LABELS = {
    "aberta": "Aberta",
    "em andamento": "Em andamento",
    "concluida": "Concluída",
}


@dataclass
class PagamentoForm:
    id_ordem: str = ""
    valor: str = ""
    status: str = "pendente"
    data_pagamento: str = ""


def _clean(value: str | None) -> str:
    return (value or "").strip()


def today_iso() -> str:
    return date.today().isoformat()


def normalize_pagamento_form(
    id_ordem: str | None,
    valor: str | None,
    status: str | None,
    data_pagamento: str | None,
) -> PagamentoForm:
    return PagamentoForm(
        id_ordem=_clean(id_ordem),
        valor=_clean(valor),
        status=_clean(status) or "pendente",
        data_pagamento=_clean(data_pagamento),
    )


def _format_currency(value: float | None) -> str:
    if value is None:
        return "-"

    formatted = f"R$ {value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_value_input(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def parse_valor(value: str) -> float | None:
    value = _clean(value)
    if not value:
        raise ValueError("Informe o valor do pagamento.")

    normalized = value.replace("R$", "").replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")

    try:
        valor = float(normalized)
    except ValueError:
        raise ValueError("Valor deve ser numérico.")

    if valor < 0:
        raise ValueError("Valor deve ser maior ou igual a zero.")

    return valor


def _with_display_fields(pagamento: dict) -> dict:
    pagamento["valor_display"] = _format_currency(pagamento.get("valor"))
    pagamento["valor_form"] = _format_value_input(pagamento.get("valor"))
    pagamento["status_label"] = STATUS_LABELS.get(
        pagamento["status"],
        pagamento["status"],
    )
    pagamento["status_ordem_label"] = ORDER_STATUS_LABELS.get(
        pagamento.get("status_ordem"),
        pagamento.get("status_ordem"),
    )
    pagamento["preco_base_display"] = _format_currency(pagamento.get("preco_base"))
    return pagamento


def _base_pagamentos_sql(where_clause: str = "") -> str:
    return f"""
        SELECT
            p.id_pagamento,
            p.valor,
            p.status,
            p.data_pagamento,
            p.id_ordem,
            os.data_abertura,
            os.status AS status_ordem,
            c.nome AS cliente,
            s.nome AS servico,
            s.preco_base
        FROM Pagamento p
        JOIN Ordem_Servico os ON os.id_ordem = p.id_ordem
        JOIN Cliente c ON c.id_cliente = os.id_cliente
        JOIN Servico s ON s.id_servico = os.id_servico
        {where_clause}
        ORDER BY p.id_pagamento DESC
    """


def list_pagamentos(
    db: Session,
    search: str = "",
    status: str = "",
    data_inicio: str = "",
    data_fim: str = "",
) -> list[dict]:
    filters = []
    params = {}

    search = _clean(search)
    status = _clean(status)
    data_inicio = _clean(data_inicio)
    data_fim = _clean(data_fim)

    if search:
        filters.append(
            """
            (
                LOWER(c.nome) LIKE :search
                OR LOWER(s.nome) LIKE :search
                OR CAST(os.id_ordem AS TEXT) LIKE :search
                OR CAST(p.id_pagamento AS TEXT) LIKE :search
            )
            """
        )
        params["search"] = f"%{search.lower()}%"

    if status in STATUS_LABELS:
        filters.append("p.status = :status")
        params["status"] = status

    if data_inicio:
        filters.append("p.data_pagamento >= :data_inicio")
        params["data_inicio"] = data_inicio

    if data_fim:
        filters.append("p.data_pagamento <= :data_fim")
        params["data_fim"] = data_fim

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(text(_base_pagamentos_sql(where_clause)), params).mappings()
    return [_with_display_fields(dict(row)) for row in rows]


def get_pagamento(db: Session, pagamento_id: int) -> dict | None:
    row = db.execute(
        text(_base_pagamentos_sql("WHERE p.id_pagamento = :pagamento_id")),
        {"pagamento_id": pagamento_id},
    ).mappings().first()
    return _with_display_fields(dict(row)) if row else None


def list_ordens_options(
    db: Session,
    current_ordem_id: int | None = None,
) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                os.id_ordem AS id,
                os.data_abertura,
                os.status AS status_ordem,
                c.nome AS cliente,
                s.nome AS servico,
                s.preco_base,
                p.id_pagamento
            FROM Ordem_Servico os
            JOIN Cliente c ON c.id_cliente = os.id_cliente
            JOIN Servico s ON s.id_servico = os.id_servico
            LEFT JOIN Pagamento p ON p.id_ordem = os.id_ordem
            WHERE p.id_pagamento IS NULL
               OR os.id_ordem = :current_ordem_id
            ORDER BY os.data_abertura DESC, os.id_ordem DESC
            """
        ),
        {"current_ordem_id": current_ordem_id},
    ).mappings()

    options = []
    for row in rows:
        option = dict(row)
        option["status_ordem_label"] = ORDER_STATUS_LABELS.get(
            option["status_ordem"],
            option["status_ordem"],
        )
        option["preco_base_display"] = _format_currency(option["preco_base"])
        options.append(option)
    return options


def validate_pagamento_form(
    db: Session,
    form: PagamentoForm,
    pagamento_id: int | None = None,
) -> tuple[list[str], dict]:
    errors = []

    if not form.id_ordem:
        errors.append("Selecione uma ordem de serviço.")
        id_ordem = None
    else:
        try:
            id_ordem = int(form.id_ordem)
        except ValueError:
            id_ordem = None
            errors.append("Ordem de serviço inválida.")

    if id_ordem and not _ordem_exists(db, id_ordem):
        errors.append("Ordem de serviço selecionada não foi encontrada.")

    if id_ordem and pagamento_for_order_exists(db, id_ordem, pagamento_id):
        errors.append("Esta ordem de serviço já possui pagamento cadastrado.")

    try:
        valor = parse_valor(form.valor)
    except ValueError as exc:
        valor = None
        errors.append(str(exc))

    if form.status not in STATUS_LABELS:
        errors.append("Selecione um status válido.")

    data_pagamento = form.data_pagamento or None
    if form.status == "pago":
        if not data_pagamento:
            errors.append("Informe a data de pagamento para pagamentos pagos.")
        else:
            _validate_date(data_pagamento, errors)
    elif data_pagamento:
        _validate_date(data_pagamento, errors)

    if form.status == "pendente":
        data_pagamento = None

    data = {
        "id_ordem": id_ordem,
        "valor": valor,
        "status": form.status,
        "data_pagamento": data_pagamento,
    }
    return errors, data


def _validate_date(value: str, errors: list[str]) -> None:
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append("Informe uma data de pagamento válida.")


def _ordem_exists(db: Session, ordem_id: int) -> bool:
    row = db.execute(
        text("SELECT COUNT(*) AS total FROM Ordem_Servico WHERE id_ordem = :ordem_id"),
        {"ordem_id": ordem_id},
    ).mappings().first()
    return bool(row and row["total"])


def pagamento_for_order_exists(
    db: Session,
    ordem_id: int,
    pagamento_id: int | None = None,
) -> bool:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM Pagamento
            WHERE id_ordem = :ordem_id
              AND (:pagamento_id IS NULL OR id_pagamento != :pagamento_id)
            """
        ),
        {"ordem_id": ordem_id, "pagamento_id": pagamento_id},
    ).mappings().first()
    return bool(row and row["total"])


def create_pagamento(db: Session, data: dict) -> int:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO Pagamento (valor, status, data_pagamento, id_ordem)
                VALUES (:valor, :status, :data_pagamento, :id_ordem)
                """
            ),
            data,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar este pagamento.")

    return int(result.lastrowid)


def update_pagamento(db: Session, pagamento_id: int, data: dict) -> None:
    try:
        db.execute(
            text(
                """
                UPDATE Pagamento
                SET
                    valor = :valor,
                    status = :status,
                    data_pagamento = :data_pagamento,
                    id_ordem = :id_ordem
                WHERE id_pagamento = :pagamento_id
                """
            ),
            {"pagamento_id": pagamento_id, **data},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível salvar este pagamento.")


def update_pagamento_status(db: Session, pagamento_id: int, status: str) -> None:
    if status not in STATUS_LABELS:
        raise ValueError("Selecione um status válido.")

    data_pagamento_sql = "COALESCE(data_pagamento, :today)" if status == "pago" else "NULL"
    db.execute(
        text(
            f"""
            UPDATE Pagamento
            SET status = :status,
                data_pagamento = {data_pagamento_sql}
            WHERE id_pagamento = :pagamento_id
            """
        ),
        {
            "pagamento_id": pagamento_id,
            "status": status,
            "today": today_iso(),
        },
    )
    db.commit()


def delete_pagamento(db: Session, pagamento_id: int) -> None:
    try:
        db.execute(
            text("DELETE FROM Pagamento WHERE id_pagamento = :pagamento_id"),
            {"pagamento_id": pagamento_id},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Não foi possível excluir este pagamento.")
