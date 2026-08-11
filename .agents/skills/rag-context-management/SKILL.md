---
name: rag-context-management
description: Use this skill to manage comment volume, context limits, chunking, ranking, summaries, and prompt evidence selection for RAG validation. Use it whenever many YouTube comments must remain traceable but only a subset, chunk, or summary can be sent to a generative model.
---

# RAG Context Management

## Proposito
Definir como manejar volumen de comentarios, limites de contexto, chunking, ranking, seleccion y resumen de evidencia sin perder el mapa completo de comentarios originales.

## Cuando Usarla
Usala cuando un evento tenga demasiados comentarios para el prompt, cuando se necesite crear chunks, cuando se vaya a resumir evidencia, o cuando el modelo solo deba recibir una seleccion representativa.

## Entradas Esperadas
- `event_comment_map` completo.
- Presupuesto de contexto o limite operativo del modelo.
- Preguntas de validacion.
- Reglas de privacidad y minimizacion.
- Scores o senales disponibles: tiempo, video, likes, reply/thread, token_count, spam, actividad y polarizacion.

## Procedimiento Paso A Paso
1. Perfila el volumen por evento: numero de comentarios, videos, autores, replies, tokens aproximados, spam probable y distribucion temporal.
2. Separa el inventario completo de la vista para el modelo. El inventario completo no debe depender de un limite de contexto.
3. Escoge una unidad de chunking trazable: comentario individual, thread, bloque temporal, bloque por video o padre-hijo evento/video/comentarios.
4. Asigna IDs a cada unidad de contexto y conserva listas de `comment_id`, rangos temporales y video IDs.
5. Aplica ranking o muestreo solo como capa posterior. Documenta criterios: relevancia semantica, cercania temporal, diversidad de videos, representacion de posturas, ruido/spam y cobertura de replies.
6. Si se usa resumen, exige que el resumen cite los IDs de comentarios o chunks que lo sustentan.
7. Define limites de prompt: maximo de chunks, maximo de comentarios por chunk, maximo de tokens y politica de truncamiento.
8. Verifica cobertura minima: al menos evidencia del evento completo, videos principales, periodo de inicio y fin, y comentarios que expliquen los temas dominantes.

## Artefactos Esperados
- Politica de chunking y seleccion de contexto.
- Tabla de chunks o unidades de contexto con `context_unit_id` y `comment_ids`.
- Registro de ranking, scores y criterios.
- Resumen trazable, si aplica.
- Checklist de cobertura y limites de contexto.

## Criterios De Calidad
- Cada fragmento enviado al modelo puede rastrearse a comentarios originales.
- El resumen nunca reemplaza el mapa completo de evidencia.
- La seleccion evita depender exclusivamente de los comentarios mas largos, mas recientes o mas extremos.
- La politica se puede reproducir con los mismos datos.
- Los limites de contexto son explicitos y no cambian criterios de deteccion.

## Estrategias RAG Relacionadas
- Context-aware chunking: recomendado para agrupar contenido coherente.
- Hierarchical RAG: recomendado cuando se busca en comentarios pequenos pero se entrega contexto de evento/video.
- Contextual retrieval: util para anteponer metadatos de evento, video y ventana a chunks.
- Late chunking: postergable; requiere modelos e infraestructura especifica.
- Re-ranking: util como capa posterior para priorizar chunks.
- Self-reflective RAG: util despues para detectar evidencia insuficiente, no como reemplazo de trazabilidad.

## Relacion Con Mi Pipeline
Esta skill responde al punto critico del PoC: aunque no todos los comentarios deben ir al modelo generativo, todos deben quedar disponibles. La gestion de contexto decide que vista compacta usa el modelo, no que evidencia existe.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos y modelado. Define transformaciones de datos textuales que deben ser documentadas para evitar sesgos, perdida de informacion y decisiones no reproducibles.

## Limites De La Skill
- No cambia la limpieza de texto existente.
- No define nuevas senales de polarizacion.
- No implementa embeddings ni resummaries.
- No elimina comentarios del paquete de evidencia.

## Que No Debe Hacer
- No filtrar comentarios antes de crear el inventario completo.
- No producir chunks sin `comment_id`.
- No resumir sin citas o referencias internas.
- No usar limites de contexto como justificacion para perder evidencia.
