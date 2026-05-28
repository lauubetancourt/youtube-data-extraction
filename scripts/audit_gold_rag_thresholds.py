#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = "data/gold/clean_comments.parquet"
WINDOW_SIZE = "2min"
SLIDE_INTERVAL = "30s"
FAST_STEPS = 4
SLOW_STEPS = 20
TRIGGER_FORCE = 1.5
SIGNIFICANT_PEAK_MIN_VOLUME = 27
COOLDOWN_MINUTES = 5
CANONICAL_EVENT_TIME_UNIX_FIELD = "event_time_unix_s"
LEGACY_EVENT_TIME_UNIX_FIELD = "event_time_unix_ms"


@dataclass(frozen=True)
class TimestampNormalizationResult:
    column_name: str
    is_legacy_column: bool
    expected_unit: str
    inferred_unit: str
    duration_seconds: float
    start_error_seconds: float
    end_error_seconds: float
    needs_conversion: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audita el dataset gold y recomienda umbrales de activacion "
            "para el modulo RAG."
        )
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Ruta al dataset gold en parquet o csv.",
    )
    parser.add_argument(
        "--trigger-force",
        type=float,
        default=TRIGGER_FORCE,
        help="Umbral de fuerza EMA_R / EMA_L para considerar un trigger.",
    )
    parser.add_argument(
        "--significant-peak-min-volume",
        type=int,
        default=SIGNIFICANT_PEAK_MIN_VOLUME,
        help=(
            "Volumen minimo para considerar que un trigger es un pico significativo "
            "en el calculo de V_min."
        ),
    )
    parser.add_argument(
        "--cooldown-minutes",
        type=int,
        default=COOLDOWN_MINUTES,
        help="Cooldown a simular despues de cada trigger.",
    )
    return parser.parse_args()


def read_table(path: str | Path) -> pd.DataFrame:
    dataset_path = Path(path)
    if dataset_path.suffix.lower() == ".csv":
        df = pd.read_csv(dataset_path)
    else:
        df = pd.read_parquet(dataset_path)
    return df


