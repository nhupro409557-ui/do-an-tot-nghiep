from __future__ import annotations

import asyncio
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any

import asyncpg
import httpx

from app.application.ai.catalog_index_search import (
    DEFAULT_INDEX_DIR,
    excerpt_from_markdown,
    query_tokens,
    search_catalog_index,
    title_from_markdown,
)
from app.config import settings


DEFAULT_EMBEDDING_INDEX_PATH = Path(settings.catalog_embedding_index_path)
MAX_EMBEDDING_TEXT_CHARS = 6000
GEMINI_EMBEDDING_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
)
CATALOG_EMBEDDING_TABLE = "catalog_embedding_documents"


def normalize_asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def prepare_embedding_query(query: str) -> str:
    return f"task: search result | query: {query}"


def prepare_embedding_document(*, title: str, text: str) -> str:
    clean_title = title.strip() or "none"
    clean_text = " ".join(text.split())[:MAX_EMBEDDING_TEXT_CHARS]
    return f"title: {clean_title} | text: {clean_text}"


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_embedding(response_payload: dict[str, Any]) -> list[float]:
    embedding = response_payload.get("embedding")
    if isinstance(embedding, dict) and isinstance(embedding.get("values"), list):
        return [float(value) for value in embedding["values"]]

    embeddings = response_payload.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, dict) and isinstance(first.get("values"), list):
            return [float(value) for value in first["values"]]

    raise ValueError("Gemini embedding response does not contain embedding values.")


async def embed_text(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    model: str,
    text: str,
    output_dimensionality: int,
    task_type: str | None = None,
) -> list[float]:
    payload: dict[str, Any] = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]},
        "output_dimensionality": output_dimensionality,
    }
    if task_type:
        payload["taskType"] = task_type

    response = await client.post(
        GEMINI_EMBEDDING_ENDPOINT.format(model=model),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        json=payload,
    )
    response.raise_for_status()
    return extract_embedding(response.json())


def dense_cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    if dot <= 0:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def load_embedding_index(index_path: Path = DEFAULT_EMBEDDING_INDEX_PATH) -> dict[str, Any] | None:
    if not index_path.exists():
        return None
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("documents"), list):
        return None
    return data


