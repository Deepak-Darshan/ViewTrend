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


def main() -> None:
    with st.spinner("Loading data..."):
        df = load_data()

    summary = process_data(df)
    years = list(summary["incidents_by_year"].keys())

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("ViewTrend")
        st.metric("Total rows loaded", summary["total_incidents"])
        if years:
            st.metric("Year range", f"{min(years)} – {max(years)}")
        st.metric("Last refreshed", dt.datetime.now().strftime("%Y-%m-%d %H:%M"))

        with st.expander("📊 About this data"):
            st.markdown(
                "This dashboard analyses NSW Government school incident reports "
                "published as open data. The dataset covers biannual incident "
                "summaries from 2020 to 2023, including incident categories, "
                "priority ratings, operational directorates, and principal "
                "networks across public schools in New South Wales."
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
                # Build a DataFrame: rows = tiers, columns = union of top categories
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
                    trend_df = pd.DataFrame(trend_rows).fillna(0).astype(int).sort_index()
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

        if "insights" not in st.session_state:
            with st.spinner("Generating AI insights..."):
                st.session_state["insights"] = generate_insights(summary)

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
            st.rerun()


if __name__ == "__main__":
    main()
