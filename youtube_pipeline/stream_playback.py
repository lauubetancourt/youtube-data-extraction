from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

import pandas as pd

try:
    from streamz import Stream
except ImportError:  # pragma: no cover
    Stream = Any  # type: ignore[misc,assignment]


ActivityHook = Callable[[pd.DataFrame], dict[str, Any]]
PolarizationHook = Callable[[pd.DataFrame], dict[str, Any]]


def _require_streamz() -> None:
    if Stream is Any:
        raise ImportError(
            "streamz is not installed. Install it with: pip install streamz"
        )


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
) -> None:
    """
    Emit events in chronological order with inter-arrival delay scaled by speed.

    speed:
      - 1.0  -> real time
      - 120.0 -> 120x faster than real time
    """
    _require_streamz()
    if speed <= 0:
        raise ValueError("speed must be > 0.")

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
        source.emit(row)
        previous_ts = current_ts


def default_activity_metrics(window_df: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {"volume": int(len(window_df))}
    if "author_id" in window_df.columns:
        out["unique_authors"] = int(window_df["author_id"].nunique(dropna=True))
    if "video_id" in window_df.columns:
        out["unique_videos"] = int(window_df["video_id"].nunique(dropna=True))
    return out


def default_polarization_metrics(window_df: pd.DataFrame) -> dict[str, Any]:
    if "sentiment_score" in window_df.columns:
        series = pd.to_numeric(window_df["sentiment_score"], errors="coerce")
        series = series.dropna()
        if not series.empty:
            return {
                "sentiment_mean": float(series.mean()),
                "sentiment_std": float(series.std(ddof=0)),
            }
    # Fallback when explicit sentiment isn't available yet.
    features = {}
    if "emoji_count" in window_df.columns:
        features["emoji_density"] = float(window_df["emoji_count"].mean())
    if "exclamation_count" in window_df.columns:
        features["exclaim_density"] = float(window_df["exclamation_count"].mean())
    if "question_count" in window_df.columns:
        features["question_density"] = float(window_df["question_count"].mean())
    return features


def build_event_time_window_stream(
    source: Stream,
    window_size: str = "30min",
    ts_col: str = "event_time_utc",
    activity_fn: ActivityHook | None = None,
    polarization_fn: PolarizationHook | None = None,
) -> Stream:
    """
    Build a stream of snapshots with event-time windows and hook-based metrics.

    Each snapshot contains:
      - window_start
      - window_end
      - activity
      - polarization
      - events (optional lightweight list for debugging)
    """
    _require_streamz()
    activity_fn = activity_fn or default_activity_metrics
    polarization_fn = polarization_fn or default_polarization_metrics
    window_td = pd.to_timedelta(window_size)

    def update_state(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        buffer: deque[dict[str, Any]] = state["buffer"]
        event_ts = pd.to_datetime(event[ts_col], utc=True, errors="coerce")
        if pd.isna(event_ts):
            return state

        event = dict(event)
        event[ts_col] = event_ts
        buffer.append(event)

        left = event_ts - window_td
        while buffer and pd.to_datetime(buffer[0][ts_col], utc=True) < left:
            buffer.popleft()

        window_df = pd.DataFrame(list(buffer))
        snapshot = {
            "window_start": left,
            "window_end": event_ts,
            "activity": activity_fn(window_df),
            "polarization": polarization_fn(window_df),
            "size": int(len(window_df)),
        }
        state["snapshot"] = snapshot
        return state

    seed = {"buffer": deque(), "snapshot": None}
    return (
        source.filter(lambda event: event is not None)
        .scan(update_state, start=seed)
        .map(lambda state: state["snapshot"])
        .filter(lambda snap: snap is not None)
    )

