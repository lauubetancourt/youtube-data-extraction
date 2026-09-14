# RAG event evidence contract

**Status:** CURRENT REFERENCE CONTRACT
**Authority:** boundary between an event candidate or historical event record,
complete causal evidence, RAG preparation, context selection, and validation
inputs.
**Architecture context:** [pipeline architecture](pipeline_architecture.md).

This document defines the evidence contracts implemented for retrospective and
daily RAG paths. It also records the compatibility schema introduced by RAG-1.
That historical schema remains active, but it is not the same object as the
neutral A6 `EventCandidate` contract.

## Scope

The contract is split into small artifacts so detection, candidate identity,
evidence assembly, RAG preparation, and validation remain separate
responsibilities.

In scope:

- define the unit of analysis for current RAG validation paths;
- preserve stable join keys between events, signals, comments, videos, and runs;
- define current reference schemas for historical candidates and evidence packages;
- distinguish complete evidence from selected RAG context;
- distinguish retrospective evidence from the daily alert/context contract;
- preserve compatibility with current snapshots, trigger logs, and exploratory
  trigger-comment maps;
- document the remaining boundary between neutral A6 candidates and historical
  event schemas.

Out of scope for evidence assembly:

- changing current `snapshots.csv`, `trigger_log.txt`, or
  `trigger_comment_map.csv` files;
- changing the detector contract or Xiao EMA behavior;
- deciding prompts, models, labels, or external-retrieval policy;
- changing data cleaning, signal formulas, metrics, thresholds, or event
  decision criteria.

## Design Principles

| Principle | Meaning for RAG integration |
|---|---|
| Detection and validation stay separate | The detector emits event candidates; RAG validates them later. |
| Current outputs remain compatible | Existing snapshots, trigger logs, and experiment files should keep working. |
| All comments remain traceable | Every comment in the event evidence window must be recoverable, even if later ranking or chunking selects a subset for the model. |
| Internal and external evidence stay separate | YouTube comments explain the online reaction; external sources validate whether a public event occurred. |
| Contracts are joinable | Artifacts join through stable IDs rather than timestamps alone. |
| UTC and Unix seconds are canonical | New artifacts should use UTC timestamps and `*_unix_s` numeric fields. |
| No future leakage | Evidence attached to a candidate should respect the event-time window and not silently use data that was unavailable at detection time. |

## Responsibility boundary

```text
DETECTION
→ CANDIDATE
→ EVIDENCE
→ RAG PREPARATION / CONTEXT SELECTION
→ VALIDATION
```

| Layer | Owns | Does not own |
|---|---|---|
| Detection | signal/detector identity, statistical decision, score, detector metadata, propagated quality | Comment/video inventory, chunking, labels |
| Candidate | Candidate identity, trigger/observation time, causal evidence interval, lifecycle when applicable, lineage references | Full comments, videos, prompts, validation |
| Evidence | Complete causal comment inventory, video associations, source references | Token budgets, model selection, labels |
| RAG preparation | Context units, chunking, ordering, capacity and selected references | Detector decision or source-data quality |
| Validation | Queries, external evidence, G-1/G-2 labels, confidence, rationale, citations | Candidate identity formulas or signal semantics |

The neutral `EventCandidate` contract is implemented but not yet the general
runtime input to evidence assembly. Retrospective `event_id` records and daily
`daily_event_id` records remain the current compatible candidate representations.

## Unit of analysis

The RAG validation unit is an event evidence package or its daily equivalent.
It represents one candidate under a specific pipeline/stage execution and links:

- the event candidate record;
- the detector and run metadata;
- the time window used as internal evidence;
- the activity and polarization signals available for that window;
- all comments associated with the window;
- the videos contributing to those comments;
- source artifact paths needed for audit;
- downstream retrieval queries, external evidence, and validation results by ID.

This package is not a replacement for detection output. It is a downstream
assembly layer that makes detection evidence ready for validation.

## Current artifact set

| Artifact | Grain | Purpose | Current reference | Implementation status |
|---|---|---|---|---|
| `run_manifest` | One row or object per evidence execution | Record dataset, detector, parameters, and output paths. | Trigger logs and extraction metadata | IMPLEMENTED_AND_ACTIVE |
| `event_candidates` | One row per retrospective candidate | Machine-readable historical candidate produced from trigger trace. | Trigger dictionaries and `trigger_log.txt` | IMPLEMENTED_AND_ACTIVE |
| `event_signal_snapshot_map` | One or more rows per event | Link candidate to monitoring snapshots and signal values. | `trigger_snapshot_map.csv` | IMPLEMENTED_AND_ACTIVE |
| `event_comment_map` | One row per event-comment pair | Preserve comments associated with the retrospective evidence window. | `trigger_comment_map.csv` | IMPLEMENTED_AND_ACTIVE |
| `event_evidence_package` | One object per event | Reference the evidence needed by downstream RAG stages. | RAG-1 contract | IMPLEMENTED_AND_ACTIVE |
| `event_comment_inventory` / `event_video_map` | One row per event-comment or event-video pair | Preserve complete sidecar evidence and video associations. | Retrospective sidecars | IMPLEMENTED_AND_ACTIVE |
| `rag_context_units` / comment map | One unit and its source-comment associations | Prepare traceable context without replacing the inventory. | Retrospective sidecars | IMPLEMENTED_AND_ACTIVE |
| `rag_validation_inputs` / context payloads | One validation input and selected payload per event | Feed G-1/G-2 with traceable evidence references. | RAG consumer | IMPLEMENTED_AND_ACTIVE |
| Daily evidence/consumer/selection artifacts | Daily event, comment/video inventory, context units, capacity, and selected context | Preserve alert evidence separately from validation context. | Daily RAG path | IMPLEMENTED_AND_ACTIVE |

