# Pipeline Architecture

This document records the current architecture of the YouTube event detection
prototype. It is descriptive only: it does not change algorithms, thresholds,
data formats, or execution behavior.

## Purpose

The pipeline supports a CRISP-DM workflow for online event detection with
YouTube comments. Its current role is to produce event candidates from activity
signals and lightweight discourse signals, while preserving enough context for
future validation.

## Phase Boundaries

| Phase | Current module or artifact | Responsibility | Main input | Main output |
|---|---|---|---|---|
| Extraction | `youtube_pipeline/data_extraction.py` | Query YouTube, filter videos, extract comments, and write run metadata. | YouTube API, extraction config, environment API key. | Dataframes, legacy CSV files, bronze/silver artifacts. |
| Storage | `youtube_pipeline/storage.py` | Normalize timestamps and persist batch snapshots in bronze/silver layout. | Video and comment dataframes. | JSONL bronze files, partitioned Parquet silver datasets. |
| Preprocessing | `youtube_pipeline/cleaning.py` | Normalize comment text, preserve emotional cues, filter high-noise records, and keep canonical temporal fields. | Silver comments or legacy comments CSV. | `data/gold/clean_comments.parquet`. |
| Stream simulation | `youtube_pipeline/replay.py` | Replay historical comments in event-time order with configurable playback speed. | Gold comments dataset. | Events emitted into a Streamz stream. |
| Signal monitoring | `youtube_pipeline/monitoring.py` | Build event-time window snapshots with activity and discourse-signal summaries. | Replayed events. | Snapshot records, usually flattened to CSV. |
| Event detection | `youtube_pipeline/detectors.py` and `youtube_pipeline/run_pipeline.py` | Create a detector through a common contract and apply it during playback. | Replayed events and detector parameters. | Trigger logs in experiments; snapshots from pipeline playback. |
| Experiment reporting | `scripts/` and `experiments/` | Inspect datasets, reconstruct trigger evidence, and summarize runs. | Gold datasets, snapshots, trigger outputs. | Audit reports, summaries, trigger maps. |
| RAG evidence preparation | `youtube_pipeline/rag_evidence.py` and `scripts/build_rag_event_evidence.py` | Assemble non-invasive event candidates, all-comment maps, signal maps, evidence packages, and execution summaries. | Gold comments, exploratory trigger-comment maps, optional snapshots, optional JSON config. | RAG evidence artifacts in a separate output directory. |
| RAG validation preparation | `youtube_pipeline/rag_validation.py` and `scripts/prepare_rag_validation.py` | Prepare posterior validation tasks, retrieval questions, query placeholders, empty external-evidence schema, and pending validation rows. | RAG evidence packages. | Contract-only validation preparation artifacts in a separate output directory. |
| RAG PoC validation | `youtube_pipeline/rag_poc.py` and `scripts/run_rag_poc_validation.py` | Execute the current `triggers_validation.ipynb` proof of concept as a posterior phase while preserving its prompts, grouping, Serper behavior, Chroma stores, and output schemas. | PoC-compatible `trigger_comment_map.csv`; optional `event_comment_map.csv` only for lineage. | `queries_df.csv`, `noticias_df.csv`, `auditoria_df.csv`, Chroma stores, manifest, lineage, and summary. |
| RAG artifact verification | `youtube_pipeline/rag_verification.py` and `scripts/verify_rag_artifacts.py` | Verify evidence and validation-preparation artifact consistency without running retrieval, generation, detection, or validation decisions. | RAG evidence and validation-preparation directories. | JSON verification report and CLI status. |
| Future RAG refinement | `docs/rag_validation_readiness.md` and `.agents/examples/structured-rag-pdf/` | Specify how the current PoC can later be refined against broader evidence and contracts. | Validation tasks, queries, retrieved evidence, event evidence packages, PoC outputs. | Future refined validation labels and rationale. |
| Regression verification | `docs/regression_verification.md` | Document checks that preserve existing behavior after refactors. | Current code, gold data, snapshots, audit scripts. | Reproducible verification evidence. |

## Current Data Flow

