# STAB-PATHS-01: inventario de compatibilidad

Fecha de corte: 2026-08-17. Este inventario corresponde a la Fase 8A y se
limita a referencias presentes en código, scripts, tests, documentación y
perfiles versionados. No inspecciona datos ni experimentos y no demuestra la
ausencia de consumidores externos al repositorio.

## Criterio

Un mecanismo se considera activo cuando existe al menos uno de estos
consumidores verificables:

- un import desde código o un script versionado;
- un entrypoint documentado;
- una prueba que protege expresamente su contrato de compatibilidad;
- una ruta de ejecución vigente que todavía no tiene reemplazo equivalente.

La palabra `legacy` en un nombre no constituye evidencia suficiente para
retirar el mecanismo.

## Autoridad nueva que permanece

| Mecanismo | Consumidores | Estado |
|---|---|---|
| `youtube_pipeline.configuration` | runners integrados, adaptadores de etapa, adquisición y preparación | Autoridad común activa; conservar. |
| `scripts/run_cyclic_pipeline.py` | perfil `configs/compatibility/cyclic_current.json`; tests del runner y del script | Runner integrado activo; conservar. |
| `scripts/run_daily_rag_pipeline.py` | perfil `configs/compatibility/daily_rag_current.json`; tests del runner y del script | Runner integrado activo; conservar. |
| CLI común de los runners integrados | ambos runners y sus pruebas | Interfaz común activa; conservar. |

## Compatibilidad con consumidores activos

| Familia | Definición actual | Consumidores comprobados | Motivo por el que no puede retirarse todavía | Condición mínima para reevaluar |
|---|---|---|---|---|
| Seis wrappers cíclicos por etapa | `scripts/run_cyclic_*.py`, `scripts/run_daily_frequency_baseline.py` y sus entrypoints | scripts versionados, pruebas de configuración y lista explícita en `configs/README.md` | Conservan ejecución y diagnóstico independiente por etapa, incluido el formato de configuración anterior. | Acordar que el runner integrado sustituye también el diagnóstico por etapa; actualizar documentación y pruebas antes del retiro. |
| Loaders públicos cíclicos en módulos de dominio | `load_cyclic_*_config` y `load_daily_frequency_baseline_config` | pruebas de compatibilidad; exportación en `__all__` | Protegen la API anterior y comparan configuración legacy con configuración resuelta. | Retirar primero el contrato público o proporcionar una ruta equivalente aprobada. |
| `python -m` de etapas cíclicas | `main()` en seis módulos de dominio | superficie de compatibilidad declarada por cada módulo; sin referencias internas adicionales | No hay consumidor versionado, pero retirar cambia una interfaz ejecutable pública. | Decisión explícita de dejar de soportar la invocación por módulo y prueba de los scripts sucesores. |
| Tres wrappers diarios RAG por etapa | `build_daily_rag_sidecars.py`, `build_daily_rag_consumer_payloads.py`, `build_daily_rag_context_selection.py` y sus entrypoints | scripts versionados y pruebas específicas de configuración | Conservan ejecución local por etapa sin llamadas externas y las tres identidades históricas de etapa. | Demostrar que el runner diario integrado cubre el uso diagnóstico requerido sin cambiar identidades, contratos ni dry-run. |
| `python -m` de etapas diarias RAG | `main()` en `daily_rag_sidecars`, `daily_rag_consumer` y `daily_rag_context_selection` | superficie de compatibilidad declarada; sin referencias internas adicionales | Su retiro cambia una interfaz ejecutable aunque los scripts apunten ya a los entrypoints. | Decisión explícita de retirar esa interfaz y mantener probados los scripts sucesores. |
| Orquestador histórico general | `youtube_pipeline/run_pipeline.py` | README, documentación arquitectónica y pruebas | Sigue siendo la única CLI conjunta para almacenamiento local, limpieza y replay, pero desde Fase 9C traduce sus argumentos hacia el resolver común. | Reevaluar su retiro solo si existe un sucesor que preserve todos los subcomandos; Fase 9C no lo elimina. |
| Adaptadores de almacenamiento, limpieza y replay | `load_legacy_local_files_config`, `load_legacy_cleaning_config`, `load_legacy_prepared_replay_configs` | pruebas focalizadas y contratos públicos conservados | Ya no son usados por `run_pipeline.py`, pero retirar esos contratos no forma parte de Fase 9C. | Comprobar por separado consumidores externos y aprobar su retiro en la limpieza final de compatibilidad. |
| Compatibilidad de adquisición | `load_legacy_youtube_extraction_config` y `resolve_youtube_extraction_config` | `run_pipeline.py`, entrypoint de adquisición y pruebas | Mantiene el formato anterior y la ruta nueva; ambas continúan cubiertas. | Retirar solo cuando el formato anterior deje de estar soportado de manera deliberada. |
| RAG no diario | resolver común para evidencia, sidecars, consumer, validación, G-1, G-2 y G-2 jerárquico; loaders y CLI legacy preservados | siete scripts versionados, imports entre G-1/G-2 y pruebas | Desde Fase 9D los scripts activos delegan en `RunConfig`, pero las interfaces legacy siguen siendo contratos compatibles. | Reevaluar loaders y argumentos solo en la limpieza final; PoC y verificación mantienen su alcance independiente. |

