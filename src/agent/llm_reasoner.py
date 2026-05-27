"""
LLM-based reasoning layer: sends candidates to Claude for final judgment.
"""
import json
import anthropic
from src.agent.candidate_generator import CandidateKey
from src.loaders.base import TableMetadata
from src.config.settings import settings


SYSTEM_PROMPT = """Você é um especialista em integração de bases de dados governamentais brasileiras.
Analise os candidatos a chave de integração fornecidos e produza o resultado final em JSON.
Seja preciso, objetivo e baseie cada decisão em evidências observáveis."""


def build_user_prompt(
    meta_a: TableMetadata,
    meta_b: TableMetadata,
    candidates: list[CandidateKey],
) -> str:
    candidates_payload = [
        {
            "table_a_columns": c.columns_a,
            "table_b_columns": c.columns_b,
            "score": c.score,
            "match_rate": c.match_rate,
            "cardinality": c.cardinality,
            "evidence_for": c.evidence_for,
            "evidence_against": c.evidence_against,
            "required_transformations": c.required_transformations,
        }
        for c in candidates
    ]

    return f"""
## Tabela A: {meta_a.name}
Colunas: {meta_a.columns}
Tipos: {meta_a.dtypes}

## Tabela B: {meta_b.name}
Colunas: {meta_b.columns}
Tipos: {meta_b.dtypes}

## Candidatos a chave de integração (gerados automaticamente):
{json.dumps(candidates_payload, indent=2, ensure_ascii=False)}

Produza um JSON com a estrutura:
{{
  "summary": "",
  "candidate_keys": [...],
  "best_match": {{
    "table_a": "{meta_a.name}",
    "columns_a": [],
    "table_b": "{meta_b.name}",
    "columns_b": [],
    "confidence": 0.0,
    "justification": ""
  }}
}}
"""


def reason_with_llm(
    meta_a: TableMetadata,
    meta_b: TableMetadata,
    candidates: list[CandidateKey],
) -> dict:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=settings.model_name,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_user_prompt(meta_a, meta_b, candidates)}
        ],
    )

    raw = response.content[0].text
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw_response": raw, "error": "Failed to parse JSON from LLM response"}
