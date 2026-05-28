---
name: signal-monitoring-spec
description: Use this skill to specify monitored activity and polarization signals for an online event detection pipeline. It documents signal definitions, windows, baselines, expected behavior, visualizations, and alert inputs under CRISP-DM.
---

# Signal Monitoring Specification

## Proposito
Definir las senales que el pipeline monitorea, sus formulas conceptuales, ventanas, lineas base, interpretacion y evidencia esperada.

## Cuando Usarla
Usala despues de construir el catalogo de variables y antes de revisar criterios de deteccion.

## Entradas Esperadas
- Catalogo de variables derivadas.
- Plan de simulacion en linea.
- Definicion de evento.
- Series temporales o resumenes de actividad.
- Medidas de polarizacion disponibles.

## Procedimiento Paso A Paso
1. Enumera senales de actividad, polarizacion y contexto.
2. Define formula conceptual, unidad, ventana y granularidad de cada senal.
3. Especifica linea base, periodo de referencia o comparador.
4. Describe comportamiento esperado en condiciones normales y anomalas.
5. Define visualizaciones o tablas necesarias para auditoria.
6. Relaciona senales con criterios de decision posteriores.
7. Registra incertidumbres, ruido esperado y dependencia de calidad de datos.

## Artefactos O Salidas Esperadas
- Ficha tecnica por senal.
- Matriz senal-ventana-linea base.
- Interpretacion metodologica de cada senal.
- Lista de visualizaciones esperadas.
- Riesgos de ruido y sensibilidad.

## Criterios De Calidad
- Cada senal tiene significado y formula reproducible.
- La linea base no usa informacion futura.
- La interpretacion distingue correlacion, actividad y evento.
- Las medidas de polarizacion explican su escala.
- Las senales son trazables hasta datos preparados.

## Relacion Con CRISP-DM
Corresponde a modelado en sentido experimental y se apoya en preparacion de datos. IBM incluye clasificar datos para modelado y derivar atributos; esta skill organiza esos atributos como senales monitoreables.

## Relacion Con Las Fases Del Pipeline
- Monitoreo: define que observar.
- Simulacion en linea: define frecuencia de actualizacion.
- Deteccion: provee entradas a reglas de evento.
- Evaluacion futura: permite explicar por que se genero una alerta.

## Limites De La Skill
- No calcula senales.
- No genera graficas.
- No declara eventos.
- No ajusta umbrales automaticamente.
- No sustituye analisis estadistico posterior.
