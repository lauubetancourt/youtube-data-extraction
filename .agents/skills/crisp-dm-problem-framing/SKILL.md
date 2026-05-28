---
name: crisp-dm-problem-framing
description: Use this skill when auditing or refining the conceptual framing of a YouTube online event detection pipeline under CRISP-DM. It defines the event concept, project objective, analytical success criteria, assumptions, scope, and decision context before touching data preparation or modeling.
---

# CRISP-DM Problem Framing

## Proposito
Establecer el encuadre metodologico del problema de deteccion de eventos en linea antes de revisar datos, senales o modelos. La skill traduce el objetivo del trabajo de grado en definiciones operativas, alcance, supuestos y criterios de exito auditables.

## Cuando Usarla
Usala al iniciar una auditoria CRISP-DM, al detectar ambiguedad sobre que cuenta como evento, o cuando los resultados tecnicos no esten claramente conectados con el objetivo del prototipo.

## Entradas Esperadas
- Titulo y objetivo general del proyecto.
- Descripcion de usuarios, contexto academico o caso de uso.
- Definicion preliminar de evento en linea.
- Fases existentes del pipeline.
- Restricciones de datos, tiempo, API o validacion.

## Procedimiento Paso A Paso
1. Identifica el objetivo de negocio o investigacion que justifica detectar eventos en comentarios de YouTube.
2. Formula la pregunta de mineria de datos en terminos observables: actividad, polarizacion, cambios temporales y evidencia posterior.
3. Define que es un evento, que no es un evento, y que nivel de evidencia minima se requiere.
4. Declara supuestos, alcance, fuentes permitidas, poblacion analizada y limites de generalizacion.
5. Establece criterios iniciales de exito tecnico y metodologico.
6. Relaciona cada criterio con una fase del pipeline que pueda producir evidencia.
7. Registra decisiones abiertas para resolver en fases posteriores.

## Artefactos O Salidas Esperadas
- Documento de encuadre del problema.
- Definicion operativa de evento en linea.
- Lista de supuestos y exclusiones.
- Criterios de exito y criterios de no exito.
- Mapa objetivo-senal-decision-evidencia.

## Criterios De Calidad
- La definicion de evento es verificable con datos temporales y textuales.
- Los criterios de exito no dependen de intuiciones no documentadas.
- El alcance distingue prototipo, sistema productivo y validacion academica.
- Cada objetivo tiene al menos una evidencia esperada.
- Las limitaciones del corpus de YouTube quedan explicitas.

## Relacion Con CRISP-DM
Corresponde principalmente a comprension del negocio. IBM SPSS Modeler resalta que comprender los objetivos antes de preparar datos ayuda a decidir que datos recopilar y en cuales concentrarse. Esta skill crea esa base antes de la comprension y preparacion de datos.

## Relacion Con Las Fases Del Pipeline
- Extraccion: define que fuentes y periodos son relevantes.
- Preprocesamiento: delimita que limpieza conserva evidencia del evento.
- Simulacion en linea: fija la nocion de deteccion temporal.
- Monitoreo y deteccion: conecta senales con decisiones.
- RAG futuro: anticipa que evidencia externa validara un evento.

## Limites De La Skill
- No implementa codigo.
- No elige algoritmos ni umbrales finales.
- No modifica datos.
- No valida eventos empiricamente.
- No reemplaza la evaluacion posterior del pipeline.
