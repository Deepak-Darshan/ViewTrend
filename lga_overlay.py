"""
lga_overlay.py
--------------
LGA Disadvantage Overlay for NSW school incident data.

Strategy
~~~~~~~~
The national SEIFA top-10 disadvantaged LGAs (Woorabinda, Cherbourg, etc.)
are all in QLD / NT — none are in NSW — so a direct LGA join on the incident
data is not possible.  Instead we use the NSW DoE's own Operational Directorate
classification, which maps cleanly onto three SEIFA tiers:

  • Advantaged  – Metropolitan directorates
                  (encompass the advantaged NSW LGAs: Woollahra, Mosman,
                   Ku-ring-gai, North Sydney, Waverley, Lane Cove)
  • Disadvantaged – Connected Communities directorates
                  (NSW DoE's designated program for the most remote and
                   socioeconomically disadvantaged communities, primarily
                   Aboriginal schools and Far West NSW)
  • Regional/Rural – all remaining regional and rural directorates

The advantaged / disadvantaged LGA CSV files are loaded and used to annotate
the overlay with real SEIFA source data for transparency.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

_ADVANTAGED_KEYWORDS = ("metropolitan",)
_DISADVANTAGED_KEYWORDS = ("connected communities",)

def _classify_directorate(directorate: str) -> str:
    """Map an Operational Directorate string to a SEIFA tier label."""
    d = str(directorate).strip().lower()
    if any(k in d for k in _DISADVANTAGED_KEYWORDS):
        return "Disadvantaged (Connected Communities)"
    if any(k in d for k in _ADVANTAGED_KEYWORDS):
        return "Advantaged (Metropolitan)"
    return "Regional / Rural"


# ---------------------------------------------------------------------------
# LGA CSV loading
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent / "data"


def _load_lga_csv(filename: str) -> list[str]:
    """Return a list of LGA names from one of the SEIFA reference CSVs."""
    path = _DATA_DIR / filename
    try:
        df = pd.read_csv(path, skiprows=1, encoding="utf-8")
        df.columns = [str(c).strip().strip('"') for c in df.columns]
        # Columns: Rank, LGA, Population, State
        lgas = df["LGA"].dropna().astype(str).str.strip().str.strip('"').tolist()
        # Remove footer lines (non-LGA rows that sneak in)
        return [l for l in lgas if l and not l.startswith("a.") and not l.startswith("Source")]
    except Exception:
        return []


def load_reference_lgas() -> dict:
    """
    Return a dict with the SEIFA reference LGA lists loaded from the local CSVs.

    Keys:
        advantaged_lgas  – list[str]  top-10 most advantaged LGA names (national)
        disadvantaged_lgas – list[str] top-10 most disadvantaged LGA names (national)
        nsw_advantaged_lgas – list[str] NSW-only subset of advantaged list
    """
    advantaged = _load_lga_csv("Ten most advantaged LGAs.csv")
    disadvantaged = _load_lga_csv("Ten most disadvantaged LGAs.csv")

    # Filter to NSW-only for the advantaged list (these are the ones geographically
    # relevant to the NSW school incident dataset).
    try:
        adv_path = _DATA_DIR / "Ten most advantaged LGAs.csv"
        adv_df = pd.read_csv(adv_path, skiprows=1, encoding="utf-8")
        adv_df.columns = [str(c).strip().strip('"') for c in adv_df.columns]
        adv_df["LGA"] = adv_df["LGA"].astype(str).str.strip().str.strip('"')
        adv_df["State"] = adv_df["State"].astype(str).str.strip().str.strip('"')
        nsw_adv = adv_df[adv_df["State"] == "New South Wales"]["LGA"].tolist()
    except Exception:
        nsw_adv = []

    return {
        "advantaged_lgas": advantaged,
        "disadvantaged_lgas": disadvantaged,
        "nsw_advantaged_lgas": nsw_adv,
    }


# ---------------------------------------------------------------------------
# Main overlay function
# ---------------------------------------------------------------------------

def build_overlay(df: pd.DataFrame) -> dict:
    """
    Enrich the incidents DataFrame with a SEIFA tier column and return
    comparative statistics across the three tiers.

    Parameters
    ----------
    df : pd.DataFrame
        The incidents DataFrame as returned by data_fetcher.fetch_data()
        after pipeline.process_data() column normalisation has been applied.
        Must contain 'Operational Directorate', 'Primary Category', and
        optionally 'Year' and 'Incident Priority Rating'.

    Returns
    -------
    dict with keys:
        tier_counts          – {tier: total_incidents}
        tier_category_matrix – {tier: {category: count}}  top-5 per tier
        tier_priority        – {tier: {priority: count}}
        tier_year_series     – {tier: {year: count}}
        reference_lgas       – output of load_reference_lgas()
        tier_incident_rate   – {tier: incidents_per_school_network}
        key_finding          – str  plain-English top-line finding
    """
    df = df.copy()
    df.columns = [str(c).replace("ï»¿", "").strip() for c in df.columns]

    if "Operational Directorate" not in df.columns:
        return {}

    df["_seifa_tier"] = df["Operational Directorate"].apply(_classify_directorate)

    reference = load_reference_lgas()

    # ── Tier counts ────────────────────────────────────────────────────────
    tier_counts = df["_seifa_tier"].value_counts().to_dict()

    # ── Tier × category (top 5 categories per tier) ────────────────────────
    tier_category_matrix: dict[str, dict[str, int]] = {}
    if "Primary Category" in df.columns:
        for tier, sub in df.groupby("_seifa_tier"):
            top5 = sub["Primary Category"].value_counts().head(5).to_dict()
            tier_category_matrix[str(tier)] = {str(k): int(v) for k, v in top5.items()}

    # ── Tier × priority ────────────────────────────────────────────────────
    tier_priority: dict[str, dict[str, int]] = {}
    if "Incident Priority Rating" in df.columns:
        for tier, sub in df.groupby("_seifa_tier"):
            dist = sub["Incident Priority Rating"].value_counts().to_dict()
            tier_priority[str(tier)] = {str(k): int(v) for k, v in dist.items()}

    # ── Tier × year time series ────────────────────────────────────────────
    tier_year_series: dict[str, dict[int, int]] = {}
    if "Year" in df.columns:
        for tier, sub in df.groupby("_seifa_tier"):
            by_year = (
                sub.dropna(subset=["Year"])
                .groupby("Year")
                .size()
                .sort_index()
            )
            tier_year_series[str(tier)] = {int(k): int(v) for k, v in by_year.items()}

    # ── Incidents per network (rough rate proxy) ───────────────────────────
    tier_incident_rate: dict[str, float] = {}
    if "Principal Network Name" in df.columns:
        for tier, sub in df.groupby("_seifa_tier"):
            n_networks = sub["Principal Network Name"].nunique()
            rate = len(sub) / n_networks if n_networks else 0.0
            tier_incident_rate[str(tier)] = round(rate, 1)

    # ── Key finding ────────────────────────────────────────────────────────
    key_finding = _derive_key_finding(tier_counts, tier_incident_rate, tier_category_matrix)

    return {
        "tier_counts": {str(k): int(v) for k, v in tier_counts.items()},
        "tier_category_matrix": tier_category_matrix,
        "tier_priority": tier_priority,
        "tier_year_series": tier_year_series,
        "reference_lgas": reference,
        "tier_incident_rate": tier_incident_rate,
        "key_finding": key_finding,
    }


def _derive_key_finding(
    tier_counts: dict,
    tier_incident_rate: dict,
    tier_category_matrix: dict,
) -> str:
    """Generate a plain-English top-line finding from the overlay stats."""
    dis_key = "Disadvantaged (Connected Communities)"
    adv_key = "Advantaged (Metropolitan)"

    dis_rate = tier_incident_rate.get(dis_key)
    adv_rate = tier_incident_rate.get(adv_key)

    if dis_rate and adv_rate and adv_rate > 0:
        ratio = dis_rate / adv_rate
        direction = "higher" if ratio > 1 else "lower"
        pct = abs(ratio - 1) * 100
        finding = (
            f"Schools in Connected Communities (disadvantaged) areas report "
            f"{pct:.0f}% {direction} incidents per network than Metropolitan "
            f"(advantaged) schools ({dis_rate:.0f} vs {adv_rate:.0f} per network)."
        )
    else:
        dis_count = tier_counts.get(dis_key, 0)
        adv_count = tier_counts.get(adv_key, 0)
        finding = (
            f"Disadvantaged (Connected Communities) schools recorded {dis_count:,} "
            f"incidents vs {adv_count:,} for Metropolitan (advantaged) schools across "
            f"the 2020–2023 reporting period."
        )

    # Append top category divergence if available
    dis_cats = tier_category_matrix.get(dis_key, {})
    adv_cats = tier_category_matrix.get(adv_key, {})
    if dis_cats and adv_cats:
        top_dis = next(iter(dis_cats))
        top_adv = next(iter(adv_cats))
        if top_dis != top_adv:
            finding += (
                f" The top incident category differs: '{top_dis}' dominates in "
                f"disadvantaged areas versus '{top_adv}' in advantaged areas."
            )

    return finding
