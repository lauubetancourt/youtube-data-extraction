## 1. Resumen Del Estado Actual Del Pipeline

El pipeline está concentrado en el paquete [youtube_pipeline](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/run_pipeline.py:1>) y se ejecuta por CLI con comandos `extract`, `storage`, `clean`, `playback` y `all`.

Fases identificadas:

- **Extracción:** [data_extraction.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/data_extraction.py:37>) define `ExtractionConfig`, consulta YouTube API, filtra videos, extrae comentarios y guarda metadata de corrida.
- **Persistencia / capas de datos:** [storage.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/storage.py:102>) escribe `bronze` JSONL y `silver` Parquet particionado.
- **Preprocesamiento:** [cleaning.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/cleaning.py:213>) normaliza texto, genera señales textuales y filtra spam/duplicados.
- **Simulación:** [stream_playback.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/stream_playback.py:272>) reproduce eventos en orden temporal con `Streamz`.
- **Monitoreo:** [stream_playback.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/stream_playback.py:357>) construye snapshots con actividad y polarización.
- **Detección:** [XiaoEMATriggerDetector](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/stream_playback.py:52>) detecta triggers EMA.
- **RAG futuro:** no está implementado en el pipeline principal, pero hay contratos de ejemplo en `.agents/examples/structured-rag-pdf/data/`.

Entradas/salidas visibles:

- Legacy CSV: `data/videos_preliminares.csv`, `data/comments.csv`.
- Bronze: `data/bronze/videos/*.jsonl`, `data/bronze/comments/*.jsonl`, `data/bronze/runs/*.json`.
- Silver: `data/silver/videos/`, `data/silver/comments/`.
- Gold: `data/gold/clean_comments.parquet`, `data/gold/snapshots_log3_variant.csv`.
- Experimentos: `experiments/xiao/*/log_*` con `snapshots.csv`, `trigger_log.txt`, `summary.md`, `trigger_comment_map.csv`.

Observación inicial: la base funcional existe y es razonable para prototipo; la mayor deuda está en contratos explícitos, trazabilidad formal, separación entre simulación/monitoreo/detección y preparación de artefactos para RAG. Adicionalmente, falta el anclaje metodológico fundacional contra el anteproyecto: no existe una definición operativa documentada de evento ni criterios de éxito del prototipo derivados del problema de investigación (ver Etapa -1 del plan).

## 2. Mapa Entre Fases Del Pipeline Y Skills CRISP-DM

| Fase del pipeline | Skill(s) relacionada(s) | Evidencia encontrada | Alineación | Brecha identificada | Riesgo si no se corrige |
|---|---|---|---|---|---|
| **Alineación con anteproyecto** | `crisp-dm-problem-framing` | Anteproyecto disponible en `.agents/examples/anteproyecto.pdf`; no hay todavía artefacto formal que traduzca sus objetivos a contrato del pipeline | Bajo | No existe definición operativa de evento ni mapa objetivo-señal-decisión-evidencia derivados del anteproyecto | Sin anclaje metodológico, la arquitectura puede optimizar componentes que no responden al problema de investigación |
| **Comprensión de datos** | `data-understanding-audit` | Sin perfil descriptivo formal del corpus; cobertura temporal no documentada sistematicamente | Bajo | Falta exploración estructurada de distribuciones por campo, patrones preliminares y riesgos de preparación | Brechas reales del corpus pueden quedar sin detectar y ser interpretadas incorrectamente como eventos |
| Extracción | `data-source-inventory-lineage`, `dataset-selection-sampling` | `ExtractionConfig`, filtros, metadata de corrida, legacy CSV, bronze/silver | Media | Filtros y fuentes existen, pero falta inventario formal de datasets y criterios metodológicos de selección | Difícil justificar corpus y reproducir selección |
| Preprocesamiento | `data-quality-reporting`, `text-preprocessing-spec`, `data-integration-formatting` | Limpieza textual, spam, duplicados, timestamps, `gold` parquet | Media-alta | Hay reglas en código, pero falta especificación documental y reporte de calidad por corrida | Limpieza difícil de auditar académicamente |
| Simulación en línea | `temporal-partitioning-validation-design`, `online-stream-simulation-design` | `read_dataset_for_playback`, `replay_events`, `start/end`, orden temporal | Media | No hay contrato formal de simulación ni separación limpia del decisor | Fuga conceptual entre reproducción y detección |
| Monitoreo | `feature-construction-aggregation`, `signal-monitoring-spec` | Snapshots con `activity.*` y `polarization.*` | Media | Señales existen, pero catálogo/fichas no están formalizados | Interpretación débil de señales |
| Detección | `event-detection-decision-criteria` | `XiaoEMATriggerDetector`, logs, experimentos Xiao | Media | Decisor acoplado a playback y sin contrato común | Difícil comparar decisores sin tocar simulación |
| Validación RAG futura | `rag-validation-readiness` | Ejemplo RAG con `queries_df`, `auditoria_df`, `trigger_comment_map` | Baja-media | Pipeline principal no emite todavía artefacto RAG-ready | Integración posterior puede requerir reconstrucciones frágiles |
| Documentación/reproducibilidad | `experiment-traceability-reporting` | `data/bronze/runs`, scripts de auditoría, experimentos | Media | Reportes están dispersos y no hay manifiesto único por experimento | Resultados difíciles de rastrear extremo a extremo |

