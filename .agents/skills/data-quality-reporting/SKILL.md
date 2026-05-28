---
name: data-quality-reporting
description: Use this skill to produce a CRISP-DM data quality report for YouTube comment data. It focuses on missing values, duplicates, coding inconsistencies, metadata errors, temporal anomalies, and documented treatment decisions before modeling.
---

# Data Quality Reporting

## Proposito
Establecer un informe de calidad de datos que documente problemas, severidad, impacto y decisiones metodologicas sobre datos crudos y preparados.

## Cuando Usarla
Usala despues de la comprension de datos y antes de fijar el dataset preparado o las senales del pipeline.

## Entradas Esperadas
- Inventario de fuentes.
- Informe de comprension de datos.
- Diccionario de campos.
- Reglas existentes de limpieza o exclusion.
- Muestras de registros problematicos.

## Procedimiento Paso A Paso
1. Lista dimensiones de calidad relevantes: completitud, unicidad, validez, consistencia, oportunidad temporal y trazabilidad.
2. Evalua valores faltantes, blancos, duplicados y campos imposibles.
3. Revisa errores de codificacion, formatos inconsistentes y metadatos sospechosos.
4. Identifica problemas propios de YouTube: comentarios eliminados, timestamps, autores anonimizados, spam o repeticion.
5. Clasifica cada problema por severidad e impacto sobre actividad, polarizacion y deteccion.
6. Registra decision recomendada a nivel metodologico: excluir, imputar, marcar, conservar o revisar.
7. Produce un informe que sirva como punto de partida para preparacion de datos.

## Artefactos O Salidas Esperadas
- Informe de calidad de datos.
- Tabla de problemas por campo o dataset.
- Registro de decisiones de tratamiento.
- Lista de riesgos residuales.
- Criterios de aceptacion del dataset preparado.

## Criterios De Calidad
- Cada problema tiene evidencia y ubicacion.
- Las decisiones distinguen impacto tecnico e impacto conceptual.
- No se eliminan registros sin justificacion.
- Las decisiones son reproducibles y auditables.
- El informe puede alimentar la limpieza sin depender de memoria informal.

## Relacion Con CRISP-DM
Corresponde a comprension de datos y preparacion. IBM indica que la limpieza observa problemas en los datos seleccionados y trata faltantes, errores, inconsistencias de codificacion y metadatos incorrectos; el informe de calidad de datos sirve como punto inicial para manipular datos.

## Relacion Con Las Fases Del Pipeline
- Extraccion: detecta problemas de captura.
- Preprocesamiento: fundamenta limpieza.
- Simulacion en linea: evita secuencias temporales invalidas.
- Monitoreo: reduce ruido de senales.
- Deteccion: disminuye falsos eventos causados por calidad baja.

## Limites De La Skill
- No ejecuta limpieza.
- No define modelos de imputacion complejos.
- No borra datos.
- No corrige codigo.
- No certifica que el dataset sea perfecto.
