"""
Entry point: run the integration agent from the command line.

Usage:
    python main.py --table-a data/raw/empenhos.csv --table-b data/raw/convenios.csv
    python main.py --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv --no-llm
"""
import argparse
import json

from src.loaders.csv_loader import CsvLoader
from src.agent.orchestrator import IntegrationAgent
from src.output.formatter import print_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Semantic Integration Agent")
    parser.add_argument("--table-a", required=True, help="Path to table A (CSV)")
    parser.add_argument("--table-b", required=True, help="Path to table B (CSV)")
    parser.add_argument("--name-a", default=None, help="Display name for table A")
    parser.add_argument("--name-b", default=None, help="Display name for table B")
    parser.add_argument("--sep", default=";", help="CSV separator (default: ;)")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM reasoning step")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loader = CsvLoader()

    print(f"Loading table A: {args.table_a}")
    df_a, meta_a = loader.load(
        args.table_a,
        table_name=args.name_a,
        encoding=args.encoding,
        sep=args.sep,
    )

    print(f"Loading table B: {args.table_b}")
    df_b, meta_b = loader.load(
        args.table_b,
        table_name=args.name_b,
        encoding=args.encoding,
        sep=args.sep,
    )

    agent = IntegrationAgent(use_llm=not args.no_llm)
    result = agent.run(df_a, meta_a, df_b, meta_b)

    print_result(result)
    saved = agent.save(result, args.output)
    print(f"\nResult saved to: {saved}")


if __name__ == "__main__":
    main()
