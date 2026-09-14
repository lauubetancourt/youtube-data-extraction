from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from youtube_pipeline.cyclic_detection_connector import (
    run_cyclic_detection_connector,
)
from youtube_pipeline.detectors import create_detector
from youtube_pipeline.entrypoints.common_cli import CommonRunCliOptions
from youtube_pipeline.entrypoints.cyclic_pipeline import (
    main,
    resolve_cyclic_pipeline_run,
    run_cyclic_pipeline,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = REPOSITORY_ROOT / "configs" / "development"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class CyclicActivityDetectionRuntimeTests(unittest.TestCase):
    def _run_profile(self, profile_name: str, output_root: Path) -> dict:
        stdout = io.StringIO()
        with (
            patch(
                "youtube_pipeline.cyclic_detection_connector.create_detector",
                wraps=create_detector,
            ) as detector_factory,
            contextlib.redirect_stdout(stdout),
        ):
            main(
                [
                    "--config",
                    str(PROFILE_DIR / profile_name),
                    "--output-root",
                    str(output_root),
                    "--dry-run",
                ],
                base_dir=REPOSITORY_ROOT,
            )

        detector_factory.assert_called_once()
        return json.loads(stdout.getvalue())

    def _assert_runtime_artifacts(
        self,
        *,
        summary: dict,
        output_root: Path,
        detector_id: str,
    ) -> None:
        stage = summary["stages"]["detection_connector"]
        artifact_dir = output_root / "activity_detection_runtime"
        results = _read_jsonl(artifact_dir / "activity_detection_results.jsonl")
        cycles = _read_jsonl(
            artifact_dir / "cycle_activity_detection_outputs.jsonl"
        )
        manifest = json.loads(
            (artifact_dir / "activity_detection_manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(set(summary["stages"]), {
            "ingestion",
            "orchestration",
            "stateful_adapter",
            "detection_connector",
        })
        self.assertEqual(stage["status"], "executed")
        self.assertEqual(stage["detector_id"], detector_id)
        self.assertEqual(stage["observations_emitted"], 6)
        self.assertEqual(stage["detection_results_produced"], 6)
        self.assertEqual(stage["trigger_count"], 0)
        self.assertEqual(stage["runtime_errors"], 0)
        self.assertEqual(len(results), 6)
        self.assertEqual(len(cycles), 2)
        self.assertTrue(all(row["detector_id"] == detector_id for row in results))
        self.assertTrue(all(row["quality"] == "passed" for row in results))
        self.assertTrue(all(row["score"] is None for row in results))
        self.assertTrue(all(row["detection_status"] == "executed" for row in cycles))
        self.assertTrue(all(row["future_leak_count"] == 0 for row in cycles))
        self.assertEqual(
            [row["detector_metadata"]["observations_processed"] for row in results],
            [1, 2, 3, 4, 5, 6],
        )

        observation_times = pd.to_datetime(
            [row["observation_time_utc"] for row in results],
            utc=True,
        )
        cutoffs = pd.to_datetime(
            [row["data_cutoff_utc"] for row in results],
            utc=True,
        )
        self.assertTrue(observation_times.is_monotonic_increasing)
        self.assertTrue((observation_times <= cutoffs).all())
        self.assertEqual(manifest["status"], "executed")
        self.assertEqual(manifest["schema_version"], "1")
        self.assertEqual(manifest["detector_id"], detector_id)
        self.assertEqual(manifest["counts"]["triggered_results"], 0)
        self.assertEqual(manifest["causality"]["future_leak_count"], 0)
        self.assertEqual(manifest["causality"]["duplicate_dispatch_count"], 0)
        self.assertEqual(
            manifest["input_source"]["role"],
            "PROVISIONAL_RUNTIME_INPUT",
        )
        self.assertFalse(
            manifest["input_source"]["final_preprocessing_authority"]
        )
        self.assertEqual(
            manifest["stateful_policy"]["detector_instances_per_route"],
            1,
        )
        self.assertTrue(
            manifest["stateful_policy"]["preserve_state_between_cycles"]
        )
        self.assertEqual(
            manifest["downstream"]["event_candidate_runtime"],
            "not_executed",
        )

    def test_page_hinkley_profile_runs_neutral_detection_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "page_hinkley"
            summary = self._run_profile(
                "cyclic_activity_page_hinkley.json",
                output_root,
            )

            self._assert_runtime_artifacts(
                summary=summary,
                output_root=output_root,
                detector_id="page_hinkley",
            )

    def test_adwin_profile_runs_same_neutral_detection_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "adwin"
            summary = self._run_profile(
                "cyclic_activity_adwin.json",
                output_root,
            )

            self._assert_runtime_artifacts(
                summary=summary,
                output_root=output_root,
                detector_id="adwin",
            )

    def test_cross_cycle_event_time_regression_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "ordering"
            resolved = resolve_cyclic_pipeline_run(
                CommonRunCliOptions(
                    config_path=(
                        PROFILE_DIR / "cyclic_activity_page_hinkley.json"
                    ),
                    output_root=output_root,
                ),
                base_dir=REPOSITORY_ROOT,
            )
            run_cyclic_pipeline(resolved)

            inventory_path = output_root / "cycle_window_inventory.csv"
            inventory = pd.read_csv(inventory_path)
            second_cycle = inventory["cycle_index"] == 2
            second_cycle_new = second_cycle & inventory["is_new_in_cycle"].astype(bool)
            inventory.loc[
                second_cycle_new,
                "event_time_utc",
            ] = "2026-06-02T04:58:00Z"
            inventory.to_csv(inventory_path, index=False)

            config = resolved.config
            assert config.signals is not None
            assert config.signals.activity is not None
            assert config.detection is not None
            assert config.detection.connector is not None
            assert config.detection.activity_route is not None
            detector_config = getattr(
                config.detection,
                config.detection.activity_route.detector_id,
            )

            with self.assertRaisesRegex(ValueError, "non-decreasing event-time"):
                run_cyclic_detection_connector(
                    config.detection.connector,
                    run_id=config.identity.run_id,
                    activity_route=config.detection.activity_route,
                    signal_definition=config.signals.activity,
                    detector_config=detector_config,
                )


if __name__ == "__main__":
    unittest.main()
