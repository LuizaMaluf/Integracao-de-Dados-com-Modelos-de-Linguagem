"""
Config-Driven E2E Bridge — encadeia as costuras A → B → C para um par de fontes.

    YAML (registry) → [ingestão: lote no DuckDB] → A: Silver Sync → Postgres
                    → B: gera sources/models + dbt run → C: PostgresLoader → IntegrationAgent

Pré-condição: a ingestão (extract → bronze → stage_silver) já gravou pelo menos
um lote de cada fonte no DuckDB. Sem lote, a costura A é pulada para aquela fonte
(útil quando o Airflow já sincronizou).

Uso:
    python -m govhub.sync.e2e ibge_municipios ibge_estados --no-llm

Os tempos de cada etapa vão no JSON de saída, em ``e2e.timings_s``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from govhub.ingestion import registry
from govhub.integration.agent.orchestrator import IntegrationAgent
from govhub.integration.loaders.postgres_loader import PostgresLoader
from govhub.sync.dbt_source_generator import generate
from govhub.sync.silver_sync import sync_to_postgres


@dataclass
class E2EConfig:
    sources: tuple[str, str]
    configs_dir: Path = Path("airflow/configs")
    dbt_dir: Path = Path("dbt")
    dbt_target: str = "dev"
    read_schema: str = "bronze"
    run_dbt: bool = True
    use_llm: bool = True
    output: Path | None = None


@dataclass
class _Timer:
    timings: dict[str, float] = field(default_factory=dict)

    def run(self, step: str, fn, *args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        self.timings[step] = round(time.perf_counter() - start, 3)
        return result


def find_config(configs: list[dict], source_name: str) -> dict:
    for cfg in configs:
        if cfg["source_name"] == source_name:
            return cfg
    raise ValueError(f"Fonte '{source_name}' não está no Source Registry")


def latest_lote(source_name: str) -> str | None:
    """Lote mais recente da fonte no silver DuckDB (``<fonte>_YYYYMMDD``)."""
    from govhub.ingestion.storage import silver

    pattern = re.compile(rf"^{re.escape(registry.normalize_name(source_name))}_\d{{8}}$")
    lotes = sorted(t for t in silver.list_tables() if pattern.match(t))
    return lotes[-1] if lotes else None


def run_dbt(dbt_dir: Path, target: str, models: list[str]) -> None:
    cmd = [
        "dbt", "run", "--project-dir", str(dbt_dir), "--profiles-dir", str(dbt_dir),
        "--target", target, "--select", *models,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"dbt run falhou:\n{proc.stdout[-3000:]}\n{proc.stderr[-2000:]}")


def run_e2e(cfg: E2EConfig) -> dict:
    timer = _Timer()
    configs = registry.load_configs(cfg.configs_dir)
    sources = [find_config(configs, name) for name in cfg.sources]
    tables = [registry.target_table(s) for s in sources]

    # Costura A — DuckDB → silver.<tabela> no Postgres
    synced = {}
    for source, table in zip(sources, tables):
        lote = latest_lote(source["source_name"])
        if lote:
            synced[table] = timer.run(f"A_sync_{table}", sync_to_postgres, lote, table)
            print(f"[A] Silver Sync: {lote} → silver.{table} ({synced[table]} linhas)")
        else:
            print(f"[A] Sem lote no DuckDB para {source['source_name']}; usando silver.{table}")

    # Costura B — sources/models gerados do registry + dbt run
    read_schema = cfg.read_schema
    if cfg.run_dbt:
        models_dir = cfg.dbt_dir / "models"
        files = timer.run("B_generate", generate, cfg.configs_dir, models_dir)
        print(f"[B] Source Generator: {len(files)} arquivo(s) em {models_dir}/bronze/_generated")
        timer.run("B_dbt_run", run_dbt, cfg.dbt_dir, cfg.dbt_target, tables)
        print(f"[B] dbt run: {', '.join(tables)}")
    else:
        read_schema = "silver"

    # Costura C — integração lê o par do banco
    loader = PostgresLoader()
    df_a, meta_a = timer.run("C_load_a", loader.load, f"{read_schema}.{tables[0]}")
    df_b, meta_b = timer.run("C_load_b", loader.load, f"{read_schema}.{tables[1]}")
    print(f"[C] Postgres Loader: {meta_a.name} ({len(df_a)}) × {meta_b.name} ({len(df_b)})")

    agent = IntegrationAgent(use_llm=cfg.use_llm)
    result = timer.run("integration", agent.run, df_a, meta_a, df_b, meta_b)
    result["e2e"] = {
        "sources": list(cfg.sources),
        "tables": tables,
        "read_schema": read_schema,
        "rows_synced": synced,
        "rows_loaded": {tables[0]: len(df_a), tables[1]: len(df_b)},
        "timings_s": timer.timings,
    }
    out = cfg.output or Path("output") / f"e2e_{tables[0]}__{tables[1]}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    print(f"Resultado: {out}")
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="Fluxo A → B → C para um par de fontes do registry")
    p.add_argument("source_a", help="source_name da fonte A no registry")
    p.add_argument("source_b", help="source_name da fonte B no registry")
    p.add_argument("--configs", type=Path, default=Path("airflow/configs"))
    p.add_argument("--dbt-dir", type=Path, default=Path("dbt"))
    p.add_argument("--dbt-target", default="dev", help="target do profiles.yml (padrão: dev)")
    p.add_argument("--skip-dbt", action="store_true",
                   help="não roda a costura B; a integração lê direto de silver.*")
    p.add_argument("--no-llm", action="store_true", help="Decision Layer sem LLM")
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    result = run_e2e(E2EConfig(
        sources=(args.source_a, args.source_b),
        configs_dir=args.configs,
        dbt_dir=args.dbt_dir,
        dbt_target=args.dbt_target,
        run_dbt=not args.skip_dbt,
        use_llm=not args.no_llm,
        output=args.output,
    ))
    best = result.get("best_match") or {}
    print(f"Integration Key: {best.get('columns_a')} ↔ {best.get('columns_b')} "
          f"(confiança {best.get('confidence')})")


if __name__ == "__main__":
    main()
