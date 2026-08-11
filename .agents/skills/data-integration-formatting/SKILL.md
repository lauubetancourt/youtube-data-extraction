---
name: data-integration-formatting
description: Use this skill to define integration and formatting contracts for datasets in a CRISP-DM YouTube event detection pipeline. It covers joins, schemas, canonical fields, data formats, keys, and handoffs between pipeline phases.
---

# Data Integration And Formatting

## Proposito
Establecer contratos de integracion y formato para que comentarios, metadatos, atributos derivados y resultados intermedios puedan circular entre fases con consistencia.

## Cuando Usarla
Usala cuando haya multiples fuentes, archivos intermedios, formatos heterogeneos, uniones por IDs o salidas que alimenten fases posteriores.

## Entradas Esperadas
- Inventario de fuentes.
- Diccionario de campos.
- Esquemas actuales o esperados.
- Archivos intermedios del pipeline.
- Requisitos de monitoreo y deteccion.

## Procedimiento Paso A Paso
1. Identifica entidades principales: comentario, video, canal, ventana, senal y evento.
2. Define llaves primarias y llaves de union.
3. Especifica esquema canonico por entidad o dataset.
4. Documenta formatos de fecha, zona horaria, texto, numericos y valores nulos.
5. Define reglas metodologicas para fusionar, concatenar o separar datasets.
6. Verifica que cada fase reciba los campos que necesita y produzca salidas auditables.
7. Registra inconsistencias de formato como riesgos para preparacion.

## Artefactos O Salidas Esperadas
- Contrato de datos entre fases.
- Esquema canonico.
- Mapa de integracion de fuentes.
- Tabla de formatos permitidos.
- Lista de validaciones de integridad.

## Criterios De Calidad
- Los campos obligatorios y opcionales estan diferenciados.
- Las uniones son trazables y no ambiguas.
- Las fechas tienen formato y zona horaria definidos.
- Los nulos tienen significado documentado.
- Cada salida intermedia tiene consumidor identificado.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos. IBM incluye fusion de conjuntos o registros, integracion de datos y formato de datos como actividades necesarias para preparar datos para mineria.

## Relacion Con Las Fases Del Pipeline
- Extraccion: captura campos base.
- Preprocesamiento: produce datos canonicos.
- Simulacion en linea: consume secuencias temporales consistentes.
- Monitoreo: consume ventanas y senales.
- Deteccion: produce eventos con campos normalizados.

## Limites De La Skill
- No migra archivos.
- No escribe validadores.
- No cambia nombres de columnas.
- No decide almacenamiento fisico.
- No implementa integraciones externas.
