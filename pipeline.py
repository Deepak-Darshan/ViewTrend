from __future__ import annotations

# pyright: reportMissingImports=false

import pandas as pd


def process_data(df: pd.DataFrame) -> dict:
    """Process the NSW school incidents DataFrame and return summary stats."""

    def _sorted_counts_desc(series: pd.Series) -> dict:
        counts = series.value_counts(dropna=False)
        return {str(k): int(v) for k, v in counts.items()}

    def _priority_sort_key(val: object) -> tuple:
        s = "" if val is None else str(val).strip()
        digits = "".join(ch for ch in s if ch.isdigit())
        if digits:
            return (0, int(digits), s)
        return (1, s)

    required_columns = [
        "Case Number",
        "Date/Time Opened",
        "Term",
        "Incident Group",
        "Operational Directorate",
        "Principal Network Name",
        "Primary Category",
        "Primary Sub-Category",
        "Secondary Category",
        "Summary of the Incident (External Distribution)",
        "Incident Priority Rating",
        "Incident Occurred",
    ]

    if not isinstance(df, pd.DataFrame):
        raise TypeError("process_data expects a pandas DataFrame.")

    df = df.copy()

    # Strip whitespace and any UTF-8 BOM artifact (ï»¿) from column names.
    df.columns = [str(c).replace("ï»¿", "").strip() for c in df.columns]

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse datetime and extract year.
    opened_dt = pd.to_datetime(df["Date/Time Opened"], errors="coerce")
    df["Year"] = opened_dt.dt.year

    # Drop ID column from analysis.
    df = df.drop(columns=["Case Number"], errors="ignore")

    # Fill NaN for key categoricals.
    df["Primary Sub-Category"] = df["Primary Sub-Category"].fillna("Not Specified")
    df["Secondary Category"] = df["Secondary Category"].fillna("Not Specified")

    total_incidents = int(len(df))

    # Counts by year, ascending.
    by_year = (
        df.dropna(subset=["Year"])
        .groupby("Year", dropna=False)
        .size()
        .sort_index()
    )
    incidents_by_year = {int(k): int(v) for k, v in by_year.items()}

    # Counts by category/group/directorate, descending.
    incidents_by_category = _sorted_counts_desc(df["Primary Category"])
    incidents_by_group = _sorted_counts_desc(df["Incident Group"])
    incidents_by_directorate = _sorted_counts_desc(df["Operational Directorate"])

    # Priority distribution, ascending by rating (best-effort numeric order).
    priority_counts = df["Incident Priority Rating"].value_counts(dropna=False)
    priority_counts = priority_counts.sort_index(key=lambda idx: idx.map(_priority_sort_key))
    priority_distribution = {str(k): int(v) for k, v in priority_counts.items()}

    # Anomalies: per Primary Category, yearly count > mean + 2*std (std over yearly counts).
    anomalies: list[dict] = []
    cat_year_counts = (
        df.dropna(subset=["Year"])
        .groupby(["Primary Category", "Year"], dropna=False)
        .size()
        .rename("count")
        .reset_index()
    )

    for category, sub in cat_year_counts.groupby("Primary Category", dropna=False):
        counts = sub["count"].astype(float)
        mean = float(counts.mean()) if len(counts) else 0.0
        std = float(counts.std(ddof=0)) if len(counts) else 0.0
        if std <= 0:
            continue

        threshold = mean + 2.0 * std
        spikes = sub[sub["count"] > threshold]
        for _, row in spikes.iterrows():
            anomalies.append(
                {
                    "category": str(category),
                    "year": int(row["Year"]),
                    "count": int(row["count"]),
                    "mean": mean,
                    "std": std,
                }
            )

    anomalies.sort(key=lambda d: (d["category"], d["year"]))

    # Sample summaries: 10 random non-null summaries (stable seed).
    summaries = (
        df["Summary of the Incident (External Distribution)"]
        .dropna()
        .astype(str)
        .map(str.strip)
    )
    summaries = summaries[summaries != ""]
    n = min(10, int(len(summaries)))
    sample_summaries = (
        [] if n == 0 else summaries.sample(n=n, random_state=42).tolist()
    )

    return {
        "total_incidents": total_incidents,
        "incidents_by_year": incidents_by_year,
        "incidents_by_category": incidents_by_category,
        "incidents_by_group": incidents_by_group,
        "incidents_by_directorate": incidents_by_directorate,
        "priority_distribution": priority_distribution,
        "anomalies": anomalies,
        "sample_summaries": sample_summaries,
    }


if __name__ == "__main__":
    from pprint import pprint

    from data_fetcher import fetch_data

    result = process_data(fetch_data())
    pprint(result)

