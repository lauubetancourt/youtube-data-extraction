# Guía de estudio verificable del pipeline actual

Esta guía responde una pregunta concreta: ¿qué ocurre hoy desde que entra un dato hasta que un candidato llega a validación, qué componente hace cada transformación y cómo puedo comprobarlo? La fuente de verdad es, en este orden, el código productivo, los tests vigentes y la documentación normativa actual.

La guía no propone una arquitectura nueva. Enseña a leer la que existe. Cuando dos contratos están implementados pero no unidos por el runtime, la separación se indica de forma explícita.

## 1. Qué hace realmente el proyecto

El proyecto toma datos de YouTube, conserva su identidad, normaliza el tiempo y el texto, y reproduce los comentarios en orden temporal. Luego convierte comentarios individuales en una señal numérica. Un detector decide si esa señal presenta un cambio según sus parámetros. Si la decisión produce un candidato activo, otra capa reúne evidencia, prepara contexto para RAG y, en la ruta retrospectiva, ejecuta validaciones internas y externas.

```text
datos de YouTube
        ↓
preparación y conservación de identidad
        ↓
simulación temporal
        ↓
medición de actividad
        ↓
detección
        ↓
candidato operativo
        ↓
evidencia completa
        ↓
preparación y selección RAG
        ↓
validación
```

La distinción más importante aparece antes de abrir una clase:

```text
detección estadística ≠ evento real confirmado
```

Una detección dice que una regla observó un cambio en una señal. La validación posterior examina si la evidencia permite interpretar ese cambio como un evento. Ninguna de las dos rutas debe convertir `triggered=true` en una afirmación automática sobre el mundo.

## 2. Dos rutas actuales

El repositorio tiene dos recorridos importantes. Comparten datos preparados y principios de trazabilidad, pero no son una sola implementación con distinta frecuencia.

### Ruta retrospectiva

```text
dataset preparado
→ replay cronológico
→ señal de 120 s, observada cada 30 s
→ XIAO
→ trigger histórico completado
→ evidencia retrospectiva
→ RAG retrospectivo
→ G-1 y G-2
```

Esta ruta reproduce comentarios históricos uno por uno. XIAO genera decisiones neutrales en su interior, pero el handoff operativo que alimenta la evidencia sigue siendo `completed_triggers`.

### Ruta diaria

```text
dataset preparado
→ simulación por ciclos diarios
→ señales diarias
→ baseline de frecuencia
→ evento diario
→ evidencia diaria
→ RAG diario
→ selección de contexto
```

Esta ruta clasifica comentarios como nuevos, activos o salidos en cada ciclo. El evento nace de un baseline diario, no de XIAO. Actualmente termina después de seleccionar y documentar el contexto. No ejecuta G-1 ni G-2.

### Tres estados que conviene reconocer

| Estado | Significado en esta guía | Ejemplo actual |
|---|---|---|
| `CONCEPTUAL_AND_ACTIVE` | El contrato y su uso están implementados en una ruta ejecutable. | `ActivityObservation → XIAO → DetectionResult` |
| `CONCEPTUAL_BUT_NOT_GENERAL_RUNTIME` | El contrato existe y está probado, pero no es el handoff general. | `DetectionResult → EventCandidate` |
| `LEGACY_ACTIVE` | Una forma histórica sigue siendo el enlace operativo vigente. | `completed_triggers → evidencia retrospectiva` |

## 3. Cómo estudiar esta guía

Estudia un bloque por vez. No abras todos los módulos a la vez. Para cada bloque:

1. Entiende el problema que resuelve.
2. Sigue el ejemplo pequeño.
3. Abre entre uno y tres archivos principales.
4. Ejecuta los tests indicados.
5. Responde las preguntas sin mirar la explicación.

Usa esta checklist en cada sesión:

- [ ] Comprendo el propósito.
- [ ] Comprendo la entrada.
- [ ] Comprendo la salida.
- [ ] Sé qué archivo lo implementa.
- [ ] Verifiqué el test.
- [ ] Puedo explicarlo sin mirar.

Los comandos de esta guía se ejecutan desde la raíz del repositorio. Los tests usan el intérprete del entorno virtual:

```bash
.venv/bin/python -m unittest tests.test_activity_signal_contracts
```

Si un test pasa, demuestra el contrato concreto que sus aserciones cubren. No demuestra que los umbrales estén calibrados, que los datos sean representativos ni que una API externa esté disponible.

## 4. Configuración de una ejecución

### El problema

¿Cómo sabe el pipeline qué dataset usar, qué detector configurar y dónde escribir resultados? Una ejecución necesita una identidad y una configuración efectiva que no dependa de recordar argumentos dispersos.

La composición tipada se llama `RunConfig`. Agrupa siete responsabilidades:

| Sección | Pregunta que responde |
|---|---|
| `identity` | ¿Cuál es el `run_id` de esta ejecución? |
| `data` | ¿Qué entrada se leerá y cómo se interpreta? |
| `simulation` | ¿Qué rango y reglas temporales usa la simulación? |
| `signals` | ¿Qué series numéricas se producirán? |
| `detection` | ¿Qué detector y parámetros se preparan o ejecutan? |
| `rag` | ¿Qué etapas RAG están configuradas? |
| `artifacts` | ¿Dónde se escriben resultados y qué nivel de traza se admite? |

El perfil JSON no es todavía la última palabra. El cargador aplica valores por defecto, incorpora el perfil y los overrides explícitos, valida campos desconocidos y resuelve rutas. El resultado es la configuración efectiva.

```text
perfil + overrides + defaults
            ↓
validación estricta y resolución de rutas
            ↓
resolved_config
            ↓
serialización canónica
            ↓
config_hash
```

- `run_id` identifica la ejecución completa. Los stages pueden producir identificadores propios y no deben confundirse con él.
- `resolved_config` es el mapeo canónico de lo que realmente se usó, después de resolver defaults y rutas.
- `config_hash` es el SHA-256 de esa representación canónica. Permite detectar si dos ejecuciones declaradas como iguales usaron configuraciones distintas.
- `run_manifest.json` reúne estos datos con el modo de ejecución y las etapas completadas.

Los runners integrados actuales admiten la política `development/minimal` y el modo `dry-run`. No debe leerse esa política como una garantía sobre modos que no ejecutan.

### Verificación

Abre, en este orden:

1. [cyclic_current.json](../configs/compatibility/cyclic_current.json), para ver un perfil de simulación cíclica.
2. [daily_rag_current.json](../configs/compatibility/daily_rag_current.json), para ver un perfil de RAG diario.
3. [models.py](../youtube_pipeline/configuration/models.py), en `RunConfig` y las clases de cada sección.
4. [loading.py](../youtube_pipeline/configuration/loading.py), en `load_run_config` y `run_config_from_mapping`.
5. [run_manifest.py](../youtube_pipeline/run_manifest.py), en `build_resolved_config_metadata` y `build_run_manifest`.

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_current_pipeline_profile \
  tests.test_traceability_policy
```

El resultado esperado es `OK`. El primer test fija parámetros y rutas de los perfiles vigentes. El segundo comprueba qué política de trazabilidad aceptan los runners actuales y qué metadatos entran en el manifiesto.

### Debo poder explicar

1. ¿Qué diferencia hay entre el JSON solicitado y `resolved_config`?
2. ¿Por qué `run_id` y `config_hash` responden preguntas distintas?
3. ¿Qué secciones de `RunConfig` eligen dataset, detector y directorio de salida?
4. ¿Por qué un identificador de stage no sustituye al `run_id` de la ejecución?

## 5. De YouTube al dataset preparado

### El problema

La API y los CSV locales entregan registros útiles, pero el resto del pipeline necesita tipos, tiempos e identidades estables. La preparación conserva el origen y añade campos que permiten medir, ordenar y auditar.

```text
YouTube
comment_id, video_id, published time, text, author
        ↓ adquisición
registros fuente
        ↓ storage y normalización
event_time_utc + tipos y particiones
        ↓ cleaning
texto limpio + atributos derivados + filtros
        ↓
prepared comment
```

### Tres clases de campos

| Clase | Ejemplos | Quién tiene autoridad |
|---|---|---|
| `SOURCE` | `comment_id`, `video_id`, `published_at`, `text`, `author_id` | La fuente de YouTube o el archivo local conserva su valor original. |
| `NORMALIZED` | `event_time_utc`, timestamps Unix, particiones temporales, tipos homogéneos | Storage normaliza representación sin inventar el hecho fuente. |
| `DERIVED` | `text_clean`, `emoji_count`, `caps_ratio`, `link_count`, `token_count`, `is_probable_spam` | Cleaning calcula atributos y aplica sus reglas. |

### Adquisición

[data_extraction.py](../youtube_pipeline/data_extraction.py) consulta YouTube cuando se ejecuta la extracción y también contiene constructores de dataframes. Su responsabilidad es obtener videos, comentarios y metadatos con sus identificadores. No decide si existe un evento.

### Storage y normalización

[storage.py](../youtube_pipeline/storage.py) convierte tiempos a una forma coherente y escribe artefactos locales. Bronze conserva registros cercanos a la fuente en JSONL. Silver usa Parquet y tipos normalizados. Estos nombres ayudan a ubicar archivos. No sustituyen la inspección del esquema real.

### Cleaning

[cleaning.py](../youtube_pipeline/cleaning.py) normaliza texto y deriva atributos como conteos de emoji, signos, enlaces, mayúsculas y tokens. También aplica reglas para spam probable, filas vacías, respuestas huérfanas y duplicados temporales. La identidad del comentario, el video y el tiempo se preserva para poder seguir el registro.

### Prepared dataset

Gold o Prepared es el archivo local que consumen replay y simulación. Es una frontera de compatibilidad: el pipeline ya no necesita consultar YouTube para reproducir ese conjunto. No debe interpretarse como una afirmación de calidad científica del dataset.

### Verificación

Abre:

- [data_extraction.py](../youtube_pipeline/data_extraction.py): busca `build_comments_dataframe` y `run_extraction_pipeline`.
- [storage.py](../youtube_pipeline/storage.py): localiza la conversión a `event_time_utc` y las escrituras Bronze/Silver.
- [cleaning.py](../youtube_pipeline/cleaning.py): sigue las columnas derivadas y el reporte de filas excluidas.

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_local_files_storage_behavior \
  tests.test_cleaning_pipeline_behavior
```

