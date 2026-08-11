# Reporte de limpieza de estabilización

- `executed_at`: `2026-08-08T16:50:34-05:00`
- `status`: `SUCCESS`
- `scope`: Eliminación controlada del conjunto `READY_FOR_DELETE` aprobado para artefactos experimentales y temporales.
- `files_deleted`: `1367`
- `bytes_recovered`: `1109940443`
- `recovered_gib`: `1.034`
- `experiments_xiao_bytes_before`: `1295653579`
- `experiments_xiao_bytes_after`: `186743458`

## Grupos eliminados

| Grupo | Archivos | Bytes |
|---|---:|---:|
| Detalle prescindible de `run_20260602T180213Z` | 355 | 365202998 |
| `run_20260602T180515Z` completo | 354 | 347767395 |
| Detalle prescindible de `run_20260602T180842Z` | 604 | 372233934 |
| `experiments/xiao/alta/log_1` | 3 | 18855576 |
| `experiments/xiao/baja/log_2` | 4 | 4837922 |
| `.DS_Store`, `__pycache__` y bytecode Python aprobados | 47 | 1042618 |

## Evidencia preservada

### `run_20260602T180213Z`

Se conservaron exactamente cuatro archivos:

- `audit/input_audit.json`
- `run_manifest.json`
- `detection/trigger_log.txt`
- `detection/summary.md`

La evidencia conserva la configuración XIAO con `v_min=46`, el replay de 178289 elementos y el resultado de cero triggers.

### `run_20260602T180842Z`

Se conservaron exactamente 23 archivos: configuración y reporte de ejecución, log y resumen de detección, lista de eventos, mapa evento-video, resultados consolidados G-1/G-2, reporte de auditoría de validación y 15 archivos no vacíos de evidencia externa.

Las comprobaciones realizadas únicamente con la evidencia restante dieron:

- eventos: `18`
- asociaciones evento-video: `84`
- asociaciones evento-comentario: `325`
- G-1: `18/18`
- G-2: `79/84`
- videos pendientes: `5`

## Elementos bloqueados e intactos

- `experiments/xiao/media/log_3/`
- `experiments/xiao/media/log_3/cyclic_ingestion_simulation/`
- `data/caso-uribe/`
- `data/comments.csv`
- `data/videos_preliminares.csv`
- `data/bronze/`
- `data/silver/`
- `data/gold/`
- `.venv/`
- `.agents/examples/`

El fingerprint conjunto de los datos y artefactos bloqueados comprobados permaneció sin cambios: `c1f82a64a147f368a8aadf9a50a820d9ac46b9131f012714eb7872828dc31099`.

`data/videos.csv` permanece intacto y en estado `REQUIRES_REVIEW`.

## Trazabilidad y seguridad

El contexto experimental se conserva en [retrospective_experiment_registry.md](retrospective_experiment_registry.md). `run_20260602T180515Z` ya no existe y queda representada únicamente en ese registro.

No se modificaron código, tests, configuración, manifests históricos ni `.gitignore`; no se ejecutaron pipelines, RAG o APIs. El fingerprint de implementación permaneció sin cambios: `699f50e6fb214226cba40b4f83be8ef276d152875a43ef4aa7ccbd46cda4b8f8`.

La eliminación fue directa, no un movimiento a archivo o papelera. La recuperación de los artefactos retirados requeriría una copia de seguridad externa o su regeneración cuando sea posible.
