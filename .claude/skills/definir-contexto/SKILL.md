---
name: definir-contexto
description: Gera ou atualiza um Domain Context JSON para um domínio de dados descrito pelo usuário em linguagem natural. O Domain Context contém grupos semânticos de colunas (aliases reconhecidos para cada conceito do domínio) e padrões regex de identificadores. Uma vez gerado, o contexto é reutilizado por todas as execuções do pipeline integrar-bases no mesmo domínio — sem precisar redefinir a cada nova integração. Use SEMPRE que o usuário quiser configurar o pipeline para um novo domínio, atualizar o contexto porque novas colunas não estão sendo reconhecidas, ou quando o pipeline reportar Context Coverage abaixo de 60%.
input:
  - type: text
    description: Descrição do domínio em linguagem natural (obrigatório)
  - type: csv
    description: Arquivos CSV de exemplo do domínio (opcional, melhora a qualidade)
    optional: true
output:
  - type: json
    path: output/contexts/context_{domain_name}.json
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
```

O Domain Context gerado aqui é consumido por todas as skills do pipeline: `analisar-tabela`, `comparar-colunas`, `identificar-chave` e `gerar-relatorio`, via `src/config/context_loader.py`.

---

## Entrada esperada

O usuário fornece em `$ARGUMENTS` ou na mensagem uma **descrição do domínio**. Exemplos:

```
"bases de saúde pública do SUS: estabelecimentos, internações, procedimentos, CID"
"dados de IPTU e ITBI municipal: imóveis, contribuintes, lançamentos, pagamentos"
"registros educacionais do MEC: escolas, matrículas, professores, turmas, notas"
```

Opcionalmente, o usuário pode fornecer caminhos de CSVs de exemplo — nesse caso, leia os nomes das colunas para enriquecer os grupos semânticos gerados.

---

## O que fazer

### 1. Extrair nomes de colunas dos CSVs (se fornecidos)

```python
import pandas as pd

def get_columns(path):
    try:
        df = pd.read_csv(path, sep=";", encoding="utf-8", nrows=0, dtype=str)
    except Exception:
        df = pd.read_csv(path, sep=",", encoding="latin-1", nrows=0, dtype=str)
    return list(df.columns)
```

### 2. Gerar o Domain Context com LLM

Monte um prompt com:
- A descrição do domínio fornecida pelo usuário
- Os nomes de colunas dos CSVs (se disponíveis)
- O schema esperado do output

**Prompt para o LLM:**

```
Você é um especialista em integração de dados. Dado o domínio descrito abaixo, gere um Domain Context JSON.

Domínio: {descricao_do_usuario}

{se_csvs: "Colunas encontradas nos arquivos de exemplo:\n{lista_de_colunas}"}

Gere um JSON com esta estrutura exata:
{
  "domain_name": "<nome_snake_case_do_dominio>",
  "version": "<data_hoje_YYYY-MM-DD>",
  "semantic_groups": {
    "<conceito>": ["alias1", "alias2", "alias3", "..."]
  },
  "key_patterns": {
    "<nome_do_padrao>": "<regex>"
  }
}

Regras:
- domain_name: snake_case, sem acentos, descritivo (ex: "saude_sus", "iptu_municipal")
- semantic_groups: para cada conceito central do domínio, liste todos os nomes de coluna plausíveis (com e sem prefixos como cd_, nr_, id_, cod_, num_)
- Inclua pelo menos 8 grupos semânticos
- key_patterns: padrões regex para identificadores estruturados do domínio (ex: código de estabelecimento, número de internação). Omita se não houver padrões conhecidos.
- Responda APENAS com o JSON, sem texto adicional.
```

### 3. Validar e salvar

```python
import json
from pathlib import Path

# Parse do JSON retornado pelo LLM
raw = response_text
start = raw.index("{")
end = raw.rindex("}") + 1
context = json.loads(raw[start:end])

# Validar campos obrigatórios
assert "domain_name" in context
assert "semantic_groups" in context
assert isinstance(context["semantic_groups"], dict)
assert len(context["semantic_groups"]) >= 3

# Salvar
output_dir = Path("output/contexts")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / f"context_{context['domain_name']}.json"
output_path.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
```

### 4. Exibir no terminal

```
══════════════════════════════════════════════════════════════════════
DOMAIN CONTEXT GERADO
  Domínio  : {domain_name}
  Grupos   : {N} grupos semânticos
  Padrões  : {N} padrões regex
  Versão   : {version}
══════════════════════════════════════════════════════════════════════

GRUPOS GERADOS:
  • {grupo}: {alias1}, {alias2}, {alias3}...
  ...

Contexto salvo em: output/contexts/context_{domain_name}.json

Para usar no pipeline:
  /integrar-bases tabela_a.csv tabela_b.csv --context output/contexts/context_{domain_name}.json
══════════════════════════════════════════════════════════════════════
```

---

## Atualização de contexto existente

Se já existir um `context_{domain_name}.json` para o domínio descrito, pergunte ao usuário se deseja:
1. **Sobrescrever** — gera um novo contexto do zero
2. **Enriquecer** — adiciona novos grupos ao contexto existente sem remover os anteriores

No modo enriquecer, carregue o JSON existente, gere somente os grupos faltantes com o LLM, e faça merge antes de salvar.

---

## Cuidados

- Se o LLM retornar um JSON inválido, tente novamente com temperatura 0 antes de reportar erro.
- `domain_name` deve ser snake_case sem acentos — normalize se necessário: `unicodedata.normalize('NFKD', ...).encode('ascii', 'ignore').decode()`.
- Se nenhum CSV for fornecido, o contexto gerado será mais genérico — informe o usuário que fornecer exemplos melhora a qualidade.
