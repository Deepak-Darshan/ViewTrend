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