`test_local_files_storage_behavior` prueba la fachada local de almacenamiento. No prueba una llamada real a YouTube. `test_cleaning_pipeline_behavior` prueba reglas y columnas de cleaning. No prueba representatividad ni sesgo de la muestra.

### Debo poder explicar

1. ¿Qué dato fuente permite enlazar un comentario con un video?
2. ¿Qué transformación convierte `published_at` en la base temporal del pipeline?
3. ¿Qué campos añade cleaning sin reemplazar el texto o los identificadores fuente?
4. ¿Qué significa Prepared para una ruta ejecutable y qué no garantiza?
5. ¿Por qué adquisición, storage y cleaning no tienen autoridad para declarar eventos?

## 6. El tiempo: la idea que gobierna el pipeline

El sistema necesita responder qué comentarios podían verse en un punto simulado. La columna que ordena y limita esa visibilidad es `event_time_utc`.

Actualmente `event_time_utc` se deriva de la hora de publicación de YouTube. No existe una segunda marca durable que registre cuándo el proyecto observó o ingirió realmente cada comentario. Por eso:

```text
event_time_utc ≠ hora real de ingestión
```

El pipeline puede simular causalidad sobre el tiempo de publicación. No puede demostrar, solo con ese campo, que los datos fueron recibidos en línea en ese instante.

### Corte causal

En la ruta cíclica, `data_cutoff_utc` marca el límite de visibilidad. La regla actual es estricta:

```text
event_time_utc < data_cutoff_utc
```

Ejemplo:

```text
cutoff = 12:00

comentario A = 11:58 → visible
comentario B = 12:00 → no visible todavía
comentario C = 12:03 → no visible todavía
```

Un `future leak` aparece si un artefacto de un ciclo usa un comentario cuyo `event_time_utc` está en o después del cutoff. La métrica `future_leak_count` debe ser cero.

La ventana de análisis usa otra condición:

```text
analysis_window_start_utc <= event_time_utc < analysis_window_end_utc
```

El cutoff responde “¿ya era visible?”. La ventana responde “¿pertenece al periodo que se analiza?”. Son controles distintos.

### Verificación

Busca `future_leak_count` y los límites semiabiertos en [cyclic_ingestion.py](../youtube_pipeline/cyclic_ingestion.py). Después ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_activity_signal_semantics.DailyReferenceSignalSemanticsTests
```

El test comprueba días locales en `America/Bogota`, límites UTC, deduplicación y ausencia de fuga futura. No crea un reloj de ingestión real.

### Debo poder explicar

1. ¿De qué campo fuente se deriva `event_time_utc`?
2. ¿Por qué `event_time_utc` no prueba ingestión online?
3. ¿Qué diferencia existe entre `data_cutoff_utc` y la ventana de análisis?
4. ¿Por qué un comentario exactamente en el cutoff aún no es visible?

## 7. Replay retrospectivo

### El problema

Tenemos todos los comentarios históricos, pero queremos entregarlos al sistema como si fueran apareciendo cronológicamente. Replay convierte un dataframe estático en una secuencia ordenada.

```text
prepared dataset
        ↓ seleccionar y validar tiempo
sort por event_time_utc
        ↓
comentario 1
comentario 2
comentario 3
...
        ↓ finalizar consumidores
```

[replay.py](../youtube_pipeline/replay.py) filtra, ordena y emite eventos. Puede introducir una demora de simulación, pero los tests suelen eliminarla. Al terminar, notifica el último tiempo a los consumidores que necesitan cerrar estado pendiente.

[prepared_replay.py](../youtube_pipeline/prepared_replay.py) adapta un dataset Prepared a ese mecanismo. Es el punto útil para estudiar selección de columnas, límites y manifiesto de replay.

### Replay y snapshot de 20 minutos no son lo mismo

[monitoring.py](../youtube_pipeline/monitoring.py) puede producir snapshots diagnósticos sobre una ventana de 20 minutos. Allí aparecen volumen, autores, videos y polarización.

```text
snapshot diagnóstico de 20 min
≠
señal XIAO de 120 s con cadence de 30 s
```

El snapshot resume el estado de una ventana amplia para inspección. XIAO consume una secuencia específica de conteos de comentarios. No uses el snapshot para explicar la entrada numérica de XIAO.

### Verificación

Abre, en orden:

1. [replay.py](../youtube_pipeline/replay.py), para la mecánica de emisión.
2. [prepared_replay.py](../youtube_pipeline/prepared_replay.py), para la frontera del dataset.
3. [monitoring.py](../youtube_pipeline/monitoring.py), solo para distinguir el snapshot.

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_prepared_replay_behavior \
  tests.test_xiao_replay_compatibility
```

El primer archivo prueba la forma y temporalidad del replay preparado. El segundo prueba orden, filtrado, finalización y compatibilidad entre alimentar XIAO con eventos o con observaciones. Ninguno demuestra que el snapshot de 20 minutos sea la señal XIAO.

### Debo poder explicar

1. ¿Por qué el dataframe se ordena antes de emitir eventos?
2. ¿Qué consumidor necesita la llamada de finalización?
3. ¿Qué diferencia hay entre reproducir comentarios y calcular un snapshot?
4. ¿Cuál es la ventana de la señal XIAO y cuál la del snapshot diagnóstico?

## 8. De comentarios a una señal de actividad

Un detector no debería tener que saber qué es un comentario de YouTube. Primero convertimos comentarios en una serie numérica.

### Métrica y señal

Una métrica dice qué se calcula:

```text
contar comentarios
```

Una señal añade identidad y semántica temporal:

```text
conteo de comentarios
en ventana cerrada de 120 s
cada 30 s
usando event_time_utc
en UTC
```

`ActivitySignalDefinition` registra esa identidad semántica. Su `signal_id` para la señal de referencia es:

```text
comment_count_event_window_120s_step_30s
```

Cada valor calculado para una ventana concreta se representa con `ActivityObservation`. Sus campos responden:

| Campo | Pregunta |
|---|---|
| `signal` | ¿Qué señal se midió? |
| `observation_time_utc` | ¿En qué tick se observó? |
| `window_start_utc`, `window_end_utc` | ¿Qué intervalo causal cubre? |
| `value` | ¿Cuál fue el valor numérico? |
| `support_count` | ¿Cuántos registros sostienen la medición? |
| `quality` | ¿Qué calidad reportó el productor de señal? |

### Ejemplo mínimo

Supón estos comentarios:

```text
c1  00:00:00
c2  00:00:10
c3  00:00:30
```

La ventana es cerrada y dura 120 segundos. La cadence es de 30 segundos.

1. Al recibir `c1`, el primer tick coincide con `00:00:00`. La ventana `23:58:00–00:00:00` contiene un comentario.
2. `c2` llega a `00:00:10`. Todavía no hay un nuevo tick.
3. `c3` llega exactamente a `00:00:30`. Se incorpora y se emite la ventana `23:58:30–00:00:30` con tres comentarios.

| Tick | Ventana | `value` | `support_count` | `quality` |
|---|---|---:|---:|---|
| `00:00:00` | `23:58:00–00:00:00` | 1 | 1 | `passed` |
| `00:00:30` | `23:58:30–00:00:30` | 3 | 3 | `passed` |

El productor de señal tiene autoridad sobre `value`, `support_count` y `quality`. El detector recibe esos campos. No vuelve a contar comentarios y no debe inventar otra calidad.

### Verificación

Abre [activity_signals.py](../youtube_pipeline/activity_signals.py). Sigue este orden:

1. `ActivitySignalDefinition`.
2. `ActivityObservation`.
3. `EventWindowActivitySignal.on_event`.
4. `_build_observation`.
5. `EventWindowCommentCountSignal`.

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_activity_signal_contracts \
  tests.test_activity_signal_semantics.XiaoReferenceSignalSemanticsTests
```

Los tests comprueban validación del contrato, alineación de ticks, fronteras cerradas, huecos y conteos. No prueban que XIAO sea el detector correcto para cualquier dataset.

### Debo poder explicar

1. ¿Por qué `comment_count` no identifica por sí solo una señal?
2. ¿Qué significado añaden ventana, cadence y base temporal?
3. ¿Quién decide `quality` y por qué?
4. ¿Qué diferencia hay entre `value` y `support_count`?
5. ¿Qué ocurre cuando un comentario llega exactamente en un tick?

## 9. Cómo XIAO analiza la señal

### El problema

Ya tenemos una secuencia de valores comparables. Falta decidir si el valor reciente se aparta de su comportamiento más lento y si el cambio satisface las condiciones del detector.

```text
ActivityObservation.value
            ↓
actualizar EMA rápida y EMA lenta
            ↓
calcular relación rápida / lenta
            ↓
comprobar warmup, volumen y cooldown
            ↓
