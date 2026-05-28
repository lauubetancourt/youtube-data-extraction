#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from youtube_pipeline.stream_playback import XiaoEMATriggerDetector


TRIGGER_WINDOW_SIZE = "120s"
TRIGGER_SLIDE_INTERVAL = "30s"
TRIGGER_SLOW_WINDOW = "10min"
TRIGGER_THRESHOLD = 1.5
TRIGGER_MIN_VOLUME = 15
TRIGGER_COOLDOWN = "3min"
TS_COL = "event_time_utc"


def _read_snapshots(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "window_start",
        "window_end",
        "size",
        "activity.volume",
        "activity.unique_authors",
        "activity.unique_videos",
        "polarization.emoji_density",
        "polarization.exclaim_density",
        "polarization.question_density",
    }
    missing = required.difference(df.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise KeyError(f"Missing required columns: {missing_cols}")

    df["window_start"] = pd.to_datetime(df["window_start"], utc=True)
    df["window_end"] = pd.to_datetime(df["window_end"], utc=True)
    df = df.sort_values(["window_end"]).reset_index(drop=True)
    return df


def _run_detector_from_snapshots(df: pd.DataFrame) -> tuple[list[dict], list[str]]:
    logs: list[str] = []
    detector = XiaoEMATriggerDetector(
        ts_col=TS_COL,
        window_size=TRIGGER_WINDOW_SIZE,
        slide_interval=TRIGGER_SLIDE_INTERVAL,
        slow_window=TRIGGER_SLOW_WINDOW,
        sensitivity_threshold=TRIGGER_THRESHOLD,
        v_min=TRIGGER_MIN_VOLUME,
        cooldown=TRIGGER_COOLDOWN,
        log_fn=logs.append,
    )

    for ts in df["window_end"]:
        detector.on_event({TS_COL: ts})

    last_ts = df["window_end"].iloc[-1] if not df.empty else None
    detector.finalize(last_ts)
    return detector.completed_triggers, logs


def _find_anchor_row(df: pd.DataFrame, trigger: dict) -> tuple[int, pd.Series]:
    trigger_time = pd.Timestamp(trigger["trigger_time"])
    trigger_volume = int(trigger["volume"])

    exact = df.loc[
        (df["window_end"] == trigger_time) & (df["activity.volume"] == trigger_volume)
    ]
    if not exact.empty:
        idx = int(exact.index[0])
        return idx, df.loc[idx]

    same_time = df.loc[df["window_end"] == trigger_time]
    if not same_time.empty:
        idx = int(same_time.index[0])
        return idx, df.loc[idx]

    first_after = df.loc[df["window_end"] > trigger_time]
    if not first_after.empty:
        idx = int(first_after.index[0])
        return idx, df.loc[idx]

    raise ValueError(
        f"No snapshot row found at or after trigger {trigger_time.isoformat()}"
    )


def _build_trigger_snapshot_map(df: pd.DataFrame, triggers: list[dict]) -> pd.DataFrame:
    window_td = pd.to_timedelta(TRIGGER_WINDOW_SIZE)
    rows: list[dict] = []

    for trigger in triggers:
        trigger_time = pd.Timestamp(trigger["trigger_time"])
        trigger_start = trigger_time
        trigger_end = trigger_time + window_td
        trigger_volume = int(trigger["volume"])
        trigger_strength = float(trigger["strength"])

        in_window = df.loc[
            (df["window_end"] >= trigger_start) & (df["window_end"] <= trigger_end)
        ].copy()

        for order, (_, row) in enumerate(in_window.iterrows(), start=1):
            rows.append(
                {
                    "trigger_time": trigger_time,
                    "trigger_context_start": trigger_start,
                    "trigger_context_end": trigger_end,
                    "trigger_volume": trigger_volume,
                    "trigger_strength": round(trigger_strength, 2),
                    "order_in_trigger": order,
                    "snapshot_window_start": row["window_start"],
                    "snapshot_window_end": row["window_end"],
                    "size": int(row["size"]),
                    "activity.volume": int(row["activity.volume"]),
                    "activity.unique_authors": int(row["activity.unique_authors"]),
                    "activity.unique_videos": int(row["activity.unique_videos"]),
                    "polarization.emoji_density": float(
                        row["polarization.emoji_density"]
                    ),
                    "polarization.exclaim_density": float(
                        row["polarization.exclaim_density"]
                    ),
                    "polarization.question_density": float(
                        row["polarization.question_density"]
                    ),
                }
            )

    return pd.DataFrame(rows)


def _format_metric(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _build_summary(df: pd.DataFrame, triggers: list[dict], source_path: Path) -> str:
    lines = [
        "# Snapshot Trigger Summary",
        "",
        f"Derivado de `{source_path.as_posix()}`.",
        "Este resumen usa exclusivamente metricas agregadas del CSV de snapshots.",
        "Los triggers se reconstruyen exactamente; las metricas agregadas se reportan",
        "a partir del primer snapshot emitido despues de cada trigger, porque el CSV",
        "no guarda una fila para todos los ticks internos del detector.",
        "",
    ]

    window_td = pd.to_timedelta(TRIGGER_WINDOW_SIZE)

    for trigger in triggers:
        trigger_time = pd.Timestamp(trigger["trigger_time"])
        trigger_start = trigger_time - window_td
        trigger_end = trigger_time
        trigger_volume = int(trigger["volume"])
        trigger_strength = float(trigger["strength"])

        anchor_idx, anchor = _find_anchor_row(df, trigger)
        post_trigger = df.loc[
            (df["window_end"] >= trigger_time)
            & (df["window_end"] <= trigger_time + window_td)
        ].copy()
        first_five = post_trigger.head(5)
        neighborhood = df.iloc[max(0, anchor_idx - 2) : anchor_idx + 3]

        lines.extend(
            [
                f"## Trigger {trigger_time.isoformat()}",
                f"- Ventana: {trigger_start.isoformat()} a {trigger_end.isoformat()}",
                f"- Volumen: {trigger_volume}",
                f"- Fuerza: {trigger_strength:.2f}",
                f"- Primer snapshot posterior: {pd.Timestamp(anchor['window_end']).isoformat()}",
                f"- Ventana del snapshot posterior: {pd.Timestamp(anchor['window_start']).isoformat()} a {pd.Timestamp(anchor['window_end']).isoformat()}",
                f"- Autores unicos en snapshot posterior: {int(anchor['activity.unique_authors'])}",
                f"- Videos unicos en snapshot posterior: {int(anchor['activity.unique_videos'])}",
                f"- Densidad emoji en snapshot posterior: {_format_metric(float(anchor['polarization.emoji_density']))}",
                f"- Densidad exclamacion en snapshot posterior: {_format_metric(float(anchor['polarization.exclaim_density']))}",
                f"- Densidad pregunta en snapshot posterior: {_format_metric(float(anchor['polarization.question_density']))}",
                "- Primeros 5 snapshots posteriores al trigger:",
            ]
        )

        for _, row in first_five.iterrows():
            lines.append(
                "  - "
                f"{pd.Timestamp(row['window_end']).isoformat()} | "
                f"vol={int(row['activity.volume'])} | "
                f"autores={int(row['activity.unique_authors'])} | "
                f"videos={int(row['activity.unique_videos'])} | "
                f"emoji={_format_metric(float(row['polarization.emoji_density']))} | "
                f"exclaim={_format_metric(float(row['polarization.exclaim_density']))} | "
                f"question={_format_metric(float(row['polarization.question_density']))}"
            )

        lines.append("- Contexto cercano al trigger:")
        for _, row in neighborhood.iterrows():
            row_end = pd.Timestamp(row["window_end"])
            marker = "*" if row_end == pd.Timestamp(anchor["window_end"]) else "-"
            lines.append(
                f"  {marker} {row_end.isoformat()} | "
                f"vol={int(row['activity.volume'])} | "
                f"autores={int(row['activity.unique_authors'])} | "
                f"videos={int(row['activity.unique_videos'])}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _build_trigger_log(
    df: pd.DataFrame, logs: list[str], source_path: Path, triggers: list[dict]
) -> str:
    first_event = pd.Timestamp(df["window_end"].iloc[0]).isoformat()
    last_event = pd.Timestamp(df["window_end"].iloc[-1]).isoformat()
    lines = [
        f"Trigger log generated from {source_path.as_posix()}",
        "Detector: XiaoEMATriggerDetector",
        "Logic: warm-up(10 windows) + emergency bypass(volume>30) + post-warm-up(volume>15 and EMA ratio>1.5)",
        f"ts_col: {TS_COL}",
        f"window_size: {TRIGGER_WINDOW_SIZE}",
        f"slide_interval: {TRIGGER_SLIDE_INTERVAL}",
        f"slow_window: {TRIGGER_SLOW_WINDOW}",
        f"sensitivity_threshold: {TRIGGER_THRESHOLD}",
        f"v_min: {TRIGGER_MIN_VOLUME}",
        f"v_extreme: {TRIGGER_MIN_VOLUME * 2}",
        f"cooldown: {TRIGGER_COOLDOWN}",
        f"rows: {len(df)}",
        f"first_event_utc: {first_event}",
        f"last_event_utc: {last_event}",
        f"triggers: {len(triggers)}",
        f"snapshots: {len(df)}",
        "",
    ]
    lines.extend(logs)
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract trigger reports directly from a snapshots CSV."
    )
    parser.add_argument("--snapshots-path", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    snapshots_path = Path(args.snapshots_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _read_snapshots(snapshots_path)
    triggers, logs = _run_detector_from_snapshots(df)
    trigger_map_df = _build_trigger_snapshot_map(df, triggers)
    summary_text = _build_summary(df, triggers, snapshots_path)
    trigger_log_text = _build_trigger_log(df, logs, snapshots_path, triggers)

    (output_dir / "summary.md").write_text(summary_text, encoding="utf-8")
    (output_dir / "trigger_log.txt").write_text(trigger_log_text, encoding="utf-8")
    trigger_map_df.to_csv(output_dir / "trigger_snapshot_map.csv", index=False)


if __name__ == "__main__":
    main()
