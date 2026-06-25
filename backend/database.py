from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Cliente (
                    id_cliente INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL,
                    empresa TEXT,
                    telefone TEXT,
                    email TEXT UNIQUE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Engenheiro (
                    id_engenheiro INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL,
                    crea TEXT UNIQUE,
                    especialidade TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Servico (
                    id_servico INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL,
                    descricao TEXT,
                    preco_base REAL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Engenheiro_Servico (
                    id_engenheiro INTEGER,
                    id_servico INTEGER,
                    nivel_experiencia TEXT CHECK(
                        nivel_experiencia IN ('junior','pleno','senior')
                    ),
                    PRIMARY KEY (id_engenheiro, id_servico),
                    FOREIGN KEY (id_engenheiro) REFERENCES Engenheiro(id_engenheiro),
                    FOREIGN KEY (id_servico) REFERENCES Servico(id_servico)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Ordem_Servico (
                    id_ordem INTEGER PRIMARY KEY,
                    data_abertura TEXT,
                    status TEXT CHECK(
                        status IN ('aberta','em andamento','concluida')
                    ),
                    id_cliente INTEGER,
                    id_engenheiro INTEGER,
                    id_servico INTEGER,
                    FOREIGN KEY (id_cliente) REFERENCES Cliente(id_cliente),
                    FOREIGN KEY (id_engenheiro) REFERENCES Engenheiro(id_engenheiro),
                    FOREIGN KEY (id_servico) REFERENCES Servico(id_servico)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Pagamento (
                    id_pagamento INTEGER PRIMARY KEY,
                    valor REAL,
                    status TEXT CHECK(
                        status IN ('pago','pendente')
                    ),
                    data_pagamento TEXT,
                    id_ordem INTEGER UNIQUE,
                    FOREIGN KEY (id_ordem) REFERENCES Ordem_Servico(id_ordem)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Colaborador (
                    id_colaborador INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL,
                    cargo TEXT NOT NULL,
                    email TEXT,
                    telefone TEXT,
                    tipo_vinculo TEXT,
                    registro_profissional TEXT,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    legacy_engenheiro_id INTEGER UNIQUE,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Usuario (
                    id_usuario INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    senha_hash TEXT NOT NULL,
                    perfil TEXT NOT NULL CHECK(
                        perfil IN ('Administrador', 'Colaborador', 'Visualizador')
                    ),
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT,
                    ultimo_login TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_usuario_email
                ON Usuario(LOWER(email))
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_colaborador_email_ativo
                ON Colaborador(LOWER(email))
                WHERE email IS NOT NULL
                  AND email != ''
                  AND ativo = 1
                """
            )
        )

        total_colaboradores = connection.execute(
            text("SELECT COUNT(*) FROM Colaborador")
        ).scalar()

        total_engenheiros = connection.execute(
            text("SELECT COUNT(*) FROM Engenheiro")
        ).scalar()

        if total_colaboradores == 0 and total_engenheiros:
            connection.execute(
                text(
                    """
                    INSERT INTO Colaborador (
                        nome,
                        cargo,
                        tipo_vinculo,
                        registro_profissional,
                        legacy_engenheiro_id
                    )
                    SELECT
                        nome,
                        'Engenheiro Responsável',
                        'Equipe Técnica',
                        crea,
                        id_engenheiro
                    FROM Engenheiro
                    """
                )
            )

        ordem_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(Ordem_Servico)"))
        }

        if "id_colaborador" not in ordem_columns:
            connection.execute(
                text("ALTER TABLE Ordem_Servico ADD COLUMN id_colaborador INTEGER")
            )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_ordem_servico_colaborador
                ON Ordem_Servico(id_colaborador)
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE Ordem_Servico
                SET id_colaborador = (
                    SELECT c.id_colaborador
                    FROM Colaborador c
                    WHERE c.legacy_engenheiro_id = Ordem_Servico.id_engenheiro
                    LIMIT 1
                )
                WHERE id_colaborador IS NULL
                  AND id_engenheiro IS NOT NULL
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS Atividade (
                    id_atividade INTEGER PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    descricao TEXT,
                    data_atividade TEXT NOT NULL,
                    hora_inicio TEXT NOT NULL,
                    hora_fim TEXT NOT NULL,
                    duracao_minutos INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(
                        status IN ('planejada', 'em andamento', 'concluida', 'cancelada')
                    ),
                    id_colaborador INTEGER NOT NULL,
                    id_cliente INTEGER,
                    id_servico INTEGER,
                    id_ordem INTEGER,
                    observacoes TEXT,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT,
                    FOREIGN KEY (id_colaborador) REFERENCES Colaborador(id_colaborador),
                    FOREIGN KEY (id_cliente) REFERENCES Cliente(id_cliente),
                    FOREIGN KEY (id_servico) REFERENCES Servico(id_servico),
                    FOREIGN KEY (id_ordem) REFERENCES Ordem_Servico(id_ordem)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_atividade_data
                ON Atividade(data_atividade)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_atividade_colaborador
                ON Atividade(id_colaborador)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_atividade_status
                ON Atividade(status)
                """
            )
        )