## Defaults y paths de compatibilidad

Los paths de `media/log_3`, Gold y Silver ya no están embebidos en la cadena de
dominio cíclica migrada: permanecen en perfiles o en capas de
entrypoint/compatibilidad. No obstante, todavía son efectivos cuando se invoca
un wrapper sin perfil.

Permanecen dependencias separadas fuera del vertical migrado:

- los entrypoints de compatibilidad de almacenamiento, limpieza y replay
  conservan los defaults para CSV legacy, Silver y Gold; `run_pipeline.py` ya
  no los vuelve a definir;
- `RagEvidenceBuildConfig` y `RagSidecarBuildConfig` conservan Gold como default
  de compatibilidad del RAG no diario; los scripts ya no vuelven a definirlo;
- los entrypoints diarios RAG conservan `media/log_3` como default del formato
  anterior.

Estas definiciones son deuda transitoria, pero no son código sin consumidores.
Eliminar solo la constante trasladaría o rompería la autoridad legacy; debe
retirarse junto con el contrato de compatibilidad que la utiliza.

## Argumentos CLI

Se encontraron 25 archivos con `argparse` en `youtube_pipeline/` y `scripts/`.
Se agrupan así:

| Grupo | Situación |
|---|---|
| CLI común integrada | Activa y deliberadamente pequeña. |
| Seis CLI cíclicas y tres CLI diarias RAG por etapa | Compatibilidad/diagnóstico activo; no deben recibir nuevos defaults. |
| `run_pipeline.py` | CLI histórica activa para adquisición y preparación. |
| Scripts RAG no diarios | Herramientas activas no sustituidas por el runner diario. |
| Scripts retrospectivos y de auditoría | Herramientas independientes; fuera del retiro de compatibilidad de esta fase. |

No existe evidencia para trasladar sus argumentos al CLI común ni para retirar
en bloque estas interfaces.

## Resultado de Fase 8A

- No se demostró que algún loader legacy con estado productivo sea de cero
  consumidores.
- Las nueve fachadas `python -m` de dominio no tienen referencias versionadas
  fuera de su propio bloque `__main__`; son los únicos candidatos acotados a
  una decisión de retiro, pero continúan siendo interfaces públicas y no se
  eliminan en esta fase.
- Los wrappers por etapa siguen explícitamente documentados como herramientas
  de compatibilidad y diagnóstico.
- Los loaders de preparación están bloqueados por el consumidor activo
  `run_pipeline.py`.
- Los flujos RAG no diarios requieren una migración separada; el runner diario
  no es un sucesor funcional de G-1/G-2 ni del PoC.

Por tanto, Fase 8A no autoriza ninguna eliminación. La siguiente unidad de
trabajo debe seleccionar un único contrato de compatibilidad, demostrar su
reemplazo y solicitar aprobación antes de retirarlo.

## Resultado de Fase 8B

Con aprobación posterior al inventario se retiraron las seis fachadas
`python -m` de los módulos de dominio cíclicos. La búsqueda local no mostró
consumidores versionados y cada una ya tenía como sucesor un script que importa
directamente el mismo entrypoint:

- `scripts/run_cyclic_ingestion_simulation.py`;
- `scripts/run_cyclic_ingestion_orchestrator.py`;
- `scripts/run_cyclic_stateful_adapter.py`;
- `scripts/run_cyclic_detection_connector.py`;
- `scripts/run_cyclic_daily_signals.py`;
- `scripts/run_daily_frequency_baseline.py`.

