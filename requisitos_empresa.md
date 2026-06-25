# Requisitos do Sistema Demo

## Objetivo

Desenvolver uma aplicacao web de demonstracao para gestao de servicos de engenharia, com foco em portfolio tecnico. O sistema deve apresentar um fluxo completo e funcional sem usar dados, marca, identidade visual ou contexto de uma empresa real.

## Escopo

O sistema deve permitir:

- autenticar usuarios;
- visualizar dashboard geral;
- gerenciar clientes ficticios;
- gerenciar colaboradores ficticios;
- gerenciar catalogo de servicos;
- criar e acompanhar ordens de servico;
- controlar pagamentos;
- registrar atividades;
- visualizar cronograma;
- consultar disponibilidade;
- acompanhar performance de colaboradores.

## Tecnologias

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Jinja2
- Bootstrap 5
- Chart.js

## Banco de Dados

A versao publica deve usar `data/demo.db`. Bancos de producao, desenvolvimento local, backups e arquivos `.env` nao devem ser versionados.

## Identidade Visual

A interface deve usar nome e marca genericos:

- Nome: Sistema de Gestao de Engenharia
- Sigla/fallback: SGE
- Contexto: Empresa de Engenharia Demo

Logo e favicon devem ser opcionais. Se nao existirem, o sistema deve continuar funcionando.

## Dados

Todos os dados usados na demo devem ser ficticios. Nomes, e-mails, telefones e empresas reais nao devem aparecer na aplicacao, nos documentos ou no banco demo.

## Modulos

### Dashboard

Deve apresentar indicadores de clientes, colaboradores, servicos, ordens, pagamentos, atividades e desempenho operacional.

### Clientes

Deve permitir listar, cadastrar, editar, pesquisar e excluir clientes quando nao houver bloqueio por relacionamento.

### Colaboradores

Deve permitir listar, cadastrar, editar, pesquisar e controlar colaboradores ativos.

### Servicos

Deve permitir manter um catalogo de servicos com descricao e preco base.

### Ordens de Servico

Deve permitir vincular cliente, servico e colaborador, alem de acompanhar status da ordem.

### Pagamentos

Deve permitir registrar valores, datas e status de pagamento.

### Atividades e Cronograma

Deve permitir planejar atividades por colaborador, data e horario, exibindo agenda e duracao calculada.

### Disponibilidade

Deve permitir consultar horarios livres com base nas atividades ja cadastradas.

### Performance

Deve apresentar horas registradas, atividades concluidas, pendentes e comparativos entre colaboradores.
