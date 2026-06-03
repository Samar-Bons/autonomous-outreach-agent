# ABOUTME: Public surface of the copy stage: the template store and the deterministic generator.
# ABOUTME: Import these from here; the seed-JSON path stays an implementation detail.
from .generator import TemplateCopyGenerator
from .templates import DEFAULT_TEMPLATES_PATH, TemplateStore

__all__ = [
    "DEFAULT_TEMPLATES_PATH",
    "TemplateCopyGenerator",
    "TemplateStore",
]
