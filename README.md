# SmartMall AI Backend

API responsável por persistir ocorrências, apoiar sua triagem com IA e acompanhar tarefas operacionais do shopping.

**Estado:** estrutura inicial; endpoints, persistência e integração com IA ainda precisam ser implementados. Não há aplicação executável neste repositório.

## Tecnologias previstas

Python, FastAPI, Pydantic, PostgreSQL, SQLAlchemy e Alembic, conforme o planejamento técnico. O backend será um monólito modular. As versões serão definidas e fixadas na implementação.

## Organização

```text
app/
  core/       configuração e regras compartilhadas
  database/   conexão e modelos de persistência
  schemas/    modelos de entrada e saída
  routers/    endpoints REST
  services/   regras de negócio e serviço de IA
tests/        testes dos fluxos e falhas relevantes
```

Os diretórios estão reservados para a implementação. Não existem módulos funcionais ainda.

## Responsabilidades

- Validar e salvar ocorrências antes de solicitar qualquer análise.
- Listar e detalhar ocorrências, tarefas e equipamentos.
- Encapsular a integração com o provedor de IA.
- Retornar sugestões estruturadas e permitir revisão humana.
- Gerar indicadores do dashboard a partir dos dados persistidos.
- Manter a chave do provedor de IA exclusivamente no servidor.

## Contrato e documentação

O repositório [docs-smartmall-ai](https://github.com/SmartMall-AI/docs-smartmall-ai) mantém [contrato-api.md](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/contrato-api.md), [arquitetura.md](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/arquitetura.md) e [backlog.md](https://github.com/SmartMall-AI/docs-smartmall-ai/blob/main/backlog.md). Consultar esses arquivos antes de implementar os endpoints. Os nomes de campos e enums descritos ali são uma proposta inicial para alinhamento da equipe.

A interface fica em [fe-smartmall-ai](https://github.com/SmartMall-AI/fe-smartmall-ai).

## Configuração prevista

Consultar `.env.example`. Ele contém apenas exemplos e não configura um servidor funcional. Não versionar `.env`, credenciais ou chaves de API.

O provedor de IA e seu SDK ainda serão escolhidos; `AI_API_KEY` é um nome de configuração da aplicação, não uma variável reconhecida automaticamente por um SDK.

## Primeira entrega

Implementar cadastro, listagem e detalhe de ocorrências com persistência. Depois integrar análise opcional, tarefas e resumo do dashboard. Acrescentar instruções de execução ao README quando os comandos existirem.
