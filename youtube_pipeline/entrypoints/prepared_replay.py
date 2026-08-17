from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from youtube_pipeline.configuration import (
    load_run_config,
    resolve_run_config,
    run_config_from_mapping,
)
from youtube_pipeline.prepared_replay import (
    DEFAULT_PREPARED_TIMESTAMP_COLUMN,
    DEFAULT_REPLAY_MAX_SLEEP_SECONDS,
    DEFAULT_REPLAY_SPEED,
    DEFAULT_REPLAY_WINDOW_SIZE,
    PreparedDatasetConfig,
    ReplayConfig,
)


LEGACY_INPUT_PATH = "data/gold/clean_comments.parquet"
LEGACY_OUTPUT_SNAPSHOTS = "data/gold/snapshots.csv"
_LEGACY_IDENTITY = "legacy_prepared_replay"
_LEGACY_FIELDS = {
    "input_path",
    "output_snapshots",
    "ts_col",
    "window_size",
    "speed",
    "max_sleep_seconds",
    "start",
    "end",
}


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Prepared replay config must be a JSON object.")
    return payload


def _legacy_defaults() -> dict[str, Any]:
    return {
        "input_path": LEGACY_INPUT_PATH,
        "output_snapshots": LEGACY_OUTPUT_SNAPSHOTS,
        "ts_col": DEFAULT_PREPARED_TIMESTAMP_COLUMN,
        "window_size": DEFAULT_REPLAY_WINDOW_SIZE,
        "speed": DEFAULT_REPLAY_SPEED,
        "max_sleep_seconds": DEFAULT_REPLAY_MAX_SLEEP_SECONDS,
        "start": None,
        "end": None,
    }


def _legacy_component_payload(
    payload: Mapping[str, Any],
    overrides: Mapping[str, Any] | None,
) -> dict[str, Any]:
    unknown = sorted(set(payload) - _LEGACY_FIELDS)
    if unknown:
        raise ValueError(f"Unknown prepared replay config fields: {unknown}")
    component = {**_legacy_defaults(), **dict(payload)}
    if overrides is not None:
        override_unknown = sorted(set(overrides) - _LEGACY_FIELDS)
        if override_unknown:
            raise ValueError(
                f"Unknown prepared replay override fields: {override_unknown}"
            )
        component.update(dict(overrides))
    return component


def _legacy_run_payload(component: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity": {"run_id": _LEGACY_IDENTITY},
        "data": {
            "prepared_dataset": {
                "path": component["input_path"],
                "timestamp_column": component["ts_col"],
            }
        },
        "simulation": {
            "replay": {
                "output_snapshots": component["output_snapshots"],
                "window_size": component["window_size"],
                "speed": component["speed"],
                "max_sleep_seconds": component["max_sleep_seconds"],
                "start": component["start"],
                "end": component["end"],
            }
        },
    }


def _profile_overrides(
    overrides: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if overrides is None:
        return None
    unknown = sorted(set(overrides) - _LEGACY_FIELDS)
    if unknown:
        raise ValueError(f"Unknown prepared replay override fields: {unknown}")

    data: dict[str, Any] = {}
    replay: dict[str, Any] = {}
    if "input_path" in overrides:
        data["path"] = overrides["input_path"]
    if "ts_col" in overrides:
        data["timestamp_column"] = overrides["ts_col"]
    for field_name in (
        "output_snapshots",
        "window_size",
        "speed",
        "max_sleep_seconds",
        "start",
        "end",
    ):
        if field_name in overrides:
            replay[field_name] = overrides[field_name]

    result: dict[str, Any] = {}
    if data:
        result["data"] = {"prepared_dataset": data}
    if replay:
        result["simulation"] = {"replay": replay}
    return result or None


def _select_configs(
    run: Any,
) -> tuple[PreparedDatasetConfig, ReplayConfig]:
    if run.data is None or run.data.prepared_dataset is None:
        raise ValueError("RunConfig must include data.prepared_dataset.")
    if run.simulation is None or run.simulation.replay is None:
        raise ValueError("RunConfig must include simulation.replay.")
    return run.data.prepared_dataset, run.simulation.replay


def load_legacy_prepared_replay_configs(
    config_file: str | Path | None,
    *,
    overrides: Mapping[str, Any] | None = None,
) -> tuple[PreparedDatasetConfig, ReplayConfig]:
    """Load the previous playback shape through the common strict loader."""

    payload: dict[str, Any] = {}
    if config_file is not None:
        payload = _read_json_object(Path(config_file))
    component = _legacy_component_payload(payload, overrides)
    return _select_configs(run_config_from_mapping(_legacy_run_payload(component)))


def resolve_prepared_replay_configs(
    *,
    config_file: str | Path | None,
    overrides: Mapping[str, Any] | None = None,
    base_dir: str | Path,
) -> tuple[PreparedDatasetConfig, ReplayConfig]:
    """Resolve either a RunConfig profile or the legacy playback shape."""

    if config_file is not None:
        path = Path(config_file)
        payload = _read_json_object(path)
        is_run_profile = "identity" in payload or any(
            section in payload
            for section in ("data", "simulation", "signals", "detection", "rag")
        )
    else:
        path = None
        payload = {}
        is_run_profile = False

    if is_run_profile:
        run = load_run_config(path, overrides=_profile_overrides(overrides))
    else:
        component = _legacy_component_payload(payload, overrides)
        run = run_config_from_mapping(_legacy_run_payload(component))

    resolved = resolve_run_config(run, base_dir=base_dir).config
    return _select_configs(resolved)


__all__ = [
    "LEGACY_INPUT_PATH",
    "LEGACY_OUTPUT_SNAPSHOTS",
    "load_legacy_prepared_replay_configs",
    "resolve_prepared_replay_configs",
]
