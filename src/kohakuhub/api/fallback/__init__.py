"""Fallback system for external repository sources (HuggingFace, other KohakuHub instances).

This module provides:
- Fallback to external sources when repositories/files not found locally
- Aggregation of repository lists from multiple sources
- Caching of repo→source mappings
- URL mapping for HuggingFace asymmetric API structure
"""

from kohakuhub.api.fallback.decorators import (
    with_list_aggregation,
    with_repo_fallback,
)

__all__ = [
    "with_repo_fallback",
    "with_list_aggregation",
]