def infer_epoch_unit(series: pd.Series) -> str:
    sample = int(series.dropna().iloc[len(series.dropna()) // 2])
    if sample >= 10**18:
        return "ns"
    if sample >= 10**15:
        return "us"
    if sample >= 10**12:
        return "ms"
    return "s"


def resolve_event_time_unix_column(df: pd.DataFrame) -> tuple[str, bool]:
    if CANONICAL_EVENT_TIME_UNIX_FIELD in df.columns:
        return CANONICAL_EVENT_TIME_UNIX_FIELD, False
    if LEGACY_EVENT_TIME_UNIX_FIELD in df.columns:
        return LEGACY_EVENT_TIME_UNIX_FIELD, True
    raise KeyError(
        "Expected one of "
        f"'{CANONICAL_EVENT_TIME_UNIX_FIELD}' or '{LEGACY_EVENT_TIME_UNIX_FIELD}'."
    )


def normalize_timestamp_check(df: pd.DataFrame) -> TimestampNormalizationResult:
    unix_column, is_legacy_column = resolve_event_time_unix_column(df)
    event_ts = pd.to_datetime(df["event_time_utc"], utc=True, errors="coerce")
    unix_series = pd.to_numeric(df[unix_column], errors="coerce")
    unit = infer_epoch_unit(unix_series)
    factor_map = {"s": 1, "ms": 1_000, "us": 1_000_000, "ns": 1_000_000_000}
    factor = factor_map[unit]
    converted = pd.to_datetime(unix_series / factor, unit="s", utc=True, errors="coerce")

    start_error = (converted.iloc[0] - event_ts.iloc[0]).total_seconds()
    end_error = (converted.iloc[-1] - event_ts.iloc[-1]).total_seconds()
    duration_seconds = (event_ts.max() - event_ts.min()).total_seconds()

    return TimestampNormalizationResult(
        column_name=unix_column,
        is_legacy_column=is_legacy_column,
        expected_unit="s",
        inferred_unit=unit,
        duration_seconds=duration_seconds,
        start_error_seconds=float(start_error),
        end_error_seconds=float(end_error),
        needs_conversion=(unit != "s"),
    )


def duplicate_audit(df: pd.DataFrame) -> tuple[int, int, int, float, pd.DataFrame]:
    working = df.copy()
    working["window_2m"] = working["event_time_utc"].dt.floor(WINDOW_SIZE)
    grouped = (
        working.groupby(["window_2m", "author_id", "text"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    duplicates = grouped[grouped["count"] > 1].copy()
    duplicate_groups = int(len(duplicates))
    duplicate_rows = int(duplicates["count"].sum())
    duplicate_excess = int((duplicates["count"] - 1).sum())
    duplicate_rate = duplicate_excess / float(len(df)) if len(df) else 0.0
    return duplicate_groups, duplicate_rows, duplicate_excess, duplicate_rate, duplicates


def orphan_audit(df: pd.DataFrame) -> tuple[int, float]:
    volume_2m = (
        df.assign(window_2m=df["event_time_utc"].dt.floor(WINDOW_SIZE))
        .groupby("window_2m")
        .size()
    )
    orphan_comments = int(volume_2m[volume_2m == 1].sum())
    orphan_rate = orphan_comments / float(len(df)) if len(df) else 0.0
    return orphan_comments, orphan_rate


def build_trigger_windows(df: pd.DataFrame, trigger_force: float) -> pd.DataFrame:
    start_tick = df["event_time_utc"].min().floor(SLIDE_INTERVAL)
    end_tick = df["event_time_utc"].max().ceil(SLIDE_INTERVAL)
    ticks = pd.date_range(start=start_tick, end=end_tick, freq=SLIDE_INTERVAL, tz="UTC")

    base_counts = (
        df.set_index("event_time_utc")
        .sort_index()
        .resample(SLIDE_INTERVAL)
        .size()
        .reindex(ticks, fill_value=0)
    )
    window_volume = base_counts.rolling(window=FAST_STEPS, min_periods=1).sum()

    ema_fast = window_volume.ewm(alpha=2.0 / (FAST_STEPS + 1), adjust=False).mean()
    ema_slow = window_volume.ewm(alpha=2.0 / (SLOW_STEPS + 1), adjust=False).mean()
    strength = ema_fast / ema_slow.replace(0, pd.NA)

    trigger_windows = pd.DataFrame(
        {
            "tick": ticks,
            "volume": window_volume.values.astype(int),
            "ema_fast": ema_fast.values,
            "ema_slow": ema_slow.values,
            "strength": strength.values,
        }
    ).dropna(subset=["strength"])
    trigger_windows["is_trigger"] = trigger_windows["strength"] > trigger_force
    trigger_windows["is_trigger_positive_volume"] = (
        trigger_windows["is_trigger"] & (trigger_windows["volume"] > 0)
    )
    return trigger_windows


def trigger_volume_frequency(trigger_windows: pd.DataFrame) -> pd.DataFrame:
    positive = trigger_windows.loc[
        trigger_windows["is_trigger_positive_volume"], "volume"
    ].astype(int)
    counts = positive.value_counts().sort_index()
    rows = []
    for volume, count in counts.items():
        label = str(volume) if volume <= 10 else ">10"
        rows.append({"bucket": label, "count": int(count)})
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    table = table.groupby("bucket", as_index=False)["count"].sum()
    order = [str(i) for i in range(0, 11)] + [">10"]
    table["bucket"] = pd.Categorical(table["bucket"], categories=order, ordered=True)
    return table.sort_values("bucket").reset_index(drop=True)


def recommend_vmin(trigger_windows: pd.DataFrame, significant_peak_min_volume: int) -> tuple[int, int, float, pd.Series]:
    positive_triggers = trigger_windows.loc[
        trigger_windows["is_trigger_positive_volume"]
    ].copy()
    significant = positive_triggers.loc[
        positive_triggers["volume"] > significant_peak_min_volume, "volume"
    ].astype(int).sort_values()

    if significant.empty:
        fallback = int(positive_triggers["volume"].quantile(0.90)) if not positive_triggers.empty else 1
        return fallback, 0, 0.0, significant

    idx = math.floor(0.10 * (len(significant) - 1))
    v_min = int(significant.iloc[idx])
    coverage = float((significant >= v_min).mean())
    return v_min, int(len(significant)), coverage, significant


def simulate_cooldown(trigger_windows: pd.DataFrame, cooldown_minutes: int) -> tuple[int, int, int]:
    candidates = trigger_windows.loc[
        trigger_windows["is_trigger_positive_volume"], ["tick", "volume", "strength"]
    ].sort_values("tick")
    kept = 0
    fused = 0
    last_kept: pd.Timestamp | None = None
    cooldown = pd.Timedelta(minutes=cooldown_minutes)

    for tick in candidates["tick"]:
        if last_kept is None or tick >= last_kept + cooldown:
            kept += 1
            last_kept = tick
        else:
            fused += 1

    return int(len(candidates)), kept, fused


def print_report(
    *,
    input_path: Path,
    df: pd.DataFrame,
    timestamp_check: TimestampNormalizationResult,
    duplicate_groups: int,
    duplicate_rows: int,
    duplicate_excess: int,
    duplicate_rate: float,
    duplicates_head: pd.DataFrame,
    orphan_comments: int,
    orphan_rate: float,
    active_mean: float,
    active_median: float,
    trigger_windows: pd.DataFrame,
    volume_table: pd.DataFrame,
    v_min: int,
    significant_count: int,
    significant_coverage: float,
    significant_volumes: pd.Series,
    raw_triggers: int,
    cooldown_kept: int,
    cooldown_fused: int,
    trigger_force: float,
    significant_peak_min_volume: int,
    cooldown_minutes: int,
) -> None:
    positive_triggers = trigger_windows.loc[
        trigger_windows["is_trigger_positive_volume"]
    ].copy()
    zero_volume_triggers = int(
        trigger_windows["is_trigger"].sum() - positive_triggers.shape[0]
    )

    print("REPORTE DE AUDITORIA GOLD")
    print("=" * 80)
    print(f"Fuente: {input_path}")
    print(
        f"Filas: {len(df):,} | "
        f"Inicio: {df['event_time_utc'].min().isoformat()} | "
        f"Fin: {df['event_time_utc'].max().isoformat()}"
    )

    print()
    print("1) Integridad y duplicados")
    print(
        f"- Duplicidad real en ventana fija de 2 minutos (author_id + text exactos): "
        f"{duplicate_groups} grupos, {duplicate_rows} filas involucradas, "
        f"{duplicate_excess} duplicados excedentes ({duplicate_rate:.2%} del dataset)."
    )
    print(
        f"- Comentarios huérfanos (ventanas de 2 minutos con volumen=1): "
        f"{orphan_comments:,} ({orphan_rate:.2%} del total)."
    )
    legacy_note = " (legacy)" if timestamp_check.is_legacy_column else ""
    print(
        f"- Normalización temporal: {timestamp_check.column_name}{legacy_note} "
        f"se comporta como '{timestamp_check.inferred_unit}'. "
        f"Unidad esperada por contrato='{timestamp_check.expected_unit}'. "
        f"Duración observada={timestamp_check.duration_seconds:,.0f}s. "
        f"Error extremo al convertir con esa unidad: "
        f"inicio={timestamp_check.start_error_seconds:.3f}s, "
        f"fin={timestamp_check.end_error_seconds:.3f}s."
    )
    if timestamp_check.is_legacy_column:
        print(
            "- Nota temporal: el nombre event_time_unix_ms queda deprecado; "
            "los datasets nuevos deben preferir event_time_unix_s."
        )
    if timestamp_check.needs_conversion:
        print(
            "- Aviso temporal: la unidad inferida no coincide con segundos. "
            "Revise el contrato antes de comparar experimentos."
        )
    if not duplicates_head.empty:
        print("- Ejemplos de duplicados detectados:")
        examples = duplicates_head.head(5)[["window_2m", "author_id", "count", "text"]]
        for row in examples.itertuples(index=False):
            text_preview = str(row.text).replace("\n", " ")[:100]
            print(
                f"  * {row.window_2m.isoformat()} | author_id={row.author_id} | "
                f"count={row.count} | text='{text_preview}'"
            )

    print()
    print("2) Umbrales de análisis y sustancia semántica")
    print(
        f"- Baseline de ventanas activas (sliding window 2min / slide 30s): "
        f"mu={active_mean:.3f}, mediana={active_median:.3f} comentarios."
    )
    print(
        f"- Momentos con Fuerza > {trigger_force}: {int(trigger_windows['is_trigger'].sum()):,}. "
        f"De ellos, {positive_triggers.shape[0]:,} tienen volumen>0 y "
        f"{zero_volume_triggers:,} ocurren con volumen=0 por arrastre de EMA."
    )
    print("- Frecuencia de volumen en triggers positivos:")
    if volume_table.empty:
        print("  * No hubo triggers con volumen>0.")
    else:
        print(volume_table.to_string(index=False))
    if significant_count > 0:
        significant_list = ", ".join(str(v) for v in significant_volumes.tolist())
        print(
            f"- Picos significativos usados para V_min (volumen > {significant_peak_min_volume}): "
            f"{significant_count} casos -> [{significant_list}]"
        )
        print(
            f"- Codo de saturación operativo: V_min={v_min}. "
            f"Ese corte retiene el {significant_coverage:.2%} de los picos significativos."
        )
    else:
        print(
            f"- No hubo suficientes picos > {significant_peak_min_volume}; "
            f"se usa fallback por percentil para V_min={v_min}."
        )

    print()
    print("3) Simulación de cooldown")
    print(
        f"- Triggers actuales con volumen>0: {raw_triggers:,}. "
        f"Con cooldown de {cooldown_minutes} minutos quedarían {cooldown_kept:,} "
        f"y se fusionarían {cooldown_fused:,}."
    )

    print()
    print("4) Conclusión QA")
    print(
        f"- El archivo Gold {'SI' if duplicate_excess > 0 else 'NO'} contiene duplicados "
        "que deben filtrarse en el código."
    )
    print(
        f"- Se recomienda un Umbral Mínimo de Volumen (V_min) de {v_min} comentarios "
        "para activar el RAG."
    )
    print(
        f"- La configuración sugerida para evitar la sobre-activación es: "
        f"Trigger si (Fuerza > {trigger_force} AND Volumen > {v_min})."
    )


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    df = read_table(input_path)
    df["event_time_utc"] = pd.to_datetime(df["event_time_utc"], utc=True, errors="coerce")
    df = df.loc[~df["event_time_utc"].isna()].sort_values("event_time_utc").reset_index(
        drop=True
    )

    timestamp_check = normalize_timestamp_check(df)
    duplicate_groups, duplicate_rows, duplicate_excess, duplicate_rate, duplicates = duplicate_audit(df)
    orphan_comments, orphan_rate = orphan_audit(df)

    trigger_windows = build_trigger_windows(df, trigger_force=args.trigger_force)
    active_windows = trigger_windows.loc[trigger_windows["volume"] > 0, "volume"]
    active_mean = float(active_windows.mean()) if not active_windows.empty else 0.0
    active_median = float(active_windows.median()) if not active_windows.empty else 0.0
    volume_table = trigger_volume_frequency(trigger_windows)
    v_min, significant_count, significant_coverage, significant_volumes = recommend_vmin(
        trigger_windows,
        significant_peak_min_volume=args.significant_peak_min_volume,
    )
    raw_triggers, cooldown_kept, cooldown_fused = simulate_cooldown(
        trigger_windows, cooldown_minutes=args.cooldown_minutes
    )

    print_report(
        input_path=input_path,
        df=df,
        timestamp_check=timestamp_check,
        duplicate_groups=duplicate_groups,
        duplicate_rows=duplicate_rows,
        duplicate_excess=duplicate_excess,
        duplicate_rate=duplicate_rate,
        duplicates_head=duplicates,
        orphan_comments=orphan_comments,
        orphan_rate=orphan_rate,
        active_mean=active_mean,
        active_median=active_median,
        trigger_windows=trigger_windows,
        volume_table=volume_table,
        v_min=v_min,
        significant_count=significant_count,
        significant_coverage=significant_coverage,
        significant_volumes=significant_volumes,
        raw_triggers=raw_triggers,
        cooldown_kept=cooldown_kept,
        cooldown_fused=cooldown_fused,
        trigger_force=args.trigger_force,
        significant_peak_min_volume=args.significant_peak_min_volume,
        cooldown_minutes=args.cooldown_minutes,
    )


if __name__ == "__main__":
    main()
