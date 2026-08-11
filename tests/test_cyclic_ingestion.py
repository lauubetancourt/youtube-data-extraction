from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from youtube_pipeline.cyclic_ingestion import (
    CyclicIngestionConfig,
    build_cyclic_ingestion_dry_run,
)


class CyclicIngestionTests(unittest.TestCase):
    def _write_comments(self, path: Path, rows: list[dict]) -> None:
        pd.DataFrame(rows).to_parquet(path, index=False)

    def test_cycle_windows_use_local_calendar_and_utc_cutoffs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_path = base / "comments.parquet"
            output_dir = base / "cyclic"
            self._write_comments(
                input_path,
                [
                    {
                        "comment_id": "c1",
                        "video_id": "v1",
                        "event_time_utc": "2026-05-30T17:00:00Z",
                    },
                    {
                        "comment_id": "c2",
                        "video_id": "v1",
                        "event_time_utc": "2026-05-31T15:00:00Z",
                    },
                    {
                        "comment_id": "c3",
                        "video_id": "v2",
                        "event_time_utc": "2026-06-01T14:00:00Z",
                    },
                    {
                        "comment_id": "c4",
                        "video_id": "v2",
                        "event_time_utc": "2026-06-02T05:00:00Z",
                    },
                ],
            )

            summary = build_cyclic_ingestion_dry_run(
                CyclicIngestionConfig(
                    input_path=input_path,
                    output_dir=output_dir,
                    collection_start_date_local="2026-05-30",
                    collection_end_date_local="2026-06-02",
                    analysis_window_size_days=3,
                    simulation_run_id="sim_test",
                )
            )

            self.assertEqual(summary["cycles_total"], 4)
            cycles = [
                json.loads(line)
                for line in (output_dir / "cycle_manifest.jsonl").read_text().splitlines()
            ]
            june_first_cycle = cycles[-2]
            self.assertEqual(
                june_first_cycle["cycle_run_at_local"], "2026-06-02T00:00:00-0500"
            )
            self.assertEqual(june_first_cycle["cycle_run_at_utc"], "2026-06-02T05:00:00Z")
            self.assertEqual(
                june_first_cycle["collection_window_start_utc"],
                "2026-06-01T05:00:00Z",
            )
            self.assertEqual(
                june_first_cycle["collection_window_end_utc"],
                "2026-06-02T05:00:00Z",
            )
            self.assertEqual(june_first_cycle["new_comment_count"], 1)
            self.assertEqual(june_first_cycle["cumulative_comment_count"], 3)
            self.assertEqual(june_first_cycle["analysis_comment_count"], 3)
            self.assertEqual(june_first_cycle["future_leak_count"], 0)
            boundary_cycle = cycles[-1]
            self.assertEqual(boundary_cycle["cycle_run_at_local"], "2026-06-03T00:00:00-0500")
            self.assertEqual(boundary_cycle["new_comment_count"], 1)
            self.assertEqual(boundary_cycle["cumulative_comment_count"], 4)

    def test_duplicates_are_not_counted_as_new_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_path = base / "comments.parquet"
            output_dir = base / "cyclic"
            self._write_comments(
                input_path,
                [
                    {
                        "comment_id": "dup",
                        "video_id": "v1",
                        "event_time_utc": "2026-06-01T12:00:00Z",
                    },
                    {
                        "comment_id": "dup",
                        "video_id": "v1",
                        "event_time_utc": "2026-06-01T12:00:00Z",
                    },
                    {
                        "comment_id": "unique",
                        "video_id": "v1",
                        "event_time_utc": "2026-06-01T13:00:00Z",
                    },
                ],
            )

            summary = build_cyclic_ingestion_dry_run(
                CyclicIngestionConfig(
                    input_path=input_path,
                    output_dir=output_dir,
                    collection_start_date_local="2026-06-01",
                    collection_end_date_local="2026-06-01",
                    simulation_run_id="sim_dups",
                )
            )

            self.assertEqual(summary["unique_comment_count"], 2)
            self.assertEqual(summary["duplicate_row_count"], 1)
            cycle = json.loads(
                (output_dir / "cycle_manifest.jsonl").read_text().splitlines()[0]
            )
            self.assertEqual(cycle["new_comment_count"], 2)
            self.assertEqual(cycle["duplicate_row_count"], 1)
            quality = [
                json.loads(line)
                for line in (output_dir / "cycle_quality_report.jsonl")
                .read_text()
                .splitlines()
            ]
            duplicate_check = [
                row for row in quality if row["check_name"] == "duplicate_comment_id"
            ][0]
            self.assertEqual(duplicate_check["status"], "warning")


if __name__ == "__main__":
    unittest.main()
