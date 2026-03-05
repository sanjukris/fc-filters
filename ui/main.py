from __future__ import annotations

import logging
import os
from time import perf_counter

import requests
import streamlit as st

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv("FILTER_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
logging.basicConfig(
    level=getattr(logging, os.getenv("FILTER_UI_LOG_LEVEL", os.getenv("FILTER_LOG_LEVEL", "INFO")).upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_matches(query: str) -> list[dict[str, str | float]]:
    if not query.strip():
        logger.info("UI fetch skipped for empty query")
        return []

    started_at = perf_counter()
    logger.info("UI fetch start query=%r backend=%s", query, API_BASE_URL)
    response = requests.get(
        f"{API_BASE_URL}/search",
        params={"q": query},
        timeout=3,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("UI fetch done query=%r results=%s elapsed_ms=%.2f", query, len(results), elapsed_ms)
    return results


def main() -> None:
    st.set_page_config(page_title="Find Care Filters")
    st.title("Find Care Filter Search")
    st.caption("Type to find matching preconfigured filters across all source files.")

    query = st.text_input("Search filters", placeholder="e.g. looking for knee doctor with handicap acess")
    st.markdown("**Suggestions**")

    if not query.strip():
        logger.info("UI idle state: waiting for input")
        st.info("Start typing to see matches.")
        return

    try:
        matches = fetch_matches(query)
    except requests.RequestException as exc:
        logger.exception("UI fetch failed query=%r error=%s", query, exc)
        st.error(
            f"Could not reach backend at {API_BASE_URL}. "
            "Start FastAPI first or set FILTER_API_BASE_URL."
        )
        return

    if not matches:
        logger.info("UI no matches query=%r", query)
        st.info("No matching options found.")
        return

    logger.info("UI rendering matches query=%r count=%s", query, len(matches))
    table_rows: list[dict[str, str | float | int]] = []
    for idx, match in enumerate(matches, start=1):
        table_rows.append(
            {
                "rank": idx,
                "match": match["display"],
                "final_score": match.get("final_score", 0.0),
                "ratio_score": match.get("ratio_score", 0.0),
                "token_sort_score": match.get("token_sort_score", 0.0),
                "token_set_score": match.get("token_set_score", 0.0),
                "token_coverage": match.get("token_coverage", 0.0),
                "coverage_boost": match.get("coverage_boost", 0.0),
                "number_penalty": match.get("number_penalty", 0.0),
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    selected = st.radio(
        "Matching options",
        options=[match["display"] for match in matches],
        index=None,
        label_visibility="collapsed",
    )
    if selected:
        logger.info("UI selected option=%r", selected)
        st.caption(f"Selected: {selected}")


if __name__ == "__main__":
    main()
