---
name: rag-evaluation-and-traceability
description: Use this skill to evaluate RAG validation quality and preserve traceability of evidence, retrieval, prompts, outputs, and runs. Use it whenever designing validation reports, acceptance criteria, audit logs, regression checks, or reproducibility evidence for RAG event validation.
---

# RAG Evaluation And Traceability

## Proposito
Definir criterios para evaluar la validacion RAG y conservar trazabilidad de evidencia, resultados, ejecucion, retrieval, prompts, fuentes y decisiones.

## Cuando Usarla
Usala al cerrar una etapa RAG, al preparar pruebas, al disenar reportes de validacion, al comparar estrategias o al verificar que los resultados RAG sean auditables.

## Entradas Esperadas
- Contratos de evidencia y validacion.
- Resultados del PoC o de una fase RAG refinada.
- Lineage de comentarios, consultas, fuentes externas y validaciones.
- Manifiestos de ejecucion.
- Criterios de aceptacion metodologicos y tecnicos.

## Procedimiento Paso A Paso
1. Define que se evalua: completitud de evidencia, calidad de retrieval, validez del label, trazabilidad, reproducibilidad y compatibilidad con pipeline.
2. Verifica cobertura de evidencia: cada `event_id` debe tener comentarios, ventanas, videos, senales y rutas de artefacto cuando correspondan.
3. Verifica trazabilidad interna: todo texto usado por el modelo debe mapear a `comment_id` o `context_unit_id` con lista de comentarios.
4. Verifica trazabilidad externa: todo argumento de validacion debe citar `evidence_id`, URL, query, proveedor y tiempo de recuperacion.
5. Evalua labels con un conjunto controlado: `confirmed`, `partially_confirmed`, `not_confirmed`, `ambiguous` o el set aprobado.
6. Registra limitaciones: consultas fallidas, baja cobertura, eventos mixtos, comentarios ruidosos, fuentes contradictorias y posibles sesgos.
7. Ejecuta o especifica pruebas de no regresion: el pipeline de deteccion debe seguir funcionando y sus outputs no deben cambiar.
8. Produce un reporte que se pueda leer sin ejecutar el modelo de nuevo.

## Artefactos Esperados
- Criterios de aceptacion RAG.
- Reporte de trazabilidad por evento.
- Matriz evento-consulta-evidencia-validacion.
- Registro de parametros, modelo, proveedor, prompts y tiempos.
- Lista de riesgos residuales y decisiones pendientes.

## Criterios De Calidad
- Cada validation result puede justificarse con evidencia identificable.
- Las razones no prometen certeza absoluta y reconocen evidencia insuficiente.
- Los conteos declarados coinciden con los artefactos.
- La evaluacion distingue fallo de retrieval, falta de evidencia y evento realmente no confirmado.
- Las pruebas no requieren cambiar deteccion, thresholds ni outputs existentes.

## Estrategias RAG Relacionadas
- Re-ranking: debe registrar candidatos iniciales, scores y top final.
- Query expansion y multi-query: deben registrar variantes, deduplicacion y aporte de cada consulta.
- Contextual retrieval y chunking: deben registrar contexto agregado y IDs originales.
- Self-reflective RAG: puede usarse luego para revisar suficiencia, pero debe guardar iteraciones y no sobrescribir evidencia.
- Agentic RAG: requiere logs de herramientas y decisiones si se considera en una fase futura.

## Relacion Con Mi Pipeline
El proyecto ya cuenta con verificacion de artefactos RAG y una integracion PoC posterior. Esta skill define como evaluar el refinamiento: no basta con producir una respuesta; debe poder rastrearse hasta comentarios, fuentes, eventos, consultas y parametros.

## Relacion Con CRISP-DM
Corresponde a evaluacion y despliegue. CRISP-DM exige comparar resultados contra objetivos, revisar supuestos, documentar limitaciones y dejar evidencia reproducible para decisiones posteriores.

## Limites De La Skill
- No decide automaticamente si un evento es verdadero.
- No ejecuta retrieval ni modelos.
- No sustituye revision humana cuando el caso sea ambiguo o sensible.
- No cambia contratos ya aprobados.

## Que No Debe Hacer
- No aceptar una validacion sin evidencia citada.
- No contar como confirmacion una coincidencia vaga entre comentarios y noticias.
- No ocultar errores de API, consultas sin resultados o evidencia contradictoria.
- No publicar datos sensibles sin minimizacion.
