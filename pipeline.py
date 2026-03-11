from __future__ import annotations

# pyright: reportMissingImports=false

from typing import Tuple

import numpy as np
import pandas as pd


def compute_summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute basic summary statistics for numeric columns in the dataset.

    This function expects a pre-loaded Pandas DataFrame rather than reading from disk.
    """
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return pd.DataFrame()

    summary = numeric_df.describe().T
    summary["missing_count"] = numeric_df.isna().sum()
    summary["missing_pct"] = summary["missing_count"] / len(df) * 100.0
    return summary


def detect_anomalies(
    df: pd.DataFrame,
    zscore_threshold: float = 3.0,
) -> pd.DataFrame:
    """
    A simple anomaly detector using z-scores on numeric columns.

    - Calculates z-scores for each numeric column.
    - Flags rows as anomalous if any numeric column exceeds the threshold.
    """
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return pd.DataFrame(columns=list(df.columns) + ["is_anomaly"])

    # Compute z-scores
    mean = numeric_df.mean()
    std = numeric_df.std(ddof=0).replace(0, np.nan)
    zscores = (numeric_df - mean) / std

    # Rows where any absolute z-score exceeds the threshold
    is_anomaly = (zscores.abs() > zscore_threshold).any(axis=1)

    result = df.copy()
    result["is_anomaly"] = is_anomaly
    return result


def run_pipeline(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    High-level pipeline entrypoint.

    Accepts a DataFrame (already loaded from the CKAN API or CSV), then:
    - Computes summary statistics.
    - Runs anomaly detection.

    Returns (summary_stats_df, anomalies_df).
    """
    summary_stats = compute_summary_statistics(df)
    anomalies = detect_anomalies(df)
    return summary_stats, anomalies

