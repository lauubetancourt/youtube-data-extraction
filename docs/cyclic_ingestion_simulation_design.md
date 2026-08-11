# Diseno de simulacion ciclica de ingesta en linea

## 1. Objetivo

`cyclic_ingestion_simulation` agrega un modo de simulacion pseudo-online basado en ciclos periodicos de ingesta. El modo actual `retrospective_replay` se conserva como alternativa y no se elimina.

El nuevo modo no cambia algoritmos, thresholds, metricas ni logica del detector. Su responsabilidad es controlar que datos estan disponibles en cada ciclo y producir contratos trazables para fases posteriores.

## 2. Politica temporal

UTC es la zona horaria canonica para almacenamiento, comparacion temporal, filtrado del corpus y reglas contra fuga de futuro.

`America/Bogota` se usa solo como zona operativa inicial para definir cortes calendario diarios. Todo corte local debe convertirse y registrarse tambien en UTC.

Los intervalos temporales son semiabiertos:

```text
collection_window_start_utc <= event_time_utc < collection_window_end_utc
analysis_window_start_utc <= event_time_utc < analysis_window_end_utc
```

`collection_window_end_utc`, `analysis_window_end_utc` y `data_cutoff_utc`
representan el inicio exacto del siguiente periodo, no el ultimo segundo del
periodo anterior. Esto evita errores con timestamps subsegundo.

Regla obligatoria contra fuga de futuro:

```text
event_time_utc < data_cutoff_utc
```

## 3. Ciclo de ingesta

Un ciclo representa una ejecucion periodica del pipeline sobre datos disponibles hasta un corte temporal.

Campos minimos:

- `simulation_run_id`
- `cycle_id`
- `cycle_index`
- `cycle_run_at_local`
- `cycle_run_at_utc`
- `collection_window_start_local`
- `collection_window_end_local`
- `collection_window_start_utc`
- `collection_window_end_utc`
- `analysis_window_start_local`
- `analysis_window_end_local`
- `analysis_window_start_utc`
- `analysis_window_end_utc`
- `analysis_window_size_days`
- `data_cutoff_local`
- `data_cutoff_utc`
- `timezone`
- `canonical_timezone`
- `simulation_mode`
- `rag_mode`

Ejemplo de corte diario operativo:

```text
collection_window_start_local = 2026-02-20T00:00:00-0500
collection_window_end_local   = 2026-02-21T00:00:00-0500
collection_window_start_utc   = 2026-02-20T05:00:00Z
collection_window_end_utc     = 2026-02-21T05:00:00Z
```

## 4. Ventana diaria movil

El valor inicial configurable es:

```text
analysis_window_size_days = 3
```

La ventana analitica incluye el presente del ciclo y pasado reciente. Se podran comparar posteriormente ventanas de `1`, `2`, `3` y `5` dias.

## 5. Estado e inventarios

C-0/C-1 produce contratos e inventarios sin ejecutar monitoreo, deteccion ni RAG.

Artefactos:

- `online_simulation_manifest.json`
- `cycle_manifest.jsonl`
- `cycle_input_inventory.csv`
- `cycle_processed_inventory.csv`
- `cycle_quality_report.jsonl`
- `cycle_state.json`

`cycle_input_inventory.csv` registra cada fila fuente con su ciclo de primera aparicion. `cycle_processed_inventory.csv` registra los comentarios canonicos incluidos en cada ventana analitica.

## 6. Orquestador de ciclos C-2

C-2 lee los contratos generados por C-0/C-1 y construye un plan de ejecucion determinista sin ejecutar monitoreo, deteccion ni RAG.

Entradas:

- `online_simulation_manifest.json`
- `cycle_manifest.jsonl`
- `cycle_state.json`

Salidas:

- `cycle_orchestration_manifest.json`
- `cycle_orchestration_plan.jsonl`
- actualizacion controlada de `cycle_state.json`

Orden determinista:

```text
cycle_index asc
cycle_run_at_utc asc
cycle_id asc
```

Estados permitidos:

- `pending`
- `ready`
- `completed_dry_run`
- `failed_contract_validation`
- `skipped_no_comments`

C-2 debe fallar si se intenta activar cualquiera de estos flags:

```text
run_monitoring = true
run_detection = true
run_rag = true
```

## 7. Adaptador stateful C-3

