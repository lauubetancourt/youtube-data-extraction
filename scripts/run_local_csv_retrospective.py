#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from youtube_pipeline import (  # noqa: E402
    DEFAULT_DETECTOR,
    build_event_time_window_stream,
    clean_comments_dataframe,
    create_detector,
    persist_batch_snapshot,
    read_dataset_for_playback,
    replay_events,
)
from youtube_pipeline.run_pipeline import (  # noqa: E402
    DEFAULT_TRIGGER_COOLDOWN,
    DEFAULT_TRIGGER_MIN_VOLUME,
    DEFAULT_TRIGGER_SLOW_WINDOW,
    DEFAULT_TRIGGER_SLIDE_INTERVAL,
    DEFAULT_TRIGGER_THRESHOLD,
DEFAULT_TRIGGER_WINDOW_SIZE,
)
from youtube_pipeline.stream_runtime import Stream  # noqa: E402


RUN_NAME = "local_csv_retrospective"
TS_COL = "event_time_utc"
RAW_TEXT_COL = "text"
HISTORICAL_RETROSPECTIVE_MIN_VOLUME = 15


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stamp() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def bool_series(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y", "si", "sí"})


def parse_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.replace("", pd.NA), utc=True, errors="coerce")


def unix_seconds(ts: pd.Series) -> pd.Series:
    return ts.map(lambda value: int(pd.Timestamp(value).timestamp())).astype("int64")


def normalize_sentiment_value(value: Any) -> tuple[str | None, float | None]:
    raw = str(value).strip()
    if not raw:
        return None, None
    normalized = raw.lower()
    mapping = {
        "negative": ("negative", -1.0),
        "negativo": ("negative", -1.0),
        "1": ("negative", -1.0),
        "1.0": ("negative", -1.0),
        "neutral": ("neutral", 0.0),
        "2": ("neutral", 0.0),
        "2.0": ("neutral", 0.0),
        "positive": ("positive", 1.0),
        "positivo": ("positive", 1.0),
        "3": ("positive", 1.0),
        "3.0": ("positive", 1.0),
    }
    if normalized in mapping:
        return mapping[normalized]
    numeric = pd.to_numeric(raw, errors="coerce")
    if pd.notna(numeric):
        return raw, float(numeric)
    return raw, None


