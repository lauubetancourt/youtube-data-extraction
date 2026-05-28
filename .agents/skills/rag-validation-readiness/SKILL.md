---
name: rag-validation-readiness
description: Use this skill to prepare future RAG-based validation of detected YouTube events. It defines evidence needs, event records, retrieval questions, source expectations, and validation labels without implementing RAG.
---

# RAG Validation Readiness

## Proposito
Preparar la trazabilidad y estructura conceptual necesaria para validar eventos detectados mediante RAG en una fase posterior.

## Cuando Usarla
Usala al disenar salidas de deteccion, al definir evidencia posterior o cuando se quiera asegurar que los eventos candidatos seran verificables despues.

## Entradas Esperadas
- Registro conceptual de eventos detectados.
- Definicion de evento y niveles de alerta.
- Ventana temporal de cada evento.
- Comentarios o senales asociadas.
- Fuentes externas potenciales para validacion.

## Procedimiento Paso A Paso
1. Define que informacion minima debe tener un evento para ser validable.
2. Especifica preguntas de recuperacion: que paso, cuando, donde, a quien afecta y con que evidencia.
3. Identifica tipos de fuente aceptables para validacion posterior.
4. Define etiquetas de validacion: confirmado, parcialmente confirmado, no confirmado, ambiguo.
5. Relaciona senales internas con evidencia externa esperada.
6. Registra riesgos de alucinacion, sesgo de fuentes y falta de cobertura.
7. Produce una plantilla de evento listo para RAG.

## Artefactos O Salidas Esperadas
- Plantilla de validacion RAG futura.
- Requisitos minimos del registro de evento.
- Preguntas de recuperacion.
- Criterios de clasificacion de evidencia.
- Lista de riesgos y controles.

## Criterios De Calidad
- Cada evento candidato conserva ventana temporal y senales asociadas.
- Las preguntas de recuperacion son especificas y verificables.
- La validacion distingue evidencia interna y externa.
- Las etiquetas no prometen certeza absoluta.
- La preparacion no depende de un motor RAG especifico.

## Relacion Con CRISP-DM
Corresponde a evaluacion y despliegue futuro. IBM destaca que CRISP-DM organiza resultados y anotaciones por fase; esta skill asegura que la fase de deteccion deje artefactos evaluables posteriormente.

## Relacion Con Las Fases Del Pipeline
- Deteccion: define que debe registrar una alerta.
- Validacion posterior mediante RAG: prepara la fase futura.
- Documentacion: conserva evidencia y decisiones.
- Monitoreo: aporta contexto cuantitativo al evento.

## Limites De La Skill
- No implementa RAG.
- No selecciona base vectorial.
- No consulta fuentes externas.
- No confirma eventos.
- No genera embeddings ni prompts finales.
