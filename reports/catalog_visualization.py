"""Skeleton utilities for visualizing the TERVYX entry catalog.

This module provides a minimal command line interface that can be expanded into a
full reporting workflow. The goal is to establish a reproducible foundation for
future dashboards without introducing heavy dependencies or bespoke plotting
logic at this stage.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[1] / "catalog" / "entry_catalog.csv"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "figures" / "catalog_category_counts.png"


def load_catalog(path: Path) -> pd.DataFrame:
    """Load the catalog CSV into a DataFrame."""

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Catalog file at {path} is empty.")
    return df


def summarize_by_category(df: pd.DataFrame) -> pd.Series:
    """Return counts of entries by category sorted in descending order."""

    if "category" not in df.columns:
        raise KeyError("Catalog data must include a 'category' column.")
    counts = df["category"].fillna("unassigned").value_counts()
    return counts.sort_values(ascending=False)


def plot_category_counts(counts: pd.Series, output_path: Path) -> None:
    """Render a simple bar chart visualizing entry counts by category."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    counts.plot(kind="bar", ax=ax, color="#2E86AB")
    ax.set_title("TERVYX Catalog Entries by Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Number of Entries")
    ax.tick_params(axis="x", rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def build_argument_parser() -> argparse.ArgumentParser:
    """Configure CLI arguments for quick explorations."""

    parser = argparse.ArgumentParser(description="Visualize the TERVYX catalog.")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Path to the entry_catalog.csv file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to save the generated plot.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the plot interactively in addition to saving it.",
    )
    return parser


def main(args: Optional[list[str]] = None) -> Path:
    """CLI entrypoint for generating the catalog visualization."""

    parser = build_argument_parser()
    parsed = parser.parse_args(args=args)
    catalog_path = parsed.catalog
    output_path = parsed.output

    df = load_catalog(catalog_path)
    counts = summarize_by_category(df)
    plot_category_counts(counts, output_path)

    if parsed.show:
        plt.show()

    return output_path


if __name__ == "__main__":
    main()