## 3. Diagnóstico Arquitectónico

**Separación de responsabilidades:** aceptable en extracción, storage y cleaning. Más débil en simulación/detección: [run_playback](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/run_pipeline.py:124>) lee datos, crea `Stream`, instancia el decisor concreto, conecta snapshots, reproduce eventos y escribe CSV.

**Acoplamiento entre fases:** el acoplamiento más fuerte está en [run_pipeline.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/run_pipeline.py:150>), donde se instancia directamente `XiaoEMATriggerDetector`. El módulo [stream_playback.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/stream_playback.py:52>) mezcla reproducción temporal, monitoreo por ventana y decisor.

**Claridad de contratos:** los formatos existen, pero están implícitos. Por ejemplo, snapshots se aplanan con `pd.json_normalize(..., sep=".")` y se escriben como CSV en [run_pipeline.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/run_pipeline.py:180>). Falta declarar columnas esperadas por fase.

**Configuración:** existe CLI suficiente para prototipo. Falta una configuración explícita de "decisor" y una forma de cargar parámetros sin amarrarlos al CLI.

**Trazabilidad:** buena base en `bronze/runs` y experimentos, pero incompleta para detección. El playback principal solo persiste snapshots, no los triggers ni su mapa comentario-evento.

**Reproducibilidad:** buena en extracción/storage por metadata; media en experimentos porque hay logs y summaries, pero no manifiesto único que una dataset, config, detector, salida y scripts usados.

**Manejo de artefactos:** hay capas `bronze/silver/gold`, lo cual alinea bien con preparación de datos. Los artefactos de validación y experimentos aún viven fuera del contrato principal.

**Preparación para RAG:** hay señales prometedoras: `trigger_comment_map.csv` en experimentos y ejemplo RAG. Falta que el pipeline principal produzca candidatos de evento con identificadores, comentarios origen, ventanas, señales y queries sugeridas.

## 4. Diagnóstico Específico De La Fase De Simulación

**Ubicación del decisor:** `XiaoEMATriggerDetector` vive en [stream_playback.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/stream_playback.py:52>) y se instancia directamente en [run_playback](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/run_pipeline.py:150>).

**Responsabilidades actuales del decisor:**

- Mantiene buffer temporal.
- Calcula EMA rápida/lenta.
- Aplica warm-up, umbral, volumen mínimo y cooldown.
- Abre/cierra triggers.
- Loguea detecciones.
- Guarda `completed_triggers`.
- Durante lock, recolecta comentarios, pero solo conserva timestamp y texto, no `comment_id`, `video_id` ni señales completas.

**Nivel de acoplamiento:** medio-alto. La simulación acepta `event_hooks`, lo cual es una buena puerta de modularidad, pero la CLI y `run_playback` conocen el decisor concreto y sus parámetros.

**Problemas arquitectónicos:**

- No hay interfaz común para decisores.
- No hay factory/registry para seleccionar decisor.
- No hay salida persistida de triggers en playback principal.
- El orden actual importa: `replay_events` llama hooks antes de `source.emit` en [stream_playback.py](</Users/lau/Desktop/Trabajo de Grado/youtube-data-extraction/youtube_pipeline/stream_playback.py:314>); cualquier refactor debe conservarlo.
- Los parámetros de experimentos no están centralizados; por ejemplo el CLI default usa `trigger_min_volume=46`, mientras scripts/experimentos usan 15.

**Propuesta conceptual para modularizar:**

Crear un contrato común tipo `DecisionHook`/`EventDecider` con estas responsabilidades mínimas:

- `name`: identificador del decisor.
- `config`: parámetros serializables.
- `on_event(event)`: consume un evento en orden temporal.
- `finalize(final_ts)`: cierra estado pendiente.
- `get_decisions()` o `completed_triggers`: expone decisiones normalizadas.
- Opcional: `get_logs()` para auditoría.

**Switch entre decisores:**

- Opción A: configuración CLI `--decision xiao_ema` + `--decision-config`.
- Opción B: inyección de dependencia en `run_playback(decider_factory=...)`.
- Opción C: registry interno `{ "xiao_ema": XiaoEMATriggerDetector }`.

Recomendación: combinar B para arquitectura/testabilidad y A para uso CLI. El decisor actual debe quedar como default `xiao_ema`, con mismos parámetros y mismo orden de ejecución.

**Riesgos del cambio:**

- Cambiar timestamps de trigger por alterar orden hook/stream.
- Cambiar resultados por defaults inconsistentes.
- Romper scripts que importan directamente `XiaoEMATriggerDetector`.
- Duplicar o perder triggers si `finalize` cambia.

Mitigación: pruebas de regresión comparando snapshots, logs y triggers actuales antes/después.

## 5. Diagnóstico De Preparación Para RAG

**Artefactos útiles ya existentes:**

