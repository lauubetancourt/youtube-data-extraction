"""Typed composition models for pipeline run configuration."""

from .loading import load_run_config, run_config_from_mapping
from .models import (
    DetectionConfig,
    RunConfig,
    RunIdentityConfig,
    SignalsConfig,
    SimulationConfig,
)
from .paths import ResolvedRunConfig, resolve_run_config, resolve_run_config_paths
from .serialization import (
    canonical_run_config_json,
    run_config_hash,
    run_config_to_mapping,
)

__all__ = [
    "canonical_run_config_json",
    "DetectionConfig",
    "load_run_config",
    "ResolvedRunConfig",
    "resolve_run_config",
    "resolve_run_config_paths",
    "RunConfig",
    "run_config_hash",
    "RunIdentityConfig",
    "run_config_from_mapping",
    "run_config_to_mapping",
    "SignalsConfig",
    "SimulationConfig",
]
