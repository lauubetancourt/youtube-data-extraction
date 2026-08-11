---
name: text-preprocessing-spec
description: Use this skill to specify NLP preprocessing rules for YouTube comments in a CRISP-DM pipeline. It documents normalization, language handling, spam treatment, URLs, emojis, punctuation, duplicates, and preservation of raw text without implementing code.
---

# Text Preprocessing Specification

## Proposito
Definir una especificacion metodologica para preparar texto de comentarios de YouTube de forma consistente, trazable y adecuada para senales de actividad y polarizacion.

## Cuando Usarla
Usala cuando el pipeline tenga reglas implicitas de limpieza textual, cuando se comparen experimentos, o antes de construir variables de polarizacion.

## Entradas Esperadas
- Campos textuales crudos.
- Informe de calidad de datos.
- Objetivo de analisis textual.
- Reglas existentes de normalizacion.
- Ejemplos de comentarios representativos y problematicos.

## Procedimiento Paso A Paso
1. Define que campo textual se conserva como version cruda inmutable.
2. Especifica versiones preparadas del texto y el proposito de cada una.
3. Documenta reglas para mayusculas, acentos, signos, emojis, URLs, menciones, hashtags y espacios.
4. Define tratamiento de idioma, spam, duplicados textuales y comentarios vacios.
5. Establece que informacion no debe eliminarse si puede ser senal de polarizacion o evento.
6. Relaciona cada regla con impacto esperado en actividad, polarizacion o validacion.
7. Crea ejemplos antes/despues para auditar la aplicacion.

## Artefactos O Salidas Esperadas
- Especificacion de preprocesamiento textual.
- Tabla de reglas y justificacion.
- Ejemplos antes/despues.
- Lista de decisiones sensibles.
- Contrato entre texto crudo y texto preparado.

## Criterios De Calidad
- El texto crudo permanece recuperable.
- Las reglas no destruyen evidencia relevante sin justificacion.
- Las decisiones son consistentes entre experimentos.
- Cada transformacion tiene proposito analitico.
- Los casos limite estan documentados.

## Relacion Con CRISP-DM
Corresponde a preparacion de datos. IBM incluye eliminacion o sustitucion de valores perdidos, formato, derivacion de atributos y preparacion de datos para mineria. En datos textuales, estas tareas se traducen en normalizacion y representaciones textuales controladas.

## Relacion Con Las Fases Del Pipeline
- Preprocesamiento: especifica reglas de limpieza NLP.
- Monitoreo: protege senales derivadas de texto.
- Deteccion: reduce decisiones ambiguas.
- Validacion RAG: conserva texto original para evidencia posterior.

## Limites De La Skill
- No implementa tokenizacion ni modelos NLP.
- No decide librerias.
- No entrena clasificadores.
- No traduce automaticamente comentarios.
- No elimina contenido sin criterio documentado.
