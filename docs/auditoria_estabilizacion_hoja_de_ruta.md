# Auditoría de estabilización y hoja de ruta del trabajo de grado

**Fecha de corte:** 8 de agosto de 2026  
**Repositorio auditado:** `youtube-data-extraction`  
**Rama observada:** `feature/pipeline`  
**Alcance:** inspección estática, inventario de archivos, lectura de manifests y contratos, contraste con los dos documentos académicos suministrados y ejecución local de pruebas de bajo costo. No se ejecutaron extracción, replay completo, RAG generativo, LLM, Serper, embeddings ni servicios externos. No se borraron, movieron, refactorizaron ni reescribieron artefactos existentes.

Las cantidades y tamaños son una fotografía del estado local. Se redondean a MiB y pueden variar ligeramente por metadatos del sistema de archivos. El árbol de trabajo ya estaba sucio antes de esta auditoría; por tanto, este informe no atribuye autoría a cambios locales ni recomienda descartarlos.

## 1. Resumen ejecutivo

1. El proyecto tiene una base técnica avanzada y modular: adquisición, Bronze/Silver/Gold, replay retrospectivo, simulación cíclica, baseline diario, evidencia RAG y validaciones de trazabilidad existen. Sin embargo, aún es un conjunto de prototipos conectados por archivos, no un flujo en línea reanudable de extremo a extremo.
2. El riesgo inmediato no es algorítmico sino de control del proyecto: casi toda la familia cíclica, nueve de diez archivos de pruebas y su documento de diseño están sin seguimiento en Git; al mismo tiempo, `.gitignore` ignora globalmente `*.json` y `*.csv`, incluidos manifests críticos.
3. `experiments/` contiene 1.569 archivos y aproximadamente 1.235,64 MiB. Tres corridas retrospectivas concentran 1.036,11 MiB; cerca de 995 MiB corresponden a tres copias del mismo contenido Bronze/Silver/Gold y de los mismos CSV normalizados.
4. No es seguro borrar `experiments/xiao/media/log_3/` completo: README, documentación y valores por defecto del código lo usan como entrada. Sí hay candidatos claros, en especial la corrida parcial `run_20260602T180515Z` y copias de datos dentro de corridas, pero cualquier borrado debe seguir a un índice de dependencias y a una selección explícita de evidencia metodológica.
5. La separación propuesta por la estudiante es adecuada: desarrollo con trazabilidad mínima o estándar; casos de estudio oficiales con trazabilidad completa e inmutable. Debe formalizarse con `run_mode`, `trace_level`, un índice de corridas, estados de terminación y retención por clase, no solo con nombres de carpetas.
6. El principal cuello de botella retrospectivo está en `monitoring.py`: por cada comentario reconstruye un `DataFrame` con toda la ventana y conserva un snapshot por evento. En las corridas de 178.289 comentarios esto produce trabajo aproximado O(N × tamaño de ventana), memoria acumulada y CSV de un registro por comentario.
7. La simulación cíclica resuelve correctamente varias cuestiones —orden determinista, ventanas semiabiertas, control de fuga temporal y joins por `comment_id`—, pero materializa 230.419 membresías de ventana y 128 MiB de CSV. Su estado del detector no contiene EMA/cooldown serializables; no puede reanudarse fielmente después de un fallo.
8. A7 no debe comenzar por implementar ER, EMD o MEC. Falta primero un contrato de representación de opinión y de distribución temporal. Los campos actuales llamados `polarization.*` son media/desviación de sentimiento o densidades de emoji/puntuación; son proxies discursivos, no medidas formales de polarización.
9. A6 puede avanzar después de la estabilización con señales derivadas de comentarios ya disponibles. Las tasas de vistas, likes y conteos de video requieren snapshots repetidos con `observed_at_utc`; el dataset actual contiene una sola observación final y usarla en replay produciría fuga de información histórica.
10. Tras cerrar los P0 y P1 indicados en este informe, es seguro continuar de manera acotada: primero un harness contractual con corpus fijo; después representación de opinión y señales en ese harness; por último, integración incremental y casos de uso oficiales. No se recomienda ampliar A6/A7/A9 directamente sobre las corridas grandes actuales.

## 2. Mapa actual del repositorio

### 2.1 Directorios y papel real

| Ruta | Papel observado | Estado |
|---|---|---|
| `youtube_pipeline/` | Código de dominio y de artefactos: extracción, storage, limpieza, replay, monitoreo, detectores, simulación cíclica, baseline diario y familias RAG. | Núcleo funcional; 57 archivos, 1,55 MiB y 20.474 líneas Python. Nueve módulos cíclicos/diarios aparecen sin seguimiento. |
| `scripts/` | Entradas CLI y scripts de auditoría/reconstrucción. | Mezcla de adaptadores delgados con scripts de dominio grandes; 29 archivos, 0,22 MiB. Diez scripts fuente aparecen sin seguimiento. |
| `tests/` | Pruebas `unittest`, concentradas en simulación cíclica, baseline diario y RAG diario/hierárquico. | 43 pruebas pasan; solo `test_rag_generation_g2_hierarchical.py` está registrado en Git. |
| `data/bronze/` | Snapshot fuente de videos/comentarios y metadata de extracción. | Fuente canónica por corrida; 3 archivos, 34,25 MiB. El manifest JSON está ignorado por Git. |
| `data/silver/` | Videos y comentarios normalizados, particionados en Parquet por fecha. | Capa canónica operativa pero reproducible; 84 archivos, 8,01 MiB. |
| `data/gold/` | Comentarios limpios para replay y snapshot retrospectivo de referencia. | `clean_comments.parquet` es la fuente analítica actual; 2 archivos, 17,38 MiB. El snapshot CSV es reproducible. |
| `data/caso-uribe/` | Corpus local de 706 videos y 185.874 comentarios con clasificación/sentimiento. | Dataset fuente de corridas retrospectivas; 2 archivos, 46,48 MiB, ignorados y sin manifest de linaje visible. |
| `experiments/xiao/` | Resultados de calibración, replay, RAG, sidecars y simulación cíclica. | 1.568 de los 1.569 archivos de `experiments/`; 1.235,63 MiB. Mezcla insumos, estados, reportes y copias de datos. |
| `notebooks/` | Extracción/limpieza históricas, sentimiento, TF-IDF, grafos y anonimización. | 10 notebooks, 2,02 MiB. La mayoría antecede al paquete actual y usa CSV legacy. |
| `docs/` | Contratos y auditorías anteriores de pipeline/RAG. | Útiles, pero `pipeline_architecture.md`, `data_contracts.md` y `regression_verification.md` no describen toda la familia cíclica actual. |
| `.agents/examples/structured-rag-pdf/` | Repositorio Git anidado de referencia. | 786 MiB; no es una carpeta de resultados del pipeline. Está modificado y debe excluirse de cualquier limpieza automática. |
| `logs/`, `outputs/`, `reports/`, `sidecars/`, `cache/`, `tmp/`, `debug/` | Patrones solicitados para revisión. | No existen como directorios superiores. Sus funciones están embebidas dentro de cada corrida en `experiments/`. |

También se observaron 42 archivos `__pycache__` —aproximadamente 0,96 MiB— y varios `.DS_Store`. Son residuos locales, no evidencia experimental.

### 2.2 Flujo principal reconstruido

```text
YouTube API o CSV legacy
  -> DataFrames de videos/comentarios
  -> Bronze JSONL + manifest de extracción
  -> Silver Parquet particionado
  -> limpieza completa
  -> Gold clean_comments.parquet
       |-> replay retrospectivo Streamz
       |     -> snapshots por comentario + Xiao EMA
       |     -> trigger logs/maps
       |     -> evidencia/sidecars RAG
       |     -> consumer payloads
       |     -> G-1 / G-2 / G-2 jerárquico
       |
       `-> partición cíclica diaria C-0/C-1
             -> orquestación dry-run C-2
             -> inventario stateful C-3
             |    -> C-4 dry-run/smoke Xiao
             `-> señales diarias C-5
                    -> daily_frequency_baseline
                    -> eventos diarios
                    -> sidecars RAG diarios
                    -> consumer diario
                    -> selección determinista de contexto
```

### 2.3 Fases, contratos y volúmenes observados

