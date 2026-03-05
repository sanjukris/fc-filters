from __future__ import annotations

import logging
import os
from time import perf_counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.service import load_filter_options, rank_matches

logging.basicConfig(
    level=getattr(logging, os.getenv("FILTER_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Find Care Filter API", version="1.0.0")
allowed_origins_env = os.getenv(
    "FILTER_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ALL_OPTIONS = load_filter_options(DATA_DIR)
logger.info("Backend initialized with total_options=%s data_dir=%s", len(ALL_OPTIONS), DATA_DIR)
logger.info("CORS enabled for origins=%s", allowed_origins)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
def search_filters(q: str = Query(default="", description="Search text")) -> dict[str, Any]:
    started_at = perf_counter()
    logger.info("search request received query=%r", q)
    if not q.strip():
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info("search request empty query elapsed_ms=%.2f", elapsed_ms)
        return {"query": q, "results": []}

    matches = rank_matches(q, ALL_OPTIONS)
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("search request completed query=%r results=%s elapsed_ms=%.2f", q, len(matches), elapsed_ms)
    return {"query": q, "results": [match.to_dict() for match in matches]}
