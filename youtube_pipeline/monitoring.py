from __future__ import annotations

from collections import deque
from typing import Any, Callable

import pandas as pd

from .stream_runtime import Stream, require_streamz

ActivityHook = Callable[[pd.DataFrame], dict[str, Any]]
PolarizationHook = Callable[[pd.DataFrame], dict[str, Any]]


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
    require_streamz()
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


__all__ = [
    "ActivityHook",
    "PolarizationHook",
    "build_event_time_window_stream",
    "default_activity_metrics",
    "default_polarization_metrics",
]
