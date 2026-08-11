from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .rag_evidence import write_json


RAG_POC_ARTIFACT_VERSION = "rag_poc_notebook_integration_v1"

QUERIES_FILE = "queries_df.csv"
NEWS_FILE = "noticias_df.csv"
AUDIT_FILE = "auditoria_df.csv"
COMMENTS_VECTORSTORE_DIR = "vectorstore_comentarios"
NEWS_VECTORSTORE_DIR = "vectorstore_noticias"
MANIFEST_FILE = "rag_poc_manifest.json"
LINEAGE_FILE = "rag_poc_lineage.csv"
SUMMARY_FILE = "rag_poc_summary.json"

TRIGGER_COMMENT_MAP_COLUMNS = {
    "trigger_time",
    "window_start",
    "window_end",
    "trigger_volume",
    "trigger_strength",
    "order_in_trigger",
    "event_time_utc",
    "video_id",
    "title",
    "channel_title",
    "author_id",
    "comment_id",
    "text",
}

QUERY_PROMPT_TEMPLATE = """Actúa como un experto analista de medios en Colombia. He detectado un pico de actividad en YouTube.
Título del Video: {title}
Muestra de Comentarios: {lista_comentarios}

Tarea: Genera una única cadena de búsqueda (query) optimizada para News API que me permita encontrar la noticia real que causó este pico.
Reglas:
1. Usa máximo 5 palabras.
2. Prioriza nombres propios y eventos específicos (ej. 'debate', 'captura', 'discurso').
3. No incluyas palabras vacías ni la palabra 'YouTube'.
Respuesta: Solo entrega la cadena de búsqueda."""

AUDIT_PROMPT_TEMPLATE = """Actúa como un Auditor de Integridad de Datos especializado en análisis de desinformación y eventos sociopolíticos en Colombia.

Contexto del Trigger (YouTube):
ID del Evento: {event_id} (Trigger Time: {trigger_time} | Video: {title})

Comentarios Recuperados:
> {chunks_comentarios}

Contexto de Cronología Pública (News API):
Noticias de la Fecha:
> {chunks_noticias}

Tarea:
Tu objetivo es determinar si el pico de actividad detectado por el sistema es un "Evento Externo" (basado en hechos reales reportados por la prensa) o un "Evento Interno" (ruido orgánico, chistes del canal o ataques coordinados).

Instrucciones de Análisis:
1. Relación Semántica: ¿Los nombres propios, lugares o acciones mencionadas en los comentarios aparecen en las noticias?
2. Sincronía: ¿La noticia reportada justifica un aumento súbito en el volumen de comentarios?
3. Veredicto: Clasifica el evento en una de estas categorías:
   [CONFIRMADO]: Hay una noticia clara que explica el pico.
   [PROBABLE]: Hay noticias relacionadas con el tema, pero no con el suceso específico.
   [COMUNIDAD]: El pico es una reacción al contenido del video (ej. humor, sátira) sin eco en la prensa.
   [DESINFORMACIÓN/RUIDO]: Los comentarios afirman hechos que la prensa desmiente o ignora totalmente.

Responde con el siguiente formato:
Veredicto: [CATEGORÍA]
Justificación: (2-3 oraciones explicando tu razonamiento)"""


