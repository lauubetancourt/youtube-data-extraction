# RAG-1 Event Evidence Contract Design

This document defines the contract between event detection evidence and future
RAG validation. The current implementation is a non-invasive evidence builder:
it does not implement RAG validation, change current outputs, change detector
behavior, change thresholds, or promote any exploratory file to a required
pipeline output.

## Scope

RAG-1 defines what a future RAG phase should receive from the detection side.
The contract is intentionally split into small artifacts so that detection,
evidence assembly, retrieval, and validation remain separate responsibilities.

In scope:

- define the conceptual unit of analysis for RAG validation;
- propose stable join keys between events, signals, comments, and runs;
- define provisional schemas for event candidates and evidence packages;
- preserve compatibility with current snapshots, trigger logs, and exploratory
  trigger-comment maps;
- document pending decisions that require approval before implementation.

Out of scope for the builder:

- changing current `snapshots.csv`, `trigger_log.txt`, or
  `trigger_comment_map.csv` files;
- changing the detector contract or Xiao EMA behavior;
- implementing retrieval, embeddings, chunking, prompts, or validation labels;
- changing data cleaning, signal formulas, metrics, thresholds, or event
  decision criteria.

## Design Principles

| Principle | Meaning for RAG integration |
|---|---|
| Detection and validation stay separate | The detector emits event candidates; RAG validates them later. |
| Current outputs remain compatible | Existing snapshots, trigger logs, and experiment files should keep working. |
| All comments remain traceable | Every comment in the event evidence window must be recoverable, even if later ranking or chunking selects a subset for the model. |
| Internal and external evidence stay separate | YouTube comments explain the online reaction; external sources validate whether a public event occurred. |
| Contracts are joinable | Every future artifact should join through stable IDs rather than timestamps alone. |
| UTC and Unix seconds are canonical | New artifacts should use UTC timestamps and `*_unix_s` numeric fields. |
| No future leakage | Evidence attached to a candidate should respect the event-time window and not silently use data that was unavailable at detection time. |

## Unit Of Analysis

The RAG validation unit is an event evidence package.

An event evidence package represents one detected event candidate produced by a
specific pipeline run and detector configuration. It links:

- the event candidate record;
- the detector and run metadata;
- the time window used as internal evidence;
- the activity and polarization signals available for that window;
- all comments associated with the window;
- the videos contributing to those comments;
- source artifact paths needed for audit;
- future retrieval queries, external evidence, and validation results.

This package is not a replacement for detection output. It is a downstream
assembly layer that makes detection evidence ready for validation.

## Proposed Artifact Set

| Artifact | Grain | Purpose | Current reference | Implementation status |
|---|---|---|---|---|
| `run_manifest` | One row or object per execution | Record dataset, detector, parameters, code context, and output paths. | Trigger logs and extraction metadata | Implemented by non-invasive builder. |
| `event_candidates` | One row per detected candidate | Machine-readable event candidate produced from detector trace. | Trigger dictionaries and `trigger_log.txt` | Implemented by non-invasive builder. |
| `event_signal_snapshot_map` | One or more rows per event | Link event candidate to monitoring snapshots and signal values. | `trigger_snapshot_map.csv` from reporting script | Implemented by non-invasive builder. |
| `event_comment_map` | One row per event-comment pair | Preserve all comments associated with the evidence window. | Exploratory `trigger_comment_map.csv` | Implemented by non-invasive builder. |
| `event_evidence_package` | One object per event | Manifest joining all event evidence needed by RAG. | No formal current artifact | Implemented by non-invasive builder. |

These names are the current non-invasive builder outputs. They are not yet
native pipeline outputs and should still be treated as RAG-preparation
artifacts.

## Current Non-Invasive Implementation

The first implementation lives outside the main pipeline:

- module: `youtube_pipeline/rag_evidence.py`;
- CLI helper: `scripts/build_rag_event_evidence.py`;
- current role: read existing experiment artifacts and write new RAG evidence
  artifacts into a separate output directory.
- configuration object: `RagEvidenceBuildConfig`;
- optional config loading: `--config-file path/to/config.json`.

