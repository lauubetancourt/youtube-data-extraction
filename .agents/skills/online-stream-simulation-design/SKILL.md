---
name: online-stream-simulation-design
description: Use this skill to specify the design of an online stream simulation for YouTube comments. It documents ordering, windows, state, latency assumptions, replay rules, and audit evidence without changing pipeline code.
---

# Online Stream Simulation Design

## Proposito
Especificar como los comentarios historicos se reproducen como flujo en linea para que monitoreo y deteccion se evalen bajo restricciones temporales realistas.

## Cuando Usarla
Usala al auditar la fase de simulacion, especialmente si el pipeline procesa lotes historicos pero pretende representar deteccion en linea.

## Entradas Esperadas
- Dataset con timestamps.
- Plan de particion temporal.
- Definicion de ventana y frecuencia de actualizacion.
- Estado esperado del simulador.
- Salidas intermedias actuales.

## Procedimiento Paso A Paso
1. Define la unidad de llegada: comentario individual, lote o ventana.
2. Establece ordenamiento temporal y desempates.
3. Declara supuestos de latencia, disponibilidad y acumulacion de datos.
4. Especifica que estado se conserva entre ventanas.
5. Define que informacion esta disponible en cada instante simulado.
6. Registra entradas y salidas por paso de simulacion.
7. Documenta diferencias entre simulacion historica y despliegue real.

## Artefactos O Salidas Esperadas
- Especificacion de simulacion en linea.
- Diagrama temporal de flujo.
- Reglas de ventana y acumulacion.
- Contrato de entrada/salida por tick o ventana.
- Lista de supuestos de latencia.

## Criterios De Calidad
- El simulador no usa informacion futura.
- El orden temporal es determinista y documentado.
- El estado entre ventanas es explicito.
- Las salidas permiten reproducir una alerta.
- Las limitaciones de simulacion quedan visibles.

## Relacion Con CRISP-DM
Se ubica entre preparacion de datos, modelado y despliegue experimental. IBM senala que los datos deben prepararse y empaquetarse para mineria; aqui el empaquetamiento requerido es un flujo temporal apto para deteccion en linea.

## Relacion Con Las Fases Del Pipeline
- Simulacion de flujo en linea: especifica la fase completa.
- Monitoreo: entrega ventanas ordenadas.
- Deteccion: controla disponibilidad temporal de senales.
- Evaluacion futura: permite reconstruir decisiones.

## Limites De La Skill
- No implementa el simulador.
- No optimiza rendimiento.
- No consume APIs en tiempo real.
- No define umbrales de alerta.
- No cambia almacenamiento de datos.
