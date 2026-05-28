---
name: feature-construction-aggregation
description: Use this skill to specify derived attributes and aggregations for YouTube online event detection under CRISP-DM. It documents activity signals, polarization measures, time windows, formulas, units, and assumptions without writing implementation code.
---

# Feature Construction And Aggregation

## Proposito
Definir de forma metodologica las variables derivadas y agregaciones que convierten comentarios en senales temporales utiles para monitoreo y deteccion.

## Cuando Usarla
Usala despues de definir calidad y seleccion de datos, y antes de auditar senales, umbrales o eventos detectados.

## Entradas Esperadas
- Dataset preparado o esquema esperado.
- Objetivo de deteccion.
- Ventanas temporales candidatas.
- Campos textuales, temporales y de metadatos.
- Medidas existentes de actividad y polarizacion.

## Procedimiento Paso A Paso
1. Enumera atributos crudos disponibles para construir senales.
2. Define cada variable derivada con formula, unidad, granularidad y proposito.
3. Especifica agregaciones por ventana, video, canal o conjunto.
4. Declara supuestos sobre conteos, normalizacion, ausencias y duplicados.
5. Identifica variables que requieren texto preparado o metadatos confiables.
6. Relaciona cada atributo con monitoreo, deteccion o validacion.
7. Documenta riesgos de interpretacion y sensibilidad.

## Artefactos O Salidas Esperadas
- Catalogo de variables derivadas.
- Diccionario de senales.
- Especificacion de ventanas y agregaciones.
- Tabla campo-crudo a atributo-derivado.
- Lista de supuestos y riesgos.

## Criterios De Calidad
- Cada variable tiene definicion reproducible.
- Las agregaciones respetan el tiempo de observacion.
- Las unidades y ventanas son explicitas.
- No se mezclan variables crudas y derivadas sin trazabilidad.
- Las medidas de polarizacion tienen interpretacion documentada.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos. IBM identifica agregacion de registros y derivacion de nuevos atributos como tareas centrales de preparacion antes del modelado.

## Relacion Con Las Fases Del Pipeline
- Preprocesamiento: prepara campos base.
- Simulacion en linea: agrega por ventana temporal.
- Monitoreo: produce senales observables.
- Deteccion: alimenta criterios de evento.
- RAG futuro: aporta resumen cuantitativo del evento.

## Limites De La Skill
- No calcula variables.
- No implementa formulas.
- No selecciona librerias.
- No optimiza rendimiento.
- No decide si una senal es suficiente para declarar evento.
