-- Schema de referencia da versao demo.
-- Este arquivo nao contem dados reais nem inserts com pessoas, empresas,
-- telefones ou e-mails de terceiros.

CREATE TABLE Cliente (
    id_cliente INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    empresa TEXT,
    telefone TEXT,
    email TEXT UNIQUE
);

CREATE TABLE Engenheiro (
    id_engenheiro INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    crea TEXT UNIQUE NOT NULL,
    especialidade TEXT
);

CREATE TABLE Servico (
    id_servico INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco_base REAL
);

CREATE TABLE Engenheiro_Servico (
    id_engenheiro INTEGER,
    id_servico INTEGER,
    nivel_experiencia TEXT CHECK (
        nivel_experiencia IN ('junior', 'pleno', 'senior')
    ),
    PRIMARY KEY (id_engenheiro, id_servico),
    FOREIGN KEY (id_engenheiro) REFERENCES Engenheiro(id_engenheiro),
    FOREIGN KEY (id_servico) REFERENCES Servico(id_servico)
);

CREATE TABLE Ordem_Servico (
    id_ordem INTEGER PRIMARY KEY,
    data_abertura TEXT,
    status TEXT CHECK (
        status IN ('aberta', 'em andamento', 'concluida')
    ),
    id_cliente INTEGER,
    id_engenheiro INTEGER,
    id_servico INTEGER,
    id_colaborador INTEGER,
    FOREIGN KEY (id_cliente) REFERENCES Cliente(id_cliente),
    FOREIGN KEY (id_engenheiro) REFERENCES Engenheiro(id_engenheiro),
    FOREIGN KEY (id_servico) REFERENCES Servico(id_servico)
);

CREATE TABLE Pagamento (
    id_pagamento INTEGER PRIMARY KEY,
    valor REAL,
    status TEXT CHECK (
        status IN ('pago', 'pendente')
    ),
    data_pagamento TEXT,
    id_ordem INTEGER UNIQUE,
    FOREIGN KEY (id_ordem) REFERENCES Ordem_Servico(id_ordem)
);

CREATE TABLE Colaborador (
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
);

CREATE TABLE Atividade (
    id_atividade INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    descricao TEXT,
    data_atividade TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fim TEXT NOT NULL,
    duracao_minutos INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
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
);

CREATE TABLE Usuario (
    id_usuario INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL CHECK (
        perfil IN ('Administrador', 'Colaborador', 'Visualizador')
    ),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT,
    ultimo_login TEXT
);
