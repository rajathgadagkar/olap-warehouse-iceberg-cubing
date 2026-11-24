"""Performance Benchmarking Suite for AOI and BUC Variants.

Measures runtime across:
1. Minimum support (``minsup``) sweeps with fixed page size.
2. Simulated memory budget (``page_size``) sweeps with fixed ``minsup``.
3. Algorithm variant comparison (In-Memory, Paged, Apriori-Pruned, Cardinality-Sorted).
4. AOI generalization vs. BUC iceberg cubing runtime comparison.

Author: Rajath Gadagkar
"""

from __future__ import annotations

import time
from typing import Any, Callable, Sequence

from .aoi import run_aoi
from .buc import (
    buc_apriori_pruned,
    buc_iceberg_sorted,
    buc_in_memory,
    buc_paged,
)


DEFAULT_DIMENSIONS = (
    "Budget_Category",
    "Revenue_Category",
    "Subscription_Tier",
)


def _time_fn(fn: Callable[[], Any], repeats: int = 3) -> tuple[float, Any]:
    """Return median runtime in milliseconds and the last function output."""
    timings: list[float] = []
    result: Any = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        timings.append(elapsed_ms)
    timings.sort()
    return round(timings[len(timings) // 2], 3), result


def run_full_benchmark(
    records: Sequence[dict[str, Any]],
    dimensions: Sequence[str] = DEFAULT_DIMENSIONS,
    repeats: int = 3,
) -> dict[str, Any]:
    """Execute the complete AOI & BUC benchmark suite."""
    minsup_values = [50, 100, 200, 500, 1000, 1500]
    minsup_sweep: list[dict[str, Any]] = []
    for ms in minsup_values:
        ms_time, cube = _time_fn(
            lambda m=ms: buc_paged(records, dimensions, minsup=m, page_size=1000),
            repeats=repeats,
        )
        minsup_sweep.append(
            {
                "minsup": ms,
                "runtime_ms": ms_time,
                "frequent_itemsets": len(cube),
            }
        )

    page_sizes = [100, 250, 500, 1000, 2000, 5000]
    page_size_sweep: list[dict[str, Any]] = []
    for ps in page_sizes:
        ps_time, cube = _time_fn(
            lambda p=ps: buc_paged(records, dimensions, minsup=100, page_size=p),
            repeats=repeats,
        )
        page_size_sweep.append(
            {
                "page_size": ps,
                "runtime_ms": ps_time,
                "frequent_itemsets": len(cube),
            }
        )

    # Multi-dimension stress test including higher-cardinality Common_Keywords
    extended_dims = (
        "Budget_Category",
        "Revenue_Category",
        "Subscription_Tier",
        "Common_Keywords",
    )
    variants: list[dict[str, Any]] = []
    for label, fn in [
        ("In-Memory BUC", lambda: buc_in_memory(records, extended_dims, minsup=100)),
        ("Paged BUC (page=1000)", lambda: buc_paged(records, extended_dims, minsup=100, page_size=1000)),
        ("Apriori-Pruned BUC", lambda: buc_apriori_pruned(records, extended_dims, minsup=100)),
        ("Cardinality-Sorted Iceberg BUC", lambda: buc_iceberg_sorted(records, extended_dims, minsup=100)),
    ]:
        v_time, cube = _time_fn(fn, repeats=repeats)
        variants.append(
            {
                "algorithm": label,
                "runtime_ms": v_time,
                "frequent_itemsets": len(cube),
            }
        )

    aoi_time, aoi_result = _time_fn(lambda: run_aoi(list(records)), repeats=repeats)
    buc_time, buc_cube = _time_fn(
        lambda: buc_in_memory(records, dimensions, minsup=100), repeats=repeats
    )

    # Full iceberg cube at minsup=50 for interactive browser filtering
    full_cube = buc_in_memory(records, dimensions, minsup=50)
    serialized_cube = [
        {
            "dimensions": [f"{k}={v}" for k, v in itemset],
            "depth": len(itemset),
            "count": count,
        }
        for itemset, count in sorted(full_cube.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    return {
        "dimensions": list(dimensions),
        "extended_dimensions": list(extended_dims),
        "aoi": aoi_result,
        "minsup_sweep": minsup_sweep,
        "page_size_sweep": page_size_sweep,
        "variant_comparison": variants,
        "aoi_vs_buc": [
            {"method": "AOI Generalization", "runtime_ms": aoi_time, "patterns_found": len(aoi_result["rules"])},
            {"method": "BUC (In-Memory, minsup=100)", "runtime_ms": buc_time, "patterns_found": len(buc_cube)},
        ],
        "iceberg_cube_minsup_50": serialized_cube,
    }
