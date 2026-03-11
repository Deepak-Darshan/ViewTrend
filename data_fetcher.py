import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd
from ckanapi import RemoteCKAN, CKANAPIError
from dotenv import load_dotenv


class DataFetchError(Exception):
    """Raised when both the API fetch and local CSV fallback fail."""


BASE_URL = "https://data.gov.au/data/"
RESOURCE_ID = "54587008-3c4e-4e8b-a045-4cc4d568ef93"


def _get_ckan_client() -> RemoteCKAN:
    """Initialise and return a CKAN client, using API key if provided."""
    load_dotenv(override=False)
    api_key = os.getenv("CKAN_API_KEY", "").strip() or None
    return RemoteCKAN(BASE_URL.rstrip("/"), apikey=api_key)


def _fetch_all_records(limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetch all records from the CKAN datastore for a given resource ID.

    Uses offset-based pagination until no more records are returned.
    """
    client = _get_ckan_client()
    all_records: List[Dict[str, Any]] = []
    offset = 0

    while True:
        try:
            response = client.action.datastore_search(
                resource_id=RESOURCE_ID,
                limit=limit,
                offset=offset,
            )
        except CKANAPIError as exc:
            raise DataFetchError(f"Error fetching data from CKAN API: {exc}") from exc

        records = response.get("records", [])
        if not records:
            break

        all_records.extend(records)
        offset += len(records)

        # Safety guard against a potential infinite loop if API behaves unexpectedly
        if len(records) < limit:
            break

    return all_records


def _load_fallback_csv() -> pd.DataFrame:
    """
    Load a fallback CSV from data/dataset.csv if it exists.

    Raises DataFetchError if the file does not exist or cannot be read.
    """
    project_root = Path(__file__).resolve().parent
    csv_path = project_root / "data" / "dataset.csv"

    if not csv_path.exists():
        raise DataFetchError(
            "Unable to fetch data from the CKAN API and no fallback CSV found at "
            f"'{csv_path}'. Please ensure network access to data.gov.au or provide "
            "a local CSV at data/dataset.csv."
        )

    try:
        return pd.read_csv(csv_path)
    except Exception as exc:
        raise DataFetchError(
            f"Failed to read fallback CSV at '{csv_path}': {exc}"
        ) from exc


def fetch_data() -> pd.DataFrame:
    """
    Fetch data as a Pandas DataFrame.

    - Tries CKAN Data API first (using pagination).
    - On any API-related error, falls back to data/dataset.csv if available.
    - Raises DataFetchError with a clear message if both strategies fail.
    """
    try:
        records = _fetch_all_records()
        if not records:
            # If API returns successfully but with no records, treat as error and try fallback.
            raise DataFetchError(
                "CKAN API returned no records for the configured resource. "
                "Falling back to local CSV if available."
            )
        return pd.DataFrame.from_records(records)
    except DataFetchError:
        # Already a well-formed error; try CSV, and if that also fails, re-raise.
        try:
            return _load_fallback_csv()
        except DataFetchError:
            # If CSV loading also failed, propagate the original API-related error.
            raise
    except Exception as exc:
        # Unexpected error type from CKAN or networking; attempt CSV, otherwise raise.
        try:
            return _load_fallback_csv()
        except DataFetchError as csv_err:
            raise DataFetchError(
                f"Unexpected error while fetching from CKAN API: {exc}. "
                f"Additionally, fallback CSV could not be loaded: {csv_err}"
            ) from exc

