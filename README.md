# ViewTrend
AI-powered dashboard that analyses Australian public sector datasets, auto-detects anomalies, and generates plain-English insights.

## Setup

1. **Create a virtual environment (optional but recommended)**  
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   # .venv\Scripts\activate   # Windows (PowerShell / CMD)
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**  
   Copy `.env.example` to `.env` and edit as needed:

   ```bash
   cp .env.example .env
   ```

   - `CKAN_API_KEY` – Optional. For public datasets on `data.gov.au` you can leave this empty.

## Data source

On load, the app fetches **live Australian Government data** from the CKAN Data API:

- **Base URL**: `https://data.gov.au/data/`  
- **Resource ID**: `54587008-3c4e-4e8b-a045-4cc4d568ef93`

Data is retrieved via the `ckanapi` client with offset-based pagination so **all available records** are loaded into a Pandas DataFrame.  
If the API is unavailable, the app will automatically fall back to `data/dataset.csv` (if present).

## Running the app

From the project root:

```bash
streamlit run app.py
```

When the app starts:

- It fetches live data from the CKAN API (or falls back to `data/dataset.csv`).
- It computes summary statistics and runs a simple anomaly detection pipeline.
- It renders an interactive dashboard in your browser.

## Using the dashboard

- **🔄 Refresh Data button (sidebar)**: Clears the cached dataset and forces a fresh fetch from the API.
- **Last fetched timestamp (sidebar)**: Shows when data was last successfully loaded.
- **Raw data**: Explore the full dataset.
- **Summary statistics**: View descriptive stats for numeric columns, including missing-value metrics.
- **Detected anomalies**: See rows flagged as anomalous by a simple z-score based heuristic.
