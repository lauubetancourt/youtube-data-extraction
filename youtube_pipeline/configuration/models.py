from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from youtube_pipeline.cyclic_daily_signals import CyclicDailySignalConfig
from youtube_pipeline.cyclic_detection_connector import CyclicDetectionConnectorConfig
from youtube_pipeline.cyclic_ingestion import CyclicIngestionConfig
from youtube_pipeline.cyclic_orchestration import CyclicOrchestratorConfig
from youtube_pipeline.cyclic_stateful_adapter import CyclicStatefulAdapterConfig
from youtube_pipeline.daily_frequency_baseline import DailyFrequencyBaselineConfig
from youtube_pipeline.daily_rag_context_selection import DailyContextSelectionConfig
from youtube_pipeline.daily_rag_consumer import DailyRagConsumerConfig
from youtube_pipeline.daily_rag_sidecars import DailyRagSidecarBuildConfig


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
class SimulationConfig:
    """Composition of the existing cyclic simulation stage configurations."""

    ingestion: CyclicIngestionConfig | None = None
    orchestration: CyclicOrchestratorConfig | None = None
    stateful_adapter: CyclicStatefulAdapterConfig | None = None

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
        if all(
            config is None
            for config in (self.ingestion, self.orchestration, self.stateful_adapter)
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
    simulation: SimulationConfig | None = None
    signals: SignalsConfig | None = None
    detection: DetectionConfig | None = None
    rag: RagConfig | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RunIdentityConfig):
            raise TypeError("identity must be RunIdentityConfig.")
        _require_optional_instance("simulation", self.simulation, SimulationConfig)
        _require_optional_instance("signals", self.signals, SignalsConfig)
        _require_optional_instance("detection", self.detection, DetectionConfig)
        _require_optional_instance("rag", self.rag, RagConfig)
        if all(
            section is None
            for section in (self.simulation, self.signals, self.detection, self.rag)
        ):
            raise ValueError("RunConfig must configure at least one execution section.")
        if self.rag is not None:
            rag_run_ids = {
                "rag.daily_sidecars": (
                    None
                    if self.rag.daily_sidecars is None
                    else self.rag.daily_sidecars.run_id
                ),
                "rag.daily_consumer": (
                    None
                    if self.rag.daily_consumer is None
                    else self.rag.daily_consumer.run_id
                ),
                "rag.daily_context_selection": (
                    None
                    if self.rag.daily_context_selection is None
                    else self.rag.daily_context_selection.run_id
                ),
            }
            competing = [
                name
                for name, run_id in rag_run_ids.items()
                if run_id is not None and run_id != self.identity.run_id
            ]
            if competing:
                raise ValueError(
                    ", ".join(competing)
                    + ".run_id must be supplied by identity.run_id."
                )
