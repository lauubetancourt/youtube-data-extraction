---
name: rag-evidence-package-design
description: Use this skill to design the evidence package that connects detected events, temporal windows, YouTube videos, activity/polarization signals, and all associated comments. Use it whenever defining event evidence, all-comment maps, event packages, or lineage for RAG validation in this YouTube pipeline.
---

# RAG Evidence Package Design

## Proposito
Disenar el paquete de evidencia que conecta un evento detectado con su ventana temporal, videos, senales de actividad/polarizacion y todos los comentarios asociados, sin perder trazabilidad hacia los comentarios originales.

## Cuando Usarla
Usala al definir o revisar `event_candidates`, `event_comment_map`, `event_signal_snapshot_map`, `event_evidence_packages`, o cualquier artefacto que conecte deteccion con validacion RAG.

## Entradas Esperadas
- Eventos candidatos o triggers con tiempo, ventana, volumen y fuerza.
- Dataset gold de comentarios con `comment_id`, `video_id`, `event_time_utc`, `text`, `text_clean`, `is_reply` y `reply_to_comment_id` cuando existan.
- Snapshots de senales de actividad y polarizacion.
- Metadatos de videos y canales.
- Run manifest o parametros de experimento.

## Procedimiento Paso A Paso
1. Define la unidad de evidencia como un `event_evidence_package` por evento candidato, no como un prompt ni como un chunk.
2. Asigna o verifica identificadores estables: `run_id`, `event_id`, rutas de artefactos y version de contrato.
3. Define la regla temporal de inclusion, por ejemplo `window_start_utc <= event_time_utc <= window_end_utc`, y marca si requiere aprobacion.
4. Construye el mapa completo de comentarios asociados al evento. Incluye todos los comentarios disponibles para la ventana y los videos pertinentes; no reduzcas la evidencia a una muestra del prompt.
5. Conserva campos de linaje: `comment_id`, `video_id`, `event_time_utc`, orden dentro del evento, texto original, texto limpio, indicadores de reply y parent comment.
6. Vincula senales del evento mediante un mapa separado que apunte a snapshots originales y preserve valores de actividad y polarizacion.
7. Mantiene separados los artefactos internos de evidencia, la evidencia externa futura y los reportes publicos anonimizados.
8. Registra cobertura y brechas: cantidad de comentarios, videos, autores, snapshots, comentarios sin texto, replies huerfanos y campos faltantes.

## Artefactos Esperados
- Especificacion de `event_evidence_package`.
- Esquema de `event_comment_map` con todos los comentarios trazables.
- Esquema de `event_signal_snapshot_map`.
- Run manifest o lista de metadatos de ejecucion necesarios.
- Checklist de completitud de evidencia.

## Criterios De Calidad
- Cada evento se puede unir con sus comentarios mediante `event_id` y con los comentarios originales mediante `comment_id`.
- La evidencia completa existe fuera del contexto enviado al modelo.
- Las replies no se pierden ni se mezclan sin metadatos con comentarios raiz.
- Las senales cuantitativas permanecen separadas del texto de comentarios.
- El paquete puede auditarse sin ejecutar retrieval, embeddings ni LLMs.

## Estrategias RAG Relacionadas
- Hierarchical RAG: el paquete puede actuar como padre y los comentarios/chunks como hijos.
- Contextual retrieval: cada chunk futuro puede enriquecerse con `event_id`, video, ventana y senales.
- Context-aware chunking: los comentarios pueden agruparse por coherencia, video, thread o tiempo manteniendo IDs.
- Re-ranking: solo debe ordenar evidencias candidatas, no alterar el inventario completo.

## Relacion Con Mi Pipeline
Esta skill traduce el requerimiento central del proyecto: el RAG formal debe considerar todos los comentarios asociados al evento, video y ventana temporal. Considerar todos no significa enviar todos al modelo; significa que todos quedan disponibles, trazables y referenciables antes de cualquier ranking, chunking, filtrado o resumen.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos y evaluacion. Documenta la integracion entre datos, senales y evidencia para que la validacion posterior sea reproducible y no dependa de reconstrucciones manuales.

## Limites De La Skill
- No define el algoritmo de deteccion.
- No cambia ventanas, thresholds ni metricas.
- No decide que comentarios entran al prompt final.
- No consulta fuentes externas.

## Que No Debe Hacer
- No crear un paquete que contenga solo los comentarios mejor rankeados.
- No reemplazar `comment_id` por texto agregado como unica evidencia.
- No mezclar `event_id` con `video_id` como si fueran la misma unidad.
- No exponer raw text o author IDs en reportes publicos sin una politica de minimizacion.