| Fase | Entrada | Salida / estado persistente | Formato y volumen observado | Consumidor |
|---|---|---|---|---|
| Adquisición | YouTube API, configuración y clave de entorno. | DataFrames, estado de cuota/errores. | Corrida canónica: 112 videos y 60.489 filas de comentarios. | Storage. |
| Bronze | DataFrames completos. | Un JSONL de videos, uno de comentarios y manifest de corrida. | 34,25 MiB. | Auditoría y reconstrucción de Silver. |
| Silver | Mismos lotes con tiempo UTC y particiones. | Directorios Parquet de videos/comentarios. | 112 videos; 60.489 filas de comentarios, 60.420 `comment_id` únicos. | Limpieza. |
| Gold | Silver completo. | Comentarios limpios con features textuales. | Parquet; 57.725 filas, 24 columnas, 112 videos. | Replay y simulación cíclica. |
| Retrospectivo | Gold completo ordenado por `event_time_utc`. | Stream, snapshots, detector en memoria y logs/mapas reconstruidos por scripts. | Un snapshot por comentario; la corrida grande produce 178.289 snapshots. | Reportes y RAG retrospectivo. |
| C-0/C-1 | Gold completo. | Manifest, estado, 49 ciclos, inventarios de entrada/procesados. | JSON/JSONL y CSV; 57.725 comentarios, ventana máxima 12.786. | C-2/C-3. |
| C-2 | Manifest, estado y ciclos. | Plan y estado de orquestación. | 49 ciclos, todos `completed_dry_run`. | C-3. |
| C-3 | Inventarios C-1 y plan C-2. | Ventanas, entradas de monitoreo/detección y contexto stateful. | 230.419 filas de ventana; 13,07 MiB de IDs repetidos en JSON. | C-4/C-5. |
| C-4 | Índices C-3 y Gold. | Dry-run de 5 ciclos o smoke test de 2 ciclos, registry y supuesto estado. | Sin filas completas por ciclo; join por IDs en memoria. | Diagnóstico de detección. |
| C-5 | Ventanas C-3 y Gold. | Una observación agregada por ciclo y contrato histórico para XIAO. | 49 observaciones; JSONL pequeño. | Baseline diario. |
| Baseline diario | Serie C-5. | Scores, calidad, eventos y manifest. | 4 eventos con cooldown 1; 5 eventos con cooldown desactivado. | RAG diario. |
| Sidecars RAG diarios | 5 eventos, Gold y ventana C-3. | Inventarios, mapas, unidades y paquetes de evidencia. | 25.661 pares evento-comentario; 3.261 unidades; 36,83 MiB. | Consumer diario. |
| Consumer/selección diarios | Sidecars completos. | Payloads completos, stubs, reporte de tamaño y selección. | 15,47 + 1,21 MiB; se seleccionan 1.893 comentarios y se omiten 3.147 unidades por presupuesto. | Futuro RAG generativo. |
| RAG retrospectivo | Eventos, comentarios, snapshots/sidecars. | G-1 interno, G-2 externo y G-2 jerárquico, manifests y respuestas crudas. | `media/log_3`: 10 eventos históricos; corrida local seleccionada: 18 eventos, G-1 completo y G-2 con 5 videos pendientes. | Validación y reporte. |

### 2.4 Modos de ejecución reales

| Modo | Qué hace | Estado real |
|---|---|---|
| `retrospective_replay` | Reproduce todo el historial por tiempo de evento con Streamz y Xiao EMA. | Funcional, costoso para el corpus grande; principal fuente de snapshots y pruebas históricas. |
| `cyclic_ingestion_simulation` | Parte un Gold histórico en cortes diarios y ventanas móviles de tres días. | Funcional como simulador offline; no ingiere una fuente viva. |
| `dry_run` | Valida y materializa contratos sin ejecutar detector/RAG. | Muy usado en C-0 a C-5; aun así produce artefactos voluminosos. |
| `detection_smoke_test` | Une por `comment_id` contra Gold y ejecuta monitoreo/Xiao en pocos ciclos. | Solo 2 de 49 ciclos en el artefacto actual. |
| `daily_frequency_baseline` | Evalúa frecuencia diaria sobre las 49 observaciones. | Funcional y exploratorio; configuración raíz y subcarpeta difieren en cooldown. |
| RAG retrospectivo | Prepara evidencia y ejecuta G-1/G-2/G-2 jerárquico. | Existen resultados generativos y externos; no son casos A10 oficiales. |
| RAG diario | Sidecars, payloads y selección de contexto sin servicios externos. | Funcional hasta la selección; no ha ejecutado validación generativa diaria. |

## 3. Auditoría de artefactos y trazabilidad

### 3.1 Inventario y clasificación

| Categoría | Ruta o patrón | Archivos / tamaño | Generador y dependencias | Reproducibilidad | Recomendación |
|---|---|---:|---|---|---|
| A. Canónico fuente | `data/bronze/{videos,comments}/*.jsonl` y `data/bronze/runs/*.json` | 3 / 34,25 MiB | `persist_batch_snapshot` y extracción; origen de Silver. | No debe asumirse regenerable sin volver a consultar la API. | Conservar inmutable. Guardar manifest y hash junto al lote; mover datos grandes a almacenamiento versionado externo si Git es remoto/público. |
| A/B. Canónico operativo | `data/silver/{videos,comments}/` | 84 / 8,01 MiB | Storage desde Bronze/CSV. Consumido por limpieza. | Sí, si Bronze y reglas exactas están disponibles. | Conservar por ahora; después permitir regeneración controlada. Nunca mezclar lotes sin política de upsert. |
| A/B. Canónico analítico | `data/gold/clean_comments.parquet` | 1 / ~12,82 MiB | Limpieza de Silver. Consumido por todos los modos. | Sí en principio; hoy faltan hashes/config/code commit completos para demostrar igualdad. | Conservar como fuente de verdad analítica hasta cerrar reproducibilidad. Versionar manifest/hash, no necesariamente el binario en Git. |
| B. Reproducible | `data/gold/snapshots_log3_variant.csv`, `experiments/xiao/{baja/log_2,media/log_3}/snapshots.csv` | 3 × 4,56 MiB | Replay/monitoreo desde el mismo Gold. | Sí; los tres archivos son byte a byte iguales. | Mantener una referencia con hash; borrar copias solo después de retirar referencias. No versionar cada copia. |
| A/F. Fuente sin linaje cerrado | `data/caso-uribe/` | 2 / 46,48 MiB | Entrada de las corridas retrospectivas locales. | No se debe asumir regenerable; no hay manifest de adquisición visible. | Conservar y documentar procedencia, permisos, hash y rol antes de cualquier limpieza. |
| B/F. Compatibilidad legacy | `data/comments.csv`, `data/videos*.csv` | 4 / ~15,81 MiB | Exportes legacy de extracción. | Sí desde el lote actual; `data/videos.csv` duplica exactamente `data/caso-uribe/videos.csv`. | Mantener mientras notebooks/scripts dependan de ellos; luego archivar uno por corpus y usar referencias. |
| C. Experimento relevante | `experiments/xiao/media/log_3/` sin la subcarpeta cíclica | 161 / ~10,66 MiB | Replay, evidencia, consumer y variantes G-1/G-2. README y código lo referencian. | Sidecars son reproducibles; respuestas LLM/Serper no lo son de forma determinista y tienen costo. | Seleccionar un bundle de referencia metodológica. Conservar manifests, prompts/hashes, métricas, evidencia externa y respuestas elegidas; retirar duplicados solo tras actualizar dependencias. |
| B/C. Simulación relevante | `experiments/xiao/media/log_3/cyclic_ingestion_simulation/` | 58 / 166,26 MiB | C-0…C-5, baseline y RAG diario. | Casi todo es regenerable desde Gold/config/código; representa decisiones recientes. | Conservar manifests, señales, eventos, calidad y una muestra de evidencia. Tratar inventarios y payloads detallados como efímeros en desarrollo. |
| D. Obsoleto/sustituido | `.../run_20260602T180213Z/` | 359 / 348,30 MiB | Replay local con `v_min=46`; produjo 0 triggers. | Sí, salvo que se quiera conservar como evidencia de una calibración descartada. | Guardar manifest/métricas y, si se documenta la decisión, un resumen. Borrar el detalle después de revisión. |
| D. Parcial | `.../run_20260602T180515Z/` | 354 / 331,66 MiB | Ejecución interrumpida; no tiene `run_manifest.json`. | Sus datos de entrada son copias; el resultado no está completo. | Candidato más seguro para borrar después de confirmar que no existe referencia externa. Conservar solo diagnóstico de fallo si aporta algo. |
| C/B. Experimento relevante seleccionado | `.../run_20260602T180842Z/` | 627 / 356,15 MiB | Replay con `v_min=15`, 18 triggers, sidecars y G-1/G-2. | Copias de datos/sidecars sí; respuestas y evidencia externa no completamente. | Archivar como corrida de referencia, no oficial. Conservar resumen consolidado, manifests y resultados costosos; eliminar después las copias de datos canónicos y retries redundantes. |
| D/F. Históricos | `experiments/xiao/alta/log_1/`, `baja/log_2/` | 7 / 22,59 MiB | Calibraciones anteriores. | `baja` duplica snapshots actuales; `alta` contiene Gold duplicado pero 231 snapshots adicionales sin explicación inmediata. | `baja`: borrar detalle tras preservar resumen. `alta`: revisión manual antes de borrar por discrepancia de filas. |
| D/C. Variantes RAG repetidas | `rag_generation_g2_hierarchical{,_primary,_evt_*,_batch,_batch_auto_lot1}` y retries de la corrida local | Decenas de archivos; ~10 MiB en conjunto | Reintentos por evento/lote. Hay eventos evaluados en más de una carpeta y lotes incompletos. | No deterministas por LLM/Serper. | Elegir la corrida que sustenta la decisión académica; archivar sus crudos. El resto es candidato a limpieza, nunca por nombre solamente. |
| E. Temporal/debug | `**/__pycache__`, `*.pyc`, `.DS_Store` | ~46 archivos / <1 MiB | Python/macOS. | Totalmente regenerable. | Ignorar en Git y borrar con limpieza rutinaria aprobada. |
| F. Fuera de limpieza automática | `.agents/examples/structured-rag-pdf/` | repositorio anidado / 786 MiB | Dependencia/referencia de trabajo, no ejecución del pipeline. | Desconocida; además está modificado. | Excluir de `cleanup`. Resolver su política como submódulo/dependencia en una tarea separada. |

No se encontró todavía ningún resultado que pueda etiquetarse como “caso de uso oficial A10”. Los resultados generativos existentes son evidencia experimental y de diseño, no resultados finales del trabajo de grado.

### 3.2 Duplicación cuantificada

