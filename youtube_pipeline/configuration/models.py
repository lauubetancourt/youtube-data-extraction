from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from youtube_pipeline.cleaning import CleaningConfig
from youtube_pipeline.cyclic_daily_signals import CyclicDailySignalConfig
from youtube_pipeline.cyclic_detection_connector import CyclicDetectionConnectorConfig
from youtube_pipeline.cyclic_ingestion import CyclicIngestionConfig
from youtube_pipeline.cyclic_orchestration import CyclicOrchestratorConfig
from youtube_pipeline.cyclic_stateful_adapter import CyclicStatefulAdapterConfig
from youtube_pipeline.daily_frequency_baseline import DailyFrequencyBaselineConfig
from youtube_pipeline.daily_rag_context_selection import DailyContextSelectionConfig
from youtube_pipeline.daily_rag_consumer import DailyRagConsumerConfig
from youtube_pipeline.daily_rag_sidecars import DailyRagSidecarBuildConfig
from youtube_pipeline.data_extraction import ExtractionConfig
from youtube_pipeline.prepared_replay import PreparedDatasetConfig, ReplayConfig
from youtube_pipeline.storage import LocalFilesConfig


RUN_MODE_DEFAULT_TRACE_LEVEL = {
    "development": "minimal",
    "reference": "standard",
    "official": "full",
}
TRACE_LEVEL_ORDER = {
    "minimal": 0,
    "standard": 1,
    "full": 2,
}


def _require_optional_instance(
    field_name: str,
    value: Any,
    expected_type: type,
) -> None:
    if value is not None and not isinstance(value, expected_type):
        raise TypeError(
            f"{field_name} must be {expected_type.__name__} or None, "
            f"not {type(value).__name__}."
        )


@dataclass(frozen=True, slots=True)
class RunIdentityConfig:
    """Stable identity supplied by the caller for one configured execution."""

    run_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str):
            raise TypeError("run_id must be a string.")
        if not self.run_id.strip():
            raise ValueError("run_id must not be empty.")


@dataclass(frozen=True, slots=True)
class ArtifactsConfig:
    """Execution-level traceability policy without component artifact details."""

    run_mode: str = "development"
    trace_level: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.run_mode, str):
            raise TypeError("run_mode must be a string.")
        if self.run_mode not in RUN_MODE_DEFAULT_TRACE_LEVEL:
            supported = ", ".join(RUN_MODE_DEFAULT_TRACE_LEVEL)
            raise ValueError(
                f"Unsupported run_mode {self.run_mode!r}; expected one of: "
                f"{supported}."
            )
        level = self.trace_level
        if level is None:
            level = RUN_MODE_DEFAULT_TRACE_LEVEL[self.run_mode]
            object.__setattr__(self, "trace_level", level)
        if not isinstance(level, str):
            raise TypeError("trace_level must be a string or None.")
        if level not in TRACE_LEVEL_ORDER:
            supported = ", ".join(TRACE_LEVEL_ORDER)
            raise ValueError(
                f"Unsupported trace_level {level!r}; expected one of: {supported}."
            )
        minimum = RUN_MODE_DEFAULT_TRACE_LEVEL[self.run_mode]
        if TRACE_LEVEL_ORDER[level] < TRACE_LEVEL_ORDER[minimum]:
            raise ValueError(
                f"run_mode={self.run_mode!r} requires trace_level "
                f"{minimum!r} or higher."
            )