C-3 prepara los insumos stateful para monitoreo y deteccion futura. No existe modo
stateless en esta etapa.

Entradas:

- `cycle_manifest.jsonl`
- `cycle_orchestration_plan.jsonl`
- `cycle_input_inventory.csv`
- `cycle_processed_inventory.csv`
- `cycle_state.json`

Salidas:

- `cycle_window_inventory.csv`
- `cycle_monitoring_inputs.jsonl`
- `cycle_detection_inputs.jsonl`
- `cycle_stateful_context.json`
- `cycle_detection_readiness_report.jsonl`
- `cycle_adapter_manifest.json`

Semantica stateful:

- un comentario solo puede ser nuevo una vez;
- un comentario puede aparecer como activo en varias ventanas por solapamiento;
- un comentario puede salir de la ventana cuando deja de cumplir el rango activo;
- el detector futuro no recibira solo comentarios nuevos, sino la ventana activa y
  el estado acumulado.

Reglas temporales:

```text
analysis_window_start_utc <= event_time_utc < analysis_window_end_utc
event_time_utc < data_cutoff_utc
```

C-3 debe fallar si se intenta activar:

```text
run_monitoring = true
run_detection = true
run_rag = true
```

## 8. Conexion controlada C-4

C-4 conecta los contratos C-3 con monitoreo y deteccion en modo controlado.
La implementacion mantiene dos modos:

```text
mode = "detection_dry_run"
mode = "detection_smoke_test"
```

`detection_dry_run` prepara y valida los inputs que recibirian monitoreo y deteccion, pero
no ejecuta `build_event_time_window_stream`, no instancia el detector, no llama
`on_event` y no produce triggers reales.

`detection_smoke_test` ejecuta una prueba pequena y controlada de monitoreo y
deteccion sobre pocos ciclos aprobados. Este modo resuelve los `comment_id`
activos de `cycle_window_inventory.csv` contra la fuente canonica
`data/gold/clean_comments.parquet` en memoria. No crea datasets completos por
ciclo, no duplica Gold y no reemplaza Bronze/Silver/Gold.

Entradas:

- `cycle_monitoring_inputs.jsonl`
- `cycle_detection_inputs.jsonl`
- `cycle_window_inventory.csv`
- `cycle_stateful_context.json`
- `cycle_adapter_manifest.json`
- `data/gold/clean_comments.parquet` solo en `detection_smoke_test`

Salidas:

- `cycle_monitoring_outputs.jsonl`
- `cycle_detection_outputs.jsonl`
- `cycle_detector_state.json`
- `cycle_event_registry.jsonl`
- `cycle_detection_manifest.json`
- `cycle_detection_quality_report.jsonl`

En `detection_smoke_test`, las salidas se escriben en una subcarpeta separada:

```text
cyclic_ingestion_simulation/detection_smoke_test/
```

y se agregan:

- `cycle_smoke_test_manifest.json`
- `cycle_smoke_test_join_report.jsonl`

Politica stateful:

- el detector futuro no debe reiniciarse entre ciclos;
- `cycle_detector_state.json` registra ciclos procesados y pendientes;
- `cycle_event_registry.jsonl` queda vacio en dry-run porque no se ejecuta deteccion;
- la politica de deduplicacion queda disenada pero no aplicada hasta ejecutar el detector.
- en smoke test, el detector stateful recibe cada comentario nuevo una sola vez;
- la ventana activa completa se valida y se registra por ciclo, aunque se solape con ciclos previos.

Politica de materializacion en `detection_smoke_test`:

- `cycle_window_inventory.csv` funciona como indice de ciclo y ventana;
- `data/gold/clean_comments.parquet` funciona como fuente canonica principal;
- la materializacion de filas se realiza en memoria;
- `debug_full_rows = false` por defecto;
- `debug_cycle_materialized_rows.parquet` no se genera sin aprobacion explicita;
- `comment_id` debe ser unico en Gold antes de ejecutar monitoreo/deteccion;
- `comment_id` activo de la ventana debe ser subconjunto de Gold;
- `joined_comment_count == active_window_comment_count`;
- `missing_comment_id_count == 0`;
- `extra_joined_comment_count == 0`;
- `event_time_utc < data_cutoff_utc`;
- `analysis_window_start_utc <= event_time_utc < analysis_window_end_utc`.