- `experiments/xiao/media/log_3/trigger_comment_map.csv` contiene `trigger_time`, ventana, volumen, fuerza, `video_id`, `title`, `channel_title`, `author_id`, `comment_id`, `text`.
- `summary.md` resume triggers, videos involucrados y primeros comentarios.
- `trigger_log.txt` conserva configuración del detector y triggers.
- `.agents/examples/structured-rag-pdf/data/queries_df.csv` usa `trigger_time`, `video_id`, `title`, `news_api_query`.
- `.agents/examples/structured-rag-pdf/data/auditoria_df.csv` añade `n_noticias` y veredicto.

**Artefactos faltantes en pipeline principal:**

- `event_candidates.csv/jsonl`.
- `event_comment_map.csv`.
- `event_signal_snapshot.csv`.
- `event_validation_queries.csv`.
- Manifiesto por experimento con dataset, configuración, detector y rutas.

**Metadatos necesarios:**

- `event_id`, `detector_name`, `detector_config`, `trigger_time`, `window_start`, `window_end`, `cooldown_until`.
- `trigger_volume`, `trigger_strength`, señales de actividad/polarización.
- `video_id`, `comment_id`, `event_time_utc`, `text`, idealmente `text_clean`, `title`, `channel_title`.
- Ruta/version del dataset de entrada y metadata de extracción.

**Contrato RAG futuro recomendado, sin implementarlo aún:**

- Entrada 1: eventos candidatos.
- Entrada 2: mapa evento-comentario.
- Entrada 3: queries sugeridas por evento/video (el campo `news_api_query` ya existe en el ejemplo; debe quedar como campo del contrato del pipeline principal, no solo en el ejemplo).
- Salida futura: veredicto, evidencia recuperada, fuentes, razonamiento, incertidumbre.

Riesgo actual: si solo se conservan snapshots agregados, luego será difícil explicar por qué un evento fue detectado y qué comentarios lo originaron.

## 6. Revisión De Contratos De Entrada Y Salida

| Fase | Entrada actual | Salida actual | ¿Debe conservarse? | ¿Requiere cambio? | Justificación | Impacto potencial |
|---|---|---|---|---|---|---|
| Extracción | `.env`, CLI/config JSON, YouTube API | legacy CSV, bronze JSONL, silver parquet, run metadata | Sí | No | Ya sostiene reproducibilidad básica | Bajo |
| Storage | videos/comments CSV o parquet | `data/bronze/*`, `data/silver/*` | Sí | No | Buen contrato por capas | Bajo |
| Preprocesamiento | `data/silver/comments` o CSV/parquet | `data/gold/clean_comments.parquet` | Sí | No | Columnas actuales alimentan playback y auditorías | Bajo |
| Simulación | gold clean + `event_time_utc` | emisión Streamz + snapshots | Sí | No funcional; sí documentar | El contrato temporal está implícito | Bajo |
| Monitoreo | eventos simulados | snapshots CSV con `activity.*`, `polarization.*` | Sí | No | Ya es compatible con scripts | Bajo |
| Detección | eventos por hook | triggers en memoria/logs; experimentos externos | Sí, pero incompleto | Agregar artefactos opcionales | Para RAG y auditoría se necesita trazabilidad evento-comentario | Medio |
| RAG futuro | no aplica en core | ejemplos CSV en `.agents/examples` | Sí como referencia | No todavía | No se debe implementar RAG aún | Bajo |

**Nota metodológica — contrato temporal (asignado a Etapa 3):** La decisión de trabajo es usar segundos como unidad numérica y UTC como zona horaria interna. `event_time_utc` debe ser el campo temporal canónico de comentarios. `event_time_unix_s` y `published_at_unix_s` quedan como nombres numéricos canónicos para nuevos artefactos. `event_time_unix_ms` y `published_at_unix_ms` deben conservarse como campos legacy mientras existan datasets previos que dependan de esos nombres.

## 7. Plan De Trabajo Propuesto

### Resumen De Etapas

| Etapa | Objetivo | Skills invocadas | Tipo | Riesgo | Prioridad | ¿Altera comportamiento? |
|---|---|---|---|---|---|---|
| -1 | Alineación con el problema de investigación y definición operativa de evento | `crisp-dm-problem-framing`, `russellian-clear-writing` | Documentación metodológica | Bajo | Bloqueante | No |
| 0 | Auditoría y documentación | `data-understanding-audit`, `data-source-inventory-lineage`, `experiment-traceability-reporting` | Documentación | Bajo | Muy alta | No |
| 1 | Organización arquitectónica mínima | `data-integration-formatting`, `dataset-selection-sampling`, `data-quality-reporting`, `text-preprocessing-spec` | Arquitectura/documentación | Bajo-medio | Alta | No |
| 2 | Modularización del decisor de simulación | `event-detection-decision-criteria`, `online-stream-simulation-design`, `signal-monitoring-spec` | Modularización | Medio | Alta | No debería |
| 3 | Fortalecimiento de trazabilidad y contratos | `experiment-traceability-reporting`, `feature-construction-aggregation`, `temporal-partitioning-validation-design` | Trazabilidad | Medio | Alta | No sobre resultados |
| 4 | Preparación para validación futura con RAG | `rag-validation-readiness` | Arquitectura/contratos | Bajo-medio | Media | No |
| 5 | Pruebas de regresión y verificación | `temporal-partitioning-validation-design`, `experiment-traceability-reporting` | Pruebas | Medio | Alta | No |