- Las tres corridas locales contienen 349 archivos y 254,96 MiB cada una bajo `data/`. Los nombres temporales difieren, pero el multiconjunto de hashes y tamaños de sus 349 contenidos es idéntico.
- Cada corrida también contiene los mismos dos CSV bajo `local_csv_load/`: 76,70 MiB idénticos. Solo esas dos familias suman cerca de 995 MiB duplicados.
- `data/gold/clean_comments.parquet` y `experiments/xiao/alta/log_1/clean_comments.parquet` son idénticos.
- `data/videos.csv` y `data/caso-uribe/videos.csv` son idénticos.
- El trigger map de `media/log_3` está copiado byte a byte dentro del repositorio anidado `.agents/examples/structured-rag-pdf/`.
- Los inventarios cíclicos grandes son: `cycle_window_inventory.csv` 48,74 MiB, `cycle_processed_inventory.csv` 37,74 MiB, `cycle_input_inventory.csv` 12,63 MiB y `cycle_stateful_context.json` 13,07 MiB.
- El RAG diario vuelve a materializar parte del mismo contenido: sidecars 36,83 MiB, consumer 15,47 MiB y selección 1,21 MiB. El inventario de comentarios incluye texto crudo y limpio, metadatos, roles y señales; luego los payloads vuelven a embebir unidades y comentarios.

### 3.3 `.gitignore`, versionado y riesgo de pérdida

El `.gitignore` actual tiene reglas globales `*.json` y `*.csv`, pero no ignora `*.jsonl`, `*.parquet`, `*.pyc`, `__pycache__/`, `.pytest_cache/`, `.venv/` ni `experiments/` por política de directorio. También usa `Notebooks/.*`, que no coincide con `notebooks/` en sistemas sensibles a mayúsculas.

Consecuencias observadas:

- El manifest `data/bronze/runs/extraction_run_20260409T154335Z.json` está ignorado aunque los JSONL Bronze sí están registrados.
- Manifests JSON de RAG/ciclos están ignorados mientras varios JSONL detallados sí están versionados: se conserva el volumen pero puede perderse el contexto de la corrida.
- `experiments/` mezcla 119 archivos registrados (18,29 MiB), 1.259 no registrados visibles y 191 ignorados (423,21 MiB). Git no representa un bundle coherente.
- Nueve archivos de pruebas cíclicas/diarias, once scripts, nueve módulos de implementación y el documento de diseño cíclico no están registrados. Son trabajo valioso y no deben confundirse con basura.
- Hay dos `.pyc` registrados en el repositorio y otros cachés locales no ignorados.

Política recomendada de versionado:

- **En Git:** código, pruebas, contratos, configuración sin secretos, manifests pequeños de corridas oficiales/de referencia, índice de corridas, métricas/reportes resumidos, hashes, corpus golden anonimizado y pequeño.
- **Fuera de Git pero bajo almacenamiento versionado:** Bronze, Gold oficiales, corpus reales con identificadores/texto, sidecars completos, respuestas crudas de LLM/Serper y bundles oficiales. Git conserva URI lógica, checksum, tamaño, esquema y política de acceso.
- **No versionar:** copias de Gold dentro de cada corrida, snapshots por comentario de desarrollo, inventarios reconstruibles, payloads intermedios, cachés, debug y corridas parciales.

“Canónico” no debe equivaler a “registrado como blob en Git”; significa que hay una fuente de verdad, identidad, hash, custodia y regla de mutabilidad claras.

### 3.4 Convenciones de identidad y manifests

Existen varias identidades útiles, pero no están unificadas:

- `run_YYYYMMDDTHHMMSSZ` en el replay local;
- `sim_<hash>` para simulación cíclica;
- `cyc_<hash>` por ciclo;
- `evt_<hash>` y `daily_event_id` para eventos;
- `ragg1_*`, `ragg2h_*`, `drun_*`, `dragconsumer_*`, `dragselect_*` en RAG.

Las fórmulas deterministas de ciclos/eventos y los `artifact_version` de RAG son fortalezas. Las carencias transversales son: no hay índice central, `run_mode`, `trace_level`, estado terminal uniforme, commit/dirty flag, hash de configuración resuelta, hash de todos los inputs, lista completa de artefactos con tamaño/hash, ni `referenced_by`.

Manifest mínimo propuesto para toda corrida:

```text
run_id, parent_run_id, pipeline_stage
run_mode, trace_level, status = in_progress|completed|failed|partial
started_at_utc, completed_at_utc
code_commit, code_dirty, environment_id
resolved_config_hash y configuración sin secretos
inputs[]  = logical_id, uri, sha256, schema_version, rows
outputs[] = role, uri, sha256, bytes, rows, retention_class
metrics, warnings, errors
dependencies[], referenced_by[]
```

### 3.5 Política de retención propuesta

Se recomienda conservar `experiments/` como espacio de resultados, pero separar propósito y no copiar la fuente canónica dentro de cada corrida:

```text
experiments/
  development/<pipeline>/<run_id>/
  references/<decision_id>/<run_id>/
  official/<case_study_id>/<run_id>/
  debug/<pipeline>/<run_id>/
  index/runs.jsonl
```

`latest` debe ser una referencia lógica en el índice, no una copia mutable de archivos.

| `run_mode` | `trace_level` por defecto | Qué persiste | Retención propuesta |
|---|---|---|---|
| `development` | `minimal` | Manifest, configuración/hash, métricas, eventos resumidos, errores y lista de artefactos. | Manifests pequeños indefinidos; detalle de las últimas 3 corridas exitosas por `pipeline + dataset + profile`, máximo 14 días; último fallo máximo 7 días. |
| `reference` | `standard` | Lo anterior + serie de señales, event registry, QA, comparación y evidencia seleccionada que documenta una decisión. | Inmutable mientras la decisión siga vigente; archivar al ser sustituida, con `superseded_by`. |
| `official` | `full` | Trazabilidad completa, hashes, todos los comentarios asociados por referencia, sidecars, contexto RAG, prompts, evidencia externa, respuestas, reportes y entorno. | Inmutable; almacenamiento externo redundante. Sin borrado automático. |
| `debug` | `minimal` o `full` explícito | Solo lo necesario para reproducir el fallo. | Borrado al cerrar el incidente o TTL máximo de 7 días. |
| `cache` | No es una corrida | Clave por hash de contenido, productor y expiración. | TTL 14 días y límite de tamaño; nunca se usa como única copia de evidencia. |

Definición de niveles:

- `minimal`: no persiste filas por comentario, snapshots por comentario ni payloads completos si se pueden reconstruir.
- `standard`: persiste agregados y evidencia seleccionada; los comentarios completos se referencian por `comment_id` y hash de dataset.
- `full`: conserva el paquete integral y las respuestas externas, requerido para A10.

La política debe incluir un futuro `cleanup --dry-run` que, antes de proponer un borrado, compruebe: modo, estado, edad, `referenced_by`, existencia de copia canónica/hash, seguimiento en Git, cambios locales, clase `official`, manifest válido y dependencias aguas abajo. El comando real debe requerir una segunda aprobación y producir un reporte firmado de lo que se eliminaría. CSV/JSONL históricos pueden comprimirse; Parquet ya comprimido no gana necesariamente al envolverse en ZIP. Las salidas costosas de LLM/Serper deben archivarse, no tratarse como reproducibles.

### 3.6 Evaluación de la separación desarrollo/oficial

La separación es correcta y necesaria. El matiz es añadir una tercera clase, `reference`, para no forzar una decisión binaria. `run_20260602T180842Z` y el `media/log_3` seleccionado pueden documentar decisiones metodológicas sin convertirse en resultados oficiales. Esto permite limpiar la mayoría del detalle de desarrollo y, al mismo tiempo, conservar evidencia no regenerable o costosa.

## 4. Auditoría arquitectónica

### 4.1 Procesamiento y memoria

**Fortalezas existentes**

- Bronze/Silver/Gold separan fuente, preparación y uso analítico.
- Gold usa Parquet y `comment_id` es único en el dataset actual.
- La simulación cíclica define intervalos semiabiertos, UTC canónico y calendario de Bogotá; las verificaciones detectan fuga temporal.
- C-4 evita escribir una copia completa de Gold por ciclo: usa el inventario como índice y materializa por `comment_id` en memoria.
- El baseline diario opera sobre una serie pequeña; no necesita comentarios completos.
- Los sidecars RAG preservan cobertura completa y separan evidencia de alerta de contexto de validación.

**Problemas concretos**

1. `storage.write_jsonl` convierte primero el DataFrame completo con `to_dict(orient="records")` (`storage.py:67-78`). Esto duplica memoria antes de escribir Bronze.
2. `clean_comments_dataframe` aplica una función Python por texto, convierte la serie de dicts a lista y concatena otro DataFrame (`cleaning.py:254-259`). Es aceptable para 60k–180k comentarios, pero no es incremental ni acotado.
3. `replay_events` copia, ordena y convierte todo el DataFrame a lista de diccionarios (`replay.py:58-80`).
4. Por cada comentario, monitoreo transforma todo el `deque` activo en un DataFrame y recalcula todos los agregados (`monitoring.py:65-86`). Con N comentarios y una ocupación media W, el costo es O(N×W), no O(N).
5. `run_playback` conserva todos los snapshots en una lista y solo escribe al final (`run_pipeline.py:219-275`). En la corrida local fueron 178.289 snapshots; una interrupción pierde el resultado y deja otras capas ya escritas.
6. C-3 carga dos CSV completos, filtra cada uno para cada ciclo y guarda todos los IDs nuevos/activos/salientes por ciclo (`cyclic_stateful_adapter.py:441-530`). El resultado repite 57.725 comentarios en 230.419 membresías.
7. C-4/C-5 cargan Gold completo y recorren `cycle_window_inventory` con un filtro completo por ciclo (`cyclic_daily_signals.py:565-615`, `cyclic_detection_connector.py:708-755`). Con 49 ciclos funciona; el patrón escala aproximadamente con ciclos × membresías.
8. Las capas RAG leen JSONL completos con `read_text().splitlines()`, cargan varios CSV en DataFrames, hacen merges/groupbys y vuelven a embebir comentarios/unidades en JSONL. En diario, 25.661 pares se representan en inventario, mapa, unidades y payloads.