It does not alter playback, monitoring, detection, thresholds, metrics,
existing snapshots, trigger logs, or exploratory trigger-comment maps.

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

Generated files:

- `run_manifest.json`;
- `event_candidates.csv`;
- `event_comment_map.csv`;
- `event_signal_snapshot_map.csv`;
- `event_evidence_packages.jsonl`;
- `rag_evidence_summary.json`.

The summary file stores the same execution summary printed by the CLI. It is
intended for experiment traceability and quick regression checks.

Config example:

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

Approved implementation decisions for this first builder:

- deterministic `event_id` from run, detector, trigger time, and window;
- inclusive evidence window:
  `window_start_utc <= event_time_utc <= window_end_utc`;
- CSV for tabular artifacts and JSON/JSONL for manifests/packages;
- raw text and author IDs are retained only in internal evidence artifacts;
- a comment may belong to multiple events if evidence windows overlap, but is
  deduplicated within each event;
- the builder is non-invasive and does not modify the main pipeline.

## Contract: `run_manifest`

The run manifest prevents each event row from becoming overloaded with repeated
configuration. Event rows should point to `run_id`; the manifest carries full
execution context.

| Field | Required | Source | Description | Compatibility note |
|---|---|---|---|---|
| `run_id` | Yes | Future execution metadata | Stable identifier for the pipeline or experiment run. | New field; no current output is changed. |
| `created_at_utc` | Yes | Runtime/reporting layer | Time when the run manifest was created. | New field. |
| `pipeline_stage` | Yes | Runtime/reporting layer | Stage that produced the artifacts, for example `playback_detection`. | New field. |
| `dataset_path` | Yes | CLI or reporting input | Dataset used for playback or report reconstruction. | Can reference current `data/gold/clean_comments.parquet`. |
| `snapshot_path` | Optional | CLI or reporting input | Snapshot artifact associated with the run. | Can reference current snapshots. |
| `detector_name` | Yes | Detector settings | Detector implementation, for example `xiao_ema`. | Matches current modular detector design. |
| `detector_params` | Yes | CLI/config | Serialized detector parameters. | Should not change parameter values. |
| `monitoring_params` | Recommended | CLI/config | Snapshot window and signal functions used. | Documents current settings without changing them. |
| `source_artifacts` | Recommended | Reporting layer | Raw, bronze, silver, gold, snapshot, and trigger paths. | New traceability field. |
| `notes` | Optional | Analyst | Human-readable caveats. | Documentation only. |

## Contract: `event_candidates`

An event candidate records the detector decision. It should be compact, one row
per candidate, and should not contain all comments directly.

| Field | Required | Source | Description | Compatibility note |
|---|---|---|---|---|
| `event_id` | Yes | Evidence assembly layer | Stable event candidate identifier. | New join key using approved deterministic hash strategy. |
| `run_id` | Yes | `run_manifest` | Run that produced the event. | New join key. |
| `detector_name` | Yes | Detector settings | Detector that emitted the candidate. | Current default remains `xiao_ema`. |
| `trigger_time_utc` | Yes | Detector trigger | UTC timestamp when the trigger opened. | Current maps have `trigger_time`. |
| `trigger_time_unix_s` | Recommended | Derived from trigger time | Numeric trigger time in Unix seconds. | Uses agreed seconds convention. |
| `window_start_utc` | Yes | Evidence window rule | Start of comment evidence window. | Current maps have `window_start`. |
| `window_end_utc` | Yes | Evidence window rule | End of comment evidence window. | Current maps have `window_end`. |
| `trigger_volume` | Yes | Detector trigger | Volume observed at trigger. | Current maps/logs have this value. |
| `trigger_strength` | Recommended | Detector trigger | Detector-specific strength. For Xiao EMA, EMA fast over EMA slow. | Current maps/logs have this value. |
| `decision_level` | Recommended | Future decision taxonomy | Suggested values: `candidate`, `validated`, `rejected`, `ambiguous`. | Future field; should not alter detector output. |
| `comment_count` | Recommended | `event_comment_map` aggregate | Count of comments linked to this event. | Derived field; useful for audit. |
| `unique_video_count` | Recommended | `event_comment_map` aggregate | Number of videos represented in the evidence window. | Derived field. |
| `unique_author_count` | Optional/internal | `event_comment_map` aggregate | Number of authors represented in the evidence window. | Sensitive in public reports. |
| `event_artifact_version` | Yes | Contract version | Version of this event contract. | New compatibility field. |

