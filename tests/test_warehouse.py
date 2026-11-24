"""Integration tests for the DuckDB Retail Star Schema & OLAP Query Suite."""

from __future__ import annotations

import unittest

from src.warehouse.runner import WarehousePipeline


class TestWarehousePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = WarehousePipeline().run_analytics()

    def test_star_schema_table_counts(self) -> None:
        counts = {row["table_name"]: row["row_count"] for row in self.results["table_counts"]}
        self.assertEqual(counts["DimDate"], 1096)  # 2016 (leap) + 2017 + 2018
        self.assertGreater(counts["DimCustomer"], 1000)
        self.assertEqual(counts["DimStore"], 3)
        self.assertGreater(counts["DimProduct"], 300)
        self.assertGreater(counts["FactSales"], 4000)

    def test_annual_revenue_and_april_2018_peak(self) -> None:
        annual = {row["year"]: row["total_revenue"] for row in self.results["annual_revenue"]}
        self.assertIn(2016, annual)
        self.assertIn(2017, annual)
        self.assertIn(2018, annual)
        self.assertGreater(annual[2017], annual[2016])
        self.assertGreater(annual[2017], annual[2018])

        peaks = {row["year"]: row["month_name"] for row in self.results["peak_month_per_year"]}
        self.assertEqual(peaks[2018], "April")

    def test_top_store_and_staff_insights(self) -> None:
        top_store = self.results["store_revenue"][0]
        self.assertEqual(top_store["store_name"], "Baldwin Bikes")
        self.assertGreater(top_store["share_pct"], 65.0)

        top_customer = self.results["top_customers"][0]
        self.assertEqual(top_customer["customer_name"], "Sharyn Hopkins")


if __name__ == "__main__":
    unittest.main()
