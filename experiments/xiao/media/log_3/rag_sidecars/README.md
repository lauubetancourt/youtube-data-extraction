# Sidecars RAG 1/RAG 2

## 1. Proposito

Esta carpeta contiene artefactos sidecar para preparar evidencia y unidades de
contexto de una futura fase de validacion RAG.

Estos archivos no ejecutan validacion generativa. No llaman modelos, no crean
embeddings, no modifican la deteccion y no reemplazan los outputs actuales del
PoC. Su funcion es dejar la evidencia interna organizada, trazable y lista para
un consumidor RAG posterior.

## 2. Artefactos incluidos

### `event_evidence_packages.jsonl`

Contiene un paquete de evidencia por evento detectado.

- Llave principal: `event_id`.
- Relaciona el evento con su ventana temporal, conteos de comentarios, videos,
  senales disponibles y rutas a los demas sidecars.
- Sirve como punto de entrada para una futura fase RAG.

### `event_comment_inventory.csv`

Contiene el inventario completo de comentarios asociados a cada evento, video y
ventana temporal.

- Llave principal recomendada: `event_id` + `comment_id`.
- Conserva `trigger_time`, `video_id`, `window_start`, `window_end`,
  `event_time_utc`, `text`, `text_clean`, `is_reply`, `parent_comment_id`,
  `root_comment_id` y `comment_source_path`.
- Sirve como evidencia completa. Ninguna unidad de contexto debe reemplazarlo.

### `event_video_map.csv`

Contiene la relacion entre eventos globales y videos asociados.

- Llave principal recomendada: `event_id` + `video_id`.
- Preserva la compatibilidad con la unidad del PoC basada en
  `trigger_time + video_id`.
- Sirve para saber que videos contribuyen a un evento global.

### `event_thread_map.csv`

Contiene una vista de hilos o grupos derivados de comentarios raiz y respuestas.

- Llave principal recomendada: `event_id` + `video_id` + `root_comment_id`.
- Indica si el comentario raiz esta presente, cuantos comentarios tiene el hilo
  y si contiene respuestas.
- Sirve para distinguir hilos completos de hilos parciales.

### `rag_context_units.jsonl`

Contiene unidades de contexto derivadas del inventario completo.

- Llave principal: `context_unit_id`.
- Cada unidad conserva `event_id`, `trigger_time`, `video_id`, ventana temporal,
  `context_type`, lista de `comment_ids`, conteo de comentarios, rango temporal
  real, razon de agrupacion y ruta al inventario fuente.
- Sirve como vista compacta para una futura fase RAG, sin reemplazar la
  evidencia completa.

### `context_unit_comment_map.csv`

Contiene la relacion normalizada entre unidades de contexto y comentarios.

- Llave principal recomendada: `context_unit_id` + `comment_id`.
- Permite recuperar todos los comentarios originales que sustentan una unidad
  de contexto.
- Debe usarse para auditoria fina de trazabilidad.

### `context_selection_manifest.json`

Contiene metadatos de ejecucion, politica de compatibilidad, formula de
`event_id`, regla de inclusion de comentarios, politica de contexto, conteos y
verificaciones de cobertura.

- Llave principal: `run_id`.
- Sirve para reproducibilidad y revision metodologica.

## 3. Identificacion de eventos

`event_id` representa un evento global por trigger y ventana temporal. No
representa un par evento-video.

Un evento puede estar asociado a varios videos. La relacion evento-video debe
consultarse en `event_video_map.csv`.

La clave `trigger_time + video_id` se conserva como referencia de compatibilidad
con el PoC actual. Los sidecars agregan `event_id` como identificador interno
retrocompatible, pero no eliminan ni reemplazan las claves actuales.

Formula actual:

```text
evt_ + sha1(run_id|detector_name|trigger_time_utc|window_start_utc|window_end_utc)[:12]
```

## 4. Regla de inclusion de comentarios

La regla de inclusion usada para construir el inventario completo es:

