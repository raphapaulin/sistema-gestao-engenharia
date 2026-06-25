import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DATABASE_PATH = PROJECT_ROOT / "data" / "demo.db"
DEMO_EMAIL = "admin@demo.local"
DEMO_PASSWORD = "demo12345"
PBKDF2_ITERATIONS = 260_000


CLIENTES = [
    (1, "Condominio Jardim Central", "Residencial Jardim Central", "00000000001", "cliente01@example.com"),
    (2, "Clinica Vida Plena", "Clinica Vida Plena", "00000000002", "cliente02@example.com"),
    (3, "Escola Tecnica Horizonte", "Instituto Horizonte", "00000000003", "cliente03@example.com"),
    (4, "Industria Metal Forte", "Metal Forte Demo", "00000000004", "cliente04@example.com"),
    (5, "Mercado Bela Vista", "Mercado Bela Vista", "00000000005", "cliente05@example.com"),
    (6, "Academia Movimento", "Academia Movimento", "00000000006", "cliente06@example.com"),
    (7, "Hotel Solaris", "Hotel Solaris", "00000000007", "cliente07@example.com"),
    (8, "Restaurante Dona Praca", "Restaurante Dona Praca", "00000000008", "cliente08@example.com"),
    (9, "Laboratorio Alfa", "Laboratorio Alfa", "00000000009", "cliente09@example.com"),
    (10, "Centro Comercial Aurora", "Centro Comercial Aurora", "00000000010", "cliente10@example.com"),
    (11, "Galpao Logistico Norte", "Logistica Norte Demo", "00000000011", "cliente11@example.com"),
    (12, "Hospital Modelo Sul", "Hospital Modelo Sul", "00000000012", "cliente12@example.com"),
    (13, "Edificio Mirante", "Condominio Edificio Mirante", "00000000013", "cliente13@example.com"),
    (14, "Parque Infantil Estrela", "Parque Infantil Estrela", "00000000014", "cliente14@example.com"),
    (15, "Oficina Mecanica Avenida", "Oficina Avenida", "00000000015", "cliente15@example.com"),
    (16, "Shopping Portal Leste", "Shopping Portal Leste", "00000000016", "cliente16@example.com"),
]

COLABORADORES = [
    (1, "Marina Duarte", "Engenheiro Responsavel", "marina.duarte@example.com", "00000001001", "Equipe Tecnica", "CREA-DEMO-0001", 1),
    (2, "Lucas Nogueira", "Estagiario de Engenharia", "lucas.nogueira@example.com", "00000001002", "Equipe Tecnica", "EST-DEMO-0002", 2),
    (3, "Camila Torres", "Tecnico de Campo", "camila.torres@example.com", "00000001003", "Equipe Tecnica", "TEC-DEMO-0003", 3),
    (4, "Renato Lima", "Analista de Projetos", "renato.lima@example.com", "00000001004", "Equipe Projetos", "PROJ-DEMO-0004", 4),
    (5, "Beatriz Ramos", "Auxiliar Administrativo", "beatriz.ramos@example.com", "00000001005", "Administrativo", "ADM-DEMO-0005", 5),
    (6, "Felipe Rocha", "Supervisor Tecnico", "felipe.rocha@example.com", "00000001006", "Equipe Tecnica", "SUP-DEMO-0006", 6),
    (7, "Sofia Martins", "Engenheiro de Seguranca", "sofia.martins@example.com", "00000001007", "Equipe Tecnica", "CREA-DEMO-0007", 7),
]

ENGENHEIROS = [
    (1, "Marina Duarte", "CREA-DEMO-0001", "Engenharia Mecanica"),
    (2, "Lucas Nogueira", "EST-DEMO-0002", "Engenharia em Formacao"),
    (3, "Camila Torres", "TEC-DEMO-0003", "Inspecoes Tecnicas"),
    (4, "Renato Lima", "PROJ-DEMO-0004", "Projetos de Engenharia"),
    (5, "Beatriz Ramos", "ADM-DEMO-0005", "Apoio Administrativo"),
    (6, "Felipe Rocha", "SUP-DEMO-0006", "Supervisao Tecnica"),
    (7, "Sofia Martins", "CREA-DEMO-0007", "Engenharia de Seguranca"),
]

