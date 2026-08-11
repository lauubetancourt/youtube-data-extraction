#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from youtube_pipeline.rag_poc import (
    RagPocConfig,
    load_rag_poc_config,
    run_rag_poc_from_config,
)


def _read_json_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON config not found: {p}")
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON config must contain an object: {p}")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the triggers_validation.ipynb RAG proof of concept as a posterior "
            "pipeline phase. The default execution preserves the notebook logic. "
            "Use --dry-run to validate contracts and write lineage without LLM, "
            "Serper, embeddings, Chroma, or external calls."
        )
    )
    parser.add_argument(
        "--config-file",
        default=None,
        help="Optional JSON config file with a rag_poc section.",
    )
    parser.add_argument(
        "--trigger-comment-map-path",
        default=None,
        help="Path to the PoC-compatible trigger_comment_map.csv input.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory where RAG PoC artifacts will be written.",
    )
    parser.add_argument(
        "--event-comment-map-path",
        default=None,
        help="Optional RAG evidence event_comment_map.csv used only for event_id lineage.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional stable RAG PoC run ID.",
    )
    parser.add_argument(
        "--openai-model",
        default=None,
        help="OpenAI chat model. Defaults to the notebook value gpt-5-mini.",
    )
    parser.add_argument(
        "--openai-temperature",
        type=float,
        default=None,
        help="OpenAI chat temperature. Defaults to the notebook value 1.",
    )
    parser.add_argument(
        "--embedding-model",
        default=None,
        help="Embedding model. Defaults to the notebook value text-embedding-ada-002.",
    )
    parser.add_argument(
        "--serper-num-results",
        type=int,
        default=None,
        help="Number of Serper news results per query. Defaults to the notebook value 5.",
    )
    parser.add_argument(
        "--serper-sleep-seconds",
        type=float,
        default=None,
        help="Delay between Serper requests. Defaults to the notebook value 1.",
    )
    parser.add_argument(
        "--params-file",
        default=None,
        help="Optional JSON file stored as run parameters in rag_poc_manifest.json.",
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional note stored in rag_poc_manifest.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate input, grouping, lineage, manifest, and summary only. "
            "Does not call LLMs, Serper, embeddings, or Chroma."
        ),
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    overrides = {
        key: value
        for key, value in {
            "trigger_comment_map_path": args.trigger_comment_map_path,
            "output_dir": args.output_dir,
            "event_comment_map_path": args.event_comment_map_path,
            "run_id": args.run_id,
            "openai_model": args.openai_model,
            "openai_temperature": args.openai_temperature,
            "embedding_model": args.embedding_model,
            "serper_num_results": args.serper_num_results,
            "serper_sleep_seconds": args.serper_sleep_seconds,
            "notes": args.notes,
        }.items()
        if value is not None
    }
    params = _read_json_file(args.params_file)
    if params:
        overrides["params"] = params

    try:
        if args.config_file:
            config = load_rag_poc_config(args.config_file, overrides=overrides)
        else:
            config = RagPocConfig.from_mapping(overrides)
    except ValueError as exc:
        parser.error(str(exc))

    summary = run_rag_poc_from_config(config, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
