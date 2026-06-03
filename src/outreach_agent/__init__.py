# ABOUTME: Top-level package for the autonomous outreach agent.
# ABOUTME: Re-exports the config entry point; domain and protocols are imported from submodules.
from .config import Config, load_config

__all__ = ["Config", "load_config"]
__version__ = "0.1.0"
