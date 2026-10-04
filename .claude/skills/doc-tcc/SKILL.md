# doc-tcc

Agente de documentação do TCC gov-hub (Luiza Maluf, UnB).

Ao ser invocado, analisa a conversa atual, extrai decisões e alimenta a documentação centralizada em `docs/`.

---

## Quando usar

- Após discutir uma decisão técnica importante
- Quando um novo componente foi implementado ou modificado
- Quando um ADR foi aceito, rejeitado ou mudou de status
- Ao final de uma sessão produtiva

---

## Etapas — execute em sequência

### Etapa 1 — Ler estado atual da documentação

Leia os arquivos abaixo para entender o que já está documentado antes de criar duplicatas:
- `CONTEXT.md` — glossário do domínio
- `docs/adr/` — listar arquivos presentes (ls)
- `docs/specs/` — specs do SDD (modelo `_template.md`)
- `docs/tcc/proposta.md` — QPs, metodologia e plano; atualizar se uma decisão mudar escopo, QPs ou lacunas
- `docs/tcc/artigo-base.md` — método de referência (SPAPI-Tester); decisões novas devem ser coerentes com o princípio do LLM embutido (ADR 0011)
- Memórias do projeto no Claude Code (`~/.claude/projects/<projeto>/memory/MEMORY.md`)

### Etapa 2 — Extrair decisões da conversa atual

Varra a conversa buscando:

**Decisões arquiteturais:**
- Padrões adotados ("vamos usar X", "adotamos Y")
- Padrões rejeitados ("rejeitamos X porque", "não vamos usar Y")
- Mudanças de design com impacto em componentes existentes

**Novos componentes ou modificações:**
- Componentes criados ou alterados nessa sessão
- Mudanças em responsabilidade, ferramenta ou fluxo de dados

**Justificativas:**
- O *por quê* de cada decisão (o que os ADRs precisam capturar)
- Trade-offs discutidos explicitamente

**Vocabulário de domínio:**
- Termos novos do domínio orçamentário brasileiro
- Siglas ou conceitos explicados na conversa

### Etapa 3 — Criar ou atualizar ADRs

Para cada decisão nova identificada na Etapa 2:

1. Determine o próximo número sequencial consultando `docs/adr/`
2. Crie `docs/adr/NNNN-<slug-kebab-case>.md` com o formato:

```markdown
# ADR NNNN — <Título conciso>

**Status:** Aceito | Proposto | Rejeitado

## Contexto

<O problema que precisava ser resolvido. Fatos, não opiniões.>

## Decisão

<O que foi decidido. Concreto e objetivo.>

## Alternativa rejeitada

<O que foi considerado e descartado, e por quê.>

## Consequências

<O que muda como resultado dessa decisão. Inclui impactos positivos e negativos.>
```

Para ADRs existentes com mudança de status: edite apenas o campo `**Status:**`.

### Etapa 4 — Atualizar CONTEXT.md

Se um termo do domínio foi definido ou mudou de sentido, atualize o glossário em `CONTEXT.md` no formato existente (termo em negrito, definição de uma ou duas frases, `_Avoid_`). Sem detalhes de implementação.

### Etapa 5 — Salvar em memória

Atualize ou crie arquivos de memória relevantes na memória do projeto no Claude Code
(`~/.claude/projects/<projeto>/memory/`).

- Se foi discutido um componente novo: atualize `project_architecture.md`
- Se foi discutida uma decisão de pipeline: atualize `project_integration_pipeline.md`
- Se foi discutido vocabulário de domínio: atualize `project_domain_vocabulary.md`

Adicione ao `MEMORY.md` se um arquivo novo foi criado.

### Etapa 6 — Reportar

Mostre ao usuário um resumo conciso do que foi atualizado:

```
Documentação atualizada:
  ADR criado  : docs/adr/0012-slug.md
  Proposta    : seção "Lacunas e plano de trabalho" atualizada
  CONTEXT.md  : termo "Abstenção" adicionado
  Memória     : project_architecture.md atualizado
```

---

## Cuidados

- **Não crie ADRs duplicados.** Antes de criar, verifique se já existe um ADR cobrindo a mesma decisão.
- **Não invente justificativas.** Se a justificativa não apareceu explicitamente na conversa, escreva "Não documentada nessa sessão." e deixe para a próxima.
- **Mantenha o tom factual.** ADRs descrevem o que foi decidido e por quê — não avaliam se a decisão foi boa ou ruim.
- **Preserve o formato.** Os arquivos MD existentes têm estrutura consistente — não adicione seções extras nem remova campos.