@dataclass(frozen=True)
class RagPocConfig:
    trigger_comment_map_path: str
    output_dir: str
    event_comment_map_path: str | None = None
    run_id: str | None = None
    openai_model: str = "gpt-5-mini"
    openai_temperature: float = 1.0
    embedding_model: str = "text-embedding-ada-002"
    serper_url: str = "https://google.serper.dev/news"
    serper_gl: str = "co"
    serper_hl: str = "es"
    serper_type: str = "news"
    serper_num_results: int = 5
    serper_sleep_seconds: float = 1.0
    notes: str | None = None
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "RagPocConfig":
        missing = [
            key
            for key in ["trigger_comment_map_path", "output_dir"]
            if not payload.get(key)
        ]
        if missing:
            raise ValueError(
                "RAG PoC config missing required fields: " + ", ".join(missing)
            )
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError("params must be an object.")
        return cls(
            trigger_comment_map_path=str(payload["trigger_comment_map_path"]),
            output_dir=str(payload["output_dir"]),
            event_comment_map_path=(
                str(payload["event_comment_map_path"])
                if payload.get("event_comment_map_path")
                else None
            ),
            run_id=payload.get("run_id"),
            openai_model=str(payload.get("openai_model", "gpt-5-mini")),
            openai_temperature=float(payload.get("openai_temperature", 1.0)),
            embedding_model=str(payload.get("embedding_model", "text-embedding-ada-002")),
            serper_url=str(payload.get("serper_url", "https://google.serper.dev/news")),
            serper_gl=str(payload.get("serper_gl", "co")),
            serper_hl=str(payload.get("serper_hl", "es")),
            serper_type=str(payload.get("serper_type", "news")),
            serper_num_results=int(payload.get("serper_num_results", 5)),
            serper_sleep_seconds=float(payload.get("serper_sleep_seconds", 1.0)),
            notes=payload.get("notes"),
            params=params,
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return Path(path).as_posix()


def _short_hash(*parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def _default_run_id(config: RagPocConfig) -> str:
    return f"ragpoc_{_short_hash(config.trigger_comment_map_path, config.output_dir)}"


def _output_paths(config: RagPocConfig) -> dict[str, str]:
    output_root = Path(config.output_dir)
    return {
        "queries": (output_root / QUERIES_FILE).as_posix(),
        "news": (output_root / NEWS_FILE).as_posix(),
        "audit": (output_root / AUDIT_FILE).as_posix(),
        "comments_vectorstore": (output_root / COMMENTS_VECTORSTORE_DIR).as_posix(),
        "news_vectorstore": (output_root / NEWS_VECTORSTORE_DIR).as_posix(),
        "manifest": (output_root / MANIFEST_FILE).as_posix(),
        "lineage": (output_root / LINEAGE_FILE).as_posix(),
        "summary": (output_root / SUMMARY_FILE).as_posix(),
    }


def _extract_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("rag_poc")
    if nested is None:
        return payload
    if not isinstance(nested, dict):
        raise ValueError("rag_poc config section must be an object.")
    return nested


def _merge_config_payloads(*payloads: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for payload in payloads:
        for key, value in payload.items():
            if value is None:
                continue
            if key == "params":
                current = merged.get(key, {})
                if not isinstance(current, dict) or not isinstance(value, dict):
                    raise ValueError("params must be an object.")
                merged[key] = {**current, **value}
            else:
                merged[key] = value
    return merged


def load_rag_poc_config(
    path: str | Path,
    *,
    overrides: dict[str, Any] | None = None,
) -> RagPocConfig:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"RAG PoC config must be an object: {p}")
    base = _extract_config_payload(payload)
    merged = _merge_config_payloads(base, overrides or {})
    return RagPocConfig.from_mapping(merged)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "python-dotenv is required to load RAG PoC environment variables."
        ) from exc
    load_dotenv()


def _prompt_template_class() -> Any:
    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langchain-core is required to run the RAG PoC prompts."
        ) from exc
    return ChatPromptTemplate


def _chat_openai_class() -> Any:
    try:
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langchain-openai is required to run the RAG PoC LLM steps."
        ) from exc
    return ChatOpenAI


def _embedding_class() -> Any:
    try:
        from langchain_openai import OpenAIEmbeddings
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langchain-openai is required to build the RAG PoC vectorstores."
        ) from exc
    return OpenAIEmbeddings


def _document_class() -> Any:
    try:
        from langchain_core.documents import Document
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langchain-core is required to build the RAG PoC documents."
        ) from exc
    return Document


def _chroma_class() -> Any:
    try:
        from langchain.vectorstores import Chroma
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langchain and chromadb are required to build the RAG PoC vectorstores."
        ) from exc
    return Chroma


def _openai_api_key() -> str | None:
    _load_dotenv()
    return os.environ.get("OPENAI_API_KEY")


def _serper_api_key() -> str | None:
    _load_dotenv()
    return os.environ.get("SERPER_API_KEY")


def _build_llm(config: RagPocConfig) -> Any:
    ChatOpenAI = _chat_openai_class()
    return ChatOpenAI(
        model=config.openai_model,
        api_key=_openai_api_key(),
        temperature=config.openai_temperature,
    )


