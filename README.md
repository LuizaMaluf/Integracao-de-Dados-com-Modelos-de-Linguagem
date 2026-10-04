# Integração de dados públicos com modelos de linguagem

Repositório do TCC de Luiza Maluf (UnB/FCTE), com orientação de Carla Rocha e Isaque Alves: *Integração de dados públicos com modelos de linguagem: um pipeline construído por Spec-Driven Development para descoberta de chaves entre bases governamentais*.

Bases do governo federal (SIAFI, Transferegov, Portal da Transparência, IBGE…) usam nomes, formatos e identificadores diferentes para os mesmos conceitos e raramente declaram uma chave comum. Este pipeline descobre a **chave de integração** entre duas tabelas: estágios determinísticos coletam evidências, um modelo de linguagem embutido decide o de-para e devolve um dicionário tipado, e o join e seus testes saem de código determinístico — o LLM nunca escreve SQL.

- Proposta, questões de pesquisa e plano: [`docs/tcc/proposta.md`](docs/tcc/proposta.md)
- Glossário do domínio: [`CONTEXT.md`](CONTEXT.md)
- Princípio do LLM embutido: [ADR 0011](docs/adr/0011-llm-embutido-saida-estruturada.md), a partir do artigo-base ([`docs/tcc/artigo-base.md`](docs/tcc/artigo-base.md))

## Como funciona

```
Coleta de evidências        Decision Layer                Geração e validação
(determinístico)        →   (LLM embutido)            →   (determinístico)
perfil e amostra das        decide a Integration Key      templates Jinja → model dbt
colunas, scores de nome     ou se abstém; devolve o       de join + testes dbt;
e de conteúdo, Candidate    Dicionário de Mapeamento      executa e valida o join
Keys ranqueadas             (JSON tipado)
```

**Estado atual.** A coleta de evidências e uma Decision Layer com prompt livre já funcionam (`govhub`, abaixo). A Decision Layer tipada com DSPy, o Catálogo de Transformações, a Abstenção, o estágio Jinja → dbt e o harness de avaliação estão em "Lacunas e plano de trabalho" na proposta.

A ingestão das bases é feita pelo GovHub (`data-application-gov-hub`): o pipeline lê as tabelas do PostgreSQL do GovHub ou de arquivos CSV.

## Setup

Requer Python 3.11+.

```bash
pip install -e ".[postgres,dev]"
cp .env.example .env        # preencha ANTHROPIC_API_KEY e, se for ler do banco, POSTGRES_*
make up                     # opcional: PostgreSQL local para os testes `pg` e o dbt
```

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Chave da API Anthropic (sem ela, use `--no-llm` ou `LLM_BACKEND=claude-cli`) |
| `MODEL_NAME` | `claude-sonnet-4-6` | Modelo da Decision Layer |
| `LLM_BACKEND` | `anthropic` | `anthropic` (API key) ou `claude-cli` (Claude Code headless, login da máquina) |
| `MAX_CANDIDATE_KEYS` | `10` | Candidate Keys enviados ao LLM |
| `SAMPLE_SIZE` | `1000` | Linhas amostradas por tabela |
| `POSTGRES_*` | `localhost`, `govhub`… | Banco de onde as tabelas são lidas (local ou do GovHub) |

## Uso

```bash
# Duas tabelas em CSV
govhub --table-a tabela_a.csv --table-b tabela_b.csv

# Sem LLM: só as evidências determinísticas (baseline)
govhub --table-a tabela_a.csv --table-b tabela_b.csv --no-llm

# Direto do PostgreSQL
govhub --table-a pg://siafi.empenhos --table-b pg://transferegov.convenios

# Salvando o resultado em outro caminho (padrão: output/integration_result.json)
govhub --table-a tabela_a.csv --table-b tabela_b.csv --output resultado.json
```

| Parâmetro | Descrição |
| --- | --- |
| `--table-a`, `--table-b` | CSV ou `pg://schema.tabela` (obrigatórios) |
| `--name-a`, `--name-b` | Nome de exibição de cada tabela |
| `--sep`, `--encoding` | Separador (padrão `;`) e encoding (padrão `utf-8`) do CSV |
| `--no-llm` | Pula a Decision Layer com LLM |
| `--output` | Caminho do JSON de saída |

## Estrutura

```
src/govhub/
  integration/
    agent/          CandidateGenerator (evidências), IntegrationAgent, llm_reasoner (Decision Layer)
    analyzers/      similaridade de nome, estatística, estrutura, conteúdo
    config/         settings e Domain Context (domain.py)
    loaders/        CSV e PostgreSQL
    transformers/   normalização e detecção de padrões
  llm.py            cliente LLM único (anthropic | claude-cli)
  postgres.py       conexão com o PostgreSQL
  cli.py            comando `govhub`
dbt/                esqueleto do projeto dbt; os models de join saem do estágio Jinja → dbt
tests/integration/  testes (os marcados `pg` precisam de POSTGRES_*)
docs/
  tcc/              proposta e artigo-base (o texto do TCC fica no Overleaf)
  adr/              decisões de arquitetura
  specs/            specs do Spec-Driven Development (modelo em _template.md)
  historico/        ciclos anteriores: skills da Fase 01 e a pilha de ingestão removida
```

## Processo

O pipeline é construído por **Spec-Driven Development**: toda mudança não trivial começa por uma spec em [`docs/specs/`](docs/specs/), com critérios de aceite verificáveis, e só é implementada depois de aprovada. O efeito do SDD é uma das questões de pesquisa (QP5) — ver a proposta.

## Testes

```bash
make test     # testes `pg` são pulados sem PostgreSQL acessível
make lint
```
