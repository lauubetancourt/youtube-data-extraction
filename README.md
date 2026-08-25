# YouTube Data Extraction

This project extracts and analyzes YouTube video and comment data with the YouTube Data API.

## Features

- Search and filter videos by topic, date range, views, and comments.
- Export batch snapshots in JSONL and Parquet.
- Clean noisy comments while preserving emotional signals for polarization analysis.
- Replay historical comments as a simulated stream with Streamz.

## Project Structure

- `notebooks/`: End-to-end notebooks.
- `youtube_pipeline/`: Reusable modules for extraction, storage, cleaning, and playback.
- `scripts/`: Audit and reporting helpers used in exploratory experiments.
- `data/`: Batch and processed datasets.
- `experiments/`: Detection experiment outputs and summaries.
- `docs/pipeline_architecture.md`: Current pipeline architecture and phase boundaries.
- `docs/data_contracts.md`: Data fields, temporal units, lineage, and compatibility rules.
- `docs/rag_validation_readiness.md`: Future RAG validation contract and evidence requirements.
- `docs/rag_artifact_audit.md`: RAG-0 inventory of current artifacts, lineage gaps, and PoC evidence.
- `docs/rag_event_evidence_contract.md`: RAG-1 proposed event-evidence contract for future validation.
- `docs/rag_poc_integration.md`: Executable integration boundary for the current RAG PoC notebook.
- `docs/regression_verification.md`: Regression checks and evidence after refinement.

## Setup

The active pipeline runtime is pinned to Python 3.14.3 in `.python-version`.
`requirements-runtime.txt` is the dependency authority for the current
pipeline, maintained scripts, and test suite. The original `requirements.txt`
is retained as a legacy dependency snapshot for the earlier environment and
historical notebooks; it is not the authority for the active runtime.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install pip==26.0.1
python -m pip install -r requirements-runtime.txt
```

## Playback Experiments

The runtime timestamp field is `event_time_utc` in UTC. New numeric timestamp
fields use Unix epoch seconds, for example `event_time_unix_s`; legacy
`*_unix_ms` fields are accepted only for compatibility with existing artifacts.

The `playback` and `all` commands expose two different window configurations:

- `--window-size`: snapshot window used by `build_event_time_window_stream`.
- `--trigger-window-size`: detector sliding window used by `XiaoEMATriggerDetector`.
- `--trigger-slide-interval`: detector step size.
- `--trigger-slow-window`: detector slow EMA horizon.
- `--trigger-cooldown`: detector lock period after a trigger.
- `--detector`: detector implementation to use. The provisional default is `xiao_ema`.
- `--detector-config-file`: optional JSON file with detector name and parameters.

Example:

```bash
python youtube_pipeline/run_pipeline.py playback \
  --input-path data/gold/clean_comments.parquet \
  --output-snapshots data/gold/snapshots_log3_variant.csv \
  --window-size 20min \
  --trigger-threshold 1.5 \
  --trigger-min-volume 15 \
  --trigger-window-size 120s \
  --trigger-slide-interval 30s \
  --trigger-slow-window 10min \
  --trigger-cooldown 3min \
  --detector xiao_ema
```

## RAG Evidence Builder

The RAG evidence builder is a non-invasive helper. It reads existing experiment
outputs and writes separate RAG-preparation artifacts without changing
playback, monitoring, detection, thresholds, metrics, or existing output files.

Example:

```bash
.venv/bin/python scripts/build_rag_event_evidence.py \
  --comments-path data/gold/clean_comments.parquet \
  --trigger-comment-map-path experiments/xiao/media/log_3/trigger_comment_map.csv \
  --snapshots-path experiments/xiao/media/log_3/snapshots.csv \
  --output-dir experiments/xiao/media/log_3/rag_evidence \
  --detector-name xiao_ema \
  --snapshot-context window
```

It writes `run_manifest.json`, `event_candidates.csv`,
`event_comment_map.csv`, `event_signal_snapshot_map.csv`,
`event_evidence_packages.jsonl`, and `rag_evidence_summary.json`.

The same helper can read a JSON config:

```bash
.venv/bin/python scripts/build_rag_event_evidence.py \
  --config-file path/to/rag_evidence_config.json
```

Config shape:

```json
{
  "rag_evidence": {
    "comments_path": "data/gold/clean_comments.parquet",
    "trigger_comment_map_path": "experiments/xiao/media/log_3/trigger_comment_map.csv",
    "snapshots_path": "experiments/xiao/media/log_3/snapshots.csv",
    "output_dir": "experiments/xiao/media/log_3/rag_evidence",
    "detector_name": "xiao_ema",
    "snapshot_context": "window"
  }
}
```

## RAG Validation Preparation

The RAG validation preparation helper is also non-invasive. It consumes
`event_evidence_packages.jsonl` and creates validation tasks, retrieval
questions, query placeholders, an empty external-evidence table, and pending
validation results. It does not call LLMs, embeddings, vector stores, external
APIs, or news sources.

Example:

```bash
.venv/bin/python scripts/prepare_rag_validation.py \
  --evidence-packages-path experiments/xiao/media/log_3/rag_evidence/event_evidence_packages.jsonl \
  --output-dir experiments/xiao/media/log_3/rag_validation \
  --validator manual_pending \
  --query-language es \
  --max-videos-per-event 5
```

It writes `rag_validation_manifest.json`, `rag_validation_tasks.csv`,
`rag_retrieval_questions.csv`, `rag_queries.csv`, `external_evidence.csv`,
`validation_results.csv`, and `rag_validation_summary.json`.

## RAG PoC Validation

The current RAG proof of concept from
`.agents/examples/structured-rag-pdf/triggers_validation.ipynb` is integrated as
a posterior phase. It preserves the notebook's `trigger_time + video_id` unit,
prompts, OpenAI model, Serper query behavior, Chroma vector stores, cache file
names, and audit output schema.

Dry-run contract check:

```bash
.venv/bin/python scripts/run_rag_poc_validation.py \
  --trigger-comment-map-path experiments/xiao/media/log_3/trigger_comment_map.csv \
  --event-comment-map-path experiments/xiao/media/log_3/rag_evidence/event_comment_map.csv \
  --output-dir experiments/xiao/media/log_3/rag_poc \
  --dry-run
```

Full PoC execution:

```bash
.venv/bin/python scripts/run_rag_poc_validation.py \
  --trigger-comment-map-path experiments/xiao/media/log_3/trigger_comment_map.csv \
  --event-comment-map-path experiments/xiao/media/log_3/rag_evidence/event_comment_map.csv \
  --output-dir experiments/xiao/media/log_3/rag_poc
```

The full execution writes `queries_df.csv`, `noticias_df.csv`,
`auditoria_df.csv`, `vectorstore_comentarios/`, `vectorstore_noticias/`, and
non-functional traceability files. It may call OpenAI and Serper if cache files
are absent.

## RAG Artifact Verification

The RAG artifact verifier checks evidence and validation-preparation outputs
without changing them. It verifies required files, required columns, event ID
alignment, per-event comment counts, temporal bounds, Unix-second timestamp
consistency, pending validation rows, and summary counts.

Example:

```bash
.venv/bin/python scripts/verify_rag_artifacts.py \
  --evidence-dir experiments/xiao/media/log_3/rag_evidence \
  --validation-dir experiments/xiao/media/log_3/rag_validation \
  --report-path experiments/xiao/media/log_3/rag_validation/rag_artifact_verification_report.json
```

The script only reads artifacts. It does not run detection, retrieval,
generation, embeddings, vector stores, external APIs, or validation decisions.
