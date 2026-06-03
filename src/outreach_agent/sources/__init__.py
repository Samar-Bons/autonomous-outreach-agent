# ABOUTME: Public surface of the sources layer: the CSV-backed data source.
# ABOUTME: Real acquisition (firmographic DB, maps API, registries) would implement DataSource too.
from pathlib import Path

from .csv_source import CsvDataSource

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[3] / "data" / "seed" / "prospects.csv"

__all__ = ["DEFAULT_SEED_PATH", "CsvDataSource"]
