"""DuckDB Star Schema ETL & OLAP Query Runner.

Executes the Star Schema DDL, loads the nine retail CSV source tables into
DuckDB, validates row counts, and runs the OLAP analytical query suite.
Supports both the ``duckdb`` Python package and the ``duckdb`` CLI binary.

Author: Rajath Gadagkar
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


SQL_DIR = Path(__file__).resolve().parent / "sql"
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "retail"


class WarehousePipeline:
    """Orchestrates DuckDB Star Schema creation, ETL loading, and OLAP queries."""

    def __init__(
        self,
        data_dir: Path | str = DEFAULT_DATA_DIR,
        db_path: Path | str = ":memory:",
    ) -> None:
        self.data_dir = Path(data_dir).resolve()
        self.db_path = str(db_path)
        self.sql_dir = SQL_DIR

    def _find_duckdb_cli(self) -> str | None:
        for candidate in [
            shutil.which("duckdb"),
            "/opt/homebrew/bin/duckdb",
            "/usr/local/bin/duckdb",
        ]:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _run_via_python(self, queries: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
        import duckdb  # type: ignore

        orig_cwd = os.getcwd()
        os.chdir(self.data_dir)
        try:
            con = duckdb.connect(self.db_path)
            con.execute((self.sql_dir / "01_schema.sql").read_text(encoding="utf-8"))
            con.execute((self.sql_dir / "02_etl_load.sql").read_text(encoding="utf-8"))
            results: dict[str, list[dict[str, Any]]] = {}
            for name, sql in queries.items():
                rel = con.execute(sql)
                cols = [desc[0] for desc in rel.description]
                rows = rel.fetchall()
                results[name] = [
                    {col: self._serialize(val) for col, val in zip(cols, row)}
                    for row in rows
                ]
            con.close()
            return results
        finally:
            os.chdir(orig_cwd)

    def _run_via_cli(self, queries: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
        cli = self._find_duckdb_cli()
        if not cli:
            raise RuntimeError(
                "Neither the 'duckdb' Python package nor the 'duckdb' CLI binary was found."
            )

        schema_sql = (self.sql_dir / "01_schema.sql").read_text(encoding="utf-8")
        etl_sql = (self.sql_dir / "02_etl_load.sql").read_text(encoding="utf-8")

        script_parts = [schema_sql, etl_sql, ".mode json"]
        markers: list[str] = []
        for name, sql in queries.items():
            marker = f"__QUERY_MARKER_{name}__"
            markers.append(name)
            script_parts.append(f".print {marker}")
            script_parts.append(sql.strip().rstrip(";") + ";")

        full_script = "\n".join(script_parts) + "\n"
        cmd = [cli] if self.db_path == ":memory:" else [cli, self.db_path]
        proc = subprocess.run(
            cmd,
            input=full_script,
            text=True,
            capture_output=True,
            cwd=str(self.data_dir),
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"DuckDB CLI failed:\n{proc.stderr}")

        results: dict[str, list[dict[str, Any]]] = {}
        stdout = proc.stdout
        for idx, name in enumerate(markers):
            start_token = f"__QUERY_MARKER_{name}__"
            start_pos = stdout.find(start_token)
            if start_pos == -1:
                results[name] = []
                continue
            start_pos += len(start_token)
            if idx + 1 < len(markers):
                end_token = f"__QUERY_MARKER_{markers[idx + 1]}__"
                end_pos = stdout.find(end_token, start_pos)
                chunk = stdout[start_pos:end_pos].strip()
            else:
                chunk = stdout[start_pos:].strip()
            results[name] = json.loads(chunk) if chunk else []
        return results

    @staticmethod
    def _serialize(value: Any) -> Any:
        if hasattr(value, "__float__") and not isinstance(value, (int, float, bool)):
            return float(value)
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    def run_analytics(self) -> dict[str, Any]:
        """Execute Star Schema ETL and return structured OLAP query results."""
        queries = {
            "table_counts": """
                SELECT 'DimDate' AS table_name, COUNT(*) AS row_count FROM DimDate
                UNION ALL SELECT 'DimCustomer', COUNT(*) FROM DimCustomer
                UNION ALL SELECT 'DimStore', COUNT(*) FROM DimStore
                UNION ALL SELECT 'DimStaff', COUNT(*) FROM DimStaff
                UNION ALL SELECT 'DimProduct', COUNT(*) FROM DimProduct
                UNION ALL SELECT 'FactSales', COUNT(*) FROM FactSales
            """,
            "annual_revenue": """
                SELECT d.year, ROUND(SUM(fs.sale_amount), 2) AS total_revenue,
                       SUM(fs.quantity) AS units_sold, COUNT(DISTINCT fs.order_id) AS order_count
                FROM FactSales fs
                JOIN DimDate d ON fs.date_key = d.date_key
                GROUP BY d.year
                ORDER BY d.year
            """,
            "monthly_revenue": """
                SELECT d.year, d.month, d.month_name,
                       ROUND(SUM(fs.sale_amount), 2) AS total_revenue
                FROM FactSales fs
                JOIN DimDate d ON fs.date_key = d.date_key
                GROUP BY d.year, d.month, d.month_name
                ORDER BY d.year, d.month
            """,
            "peak_month_per_year": """
                WITH MonthlySales AS (
                    SELECT d.year, d.month_name,
                           ROUND(SUM(fs.sale_amount), 2) AS monthly_revenue,
                           ROW_NUMBER() OVER(PARTITION BY d.year ORDER BY SUM(fs.sale_amount) DESC) AS rn
                    FROM FactSales fs
                    JOIN DimDate d ON fs.date_key = d.date_key
                    GROUP BY d.year, d.month_name
                )
                SELECT year, month_name, monthly_revenue
                FROM MonthlySales WHERE rn = 1 ORDER BY year
            """,
            "category_revenue": """
                WITH Total AS (SELECT SUM(sale_amount) AS grand_total FROM FactSales)
                SELECT p.category_name,
                       ROUND(SUM(fs.sale_amount), 2) AS total_revenue,
                       ROUND(SUM(fs.sale_amount) * 100.0 / t.grand_total, 2) AS share_pct
                FROM FactSales fs
                JOIN DimProduct p ON fs.product_key = p.product_key
                CROSS JOIN Total t
                GROUP BY p.category_name, t.grand_total
                ORDER BY total_revenue DESC
            """,
            "brand_revenue": """
                SELECT p.brand_name,
                       ROUND(SUM(fs.sale_amount), 2) AS total_revenue
                FROM FactSales fs
                JOIN DimProduct p ON fs.product_key = p.product_key
                GROUP BY p.brand_name
                ORDER BY total_revenue DESC
            """,
            "top_products": """
                SELECT p.category_name, p.product_name, p.brand_name,
                       ROUND(SUM(fs.sale_amount), 2) AS total_revenue,
                       SUM(fs.quantity) AS units_sold
                FROM FactSales fs
                JOIN DimProduct p ON fs.product_key = p.product_key
                GROUP BY p.category_name, p.product_name, p.brand_name
                ORDER BY total_revenue DESC
                LIMIT 10
            """,
            "top_customers": """
                SELECT c.first_name || ' ' || c.last_name AS customer_name,
                       c.city, c.state,
                       ROUND(SUM(fs.sale_amount), 2) AS total_purchase_amount,
                       COUNT(DISTINCT fs.order_id) AS orders
                FROM FactSales fs
                JOIN DimCustomer c ON fs.customer_key = c.customer_key
                GROUP BY customer_name, c.city, c.state
                ORDER BY total_purchase_amount DESC
                LIMIT 5
            """,
            "store_revenue": """
                WITH Total AS (SELECT SUM(sale_amount) AS grand_total FROM FactSales)
                SELECT s.store_name, s.city, s.state,
                       ROUND(SUM(fs.sale_amount), 2) AS total_revenue,
                       ROUND(SUM(fs.sale_amount) * 100.0 / t.grand_total, 2) AS share_pct
                FROM FactSales fs
                JOIN DimStore s ON fs.store_key = s.store_key
                CROSS JOIN Total t
                GROUP BY s.store_name, s.city, s.state, t.grand_total
                ORDER BY total_revenue DESC
            """,
            "top_staff_per_store": """
                WITH StaffSales AS (
                    SELECT st.store_name,
                           sf.first_name || ' ' || sf.last_name AS staff_name,
                           ROUND(SUM(fs.sale_amount), 2) AS total_sales,
                           RANK() OVER(PARTITION BY st.store_name ORDER BY SUM(fs.sale_amount) DESC) AS sales_rank
                    FROM FactSales fs
                    JOIN DimStaff sf ON fs.staff_key = sf.staff_key
                    JOIN DimStore st ON fs.store_key = st.store_key
                    GROUP BY st.store_name, staff_name
                )
                SELECT store_name, staff_name, total_sales
                FROM StaffSales WHERE sales_rank = 1 ORDER BY total_sales DESC
            """,
            "cube_brand_category_year_count": """
                SELECT COUNT(*) AS cuboid_rows FROM (
                    SELECT p.brand_name, p.category_name, d.year, SUM(fs.sale_amount)
                    FROM FactSales fs
                    JOIN DimProduct p ON fs.product_key = p.product_key
                    JOIN DimDate d ON fs.date_key = d.date_key
                    GROUP BY CUBE(p.brand_name, p.category_name, d.year)
                )
            """,
        }

        try:
            import duckdb  # noqa: F401
            return self._run_via_python(queries)
        except ImportError:
            return self._run_via_cli(queries)


def main() -> None:
    pipeline = WarehousePipeline()
    results = pipeline.run_analytics()
    print("=== Star Schema Table Counts ===")
    for row in results["table_counts"]:
        print(f"  {row['table_name']:<14}: {row['row_count']:>6} rows")

    print("\n=== Annual Revenue (2016-2018) ===")
    for row in results["annual_revenue"]:
        print(f"  {row['year']}: ${row['total_revenue']:>12,.2f} ({row['order_count']} orders)")

    print("\n=== Peak Month per Year ===")
    for row in results["peak_month_per_year"]:
        print(f"  {row['year']}: {row['month_name']:<10} -> ${row['monthly_revenue']:>10,.2f}")

    print("\n=== Store Revenue Concentration ===")
    for row in results["store_revenue"]:
        print(f"  {row['store_name']:<18}: ${row['total_revenue']:>12,.2f} ({row['share_pct']}%)")

    print("\n=== Top 5 Customers ===")
    for row in results["top_customers"]:
        print(f"  {row['customer_name']:<20} ({row['city']}, {row['state']}): ${row['total_purchase_amount']:>10,.2f}")


if __name__ == "__main__":
    main()
