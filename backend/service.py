from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

STOP_WORDS = {
    "the",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
MIN_SCORE = 60.0
MIN_TOKEN_COVERAGE = 0.34
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilterOption:
    value: str
    source: str
    normalized: str

    def to_dict(self) -> dict[str, str]:
        return {
            "value": self.value,
            "source": self.source,
            "display": f"{self.value} - {self.source}",
        }


@dataclass(frozen=True)
class MatchResult:
    option: FilterOption
    final_score: float
    token_coverage: float
    ratio_score: float
    token_sort_score: float
    token_set_score: float
    coverage_boost: float
    number_penalty: float

    def to_dict(self) -> dict[str, str | float]:
        return {
            "value": self.option.value,
            "source": self.option.source,
            "display": f"{self.option.value} - {self.option.source}",
            "final_score": round(self.final_score, 2),
            "token_coverage": round(self.token_coverage, 2),
            "ratio_score": round(self.ratio_score, 2),
            "token_sort_score": round(self.token_sort_score, 2),
            "token_set_score": round(self.token_set_score, 2),
            "coverage_boost": round(self.coverage_boost, 2),
            "number_penalty": round(self.number_penalty, 2),
        }


def normalize_text(text: str) -> str:
    tokens = TOKEN_PATTERN.findall(text.lower())
    filtered_tokens = [token for token in tokens if token not in STOP_WORDS]
    normalized = " ".join(filtered_tokens)
    logger.debug("normalize_text input=%r tokens=%s normalized=%r", text, tokens, normalized)
    return normalized


def load_filter_options(data_dir: Path) -> list[FilterOption]:
    logger.info("Loading filter options from data_dir=%s", data_dir)
    options: list[FilterOption] = []
    for csv_path in sorted(data_dir.glob("*.csv")):
        source = csv_path.stem
        file_count = 0
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
                file_count += 1
        logger.info("Loaded %s options from %s", file_count, csv_path.name)
    logger.info("Completed loading options. total_options=%s", len(options))
    return options


def token_coverage_score(query_tokens: list[str], candidate_tokens: list[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0

    hits = 0
    for query_token in query_tokens:
        best_match = max((fuzz.ratio(query_token, token) for token in candidate_tokens), default=0)
        if best_match >= 80:
            # print(f"query_tokens best_match {best_match} - {query_tokens} - candidate_tokens {candidate_tokens}")
            hits += 1
    return hits / len(query_tokens)


def rank_matches(query: str, options: list[FilterOption]) -> list[MatchResult]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        logger.info("rank_matches empty_query query=%r", query)
        return []

    query_tokens = normalized_query.split()
    query_numbers = {token for token in query_tokens if token.isdigit()}
    scored: list[MatchResult] = []
    skipped_low_coverage = 0
    skipped_low_score = 0
    number_penalties = 0
    logger.info(
        "rank_matches start query=%r normalized_query=%r query_tokens=%s options_count=%s",
        query,
        normalized_query,
        query_tokens,
        len(options),
    )

    for option in options:
        if not option.normalized:
            continue

        candidate_tokens = option.normalized.split()
        candidate_numbers = {token for token in candidate_tokens if token.isdigit()}
        token_coverage = token_coverage_score(query_tokens, candidate_tokens)

        if len(query_tokens) > 1 and token_coverage < MIN_TOKEN_COVERAGE:
            skipped_low_coverage += 1
            continue

        ratio_score = fuzz.ratio(normalized_query, option.normalized)
        token_sort_score = fuzz.token_sort_ratio(normalized_query, option.normalized)
        token_set_score = fuzz.token_set_ratio(normalized_query, option.normalized)
        coverage_boost = 35 * token_coverage
        number_penalty = 0.0
        weighted_score = (
            0.45 * ratio_score
            + 0.35 * token_sort_score
            + 0.20 * token_set_score
            + coverage_boost
        )

        if query_numbers and not query_numbers.issubset(candidate_numbers):
            weighted_score -= 25
            number_penalty = -25.0
            number_penalties += 1

        if weighted_score >= MIN_SCORE:
            scored.append(
                MatchResult(
                    option=option,
                    final_score=weighted_score,
                    token_coverage=token_coverage,
                    ratio_score=ratio_score,
                    token_sort_score=token_sort_score,
                    token_set_score=token_set_score,
                    coverage_boost=coverage_boost,
                    number_penalty=number_penalty,
                )
            )
            logger.debug(
                "rank_matches accept option=%r source=%s score=%.2f coverage=%.2f",
                option.value,
                option.source,
                weighted_score,
                token_coverage,
            )
        else:
            skipped_low_score += 1

    scored.sort(key=lambda item: item.final_score, reverse=True)
    top_displays = [match.to_dict()["display"] for match in scored[:5]]
    logger.info(
        "rank_matches done query=%r matches=%s skipped_low_coverage=%s skipped_low_score=%s "
        "number_penalties=%s top5=%s",
        query,
        len(scored),
        skipped_low_coverage,
        skipped_low_score,
        number_penalties,
        top_displays,
    )
    return scored