def read_trigger_comment_map(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = sorted(TRIGGER_COMMENT_MAP_COLUMNS.difference(df.columns))
    if missing:
        raise KeyError(
            "trigger_comment_map.csv missing required columns: " + ", ".join(missing)
        )
    return df


def group_trigger_comments(trigger_df: pd.DataFrame) -> pd.DataFrame:
    return (
        trigger_df.groupby(["trigger_time", "video_id"])
        .agg(title=("title", "first"), comentarios=("text", list))
        .reset_index()
    )


def generar_query(title: str, comentarios: list[str], llm: Any) -> str:
    ChatPromptTemplate = _prompt_template_class()
    prompt_template = ChatPromptTemplate.from_template(QUERY_PROMPT_TEMPLATE)
    prompt = prompt_template.format(title=title, lista_comentarios=comentarios)
    respuesta = llm.invoke(prompt)
    return respuesta.content


def load_or_generate_queries(
    grouped_agg: pd.DataFrame,
    *,
    queries_path: str | Path,
    llm: Any,
) -> pd.DataFrame:
    p = Path(queries_path)
    if p.exists():
        return pd.read_csv(p)

    queries = []
    for _, row in grouped_agg.iterrows():
        query = generar_query(row["title"], row["comentarios"], llm)
        queries.append(
            {
                "trigger_time": row["trigger_time"],
                "video_id": row["video_id"],
                "title": row["title"],
                "news_api_query": query,
            }
        )
    queries_df = pd.DataFrame(queries)
    p.parent.mkdir(parents=True, exist_ok=True)
    queries_df.to_csv(p, index=False)
    return queries_df


def consultar_serper(
    query: str,
    trigger_time: Any,
    *,
    serper_api_key: str | None,
    serper_url: str,
    gl: str,
    hl: str,
    search_type: str,
    num_results: int = 5,
) -> pd.DataFrame:
    fecha = pd.Timestamp(trigger_time).date()
    fecha_min = (fecha - timedelta(days=1)).strftime("%-m/%-d/%Y")
    fecha_max = (fecha + timedelta(days=1)).strftime("%-m/%-d/%Y")

    payload = {
        "q": query,
        "gl": gl,
        "hl": hl,
        "tbs": f"cdr:1,cd_min:{fecha_min},cd_max:{fecha_max}",
        "type": search_type,
        "num": num_results,
    }
    headers = {
        "X-API-KEY": serper_api_key,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(serper_url, json=payload, headers=headers)
        resp.raise_for_status()
        noticias = resp.json().get("news", [])
        return pd.DataFrame(noticias) if noticias else pd.DataFrame()
    except Exception as exc:
        print(f"Error en '{query}': {exc}")
        return pd.DataFrame()


def load_or_fetch_news(
    queries_df: pd.DataFrame,
    *,
    news_path: str | Path,
    config: RagPocConfig,
) -> pd.DataFrame:
    p = Path(news_path)
    if p.exists():
        return pd.read_csv(p)

    resultados = []
    serper_api_key = _serper_api_key()
    for i, (_, row) in enumerate(queries_df.iterrows()):
        articulos_df = consultar_serper(
            row["news_api_query"],
            row["trigger_time"],
            serper_api_key=serper_api_key,
            serper_url=config.serper_url,
            gl=config.serper_gl,
            hl=config.serper_hl,
            search_type=config.serper_type,
            num_results=config.serper_num_results,
        )
        n = len(articulos_df) if not articulos_df.empty else 0
        print(f"[{i+1}/{len(queries_df)}] '{row['news_api_query']}' -> {n} articulos")
        if not articulos_df.empty:
            articulos_df["trigger_time"] = row["trigger_time"]
            articulos_df["news_api_query"] = row["news_api_query"]
            resultados.append(articulos_df)
        time.sleep(config.serper_sleep_seconds)

    resultados_df = (
        pd.concat(resultados, ignore_index=True) if resultados else pd.DataFrame()
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    resultados_df.to_csv(p, index=False)
    return resultados_df


def create_vectorstore(
    chunks: list[Any],
    embedding_function: Any,
    vectorstore_path: str | Path,
) -> Any:
    Chroma = _chroma_class()
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.page_content)) for doc in chunks]
    unique_ids = set()
    unique_chunks = []
    for chunk, item_id in zip(chunks, ids):
        if item_id not in unique_ids:
            unique_ids.add(item_id)
            unique_chunks.append(chunk)
    vectorstore = Chroma.from_documents(
        documents=unique_chunks,
        ids=list(unique_ids),
        embedding=embedding_function,
        persist_directory=str(vectorstore_path),
    )
    vectorstore.persist()
    return vectorstore


