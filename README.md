# ViewTrend
AI-powered dashboard that analyses NSW Government school incident reports, auto-detects anomalies, and generates plain-English insights for a consulting audience.

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

   | Variable | Required | Description |
   |---|---|---|
   | `GROQ_API_KEY` | Yes | API key for Groq — used to generate AI insights via `llama-3.3-70b-versatile`. Get one at [console.groq.com](https://console.groq.com). |
   | `CKAN_API_KEY` | No | Optional. For public datasets on `data.gov.au` you can leave this empty. |

   > **Streamlit Cloud**: Add these as secrets in your app's settings instead of using a `.env` file.

## Data source

On load, the app fetches **live NSW Government school incident data** from the CKAN Data API:

- **Base URL**: `https://data.gov.au/data/`
- **Resource ID**: `54587008-3c4e-4e8b-a045-4cc4d568ef93`

Data covers biannual incident summaries from **2020 to 2023**, including incident categories, priority ratings, operational directorates, and principal networks across public schools in New South Wales.

Data is retrieved via the `ckanapi` client with offset-based pagination so **all available records** are loaded into a Pandas DataFrame. If the API is unavailable, the app automatically falls back to any incident CSV files in the `data/` directory (files with `advantaged` or `LGA` in their name are excluded as they are socioeconomic reference files).

## Running the app

```bash
streamlit run app.py
```

## Dashboard

The dashboard is split into two columns:

**Left — Data visualisations**
- **Incidents by Year** — line chart of total incident counts per year
- **Top 8 Primary Categories** — bar chart of the most common incident types
- **Detected Anomalies** — table of rows flagged by a z-score based heuristic

**Right — AI Insights** (powered by Groq)
- **Key Trends** — notable patterns identified in the data
- **Anomalies Identified** — statistically or contextually unusual findings
- **Business Implications** — policy and operational recommendations
- **Executive Summary** — 2–3 sentence summary written for a government client
- **🔄 Regenerate Insights button** — re-runs the AI analysis on demand

**Sidebar**
- Total rows loaded, year range, and last refreshed timestamp
- "About this data" expander with dataset context
