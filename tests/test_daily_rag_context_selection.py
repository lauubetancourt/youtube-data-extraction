from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from youtube_pipeline.daily_rag_context_selection import (
    DailyContextSelectionConfig,
    write_daily_context_selection_artifacts_from_config,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _unit(
    unit_id: str,
    *,
    video_id: str,
    role: str,
    comment_ids: list[str],
    tokens: int,
    time_start: str,
) -> dict:
    return {
        "context_unit_id": unit_id,
        "daily_rag_event_id": "drage_test",
        "daily_event_id": "dfe_test",
        "cycle_id": "cyc_1",
        "video_id": video_id,
        "context_type": "video_time_block",
        "temporal_scope": "alert_cycle" if role == "alert_evidence_unit" else "prior_window",
        "context_role": role,
        "contains_alert_evidence": role == "alert_evidence_unit",
        "contains_validation_context": True,
        "alert_evidence_comment_count": len(comment_ids) if role == "alert_evidence_unit" else 0,
        "validation_context_comment_count": len(comment_ids),
        "comment_ids": comment_ids,
        "comment_ids_hash": "test",
        "comment_count": len(comment_ids),
        "time_start_utc": time_start,
        "time_end_utc": time_start,
        "estimated_tokens": tokens,
        "text_block": " ".join(comment_ids),
    }


def _make_inputs(root: Path, *, second_video_tokens: int = 100) -> tuple[Path, Path]:
    consumer = root / "consumer"
    sidecars = root / "sidecars"
    consumer.mkdir()
    sidecars.mkdir()

    units = [
        _unit(
            "u_alert_v1",
            video_id="v1",
            role="alert_evidence_unit",
            comment_ids=["c1", "c2"],
            tokens=100,
            time_start="2026-06-03T10:00:00Z",
        ),
        _unit(
            "u_alert_v2",
            video_id="v2",
            role="alert_evidence_unit",
            comment_ids=["c3"],
            tokens=second_video_tokens,
            time_start="2026-06-03T11:00:00Z",
        ),
        _unit(
            "u_context_v1",
            video_id="v1",
            role="validation_context_unit",
            comment_ids=["c4"],
            tokens=50,
            time_start="2026-06-02T09:00:00Z",
        ),
        _unit(
            "u_context_v2",
            video_id="v2",
            role="validation_context_unit",
            comment_ids=["c5"],
            tokens=50,
            time_start="2026-06-02T09:30:00Z",
        ),
    ]
    payload = {
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
        "analysis_window_start_utc": "2026-06-01T00:00:00Z",
        "analysis_window_end_utc": "2026-06-04T00:00:00Z",
        "data_cutoff_utc": "2026-06-04T00:00:00Z",
        "alert_evidence_comment_count": 3,
        "validation_context_comment_count": 5,
        "alert_evidence_unit_count": 2,
        "validation_context_unit_count": 2,
        "video_ids": ["v1", "v2"],
        "context_unit_ids": [unit["context_unit_id"] for unit in units],
        "estimated_input_tokens": sum(unit["estimated_tokens"] for unit in units),
        "context_size_status": "requires_context_selection_policy",
        "consumer_run_id": "dconsumer_test",
        "signal_summary": {},
        "alert_evidence_units": units[:2],
        "validation_context_units": units[2:],
        "used_context_units": units,
        "used_context_unit_count": len(units),
        "grouping_by_video": [
            {
                "video_id": "v1",
                "alert_evidence_comment_count": 2,
                "validation_context_comment_count": 3,
            },
            {
                "video_id": "v2",
                "alert_evidence_comment_count": 1,
                "validation_context_comment_count": 2,
            },
        ],
        "limitations": [],
    }
    _write_jsonl(consumer / "daily_rag_context_payloads.jsonl", [payload])
    _write_jsonl(consumer / "daily_rag_validation_inputs.jsonl", [{"daily_event_id": "dfe_test"}])
    _write_jsonl(consumer / "daily_rag_context_size_report.jsonl", [{"daily_event_id": "dfe_test"}])
    _write_json(consumer / "daily_rag_consumer_manifest.json", {"run_id": "dconsumer_test"})
    _write_jsonl(
        consumer / "daily_rag_validation_reports_stub.jsonl",
        [{"daily_event_id": "dfe_test", "validation_status": "not_evaluated"}],
    )

    inventory_rows = []
    context_map_rows = []
    for index, comment_id in enumerate(["c1", "c2", "c3", "c4", "c5"], start=1):
        video_id = "v1" if comment_id in {"c1", "c2", "c4"} else "v2"
        is_alert = comment_id in {"c1", "c2", "c3"}
        inventory_rows.append(
            {
                "daily_rag_event_id": "drage_test",
                "daily_event_id": "dfe_test",
                "cycle_id": "cyc_1",
                "cycle_index": 1,
                "comment_id": comment_id,
                "video_id": video_id,
                "event_time_utc": f"2026-06-03T1{index}:00:00Z",
                "text": comment_id,
                "is_alert_evidence": is_alert,
                "is_validation_context": True,
                "temporal_role": "alert_evidence" if is_alert else "validation_context_prior",
                "data_cutoff_utc": "2026-06-04T00:00:00Z",
            }
        )
    for unit in units:
        for order, comment_id in enumerate(unit["comment_ids"], start=1):
            context_map_rows.append(
                {
                    "context_unit_id": unit["context_unit_id"],
                    "daily_rag_event_id": "drage_test",
                    "daily_event_id": "dfe_test",
                    "cycle_id": "cyc_1",
                    "video_id": unit["video_id"],
                    "comment_id": comment_id,
                    "order_in_context_unit": order,
                    "event_time_utc": "2026-06-03T10:00:00Z",
                    "is_alert_evidence": unit["context_role"] == "alert_evidence_unit",
                    "is_validation_context": True,
                    "temporal_role": (
                        "alert_evidence"
                        if unit["context_role"] == "alert_evidence_unit"
                        else "validation_context_prior"
                    ),
                    "context_type": "video_time_block",
                }
            )
    pd.DataFrame(inventory_rows).to_csv(sidecars / "daily_event_comment_inventory.csv", index=False)
    _write_jsonl(sidecars / "daily_rag_context_units.jsonl", units)
    pd.DataFrame(context_map_rows).to_csv(sidecars / "daily_context_unit_comment_map.csv", index=False)
    return consumer, sidecars


class DailyRagContextSelectionTests(unittest.TestCase):
    def test_selects_alert_units_before_validation_and_maps_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer, sidecars = _make_inputs(root)
            output_dir = root / "selection"

            summary = write_daily_context_selection_artifacts_from_config(
                DailyContextSelectionConfig(
                    consumer_dir=str(consumer),
                    sidecars_dir=str(sidecars),
                    output_dir=str(output_dir),
                    max_selected_tokens_per_event=500,
                )
            )

            self.assertEqual(summary["validation_status"], "passed")
            selected = json.loads(
                (output_dir / "daily_rag_selected_context_payloads.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )
            self.assertEqual(selected["context_selection_status"], "complete_within_token_limit")
            roles = [unit["context_role"] for unit in selected["selected_context_units"]]
            self.assertEqual(roles[:2], ["alert_evidence_unit", "alert_evidence_unit"])
            self.assertIn("u_context_v1", selected["selected_validation_context_unit_ids"])
            unit_map = pd.read_csv(output_dir / "daily_context_selection_unit_map.csv")
            self.assertEqual(set(unit_map["comment_id"]), {"c1", "c2", "c3", "c4", "c5"})

    def test_marks_partial_when_budget_prevents_second_video_alert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer, sidecars = _make_inputs(root, second_video_tokens=200)
            output_dir = root / "selection"

            write_daily_context_selection_artifacts_from_config(
                DailyContextSelectionConfig(
                    consumer_dir=str(consumer),
                    sidecars_dir=str(sidecars),
                    output_dir=str(output_dir),
                    max_selected_tokens_per_event=120,
                    alert_coverage_target=1.0,
                )
            )

            selected = json.loads(
                (output_dir / "daily_rag_selected_context_payloads.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )
            self.assertEqual(selected["context_selection_status"], "partial_due_to_token_limit")
            self.assertLessEqual(selected["selected_token_estimate"], 120)
            self.assertEqual(selected["selected_video_ids"], ["v1"])
            omissions = pd.read_csv(output_dir / "daily_context_selection_omissions.csv")
            reasons = dict(zip(omissions["context_unit_id"], omissions["omission_reason"], strict=False))
            self.assertEqual(reasons["u_alert_v2"], "token_limit")
            self.assertEqual(reasons["u_context_v2"], "video_quota_reached")

    def test_rejects_generative_or_external_flags(self) -> None:
        with self.assertRaises(ValueError):
            DailyContextSelectionConfig(run_llm=True).validate()
        with self.assertRaises(ValueError):
            DailyContextSelectionConfig(run_serper=True).validate()
        with self.assertRaises(ValueError):
            DailyContextSelectionConfig(use_embeddings=True).validate()
        with self.assertRaises(ValueError):
            DailyContextSelectionConfig(use_vectorstore=True).validate()


if __name__ == "__main__":
    unittest.main()