def build_vectorstores(
    grouped_agg: pd.DataFrame,
    resultados_df: pd.DataFrame,
    *,
    config: RagPocConfig,
    comments_vectorstore_path: str | Path,
    news_vectorstore_path: str | Path,
) -> dict[str, int]:
    Document = _document_class()
    OpenAIEmbeddings = _embedding_class()
    embedding_function = OpenAIEmbeddings(
        model=config.embedding_model,
        openai_api_key=_openai_api_key(),
    )

    comentarios_docs = []
    for _, row in grouped_agg.iterrows():
        texto = (
            f"Video: {row['title']}\n\nComentarios:\n"
            + "\n".join(f"- {comment}" for comment in row["comentarios"])
        )
        comentarios_docs.append(
            Document(
                page_content=texto,
                metadata={
                    "trigger_time": str(row["trigger_time"]),
                    "video_id": str(row["video_id"]),
                    "title": str(row["title"]),
                    "tipo": "comentarios",
                },
            )
        )

    create_vectorstore(
        chunks=comentarios_docs,
        embedding_function=embedding_function,
        vectorstore_path=comments_vectorstore_path,
    )
    print(f"Comentarios guardados: {len(comentarios_docs)} grupos")

    noticias_docs = []
    for _, row in resultados_df.iterrows():
        texto = f"Titular: {row.get('title', '')}\n\n{row.get('snippet', '')}"
        noticias_docs.append(
            Document(
                page_content=texto,
                metadata={
                    "trigger_time": str(row.get("trigger_time", "")),
                    "query": str(row.get("news_api_query", "")),
                    "source": str(row.get("source", "")),
                    "link": str(row.get("link", "")),
                    "date": str(row.get("date", "")),
                    "tipo": "noticia",
                },
            )
        )

    create_vectorstore(
        chunks=noticias_docs,
        embedding_function=embedding_function,
        vectorstore_path=news_vectorstore_path,
    )
    print(f"Noticias guardadas: {len(noticias_docs)} articulos")
    return {
        "comment_document_count": int(len(comentarios_docs)),
        "news_document_count": int(len(noticias_docs)),
    }


def load_or_audit_events(
    grouped_agg: pd.DataFrame,
    queries_df: pd.DataFrame,
    resultados_df: pd.DataFrame,
    *,
    audit_path: str | Path,
    llm: Any,
) -> pd.DataFrame:
    p = Path(audit_path)
    if p.exists():
        return pd.read_csv(p)

    ChatPromptTemplate = _prompt_template_class()
    audit_prompt = ChatPromptTemplate.from_template(AUDIT_PROMPT_TEMPLATE)
    merged = grouped_agg.merge(
        queries_df[["trigger_time", "video_id", "news_api_query"]],
        on=["trigger_time", "video_id"],
        how="left",
    )

    resultados_auditoria = []
    for i, (_, row) in enumerate(merged.iterrows()):
        noticias_grupo = resultados_df[
            (resultados_df["trigger_time"].astype(str) == str(row["trigger_time"]))
            & (
                resultados_df["news_api_query"].astype(str)
                == str(row.get("news_api_query", ""))
            )
        ]

        chunks_comentarios = "\n".join(f"- {comment}" for comment in row["comentarios"][:15])

        if not noticias_grupo.empty:
            chunks_noticias = "\n\n".join(
                f"[{r.get('source', '')}] {r.get('title', '')}: {r.get('snippet', '')}"
                for _, r in noticias_grupo.iterrows()
            )
        else:
            chunks_noticias = "No se encontraron noticias para este evento."

        prompt = audit_prompt.format(
            event_id=row["video_id"],
            trigger_time=row["trigger_time"],
            title=row["title"],
            chunks_comentarios=chunks_comentarios,
            chunks_noticias=chunks_noticias,
        )

        respuesta = llm.invoke(prompt)
        resultados_auditoria.append(
            {
                "trigger_time": row["trigger_time"],
                "video_id": row["video_id"],
                "title": row["title"],
                "news_api_query": row.get("news_api_query", ""),
                "n_noticias": len(noticias_grupo),
                "auditoria": respuesta.content,
            }
        )

        print(f"[{i+1}/{len(merged)}] {str(row['title'])[:50]}...")

    auditoria_df = pd.DataFrame(resultados_auditoria)
    p.parent.mkdir(parents=True, exist_ok=True)
    auditoria_df.to_csv(p, index=False)
    return auditoria_df