---

### Detalle Por Etapa

### Etapa -1: Alineación con el problema de investigación y definición operativa de evento

**Objetivo:** Alinear el pipeline con el problema, objetivos, alcance y criterios del anteproyecto antes de auditar arquitectura, contratos técnicos o módulos. Esta etapa invoca primero `crisp-dm-problem-framing` y usa `russellian-clear-writing` para redactar definiciones claras, sin mezclar afirmaciones, supuestos y límites.

**Fuente base:** `.agents/examples/anteproyecto.pdf`.

**Extracción del anteproyecto:**

- **Problema de investigación:** los enfoques de detección de eventos en redes sociales dependen en gran parte de volumen o ráfagas de actividad. El anteproyecto sostiene que el volumen por sí solo es insuficiente para detectar eventos socialmente relevantes, porque puede reaccionar al ruido o ignorar sucesos críticos con menor volumen pero alta tensión social. El vacío está en integrar medidas avanzadas de polarización con arquitecturas de detección en línea para YouTube.
- **Pregunta formulada:** cómo desarrollar un prototipo para detección en línea de eventos mediante señales de actividad y medidas de polarización con datos de YouTube.
- **Objetivo general:** desarrollar un prototipo de detección en línea de eventos que integre señales de actividad y medidas de polarización con datos de YouTube, y mostrar su utilidad mediante casos de uso.
- **Objetivos específicos:** revisar literatura; implementar pipeline reproducible de adquisición y preprocesamiento vía API de YouTube; construir señales de actividad y medidas de polarización; diseñar e implementar un decisor que combine ambas; documentar casos de uso con verificación basada en cronología pública.
- **Alcance del prototipo:** se limita a YouTube; usa datos generados por usuarios como visualizaciones, comentarios y reacciones; adopta detección en línea, no tiempo real estricto; excluye detección retrospectiva, prospectiva y dominio multiplataforma.
- **Definición de evento en el anteproyecto:** suceso de interés público y relevancia social que genera debate colectivo y respuesta social significativa. Operacionalmente, es un suceso emergente que produce anomalías detectables tanto en señales de actividad como en medidas de polarización.
- **Señales esperadas:** tasas de cambio de actividad por ventana, como comentarios por minuto, visualizaciones y reacciones cuando estén disponibles; medidas de polarización como Esteban-Ray, EMD y MEC; el sentimiento puede apoyar, pero no sustituye la polarización.
- **Criterios de éxito esperados:** pipeline reproducible; señales y medidas calculadas; decisor funcional que genera alarmas cuando combina filtro de actividad y criterio de polarización; casos de uso documentados y verificados contra cronología pública.
- **Restricciones relevantes:** uso de YouTube Data API; cuotas, latencias y disponibilidad de campos; foco en prototipo académico; ausencia de garantías de tiempo real duro; validación basada en evidencia pública, no en predicción futura.

**Definición operativa de evento para este pipeline:**

Un evento es una alerta candidata sobre un suceso emergente de interés público que se manifiesta en YouTube dentro de una ventana temporal concreta. Para declararlo, el pipeline debe observar una anomalía de actividad y una señal de polarización compatible con cambio, división o consenso abrupto del discurso. La alerta debe conservar evidencia suficiente para ser revisada y, más adelante, validada contra cronología pública mediante RAG.

**Qué se considera evento dentro del sistema:**

- Un aumento anómalo de actividad en comentarios u otras interacciones disponibles.
- Una variación relevante en la distribución de posturas o señales de polarización.
- Una ventana temporal con comentarios trazables, videos asociados y señales que expliquen la alerta.
- Un caso que pueda formularse como hipótesis verificable contra evidencia pública.

**Qué no se considera evento dentro del sistema:**

- Un pico de volumen sin evidencia mínima de relevancia social o polarización.
- Un fenómeno viral puramente recreativo si no muestra tensión, división, consenso abrupto o vínculo verificable con un suceso de interés público.
- Una predicción de eventos futuros.
- Un hallazgo retrospectivo sin simulación de disponibilidad temporal.
- Una alerta que no pueda rastrearse hasta comentarios, ventana y señales.

**Evidencia mínima para declarar un evento candidato:**

- `trigger_time`, `window_start`, `window_end` y zona horaria UTC.
- Señal de actividad usada para activar o filtrar la ventana.
- Medida o proxy de polarización usado como criterio de relevancia.
- Comentarios incluidos en la ventana, no solo ejemplos.
- Identificadores de video, comentario y canal cuando estén disponibles.
- Configuración del decisor y parámetros de ventana.
- Consulta o pregunta inicial para verificación por cronología pública.

**Papel de las señales de actividad:** funcionan como filtro de anomalía de primer nivel. Detectan cambios de volumen o velocidad de interacción. No bastan por sí solas para declarar un evento socialmente relevante.

