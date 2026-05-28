# RAG-0 Artifact And Traceability Audit

This document records the first audit stage for future RAG validation. It is
descriptive only. It does not implement RAG, change detector behavior, change
formats, change thresholds, or promote exploratory artifacts to required
pipeline outputs.

## Scope

RAG-0 answers one question: what evidence already exists, and what traceability
is still missing before a RAG validation phase can be integrated safely?

In scope:

- inventory current data, experiment, detection, and RAG proof-of-concept
  artifacts;
- identify which artifacts can support event validation later;
- document lineage from YouTube comments to candidate-event evidence;
- identify gaps before defining a formal event-evidence contract.

Out of scope:

- implementing RAG;
- changing pipeline execution;
- changing current detection outputs;
- changing snapshot or trigger formats;
- changing cleaning, monitoring, detection, threshold, or metric logic.

## Skills Applied

| Skill | How it guided this audit |
|---|---|
| `data-source-inventory-lineage` | Used to trace raw, bronze, silver, gold, experiment, and RAG PoC artifacts. |
| `data-understanding-audit` | Used to inspect corpus size, temporal coverage, identifiers, and artifact schemas. |
| `data-integration-formatting` | Used to check join keys, timestamp fields, and handoffs between detection and RAG evidence. |
| `rag-validation-readiness` | Used to assess whether candidate events can be validated from internal and external evidence. |
| `experiment-traceability-reporting` | Used to identify missing run, detector, parameter, and artifact provenance fields. |

## Current Artifact Inventory

| Artifact | Location | Shape or size observed | Main fields or content | RAG usefulness | Current limitation |
|---|---:|---:|---|---|---|
| Raw legacy comments | `data/comments.csv` | 14.3 MB | Comment exports | Historical input reference | Not the current runtime gold artifact. |
| Raw legacy videos | `data/videos_preliminares.csv` | 174 KB | Video metadata | Video context | Legacy compatibility source. |
| Bronze comments | `data/bronze/comments/comments_20260409T154331Z.jsonl` | 35.7 MB | Extracted comment records | Source-level reproducibility | Not used directly by detection. |
| Bronze videos | `data/bronze/videos/videos_20260409T154331Z.jsonl` | 220 KB | Extracted video records | Source-level video lineage | Not directly joined in current RAG PoC tables. |
| Extraction run metadata | `data/bronze/runs/extraction_run_20260409T154335Z.json` | 988 bytes | Extraction run metadata | Reproducibility context | Needs propagation into future event records. |
| Gold comments | `data/gold/clean_comments.parquet` | 57,725 rows, 24 columns | `comment_id`, `video_id`, `text`, `author_id`, `is_reply`, `reply_to_comment_id`, `event_time_utc`, `text_clean`, signal features | Best current source for all comments and reply metadata | Current dataset still contains legacy `event_time_unix_ms`; new artifacts should use seconds. |
| Gold snapshots | `data/gold/snapshots_log3_variant.csv` | 57,725 rows, 9 columns | Window boundaries, activity, polarization fields | Window-level signal evidence | No comment-level rows or event IDs. |
| Experiment snapshots | `experiments/xiao/*/log_*/snapshots.csv` | 57,725 rows in inspected logs | Monitoring snapshots per run | Detection context and regression comparison | No stable event candidate table. |
| Trigger logs | `experiments/xiao/*/log_*/trigger_log.txt` | 800 bytes to 615 KB | Human-readable trigger traces | Useful audit trail | Not machine-readable enough for RAG input. |
| Trigger summaries | `experiments/xiao/baja/log_2/summary.md`, `experiments/xiao/media/log_3/summary.md` | Markdown reports | Run-level summaries | Human audit evidence | Not a structured contract. |
| Trigger-comment maps | `experiments/xiao/baja/log_2/trigger_comment_map.csv`, `experiments/xiao/media/log_3/trigger_comment_map.csv` | 190 and 292 rows | Trigger time, window, video, author, comment ID, text | Closest current internal evidence package | Exploratory, no `event_id`, no `run_id`, limited comment metadata. |
| PoC trigger-comment map | `.agents/examples/structured-rag-pdf/data/trigger_comment_map.csv` | 292 rows, 13 columns | Same shape as media log map | Current RAG PoC internal evidence | Depends on exploratory map shape. |
| PoC queries | `.agents/examples/structured-rag-pdf/data/queries_df.csv` | 51 rows, 4 columns | `trigger_time`, `video_id`, `title`, `news_api_query` | Query-generation reference | No `event_id`, `query_id`, query provenance, or retrieval time bounds. |
| PoC external evidence | `.agents/examples/structured-rag-pdf/data/noticias_df.csv` | 389 rows, 8 columns | News title, link, snippet, date, source, query | External validation evidence prototype | No stable `evidence_id`, retrieval timestamp, or normalized provider metadata. |
| PoC audit output | `.agents/examples/structured-rag-pdf/data/auditoria_df.csv` | 51 rows, 6 columns | Query, number of news items, audit rationale | Validation-output reference | Validation label is not a controlled field. |

## Corpus Snapshot For RAG Readiness

Observed current gold comment corpus:

- Rows: 57,725 comments.
- Unique comments: 57,725.
- Unique videos: 112.
- Unique authors: 35,652.
- Event-time range: from `2026-02-20 11:54:45+00:00` to
  `2026-04-09 15:30:11+00:00`.
- Important available fields: `comment_id`, `video_id`, `text`, `author_id`,
  `is_reply`, `reply_to_comment_id`, `event_time_utc`, `text_clean`,
  `emoji_count`, `exclamation_count`, `question_count`, `caps_ratio`,
  `link_count`, `token_count`, `is_probable_spam`.

