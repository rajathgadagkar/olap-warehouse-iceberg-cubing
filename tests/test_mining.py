"""Unit tests for Attribute-Oriented Induction (AOI) and BUC Iceberg Cubing."""

from __future__ import annotations

import unittest

from src.mining.aoi import generalize_budget, generalize_revenue, load_marketing_dataset, run_aoi
from src.mining.buc import (
    _canonicalize,
    buc_apriori_pruned,
    buc_iceberg_sorted,
    buc_in_memory,
    buc_paged,
)


class TestMiningEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_marketing_dataset()
        cls.dims = ("Budget_Category", "Revenue_Category", "Subscription_Tier")

    def test_dataset_loaded(self) -> None:
        self.assertEqual(len(self.records), 10_000)

    def test_generalization_boundaries(self) -> None:
        self.assertEqual(generalize_budget(9_999.99), "Low")
        self.assertEqual(generalize_budget(10_000.00), "Medium")
        self.assertEqual(generalize_budget(30_000.00), "High")
        self.assertEqual(generalize_revenue(24_999.99), "Low")
        self.assertEqual(generalize_revenue(25_000.00), "Medium")
        self.assertEqual(generalize_revenue(75_000.00), "High")

    def test_aoi_characteristic_rules(self) -> None:
        result = run_aoi(self.records)
        self.assertEqual(result["total_records"], 10_000)
        self.assertEqual(len(result["rules"]), 9)
        top_rule = result["rules"][0]
        self.assertEqual(top_rule["Budget_Category"], "Medium")
        self.assertEqual(top_rule["Revenue_Category"], "Medium")
        self.assertEqual(top_rule["count"], 2091)

    def test_buc_variants_exact_equivalence(self) -> None:
        minsup = 100
        base = {_canonicalize(k): v for k, v in buc_in_memory(self.records, self.dims, minsup).items()}
        paged = {_canonicalize(k): v for k, v in buc_paged(self.records, self.dims, minsup, page_size=500).items()}
        apriori = {_canonicalize(k): v for k, v in buc_apriori_pruned(self.records, self.dims, minsup).items()}
        sorted_buc = buc_iceberg_sorted(self.records, self.dims, minsup)

        self.assertGreater(len(base), 0)
        self.assertEqual(base, paged)
        self.assertEqual(base, apriori)
        self.assertEqual(base, sorted_buc)

    def test_buc_minsup_monotonicity(self) -> None:
        c_low = buc_in_memory(self.records, self.dims, minsup=100)
        c_high = buc_in_memory(self.records, self.dims, minsup=1000)
        self.assertGreaterEqual(len(c_low), len(c_high))
        self.assertTrue(all(v >= 1000 for v in c_high.values()))


if __name__ == "__main__":
    unittest.main()