def audit_inputs(videos: pd.DataFrame, comments: pd.DataFrame) -> dict[str, Any]:
    comment_ts = parse_utc(comments["published_at"])
    video_ids = set(videos["video_id"].astype(str)) if "video_id" in videos else set()
    comment_video_id = comments["video_id"].astype(str)
    comment_id = comments["comment_id"].astype(str)
    duplicate_rows = comments.loc[
        comment_id.ne("") & comment_id.duplicated(keep=False)
    ].copy()

    duplicate_groups: list[dict[str, Any]] = []
    non_exact_duplicate_ids: list[str] = []
    if not duplicate_rows.empty:
        for cid, group in duplicate_rows.groupby("comment_id", sort=False):
            unique_full_rows = len(group.drop_duplicates())
            duplicate_groups.append(
                {
                    "comment_id": cid,
                    "rows": int(len(group)),
                    "unique_full_rows": int(unique_full_rows),
                }
            )
            if unique_full_rows > 1:
                non_exact_duplicate_ids.append(str(cid))

    meta_cols = [
        col
        for col in ["video_id", "title", "publishedAt", "published_at", "channel_id", "channel_title"]
        if col in videos.columns
    ]
    video_missing_by_column = {
        col: int(videos[col].astype(str).eq("").sum()) for col in meta_cols
    }
    video_rows_missing_any_key_metadata = (
        int(videos[meta_cols].astype(str).eq("").any(axis=1).sum()) if meta_cols else 0
    )
    unknown_mask = ~comment_video_id.isin(video_ids) & comment_video_id.ne("")
    is_reply = bool_series(comments["is_reply"]) if "is_reply" in comments else pd.Series(False, index=comments.index)
    missing_published = comments["published_at"].astype(str).eq("")
    invalid_published = comment_ts.isna() & ~missing_published

    return {
        "videos_rows": int(len(videos)),
        "comments_rows": int(len(comments)),
        "videos_columns": list(videos.columns),
        "comments_columns": list(comments.columns),
        "comment_time_min_utc": (
            None if comment_ts.dropna().empty else comment_ts.min().isoformat()
        ),
        "comment_time_max_utc": (
            None if comment_ts.dropna().empty else comment_ts.max().isoformat()
        ),
        "comments_without_comment_id": int(comment_id.eq("").sum()),
        "comments_without_video_id": int(comment_video_id.eq("").sum()),
        "comments_without_published_at": int(missing_published.sum()),
        "comments_with_invalid_published_at": int(invalid_published.sum()),
        "duplicate_comment_id_rows_nonblank": int(len(duplicate_rows)),
        "duplicate_comment_id_groups": duplicate_groups,
        "non_exact_duplicate_comment_ids": non_exact_duplicate_ids,
        "video_rows_missing_any_key_metadata": video_rows_missing_any_key_metadata,
        "video_missing_by_column": video_missing_by_column,
        "comments_with_unknown_video_id": int(unknown_mask.sum()),
        "unknown_video_id_sample": sorted(set(comment_video_id.loc[unknown_mask].head(20).tolist())),
        "sentiment_distribution": (
            comments["sentiment"].replace("", "<blank>").value_counts(dropna=False).to_dict()
            if "sentiment" in comments.columns
            else {}
        ),
        "classification_distribution": (
            comments["classification"].replace("", "<blank>").value_counts(dropna=False).to_dict()
            if "classification" in comments.columns
            else {}
        ),
        "reply_count": int(is_reply.sum()),
        "critical_issues": [],
    }


def critical_issues_from_audit(audit: dict[str, Any]) -> list[str]:
    checks = {
        "comments_without_comment_id": "Hay comentarios sin comment_id.",
        "comments_without_video_id": "Hay comentarios sin video_id.",
        "comments_without_published_at": "Hay comentarios sin published_at.",
        "comments_with_invalid_published_at": "Hay comentarios con published_at invalido.",
        "comments_with_unknown_video_id": "Hay comentarios cuyo video_id no existe en videos.csv.",
    }
    issues = [message for key, message in checks.items() if audit.get(key, 0)]
    if audit.get("non_exact_duplicate_comment_ids"):
        issues.append(
            "Hay comment_id duplicados con filas no identicas; no se puede resolver sin decision metodologica."
        )
    return issues