```text
window_start <= event_time_utc <= window_end
AND video_id asociado al evento en trigger_comment_map
```

Esta regla permite inventariar todos los comentarios asociados al evento, video
y ventana temporal correspondiente. Incluye comentarios principales y respuestas
cuando existen en los datos fuente.

No se traen comentarios fuera de la ventana de evidencia sin aprobacion
metodologica posterior.

## 5. Evidencia completa vs. unidades de contexto

La evidencia completa esta en `event_comment_inventory.csv`. Ese archivo es el
inventario auditable de comentarios originales asociados a los eventos.

Las unidades de contexto estan en `rag_context_units.jsonl`. Son vistas
derivadas para manejar limites de contexto en una futura fase RAG. Pueden agrupar
comentarios por hilo o por bloque temporal de video.

Las unidades de contexto no reemplazan el inventario completo. Si una unidad se
usa en un prompt futuro, debe poder rastrearse a sus `comment_ids` y luego al
inventario.

## 6. Hilos y respuestas

`is_reply` indica que un comentario es respuesta a otro comentario.

`parent_comment_id` identifica el comentario padre cuando esa metadata existe.
`root_comment_id` representa el comentario raiz usado para agrupar el hilo.

Una reply puede tener padre fuera de la ventana. En ese caso, el comentario padre
puede existir en el dataset gold, pero no forma parte de la evidencia del evento
porque no cumple la regla temporal aprobada.

Un hilo parcial es un hilo en el que aparece una reply, pero el comentario padre
no esta dentro del inventario del evento. Esto no es un error. Es una
consecuencia de respetar la ventana temporal.

Los padres fuera de ventana no se traen automaticamente porque eso cambiaria la
regla de evidencia y podria introducir informacion que no pertenece a la ventana
del evento.

## 7. Trazabilidad recomendada

Ruta recomendada para auditar evidencia:

```text
event_id
-> event_video_map.csv
-> event_comment_inventory.csv
-> rag_context_units.jsonl
-> context_unit_comment_map.csv
```

Para recuperar los comentarios originales desde una unidad de contexto:

1. Tome `context_unit_id` en `rag_context_units.jsonl`.
2. Busque ese `context_unit_id` en `context_unit_comment_map.csv`.
3. Recupere la lista de `comment_id`.
4. Una esos `comment_id` con `event_comment_inventory.csv` usando
   `event_id + comment_id`.
5. Consulte `text`, `text_clean`, `event_time_utc`, `video_id`,
   `is_reply`, `parent_comment_id` y `comment_source_path`.

## 8. Compatibilidad

Estos sidecars:

- no reemplazan outputs actuales;
- no modifican el pipeline;
- no modifican el PoC;
- no modifican `trigger_comment_map.csv`;
- no modifican `snapshots.csv`;
- no modifican `clean_comments.parquet`;
- no cambian deteccion, monitoreo, simulacion ni preprocesamiento.

El PoC actual basado en `trigger_time + video_id` puede seguir funcionando sin
cambios.

## 9. Limitaciones conocidas

- Todavia no hay validacion generativa.
- No hay embeddings.
- No hay ranking semantico.
- No hay resumen generativo.
- Puede haber asignacion multiple de comentarios si en futuras corridas existen
  ventanas solapadas.
- `event_id` depende de `run_id`; por tanto, `run_id` debe usarse correctamente
  para distinguir ejecuciones.
- Algunos hilos pueden ser parciales cuando la reply esta dentro de la ventana,
  pero el comentario padre esta fuera de ella.

## 10. Uso futuro

Estos sidecars son la base para disenar un consumidor RAG posterior. Ese
consumidor deberia leer paquetes de evidencia, seleccionar unidades de contexto
trazables y producir reportes de validacion sin alterar la deteccion actual.

La secuencia metodologica recomendada es:

```text
Sidecars aprobados
-> README de sidecars
-> diseno del consumidor RAG
-> implementacion minima del consumidor
-> validacion controlada con pocos eventos
-> reporte de resultados
```