def build_poc_lineage(
    *,
    grouped_agg: pd.DataFrame,
    queries_df: pd.DataFrame | None,
    resultados_df: pd.DataFrame | None,
    auditoria_df: pd.DataFrame | None,
    event_comment_map_path: str | Path | None,
) -> pd.DataFrame:
    lineage = grouped_agg.copy()
    lineage["_trigger_time_key"] = pd.to_datetime(
        lineage["trigger_time"], utc=True, errors="coerce"
    ).map(lambda value: value.isoformat() if pd.notna(value) else None)
    lineage["rag_poc_comment_count"] = lineage["comentarios"].map(len)
    lineage = lineage.drop(columns=["comentarios"])

    if queries_df is not None and not queries_df.empty:
        lineage = lineage.merge(
            queries_df[["trigger_time", "video_id", "news_api_query"]],
            on=["trigger_time", "video_id"],
            how="left",
        )
    else:
        lineage["news_api_query"] = pd.NA

    if resultados_df is not None and not resultados_df.empty:
        news_counts = (
            resultados_df.groupby(["trigger_time", "news_api_query"])
            .size()
            .reset_index(name="n_noticias_retrieved")
        )
        lineage = lineage.merge(
            news_counts,
            on=["trigger_time", "news_api_query"],
            how="left",
        )
    else:
        lineage["n_noticias_retrieved"] = pd.NA

    if auditoria_df is not None and not auditoria_df.empty:
        audit_cols = [
            "trigger_time",
            "video_id",
            "news_api_query",
            "n_noticias",
            "auditoria",
        ]
        lineage = lineage.merge(
            auditoria_df[audit_cols],
            on=["trigger_time", "video_id", "news_api_query"],
            how="left",
            suffixes=("", "_audit"),
        )
    else:
        lineage["n_noticias"] = pd.NA
        lineage["auditoria"] = pd.NA

    if event_comment_map_path:
        event_map = pd.read_csv(event_comment_map_path)
        if {"event_id", "trigger_time_utc", "video_id", "comment_id"}.issubset(
            event_map.columns
        ):
            event_map = event_map.rename(columns={"trigger_time_utc": "trigger_time"})
            event_map["_trigger_time_key"] = pd.to_datetime(
                event_map["trigger_time"], utc=True, errors="coerce"
            ).map(lambda value: value.isoformat() if pd.notna(value) else None)
            event_counts = (
                event_map.groupby(["event_id", "_trigger_time_key", "video_id"])
                .agg(event_comment_count=("comment_id", "nunique"))
                .reset_index()
            )
            lineage = lineage.merge(
                event_counts,
                on=["_trigger_time_key", "video_id"],
                how="left",
            )
    if "event_id" not in lineage.columns:
        lineage["event_id"] = pd.NA
    if "event_comment_count" not in lineage.columns:
        lineage["event_comment_count"] = pd.NA

    return lineage[
        [
            "event_id",
            "trigger_time",
            "video_id",
            "title",
            "rag_poc_comment_count",
            "event_comment_count",
            "news_api_query",
            "n_noticias_retrieved",
            "n_noticias",
            "auditoria",
        ]
    ]


