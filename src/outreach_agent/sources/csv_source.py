# ABOUTME: A DataSource that loads prospects from a CSV file into typed Prospect models.
# ABOUTME: Stands in for the real multi-source acquisition layer in this reference build.
from __future__ import annotations

import csv
from pathlib import Path

from ..domain import Prospect


def _opt(value: str) -> str | None:
    value = value.strip()
    return value or None


def _opt_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def _opt_float(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


class CsvDataSource:
    """Loads prospects from a CSV with one row per business.

    Expected columns: id, name, city, state, sic, website, email, phone,
    employees, rating, review_count, source. Blank cells become None.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[Prospect]:
        prospects: list[Prospect] = []
        with self._path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                prospects.append(
                    Prospect(
                        id=row["id"].strip(),
                        name=row["name"].strip(),
                        city=row["city"].strip(),
                        state=_opt(row.get("state", "")) or "TX",
                        sic=_opt(row.get("sic", "")),
                        website=_opt(row.get("website", "")),
                        email=_opt(row.get("email", "")),
                        phone=_opt(row.get("phone", "")),
                        employees=_opt_int(row.get("employees", "")),
                        rating=_opt_float(row.get("rating", "")),
                        review_count=_opt_int(row.get("review_count", "")),
                        source=_opt(row.get("source", "")) or "seed",
                    )
                )
        return prospects
