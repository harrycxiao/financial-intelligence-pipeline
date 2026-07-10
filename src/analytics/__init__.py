# src/analytics/__init__.py

"""
Public interface for the quantitative analytics package.

The high-level research-engine interface is loaded lazily so importing a
lower-level analytics module does not eagerly initialize the full analytics
dependency graph.
"""

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from src.analytics.research_engine import (
        ResearchEngineConfig,
        run_research_engine,
    )


__all__ = [
    "ResearchEngineConfig",
    "run_research_engine",
]


def __getattr__(name: str) -> Any:
    """Lazily load public research-engine objects on first access."""

    if name == "ResearchEngineConfig":
        from src.analytics.research_engine import ResearchEngineConfig

        return ResearchEngineConfig

    if name == "run_research_engine":
        from src.analytics.research_engine import run_research_engine

        return run_research_engine

    raise AttributeError(
        f"Module {__name__!r} has no attribute {name!r}."
    )


def __dir__() -> list[str]:
    """Expose lazy public names to introspection tools."""

    return sorted(set(globals()) | set(__all__))