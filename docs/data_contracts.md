# Data Contracts And Traceability

This document records the current data contracts for the YouTube event
detection prototype. It is a compatibility contract: it documents fields,
formats, lineage, and expected consumers without changing algorithms,
thresholds, metrics, or detector decisions.

## Contract Principles

- Preserve current inputs and outputs unless a change is required for
  traceability, reproducibility, or methodological clarity.
- Treat `event_time_utc` and `published_at_utc` as UTC event-time fields.
- Use Unix epoch seconds for numeric time fields.
- Prefer canonical `*_unix_s` fields in new artifacts.
- Accept legacy `*_unix_ms` fields while existing datasets are still present.
- Do not rewrite historical datasets during architectural refactors unless a
  migration is approved.

## Temporal Contract

| Entity | Canonical UTC field | Canonical numeric field | Legacy field | Unit | Timezone |
|---|---|---|---|---|---|
| Comment | `event_time_utc` | `event_time_unix_s` | `event_time_unix_ms` | seconds | UTC |
| Video | `published_at_utc` | `published_at_unix_s` | `published_at_unix_ms` | seconds | UTC |

`*_unix_ms` is a deprecated name in this project. Existing observed values
behave as Unix epoch seconds, not milliseconds. New code should write and
prefer `*_unix_s`; readers that need to support previous artifacts should
fallback to `*_unix_ms`.

## Data Layers

| Layer | Location | Format | Producer | Main Consumer | Contract Status |
|---|---|---|---|---|---|
| Legacy extraction exports | `data/videos_preliminares.csv`, `data/comments.csv` | CSV | Extraction phase | Storage and exploratory notebooks | Compatibility input |
| Bronze videos | `data/bronze/videos/videos_*.jsonl` | JSONL | `persist_batch_snapshot` | Audits and reproducibility checks | Versioned batch output |
| Bronze comments | `data/bronze/comments/comments_*.jsonl` | JSONL | `persist_batch_snapshot` | Stream audits and silver preparation | Versioned batch output |
| Silver videos | `data/silver/videos/` | Partitioned Parquet | `persist_batch_snapshot` | Downstream preparation | Prepared source metadata |
| Silver comments | `data/silver/comments/` | Partitioned Parquet | `persist_batch_snapshot` | Cleaning phase | Prepared comment input |
| Gold comments | `data/gold/clean_comments.parquet` | Parquet | Cleaning phase | Playback, monitoring, detection, audits | Runtime analytical dataset |
| Snapshots | `data/gold/snapshots*.csv` | CSV | Playback and monitoring | Experiment inspection | Stable experiment output |
| Experiment outputs | `experiments/` | CSV/Markdown/JSON-like reports | Scripts and manual experiments | Audit, thesis evidence, future RAG | Exploratory evidence |

## Comment Entity

| Field | Required | Description | Notes |
|---|---|---|---|
| `comment_id` | Recommended | YouTube comment identifier. | Primary traceability key when available. |
| `video_id` | Required | YouTube video identifier. | Join key to video metadata. |
| `author_id` | Recommended | Comment author/channel identifier. | Sensitive in public reports; consider anonymization. |
| `text` | Required | Raw comment text as extracted. | Preserve for audit and future RAG evidence. |
| `published_at_raw` | Recommended | Original timestamp string from source column. | Supports source-level audit. |
| `event_time_utc` | Required | Parsed comment timestamp in UTC. | Runtime event-time field. |
| `event_time_unix_s` | Required for new artifacts | Unix epoch seconds. | Canonical numeric time field. |
| `event_time_unix_ms` | Legacy-compatible | Deprecated alias currently containing seconds. | Keep only for compatibility. |
| `event_date`, `event_year`, `event_month`, `event_day` | Required in partitioned datasets | Derived calendar fields in UTC. | Used for partitioning and audit. |
| `text_clean` or equivalent cleaned text | Required in gold | Text after cleaning rules. | Exact name depends on cleaning output. |

## Video Entity

| Field | Required | Description | Notes |
|---|---|---|---|
| `video_id` | Required | YouTube video identifier. | Join key to comments. |
| `published_at_raw` | Recommended | Original video timestamp string. | Supports source-level audit. |
| `published_at_utc` | Required | Parsed video publication time in UTC. | Canonical time field. |
| `published_at_unix_s` | Required for new artifacts | Unix epoch seconds. | Canonical numeric time field. |
| `published_at_unix_ms` | Legacy-compatible | Deprecated alias currently containing seconds. | Keep only for compatibility. |
| `published_date` | Recommended | UTC date string. | Useful for reporting. |

## Snapshot Contract

Snapshots are flat CSV records produced by playback and monitoring. The current
format should be preserved during architectural refactors.

| Field Family | Meaning | Consumer |
|---|---|---|
| `event_time_utc` or equivalent window timestamp | Window time reference in UTC. | Audit, plotting, experiment comparison. |
| `activity.*` | Activity counts and activity-derived summary fields. | Monitoring and event interpretation. |
| `polarization.*` | Current polarization-related summary fields. | Detection context and future methodological refinement. |
| Other flattened monitoring fields | Window-level metadata. | Reports and exploratory analysis. |