Evidence and RAG artifacts are written under configured stage output roots. They
are active downstream contracts, not required columns of the prepared dataset or
native outputs of every detector.

## Retrospective compatibility implementation

The first retrospective implementation remains a non-invasive stage:

- module: `youtube_pipeline/rag_evidence.py`;
- CLI helper: `scripts/build_rag_event_evidence.py`;
- current role: read existing experiment artifacts and write new RAG evidence
  artifacts into a separate output directory.
- configuration object: `RagEvidenceBuildConfig`;
- common configuration through `RagConfig.evidence` plus preserved legacy CLI/config
  translation.

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

### Neutral candidate versus historical event row

The A6 `EventCandidate` contract and this file's `event_candidates.csv` serve
related but different roles:

- neutral `EventCandidate` composes an `ActivityObservation`, a triggered
  `DetectionResult`, minimal lineage, and a causal interval;
- retrospective `event_candidates.csv` is the active compatibility projection built
  from XIAO trigger artifacts and contains XIAO-specific fields;
- the daily path uses `daily_event_id` records produced directly by the baseline.

The neutral contract does not replace either persisted schema yet. A future
connection must preserve current ID formulas and project into the existing RAG
contracts before any schema migration is considered.

## Contract: `run_manifest`

The run manifest prevents each event row from becoming overloaded with repeated
configuration. Event rows should point to `run_id`; the manifest carries full
execution context.

| Field | Required | Source | Description | Compatibility note |
|---|---|---|---|---|
| `run_id` | Yes | Evidence execution metadata | Stable identifier for the pipeline or experiment run. | Preserved current field. |
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
| `decision_level` | Recommended | Evidence/candidate projection | Distinguishes an unvalidated candidate from posterior validation. | Must not alter detector output. |
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
| `signal_role` | Recommended | Evidence assembly layer | Example values: `trigger_anchor`, `pre_context`, `post_context`. | Explanatory field. |

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

## Evidence inventory versus RAG context

The evidence inventory is complete under the stage's declared evidence rule. RAG
context may be a selected subset under a token budget. Selection must retain
`comment_id`, `video_id`, and `context_unit_id` references and must never rewrite the
complete evidence inventory.

Retrospective consumer semantics distinguish comments available at or before the
trigger from post-trigger validation context when such context is present. The daily
path makes the distinction explicit:

```text
alert evidence
= comments new in the triggering cycle

validation context
= comments active in the analysis window
```

Both daily sets satisfy `event_time_utc < data_cutoff_utc`. Alert evidence is a
subset of validation context. Context units, chunking, token estimates, selection,
and capacity reports belong to RAG preparation, not to the candidate.

## Relationship to validation artifacts

RAG consumes evidence packages/sidecars and produces separate downstream artifacts.
These outputs never become detector fields.

| Validation artifact | Input dependency | Responsibility |
|---|---|---|
| `rag_queries` | `event_evidence_package`, event videos, titles, time window | Define external retrieval queries. |
| `external_evidence` | `rag_queries` | Store retrieved sources with URLs, snippets, dates, and retrieval metadata. |
| `validation_results` | `event_evidence_package`, `external_evidence` | Store validation label, rationale, evidence IDs, limitations, and validator metadata. |
| `public_validation_report` | `validation_results`, anonymized/minimized evidence | Communicate results without exposing unnecessary raw text or author IDs. |

## Compatibility strategy

Current evidence stages preserve existing trigger and PoC files and add their own
artifacts instead of mutating upstream outputs.

| Current artifact | Compatibility stance |
|---|---|
| `snapshots.csv` | Preserve current shape. Use it as a source for `event_signal_snapshot_map`. |
| `trigger_log.txt` | Preserve as human-readable historical evidence. |
| `trigger_comment_map.csv` | Preserve as the compatibility bridge into retrospective evidence. |
| `queries_df.csv` | Preserve the PoC reference separately from current query artifacts. |
| `noticias_df.csv` | Preserve the PoC reference separately from current external-evidence artifacts. |
| `auditoria_df.csv` | Preserve the PoC reference separately from current controlled validation results. |

## Deferred refinements

Current retrospective and daily paths implement the approved reference contracts.
The following choices remain deferred:

1. Whether neutral `EventCandidate` becomes the common runtime handoff through
   compatibility adapters.
2. Whether public reports should generate separate anonymized evidence
   artifacts instead of reusing internal `event_comment_map.csv`.
3. Whether retrieval queries are manual, template-based, or model-assisted.
4. Whether snapshot linkage should stay configurable (`window`, `anchor`,
   `none`) or be fixed for thesis experiments.
5. Whether validation results should be stored beside each experiment or
   in a shared `reports/` or `rag_validation/` area.

## Current contract status

The reference contract is implemented for retrospective evidence, retrospective
sidecars/consumer, and the daily sidecar/consumer/selection chain. G-1, G-2, and
hierarchical G-2 consume downstream validation inputs without changing detection.

The remaining architectural gap is explicit: neutral `EventCandidate` is not yet
the common persisted handoff, and `quality` is not uniformly propagated into the
historical RAG schemas. This is documented debt, not permission to change current
IDs, sidecars, prompts, or evidence rules during detector integration.
