from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from youtube_pipeline.daily_rag_consumer import (
    DailyRagConsumerConfig,
    write_daily_rag_consumer_artifacts_from_config,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _make_sidecars(root: Path) -> Path:
    sidecars = root / "sidecars"
    sidecars.mkdir()
    _write_jsonl(
        sidecars / "daily_event_evidence_packages.jsonl",
        [
            {
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "cycle_index": 1,
                "detector_name": "daily_frequency_baseline",
                "signal_name": "new_comment_count",
                "signal_value": 10,
                "baseline_mean": 2,
                "ratio_to_baseline": 5,
                "delta_value": 8,
                "pct_change_value": 4,
                "threshold_value": 4,
                "trigger_reason": "test",
                "analysis_window_start_utc": "2026-06-01T00:00:00Z",
                "analysis_window_end_utc": "2026-06-04T00:00:00Z",
                "data_cutoff_utc": "2026-06-04T00:00:00Z",
                "alert_evidence_comment_count": 1,
                "validation_context_comment_count": 2,
                "video_ids": ["v1"],
                "source_artifacts": {},
                "created_at_utc": "2026-06-05T00:00:00Z",
            }
        ],
    )
    pd.DataFrame(
        [
            {
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "cycle_index": 1,
                "comment_id": "c1",
                "video_id": "v1",
                "event_time_utc": "2026-06-03T10:00:00Z",
                "text": "alert evidence",
                "is_alert_evidence": True,
                "is_validation_context": True,
                "temporal_role": "alert_evidence",
                "data_cutoff_utc": "2026-06-04T00:00:00Z",
                "analysis_window_start_utc": "2026-06-01T00:00:00Z",
                "analysis_window_end_utc": "2026-06-04T00:00:00Z",
            },
            {
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "cycle_index": 1,
                "comment_id": "c2",
                "video_id": "v1",
                "event_time_utc": "2026-06-02T10:00:00Z",
                "text": "prior context",
                "is_alert_evidence": False,
                "is_validation_context": True,
                "temporal_role": "validation_context_prior",
                "data_cutoff_utc": "2026-06-04T00:00:00Z",
                "analysis_window_start_utc": "2026-06-01T00:00:00Z",
                "analysis_window_end_utc": "2026-06-04T00:00:00Z",
            },
        ]
    ).to_csv(sidecars / "daily_event_comment_inventory.csv", index=False)
    pd.DataFrame(
        [
            {
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "video_id": "v1",
                "alert_evidence_comment_count": 1,
                "validation_context_comment_count": 2,
                "first_comment_time_utc": "2026-06-02T10:00:00Z",
                "last_comment_time_utc": "2026-06-03T10:00:00Z",
                "video_context_role": "alert_and_validation_context",
            }
        ]
    ).to_csv(sidecars / "daily_event_video_map.csv", index=False)
    pd.DataFrame(
        [
            {
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "video_id": "v1",
                "root_comment_id": "c1",
                "comment_count": 1,
            }
        ]
    ).to_csv(sidecars / "daily_event_thread_map.csv", index=False)
    _write_jsonl(
        sidecars / "daily_rag_context_units.jsonl",
        [
            {
                "context_unit_id": "dctx_alert",
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "cycle_index": 1,
                "video_id": "v1",
                "context_type": "video_time_block",
                "temporal_scope": "alert_cycle",
                "context_role": "alert_evidence_unit",
                "contains_alert_evidence": True,
                "contains_validation_context": True,
                "alert_evidence_comment_count": 1,
                "validation_context_comment_count": 1,
                "comment_ids": ["c1"],
                "comment_count": 1,
                "time_start_utc": "2026-06-03T10:00:00Z",
                "time_end_utc": "2026-06-03T10:00:00Z",
                "text_block": "alert evidence",
            },
            {
                "context_unit_id": "dctx_context",
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "cycle_index": 1,
                "video_id": "v1",
                "context_type": "video_time_block",
                "temporal_scope": "prior_window",
                "context_role": "validation_context_unit",
                "contains_alert_evidence": False,
                "contains_validation_context": True,
                "alert_evidence_comment_count": 0,
                "validation_context_comment_count": 1,
                "comment_ids": ["c2"],
                "comment_count": 1,
                "time_start_utc": "2026-06-02T10:00:00Z",
                "time_end_utc": "2026-06-02T10:00:00Z",
                "text_block": "prior context",
            },
        ],
    )
    pd.DataFrame(
        [
            {
                "context_unit_id": "dctx_alert",
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "video_id": "v1",
                "comment_id": "c1",
                "is_alert_evidence": True,
                "is_validation_context": True,
                "temporal_role": "alert_evidence",
            },
            {
                "context_unit_id": "dctx_context",
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "video_id": "v1",
                "comment_id": "c2",
                "is_alert_evidence": False,
                "is_validation_context": True,
                "temporal_role": "validation_context_prior",
            },
        ]
    ).to_csv(sidecars / "daily_context_unit_comment_map.csv", index=False)
    _write_json(
        sidecars / "daily_rag_sidecars_manifest.json",
        {"run_id": "drun_test", "validations": {"status": "passed"}},
    )
    (sidecars / "README.md").write_text("daily sidecars", encoding="utf-8")
    return sidecars


class DailyRagConsumerTests(unittest.TestCase):
    def test_builds_non_generative_payloads_and_stubs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sidecars = _make_sidecars(root)
            output_dir = root / "consumer"

            summary = write_daily_rag_consumer_artifacts_from_config(
                DailyRagConsumerConfig(
                    sidecars_dir=str(sidecars),
                    output_dir=str(output_dir),
                )
            )

            self.assertEqual(summary["validation_status"], "passed")
            inputs = [
                json.loads(line)
                for line in (output_dir / "daily_rag_validation_inputs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            reports = [
                json.loads(line)
                for line in (output_dir / "daily_rag_validation_reports_stub.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(inputs[0]["alert_evidence_unit_count"], 1)
            self.assertEqual(inputs[0]["validation_context_unit_count"], 1)
            self.assertEqual(reports[0]["validation_status"], "not_evaluated")
            self.assertEqual(reports[0]["cited_comment_ids"], [])
            self.assertEqual(reports[0]["cited_context_unit_ids"], [])

    def test_marks_large_context_as_requiring_selection_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sidecars = _make_sidecars(root)
            output_dir = root / "consumer"

            write_daily_rag_consumer_artifacts_from_config(
                DailyRagConsumerConfig(
                    sidecars_dir=str(sidecars),
                    output_dir=str(output_dir),
                    max_estimated_input_tokens=1,
                )
            )

            size_reports = [
                json.loads(line)
                for line in (output_dir / "daily_rag_context_size_report.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                size_reports[0]["context_size_status"],
                "requires_context_selection_policy",
            )

    def test_rejects_external_execution_flags(self) -> None:
        for flag in [
            "run_llm",
            "run_serper",
            "use_embeddings",
            "use_vectorstore",
            "run_g1",
            "run_g2",
        ]:
            with self.assertRaises(ValueError):
                DailyRagConsumerConfig(**{flag: True}).validate()


if __name__ == "__main__":
    unittest.main()