SERVICOS = [
    (1, "Laudo NR12", "Avaliacao de seguranca em maquinas e equipamentos.", 2800.00),
    (2, "Laudo NR13", "Inspecao de vasos de pressao e sistemas pressurizados.", 3400.00),
    (3, "Laudo de Ruido", "Medicao e analise de niveis de ruido ocupacional.", 1900.00),
    (4, "Laudo de Vibracao", "Analise de vibracoes em maquinas e estruturas.", 2300.00),
    (5, "ART de Ar Condicionado", "Emissao de ART para sistemas de climatizacao.", 1300.00),
    (6, "Inspecao Tecnica de Elevador", "Vistoria tecnica em elevadores e plataformas.", 3100.00),
    (7, "Laudo de Playground", "Inspecao de brinquedos e areas recreativas.", 2600.00),
    (8, "Projeto de Exaustao", "Projeto tecnico para ventilacao e exaustao.", 4200.00),
    (9, "Projeto de Refrigeracao", "Projeto de sistemas de refrigeracao comercial.", 5200.00),
    (10, "Relatorio Tecnico de Conformidade", "Relatorio de conformidade tecnica para operacao.", 2400.00),
    (11, "Vistoria Tecnica", "Vistoria de campo com registro tecnico.", 1600.00),
    (12, "Medicao Acustica", "Medicao acustica ambiental e ocupacional.", 2100.00),
    (13, "Plano de Manutencao Preventiva", "Plano tecnico de manutencao preventiva.", 3600.00),
]

STATUS_ORDENS = ["aberta", "em andamento", "concluida"]
STATUS_ATIVIDADES = ["planejada", "em andamento", "concluida", "cancelada"]


def _database_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Popula data/demo.db com dados ficticios de portfolio."
    )
    parser.add_argument(
        "--database",
        default=str(DEMO_DATABASE_PATH),
        help="Banco SQLite demo. Por seguranca, apenas data/demo.db e aceito.",
    )
    return parser.parse_args()


def _resolve_database_path(value: str) -> Path:
    database_path = Path(value)
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path
    database_path = database_path.resolve()
    expected_path = DEMO_DATABASE_PATH.resolve()
    if database_path != expected_path:
        raise SystemExit(
            "Seed demo recusado: este script so pode alterar data/demo.db.\n"
            f"Recebido: {database_path}\n"
            f"Esperado: {expected_path}"
        )
    return database_path


def _hash_password(password: str) -> str:
    salt = "demo_public_salt_2026"
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${password_hash}"


def _init_schema(database_path: Path) -> None:
    os.environ["DATABASE_URL"] = _database_url(database_path)
    sys.path.insert(0, str(PROJECT_ROOT))
    from backend.database import init_db

    init_db()


def _duration_minutes(start: str, end: str) -> int:
    start_hour, start_minute = [int(part) for part in start.split(":")]
    end_hour, end_minute = [int(part) for part in end.split(":")]
    return (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)


