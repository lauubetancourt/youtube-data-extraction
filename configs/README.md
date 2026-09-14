# Versionable execution configuration

**Status:** CURRENT CONFIGURATION AUTHORITY
**Architecture context:** [`docs/pipeline_architecture.md`](../docs/pipeline_architecture.md).

Files under `configs/` describe concrete executions or methodologies. They do not
store secrets, datasets, or generated outputs, and the project does not create one
profile per component.

## Configuration model

`RunConfig` is the immutable composition root for one execution:

```text
RunConfig
├── identity
├── data
├── simulation
├── signals
├── detection
├── rag
└── artifacts
```

Sections are optional when a run does not use them. Each section reuses the
component's existing typed configuration; `RunConfig` does not copy detector,
signal, RAG, storage, or replay parameters.

Components receive only the subconfiguration they need. Domain modules do not read
JSON, parse CLI arguments, inspect environment variables for methodological values,
or receive the complete `RunConfig` merely for convenience.

## Resolution and precedence

The common configuration path is:

```text
typed component defaults
→ versionable JSON profile
→ explicit supported overrides
→ strict validation
→ path resolution
→ resolved configuration
```

Unknown keys are rejected. Values are not silently coerced to unrelated types.
Explicit CLI overrides apply after file values, but the common CLI is limited to:

- `--config`;
- `--run-id`;
- `--output-root`;
- `--dry-run` or `--execute`;
- `--log-level`.

Methodological parameters remain in component configurations and profiles. Legacy
wrappers may translate older arguments into the same resolver, but they do not
introduce new defaults.

## Paths

Profiles store logical paths. `resolve_run_config` resolves them relative to the
profile/workspace boundary before components execute. Canonical serialization
normalizes known paths so a machine-specific absolute workspace path does not
change `config_hash`.

Historical locations such as:

- `data/gold/clean_comments.parquet`;
- `experiments/xiao/media/log_3/cyclic_ingestion_simulation`;

remain `LEGACY_COMPATIBILITY_DEFAULT` values in current profiles and entrypoint
shims. They are not embedded authorities in signal or detector logic. Another
prepared dataset can be selected by changing `DataConfig`/component paths, without
editing domain code.

Configuration declares where a dataset is. Dataset storage, fingerprinting,
distribution, and recovery belong to STAB-DATA-01.

## Effective configuration and hash

The resolver produces:

- a typed, path-resolved `RunConfig`;
- deterministic canonical JSON (`resolved_config`);
- a SHA-256 `config_hash` computed from effective values.

The canonical representation includes component defaults after resolution and
excludes machine-specific path prefixes where configured. A methodological change
changes the hash; merely running from another workspace does not.

The execution-level manifest records the global `run_id`, run mode, trace level,
`config_hash`, `resolved_config`, execution mode, and completed stages. It does not
copy the same configuration into every component artifact.

## Signal-to-detector selection

When a neutral activity route is configured, the association is explicit:

```json
{
  "detection": {
    "activity_route": {
      "signal_id": "comment_count_event_window_120s_step_30s",
      "detector_id": "xiao_ema"
    },
    "xiao_ema": {
      "v_min": 46
    }
  }
}
```

`activity_route` contains references only. Signal semantics remain authoritative in
`ActivitySignalDefinition`; XIAO parameters remain authoritative in
`XiaoEMAConfig`. The route and loader are implemented and tested, but the integrated
cyclic compatibility profile has not yet adopted this route as its general runtime
dispatch.

Page-Hinkley can be selected explicitly without changing the signal definition:

```json
{
  "detection": {
    "activity_route": {
      "signal_id": "comment_count_event_window_120s_step_30s",
      "detector_id": "page_hinkley"
    },
    "page_hinkley": {
      "min_instances": 30,
      "delta": 0.005,
      "threshold": 50.0,
      "alpha": 0.9999,
      "mode": "both"
    }
  }
}
```

ADWIN uses the same route without changing the signal's physical-time window:

```json
{
  "detection": {
    "activity_route": {
      "signal_id": "comment_count_event_window_120s_step_30s",
      "detector_id": "adwin"
    },
    "adwin": {
      "delta": 0.002,
      "clock": 32,
      "max_buckets": 5,
      "min_window_length": 5,
      "grace_period": 10
    }
  }
}
```

The Page-Hinkley and ADWIN values shown above mirror River's technical defaults;
they are not calibrated or methodologically validated for event detection. No
current profile selects either detector by default, and cyclic execution has not
been connected to the neutral route. ADWIN's adaptive window counts observations
inside the detector and does not replace `ActivitySignalDefinition.window`.

## Current profiles

### `compatibility/cyclic_current.json`

Represents the migrated cyclic compatibility execution:

```text
cyclic simulation
→ daily signals
→ XIAO connector compatibility configuration
→ daily_frequency_baseline
```

It preserves the current event-time, Bogotá timezone, XIAO, baseline, and guarded
dry-run parameters. Its historical data/output paths are compatibility values, not
permanent architecture.

Run it without overwriting the historical output tree:

```bash
.venv/bin/python scripts/run_cyclic_pipeline.py \
  --config configs/compatibility/cyclic_current.json \
  --output-root outputs/cyclic_current \
  --dry-run
```

### `compatibility/daily_rag_current.json`

Represents the current non-generative daily RAG execution:

```text
daily events
→ daily sidecars
→ daily consumer
→ deterministic context selection
```

It preserves separate historical identities for sidecars (`drun_*`), consumer
(`dragconsumer_*`), and selection (`dragselect_*`). The global `run_id` supplies
execution context and does not replace these stage identities.

```bash
.venv/bin/python scripts/run_daily_rag_pipeline.py \
  --config configs/compatibility/daily_rag_current.json \
  --output-root outputs/daily_rag_current \
  --dry-run
```

Profiles represent real executions. A new profile should answer which execution or
methodology it preserves and why it needs versioning. Similar component-level files
should not proliferate.

## Traceability policy

Typed minimum levels are:

- `development` → `minimal`;
- `reference` → `standard`;
- `official` → `full`.

The current integrated runners implement only `development/minimal`. Requesting a
higher unimplemented policy fails before artifacts are created. The type model can
represent future policies without claiming their persistence behavior already
exists.

## Secrets and infrastructure

API keys and provider credentials are resolved at entrypoint/infrastructure
boundaries. They never belong in profiles, `RunConfig`, `resolved_config`,
`config_hash`, or methodological manifests.

Logging level and execution mode are operational controls. They are not detector or
signal parameters.

## Legacy compatibility

Stage-specific scripts and `run_pipeline.py` remain where their interfaces are
tested. They translate legacy inputs to the common resolver and may preserve old
path defaults. New methodological parameters must not be added independently to
those wrappers.

Removal requires all of the following:

```text
replacement working
+ compatibility tests passing
+ no required consumers
+ documentation updated
```
