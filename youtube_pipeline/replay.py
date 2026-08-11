from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .stream_runtime import Stream, require_streamz

PlaybackEventHook = Callable[[dict[str, Any]], None]


def read_dataset_for_playback(
    dataset_path: str | Path,
    ts_col: str = "event_time_utc",
) -> pd.DataFrame:
    path = Path(dataset_path)
    if path.is_dir() or path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(
            "Unsupported dataset format. Use parquet dataset, parquet file, or csv."
        )

    if ts_col not in df.columns:
        raise KeyError(f"Column '{ts_col}' not found in dataset.")

    df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
    df = df.loc[~df[ts_col].isna()].sort_values(ts_col).reset_index(drop=True)
    return df


def replay_events(
    source: Stream,
    events_df: pd.DataFrame,
    ts_col: str = "event_time_utc",
    speed: float = 120.0,
    max_sleep_seconds: float | None = 1.0,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    event_hooks: list[PlaybackEventHook] | None = None,
) -> None:
    """
    Emit events in chronological order with inter-arrival delay scaled by speed.

    speed:
      - 1.0  -> real time
      - 120.0 -> 120x faster than real time
    """
    require_streamz()
    if speed <= 0:
        raise ValueError("speed must be > 0.")
    event_hooks = event_hooks or []

    df = events_df.copy()
    if start is not None:
        start_ts = pd.to_datetime(start, utc=True)
        df = df.loc[df[ts_col] >= start_ts]
    if end is not None:
        end_ts = pd.to_datetime(end, utc=True)
        df = df.loc[df[ts_col] <= end_ts]
    df = df.sort_values(ts_col)

    previous_ts: pd.Timestamp | None = None
    for row in df.to_dict(orient="records"):
        current_ts = pd.to_datetime(row[ts_col], utc=True)
        if previous_ts is not None:
            wait_seconds = max(
                0.0, (current_ts - previous_ts).total_seconds() / float(speed)
            )
            if max_sleep_seconds is not None:
                wait_seconds = min(wait_seconds, max_sleep_seconds)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
        for hook in event_hooks:
            hook(row)
        source.emit(row)
        previous_ts = current_ts

    for hook in event_hooks:
        finalize = getattr(hook, "finalize", None)
        if not callable(finalize):
            owner = getattr(hook, "__self__", None)
            finalize = getattr(owner, "finalize", None)
        if callable(finalize):
            finalize(previous_ts)


__all__ = ["PlaybackEventHook", "read_dataset_for_playback", "replay_events"]