DetectionResult
```

La EMA rápida reacciona antes a un aumento. La EMA lenta conserva más historia. XIAO compara ambas sin volver a consultar los comentarios.

### Condiciones necesarias para seguir la ejecución

- `warmup` deja que las EMAs acumulen observaciones antes de aplicar la regla normal. Durante esa fase solo puede abrirse un trigger por volumen extremo.
- `v_min` exige un volumen mínimo para la regla posterior al warmup.
- `sensitivity` exige que la EMA rápida supere la EMA lenta por la relación configurada.
- `cooldown` bloquea la apertura de otro trigger durante un intervalo y permite completar el trigger activo.

Los valores por defecto de la implementación de referencia son 10 ventanas de warmup, `v_min=46`, sensibilidad `1.5` y cooldown de 3 minutos. Un perfil de compatibilidad puede resolver otros valores. Por eso, al explicar una ejecución concreta, consulta su `resolved_config`.

### La salida neutral: `DetectionResult`

El detector devuelve una decisión para una observación:

| Campo | Significado |
|---|---|
| `detector_id` | Estrategia que tomó la decisión, hoy `xiao_ema` en esta ruta. |
| `signal_id` | Señal evaluada. |
| `observation_time_utc` | Tick de la observación. |
| `triggered` | Si esta evaluación abrió un trigger. |
| `quality` | Calidad propagada desde la observación. |
| `score` | Relación numérica usada como fuerza de la decisión. |
| `detector_metadata` | Volumen, EMAs, ventanas procesadas, warmup y cooldown. |

La frontera de autoridad es precisa:

```text
productor de señal → value, support_count, quality
detector            → triggered, score, detector_metadata
```

XIAO copia `quality` sin modificarla. Esto evita que una regla estadística se atribuya autoridad sobre la calidad del dato que recibió.

### El ejemplo anterior entra en XIAO

Con `c1`, `c2` y `c3`, los dos resultados son:

| Tick | Valor | EMA rápida | EMA lenta | Score | `triggered` |
|---|---:|---:|---:|---:|---|
| `00:00:00` | 1 | 1.0 | 1.0 | 1.0 | `false` |
| `00:00:30` | 3 | 1.8 | 1.190476 | 1.512 | `false` |

Aunque el segundo score supera 1.5, no se abre un trigger. Solo se han procesado dos ventanas y el volumen tampoco supera el umbral extremo. Este ejemplo sirve para seguir el contrato. No calibra ni evalúa el detector.

### Verificación

Abre:

1. [detectors.py](../youtube_pipeline/detectors.py), en `XiaoEMAConfig`, `on_observation` y `_advance_observation`.
2. [activity_detection.py](../youtube_pipeline/activity_detection.py), en `DetectionResult` y `dispatch_activity_observation`.

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_detection_result_contract \
  tests.test_xiao_replay_compatibility.XiaoCompatibilityTests
```

El primer test prueba forma, validación e inmutabilidad del resultado neutral. El segundo compara las decisiones de XIAO cuando recibe eventos y cuando recibe observaciones explícitas.

### Debo poder explicar

1. ¿Qué cambia más rápido, la EMA rápida o la lenta?
2. ¿Por qué un score alto puede no producir un trigger durante warmup?
3. ¿Qué campos decide XIAO y cuál debe propagar?
4. ¿Qué referencias prueban que resultado y observación corresponden al mismo tick?

## 10. Un resultado del detector no es un evento real

La cadena conceptual tiene cuatro afirmaciones de alcance distinto:

```text
ActivityObservation
“la señal valió X en esta ventana”
        ↓
DetectionResult
“el detector aplicó su regla y decidió Y”
        ↓
EventCandidate
“la detección disparada se puede identificar y rastrear”
        ↓
validación posterior
“la evidencia permite o no interpretar lo ocurrido”
```

`triggered=true` significa que el detector encontró un cambio según sus parámetros. No significa que ocurrió un evento real. Tampoco dice cuál fue el tema, la causa o el alcance social del cambio.

G-1 y G-2 están después porque responden preguntas distintas. El detector trabaja con una señal. Las validaciones trabajan con evidencia interna y externa.

## 11. El split importante de la ruta retrospectiva

Hay dos salidas nacidas de la misma evaluación de XIAO. Ocupan papeles distintos en el runtime actual.

### Contrato neutral implementado

```text
ActivityObservation
        ↓ XIAO.on_observation
DetectionResult
```

Esta frontera está implementada y probada. `DetectionResult` permite hablar de una decisión sin depender de la forma histórica de XIAO.

### Runtime histórico activo

```text
XIAO abre active trigger
        ↓ mantiene lock
cooldown
        ↓ cierre o finalize
completed_triggers
```

Cuando el replay llama `XiaoEMATriggerDetector.on_event`, el detector produce internamente observaciones y resultados. `on_event` no devuelve ni persiste esos `DetectionResult`. El flujo retrospectivo continúa con `detector.completed_triggers`.

Por tanto:

```text
DetectionResult producido internamente
≠ objeto persistido que alimenta evidencia retrospectiva
```

Ambas formas nacen de la misma evaluación. Los tests comprueban que el trigger neutral y el trigger completado coinciden en tiempo, fuerza y volumen. Sin embargo, el runner retrospectivo lee `completed_triggers`, no una colección persistida de `DetectionResult`.

### Verificación

En [detectors.py](../youtube_pipeline/detectors.py):

1. Sigue `on_event` hasta `on_observation`.
2. Observa que `on_event` no retorna el resultado.
3. Sigue `_open_trigger`, `_close_trigger` y `completed_triggers`.

En [run_local_csv_retrospective.py](../scripts/run_local_csv_retrospective.py), busca `detector.completed_triggers` en el replay y en la creación del mapa de comentarios.

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_xiao_replay_compatibility.XiaoCompatibilityTests.test_explicit_observation_route_preserves_xiao_decisions
```

El test demuestra paridad de decisiones. No demuestra que el runner persista `DetectionResult` ni que lo promueva automáticamente.

### Debo poder explicar

1. ¿De dónde nacen `DetectionResult` y el trigger activo?
2. ¿Qué objeto espera hoy la evidencia retrospectiva?
3. ¿Por qué paridad de decisión no implica igualdad de handoff?
4. ¿Qué hace `finalize` si queda un trigger abierto?

## 12. Qué es `EventCandidate`

Una detección disparada necesita identidad, una ventana causal y referencias de linaje. El contrato neutral que reúne esos elementos se llama `EventCandidate`.

```text
DetectionResult con triggered=true
+ ActivityObservation correspondiente
+ candidate_id
+ ventana de evidencia causal
+ run_id, config_hash y dataset_ref
        ↓
EventCandidate
```

El contrato exige que señal, tiempo y calidad coincidan entre observación y resultado. También impide que la ventana de evidencia termine después de la detección.

`EventCandidate` no contiene:

- comentarios;
- videos;
- unidades de contexto;
- prompts;
- resultados de G-1 o G-2.

Esa ausencia preserva responsabilidades. El candidato identifica una decisión promovida. La capa de evidencia decide qué registros se asocian. La capa RAG organiza y selecciona contexto. La validación produce una interpretación.

### Estado actual

`EventCandidate` existe y está probado. También existe `promote_detection_result`. Pero todavía no es el handoff general del runtime retrospectivo o diario.

El archivo `event_candidates.csv` que puede producir la preparación retrospectiva es una proyección tabular construida a partir del mapa de triggers. No prueba que el runtime haya instanciado o persistido la clase `EventCandidate`.

### Verificación

Abre [event_candidates.py](../youtube_pipeline/event_candidates.py). Revisa `EventCandidateLineage`, `EventCandidate` y `promote_detection_result`.

Ejecuta:

```bash
.venv/bin/python -m unittest tests.test_event_candidate_contract
```

El test demuestra que solo un resultado disparado y consistente puede promoverse, y que el linaje y las ventanas se validan. No demuestra que un entrypoint actual llame a esa promoción.

### Debo poder explicar

1. ¿Qué añade `EventCandidate` sobre `DetectionResult`?
2. ¿Por qué no copia comentarios o videos?
3. ¿Qué referencias mínimas conserva su linaje?
4. ¿Qué diferencia hay entre la clase y `event_candidates.csv`?

## 13. Cómo se construye realmente la evidencia retrospectiva

La ruta activa parte del trigger histórico:

```text
completed_trigger
        ↓ build_trigger_comment_map
trigger_comment_map.csv
        ↓ ensamblado
event_comment_inventory.csv
event_video_map.csv
event_evidence_packages.jsonl
```

### Ventana pre-trigger

El runner vuelve al dataset limpio y selecciona comentarios con una ventana inclusiva:

```text
window_start <= comment_time <= trigger_time
```

Este paso crea asociaciones trazables mediante `comment_id` y conserva `video_id`. El periodo previo permite examinar qué comentarios sostienen el cambio observado, sin incluir información posterior al trigger.

### Por qué no basta con `trigger["comments"]`

Mientras el detector está en cooldown, guarda una lista interna con tiempo y texto de comentarios recibidos después de abrir el trigger. Esa lista ayuda al estado histórico del detector, pero no es el inventario definitivo de evidencia:

- corresponde al intervalo de lock, no a la ventana causal pre-trigger;
- no conserva toda la identidad y el linaje requeridos;
- la autoridad para asociar evidencia pertenece al ensamblador.

Por eso `build_trigger_comment_map` reconstruye la asociación desde el dataset limpio.

### Artefactos principales

- `event_id` identifica el candidato operativo retrospectivo y une los artefactos posteriores.
- `event_comment_inventory.csv` contiene el inventario completo de comentarios asociados.
- `event_video_map.csv` resume la relación evento-video sin perder la referencia al evento.
- `event_evidence_packages.jsonl` agrupa referencias y conteos de la evidencia por evento.

Dos módulos producen representaciones complementarias. [rag_evidence.py](../youtube_pipeline/rag_evidence.py) construye candidatos tabulares, mapas y paquetes formales. [rag_sidecars.py](../youtube_pipeline/rag_sidecars.py) construye los sidecars orientados al consumidor que usa el RAG retrospectivo activo.

### Verificación

1. En [run_local_csv_retrospective.py](../scripts/run_local_csv_retrospective.py), abre `build_trigger_comment_map` y comprueba ambos límites inclusivos.
2. En [rag_sidecars.py](../youtube_pipeline/rag_sidecars.py), sigue `build_event_comment_inventory`, `build_event_video_map` y `build_context_units`.
3. En [rag_evidence.py](../youtube_pipeline/rag_evidence.py), compara la preparación formal. No la confundas con la entrada del consumidor activo.

El test de compatibilidad de XIAO prueba que se completa el trigger. Los tests de sidecars y consumidor prueban la evidencia posterior. Ningún test convierte los comentarios acumulados en cooldown en inventario definitivo.

### Debo poder explicar

1. ¿Desde qué objeto comienza la evidencia retrospectiva activa?
2. ¿Qué regla temporal decide qué comentarios entran?
3. ¿Por qué el detector no decide el inventario final?
4. ¿Qué ID permite unir inventario, videos y paquete de evidencia?

## 14. Evidencia no es contexto RAG

El inventario de evidencia busca conservar pertenencia y trazabilidad. Un modelo generativo tiene un presupuesto finito. Por eso una segunda capa organiza comentarios y puede seleccionar solo una parte.

```text
EVIDENCIA COMPLETA
todos los comentarios asociados al event_id
        ↓ organizar por video, hilo y tiempo