**Papel de las medidas de polarización:** funcionan como criterio de relevancia social. Deben ayudar a distinguir una simple ráfaga de actividad de un cambio en la distribución de opiniones, división o consenso abrupto.

**Papel de los comentarios de YouTube:** son la fuente textual primaria para construir señales, explicar la alerta y alimentar la validación futura. Deben conservarse con trazabilidad hacia ventana, video y trigger.

**Límites de esta definición:** es una definición operativa para un prototipo. No confirma por sí sola que el suceso ocurrió en el mundo real. No garantiza detección en tiempo real estricto. No generaliza fuera de YouTube sin nueva validación. Si el anteproyecto no fija umbrales cuantitativos definitivos, estos deben tratarse como brecha metodológica y calibrarse en etapas posteriores.

**Brechas metodológicas detectadas:**

- El anteproyecto define el evento con claridad conceptual, pero no fija umbrales operativos para actividad ni polarización.
- No define todavía cómo se combinan exactamente ambas señales en un contrato de decisión.
- No especifica formato de artefactos para validación por cronología pública o RAG.
- No define una política final para distinguir alarma, evento candidato, evento confirmado y falsa alarma.

**Formulación provisional de niveles de decisión:**

- **Alarma:** la actividad supera el criterio operativo del decisor.
- **Evento candidato:** la alarma conserva evidencia textual y muestra señal de polarización o relevancia social.
- **Evento validado:** el evento candidato se contrasta con cronología pública o evidencia externa.
- **Falsa alarma o ruido:** la alerta no encuentra evidencia pública o se explica por dinámica interna no vinculada a un suceso socialmente relevante.

**Mapa objetivo-señal-decisión-evidencia:**

| Objetivo del anteproyecto | Fase del pipeline relacionada | Señal o variable observada | Decisión que permite tomar | Evidencia producida por el pipeline | Riesgo si la evidencia no existe | Skill CRISP-DM relacionada |
|---|---|---|---|---|---|---|
| Revisar literatura sobre detección en línea y YouTube | Comprensión del negocio | Conceptos de evento, detección en línea, actividad y polarización | Delimitar qué se puede llamar evento en este prototipo | Documento de marco conceptual y definición operativa | La arquitectura se evalúa con criterios ajenos al problema | `crisp-dm-problem-framing` |
| Implementar pipeline reproducible de adquisición y preprocesamiento | Extracción y preprocesamiento | Videos, comentarios, timestamps, metadatos, texto limpio | Decidir si el corpus es apto para monitoreo | Datasets bronze/silver/gold, metadata de corrida, reporte de calidad | No se puede reproducir ni justificar el corpus | `data-source-inventory-lineage`, `data-quality-reporting` |
| Construir señales de actividad | Monitoreo | Volumen por ventana, autores únicos, videos únicos, tasas por ventana | Detectar anomalías de interacción | Snapshots de actividad con ventana temporal | Se confunden fluctuaciones normales con eventos | `feature-construction-aggregation`, `signal-monitoring-spec` |
| Calcular medidas de polarización | Preprocesamiento y monitoreo | Distribución de posturas, ER, EMD, MEC o proxies documentados | Evaluar relevancia social de una anomalía | Fichas de polarización y valores por ventana | El sistema queda reducido a detección por volumen | `signal-monitoring-spec`, `text-preprocessing-spec` |
| Diseñar e implementar el decisor combinado | Simulación y detección | Actividad + polarización + reglas de persistencia/cooldown | Declarar alarma o evento candidato | Registro de evento, configuración del decisor, mapa comentario-ventana | No se puede explicar por qué se detectó un evento | `event-detection-decision-criteria`, `online-stream-simulation-design` |
| Documentar casos de uso con cronología pública | Validación futura | Evento candidato, comentarios, video, ventana, query de verificación | Confirmar, descartar o marcar como ambiguo | `event_candidates`, `event_comment_map`, `rag_queries`, reporte de validación | RAG no podrá recuperar ni contrastar evidencia | `rag-validation-readiness`, `experiment-traceability-reporting` |

**Criterios de éxito para el pipeline:**

- **Éxito metodológico:** el pipeline responde a la definición de evento del anteproyecto; distingue detección en línea de tiempo real estricto; documenta exclusiones, supuestos y brechas.
- **Éxito técnico:** las fases se ejecutan de forma reproducible; las entradas y salidas tienen contratos claros; el decisor puede seleccionarse por CLI y JSON; `XiaoEMATriggerDetector` queda como default provisional.
- **Éxito experimental:** el pipeline genera alarmas o eventos candidatos con actividad y polarización documentadas, sin cambiar algoritmos ni thresholds durante el refinamiento arquitectónico.
- **Éxito de trazabilidad:** cada alerta puede rastrearse hasta ventana temporal, señales, comentarios, video, configuración del decisor y dataset de origen.
- **Éxito de preparación para RAG:** cada evento candidato produce artefactos suficientes para construir consultas, recuperar evidencia pública y emitir un veredicto futuro sin reconstrucciones manuales.

