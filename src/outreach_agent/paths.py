# ABOUTME: Centralizes filesystem anchors so repo-relative path math lives in one place.
# ABOUTME: Avoids fragile parents[N] arithmetic duplicated across packages.
from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
SEED_DIR = REPO_ROOT / "data" / "seed"
