# Attribute-Oriented Induction (AOI) & Bottom-Up Cubing (BUC) Technical Report

**Author:** Rajath Gadagkar

## 1. Attribute-Oriented Induction (AOI)

Attribute-Oriented Induction (AOI) summarizes large datasets into concise, human-readable characteristic rules by replacing low-level numerical values with higher-level concept hierarchies.

Applied to the 10,000-record marketing campaign dataset (`data/marketing/marketing_campaigns.csv`), continuous `Budget` and `Revenue_Generated` metrics were generalized into three tiers (`Low`, `Medium`, `High`) aligned to the empirical quartile distribution:
- **Budget:** `Low` (< $10,000), `Medium` ($10,000–$29,999), `High` (≥ $30,000)
- **Revenue:** `Low` (< $25,000), `Medium` ($25,000–$74,999), `High` (≥ $75,000)

The resulting 3×3 generalization matrix identifies `(Budget_Category=Medium, Revenue_Category=Medium)` as the dominant characteristic rule with **2,091 campaigns (20.91%)**, closely followed by `(Budget_Category=High, Revenue_Category=Medium)` at **2,023 campaigns (20.23%)**.

## 2. Bottom-Up Cube (BUC) Iceberg Cubing

The **Bottom-Up Cube (BUC)** algorithm computes iceberg data cubes — returning only cuboids whose support meets or exceeds a minimum support threshold (`minsup`). By partitioning data from 1D cuboids upward toward higher-dimensional combinations, BUC prunes entire subtrees the moment a partition's cardinality drops below `minsup`.

This project implements four modular variants in `src/mining/buc.py`:
1. **In-Memory BUC (`buc_in_memory`):** Standard recursive partitioning assuming the working set fits in RAM.
2. **Out-of-Memory Paged BUC (`buc_paged`):** Simulates constrained memory budgets by scanning partitions in fixed-size chunks (`page_size`) to aggregate frequencies before writing frequent partitions.
3. **Apriori-Pruned BUC (`buc_apriori_pruned`):** Enforces explicit Apriori partition-size guards prior to scanning and recursing.
4. **Cardinality-Sorted Iceberg BUC (`buc_iceberg_sorted`):** Sorts input dimensions by descending cardinality before cubing, producing smaller partitions earlier in the recursion tree to trigger Apriori pruning sooner on multi-dimensional workloads.

All four variants are unit-tested (`tests/test_mining.py`) to guarantee bit-for-bit identical canonical iceberg cubes.

## 3. Performance Observations

- **Minimum Support (`minsup`) vs. Runtime:** Increasing `minsup` monotonically decreases both the number of surviving cuboids (from 63 itemsets at `minsup=50` down to 14 at `minsup=1500`) and overall runtime, as Apriori pruning eliminates deeper recursive partitions early.
- **Simulated Memory (`page_size`) vs. Runtime:** Smaller page sizes increase loop and I/O pass overhead, whereas larger pages amortize scan overhead until the dataset fits within a single page.
- **Dimension Sorting Optimization:** On datasets with heterogeneous dimension cardinalities, sorting dimensions from highest to lowest cardinality minimizes intermediate partition size and accelerates early pruning without altering cube outputs.

## 4. Comparative Summary: BUC vs. AOI

| Dimension | Bottom-Up Cube (BUC) | Attribute-Oriented Induction (AOI) |
| :--- | :--- | :--- |
| **Primary Goal** | Compute granular multi-dimensional iceberg aggregates | Generalize raw data into concise characteristic rules |
| **Traversal Direction** | Bottom-up (1D → k-D recursive partitioning) | Top-down (concept hierarchy generalization) |
| **Output Form** | Frequent multi-attribute itemsets & support counts | Compact 2D/low-dimensional rule tables & heatmaps |
| **Ideal Use Case** | OLAP exploration, anomaly hunting, iceberg cubing | Executive summarization, initial exploratory profiling |
| **Concrete Example** | `(Budget=Medium, Revenue=Medium, Tier=Basic) -> 736` | `(Budget=High, Revenue=Medium) -> 2,023 (20.23%)` |