**Archivos/módulos involucrados:** `.agents/examples/anteproyecto.pdf`, `WORK-PLAN.MD`, `.agents/skills/crisp-dm-problem-framing/SKILL.md`, `.agents/skills/russellian-clear-writing/SKILL.md`.

**Tipo de cambio:** Documentación metodológica. No hay cambios funcionales.

**Riesgo:** Bajo.

**Prioridad:** Bloqueante.

**Criterio de aceptación:** La definición operativa de evento y el mapa objetivo-señal-decisión-evidencia quedan documentados antes de iniciar auditoría técnica o refinamiento arquitectónico.

**¿Altera comportamiento?:** No.

---

### Etapa 0: Auditoría Y Documentación Formal

**Objetivo:** Crear inventario formal de fuentes, contratos entre fases y estructura de trazabilidad de experimentos, usando los artefactos de Etapa -1 como entrada. Esta etapa no debe proponer refactors arquitectónicos todavía.

**Skills invocadas → artefactos → consumidor siguiente:**

| Skill | Artefacto producido | Consumidor |
|---|---|---|
| `data-source-inventory-lineage` | Inventario de fuentes con origen, fecha, alcance y propietario lógico; diccionario de campos por dataset; matriz de linaje (raw → bronze → silver → gold → experimento); registro de ejecuciones de extracción; lista de gaps de trazabilidad | Etapa 1 (selección), Etapa 3 (contratos), §9 decisiones |
| `data-integration-formatting` | Contrato de datos entre fases: schemas canónicos por entidad (comentario, video, ventana, señal, evento); tabla de formatos permitidos; lista de validaciones de integridad; identificación de cada consumidor por output intermedio | Etapa 2 (modularización), Etapa 3 (trazabilidad), Etapa 4 (RAG) |
| `experiment-traceability-reporting` | Log de experimentos (dataset + parámetros + fecha + objetivo por corrida); reporte de estado por fase CRISP-DM; matriz artefacto-fase-pipeline; lista de pendientes y riesgos residuales | Etapa 3 (fortalecimiento), Etapa 5 (regresión) |

**Archivos/módulos:** `README.md`, `data/bronze/runs/`, `experiments/xiao/`, `scripts/`, módulos principales del paquete.

**Tipo de cambio:** Documentación (sin cambios funcionales).

**Riesgo:** Bajo.

**Prioridad:** Alta.

**Criterio de aceptación:** Cada dataset tiene origen, fecha, alcance y propietario lógico documentados; joins y claves de trazabilidad declarados; cada experimento rastreable a dataset + configuración + detector + salida; schemas intermedios declarados con consumidor identificado.

**¿Altera comportamiento?:** No.

---

### Etapa 1: Organización Arquitectónica Mínima, Selección Y Calidad De Datos

**Objetivo:** Formalizar criterios de selección del corpus, especificar reglas de preprocesamiento y documentar calidad por corrida de limpieza. En esta etapa se incorporan las skills `dataset-selection-sampling` y `data-quality-reporting`, que estaban en el diagnóstico inicial pero sin etapa concreta asignada.

**Rationale:** Estas dos skills aparecían en la tabla §2 pero desaparecían del plan de etapas, lo que dejaba sin artefactos concretos el protocolo de selección y el reporte de calidad.

**Skills invocadas → artefactos → consumidor siguiente:**

| Skill | Artefacto producido | Consumidor |
|---|---|---|
| `dataset-selection-sampling` | Protocolo de selección; tabla de criterios de inclusión/exclusión; descripción de muestras y subsets; registro de sesgos y limitaciones conocidas; mapa dataset-experimento | Etapa 3 (contratos), Etapa 5 (regresión), evaluación académica |
| `data-quality-reporting` | Reporte de calidad por corrida de limpieza: volúmenes, duplicados eliminados, spam, comentarios vacíos, cobertura de campos críticos | Etapa 3 (trazabilidad), Etapa 4 (RAG readiness) |
| `text-preprocessing-spec` | Especificación de reglas NLP: caso, acentos, signos, emojis, URLs, menciones, hashtags, idioma, spam, duplicados; tabla regla-justificación; ejemplos antes/después; contrato texto-crudo-a-preparado | Etapa 3 (contratos), Etapa 4 (RAG) |

**Archivos/módulos:** `youtube_pipeline/cleaning.py`, `data/gold/`, `data/silver/comments/`, documentación.

**Tipo de cambio:** Arquitectura/documentación (sin cambios funcionales en código).

**Riesgo:** Bajo.

**Prioridad:** Alta.

**Criterio de aceptación:** Criterios de selección documentados y justificados; reglas de limpieza especificadas con propósito analítico por cada transformación; reporte de calidad reproducible por corrida.

**¿Altera comportamiento?:** No.

---

### Etapa 2: Modularización Del Decisor De Simulación

**Objetivo:** Implementar contrato común para decisores, permitir switch entre ellos sin reescribir la simulación, conservando `XiaoEMATriggerDetector` como implementación por defecto bajo el identificador `xiao_ema`.

**Skills invocadas → artefactos → consumidor siguiente:**

