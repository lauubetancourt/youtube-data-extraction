from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_daily_rag_sidecars import (
    _comments,
    _event_row,
    _window_inventory,
    _write_jsonl,
)
from youtube_pipeline.entrypoints.common_cli import CommonRunCliOptions
from youtube_pipeline.entrypoints.daily_rag_pipeline import (
    main,
    resolve_daily_rag_pipeline_run,
)


def _write_fixture(base: Path) -> Path:
    _write_jsonl(base / "events.jsonl", [_event_row()])
    _comments().to_csv(base / "comments.csv", index=False)
    _window_inventory().to_csv(base / "window.csv", index=False)
    config_path = base / "daily_rag.json"
    config_path.write_text(
        json.dumps(
            {
                "identity": {"run_id": "daily_rag_profile"},
                "rag": {
                    "daily_sidecars": {
                        "daily_events_path": "events.jsonl",
                        "output_dir": "profile_outputs/daily_rag_sidecars",
                        "comments_path": "comments.csv",
                        "cycle_window_inventory_path": "window.csv",
                        "daily_scores_path": None,
                        "daily_detector_manifest_path": None,
                        "cycle_signal_series_path": None,
                        "cycle_stateful_context_path": None,
                        "max_comments_per_context_unit": 2,
                    },
                    "daily_consumer": {
                        "sidecars_dir": "profile_outputs/daily_rag_sidecars",
                        "output_dir": "profile_outputs/daily_rag_consumer",
                        "max_estimated_input_tokens": 16_000,
                    },
                    "daily_context_selection": {
                        "consumer_dir": "profile_outputs/daily_rag_consumer",
                        "sidecars_dir": "profile_outputs/daily_rag_sidecars",
                        "output_dir": "profile_outputs/daily_rag_context_selection",
                        "max_selected_tokens_per_event": 16_000,
                        "alert_coverage_target": 0.35,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


class DailyRagPipelineEntrypointTests(unittest.TestCase):
    def test_current_compatibility_profile_preserves_historical_stage_ids(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        resolved = resolve_daily_rag_pipeline_run(
            CommonRunCliOptions(
                config_path=(
                    project_root
                    / "configs"
                    / "compatibility"
                    / "daily_rag_current.json"
                )
            ),
            base_dir=project_root,
        )

        self.assertEqual(
            resolved.config.rag.daily_sidecars.run_id,
            "drun_c79d30f6e5a3",
        )
        self.assertEqual(
            resolved.config.rag.daily_consumer.run_id,
            "dragconsumer_ed2f98feca1d",
        )
        self.assertEqual(
            resolved.config.rag.daily_context_selection.run_id,
            "dragselect_09f6ade845cc",
        )

    def test_common_cli_runs_non_generative_chain_with_stage_identities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config_path = _write_fixture(base)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                main(
                    [
                        "--config",
                        str(config_path),
                        "--run-id",
                        "global_cli_run",
                        "--output-root",
                        "relocated",
                        "--dry-run",
                    ],
                    base_dir=base,
                )

            summary = json.loads(stdout.getvalue())
            sidecar_id = summary["stages"]["sidecars"]["run_id"]
            consumer_id = summary["stages"]["consumer"]["run_id"]
            selection_id = summary["stages"]["context_selection"]["run_id"]
            relocated = base / "relocated"

            self.assertEqual(summary["run_id"], "global_cli_run")
            self.assertEqual(summary["execution_mode"], "dry_run")
            self.assertEqual(len(summary["config_hash"]), 64)
            self.assertTrue(sidecar_id.startswith("drun_"))
            self.assertTrue(consumer_id.startswith("dragconsumer_"))
            self.assertTrue(selection_id.startswith("dragselect_"))
            self.assertEqual(len({sidecar_id, consumer_id, selection_id}), 3)
            self.assertNotIn(summary["run_id"], {sidecar_id, consumer_id, selection_id})
            self.assertEqual(summary["stages"]["sidecars"]["events_processed"], 1)
            self.assertEqual(summary["stages"]["consumer"]["validation_status"], "passed")
            self.assertEqual(
                summary["stages"]["context_selection"]["validation_status"],
                "passed",
            )
            self.assertTrue(
                (relocated / "daily_rag_sidecars" / "daily_rag_sidecars_manifest.json").is_file()
            )
            self.assertTrue(
                (relocated / "daily_rag_consumer" / "daily_rag_consumer_manifest.json").is_file()
            )
            self.assertTrue(
                (
                    relocated
                    / "daily_rag_context_selection"
                    / "daily_context_selection_manifest.json"
                ).is_file()
            )
            self.assertFalse((base / "profile_outputs").exists())

    def test_global_run_id_override_does_not_override_stage_identities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config_path = _write_fixture(base)
            profile = resolve_daily_rag_pipeline_run(
                CommonRunCliOptions(config_path=config_path),
                base_dir=base,
            )
            overridden = resolve_daily_rag_pipeline_run(
                CommonRunCliOptions(
                    config_path=config_path,
                    run_id="other_global_run",
                ),
                base_dir=base,
            )

            self.assertEqual(profile.config.identity.run_id, "daily_rag_profile")
            self.assertEqual(overridden.config.identity.run_id, "other_global_run")
            self.assertEqual(profile.config.rag, overridden.config.rag)
            self.assertNotEqual(profile.config_hash, overridden.config_hash)
            self.assertIsNone(profile.config.rag.daily_sidecars.run_id)
            self.assertIsNone(profile.config.rag.daily_consumer.run_id)
            self.assertIsNone(profile.config.rag.daily_context_selection.run_id)

    def test_execute_fails_before_creating_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config_path = _write_fixture(base)

            with self.assertRaisesRegex(ValueError, "supports only --dry-run"):
                resolve_daily_rag_pipeline_run(
                    CommonRunCliOptions(
                        config_path=config_path,
                        execution_mode="execute",
                    ),
                    base_dir=base,
                )

            self.assertFalse((base / "profile_outputs").exists())

    def test_script_exposes_only_the_small_common_cli(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(project_root / "scripts" / "run_daily_rag_pipeline.py"),
                "--help",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        for argument in (
            "--config",
            "--run-id",
            "--output-root",
            "--dry-run",
            "--execute",
            "--log-level",
        ):
            self.assertIn(argument, result.stdout)
        self.assertNotIn("--max-estimated-input-tokens", result.stdout)
        self.assertNotIn("--alert-coverage-target", result.stdout)


if __name__ == "__main__":
    unittest.main()