context units
        ↓ aplicar presupuesto
SELECCIÓN RAG
solo las unidades que caben
```

Que un comentario no sea seleccionado por presupuesto no significa que deje de pertenecer a la evidencia. Debe permanecer en `event_comment_inventory.csv` y aparecer como omitido o no usado en los reportes correspondientes.

### Unidades de contexto

Una unidad de contexto agrupa comentarios que pueden enviarse juntos. Su `context_unit_id` identifica el grupo. El mapa `context_unit_comment_map.csv` enlaza cada unidad con sus `comment_id`.

```text
event_id
  └─ context_unit_id
       ├─ comment_id c1
       ├─ comment_id c2
       └─ comment_id c3
```

[rag_consumer.py](../youtube_pipeline/rag_consumer.py) lee los sidecars, arma entradas de validación y payloads de contexto, y deja stubs de evaluación cuando todavía no se ejecuta una validación generativa.

### Verificación

En [rag_sidecars.py](../youtube_pipeline/rag_sidecars.py), compara el inventario completo con `build_context_units`. En [rag_consumer.py](../youtube_pipeline/rag_consumer.py), sigue la lista `selected_unit_ids` y el mapa de comentarios utilizado.

Preguntas para revisar:

1. ¿Dónde se conserva un comentario omitido por presupuesto?
2. ¿Qué relación enlaza `context_unit_id` con `comment_id`?
3. ¿Qué capa decide pertenencia a evidencia y cuál decide uso de contexto?
4. ¿Por qué el número de comentarios enviados puede ser menor que el inventario?

## 15. G-1 y G-2

Una vez preparado el contexto retrospectivo, la ruta puede ejecutar dos validaciones con preguntas diferentes.

### G-1: interpretación interna

```text
candidato
+ evidencia interna de YouTube
        ↓
evaluación de lo ocurrido dentro de la comunidad observada
```

[rag_generation_g1.py](../youtube_pipeline/rag_generation_g1.py) consume la entrada retrospectiva y exige citas trazables a `comment_id` o `context_unit_id`. Produce una evaluación, una interpretación, confianza y referencias. No consulta noticias para decidir qué ocurrió fuera de la comunidad observada.

### G-2: contraste externo

```text
candidato
+ resultado interno
+ evidencia externa recuperada
        ↓
contraste con información externa
```

[rag_generation_g2.py](../youtube_pipeline/rag_generation_g2.py) construye una consulta, obtiene evidencia externa y produce la evaluación externa plana. Su ejecución real requiere servicios externos. Los laboratorios de esta guía no los llaman.

### Variante jerárquica de G-2

La implementación jerárquica cambia la unidad de trabajo, no el propósito:

```text
evento
→ video
→ consulta y evidencia externa del video
→ evaluación por video
→ síntesis del evento
```

[rag_generation_g2_hierarchical.py](../youtube_pipeline/rag_generation_g2_hierarchical.py) conserva citas aisladas por video antes de sintetizar el evento. El modo dry-run valida preparación y orden sin red y sin escribir resultados generativos.

G-1 y G-2 no forman parte del detector. Reciben un candidato operativo y evidencia ya ensamblada. Una salida generativa tampoco reescribe la señal ni el trigger.

### Otra preparación retrospectiva vigente

También existe una rama ejecutable de preparación contractual:

```text
trigger_comment_map.csv
→ rag_evidence
→ event_evidence_packages.jsonl
→ rag_validation
→ tareas, preguntas, placeholders y resultados pending
```

[rag_validation.py](../youtube_pipeline/rag_validation.py) prepara esos artefactos, pero no recupera evidencia externa ni ejecuta un modelo. Esta rama no sustituye el camino sidecars → consumer → G-1/G-2 descrito arriba. `test_non_daily_rag_stage_scripts` comprueba que sus scripts delegan en los resolvers comunes, no que produzcan una validación generativa.

### Verificación

Ejecuta el test determinista de la variante jerárquica:

```bash
.venv/bin/python -m unittest tests.test_rag_generation_g2_hierarchical
```

El test comprueba orden, aislamiento de citas por video, verificaciones y dry-run. No prueba credenciales, disponibilidad de APIs ni calidad factual de una respuesta remota.

### Debo poder explicar

1. ¿Qué evidencia usa G-1?
2. ¿Qué añade G-2 a la pregunta de G-1?
3. ¿Por qué la variante jerárquica evalúa por video antes de sintetizar?
4. ¿Por qué ninguna de estas etapas debe alterar `DetectionResult`?

## 16. Recorrido retrospectivo completo

Este recorrido une solo componentes activos. La ejecución está repartida entre el runner retrospectivo y entrypoints RAG posteriores. No hay un único comando que ejecute toda la cadena de extremo a extremo.

### Paso 1. Preparar la configuración retrospectiva

**Qué entra:** argumentos del runner, rutas locales y parámetros de detector.

**Qué ocurre:** se fija identidad, dataset, salida y configuración efectiva de la ejecución local.

**Qué sale:** configuración resuelta y referencias que luego entran al manifiesto.

**Archivo:** [run_local_csv_retrospective.py](../scripts/run_local_csv_retrospective.py).

**Cómo verificarlo:** inspecciona los argumentos del `main` y el contenido de `build_manifest`.

### Paso 2. Extraer o leer comentarios

**Qué entra:** una fuente de YouTube o un CSV local.

**Qué ocurre:** se forman registros con `comment_id`, `video_id`, tiempo, texto y autor.

**Qué sale:** dataframe de comentarios fuente.

**Archivos:** [data_extraction.py](../youtube_pipeline/data_extraction.py) y [run_local_csv_retrospective.py](../scripts/run_local_csv_retrospective.py).

**Cómo verificarlo:** ejecuta `tests.test_local_files_storage_behavior` para la ruta local. No lo interpretes como prueba de la API.

### Paso 3. Normalizar y limpiar

**Qué entra:** registros fuente.

**Qué ocurre:** storage normaliza tiempos y tipos; cleaning produce texto y atributos derivados y aplica exclusiones documentadas.

**Qué sale:** dataset Gold/Prepared con identidad preservada y `event_time_utc`.

**Archivos:** [storage.py](../youtube_pipeline/storage.py) y [cleaning.py](../youtube_pipeline/cleaning.py).

**Cómo verificarlo:** ejecuta `tests.test_cleaning_pipeline_behavior` y sigue un `comment_id` en la salida.

### Paso 4. Reproducir en orden causal

**Qué entra:** dataset preparado.

**Qué ocurre:** replay ordena por `event_time_utc`, filtra el intervalo seleccionado y emite comentarios.

**Qué sale:** stream histórico ordenado.

**Archivos:** [replay.py](../youtube_pipeline/replay.py) y [prepared_replay.py](../youtube_pipeline/prepared_replay.py).

**Cómo verificarlo:** ejecuta `tests.test_prepared_replay_behavior` y revisa el orden esperado.

### Paso 5. Producir observaciones de actividad

**Qué entra:** comentarios ordenados.

**Qué ocurre:** la señal mantiene una ventana cerrada de 120 segundos y emite un conteo cada 30 segundos.

**Qué sale:** `ActivityObservation` con valor, soporte y calidad.

**Archivo:** [activity_signals.py](../youtube_pipeline/activity_signals.py).

**Cómo verificarlo:** ejecuta `tests.test_activity_signal_semantics.XiaoReferenceSignalSemanticsTests`.

### Paso 6. Evaluar con XIAO

**Qué entra:** cada `ActivityObservation`.

**Qué ocurre:** XIAO actualiza EMAs, comprueba warmup, volumen, sensibilidad y cooldown.

**Qué sale:** un `DetectionResult` por observación y, si se dispara y cierra, un elemento en `completed_triggers`.

**Archivos:** [detectors.py](../youtube_pipeline/detectors.py) y [activity_detection.py](../youtube_pipeline/activity_detection.py).

**Cómo verificarlo:** ejecuta `tests.test_xiao_replay_compatibility`. Confirma tanto el resultado neutral como el trigger completado.

### Paso 7. Construir el mapa trigger-comentario

**Qué entra:** `completed_triggers` y dataset limpio.

**Qué ocurre:** para cada trigger se selecciona la ventana pre-trigger inclusiva.

**Qué sale:** `trigger_comment_map.csv` con referencias a `comment_id` y `video_id`.

**Archivo:** [run_local_csv_retrospective.py](../scripts/run_local_csv_retrospective.py), función `build_trigger_comment_map`.

**Cómo verificarlo:** inspecciona la máscara `window_start <= event_time <= trigger_time`.

### Paso 8. Ensamblar evidencia y sidecars

**Qué entra:** mapa trigger-comentario, comentarios y videos.

**Qué ocurre:** se crea `event_id`, inventario completo, mapa de videos, unidades de contexto y paquete de evidencia.

**Qué sale:** sidecars retrospectivos trazables.

**Archivo:** [rag_sidecars.py](../youtube_pipeline/rag_sidecars.py).

**Cómo verificarlo:** comprueba que cada fila del mapa de unidad conserve `event_id`, `context_unit_id` y `comment_id`.

### Paso 9. Preparar el input RAG

**Qué entra:** sidecars retrospectivos.

**Qué ocurre:** el consumidor valida relaciones, selecciona unidades y crea payloads y stubs.

**Qué sale:** `rag_validation_inputs.jsonl`, `rag_context_payloads.jsonl` y artefactos de no evaluación.

**Archivo:** [rag_consumer.py](../youtube_pipeline/rag_consumer.py).

**Cómo verificarlo:** compara comentarios del inventario con comentarios usados. Una diferencia debe ser explicable por la selección.

### Paso 10. Ejecutar G-1

**Qué entra:** candidato operativo y evidencia interna seleccionada.

**Qué ocurre:** se evalúa qué puede sostenerse dentro de la comunidad observada.

**Qué sale:** resultado G-1 con estado, interpretación, confianza y citas.

**Archivo:** [rag_generation_g1.py](../youtube_pipeline/rag_generation_g1.py).

**Cómo verificarlo:** en una ejecución ya producida, valida que cada cita pertenezca al conjunto permitido. No llames una API externa en este estudio.

### Paso 11. Ejecutar G-2

**Qué entra:** candidato, resultado G-1 y evidencia externa recuperada.

**Qué ocurre:** se contrasta el candidato con fuentes externas, en forma plana o por video.

**Qué sale:** resultado G-2 y verificaciones de citas.

**Archivos:** [rag_generation_g2.py](../youtube_pipeline/rag_generation_g2.py) o [rag_generation_g2_hierarchical.py](../youtube_pipeline/rag_generation_g2_hierarchical.py).

**Cómo verificarlo:** usa `tests.test_rag_generation_g2_hierarchical` para la frontera determinista. Este test no contacta servicios externos.

## 17. La ruta diaria desde cero

Ahora cambia de ruta. La ruta diaria no es la retrospectiva ejecutada una vez por día. Cambian la unidad temporal, la señal que llega al detector, el objeto de evento y la forma de separar evidencia.

```text
Gold/Prepared
      ↓