No se encontró un loop explícito de comparación comentario-con-comentario O(N²). El riesgo dominante es reconstrucción repetida de ventanas y escaneo completo por ciclo, que puede acercarse a comportamiento cuadrático cuando crecen simultáneamente N, número de ciclos y tamaño de ventana.

### 4.2 I/O y formatos

| Uso | Formato actual | Diagnóstico | Dirección futura, sin migrar todavía |
|---|---|---|---|
| Bronze inmutable | JSONL | Adecuado para auditoría/append y lectura secuencial; la implementación escribe un lote completo. | Mantener JSONL por lote y escribir de forma streaming/atómica. |
| Silver/Gold | Parquet | Elección correcta para columnas, compresión y particiones. | Mantener; añadir identidad de lote y política de upsert/compaction. |
| Snapshots por comentario | CSV | Legible, pero voluminoso y tipado débil. Se escribe para análisis posterior. | En desarrollo, no persistir todos; para volúmenes altos, Parquet. Mantener exportes CSV pequeños para reportes. |
| Inventarios cíclicos | CSV | 99,11 MiB en tres archivos y lecturas completas repetidas. | Cuando se apruebe una migración, Parquet particionado por `cycle_id`/fecha o índices compactos por IDs. |
| Estado | JSON | Legible, pero `cycle_stateful_context.json` incluye 13,07 MiB de listas repetidas. | JSON pequeño para estado real; inventarios voluminosos fuera del estado. |
| Eventos/señales/reportes por registro | JSONL | Adecuado y append-friendly en concepto; hoy se reescribe el archivo completo. | Mantener JSONL para registros pequeños, con commit atómico. |
| Sidecars tabulares | CSV | Facilita auditoría, pero duplica texto y pierde tipos. | Parquet para inventarios/mapas grandes; JSONL para paquetes anidados; CSV solo resumen. |
| Config/manifests | JSON | Adecuado. | Mantener y dejar de ignorarlos globalmente. |

Hay persistencias necesarias entre fases —por reproducibilidad y ejecución independiente—, pero otras son copias de conveniencia. Durante una misma corrida, Gold no necesita copiarse bajo el `run_id`; debe referenciarse por hash. Las vistas activas de C-4 ya muestran el patrón correcto: IDs persistentes, filas materializadas en memoria. La misma idea puede extenderse a sidecars y señales cuando se apruebe el cambio.

### 4.3 Incrementalidad

El diseño actual **simula disponibilidad temporal**, pero no procesa únicamente datos nuevos de una fuente viva:

- Extracción consulta un rango y acumula todos los videos/comentarios en listas. No hay watermark, `observed_at_utc`, token de continuación durable ni registro de comentario actualizado.
- Storage escribe nuevos Bronze, pero agrega Parquet a los mismos directorios Silver sin borrar, hacer merge ni deduplicar contra lotes previos. Repetir un lote puede duplicar filas físicas.
- Gold se recalcula completo desde Silver.
- C-0/C-1 vuelve a leer y ordenar todo Gold para construir los 49 ciclos.
- C-3/C-5 reconstruyen todas las ventanas y señales desde archivos previos.
- El detector Xiao conserva estado entre ciclos solo dentro del proceso. `cycle_detector_state.json` declara `detector_internal_state_not_serialized`; no contiene buffer, EMAs, próximo tick, trigger activo ni `lock_until`.
- G-1 agrega o reemplaza resultados por evento y G-2 jerárquico divide por lotes/eventos, lo que ofrece reanudación manual parcial. No existe un checkpoint transversal ni una caché por hash de input/prompt.

Para A9, la unidad incremental mínima debe ser un lote de observaciones con `ingested_at_utc`, identidad de extracción y upsert por `comment_id`/`video_id + observed_at_utc`; el estado de señales debe guardar estadísticas suficientes de la ventana, no todas las filas históricas; el decisor debe serializar estado y event registry de forma atómica.

### 4.4 Estado y fuente de verdad

| Estado actual | Papel | Solapamiento/riesgo |
|---|---|---|
| `online_simulation_manifest.json` | Define corrida, corpus y ciclos. | No tiene hash del Gold ni commit de código. |
| `cycle_state.json` | Resumen C-0/C-1 y luego estado mutado por C-2. | Un archivo tiene dos propietarios; repetir C-2 agrega historia duplicada. |
| `cycle_stateful_context.json` | IDs vistos, activos, salientes y stubs futuros. | Mezcla checkpoint, inventario derivado y diseño futuro; 13 MiB. |
| `cycle_detector_state.json` | Ciclos procesados y eventos emitidos. | No serializa el estado interno real del detector; no permite resume equivalente. |
| `cycle_event_registry.jsonl` / eventos diarios | Eventos emitidos. | Hay registries distintos por modo; falta autoridad común e idempotency key transversal. |
| Manifests de señales/baseline/RAG | Linaje y configuración por fase. | Bien delimitados localmente, pero sin índice padre-hijo global. |
| Sidecars/consumer/context selection | Estado de preparación RAG. | Son outputs derivados, no deberían actuar como checkpoint primario. |

Fuente de verdad recomendada por responsabilidad:

1. lote de ingesta + watermark;
2. tabla canónica/upsert de entidades;
3. checkpoint de ventana y agregados;
4. estado serializable del detector/decisor;
5. event registry único e idempotente;
6. estado RAG subordinado a `event_id`;
7. manifest e índice solo para linaje, no para duplicar el estado.

### 4.5 Modularidad y acoplamiento

- La separación original `storage` / `cleaning` / `replay` / `monitoring` / `detectors` es clara.
- La arquitectura posterior creció por módulos independientes, pero varios son muy grandes: G-2 jerárquico 2.430 líneas, G-2 1.653, sidecars diarios 1.298, sidecars retrospectivos 1.216 y conector cíclico 1.159. En ellos conviven configuración, validación, I/O, transformación, prompts, llamadas y reporting.
- Un análisis AST encontró copias exactas de `_utc_now_iso` y `_normalize_path` en 10 módulos, `_short_hash` en 8, `_bool_series` en 6, merge de configuración en 6 y múltiples lectores/escritores JSON/JSONL. Esto aumenta la probabilidad de contratos divergentes y escrituras no atómicas.
- La familia retrospectiva y la diaria tienen sidecars, consumers y selección paralelos. Sus conceptos son equivalentes, pero sus esquemas y nombres no comparten una abstracción contractual.
- `run_local_csv_retrospective.py` tiene 729 líneas y ejecuta normalización, limpieza, replay, reconstrucción de triggers, reportes y manifests: un script experimental asumió responsabilidades de orquestador.
- `audit_comment_stream.py` tiene 1.057 líneas y `audit_gold_rag_thresholds.py` 440; son herramientas útiles, pero contienen lógica analítica que no está cubierta por pruebas.
- Los defaults de nueve módulos apuntan a `experiments/xiao/media/log_3/cyclic_ingestion_simulation`; README y documentos apuntan a `media/log_3`. Los resultados históricos forman parte accidental de la configuración del sistema.

No se recomienda una gran refactorización previa a A6/A7. Primero deben congelarse contratos y pruebas; luego extraer utilidades/I/O y componentes puros en cambios pequeños con equivalencia demostrada.

### 4.6 Robustez

**Positivo:** adquisición tiene timeout, backoff, retries y registro de cuota/errores; los contratos cíclicos rechazan flags externos; los joins validan unicidad, cobertura y fuga temporal; RAG verifica IDs citados y tiene retries/límites por lote.

**Brechas:**

- Casi todos los writers usan `write_text`, `to_csv` o `to_parquet` directamente. No hay `temp + fsync + rename`, checksum posterior ni marcador `COMPLETED`.
- C-0 escribe manifest y estado antes de los CSV grandes (`cyclic_ingestion.py:696-712`); C-4 smoke escribe manifest antes de seis outputs (`cyclic_detection_connector.py:896-902`). Un fallo puede dejar un manifest aparentemente válido con bundle incompleto.
- La corrida parcial de 331,66 MiB sin manifest demuestra que los residuos de fallo no se aíslan ni limpian automáticamente.
- Reruns usan rutas fijas y pueden sobrescribir agregados. C-2 muta `cycle_state.json` y agrega historia sin idempotency key.
- Silver puede acumular particiones duplicadas al repetir storage.
- La detección retrospectiva solo devuelve la ruta de snapshots; el detector queda en memoria y el pipeline base no emite un event registry formal. Los scripts posteriores reconstruyen evidencia desde stdout/logs.
- No hay política uniforme para `in_progress`, `completed`, `failed`, `partial`, reanudación o rollback.

### 4.7 Testing y reproducibilidad

Se ejecutó `python -m unittest discover` con escritura de bytecode desactivada: **43 pruebas pasaron en 0,306 s**. Cubren principalmente contratos cíclicos, fuga temporal, baseline, sidecars/consumer/selección diarios y algunos invariantes de G-2 jerárquico.

