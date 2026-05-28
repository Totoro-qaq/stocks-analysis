from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs"

UNIVERSE_HOLDINGS_CSV = RAW_DATA_DIR / "universe_holdings.csv"
BENCHMARK_METADATA_CSV = RAW_DATA_DIR / "benchmark_metadata.csv"
DAILY_PRICES_CSV = RAW_DATA_DIR / "daily_prices.csv"
DATA_FETCH_FAILURES_CSV = RAW_DATA_DIR / "data_fetch_failures.csv"
ANALYSIS_UNIVERSE_50_CSV = PROCESSED_DATA_DIR / "analysis_universe_50.csv"
HUMAN_OVERRIDES_CSV = CONFIG_DIR / "human_overrides.csv"
ENV_FILE = CONFIG_DIR / ".env"
ENV_EXAMPLE = CONFIG_DIR / ".env.example"


def ensure_project_dirs() -> None:
    for path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, CONFIG_DIR, DOCS_DIR, OUTPUT_DIR]:
        path.mkdir(parents=True, exist_ok=True)