This is the strongest internal evidence source for future RAG because it can
preserve both raw text and cleaned text while keeping reply relationships.

## Lineage View

```text
YouTube API or legacy CSV
  -> bronze JSONL videos/comments
  -> silver partitioned Parquet videos/comments
  -> gold clean comments
  -> stream replay
  -> monitoring snapshots
  -> detector trigger trace
  -> exploratory trigger-comment map
  -> RAG PoC queries
  -> retrieved external evidence
  -> exploratory audit output
```

The chain exists conceptually, but it is not yet encoded as a formal set of
joinable contracts. The weak points are between detector trigger trace and
trigger-comment map, and between trigger-comment map and the RAG PoC tables.

## Trigger-Comment Coverage Check

The current maps were compared against `data/gold/clean_comments.parquet` using
their own `window_start`, `window_end`, and `comment_id` fields.

| Map | Rows | Triggers | Unique videos | Unique comments | Unmatched comment IDs | Reply rows found after gold join | Missing gold comments from same windows |
|---|---:|---:|---:|---:|---:|---:|---:|
| `experiments/xiao/baja/log_2/trigger_comment_map.csv` | 190 | 3 | 6 | 190 | 0 | 6 | 0 |
| `experiments/xiao/media/log_3/trigger_comment_map.csv` | 292 | 10 | 35 | 292 | 0 | 21 | 0 |
| `.agents/examples/structured-rag-pdf/data/trigger_comment_map.csv` | 292 | 10 | 35 | 292 | 0 | 21 | 0 |

Interpretation:

- The inspected maps are consistent with all gold comments in their recorded
  evidence windows.
- They are not limited to only top-level comments in the inspected files,
  because replies are present when the maps are joined back to gold comments.
- The remaining gap is contractual: the map schema does not explicitly include
  `is_reply`, `reply_to_comment_id`, `text_clean`, `event_time_unix_s`,
  `run_id`, or stable `event_id`.
- Future RAG integration should therefore preserve this all-comments behavior,
  but make it explicit and reproducible.

## RAG Readiness Assessment

| Requirement | Current status | Evidence | Gap |
|---|---|---|---|
| Event candidate can be identified | Partial | Trigger time, window, volume, strength in logs/maps | No stable `event_id`. |
| Event can be joined to all comments in its evidence window | Partial | Existing maps match all comments in inspected windows | Join rule is not a formal contract. |
| Event can be traced to videos | Partial | Maps include `video_id`, `title`, `channel_title` | Video metadata source path and extraction run are not carried. |
| Event can be traced to signal values | Partial | Snapshots contain activity/polarization fields | Maps do not carry or reference snapshot row IDs. |
| Detector decision is reproducible | Partial | Logs and summaries include parameters in human-readable form | No structured run manifest per event. |
| Query generation can be reproduced | Low | PoC `queries_df.csv` stores query text | No query provenance, query ID, or time-window policy. |
| External evidence can be audited | Partial | `noticias_df.csv` stores links and snippets | No evidence ID, retrieval timestamp, or provider configuration. |
| Validation output can be analyzed | Partial | `auditoria_df.csv` has audit text and news count | No controlled validation labels or explicit evidence IDs. |
| Public-report privacy can be controlled | Low | Raw `author_id` and `text` appear in maps | No separation between internal evidence and public-safe report. |

## Strengths To Preserve

- The gold comments artifact has enough identifiers and metadata to support
  event-to-comment traceability.
- The current trigger-comment maps already demonstrate the right direction:
  event windows can be expanded into comment-level evidence.
- The PoC separates internal comments, generated queries, external evidence,
  and audit output into separate files. This separation should be preserved.
- Snapshots already keep activity and polarization summaries separate from raw
  comments, which helps maintain clear responsibilities.

## Gaps Before RAG Implementation

| Gap | Why it matters | Suggested stage |
|---|---|---|
| No stable `event_id` | RAG needs a durable key across event, comments, queries, external evidence, and validation output. | RAG-1 |
| No formal event candidate artifact | Trigger logs are not enough as machine-readable RAG input. | RAG-1 |
| Trigger-comment map is exploratory | The current map is useful but not guaranteed by the pipeline. | RAG-2 |
| No explicit all-comments contract | The desired requirement is all comments in the evidence window, not only selected comments. | RAG-2 |
| Reply metadata not present in maps | RAG and audits may need to distinguish top-level comments from replies. | RAG-2 |
| Snapshot evidence is not linked by ID | RAG explanations need to cite the signals that justified detection. | RAG-1/RAG-3 |
| Query and external evidence provenance is weak | Validation must be auditable and reproducible. | RAG-4 |
| Validation labels are unstructured | Later evaluation needs controlled labels and rationale fields. | RAG-4 |
| Public/privacy policy is not encoded | Raw text and author IDs should not flow automatically into public reports. | RAG-4/RAG-5 |

## Decisions Deferred

No critical decision is required to complete RAG-0. The following decisions
should be approved before implementation stages:

1. Stable `event_id` strategy.
2. Exact evidence-window boundary rule.
3. Whether future formal artifacts are CSV, JSONL, or both.
4. Which fields remain internal-only before public reporting.
5. Whether query generation starts as manual, template-based, or model-assisted.
6. How much detector configuration is duplicated in each event record versus
   referenced through a run manifest.

## RAG-0 Acceptance Result

RAG-0 is complete if the next stage can start from this documented evidence:

- current artifacts have been inventoried;
- lineage from comments to RAG PoC outputs is described;
- all-comments coverage in existing maps has been checked;
- missing contracts and traceability fields are listed;
- no functional pipeline behavior has been changed.

