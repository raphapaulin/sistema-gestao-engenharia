# Sistema de Gestao de Engenharia

Sistema web demo para gestao integrada de uma empresa de engenharia, com controle de clientes, colaboradores, servicos, ordens de servico, pagamentos, atividades, cronograma, disponibilidade da equipe e indicadores operacionais.

## Tecnologias Utilizadas

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Jinja2
- Bootstrap 5
- Chart.js

## Funcionalidades

- Autenticacao e login
- Dashboard geral com indicadores operacionais e financeiros
- Gestao de clientes
- Gestao de colaboradores
- Catalogo de servicos
- Ordens de servico com acompanhamento de status
- Controle de pagamentos
- Registro e acompanhamento de atividades
- Cronograma operacional
- Analise de disponibilidade da equipe
- Indicadores de performance dos colaboradores
- Backup local do banco demo

## Banco de Demonstracao

O projeto inclui um banco SQLite de demonstracao em:

```text
data/demo.db
```

Os dados sao ficticios e servem para testar as funcionalidades, navegar pelos modulos e visualizar os dashboards com informacoes preenchidas.

Para recriar a base de demonstracao com dados ficticios:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

## Login Demo

```text
E-mail: admin@demo.local
Senha: demo12345
```

## Como Executar

Crie o ambiente virtual:

```powershell
py -m venv .venv
```

Instale as dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Inicie o sistema pelo atalho:

```powershell
.\iniciar_sistema.bat
```

Acesse no navegador:

```text
http://127.0.0.1:8000/
```

### Execucao Manual

Tambem e possivel iniciar o servidor manualmente:

```powershell
$env:DATABASE_URL="sqlite:///data/demo.db"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

## Modulos Disponiveis

- Dashboard: `http://127.0.0.1:8000/`
- Clientes: `http://127.0.0.1:8000/clientes`
- Colaboradores: `http://127.0.0.1:8000/colaboradores`
- Servicos: `http://127.0.0.1:8000/servicos`
- Ordens de Servico: `http://127.0.0.1:8000/ordens`
- Pagamentos: `http://127.0.0.1:8000/pagamentos`
- Atividades: `http://127.0.0.1:8000/atividades`
- Cronograma: `http://127.0.0.1:8000/cronograma`
- Disponibilidade: `http://127.0.0.1:8000/disponibilidade`
- Performance: `http://127.0.0.1:8000/performance`

## Estrutura do Projeto

- `backend/`: aplicacao FastAPI, rotas, configuracao, conexao com banco e regras de negocio.
- `templates/`: paginas Jinja2 renderizadas pelo servidor.
- `static/`: arquivos CSS, JavaScript e assets da interface.
- `scripts/`: utilitarios para inicializacao, seed, usuario administrador e backup.
- `data/`: banco SQLite de demonstracao.
- `docs/`: materiais de apoio e schema de referencia.

## Observacao

Este projeto foi desenvolvido com fins de estudo, portfolio e demonstracao de um sistema web administrativo para gestao de servicos de engenharia.