Brechas:

- 42 de las 43 pruebas no están registradas en Git; por tanto, el estado reproducible del repositorio no contiene la cobertura observada.
- No hay pruebas directas para API/extracción, escritura idempotente de Silver, limpieza completa, replay, monitoreo por ventanas, Xiao retrospectivo, RAG evidence/sidecars retrospectivos, G-1/G-2 globales, PoC ni verificador.
- No hay prueba de reanudación tras fallo, escritura atómica, rerun idempotente, lote incremental o equivalencia retrospectivo-cíclico.
- No hay CI ni `pyproject.toml`/configuración central de pruebas.
- `.python-version` fija 3.12.13, pero `.venv/bin/python` es 3.14.3.
- `requirements.txt` contiene más de cien dependencias y mezcla Jupyter, NLP, RAG y runtime. En el código de paquete/scripts/tests solo se observaron siete raíces de terceros; los notebooks explican parte del resto. Conviene separar dependencias más adelante, no ahora.

## 5. Código muerto y deuda experimental

La clasificación se basa en referencias estáticas, imports, documentación y manifests. El uso externo al repositorio no puede descartarse; por eso solo dos funciones pequeñas se califican como eliminación segura y aun ellas requieren una prueba antes de borrarse.

| Candidato | Evidencia | Clasificación | Recomendación |
|---|---|---|---|
| `cleaning.top_emoji_tokens` | Definida en `cleaning.py:281`; cero referencias en Python del repositorio. | `seguro_para_eliminar` | Probar import público y retirar en saneamiento posterior. |
| `run_local_csv_retrospective.unix_seconds` | Definida en `scripts/run_local_csv_retrospective.py:98`; cero usos. | `seguro_para_eliminar` | Retirar junto con prueba del script, no durante esta auditoría. |
| Wrappers públicos `write_*_artifacts`, `run_rag_g1_validation`, `run_rag_g2_validation`, `run_rag_g2_hierarchical` | Algunos no se llaman internamente, pero están en `__all__` y pueden ser API externa. | `mantener_por_compatibilidad` | No confundir “sin referencia interna” con código muerto. Deprecar solo con búsqueda de consumidores externos. |
| `data_extraction.py` de raíz | Wrapper de 6 líneas hacia el paquete. | `mantener_por_compatibilidad` | Mantener como entrada histórica hasta documentar una CLI única. |
| `youtube_pipeline/stream_playback.py` | Fachada documentada; importada por `__init__` y un script. | `mantener_por_compatibilidad` | No eliminar. |
| `notebooks/DataExtraction.ipynb`, `DataCleaning.ipynb` | Repiten lógica hoy presente en módulos y usan CSV legacy. | `probablemente_obsoleto` | Archivar como historia, no usar como referencia ejecutable. |
| `CommentClassificationGPT.ipynb`, `VideoClassification.ipynb`, `VideosSummary.ipynb` | Código de 2025, paths de ejemplo, servicios externos y sin integración al pipeline. | `probablemente_obsoleto` | Archivar fuera del flujo; revisar si alguna decisión metodológica debe documentarse. |
| `CommentClassificationBert.ipynb`, `CommentClassificationVader.ipynb` | Experimentos de sentimiento, no polarización formal. | `mantener_como_referencia` | Conservar como antecedentes de representación, sin promoverlos a A7. |
| `TF-IDF.ipynb` | 1,95 MiB, contiene simulación Streamz y términos por ventana; antecedente potencial de señal semántica. | `mantener_como_referencia` | Limpiar outputs solo después de exportar conclusiones; no usar como arquitectura paralela. |
| `CommentGraphs.ipynb`, `DataAnonymization.ipynb` | Exploración de redes y privacidad; no integradas. | `requiere_revision_manual` | Decidir si apoyan estado del arte/metodología o se archivan. |
| `rag_poc.py` y `rag_validation.py` | Continúan documentados y tienen scripts, pero fueron superados funcionalmente por sidecars/consumer/G-1/G-2. | `mantener_como_referencia` | Congelar como legacy; no extender sin decidir una única familia RAG. |
| `rag_evidence.py` vs. `rag_sidecars.py` y equivalentes diarios | Contratos superpuestos de evento, inventario, contexto y manifest. Todos tienen consumidores. | `requiere_revision_manual` | Definir contrato común antes de retirar una familia. |
| `rag_generation_g2.py` | Variante global anterior, pero G-2 jerárquico importa utilidades de G-1/G-2. | `mantener_por_compatibilidad` | No eliminar hasta desacoplar imports y conservar baseline comparativo. |
| `cycle_xiao_inputs.jsonl` y `_build_xiao_input` | El diseño cíclico lo declara “nota histórica/backlog”; la rama vigente usa `daily_frequency_baseline`. | `probablemente_obsoleto` | Mantener por ahora como evidencia de decisión; retirar solo tras aprobar que XIAO diario no se retomará. |
| Carpetas G-2 `primary`, `evt_*`, `batch`, `batch_auto_lot1` | Mismos eventos reaparecen en varias corridas; algunos lotes quedan pendientes. | `requiere_revision_manual` | Seleccionar una ejecución por decisión/evento; archivar crudos costosos y retirar reintentos sustituidos. |
| `run_20260602T180515Z` | Parcial, sin manifest, solo datos copiados y stdout incompleto. | `probablemente_obsoleto` | Primer candidato de limpieza tras búsqueda final de referencias. |
| `alta/log_1` | Gold duplicado, pero snapshots tienen 57.956 filas frente a 57.725 canónicas. | `requiere_revision_manual` | Explicar las 231 filas antes de borrar. |
| `baja/log_2` y `run_20260602T180213Z` | Resultados sustituidos; snapshots duplicados o cero triggers. | `probablemente_obsoleto` | Conservar resumen/manifest si documentan calibración; retirar detalle. |
| Campos legacy `*_unix_ms` con segundos | Documentados como compatibilidad; nombre semánticamente incorrecto. | `mantener_por_compatibilidad` | No cambiar todavía; planear migración explícita después de A6/A7 contracts. |

No se encontró código comentado sustantivo que constituya otra implementación completa. Sí hay deuda documental: `regression_verification.md` afirma un estado anterior sin pruebas formales; el documento académico consolidado contiene referencias editoriales pendientes como `Anexo ??` y la cita MEC `[?]`. Son P2 de documentación, no bloqueos de la arquitectura inmediata.

## 6. Estrategia experimental recomendada

### 6.1 Veredicto

Se recomienda un **harness experimental contractual con golden dataset mixto**, no un POC independiente. “Sandbox” puede describir el espacio de ejecución; el componente estable debe ser el harness. Un shadow pipeline solo será útil más adelante, cuando exista una fuente incremental real. Los feature flags son complementarios, no sustitutos del harness.

```text
corpus golden versionado
  -> adaptador de entrada del harness
  -> mismos componentes/contratos canónicos
       -> señal candidata
       -> distribución/polarización candidata
       -> decisor candidato
  -> assertions + comparación contra baseline
  -> reporte pequeño en directorio temporal
  -> promoción explícita a reference si pasa
```

La regla esencial para no mantener dos arquitecturas es que el harness no copie algoritmos: importa funciones puras, factories y contratos del paquete. Solo reemplaza fuente, reloj, sink y configuración. Una señal nueva debe implementar el mismo contrato que usará el pipeline; no se reescribe al promoverla.

### 6.2 Corpus recomendado

**Tipo:** mixto.

- Componente real, anonimizado y estratificado: conserva ruido lingüístico, emojis, replies, múltiples videos/autores y distribución temporal real.
- Componente sintético: controla exactamente picos, cambios de opinión, duplicados, llegadas tardías, ventanas vacías y casos límite.

**Tamaño inicial:** 6–10 videos, 2.000–5.000 comentarios, 14–21 días y 2–4 hilos densos. Debe caber en un Parquet pequeño y ejecutar todo el harness local en segundos, con menos de ~20 MiB de artefactos temporales. El tamaño se valida por tiempo y memoria, no como muestra representativa para conclusiones académicas.

**Escenarios mínimos:**

1. periodo estable sin evento;
2. pico de actividad sin cambio de opinión;
3. cambio de distribución de opinión con volumen moderado;
4. actividad y polarización simultáneas;
5. consenso abrupto, si MEC lo modela como caso relevante;
6. baja cobertura de opinión que debe producir `insufficient_support`;
7. duplicados, reply huérfano y timestamp inválido;
8. comentario tardío con `event_time` anterior pero `ingested_at` posterior;
9. límite exacto de ventana semiabierta;
10. más de un video y un hilo en el mismo ciclo.

**Invariantes esperadas:** mismos hashes y orden con la misma semilla/configuración; cero fuga temporal; `comment_id` único tras contrato; ninguna señal ausente interpretada como cero; valores de medidas dentro de su rango declarado; soporte y distribución suman lo esperado; triggers/no-triggers preanotados; reejecución idempotente; equivalencia entre batch y alimentación incremental; artefactos solo en directorio temporal salvo promoción.

### 6.3 Puertas de promoción

1. prueba unitaria de la señal/medida;
2. prueba del contrato y esquema;
3. regresión determinista sobre golden dataset;
4. comparación contra baseline y explicación de diferencias;
5. smoke test sobre muestra real mayor;
6. integración al pipeline tras aprobación metodológica.

El harness debe producir solo `manifest`, métricas, assertions y un diff. La evidencia detallada se activa con `trace_level=full` de forma explícita. Así se evita contaminar `experiments/` y se hace comprensible cada cambio.