```text
YouTube API or legacy CSV
  -> extraction dataframe
  -> bronze JSONL
  -> silver Parquet
  -> gold clean comments
  -> stream playback
  -> window snapshots
  -> trigger logs and experiment summaries
  -> non-invasive RAG evidence artifacts
  -> contract-only RAG validation preparation artifacts
  -> RAG PoC validation artifacts
  -> RAG artifact verification report
  -> future RAG refinement contract
```

## Canonical Runtime Fields

The current runtime timestamp used by playback, monitoring, and detection is
`event_time_utc`. It is parsed with `utc=True` and should be treated as the
canonical event-time field.

The canonical numeric timestamp for new comment artifacts is
`event_time_unix_s`. The canonical numeric timestamp for new video artifacts is
`published_at_unix_s`. Both use Unix epoch seconds in UTC.

The legacy fields `event_time_unix_ms` and `published_at_unix_ms` may still
appear in existing artifacts. In this project, their observed values behave as
seconds despite the `ms` suffix. New readers should prefer the `*_unix_s`
fields and fallback to legacy names only for compatibility.

See `docs/data_contracts.md` for the full data contract and lineage notes.
See `docs/rag_validation_readiness.md` for the future RAG validation contract.
See `docs/rag_artifact_audit.md` for the RAG-0 artifact and traceability audit.
See `docs/rag_event_evidence_contract.md` for the RAG-1 event-evidence contract design.
See `docs/rag_poc_integration.md` for the executable RAG PoC integration boundary.
See `docs/regression_verification.md` for the latest regression evidence.

## Separation Of Responsibilities

- `data_extraction.py` owns API access, extraction config, and extraction run
  metadata.
- `storage.py` owns timestamp normalization and physical persistence layout.
- `cleaning.py` owns text normalization, spam flags, orphan reply handling, and
  temporal duplicate removal.
- `replay.py` owns event-time replay.
- `monitoring.py` owns event-time windows and signal snapshots.
- `detectors.py` owns the detector contract, detector registry, and the default
  `xiao_ema` implementation.
- `stream_playback.py` remains as a compatibility facade for older imports.
- `run_pipeline.py` is the compatibility facade for the historical CLI. It
  translates legacy arguments through the common `RunConfig` resolvers and
  connects the unchanged phase components.
- `scripts/` contains exploratory audit/report helpers. These are useful for
  analysis; scripts that read numeric timestamps should prefer `*_unix_s` and
  fallback to `*_unix_ms`.
- `rag_evidence.py` owns non-invasive RAG evidence assembly. It reads current
  artifacts or a JSON build config and writes separate RAG-preparation outputs
  without changing the detection pipeline.
- `rag_validation.py` owns non-invasive RAG validation preparation. It consumes
  evidence packages and writes validation tasks without retrieval, generation,
  embeddings, vector stores, or external API calls.
- `rag_poc.py` owns the current executable RAG proof of concept as a posterior
  validation phase. It preserves the notebook's unit of analysis
  `trigger_time + video_id`; `event_id` is attached only in auxiliary lineage.
- `rag_verification.py` owns read-only consistency checks for RAG evidence and
  validation-preparation artifacts. It does not alter artifacts or decide
  whether an event is true.

## Known Architectural Gaps

- The README previously referenced `src/youtube_pipeline/`, but the actual
  package lives in `youtube_pipeline/`.
- New detector implementations must follow the common `TriggerDetector` contract
  and should be registered in `detectors.py`.
- Snapshot CSV outputs are stable enough for experiments, and their current
  shape is documented in `docs/data_contracts.md`.
- Trigger-to-comment maps exist in experiments and are promising for future RAG
  validation. The current RAG PoC consumes this shape directly; these maps are
  still experiment artifacts rather than required detector outputs.
- Public reports should consider anonymization or text minimization before
  exposing raw comments.

## Non-Goals For This Stage

- No algorithm changes.
- No threshold changes.
- No metric changes.
- No column renames.
- No file moves.
- No changes to the RAG PoC prompts, grouping, embeddings, vector stores,
  external retrieval behavior, or output schemas.
- No change to pipeline execution behavior.