def embedding_table_ddl() -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS {CATALOG_EMBEDDING_TABLE} (
        file TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        excerpt TEXT NOT NULL DEFAULT '',
        text_hash TEXT NOT NULL,
        provider TEXT NOT NULL DEFAULT 'gemini',
        model TEXT NOT NULL,
        output_dimensionality INTEGER NOT NULL,
        embedding JSONB NOT NULL,
        source_dir TEXT NOT NULL DEFAULT '',
        complete_snapshot BOOLEAN NOT NULL DEFAULT FALSE,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT catalog_embedding_documents_embedding_array_check
            CHECK (jsonb_typeof(embedding) = 'array'),
        CONSTRAINT catalog_embedding_documents_dimensionality_check
            CHECK (output_dimensionality > 0)
    )
    """


async def sync_embedding_index_to_database(
    payload: dict[str, Any],
    *,
    database_url: str = settings.database_url,
) -> int:
    documents = payload.get("documents")
    if not isinstance(documents, list):
        return 0

    connection = await asyncpg.connect(normalize_asyncpg_dsn(database_url))
    try:
        await connection.execute(embedding_table_ddl())
        async with connection.transaction():
            for document in documents:
                await connection.execute(
                    f"""
                    INSERT INTO {CATALOG_EMBEDDING_TABLE} (
                        file,
                        title,
                        excerpt,
                        text_hash,
                        provider,
                        model,
                        output_dimensionality,
                        embedding,
                        source_dir,
                        complete_snapshot,
                        updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, NOW())
                    ON CONFLICT (file) DO UPDATE SET
                        title = EXCLUDED.title,
                        excerpt = EXCLUDED.excerpt,
                        text_hash = EXCLUDED.text_hash,
                        provider = EXCLUDED.provider,
                        model = EXCLUDED.model,
                        output_dimensionality = EXCLUDED.output_dimensionality,
                        embedding = EXCLUDED.embedding,
                        source_dir = EXCLUDED.source_dir,
                        complete_snapshot = EXCLUDED.complete_snapshot,
                        updated_at = NOW()
                    """,
                    str(document.get("file") or ""),
                    str(document.get("title") or ""),
                    str(document.get("excerpt") or ""),
                    str(document.get("text_hash") or ""),
                    str(payload.get("provider") or "gemini"),
                    str(payload.get("model") or ""),
                    int(payload.get("output_dimensionality") or 0),
                    json.dumps(document.get("embedding") or []),
                    str(payload.get("source_dir") or ""),
                    bool(payload.get("complete")),
                )
        return len(documents)
    finally:
        await connection.close()


async def load_embedding_documents_from_database(
    *,
    database_url: str = settings.database_url,
    model: str = settings.gemini_embedding_model,
    output_dimensionality: int = settings.gemini_embedding_output_dimensionality,
) -> list[dict[str, Any]]:
    connection = await asyncpg.connect(normalize_asyncpg_dsn(database_url))
    try:
        exists = await connection.fetchval(
            "SELECT to_regclass($1) IS NOT NULL",
            f"public.{CATALOG_EMBEDDING_TABLE}",
        )
        if not exists:
            return []
        rows = await connection.fetch(
            f"""
            SELECT file, title, excerpt, text_hash, embedding
            FROM {CATALOG_EMBEDDING_TABLE}
            WHERE model = $1 AND output_dimensionality = $2
            ORDER BY file
            """,
            model,
            output_dimensionality,
        )
        documents = []
        for row in rows:
            embedding = json.loads(row["embedding"]) if isinstance(row["embedding"], str) else row["embedding"]
            documents.append(
                {
                    "file": row["file"],
                    "title": row["title"],
                    "excerpt": row["excerpt"],
                    "text_hash": row["text_hash"],
                    "embedding": embedding,
                }
            )
        return documents
    finally:
        await connection.close()


def embedding_task_type(model: str, *, query: bool) -> str | None:
    if model == "gemini-embedding-001":
        return "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT"
    return None


def make_index_payload(
    *,
    index_dir: Path,
    model: str,
    output_dimensionality: int,
    documents: list[dict[str, Any]],
    complete: bool,
    last_error: str | None = None,
) -> dict[str, Any]:
    payload = {
        "version": 1,
        "provider": "gemini",
        "model": model,
        "output_dimensionality": output_dimensionality,
        "source_dir": str(index_dir),
        "complete": complete,
        "documents": documents,
    }
    if last_error:
        payload["last_error"] = last_error
    return payload


def write_embedding_index(payload: dict[str, Any], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=index_path.parent,
        delete=False,
        suffix=".tmp",
    ) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False)
        temp_name = temp_file.name
    Path(temp_name).replace(index_path)


def reusable_documents(
    *,
    index_path: Path,
    model: str,
    output_dimensionality: int,
) -> dict[str, dict[str, Any]]:
    existing = load_embedding_index(index_path)
    if not existing:
        return {}
    if existing.get("model") != model or existing.get("output_dimensionality") != output_dimensionality:
        return {}

    reusable: dict[str, dict[str, Any]] = {}
    for document in existing.get("documents", []):
        if (
            isinstance(document, dict)
            and isinstance(document.get("file"), str)
            and isinstance(document.get("text_hash"), str)
            and isinstance(document.get("embedding"), list)
        ):
            reusable[document["file"]] = document
    return reusable


async def build_catalog_embedding_index(
    *,
    index_dir: Path = DEFAULT_INDEX_DIR,
    index_path: Path = DEFAULT_EMBEDDING_INDEX_PATH,
    api_key: str = settings.gemini_api_key,
    model: str = settings.gemini_embedding_model,
    output_dimensionality: int = settings.gemini_embedding_output_dimensionality,
    request_delay_seconds: float = settings.catalog_embedding_request_delay_seconds,
    max_documents: int = settings.catalog_embedding_max_documents,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("Thiếu GEMINI_API_KEY để build catalog embedding index.")
    if not index_dir.exists():
        raise RuntimeError(f"Chưa có thư mục index Markdown: {index_dir}")

    documents = []
    reusable = reusable_documents(
        index_path=index_path,
        model=model,
        output_dimensionality=output_dimensionality,
    )
    async with httpx.AsyncClient(timeout=30) as client:
        for path in sorted(index_dir.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            title = title_from_markdown(text, path.stem)
            current_hash = text_hash(text)
            existing = reusable.get(path.name)
            if existing and existing.get("text_hash") == current_hash:
                documents.append(existing)
                continue

            embedding_text = prepare_embedding_document(title=title, text=text)
            try:
                embedding = await embed_text(
                    client,
                    api_key=api_key,
                    model=model,
                    text=embedding_text,
                    output_dimensionality=output_dimensionality,
                    task_type=embedding_task_type(model, query=False),
                )
            except httpx.HTTPStatusError as exc:
                payload = make_index_payload(
                    index_dir=index_dir,
                    model=model,
                    output_dimensionality=output_dimensionality,
                    documents=documents,
                    complete=False,
                    last_error=f"HTTP {exc.response.status_code}",
                )
                write_embedding_index(payload, index_path)
                raise

            documents.append(
                {
                    "file": path.name,
                    "title": title,
                    "excerpt": excerpt_from_markdown(text, query_tokens(title)),
                    "text_hash": current_hash,
                    "embedding": embedding,
                }
            )
            payload = make_index_payload(
                index_dir=index_dir,
                model=model,
                output_dimensionality=output_dimensionality,
                documents=documents,
                complete=False,
            )
            write_embedding_index(payload, index_path)

            if max_documents > 0 and len(documents) >= max_documents:
                return payload
            if request_delay_seconds > 0:
                await asyncio.sleep(request_delay_seconds)

    payload = make_index_payload(
        index_dir=index_dir,
        model=model,
        output_dimensionality=output_dimensionality,
        documents=documents,
        complete=True,
    )
    write_embedding_index(payload, index_path)
    return payload


async def search_catalog_embeddings(
    query: str,
    *,
    index_path: Path = DEFAULT_EMBEDDING_INDEX_PATH,
    limit: int = 3,
    api_key: str = settings.gemini_api_key,
    model: str = settings.gemini_embedding_model,
    output_dimensionality: int = settings.gemini_embedding_output_dimensionality,
) -> list[dict]:
    data = load_embedding_index(index_path)
    if not api_key or limit <= 0:
        return []
    try:
        documents = await load_embedding_documents_from_database(
            model=model,
            output_dimensionality=output_dimensionality,
        )
    except (asyncpg.PostgresError, OSError):
        documents = []
    if not documents:
        if not data:
            return []
        if data.get("model") != model or data.get("output_dimensionality") != output_dimensionality:
            return []
        documents = data.get("documents", [])

    async with httpx.AsyncClient(timeout=15) as client:
        query_embedding = await embed_text(
            client,
            api_key=api_key,
            model=model,
            text=prepare_embedding_query(query),
            output_dimensionality=output_dimensionality,
            task_type=embedding_task_type(model, query=True),
        )

    ranked: list[tuple[float, str, dict]] = []
    for document in documents:
        embedding = document.get("embedding")
        if not isinstance(embedding, list):
            continue
        score = dense_cosine_similarity(query_embedding, [float(value) for value in embedding])
        if score <= 0:
            continue
        ranked.append(
            (
                score,
                str(document.get("title") or "").lower(),
                {
                    "title": document.get("title") or document.get("file") or "Catalog item",
                    "excerpt": document.get("excerpt") or "",
                    "file": document.get("file") or "",
                    "score": round(score, 4),
                    "source": "cocoindex_catalog_embedding",
                },
            )
        )

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item for _, _, item in ranked[:limit]]


async def search_catalog_index_semantic(query: str, *, limit: int = 3) -> list[dict]:
    try:
        hits = await search_catalog_embeddings(query, limit=limit)
    except (asyncpg.PostgresError, httpx.HTTPError, ValueError, OSError, TypeError):
        hits = []
    return hits or search_catalog_index(query, limit=limit)


async def main() -> None:
    try:
        payload = await build_catalog_embedding_index()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300].replace("\n", " ")
        raise SystemExit(
            "Không build được catalog embedding index: "
            f"Gemini trả HTTP {exc.response.status_code} cho model "
            f"{settings.gemini_embedding_model}. "
            "Hãy kiểm tra quyền của GEMINI_API_KEY hoặc đổi GEMINI_EMBEDDING_MODEL. "
            f"Chi tiết: {detail}"
        ) from exc
    print(
        "Built catalog embedding index: "
        f"{len(payload['documents'])} documents, "
        f"model={payload['model']}, "
        f"dim={payload['output_dimensionality']}, "
        f"path={DEFAULT_EMBEDDING_INDEX_PATH}"
    )
    synced_count = await sync_embedding_index_to_database(payload)
    print(f"Synced catalog embedding index to database: {synced_count} documents.")


if __name__ == "__main__":
    asyncio.run(main())