No se retiraron los scripts, entrypoints, loaders legacy, defaults ni contratos
de configuración. Las tres fachadas `python -m` diarias RAG permanecen sin
cambios y requieren una decisión independiente.

## Resultado de Fase 8C

Con aprobación independiente se retiraron las tres fachadas `python -m` de los
módulos de dominio RAG diario. Sus sucesores versionados siguen siendo:

- `scripts/build_daily_rag_sidecars.py`;
- `scripts/build_daily_rag_consumer_payloads.py`;
- `scripts/build_daily_rag_context_selection.py`.

Los scripts continúan importando directamente los mismos entrypoints. No se
modificaron los loaders, los contratos de sidecars, los manifests, el dry-run
ni las fórmulas de las identidades de etapa.

## Resultado de Fase 8D

Se retiraron los seis loaders-fachada alojados en módulos cíclicos de dominio:
`load_cyclic_ingestion_config`, `load_cyclic_orchestrator_config`,
`load_cyclic_stateful_adapter_config`,
`load_cyclic_detection_connector_config`,
`load_cyclic_daily_signal_config` y
`load_daily_frequency_baseline_config`.

La compatibilidad de configuración permanece en la capa que le corresponde:
los seis `load_legacy_*` y sus resolvers de `youtube_pipeline.entrypoints`.
Las pruebas de equivalencia apuntan ahora a esos contratos conservados, sin
cambiar datos de entrada, expectativas, defaults ni resultados.

## Resultado de Fase 9C

`youtube_pipeline/run_pipeline.py` conserva sus cinco subcomandos y argumentos
históricos, pero dejó de leer la configuración del detector o de aplicar
defaults metodológicos por su cuenta. La fachada traduce almacenamiento,
limpieza y replay a los resolvers comunes; replay produce un `RunConfig`
resuelto que contiene `PreparedDatasetConfig`, `ReplayConfig` y
`DetectionConfig.xiao_ema` antes de invocar el componente existente.

Los seis nombres `DEFAULT_TRIGGER_*` continúan exportados porque el script
retrospectivo los consume, pero ahora son alias derivados de `XiaoEMAConfig` y
no una autoridad independiente. No se retiraron subcomandos, argumentos,
loaders públicos ni wrappers.

## Resultado de Fase 9D

### Autoridad de parámetros RAG no diario

| Parámetro o grupo | Ubicación anterior | Nueva autoridad | Riesgo controlado |
|---|---|---|---|
| Paths de entrada y salida | dataclass y loader propio de cada etapa | la misma dataclass compuesta en `RagConfig` y resuelta por `entrypoints/non_daily_rag.py` | cambio accidental de fuente o destino |
| Identidad de evidencia, sidecars, consumer y validación | fórmula propia de cada etapa | la misma fórmula, aplicada antes de resolver paths y almacenada en la subconfiguración | cambio de IDs y linaje |
| Modelo, proveedor y temperatura G-1/G-2 | `RagG1Config`, `RagG2Config`, `RagG2HierarchicalConfig` | las mismas dataclasses, sin copia en `RunConfig` ni scripts | cambio metodológico |
| Batching, tokens, retries y timeouts | dataclass específica de G-1/G-2 | la misma dataclass específica | cambio de costo o estrategia |
| Parámetros de Serper y ventana de búsqueda | configs G-2 | las mismas configs G-2 | cambio de recuperación externa |
| Prompts, queries, labels y esquemas | funciones y constantes de los módulos generativos | sin traslado; permanecen en los módulos | cambio de resultados o contratos |
| `OPENAI_API_KEY`, `SERPER_API_KEY` | entorno/`.env` | entorno/infraestructura, fuera de `RunConfig` y `config_hash` | exposición de secretos |

Los siete scripts activos de RAG no diario conservan argumentos y formatos
legacy, pero ahora traducen esos inputs mediante un solo resolver. Los loaders
anteriores permanecen disponibles para compatibilidad y ya no son la ruta de
configuración de esos scripts. `RunConfig.identity.run_id` continúa siendo la
identidad global; no sustituye las identidades derivadas por cada etapa.

No se modificaron prompts, modelos, temperaturas, queries, proveedores,
contratos de artefactos, labels, estrategias, retries ni timeouts. El PoC y el
verificador de artefactos no formaban parte del alcance autorizado de esta
fase.