cycle diario
      ↓
ventana activa causal
      ↓
daily signals
      ↓
baseline de frecuencia
      ↓
daily event
      ↓
daily evidence sidecars
      ↓
daily RAG consumer
      ↓
context selection
```

El runner integrado [cyclic_pipeline.py](../youtube_pipeline/entrypoints/cyclic_pipeline.py) coordina:

1. ingestión cíclica;
2. plan de orquestación;
3. estado activo;
4. conector de detección preparado;
5. señales diarias;
6. baseline diario.

Después, [daily_rag_pipeline.py](../youtube_pipeline/entrypoints/daily_rag_pipeline.py) coordina sidecars, consumidor y selección de contexto.

Estos runners escriben manifiestos de ejecución separados. Por eso una traza diaria puede contener el `run_id` global y varios IDs de stage. Tampoco se debe asumir un único `config_hash` compartido entre la ejecución cíclica y una ejecución diaria RAG posterior, salvo que los manifiestos lo demuestren.

## 18. Simulación cíclica

### El problema

La simulación debe revelar comentarios en ciclos sin usar datos futuros. También necesita conservar cuáles siguen activos dentro de la ventana de análisis.

Imagina tres comentarios y una ventana activa de dos días:

```text
comentario c1 publicado el día 1
comentario c2 publicado el día 2
comentario c3 publicado el día 3
```

Un recorrido pedagógico sería:

| Ciclo | `new` | `active` | `exited` |
|---|---|---|---|
| Día 1 | c1 | c1 | ninguno |
| Día 2 | c2 | c1, c2 | ninguno |
| Día 3 | c3 | c2, c3 | c1 |

- `new` identifica comentarios publicados en la colección del ciclo.
- `active` identifica comentarios todavía dentro de la ventana causal activa.
- `exited` identifica comentarios que estaban activos y ya salieron de esa ventana.

El ejemplo muestra el cambio de estado. Los límites exactos se calculan con timestamps UTC y una fecha de ciclo en `America/Bogota` según el perfil actual.

### Corte y ventana

Cada ciclo tiene `data_cutoff_utc`. Ningún comentario con tiempo igual o posterior puede entrar. La ventana de análisis determina qué comentarios visibles siguen activos.

```text
visible: event_time_utc < data_cutoff_utc
activo:  analysis_start <= event_time_utc < analysis_end
```

### El conector XIAO está preparado, pero no ejecutado

[cyclic_detection_connector.py](../youtube_pipeline/cyclic_detection_connector.py) prepara contratos e inventarios para detección. En el runner integrado actual se usa `detection_dry_run`. El resultado debe indicar:

```text
status = prepared_not_executed
```

Esto significa que el ciclo comprobó que podría preparar la entrada. No significa que XIAO procesó las observaciones ni que produjo triggers.

El módulo contiene una función de smoke test que puede ejecutar más lógica de XIAO de forma aislada. Esa función no convierte el runner cíclico actual en una ejecución XIAO.

### Verificación

Abre:

1. [cyclic_ingestion.py](../youtube_pipeline/cyclic_ingestion.py), para cortes y ciclos.
2. [cyclic_stateful_adapter.py](../youtube_pipeline/cyclic_stateful_adapter.py), para `new`, `active` y `exited`.
3. [cyclic_detection_connector.py](../youtube_pipeline/cyclic_detection_connector.py), para `prepared_not_executed`.

Ejecuta:

```bash
.venv/bin/python -m unittest tests.test_cyclic_pipeline_entrypoint
```

El test demuestra que las seis etapas se conectan, que el manifiesto se escribe y que no hay fuga futura. También fija que el conector produce cero eventos en el modo integrado actual. No demuestra ejecución cíclica real de XIAO.

### Debo poder explicar

1. ¿Qué diferencia hay entre comentario nuevo y comentario activo?
2. ¿Cuándo un comentario pasa a `exited`?
3. ¿Qué controla `data_cutoff_utc`?
4. ¿Por qué `prepared_not_executed` no es una detección?

## 19. Baseline diario

### El problema

La ruta diaria necesita comparar la actividad del ciclo actual con actividad reciente. Para el perfil vigente, la señal principal es `new_comment_count`.

```text
actividad nueva de hoy
        vs
actividad de ciclos recientes
        ↓
baseline, ratio y delta
        ↓
condiciones de umbral
        ↓
trigger_candidate
        ↓
daily_event_id
```

[cyclic_daily_signals.py](../youtube_pipeline/cyclic_daily_signals.py) produce `cycle_signal_series.jsonl`. Además del conteo nuevo, conserva conteos activos y salidos, videos, deltas y hashes necesarios para trazabilidad.

[daily_frequency_baseline.py](../youtube_pipeline/daily_frequency_baseline.py) calcula:

- `baseline`: referencia de ciclos recientes;
- `ratio`: valor actual dividido por baseline cuando está definido;
- `delta`: diferencia absoluta;
- condiciones mínimas de conteo, cambio y porcentaje;
- warmup y cooldown del detector diario;
- `trigger_candidate` y, cuando corresponde, `daily_event_id`.

El perfil actual usa tres ciclos para el baseline y exige warmup antes de disparar. Sus umbrales son parámetros de ejecución. Los tests prueban su aplicación, no una calibración científica.

### Frontera activa

El evento diario es un contrato especializado de esta ruta. Actualmente no se crea mediante `DetectionResult` ni `EventCandidate`. Presentarlo como esos objetos ocultaría el runtime real.

```text
cycle signal row
→ daily frequency baseline
→ daily_event_id

no actualmente:
cycle signal row
→ DetectionResult
→ EventCandidate
```

### Verificación

Abre [cyclic_daily_signals.py](../youtube_pipeline/cyclic_daily_signals.py) y luego [daily_frequency_baseline.py](../youtube_pipeline/daily_frequency_baseline.py).

Ejecuta:

```bash
.venv/bin/python -m unittest tests.test_daily_frequency_baseline
```

El test demuestra warmup, cálculo del baseline, condiciones de aumento, identidad determinista y cooldown configurado. No demuestra que los umbrales generalicen a otro canal o periodo.

### Debo poder explicar

1. ¿Qué valor diario usa el perfil como señal de detección?
2. ¿Qué diferencias expresan `ratio` y `delta`?
3. ¿Por qué se necesita warmup en el baseline?
4. ¿Por qué el evento diario no debe llamarse `DetectionResult`?

## 20. Alert evidence frente a validation context

El evento diario necesita dos conjuntos relacionados, pero no idénticos.

- **Alert evidence** responde: ¿qué comentarios nuevos del ciclo participaron en la alerta?
- **Validation context** responde: ¿qué comentarios visibles y activos pueden ayudar a interpretar el evento?

Ejemplo:

```text
comentario nuevo hoy
→ is_alert_evidence = true
→ is_validation_context = true si está activo

