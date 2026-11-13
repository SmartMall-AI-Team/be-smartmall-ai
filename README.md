# SmartMall AI Backend

API para registrar e acompanhar ocorrências operacionais de um shopping.

**Estado desta entrega (BE-01):** FastAPI, configuração por ambiente, CORS, PostgreSQL, migração inicial e verificações de saúde implementados. As rotas de ocorrências serão acrescentadas em BE-02. IA, tarefas, dashboard e autenticação ainda não estão implementados.

## Requisitos

- Python 3.12 e [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Docker com Compose, ou PostgreSQL 18 já disponível.

As dependências diretas estão fixadas em `pyproject.toml`; `uv.lock` registra a resolução completa. Use `uv sync --frozen` para reproduzir o ambiente.

## Executar localmente

Na raiz deste repositório:

```powershell
uv sync --frozen
Copy-Item .env.example .env
```

Edite `.env`: escolha a senha de desenvolvimento e use o mesmo valor em `POSTGRES_PASSWORD`, `DATABASE_URL` e `TEST_DATABASE_URL`. Caracteres especiais em senhas dentro de URLs precisam de codificação de URL. Não versione `.env`.

Suba o banco, aplique as migrações e inicie a API:

```powershell
docker compose up -d --wait db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Com PostgreSQL já instalado, ajuste as URLs em `.env` e execute a migração e a API sem o comando Docker. `POSTGRES_PORT` controla a porta publicada pelo Compose; mantenha as URLs alinhadas a ela.

- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Esquema OpenAPI: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)
- `GET /health`: processo da API disponível.
- `GET /health/ready`: conexão com o banco disponível; retorna 503 em falha.

As tabelas são criadas por Alembic, não na inicialização da API. `CORS_ORIGINS` aceita origens HTTP/HTTPS separadas por vírgula; o padrão é `http://localhost:5173`.

## Organização

```text
app/
  main.py       criação da API e middleware
  core/         configuração e enums compartilhados
  database/     modelos SQLAlchemy e sessões
  schemas/      contratos de entrada e saída
  routers/      rotas REST
  services/     regras de negócio
migrations/     alterações de banco com Alembic
tests/          testes com PostgreSQL real
```

A tabela `equipment` prepara a referência usada em ocorrências; não existe ainda uma API de equipamentos. Usuários, tarefas e análise de IA serão tratados nas próximas entregas.

## Verificar

Com o banco disponível e `TEST_DATABASE_URL` configurada:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic check
```

Os testes criam um banco com nome aleatório `smartmall_test_<uuid>`, aplicam a migração e removem apenas esse banco ao terminar. O usuário de teste precisa de permissão `CREATEDB`. O banco de desenvolvimento mantém seus registros. O GitHub Actions executa as verificações com seu próprio PostgreSQL.

## Trabalho compartilhado

- [Contrato da API](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/contrato-api.md)
- [Escopo](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/escopo.md)
- [Backlog](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/backlog.md)
- [Frontend](https://github.com/SmartMall-AI/fe-smartmall-ai)
- [Trello](https://trello.com/b/TMJ0EfTl)

Esta é uma API para desenvolvimento local, ainda sem autenticação. Use dados fictícios. A chave do futuro provedor de IA ficará exclusivamente no servidor; as variáveis `AI_*` no exemplo estão reservadas e ainda não são consumidas.
