from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from data_fetcher import fetch_data
from pipeline import process_data
from ai_insights import generate_insights


st.set_page_config(
    page_title="ViewTrend — NSW School Incident Insights",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """Load and cache the NSW school incidents dataset."""
    return fetch_data()


def _priority_sort_key(val: object) -> tuple:
    """Numeric-aware sort key for Incident Priority Rating values."""
    s = "" if val is None else str(val).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    if digits:
        return (0, int(digits), s)
    return (1, s)


def main() -> None:
    with st.spinner("Loading data..."):
        df = load_data()

    # Clean column names (same BOM + whitespace stripping as pipeline.py)
    df_clean = df.copy()
    df_clean.columns = [str(c).replace("ï»¿", "").strip() for c in df_clean.columns]

    # Parse Year on the full dataset so filter options are always complete
    df_clean["Year"] = pd.to_datetime(
        df_clean["Date/Time Opened"], errors="coerce"
    ).dt.year

    total_rows = len(df_clean)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("ViewTrend")

        # ── Filters (above metadata) ──────────────────────────────────────────
        st.subheader("Filters")

        year_range: tuple[int, int] = st.slider(
            "📅 Year Range",
            min_value=2020,
            max_value=2023,
            value=(2020, 2023),
        )

        all_groups = sorted(df_clean["Incident Group"].dropna().unique().tolist())
        selected_groups: list[str] = st.multiselect(
            "🗂️ Incident Group",
            options=all_groups,
            default=all_groups,
        )

        all_directorates = sorted(
            df_clean["Operational Directorate"].dropna().unique().tolist()
        )
        selected_directorates: list[str] = st.multiselect(
            "🏫 Operational Directorate",
            options=all_directorates,
            default=all_directorates,
        )

        all_priorities = sorted(
            df_clean["Incident Priority Rating"].dropna().unique().tolist(),
            key=_priority_sort_key,
        )
        selected_priorities: list[str] = st.multiselect(
            "⚠️ Incident Priority Rating",
            options=all_priorities,
            default=all_priorities,
        )

        # Apply filters
        if selected_groups and selected_directorates and selected_priorities:
            filtered_df = df_clean[
                (df_clean["Year"].between(year_range[0], year_range[1]))
                & (df_clean["Incident Group"].isin(selected_groups))
                & (df_clean["Operational Directorate"].isin(selected_directorates))
                & (df_clean["Incident Priority Rating"].isin(selected_priorities))
            ]
        else:
            filtered_df = df_clean.iloc[0:0]  # empty but schema-preserving

        # Filter count callout
        st.caption(f"Showing **{len(filtered_df):,}** of {total_rows:,} incidents")

        st.divider()

        # ── Metadata (below filters) ──────────────────────────────────────────
        st.metric("Total rows loaded", total_rows)
        st.metric("Last refreshed", dt.datetime.now().strftime("%Y-%m-%d %H:%M"))

        with st.expander("📊 About this data"):
            st.markdown(
                "This dashboard analyses NSW Government school incident reports "
                "published as open data. The dataset covers biannual incident "
                "summaries from 2020 to 2023, including incident categories, "
                "priority ratings, operational directorates, and principal "
                "networks across public schools in New South Wales."
            )

    # ── Empty filter guard ────────────────────────────────────────────────────
    if filtered_df.empty:
        st.warning(
            "No incidents match the current filters. Please adjust your selection."
        )
        st.stop()

    # ── Process filtered data ─────────────────────────────────────────────────
    summary = process_data(filtered_df)
    years = list(summary["incidents_by_year"].keys())

    # ── Filter state key (used to detect staleness of AI insights) ────────────
    current_filter_key = (
        year_range,
        tuple(sorted(selected_groups)),
        tuple(sorted(selected_directorates)),
        tuple(sorted(selected_priorities)),
    )

    # ── Two-column layout ─────────────────────────────────────────────────────
    left, right = st.columns([1.2, 1])

    # ── Left column ───────────────────────────────────────────────────────────
    with left:
        st.title("ViewTrend — NSW School Incident Insights")

        # Dataset overview metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Incidents", summary["total_incidents"])
        c2.metric(
            "Year Range",
            f"{min(years)} – {max(years)}" if years else "N/A",
        )
        c3.metric("Categories", len(summary["incidents_by_category"]))

        # Line chart: incidents by year
        st.subheader("Incidents by Year")
        st.line_chart(pd.DataFrame({"Incidents": summary["incidents_by_year"]}))

        # Bar chart: top 8 primary categories
        st.subheader("Top 8 Primary Categories")
        top8 = dict(list(summary["incidents_by_category"].items())[:8])
        st.bar_chart(pd.DataFrame({"Count": top8}))

        # Anomalies table
        st.subheader("Detected Anomalies")
        if summary["anomalies"]:
            st.dataframe(pd.DataFrame(summary["anomalies"]), use_container_width=True)
        else:
            st.info("No statistical anomalies detected in the dataset.")

        # ── LGA Disadvantage Overlay ───────────────────────────────────────
        overlay = summary.get("lga_overlay", {})
        if overlay:
            st.subheader("LGA Disadvantage Overlay")

            tier_counts = overlay.get("tier_counts", {})
            tier_rate = overlay.get("tier_incident_rate", {})
            reference = overlay.get("reference_lgas", {})

            # Key finding callout
            key_finding = overlay.get("key_finding", "")
            if key_finding:
                st.info(key_finding)

            # Tier summary metrics
            tiers = [
                "Disadvantaged (Connected Communities)",
                "Regional / Rural",
                "Advantaged (Metropolitan)",
            ]
            cols = st.columns(len(tiers))
            for col, tier in zip(cols, tiers):
                count = tier_counts.get(tier, 0)
                rate = tier_rate.get(tier, 0)
                short = tier.split(" (")[0] if " (" in tier else tier
                col.metric(short, f"{count:,} incidents", f"{rate:.0f} per network")

            # Stacked bar: top categories by tier
            cat_matrix = overlay.get("tier_category_matrix", {})
            if cat_matrix:
                st.markdown("**Top Incident Categories by Socioeconomic Tier**")
                all_cats: set[str] = set()
                for cats in cat_matrix.values():
                    all_cats.update(cats.keys())
                rows = {}
                for tier in tiers:
                    if tier in cat_matrix:
                        rows[tier.split(" (")[0] if " (" in tier else tier] = {
                            cat: cat_matrix[tier].get(cat, 0) for cat in all_cats
                        }
                if rows:
                    chart_df = pd.DataFrame(rows).T.fillna(0).astype(int)
                    st.bar_chart(chart_df)

            # Year trend by tier
            tier_year = overlay.get("tier_year_series", {})
            if tier_year:
                st.markdown("**Incident Trend by Socioeconomic Tier**")
                trend_rows: dict[str, dict] = {}
                for tier, by_year in tier_year.items():
                    short = tier.split(" (")[0] if " (" in tier else tier
                    trend_rows[short] = by_year
                if trend_rows:
                    trend_df = (
                        pd.DataFrame(trend_rows).fillna(0).astype(int).sort_index()
                    )
                    st.line_chart(trend_df)

            # SEIFA reference footnote
            nsw_adv = reference.get("nsw_advantaged_lgas", [])
            if nsw_adv:
                st.caption(
                    f"SEIFA source: ABS Socio-Economic Indexes for Areas 2021. "
                    f"Top NSW advantaged LGAs (national top 10): {', '.join(nsw_adv)}. "
                    f"'Disadvantaged' tier uses NSW DoE Connected Communities directorate "
                    f"as a validated proxy — no NSW LGAs appear in the national "
                    f"top-10 most disadvantaged list."
                )

    # ── Right column ──────────────────────────────────────────────────────────
    with right:
        st.header("AI Insights")

        # Detect whether filters have changed since insights were last generated
        last_filter_key = st.session_state.get("insights_filter_key")
        insights_are_stale = (
            "insights" in st.session_state
            and last_filter_key is not None
            and last_filter_key != current_filter_key
        )

        if insights_are_stale:
            st.info(
                "⚠️ Filters have changed — click Regenerate Insights to update AI analysis."
            )

        if "insights" not in st.session_state:
            with st.spinner("Generating AI insights..."):
                st.session_state["insights"] = generate_insights(summary)
                st.session_state["insights_filter_key"] = current_filter_key

        insights: dict = st.session_state["insights"]

        st.subheader("Key Trends")
        for item in insights.get("key_trends", []):
            st.markdown(f"- {item}")

        st.subheader("Anomalies Identified")
        for item in insights.get("anomalies_identified", []):
            st.markdown(f"- {item}")

        st.subheader("Business Implications")
        for item in insights.get("business_implications", []):
            st.markdown(f"- {item}")

        st.subheader("Executive Summary")
        st.info(insights.get("executive_summary", "No summary available."))

        if st.button("🔄 Regenerate Insights"):
            with st.spinner("Regenerating AI insights..."):
                st.session_state["insights"] = generate_insights(summary)
                st.session_state["insights_filter_key"] = current_filter_key
            st.rerun()


if __name__ == "__main__":
    main()
