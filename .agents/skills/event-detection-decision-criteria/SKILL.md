---
name: event-detection-decision-criteria
description: Use this skill to formalize event detection decision criteria for a YouTube online event detection pipeline. It documents thresholds, persistence, multi-signal rules, severity, false positive handling, and audit evidence.
---

# Event Detection Decision Criteria

## Proposito
Formalizar cuando el pipeline debe declarar un evento, una alerta candidata o una no deteccion, usando criterios explicitos y auditables.

## Cuando Usarla
Usala despues de definir senales monitoreadas y antes de evaluar resultados de deteccion.

## Entradas Esperadas
- Definicion operativa de evento.
- Fichas de senales monitoreadas.
- Plan temporal de simulacion.
- Resultados preliminares de alertas, si existen.
- Criterios de exito del proyecto.

## Procedimiento Paso A Paso
1. Define niveles de decision: no alerta, alerta candidata, evento detectado, evento validado.
2. Especifica condiciones por senal: umbral, cambio relativo, persistencia o combinacion.
3. Define reglas para severidad, prioridad y agrupacion de alertas cercanas.
4. Documenta manejo de ruido, datos faltantes y senales contradictorias.
5. Establece evidencia minima para justificar una deteccion.
6. Relaciona cada decision con validacion posterior.
7. Registra casos de borde y criterios de revision manual.

## Artefactos O Salidas Esperadas
- Matriz de decision de eventos.
- Definicion de niveles de alerta.
- Criterios de severidad y persistencia.
- Plantilla de registro de evento detectado.
- Lista de casos limite.

## Criterios De Calidad
- Las reglas son aplicables con datos disponibles en tiempo simulado.
- Los umbrales o criterios tienen justificacion.
- La decision es reproducible.
- Los falsos positivos esperados se reconocen.
- La salida conserva evidencia para revision posterior.

## Relacion Con CRISP-DM
Corresponde a modelado y evaluacion. CRISP-DM exige que el modelo o tecnica responda al objetivo definido y que sus resultados puedan evaluarse. Esta skill hace explicita la logica de decision antes de validarla.

## Relacion Con Las Fases Del Pipeline
- Deteccion: define la logica conceptual.
- Monitoreo: consume senales.
- Simulacion en linea: respeta disponibilidad temporal.
- Validacion RAG: produce eventos candidatos a verificar.

## Limites De La Skill
- No implementa reglas.
- No optimiza umbrales.
- No calcula precision o recall.
- No valida eventos con fuentes externas.
- No cambia la arquitectura del pipeline.
