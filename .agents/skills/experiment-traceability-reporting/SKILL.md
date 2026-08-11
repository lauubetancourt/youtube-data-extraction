---
name: experiment-traceability-reporting
description: Use this skill to organize CRISP-DM experiment traceability and reporting for the YouTube event detection pipeline. It documents runs, parameters, datasets, decisions, outputs, annotations, and reproducibility evidence.
---

# Experiment Traceability And Reporting

## Proposito
Crear una estructura metodologica para registrar experimentos, decisiones, artefactos y resultados por fase CRISP-DM, permitiendo auditoria y reproducibilidad.

## Cuando Usarla
Usala transversalmente durante la auditoria y al cerrar cada fase revisada del pipeline.

## Entradas Esperadas
- Lista de fases del pipeline.
- Inventario de datasets y versiones.
- Configuraciones o parametros experimentales.
- Resultados intermedios y finales.
- Decisiones metodologicas tomadas.

## Procedimiento Paso A Paso
1. Define una unidad de ejecucion o experimento.
2. Registra dataset, parametros, fecha, version y objetivo de cada ejecucion.
3. Relaciona artefactos con fases CRISP-DM: negocio, datos, preparacion, modelado, evaluacion y despliegue.
4. Documenta decisiones, justificaciones y riesgos residuales.
5. Vincula salidas con insumos mediante linaje.
6. Produce reportes de estado por fase y por experimento.
7. Mantiene una lista de pendientes para la siguiente iteracion CRISP-DM.

## Artefactos O Salidas Esperadas
- Bitacora de experimentos.
- Reporte CRISP-DM por fase.
- Registro de decisiones metodologicas.
- Matriz artefacto-fase-pipeline.
- Lista de pendientes y riesgos residuales.

## Criterios De Calidad
- Cada resultado puede rastrearse hasta datos y parametros.
- Las decisiones importantes tienen justificacion.
- Los artefactos estan organizados por fase.
- La reproducibilidad no depende de memoria personal.
- El reporte permite revisar avances y problemas no resueltos.

## Relacion Con CRISP-DM
Corresponde a todas las fases. IBM SPSS Modeler destaca que CRISP-DM organiza rutas, resultados y anotaciones, y que los informes de proyecto son componentes cruciales para una mineria de datos eficaz.

## Relacion Con Las Fases Del Pipeline
- Extraccion a validacion RAG: registra entradas, salidas y decisiones.
- Auditoria: organiza evidencias de cumplimiento metodologico.
- Refinamiento posterior: indica que cambiar, por que y con que riesgo.

## Limites De La Skill
- No ejecuta experimentos.
- No modifica resultados.
- No decide cambios de implementacion.
- No reemplaza control de versiones.
- No genera metricas automaticamente.
