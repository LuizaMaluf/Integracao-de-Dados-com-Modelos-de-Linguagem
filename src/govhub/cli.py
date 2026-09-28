"""
Entry point: run the integration agent from the command line.

Usage:
    govhub --table-a data/raw/empenhos.csv --table-b data/raw/convenios.csv
    govhub --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv --no-llm
    govhub --table-a pg://silver.ibge_municipios --table-b pg://silver.ibge_estados
"""
import argparse
import json

from govhub.integration.agent.orchestrator import IntegrationAgent
from govhub.integration.loaders.csv_loader import CsvLoader
from govhub.integration.loaders.postgres_loader import PostgresLoader, is_pg_source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Semantic Integration Agent")
    parser.add_argument("--table-a", required=True,
                        help="Tabela A: caminho de CSV ou pg://schema.tabela")
    parser.add_argument("--table-b", required=True,
                        help="Tabela B: caminho de CSV ou pg://schema.tabela")
    parser.add_argument("--name-a", default=None, help="Display name for table A")
    parser.add_argument("--name-b", default=None, help="Display name for table B")
    parser.add_argument("--sep", default=";", help="CSV separator (default: ;)")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM reasoning step")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    return parser.parse_args()


def load_table(source: str, name: str | None, args: argparse.Namespace):
    """Carrega de CSV ou, com prefixo pg://, do PostgreSQL (costura C)."""
    if is_pg_source(source):
        return PostgresLoader().load(source, table_name=name)
    return CsvLoader().load(source, table_name=name, encoding=args.encoding, sep=args.sep)


def main() -> None:
    args = parse_args()

    print(f"Loading table A: {args.table_a}")
    df_a, meta_a = load_table(args.table_a, args.name_a, args)

    print(f"Loading table B: {args.table_b}")
    df_b, meta_b = load_table(args.table_b, args.name_b, args)

    agent = IntegrationAgent(use_llm=not args.no_llm)
    result = agent.run(df_a, meta_a, df_b, meta_b)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    saved = agent.save(result, args.output)
    print(f"\nResult saved to: {saved}")


if __name__ == "__main__":
    main()
