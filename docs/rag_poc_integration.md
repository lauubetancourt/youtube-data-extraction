# RAG PoC Integration

This document describes how `triggers_validation.ipynb` is integrated as a
posterior pipeline phase without changing its RAG behavior.

## Source Of Truth

The implementation source is:

```text
.agents/examples/structured-rag-pdf/triggers_validation.ipynb
```

The executable integration lives in:

```text
youtube_pipeline/rag_poc.py
scripts/run_rag_poc_validation.py
```

The module preserves the notebook's core behavior:

- input unit: `trigger_time + video_id`;
- query model: `gpt-5-mini`;
- query and audit temperature: `1`;
- query prompt text;
- Serper endpoint: `https://google.serper.dev/news`;
- Serper parameters: `gl=co`, `hl=es`, `type=news`, `num=5`;
- Serper search window: `trigger_time +/- 1 day`;
- embeddings model: `text-embedding-ada-002`;
- vector stores: `vectorstore_comentarios` and `vectorstore_noticias`;
- audit prompt text;
- audit comment limit: first 15 comments per `trigger_time + video_id` group;
- output files: `queries_df.csv`, `noticias_df.csv`, and `auditoria_df.csv`.

## Required Environment

The full PoC execution requires:

- Python 3.12.13, as declared in `.python-version`;
- `OPENAI_API_KEY`;
- `SERPER_API_KEY`;
- dependencies declared in `requirements.txt`, including `langchain`,
  `langchain-openai`, `langchain-core`, `langchain-community`, `chromadb`, and
  `tiktoken`;
- `numpy==1.26.4`, which reconciles the current pipeline with
  `chromadb==0.5.5`.

The dry-run mode does not call OpenAI, Serper, Chroma, embeddings, or external
APIs. It only validates the input contract and writes lineage artifacts.

## Input Contract

The PoC input remains the same CSV contract used by the notebook:

```text
trigger_time,window_start,window_end,trigger_volume,trigger_strength,
order_in_trigger,event_time_utc,video_id,title,channel_title,author_id,
comment_id,text
```

The pipeline can provide this input from the current experiment artifact:

```text
experiments/xiao/media/log_3/trigger_comment_map.csv
```

The optional `event_comment_map.csv` from RAG evidence preparation is used only
to attach `event_id` lineage. It does not alter the RAG PoC input or outputs.

## Output Contract

The full PoC execution writes the same functional outputs as the notebook:

| Artifact | Description |
|---|---|
| `queries_df.csv` | One generated News API query per `trigger_time + video_id`. |
| `noticias_df.csv` | Serper news results for generated queries. |
| `auditoria_df.csv` | LLM audit result per `trigger_time + video_id`. |
| `vectorstore_comentarios/` | Chroma vector store for grouped comments. |
| `vectorstore_noticias/` | Chroma vector store for retrieved news. |

The integration also writes non-functional traceability artifacts:

| Artifact | Description |
|---|---|
| `rag_poc_manifest.json` | Run metadata, source notebook, paths, and PoC parameters. |
| `rag_poc_lineage.csv` | Mapping between `event_id`, `trigger_time`, `video_id`, comments, queries, news, and audit rows when available. |
| `rag_poc_summary.json` | Counts and output paths for the run. |

## Execution

Dry-run integration check:

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

The full execution may call OpenAI and Serper if cache files do not already
exist in the output directory.

## Integration Boundary

This integration does not change:

- event detection;
- stream replay;
- signal monitoring;
- detector thresholds;
- detector formulas;
- PoC prompts;
- PoC grouping;
- PoC output schemas.

The `event_id` bridge is stored in `rag_poc_lineage.csv` only. It is not added
to `queries_df.csv`, `noticias_df.csv`, or `auditoria_df.csv`.