comentario de ayer todavía activo
→ is_alert_evidence = false
→ is_validation_context = true
```

Los conjuntos pueden solaparse. No son particiones excluyentes.

En [daily_rag_sidecars.py](../youtube_pipeline/daily_rag_sidecars.py), las reglas activas son:

```text
is_alert_evidence = is_new_in_cycle
is_validation_context = is_active_in_window
```

Si un comentario cumple ambas, su `temporal_role` principal es `alert_evidence`, pero la bandera de contexto sigue siendo verdadera.

### Verificación

Ejecuta:

```bash
.venv/bin/python -m unittest tests.test_daily_rag_sidecars
```

El caso central construye cuatro comentarios de contexto, dos de ellos nuevos. Comprueba dos filas de alert evidence y cuatro de validation context. No prueba relevancia semántica del texto.

### Debo poder explicar

1. ¿Puede un comentario pertenecer a ambos conjuntos?
2. ¿Qué condición activa cada bandera?
3. ¿Por qué un comentario de ayer puede ayudar a validar una alerta de hoy?
4. ¿Qué inventario conserva las dos decisiones por `comment_id`?

## 21. RAG diario

La ruta diaria transforma sidecars en entradas consumibles y después decide qué unidades caben en el presupuesto.

```text
daily sidecars
        ↓
daily consumer
        ↓
payload completo por evento
        ↓
context selection
        ↓
payload seleccionado + omisiones
```

### Sidecars

[daily_rag_sidecars.py](../youtube_pipeline/daily_rag_sidecars.py) crea el inventario por `daily_event_id`, mapas de video y unidades de contexto `dctx_*`. Las unidades se agrupan por video, hilo y tiempo, con un máximo de comentarios configurado.

### Consumer

[daily_rag_consumer.py](../youtube_pipeline/daily_rag_consumer.py) valida que las referencias sean coherentes y prepara inputs, payloads y stubs. No llama un modelo ni una fuente externa.

### Selección

[daily_rag_context_selection.py](../youtube_pipeline/daily_rag_context_selection.py) aplica el orden actual:

1. unidades de alerta primero;
2. cobertura inicial de videos activos mientras haya presupuesto;
3. más unidades de alerta hasta el objetivo de cobertura;
4. contexto de validación para videos ya seleccionados si aún cabe;
5. registro de unidades omitidas y su razón.

El presupuesto vigente del perfil se expresa en tokens. No altera el inventario de evidencia. Solo limita el payload seleccionado.

### Punto de parada actual

```text
daily RAG context selection
→ fin de la ruta diaria actual
```

No hay un stage diario integrado que ejecute G-1 o G-2 después de esta selección.

### Verificación

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_daily_rag_pipeline_entrypoint \
  tests.test_daily_rag_context_selection
```

El primer test demuestra la conexión sidecars-consumer-selector y la propagación de IDs de stage. El segundo demuestra prioridad de alerta, presupuesto y razones de omisión. Ninguno demuestra validación generativa diaria.

### Debo poder explicar

1. ¿Qué produce el sidecar que después consume el selector?
2. ¿Por qué se prioriza alert evidence?
3. ¿Dónde quedan documentadas las unidades que no caben?
4. ¿En qué punto exacto termina la ruta diaria?

## 22. Las dos rutas comparadas

| Concepto | Retrospectiva | Diaria |
|---|---|---|
| Tiempo | Replay continuo por `event_time_utc` | Ciclos diarios con cutoff |
| Señal de detección | Conteo en 120 s, cadence 30 s | `new_comment_count` por ciclo |
| Detector activo | XIAO | Baseline de frecuencia |
| Candidato operativo | Trigger histórico completado | Evento con `daily_event_id` |
| Evidencia de alerta | Ventana pre-trigger inclusiva | Comentarios nuevos del ciclo |
| Contexto disponible | Evidencia retrospectiva asociada | Comentarios activos de la ventana |
| Preparación RAG | Sidecars y consumidor retrospectivos | Sidecars, consumidor y selector diarios |
| G-1/G-2 | Sí, como stages posteriores | No actualmente |
| Contrato neutral general | Producido en XIAO, no es el handoff de evidencia | No usado por el baseline diario |

La tabla muestra equivalencias pedagógicas, no identidad de clases. “Candidato operativo” significa el objeto o fila que realmente continúa en cada ruta.

## 23. Trazabilidad: seguir un resultado hacia atrás

La trazabilidad no consiste en recordar carpetas. Consiste en usar IDs y referencias para reconstruir cada salto.

### Ejercicio A. Ruta retrospectiva

Empieza por un resultado G-2 ya producido. Un ejemplo conservado puede usar IDs como `event_id=evt_34d7999bde8c` y un `run_id` como `run_a3547acbcfd1`. Los valores concretos cambian por ejecución.

```text
G-2 result
    ↑ event_id, validation_id, citas externas e internas
G-1 result / RAG input
    ↑ event_id, used_context_unit_ids
context payload
    ↑ context_unit_id
context_unit_comment_map.csv
    ↑ comment_id
event_comment_inventory.csv
    ↑ event_id, trigger_time, window_start
trigger_comment_map.csv
    ↑ trigger_time, window_start, window_end, comment_id
completed_trigger
    ↑ detector_id, trigger_time, score/strength
ActivityObservation y señal
    ↑ signal_id, observation_time_utc
prepared dataset
    ↑ dataset_ref y comment_id
resolved config / manifest
    ↑ run_id, config_hash
```

Pasos del ejercicio:

1. Toma el `event_id` del resultado G-2.
2. Busca el mismo `event_id` en la entrada G-2 y en el resultado G-1.
3. Lee `used_context_unit_ids` o las citas `context_unit_id`.
4. Resuelve cada unidad a `comment_id` mediante el mapa de unidades.
5. Confirma que esos comentarios pertenecen al inventario completo del mismo evento.
6. Usa `trigger_time`, `window_start` y `window_end` para volver a `trigger_comment_map.csv`.
7. Comprueba `trigger_time` contra el trigger completado y la observación de señal.
8. Resuelve `dataset_ref`, `run_id` y `config_hash` en el manifiesto disponible.

Límite actual: los stages retrospectivos históricos no mantienen necesariamente un único `config_hash` global a través de toda la cadena. Si una referencia no aparece en el artefacto concreto, no la inventes. Marca ese salto como inspección del manifiesto del stage.

### Ejercicio B. Ruta diaria

Empieza por un payload seleccionado. Un conjunto conservado puede incluir `daily_event_id=dfe_04585f993970`, `cycle_id=cyc_30e049ebfc26` y unidades `dctx_*`. Usa siempre los valores de tu ejecución.

```text
selected RAG payload
    ↑ daily_rag_event_id, selection_run_id
daily consumer payload
    ↑ daily_event_id, context_unit_ids
daily context unit map
    ↑ context_unit_id, comment_id
daily_event_comment_inventory.csv
    ↑ is_alert_evidence, is_validation_context
daily event
    ↑ daily_event_id, cycle_id, signal_name
cycle signal row
    ↑ cycle_id, data_cutoff_utc, source artifact hashes
cycle manifest / inventory
    ↑ comment_id, is_new_in_cycle, is_active_in_window
prepared dataset
    ↑ dataset_ref, comment_id
run manifests
    ↑ run_id, config_hash, resolved_config
```

Pasos del ejercicio:

1. Lee `selected_context_unit_ids` y `daily_event_id` del payload final.
2. Resuelve cada `dctx_*` a sus `comment_id`.
3. Comprueba en el inventario si cada comentario era alerta, contexto o ambos.
4. Usa `daily_event_id` para localizar `cycle_id` en el evento del baseline.
5. Busca el ciclo en `cycle_signal_series.jsonl` y comprueba señal, valor y cutoff.
6. Busca cada `comment_id` en el inventario cíclico y en el dataset preparado.
7. Abre los manifiestos del runner cíclico y del runner diario RAG. Comprueba sus propios `run_id`, `config_hash` y `resolved_config`.

Los IDs de stage, por ejemplo `drun_*`, `dragconsumer_*` o `dragselect_*`, identifican transformaciones diarias particulares. No reemplazan el `run_id` de sus manifiestos.

## 24. Qué garantiza cada test esencial

No estudies todos los tests al principio. Usa este conjunto como especificación ejecutable de las fronteras principales.

### Foundational

| Test | Qué demuestra | Qué NO demuestra |
|---|---|---|
| [test_cleaning_pipeline_behavior.py](../tests/test_cleaning_pipeline_behavior.py) | Cleaning conserva el contrato de salida y aplica normalización y filtros esperados. | Que la adquisición sea completa o que la muestra sea representativa. |
| [test_activity_signal_contracts.py](../tests/test_activity_signal_contracts.py) | La definición y la observación tienen identidad temporal explícita, validación e inmutabilidad. | Que una ruta general despache todas las señales posibles. |
| [test_activity_signal_semantics.py](../tests/test_activity_signal_semantics.py) | La señal XIAO conserva ticks y fronteras; la señal diaria respeta días locales y cortes causales. | Que ambas señales sean la misma o usen el mismo detector. |
| [test_detection_result_contract.py](../tests/test_detection_result_contract.py) | `DetectionResult` es neutral, inmutable y mantiene metadatos específicos fuera de los campos comunes. | Que el resultado se persista o se promueva en un runner. |
| [test_event_candidate_contract.py](../tests/test_event_candidate_contract.py) | Solo un resultado disparado y consistente puede promoverse con linaje y ventana causal. | Que `EventCandidate` sea el handoff activo hacia RAG. |
| [test_daily_frequency_baseline.py](../tests/test_daily_frequency_baseline.py) | El baseline aplica warmup, umbrales, dirección y cooldown de manera determinista. | Que los parámetros estén calibrados científicamente. |

### End-to-end boundary

