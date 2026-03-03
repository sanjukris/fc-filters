from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from rapidfuzz import fuzz

STOP_WORDS = {
    "the",
    "and",
    "or",
    "but",
    "in",
    "looking",
    "for",
    "on",
    "at",
    "to",
    "of",
    "with",
    "by",
}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
DATA_DIR = Path(__file__).resolve().parent / "data"
MIN_SCORE = 60.0
MIN_TOKEN_COVERAGE = 0.34


@dataclass(frozen=True)
class FilterOption:
    value: str
    source: str
    normalized: str

    @property
    def display(self) -> str:
        return f"{self.value} - {self.source}"


def normalize_text(text: str) -> str:
    tokens = TOKEN_PATTERN.findall(text.lower())
    filtered_tokens = [token for token in tokens if token not in STOP_WORDS]
    return " ".join(filtered_tokens)


@st.cache_data(show_spinner=False)
def load_filter_options(data_dir: str) -> list[FilterOption]:
    options: list[FilterOption] = []
    for csv_path in sorted(Path(data_dir).glob("*.csv")):
        source = csv_path.stem
        with csv_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if not row:
                    continue
                value = row[0].strip()
                if not value:
                    continue
                options.append(
                    FilterOption(
                        value=value,
                        source=source,
                        normalized=normalize_text(value),
                    )
                )
    return options


def token_coverage_score(query_tokens: list[str], candidate_tokens: list[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0

    hits = 0
    for query_token in query_tokens:
        best_match = max((fuzz.ratio(query_token, token) for token in candidate_tokens), default=0)
        if best_match >= 80:
            hits += 1
    return hits / len(query_tokens)


def rank_matches(query: str, options: list[FilterOption]) -> list[FilterOption]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    query_tokens = normalized_query.split()
    query_numbers = {token for token in query_tokens if token.isdigit()}
    scored: list[tuple[float, FilterOption]] = []
    for option in options:
        if not option.normalized:
            continue

        candidate_tokens = option.normalized.split()
        candidate_numbers = {token for token in candidate_tokens if token.isdigit()}
        token_coverage = token_coverage_score(query_tokens, candidate_tokens)

        if len(query_tokens) > 1 and token_coverage < MIN_TOKEN_COVERAGE:
            continue

        weighted_score = (
            0.45 * fuzz.ratio(normalized_query, option.normalized)
            + 0.35 * fuzz.token_sort_ratio(normalized_query, option.normalized)
            + 0.20 * fuzz.token_set_ratio(normalized_query, option.normalized)
            + (35 * token_coverage)
        )

        if query_numbers and not query_numbers.issubset(candidate_numbers):
            weighted_score -= 25

        if weighted_score >= MIN_SCORE:
            scored.append((weighted_score, option))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [option for _, option in scored]


def main() -> None:
    st.set_page_config(page_title="Find Care Filters")
    st.title("Find Care Filter Search")
    st.caption("Type to find matching preconfigured filters across all source files.")

    all_options = load_filter_options(str(DATA_DIR))
    query = st.text_input("Search filters", placeholder="e.g. looking for knee doctor with handicap acess")
    st.markdown("**Suggestions**")

    if not query.strip():
        st.info("Start typing to see matches.")
        return

    matches = rank_matches(query, all_options)
    if not matches:
        st.info("No matching options found.")
        return

    selected = st.radio(
        "Matching options",
        options=[match.display for match in matches],
        index=None,
        label_visibility="collapsed",
    )
    if selected:
        st.caption(f"Selected: {selected}")


if __name__ == "__main__":
    main()
