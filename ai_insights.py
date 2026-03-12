from __future__ import annotations

import json
import os

from groq import Groq, AuthenticationError, APIError
from dotenv import load_dotenv

load_dotenv()

_SYSTEM_PROMPT = (
    "You are a senior data analyst specialising in Australian public sector and education policy. "
    "Given structured summary statistics from NSW Government school incident reports, "
    "generate insights for a Deloitte consulting audience."
)

_MODEL = "llama-3.3-70b-versatile"

_FALLBACK: dict = {
    "key_trends": ["Unable to generate insights — API error."],
    "anomalies_identified": ["API error occurred."],
    "business_implications": ["Please check your GROQ_API_KEY and try again."],
    "executive_summary": (
        "AI insight generation failed. Please verify your GROQ_API_KEY "
        "in the .env file and your network connection."
    ),
}


def _get_api_key() -> str:
    """Return GROQ_API_KEY from Streamlit secrets (Cloud) or .env (local)."""
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "").strip()


def generate_insights(summary: dict) -> dict:
    """
    Take the dict returned by process_data(), call the Groq API, and
    return a dict with keys: key_trends, anomalies_identified,
    business_implications, executive_summary.
    """
    api_key = _get_api_key()
    if not api_key:
        result = dict(_FALLBACK)
        result["executive_summary"] = (
            "GROQ_API_KEY is not set. Add it to your .env file (local) "
            "or Streamlit Cloud Secrets (deployed)."
        )
        return result

    client = Groq(api_key=api_key)

    overlay = summary.get("lga_overlay", {})
    overlay_section = ""
    if overlay:
        overlay_section = (
            f"lga_overlay_tier_counts: {json.dumps(overlay.get('tier_counts', {}))}\n"
            f"lga_overlay_incidents_per_network: {json.dumps(overlay.get('tier_incident_rate', {}))}\n"
            f"lga_overlay_top_categories_by_tier: {json.dumps(overlay.get('tier_category_matrix', {}))}\n"
            f"lga_overlay_key_finding: {json.dumps(overlay.get('key_finding', ''))}\n"
            "Note: 'Disadvantaged (Connected Communities)' = NSW DoE schools in the most "
            "remote/socioeconomically disadvantaged communities (SEIFA proxy). "
            "'Advantaged (Metropolitan)' = schools in metropolitan areas encompassing "
            "the top NSW SEIFA LGAs (Woollahra, Mosman, Ku-ring-gai, North Sydney, "
            "Waverley, Lane Cove). Please incorporate the socioeconomic equity angle "
            "prominently in your insights.\n"
        )

    user_message = (
        "Below are summary statistics from NSW Government school incident reports "
        "(2020–2023). Return ONLY valid JSON — no markdown, no preamble — in exactly "
        "this shape:\n"
        "{\n"
        '  "key_trends": ["...", "...", "..."],\n'
        '  "anomalies_identified": ["...", "..."],\n'
        '  "business_implications": ["...", "..."],\n'
        '  "executive_summary": "2-3 sentence summary written for a government client"\n'
        "}\n\n"
        f"incidents_by_year: {json.dumps(summary.get('incidents_by_year', {}))}\n"
        f"incidents_by_category: {json.dumps(summary.get('incidents_by_category', {}))}\n"
        f"incidents_by_group: {json.dumps(summary.get('incidents_by_group', {}))}\n"
        f"priority_distribution: {json.dumps(summary.get('priority_distribution', {}))}\n"
        f"anomalies: {json.dumps(summary.get('anomalies', []))}\n"
        f"sample_summaries: {json.dumps(summary.get('sample_summaries', []))}\n"
        + overlay_section
    )

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if the model wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return json.loads(raw)

    except json.JSONDecodeError as exc:
        result = dict(_FALLBACK)
        result["executive_summary"] = f"Model returned non-JSON output: {exc}"
        return result
    except AuthenticationError:
        result = dict(_FALLBACK)
        result["executive_summary"] = (
            "Authentication failed. Check that GROQ_API_KEY is correct."
        )
        return result
    except APIError as exc:
        result = dict(_FALLBACK)
        result["executive_summary"] = f"Groq API error: {exc}"
        return result