| Skill | Artefacto producido | Consumidor |
|---|---|---|
| `event-detection-decision-criteria` | Matriz de decisión de eventos formalizada; definición de niveles de alerta; criterios de severidad/persistencia; plantilla de registro de trigger detectado; lista de casos borde | Etapa 3 (trazabilidad), Etapa 4 (RAG) |
| `online-stream-simulation-design` | Especificación de simulación en línea: unidad de llegada, ordenamiento temporal y criterio de desempate, supuestos de latencia/acumulación, contrato entrada/salida por paso, diferencias histórico vs. real | Implementación de Etapa 2; Etapa 5 (regresión) |
| `signal-monitoring-spec` | Ficha técnica por señal (actividad, polarización); matriz señal-ventana-baseline; interpretación metodológica por señal; lista de sensibilidad/ruido | Implementación de Etapa 2; Etapa 4 (RAG); Etapa 5 (regresión) |

**Archivos/módulos:** `youtube_pipeline/stream_playback.py`, `youtube_pipeline/run_pipeline.py`, posible módulo `youtube_pipeline/deciders/`.

**Tipo de cambio:** Modularización (cambio arquitectónico sin cambio funcional).

**Riesgo:** Medio. Mitigación: ejecutar Etapa 5 (regresión) comparando snapshots, logs y triggers antes/después; conservar estrictamente el orden hook→stream.

**Prioridad:** Alta.

**Criterio de aceptación:** Misma salida con decisor default `xiao_ema`; selector disponible por CLI y/o inyección de dependencia; `XiaoEMATriggerDetector` queda como implementación bajo contrato común; scripts externos que importan directamente el decisor no se rompen.

**¿Altera comportamiento?:** No debería; verificable con Etapa 5.

---

### Etapa 3: Fortalecimiento De Trazabilidad Y Contratos

**Objetivo:** Formalizar artefactos opcionales de detección para auditoría y RAG; documentar el contrato temporal en UTC y segundos; completar contratos entre fases con catálogo de variables derivadas y plan de partición temporal.

**Rationale:** La alerta sobre `event_time_unix_ms` fue identificada en §6. La decisión metodológica es usar segundos para el campo numérico nuevo y UTC para el contrato interno. Esta etapa convierte esa decisión en documentación y, si se aprueba al implementar, en un campo compatible sin romper salidas existentes.

**Skills invocadas → artefactos → consumidor siguiente:**

| Skill | Artefacto producido | Consumidor |
|---|---|---|
| `experiment-traceability-reporting` | Manifiesto por experimento (dataset + config + detector + salidas + scripts usados); actualización del log post-modularización; reporte de estado CRISP-DM actualizado | Etapa 4 (RAG), Etapa 5 (regresión) |
| `feature-construction-aggregation` | Catálogo de variables derivadas con fórmula reproducible, unidad, granularidad y propósito; diccionario de señales; especificación de ventanas y agregaciones; tabla campo-crudo-a-derivado; lista de supuestos y riesgos de sensibilidad | Etapa 4 (RAG readiness), evaluación académica |
| `temporal-partitioning-validation-design` | Plan de partición temporal; calendario de ventanas calibración/test/validación futura; reglas de prevención de fuga de información; matriz experimento-período; riesgos de evaluación temporal | Etapa 4 (RAG), Etapa 5 (regresión) |

**Resolución temporal aprobada para el plan:**

1. Verificar unidad real usando `scripts/audit_gold_rag_thresholds.py`.
2. Mantener `event_time_utc` como campo canónico para simulación, detección, trazabilidad y RAG.
3. Documentar `event_time_unix_ms` como campo legacy si su contenido observado no corresponde al nombre.
4. Si se implementa un campo nuevo, usar `event_time_unix_s` para comentarios y `published_at_unix_s` para videos.
5. No eliminar ni reinterpretar columnas existentes sin estrategia de compatibilidad.

**Archivos/módulos:** `scripts/`, `experiments/xiao/`, `youtube_pipeline/run_pipeline.py`, `youtube_pipeline/stream_playback.py`, `data/gold/`.

**Tipo de cambio:** Trazabilidad (sin cambios funcionales sobre resultados; posible campo adicional compatible).

**Riesgo:** Medio sobre nuevos artefactos de detección; bajo sobre resultados existentes.

**Prioridad:** Alta.

**Criterio de aceptación:** Cada trigger rastreable a ventana, señales y comentarios que lo originaron; contrato temporal documentado como UTC + segundos; manifiesto por experimento disponible; catálogo de variables derivadas completo.

**¿Altera comportamiento?:** No sobre resultados; posible campo adicional en salida de detección con aprobación.

---

### Etapa 4: Preparación Para Validación Futura Con RAG

**Objetivo:** Diseñar contrato RAG-ready sin implementar RAG completo. El campo `news_api_query`, ya presente en el ejemplo `.agents/examples/structured-rag-pdf/data/queries_df.csv`, debe quedar formalizado como parte del contrato del pipeline principal.

**Skills invocadas → artefactos → consumidor siguiente:**

