# SmartMall AI Backend

API FastAPI/PostgreSQL para ocorrências operacionais de um shopping, com triagem assistida por OpenAI e revisão humana.

[Demonstração online](https://smartmall-ai-demo.vercel.app) com código privado compartilhado, dados fictícios e IA simulada. [Prontidão da API publicada](https://smartmall-ai-demo-api-8mez.onrender.com/health/ready). O [guia de deploy](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/deploy.md) registra os recursos e a verificação de 12 cenários de navegador contra Vercel, Render e Supabase.

**Entrega implementada:** ocorrências, tarefas, responsáveis fictícios, equipamentos, filtros, histórico e dashboard. A integração OpenAI está implementada e testada com respostas HTTP controladas. A tentativa real de 13/11/2026 foi recusada por saldo esgotado da API (`credit_balance_exhausted`); não houve análise real validada. O frontend foi publicado e passou em 12 cenários de navegador, inclusive contra a nuvem; veja [evidências e pendências](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/deploy.md). Validação com usuários e autenticação individual continuam pendentes.

## Executar

Requisitos: Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/) e PostgreSQL 18 (instalado ou via Docker Compose).

```powershell
uv sync --frozen
Copy-Item .env.example .env
```

Escolha uma senha local e mantenha `POSTGRES_PASSWORD`, `DATABASE_URL` e `TEST_DATABASE_URL` alinhados. Caracteres especiais em senhas de URLs precisam de codificação de URL. Nunca versione `.env`.

```powershell
docker compose up -d --wait db
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Com PostgreSQL já instalado, ajuste as URLs e dispense o comando Docker. `POSTGRES_PORT` controla a porta publicada pelo Compose. O seed é opcional, idempotente, restrito a `APP_ENV=development` e usa somente dados fictícios; não chama a IA nem sobrescreve registros existentes.

- [Swagger local](http://127.0.0.1:8000/docs) e [OpenAPI local](http://127.0.0.1:8000/openapi.json).
- [Contrato exportado](openapi.json), gerado por `uv run python -m app.export_openapi`.
- `GET /health`: processo disponível. `GET /health/ready`: conexão com o banco, ou 503.
- `CORS_ORIGINS` aceita origens HTTP/HTTPS separadas por vírgula; padrão `http://localhost:5173`.

As migrações são explícitas, sem criação automática de tabelas ao iniciar a API.

## Rotas implementadas

Base `/api/v1`. Detalhes de campos, enums e erros no [contrato compartilhado](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/contrato-api.md) e no Swagger.

| Recurso | Operações |
| --- | --- |
| `/occurrences` | POST e GET; filtros combináveis `status`, `priority`, `category`, `equipment_id`, `location` |
| `/occurrences/{id}` | GET com tarefas vinculadas; PATCH de campos editáveis |
| `/occurrences/{id}/analyze` | POST solicita e salva sugestões estruturadas |
| `/occurrences/{id}/history` | GET histórico de criação, alterações, análise e revisão |
| `/users` | POST cadastro de responsável e GET de ativos, com filtro `role` |
| `/tasks` | POST e GET; filtros `status`, `assigned_to`, `occurrence_id` |
| `/tasks/{id}` | GET e PATCH |
| `/equipment` | POST e GET; filtros `operational_status`, `location` |
| `/equipment/{id}` | GET e PATCH |
| `/equipment/{id}/occurrences` | GET ocorrências vinculadas |
| `/dashboard/summary` | GET contagens calculadas do banco |

Listas retornam arrays sem paginação no MVP. Ocorrências vêm da mais recente para a mais antiga; tarefas por prazo, equipamentos e responsáveis por nome. A busca de local usa trecho literal, com comparação de caixa dependente da configuração do PostgreSQL; não remove acentos.

## Fluxo para integrar o frontend

1. Criar ocorrência com `title`, `description`, `location` e, opcionalmente, `category`/`equipment_id`. A API define `status=open`, `priority=untriaged`, UUID e datas UTC.
2. Solicitar `/analyze`. As sugestões ficam em `ai_analysis`; a API não aplica prioridade, categoria, equipe ou recomendação automaticamente.
3. A pessoa escolhe os valores e envia PATCH, por exemplo `{"priority":"high","assigned_team":"Climatização","confirm_ai_review":true}`. A confirmação exige análise atual e grava `ai_reviewed_at`. A classificação manual funciona sem IA, omitindo a confirmação.
4. Obter um responsável em `/users`; criar tarefa com `occurrence_id`, `title`, `assigned_to`, `due_at` com fuso e `details` opcional.
5. Iniciar a tarefa (`pending` → `in_progress`) também põe uma ocorrência aberta em andamento. Concluir (`in_progress` → `completed`) grava a data, sem encerrar automaticamente a ocorrência. Pode-se retornar de `in_progress` a `pending` ou reativar `completed` para `in_progress`.
6. Resolver a ocorrência explicitamente via PATCH. Tarefas pendentes impedem o encerramento (409). Para adicionar ou reativar tarefa de ocorrência resolvida, primeiro reabrir a ocorrência.
7. Consultar histórico e dashboard. Mudanças e eventos são gravados na mesma transação; escritas de tarefas e encerramento serializam pelo bloqueio da ocorrência.

Alterar título, descrição, local ou vínculo de equipamento invalida a análise anterior e sua confirmação. Uma alteração concorrente durante a chamada de IA descarta a resposta com 409. PATCH vazio, campos desconhecidos ou `null` em campo obrigatório são recusados. Equipamentos e responsáveis precisam existir; responsáveis inativos não recebem tarefas.

