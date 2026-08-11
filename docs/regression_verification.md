# Regression Verification

Date: 2026-05-18  
Scope: verification after CRISP-DM architectural, contract, and documentation
refinement stages.

This report documents checks used to verify that the refinements did not change
pipeline behavior. It does not introduce new algorithms, thresholds, metrics,
formats, or regenerated official datasets. RAG PoC dependencies were added to
`requirements.txt` after explicit approval so the existing notebook can be
executed as a pipeline phase. The reconciled project environment is Python
3.12.13 with `numpy==1.26.4`.

## Verification Boundary

Verified:

- Python syntax for pipeline and script modules.
- Temporal contract compatibility for `*_unix_s` and legacy `*_unix_ms`.
- Cleaning output values against the current gold dataset.
- Playback snapshot output against the existing expected snapshot artifact.
- Detector factory behavior against direct `XiaoEMATriggerDetector` usage.
- CLI playback path with detector config file.
- Audit scripts that consume legacy and canonical timestamp contracts.
- Snapshot trigger report reconstruction.
- Non-invasive RAG evidence builder output consistency.
- Contract-only RAG validation preparation output consistency.
- RAG evidence and validation artifact contract verification.
- RAG PoC dry-run integration contract and lineage output.

Not verified in this stage:

- Live YouTube API extraction, because it depends on external state and would
  create new extraction artifacts.
- RAG validation execution, because retrieval, generation, and validation are
  intentionally limited to the current PoC and were not executed in regression
  to avoid external calls.
- Full RAG PoC execution, because it may call OpenAI, Serper, embeddings, and
  Chroma when caches are absent.
- Full dependency installation in the current `.venv`, because it is Python
  3.14.3 and the reconciled environment is Python 3.12.13.
- Alternative detector algorithms, because only `xiao_ema` exists currently.

## Commands And Evidence

All commands were run from the repository root using `.venv/bin/python`.

| Check | Command Summary | Result |
|---|---|---|
| Syntax check | Compile all `youtube_pipeline/*.py` and `scripts/*.py` in memory. | Passed: 13 files. |
| Temporal contract | Verify storage and cleaning create `event_time_unix_s` / `published_at_unix_s` and retain legacy aliases as seconds. | Passed. |
| Legacy fallback | Load a JSONL record with only `event_time_unix_ms` while requesting `event_time_unix_s`. | Passed: fallback uses legacy field and infers seconds. |
| Cleaning regression | Recompute cleaning from `data/silver/comments` and compare all existing columns to `data/gold/clean_comments.parquet`. | Passed: 57,725 rows; existing values preserved. |
| Playback regression | Run playback to a temporary CSV and compare to `data/gold/snapshots_log3_variant.csv`. | Passed: shape, columns, and values identical. |
| Detector factory regression | Compare direct `XiaoEMATriggerDetector` with `create_detector("xiao_ema")`. | Passed: same 10 triggers. |
| Gold audit | Run `scripts/audit_gold_rag_thresholds.py`. | Passed: gold has 57,725 rows; temporal legacy field inferred as seconds; no exact duplicate excess in 2-minute windows. |
| Bronze stream audit | Run `scripts/audit_comment_stream.py` on `data/bronze/comments`. | Passed: 60,489 rows; 0 invalid timestamps; fallback from canonical seconds field to legacy field works. |
| Snapshot report | Run `scripts/extract_snapshot_trigger_report.py` on existing snapshots into a temporary directory. | Passed: summary, trigger log, and trigger snapshot map generated; 10 triggers reconstructed. |
| CLI playback with config | Run `youtube_pipeline/run_pipeline.py playback` with `--detector-config-file` into a temporary CSV. | Passed: output identical to expected snapshots. |
| RAG evidence builder | Run `scripts/build_rag_event_evidence.py` for `experiments/xiao/media/log_3`. | Passed: 10 events, 292 event-comment rows, 292 signal rows, 10 ready packages, 0 duplicate comments within event, 21 reply rows preserved. |
| RAG evidence config path | Run `scripts/build_rag_event_evidence.py --config-file` against a temporary JSON config. | Passed: 10 events, 292 event-comment rows, 10 anchor signal rows, 10 ready packages. |
| RAG validation preparation | Run `scripts/prepare_rag_validation.py` for `experiments/xiao/media/log_3/rag_evidence/event_evidence_packages.jsonl`. | Passed: 10 tasks, 60 retrieval questions, 40 query placeholders, 0 external evidence rows, 10 pending validation rows. |
| RAG validation config path | Run `scripts/prepare_rag_validation.py --config-file` against a temporary JSON config. | Passed: 10 tasks, 60 retrieval questions, 27 query placeholders with a lower per-event video cap, 10 pending validation rows. |
| RAG artifact verifier | Run `scripts/verify_rag_artifacts.py` against `experiments/xiao/media/log_3/rag_evidence` and `experiments/xiao/media/log_3/rag_validation`. | Passed: required files and columns exist; 10 event IDs align across evidence and validation; 292 comments are inside event windows; Unix-second timestamps match UTC timestamps; 0 errors and 0 warnings. |
| RAG PoC dry-run integration | Run `scripts/run_rag_poc_validation.py --dry-run` against `experiments/xiao/media/log_3/trigger_comment_map.csv` with optional RAG evidence lineage. | Passed: 292 trigger-comment rows, 10 trigger times, 51 `trigger_time + video_id` groups, 35 videos, 51 lineage rows, 10 linked event IDs, and 0 comment-count mismatches. |

## Functional Baseline Preserved

The following externally visible behavior was preserved:

- `data/gold/snapshots_log3_variant.csv` remains the reference snapshot output.
- Default playback with `xiao_ema` still detects the same three trigger log
  messages for the strict default configuration used by `run_playback`.
- The medium sensitivity reconstruction still produces 10 triggers.
- Existing gold dataset columns keep the same values when cleaning is
  recomputed from current silver data.
- Legacy timestamp fields remain readable.

## Critical Non-Changes

No changes were made to:

- detection formulas;
- EMA parameters;
- thresholds;
- spam or duplicate filtering rules;
- polarization metrics;
- snapshot CSV schema;
- existing datasets in `data/`;
- existing experiment outputs in `experiments/`;
- RAG PoC prompts, grouping, retrieval parameters, embeddings model, vector
  store behavior, or audit output schema.

## Residual Risks

- There is no formal automated test suite yet. The checks above are repeatable,
  but they are not packaged as CI.
- Existing generated `.pyc` files remain in the worktree from earlier command
  execution; they are not functional source changes.
- Live extraction remains unverified in regression because it depends on the
  YouTube API and current external data.
- RAG evidence is prepared by a non-invasive builder only; retrieval, query
  generation, and validation outputs in the full PoC still need a separate
  regression plan with cache controls and API-key handling.
- The RAG artifact verifier checks contract consistency for generated artifacts,
  but it does not validate event truth against external sources.

## Acceptance Criteria Status

| Criterion | Status |
|---|---|
| Architectural refactors preserve playback snapshots. | Passed |
| Detector modularization preserves default behavior. | Passed |
| Temporal contract remains backward compatible. | Passed |
| Cleaning preserves existing gold values. | Passed |
| RAG preparation does not alter execution behavior. | Passed |
| Verification evidence is documented. | Passed |
