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
dominio todavía contienen defaults equivalentes durante la transición. El
perfil será la autoridad externa cuando cada etapa migre al resolver común, y
los defaults legacy solo se retirarán en la Fase 8 tras demostrar que no tienen
consumidores.
