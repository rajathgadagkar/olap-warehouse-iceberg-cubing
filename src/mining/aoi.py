"""Attribute-Oriented Induction (AOI) Engine.

Performs concept hierarchy generalization on numerical marketing attributes
(``Budget`` and ``Revenue_Generated``) and extracts characteristic rules
describing high-level data distributions.

Author: Rajath Gadagkar
"""

from __future__ import annotations

import csv
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_MARKETING_CSV = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "marketing"
    / "marketing_campaigns.csv"
)


def generalize_budget(budget: float) -> str:
    """Map numerical campaign budget into concept hierarchy tiers."""
    if budget < 10_000:
        return "Low"
    if budget < 30_000:
        return "Medium"
    return "High"


def generalize_revenue(revenue: float) -> str:
    """Map numerical generated revenue into concept hierarchy tiers."""
    if revenue < 25_000:
        return "Low"
    if revenue < 75_000:
        return "Medium"
    return "High"


def load_marketing_dataset(
    csv_path: Path | str = DEFAULT_MARKETING_CSV,
) -> list[dict[str, Any]]:
    """Load and generalize the marketing campaigns CSV dataset."""
    records: list[dict[str, Any]] = []
    with open(csv_path, mode="r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            budget = float(row["Budget"])
            revenue = float(row["Revenue_Generated"])
            records.append(
                {
                    "Campaign_ID": row["Campaign_ID"],
                    "Product_ID": row["Product_ID"],
                    "Budget": budget,
                    "Revenue_Generated": revenue,
                    "Subscription_Tier": row["Subscription_Tier"],
                    "Common_Keywords": row["Common_Keywords"],
                    "Budget_Category": generalize_budget(budget),
                    "Revenue_Category": generalize_revenue(revenue),
                }
            )
    return records


def describe_numeric_fields(records: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Compute summary statistics (count, mean, std, min, quartiles, max)."""
    summary: dict[str, dict[str, float]] = {}
    for field in ("Budget", "Revenue_Generated"):
        vals = sorted(r[field] for r in records)
        n = len(vals)
        q1 = vals[int(0.25 * (n - 1))]
        q2 = statistics.median(vals)
        q3 = vals[int(0.75 * (n - 1))]
        summary[field] = {
            "count": float(n),
            "mean": round(statistics.mean(vals), 2),
            "std": round(statistics.stdev(vals), 2),
            "min": round(vals[0], 2),
            "25%": round(q1, 2),
            "50%": round(q2, 2),
            "75%": round(q3, 2),
            "max": round(vals[-1], 2),
        }
    return summary


def run_aoi(
    records: list[dict[str, Any]],
    attributes: tuple[str, str] = ("Budget_Category", "Revenue_Category"),
) -> dict[str, Any]:
    """Extract AOI characteristic rules and a 2D contingency matrix."""
    attr_a, attr_b = attributes
    counts = Counter((r[attr_a], r[attr_b]) for r in records)
    total = len(records)

    rules = [
        {
            attr_a: k[0],
            attr_b: k[1],
            "count": v,
            "support_pct": round((v / total) * 100, 2) if total else 0.0,
        }
        for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    tier_order = ["Low", "Medium", "High"]
    matrix = {
        row_tier: {
            col_tier: counts.get((row_tier, col_tier), 0)
            for col_tier in tier_order
        }
        for row_tier in tier_order
    }

    return {
        "total_records": total,
        "attributes": list(attributes),
        "rules": rules,
        "heatmap_matrix": matrix,
        "numeric_summary": describe_numeric_fields(records),
    }
