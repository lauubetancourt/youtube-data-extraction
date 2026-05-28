from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .rag_evidence import (
    EVENT_CANDIDATES_FILE,
    EVENT_COMMENT_MAP_FILE,
    EVENT_EVIDENCE_PACKAGES_FILE,
    EVENT_SIGNAL_SNAPSHOT_MAP_FILE,
    RAG_EVIDENCE_SUMMARY_FILE,
    RUN_MANIFEST_FILE,
    write_json,
)
from .rag_validation import (
    EXTERNAL_EVIDENCE_FILE,
    RAG_QUERIES_FILE,
    RETRIEVAL_QUESTIONS_FILE,
    VALIDATION_MANIFEST_FILE,
    VALIDATION_RESULTS_FILE,
    VALIDATION_SUMMARY_FILE,
    VALIDATION_TASKS_FILE,
)


EVIDENCE_REQUIRED_FILES = {
    "run_manifest": RUN_MANIFEST_FILE,
    "event_candidates": EVENT_CANDIDATES_FILE,
    "event_comment_map": EVENT_COMMENT_MAP_FILE,
    "event_signal_snapshot_map": EVENT_SIGNAL_SNAPSHOT_MAP_FILE,
    "event_evidence_packages": EVENT_EVIDENCE_PACKAGES_FILE,
    "summary": RAG_EVIDENCE_SUMMARY_FILE,
}

VALIDATION_REQUIRED_FILES = {
    "manifest": VALIDATION_MANIFEST_FILE,
    "validation_tasks": VALIDATION_TASKS_FILE,
    "retrieval_questions": RETRIEVAL_QUESTIONS_FILE,
    "rag_queries": RAG_QUERIES_FILE,
    "external_evidence": EXTERNAL_EVIDENCE_FILE,
    "validation_results": VALIDATION_RESULTS_FILE,
    "summary": VALIDATION_SUMMARY_FILE,
}

EVIDENCE_EVENT_COLUMNS = {
    "event_id",
    "run_id",
    "detector_name",
    "trigger_time_utc",
    "trigger_time_unix_s",
    "window_start_utc",
    "window_end_utc",
    "trigger_volume",
    "decision_level",
    "comment_count",
    "unique_video_count",
    "unique_author_count",
    "event_artifact_version",
}

EVIDENCE_COMMENT_COLUMNS = {
    "event_id",
    "run_id",
    "order_in_event",
    "trigger_time_utc",
    "window_start_utc",
    "window_end_utc",
    "event_time_utc",
    "event_time_unix_s",
    "video_id",
    "comment_id",
    "text",
    "comment_source_path",
}

EVIDENCE_PACKAGE_FIELDS = {
    "event_id",
    "run_id",
    "trigger_time_utc",
    "window_start_utc",
    "window_end_utc",
    "event_candidate_path",
    "event_comment_map_path",
    "source_dataset_path",
    "package_artifact_version",
    "rag_readiness_status",
    "comment_count",
    "signal_snapshot_count",
}

VALIDATION_TASK_COLUMNS = {
    "validation_task_id",
    "validation_run_id",
    "event_id",
    "run_id",
    "trigger_time_utc",
    "window_start_utc",
    "window_end_utc",
    "event_evidence_package_path",
    "event_candidate_path",
    "event_comment_map_path",
    "event_signal_snapshot_map_path",
    "comment_count",
    "signal_snapshot_count",
    "rag_readiness_status",
    "validation_status",
    "validator",
    "created_at_utc",
    "artifact_version",
}

RETRIEVAL_QUESTION_COLUMNS = {
    "question_id",
    "validation_run_id",
    "event_id",
    "question_order",
    "question_type",
    "question_text",
    "question_status",
    "artifact_version",
}

RAG_QUERY_COLUMNS = {
    "query_id",
    "validation_run_id",
    "event_id",
    "trigger_time_utc",
    "video_id",
    "news_api_query",
    "query_language",
    "query_time_window_start_utc",
    "query_time_window_end_utc",
    "query_source",
    "query_status",
    "artifact_version",
}