## OpenAI e demonstração

No `.env` local:

```dotenv
AI_PROVIDER=openai
AI_MODEL=gpt-5.4-mini
AI_SIMULATION=false
OPENAI_API_KEY=SUBSTITUA_SOMENTE_NO_ARQUIVO_LOCAL
AI_TIMEOUT_SECONDS=20
```

Use uma chave com permissão de escrita na Responses API. O saldo da API é necessário para chamadas reais. A chave fica apenas no servidor. O SDK usa Responses com saída estruturada validada, `store=false`, limite de tokens e sem repetição automática. São enviados título, descrição, local e categoria do relato; dados de responsáveis não são enviados.

Falha, timeout, recusa ou resposta inválida retornam 503 sem apagar ocorrência nem análise válida anterior. O operador pode classificar manualmente e tentar novamente depois. O conteúdo dos erros do provedor não é exposto pela API nem registrado no log.

Para demonstrar sem consumir a API, defina `AI_SIMULATION=true` e reinicie o servidor. O resultado determinístico traz `is_simulation=true`; a interface deve mostrar essa condição. O modo real retorna `false`. Não existe substituição silenciosa por simulação após falha real. `store=false` desativa o armazenamento da resposta para recuperação; não representa garantia geral de retenção zero pelo provedor.

## Verificar

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic check
```

54 testes passaram com PostgreSQL real: persistência, migrações de ida e volta, fluxos operacionais, dados inválidos, revisão e invalidação de análise, alteração concorrente, seed, falhas do provedor, proteção do ambiente, RLS contra papel público e inicialização idempotente do deploy. Os testes de IA usam transporte HTTP controlado, sem chave real nem consumo de saldo. A validação real permanece bloqueada pelo saldo informado acima.

`TEST_DATABASE_URL` aponta para um banco acessível por usuário com `CREATEDB`. Os testes criam e removem somente um banco aleatório `smartmall_test_<uuid>`; o banco de desenvolvimento é preservado. O GitHub Actions repete as verificações com PostgreSQL próprio. Dependências diretas e resolução completa estão fixadas em `pyproject.toml` e `uv.lock`.

## Organização e limites

`app/routers` define rotas; `schemas` valida contratos; `services` aplica regras; `database` persiste; `migrations` evolui o banco. O histórico não registra um autor autenticado, porque login e autorização ainda estão fora deste MVP. Os papéis de `/users` são descritivos e não restringem acesso.

A API usa dados fictícios. O modo de demonstração tem uma barreira de acesso compartilhada; não há identidade autenticada individual, autorização por perfil, paginação ou upload de fotos. O Compose do banco e a execução local são caminhos distintos; Docker não estava disponível no ambiente usado para a verificação local.

## Deploy de demonstração

`render.yaml` configura o serviço gratuito publicado no Render, com Python 3.12, dependências fixadas, deploy manual e `/health/ready` como verificação. Por decisão da liderança, a API não publica automaticamente após merges; conferir o check `check` e a main antes de acionar **Manual Deploy → Deploy latest commit**. O estado e os endereços estão registrados no [guia de deploy](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/deploy.md).

- `APP_ENV=demo` exige `AI_SIMULATION=true` e `DEMO_ACCESS_TOKEN` privado com pelo menos 32 caracteres ASCII sem espaços. Fora de `development`, a ausência do código impede iniciar a aplicação. O Blueprint gera esse código no Render; não o copie para commits, URLs ou variáveis `VITE_`.
- Configure `DATABASE_URL` com conexão PostgreSQL TLS e `CORS_ORIGINS` com a origem HTTPS exata do frontend. Para rede IPv4 e Supabase, use o **Session pooler** indicado pelo painel, sem adivinhar o host.
- `uv run --no-sync python -m app.deploy` aplica migrações sob bloqueio PostgreSQL, executa o seed fictício idempotente quando `DEMO_SEED=true` e inicia a API na porta `PORT`. Não exige o pre-deploy pago do Render. O seed é permitido somente em desenvolvimento ou demonstração.
- Em ambiente protegido, todas as rotas, inclusive Swagger/OpenAPI, exigem `Authorization: Bearer <código>`. Apenas `/health`, `/health/ready` e preflights CORS são públicos. Respostas protegidas não são armazenadas em cache. `GET /api/v1/access` valida o código sem consultar o banco.
- As migrações habilitam RLS sem políticas públicas nas cinco tabelas operacionais, bloqueando acesso por papéis não proprietários mesmo com grants de tabela. A conexão privada da API deve ser proprietária dessas tabelas; esse é o papel que executa as migrações. Assim, a Data API do Supabase não oferece um caminho público alternativo aos dados.

O código compartilhado permite acesso completo aos dados fictícios do ambiente; não estabelece permissões por pessoa nem torna o sistema adequado a dados reais. O modo `demo` sempre simula IA e não consome a OpenAI. O plano gratuito do Render pode suspender por inatividade.

[Liderança: @geraldojoao](https://github.com/geraldojoao). Trabalhe em branch e abra PR conforme [CONTRIBUTING.md](CONTRIBUTING.md); a `main` mantém checks e proteções. Consulte [escopo](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/escopo.md), [backlog](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/backlog.md), [frontend](https://github.com/SmartMall-AI/fe-smartmall-ai) e [Trello](https://trello.com/b/TMJ0EfTl).