def _insert_base_data(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO Cliente (id_cliente, nome, empresa, telefone, email)
        VALUES (?, ?, ?, ?, ?)
        """,
        CLIENTES,
    )
    connection.executemany(
        """
        INSERT INTO Engenheiro (id_engenheiro, nome, crea, especialidade)
        VALUES (?, ?, ?, ?)
        """,
        ENGENHEIROS,
    )
    connection.executemany(
        """
        INSERT INTO Colaborador (
            id_colaborador,
            nome,
            cargo,
            email,
            telefone,
            tipo_vinculo,
            registro_profissional,
            ativo,
            legacy_engenheiro_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        COLABORADORES,
    )
    connection.executemany(
        """
        INSERT INTO Servico (id_servico, nome, descricao, preco_base)
        VALUES (?, ?, ?, ?)
        """,
        SERVICOS,
    )

    vinculos = []
    for id_engenheiro, _, _, _ in ENGENHEIROS:
        for id_servico in range(1, len(SERVICOS) + 1):
            if (id_engenheiro + id_servico) % 3 == 0:
                nivel = ["junior", "pleno", "senior"][(id_engenheiro + id_servico) % 3]
                vinculos.append((id_engenheiro, id_servico, nivel))
    connection.executemany(
        """
        INSERT INTO Engenheiro_Servico (id_engenheiro, id_servico, nivel_experiencia)
        VALUES (?, ?, ?)
        """,
        vinculos,
    )


def _build_orders(today: date) -> list[tuple]:
    orders = []
    offsets = [-118, -111, -104, -97, -90, -83, -76, -69, -62, -55, -48, -42]
    offsets += [-36, -31, -27, -23, -19, -15, -12, -9, -6, -4, -2, -1]
    offsets += [0, 2, 4, 7, 10, 13, 16, 20, 24, 28, 32, 36]

    collaborator_pattern = [1, 1, 1, 2, 2, 3, 4, 4, 5, 6, 6, 7]
    for index, offset in enumerate(offsets, start=1):
        order_date = today + timedelta(days=offset)
        if offset < -12:
            status = "concluida" if index % 5 else "em andamento"
        elif offset <= 4:
            status = STATUS_ORDENS[index % len(STATUS_ORDENS)]
        else:
            status = "aberta" if index % 2 else "em andamento"

        id_cliente = ((index - 1) % len(CLIENTES)) + 1
        id_servico = ((index * 2) % len(SERVICOS)) + 1
        id_colaborador = collaborator_pattern[(index - 1) % len(collaborator_pattern)]
        orders.append(
            (
                index,
                order_date.isoformat(),
                status,
                id_cliente,
                id_colaborador,
                id_servico,
                id_colaborador,
            )
        )
    return orders


def _insert_orders(connection: sqlite3.Connection, orders: list[tuple]) -> None:
    connection.executemany(
        """
        INSERT INTO Ordem_Servico (
            id_ordem,
            data_abertura,
            status,
            id_cliente,
            id_engenheiro,
            id_servico,
            id_colaborador
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        orders,
    )


def _insert_payments(connection: sqlite3.Connection, orders: list[tuple], today: date) -> None:
    service_prices = {id_servico: preco for id_servico, _, _, preco in SERVICOS}
    payments = []
    for index, order in enumerate(orders, start=1):
        id_ordem, data_abertura, order_status, _, _, id_servico, _ = order
        base_value = service_prices[id_servico]
        multiplier = [0.9, 1.0, 1.12, 1.25][index % 4]
        value = round(base_value * multiplier + (index % 5) * 180, 2)

        order_date = date.fromisoformat(data_abertura)
        if order_status == "concluida" and index % 4 != 0:
            status = "pago"
        elif order_date < today and index % 5 == 0:
            status = "pago"
        else:
            status = "pendente"

        payment_date = None
        if status == "pago":
            payment_date = min(order_date + timedelta(days=8 + index % 5), today).isoformat()

        payments.append((index, value, status, payment_date, id_ordem))

    connection.executemany(
        """
        INSERT INTO Pagamento (id_pagamento, valor, status, data_pagamento, id_ordem)
        VALUES (?, ?, ?, ?, ?)
        """,
        payments,
    )


def _activity_tuple(
    activity_id: int,
    title: str,
    description: str,
    activity_date: date,
    start: str,
    end: str,
    status: str,
    id_colaborador: int,
    id_cliente: int | None,
    id_servico: int | None,
    id_ordem: int | None,
    notes: str,
) -> tuple:
    return (
        activity_id,
        title,
        description,
        activity_date.isoformat(),
        start,
        end,
        _duration_minutes(start, end),
        status,
        id_colaborador,
        id_cliente,
        id_servico,
        id_ordem,
        notes,
    )


def _build_activities(today: date, orders: list[tuple]) -> list[tuple]:
    order_by_id = {order[0]: order for order in orders}
    activities = []
    next_id = 1

    special_today = [
        ("Inspecao NR12 em campo", "Visita tecnica e checklist de seguranca.", 1, 1, "08:00", "10:00", "em andamento"),
        ("Analise de documentacao tecnica", "Conferencia de documentos recebidos.", 2, 1, "10:00", "12:00", "em andamento"),
        ("Vistoria de equipamentos", "Verificacao de itens criticos de operacao.", 3, 1, "13:00", "15:00", "planejada"),
        ("Reuniao de fechamento tecnico", "Alinhamento de pendencias com cliente demo.", 4, 1, "15:00", "18:00", "planejada"),
        ("Levantamento em campo", "Coleta de informacoes para relatorio tecnico.", 5, 2, "09:00", "10:30", "em andamento"),
        ("Revisao de memorial", "Revisao de escopo e anexos tecnicos.", 6, 2, "13:30", "15:00", "planejada"),
        ("Modelagem de proposta tecnica", "Preparacao de escopo para projeto.", 7, 4, "08:30", "10:00", "concluida"),
        ("Atualizacao de cronograma", "Organizacao de prazos da equipe demo.", 8, 4, "11:00", "12:00", "planejada"),
        ("Validacao de evidencias", "Conferencia de fotos e registros de campo.", 9, 4, "16:00", "17:30", "planejada"),
    ]
    for title, description, order_id, collaborator_id, start, end, status in special_today:
        order = order_by_id[order_id]
        activities.append(
            _activity_tuple(
                next_id,
                title,
                description,
                today,
                start,
                end,
                status,
                collaborator_id,
                order[3],
                order[5],
                order_id,
                "Atividade criada para demonstrar agenda e disponibilidade.",
            )
        )
        next_id += 1

    titles = [
        "Vistoria tecnica programada",
        "Elaboracao de laudo tecnico",
        "Revisao de relatorio",
        "Coleta de evidencias em campo",
        "Reuniao de alinhamento operacional",
        "Conferencia de normas aplicaveis",
        "Desenho de solucao tecnica",
        "Planejamento de manutencao",
        "Validacao de medições",
        "Organizacao de documentos",
    ]
    slots = [
        ("08:00", "09:30"),
        ("09:45", "11:15"),
        ("11:00", "12:00"),
        ("13:00", "14:30"),
        ("14:45", "16:15"),
        ("16:15", "17:45"),
    ]
    collaborator_pattern = [1, 1, 1, 1, 2, 2, 3, 4, 4, 5, 6, 6, 7]
    status_by_period = {
        "past": ["concluida", "concluida", "concluida", "cancelada"],
        "recent": ["concluida", "em andamento", "planejada", "cancelada"],
        "future": ["planejada", "planejada", "em andamento", "planejada"],
    }

    for index in range(75):
        order_id = ((index * 5) % len(orders)) + 1
        order = order_by_id[order_id]

        if index < 45:
            activity_date = today - timedelta(days=2 + ((index * 3) % 120))
            period = "past"
        elif index < 58:
            activity_date = today - timedelta(days=1 + (index % 14))
            period = "recent"
        else:
            activity_date = today + timedelta(days=1 + ((index - 58) * 2))
            period = "future"

        id_colaborador = collaborator_pattern[index % len(collaborator_pattern)]
        if id_colaborador == 3 and activity_date == today:
            activity_date += timedelta(days=1)

        start, end = slots[index % len(slots)]
        status_options = status_by_period[period]
        status = status_options[index % len(status_options)]
        has_order = index % 6 != 0
        id_cliente = order[3] if has_order else ((index % len(CLIENTES)) + 1)
        id_servico = order[5] if has_order else (((index * 3) % len(SERVICOS)) + 1)
        linked_order_id = order_id if has_order else None

        title = titles[index % len(titles)]
        service_name = SERVICOS[id_servico - 1][1]
        activities.append(
            _activity_tuple(
                next_id,
                title,
                f"{title} para {service_name.lower()} em ambiente demo.",
                activity_date,
                start,
                end,
                status,
                id_colaborador,
                id_cliente,
                id_servico,
                linked_order_id,
                "Registro ficticio gerado pelo seed demo.",
            )
        )
        next_id += 1

    return activities


def _insert_activities(connection: sqlite3.Connection, activities: list[tuple]) -> None:
    connection.executemany(
        """
        INSERT INTO Atividade (
            id_atividade,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        activities,
    )


def _recreate_demo_user(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM Usuario")
    connection.execute(
        """
        INSERT INTO Usuario (id_usuario, nome, email, senha_hash, perfil, ativo, atualizado_em, ultimo_login)
        VALUES (1, ?, ?, ?, 'Administrador', 1, ?, NULL)
        """,
        (
            "Administrador Demo",
            DEMO_EMAIL,
            _hash_password(DEMO_PASSWORD),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )


def _clear_demo_data(connection: sqlite3.Connection) -> None:
    for table_name in [
        "Atividade",
        "Pagamento",
        "Ordem_Servico",
        "Engenheiro_Servico",
        "Servico",
        "Colaborador",
        "Engenheiro",
        "Cliente",
    ]:
        connection.execute(f"DELETE FROM {table_name}")


def _seed(database_path: Path) -> dict[str, int]:
    _init_schema(database_path)
    today = date.today()
    orders = _build_orders(today)
    activities = _build_activities(today, orders)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _clear_demo_data(connection)
        _recreate_demo_user(connection)
        _insert_base_data(connection)
        _insert_orders(connection, orders)
        _insert_payments(connection, orders, today)
        _insert_activities(connection, activities)
        connection.commit()

    with sqlite3.connect(database_path) as connection:
        connection.execute("VACUUM")

    return {
        "clientes": len(CLIENTES),
        "colaboradores": len(COLABORADORES),
        "servicos": len(SERVICOS),
        "ordens": len(orders),
        "pagamentos": len(orders),
        "atividades": len(activities),
    }


def main() -> None:
    args = _parse_args()
    database_path = _resolve_database_path(args.database)
    counts = _seed(database_path)

    print("Banco demo populado com sucesso.")
    print(f"Banco: {database_path}")
    for label, total in counts.items():
        print(f"{label}: {total}")
    print(f"Login demo: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