## 7. Preparación para A6 — señales de actividad

### 7.1 Infraestructura ya disponible

- `monitoring.py` acepta un `ActivityHook`, y el contrato actual devuelve `volume`, `unique_authors` y `unique_videos` por ventana.
- `cyclic_daily_signals.py` ya calcula por ciclo: comentarios activos, nuevos y salientes; videos activos; autores únicos; replies y ratio; densidades de emoji/exclamación/pregunta; media de mayúsculas; sentimiento opcional; delta y cambio porcentual del conteo activo.
- `daily_frequency_baseline.py` consume una serie de una observación por ciclo, calcula baseline y aplica soporte, delta, porcentaje, warmup y cooldown.
- C-3 conserva IDs y límites temporales; C-5 valida cobertura, unicidad y fuga temporal.
- Gold contiene `likes` por comentario, pero como valor observado al momento de la extracción.
- Silver videos contiene `views`, `likes` y `comments` para 112 videos, con una sola fila por video.

### 7.2 Viabilidad por señal

| Señal | Disponible ahora | ¿Requiere snapshots repetidos? | Viabilidad en línea | Observación |
|---|---|---|---|---|
| Frecuencia de comentarios nuevos por ciclo | Sí | No | Alta | Es la señal más limpia y ya alimenta el baseline diario. Debe expresarse con unidad (`comentarios/día`, etc.). |
| Conteo activo en ventana y delta/% | Sí | No | Alta | Ya existe; el delta de una ventana móvil no equivale exactamente a velocidad de llegada y debe nombrarse con precisión. |
| Comentarios/minuto o por hora | Sí, desde `event_time_utc` | No | Alta | Requiere fijar granularidad y manejo de ciclos vacíos. |
| Velocidad/aceleración de llegada de comentarios | Derivable de la serie | No | Alta | Calcular sobre bins/ciclos causales; evitar diferencias sobre ventanas solapadas sin documentarlas. |
| Autores/videos únicos, replies y ratio | Sí | No | Alta | Señales de diversidad/estructura, no sustitutos del volumen. |
| Likes absolutos de comentarios | Sí | No para el valor absoluto | Baja en replay causal | El valor fue observado después de publicados muchos comentarios. Usarlo en una fecha histórica introduce look-ahead. |
| Tasa de likes de comentarios | No | Sí | Media | Necesita observaciones del mismo `comment_id` con `observed_at_utc`. |
| Views/likes/conteo de comentarios de video absolutos | Silver, una observación | No para contexto estático | Baja como señal temporal | Útiles como metadato de contexto, no como serie. No están en Gold. |
| Tasa, velocidad y aceleración de views/reacciones del video | No | Sí | Media/alta tras adquisición | Requiere tabla de snapshots por `video_id + observed_at_utc`. |
| Densidades emoji/puntuación/caps | Sí | No | Alta | Son señales discursivas, no polarización formal. |
| Novedad temática/TF-IDF | Solo notebook histórico | No necesariamente | Media | Requiere contrato de vocabulario/modelo y estado incremental; no está en producción. |

### 7.3 Bloqueantes antes de ampliar A6

1. contrato común de `signal_observation` con nombre, unidad, valor, ventana, soporte, baseline, calidad y versión;
2. separar señal calculada sobre comentarios nuevos de señal calculada sobre ventana activa;
3. decidir el modelo de snapshots de métricas mutables y añadir `observed_at_utc` antes de usar views/likes como tasa;
4. estado incremental de agregados para no reconstruir todas las ventanas;
5. golden dataset y expectativas de picos/no picos;
6. política de missingness: no confundir señal no disponible con valor 0.

Después de estos puntos, pueden añadirse primero señales 100 % derivables del Gold actual —frecuencia normalizada, velocidad/aceleración de llegada, diversidad de autores/videos y replies—. Las señales de plataforma deben esperar cambios de adquisición.

## 8. Preparación para A7 — polarización

### 8.1 Estado actual

No existe implementación local de Esteban–Ray, EMD o MEC, ni se encontró un paquete/dependencia del proyecto que las implemente. `scipy` está instalado, pero eso no define el modelo de opinión, la distribución, el baseline ni los parámetros metodológicos.

`default_polarization_metrics` devuelve media/desviación de `sentiment_score` si existe; de lo contrario, medias de emoji, exclamación y pregunta (`monitoring.py:23-40`). El Gold canónico actual no contiene `sentiment_score`. El corpus `caso-uribe` sí contiene sentimiento/clasificación, y el script retrospectivo lo transforma a `-1, 0, 1`, pero eso es una normalización experimental, no una representación de postura validada.

Conclusión: renombrar conceptualmente estos campos como **proxies discursivos/sentimiento** en la documentación futura. No deben usarse para declarar A7 cumplida.

### 8.2 Cadena faltante

```text
comentario canónico
  -> representación de opinión versionada
  -> observaciones válidas/no válidas con confianza
  -> distribución por ventana y población
  -> ER / EMD / MEC con parámetros explícitos
  -> serie temporal + calidad + baseline
  -> entrada del decisor
```

**Ubicación recomendada:** una fase derivada entre Gold limpio y agregación de señales, mediante un sidecar versionado por `comment_id + opinion_model_version`. No conviene sobrescribir el Gold fuente ni esconder la representación dentro de `monitoring.default_polarization_metrics`. Así se puede comparar VADER/BERT/clasificador de postura u otras representaciones sin duplicar comentarios.

**Contrato de representación de opinión:**

```text
comment_id, opinion_model_id, opinion_model_version
target/topic, scale_type = ordinal|continuous|categorical
score o probabilities, label opcional
language, confidence, status, missing_reason
inferred_at_utc, source_text_hash
```

**Contrato de distribución por ventana:**

```text
run_id, cycle_id, window_start/end, data_cutoff
population_scope, topic, opinion_model_version
bin_edges/categories, counts, probabilities
support_total, support_valid, missing_count
weighting_policy, distribution_hash, quality_status
```

**Contrato de medida:**

```text
metric_name = ER|EMD|MEC
metric_version, value, valid_range
distribution_ref/hash, baseline_distribution_ref si aplica
parameters (alpha, bins, ground distance, consensus target, etc.)
support, uncertainty/quality, missing_reason
```

### 8.3 Decisiones metodológicas previas

- ¿La opinión es sentimiento, postura respecto a una entidad/tema, toxicidad u otra escala? El documento académico distingue sentimiento de polarización; por ello, sentimiento no basta.
- ¿La escala es ordinal/continua o categorías? Esto condiciona las tres medidas.
- ¿La unidad es todos los comentarios de la ventana, por video, por tópico o por hilo?
- ¿Cómo se ponderan autores, likes, duplicados y usuarios muy activos?
- ¿Cuál es el soporte mínimo y cómo se reporta incertidumbre?
- Para EMD, ¿qué dos distribuciones se comparan y cuál es la distancia base: ventana vs baseline, ventana consecutiva u otra referencia?
- ¿Qué parametrización de ER y definición operativa de MEC se adoptan y citan?
- ¿Cómo se valida la representación de opinión en español colombiano y en texto ruidoso?

Reutilizable: `comment_id`, `event_time_utc`, ventanas C-3/C-5, hooks de métricas, contratos de calidad, hashes, event evidence y harness. No reutilizable como medida formal: las densidades de emoji/puntuación ni la media de sentimiento. Los notebooks de sentimiento pueden servir para comparar representaciones, no como solución final.

## 9. Preparación para A8 — decisor

No se recomienda rediseñar aún el decisor. El contrato actual `TriggerDetector` solo recibe eventos crudos mediante `on_event` y expone `completed_triggers`; Xiao calcula actividad internamente. Para combinar actividad y polarización sin acoplar el decisor a comentarios o modelos, la futura entrada debe ser una observación normalizada por ciclo/ventana:

```text
decision_input
  run_id, cycle_id, observation_time_utc
  window_start_utc, window_end_utc, data_cutoff_utc
  activity_signals[]
    name, value, unit, baseline, anomaly_score, support, quality, version
  polarization_signals[]
    metric, value, distribution_ref, opinion_model_version,
    parameters, support, quality
  availability
    available, unavailable_reason, stale
  lineage
    dataset_hash, signal_artifact_refs, config_hash
```

El futuro output debería distinguir `alarm`, `event_candidate`, `validated_event` y `false_alarm`; incluir regla/versión, severidad, señales que justificaron la decisión, cooldown/persistencia, `event_id` idempotente y referencias a evidencia. Los comentarios completos no deben atravesar el contrato del decisor: se resuelven por IDs al preparar evidencia.

Este contrato permite reglas futuras de tipo actividad **y** polarización, persistencia durante K ventanas, degradación cuando una señal falta y comparación de decisores. Requiere cambio de contrato; debe aprobarse después de fijar A7 y antes de integrar ambos tipos de señales.

## 10. Preparación para A9 — procesamiento en línea

### 10.1 Elementos reutilizables

- semántica UTC/Bogotá y ventanas semiabiertas;
- IDs deterministas de corrida, ciclo y evento;
- separación entre comentarios nuevos, activos y salientes;
- validación de no-future-leak y unicidad;
- join por `comment_id` contra la fuente canónica sin copiar Gold por ciclo;
- una observación agregada por ciclo;
- baseline diario y event registry tabular;
- guardas que impiden RAG/LLM/Serper en dry-runs;
- sidecars que separan evidencia causal de contexto de validación;
- 42 pruebas locales cíclicas/diarias que deben preservarse.

