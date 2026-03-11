import datetime as dt

import pandas as pd
import streamlit as st

from data_fetcher import fetch_data, DataFetchError
from pipeline import run_pipeline


st.set_page_config(
    page_title="ViewTrend – Australian Public Sector Insights",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_data_cached() -> pd.DataFrame:
    """Cached wrapper around the CKAN/CSV data fetcher."""
    return fetch_data()


def main() -> None:
    st.title("ViewTrend")
    st.caption(
        "AI-powered dashboard that analyses Australian public sector datasets, "
        "auto-detects anomalies, and generates plain-English insights."
    )

    # Sidebar controls
    with st.sidebar:
        st.header("Data controls")

        # Last fetched timestamp stored in session state for display
        last_fetched = st.session_state.get("last_fetched")
        if last_fetched is not None:
            st.markdown(f"**Last fetched:** {last_fetched}")
        else:
            st.markdown("**Last fetched:** Not yet fetched")

        refresh = st.button("🔄 Refresh Data")
        if refresh:
            # Clear the cache so next load pulls fresh data from the API
            load_data_cached.clear()
            st.session_state["last_fetched"] = dt.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            st.experimental_rerun()

    # Main content
    try:
        with st.spinner("Fetching latest data from data.gov.au..."):
            df = load_data_cached()
            if "last_fetched" not in st.session_state:
                st.session_state["last_fetched"] = dt.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
    except DataFetchError as exc:
        st.error(
            "Unable to load data.\n\n"
            f"**Details:** {exc}\n\n"
            "Please check your network connection or provide a fallback CSV at "
            "`data/dataset.csv`."
        )
        return

    if df.empty:
        st.warning("The dataset is empty. Please check the source data.")
        return

    summary_stats, anomalies = run_pipeline(df)

    st.subheader("Raw data")
    st.dataframe(df, use_container_width=True)

    st.subheader("Summary statistics")
    if not summary_stats.empty:
        st.dataframe(summary_stats, use_container_width=True)
    else:
        st.info("No numeric columns available for summary statistics.")

    st.subheader("Detected anomalies")
    if not anomalies.empty and anomalies["is_anomaly"].any():
        st.dataframe(
            anomalies[anomalies["is_anomaly"]],
            use_container_width=True,
        )
    else:
        st.info(
            "No anomalies detected using the current heuristic "
            "(z-score based, configurable in `pipeline.py`)."
        )


if __name__ == "__main__":
    main()