### Implemented decision: `event_id`

Recommended provisional strategy:

```text
event_id = "evt_" + short_hash(run_id, detector_name, trigger_time_utc, window_start_utc, window_end_utc)
```

This is deterministic within a run and avoids depending only on row order.

## Contract: `event_signal_snapshot_map`

This artifact links each event to the signal evidence that explains why it was
detected. It should not duplicate the whole snapshot file unless needed; it can
store a selected set of signal values plus a pointer to the original snapshot
artifact.

| Field | Required | Source | Description | Compatibility note |
|---|---|---|---|---|
| `event_id` | Yes | `event_candidates` | Event candidate being explained. | New join key. |
| `run_id` | Yes | `run_manifest` | Run that produced the snapshot evidence. | New join key. |
| `snapshot_path` | Yes | Run/reporting layer | Source snapshot file. | References current snapshot CSV. |
| `snapshot_order_in_event` | Recommended | Evidence assembly layer | Row order for snapshots attached to the event. | New field. |
| `snapshot_window_start_utc` | Yes | Snapshot | Start of snapshot window. | Current snapshots have `window_start`. |
| `snapshot_window_end_utc` | Yes | Snapshot | End of snapshot window. | Current snapshots have `window_end`. |
| `activity.volume` | Yes | Snapshot | Comment volume. | Current field. |
| `activity.unique_authors` | Recommended | Snapshot | Unique author count. | Current field when available. |
| `activity.unique_videos` | Recommended | Snapshot | Unique video count. | Current field when available. |
| `polarization.*` | Recommended | Snapshot | Available polarization or discourse summary fields. | Field meaning remains unchanged. |
| `signal_role` | Recommended | Future evidence assembly layer | Example values: `trigger_anchor`, `pre_context`, `post_context`. | New explanatory field. |

## Contract: `event_comment_map`

This artifact preserves all comments associated with the event evidence window.
It is the internal evidence backbone for RAG. A later RAG component may rank,
chunk, summarize, or select comments for context limits, but that later step
must not erase the full map.

| Field | Required | Source | Description | Compatibility note |
|---|---|---|---|---|
| `event_id` | Yes | `event_candidates` | Event candidate being linked to the comment. | New join key. |
| `run_id` | Yes | `run_manifest` | Run that produced the map. | New join key. |
| `order_in_event` | Yes | Evidence assembly layer | Comment order inside the evidence window. | Current maps have `order_in_trigger`. |
| `event_time_utc` | Yes | Gold comments | Comment timestamp in UTC. | Current maps have this field. |
| `event_time_unix_s` | Recommended | Gold comments or derived | Numeric comment timestamp in Unix seconds. | New canonical seconds field. |
| `video_id` | Yes | Gold comments | YouTube video ID. | Current maps have this field. |
| `title` | Recommended | Video metadata/map | Video title at extraction time. | Current maps have this field. |
| `channel_title` | Recommended | Video metadata/map | Channel title. | Current maps have this field. |
| `comment_id` | Yes | Gold comments | YouTube comment ID. | Current maps have this field. |
| `author_id` | Internal | Gold comments | Author/channel ID. | Keep internal; public reports should minimize or anonymize. |
| `text` | Internal required | Gold comments | Raw comment text for validation evidence. | Current maps have this field; public exposure should be controlled. |
| `text_clean` | Recommended | Gold comments | Cleaned text used by preprocessing. | Not present in current maps. |
| `is_reply` | Recommended | Gold comments | Whether the comment is a reply. | Not present in current maps, but available in gold. |
| `reply_to_comment_id` | Recommended | Gold comments | Parent comment ID if the row is a reply. | Not present in current maps, but available in gold. |
| `comment_source_path` | Recommended | Run/reporting layer | Path to the source comment artifact. | New traceability field. |

### Implemented decision: evidence-window rule

The provisional rule remains:

