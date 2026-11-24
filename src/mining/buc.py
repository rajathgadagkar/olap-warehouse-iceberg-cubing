"""Bottom-Up Cube (BUC) Iceberg Cubing Algorithms.

Implements four variants of the Bottom-Up Cube algorithm for iceberg data cube
computation:
1. ``buc_in_memory``: Standard recursive in-memory partitioning BUC.
2. ``buc_paged``: Simulated out-of-memory BUC that scans partitions in fixed-size
   pages to aggregate frequencies under constrained memory budgets.
3. ``buc_apriori_pruned``: Explicit Apriori-checked recursive BUC.
4. ``buc_iceberg_sorted``: Cardinality-sorted Iceberg BUC that processes
   highest-cardinality dimensions first to maximize early partition pruning.

Author: Rajath Gadagkar
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence


Itemset = tuple[tuple[str, Any], ...]


def _canonicalize(itemset: Itemset) -> Itemset:
    """Return a dimension-sorted canonical representation for comparison."""
    return tuple(sorted(itemset, key=lambda pair: pair[0]))


def buc_in_memory(
    records: Sequence[dict[str, Any]],
    dimensions: Sequence[str],
    minsup: int,
) -> dict[Itemset, int]:
    """Compute an iceberg cube in memory via recursive bottom-up partitioning."""
    output: dict[Itemset, int] = {}
    num_dims = len(dimensions)

    def _recurse(data: Sequence[dict[str, Any]], dim_idx: int, prefix: Itemset) -> None:
        if dim_idx >= num_dims or len(data) < minsup:
            return

        dim = dimensions[dim_idx]
        buckets: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for row in data:
            buckets[row[dim]].append(row)

        for val, partition in buckets.items():
            count = len(partition)
            if count >= minsup:
                itemset = prefix + ((dim, val),)
                output[itemset] = count
                for next_dim in range(dim_idx + 1, num_dims):
                    _recurse(partition, next_dim, itemset)

    for start_dim in range(num_dims):
        _recurse(records, start_dim, ())

    return output


def buc_paged(
    records: Sequence[dict[str, Any]],
    dimensions: Sequence[str],
    minsup: int,
    page_size: int = 1000,
) -> dict[Itemset, int]:
    """Compute an iceberg cube using simulated out-of-memory paging.

    Each partition is scanned in chunks of ``page_size`` rows to accumulate
    frequency counts without materializing full-column aggregates at once,
    followed by paged partition writes for values meeting ``minsup``.
    """
    if page_size <= 0:
        raise ValueError("page_size must be a positive integer.")

    output: dict[Itemset, int] = {}
    num_dims = len(dimensions)

    def _recurse_paged(
        data: Sequence[dict[str, Any]], dim_idx: int, prefix: Itemset
    ) -> None:
        if dim_idx >= num_dims or len(data) < minsup:
            return

        dim = dimensions[dim_idx]
        counts: Counter[Any] = Counter()

        # Pass 1: Page-by-page frequency aggregation
        for start in range(0, len(data), page_size):
            page = data[start : start + page_size]
            for row in page:
                counts[row[dim]] += 1

        frequent_vals = {val for val, cnt in counts.items() if cnt >= minsup}
        if not frequent_vals:
            return

        # Pass 2: Page-by-page partitioning only for frequent values
        partitions: dict[Any, list[dict[str, Any]]] = {
            val: [] for val in frequent_vals
        }
        for start in range(0, len(data), page_size):
            page = data[start : start + page_size]
            for row in page:
                val = row[dim]
                if val in partitions:
                    partitions[val].append(row)

        for val in frequent_vals:
            itemset = prefix + ((dim, val),)
            output[itemset] = counts[val]
            for next_dim in range(dim_idx + 1, num_dims):
                _recurse_paged(partitions[val], next_dim, itemset)

    for start_dim in range(num_dims):
        _recurse_paged(records, start_dim, ())

    return output


def buc_apriori_pruned(
    records: Sequence[dict[str, Any]],
    dimensions: Sequence[str],
    minsup: int,
) -> dict[Itemset, int]:
    """Compute an iceberg cube with explicit Apriori cardinality upper-bound pruning."""
    output: dict[Itemset, int] = {}
    num_dims = len(dimensions)

    def _recurse(data: Sequence[dict[str, Any]], dim_idx: int, prefix: Itemset) -> None:
        # Explicit Apriori guard: a partition smaller than minsup cannot yield frequent supersets
        if dim_idx >= num_dims or len(data) < minsup:
            return

        dim = dimensions[dim_idx]
        counts = Counter(row[dim] for row in data)
        frequent = {val: cnt for val, cnt in counts.items() if cnt >= minsup}
        if not frequent:
            return

        partitions: dict[Any, list[dict[str, Any]]] = {val: [] for val in frequent}
        for row in data:
            val = row[dim]
            if val in partitions:
                partitions[val].append(row)

        for val, count in frequent.items():
            itemset = prefix + ((dim, val),)
            output[itemset] = count
            if count >= minsup:
                for next_dim in range(dim_idx + 1, num_dims):
                    _recurse(partitions[val], next_dim, itemset)

    for start_dim in range(num_dims):
        _recurse(records, start_dim, ())

    return output


def buc_iceberg_sorted(
    records: Sequence[dict[str, Any]],
    dimensions: Sequence[str],
    minsup: int,
) -> dict[Itemset, int]:
    """Iceberg BUC optimized by descending dimension-cardinality ordering.

    Ordering dimensions from highest cardinality to lowest shrinks partition
    sizes earlier in the recursion tree, triggering Apriori pruning sooner.
    """
    sorted_dims = sorted(
        dimensions,
        key=lambda d: len({row[d] for row in records}),
        reverse=True,
    )
    raw_output = buc_in_memory(records, sorted_dims, minsup)
    return {_canonicalize(k): v for k, v in raw_output.items()}
