# RAG Validation Readiness

This document defines the future validation contract for detected YouTube event
candidates. It prepares the pipeline for a later RAG proof of concept without
implementing retrieval, embeddings, vector stores, prompts, or external-source
queries in the current pipeline.

The current implementation includes a contract-only validation preparation
harness in `youtube_pipeline/rag_validation.py` and
`scripts/prepare_rag_validation.py`. This harness creates validation tasks,
retrieval questions, query placeholders, an empty external-evidence table, and
pending validation results. It does not run retrieval, embeddings, LLM calls, or
external API requests.

RAG artifact consistency can be checked with
`youtube_pipeline/rag_verification.py` and `scripts/verify_rag_artifacts.py`.
The verifier is read-only: it checks contracts, event ID alignment, per-event
counts, temporal bounds, and pending validation artifacts, but it does not
validate events against external evidence.

The current RAG proof of concept from
`.agents/examples/structured-rag-pdf/triggers_validation.ipynb` is integrated as
a posterior phase through `youtube_pipeline/rag_poc.py` and
`scripts/run_rag_poc_validation.py`. This integration preserves the notebook's
behavior and stores `event_id` only in auxiliary lineage.

## Scope

In scope for this stage:

- define the minimum evidence needed for a detected event to be validated later;
- document how to trace an event to windows, signals, videos, and comments;
- define provisional future artifacts for RAG input and validation output;
- document retrieval questions, validation labels, and risks.

Out of scope for this stage:

- generating embeddings;
- querying news APIs or search engines;
- selecting a vector database;
- implementing prompt chains;
- changing detector logic, thresholds, metrics, or snapshot formats;
- promoting `trigger_comment_map.csv` to a required pipeline output.

## Current Evidence Available

| Artifact | Location | Current Use | RAG Readiness |
|---|---|---|---|
| Clean comments | `data/gold/clean_comments.parquet` | Runtime input for playback and detection | Contains comment IDs, video IDs, text, timestamps, and cleaned text. |
| Snapshots | `data/gold/snapshots*.csv`, `experiments/xiao/*/log_*/snapshots.csv` | Window-level monitoring evidence | Contains activity and polarization summaries, but not comment-level evidence. |
| Trigger logs | `experiments/xiao/*/log_*/trigger_log.txt` | Human-readable detector trace | Contains detector settings and trigger times, but not a stable tabular event ID. |
| Trigger summaries | `experiments/xiao/*/log_*/summary.md` | Human-readable explanation | Useful for manual audit; not a machine-readable RAG input. |
| Trigger-comment maps | `experiments/xiao/*/log_*/trigger_comment_map.csv` and `.agents/examples/structured-rag-pdf/data/trigger_comment_map.csv` | Exploratory mapping between triggers and comments | Closest current artifact to RAG input, but not yet a formal pipeline contract. |
| RAG example queries | `.agents/examples/structured-rag-pdf/data/queries_df.csv` | Proof-of-concept query input | Shows useful fields: `trigger_time`, `video_id`, `title`, `news_api_query`. |
| RAG example validation | `.agents/examples/structured-rag-pdf/data/auditoria_df.csv` | Manual or assisted validation output | Shows useful fields: `n_noticias` and a verdict/rationale field. |
| RAG validation preparation | `experiments/*/*/rag_validation/` when generated | Contract-only posterior validation setup | Contains tasks, retrieval questions, query placeholders, empty external evidence, and pending validation rows. |
| RAG PoC validation | `experiments/*/*/rag_poc/` when generated | Executable current RAG proof of concept | Contains notebook-compatible query, news, audit, vectorstore, manifest, lineage, and summary artifacts. |
| RAG artifact verification report | `experiments/*/*/rag_validation/rag_artifact_verification_report.json` when generated | Read-only consistency evidence | Confirms whether generated RAG evidence and validation-preparation artifacts satisfy the expected contracts. |

## Minimum RAG-Ready Event Record

A detected event candidate is RAG-ready only if it can be traced from the event
decision back to all comments in its evidence window.