Do not rename snapshot columns during Etapa 3. If a future stage requires a
schema change, keep a compatibility export or migration note.

## Detection Evidence Contract

The detector currently emits decisions through runtime hooks and experiment
logs. A formal RAG-ready event artifact is documented for future implementation
but is not generated by the pipeline yet. For now, any future event record
should remain traceable to:

- detector name and detector parameters;
- trigger time in UTC;
- window start and window end in UTC;
- activity signal values used by the detector;
- polarization fields available at the window;
- comment identifiers or rows that fall inside the detected window;
- source dataset and run configuration.

`trigger_comment_map.csv` remains an exploratory RAG input candidate. It is not
promoted to a required pipeline contract in this stage.

## Future RAG Validation Contract

The future RAG phase should consume event candidates, event-comment evidence,
retrieval queries, external evidence, and validation results as separate
artifacts. This keeps internal YouTube evidence distinct from external
validation evidence.

| Future Artifact | Purpose | Required Join Key | Current Reference |
|---|---|---|---|
| Event candidates | One row per detected event candidate. | `event_id` | Trigger dictionaries and `trigger_log.txt`. |
| Event-comment map | All comments associated with the event evidence window. | `event_id`, `comment_id` | `trigger_comment_map.csv` examples. |
| RAG queries | One or more external retrieval queries per event or video. | `event_id`, `query_id` | `queries_df.csv` example. |
| External evidence | Retrieved source records from news or other accepted sources. | `event_id`, `query_id`, `evidence_id` | `noticias_df.csv` example. |
| Validation results | Final validation label and rationale. | `event_id` | `auditoria_df.csv` example. |
| Validation tasks | Pending posterior validation work items. | `event_id`, `validation_task_id` | `rag_validation_tasks.csv`. |
| RAG PoC lineage | Non-functional bridge between current PoC groups and pipeline event IDs. | `event_id`, `trigger_time`, `video_id` | `rag_poc_lineage.csv`. |

See `docs/rag_validation_readiness.md` for field-level requirements,
validation labels, retrieval questions, risks, and implementation decisions.
See `docs/rag_event_evidence_contract.md` for the proposed RAG-1 split between
run manifests, event candidates, signal maps, comment maps, and evidence
packages.

The first non-invasive builder for the event/evidence artifacts is
`scripts/build_rag_event_evidence.py`. It writes new files into a separate
output directory and does not modify existing pipeline artifacts. It can be
driven through CLI arguments or a JSON config file, and writes a
`rag_evidence_summary.json` file for run-level traceability.

The first non-invasive validation preparation helper is
`scripts/prepare_rag_validation.py`. It consumes `event_evidence_packages.jsonl`
and writes validation tasks, retrieval questions, query placeholders, an empty
external-evidence table, pending validation rows, and a
`rag_validation_summary.json` file. It does not retrieve external sources or
generate validation labels.

The RAG artifact verifier is `scripts/verify_rag_artifacts.py`. It reads the
evidence and validation-preparation directories, checks required files and
columns, verifies event ID alignment, compares summary counts to artifact
contents, checks that comments fall inside event windows, and confirms that
`event_time_unix_s` matches `event_time_utc`. It writes an optional JSON report
and does not modify artifacts.

The executable integration of the current RAG proof of concept is
`scripts/run_rag_poc_validation.py`. Its functional inputs and outputs preserve
the notebook contract:

- input: `trigger_comment_map.csv` with `trigger_time`, `window_start`,
  `window_end`, `trigger_volume`, `trigger_strength`, `order_in_trigger`,
  `event_time_utc`, `video_id`, `title`, `channel_title`, `author_id`,
  `comment_id`, and `text`;
- outputs: `queries_df.csv`, `noticias_df.csv`, `auditoria_df.csv`,
  `vectorstore_comentarios/`, and `vectorstore_noticias/`.

`event_id` is not added to those PoC outputs. When an RAG evidence
`event_comment_map.csv` is provided, the integration writes `rag_poc_lineage.csv`
as an auxiliary bridge from `trigger_time + video_id` groups to pipeline
`event_id` values.

## Lineage Expectations

Every analytical artifact should be explainable with this chain:

```text
YouTube source metadata
  -> extraction run
  -> bronze JSONL
  -> silver Parquet
  -> gold clean comments
  -> playback stream
  -> monitoring snapshot
  -> detector evidence or experiment report
  -> future RAG validation input
```

Minimum lineage metadata for future reports:

- source path or dataset version;
- extraction or processing timestamp when available;
- temporal field used and its unit;
- relevant CLI/config parameters;
- detector name;
- output artifact path;
- known compatibility notes.

## Compatibility Rules

- New artifacts should include `event_time_unix_s` or `published_at_unix_s`.
- Readers should prefer `*_unix_s` and fallback to `*_unix_ms`.
- Existing `data/` artifacts are not migrated automatically.
- Public reports that include text should apply anonymization or text
  minimization before publication.
