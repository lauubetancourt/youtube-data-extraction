#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from youtube_pipeline import (  # noqa: E402
    DEFAULT_DETECTOR,
    ExtractionConfig,
    build_event_time_window_stream,
    clean_comments_dataframe,
    create_detector,
    get_detector_names,
    persist_batch_snapshot,
    read_dataset_for_playback,
    replay_events,
    run_extraction_pipeline,
)

DEFAULT_TRIGGER_THRESHOLD = 1.5
DEFAULT_TRIGGER_MIN_VOLUME = 46
DEFAULT_TRIGGER_WINDOW_SIZE = "120s"
DEFAULT_TRIGGER_SLIDE_INTERVAL = "30s"
DEFAULT_TRIGGER_SLOW_WINDOW = "10min"
DEFAULT_TRIGGER_COOLDOWN = "3min"


def _read_table(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.is_dir() or p.suffix.lower() == ".parquet":
        return pd.read_parquet(p)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    raise ValueError(f"Unsupported file format: {p}")


def _write_table(df: pd.DataFrame, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() == ".csv":
        df.to_csv(p, index=False)
    else:
        df.to_parquet(p, index=False)
    return p


def run_storage(videos_path: str, comments_path: str, data_root: str) -> dict[str, Any]:
    videos_df = _read_table(videos_path)
    comments_df = _read_table(comments_path)
    return persist_batch_snapshot(videos_df, comments_df, data_root=data_root)


def _read_json_config(config_file: str | None) -> dict[str, Any]:
    if not config_file:
        return {}
    path = Path(config_file)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_detector_config(config_file: str | None) -> tuple[str | None, dict[str, Any]]:
    payload = _read_json_config(config_file)
    if not payload:
        return None, {}

    detector_payload = payload.get("detector", payload)
    if isinstance(detector_payload, str):
        return detector_payload, {}
    if not isinstance(detector_payload, dict):
        raise ValueError("Detector config must be an object or a detector name string.")

    detector_name = (
        detector_payload.get("name")
        or detector_payload.get("detector")
        or detector_payload.get("type")
    )
    raw_params = detector_payload.get("params", {})
    if raw_params is None:
        raw_params = {}
    if not isinstance(raw_params, dict):
        raise ValueError("Detector config field 'params' must be an object.")

    inline_params = {
        key: value
        for key, value in detector_payload.items()
        if key not in {"name", "detector", "type", "params"}
    }
    return detector_name, {**inline_params, **raw_params}


def _resolve_detector_settings(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    config_name, config_params = _read_detector_config(
        getattr(args, "detector_config_file", None)
    )
    detector_name = getattr(args, "detector", None) or config_name or DEFAULT_DETECTOR
    params = dict(config_params)

    if detector_name == DEFAULT_DETECTOR:
        params.setdefault("window_size", DEFAULT_TRIGGER_WINDOW_SIZE)
        params.setdefault("slide_interval", DEFAULT_TRIGGER_SLIDE_INTERVAL)
        params.setdefault("slow_window", DEFAULT_TRIGGER_SLOW_WINDOW)
        params.setdefault("sensitivity_threshold", DEFAULT_TRIGGER_THRESHOLD)
        params.setdefault("v_min", DEFAULT_TRIGGER_MIN_VOLUME)
        params.setdefault("cooldown", DEFAULT_TRIGGER_COOLDOWN)

    cli_overrides = {
        "trigger_window_size": "window_size",
        "trigger_slide_interval": "slide_interval",
        "trigger_slow_window": "slow_window",
        "trigger_threshold": "sensitivity_threshold",
        "trigger_min_volume": "v_min",
        "trigger_cooldown": "cooldown",
    }
    for attr, param_name in cli_overrides.items():
        value = getattr(args, attr, None)
        if value is not None:
            params[param_name] = value

    return detector_name, params


def run_extract(
    *,
    config_file: str | None = None,
    data_root: str | None = None,
    query: str | None = None,
    published_after: str | None = None,
    published_before: str | None = None,
    min_views: int | None = None,
    min_comments: int | None = None,
    max_comments: int | None = None,
    max_results: int | None = None,
    save_legacy_csv: bool | None = None,
    log_level: str = "INFO",
) -> dict[str, Any]:
    cfg_payload = _read_json_config(config_file)
    cfg = ExtractionConfig.from_mapping(cfg_payload)

    overrides = {
        "data_root": data_root,
        "query": query,
        "published_after": published_after,
        "published_before": published_before,
        "min_views": min_views,
        "min_comments": min_comments,
        "max_comments": max_comments,
        "max_results": max_results,
        "save_legacy_csv": save_legacy_csv,
    }
    for key, value in overrides.items():
        if value is not None:
            setattr(cfg, key, value)

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logger = logging.getLogger("run_pipeline.extract")
    return run_extraction_pipeline(cfg, logger)


def run_clean(
    input_path: str,
    output_path: str,
    raw_text_col: str,
    timestamp_col: str,
    keep_spam: bool,
) -> Path:
    comments_df = _read_table(input_path)
    ts_col = timestamp_col
    if ts_col not in comments_df.columns and "event_time_utc" in comments_df.columns:
        ts_col = "event_time_utc"

    clean_df = clean_comments_dataframe(
        comments_df,
        raw_text_col=raw_text_col,
        timestamp_col=ts_col,
        keep_spam=keep_spam,
    )
    return _write_table(clean_df, output_path)


def run_playback(
    input_path: str,
    output_snapshots: str,
    ts_col: str = "event_time_utc",
    window_size: str = "20min",
    trigger_threshold: float | None = None,
    trigger_min_volume: int | None = None,
    trigger_window_size: str | None = None,
    trigger_slide_interval: str | None = None,
    trigger_slow_window: str | None = None,
    trigger_cooldown: str | None = None,
    speed: float = 120.0,
    max_sleep_seconds: float | None = 0.2,
    start: str | None = None,
    end: str | None = None,
    detector_name: str = DEFAULT_DETECTOR,
    detector_params: dict[str, Any] | None = None,
) -> Path:
    try:
        from streamz import Stream
    except ImportError as exc:
        raise ImportError(
            "streamz is required for playback. Install with: pip install streamz"
        ) from exc

    events = read_dataset_for_playback(input_path, ts_col=ts_col)
    source = Stream()
    snapshots: list[dict[str, Any]] = []
    resolved_detector_params = dict(detector_params or {})
    resolved_detector_params.setdefault("ts_col", ts_col)
    if detector_name == DEFAULT_DETECTOR:
        resolved_detector_params.setdefault(
            "window_size", trigger_window_size or DEFAULT_TRIGGER_WINDOW_SIZE
        )
        resolved_detector_params.setdefault(
            "slide_interval",
            trigger_slide_interval or DEFAULT_TRIGGER_SLIDE_INTERVAL,
        )
        resolved_detector_params.setdefault(
            "slow_window", trigger_slow_window or DEFAULT_TRIGGER_SLOW_WINDOW
        )
        resolved_detector_params.setdefault(
            "sensitivity_threshold",
            trigger_threshold
            if trigger_threshold is not None
            else DEFAULT_TRIGGER_THRESHOLD,
        )
        resolved_detector_params.setdefault(
            "v_min",
            trigger_min_volume
            if trigger_min_volume is not None
            else DEFAULT_TRIGGER_MIN_VOLUME,
        )
        resolved_detector_params.setdefault(
            "cooldown", trigger_cooldown or DEFAULT_TRIGGER_COOLDOWN
        )
    detector = create_detector(detector_name, **resolved_detector_params)

    (
        build_event_time_window_stream(
            source,
            window_size=window_size,
            ts_col=ts_col,
        )
        .sink(snapshots.append)
    )

    replay_events(
        source=source,
        events_df=events,
        ts_col=ts_col,
        speed=speed,
        max_sleep_seconds=max_sleep_seconds,
        start=start,
        end=end,
        event_hooks=[detector.on_event],
    )

    snap_df = pd.json_normalize(snapshots, sep=".")
    out_path = Path(output_snapshots)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    snap_df.to_csv(out_path, index=False)
    return out_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run YouTube extraction storage, cleaning, and Streamz playback pipeline."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_extract = subparsers.add_parser("extract", help="Run live extraction from YouTube API.")
    p_extract.add_argument("--config-file", default=None, help="Extraction JSON config file.")
    p_extract.add_argument("--data-root", default=None, help="Output root folder (e.g., data).")
    p_extract.add_argument("--query", default=None)
    p_extract.add_argument("--published-after", default=None)
    p_extract.add_argument("--published-before", default=None)
    p_extract.add_argument("--min-views", type=int, default=None)
    p_extract.add_argument("--min-comments", type=int, default=None)
    p_extract.add_argument("--max-comments", type=int, default=None)
    p_extract.add_argument("--max-results", type=int, default=None)
    p_extract.add_argument("--log-level", default="INFO")
    extract_csv_group = p_extract.add_mutually_exclusive_group()
    extract_csv_group.add_argument(
        "--save-legacy-csv",
        dest="save_legacy_csv",
        action="store_true",
        help="Also write data/videos_preliminares.csv and data/comments.csv.",
    )
    extract_csv_group.add_argument(
        "--no-save-legacy-csv",
        dest="save_legacy_csv",
        action="store_false",
        help="Skip compatibility CSV exports.",
    )
    p_extract.set_defaults(save_legacy_csv=None)

    p_storage = subparsers.add_parser("storage", help="Run storage phase only.")
    p_storage.add_argument("--videos-path", required=True, help="CSV/Parquet of videos.")
    p_storage.add_argument(
        "--comments-path", required=True, help="CSV/Parquet of comments."
    )
    p_storage.add_argument("--data-root", default="data", help="Output root folder.")

    p_clean = subparsers.add_parser("clean", help="Run cleaning phase only.")
    p_clean.add_argument(
        "--input-path",
        default="data/silver/comments",
        help="Input comments (CSV/Parquet file or Parquet dataset dir).",
    )
    p_clean.add_argument(
        "--output-path",
        default="data/gold/clean_comments.parquet",
        help="Output cleaned comments (.parquet or .csv).",
    )
    p_clean.add_argument("--raw-text-col", default="text")
    p_clean.add_argument("--timestamp-col", default="published_at")
    p_clean.add_argument("--keep-spam", action="store_true")

    p_play = subparsers.add_parser("playback", help="Run playback phase only.")
    p_play.add_argument(
        "--input-path",
        default="data/gold/clean_comments.parquet",
        help="Input cleaned dataset (CSV/Parquet).",
    )
    p_play.add_argument(
        "--output-snapshots",
        default="data/gold/snapshots.csv",
        help="Output snapshots as CSV.",
    )
    p_play.add_argument("--ts-col", default="event_time_utc")
    p_play.add_argument("--window-size", default="20min")
    p_play.add_argument("--trigger-threshold", type=float, default=None)
    p_play.add_argument("--trigger-min-volume", type=int, default=None)
    p_play.add_argument("--trigger-window-size", default=None)
    p_play.add_argument("--trigger-slide-interval", default=None)
    p_play.add_argument("--trigger-slow-window", default=None)
    p_play.add_argument("--trigger-cooldown", default=None)
    p_play.add_argument("--detector", choices=get_detector_names(), default=None)
    p_play.add_argument("--detector-config-file", default=None)
    p_play.add_argument("--speed", type=float, default=120.0)
    p_play.add_argument("--max-sleep-seconds", type=float, default=0.2)
    p_play.add_argument("--start", default=None)
    p_play.add_argument("--end", default=None)

    p_all = subparsers.add_parser("all", help="Run full 3-phase pipeline.")
    p_all.add_argument(
        "--videos-path",
        default="data/videos_preliminares.csv",
        help="CSV/Parquet generated from extraction phase.",
    )
    p_all.add_argument(
        "--comments-path",
        default="data/comments.csv",
        help="CSV/Parquet generated from extraction phase.",
    )
    p_all.add_argument("--data-root", default="data")
    p_all.add_argument(
        "--clean-output",
        default="data/gold/clean_comments.parquet",
        help="Output cleaned comments path.",
    )
    p_all.add_argument(
        "--snapshots-output",
        default="data/gold/snapshots.csv",
        help="Output snapshots path.",
    )
    p_all.add_argument("--raw-text-col", default="text")
    p_all.add_argument("--timestamp-col", default="published_at")
    p_all.add_argument("--keep-spam", action="store_true")
    p_all.add_argument("--ts-col", default="event_time_utc")
    p_all.add_argument("--window-size", default="20min")
    p_all.add_argument("--trigger-threshold", type=float, default=None)
    p_all.add_argument("--trigger-min-volume", type=int, default=None)
    p_all.add_argument("--trigger-window-size", default=None)
    p_all.add_argument("--trigger-slide-interval", default=None)
    p_all.add_argument("--trigger-slow-window", default=None)
    p_all.add_argument("--trigger-cooldown", default=None)
    p_all.add_argument("--detector", choices=get_detector_names(), default=None)
    p_all.add_argument("--detector-config-file", default=None)
    p_all.add_argument("--speed", type=float, default=120.0)
    p_all.add_argument("--max-sleep-seconds", type=float, default=0.2)
    p_all.add_argument("--start", default=None)
    p_all.add_argument("--end", default=None)
    p_all.add_argument(
        "--extract-first",
        action="store_true",
        help="Run API extraction first and use its outputs for clean/playback.",
    )
    p_all.add_argument(
        "--extract-config-file",
        default=None,
        help="Extraction JSON config used when --extract-first is enabled.",
    )
    p_all.add_argument("--extract-log-level", default="INFO")
    p_all.add_argument(
        "--skip-playback",
        action="store_true",
        help="Run storage+clean only.",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "extract":
        result = run_extract(
            config_file=args.config_file,
            data_root=args.data_root,
            query=args.query,
            published_after=args.published_after,
            published_before=args.published_before,
            min_views=args.min_views,
            min_comments=args.min_comments,
            max_comments=args.max_comments,
            max_results=args.max_results,
            save_legacy_csv=args.save_legacy_csv,
            log_level=args.log_level,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.command == "storage":
        result = run_storage(args.videos_path, args.comments_path, args.data_root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.command == "clean":
        output = run_clean(
            input_path=args.input_path,
            output_path=args.output_path,
            raw_text_col=args.raw_text_col,
            timestamp_col=args.timestamp_col,
            keep_spam=args.keep_spam,
        )
        print(str(output))
        return

    if args.command == "playback":
        detector_name, detector_params = _resolve_detector_settings(args)
        output = run_playback(
            input_path=args.input_path,
            output_snapshots=args.output_snapshots,
            ts_col=args.ts_col,
            window_size=args.window_size,
            speed=args.speed,
            max_sleep_seconds=args.max_sleep_seconds,
            start=args.start,
            end=args.end,
            detector_name=detector_name,
            detector_params=detector_params,
        )
        print(str(output))
        return

    if args.command == "all":
        if args.extract_first:
            extract_result = run_extract(
                config_file=args.extract_config_file,
                data_root=args.data_root,
                log_level=args.extract_log_level,
            )
            storage_result = extract_result["persisted"]
        else:
            storage_result = run_storage(args.videos_path, args.comments_path, args.data_root)

        clean_output = run_clean(
            input_path=storage_result["comments_parquet"],
            output_path=args.clean_output,
            raw_text_col=args.raw_text_col,
            timestamp_col=args.timestamp_col,
            keep_spam=args.keep_spam,
        )

        summary: dict[str, Any] = {
            "storage": storage_result,
            "clean_output": str(clean_output),
        }
        if args.extract_first:
            summary["extract"] = extract_result

        if not args.skip_playback:
            detector_name, detector_params = _resolve_detector_settings(args)
            snapshots_output = run_playback(
                input_path=str(clean_output),
                output_snapshots=args.snapshots_output,
                ts_col=args.ts_col,
                window_size=args.window_size,
                speed=args.speed,
                max_sleep_seconds=args.max_sleep_seconds,
                start=args.start,
                end=args.end,
                detector_name=detector_name,
                detector_params=detector_params,
            )
            summary["snapshots_output"] = str(snapshots_output)

        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    parser.error("Unknown command.")


if __name__ == "__main__":
    main()
