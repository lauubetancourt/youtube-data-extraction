---
name: rag-strategy-selection
description: Use this skill to choose appropriate RAG strategies for validating detected YouTube events. Use it whenever refining the RAG phase, comparing re-ranking, query expansion, multi-query, contextual retrieval, chunking, hierarchical RAG, agentic RAG, knowledge graphs, self-reflection, or fine-tuned embeddings for this event-detection pipeline.
---

# RAG Strategy Selection

## Proposito
Evaluar que estrategias RAG son adecuadas para validar eventos detectados por el pipeline de YouTube, priorizando trazabilidad, explicabilidad, costo razonable y compatibilidad con los artefactos actuales.

## Cuando Usarla
Usala antes de implementar o modificar cualquier componente RAG, al decidir entre estrategias avanzadas, al revisar el PoC existente o al justificar por que una estrategia debe implementarse, postergarse o descartarse.

## Entradas Esperadas
- Descripcion del objetivo de validacion RAG.
- Estado del PoC actual y sus artefactos (`queries_df.csv`, `noticias_df.csv`, `auditoria_df.csv`, vectorstores y linaje).
- Contratos disponibles de evento, evidencia, consultas, evidencia externa y resultados.
- Restricciones de costo, dependencias, latencia, privacidad y reproducibilidad.
- Lista de estrategias candidatas tomada de `.agents/all-rag-strategies/`.

## Procedimiento Paso A Paso
1. Define la pregunta de validacion: si el evento detectado corresponde a un evento publico externo, una reaccion interna de comunidad, ruido/desinformacion o un caso ambiguo.
2. Identifica la brecha concreta del PoC que se quiere resolver: baja precision, baja cobertura, perdida de trazabilidad, limite de contexto, evidencia externa insuficiente o salida poco evaluable.
3. Mapea cada estrategia RAG a una etapa: preparacion de evidencia, generacion de consultas, recuperacion, ranking, gestion de contexto, generacion de veredicto o evaluacion.
4. Evalua compatibilidad con el pipeline actual: debe consumir artefactos posteriores y no cambiar extraccion, limpieza, simulacion, monitoreo, deteccion, thresholds, ventanas ni metricas.
5. Califica cada estrategia con estos criterios: utilidad para validar eventos, trazabilidad hacia comentarios originales, explicabilidad, costo de implementacion, nuevas dependencias, riesgo de sobreingenieria y facilidad de prueba.
6. Selecciona una estrategia base minima y una lista de estrategias postergadas. Prefiere capas simples que mejoren el PoC sin cambiar formatos actuales.
7. Documenta las decisiones que requieren aprobacion: nuevo modelo, nueva base vectorial, nuevas dependencias, cambio de unidad de analisis, cambio de output o cambio de criterios de validacion.

## Artefactos Esperados
- Matriz de seleccion de estrategias RAG.
- Recomendacion de estrategia inicial.
- Lista de estrategias postergadas o descartadas.
- Justificacion tecnica y metodologica.
- Riesgos, dependencias y criterios de aceptacion.

## Criterios De Calidad
- La recomendacion responde a una brecha real del pipeline, no a una moda tecnica.
- La estrategia elegida conserva trazabilidad desde resultado RAG hasta `event_id`, `video_id`, ventana temporal y `comment_id`.
- El plan mantiene al RAG como fase posterior no invasiva.
- Las estrategias costosas se justifican con beneficios observables.
- Las decisiones irreversibles o con nuevas dependencias quedan marcadas para aprobacion.

## Estrategias RAG Relacionadas
- Re-ranking: util como segunda etapa para mejorar precision sobre candidatos ya recuperados.
- Query expansion: util para generar variantes de busqueda externa cuando titulos o comentarios son ambiguos.
- Multi-query RAG: util para mejorar cobertura cuando un evento puede tener varios nombres, actores o enfoques.
- Contextual retrieval: util si los chunks pierden contexto de evento, video o ventana.
- Context-aware chunking: util para crear unidades coherentes sin perder mapeo a comentarios.
- Hierarchical RAG: util si se requiere recuperar comentarios pequenos pero presentar contexto de evento/video/ventana.
- Self-reflective RAG: postergable como control de calidad cuando exista una base trazable.
- Agentic RAG, knowledge graphs y fine-tuned embeddings: evaluar con cautela por costo, infraestructura y riesgo de sobreingenieria.

## Relacion Con Mi Pipeline
La seleccion debe partir de que la deteccion ya produce candidatos y que el RAG valida despues. El primer objetivo no es crear un agente complejo, sino formalizar una fase que use todos los comentarios asociados al evento, preserve evidencia completa y seleccione solo una vista manejable para el modelo.

## Relacion Con CRISP-DM
Corresponde principalmente a modelado y evaluacion. En CRISP-DM, la seleccion de tecnica debe estar justificada por el objetivo analitico, los datos disponibles, los riesgos y los criterios de exito; aqui eso significa validar eventos detectados sin contaminar la fase de deteccion.

## Limites De La Skill
- No implementa RAG.
- No instala dependencias.
- No cambia prompts, modelos, thresholds, ventanas ni formatos.
- No decide por si sola una base vectorial o un proveedor externo.

## Que No Debe Hacer
- No recomendar estrategias avanzadas sin una brecha concreta.
- No copiar codigo desde `.agents/all-rag-strategies/`.
- No mezclar comentarios internos con evidencia externa como si tuvieran el mismo papel.
- No permitir que ranking, chunking o resumen eliminen la evidencia completa.