| Test | Qué demuestra | Qué NO demuestra |
|---|---|---|
| [test_cyclic_pipeline_entrypoint.py](../tests/test_cyclic_pipeline_entrypoint.py) | El runner cíclico conecta seis stages, escribe manifiesto y mantiene `future_leak_count==0`. | Que el conector cíclico ejecute XIAO. Espera cero eventos y estado preparado. |
| [test_daily_rag_pipeline_entrypoint.py](../tests/test_daily_rag_pipeline_entrypoint.py) | Sidecars, consumer y selector diarios se conectan y conservan identidades de stage. | Que la ruta diaria ejecute G-1 o G-2. |
| [test_xiao_replay_compatibility.py](../tests/test_xiao_replay_compatibility.py) | Replay ordena y finaliza; XIAO mantiene paridad entre entrada por evento y por observación. | Que `DetectionResult` se persista o alimente evidencia. |
| [test_daily_rag_sidecars.py](../tests/test_daily_rag_sidecars.py) | Se separan alert evidence y validation context, y se valida causalidad. | Que el texto seleccionado sea semánticamente relevante. |
| [test_daily_rag_context_selection.py](../tests/test_daily_rag_context_selection.py) | La selección prioriza alerta, respeta presupuesto y registra omisiones. | Que exista ranking semántico o una llamada a modelo. |
| [test_rag_generation_g2_hierarchical.py](../tests/test_rag_generation_g2_hierarchical.py) | Orden determinista, aislamiento de citas por video y dry-run sin red ni escritura. | Que las APIs externas respondan o que el juicio generativo sea correcto. |

### Legacy reference

| Test | Qué demuestra | Qué NO demuestra |
|---|---|---|
| [test_prepared_replay_behavior.py](../tests/test_prepared_replay_behavior.py) | El replay preparado conserva el contrato del snapshot diagnóstico. | Que ese snapshot sea la señal XIAO o evidencia RAG. |
| [test_local_files_storage_behavior.py](../tests/test_local_files_storage_behavior.py) | La fachada local lee tablas y conserva el contrato de persistencia. | Que una consulta real a YouTube funcione. |
| [test_current_pipeline_profile.py](../tests/test_current_pipeline_profile.py) | Los perfiles de compatibilidad vigentes resuelven parámetros, rutas e identidad estable. | Que esos valores sean una arquitectura permanente o calibrada. |
| [test_non_daily_rag_stage_scripts.py](../tests/test_non_daily_rag_stage_scripts.py) | Los scripts retrospectivos delegan en los resolvers comunes esperados. | Que ejecuten toda la transformación o contacten APIs. |

## 25. Laboratorio de verificación personal

Todos los laboratorios parten de la raíz del repositorio. Ninguno requiere una API externa. Los laboratorios D y E escriben solo bajo `/tmp`.

### Laboratorio A. Configuración

Ejecuta:

```bash
.venv/bin/python -m unittest \
  tests.test_current_pipeline_profile \
  tests.test_traceability_policy
```

Comprueba:

- salida final `OK`;
- el perfil cíclico resuelve una identidad estable;
- `run_mode` y `trace_level` forman parte de `resolved_config` y `config_hash`;
- una política no implementada falla antes de escribir artefactos.

**Prueba de comprensión:** explica por qué cambiar solo `run_id` cambia la identidad resuelta, pero no debe sobrescribir los IDs propios de los stages diarios.

### Laboratorio B. Señal

Recrea el ejemplo sintético:

```bash
.venv/bin/python - <<'PY'
from youtube_pipeline.activity_signals import (
    EventWindowCommentCountSignal,
    event_window_comment_count_definition,
)

signal = EventWindowCommentCountSignal(
    definition=event_window_comment_count_definition(
        window="120s",
        cadence="30s",
        time_basis="event_time_utc",
    ),
    timestamp_column="event_time_utc",
)

for comment_id, event_time in [
    ("c1", "2026-01-01T00:00:00Z"),
    ("c2", "2026-01-01T00:00:10Z"),
    ("c3", "2026-01-01T00:00:30Z"),
]:
    observations = signal.on_event(
        {"comment_id": comment_id, "event_time_utc": event_time, "text": comment_id}
    )
    for observation in observations:
        print(
            observation.observation_time_utc.isoformat(),
            observation.value,
            observation.support_count,
            observation.quality,
        )
PY
```

Salida esperada:

```text
2026-01-01T00:00:00+00:00 1 1 passed
2026-01-01T00:00:30+00:00 3 3 passed
```

**Prueba de comprensión:** cambia `c3` a `00:00:31`. Explica por qué el tick `00:00:30` se emite antes de incorporar `c3`.

### Laboratorio C. XIAO

Pasa las mismas observaciones al detector:

```bash
.venv/bin/python - <<'PY'
from youtube_pipeline.activity_signals import (
    EventWindowCommentCountSignal,
    event_window_comment_count_definition,
)
from youtube_pipeline.detectors import XiaoEMATriggerDetector

signal = EventWindowCommentCountSignal(
    definition=event_window_comment_count_definition(
        window="120s", cadence="30s", time_basis="event_time_utc"
    ),
    timestamp_column="event_time_utc",
)
detector = XiaoEMATriggerDetector(log_fn=lambda _message: None)

for comment_id, event_time in [
    ("c1", "2026-01-01T00:00:00Z"),
    ("c2", "2026-01-01T00:00:10Z"),
    ("c3", "2026-01-01T00:00:30Z"),
]:
    for observation in signal.on_event(
        {"comment_id": comment_id, "event_time_utc": event_time, "text": comment_id}
    ):
        result = detector.on_observation(observation)
        print(
            result.observation_time_utc.isoformat(),
            result.signal_id,
            result.triggered,
            result.quality,
            round(result.score or 0.0, 6),
            dict(result.detector_metadata),
        )
PY
```

Comprueba:

- dos instancias de `DetectionResult`;
- `signal_id=comment_count_event_window_120s_step_30s`;
- `quality=passed` en ambos;
- scores aproximados `1.0` y `1.512`;
- `triggered=False` por warmup y volumen.

**Prueba de comprensión:** identifica qué campos proceden de la señal y cuáles decide el detector.

### Laboratorio D. Pipeline cíclico

Ejecuta exactamente:

```bash
.venv/bin/python scripts/run_cyclic_pipeline.py \
  --config configs/compatibility/cyclic_current.json \
  --output-root /tmp/study-cyclic \
  --dry-run
```

La salida estándar es un resumen JSON. Comprueba:

- `execution_mode` igual a `dry_run`;
- seis stages en `stages`;
- `future_leak_count == 0` en las validaciones temporales;
- el conector de detección con `status == "prepared_not_executed"`;
- ausencia de eventos XIAO ejecutados;
- `run_manifest` bajo `/tmp/study-cyclic`.

**Prueba de comprensión:** explica por qué una configuración XIAO presente en `resolved_config` no prueba que el conector la haya ejecutado.

### Laboratorio E. RAG diario

Este laboratorio necesita que existan los artefactos cíclicos de entrada declarados por `daily_rag_current.json`. `--output-root` relocaliza las tres salidas de RAG diario y sus enlaces internos, pero conserva esas entradas fuente. El laboratorio D es útil para estudiar el runner cíclico, pero su salida `/tmp/study-cyclic` no reemplaza automáticamente las rutas fuente del perfil diario. Ejecuta:

```bash
.venv/bin/python scripts/run_daily_rag_pipeline.py \
  --config configs/compatibility/daily_rag_current.json \
  --output-root /tmp/study-daily-rag \
  --dry-run
```

Comprueba en el resumen JSON y en `/tmp/study-daily-rag`:

- stages `sidecars`, `consumer` y `context_selection`;
- `daily_event_comment_inventory.csv` con ambas banderas temporales;
- `daily_rag_selected_context_payloads.jsonl` con unidades seleccionadas;
- `daily_context_selection_omissions.csv` con razones para unidades no elegidas;
- `future_leak_count == 0`;
- banderas `run_llm`, `run_g1` y `run_g2` desactivadas.

Nota operativa: los perfiles resuelven entradas de cada stage de forma conjunta cuando se aplica `--output-root`. Si el dataset Prepared de entrada no existe, el comando falla de forma explícita. Eso es una precondición local, no una razón para sustituirlo con una API externa.

**Prueba de comprensión:** elige un `dctx_*` omitido y resuélvelo hasta sus `comment_id`. Confirma que los comentarios siguen en el inventario de evidencia.

## 26. Preguntas finales de dominio

Responde sin mirar la clave. Una respuesta suficiente debe nombrar el componente responsable y una forma de comprobarla.

1. ¿Por qué `event_time_utc` no permite afirmar que tenemos ingestión online real?
2. ¿Por qué `comment_count` no identifica por sí solo una señal?
3. ¿Quién decide `quality` y quién debe conservarla?
4. ¿Qué diferencia hay entre `value` y `support_count`?
5. ¿Qué diferencia hay entre `DetectionResult` y `completed_trigger`?
6. ¿Por qué `triggered=true` no confirma un evento real?
7. ¿Qué añade `EventCandidate` y por qué no contiene comentarios?
8. ¿Es `EventCandidate` el handoff general actual hacia RAG?
9. ¿Quién decide qué comentarios pertenecen a la evidencia retrospectiva?
10. ¿Por qué los comentarios acumulados durante cooldown no son el inventario definitivo?
11. ¿Qué diferencia hay entre evidencia completa e input RAG seleccionado?
12. ¿Cómo se resuelve un `context_unit_id` hasta comentarios originales?
13. ¿Por qué G-1 y G-2 no forman parte del detector?
14. ¿Qué diferencia existe entre G-1 y G-2?
15. ¿Por qué la señal diagnóstica de 20 minutos no es la señal XIAO?
16. ¿Qué significan `new`, `active` y `exited` en un ciclo diario?
17. ¿Por qué el conector cíclico no debe presentarse como XIAO ejecutado?
18. ¿Por qué el baseline diario no debe presentarse como `DetectionResult` actualmente?
19. ¿Cómo puede un comentario pertenecer a alert evidence y validation context a la vez?
20. ¿Dónde termina la ruta diaria actual y qué prueba esa frontera?

### Clave de respuestas

