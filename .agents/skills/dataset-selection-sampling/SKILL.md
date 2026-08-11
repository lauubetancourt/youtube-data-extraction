---
name: dataset-selection-sampling
description: Use this skill to define dataset selection and sampling criteria for CRISP-DM audits of YouTube event detection experiments. It covers inclusion, exclusion, temporal scope, representativeness, bias, and experiment subsets.
---

# Dataset Selection And Sampling

## Proposito
Formalizar criterios para seleccionar videos, comentarios, periodos y subconjuntos experimentales, manteniendo coherencia con el objetivo de deteccion de eventos.

## Cuando Usarla
Usala antes de comparar experimentos, definir corpus de prueba, recortar datos o justificar por que ciertos videos o ventanas temporales fueron analizados.

## Entradas Esperadas
- Inventario de fuentes.
- Encadre del problema.
- Cobertura temporal y volumen de datos.
- Restricciones de API o disponibilidad.
- Objetivos de los experimentos iniciales.

## Procedimiento Paso A Paso
1. Define unidad de seleccion: video, canal, comentario, ventana temporal o lote.
2. Especifica criterios de inclusion y exclusion.
3. Evalua sesgos esperados por disponibilidad, popularidad, idioma, tema o periodo.
4. Define si la muestra es exploratoria, calibracion, prueba o demostracion.
5. Documenta el impacto de la seleccion sobre actividad y polarizacion.
6. Verifica que la seleccion respete el orden temporal cuando aplique.
7. Registra limitaciones de representatividad y generalizacion.

## Artefactos O Salidas Esperadas
- Protocolo de seleccion de datos.
- Tabla de criterios de inclusion/exclusion.
- Descripcion de muestra o subconjunto.
- Registro de sesgos y limitaciones.
- Mapa de datasets por experimento.

## Criterios De Calidad
- La muestra responde al objetivo declarado.
- La exclusion de datos tiene justificacion.
- La representatividad no se sobreafirma.
- Se diferencia exploracion de evaluacion.
- Las particiones temporales no mezclan futuro con pasado.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos. IBM incluye seleccion de muestras o subconjuntos como tarea tipica de preparacion, y la conecta con objetivos de la organizacion y comprension previa de datos.

## Relacion Con Las Fases Del Pipeline
- Extraccion: decide que datos son pertinentes.
- Preprocesamiento: delimita corpus preparado.
- Simulacion en linea: define secuencias disponibles.
- Monitoreo/deteccion: condiciona linea base y sensibilidad.
- Evaluacion futura: permite interpretar resultados.

## Limites De La Skill
- No extrae datos nuevos.
- No balancea datos automaticamente.
- No define umbrales de deteccion.
- No garantiza representatividad estadistica.
- No modifica archivos del pipeline.
