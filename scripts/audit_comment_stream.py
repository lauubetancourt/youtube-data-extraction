#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from bisect import bisect_left
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pvariance


SECONDS_PER_DAY = 86_400
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3_600
CANONICAL_TS_FIELD = "event_time_unix_s"
LEGACY_TS_FALLBACKS = {
    "event_time_unix_s": "event_time_unix_ms",
    "published_at_unix_s": "published_at_unix_ms",
}


@dataclass(frozen=True)
class CommentEvent:
    timestamp_s: int
    text: str


@dataclass(frozen=True)
class DatasetSummary:
    source_path: Path
    requested_timestamp_field: str
    timestamp_field: str
    unit_name: str
    row_count: int
    event_count: int
    missing_text_count: int
    invalid_timestamp_count: int
    start_s: int
    end_s: int
    unique_videos: int
    reply_count: int
    events: tuple[CommentEvent, ...]


@dataclass(frozen=True)
class DensityStats:
    mean: float
    variance: float
    std: float
    dispersion_index: float
    total_bins: int
    active_bins: int
    active_share: float
    q95: float
    q99: float
    max_count: int


@dataclass(frozen=True)
class TriggerEpisode:
    start_s: int
    end_s: int
    peak_s: int
    peak_count: int
    start_count: int
    start_ema_short: float
    baseline_ema_short: float
    start_k: float


@dataclass(frozen=True)
class TriggerSimulation:
    bin_size_s: int
    trigger_count: int
    activation_bins: int
    eligible_bins: int
    max_k: float
    max_activation_ratio: float
    episodes: tuple[TriggerEpisode, ...]


@dataclass(frozen=True)
class PeakRun:
    start_s: int
    end_s_exclusive: int
    counts: tuple[int, ...]

    @property
    def duration_minutes(self) -> int:
        return len(self.counts)

    @property
    def total_comments(self) -> int:
        return sum(self.counts)

    @property
    def native_rate_per_minute(self) -> float:
        if not self.counts:
            return 0.0
        return self.total_comments / float(self.duration_minutes)


@dataclass(frozen=True)
class DilutionStats:
    window_minutes: int
    mean_retention: float
    median_retention: float
    min_retention: float
    lost_significance_count: int


@dataclass(frozen=True)
class WindowCandidate:
    window_size_s: int
    slide_s: int
    mean_retention: float
    median_retention: float
    min_retention: float


@dataclass(frozen=True)
class SemanticNoiseStats:
    high_density_minutes: int
    comments_in_high_density: int
    duplicate_excess: int
    duplicate_rate: float
    top_duplicates: tuple[tuple[str, int], ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audita el flujo temporal de comentarios de YouTube para seleccionar "
            "una estrategia de deteccion de eventos."
        )
    )
    parser.add_argument(
        "--input",
        default="data/bronze/comments",
        help="Archivo JSONL o directorio que contiene comments_*.jsonl.",
    )
    parser.add_argument(
        "--ts-field",
        default=CANONICAL_TS_FIELD,
        help=(
            "Campo temporal a auditar. Por defecto usa event_time_unix_s y "
            "acepta event_time_unix_ms como fallback legacy."
        ),
    )
    parser.add_argument(
        "--text-field",
        default="text",
        help="Campo de texto a auditar.",
    )
    parser.add_argument(
        "--high-density-threshold",
        type=int,
        default=None,
        help=(
            "Umbral absoluto de alta densidad en comentarios/minuto. "
            "Si no se indica, usa max(P99, ceil(mu + 3*sigma))."
        ),
    )
    parser.add_argument(
        "--window-candidates",
        default="120,180,300,600",
        help="Candidatos de window_size en segundos para la recomendacion final.",
    )
    parser.add_argument(
        "--slide-candidates",
        default="30,60,120",
        help="Candidatos de slide_interval en segundos para la recomendacion final.",
    )
    parser.add_argument(
        "--trigger-bin-seconds",
        type=int,
        default=SECONDS_PER_HOUR,
        help=(
            "Granularidad del trigger de Xiao. Por defecto 3600s para respetar "
            "la granularidad base de la referencia."
        ),
    )
    parser.add_argument(
        "--trigger-proxy-minute-scan",
        action="store_true",
        help=(
            "Tambien calcula una simulacion adicional de Xiao a 60s para ver "
            "si un trigger minuto a minuto sobrerreacciona."
        ),
    )
    return parser.parse_args()


