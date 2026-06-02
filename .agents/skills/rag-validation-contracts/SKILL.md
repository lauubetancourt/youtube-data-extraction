---
name: rag-validation-contracts
description: Use this skill to define input and output contracts between event detection artifacts and RAG validation. Use it whenever specifying schemas, compatibility rules, validation labels, query contracts, external evidence contracts, or non-invasive RAG integration boundaries.
---

# RAG Validation Contracts

## Proposito
Definir contratos de entrada y salida entre la fase de deteccion y la fase de validacion con RAG, manteniendo compatibilidad con el pipeline actual y evitando cambios invasivos.

## Cuando Usarla
Usala al disenar esquemas, artefactos, IDs, columnas, labels, manifiestos, compatibilidad con el PoC o handoffs entre deteccion, evidencia, retrieval y validacion.

## Entradas Esperadas
- Contratos actuales de datos y arquitectura.
- Artefactos de evidencia RAG (`run_manifest`, `event_candidates`, `event_comment_map`, `event_signal_snapshot_map`, `event_evidence_packages`).
- Artefactos de validacion (`rag_validation_tasks`, `rag_retrieval_questions`, `rag_queries`, `external_evidence`, `validation_results`).
- PoC actual y sus archivos compatibles.
- Reglas de compatibilidad y decisiones pendientes.

## Procedimiento Paso A Paso
1. Declara la frontera arquitectonica: deteccion produce candidatos; RAG prepara, recupera y valida despues.
2. Define el contrato de entrada RAG: `event_id`, `run_id`, detector, tiempo, ventana, senales, videos, comentarios, rutas y version de artefacto.
3. Define el contrato de salida RAG: `validation_id`, `event_id`, label controlado, estado, evidencia usada, razonamiento, limitaciones, validador y timestamp.
4. Define contratos intermedios: consultas, evidencia externa, unidades de contexto, ranking y resumen.
5. Especifica compatibilidad con PoC: que columnas se preservan, que linaje se agrega de forma auxiliar y que no se debe cambiar.
6. Marca campos internos y campos publicables. Raw text y author IDs deben tratarse como evidencia interna salvo aprobacion.
7. Define reglas de versionado y migracion: nuevos artefactos deben tener `artifact_version` y no romper consumidores actuales.
8. Lista cambios que requieren aprobacion explicita antes de implementar.

## Artefactos Esperados
- Contrato de entrada RAG.
- Contrato de salida RAG.
- Diccionario de campos y llaves de union.
- Matriz de compatibilidad con artefactos actuales.
- Lista de decisiones que requieren aprobacion.

## Criterios De Calidad
- Los contratos son joinables por IDs estables, no solo por timestamps.
- La unidad de evento, la unidad de video y la unidad de comentario no se confunden.
- La salida RAG distingue label, estado, razonamiento, evidencia y limitaciones.
- Los contratos permiten dry-run y verificacion sin llamar LLMs ni APIs externas.
- Los cambios nuevos se agregan como artefactos posteriores, no como modificaciones silenciosas de deteccion.

## Estrategias RAG Relacionadas
- Todas las estrategias dependen de contratos claros.
- Hierarchical RAG necesita relaciones padre-hijo explicitas.
- Re-ranking y multi-query necesitan IDs para auditar candidatos y resultados.
- Self-reflective RAG necesita registrar iteraciones y cambios de consulta.
- Knowledge graphs y fine-tuned embeddings requieren contratos adicionales, por eso deben postergarse salvo aprobacion.

## Relacion Con Mi Pipeline
El pipeline ya tiene una integracion no invasiva para evidencia, preparacion de validacion y PoC. Esta skill protege esa separacion y evita que el refinamiento RAG altere monitoreo, deteccion o formatos existentes sin aprobacion.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos, modelado, evaluacion y despliegue experimental. Los contratos hacen que cada fase tenga entradas, salidas y responsabilidades auditables.

## Limites De La Skill
- No implementa transformaciones.
- No decide el contenido final de prompts.
- No cambia outputs actuales del PoC.
- No reemplaza una politica de privacidad.

## Que No Debe Hacer
- No introducir columnas obligatorias en outputs existentes sin aprobacion.
- No cambiar labels de validacion sin registrar impacto.
- No ocultar decisiones de modelo, proveedor o base vectorial en codigo.
- No mezclar evidencia interna y externa en un solo campo opaco.
