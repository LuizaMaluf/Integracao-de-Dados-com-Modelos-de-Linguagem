# doc-tcc

Agente de documentação do TCC gov-hub (Luiza & Lucas, UnB).

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
- `docs/architecture.md` — componentes e ADRs existentes
- `docs/adr/` — listar arquivos presentes (ls)
- Memórias em `/home/luiza-maluf/.claude/projects/-home-luiza-maluf--rea-de-trabalho-tcc-gov-hub/memory/MEMORY.md`

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

### Etapa 4 — Atualizar architecture.md

Se um novo componente foi criado:
- Adicione uma seção `### N. Nome` com: Responsabilidade, Ferramenta, Por quê, Sem mudança (se aplicável)
- Atualize a tabela "Decisões de design" com o novo ADR

Se um componente existente mudou de ferramenta ou responsabilidade:
- Atualize a seção correspondente

### Etapa 5 — Atualizar architecture-interactive.html

Se houve mudança em componente ou ADR, atualize o array `COMPONENTS` ou `ADRS` em `docs/architecture-interactive.html`:
- `COMPONENTS[i].responsibility` — se a responsabilidade mudou
- `COMPONENTS[i].tool` — se a ferramenta mudou
- `COMPONENTS[i].adr` — se um ADR novo foi vinculado
- `ADRS` — adicione o novo ADR ao array

**Formato de um novo item em ADRS:**
```js
{ num:"ADR NNNN", title:"Título", status:"Aceito", body:"Resumo em 1-2 frases para o card visual." },
```

**Formato de um novo item em COMPONENTS** (se componente totalmente novo):
```js
{
  num:N, id:"slug", name:"Nome", layer:"Camada",
  color:"#hex", bg:"#hex-claro",
  responsibility:"Uma frase.",
  detail:"Parágrafo explicativo.",
  tool:"Ferramenta",
  why:"Justificativa.",
  code:"path/relativo/",
  adr:{num:"ADR NNNN", file:"adr/NNNN-slug.md"},
  example:`código de exemplo ou null`
},
```

### Etapa 6 — Salvar em memória

Atualize ou crie arquivos de memória relevantes em:
`/home/luiza-maluf/.claude/projects/-home-luiza-maluf--rea-de-trabalho-tcc-gov-hub/memory/`

- Se foi discutido um componente novo: atualize `project_architecture.md`
- Se foi discutida uma decisão de pipeline: atualize `project_integration_pipeline.md`
- Se foi discutido vocabulário de domínio: atualize `project_domain_vocabulary.md`

Adicione ao `MEMORY.md` se um arquivo novo foi criado.

### Etapa 7 — Reportar

Mostre ao usuário um resumo conciso do que foi atualizado:

```
Documentação atualizada:
  ADR criado  : docs/adr/0008-slug.md
  arch.md     : seção "Componente 12" adicionada
  HTML        : ADRS[7] adicionado
  Memória     : project_architecture.md atualizado
```

---

## Cuidados

- **Não crie ADRs duplicados.** Antes de criar, verifique se já existe um ADR cobrindo a mesma decisão.
- **Não invente justificativas.** Se a justificativa não apareceu explicitamente na conversa, escreva "Não documentada nessa sessão." e deixe para a próxima.
- **Mantenha o tom factual.** ADRs descrevem o que foi decidido e por quê — não avaliam se a decisão foi boa ou ruim.
- **Preserve o formato.** Os arquivos MD existentes têm estrutura consistente — não adicione seções extras nem remova campos.
- **architecture-interactive.html:** edite apenas os arrays JS (`COMPONENTS`, `ADRS`). Não altere o HTML ou CSS.
