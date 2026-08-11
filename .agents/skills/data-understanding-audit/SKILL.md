---
name: data-understanding-audit
description: Use this skill to perform the CRISP-DM data understanding audit for YouTube comment datasets. It guides descriptive exploration of volume, time coverage, distributions, language, relationships, outliers, and preliminary patterns before data preparation.
---

# Data Understanding Audit

## Proposito
Guiar una exploracion metodologica de los datos disponibles para entender estructura, cobertura, patrones y riesgos antes de preparar, modelar o detectar eventos.

## Cuando Usarla
Usala despues del inventario de fuentes y antes de limpieza, seleccion de muestras o construccion de senales.

## Entradas Esperadas
- Inventario de fuentes y campos.
- Muestras o resumenes de comentarios.
- Metadatos temporales de videos y comentarios.
- Conteos por video, canal, periodo y lote.
- Cualquier informe exploratorio existente.

## Procedimiento Paso A Paso
1. Describe el tamano del corpus por unidad relevante: comentario, video, canal, periodo y ejecucion.
2. Revisa cobertura temporal, huecos, concentraciones y cambios de volumen.
3. Examina distribuciones de campos clave: fechas, longitud de texto, idioma, likes, respuestas y autor.
4. Identifica relaciones preliminares entre actividad, polarizacion, video y tiempo.
5. Senala valores extremos, ausentes y patrones sospechosos para la skill de calidad.
6. Documenta hallazgos con tablas, graficos o resumenes.
7. Distingue hallazgos descriptivos de interpretaciones sobre eventos.

## Artefactos O Salidas Esperadas
- Informe de comprension de datos.
- Perfil descriptivo del corpus.
- Lista de patrones preliminares.
- Lista de riesgos para preparacion.
- Preguntas abiertas para limpieza o seleccion.

## Criterios De Calidad
- La exploracion cubre estructura, relaciones y patrones.
- Los hallazgos estan vinculados a campos concretos.
- La cobertura temporal queda claramente descrita.
- Los riesgos no se mezclan con decisiones de implementacion.
- Las visualizaciones o tablas son interpretables y reproducibles.

## Relacion Con CRISP-DM
Corresponde a comprension de datos. IBM senala que esta fase estudia los datos disponibles para evitar problemas en preparacion, usando tablas, graficos, estadisticas y documentacion de resultados.

## Relacion Con Las Fases Del Pipeline
- Extraccion: verifica cobertura y suficiencia inicial.
- Preprocesamiento: informa problemas esperados.
- Simulacion en linea: revisa continuidad temporal.
- Monitoreo: anticipa escalas normales de actividad.
- Deteccion: evita interpretar anomalias de datos como eventos.

## Limites De La Skill
- No limpia datos.
- No selecciona la muestra final.
- No declara eventos.
- No ajusta modelos.
- No reemplaza el informe de calidad de datos.