### 10.2 Elementos todavía experimentales

- los 49 ciclos se construyen de una vez desde un Gold histórico;
- frecuencia fija diaria y ventana fija de tres días;
- C-2 es solo dry-run y C-3 prepara estado futuro;
- C-4 real solo se probó sobre dos ciclos;
- el adaptador XIAO diario está declarado como backlog;
- los defaults dependen de una corrida histórica concreta;
- no hay scheduler, cola, servicio de ingesta ni watermark durable;
- no existe política real de comentarios tardíos porque falta tiempo de ingesta;
- no se serializa el estado interno del detector;
- las escrituras y el event registry no son transaccionales;
- el RAG diario llega hasta selección de contexto, sin validación generativa.

### 10.3 Qué falta para un flujo operativo

1. contrato de observación con `event_time_utc` e `ingested_at_utc`;
2. ingesta/upsert idempotente y watermark por fuente;
3. storage incremental sin duplicar particiones;
4. estado acotado de ventanas/señales y checkpoint serializable;
5. detector/decisor reanudable con cooldown y eventos emitidos;
6. commit atómico de `state + outputs + manifest`;
7. retries y dead-letter/registro de lote fallido;
8. control de backpressure, memoria y límite de artefactos;
9. pruebas batch-vs-incremental y restart-vs-continuous;
10. observabilidad operativa de latencia, atraso, throughput y estado.

### 10.4 Principales problemas de escala

El mayor problema observado por volumen no está en el baseline de 49 filas, sino antes y después: inventarios CSV de membresías, JSON con listas completas de IDs, filtros completos por ciclo, payloads RAG con comentarios repetidos y snapshots por comentario. La arquitectura futura debe persistir deltas y referencias, mantener en memoria solo el estado de ventana y materializar evidencia completa únicamente cuando se detecta/promueve un evento.

## 11. Hallazgos priorizados

En “Acción” se indica `F` si puede cambiar comportamiento funcional y `C` si puede alterar contratos.

| Prioridad | Hallazgo | Evidencia | Impacto | Acción | Esfuerzo |
|---|---|---|---|---|---|
| P0 | El estado técnico reciente no está preservado coherentemente. | `git status`: módulos/scripts/docs cíclicos y 9 tests sin seguimiento; `.gitignore:11-12` ignora JSON/CSV. | Riesgo de perder implementación, tests y manifests antes de cualquier limpieza. | Congelar inventario y decidir qué trabajo local se preserva; corregir política de ignore después de aprobación. F: no; C: no. | Pequeño |
| P0 | No existe autoridad de retención/dependencias; algunas corridas antiguas son inputs por defecto. | README y 9 módulos apuntan a `experiments/xiao/media/log_3`; no existe `runs.jsonl` ni `referenced_by`. | Un borrado aparentemente seguro puede romper comandos, docs o linaje RAG. | Crear índice read-only inicial y mapa de dependencias; no borrar hasta etiquetar `reference/official`. F: no; C: no. | Pequeño |
| P0 | A7 carece de representación de opinión y las métricas actuales están semánticamente mal ubicadas. | `monitoring.py:23-40`; Gold no tiene `sentiment_score`; búsqueda local sin ER/EMD/MEC. | Implementar fórmulas ahora produciría números sin significado metodológico y bloquearía A8. | Aprobar contratos de opinión, distribución y medida antes de código. F: sí futuro; C: sí. | Medio |
| P0 | El estado interno del detector no es serializable/reanudable. | `cyclic_detection_connector.py:814-835` declara `detector_internal_state_not_serialized`. | Tras fallo, EMA, buffer, tick, cooldown y trigger activo no pueden reconstruirse fielmente; bloquea A9 operativo. | Definir checkpoint y prueba restart-vs-continuous antes de ampliar el modo online. F: sí; C: sí. | Medio |
| P0 | No hay tiempo de observación para métricas mutables ni llegadas tardías. | Una fila por video en Silver; `cyclic_ingestion_simulation_design.md:263-267` reconoce que no se infieren late arrivals. | Views/likes rates y semántica online pueden usar información futura. | Aprobar contrato `observed_at_utc/ingested_at_utc` y snapshots de métricas antes de esas señales. F: sí; C: sí. | Grande |
| P1 | Corridas duplican casi 1 GiB de datos canónicos. | Tres árboles de 254,96 MiB con contenido idéntico y tres pares CSV de 76,70 MiB idénticos. | Ruido, costo de disco y dificultad para distinguir fuente/resultado. | Referenciar dataset por hash; después limpiar copias con `cleanup --dry-run`. F: no; C: rutas/manifests. | Medio |
| P1 | Escritura Silver no es idempotente. | `storage.py:82-103,131-140` escribe al mismo dataset particionado sin upsert/dedupe. | Repetir storage puede duplicar filas y contaminar Gold/señales. | Definir identidad de lote, staging y merge/replace atómico. F: sí; C: almacenamiento. | Medio |
| P1 | Bundles pueden quedar parcialmente escritos o sobrescritos. | C-0 y C-4 escriben manifest antes de outputs; corrida parcial sin manifest ocupa 331,66 MiB. | Estado inconsistente y reanudación insegura. | Estado `in_progress`, staging, rename atómico y validación de bundle antes de `completed`. F: no esperado; C: manifest. | Medio |
| P1 | Monitoreo retrospectivo reconstruye la ventana por comentario. | `monitoring.py:65-86`; `run_pipeline.py:219-275` acumula todos los snapshots. | CPU/memoria crecen con N×W; limita corpus y nuevas medidas. | Mantener agregados incrementales y muestrear/persistir snapshots por slide, no por comentario, con equivalencia contractual. F: posible; C: snapshots. | Grande |
| P1 | Simulación cíclica materializa demasiado estado derivado. | 230.419 membresías; 128,08 MiB CSV + 13,07 MiB JSON de IDs. | Escala mal y encarece cada señal nueva. | Separar checkpoint mínimo de inventario reproducible; indexar/particionar antes de A9. F: no esperado; C: artifacts. | Medio |
| P1 | No hay harness/golden dataset. | Los cambios se prueban sobre `media/log_3` o corpus de 178k comentarios. | Iteraciones lentas, artefactos masivos y difícil atribución causal. | Construir harness contractual mixto antes de A6/A7. F: no producción; C: prueba. | Medio |
| P1 | Cobertura de tests importante pero no reproducible y con huecos del core. | 43 pasan; 42 están en archivos no registrados; no hay tests de storage/replay/monitoring/incrementalidad. | Refactors y optimizaciones pueden alterar resultados sin detectarse. | Preservar tests actuales y añadir gates de contratos/idempotencia/restart. F: no; C: no. | Medio |
| P1 | Entorno no coincide y dependencias están mezcladas. | `.python-version` 3.12.13 vs `.venv` 3.14.3; `requirements.txt` amplio. | Resultados y serializaciones pueden variar; onboarding costoso. | Fijar entorno soportado y separar grupos después de preservar pruebas. F: posible; C: entorno. | Medio |
| P1 | Configuración y resultados históricos divergen. | Manifest raíz: cooldown 1/4 eventos; subcarpeta vigente: cooldown 0/5 eventos; docs declaran cooldown desactivado. | No queda claro cuál resultado es baseline vigente. | Elegir y etiquetar una corrida de referencia; no cambiar threshold en la limpieza. F: no; C: config de referencia. | Pequeño |
| P1 | El pipeline retrospectivo no produce un event registry formal. | `run_playback` retorna solo snapshots; triggers viven en detector/logs y scripts reconstruyen mapas. | Evidencia y decisión dependen de scripts experimentales. | Definir output opcional versionado del detector sin cambiar el algoritmo. F: aditivo; C: sí. | Medio |
| P1 | RAG duplica texto/contexto en varias capas. | Daily sidecars 36,83 MiB + consumer 15,47 MiB para 25.661 pares; 5/5 payloads exceden presupuesto. | I/O y memoria aumentan antes de cualquier llamada generativa. | Mantener inventario único y payloads por referencia; persistir detalle solo full. F: no esperado; C: RAG artifacts. | Medio |
| P1 | Datos crudos con autores/texto están versionados o dispersos sin política de acceso. | Bronze registrado; Gold/experimentos contienen `author_id`, `author_name`, texto. | Privacidad, tamaño del repositorio y exposición en informes públicos. | Política de datos: almacenamiento externo, hashes y golden anonimizado. F: no; C: custodia. | Medio |
| P2 | Utilidades exactas y responsabilidades están duplicadas. | `_utc_now_iso`/`_normalize_path` ×10; varios módulos >1.000 líneas. | Correcciones divergentes y mantenibilidad. | Extraer utilidades/I/O después de congelar contratos; cambios pequeños. F: no esperado; C: no. | Medio |
| P2 | Notebooks, PoC y familias RAG legacy siguen mezclados con arquitectura vigente. | 10 notebooks; `rag_poc`, `rag_validation`, sidecars y versiones diarias paralelas. | Navegación difícil y dos conceptos para la misma entidad. | Etiquetar `legacy/reference`, documentar sucesor y deprecar gradualmente. F: no inicial; C: posible. | Medio |
| P2 | Documentación y contrato temporal tienen deuda. | Docs base no incluyen ciclos; `*_unix_ms` contiene segundos; referencias académicas pendientes. | Confusión metodológica y de mantenimiento. | Actualizar después de decidir contratos, sin migrar datos todavía. F: no; C: documentación. | Pequeño |
| P3 | No hay compresión/índice consultable de archivos históricos. | RAG/CSV/JSONL de referencia permanecen expandidos. | Ocupación y búsqueda manual. | Comprimir bundles cerrados y generar catálogo; no comprimir Parquet por defecto. F: no; C: no. | Pequeño |

