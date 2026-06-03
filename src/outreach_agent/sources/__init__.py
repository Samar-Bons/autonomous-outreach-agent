# ABOUTME: Public surface of the sources layer: the CSV-backed data source.
# ABOUTME: Real acquisition (firmographic DB, maps API, registries) would implement DataSource too.
from ..paths import SEED_DIR
from .csv_source import CsvDataSource

DEFAULT_SEED_PATH = SEED_DIR / "prospects.csv"

__all__ = ["DEFAULT_SEED_PATH", "CsvDataSource"]
