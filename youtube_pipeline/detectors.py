from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Any, Callable, Protocol

import pandas as pd


class TriggerDetector(Protocol):
    completed_triggers: list[dict[str, Any]]

    def on_event(self, event: dict[str, Any]) -> None:
        ...

    def finalize(self, final_ts: pd.Timestamp | None = None) -> None:
        ...


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


@dataclass(frozen=True, slots=True)
class XiaoEMAConfig:
    """Authoritative methodological parameters for the XIAO EMA detector."""

    ts_col: str = "event_time_utc"
    text_col: str = "text"
    window_size: str = "120s"
    slide_interval: str = "30s"
    slow_window: str = "10min"
    sensitivity_threshold: float = 1.5
    v_min: int = 46
    cooldown: str = "3min"
    warmup_windows: int = 10
    extreme_volume_multiplier: float = 2.0

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "XiaoEMAConfig":
        config_payload = payload.get("xiao_ema", payload)
        if not isinstance(config_payload, dict):
            raise ValueError("XIAO EMA config must be an object.")
        allowed = set(cls.__dataclass_fields__)
        unknown = sorted(set(config_payload) - allowed)
        if unknown:
            raise ValueError(f"Unknown XIAO EMA config fields: {unknown}")
        return cls(**config_payload)

    def __post_init__(self) -> None:
        for field_name in (
            "ts_col",
            "text_col",
            "window_size",
            "slide_interval",
            "slow_window",
            "cooldown",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string.")
            if not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if self.sensitivity_threshold <= 0:
            raise ValueError("sensitivity_threshold must be > 0.")
        if self.v_min <= 0:
            raise ValueError("v_min must be > 0.")
        if self.warmup_windows < 0:
            raise ValueError("warmup_windows must be >= 0.")
        if self.extreme_volume_multiplier <= 0:
            raise ValueError("extreme_volume_multiplier must be > 0.")

        slide_td = pd.to_timedelta(self.slide_interval)
        _timedelta_steps(
            pd.to_timedelta(self.window_size),
            slide_td,
            label="window_size",
        )
        _timedelta_steps(
            pd.to_timedelta(self.slow_window),
            slide_td,
            label="slow_window",
        )
        _timedelta_steps(
            pd.to_timedelta(self.cooldown),
            slide_td,
            label="cooldown",
        )


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
        config: XiaoEMAConfig | None = None,
        ts_col: str | None = None,
        text_col: str | None = None,
        window_size: str | None = None,
        slide_interval: str | None = None,
        slow_window: str | None = None,
        sensitivity_threshold: float | None = None,
        v_min: int | None = None,
        cooldown: str | None = None,
        log_fn: Callable[[str], None] | None = None,
    ) -> None:
        if config is not None and not isinstance(config, XiaoEMAConfig):
            raise TypeError("config must be XiaoEMAConfig or None.")
        overrides = {
            key: value
            for key, value in {
                "ts_col": ts_col,
                "text_col": text_col,
                "window_size": window_size,
                "slide_interval": slide_interval,
                "slow_window": slow_window,
                "sensitivity_threshold": sensitivity_threshold,
                "v_min": v_min,
                "cooldown": cooldown,
            }.items()
            if value is not None
        }
        if config is not None and overrides:
            raise ValueError(
                "Pass either XiaoEMAConfig or legacy keyword overrides, not both."
            )
        effective = config or XiaoEMAConfig()
        if overrides:
            effective = replace(effective, **overrides)

        self.config = effective
        self.ts_col = effective.ts_col
        self.text_col = effective.text_col
        self.window_td = pd.to_timedelta(effective.window_size)
        self.slide_td = pd.to_timedelta(effective.slide_interval)
        self.slow_window_td = pd.to_timedelta(effective.slow_window)
        self.cooldown_td = pd.to_timedelta(effective.cooldown)

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
        self.sensitivity_threshold = float(effective.sensitivity_threshold)
        self.log_fn = log_fn or print
        self.windows_processed = 0
        self.warmup_windows = int(effective.warmup_windows)
        self.v_min = int(effective.v_min)
        self.v_extreme = int(self.v_min * effective.extreme_volume_multiplier)

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


DEFAULT_DETECTOR = "xiao_ema"
DETECTOR_PARAM_ALIASES = {
    "trigger_window_size": "window_size",
    "trigger_slide_interval": "slide_interval",
    "trigger_slow_window": "slow_window",
    "trigger_threshold": "sensitivity_threshold",
    "trigger_min_volume": "v_min",
    "trigger_cooldown": "cooldown",
}
DETECTOR_REGISTRY: dict[str, Callable[..., TriggerDetector]] = {
    DEFAULT_DETECTOR: XiaoEMATriggerDetector,
}


def normalize_detector_params(params: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in params.items():
        normalized[DETECTOR_PARAM_ALIASES.get(key, key)] = value
    return normalized


def get_detector_names() -> tuple[str, ...]:
    return tuple(sorted(DETECTOR_REGISTRY))


def create_detector(
    name: str | None = DEFAULT_DETECTOR,
    **params: Any,
) -> TriggerDetector:
    detector_name = name or DEFAULT_DETECTOR
    try:
        factory = DETECTOR_REGISTRY[detector_name]
    except KeyError as exc:
        available = ", ".join(get_detector_names())
        raise ValueError(
            f"Unknown detector '{detector_name}'. Available detectors: {available}."
        ) from exc
    return factory(**normalize_detector_params(params))


__all__ = [
    "DEFAULT_DETECTOR",
    "DETECTOR_PARAM_ALIASES",
    "DETECTOR_REGISTRY",
    "TriggerDetector",
    "XiaoEMAConfig",
    "XiaoEMATriggerDetector",
    "_align_timestamp_to_slide",
    "_timedelta_steps",
    "create_detector",
    "get_detector_names",
    "normalize_detector_params",
]
