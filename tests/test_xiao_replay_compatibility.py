from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from youtube_pipeline.detectors import XiaoEMATriggerDetector
from youtube_pipeline.replay import replay_events


class _RecordingSource:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, event: dict) -> None:
        self.events.append(event)


class _RecordingHook:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.finalized_at: pd.Timestamp | None = None

    def __call__(self, event: dict) -> None:
        self.events.append(event)

    def finalize(self, final_ts: pd.Timestamp | None) -> None:
        self.finalized_at = final_ts


class XiaoCompatibilityTests(unittest.TestCase):
    def test_default_xiao_detects_known_burst_without_changing_contract(self) -> None:
        detector = XiaoEMATriggerDetector(log_fn=lambda _message: None)
        start = pd.Timestamp("2026-01-01T00:00:00Z")

        for index in range(11):
            detector.on_event(
                {
                    "event_time_utc": start + pd.Timedelta(seconds=30 * index),
                    "text": f"steady-{index}",
                }
            )
        for index in range(50):
            detector.on_event(
                {
                    "event_time_utc": start + pd.Timedelta(seconds=330),
                    "text": f"burst-{index}",
                }
            )
        detector.on_event(
            {
                "event_time_utc": start + pd.Timedelta(seconds=390),
                "text": "after-trigger",
            }
        )
        detector.finalize(start + pd.Timedelta(minutes=10))

        self.assertEqual(detector.fast_span_steps, 4)
        self.assertEqual(detector.slow_span_steps, 20)
        self.assertEqual(detector.warmup_windows, 10)
        self.assertEqual(detector.windows_processed, 14)
        self.assertEqual(len(detector.completed_triggers), 1)

        trigger = detector.completed_triggers[0]
        self.assertEqual(trigger["trigger_time"], start + pd.Timedelta(minutes=6))
        self.assertEqual(trigger["cooldown_until"], start + pd.Timedelta(minutes=9))
        self.assertEqual(trigger["closed_at"], start + pd.Timedelta(minutes=10))
        self.assertEqual(trigger["volume"], 53)
        self.assertAlmostEqual(trigger["strength"], 2.9614987988866464)
        self.assertEqual(
            trigger["comments"],
            [
                {
                    "event_time_utc": start + pd.Timedelta(seconds=390),
                    "text": "after-trigger",
                }
            ],
        )


class ReplayCompatibilityTests(unittest.TestCase):
    def test_replay_filters_orders_delays_and_finalizes_selected_events(self) -> None:
        source = _RecordingSource()
        hook = _RecordingHook()
        events = pd.DataFrame(
            [
                {"comment_id": "c4", "event_time_utc": "2026-01-01T00:01:30Z"},
                {"comment_id": "c2", "event_time_utc": "2026-01-01T00:00:30Z"},
                {"comment_id": "c1", "event_time_utc": "2026-01-01T00:00:00Z"},
                {"comment_id": "c3", "event_time_utc": "2026-01-01T00:01:00Z"},
            ]
        )
        events["event_time_utc"] = pd.to_datetime(events["event_time_utc"], utc=True)

        with (
            patch("youtube_pipeline.replay.require_streamz"),
            patch("youtube_pipeline.replay.time.sleep") as sleep,
        ):
            replay_events(
                source,
                events,
                speed=120.0,
                max_sleep_seconds=1.0,
                start="2026-01-01T00:00:30Z",
                end="2026-01-01T00:01:00Z",
                event_hooks=[hook],
            )

        self.assertEqual(
            [event["comment_id"] for event in source.events],
            ["c2", "c3"],
        )
        self.assertEqual(
            [event["comment_id"] for event in hook.events],
            ["c2", "c3"],
        )
        sleep.assert_called_once_with(0.25)
        self.assertEqual(
            hook.finalized_at,
            pd.Timestamp("2026-01-01T00:01:00Z"),
        )


if __name__ == "__main__":
    unittest.main()