| Field | Required | Description |
|---|---|---|
| `event_id` | Yes | Stable identifier for the detected candidate. Future implementation may derive it from run, detector, trigger time, and window. |
| `run_id` | Yes | Identifier of the pipeline or experiment execution that produced the event. |
| `detector_name` | Yes | Detector implementation, for example `xiao_ema`. |
| `detector_params` | Yes | Serialized detector parameters used for the run. |
| `trigger_time_utc` | Yes | Time at which the detector opened the event candidate, in UTC. |
| `window_start_utc` | Yes | Start of the comment evidence window, in UTC. |
| `window_end_utc` | Yes | End of the comment evidence window, in UTC. |
| `trigger_volume` | Yes | Activity volume observed by the detector at trigger time. |
| `trigger_strength` | Yes | Detector-specific strength score. For Xiao EMA, this is EMA fast over EMA slow. |
| `activity` | Recommended | Window-level activity metrics, such as volume, unique authors, and unique videos. |
| `polarization` | Recommended | Available polarization or discourse-summary metrics for the same window. |
| `top_videos` | Recommended | Videos contributing most comments to the event window. |
| `comment_count` | Yes | Number of comments linked to the event evidence window. |
| `comment_map_path` | Recommended | Path to the table containing all comments linked to this event. |
| `snapshot_path` | Recommended | Path to the snapshot artifact used for window-level evidence. |
| `dataset_path` | Yes | Dataset used to generate the run, usually gold comments. |

The current detector output already contains `trigger_time`, `cooldown_until`,
`volume`, `strength`, and an internal list of comments collected during the
lock period. Future RAG preparation should not assume those comments are enough
unless the intended evidence window is explicitly the lock period. The user's
current requirement is broader: all comments belonging to the join between the
trigger window and event time should be available.

## Event-Comment Evidence Map

The future event-comment map should preserve all comments associated with the
event evidence window. The current exploratory `trigger_comment_map.csv` is a
useful reference because it already contains trigger, window, video, author,
comment, timestamp, and text fields.

| Field | Required | Description |
|---|---|---|
| `event_id` | Yes | Join key to the event candidate table. |
| `trigger_time_utc` | Yes | UTC trigger time copied from the event record. |
| `window_start_utc` | Yes | Start of the evidence window in UTC. |
| `window_end_utc` | Yes | End of the evidence window in UTC. |
| `order_in_event` | Yes | Comment order within the event evidence set. |
| `event_time_utc` | Yes | Comment timestamp in UTC. |
| `event_time_unix_s` | Recommended | Numeric timestamp in Unix seconds. |
| `video_id` | Yes | YouTube video identifier. |
| `title` | Recommended | Video title at extraction time. |
| `channel_title` | Recommended | YouTube channel title. |
| `comment_id` | Yes | Comment identifier. |
| `author_id` | Internal only | Author identifier. Should be minimized or anonymized in public reports. |
| `text` | Required internally | Raw comment text for validation evidence. Public reports should minimize or anonymize. |
| `text_clean` | Recommended | Cleaned comment text used by NLP steps, if available. |
| `is_reply` | Recommended | Whether the row is a reply. |
| `reply_to_comment_id` | Recommended | Parent comment identifier, if applicable. |

Provisional window rule for future implementation:

```text
window_start_utc <= event_time_utc <= window_end_utc
```

This inclusive rule matches the shape of current exploratory maps. It should be
approved again before code generation because changing the boundary rule can
change comment counts.

## RAG Query Contract

The examples use one row per trigger/video query. The future contract should
keep that shape because a single event can involve multiple videos or topics.

| Field | Required | Description |
|---|---|---|
| `query_id` | Yes | Stable query identifier. |
| `event_id` | Yes | Event candidate being validated. |
| `trigger_time_utc` | Yes | UTC trigger time. |
| `video_id` | Recommended | Video being used to formulate the query. |
| `title` | Recommended | Video title used as query context. |
| `news_api_query` | Yes | External retrieval query. Present in the current RAG examples. |
| `query_language` | Recommended | Expected retrieval language, for example `es`. |
| `query_time_window_start_utc` | Recommended | Earliest external-source date to search. |
| `query_time_window_end_utc` | Recommended | Latest external-source date to search. |
| `query_source` | Recommended | Whether the query was manual, template-based, or model-generated. |

`news_api_query` should remain a future contract field. This does not mean the
current pipeline must generate real retrieval queries yet. The RAG-4 harness
creates placeholder rows with `query_status=pending_query_design` and empty
`news_api_query` values until a query-generation policy is approved.

## External Evidence Contract

Future RAG validation should keep retrieved evidence separate from internal
YouTube evidence.

| Field | Required | Description |
|---|---|---|
| `evidence_id` | Yes | Stable identifier for the retrieved source. |
| `query_id` | Yes | Query that retrieved the source. |
| `event_id` | Yes | Event being validated. |
| `title` | Yes | Source title. |
| `link` | Yes | Source URL. |
| `snippet` | Recommended | Short retrieved excerpt or summary. |
| `date` | Recommended | Source publication date as provided by retrieval provider. |
| `source` | Recommended | Publisher or source name. |
| `retrieved_at_utc` | Yes | Retrieval timestamp. |
| `retrieval_provider` | Recommended | Search API, database, or corpus used. |

