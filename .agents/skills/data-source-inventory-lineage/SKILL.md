---
name: data-source-inventory-lineage
description: Use this skill to inventory YouTube data sources and document lineage for a CRISP-DM audit. It captures videos, channels, queries, dates, fields, extraction runs, data ownership, and traceability from raw comments to prepared datasets.
---

# Data Source Inventory And Lineage

## Proposito
Documentar de forma trazable de donde vienen los datos, como fueron extraidos y que transformaciones conceptuales conectan cada archivo o tabla con las fases del pipeline.

## Cuando Usarla
Usala antes de evaluar calidad, limpieza, agregaciones o deteccion. Tambien usala cuando existan multiples archivos, ejecuciones de extraccion, videos, canales, ventanas temporales o versiones de dataset.

## Entradas Esperadas
- Lista de archivos o tablas de datos.
- Parametros de extraccion disponibles.
- Metadatos de videos, canales y comentarios.
- Fechas de extraccion y rangos temporales.
- Estructura de carpetas y nombres de datasets.

## Procedimiento Paso A Paso
1. Enumera cada fuente de datos y su proposito dentro del proyecto.
2. Registra campos disponibles, tipos esperados y significado semantico.
3. Identifica llaves de trazabilidad: video, canal, comentario, autor anonimo, fecha y lote de extraccion.
4. Describe el flujo desde dato crudo hasta dato preparado sin proponer cambios de codigo.
5. Marca fuentes incompletas, duplicadas, derivadas o no verificadas.
6. Relaciona cada dataset con una fase CRISP-DM y una fase del pipeline.
7. Produce una matriz de linaje que permita reproducir que salida depende de que entrada.

## Artefactos O Salidas Esperadas
- Inventario de fuentes.
- Diccionario de campos.
- Matriz de linaje de datos.
- Registro de ejecuciones de extraccion.
- Lista de brechas de trazabilidad.

## Criterios De Calidad
- Cada dataset tiene origen, fecha, alcance y responsable logico.
- Los campos derivados se distinguen de los campos crudos.
- Las llaves de union y trazabilidad estan documentadas.
- Las versiones de datos se pueden diferenciar.
- Las brechas se reportan sin ocultar incertidumbre.

## Relacion Con CRISP-DM
Corresponde a comprension de datos y prepara la fase de preparacion. IBM indica que la comprension de datos implica acceder, explorar y documentar datos para determinar su calidad, y que CRISP-DM organiza rutas, resultados y anotaciones por fase.

## Relacion Con Las Fases Del Pipeline
- Extraccion: documenta fuentes y parametros.
- Preprocesamiento: identifica campos crudos y transformados.
- Simulacion en linea: conserva orden temporal y procedencia.
- Monitoreo/deteccion: permite rastrear una alerta hasta comentarios originales.
- Validacion RAG: preserva contexto para evidencia posterior.

## Limites De La Skill
- No descarga datos.
- No reestructura archivos.
- No anonimiza ni transforma contenido.
- No evalua rendimiento de modelos.
- No define reglas de limpieza.
