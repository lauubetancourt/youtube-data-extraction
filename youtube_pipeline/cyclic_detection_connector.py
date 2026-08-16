from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .detectors import create_detector
from .monitoring import default_activity_metrics, default_polarization_metrics


DETECTION_CONNECTOR_MODE = "detection_dry_run"
DETECTION_SMOKE_TEST_MODE = "detection_smoke_test"
SMOKE_TEST_OUTPUT_SUBDIR = "detection_smoke_test"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required JSON artifact not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must contain an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Required JSONL artifact not found: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL line {line_number} must contain an object: {path}")
        rows.append(payload)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV artifact not found: {path}")
    return pd.read_csv(path)


def _read_table(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.is_dir() or p.suffix.lower() == ".parquet":
        return pd.read_parquet(p)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    raise ValueError(f"Unsupported canonical dataset format: {p}")


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _hash_values(values: list[str] | set[str]) -> str:
    joined = "\n".join(sorted(str(value) for value in values))
    return "sha1_" + hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _required_gold_columns() -> list[str]:
    return ["comment_id", "video_id", "event_time_utc", "text"]


def _optional_gold_columns() -> list[str]:
    return [
        "text_clean",
        "author_id",
        "emoji_count",
        "exclamation_count",
        "question_count",
        "caps_ratio",
        "link_count",
        "token_count",
    ]


def _format_timestamp(value: Any) -> str | None:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class CyclicDetectionConnectorConfig:
    simulation_dir: str | Path
    canonical_dataset_path: str | Path
    mode: str = DETECTION_CONNECTOR_MODE
    max_cycles: int = 5
    output_dir: str | Path | None = None
    debug_full_rows: bool = False
    run_monitoring: bool = False
    run_detection: bool = False
    run_rag: bool = False

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "CyclicDetectionConnectorConfig":
        config_payload = payload.get("cyclic_detection_connector", payload)
        if not isinstance(config_payload, dict):
            raise ValueError("Cyclic detection connector config must be an object.")
        allowed = set(cls.__dataclass_fields__)
        unknown = sorted(set(config_payload) - allowed)
        if unknown:
            raise ValueError(f"Unknown cyclic detection connector config fields: {unknown}")
        return cls(**config_payload)

    def simulation_path(self) -> Path:
        return Path(self.simulation_dir)

    def output_path(self) -> Path:
        if self.output_dir is not None:
            return Path(self.output_dir)
        if self.mode == DETECTION_SMOKE_TEST_MODE:
            return self.simulation_path() / SMOKE_TEST_OUTPUT_SUBDIR
        return self.simulation_path()

    def validate_c4_scope(self) -> None:
        if self.mode not in {DETECTION_CONNECTOR_MODE, DETECTION_SMOKE_TEST_MODE}:
            raise ValueError(
                "C-4 supports mode='detection_dry_run' or mode='detection_smoke_test'."
            )
        if self.max_cycles < 1:
            raise ValueError("max_cycles must be >= 1.")
        if self.debug_full_rows:
            raise ValueError(
                "debug_full_rows requires explicit approval and is disabled for this smoke test."
            )
        forbidden = {
            "run_rag": self.run_rag,
        }
        if self.mode == DETECTION_CONNECTOR_MODE:
            forbidden["run_monitoring"] = self.run_monitoring
            forbidden["run_detection"] = self.run_detection
        elif self.run_monitoring or self.run_detection:
            raise ValueError(
                "detection_smoke_test runs the approved controlled path internally; "
                "do not pass run_monitoring/run_detection flags."
            )
        enabled = [name for name, value in forbidden.items() if value]
        if enabled:
            raise ValueError(
                f"C-4 {self.mode} forbids these flags: "
                + ", ".join(enabled)
            )


def load_cyclic_detection_connector_config(
    config_file: str | Path | None,
    *,
    overrides: dict[str, Any] | None = None,
) -> CyclicDetectionConnectorConfig:
    """Compatibility shim; configuration I/O belongs to the entrypoint layer."""

    from .entrypoints.cyclic_detection_connector import (
        load_legacy_detection_connector_config,
    )

    return load_legacy_detection_connector_config(config_file, overrides=overrides)


def _validate_inputs(
    *,
    adapter_manifest: dict[str, Any],
    monitoring_inputs: list[dict[str, Any]],
    detection_inputs: list[dict[str, Any]],
    window_inventory: pd.DataFrame,
) -> list[str]:
    errors: list[str] = []
    if adapter_manifest.get("adapter_stage") != "C-3":
        errors.append("cycle_adapter_manifest.json must come from C-3.")
    if adapter_manifest.get("adapter_mode") != "stateful":
        errors.append("C-4 requires C-3 adapter_mode='stateful'.")
    guards = adapter_manifest.get("execution_guards", {})
    for key in ["run_monitoring", "run_detection", "run_rag"]:
        if guards.get(key) is not False:
            errors.append(f"C-3 execution guard {key} must be false.")
    if len(monitoring_inputs) != len(detection_inputs):
        errors.append("Monitoring and detection input counts must match.")
    monitoring_cycle_ids = {row.get("cycle_id") for row in monitoring_inputs}
    detection_cycle_ids = {row.get("cycle_id") for row in detection_inputs}
    if monitoring_cycle_ids != detection_cycle_ids:
        errors.append("Monitoring and detection input cycle_id sets must match.")
    required_window = {
        "cycle_id",
        "cycle_index",
        "comment_id",
        "video_id",
        "event_time_utc",
        "analysis_window_start_utc",
        "analysis_window_end_utc",
        "data_cutoff_utc",
        "is_active_in_window",
        "exited_window",
    }
    missing_window = sorted(required_window - set(window_inventory.columns))
    if missing_window:
        errors.append(f"cycle_window_inventory.csv missing fields: {missing_window}")
    return errors


def _selected_cycles(
    detection_inputs: list[dict[str, Any]],
    *,
    max_cycles: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    ordered = sorted(
        detection_inputs,
        key=lambda row: (
            int(row["cycle_index"]),
            pd.Timestamp(row["cycle_run_at_utc"]),
            str(row["cycle_id"]),
        ),
    )
    selected = ordered[:max_cycles]
    pending = [str(row["cycle_id"]) for row in ordered[max_cycles:]]
    return selected, pending


def _active_window_rows(window_inventory: pd.DataFrame, cycle_id: str) -> pd.DataFrame:
    active = _bool_series(window_inventory["is_active_in_window"])
    return window_inventory.loc[active & (window_inventory["cycle_id"] == cycle_id)].copy()


def _cycle_time_summary(active_rows: pd.DataFrame) -> dict[str, Any]:
    if active_rows.empty:
        return {
            "event_time_min_utc": None,
            "event_time_max_utc": None,
        }
    times = pd.to_datetime(active_rows["event_time_utc"], utc=True, errors="coerce")
    return {
        "event_time_min_utc": times.min().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_time_max_utc": times.max().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _validate_temporal_semantics(active_rows: pd.DataFrame, cycle: dict[str, Any]) -> dict[str, Any]:
    if active_rows.empty:
        return {
            "future_leak_count": 0,
            "outside_analysis_window_count": 0,
            "temporal_status": "passed",
        }
    event_time = pd.to_datetime(active_rows["event_time_utc"], utc=True, errors="coerce")
    start = pd.Timestamp(cycle["analysis_window_start_utc"])
    end = pd.Timestamp(cycle["analysis_window_end_utc"])
    cutoff = pd.Timestamp(cycle["data_cutoff_utc"])
    future_leak_count = int((event_time >= cutoff).sum())
    outside_count = int(((event_time < start) | (event_time >= end)).sum())
    return {
        "future_leak_count": future_leak_count,
        "outside_analysis_window_count": outside_count,
        "temporal_status": "passed"
        if future_leak_count == 0 and outside_count == 0
        else "failed",
    }


def _load_and_validate_gold(config: CyclicDetectionConnectorConfig) -> tuple[pd.DataFrame, dict[str, Any]]:
    gold_path = Path(config.canonical_dataset_path)
    gold = _read_table(gold_path).copy()
    required = _required_gold_columns()
    missing_columns = sorted(set(required) - set(gold.columns))
    if missing_columns:
        raise ValueError(
            "Gold canonical dataset missing required fields: "
            + ", ".join(missing_columns)
        )

    gold["comment_id"] = gold["comment_id"].astype(str)
    duplicate_mask = gold["comment_id"].duplicated(keep=False)
    duplicate_count = int(duplicate_mask.sum())
    if duplicate_count:
        sample = sorted(gold.loc[duplicate_mask, "comment_id"].unique().tolist())[:10]
        raise ValueError(
            "comment_id must be unique in Gold before detection_smoke_test. "
            f"duplicate_row_count={duplicate_count}; sample={sample}"
        )

    gold["event_time_utc"] = pd.to_datetime(
        gold["event_time_utc"], utc=True, errors="coerce"
    )
    invalid_time_count = int(gold["event_time_utc"].isna().sum())
    if invalid_time_count:
        raise ValueError(
            "Gold canonical dataset has invalid event_time_utc values. "
            f"invalid_time_count={invalid_time_count}"
        )

    optional_available = [column for column in _optional_gold_columns() if column in gold.columns]
    schema = {
        "canonical_dataset_path": str(gold_path),
        "canonical_dataset_role": "gold_comments",
        "row_count": int(len(gold)),
        "required_columns": required,
        "optional_columns_available": optional_available,
        "all_columns": list(gold.columns),
        "comment_id_unique": True,
        "duplicate_comment_id_count": 0,
        "invalid_event_time_count": 0,
        "schema_status": "passed",
    }
    return gold, schema


def _resolve_cycle_gold_view(
    *,
    cycle: dict[str, Any],
    active_rows: pd.DataFrame,
    gold_by_comment_id: pd.DataFrame,
    gold_schema: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    active_rows = active_rows.copy()
    active_rows["comment_id"] = active_rows["comment_id"].astype(str)
    active_comment_ids = active_rows["comment_id"].tolist()
    active_unique_comment_ids = sorted(set(active_comment_ids))
    duplicate_active_count = int(len(active_comment_ids) - len(active_unique_comment_ids))

    missing_comment_ids = sorted(set(active_unique_comment_ids) - set(gold_by_comment_id.index))
    joined = gold_by_comment_id.reindex(active_comment_ids).reset_index()
    joined = joined.dropna(subset=["video_id", "event_time_utc"], how="all")
    joined_comment_count = int(len(joined))
    expected_count = int(len(active_rows))
    extra_joined_count = max(0, joined_comment_count - expected_count)

    cycle_context_columns = [
        "comment_id",
        "cycle_id",
        "cycle_index",
        "first_seen_cycle_id",
        "window_membership_role",
        "is_new_in_cycle",
        "is_active_in_window",
        "is_accumulated_by_cycle",
        "analysis_window_start_utc",
        "analysis_window_end_utc",
        "data_cutoff_utc",
    ]
    available_context_columns = [
        column for column in cycle_context_columns if column in active_rows.columns
    ]
    cycle_context = active_rows[available_context_columns].copy()
    view = joined.merge(
        cycle_context,
        on="comment_id",
        how="left",
        suffixes=("", "_cycle"),
    )

    event_time = pd.to_datetime(view["event_time_utc"], utc=True, errors="coerce")
    start = pd.Timestamp(cycle["analysis_window_start_utc"])
    end = pd.Timestamp(cycle["analysis_window_end_utc"])
    cutoff = pd.Timestamp(cycle["data_cutoff_utc"])
    future_leak_count = int((event_time >= cutoff).sum())
    outside_analysis_count = int(((event_time < start) | (event_time >= end)).sum())

    checks_pass = (
        gold_schema["comment_id_unique"] is True
        and duplicate_active_count == 0
        and len(missing_comment_ids) == 0
        and joined_comment_count == expected_count
        and extra_joined_count == 0
        and future_leak_count == 0
        and outside_analysis_count == 0
    )
    report = {
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "canonical_dataset_path": gold_schema["canonical_dataset_path"],
        "canonical_dataset_role": gold_schema["canonical_dataset_role"],
        "comment_ids_hash": _hash_values(active_comment_ids),
        "active_window_comment_count": expected_count,
        "active_unique_comment_count": int(len(active_unique_comment_ids)),
        "duplicate_active_comment_id_count": duplicate_active_count,
        "joined_comment_count": joined_comment_count,
        "missing_comment_id_count": int(len(missing_comment_ids)),
        "missing_comment_id_sample": missing_comment_ids[:10],
        "extra_joined_comment_count": int(extra_joined_count),
        "future_leak_count": future_leak_count,
        "outside_analysis_window_count": outside_analysis_count,
        "gold_comment_id_unique": gold_schema["comment_id_unique"],
        "gold_duplicate_comment_id_count": gold_schema["duplicate_comment_id_count"],
        "required_columns": gold_schema["required_columns"],
        "optional_columns_available": gold_schema["optional_columns_available"],
        "schema_status": gold_schema["schema_status"],
        "join_status": "passed" if checks_pass else "failed",
        "materialization_mode": "in_memory",
        "full_rows_written": False,
        "debug_full_rows": False,
        "analysis_window_start_utc": cycle["analysis_window_start_utc"],
        "analysis_window_end_utc": cycle["analysis_window_end_utc"],
        "data_cutoff_utc": cycle["data_cutoff_utc"],
    }
    return view, report


def _monitoring_output(
    *,
    cycle: dict[str, Any],
    active_rows: pd.DataFrame,
    temporal: dict[str, Any],
) -> dict[str, Any]:
    comment_ids = active_rows["comment_id"].astype(str).tolist()
    video_ids = sorted(active_rows["video_id"].dropna().astype(str).unique().tolist())
    return {
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "mode": DETECTION_CONNECTOR_MODE,
        "monitoring_status": "prepared_not_executed",
        "analysis_window_start_utc": cycle["analysis_window_start_utc"],
        "analysis_window_end_utc": cycle["analysis_window_end_utc"],
        "data_cutoff_utc": cycle["data_cutoff_utc"],
        "active_window_comment_count": len(comment_ids),
        "active_video_count": len(video_ids),
        "active_comment_ids_hash": _hash_values(comment_ids),
        "active_video_ids": video_ids,
        "time_summary": _cycle_time_summary(active_rows),
        "input_table_ref": "cycle_window_inventory.csv",
        "monitoring_function_ref": "build_event_time_window_stream",
        "metrics_contract_ref": [
            "default_activity_metrics",
            "default_polarization_metrics",
        ],
        "temporal_validation": temporal,
        "run_monitoring": False,
    }


def _detection_output(
    *,
    cycle: dict[str, Any],
    active_rows: pd.DataFrame,
    detection_input: dict[str, Any],
    temporal: dict[str, Any],
) -> dict[str, Any]:
    comment_ids = active_rows["comment_id"].astype(str).tolist()
    video_ids = sorted(active_rows["video_id"].dropna().astype(str).unique().tolist())
    return {
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "mode": DETECTION_CONNECTOR_MODE,
        "detection_status": "prepared_not_executed",
        "detector_ref": "xiao_ema",
        "detector_state_mode": "stateful_required",
        "analysis_window_start_utc": cycle["analysis_window_start_utc"],
        "analysis_window_end_utc": cycle["analysis_window_end_utc"],
        "data_cutoff_utc": cycle["data_cutoff_utc"],
        "active_window_comment_count": len(comment_ids),
        "new_comment_count": int(detection_input.get("new_comment_count", 0)),
        "overlap_with_previous_cycle_count": int(
            detection_input.get("overlap_with_previous_cycle_count", 0)
        ),
        "active_comment_ids_hash": _hash_values(comment_ids),
        "active_video_ids": video_ids,
        "input_table_ref": "cycle_window_inventory.csv",
        "decision_state_ref": "cycle_detector_state.json",
        "event_registry_ref": "cycle_event_registry.jsonl",
        "deduplication_policy_ref": "cycle_detection_manifest.json#deduplication_policy",
        "events_detected_count": 0,
        "trigger_ids": [],
        "temporal_validation": temporal,
        "run_detection": False,
    }


def _quality_row(
    *,
    cycle: dict[str, Any],
    monitoring_output: dict[str, Any],
    detection_output: dict[str, Any],
    temporal: dict[str, Any],
) -> dict[str, Any]:
    status = (
        "passed"
        if (
            temporal["temporal_status"] == "passed"
            and monitoring_output["active_window_comment_count"]
            == detection_output["active_window_comment_count"]
        )
        else "failed"
    )
    return {
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "quality_status": status,
        "checks": {
            "temporal_status": temporal["temporal_status"],
            "future_leak_count": temporal["future_leak_count"],
            "outside_analysis_window_count": temporal["outside_analysis_window_count"],
            "monitoring_detection_input_counts_match": (
                monitoring_output["active_window_comment_count"]
                == detection_output["active_window_comment_count"]
            ),
            "run_monitoring": False,
            "run_detection": False,
            "run_rag": False,
            "event_registry_status": "empty_detector_not_executed",
        },
    }


def _trigger_record(
    *,
    trigger: dict[str, Any],
    cycle: dict[str, Any],
    trigger_ordinal: int,
) -> dict[str, Any]:
    trigger_time = _format_timestamp(trigger.get("trigger_time"))
    cooldown_until = _format_timestamp(trigger.get("cooldown_until"))
    closed_at = _format_timestamp(trigger.get("closed_at"))
    digest = hashlib.sha1(
        "|".join(
            [
                str(cycle["simulation_run_id"]),
                str(cycle["cycle_id"]),
                str(trigger_time),
                str(cooldown_until),
                str(trigger.get("volume")),
                str(trigger_ordinal),
            ]
        ).encode("utf-8")
    ).hexdigest()[:12]
    comments = trigger.get("comments", [])
    return {
        "trigger_id": f"smoke_trg_{digest}",
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "trigger_ordinal": int(trigger_ordinal),
        "trigger_time": trigger_time,
        "cooldown_until": cooldown_until,
        "closed_at": closed_at,
        "volume": int(trigger.get("volume", 0)),
        "strength": float(trigger.get("strength", 0.0)),
        "trigger_comment_count": int(len(comments)),
        "detector_ref": "xiao_ema",
        "source": DETECTION_SMOKE_TEST_MODE,
    }


def _run_monitoring_for_view(
    *,
    cycle: dict[str, Any],
    view: pd.DataFrame,
    join_report: dict[str, Any],
) -> dict[str, Any]:
    comment_ids = view["comment_id"].astype(str).tolist()
    video_ids = sorted(view["video_id"].dropna().astype(str).unique().tolist())
    activity = default_activity_metrics(view)
    polarization = default_polarization_metrics(view)
    return {
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "mode": DETECTION_SMOKE_TEST_MODE,
        "monitoring_status": "executed_smoke_test",
        "analysis_window_start_utc": cycle["analysis_window_start_utc"],
        "analysis_window_end_utc": cycle["analysis_window_end_utc"],
        "data_cutoff_utc": cycle["data_cutoff_utc"],
        "active_window_comment_count": int(len(comment_ids)),
        "active_video_count": int(len(video_ids)),
        "active_comment_ids_hash": _hash_values(comment_ids),
        "active_video_ids": video_ids,
        "time_summary": _cycle_time_summary(view),
        "canonical_dataset_ref": join_report["canonical_dataset_path"],
        "input_table_ref": "cycle_window_inventory.csv",
        "materialization_mode": "in_memory",
        "full_rows_written": False,
        "activity": activity,
        "polarization": polarization,
        "join_status": join_report["join_status"],
        "run_monitoring": True,
    }


def _events_for_detector(view: pd.DataFrame, cycle: dict[str, Any]) -> pd.DataFrame:
    if view.empty:
        return view.copy()
    if "first_seen_cycle_id" in view.columns:
        events = view.loc[view["first_seen_cycle_id"].astype(str) == str(cycle["cycle_id"])].copy()
    else:
        events = view.copy()
    if events.empty:
        return events
    events["event_time_utc"] = pd.to_datetime(
        events["event_time_utc"], utc=True, errors="coerce"
    )
    events = events.dropna(subset=["event_time_utc"])
    return events.sort_values(["event_time_utc", "comment_id"])


def _run_detector_for_cycle(
    *,
    detector: Any,
    cycle: dict[str, Any],
    view: pd.DataFrame,
    previous_completed_count: int,
    canonical_dataset_path: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    events = _events_for_detector(view, cycle)
    for _, row in events.iterrows():
        detector.on_event(row.to_dict())

    new_triggers = detector.completed_triggers[previous_completed_count:]
    trigger_rows = [
        _trigger_record(trigger=trigger, cycle=cycle, trigger_ordinal=index)
        for index, trigger in enumerate(new_triggers, start=previous_completed_count + 1)
    ]
    comment_ids = view["comment_id"].astype(str).tolist()
    video_ids = sorted(view["video_id"].dropna().astype(str).unique().tolist())
    output = {
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "mode": DETECTION_SMOKE_TEST_MODE,
        "detection_status": "executed_smoke_test",
        "detector_ref": "xiao_ema",
        "detector_state_mode": "stateful",
        "analysis_window_start_utc": cycle["analysis_window_start_utc"],
        "analysis_window_end_utc": cycle["analysis_window_end_utc"],
        "data_cutoff_utc": cycle["data_cutoff_utc"],
        "active_window_comment_count": int(len(comment_ids)),
        "event_rows_fed_count": int(len(events)),
        "active_comment_ids_hash": _hash_values(comment_ids),
        "active_video_ids": video_ids,
        "input_table_ref": "cycle_window_inventory.csv",
        "canonical_dataset_ref": canonical_dataset_path,
        "materialization_mode": "in_memory",
        "full_rows_written": False,
        "events_detected_count": int(len(trigger_rows)),
        "trigger_ids": [row["trigger_id"] for row in trigger_rows],
        "run_detection": True,
        "detector_feed_policy": (
            "stateful detector receives new comments once; active sliding-window "
            "context is resolved and recorded per cycle"
        ),
    }
    return output, trigger_rows


def _smoke_quality_row(
    *,
    cycle: dict[str, Any],
    join_report: dict[str, Any],
    monitoring_output: dict[str, Any],
    detection_output: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "gold_comment_id_unique": join_report["gold_comment_id_unique"],
        "inventory_subset_of_gold": join_report["missing_comment_id_count"] == 0,
        "joined_comment_count_matches_active_window": (
            join_report["joined_comment_count"]
            == join_report["active_window_comment_count"]
        ),
        "missing_comment_id_count": join_report["missing_comment_id_count"],
        "extra_joined_comment_count": join_report["extra_joined_comment_count"],
        "future_leak_count": join_report["future_leak_count"],
        "outside_analysis_window_count": join_report["outside_analysis_window_count"],
        "monitoring_detection_input_counts_match": (
            monitoring_output["active_window_comment_count"]
            == detection_output["active_window_comment_count"]
        ),
        "materialization_mode": "in_memory",
        "full_rows_written": False,
        "run_rag": False,
    }
    passed = (
        join_report["join_status"] == "passed"
        and checks["monitoring_detection_input_counts_match"]
    )
    return {
        "simulation_run_id": cycle["simulation_run_id"],
        "cycle_id": cycle["cycle_id"],
        "cycle_index": int(cycle["cycle_index"]),
        "quality_status": "passed" if passed else "failed",
        "checks": checks,
    }


def run_cyclic_detection_smoke_test(config: CyclicDetectionConnectorConfig) -> dict[str, Any]:
    simulation_dir = config.simulation_path()
    output_dir = config.output_path()
    adapter_manifest = _read_json(simulation_dir / "cycle_adapter_manifest.json")
    stateful_context = _read_json(simulation_dir / "cycle_stateful_context.json")
    monitoring_inputs = _read_jsonl(simulation_dir / "cycle_monitoring_inputs.jsonl")
    detection_inputs = _read_jsonl(simulation_dir / "cycle_detection_inputs.jsonl")
    window_inventory = _read_csv(simulation_dir / "cycle_window_inventory.csv")
    input_errors = _validate_inputs(
        adapter_manifest=adapter_manifest,
        monitoring_inputs=monitoring_inputs,
        detection_inputs=detection_inputs,
        window_inventory=window_inventory,
    )
    if input_errors:
        raise ValueError("C-4 smoke input validation failed: " + "; ".join(input_errors))

    gold, gold_schema = _load_and_validate_gold(config)
    gold_by_comment_id = gold.set_index("comment_id")
    selected_cycles, pending_cycle_ids = _selected_cycles(
        detection_inputs,
        max_cycles=config.max_cycles,
    )
    monitoring_by_cycle = {row["cycle_id"]: row for row in monitoring_inputs}

    detector_logs: list[str] = []
    detector = create_detector(log_fn=detector_logs.append)
    previous_completed_count = 0
    processed_cycle_ids: list[str] = []
    monitoring_outputs: list[dict[str, Any]] = []
    detection_outputs: list[dict[str, Any]] = []
    join_reports: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    event_registry_rows: list[dict[str, Any]] = []
    last_cycle: dict[str, Any] | None = None
    last_processed_ts: pd.Timestamp | None = None

    for cycle in selected_cycles:
        cycle_id = cycle["cycle_id"]
        if cycle_id not in monitoring_by_cycle:
            raise ValueError(f"Missing monitoring input for cycle_id={cycle_id}")
        active_rows = _active_window_rows(window_inventory, cycle_id)
        view, join_report = _resolve_cycle_gold_view(
            cycle=cycle,
            active_rows=active_rows,
            gold_by_comment_id=gold_by_comment_id,
            gold_schema=gold_schema,
        )
        if join_report["join_status"] != "passed":
            raise ValueError(
                "C-4 smoke join validation failed for "
                f"cycle_id={cycle_id}: {join_report}"
            )

        monitoring_output = _run_monitoring_for_view(
            cycle=cycle,
            view=view,
            join_report=join_report,
        )
        detection_output, trigger_rows = _run_detector_for_cycle(
            detector=detector,
            cycle=cycle,
            view=view,
            previous_completed_count=previous_completed_count,
            canonical_dataset_path=gold_schema["canonical_dataset_path"],
        )
        previous_completed_count = len(detector.completed_triggers)
        if not view.empty:
            cycle_max_ts = pd.to_datetime(view["event_time_utc"], utc=True, errors="coerce").max()
            if not pd.isna(cycle_max_ts):
                last_processed_ts = pd.Timestamp(cycle_max_ts)
        monitoring_outputs.append(monitoring_output)
        detection_outputs.append(detection_output)
        event_registry_rows.extend(trigger_rows)
        join_reports.append(join_report)
        quality_rows.append(
            _smoke_quality_row(
                cycle=cycle,
                join_report=join_report,
                monitoring_output=monitoring_output,
                detection_output=detection_output,
            )
        )
        processed_cycle_ids.append(cycle_id)
        last_cycle = cycle

    if last_cycle is not None:
        detector.finalize(last_processed_ts or pd.Timestamp(last_cycle["data_cutoff_utc"]))
        final_triggers = detector.completed_triggers[previous_completed_count:]
        if final_triggers:
            final_rows = [
                _trigger_record(trigger=trigger, cycle=last_cycle, trigger_ordinal=index)
                for index, trigger in enumerate(
                    final_triggers,
                    start=previous_completed_count + 1,
                )
            ]
            event_registry_rows.extend(final_rows)
            if detection_outputs:
                detection_outputs[-1]["events_detected_count"] += len(final_rows)
                detection_outputs[-1]["trigger_ids"].extend(
                    row["trigger_id"] for row in final_rows
                )

    simulation_run_id = str(adapter_manifest["simulation_run_id"])
    events_detected_count = int(len(event_registry_rows))
    detector_state = {
        "simulation_run_id": simulation_run_id,
        "stage": "C-4",
        "mode": DETECTION_SMOKE_TEST_MODE,
        "stateful": True,
        "status": "executed_smoke_test",
        "processed_cycle_ids": processed_cycle_ids,
        "pending_cycle_ids": pending_cycle_ids,
        "last_processed_cycle_id": processed_cycle_ids[-1] if processed_cycle_ids else None,
        "comments_seen_count_from_c3": stateful_context.get("seen_comment_count"),
        "events_emitted_count": events_detected_count,
        "events_emitted_hash": _hash_values(
            [row["trigger_id"] for row in event_registry_rows]
        ),
        "cooldown_state": {
            "status": "detector_internal_state_not_serialized",
            "detector_ref": "xiao_ema",
        },
        "decision_state": {
            "status": "stateful_smoke_executed",
            "detector_ref": "xiao_ema",
            "feed_policy": "new_comments_once_active_window_validated_per_cycle",
        },
        "last_triggers": event_registry_rows[-5:],
    }
    manifest = {
        "simulation_run_id": simulation_run_id,
        "stage": "C-4",
        "mode": DETECTION_SMOKE_TEST_MODE,
        "status": "executed_smoke_test",
        "processed_cycle_count": len(processed_cycle_ids),
        "pending_cycle_count": len(pending_cycle_ids),
        "processed_cycle_ids": processed_cycle_ids,
        "pending_cycle_ids": pending_cycle_ids,
        "max_cycles": config.max_cycles,
        "canonical_dataset": gold_schema,
        "materialization_policy": {
            "cycle_window_inventory_role": "cycle_and_window_index",
            "canonical_source_for_rows": gold_schema["canonical_dataset_path"],
            "materialization_mode": "in_memory",
            "debug_full_rows": False,
            "full_rows_written": False,
            "debug_full_rows_artifact": None,
        },
        "execution_guards": {
            "run_monitoring": True,
            "run_detection": True,
            "run_rag": False,
            "llm_calls": 0,
            "serper_calls": 0,
            "embeddings": False,
            "vectorstore": False,
        },
        "stateful_policy": {
            "preserve_state_between_cycles": True,
            "detector_reset_between_cycles": False,
            "state_source": "cycle_stateful_context.json",
            "detector_state_output": "cycle_detector_state.json",
            "detector_feed_policy": (
                "new comments are sent once to the event-driven detector; "
                "active sliding-window context is joined and validated every cycle"
            ),
        },
        "output_artifacts": {
            "cycle_smoke_test_manifest": "cycle_smoke_test_manifest.json",
            "cycle_smoke_test_join_report": "cycle_smoke_test_join_report.jsonl",
            "cycle_monitoring_outputs": "cycle_monitoring_outputs.jsonl",
            "cycle_detection_outputs": "cycle_detection_outputs.jsonl",
            "cycle_detector_state": "cycle_detector_state.json",
            "cycle_event_registry": "cycle_event_registry.jsonl",
            "cycle_detection_quality_report": "cycle_detection_quality_report.jsonl",
        },
        "detector_logs": detector_logs,
        "compatibility": {
            "retrospective_replay_status": "untouched",
            "dry_run_outputs_status": "untouched_separate_output_dir",
            "rag_status": "not_executed_smoke_test",
            "sidecars_status": "untouched",
            "bronze_silver_gold_status": "read_only_gold_not_modified",
        },
    }

    _write_json(output_dir / "cycle_smoke_test_manifest.json", manifest)
    _write_jsonl(output_dir / "cycle_smoke_test_join_report.jsonl", join_reports)
    _write_jsonl(output_dir / "cycle_monitoring_outputs.jsonl", monitoring_outputs)
    _write_jsonl(output_dir / "cycle_detection_outputs.jsonl", detection_outputs)
    _write_json(output_dir / "cycle_detector_state.json", detector_state)
    _write_jsonl(output_dir / "cycle_event_registry.jsonl", event_registry_rows)
    _write_jsonl(output_dir / "cycle_detection_quality_report.jsonl", quality_rows)

    failed_quality = sum(1 for row in quality_rows if row["quality_status"] != "passed")
    return {
        "simulation_run_id": simulation_run_id,
        "simulation_dir": str(simulation_dir),
        "output_dir": str(output_dir),
        "mode": DETECTION_SMOKE_TEST_MODE,
        "processed_cycle_count": len(processed_cycle_ids),
        "pending_cycle_count": len(pending_cycle_ids),
        "failed_quality_count": failed_quality,
        "events_detected_count": events_detected_count,
        "gold_comment_id_unique": gold_schema["comment_id_unique"],
        "full_rows_written": False,
        "artifacts": {
            "cycle_smoke_test_manifest": str(output_dir / "cycle_smoke_test_manifest.json"),
            "cycle_smoke_test_join_report": str(
                output_dir / "cycle_smoke_test_join_report.jsonl"
            ),
            "cycle_monitoring_outputs": str(output_dir / "cycle_monitoring_outputs.jsonl"),
            "cycle_detection_outputs": str(output_dir / "cycle_detection_outputs.jsonl"),
            "cycle_detector_state": str(output_dir / "cycle_detector_state.json"),
            "cycle_event_registry": str(output_dir / "cycle_event_registry.jsonl"),
            "cycle_detection_quality_report": str(
                output_dir / "cycle_detection_quality_report.jsonl"
            ),
        },
    }


def run_cyclic_detection_connector(config: CyclicDetectionConnectorConfig) -> dict[str, Any]:
    config.validate_c4_scope()
    if config.mode == DETECTION_SMOKE_TEST_MODE:
        return run_cyclic_detection_smoke_test(config)
    simulation_dir = config.simulation_path()
    adapter_manifest = _read_json(simulation_dir / "cycle_adapter_manifest.json")
    stateful_context = _read_json(simulation_dir / "cycle_stateful_context.json")
    monitoring_inputs = _read_jsonl(simulation_dir / "cycle_monitoring_inputs.jsonl")
    detection_inputs = _read_jsonl(simulation_dir / "cycle_detection_inputs.jsonl")
    window_inventory = _read_csv(simulation_dir / "cycle_window_inventory.csv")
    input_errors = _validate_inputs(
        adapter_manifest=adapter_manifest,
        monitoring_inputs=monitoring_inputs,
        detection_inputs=detection_inputs,
        window_inventory=window_inventory,
    )
    if input_errors:
        raise ValueError("C-4 input validation failed: " + "; ".join(input_errors))

    selected_cycles, pending_cycle_ids = _selected_cycles(
        detection_inputs,
        max_cycles=config.max_cycles,
    )
    monitoring_by_cycle = {row["cycle_id"]: row for row in monitoring_inputs}
    detection_outputs: list[dict[str, Any]] = []
    monitoring_outputs: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    processed_cycle_ids: list[str] = []
    previous_active_hash: str | None = None

    for cycle in selected_cycles:
        cycle_id = cycle["cycle_id"]
        if cycle_id not in monitoring_by_cycle:
            raise ValueError(f"Missing monitoring input for cycle_id={cycle_id}")
        active_rows = _active_window_rows(window_inventory, cycle_id)
        temporal = _validate_temporal_semantics(active_rows, cycle)
        monitoring_output = _monitoring_output(
            cycle=cycle,
            active_rows=active_rows,
            temporal=temporal,
        )
        detection_output = _detection_output(
            cycle=cycle,
            active_rows=active_rows,
            detection_input=cycle,
            temporal=temporal,
        )
        detection_output["previous_active_comment_ids_hash"] = previous_active_hash
        previous_active_hash = detection_output["active_comment_ids_hash"]
        monitoring_outputs.append(monitoring_output)
        detection_outputs.append(detection_output)
        quality_rows.append(
            _quality_row(
                cycle=cycle,
                monitoring_output=monitoring_output,
                detection_output=detection_output,
                temporal=temporal,
            )
        )
        processed_cycle_ids.append(cycle_id)

    simulation_run_id = str(adapter_manifest["simulation_run_id"])
    detector_state = {
        "simulation_run_id": simulation_run_id,
        "stage": "C-4",
        "mode": DETECTION_CONNECTOR_MODE,
        "stateful": True,
        "status": "prepared_not_executed",
        "processed_cycle_ids": processed_cycle_ids,
        "pending_cycle_ids": pending_cycle_ids,
        "last_processed_cycle_id": processed_cycle_ids[-1] if processed_cycle_ids else None,
        "comments_seen_count_from_c3": stateful_context.get("seen_comment_count"),
        "snapshots_previous_ref": "cycle_monitoring_outputs.jsonl",
        "events_emitted_count": 0,
        "events_emitted_hash": _hash_values([]),
        "cooldown_state": {
            "status": "not_available_detector_not_executed",
            "entries": [],
        },
        "decision_state": {
            "status": "not_available_detector_not_executed",
            "detector_ref": "xiao_ema",
        },
        "last_triggers": [],
    }
    event_registry_rows: list[dict[str, Any]] = []
    manifest = {
        "simulation_run_id": simulation_run_id,
        "stage": "C-4",
        "mode": DETECTION_CONNECTOR_MODE,
        "status": "prepared_not_executed",
        "processed_cycle_count": len(processed_cycle_ids),
        "pending_cycle_count": len(pending_cycle_ids),
        "processed_cycle_ids": processed_cycle_ids,
        "pending_cycle_ids": pending_cycle_ids,
        "max_cycles": config.max_cycles,
        "execution_guards": {
            "run_monitoring": False,
            "run_detection": False,
            "run_rag": False,
            "llm_calls": 0,
            "serper_calls": 0,
            "embeddings": False,
            "vectorstore": False,
        },
        "stateful_policy": {
            "preserve_state_between_cycles": True,
            "detector_reset_between_cycles": False,
            "state_source": "cycle_stateful_context.json",
            "detector_state_output": "cycle_detector_state.json",
        },
        "deduplication_policy": {
            "status": "designed_not_applied_detector_not_executed",
            "registry_ref": "cycle_event_registry.jsonl",
            "fields_considered": [
                "cycle_id",
                "trigger_time",
                "window_start",
                "window_end",
                "video_id",
                "active_comment_ids_hash",
                "overlap_with_previous_cycle_count",
                "cooldown_state",
            ],
            "requires_detector_execution": True,
        },
        "output_artifacts": {
            "cycle_monitoring_outputs": "cycle_monitoring_outputs.jsonl",
            "cycle_detection_outputs": "cycle_detection_outputs.jsonl",
            "cycle_detector_state": "cycle_detector_state.json",
            "cycle_event_registry": "cycle_event_registry.jsonl",
            "cycle_detection_manifest": "cycle_detection_manifest.json",
            "cycle_detection_quality_report": "cycle_detection_quality_report.jsonl",
        },
        "compatibility": {
            "retrospective_replay_status": "untouched",
            "rag_status": "not_executed_c4",
            "sidecars_status": "untouched",
        },
    }

    _write_jsonl(simulation_dir / "cycle_monitoring_outputs.jsonl", monitoring_outputs)
    _write_jsonl(simulation_dir / "cycle_detection_outputs.jsonl", detection_outputs)
    _write_json(simulation_dir / "cycle_detector_state.json", detector_state)
    _write_jsonl(simulation_dir / "cycle_event_registry.jsonl", event_registry_rows)
    _write_json(simulation_dir / "cycle_detection_manifest.json", manifest)
    _write_jsonl(simulation_dir / "cycle_detection_quality_report.jsonl", quality_rows)

    failed_quality = sum(1 for row in quality_rows if row["quality_status"] != "passed")
    return {
        "simulation_run_id": simulation_run_id,
        "simulation_dir": str(simulation_dir),
        "mode": DETECTION_CONNECTOR_MODE,
        "processed_cycle_count": len(processed_cycle_ids),
        "pending_cycle_count": len(pending_cycle_ids),
        "failed_quality_count": failed_quality,
        "events_detected_count": 0,
        "artifacts": {
            "cycle_monitoring_outputs": str(simulation_dir / "cycle_monitoring_outputs.jsonl"),
            "cycle_detection_outputs": str(simulation_dir / "cycle_detection_outputs.jsonl"),
            "cycle_detector_state": str(simulation_dir / "cycle_detector_state.json"),
            "cycle_event_registry": str(simulation_dir / "cycle_event_registry.jsonl"),
            "cycle_detection_manifest": str(simulation_dir / "cycle_detection_manifest.json"),
            "cycle_detection_quality_report": str(
                simulation_dir / "cycle_detection_quality_report.jsonl"
            ),
        },
    }


def main(argv: list[str] | None = None) -> None:
    """Compatibility shim for ``python -m youtube_pipeline.cyclic_detection_connector``."""

    from .entrypoints.cyclic_detection_connector import main as entrypoint_main

    entrypoint_main(argv)


__all__ = [
    "CyclicDetectionConnectorConfig",
    "load_cyclic_detection_connector_config",
    "run_cyclic_detection_connector",
]


if __name__ == "__main__":
    main()
