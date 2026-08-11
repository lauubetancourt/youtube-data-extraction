from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ARTIFACT_VERSION = "rag_event_evidence_v1"

TRIGGER_TIME_COL = "trigger_time_utc"
WINDOW_START_COL = "window_start_utc"
WINDOW_END_COL = "window_end_utc"
EVENT_TIME_COL = "event_time_utc"

EVENT_CANDIDATES_FILE = "event_candidates.csv"
EVENT_COMMENT_MAP_FILE = "event_comment_map.csv"
EVENT_SIGNAL_SNAPSHOT_MAP_FILE = "event_signal_snapshot_map.csv"
EVENT_EVIDENCE_PACKAGES_FILE = "event_evidence_packages.jsonl"
RUN_MANIFEST_FILE = "run_manifest.json"
RAG_EVIDENCE_SUMMARY_FILE = "rag_evidence_summary.json"


@dataclass(frozen=True)
class RagEvidenceBuildConfig:
    trigger_comment_map_path: str
    output_dir: str
    comments_path: str = "data/gold/clean_comments.parquet"
    snapshots_path: str | None = None
    detector_name: str = "xiao_ema"
    detector_params: dict[str, Any] = field(default_factory=dict)
    monitoring_params: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    notes: str | None = None
    snapshot_context: str = "window"

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "RagEvidenceBuildConfig":
        missing = [
            key
            for key in ["trigger_comment_map_path", "output_dir"]
            if not payload.get(key)
        ]
        if missing:
            raise ValueError(
                "RAG evidence config missing required fields: "
                + ", ".join(missing)
            )
        detector_params = payload.get("detector_params") or {}
        monitoring_params = payload.get("monitoring_params") or {}
        if not isinstance(detector_params, dict):
            raise ValueError("detector_params must be an object.")
        if not isinstance(monitoring_params, dict):
            raise ValueError("monitoring_params must be an object.")
        return cls(
            trigger_comment_map_path=str(payload["trigger_comment_map_path"]),
            output_dir=str(payload["output_dir"]),
            comments_path=str(
                payload.get("comments_path", "data/gold/clean_comments.parquet")
            ),
            snapshots_path=(
                str(payload["snapshots_path"])
                if payload.get("snapshots_path") is not None
                else None
            ),
            detector_name=str(payload.get("detector_name", "xiao_ema")),
            detector_params=detector_params,
            monitoring_params=monitoring_params,
            run_id=payload.get("run_id"),
            notes=payload.get("notes"),
            snapshot_context=str(payload.get("snapshot_context", "window")),
        )


def _extract_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("rag_evidence")
    if nested is None:
        return payload
    if not isinstance(nested, dict):
        raise ValueError("rag_evidence config section must be an object.")
    return nested


def _merge_config_payloads(*payloads: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for payload in payloads:
        for key, value in payload.items():
            if value is None:
                continue
            if key in {"detector_params", "monitoring_params"}:
                current = merged.get(key, {})
                if not isinstance(current, dict) or not isinstance(value, dict):
                    raise ValueError(f"{key} must be an object.")
                merged[key] = {**current, **value}
            else:
                merged[key] = value
    return merged


def load_rag_evidence_config(
    path: str | Path,
    *,
    overrides: dict[str, Any] | None = None,
) -> RagEvidenceBuildConfig:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"RAG evidence config must be an object: {p}")
    base = _extract_config_payload(payload)
    merged = _merge_config_payloads(base, overrides or {})
    return RagEvidenceBuildConfig.from_mapping(merged)


