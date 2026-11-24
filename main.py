"""Unified CLI entry point for OLAP Data Warehouse & Iceberg Cubing Analytics Suite.

Usage:
    python3 main.py --all
    python3 main.py --warehouse
    python3 main.py --mining
    python3 main.py --export-dashboard-data

Author: Rajath Gadagkar
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.mining.aoi import load_marketing_dataset
from src.mining.benchmark import run_full_benchmark
from src.mining.cli import main as run_mining_cli
from src.warehouse.runner import WarehousePipeline, main as run_warehouse_cli


DOCS_DIR = Path(__file__).resolve().parent / "docs"


def export_dashboard_data() -> Path:
    """Run both pipelines and export verified JSON payload for GitHub Pages."""
    warehouse = WarehousePipeline().run_analytics()
    records = load_marketing_dataset()
    mining = run_full_benchmark(records, repeats=3)

    payload = {
        "warehouse": warehouse,
        "mining": mining,
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DOCS_DIR / "dashboard_data.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Also write a JS wrapper so docs/index.html works over file:// as well as GitHub Pages
    js_path = DOCS_DIR / "dashboard_data.js"
    js_path.write_text(
        f"window.DASHBOARD_DATA = {json.dumps(payload)};\n",
        encoding="utf-8",
    )
    print(f"Exported verified dashboard data to {json_path} and {js_path}")
    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OLAP Data Warehouse & Iceberg Cubing Analytics Suite"
    )
    parser.add_argument(
        "--warehouse",
        action="store_true",
        help="Run the DuckDB Star Schema ETL & OLAP analytical query suite.",
    )
    parser.add_argument(
        "--mining",
        action="store_true",
        help="Run the AOI & BUC iceberg cubing engine and performance benchmarks.",
    )
    parser.add_argument(
        "--export-dashboard-data",
        action="store_true",
        help="Export live-verified pipeline results for the interactive GitHub Pages dashboard.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run both the Data Warehouse and Data Mining pipelines.",
    )
    args = parser.parse_args()

    if not any([args.warehouse, args.mining, args.export_dashboard_data, args.all]):
        args.all = True

    if args.all or args.warehouse:
        print("\n" + "=" * 72)
        print("MODULE 1: RETAIL STAR SCHEMA DATA WAREHOUSE & OLAP ANALYTICS (DuckDB)")
        print("=" * 72)
        run_warehouse_cli()

    if args.all or args.mining:
        print("\n" + "=" * 72)
        print("MODULE 2: ATTRIBUTE-ORIENTED INDUCTION & BUC ICEBERG CUBING")
        print("=" * 72)
        run_mining_cli()

    if args.export_dashboard_data:
        export_dashboard_data()


if __name__ == "__main__":
    main()
