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
PlaybackEventHook = Callable[[dict[str, Any]], None]


def _require_streamz() -> None:
    if Stream is Any:
        raise ImportError(
            "streamz is not installed. Install it with: pip install streamz"
        )


def _align_timestamp_to_slide(ts: pd.Timestamp, slide_td: pd.Timedelta) -> pd.Timestamp:
    """Return the next slide boundary at-or-after ts."""
    slide_ns = int(slide_td.value)
    if slide_ns <= 0:
        raise ValueError("slide_interval must be > 0.")
    ts_ns = int(ts.value)
    remainder = ts_ns % slide_ns
    if remainder == 0:
        return ts
    return pd.Timestamp(ts_ns + (slide_ns - remainder), tz="UTC")


def _timedelta_steps(window_td: pd.Timedelta, slide_td: pd.Timedelta, label: str) -> int:
    window_ns = int(window_td.value)
    slide_ns = int(slide_td.value)
    if window_ns <= 0:
        raise ValueError(f"{label} must be > 0.")
    if slide_ns <= 0:
        raise ValueError("slide_interval must be > 0.")
    if window_ns % slide_ns != 0:
        raise ValueError(f"{label} must be an exact multiple of slide_interval.")
    return window_ns // slide_ns


class XiaoEMATriggerDetector:
    """
    EMA trigger inspired by Xiao et al. (2025), adapted to the audited stream cadence.

    Implementation choices required by the prototype request:
      - Sliding window volume: 2 minutes
      - Slide interval: 30 seconds
      - Fast EMA span: 2 minutes / 30 seconds = 4 steps
      - Slow EMA span: 10 minutes / 30 seconds = 20 steps
      - Warm-up: first 10 windows update EMAs silently unless volume > v_extreme
      - Post warm-up trigger: EMA_fast > EMA_slow * sensitivity_threshold and volume > v_min
      - Cooldown / lock: 3 minutes
    """

    def __init__(
        self,
        *,
        ts_col: str = "event_time_utc",
        text_col: str = "text",
        window_size: str = "120s",
        slide_interval: str = "30s",
        slow_window: str = "10min",
        sensitivity_threshold: float = 1.5,
        v_min: int = 46,
        cooldown: str = "3min",
        log_fn: Callable[[str], None] | None = None,
    ) -> None:
        self.ts_col = ts_col
        self.text_col = text_col
        self.window_td = pd.to_timedelta(window_size)
        self.slide_td = pd.to_timedelta(slide_interval)
        self.slow_window_td = pd.to_timedelta(slow_window)
        self.cooldown_td = pd.to_timedelta(cooldown)

        if sensitivity_threshold <= 0:
            raise ValueError("sensitivity_threshold must be > 0.")
        if v_min <= 0:
            raise ValueError("v_min must be > 0.")

        self.fast_span_steps = _timedelta_steps(
            self.window_td, self.slide_td, label="window_size"
        )
        self.slow_span_steps = _timedelta_steps(
            self.slow_window_td, self.slide_td, label="slow_window"
        )
        _timedelta_steps(self.cooldown_td, self.slide_td, label="cooldown")

        # Academic EMA form: alpha = 2 / (n + 1)
        self.fast_alpha = 2.0 / float(self.fast_span_steps + 1)
        self.slow_alpha = 2.0 / float(self.slow_span_steps + 1)
        self.sensitivity_threshold = float(sensitivity_threshold)
        self.log_fn = log_fn or print
        self.windows_processed = 0
        self.warmup_windows = 10
        self.v_min = int(v_min)
        self.v_extreme = self.v_min * 2

        self._buffer: deque[dict[str, Any]] = deque()
        self._next_tick: pd.Timestamp | None = None
        self._ema_fast: float | None = None
        self._ema_slow: float | None = None
        self._lock_until: pd.Timestamp | None = None
        self._active_trigger: dict[str, Any] | None = None
        self.completed_triggers: list[dict[str, Any]] = []

    def on_event(self, event: dict[str, Any]) -> None:
        event_ts = pd.to_datetime(event.get(self.ts_col), utc=True, errors="coerce")
        if pd.isna(event_ts):
            return

        event_ts = pd.Timestamp(event_ts)
        if self._next_tick is None:
            self._next_tick = _align_timestamp_to_slide(event_ts, self.slide_td)

        # Emit all completed slide steps before the current event enters the window.
        while self._next_tick is not None and self._next_tick < event_ts:
            self._advance_tick(self._next_tick)
            self._next_tick += self.slide_td

        normalized_event = dict(event)
        normalized_event[self.ts_col] = event_ts
        self._buffer.append(normalized_event)
        self._trim_buffer(event_ts)
        self._collect_if_locked(normalized_event)

        # If the event lands exactly on a slide boundary, it belongs to that step.
        while self._next_tick is not None and self._next_tick == event_ts:
            self._advance_tick(self._next_tick)
            self._next_tick += self.slide_td

    def finalize(self, final_ts: pd.Timestamp | None = None) -> None:
        if self._active_trigger is None:
            return
        self._close_trigger(final_ts)

    def _advance_tick(self, tick_ts: pd.Timestamp) -> None:
        if self._lock_until is not None and tick_ts >= self._lock_until:
            self._close_trigger(tick_ts)

        self._trim_buffer(tick_ts)
        volume = int(len(self._buffer))
        self.windows_processed += 1

        if self._ema_fast is None:
            self._ema_fast = float(volume)
        else:
            self._ema_fast = (
                self.fast_alpha * float(volume)
                + (1.0 - self.fast_alpha) * self._ema_fast
            )

        if self._ema_slow is None:
            self._ema_slow = float(volume)
        else:
            self._ema_slow = (
                self.slow_alpha * float(volume)
                + (1.0 - self.slow_alpha) * self._ema_slow
            )

        if self._lock_until is not None:
            return

        if self._ema_fast is None or self._ema_slow is None or self._ema_slow <= 0:
            return

        strength = self._ema_fast / self._ema_slow

        if self.windows_processed <= self.warmup_windows:
            if volume > self.v_extreme:
                self._open_trigger(tick_ts=tick_ts, volume=volume, strength=strength)
            return

        if volume <= self.v_min:
            return

        if self._ema_fast <= self._ema_slow * self.sensitivity_threshold:
            return

        self._open_trigger(tick_ts=tick_ts, volume=volume, strength=strength)

    def _open_trigger(
        self,
        *,
        tick_ts: pd.Timestamp,
        volume: int,
        strength: float,
    ) -> None:
        self._lock_until = tick_ts + self.cooldown_td
        self._active_trigger = {
            "trigger_time": tick_ts,
            "cooldown_until": self._lock_until,
            "volume": volume,
            "strength": strength,
            "comments": [],
        }
        self.log_fn(
            "[TRIGGER] Evento detectado a las "
            f"{tick_ts.isoformat()}. "
            f"Volumen actual: {volume}. "
            f"Fuerza del pico (EMA_R / EMA_L): {strength:.2f}."
        )

    def _trim_buffer(self, reference_ts: pd.Timestamp) -> None:
        left = reference_ts - self.window_td
        while self._buffer:
            item_ts = pd.to_datetime(
                self._buffer[0].get(self.ts_col), utc=True, errors="coerce"
            )
            if pd.isna(item_ts) or pd.Timestamp(item_ts) >= left:
                break
            self._buffer.popleft()

    def _collect_if_locked(self, event: dict[str, Any]) -> None:
        if self._active_trigger is None or self._lock_until is None:
            return
        event_ts = pd.to_datetime(event.get(self.ts_col), utc=True, errors="coerce")
        if pd.isna(event_ts):
            return
        if pd.Timestamp(event_ts) >= self._lock_until:
            return
        self._active_trigger["comments"].append(
            {
                self.ts_col: pd.Timestamp(event_ts),
                self.text_col: event.get(self.text_col),
            }
        )

    def _close_trigger(self, closed_at: pd.Timestamp | None) -> None:
        if self._active_trigger is None:
            self._lock_until = None
            return
        trigger = dict(self._active_trigger)
        trigger["closed_at"] = closed_at
        self.completed_triggers.append(trigger)
        self._active_trigger = None
        self._lock_until = None


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
    _require_streamz()
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
