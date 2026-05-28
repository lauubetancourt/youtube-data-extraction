#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from youtube_pipeline.rag_verification import verify_rag_artifacts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify non-invasive RAG evidence and validation-preparation artifacts. "
            "This script only reads artifacts and does not run retrieval, generation, "
            "or detection."
        )
    )
    parser.add_argument(
        "--evidence-dir",
        default=None,
        help="Directory containing event evidence artifacts.",
    )
    parser.add_argument(
        "--validation-dir",
        default=None,
        help="Directory containing RAG validation preparation artifacts.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional JSON path where the verification report will be written.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when warnings are present.",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if not args.evidence_dir and not args.validation_dir:
        parser.error("--evidence-dir, --validation-dir, or both are required.")

    try:
        report = verify_rag_artifacts(
            evidence_dir=args.evidence_dir,
            validation_dir=args.validation_dir,
            report_path=args.report_path,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["status"] != "passed":
        raise SystemExit(1)
    if args.strict and report["warning_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