## 12. Plan de saneamiento

### S0 — Congelación e inventario verificable

- Preservar explícitamente código, tests y documentos locales actuales.
- Generar, tras aprobación, un inventario con ruta, tamaño, hash, estado Git, productor, consumidores y clasificación.
- Marcar `run_20260602T180842Z` y un `media/log_3` elegido como candidatos `reference`, no `official`.
- Criterio de salida: ningún archivo puede proponerse para borrado sin clase y dependencias.

### S1 — Política de artefactos sin cambios funcionales

- Aprobar `run_mode`, `trace_level`, manifest mínimo, índice y retención.
- Corregir `.gitignore` con reglas por directorio/rol y preservar manifests.
- Definir custodia de datos reales y privacidad.
- Criterio de salida: una corrida nueva puede clasificarse y localizarse sin inspección manual del árbol.

### S2 — Limpieza segura en dos pasos

- Ejecutar solo un reporte `cleanup --dry-run`.
- Revisar primero parcial `180515`, cachés, copias canónicas y snapshots duplicados.
- Archivar crudos RAG seleccionados y resúmenes de calibración antes de eliminar variantes.
- Criterio de salida: lista aprobada con recuperación/copia y ahorro estimado; el borrado sería una tarea posterior separada.

### S3 — Estabilización de ejecución

- Resolver idempotencia de Silver, staging/atomicidad, estado terminal y event registry.
- Preservar y ampliar pruebas de core, rerun y fallo.
- Alinear Python/entorno.
- Criterio de salida: rerun no duplica; fallo no publica bundle completo; restart reproduce la corrida continua en fixture.

### S4 — Harness y contratos de señales/opinión

- Crear golden dataset mixto y harness que reutilice componentes canónicos.
- Congelar `signal_observation`, representación de opinión, distribución y medida.
- Criterio de salida: ejecución rápida/determinista, sin artefactos persistentes por defecto, con expected outputs.

### S5 — Reanudación académica controlada

- A6: señales derivables primero; snapshots de plataforma después.
- A7: representación validada, luego ER/EMD/MEC.
- A8: decisor combinado tras estabilizar ambos contratos.
- A9: incrementalidad y checkpoint sobre el mismo harness antes de la corrida real.

## 13. Qué NO tocar todavía

- Fórmulas, thresholds o cooldowns de Xiao y baseline diario.
- Prompts, proveedores, estrategias, contratos o resultados G-1/G-2.
- Formatos históricos CSV/JSONL/Parquet hasta aprobar migración y compatibilidad.
- Campos legacy `event_time_unix_ms` / `published_at_unix_ms`.
- Bronze/Silver/Gold actuales, `data/caso-uribe/` o el repositorio anidado `.agents/...`.
- `media/log_3` completo, porque tiene consumidores hardcodeados y evidencia costosa.
- La discrepancia de `alta/log_1` mediante borrado; primero debe explicarse.
- Nuevas señales, ER/EMD/MEC o un decisor combinado antes de contratos y harness.
- Un servicio/scheduler online real antes de checkpoint, idempotencia y `ingested_at_utc`.
- Una refactorización masiva de RAG o de módulos de más de mil líneas; primero pruebas y fronteras.
- Casos de uso A10: ninguna corrida actual debe renombrarse como oficial retroactivamente.

## 14. Hoja de ruta recomendada

Máximo seis etapas, en este orden:

| Etapa | Objetivo | Entregable | Criterio de aceptación | Desbloquea |
|---|---|---|---|---|
| 1. Preservar y catalogar | Recuperar una verdad verificable del estado actual. | Inventario hash/dependencias + selección preliminar de corridas `reference`; código/tests locales preservados. | 100 % de artefactos >1 MiB y de manifests clasificados; cero rutas desconocidas para los bundles seleccionados. | Limpieza segura y trabajo reproducible. |
| 2. Política de corridas | Separar desarrollo, referencia y oficial. | Especificación de `run_mode`, `trace_level`, manifest, índice, retención y custodia. | Un ejemplo de cada modo muestra exactamente qué persiste; `cleanup --dry-run` tiene reglas aprobadas. | Reducción sostenida de artefactos. |
| 3. Estabilidad operacional mínima | Eliminar riesgos de rerun/fallo antes de ampliar funcionalidad. | Diseño y pruebas de idempotencia, escritura atómica, event registry y checkpoint real. | Dos reruns no duplican; fallo simulado no publica `completed`; restart equivale a continuo en fixture. | A9 incremental y refactors seguros. |
| 4. Harness contractual | Probar rápido con evidencia comprensible. | Golden dataset mixto, runner temporal y reporte de comparación. | Ejecución determinista en segundos, <20 MiB temporal, sin escribir `experiments/` por defecto. | A6 y A7 de bajo riesgo. |
| 5. Contratos académicos | Fijar semántica antes de algoritmos. | Contratos de señal, snapshot mutable, opinión, distribución, medida y entrada del decisor. | Cada campo tiene unidad, tiempo, soporte, calidad, versión y expectativa en el golden dataset. | Implementación de señales y polarización. |
| 6. Desarrollo y promoción | Implementar A6/A7, luego A8/A9, y preparar A10. | Componentes validados en harness, integración incremental y protocolo de corrida oficial full. | Gates unitarios/contrato/golden/smoke pasan; una corrida candidata puede promoverse sin copiar datos ni perder linaje. | Casos de uso oficiales y cierre académico. |

## 15. Decisiones que requieren aprobación

### 15.1 Seguras y reversibles

- Crear inventario/índice sin borrar nada.
- Etiquetar corridas como `development`, `reference`, `official` o `debug` en metadata nueva.
- Preservar manifests y excluir cachés en una política de Git más precisa.
- Diseñar `cleanup --dry-run` sin habilitar borrado.
- Añadir tests y golden dataset pequeño anonimizado.
- Marcar documentos/notebooks como `legacy` sin moverlos todavía.

### 15.2 Arquitectónicas

- Adoptar la taxonomía de directorios y `trace_level`.
- Elegir una fuente de verdad para ingestion checkpoint, signal state, detector state y event registry.
- Cambiar storage a staging/upsert y writers atómicos.
- Sustituir copias de datos por referencias/hashes.
- Unificar contratos retrospectivos y diarios de evidencia/RAG.
- Definir si el replay por comentario continúa siendo referencia o se reemplaza por agregación por slide.

### 15.3 Metodológicas

- Definición de opinión/postura y esquema de anotación/evaluación.
- Parametrizaciones y significado de ER, EMD y MEC.
- Granularidad/población de las distribuciones y soporte mínimo.
- Ventanas, baseline, velocidad/aceleración y ponderación por usuario/video/likes.
- Regla futura de combinación actividad + polarización y niveles de decisión.
- Selección del golden corpus y de los casos de uso A10.
- Qué corridas actuales merecen conservarse como evidencia de decisiones.

### 15.4 Potencialmente incompatibles

- Borrar o mover `media/log_3` antes de retirar defaults y referencias.
- Dejar de producir CSV legacy o retirar campos `*_unix_ms`.
- Migrar inventarios/sidecars CSV a Parquet.
- Cambiar el protocolo `TriggerDetector` o el esquema de eventos.
- Retirar `rag_poc`, G-2 global, wrappers o notebooks usados externamente.
- Cambiar IDs/fórmulas de `run_id`, `cycle_id` o `event_id`.
- Sacar datasets reales de Git o reescribir su historial; requiere plan de custodia y, si aplica, de privacidad.
- Ejecutar el borrado real tras el dry-run.

## 16. Veredicto final

1. **¿Debo continuar implementando A6/A7/A9 inmediatamente?** No de forma amplia sobre la arquitectura principal. A6 puede reanudarse pronto en un harness después de preservar el estado y fijar el contrato de señales. A7 y A9 tienen P0 metodológicos/operativos que deben cerrarse primero.
2. **¿Qué debo cerrar antes?** Preservación de código/tests/manifests; inventario y dependencias; política de corridas; opinión/distribución para A7; `ingested_at/observed_at`, estado serializable, idempotencia y atomicidad para A9.
3. **¿Conviene introducir un harness/POC?** Sí: un harness contractual con golden dataset mixto. No conviene otro POC con lógica copiada ni dos arquitecturas.
4. **¿Qué artefactos pueden probablemente eliminarse?** Después de revisión: la corrida parcial `180515`; copias `data/` y `local_csv_load/` dentro de corridas; snapshots byte-idénticos; `__pycache__`/`.DS_Store`; detalle de `180213`; variantes G-2 sustituidas y `baja/log_2`. `alta/log_1`, datos fuente, manifests ignorados, outputs externos costosos y `media/log_3` completo requieren revisión o archivo previo.
5. **¿Qué trazabilidad conviene durante desarrollo?** `minimal` por defecto: manifest, config/hash, inputs por referencia/hash, métricas, eventos resumidos y errores. `standard` solo para experimentos que justifican decisiones; `full` para casos oficiales o debugging explícito y temporal.
6. **¿Cuál debe ser la siguiente tarea concreta?** Ejecutar la etapa 1 de la hoja de ruta: producir y revisar un inventario hash/dependencias que preserve el trabajo local y marque las dos corridas candidatas a `reference`, sin mover ni borrar archivos. Esa tarea convierte la limpieza posterior en una decisión segura y desbloquea el harness.
