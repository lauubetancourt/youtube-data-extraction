---
name: rag-retrieval-design
description: Use this skill to design retrieval for RAG validation over YouTube event evidence while preserving traceability to all original comments. Use it whenever planning lexical, semantic, multi-query, query expansion, re-ranking, external news retrieval, or internal-comment retrieval for detected events.
---

# RAG Retrieval Design

## Proposito
Definir como recuperar evidencia textual relevante para validar eventos detectados, manteniendo trazabilidad completa hacia los comentarios originales y separando evidencia interna de YouTube de evidencia externa.

## Cuando Usarla
Usala al pasar de paquetes de evidencia a consultas, retrieval interno, retrieval externo, ranking de comentarios, seleccion de snippets o almacenamiento de evidencia recuperada.

## Entradas Esperadas
- `event_evidence_package` por evento.
- `event_comment_map` completo con todos los comentarios asociados.
- Preguntas de recuperacion y objetivos de validacion.
- Metadatos de video, ventana temporal y senales.
- Restricciones de proveedor externo, API, idioma y rango temporal.

## Procedimiento Paso A Paso
1. Separa dos tareas de retrieval: evidencia interna de comentarios y evidencia externa de fuentes publicas.
2. Define la unidad recuperable interna: comentario individual, thread, bloque temporal, bloque por video o chunk jerarquico. Cada unidad debe guardar lista de `comment_id`.
3. Define la unidad recuperable externa: articulo, resultado de busqueda, snippet, URL o documento recuperado. Cada unidad debe guardar `evidence_id`, `query_id` y proveedor.
4. Genera preguntas o consultas a partir de evento, videos, titulos, entidades y tiempo. Indica si son manuales, template-based o model-assisted.
5. Usa recuperacion simple como base: filtros por `event_id`, `video_id` y ventana; despues aplica busqueda lexica o semantica si el volumen lo exige.
6. Si hay ambiguedad, considera query expansion o multi-query para cubrir nombres propios, sinonimos y variantes de la noticia.
7. Si hay muchos candidatos, considera re-ranking para priorizar evidencia que mejor responda la pregunta de validacion.
8. Registra siempre resultados y descartes: candidatos recuperados, scores, ranking, IDs, filtros usados y razon de seleccion.
9. Produce una vista compacta para el modelo, pero conserva el inventario completo en artefactos auditables.

## Artefactos Esperados
- Diseno de retrieval interno y externo.
- Esquema de `rag_queries` con IDs, fuente de consulta, idioma y ventana temporal.
- Esquema de candidatos recuperados con scores y `comment_id` o `evidence_id`.
- Politica de ranking y deduplicacion.
- Registro de lineage desde respuesta final hasta comentarios y fuentes.

## Criterios De Calidad
- Ningun resultado RAG queda sin una ruta hacia comentario original o fuente externa.
- Los filtros temporales son explicitos y reproducibles.
- La evidencia interna explica la reaccion en YouTube; la evidencia externa valida si ocurrio un evento publico.
- Las consultas no dependen solo de texto partidista o ruido de comentarios.
- El retrieval puede ejecutarse de forma incremental sin cambiar outputs de deteccion.

## Estrategias RAG Relacionadas
- Query expansion: para ampliar consultas externas sin perder intencion.
- Multi-query RAG: para buscar por varios angulos del mismo evento.
- Re-ranking: para mejorar precision sobre candidatos recuperados.
- Contextual retrieval: para recuperar chunks que llevan contexto de evento/video/ventana.
- Agentic RAG: postergable; solo considerar si hay multiples herramientas maduras y trazables.

## Relacion Con Mi Pipeline
El pipeline ya dispone de eventos, comentarios, videos y snapshots. Esta skill disena la capa que transforma esos artefactos en evidencia recuperable para validacion, sin asumir que el PoC actual de `trigger_time + video_id` sea suficiente como contrato formal.

## Relacion Con CRISP-DM
Corresponde a modelado y evaluacion. La recuperacion es parte del procedimiento experimental y debe registrar parametros, datos usados, decisiones y limitaciones para poder evaluar resultados despues.

## Limites De La Skill
- No implementa motores vectoriales.
- No decide proveedor de noticias.
- No cambia prompts ni modelos.
- No cambia la unidad de deteccion.

## Que No Debe Hacer
- No usar solo los primeros comentarios como evidencia completa.
- No perder `comment_id` al convertir comentarios en documentos o chunks.
- No confirmar eventos solo con comentarios internos.
- No ocultar consultas fallidas o resultados descartados.