Guardas de ejecucion:

```text
run_monitoring = false
run_detection = false
run_rag = false
```

En `detection_smoke_test`, `run_monitoring` y `run_detection` no se activan como
flags externos; el camino aprobado los controla internamente. `run_rag` sigue
prohibido.

## 9. Duplicados y comentarios tardios

La llave de deduplicacion es `comment_id`.

Las filas duplicadas no se cuentan como comentarios nuevos despues de la primera aparicion. En esta etapa, comentarios tardios no se pueden inferir si no existe un timestamp real de ingesta separado de `event_time_utc`.

## 10. Nota historica/backlog: adaptador C-5 de senales diarias para XIAO

Esta seccion queda como nota historica y backlog tecnico. No forma parte de la
rama vigente del detector diario. La decision actual es no adaptar XIAO por
ahora, mantener `XiaoEMATriggerDetector` intacto para `retrospective_replay` o
trabajo futuro, y usar `daily_frequency_baseline` como detector diario externo.

La idea explorada para C-5 cambiaba la unidad de entrada del decisor: XIAO se
mantenia como decisor, pero no recibia comentarios individuales. Recibia una
observacion diaria agregada por ciclo, calculada sobre la ventana movil diaria
activa.

Modo inicial:

```text
mode = "signals_dry_run"
```

Este modo no ejecuta XIAO. Solo prepara la serie diaria de senales y el contrato
normalizado que XIAO podria consumir en una etapa posterior.

Flujo:

```text
cycle_window_inventory.csv
-> join contra data/gold/clean_comments.parquet
-> vista en memoria por ventana movil diaria
-> calculo de senales agregadas por ciclo
-> cycle_signal_series.jsonl
-> cycle_xiao_inputs.jsonl
-> futura ejecucion stateful de XIAO
```

Senales minimas:

- `active_window_comment_count`
- `new_comment_count`
- `exited_window_comment_count`
- `active_video_count`
- `unique_author_count`, si existe `author_id`
- `reply_count` y `reply_ratio`, si existe `is_reply`
- `emoji_density`, si existe `emoji_count`
- `exclaim_density`, si existe `exclamation_count`
- `question_density`, si existe `question_count`
- `caps_ratio_mean`, si existe `caps_ratio`
- `sentiment_mean` y `sentiment_std`, si existe `sentiment_score`
- `delta_active_window_comment_count`
- `pct_change_active_window_comment_count`
- `comment_ids_hash`
- `new_comment_ids_hash`

Contrato para XIAO:

- `simulation_run_id`
- `cycle_id`
- `cycle_index`
- `signal_date`
- `observation_time_utc`
- `analysis_window_start_utc`
- `analysis_window_end_utc`
- `data_cutoff_utc`
- `xiao_signal_name`
- `xiao_signal_value`
- `delta_signal_value`
- `pct_change_signal_value`
- `support_comment_count`
- `active_video_count`
- `comment_ids_hash`
- `join_status`
- `temporal_status`
- `schema_status`

Valor inicial:

```text
xiao_signal_name = "active_window_comment_count"
```

Politica de doble conteo:

- no se envian comentarios individuales repetidos a XIAO;
- cada ciclo produce una sola observacion agregada;
- los comentarios pueden aparecer en varias ventanas por solapamiento;
- los comentarios solo contribuyen al agregado de su ventana activa;
- no se suman ventanas entre si;
- cada observacion conserva hashes para auditoria.

Artefactos:

- `cycle_signal_manifest.json`
- `cycle_signal_join_report.jsonl`
- `cycle_signal_series.jsonl`
- `cycle_signal_quality_report.jsonl`
- `cycle_xiao_inputs.jsonl`

No se generan todavia:

- `cycle_xiao_state.json`
- `cycle_daily_events.jsonl`

Guardas:

```text
run_xiao = false
run_detection = false
run_rag = false
run_llm = false
run_serper = false
use_embeddings = false
use_vectorstore = false
```

## 11. Integracion futura con monitoreo, deteccion y RAG

C-0/C-1 no ejecuta monitoreo, deteccion, sidecars RAG, G-1, G-2, LLM, Serper, embeddings ni vectorstore.

Fases futuras podran consumir los inventarios por ciclo para ejecutar el pipeline sobre datos temporalmente disponibles sin alterar `retrospective_replay`.