def audit_markdown(audit: dict[str, Any], videos_path: Path, comments_path: Path) -> str:
    lines = [
        "# Auditoria de entrada CSV",
        "",
        f"- videos.csv: `{videos_path.as_posix()}`",
        f"- comments.csv: `{comments_path.as_posix()}`",
        f"- Videos: {audit['videos_rows']}",
        f"- Comentarios: {audit['comments_rows']}",
        f"- Rango temporal comentarios: {audit['comment_time_min_utc']} a {audit['comment_time_max_utc']}",
        f"- Comentarios sin comment_id: {audit['comments_without_comment_id']}",
        f"- Comentarios sin video_id: {audit['comments_without_video_id']}",
        f"- Comentarios sin published_at: {audit['comments_without_published_at']}",
        f"- Comentarios con published_at invalido: {audit['comments_with_invalid_published_at']}",
        f"- Filas con comment_id duplicado: {audit['duplicate_comment_id_rows_nonblank']}",
        f"- Videos con metadatos clave faltantes: {audit['video_rows_missing_any_key_metadata']}",
        f"- Comentarios con video_id inexistente: {audit['comments_with_unknown_video_id']}",
        f"- Replies: {audit['reply_count']}",
        "",
        "## Distribucion de sentiment",
        "",
    ]
    for key, value in audit["sentiment_distribution"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Distribucion de classification", ""])
    for key, value in audit["classification_distribution"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Duplicados", ""])
    if not audit["duplicate_comment_id_groups"]:
        lines.append("- No se encontraron duplicados por comment_id.")
    else:
        for group in audit["duplicate_comment_id_groups"]:
            lines.append(
                "- "
                f"{group['comment_id']}: rows={group['rows']}, "
                f"unique_full_rows={group['unique_full_rows']}"
            )
    lines.extend(["", "## Problemas criticos", ""])
    if not audit["critical_issues"]:
        lines.append("- No se encontraron problemas criticos para bloquear la corrida.")
    else:
        for issue in audit["critical_issues"]:
            lines.append(f"- {issue}")
    return "\n".join(lines) + "\n"


def normalize_inputs(videos: pd.DataFrame, comments: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    videos_norm = videos.copy()
    comments_norm = comments.copy()

    if "publishedAt" not in videos_norm.columns and "published_at" in videos_norm.columns:
        videos_norm["publishedAt"] = videos_norm["published_at"]
    if "published_at" not in videos_norm.columns and "publishedAt" in videos_norm.columns:
        videos_norm["published_at"] = videos_norm["publishedAt"]
    if "url" not in videos_norm.columns and "video_url" in videos_norm.columns:
        videos_norm["url"] = videos_norm["video_url"]
    if "duration" not in videos_norm.columns and "duration_seconds" in videos_norm.columns:
        videos_norm["duration"] = videos_norm["duration_seconds"]
    if "country" not in videos_norm.columns and "channel_country" in videos_norm.columns:
        videos_norm["country"] = videos_norm["channel_country"]

    before_rows = len(comments_norm)
    comments_norm = comments_norm.drop_duplicates(keep="first").copy()
    exact_duplicate_rows_removed = before_rows - len(comments_norm)

    comments_norm["is_reply"] = bool_series(comments_norm["is_reply"])
    comments_norm["reply_to_comment_id"] = comments_norm["reply_to_comment_id"].replace("", pd.NA)
    comments_norm["published_at"] = parse_utc(comments_norm["published_at"]).dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    comments_norm["published_at"] = comments_norm["published_at"].str.replace(r"(\+0000)$", "+00:00", regex=True)

    sentiment_pairs = comments_norm["sentiment"].map(normalize_sentiment_value)
    comments_norm["sentiment_label"] = sentiment_pairs.map(lambda pair: pair[0])
    comments_norm["sentiment_score"] = sentiment_pairs.map(lambda pair: pair[1]).astype("Float64")
    comments_norm["sentiment_Bert"] = comments_norm["sentiment"]
    comments_norm["classification_num"] = pd.to_numeric(
        comments_norm.get("classification", pd.Series(pd.NA, index=comments_norm.index)),
        errors="coerce",
    ).astype("Float64")

    video_meta_cols = [
        col
        for col in ["video_id", "title", "channel_title", "publishedAt", "channel_id"]
        if col in videos_norm.columns
    ]
    video_meta = videos_norm[video_meta_cols].drop_duplicates(subset=["video_id"])
    video_meta = video_meta.rename(
        columns={
            "publishedAt": "video_published_at",
            "channel_id": "video_channel_id",
        }
    )
    comments_norm = comments_norm.merge(video_meta, on="video_id", how="left")

    info = {
        "exact_duplicate_rows_removed": int(exact_duplicate_rows_removed),
        "sentiment_mapping": {
            "1/1.0/Negative": -1.0,
            "2/2.0/Neutral": 0.0,
            "3/3.0/Positive": 1.0,
        },
        "video_metadata_joined_to_comments": True,
    }
    return videos_norm, comments_norm, info


def run_cleaning(comments_parquet: str, output_path: Path) -> tuple[Path, dict[str, Any]]:
    comments_df = pd.read_parquet(comments_parquet)
    clean_df = clean_comments_dataframe(
        comments_df,
        raw_text_col=RAW_TEXT_COL,
        timestamp_col="published_at",
        keep_spam=False,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_parquet(output_path, index=False)
    info = {
        "input_rows": int(len(comments_df)),
        "output_rows": int(len(clean_df)),
        "removed_rows": int(len(comments_df) - len(clean_df)),
        "columns": list(clean_df.columns),
        "comment_id_preserved": "comment_id" in clean_df.columns,
        "video_id_preserved": "video_id" in clean_df.columns,
        "event_time_utc_preserved": "event_time_utc" in clean_df.columns,
        "text_clean_generated": "text_clean" in clean_df.columns,
        "sentiment_score_available": "sentiment_score" in clean_df.columns,
        "reply_metadata_preserved": all(
            col in clean_df.columns for col in ["is_reply", "reply_to_comment_id"]
        ),
    }
    return output_path, info


def build_trigger_comment_map(
    *,
    clean_df: pd.DataFrame,
    triggers: list[dict[str, Any]],
    window_size: str,
) -> pd.DataFrame:
    window_td = pd.to_timedelta(window_size)
    rows: list[dict[str, Any]] = []
    comments = clean_df.copy()
    comments[TS_COL] = pd.to_datetime(comments[TS_COL], utc=True, errors="coerce")
    comments = comments.loc[comments[TS_COL].notna()].sort_values(TS_COL)

    for trigger in triggers:
        trigger_time = pd.Timestamp(trigger["trigger_time"])
        window_start = trigger_time - window_td
        window_end = trigger_time
        in_window = comments.loc[
            (comments[TS_COL] >= window_start) & (comments[TS_COL] <= window_end)
        ].copy()
        in_window = in_window.sort_values([TS_COL, "video_id", "comment_id"])
        for order, (_, row) in enumerate(in_window.iterrows(), start=1):
            rows.append(
                {
                    "trigger_time": trigger_time,
                    "window_start": window_start,
                    "window_end": window_end,
                    "trigger_volume": int(trigger["volume"]),
                    "trigger_strength": round(float(trigger["strength"]), 4),
                    "order_in_trigger": order,
                    "event_time_utc": row[TS_COL],
                    "video_id": row.get("video_id"),
                    "title": row.get("title"),
                    "channel_title": row.get("channel_title"),
                    "author_id": row.get("author_id"),
                    "comment_id": row.get("comment_id"),
                    "text": row.get("text"),
                    "text_clean": row.get("text_clean"),
                    "is_reply": row.get("is_reply"),
                    "reply_to_comment_id": row.get("reply_to_comment_id"),
                }
            )
    return pd.DataFrame(rows)


def run_retrospective_playback(
    *,
    clean_path: Path,
    snapshots_path: Path,
    trigger_comment_map_path: Path,
    trigger_log_path: Path,
    summary_path: Path,
    run_stdout_path: Path,
    trigger_min_volume: int,
) -> dict[str, Any]:
    events = read_dataset_for_playback(clean_path, ts_col=TS_COL)
    source = Stream()
    snapshots: list[dict[str, Any]] = []
    trigger_logs: list[str] = []
    detector_params = {
        "ts_col": TS_COL,
        "window_size": DEFAULT_TRIGGER_WINDOW_SIZE,
        "slide_interval": DEFAULT_TRIGGER_SLIDE_INTERVAL,
        "slow_window": DEFAULT_TRIGGER_SLOW_WINDOW,
        "sensitivity_threshold": DEFAULT_TRIGGER_THRESHOLD,
        "v_min": trigger_min_volume,
        "cooldown": DEFAULT_TRIGGER_COOLDOWN,
        "log_fn": trigger_logs.append,
    }
    detector = create_detector(DEFAULT_DETECTOR, **detector_params)

    build_event_time_window_stream(
        source,
        window_size="20min",
        ts_col=TS_COL,
    ).sink(snapshots.append)

    run_stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with run_stdout_path.open("w", encoding="utf-8") as stdout_handle:
        with redirect_stdout(stdout_handle):
            replay_events(
                source=source,
                events_df=events,
                ts_col=TS_COL,
                speed=1_000_000.0,
                max_sleep_seconds=0.0,
                event_hooks=[detector.on_event],
            )

    snapshots_df = pd.json_normalize(snapshots, sep=".")
    snapshots_path.parent.mkdir(parents=True, exist_ok=True)
    snapshots_df.to_csv(snapshots_path, index=False)

    clean_df = pd.read_parquet(clean_path)
    trigger_comment_df = build_trigger_comment_map(
        clean_df=clean_df,
        triggers=detector.completed_triggers,
        window_size=DEFAULT_TRIGGER_WINDOW_SIZE,
    )
    trigger_comment_map_path.parent.mkdir(parents=True, exist_ok=True)
    trigger_comment_df.to_csv(trigger_comment_map_path, index=False)

    first_event = None if events.empty else pd.Timestamp(events[TS_COL].min()).isoformat()
    last_event = None if events.empty else pd.Timestamp(events[TS_COL].max()).isoformat()
    trigger_lines = [
        f"Trigger log generated by {Path(__file__).as_posix()}",
        "simulation_mode: retrospective_replay",
        f"Detector: {DEFAULT_DETECTOR}",
        f"ts_col: {TS_COL}",
        f"snapshot_window_size: 20min",
        f"window_size: {DEFAULT_TRIGGER_WINDOW_SIZE}",
        f"slide_interval: {DEFAULT_TRIGGER_SLIDE_INTERVAL}",
        f"slow_window: {DEFAULT_TRIGGER_SLOW_WINDOW}",
        f"sensitivity_threshold: {DEFAULT_TRIGGER_THRESHOLD}",
        f"v_min: {trigger_min_volume}",
        f"cooldown: {DEFAULT_TRIGGER_COOLDOWN}",
        f"events: {len(events)}",
        f"snapshots: {len(snapshots_df)}",
        f"first_event_utc: {first_event}",
        f"last_event_utc: {last_event}",
        f"triggers: {len(detector.completed_triggers)}",
        "",
        *trigger_logs,
    ]
    write_text(trigger_log_path, "\n".join(trigger_lines).rstrip() + "\n")

    summary_lines = [
        "# Retrospective Replay Summary",
        "",
        f"- simulation_mode: retrospective_replay",
        f"- detector: {DEFAULT_DETECTOR}",
        f"- events_replayed: {len(events)}",
        f"- snapshots: {len(snapshots_df)}",
        f"- triggers: {len(detector.completed_triggers)}",
        f"- trigger_comment_rows: {len(trigger_comment_df)}",
        f"- first_event_utc: {first_event}",
        f"- last_event_utc: {last_event}",
        f"- snapshots_path: `{snapshots_path.as_posix()}`",
        f"- trigger_comment_map_path: `{trigger_comment_map_path.as_posix()}`",
        f"- trigger_log_path: `{trigger_log_path.as_posix()}`",
        "",
    ]
    for idx, trigger in enumerate(detector.completed_triggers, start=1):
        trigger_time = pd.Timestamp(trigger["trigger_time"])
        count = int(
            (trigger_comment_df["trigger_time"].astype(str) == str(trigger_time)).sum()
        ) if not trigger_comment_df.empty else 0
        summary_lines.append(
            f"## Trigger {idx}: {trigger_time.isoformat()}\n"
            f"- volume: {int(trigger['volume'])}\n"
            f"- strength: {float(trigger['strength']):.4f}\n"
            f"- trigger_comment_rows: {count}\n"
        )
    write_text(summary_path, "\n".join(summary_lines).rstrip() + "\n")

    return {
        "events_replayed": int(len(events)),
        "snapshots": int(len(snapshots_df)),
        "triggers": int(len(detector.completed_triggers)),
        "trigger_comment_rows": int(len(trigger_comment_df)),
        "detector_name": DEFAULT_DETECTOR,
        "detector_params": {
            "window_size": DEFAULT_TRIGGER_WINDOW_SIZE,
            "slide_interval": DEFAULT_TRIGGER_SLIDE_INTERVAL,
            "slow_window": DEFAULT_TRIGGER_SLOW_WINDOW,
            "sensitivity_threshold": DEFAULT_TRIGGER_THRESHOLD,
            "v_min": trigger_min_volume,
            "cooldown": DEFAULT_TRIGGER_COOLDOWN,
        },
        "monitoring_params": {"window_size": "20min"},
    }


def env_file_has_key(key: str) -> bool:
    if os.environ.get(key):
        return True
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == key and value.strip().strip("'\""):
            return True
    return False


def build_manifest(
    *,
    args: argparse.Namespace,
    run_dir: Path,
    audit: dict[str, Any],
    normalization: dict[str, Any],
    storage: dict[str, Any],
    cleaning: dict[str, Any],
    replay: dict[str, Any],
    generated_paths: dict[str, str],
) -> dict[str, Any]:
    return {
        "run_name": RUN_NAME,
        "run_id": run_dir.name,
        "created_at_utc": utc_now().isoformat(),
        "simulation_mode": "retrospective_replay",
        "source_mode": "local_csv_only",
        "youtube_api_called": False,
        "cyclic_ingestion_simulation_used": False,
        "daily_rag_used": False,
        "restricted_components_modified": False,
        "input_paths": {
            "videos_csv": str(Path(args.videos_path)),
            "comments_csv": str(Path(args.comments_path)),
        },
        "audit": audit,
        "normalization": normalization,
        "storage": storage,
        "cleaning": cleaning,
        "replay": replay,
        "retrospective_profile": {
            "name": args.retrospective_profile,
            "trigger_min_volume": args.trigger_min_volume,
            "historical_reference": (
                "experiments/xiao/media/log_3/trigger_log.txt"
                if args.retrospective_profile == "historical_media_log_3"
                else None
            ),
            "current_run_pipeline_default_trigger_min_volume": DEFAULT_TRIGGER_MIN_VOLUME,
        },
        "rag_credentials_available": {
            "OPENAI_API_KEY": env_file_has_key("OPENAI_API_KEY"),
            "SERPER_API_KEY": env_file_has_key("SERPER_API_KEY"),
        },
        "generated_paths": generated_paths,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a non-invasive retrospective replay from local videos.csv and comments.csv."
        )
    )
    parser.add_argument("--videos-path", default="data/caso-uribe/videos.csv")
    parser.add_argument("--comments-path", default="data/caso-uribe/comments.csv")
    parser.add_argument(
        "--run-dir",
        default=None,
        help=(
            "Output directory. Defaults to experiments/xiao/local_csv_retrospective_run/run_<UTC>."
        ),
    )
    parser.add_argument(
        "--stop-after-audit",
        action="store_true",
        help="Write audit artifacts and stop before normalization/execution.",
    )
    parser.add_argument(
        "--retrospective-profile",
        choices=["historical_media_log_3", "current_run_pipeline_default"],
        default="historical_media_log_3",
        help=(
            "Retrospective detector preset. The historical profile matches the "
            "previous stabilized RAG run in experiments/xiao/media/log_3."
        ),
    )
    parser.add_argument(
        "--trigger-min-volume",
        type=int,
        default=None,
        help=(
            "Optional local run override. Omit it to use the selected retrospective profile."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.trigger_min_volume is None:
        args.trigger_min_volume = (
            HISTORICAL_RETROSPECTIVE_MIN_VOLUME
            if args.retrospective_profile == "historical_media_log_3"
            else DEFAULT_TRIGGER_MIN_VOLUME
        )
    videos_path = Path(args.videos_path)
    comments_path = Path(args.comments_path)
    run_dir = (
        Path(args.run_dir)
        if args.run_dir
        else Path("experiments/xiao/local_csv_retrospective_run") / f"run_{stamp()}"
    )
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"Run directory already exists and is not empty: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    audit_dir = run_dir / "audit"
    normalized_dir = run_dir / "local_csv_load"
    data_root = run_dir / "data"
    detection_dir = run_dir / "detection"

    videos = read_csv(videos_path)
    comments = read_csv(comments_path)
    audit = audit_inputs(videos, comments)
    audit["critical_issues"] = critical_issues_from_audit(audit)
    write_json(audit_dir / "input_audit.json", audit)
    write_text(audit_dir / "input_audit.md", audit_markdown(audit, videos_path, comments_path))

    if audit["critical_issues"] or args.stop_after_audit:
        manifest = {
            "run_name": RUN_NAME,
            "run_id": run_dir.name,
            "created_at_utc": utc_now().isoformat(),
            "stopped_after_audit": True,
            "critical_issues": audit["critical_issues"],
            "audit_artifacts": {
                "input_audit_json": str(audit_dir / "input_audit.json"),
                "input_audit_md": str(audit_dir / "input_audit.md"),
            },
        }
        write_json(run_dir / "run_manifest.json", manifest)
        print(json.dumps(json_safe(manifest), indent=2, ensure_ascii=False))
        return

    videos_norm, comments_norm, normalization = normalize_inputs(videos, comments)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized_videos_path = normalized_dir / "videos_normalized.csv"
    normalized_comments_path = normalized_dir / "comments_normalized.csv"
    videos_norm.to_csv(normalized_videos_path, index=False)
    comments_norm.to_csv(normalized_comments_path, index=False)

    storage = persist_batch_snapshot(videos_norm, comments_norm, data_root=data_root)
    clean_path, cleaning = run_cleaning(
        storage["comments_parquet"],
        data_root / "gold" / "clean_comments.parquet",
    )

    replay = run_retrospective_playback(
        clean_path=clean_path,
        snapshots_path=detection_dir / "snapshots.csv",
        trigger_comment_map_path=detection_dir / "trigger_comment_map.csv",
        trigger_log_path=detection_dir / "trigger_log.txt",
        summary_path=detection_dir / "summary.md",
        run_stdout_path=detection_dir / "playback_stdout.txt",
        trigger_min_volume=args.trigger_min_volume,
    )

    generated_paths = {
        "input_audit_json": str(audit_dir / "input_audit.json"),
        "input_audit_md": str(audit_dir / "input_audit.md"),
        "normalized_videos_csv": str(normalized_videos_path),
        "normalized_comments_csv": str(normalized_comments_path),
        "bronze_videos_jsonl": storage["videos_jsonl"],
        "bronze_comments_jsonl": storage["comments_jsonl"],
        "silver_videos_parquet": storage["videos_parquet"],
        "silver_comments_parquet": storage["comments_parquet"],
        "gold_clean_comments_parquet": str(clean_path),
        "snapshots_csv": str(detection_dir / "snapshots.csv"),
        "trigger_comment_map_csv": str(detection_dir / "trigger_comment_map.csv"),
        "trigger_log_txt": str(detection_dir / "trigger_log.txt"),
        "summary_md": str(detection_dir / "summary.md"),
        "playback_stdout_txt": str(detection_dir / "playback_stdout.txt"),
    }
    manifest = build_manifest(
        args=args,
        run_dir=run_dir,
        audit=audit,
        normalization=normalization,
        storage=storage,
        cleaning=cleaning,
        replay=replay,
        generated_paths=generated_paths,
    )
    write_json(run_dir / "run_manifest.json", manifest)
    print(json.dumps(json_safe(manifest), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