| Skill | Artefacto producido | Consumidor |
|---|---|---|
| `rag-validation-readiness` | Plantilla de evento validable; requisitos mínimos de registro de evento; conjunto de preguntas de recuperación por evento/video; criterios de clasificación de evidencia (confirmado/parcial/no confirmado/ambiguo); lista de riesgos y controles | Integración RAG futura; evaluación académica |

**Archivos/módulos:** ejemplos RAG en `.agents/examples/`, documentación, posibles schemas de salida.

**Tipo de cambio:** Arquitectura/contratos (sin implementación de RAG).

**Riesgo:** Bajo-medio.

**Prioridad:** Media.

**Criterio de aceptación:** Plantilla de evento/query/map validada y consistente con artefactos de Etapa 3; contrato de entrada para fase RAG futura documentado; `news_api_query` formalizado como campo del contrato.

**Estado de implementación:** Se documenta el contrato RAG-ready en `docs/rag_validation_readiness.md`. La etapa no implementa motor RAG, embeddings, recuperación externa, prompts, ni cambia el formato actual de snapshots, triggers o `trigger_comment_map.csv`.

**¿Altera comportamiento?:** No.

---

### Etapa 5: Pruebas De Regresión Y Verificación

**Objetivo:** Demostrar que los resultados producidos por las etapas 2 y 3 conservan el comportamiento funcional anterior. Esta etapa valida que el refinamiento no alteró snapshots, triggers ni logs de detección.

**Skills invocadas → artefactos → consumidor siguiente:**

| Skill | Artefacto producido | Consumidor |
|---|---|---|
| `temporal-partitioning-validation-design` | Verificación de que particiones y orden temporal se conservan antes/después | Cierre del plan; evaluación académica |
| `experiment-traceability-reporting` | Comparación formal antes/después: snapshots, trigger_log, trigger_comment_map, summary; reporte de regresión | Cierre del plan; evaluación académica |

**Archivos/módulos:** scripts existentes de auditoría, `experiments/xiao/`, salidas de playback principal.

**Tipo de cambio:** Pruebas (sin cambios funcionales).

**Riesgo:** Medio (si se detectan diferencias, implica revisión de Etapa 2 o 3).

**Prioridad:** Alta.

**Criterio de aceptación:** Snapshots, triggers y logs antes/después son idénticos en contenido bajo el decisor default `xiao_ema` con los mismos parámetros.

**Estado de implementación:** La evidencia de regresión queda documentada en `docs/regression_verification.md`. La verificación confirma que snapshots, limpieza, contrato temporal, selector de decisor y scripts de auditoría preservan comportamiento esperado sin regenerar datasets oficiales.

**¿Altera comportamiento?:** No.

## 8. Cambios Que NO Deben Hacerse Todavía

- No cambiar algoritmos de detección.
- No cambiar thresholds.
- No cambiar métricas de polarización o actividad.
- No cambiar resultados esperados.
- No cambiar formatos actuales por estética.
- No implementar RAG.
- No reemplazar Streamz.
- No reescribir el pipeline completo.
- No eliminar legacy CSV.
- No mover datos ni regenerar experimentos sin aprobación.
- No modificar notebooks exploratorios salvo que luego se defina como parte de documentación.
- No eliminar ni reinterpretar `event_time_unix_ms`; el contrato temporal debe migrar de forma compatible hacia UTC + segundos.

## 9. Preguntas O Decisiones Que Requieren Tu Aprobación

1. Confirmar si la definición operativa de evento de Etapa -1 queda aprobada o debe ajustarse con el director/codirector.
2. Aprobar el contrato común de decisores antes de modularizar `XiaoEMATriggerDetector`.
3. Confirmar que los artefactos de detección usarán estrategia híbrida: CSV para tablas planas y JSONL para eventos canónicos.
4. Aprobar que RAG reciba todos los comentarios asociados a la ventana/trigger.
5. Decisión aprobada: usar `event_time_unix_s` y `published_at_unix_s` como campos compatibles, manteniendo `event_time_utc` como canónico para comentarios.
6. Decidir estructura final para `experiments/` y `reports/`.
7. Definir si la Etapa -1 se mantiene solo en `WORK-PLAN.MD` o se extrae luego a un documento metodológico independiente.

## 10. Próximo Paso

El primer paso recomendado, después de tu aprobación explícita, es cerrar la **Etapa -1: Alineación con el problema de investigación y definición operativa de evento**. Solo después debe empezar la Etapa 0 de auditoría y documentación técnica.

Fuentes metodológicas consultadas: `.agents/examples/anteproyecto.pdf`; `.agents/skills/crisp-dm-problem-framing/SKILL.md`; `.agents/skills/russellian-clear-writing/SKILL.md`; IBM SPSS Modeler sobre [preparación de datos](https://www.ibm.com/docs/es/spss-modeler/saas?topic=preparation-data-overview), [comprensión de datos](https://www.ibm.com/docs/es/spss-modeler/saas?topic=understanding-data-overview), [CRISP-DM en SPSS Modeler](https://www.ibm.com/docs/es/spss-modeler/saas?topic=overview-crisp-dm-in-spss-modeler) e [informes de proyecto](https://www.ibm.com/docs/es/spss-modeler/saas?topic=reports-generating-report).
