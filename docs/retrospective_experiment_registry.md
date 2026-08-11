# Registro consolidado de experimentos retrospectivos

Este registro conserva las decisiones y los resultados relevantes de las corridas retrospectivas de desarrollo. No convierte las corridas en casos de uso oficiales ni exige conservar sus materializaciones completas.

## Dataset experimental compartido

- `dataset_role`: `retrospective_experimental_input`
- `logical_name`: `caso-uribe-retrospective-input`
- `canonical_project_dataset`: `false`
- `videos_rows`: `706`
- `comments_rows_raw`: `185874`
- `comments_unique_ids`: `185865`
- `comment_time_min_utc`: `2025-02-23T10:48:53+00:00`
- `comment_time_max_utc`: `2025-09-20T18:29:49+00:00`
- `videos_sha256`: `f1af37c9bb00384ed69d07f662767a4bddf6eff86f7fea1a8dbe13d87fc6922e`
- `comments_sha256`: `d8bcae801df267487b20149fced8d8bf8b30e9f0fbb27d092c2529b3fa2ec0b4`
- `dataset_fingerprint`: `c25923f719df2d809be1d5af5b0a36110affee9bca81b60afaf6853b7e6d03c7`
- `fingerprint_formula`: `SHA256("videos:<videos_sha256>\ncomments:<comments_sha256>\n")`

`data/caso-uribe/` es el input experimental de esta familia retrospectiva. Su uso en estas corridas no le asigna carácter canónico ni permanencia definitiva en el proyecto.

## run_20260602T180213Z

- `experiment_id`: `run_20260602T180213Z`
- `classification`: `calibration_run`
- `purpose`: Evaluar un replay retrospectivo completo con la configuración XIAO disponible y comprobar si producía activaciones sobre el corpus experimental.
- `dataset_fingerprint`: `c25923f719df2d809be1d5af5b0a36110affee9bca81b60afaf6853b7e6d03c7`
- `relevant_configuration`: `detector=xiao_ema; window_size=120s; slide_interval=30s; slow_window=10min; sensitivity_threshold=1.5; v_min=46; cooldown=3min; monitoring_window=20min`
- `main_result`: Replay completo de `178289` elementos; `178289` snapshots; `0` triggers; `0` asociaciones trigger-comentario.
- `methodological_or_architectural_decision`: Esta parametrización no produjo activaciones sobre este corpus experimental y no fue utilizada como configuración principal de la integración retrospectiva posterior.
- `limitations`: El resultado es específico del corpus y de la configuración evaluada. No demuestra que `v_min=46` sea inválido universalmente. La revisión exacta del código ejecutado no quedó registrada.
- `preservation_status`: `compact_evidence_in_place`; se conservan manifest, auditoría JSON, trigger log y resumen.
- `removal_status`: `detail_ready_for_delete`; pueden retirarse materializaciones del dataset, snapshot y auxiliares no informativos.

## run_20260602T180515Z

- `experiment_id`: `run_20260602T180515Z`
- `classification`: `development_run_interrupted`
- `purpose`: Intento de ejecución retrospectiva local durante el desarrollo.
- `dataset_fingerprint`: `c25923f719df2d809be1d5af5b0a36110affee9bca81b60afaf6853b7e6d03c7`
- `relevant_configuration`: `no_demostrada`
- `main_result`: Ejecución interrumpida sin resultado analítico consolidado.
- `methodological_or_architectural_decision`: `ninguna`
- `limitations`: No existe manifest final, configuración exacta verificable ni resultado de detección utilizable.
- `preservation_status`: `represented_only_in_global_registry`
- `removal_status`: `complete_run_ready_for_delete`

## run_20260602T180842Z

- `experiment_id`: `run_20260602T180842Z`
- `classification`: `retrospective_integration_experiment`
- `purpose`: Integrar replay retrospectivo, detección, evidencia trazable y validación RAG interna/externa sobre el corpus experimental.
- `dataset_fingerprint`: `c25923f719df2d809be1d5af5b0a36110affee9bca81b60afaf6853b7e6d03c7`
- `relevant_configuration`: `detector=xiao_ema; retrospective_profile=historical_media_log_3; window_size=120s; slide_interval=30s; slow_window=10min; sensitivity_threshold=1.5; v_min=15; cooldown=3min; monitoring_window=20min`
- `main_result`: `18` eventos detectados y `325` asociaciones evento-comentario; G-1 completó `18/18` eventos; G-2 completó `79/84` asociaciones evento-video y dejó `5` videos pendientes por timeout del proveedor externo.
- `methodological_or_architectural_decision`: Separar G-1, basado únicamente en evidencia interna de YouTube, de G-2, basado en evidencia externa; ejecutar y consolidar G-2 por video para no transferir evidencia externa entre videos del mismo evento.
- `limitations`: Corrida experimental de integración, no caso de uso oficial A10. El perfil histórico `v_min=15` no constituye una configuración académica definitiva. G-2 quedó incompleto para `evt_924cefbc8e4e` y los videos `4hjg582JIO0`, `FuDMj0snITU`, `O47u_61AwaI`, `hhtMac_On1M` y `qs8YORXeIJE`. Los labels RAG dependen de la evidencia recuperada y de ejecuciones generativas de desarrollo.
- `preservation_status`: `compact_evidence_in_place`; se conservan configuración, lista de eventos, asociaciones compactas, resultados consolidados G-1/G-2, evidencia externa no vacía, limitaciones y reporte de decisiones.
- `removal_status`: `detail_ready_for_delete`; pueden retirarse materializaciones, snapshots, payloads, sidecars no seleccionados, raw responses, retries y manifests repetidos.

## Alcance académico

Ninguna de estas tres corridas es un caso de uso oficial del objetivo A10. Su conservación responde exclusivamente a la estabilización y comprensión de la evolución del prototipo.