def read_table(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.is_dir() or p.suffix.lower() == ".parquet":
        return pd.read_parquet(p)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    raise ValueError(f"Unsupported file format: {p}")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return Path(path).as_posix()


def _require_columns(df: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required.difference(df.columns))
    if missing:
        raise KeyError(f"{label} missing required columns: {', '.join(missing)}")


def _to_utc_timestamp(value: Any) -> pd.Timestamp:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid UTC timestamp: {value!r}")
    return pd.Timestamp(ts)


def _normalize_utc_column(df: pd.DataFrame, column: str) -> None:
    df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")
    if df[column].isna().any():
        raise ValueError(f"Column {column!r} contains invalid timestamps.")


def _isoformat(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def _unix_seconds(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(pd.Timestamp(value).timestamp())


def _event_id(
    *,
    run_id: str,
    detector_name: str,
    trigger_time: pd.Timestamp,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> str:
    payload = "|".join(
        [
            run_id,
            detector_name,
            trigger_time.isoformat(),
            window_start.isoformat(),
            window_end.isoformat(),
        ]
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"evt_{digest}"


def make_run_id(
    *,
    detector_name: str,
    trigger_comment_map_path: str | Path,
    comments_path: str | Path,
    snapshots_path: str | Path | None = None,
) -> str:
    payload = "|".join(
        value
        for value in [
            detector_name,
            _normalize_path(trigger_comment_map_path),
            _normalize_path(comments_path),
            _normalize_path(snapshots_path),
        ]
        if value
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"run_{digest}"


def prepare_trigger_comment_map(trigger_df: pd.DataFrame) -> pd.DataFrame:
    df = trigger_df.copy()
    rename_map = {
        "trigger_time": TRIGGER_TIME_COL,
        "window_start": WINDOW_START_COL,
        "window_end": WINDOW_END_COL,
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    _require_columns(
        df,
        {
            TRIGGER_TIME_COL,
            WINDOW_START_COL,
            WINDOW_END_COL,
            "trigger_volume",
            "comment_id",
            "event_time_utc",
            "video_id",
        },
        "trigger comment map",
    )
    for col in [TRIGGER_TIME_COL, WINDOW_START_COL, WINDOW_END_COL, EVENT_TIME_COL]:
        _normalize_utc_column(df, col)
    return df


def build_run_manifest(
    *,
    run_id: str,
    detector_name: str,
    detector_params: dict[str, Any] | None,
    comments_path: str | Path,
    trigger_comment_map_path: str | Path,
    output_dir: str | Path,
    snapshots_path: str | Path | None = None,
    monitoring_params: dict[str, Any] | None = None,
    notes: str | None = None,
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    source_artifacts = {
        "comments_path": _normalize_path(comments_path),
        "trigger_comment_map_path": _normalize_path(trigger_comment_map_path),
        "snapshots_path": _normalize_path(snapshots_path),
    }
    return {
        "run_id": run_id,
        "created_at_utc": created_at_utc or _utc_now_iso(),
        "pipeline_stage": "rag_evidence_assembly",
        "dataset_path": _normalize_path(comments_path),
        "snapshot_path": _normalize_path(snapshots_path),
        "detector_name": detector_name,
        "detector_params": detector_params or {},
        "monitoring_params": monitoring_params or {},
        "source_artifacts": source_artifacts,
        "output_dir": _normalize_path(output_dir),
        "artifact_version": ARTIFACT_VERSION,
        "notes": notes,
    }


def build_event_candidates(
    trigger_df: pd.DataFrame,
    *,
    run_id: str,
    detector_name: str,
) -> pd.DataFrame:
    df = prepare_trigger_comment_map(trigger_df)
    event_cols = [
        TRIGGER_TIME_COL,
        WINDOW_START_COL,
        WINDOW_END_COL,
        "trigger_volume",
    ]
    if "trigger_strength" in df.columns:
        event_cols.append("trigger_strength")

    events = df[event_cols].drop_duplicates().sort_values(
        [TRIGGER_TIME_COL, WINDOW_START_COL, WINDOW_END_COL]
    )
    rows: list[dict[str, Any]] = []
    for _, event in events.iterrows():
        trigger_time = _to_utc_timestamp(event[TRIGGER_TIME_COL])
        window_start = _to_utc_timestamp(event[WINDOW_START_COL])
        window_end = _to_utc_timestamp(event[WINDOW_END_COL])
        event_id = _event_id(
            run_id=run_id,
            detector_name=detector_name,
            trigger_time=trigger_time,
            window_start=window_start,
            window_end=window_end,
        )
        rows.append(
            {
                "event_id": event_id,
                "run_id": run_id,
                "detector_name": detector_name,
                TRIGGER_TIME_COL: trigger_time,
                "trigger_time_unix_s": _unix_seconds(trigger_time),
                WINDOW_START_COL: window_start,
                WINDOW_END_COL: window_end,
                "trigger_volume": int(event["trigger_volume"]),
                "trigger_strength": (
                    float(event["trigger_strength"])
                    if "trigger_strength" in event and pd.notna(event["trigger_strength"])
                    else pd.NA
                ),
                "decision_level": "candidate",
                "comment_count": pd.NA,
                "unique_video_count": pd.NA,
                "unique_author_count": pd.NA,
                "event_artifact_version": ARTIFACT_VERSION,
            }
        )
    return pd.DataFrame(rows)


def _video_metadata_from_trigger_map(trigger_df: pd.DataFrame) -> pd.DataFrame:
    candidates = [col for col in ["video_id", "title", "channel_title"] if col in trigger_df.columns]
    if "video_id" not in candidates:
        return pd.DataFrame(columns=["video_id", "title", "channel_title"])
    metadata = trigger_df[candidates].drop_duplicates(subset=["video_id"])
    if "title" not in metadata.columns:
        metadata["title"] = pd.NA
    if "channel_title" not in metadata.columns:
        metadata["channel_title"] = pd.NA
    return metadata[["video_id", "title", "channel_title"]]


def build_event_comment_map(
    *,
    comments_df: pd.DataFrame,
    trigger_df: pd.DataFrame,
    event_candidates: pd.DataFrame,
    run_id: str,
    comment_source_path: str | Path,
) -> pd.DataFrame:
    comments = comments_df.copy()
    trigger_map = prepare_trigger_comment_map(trigger_df)
    _require_columns(comments, {EVENT_TIME_COL, "video_id", "comment_id", "text"}, "comments")
    _normalize_utc_column(comments, EVENT_TIME_COL)

    video_metadata = _video_metadata_from_trigger_map(trigger_map)
    rows: list[pd.DataFrame] = []

    for _, event in event_candidates.iterrows():
        window_start = _to_utc_timestamp(event[WINDOW_START_COL])
        window_end = _to_utc_timestamp(event[WINDOW_END_COL])
        mask = (comments[EVENT_TIME_COL] >= window_start) & (
            comments[EVENT_TIME_COL] <= window_end
        )
        selected = comments.loc[mask].copy()
        if selected.empty:
            continue

        selected = selected.drop_duplicates(subset=["comment_id"])
        selected = selected.sort_values([EVENT_TIME_COL, "video_id", "comment_id"])
        selected.insert(0, "order_in_event", range(1, len(selected) + 1))
        selected.insert(0, "run_id", run_id)
        selected.insert(0, "event_id", event["event_id"])
        selected[TRIGGER_TIME_COL] = event[TRIGGER_TIME_COL]
        selected[WINDOW_START_COL] = window_start
        selected[WINDOW_END_COL] = window_end
        selected["event_time_unix_s"] = selected[EVENT_TIME_COL].map(_unix_seconds)
        selected["comment_source_path"] = _normalize_path(comment_source_path)

        selected = selected.merge(video_metadata, on="video_id", how="left", suffixes=("", "_from_map"))
        rows.append(selected)

    if not rows:
        return pd.DataFrame(
            columns=[
                "event_id",
                "run_id",
                "order_in_event",
                TRIGGER_TIME_COL,
                WINDOW_START_COL,
                WINDOW_END_COL,
                EVENT_TIME_COL,
                "event_time_unix_s",
                "video_id",
                "title",
                "channel_title",
                "comment_id",
                "author_id",
                "text",
                "text_clean",
                "is_reply",
                "reply_to_comment_id",
                "comment_source_path",
            ]
        )

    out = pd.concat(rows, ignore_index=True)
    field_order = [
        "event_id",
        "run_id",
        "order_in_event",
        TRIGGER_TIME_COL,
        WINDOW_START_COL,
        WINDOW_END_COL,
        EVENT_TIME_COL,
        "event_time_unix_s",
        "video_id",
        "title",
        "channel_title",
        "comment_id",
        "author_id",
        "text",
        "text_clean",
        "is_reply",
        "reply_to_comment_id",
        "likes",
        "emoji_count",
        "exclamation_count",
        "question_count",
        "caps_ratio",
        "link_count",
        "token_count",
        "is_probable_spam",
        "comment_source_path",
    ]
    for col in field_order:
        if col not in out.columns:
            out[col] = pd.NA
    return out[field_order]


def enrich_event_candidate_counts(
    event_candidates: pd.DataFrame, event_comment_map: pd.DataFrame
) -> pd.DataFrame:
    events = event_candidates.copy()
    if event_comment_map.empty:
        events["comment_count"] = 0
        events["unique_video_count"] = 0
        events["unique_author_count"] = 0
        return events

    counts = event_comment_map.groupby("event_id").agg(
        comment_count=("comment_id", "nunique"),
        unique_video_count=("video_id", "nunique"),
        unique_author_count=("author_id", "nunique"),
    )
    events = events.drop(
        columns=["comment_count", "unique_video_count", "unique_author_count"],
        errors="ignore",
    ).merge(counts, on="event_id", how="left")
    for col in ["comment_count", "unique_video_count", "unique_author_count"]:
        events[col] = events[col].fillna(0).astype(int)
    return events


def build_event_signal_snapshot_map(
    *,
    snapshots_df: pd.DataFrame | None,
    event_candidates: pd.DataFrame,
    run_id: str,
    snapshot_path: str | Path | None,
    snapshot_context: str = "window",
) -> pd.DataFrame:
    empty_cols = [
        "event_id",
        "run_id",
        "snapshot_path",
        "snapshot_order_in_event",
        "snapshot_window_start_utc",
        "snapshot_window_end_utc",
        "signal_role",
    ]
    if snapshots_df is None or snapshot_context == "none":
        return pd.DataFrame(columns=empty_cols)
    if snapshot_context not in {"window", "anchor"}:
        raise ValueError("snapshot_context must be one of: window, anchor, none.")

    snapshots = snapshots_df.copy()
    _require_columns(snapshots, {"window_start", "window_end"}, "snapshots")
    _normalize_utc_column(snapshots, "window_start")
    _normalize_utc_column(snapshots, "window_end")

    signal_cols = [
        col
        for col in snapshots.columns
        if col == "size" or col.startswith("activity.") or col.startswith("polarization.")
    ]
    rows: list[pd.DataFrame] = []
    for _, event in event_candidates.iterrows():
        window_start = _to_utc_timestamp(event[WINDOW_START_COL])
        window_end = _to_utc_timestamp(event[WINDOW_END_COL])
        trigger_time = _to_utc_timestamp(event[TRIGGER_TIME_COL])

        if snapshot_context == "window":
            selected = snapshots.loc[
                (snapshots["window_end"] >= window_start)
                & (snapshots["window_end"] <= window_end)
            ].copy()
            signal_role = "evidence_window"
        else:
            exact = snapshots.loc[snapshots["window_end"] == trigger_time].copy()
            selected = exact
            if selected.empty:
                selected = snapshots.loc[snapshots["window_end"] > trigger_time].head(1).copy()
            signal_role = "trigger_anchor"

        if selected.empty:
            continue

        selected = selected.sort_values(["window_end", "window_start"])
        selected.insert(0, "snapshot_order_in_event", range(1, len(selected) + 1))
        selected.insert(0, "run_id", run_id)
        selected.insert(0, "event_id", event["event_id"])
        selected["snapshot_path"] = _normalize_path(snapshot_path)
        selected["signal_role"] = signal_role
        selected = selected.rename(
            columns={
                "window_start": "snapshot_window_start_utc",
                "window_end": "snapshot_window_end_utc",
            }
        )
        rows.append(
            selected[
                [
                    "event_id",
                    "run_id",
                    "snapshot_path",
                    "snapshot_order_in_event",
                    "snapshot_window_start_utc",
                    "snapshot_window_end_utc",
                    *signal_cols,
                    "signal_role",
                ]
            ]
        )

    if not rows:
        return pd.DataFrame(columns=empty_cols)
    return pd.concat(rows, ignore_index=True)


def build_event_evidence_packages(
    *,
    event_candidates: pd.DataFrame,
    event_comment_map: pd.DataFrame,
    event_signal_snapshot_map: pd.DataFrame,
    run_id: str,
    comments_path: str | Path,
    output_paths: dict[str, str],
    snapshots_path: str | Path | None = None,
    package_created_at_utc: str | None = None,
) -> list[dict[str, Any]]:
    created_at = package_created_at_utc or _utc_now_iso()
    comment_counts = (
        event_comment_map.groupby("event_id")["comment_id"].nunique().to_dict()
        if not event_comment_map.empty
        else {}
    )
    signal_counts = (
        event_signal_snapshot_map.groupby("event_id").size().to_dict()
        if not event_signal_snapshot_map.empty
        else {}
    )
    packages: list[dict[str, Any]] = []
    for _, event in event_candidates.iterrows():
        event_id = event["event_id"]
        comment_count = int(comment_counts.get(event_id, 0))
        signal_count = int(signal_counts.get(event_id, 0))
        missing: list[str] = []
        if comment_count == 0:
            missing.append("comments")
        if snapshots_path is not None and signal_count == 0:
            missing.append("signals")
        status = "ready" if not missing else "missing_" + "_and_".join(missing)
        packages.append(
            {
                "event_id": event_id,
                "run_id": run_id,
                TRIGGER_TIME_COL: _isoformat(event[TRIGGER_TIME_COL]),
                WINDOW_START_COL: _isoformat(event[WINDOW_START_COL]),
                WINDOW_END_COL: _isoformat(event[WINDOW_END_COL]),
                "event_candidate_path": output_paths.get("event_candidates"),
                "event_signal_snapshot_map_path": output_paths.get(
                    "event_signal_snapshot_map"
                ),
                "event_comment_map_path": output_paths.get("event_comment_map"),
                "source_dataset_path": _normalize_path(comments_path),
                "snapshot_path": _normalize_path(snapshots_path),
                "package_created_at_utc": created_at,
                "package_artifact_version": ARTIFACT_VERSION,
                "rag_readiness_status": status,
                "comment_count": comment_count,
                "signal_snapshot_count": signal_count,
            }
        )
    return packages


def _format_timestamp_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].map(_isoformat)
    return out


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(_json_safe(record), ensure_ascii=False) for record in records]
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_rag_evidence_artifacts(
    *,
    comments_path: str | Path,
    trigger_comment_map_path: str | Path,
    output_dir: str | Path,
    snapshots_path: str | Path | None = None,
    detector_name: str = "xiao_ema",
    detector_params: dict[str, Any] | None = None,
    monitoring_params: dict[str, Any] | None = None,
    run_id: str | None = None,
    notes: str | None = None,
    snapshot_context: str = "window",
) -> dict[str, Any]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    resolved_run_id = run_id or make_run_id(
        detector_name=detector_name,
        trigger_comment_map_path=trigger_comment_map_path,
        comments_path=comments_path,
        snapshots_path=snapshots_path,
    )
    created_at = _utc_now_iso()
    comments_df = read_table(comments_path)
    trigger_df = read_table(trigger_comment_map_path)
    snapshots_df = read_table(snapshots_path) if snapshots_path else None

    manifest = build_run_manifest(
        run_id=resolved_run_id,
        detector_name=detector_name,
        detector_params=detector_params,
        comments_path=comments_path,
        trigger_comment_map_path=trigger_comment_map_path,
        snapshots_path=snapshots_path,
        output_dir=output_root,
        monitoring_params=monitoring_params,
        notes=notes,
        created_at_utc=created_at,
    )
    event_candidates = build_event_candidates(
        trigger_df,
        run_id=resolved_run_id,
        detector_name=detector_name,
    )
    event_comment_map = build_event_comment_map(
        comments_df=comments_df,
        trigger_df=trigger_df,
        event_candidates=event_candidates,
        run_id=resolved_run_id,
        comment_source_path=comments_path,
    )
    event_candidates = enrich_event_candidate_counts(event_candidates, event_comment_map)
    event_signal_snapshot_map = build_event_signal_snapshot_map(
        snapshots_df=snapshots_df,
        event_candidates=event_candidates,
        run_id=resolved_run_id,
        snapshot_path=snapshots_path,
        snapshot_context=snapshot_context,
    )

    output_paths = {
        "run_manifest": (output_root / RUN_MANIFEST_FILE).as_posix(),
        "event_candidates": (output_root / EVENT_CANDIDATES_FILE).as_posix(),
        "event_comment_map": (output_root / EVENT_COMMENT_MAP_FILE).as_posix(),
        "event_signal_snapshot_map": (
            output_root / EVENT_SIGNAL_SNAPSHOT_MAP_FILE
        ).as_posix(),
        "event_evidence_packages": (
            output_root / EVENT_EVIDENCE_PACKAGES_FILE
        ).as_posix(),
        "summary": (output_root / RAG_EVIDENCE_SUMMARY_FILE).as_posix(),
    }
    packages = build_event_evidence_packages(
        event_candidates=event_candidates,
        event_comment_map=event_comment_map,
        event_signal_snapshot_map=event_signal_snapshot_map,
        run_id=resolved_run_id,
        comments_path=comments_path,
        snapshots_path=snapshots_path,
        output_paths=output_paths,
        package_created_at_utc=created_at,
    )

    write_json(output_paths["run_manifest"], manifest)
    _format_timestamp_columns(
        event_candidates,
        [TRIGGER_TIME_COL, WINDOW_START_COL, WINDOW_END_COL],
    ).to_csv(output_paths["event_candidates"], index=False)
    _format_timestamp_columns(
        event_comment_map,
        [TRIGGER_TIME_COL, WINDOW_START_COL, WINDOW_END_COL, EVENT_TIME_COL],
    ).to_csv(output_paths["event_comment_map"], index=False)
    _format_timestamp_columns(
        event_signal_snapshot_map,
        ["snapshot_window_start_utc", "snapshot_window_end_utc"],
    ).to_csv(output_paths["event_signal_snapshot_map"], index=False)
    write_jsonl(output_paths["event_evidence_packages"], packages)

    summary = {
        "run_id": resolved_run_id,
        "artifact_version": ARTIFACT_VERSION,
        "output_paths": output_paths,
        "event_count": int(len(event_candidates)),
        "event_comment_rows": int(len(event_comment_map)),
        "event_signal_snapshot_rows": int(len(event_signal_snapshot_map)),
        "ready_packages": int(
            sum(1 for item in packages if item["rag_readiness_status"] == "ready")
        ),
    }
    write_json(output_paths["summary"], summary)
    return summary


def write_rag_evidence_artifacts_from_config(
    config: RagEvidenceBuildConfig,
) -> dict[str, Any]:
    return write_rag_evidence_artifacts(
        comments_path=config.comments_path,
        trigger_comment_map_path=config.trigger_comment_map_path,
        snapshots_path=config.snapshots_path,
        output_dir=config.output_dir,
        detector_name=config.detector_name,
        detector_params=config.detector_params,
        monitoring_params=config.monitoring_params,
        run_id=config.run_id,
        notes=config.notes,
        snapshot_context=config.snapshot_context,
    )


__all__ = [
    "ARTIFACT_VERSION",
    "RAG_EVIDENCE_SUMMARY_FILE",
    "RagEvidenceBuildConfig",
    "build_event_candidates",
    "build_event_comment_map",
    "build_event_evidence_packages",
    "build_event_signal_snapshot_map",
    "build_run_manifest",
    "enrich_event_candidate_counts",
    "load_rag_evidence_config",
    "make_run_id",
    "prepare_trigger_comment_map",
    "read_table",
    "write_rag_evidence_artifacts",
    "write_rag_evidence_artifacts_from_config",
]