EXTERNAL_EVIDENCE_COLUMNS = {
    "evidence_id",
    "query_id",
    "event_id",
    "title",
    "link",
    "snippet",
    "date",
    "source",
    "retrieved_at_utc",
    "retrieval_provider",
    "artifact_version",
}

VALIDATION_RESULT_COLUMNS = {
    "validation_id",
    "validation_run_id",
    "event_id",
    "validation_label",
    "validation_status",
    "n_external_sources",
    "rationale",
    "supporting_evidence_ids",
    "contradictory_evidence_ids",
    "limitations",
    "validated_at_utc",
    "prepared_at_utc",
    "validator",
    "artifact_version",
}


@dataclass(frozen=True)
class RagArtifactVerificationConfig:
    evidence_dir: str | None = None
    validation_dir: str | None = None
    report_path: str | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "RagArtifactVerificationConfig":
        evidence_dir = payload.get("evidence_dir")
        validation_dir = payload.get("validation_dir")
        report_path = payload.get("report_path")
        if not evidence_dir and not validation_dir:
            raise ValueError(
                "RAG verification config requires evidence_dir, validation_dir, or both."
            )
        return cls(
            evidence_dir=str(evidence_dir) if evidence_dir else None,
            validation_dir=str(validation_dir) if validation_dir else None,
            report_path=str(report_path) if report_path else None,
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return Path(path).as_posix()


def _new_report(config: RagArtifactVerificationConfig) -> dict[str, Any]:
    return {
        "created_at_utc": _utc_now_iso(),
        "verification_mode": "rag_artifact_contract_consistency",
        "inputs": {
            "evidence_dir": _normalize_path(config.evidence_dir),
            "validation_dir": _normalize_path(config.validation_dir),
        },
        "checks": [],
        "evidence": {},
        "validation": {},
        "cross_artifact": {},
    }


def _add_check(
    report: dict[str, Any],
    name: str,
    status: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> None:
    report["checks"].append(
        {
            "name": name,
            "status": status,
            "message": message,
            "details": details or {},
        }
    )


def _read_json(path: Path, report: dict[str, Any], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _add_check(report, f"{label}.read_json", "error", f"Missing JSON file: {path}")
        return {}
    except json.JSONDecodeError as exc:
        _add_check(
            report,
            f"{label}.read_json",
            "error",
            f"Invalid JSON file: {path}",
            details={"error": str(exc)},
        )
        return {}
    if not isinstance(payload, dict):
        _add_check(report, f"{label}.read_json", "error", f"JSON must be an object: {path}")
        return {}
    _add_check(report, f"{label}.read_json", "passed", f"Read JSON file: {path}")
    return payload


def _read_jsonl(path: Path, report: dict[str, Any], label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        _add_check(report, f"{label}.read_jsonl", "error", f"Missing JSONL file: {path}")
        return rows
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            _add_check(
                report,
                f"{label}.read_jsonl",
                "error",
                f"Invalid JSONL record in {path}",
                details={"line": line_no, "error": str(exc)},
            )
            continue
        if not isinstance(payload, dict):
            _add_check(
                report,
                f"{label}.read_jsonl",
                "error",
                f"JSONL record must be an object in {path}",
                details={"line": line_no},
            )
            continue
        rows.append(payload)
    _add_check(
        report,
        f"{label}.read_jsonl",
        "passed",
        f"Read JSONL file: {path}",
        details={"record_count": len(rows)},
    )
    return rows


def _read_csv(path: Path, report: dict[str, Any], label: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        _add_check(report, f"{label}.read_csv", "error", f"Missing CSV file: {path}")
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        _add_check(report, f"{label}.read_csv", "error", f"CSV has no header: {path}")
        return pd.DataFrame()
    _add_check(
        report,
        f"{label}.read_csv",
        "passed",
        f"Read CSV file: {path}",
        details={"row_count": int(len(df)), "column_count": int(len(df.columns))},
    )
    return df


def _check_files(
    root: Path,
    required: dict[str, str],
    report: dict[str, Any],
    namespace: str,
) -> dict[str, Path]:
    paths = {name: root / filename for name, filename in required.items()}
    missing = sorted(name for name, path in paths.items() if not path.exists())
    if missing:
        _add_check(
            report,
            f"{namespace}.required_files",
            "error",
            f"Missing required {namespace} artifact files.",
            details={"missing": missing},
        )
    else:
        _add_check(
            report,
            f"{namespace}.required_files",
            "passed",
            f"All required {namespace} artifact files are present.",
        )
    return paths


def _check_columns(
    df: pd.DataFrame,
    required: set[str],
    report: dict[str, Any],
    name: str,
) -> None:
    missing = sorted(required.difference(df.columns))
    if missing:
        _add_check(
            report,
            f"{name}.required_columns",
            "error",
            "Required columns are missing.",
            details={"missing": missing},
        )
    else:
        _add_check(report, f"{name}.required_columns", "passed", "Required columns exist.")


def _check_unique(df: pd.DataFrame, column: str, report: dict[str, Any], name: str) -> None:
    if column not in df.columns:
        return
    duplicate_count = int(df[column].duplicated().sum())
    if duplicate_count:
        _add_check(
            report,
            f"{name}.{column}.unique",
            "error",
            f"Column {column} contains duplicate values.",
            details={"duplicate_count": duplicate_count},
        )
    else:
        _add_check(report, f"{name}.{column}.unique", "passed", f"Column {column} is unique.")


def _event_ids(df: pd.DataFrame) -> set[str]:
    if "event_id" not in df.columns:
        return set()
    return {str(value) for value in df["event_id"].dropna().unique()}


def _count_by_event(df: pd.DataFrame, column: str) -> dict[str, int]:
    if df.empty or "event_id" not in df.columns or column not in df.columns:
        return {}
    return {
        str(event_id): int(count)
        for event_id, count in df.groupby("event_id")[column].nunique().items()
    }


def _numeric_count_by_event(df: pd.DataFrame, column: str) -> dict[str, int]:
    if df.empty or "event_id" not in df.columns or column not in df.columns:
        return {}
    out: dict[str, int] = {}
    for _, row in df[["event_id", column]].drop_duplicates("event_id").iterrows():
        value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
        out[str(row["event_id"])] = 0 if pd.isna(value) else int(value)
    return out


def _check_event_subset(
    child_ids: set[str],
    parent_ids: set[str],
    report: dict[str, Any],
    name: str,
) -> None:
    extra = sorted(child_ids.difference(parent_ids))
    if extra:
        _add_check(
            report,
            name,
            "error",
            "Child artifact contains event IDs absent from the parent artifact.",
            details={"extra_event_ids": extra[:20], "extra_count": len(extra)},
        )
    else:
        _add_check(report, name, "passed", "Event IDs are compatible.")


def _check_count_match(
    expected: dict[str, int],
    observed: dict[str, int],
    report: dict[str, Any],
    name: str,
) -> None:
    mismatches = []
    for event_id, expected_count in expected.items():
        observed_count = observed.get(event_id, 0)
        if expected_count != observed_count:
            mismatches.append(
                {
                    "event_id": event_id,
                    "expected": expected_count,
                    "observed": observed_count,
                }
            )
    if mismatches:
        _add_check(
            report,
            name,
            "error",
            "Per-event counts do not match.",
            details={"mismatches": mismatches[:20], "mismatch_count": len(mismatches)},
        )
    else:
        _add_check(report, name, "passed", "Per-event counts match.")


def _check_comment_windows(event_comment_map: pd.DataFrame, report: dict[str, Any]) -> None:
    required = {"event_time_utc", "window_start_utc", "window_end_utc"}
    if event_comment_map.empty or required.difference(event_comment_map.columns):
        return
    event_times = pd.to_datetime(event_comment_map["event_time_utc"], utc=True, errors="coerce")
    starts = pd.to_datetime(event_comment_map["window_start_utc"], utc=True, errors="coerce")
    ends = pd.to_datetime(event_comment_map["window_end_utc"], utc=True, errors="coerce")
    invalid_timestamp_count = int((event_times.isna() | starts.isna() | ends.isna()).sum())
    out_of_window_count = int(((event_times < starts) | (event_times > ends)).sum())
    if invalid_timestamp_count:
        _add_check(
            report,
            "evidence.comment_windows.parse",
            "error",
            "Some event-comment map timestamps could not be parsed.",
            details={"invalid_timestamp_count": invalid_timestamp_count},
        )
    else:
        _add_check(
            report,
            "evidence.comment_windows.parse",
            "passed",
            "Event-comment map timestamps are parseable as UTC.",
        )
    if out_of_window_count:
        _add_check(
            report,
            "evidence.comment_windows.bounds",
            "error",
            "Some comments fall outside their event window.",
            details={"out_of_window_count": out_of_window_count},
        )
    else:
        _add_check(
            report,
            "evidence.comment_windows.bounds",
            "passed",
            "All comments fall inside their event windows.",
        )


def _check_event_time_seconds(event_comment_map: pd.DataFrame, report: dict[str, Any]) -> None:
    required = {"event_time_utc", "event_time_unix_s"}
    if event_comment_map.empty or required.difference(event_comment_map.columns):
        return
    event_times = pd.to_datetime(event_comment_map["event_time_utc"], utc=True, errors="coerce")
    unix_s = pd.to_numeric(event_comment_map["event_time_unix_s"], errors="coerce")
    expected = event_times.map(lambda value: int(value.timestamp()) if pd.notna(value) else pd.NA)
    mismatch_count = int((unix_s.fillna(-1).astype("int64") != expected.fillna(-2).astype("int64")).sum())
    if mismatch_count:
        _add_check(
            report,
            "evidence.event_time_unix_s",
            "error",
            "event_time_unix_s does not match event_time_utc for some rows.",
            details={"mismatch_count": mismatch_count},
        )
    else:
        _add_check(
            report,
            "evidence.event_time_unix_s",
            "passed",
            "event_time_unix_s matches event_time_utc.",
        )


def _check_order_in_event(event_comment_map: pd.DataFrame, report: dict[str, Any]) -> None:
    if event_comment_map.empty or "event_id" not in event_comment_map.columns or "order_in_event" not in event_comment_map.columns:
        return
    mismatches = []
    for event_id, group in event_comment_map.groupby("event_id"):
        observed = sorted(pd.to_numeric(group["order_in_event"], errors="coerce").dropna().astype(int).tolist())
        expected = list(range(1, len(group) + 1))
        if observed != expected:
            mismatches.append(str(event_id))
    if mismatches:
        _add_check(
            report,
            "evidence.order_in_event",
            "error",
            "order_in_event is not sequential within some events.",
            details={"event_ids": mismatches[:20], "event_count": len(mismatches)},
        )
    else:
        _add_check(
            report,
            "evidence.order_in_event",
            "passed",
            "order_in_event is sequential within each event.",
        )


def _verify_evidence_dir(evidence_dir: str | Path, report: dict[str, Any]) -> dict[str, Any]:
    root = Path(evidence_dir)
    paths = _check_files(root, EVIDENCE_REQUIRED_FILES, report, "evidence")
    manifest = _read_json(paths["run_manifest"], report, "evidence.run_manifest")
    summary = _read_json(paths["summary"], report, "evidence.summary")
    event_candidates = _read_csv(paths["event_candidates"], report, "evidence.event_candidates")
    event_comment_map = _read_csv(paths["event_comment_map"], report, "evidence.event_comment_map")
    signal_map = _read_csv(paths["event_signal_snapshot_map"], report, "evidence.event_signal_snapshot_map")
    packages = _read_jsonl(paths["event_evidence_packages"], report, "evidence.event_evidence_packages")

    _check_columns(event_candidates, EVIDENCE_EVENT_COLUMNS, report, "evidence.event_candidates")
    _check_columns(event_comment_map, EVIDENCE_COMMENT_COLUMNS, report, "evidence.event_comment_map")
    _check_unique(event_candidates, "event_id", report, "evidence.event_candidates")

    package_missing = []
    for index, package in enumerate(packages, start=1):
        missing = sorted(EVIDENCE_PACKAGE_FIELDS.difference(package))
        if missing:
            package_missing.append({"record": index, "missing": missing})
    if package_missing:
        _add_check(
            report,
            "evidence.event_evidence_packages.required_fields",
            "error",
            "Some evidence package records are missing required fields.",
            details={"records": package_missing[:20], "record_count": len(package_missing)},
        )
    else:
        _add_check(
            report,
            "evidence.event_evidence_packages.required_fields",
            "passed",
            "Evidence package records contain required fields.",
        )

    event_candidate_ids = _event_ids(event_candidates)
    comment_event_ids = _event_ids(event_comment_map)
    signal_event_ids = _event_ids(signal_map)
    package_event_ids = {str(package.get("event_id")) for package in packages if package.get("event_id")}
    _check_event_subset(comment_event_ids, event_candidate_ids, report, "evidence.comment_map.event_ids")
    _check_event_subset(signal_event_ids, event_candidate_ids, report, "evidence.signal_map.event_ids")
    _check_event_subset(package_event_ids, event_candidate_ids, report, "evidence.packages.event_ids")
    missing_packages = sorted(event_candidate_ids.difference(package_event_ids))
    if missing_packages:
        _add_check(
            report,
            "evidence.packages.coverage",
            "error",
            "Some event candidates have no evidence package.",
            details={"event_ids": missing_packages[:20], "event_count": len(missing_packages)},
        )
    else:
        _add_check(
            report,
            "evidence.packages.coverage",
            "passed",
            "Every event candidate has an evidence package.",
        )

    candidate_comment_counts = _numeric_count_by_event(event_candidates, "comment_count")
    observed_comment_counts = _count_by_event(event_comment_map, "comment_id")
    package_comment_counts = {
        str(package["event_id"]): int(package.get("comment_count") or 0)
        for package in packages
        if package.get("event_id")
    }
    _check_count_match(
        candidate_comment_counts,
        observed_comment_counts,
        report,
        "evidence.candidate_comment_counts",
    )
    _check_count_match(
        package_comment_counts,
        observed_comment_counts,
        report,
        "evidence.package_comment_counts",
    )

    _check_comment_windows(event_comment_map, report)
    _check_event_time_seconds(event_comment_map, report)
    _check_order_in_event(event_comment_map, report)

    if summary:
        expected_counts = {
            "event_count": len(event_candidates),
            "event_comment_rows": len(event_comment_map),
            "event_signal_snapshot_rows": len(signal_map),
            "ready_packages": sum(
                1 for package in packages if package.get("rag_readiness_status") == "ready"
            ),
        }
        mismatches = {
            key: {"summary": summary.get(key), "observed": value}
            for key, value in expected_counts.items()
            if summary.get(key) != value
        }
        if mismatches:
            _add_check(
                report,
                "evidence.summary.counts",
                "error",
                "Evidence summary counts do not match artifact contents.",
                details=mismatches,
            )
        else:
            _add_check(
                report,
                "evidence.summary.counts",
                "passed",
                "Evidence summary counts match artifact contents.",
            )

    report["evidence"] = {
        "path": root.as_posix(),
        "run_id": manifest.get("run_id") or summary.get("run_id"),
        "event_count": int(len(event_candidates)),
        "event_comment_rows": int(len(event_comment_map)),
        "event_signal_snapshot_rows": int(len(signal_map)),
        "evidence_package_count": int(len(packages)),
        "ready_package_count": int(
            sum(1 for package in packages if package.get("rag_readiness_status") == "ready")
        ),
    }
    return {
        "event_ids": event_candidate_ids,
        "packages": packages,
        "event_comment_map": event_comment_map,
    }


def _verify_validation_dir(
    validation_dir: str | Path,
    report: dict[str, Any],
) -> dict[str, Any]:
    root = Path(validation_dir)
    paths = _check_files(root, VALIDATION_REQUIRED_FILES, report, "validation")
    manifest = _read_json(paths["manifest"], report, "validation.manifest")
    summary = _read_json(paths["summary"], report, "validation.summary")
    tasks = _read_csv(paths["validation_tasks"], report, "validation.validation_tasks")
    questions = _read_csv(paths["retrieval_questions"], report, "validation.retrieval_questions")
    queries = _read_csv(paths["rag_queries"], report, "validation.rag_queries")
    external_evidence = _read_csv(paths["external_evidence"], report, "validation.external_evidence")
    results = _read_csv(paths["validation_results"], report, "validation.validation_results")

    _check_columns(tasks, VALIDATION_TASK_COLUMNS, report, "validation.validation_tasks")
    _check_columns(questions, RETRIEVAL_QUESTION_COLUMNS, report, "validation.retrieval_questions")
    _check_columns(queries, RAG_QUERY_COLUMNS, report, "validation.rag_queries")
    _check_columns(external_evidence, EXTERNAL_EVIDENCE_COLUMNS, report, "validation.external_evidence")
    _check_columns(results, VALIDATION_RESULT_COLUMNS, report, "validation.validation_results")
    _check_unique(tasks, "validation_task_id", report, "validation.validation_tasks")
    _check_unique(questions, "question_id", report, "validation.retrieval_questions")
    _check_unique(queries, "query_id", report, "validation.rag_queries")
    _check_unique(results, "validation_id", report, "validation.validation_results")

    task_event_ids = _event_ids(tasks)
    question_event_ids = _event_ids(questions)
    query_event_ids = _event_ids(queries)
    result_event_ids = _event_ids(results)
    _check_event_subset(question_event_ids, task_event_ids, report, "validation.questions.event_ids")
    _check_event_subset(query_event_ids, task_event_ids, report, "validation.queries.event_ids")
    _check_event_subset(result_event_ids, task_event_ids, report, "validation.results.event_ids")
    missing_results = sorted(task_event_ids.difference(result_event_ids))
    if missing_results:
        _add_check(
            report,
            "validation.results.coverage",
            "error",
            "Some validation tasks have no pending result row.",
            details={"event_ids": missing_results[:20], "event_count": len(missing_results)},
        )
    else:
        _add_check(
            report,
            "validation.results.coverage",
            "passed",
            "Every validation task has a result row.",
        )

    if "validation_status" in tasks.columns:
        bad_status = int((tasks["validation_status"] != "needs_external_evidence").sum())
        if bad_status:
            _add_check(
                report,
                "validation.tasks.pending_status",
                "warning",
                "Some validation tasks are not marked as needs_external_evidence.",
                details={"row_count": bad_status},
            )
        else:
            _add_check(
                report,
                "validation.tasks.pending_status",
                "passed",
                "Validation tasks are pending external evidence.",
            )
    if "validation_status" in results.columns:
        bad_status = int((results["validation_status"] != "needs_external_evidence").sum())
        if bad_status:
            _add_check(
                report,
                "validation.results.pending_status",
                "warning",
                "Some validation results are not marked as needs_external_evidence.",
                details={"row_count": bad_status},
            )
        else:
            _add_check(
                report,
                "validation.results.pending_status",
                "passed",
                "Validation results are pending external evidence.",
            )

    if summary:
        expected_counts = {
            "validation_task_count": len(tasks),
            "retrieval_question_count": len(questions),
            "rag_query_placeholder_count": len(queries),
            "external_evidence_count": len(external_evidence),
            "pending_validation_count": int(
                (results.get("validation_status", pd.Series(dtype=str)) == "needs_external_evidence").sum()
            ),
        }
        mismatches = {
            key: {"summary": summary.get(key), "observed": value}
            for key, value in expected_counts.items()
            if summary.get(key) != value
        }
        if mismatches:
            _add_check(
                report,
                "validation.summary.counts",
                "error",
                "Validation summary counts do not match artifact contents.",
                details=mismatches,
            )
        else:
            _add_check(
                report,
                "validation.summary.counts",
                "passed",
                "Validation summary counts match artifact contents.",
            )

    mode = manifest.get("mode") or summary.get("mode")
    if mode != "contract_only_no_retrieval_no_generation":
        _add_check(
            report,
            "validation.mode",
            "warning",
            "Validation artifacts are not in contract-only preparation mode.",
            details={"mode": mode},
        )
    else:
        _add_check(
            report,
            "validation.mode",
            "passed",
            "Validation artifacts are in contract-only preparation mode.",
        )

    report["validation"] = {
        "path": root.as_posix(),
        "validation_run_id": manifest.get("validation_run_id") or summary.get("validation_run_id"),
        "validation_task_count": int(len(tasks)),
        "retrieval_question_count": int(len(questions)),
        "rag_query_placeholder_count": int(len(queries)),
        "external_evidence_count": int(len(external_evidence)),
        "pending_validation_count": int(
            (results.get("validation_status", pd.Series(dtype=str)) == "needs_external_evidence").sum()
        ),
        "mode": mode,
    }
    return {"event_ids": task_event_ids, "tasks": tasks, "results": results}


def _verify_cross_artifact_alignment(
    evidence_context: dict[str, Any],
    validation_context: dict[str, Any],
    report: dict[str, Any],
) -> None:
    evidence_event_ids = evidence_context.get("event_ids", set())
    validation_event_ids = validation_context.get("event_ids", set())
    missing_in_validation = sorted(evidence_event_ids.difference(validation_event_ids))
    extra_in_validation = sorted(validation_event_ids.difference(evidence_event_ids))
    if missing_in_validation or extra_in_validation:
        _add_check(
            report,
            "cross_artifact.event_ids",
            "error",
            "Evidence and validation event IDs do not match.",
            details={
                "missing_in_validation": missing_in_validation[:20],
                "extra_in_validation": extra_in_validation[:20],
                "missing_count": len(missing_in_validation),
                "extra_count": len(extra_in_validation),
            },
        )
    else:
        _add_check(
            report,
            "cross_artifact.event_ids",
            "passed",
            "Evidence and validation event IDs match.",
        )
    report["cross_artifact"] = {
        "evidence_event_count": len(evidence_event_ids),
        "validation_event_count": len(validation_event_ids),
        "matching_event_ids": not missing_in_validation and not extra_in_validation,
    }


def verify_rag_artifacts(
    *,
    evidence_dir: str | Path | None = None,
    validation_dir: str | Path | None = None,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    config = RagArtifactVerificationConfig.from_mapping(
        {
            "evidence_dir": evidence_dir,
            "validation_dir": validation_dir,
            "report_path": report_path,
        }
    )
    report = _new_report(config)
    evidence_context: dict[str, Any] | None = None
    validation_context: dict[str, Any] | None = None

    if config.evidence_dir:
        evidence_context = _verify_evidence_dir(config.evidence_dir, report)
    if config.validation_dir:
        validation_context = _verify_validation_dir(config.validation_dir, report)
    if evidence_context is not None and validation_context is not None:
        _verify_cross_artifact_alignment(evidence_context, validation_context, report)

    error_count = sum(1 for check in report["checks"] if check["status"] == "error")
    warning_count = sum(1 for check in report["checks"] if check["status"] == "warning")
    report["error_count"] = int(error_count)
    report["warning_count"] = int(warning_count)
    report["status"] = "failed" if error_count else "passed"
    if config.report_path:
        write_json(config.report_path, report)
    return report


__all__ = [
    "RagArtifactVerificationConfig",
    "verify_rag_artifacts",
]
