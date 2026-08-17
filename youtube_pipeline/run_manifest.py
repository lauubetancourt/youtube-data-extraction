from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from youtube_pipeline.configuration import ResolvedRunConfig


RUN_MANIFEST_FILE = "run_manifest.json"
RUN_MANIFEST_SCHEMA_VERSION = "1"


def build_run_manifest(
    resolved: ResolvedRunConfig,
    *,
    execution_mode: str,
    completed_stages: Sequence[str],
) -> dict[str, Any]:
    """Build one compact execution-level manifest from the resolved config."""

    if not isinstance(resolved, ResolvedRunConfig):
        raise TypeError("resolved must be ResolvedRunConfig.")
    if not isinstance(execution_mode, str) or not execution_mode.strip():
        raise ValueError("execution_mode must not be empty.")
    stage_names = list(completed_stages)
    if not stage_names or any(
        not isinstance(name, str) or not name.strip() for name in stage_names
    ):
        raise ValueError("completed_stages must contain non-empty stage names.")

    effective_config = json.loads(resolved.canonical_json)
    if not isinstance(effective_config, dict):
        raise TypeError("resolved_config must serialize to an object.")
    return {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": resolved.config.identity.run_id,
        "status": "completed",
        "execution_mode": execution_mode,
        "config_hash": resolved.config_hash,
        "resolved_config": effective_config,
        "completed_stages": stage_names,
    }


def write_run_manifest(
    resolved: ResolvedRunConfig,
    *,
    output_dir: str | Path,
    execution_mode: str,
    completed_stages: Sequence[str],
    filename: str = RUN_MANIFEST_FILE,
) -> Path:
    """Persist the single execution-level configuration manifest."""

    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must not be empty.")
    if Path(filename).name != filename:
        raise ValueError("filename must be a file name without directories.")
    output = Path(output_dir) / filename
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_run_manifest(
        resolved,
        execution_mode=execution_mode,
        completed_stages=completed_stages,
    )
    output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


__all__ = [
    "build_run_manifest",
    "RUN_MANIFEST_FILE",
    "RUN_MANIFEST_SCHEMA_VERSION",
    "write_run_manifest",
]