```text
window_start_utc <= event_time_utc <= window_end_utc
```

This matches the inspected maps and the approved first implementation rule.

## Contract: `event_evidence_package`

The evidence package is a manifest-like object that tells RAG where to find the
pieces of evidence for one event. It should reference artifacts instead of
embedding all comments directly.

| Field | Required | Source | Description | Compatibility note |
|---|---|---|---|---|
| `event_id` | Yes | `event_candidates` | Event being packaged. | New join key. |
| `run_id` | Yes | `run_manifest` | Run context. | New join key. |
| `event_candidate_path` | Yes | Evidence assembly layer | Path to event candidate artifact. | New artifact reference. |
| `event_signal_snapshot_map_path` | Recommended | Evidence assembly layer | Path to signal evidence artifact. | New artifact reference. |
| `event_comment_map_path` | Yes | Evidence assembly layer | Path to all-comment evidence map. | New artifact reference. |
| `source_dataset_path` | Yes | Run manifest | Gold comment dataset path. | References current data. |
| `snapshot_path` | Recommended | Run manifest | Snapshot CSV used for signal context. | References current snapshots. |
| `package_created_at_utc` | Yes | Evidence assembly layer | Package creation timestamp. | New field. |
| `package_artifact_version` | Yes | Contract version | Version of the package contract. | New compatibility field. |
| `rag_readiness_status` | Recommended | Evidence assembly layer | Example values: `ready`, `missing_comments`, `missing_signals`, `needs_review`. | Does not validate the event; only checks readiness. |

## Relationship To Future RAG Artifacts

The RAG phase should consume the evidence package and produce separate
artifacts. The contract should not mix these downstream artifacts into
detection outputs.

| Future artifact | Input dependency | Responsibility |
|---|---|---|
| `rag_queries` | `event_evidence_package`, event videos, titles, time window | Define external retrieval queries. |
| `external_evidence` | `rag_queries` | Store retrieved sources with URLs, snippets, dates, and retrieval metadata. |
| `validation_results` | `event_evidence_package`, `external_evidence` | Store validation label, rationale, evidence IDs, limitations, and validator metadata. |
| `public_validation_report` | `validation_results`, anonymized/minimized evidence | Communicate results without exposing unnecessary raw text or author IDs. |

## Compatibility Strategy

RAG-1 does not require changing existing files. Future implementation should
add new artifacts instead of mutating current outputs.

| Current artifact | Compatibility stance |
|---|---|
| `snapshots.csv` | Preserve current shape. Use it as a source for `event_signal_snapshot_map`. |
| `trigger_log.txt` | Preserve as human-readable evidence. Future event artifacts may be derived from detector trace or reporting logic. |
| `trigger_comment_map.csv` | Preserve current exploratory files. Future `event_comment_map` can extend the schema in a new artifact. |
| `queries_df.csv` | Preserve PoC reference. Future `rag_queries` should add IDs and provenance. |
| `noticias_df.csv` | Preserve PoC reference. Future external evidence should add IDs and retrieval metadata. |
| `auditoria_df.csv` | Preserve PoC reference. Future validation results should add controlled labels. |

## Decisions For Future Stages

The first non-invasive builder implements the approved baseline decisions. The
following choices remain open before deeper RAG integration:

1. Whether the builder becomes a subcommand of `run_pipeline.py` or remains an
   external helper script.
2. Whether future public reports should generate separate anonymized evidence
   artifacts instead of reusing internal `event_comment_map.csv`.
3. Whether retrieval queries are manual, template-based, or model-assisted.
4. Whether snapshot linkage should stay configurable (`window`, `anchor`,
   `none`) or be fixed for thesis experiments.
5. Whether future validation results should be stored beside each experiment or
   in a shared `reports/` or `rag_validation/` area.

## Acceptance Criteria For RAG-1

RAG-1 is complete when:

- the event evidence package is defined as the RAG unit of analysis;
- proposed artifacts and join keys are documented;
- required, recommended, optional, and internal fields are distinguished;
- compatibility with current outputs is preserved;
- critical implementation decisions are listed and not silently assumed;
- no existing detection, monitoring, or playback behavior has been changed.
