# Skills metodologicas para auditoria CRISP-DM

Este directorio contiene skills reutilizables para auditar y refinar metodologicamente el pipeline del trabajo de grado "Prototipo para deteccion en linea de eventos mediante senales de actividad y medidas de polarizacion con datos de YouTube".

La base principal es la documentacion de IBM SPSS Modeler sobre CRISP-DM y preparacion de datos. IBM enfatiza que la preparacion de datos suele concentrar gran parte del esfuerzo del proyecto, y que las fases previas de comprension del negocio y comprension de datos reducen problemas posteriores. Tambien identifica tareas de preparacion como fusion, seleccion de muestras, agregacion, derivacion de atributos, clasificacion/formato para modelado, tratamiento de valores perdidos y division en conjuntos de prueba y entrenamiento.

## Skills creadas

| Skill | Relacion CRISP-DM | Fases del pipeline | Artefactos esperados |
|---|---|---|---|
| `crisp-dm-problem-framing` | Comprension del negocio | Todas, antes de auditar | Definicion de evento, objetivos, criterios de exito, supuestos |
| `data-source-inventory-lineage` | Comprension de datos | Extraccion, preprocesamiento | Inventario de fuentes, diccionario de campos, matriz de linaje |
| `data-understanding-audit` | Comprension de datos | Extraccion, preprocesamiento | Informe exploratorio, perfil del corpus, riesgos preliminares |
| `data-quality-reporting` | Comprension/preparacion de datos | Preprocesamiento | Informe de calidad, decisiones de tratamiento, riesgos residuales |
| `text-preprocessing-spec` | Preparacion de datos | Preprocesamiento, RAG futuro | Especificacion de limpieza NLP, reglas antes/despues |
| `dataset-selection-sampling` | Preparacion de datos | Extraccion, experimentos | Protocolo de seleccion, criterios de inclusion/exclusion |
| `feature-construction-aggregation` | Preparacion de datos | Preprocesamiento, monitoreo | Catalogo de variables derivadas y agregaciones |
| `data-integration-formatting` | Preparacion de datos | Preprocesamiento, simulacion, deteccion | Contrato de datos, esquema canonico, validaciones |
| `temporal-partitioning-validation-design` | Preparacion/evaluacion | Simulacion, deteccion, evaluacion futura | Plan de particion temporal, reglas contra fuga de informacion |
| `online-stream-simulation-design` | Preparacion/modelado/despliegue experimental | Simulacion de flujo en linea | Especificacion de simulacion, reglas de ventana y estado |
| `signal-monitoring-spec` | Modelado experimental | Monitoreo | Fichas de senales, lineas base, visualizaciones esperadas |
| `event-detection-decision-criteria` | Modelado/evaluacion | Deteccion | Matriz de decision, niveles de alerta, plantilla de evento |
| `rag-validation-readiness` | Evaluacion/despliegue futuro | Validacion posterior mediante RAG | Plantilla de validacion, preguntas de recuperacion, etiquetas |
| `rag-strategy-selection` | Modelado/evaluacion | Refinamiento RAG | Matriz de seleccion de estrategias, recomendacion inicial, riesgos |
| `rag-evidence-package-design` | Preparacion/evaluacion | Evidencia para RAG | Paquete evento-evidencia, mapa completo de comentarios, mapa de senales |
| `rag-retrieval-design` | Modelado/evaluacion | Recuperacion interna y externa | Diseno de retrieval, consultas, candidatos, ranking y linaje |
| `rag-context-management` | Preparacion/modelado | Contexto para RAG | Politica de chunking, seleccion, resumen y limites de contexto |
| `rag-validation-contracts` | Preparacion/evaluacion/despliegue | Contratos RAG | Contratos de entrada/salida, compatibilidad, diccionario de campos |
| `rag-evaluation-and-traceability` | Evaluacion/despliegue | Verificacion RAG | Criterios de aceptacion, reporte de trazabilidad, riesgos residuales |
| `experiment-traceability-reporting` | Todas las fases | Transversal | Bitacora de experimentos, reporte CRISP-DM, registro de decisiones |

## Orden sugerido para auditar el pipeline

1. `crisp-dm-problem-framing`
2. `data-source-inventory-lineage`
3. `data-understanding-audit`
4. `data-quality-reporting`
5. `dataset-selection-sampling`
6. `text-preprocessing-spec`
7. `data-integration-formatting`
8. `feature-construction-aggregation`
9. `temporal-partitioning-validation-design`
10. `online-stream-simulation-design`
11. `signal-monitoring-spec`
12. `event-detection-decision-criteria`
13. `rag-validation-readiness`
14. `rag-strategy-selection`
15. `rag-evidence-package-design`
16. `rag-validation-contracts`
17. `rag-retrieval-design`
18. `rag-context-management`
19. `rag-evaluation-and-traceability`
20. `experiment-traceability-reporting`

`experiment-traceability-reporting` debe usarse tambien al cierre de cada etapa para registrar decisiones, artefactos y pendientes.

## Relacion con CRISP-DM

- Comprension del negocio: delimita objetivo, definicion de evento y criterios de exito.
- Comprension de datos: inventaria, explora y evalua calidad de comentarios y metadatos.
- Preparacion de datos: selecciona, limpia, integra, formatea, agrega y deriva atributos.
- Modelado: organiza senales y reglas de deteccion como logica experimental.
- Evaluacion: define particiones, criterios de decision y validacion futura.
- Despliegue: prepara trazabilidad, reportes y salida validable por RAG.

## Relacion con el pipeline

- Extraccion: `data-source-inventory-lineage`, `dataset-selection-sampling`.
- Preprocesamiento: `data-quality-reporting`, `text-preprocessing-spec`, `data-integration-formatting`.
- Simulacion de flujo en linea: `temporal-partitioning-validation-design`, `online-stream-simulation-design`.
- Monitoreo: `feature-construction-aggregation`, `signal-monitoring-spec`.
- Deteccion: `event-detection-decision-criteria`.
- Validacion posterior mediante RAG: `rag-validation-readiness`, `rag-strategy-selection`, `rag-evidence-package-design`, `rag-retrieval-design`, `rag-context-management`, `rag-validation-contracts`, `rag-evaluation-and-traceability`.
- Documentacion y reproducibilidad: `experiment-traceability-reporting`.

## Limite de esta base

Estas skills son guias metodologicas. No implementan extraccion, limpieza, simulacion, monitoreo, deteccion ni RAG. Su objetivo es producir artefactos auditables para que el refinamiento posterior del pipeline sea trazable y alineado con CRISP-DM.

## Fuentes metodologicas consultadas

- IBM SPSS Modeler: Conceptos basicos sobre preparacion de datos: https://www.ibm.com/docs/es/spss-modeler/saas?topic=preparation-data-overview
- IBM SPSS Modeler: Conceptos basicos sobre comprension de datos: https://www.ibm.com/docs/es/spss-modeler/saas?topic=understanding-data-overview
- IBM SPSS Modeler: CRISP-DM en SPSS Modeler: https://www.ibm.com/docs/es/spss-modeler/saas?topic=overview-crisp-dm-in-spss-modeler
- IBM SPSS Modeler: Generacion de informes de proyecto: https://www.ibm.com/docs/es/spss-modeler/saas?topic=reports-generating-report