def build_manifest(
    *,
    config: RagPocConfig,
    run_id: str,
    output_paths: dict[str, str],
    dry_run: bool,
    created_at_utc: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at_utc": created_at_utc,
        "pipeline_stage": "rag_poc_validation",
        "mode": "dry_run_contract_only" if dry_run else "notebook_poc_execution",
        "artifact_version": RAG_POC_ARTIFACT_VERSION,
        "source_notebook": ".agents/examples/structured-rag-pdf/triggers_validation.ipynb",
        "trigger_comment_map_path": _normalize_path(config.trigger_comment_map_path),
        "event_comment_map_path": _normalize_path(config.event_comment_map_path),
        "output_paths": output_paths,
        "poc_contract": {
            "unit_of_analysis": "trigger_time + video_id",
            "query_model": config.openai_model,
            "query_temperature": config.openai_temperature,
            "embedding_model": config.embedding_model,
            "serper_url": config.serper_url,
            "serper_gl": config.serper_gl,
            "serper_hl": config.serper_hl,
            "serper_type": config.serper_type,
            "serper_num_results": config.serper_num_results,
            "serper_sleep_seconds": config.serper_sleep_seconds,
            "audit_comment_limit": 15,
        },
        "notes": config.notes,
        "params": config.params,
    }


def run_rag_poc(config: RagPocConfig, *, dry_run: bool = False) -> dict[str, Any]:
    output_root = Path(config.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_paths = _output_paths(config)
    run_id = config.run_id or _default_run_id(config)
    created_at = _utc_now_iso()

    trigger_df = read_trigger_comment_map(config.trigger_comment_map_path)
    grouped_agg = group_trigger_comments(trigger_df)

    queries_df: pd.DataFrame | None = None
    resultados_df: pd.DataFrame | None = None
    auditoria_df: pd.DataFrame | None = None
    vectorstore_counts = {"comment_document_count": 0, "news_document_count": 0}

    if not dry_run:
        llm = _build_llm(config)
        queries_df = load_or_generate_queries(
            grouped_agg,
            queries_path=output_paths["queries"],
            llm=llm,
        )
        resultados_df = load_or_fetch_news(
            queries_df,
            news_path=output_paths["news"],
            config=config,
        )
        vectorstore_counts = build_vectorstores(
            grouped_agg,
            resultados_df,
            config=config,
            comments_vectorstore_path=output_paths["comments_vectorstore"],
            news_vectorstore_path=output_paths["news_vectorstore"],
        )
        auditoria_df = load_or_audit_events(
            grouped_agg,
            queries_df,
            resultados_df,
            audit_path=output_paths["audit"],
            llm=llm,
        )

    lineage = build_poc_lineage(
        grouped_agg=grouped_agg,
        queries_df=queries_df,
        resultados_df=resultados_df,
        auditoria_df=auditoria_df,
        event_comment_map_path=config.event_comment_map_path,
    )
    lineage.to_csv(output_paths["lineage"], index=False)

    manifest = build_manifest(
        config=config,
        run_id=run_id,
        output_paths=output_paths,
        dry_run=dry_run,
        created_at_utc=created_at,
    )
    write_json(output_paths["manifest"], manifest)

    summary = {
        "run_id": run_id,
        "artifact_version": RAG_POC_ARTIFACT_VERSION,
        "mode": manifest["mode"],
        "trigger_comment_rows": int(len(trigger_df)),
        "trigger_time_count": int(trigger_df["trigger_time"].nunique()),
        "trigger_video_group_count": int(len(grouped_agg)),
        "unique_video_count": int(trigger_df["video_id"].nunique()),
        "queries_count": int(len(queries_df)) if queries_df is not None else 0,
        "news_count": int(len(resultados_df)) if resultados_df is not None else 0,
        "audit_count": int(len(auditoria_df)) if auditoria_df is not None else 0,
        "lineage_rows": int(len(lineage)),
        "output_paths": output_paths,
        **vectorstore_counts,
    }
    write_json(output_paths["summary"], summary)
    return summary


def run_rag_poc_from_config(config: RagPocConfig, *, dry_run: bool = False) -> dict[str, Any]:
    return run_rag_poc(config, dry_run=dry_run)


__all__ = [
    "AUDIT_FILE",
    "AUDIT_PROMPT_TEMPLATE",
    "LINEAGE_FILE",
    "MANIFEST_FILE",
    "NEWS_FILE",
    "QUERIES_FILE",
    "QUERY_PROMPT_TEMPLATE",
    "RAG_POC_ARTIFACT_VERSION",
    "RagPocConfig",
    "SUMMARY_FILE",
    "build_poc_lineage",
    "consultar_serper",
    "create_vectorstore",
    "generar_query",
    "group_trigger_comments",
    "load_rag_poc_config",
    "read_trigger_comment_map",
    "run_rag_poc",
    "run_rag_poc_from_config",
]