## 12. Detector diario baseline externo a XIAO

El detector `daily_frequency_baseline` es un baseline diario para validar la
simulacion ciclica por ciclos. No reemplaza XIAO y no modifica
`XiaoEMATriggerDetector`, `create_detector("xiao_ema")`, thresholds, EMA,
warm-up, cooldown ni `retrospective_replay`.

Flujo:

```text
cycle_signal_series.jsonl
-> daily_frequency_baseline
-> cycle_daily_frequency_scores.jsonl
-> cycle_daily_frequency_events.jsonl
```

Senal principal inicial:

```text
signal_name = "new_comment_count"
```

Regla configurable:

```text
current_value >= min_count
AND current_value > k_multiplier * mean(previous baseline_window_size_cycles)
AND delta_value >= min_delta
AND, si use_pct_change = true:
    pct_change_value >= min_pct_change
AND, si trigger_on_increase_only = true:
    delta_value > 0
AND, si cooldown_cycles > 0:
    no esta en cooldown
```

Parametros exploratorios iniciales:

```json
{
  "signal_name": "new_comment_count",
  "baseline_window_size_cycles": 3,
  "k_multiplier": 2.0,
  "min_count": 500,
  "min_delta": 250,
  "min_pct_change": 0.5,
  "warmup_cycles": 3,
  "cooldown_cycles": 0,
  "cooldown_policy": "disabled_for_daily_detection",
  "use_pct_change": true,
  "use_delta": true,
  "trigger_on_increase_only": true,
  "parameter_status": "exploratory_defaults"
}
```

La politica vigente deshabilita el cooldown por defecto porque, en deteccion
diaria, un ciclo consecutivo puede representar una fase distinta, una escalada o
un subevento legitimo. El detector conserva soporte opcional para
`cooldown_cycles > 0`, pero esa ya no es la configuracion base.

La politica de `pct_change` es explicita: si el valor previo es cero,
`pct_change_value = null` y `pct_change_status =
"undefined_previous_zero"`. Esto no falla la corrida, pero si
`use_pct_change = true`, el ciclo no pasa la condicion de cambio porcentual.

Artefactos:

- `cycle_daily_frequency_scores.jsonl`
- `cycle_daily_frequency_events.jsonl`
- `cycle_daily_frequency_detector_manifest.json`
- `cycle_daily_frequency_quality_report.jsonl`

## 13. Modos de ejecucion

Modos reconocidos:

```text
simulation_mode = "retrospective_replay"
simulation_mode = "cyclic_ingestion_simulation"
```

La seleccion del modo debe hacerse por configuracion. El modo ciclico genera artefactos propios en una carpeta separada y no reemplaza salidas actuales.

## 14. Riesgos metodologicos

- fuga de informacion futura;
- doble conteo de comentarios;
- reinicio incorrecto de estado en fases posteriores;
- eventos duplicados entre ciclos;
- comentarios tardios no observables sin timestamp de ingesta;
- perdida de eventos entre cortes diarios;
- ventanas diarias demasiado largas o cortas;
- RAG usando evidencia posterior en fases futuras;
- diferencia entre API real y corpus historico;
- costo de ejecutar RAG por ciclo;
- el detector diario baseline puede detectar picos de frecuencia sin capturar polarizacion o semantica;
- backlog historico: si se retoma XIAO diario, habria que validar el cambio de
  escala temporal antes de ejecutar `XiaoEMATriggerDetector` con senales
  agregadas.

## 15. Plan por etapas

- C-0: contratos de ciclo.
- C-1: particionador temporal del corpus.
- C-2: orquestador de ciclos.
- C-3: adaptador hacia monitoreo/deteccion.
- C-4: conexion controlada hacia monitoreo/deteccion.
- C-5: senales diarias agregadas en modo dry-run.
- D: detector diario baseline externo a XIAO.

La implementacion actual cubre C-0/C-1, C-2, C-3 y C-4 con
`detection_dry_run` y `detection_smoke_test`, y C-5 con `signals_dry_run`.
C-5 no ejecuta XIAO ni RAG. D ejecuta solo el detector diario baseline externo.
La adaptacion de XIAO diario queda fuera del informe vigente y solo deberia
retomarse con aprobacion explicita.
