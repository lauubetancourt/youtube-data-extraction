# Configuraciones versionables

Cada archivo de este directorio representa una ejecución o metodología concreta.
No se crea un perfil por componente ni se almacenan secretos, datasets u outputs
experimentales aquí.

## Perfiles de compatibilidad

`compatibility/cyclic_current.json` describe el comportamiento vigente del
primer bloque que migrará STAB-PATHS-01:

```text
simulación cíclica
→ señales diarias
→ daily_frequency_baseline
```

El perfil corresponde a la simulación `sim_42fc5b0f114b` y a la variante
vigente del baseline diario con `cooldown_cycles = 0`. No incluye RAG,
adquisición, retrospectiva ni XIAO EMA porque no forman parte de esta ejecución.

Los siguientes valores se conservan temporalmente como
`LEGACY_COMPATIBILITY_DEFAULT`:

- `data/gold/clean_comments.parquet`;
- `experiments/xiao/media/log_3/cyclic_ingestion_simulation`;
- su subdirectorio `daily_frequency_baseline_cooldown_0`.

Estos paths documentan y reproducen la implementación actual; no convierten el
dataset o el experimento histórico en ubicaciones permanentes. Los módulos de
dominio ya reciben paths explícitos; los wrappers legacy conservan defaults
equivalentes únicamente durante la transición. El perfil es la autoridad
externa del flujo integrado, y los defaults legacy solo se retirarán en la Fase
8 tras demostrar que no tienen consumidores.

## Ejecución integrada del bloque cíclico

El entrypoint principal del bloque ya migrado consume el perfil completo con la
CLI común y entrega a cada etapa únicamente su subconfiguración:

```bash
.venv/bin/python scripts/run_cyclic_pipeline.py \
  --config configs/compatibility/cyclic_current.json \
  --output-root outputs/cyclic_current \
  --dry-run
```

`--output-root` evita escribir sobre el directorio histórico del perfil y
reubica el árbol de artefactos conservando sus subdirectorios. Los parámetros
metodológicos —ventanas, señales, umbrales y cooldown— permanecen en el JSON.
La CLI común se limita a `--config`, `--run-id`, `--output-root`, el modo de
ejecución y `--log-level`. El runner actual solo admite el modo protegido;
`--execute` falla antes de generar artefactos.

Los siguientes scripts por etapa permanecen temporalmente como wrappers de
compatibilidad y herramientas de diagnóstico:

- `run_cyclic_ingestion_simulation.py`;
- `run_cyclic_ingestion_orchestrator.py`;
- `run_cyclic_stateful_adapter.py`;
- `run_cyclic_detection_connector.py`;
- `run_cyclic_daily_signals.py`;
- `run_daily_frequency_baseline.py`.

No son una segunda autoridad para nuevas ejecuciones integradas y no deben
recibir nuevos defaults metodológicos. Su posible retiro corresponde a la Fase
8, después de verificar que no existan consumidores necesarios.