def resolve_input_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted(path.glob("comments_*.jsonl"))
        if not candidates:
            raise FileNotFoundError(f"No se encontraron archivos comments_*.jsonl en {path}")
        return candidates[-1]
    raise FileNotFoundError(f"Ruta no encontrada: {path}")


def safe_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)):
            return None
        return float(value)
    return None


def infer_epoch_unit(values: list[int]) -> tuple[str, int]:
    if not values:
        raise ValueError("No hay timestamps validos para inferir la unidad.")
    probe = sorted(values)[len(values) // 2]
    if probe >= 10**18:
        return "ns", 1_000_000_000
    if probe >= 10**15:
        return "us", 1_000_000
    if probe >= 10**12:
        return "ms", 1_000
    return "s", 1


def normalize_spam_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def candidate_timestamp_fields(ts_field: str) -> tuple[str, ...]:
    fallback = LEGACY_TS_FALLBACKS.get(ts_field)
    if fallback is None:
        return (ts_field,)
    return (ts_field, fallback)


def bucket_floor(timestamp_s: int, bin_size_s: int) -> int:
    return (timestamp_s // bin_size_s) * bin_size_s


def percentile(sorted_values: list[int], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(q * (len(sorted_values) - 1))))
    return float(sorted_values[idx])


def iso(ts_s: int) -> str:
    return datetime.fromtimestamp(ts_s, tz=timezone.utc).isoformat()


def format_duration_hours(start_s: int, end_s: int) -> float:
    return round((end_s - start_s) / float(SECONDS_PER_HOUR), 2)


def load_dataset(input_path: Path, ts_field: str, text_field: str) -> DatasetSummary:
    raw_rows = 0
    missing_text_count = 0
    invalid_timestamp_count = 0
    raw_timestamps: list[int] = []
    staged_rows: list[tuple[int, str, str, bool]] = []
    timestamp_field_counts: Counter[str] = Counter()
    timestamp_fields = candidate_timestamp_fields(ts_field)
    videos: set[str] = set()
    replies = 0

    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw_rows += 1
            payload = json.loads(line)
            raw_ts: float | None = None
            used_ts_field: str | None = None
            for candidate_ts_field in timestamp_fields:
                raw_ts = safe_float(payload.get(candidate_ts_field))
                if raw_ts is not None:
                    used_ts_field = candidate_ts_field
                    break
            raw_text = payload.get(text_field)
            if raw_text is None or not str(raw_text).strip():
                missing_text_count += 1

            video_id = payload.get("video_id")
            if isinstance(video_id, str) and video_id:
                videos.add(video_id)
            replies += int(bool(payload.get("is_reply")))

            if raw_ts is None:
                invalid_timestamp_count += 1
                continue

            if used_ts_field is not None:
                timestamp_field_counts[used_ts_field] += 1
            staged_rows.append(
                (
                    int(raw_ts),
                    str(raw_text or ""),
                    str(video_id or ""),
                    bool(payload.get("is_reply")),
                )
            )
            raw_timestamps.append(int(raw_ts))

    unit_name, divisor = infer_epoch_unit(raw_timestamps)
    events = tuple(
        sorted(
            (
                CommentEvent(timestamp_s=raw_ts // divisor, text=text)
                for raw_ts, text, _video_id, _is_reply in staged_rows
            ),
            key=lambda event: event.timestamp_s,
        )
    )
    if not events:
        raise ValueError("No hay eventos validos en el archivo auditado.")

    resolved_timestamp_field = (
        timestamp_field_counts.most_common(1)[0][0]
        if timestamp_field_counts
        else ts_field
    )
    return DatasetSummary(
        source_path=input_path,
        requested_timestamp_field=ts_field,
        timestamp_field=resolved_timestamp_field,
        unit_name=unit_name,
        row_count=raw_rows,
        event_count=len(events),
        missing_text_count=missing_text_count,
        invalid_timestamp_count=invalid_timestamp_count,
        start_s=events[0].timestamp_s,
        end_s=events[-1].timestamp_s,
        unique_videos=len(videos),
        reply_count=replies,
        events=events,
    )


def build_series(events: tuple[CommentEvent, ...], bin_size_s: int) -> tuple[list[int], list[int], Counter[int]]:
    counts: Counter[int] = Counter()
    for event in events:
        counts[bucket_floor(event.timestamp_s, bin_size_s)] += 1
    first_bucket = min(counts)
    last_bucket = max(counts)
    buckets = list(range(first_bucket, last_bucket + bin_size_s, bin_size_s))
    series = [counts.get(bucket, 0) for bucket in buckets]
    return buckets, series, counts


def compute_density_stats(series: list[int]) -> DensityStats:
    if not series:
        raise ValueError("La serie no puede estar vacia.")
    variance = pvariance(series)
    mu = mean(series)
    std = math.sqrt(variance)
    active_bins = sum(1 for value in series if value > 0)
    sorted_series = sorted(series)
    return DensityStats(
        mean=mu,
        variance=variance,
        std=std,
        dispersion_index=(variance / mu) if mu else 0.0,
        total_bins=len(series),
        active_bins=active_bins,
        active_share=(active_bins / len(series)),
        q95=percentile(sorted_series, 0.95),
        q99=percentile(sorted_series, 0.99),
        max_count=max(series),
    )


def classify_burstiness(dispersion_index: float) -> str:
    if dispersion_index <= 1.0:
        return "estable / cuasi Poisson"
    if dispersion_index <= 2.0:
        return "leve"
    if dispersion_index <= 5.0:
        return "moderada"
    if dispersion_index <= 10.0:
        return "alta"
    return "extrema"


def ema(values: list[float], span: int) -> list[float]:
    alpha = 2.0 / float(span + 1)
    out: list[float] = []
    current: float | None = None
    for value in values:
        current = value if current is None else alpha * value + (1.0 - alpha) * current
        out.append(current)
    return out


def rolling_abs_mean(values: list[float], window: int) -> list[float]:
    q: deque[float] = deque()
    running_sum = 0.0
    out: list[float] = []
    for value in values:
        absolute = abs(value)
        q.append(absolute)
        running_sum += absolute
        if len(q) > window:
            running_sum -= q.popleft()
        out.append(running_sum / float(len(q)))
    return out


def prefix_sums(values: list[float]) -> list[float]:
    out = [0.0]
    for value in values:
        out.append(out[-1] + value)
    return out


def simulate_xiao_trigger(
    events: tuple[CommentEvent, ...],
    *,
    bin_size_s: int,
    ema_short_span: int = 12,
    ema_long_span: int = 26,
    signal_span: int = 9,
    hist_fast_window: int = 24,
    hist_slow_window: int = 720,
    activation_ratio: float = 2.0,
    activation_history_days: int = 180,
) -> TriggerSimulation:
    buckets, series, _ = build_series(events, bin_size_s)
    if not series:
        return TriggerSimulation(
            bin_size_s=bin_size_s,
            trigger_count=0,
            activation_bins=0,
            eligible_bins=0,
            max_k=0.0,
            max_activation_ratio=0.0,
            episodes=(),
        )

    series_f = [float(value) for value in series]
    ema_short = ema(series_f, ema_short_span)
    ema_long = ema(series_f, ema_long_span)
    dif = [left - right for left, right in zip(ema_short, ema_long)]
    dea = ema(dif, signal_span)
    histogram = [(left - right) * 2.0 for left, right in zip(dif, dea)]
    fast = rolling_abs_mean(histogram, hist_fast_window)
    slow = rolling_abs_mean(histogram, hist_slow_window)

    history_cap_bins = max(1, int((activation_history_days * SECONDS_PER_DAY) // bin_size_s))
    ema_prefix = prefix_sums(ema_short)

    activation_bins = 0
    eligible_bins = 0
    max_k = 0.0
    max_activation_ratio = 0.0
    episodes: list[TriggerEpisode] = []
    open_episode: dict[str, float | int] | None = None

    for idx, bucket in enumerate(buckets):
        history_start = max(0, idx - history_cap_bins)
        history_len = idx - history_start
        baseline = 0.0
        activation = False
        activation_multiple = 0.0

        if history_len > 0:
            eligible_bins += 1
            baseline = (ema_prefix[idx] - ema_prefix[history_start]) / float(history_len)
            if baseline > 0:
                activation_multiple = ema_short[idx] / baseline
                max_activation_ratio = max(max_activation_ratio, activation_multiple)
                activation = activation_multiple > activation_ratio
                if activation:
                    activation_bins += 1

        k_value = (fast[idx] / slow[idx]) if slow[idx] > 0 else 0.0
        max_k = max(max_k, k_value)

        if open_episode is None and activation and k_value > 2.0:
            open_episode = {
                "start_s": bucket,
                "end_s": bucket + bin_size_s,
                "peak_s": bucket,
                "peak_count": series[idx],
                "start_count": series[idx],
                "start_ema_short": ema_short[idx],
                "baseline_ema_short": baseline,
                "start_k": k_value,
            }
            continue

        if open_episode is None:
            continue

        open_episode["end_s"] = bucket + bin_size_s
        if series[idx] > int(open_episode["peak_count"]):
            open_episode["peak_count"] = series[idx]
            open_episode["peak_s"] = bucket

        if k_value < 1.0:
            episodes.append(
                TriggerEpisode(
                    start_s=int(open_episode["start_s"]),
                    end_s=int(open_episode["end_s"]),
                    peak_s=int(open_episode["peak_s"]),
                    peak_count=int(open_episode["peak_count"]),
                    start_count=int(open_episode["start_count"]),
                    start_ema_short=float(open_episode["start_ema_short"]),
                    baseline_ema_short=float(open_episode["baseline_ema_short"]),
                    start_k=float(open_episode["start_k"]),
                )
            )
            open_episode = None

    if open_episode is not None:
        episodes.append(
            TriggerEpisode(
                start_s=int(open_episode["start_s"]),
                end_s=int(open_episode["end_s"]),
                peak_s=int(open_episode["peak_s"]),
                peak_count=int(open_episode["peak_count"]),
                start_count=int(open_episode["start_count"]),
                start_ema_short=float(open_episode["start_ema_short"]),
                baseline_ema_short=float(open_episode["baseline_ema_short"]),
                start_k=float(open_episode["start_k"]),
            )
        )

    return TriggerSimulation(
        bin_size_s=bin_size_s,
        trigger_count=len(episodes),
        activation_bins=activation_bins,
        eligible_bins=eligible_bins,
        max_k=max_k,
        max_activation_ratio=max_activation_ratio,
        episodes=tuple(episodes),
    )


def choose_high_density_threshold(density: DensityStats, override: int | None) -> int:
    if override is not None and override > 0:
        return override
    return max(int(density.q99), math.ceil(density.mean + 3.0 * density.std))


def detect_short_peaks(
    buckets: list[int],
    series: list[int],
    *,
    threshold: int,
    max_duration_minutes: int = 2,
) -> tuple[PeakRun, ...]:
    peaks: list[PeakRun] = []
    start_s: int | None = None
    counts: list[int] = []
    prev_bucket: int | None = None

    for bucket, value in zip(buckets, series):
        active = value >= threshold
        if active and start_s is None:
            start_s = bucket
            counts = []

        if start_s is not None and not active:
            assert prev_bucket is not None
            if len(counts) <= max_duration_minutes:
                peaks.append(
                    PeakRun(
                        start_s=start_s,
                        end_s_exclusive=prev_bucket + SECONDS_PER_MINUTE,
                        counts=tuple(counts),
                    )
                )
            start_s = None
            counts = []

        if active:
            counts.append(value)
        prev_bucket = bucket

    if start_s is not None and counts:
        peaks.append(
            PeakRun(
                start_s=start_s,
                end_s_exclusive=buckets[-1] + SECONDS_PER_MINUTE,
                counts=tuple(counts),
            )
        )

    return tuple(peaks)


def rolling_average(values: list[int], window: int) -> list[float]:
    if not values or window <= 0 or window > len(values):
        return []
    out: list[float] = []
    running = sum(values[:window])
    out.append(running / float(window))
    for idx in range(window, len(values)):
        running += values[idx] - values[idx - window]
        out.append(running / float(window))
    return out


def analyze_dilution(
    minute_buckets: list[int],
    minute_series: list[int],
    peaks: tuple[PeakRun, ...],
    density: DensityStats,
    *,
    window_minutes: int,
) -> DilutionStats:
    averages = rolling_average(minute_series, window_minutes)
    if not averages or not peaks:
        return DilutionStats(
            window_minutes=window_minutes,
            mean_retention=0.0,
            median_retention=0.0,
            min_retention=0.0,
            lost_significance_count=0,
        )

    average_starts = minute_buckets[: len(averages)]
    average_mean = mean(averages)
    average_std = math.sqrt(pvariance(averages))

    retentions: list[float] = []
    lost_significance_count = 0
    for peak in peaks:
        native_rate = peak.native_rate_per_minute
        best_rate = 0.0
        best_z = float("-inf")
        for start_s, value in zip(average_starts, averages):
            end_s = start_s + (window_minutes * SECONDS_PER_MINUTE)
            overlaps = not (end_s <= peak.start_s or start_s >= peak.end_s_exclusive)
            if not overlaps:
                continue
            best_rate = max(best_rate, value)
            if average_std > 0:
                best_z = max(best_z, (value - average_mean) / average_std)
        retention = (best_rate / native_rate) if native_rate else 0.0
        retentions.append(retention)

        native_z = (
            (native_rate - density.mean) / density.std if density.std > 0 else 0.0
        )
        if native_z >= 2.0 and best_z < 2.0:
            lost_significance_count += 1

    return DilutionStats(
        window_minutes=window_minutes,
        mean_retention=mean(retentions),
        median_retention=median(retentions),
        min_retention=min(retentions),
        lost_significance_count=lost_significance_count,
    )


def count_events_in_window(sorted_timestamps_s: list[int], start_s: int, end_s: int) -> int:
    return bisect_left(sorted_timestamps_s, end_s) - bisect_left(sorted_timestamps_s, start_s)


def parse_int_list(values: str) -> list[int]:
    out: list[int] = []
    for raw in values.split(","):
        cleaned = raw.strip()
        if not cleaned:
            continue
        out.append(int(cleaned))
    if not out:
        raise ValueError("La lista de candidatos no puede quedar vacia.")
    return out


def evaluate_window_candidates(
    events: tuple[CommentEvent, ...],
    peaks: tuple[PeakRun, ...],
    *,
    window_candidates_s: list[int],
    slide_candidates_s: list[int],
) -> tuple[WindowCandidate, ...]:
    if not peaks:
        return ()

    sorted_timestamps_s = [event.timestamp_s for event in events]
    results: list[WindowCandidate] = []

    for window_size_s in window_candidates_s:
        window_minutes = window_size_s / float(SECONDS_PER_MINUTE)
        for slide_s in slide_candidates_s:
            retentions: list[float] = []
            for peak in peaks:
                native_rate = peak.native_rate_per_minute
                if native_rate <= 0:
                    retentions.append(0.0)
                    continue

                search_start = ((peak.start_s - window_size_s) // slide_s) * slide_s
                search_end = peak.end_s_exclusive
                best_rate = 0.0
                start_s = search_start
                while start_s <= search_end:
                    end_s = start_s + window_size_s
                    overlaps = not (
                        end_s <= peak.start_s or start_s >= peak.end_s_exclusive
                    )
                    if overlaps:
                        count = count_events_in_window(sorted_timestamps_s, start_s, end_s)
                        rate = count / window_minutes
                        best_rate = max(best_rate, rate)
                    start_s += slide_s
                retentions.append(best_rate / native_rate)

            results.append(
                WindowCandidate(
                    window_size_s=window_size_s,
                    slide_s=slide_s,
                    mean_retention=mean(retentions),
                    median_retention=median(retentions),
                    min_retention=min(retentions),
                )
            )

    return tuple(
        sorted(
            results,
            key=lambda candidate: (
                candidate.mean_retention,
                candidate.median_retention,
                -candidate.window_size_s,
                -candidate.slide_s,
            ),
            reverse=True,
        )
    )


def analyze_semantic_noise(
    events: tuple[CommentEvent, ...],
    *,
    high_density_minutes: set[int],
) -> SemanticNoiseStats:
    texts: list[str] = []
    for event in events:
        minute_bucket = bucket_floor(event.timestamp_s, SECONDS_PER_MINUTE)
        if minute_bucket not in high_density_minutes:
            continue
        normalized = normalize_spam_text(event.text)
        if normalized:
            texts.append(normalized)

    counts = Counter(texts)
    duplicate_excess = sum(count - 1 for count in counts.values() if count > 1)
    top_duplicates = tuple((text, count) for text, count in counts.most_common(5) if count > 1)
    return SemanticNoiseStats(
        high_density_minutes=len(high_density_minutes),
        comments_in_high_density=len(texts),
        duplicate_excess=duplicate_excess,
        duplicate_rate=(duplicate_excess / len(texts)) if texts else 0.0,
        top_duplicates=top_duplicates,
    )


def print_report(
    *,
    dataset: DatasetSummary,
    density: DensityStats,
    burstiness_label: str,
    high_density_threshold: int,
    peaks: tuple[PeakRun, ...],
    short_peak_share: float,
    xiao_reference: TriggerSimulation,
    xiao_minute_proxy: TriggerSimulation | None,
    dilution_5m: DilutionStats,
    dilution_10m: DilutionStats,
    candidates: tuple[WindowCandidate, ...],
    semantic_noise: SemanticNoiseStats,
) -> None:
    history_days = (dataset.end_s - dataset.start_s) / float(SECONDS_PER_DAY)
    best_candidate = candidates[0] if candidates else None

    print("REPORTE DE AUDITORIA")
    print("=" * 80)
    print(f"Fuente: {dataset.source_path}")
    print(
        "Cobertura: "
        f"{iso(dataset.start_s)} -> {iso(dataset.end_s)} "
        f"({history_days:.2f} dias)"
    )
    print(
        "Registros: "
        f"{dataset.row_count:,} filas | {dataset.event_count:,} eventos validos | "
        f"{dataset.unique_videos} videos"
    )
    print(
        "Calidad basica: "
        f"{dataset.missing_text_count} textos vacios | "
        f"{dataset.invalid_timestamp_count} timestamps invalidos"
    )
    print(
        "Contrato temporal: "
        f"campo solicitado={dataset.requested_timestamp_field} | "
        f"campo usado={dataset.timestamp_field} | unidad inferida={dataset.unit_name}"
    )
    if dataset.timestamp_field.endswith("_unix_ms"):
        print(
            "Aviso temporal: "
            f"{dataset.timestamp_field} es un nombre legacy; "
            "el contrato vigente usa Unix epoch en segundos."
        )
    if dataset.unit_name != "s":
        print(
            "Aviso temporal: "
            f"el campo {dataset.timestamp_field} parece venir en {dataset.unit_name}, "
            "pero el contrato vigente espera segundos."
        )

    print()
    print("1) Analisis de densidad y volatilidad")
    print(
        f"- Volumen base: 60s | bins observados: {density.total_bins:,} | "
        f"bins activos: {density.active_bins:,} ({density.active_share:.2%})"
    )
    print(
        f"- mu={density.mean:.3f} comentarios/min | "
        f"sigma^2={density.variance:.3f} | "
        f"ID=sigma^2/mu={density.dispersion_index:.3f}"
    )
    print(
        f"- P95={density.q95:.0f} | P99={density.q99:.0f} | max={density.max_count} comentarios/min"
    )
    print(
        f"- Burstiness: {burstiness_label} "
        "(escala operativa basada en sobre-dispersion; la referencia de Sahin no define cortes ordinales explicitos)."
    )

    print()
    print("2) Simulacion de trigger (Xiao et al.)")
    print(
        f"- Trigger alineado a la referencia ({xiao_reference.bin_size_s}s): "
        f"{xiao_reference.trigger_count} episodios | "
        f"{xiao_reference.activation_bins} bins activados de {xiao_reference.eligible_bins} elegibles | "
        f"K_max={xiao_reference.max_k:.2f} | ratio_EMA_max={xiao_reference.max_activation_ratio:.2f}"
    )
    if history_days < 180.0:
        print(
            "- Nota: la referencia pide 180 dias de historial. "
            "Aqui se usa el historial disponible como proxy."
        )
    for episode in xiao_reference.episodes[:3]:
        print(
            "- Episodio: "
            f"{iso(episode.start_s)} -> {iso(episode.end_s)} "
            f"({format_duration_hours(episode.start_s, episode.end_s)} h), "
            f"pico={episode.peak_count} en {iso(episode.peak_s)}, "
            f"EMA12_inicio={episode.start_ema_short:.2f}, "
            f"baseline={episode.baseline_ema_short:.2f}, "
            f"K_inicio={episode.start_k:.2f}"
        )
    if xiao_minute_proxy is not None:
        print(
            f"- Proxy minuto a minuto (60s): {xiao_minute_proxy.trigger_count} triggers. "
            "Sirve como stress test de sobrerreaccion."
        )

    print()
    print("3) Prueba de granularidad (Kilroy et al.)")
    print(
        f"- Umbral de alta densidad: {high_density_threshold} comentarios/min "
        "(auto=max(P99, mu + 3*sigma))"
    )
    print(
        f"- Rafagas intensas <= 2 min: {len(peaks)} | "
        f"participacion sobre todas las rafagas intensas: {short_peak_share:.2%}"
    )
    print(
        f"- Ventanas de 5 min: retencion media={dilution_5m.mean_retention:.2%}, "
        f"mediana={dilution_5m.median_retention:.2%}, "
        f"min={dilution_5m.min_retention:.2%}, "
        f"picos que pierden z>=2: {dilution_5m.lost_significance_count}"
    )
    print(
        f"- Ventanas de 10 min: retencion media={dilution_10m.mean_retention:.2%}, "
        f"mediana={dilution_10m.median_retention:.2%}, "
        f"min={dilution_10m.min_retention:.2%}, "
        f"picos que pierden z>=2: {dilution_10m.lost_significance_count}"
    )
    print("- Ranking de window_size / slide_interval por retencion media:")
    for candidate in candidates[:5]:
        print(
            f"  * {candidate.window_size_s}s / {candidate.slide_s}s -> "
            f"mean={candidate.mean_retention:.2%}, "
            f"median={candidate.median_retention:.2%}, "
            f"min={candidate.min_retention:.2%}"
        )

    print()
    print("4) Analisis de ruido semantico")
    print(
        f"- Minutos de alta densidad: {semantic_noise.high_density_minutes} | "
        f"comentarios no vacios en esos minutos: {semantic_noise.comments_in_high_density:,}"
    )
    print(
        f"- Duplicados exactos (tras normalizar espacios): "
        f"{semantic_noise.duplicate_excess:,} comentarios extra | "
        f"tasa={semantic_noise.duplicate_rate:.2%}"
    )
    if semantic_noise.top_duplicates:
        print("- Textos repetidos mas frecuentes:")
        for text, count in semantic_noise.top_duplicates:
            preview = text[:90]
            print(f"  * {count:>3}x | {preview}")

    print()
    print("5) Respuesta ejecutiva")
    if density.dispersion_index > 1.0 and short_peak_share >= 0.5:
        print(
            "- Estabilidad del flujo: no es suficientemente estable para ventanas fijas gruesas "
            "(5-10 min). El flujo es sobre-disperso y concentra muchas rafagas breves."
        )
    else:
        print(
            "- Estabilidad del flujo: si tolera ventanas fijas, pero conviene validarlas contra "
            "rafagas breves antes de endurecer el prototipo."
        )

    if xiao_reference.trigger_count > 0:
        print(
            "- Xiao dinamico: util como supervisor macro para abrir/cerrar episodios de interes, "
            "pero no reemplaza ventanas cortas para detectar picos sub-2-min."
        )
    else:
        print(
            "- Xiao dinamico: con el historial disponible no ofrece una senal suficientemente estable "
            "por si solo; hoy conviene tratarlo como complemento y no como unico disparador."
        )

    if best_candidate is not None:
        print(
            "- Recomendacion para StreamDetector: "
            f"window_size='{int(best_candidate.window_size_s / 60)}min', "
            f"slide_interval='{best_candidate.slide_s}s'."
        )
        print(
            "- Justificacion: esa combinacion maximiza la retencion media de picos cortos "
            f"({best_candidate.mean_retention:.2%}) dentro de los candidatos evaluados."
        )
    else:
        print(
            "- Recomendacion para StreamDetector: no hubo suficientes picos cortos para rankear "
            "ventanas; usa un valor inicial conservador de 2min / 60s y vuelve a auditar."
        )

    print(
        "- Configuracion sugerida de prototipo: ventanas fijas cortas para scoring local + "
        "trigger horario de Xiao como capa de activacion superior cuando acumules mas historia."
    )


def main() -> None:
    args = parse_args()
    input_path = resolve_input_path(args.input)
    dataset = load_dataset(input_path, args.ts_field, args.text_field)

    minute_buckets, minute_series, minute_counts = build_series(
        dataset.events, SECONDS_PER_MINUTE
    )
    density = compute_density_stats(minute_series)
    burstiness_label = classify_burstiness(density.dispersion_index)

    high_density_threshold = choose_high_density_threshold(
        density, args.high_density_threshold
    )
    peaks = detect_short_peaks(
        minute_buckets,
        minute_series,
        threshold=high_density_threshold,
        max_duration_minutes=2,
    )

    all_intense_runs = detect_short_peaks(
        minute_buckets,
        minute_series,
        threshold=high_density_threshold,
        max_duration_minutes=10**9,
    )
    intense_run_count = len(all_intense_runs)
    short_peak_share = (
        (len(peaks) / float(intense_run_count)) if intense_run_count else 0.0
    )

    xiao_reference = simulate_xiao_trigger(
        dataset.events,
        bin_size_s=args.trigger_bin_seconds,
    )
    xiao_minute_proxy = None
    if args.trigger_proxy_minute_scan:
        xiao_minute_proxy = simulate_xiao_trigger(
            dataset.events,
            bin_size_s=SECONDS_PER_MINUTE,
        )

    dilution_5m = analyze_dilution(
        minute_buckets,
        minute_series,
        peaks,
        density,
        window_minutes=5,
    )
    dilution_10m = analyze_dilution(
        minute_buckets,
        minute_series,
        peaks,
        density,
        window_minutes=10,
    )

    window_candidates_s = parse_int_list(args.window_candidates)
    slide_candidates_s = parse_int_list(args.slide_candidates)
    candidates = evaluate_window_candidates(
        dataset.events,
        peaks,
        window_candidates_s=window_candidates_s,
        slide_candidates_s=slide_candidates_s,
    )

    high_density_minutes = {
        bucket for bucket, count in minute_counts.items() if count >= high_density_threshold
    }
    semantic_noise = analyze_semantic_noise(
        dataset.events,
        high_density_minutes=high_density_minutes,
    )

    print_report(
        dataset=dataset,
        density=density,
        burstiness_label=burstiness_label,
        high_density_threshold=high_density_threshold,
        peaks=peaks,
        short_peak_share=short_peak_share,
        xiao_reference=xiao_reference,
        xiao_minute_proxy=xiao_minute_proxy,
        dilution_5m=dilution_5m,
        dilution_10m=dilution_10m,
        candidates=candidates,
        semantic_noise=semantic_noise,
    )


if __name__ == "__main__":
    main()
