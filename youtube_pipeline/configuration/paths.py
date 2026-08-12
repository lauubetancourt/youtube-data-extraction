from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from youtube_pipeline.cyclic_daily_signals import CyclicDailySignalConfig
from youtube_pipeline.cyclic_ingestion import CyclicIngestionConfig
from youtube_pipeline.cyclic_orchestration import CyclicOrchestratorConfig
from youtube_pipeline.cyclic_stateful_adapter import CyclicStatefulAdapterConfig
from youtube_pipeline.daily_frequency_baseline import DailyFrequencyBaselineConfig

from .models import DetectionConfig, RunConfig, SignalsConfig, SimulationConfig
from .serialization import canonical_run_config_json, run_config_hash


def _resolve_path(value: str | Path, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve(strict=False)


def _resolve_optional_path(
    value: str | Path | None,
    base_dir: Path,
) -> Path | None:
    return None if value is None else _resolve_path(value, base_dir)


def _resolve_ingestion(
    config: CyclicIngestionConfig,
    base_dir: Path,
) -> CyclicIngestionConfig:
    return replace(
        config,
        input_path=_resolve_path(config.input_path, base_dir),
        output_dir=_resolve_path(config.output_dir, base_dir),
    )


def _resolve_orchestration(
    config: CyclicOrchestratorConfig,
    base_dir: Path,
) -> CyclicOrchestratorConfig:
    return replace(config, simulation_dir=_resolve_path(config.simulation_dir, base_dir))


def _resolve_stateful_adapter(
    config: CyclicStatefulAdapterConfig,
    base_dir: Path,
) -> CyclicStatefulAdapterConfig:
    return replace(config, simulation_dir=_resolve_path(config.simulation_dir, base_dir))


def _resolve_daily_signals(
    config: CyclicDailySignalConfig,
    base_dir: Path,
) -> CyclicDailySignalConfig:
    return replace(
        config,
        simulation_dir=_resolve_path(config.simulation_dir, base_dir),
        canonical_dataset_path=_resolve_path(config.canonical_dataset_path, base_dir),
        output_dir=_resolve_optional_path(config.output_dir, base_dir),
    )


def _resolve_daily_frequency(
    config: DailyFrequencyBaselineConfig,
    base_dir: Path,
) -> DailyFrequencyBaselineConfig:
    return replace(
        config,
        simulation_dir=_resolve_path(config.simulation_dir, base_dir),
        output_dir=_resolve_optional_path(config.output_dir, base_dir),
    )


def resolve_run_config_paths(
    config: RunConfig,
    *,
    base_dir: str | Path,
) -> RunConfig:
    """Return a new RunConfig with known component paths resolved absolutely."""

    if not isinstance(config, RunConfig):
        raise TypeError("config must be RunConfig.")
    base = Path(base_dir).expanduser().resolve(strict=False)

    simulation = config.simulation
    if simulation is not None:
        simulation = SimulationConfig(
            ingestion=(
                _resolve_ingestion(simulation.ingestion, base)
                if simulation.ingestion is not None
                else None
            ),
            orchestration=(
                _resolve_orchestration(simulation.orchestration, base)
                if simulation.orchestration is not None
                else None
            ),
            stateful_adapter=(
                _resolve_stateful_adapter(simulation.stateful_adapter, base)
                if simulation.stateful_adapter is not None
                else None
            ),
        )

    signals = config.signals
    if signals is not None:
        signals = SignalsConfig(
            daily=(
                _resolve_daily_signals(signals.daily, base)
                if signals.daily is not None
                else None
            )
        )

    detection = config.detection
    if detection is not None:
        detection = DetectionConfig(
            daily_frequency=(
                _resolve_daily_frequency(detection.daily_frequency, base)
                if detection.daily_frequency is not None
                else None
            )
        )

    return RunConfig(
        identity=config.identity,
        simulation=simulation,
        signals=signals,
        detection=detection,
    )


@dataclass(frozen=True, slots=True)
class ResolvedRunConfig:
    """Execution-ready paths plus stable canonical identity for one RunConfig."""

    config: RunConfig
    canonical_json: str
    config_hash: str


def resolve_run_config(
    config: RunConfig,
    *,
    base_dir: str | Path,
) -> ResolvedRunConfig:
    """Resolve physical paths and derive machine-independent canonical identity."""

    base = Path(base_dir).expanduser().resolve(strict=False)
    resolved = resolve_run_config_paths(config, base_dir=base)
    canonical = canonical_run_config_json(resolved, path_base=base)
    return ResolvedRunConfig(
        config=resolved,
        canonical_json=canonical,
        config_hash=run_config_hash(resolved, path_base=base),
    )


__all__ = ["ResolvedRunConfig", "resolve_run_config", "resolve_run_config_paths"]
