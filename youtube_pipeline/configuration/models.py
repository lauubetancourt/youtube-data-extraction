from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from youtube_pipeline.cyclic_daily_signals import CyclicDailySignalConfig
from youtube_pipeline.cyclic_ingestion import CyclicIngestionConfig
from youtube_pipeline.cyclic_orchestration import CyclicOrchestratorConfig
from youtube_pipeline.cyclic_stateful_adapter import CyclicStatefulAdapterConfig
from youtube_pipeline.daily_frequency_baseline import DailyFrequencyBaselineConfig


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

    daily_frequency: DailyFrequencyBaselineConfig | None = None

    def __post_init__(self) -> None:
        _require_optional_instance(
            "daily_frequency",
            self.daily_frequency,
            DailyFrequencyBaselineConfig,
        )
        if self.daily_frequency is None:
            raise ValueError("DetectionConfig must configure at least one detector.")


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Typed composition root for one execution without duplicating component fields."""

    identity: RunIdentityConfig
    simulation: SimulationConfig | None = None
    signals: SignalsConfig | None = None
    detection: DetectionConfig | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RunIdentityConfig):
            raise TypeError("identity must be RunIdentityConfig.")
        _require_optional_instance("simulation", self.simulation, SimulationConfig)
        _require_optional_instance("signals", self.signals, SignalsConfig)
        _require_optional_instance("detection", self.detection, DetectionConfig)
        if all(
            section is None
            for section in (self.simulation, self.signals, self.detection)
        ):
            raise ValueError("RunConfig must configure at least one execution section.")