@dataclass(frozen=True, slots=True)
class DataConfig:
    """Composition of implemented data-source configurations."""

    youtube_api: ExtractionConfig | None = None
    local_files: LocalFilesConfig | None = None
    prepared_dataset: PreparedDatasetConfig | None = None
    cleaning: CleaningConfig | None = None

    def __post_init__(self) -> None:
        _require_optional_instance("youtube_api", self.youtube_api, ExtractionConfig)
        _require_optional_instance("local_files", self.local_files, LocalFilesConfig)
        _require_optional_instance(
            "prepared_dataset",
            self.prepared_dataset,
            PreparedDatasetConfig,
        )
        _require_optional_instance("cleaning", self.cleaning, CleaningConfig)
        configured_sources = sum(
            source is not None
            for source in (
                self.youtube_api,
                self.local_files,
                self.prepared_dataset,
            )
        )
        if configured_sources > 1:
            raise ValueError("DataConfig must configure exactly one data source.")
        if configured_sources == 0 and self.cleaning is None:
            raise ValueError(
                "DataConfig must configure exactly one data source or at least "
                "one preparation stage."
            )


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Composition of the existing cyclic simulation stage configurations."""

    ingestion: CyclicIngestionConfig | None = None
    orchestration: CyclicOrchestratorConfig | None = None
    stateful_adapter: CyclicStatefulAdapterConfig | None = None
    replay: ReplayConfig | None = None

    def __post_init__(self) -> None:
        _require_optional_instance("ingestion", self.ingestion, CyclicIngestionConfig)
        _require_optional_instance(
            "orchestration",
            self.orchestration,
            CyclicOrchestratorConfig,
        )
        _require_optional_instance(
            "stateful_adapter",
            self.stateful_adapter,
            CyclicStatefulAdapterConfig,
        )
        _require_optional_instance("replay", self.replay, ReplayConfig)
        if all(
            config is None
            for config in (
                self.ingestion,
                self.orchestration,
                self.stateful_adapter,
                self.replay,
            )
        ):
            raise ValueError("SimulationConfig must configure at least one stage.")


@dataclass(frozen=True, slots=True)
class SignalsConfig:
    """Composition of implemented signal configurations."""

    daily: CyclicDailySignalConfig | None = None

    def __post_init__(self) -> None:
        _require_optional_instance("daily", self.daily, CyclicDailySignalConfig)
        if self.daily is None:
            raise ValueError("SignalsConfig must configure at least one signal stage.")


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    """Composition of implemented detector configurations."""

    connector: CyclicDetectionConnectorConfig | None = None
    daily_frequency: DailyFrequencyBaselineConfig | None = None

    def __post_init__(self) -> None:
        _require_optional_instance(
            "connector",
            self.connector,
            CyclicDetectionConnectorConfig,
        )
        _require_optional_instance(
            "daily_frequency",
            self.daily_frequency,
            DailyFrequencyBaselineConfig,
        )
        if self.connector is None and self.daily_frequency is None:
            raise ValueError("DetectionConfig must configure at least one detector.")


@dataclass(frozen=True, slots=True)
class RagConfig:
    """Composition of implemented RAG-stage configurations."""

    daily_sidecars: DailyRagSidecarBuildConfig | None = None
    daily_consumer: DailyRagConsumerConfig | None = None
    daily_context_selection: DailyContextSelectionConfig | None = None

    def __post_init__(self) -> None:
        _require_optional_instance(
            "daily_sidecars",
            self.daily_sidecars,
            DailyRagSidecarBuildConfig,
        )
        _require_optional_instance(
            "daily_consumer",
            self.daily_consumer,
            DailyRagConsumerConfig,
        )
        _require_optional_instance(
            "daily_context_selection",
            self.daily_context_selection,
            DailyContextSelectionConfig,
        )
        if all(
            config is None
            for config in (
                self.daily_sidecars,
                self.daily_consumer,
                self.daily_context_selection,
            )
        ):
            raise ValueError("RagConfig must configure at least one RAG stage.")


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Typed composition root for one execution without duplicating component fields."""

    identity: RunIdentityConfig
    data: DataConfig | None = None
    simulation: SimulationConfig | None = None
    signals: SignalsConfig | None = None
    detection: DetectionConfig | None = None
    rag: RagConfig | None = None
    artifacts: ArtifactsConfig | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RunIdentityConfig):
            raise TypeError("identity must be RunIdentityConfig.")
        _require_optional_instance("data", self.data, DataConfig)
        _require_optional_instance("simulation", self.simulation, SimulationConfig)
        _require_optional_instance("signals", self.signals, SignalsConfig)
        _require_optional_instance("detection", self.detection, DetectionConfig)
        _require_optional_instance("rag", self.rag, RagConfig)
        _require_optional_instance("artifacts", self.artifacts, ArtifactsConfig)
        if all(
            section is None
            for section in (
                self.data,
                self.simulation,
                self.signals,
                self.detection,
                self.rag,
            )
        ):
            raise ValueError("RunConfig must configure at least one execution section.")
