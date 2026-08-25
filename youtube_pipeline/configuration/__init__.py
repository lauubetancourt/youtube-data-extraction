"""Typed composition models for pipeline run configuration."""

from youtube_pipeline.activity_detection import (
    ActivityDetectionRouteConfig,
    DetectionResult,
)
from youtube_pipeline.detectors import XiaoEMAConfig

from .loading import load_run_config, run_config_from_mapping
from .models import (
    ArtifactsConfig,
    DataConfig,
    DetectionConfig,
    RagConfig,
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
    "ActivityDetectionRouteConfig",
    "ArtifactsConfig",
    "canonical_run_config_json",
    "DataConfig",
    "DetectionConfig",
    "DetectionResult",
    "load_run_config",
    "RagConfig",
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
    "XiaoEMAConfig",
]