## Validation Result Contract

The validation output should separate the label from the evidence and the
reasoning. Labels should not imply absolute certainty.

| Field | Required | Description |
|---|---|---|
| `event_id` | Yes | Event candidate being validated. |
| `validation_label` | Yes | One of `confirmed`, `partially_confirmed`, `not_confirmed`, or `ambiguous`. |
| `validation_status` | Yes | Processing status, for example `completed`, `retrieval_failed`, or `needs_review`. |
| `n_external_sources` | Yes | Count of retrieved external sources used in validation. |
| `rationale` | Yes | Concise explanation of the label. |
| `supporting_evidence_ids` | Recommended | Evidence IDs used in the rationale. |
| `contradictory_evidence_ids` | Recommended | Evidence IDs that conflict with the candidate event. |
| `limitations` | Recommended | Missing evidence, weak coverage, noisy comments, or ambiguous source timing. |
| `validated_at_utc` | Yes | Validation timestamp. |
| `validator` | Recommended | Human, model, or hybrid process. |

The RAG-4 preparation harness writes pending validation rows with
`validation_status=needs_external_evidence` and an empty `validation_label`.
Those rows are not final validation results; they are tasks for a later human,
model, or hybrid validator.

## Retrieval Questions

Each event candidate should support questions that can be answered from
external evidence:

- What public event, if any, occurred near `trigger_time_utc`?
- Which people, institutions, places, or topics are central to the event?
- Do external sources mention the same event within the validation time window?
- Is the YouTube activity reacting to a documented public event, to the video
  publication itself, or to internal platform dynamics?
- Are the strongest claims in comments supported, contradicted, or absent in
  external sources?
- Does the event involve one video, multiple related videos, or unrelated
  videos that only coincide temporally?

## Label Guidance

| Label | Meaning | Minimum Evidence |
|---|---|---|
| `confirmed` | External evidence supports a real public event that explains the detected activity. | At least one credible source aligned with time, topic, and entities. |
| `partially_confirmed` | A related public event exists, but comments mix unsupported claims, satire, or weakly related topics. | External evidence aligns with part of the signal. |
| `not_confirmed` | No reliable external evidence supports the candidate event. | Retrieval attempted with adequate queries and no relevant source found. |
| `ambiguous` | Evidence is insufficient, conflicting, or too broad to decide. | Sources are inconclusive or the comment evidence is too noisy. |

## Internal vs External Evidence

Internal evidence explains why the pipeline detected a candidate:

- activity volume;
- detector strength;
- window boundaries;
- videos and comments in the window;
- available polarization or discourse signals.

External evidence validates whether the candidate corresponds to a public event:

- news articles;
- official publications;
- reliable public statements;
- independent timeline references.

The RAG phase should not use comments alone to confirm an event. Comments are
evidence of online reaction, not proof that the external event happened.

## Risks And Controls

| Risk | Control |
|---|---|
| Hallucinated validation rationale | Require source IDs and separate retrieved evidence from reasoning. |
| Query bias from video titles or partisan language | Store query text and query source; compare multiple queries for high-impact events. |
| Missing external coverage | Use `ambiguous` or `not_confirmed` rather than forcing confirmation. |
| Privacy exposure in public reports | Keep raw author IDs/text internal; anonymize or minimize public outputs. |
| Boundary ambiguity around windows | Document window rule and rerun regression when implementation is added. |
| Mixed-topic trigger windows | Preserve all comments and per-video counts so validation can separate sub-events. |

## Readiness Checklist For Future Implementation

- Each event candidate has a stable `event_id`.
- Each event has UTC trigger and evidence-window fields.
- Each event can be joined to all comments in its evidence window.
- Each event stores detector name and parameters.
- Each event stores or links to snapshot-level activity and polarization fields.
- Each event can generate one or more `news_api_query` rows.
- Retrieved evidence is stored separately from YouTube comments.
- Validation labels use the controlled label set.
- Public reports minimize raw text and author identifiers.

## Decisions Required Before Implementing RAG Outputs

These decisions are not needed to complete this documentation stage, but they
will be critical before generating new pipeline artifacts:

1. Confirm the exact evidence-window boundary rule.
2. Decide whether the canonical event artifact will be CSV, JSONL, or both.
3. Decide whether `event_id` is deterministic from fields or assigned per run.
4. Decide whether raw comment text is included in internal artifacts only, with
   separate anonymized public reports.
5. Decide whether `news_api_query` is manually curated, template-generated, or
   model-generated in the first RAG proof of concept.
