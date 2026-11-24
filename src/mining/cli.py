"""CLI runner for the AOI & BUC Data Mining module.

Author: Rajath Gadagkar
"""

from __future__ import annotations

from .aoi import load_marketing_dataset
from .benchmark import run_full_benchmark


def main() -> None:
    records = load_marketing_dataset()
    results = run_full_benchmark(records)

    print(f"=== Attribute-Oriented Induction ({results['aoi']['total_records']} records) ===")
    for rule in results["aoi"]["rules"]:
        print(
            f"  Budget={rule['Budget_Category']:<6} | Revenue={rule['Revenue_Category']:<6} "
            f"-> {rule['count']:>4} ({rule['support_pct']:>5.2f}%)"
        )

    print("\n=== BUC Benchmark: Minsup vs. Runtime (page_size=1000) ===")
    for row in results["minsup_sweep"]:
        print(
            f"  minsup={row['minsup']:<4} -> {row['runtime_ms']:>7.3f} ms "
            f"({row['frequent_itemsets']} frequent itemsets)"
        )

    print("\n=== BUC Benchmark: Page Size vs. Runtime (minsup=100) ===")
    for row in results["page_size_sweep"]:
        print(
            f"  page_size={row['page_size']:<4} -> {row['runtime_ms']:>7.3f} ms "
            f"({row['frequent_itemsets']} frequent itemsets)"
        )

    print("\n=== BUC Algorithm Variant Comparison (4 Dimensions, minsup=100) ===")
    for row in results["variant_comparison"]:
        print(
            f"  {row['algorithm']:<32}: {row['runtime_ms']:>7.3f} ms "
            f"({row['frequent_itemsets']} itemsets)"
        )


if __name__ == "__main__":
    main()