1. Se deriva de la publicación en YouTube. No hay una marca durable separada de cuándo el proyecto recibió el comentario.
2. Falta especificar fuente, alcance, unidad, ventana, cadence, base temporal, zona e intervalo. Eso lo aporta `ActivitySignalDefinition`.
3. El productor de señal calcula `quality`. XIAO la copia en `DetectionResult`; no la reinterpreta.
4. `value` es el resultado de la métrica. `support_count` indica cuántos registros sostienen esa observación. Pueden diferir para otras métricas.
5. `DetectionResult` es la decisión neutral por observación. `completed_trigger` es el estado histórico cerrado que XIAO guarda después del cooldown y que usa el runtime retrospectivo.
6. Solo afirma que la regla y sus parámetros se cumplieron. La interpretación necesita evidencia y validación posterior.
7. Añade identidad, ventana causal y linaje. No contiene comentarios porque la pertenencia a evidencia es autoridad de otra capa.
8. No. El contrato existe y está probado, pero evidencia retrospectiva usa `completed_triggers` y la diaria usa eventos del baseline.
9. `build_trigger_comment_map` y el ensamblado de sidecars, usando el dataset limpio y la ventana pre-trigger inclusiva.
10. Son comentarios recogidos después de abrir el trigger durante el lock, con identidad limitada. No representan la ventana pre-trigger ni el inventario auditable completo.
11. La evidencia conserva todos los comentarios asociados. El input RAG puede usar solo unidades que caben en el presupuesto, sin borrar la pertenencia de las omitidas.
12. Se busca en `context_unit_comment_map.csv` o `daily_context_unit_comment_map.csv`, donde cada unidad apunta a uno o más `comment_id`.
13. El detector decide sobre una serie numérica. G-1 y G-2 interpretan evidencia interna o externa y producen validaciones posteriores.
14. G-1 evalúa lo observable dentro de la comunidad de YouTube. G-2 contrasta con evidencia externa; la variante jerárquica lo hace por video antes de sintetizar.
15. El snapshot de monitoring resume 20 minutos y varias métricas. XIAO consume conteos en ventanas de 120 segundos emitidos cada 30 segundos.
16. `new` apareció en el ciclo, `active` sigue dentro de la ventana causal y `exited` estaba activo pero salió de ella.
17. El runner usa modo `detection_dry_run` y devuelve `prepared_not_executed`. Prepara contratos, pero no llama la detección XIAO del ciclo.
18. El baseline produce su propio `daily_event_id` desde filas de señal diaria. El runtime no instancia `DetectionResult` ni `EventCandidate` en esa ruta.
19. Un comentario nuevo del ciclo también está activo en la ventana. Entonces ambas banderas son verdaderas, aunque su rol principal sea alerta.
20. Termina en selección determinista de contexto. `test_daily_rag_pipeline_entrypoint` conecta sidecars, consumer y selector, y mantiene desactivadas las etapas generativas.

## 27. Plan concreto de estudio en nueve sesiones

Cada sesión debe terminar con una explicación propia, no solo con tests verdes.

### Sesión 1. Reconocer una ejecución

- **Objetivo:** distinguir configuración solicitada, configuración resuelta, identidad y hash.
- **Secciones:** 1 a 4.
- **Archivos:** `cyclic_current.json`, `daily_rag_current.json`, `configuration/models.py`, `configuration/loading.py`, `run_manifest.py`.
- **Tests:** `test_current_pipeline_profile`, `test_traceability_policy`.
- **Ejercicio:** toma un perfil y señala qué sección elige entrada, detector y salida.
- **Criterio para avanzar:** puedes explicar `run_id`, `resolved_config`, `config_hash` e ID de stage sin mezclarlos.

### Sesión 2. Seguir un comentario hasta Prepared

- **Objetivo:** separar campos fuente, normalizados y derivados.
- **Secciones:** 5 y 6.
- **Archivos:** `data_extraction.py`, `storage.py`, `cleaning.py`.
- **Tests:** `test_local_files_storage_behavior`, `test_cleaning_pipeline_behavior`.
- **Ejercicio:** dibuja el linaje de `comment_id`, `published_at`, `event_time_utc` y `text_clean`.
- **Criterio para avanzar:** puedes decir qué componente tiene autoridad sobre cada campo.

### Sesión 3. Entender tiempo y replay

- **Objetivo:** explicar causalidad simulada y distinguir replay de snapshot.
- **Secciones:** 6 y 7.
- **Archivos:** `replay.py`, `prepared_replay.py`, `monitoring.py`, `cyclic_ingestion.py`.
- **Tests:** `test_prepared_replay_behavior`, clase `ReplayCompatibilityTests`.
- **Ejercicio:** con cinco timestamps desordenados, ordena cuáles serían visibles antes de un cutoff.
- **Criterio para avanzar:** puedes explicar `event_time_utc`, cutoff, finalización y snapshot de 20 minutos.

### Sesión 4. Construir la señal

- **Objetivo:** pasar de comentarios a observaciones numéricas.
- **Secciones:** 8 y laboratorio B.
- **Archivos:** `activity_signals.py`.
- **Tests:** `test_activity_signal_contracts`, clase `XiaoReferenceSignalSemanticsTests`.
- **Ejercicio:** ejecuta el ejemplo c1-c3 y cambia un timestamp de frontera.
- **Criterio para avanzar:** puedes calcular ventanas, ticks, valor, soporte y calidad a mano.

### Sesión 5. Entender XIAO y el split retrospectivo

- **Objetivo:** separar decisión neutral, trigger histórico y candidato neutral.
- **Secciones:** 9 a 12 y laboratorio C.
- **Archivos:** `detectors.py`, `activity_detection.py`, `event_candidates.py`, `run_local_csv_retrospective.py`.
- **Tests:** `test_detection_result_contract`, `test_xiao_replay_compatibility`, `test_event_candidate_contract`.
- **Ejercicio:** dibuja las dos salidas de `on_observation` y marca cuál usa el runner.
- **Criterio para avanzar:** puedes explicar por qué `DetectionResult → EventCandidate → RAG` no es el handoff general activo.

### Sesión 6. Reconstruir la ruta diaria

- **Objetivo:** entender ciclos, estado y baseline.
- **Secciones:** 17 a 19 y laboratorio D.
- **Archivos:** `cyclic_ingestion.py`, `cyclic_stateful_adapter.py`, `cyclic_daily_signals.py`, `daily_frequency_baseline.py`, `cyclic_pipeline.py`.
- **Tests:** `test_cyclic_pipeline_entrypoint`, `test_daily_frequency_baseline`.
- **Ejercicio:** crea una tabla de tres ciclos con `new`, `active`, `exited`, señal y baseline.
- **Criterio para avanzar:** puedes explicar por qué el detector diario no es XIAO y por qué el conector queda preparado.

### Sesión 7. Construir evidencia

- **Objetivo:** distinguir pertenencia a evidencia en ambas rutas.
- **Secciones:** 13, 14 y 20.
- **Archivos:** `run_local_csv_retrospective.py`, `rag_sidecars.py`, `daily_rag_sidecars.py`.
- **Tests:** `test_daily_rag_sidecars` y el caso de trigger completado de `test_xiao_replay_compatibility`.
- **Ejercicio:** clasifica cinco comentarios en ventana pre-trigger, alerta diaria y contexto diario.
- **Criterio para avanzar:** puedes defender quién decide pertenencia y por qué el detector no lo hace.

### Sesión 8. Preparar y seleccionar contexto RAG

- **Objetivo:** resolver unidades a comentarios y explicar presupuesto y omisiones.
- **Secciones:** 14, 21, 22 y laboratorio E.
- **Archivos:** `rag_consumer.py`, `daily_rag_consumer.py`, `daily_rag_context_selection.py`, `daily_rag_pipeline.py`.
- **Tests:** `test_daily_rag_pipeline_entrypoint`, `test_daily_rag_context_selection`.
- **Ejercicio:** toma una unidad seleccionada y otra omitida y resuelve ambas hasta el inventario.
- **Criterio para avanzar:** puedes explicar por qué selección no cambia evidencia y dónde termina la ruta diaria.

### Sesión 9. Validar y reconstruir trazabilidad

- **Objetivo:** seguir un resultado retrospectivo y un payload diario hasta su configuración.
- **Secciones:** 15, 16, 23, 24 y 26.
- **Archivos:** `rag_generation_g1.py`, `rag_generation_g2.py`, `rag_generation_g2_hierarchical.py`, `run_manifest.py`.
- **Tests:** `test_rag_generation_g2_hierarchical`, `test_non_daily_rag_stage_scripts`.
- **Ejercicio:** completa los dos ejercicios de trazabilidad y responde las 20 preguntas.
- **Criterio para avanzar:** obtienes al menos 17 respuestas correctas y puedes justificar cada salto con un ID o una referencia real.

## 28. Qué NO estudiar todavía

Para construir el modelo mental inicial no necesitas:

- notebooks;
- A9;
- auditorías históricas;
- wrappers secundarios;
- el PoC antiguo;
- Page-Hinkley;
- dependencias internas de librerías;
- todos los tests del repositorio.

Estos elementos pueden estudiarse después. No son necesarios para explicar la ruta activa desde entrada hasta validación.

### Qué NO hace todavía el pipeline

- La ruta diaria no ejecuta G-1 ni G-2.
- El conector cíclico integrado no ejecuta XIAO. Deja la entrada `prepared_not_executed`.
- `DetectionResult → EventCandidate → RAG` no es un handoff general activo.
- La ruta retrospectiva sigue pasando `completed_triggers` a la evidencia.
- `event_time_utc` no demuestra una hora real de ingestión online.

Cuando puedas explicar estas cinco ausencias sin confundirlas con errores del estudio, habrás reconstruido el alcance actual del sistema.
