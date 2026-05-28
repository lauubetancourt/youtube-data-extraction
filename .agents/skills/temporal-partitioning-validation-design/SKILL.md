---
name: temporal-partitioning-validation-design
description: Use this skill to design temporal partitions for calibration, testing, and future validation in online event detection pipelines. It prevents leakage by respecting chronological order and CRISP-DM evaluation needs.
---

# Temporal Partitioning And Validation Design

## Proposito
Definir particiones temporales y criterios de validacion que permitan evaluar el pipeline sin usar informacion futura para decisiones pasadas.

## Cuando Usarla
Usala antes de calibrar lineas base, comparar experimentos, declarar desempeno o preparar validacion posterior.

## Entradas Esperadas
- Cobertura temporal del dataset.
- Objetivo y definicion de evento.
- Ventanas de simulacion en linea.
- Senales candidatas.
- Necesidades de evaluacion o RAG futuro.

## Procedimiento Paso A Paso
1. Identifica la unidad temporal minima y la ventana operacional.
2. Divide periodos para exploracion, calibracion, prueba y validacion posterior.
3. Verifica que ninguna metrica de decision use datos posteriores a la ventana evaluada.
4. Define reglas para eventos que cruzan limites de particion.
5. Documenta criterios de comparacion entre experimentos.
6. Registra limitaciones por pocos datos, huecos temporales o eventos escasos.
7. Produce un plan de validacion temporal reproducible.

## Artefactos O Salidas Esperadas
- Plan de particion temporal.
- Calendario de ventanas de calibracion, prueba y validacion.
- Reglas contra fuga de informacion.
- Matriz experimento-periodo.
- Riesgos de evaluacion temporal.

## Criterios De Calidad
- La particion respeta cronologia.
- Calibracion, prueba y validacion estan separadas conceptualmente.
- Las ventanas se pueden reproducir.
- La definicion de evento no se ajusta usando resultados futuros.
- Los huecos temporales se reportan.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos y evaluacion. IBM incluye division en conjuntos de prueba y entrenamiento como tarea de preparacion; en un pipeline en linea, esa division debe adaptarse a secuencias temporales.

## Relacion Con Las Fases Del Pipeline
- Simulacion en linea: define el orden de reproduccion.
- Monitoreo: separa linea base y observacion.
- Deteccion: evita umbrales informados por el futuro.
- Validacion RAG: define ventanas que deben investigarse despues.

## Limites De La Skill
- No calcula metricas.
- No etiqueta eventos.
- No implementa particiones.
- No selecciona modelos.
- No reemplaza la evaluacion empirica.
