from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import asyncpg

from app.application.ai.catalog_embedding_index import (
    CATALOG_EMBEDDING_TABLE,
    DEFAULT_EMBEDDING_INDEX_PATH,
    normalize_asyncpg_dsn,
)
from app.application.ai.catalog_index_search import DEFAULT_INDEX_DIR
from app.config import settings


def markdown_status(index_dir: Path = DEFAULT_INDEX_DIR) -> dict[str, Any]:
    files = sorted(index_dir.glob("*.md")) if index_dir.exists() else []
    return {
        "path": str(index_dir),
        "exists": index_dir.exists(),
        "documents": len(files),
    }


def embedding_json_status(index_path: Path = DEFAULT_EMBEDDING_INDEX_PATH) -> dict[str, Any]:
    if not index_path.exists():
        return {
            "path": str(index_path),
            "exists": False,
            "documents": 0,
            "complete": False,
        }

    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "path": str(index_path),
            "exists": True,
            "documents": 0,
            "complete": False,
            "error": str(exc),
        }

    documents = data.get("documents") if isinstance(data, dict) else []
    return {
        "path": str(index_path),
        "exists": True,
        "documents": len(documents) if isinstance(documents, list) else 0,
        "complete": bool(data.get("complete")) if isinstance(data, dict) else False,
        "model": data.get("model") if isinstance(data, dict) else None,
        "output_dimensionality": data.get("output_dimensionality") if isinstance(data, dict) else None,
    }


async def database_status(database_url: str = settings.database_url) -> dict[str, Any]:
    try:
        connection = await asyncpg.connect(normalize_asyncpg_dsn(database_url))
    except (OSError, asyncpg.PostgresError) as exc:
        return {
            "connected": False,
            "error": str(exc),
        }

    try:
        vector_available = await connection.fetchval(
            "SELECT COUNT(*) FROM pg_available_extensions WHERE name = 'vector'"
        )
        vector_installed = await connection.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        )
        table_exists = await connection.fetchval(
            "SELECT to_regclass($1) IS NOT NULL",
            f"public.{CATALOG_EMBEDDING_TABLE}",
        )
        if not table_exists:
            return {
                "connected": True,
                "table_exists": False,
                "documents": 0,
                "vector_available": bool(vector_available),
                "vector_installed": bool(vector_installed),
            }

        row = await connection.fetchrow(
            f"""
            SELECT
                COUNT(*)::int AS documents,
                MAX(updated_at) AS last_updated_at,
                MIN(output_dimensionality)::int AS min_dim,
                MAX(output_dimensionality)::int AS max_dim,
                COUNT(*) FILTER (WHERE complete_snapshot)::int AS complete_snapshot_documents,
                string_agg(DISTINCT model, ', ' ORDER BY model) AS models
            FROM {CATALOG_EMBEDDING_TABLE}
            """
        )
        return {
            "connected": True,
            "table_exists": True,
            "documents": row["documents"] if row else 0,
            "models": row["models"] if row else None,
            "min_dim": row["min_dim"] if row else None,
            "max_dim": row["max_dim"] if row else None,
            "complete_snapshot_documents": row["complete_snapshot_documents"] if row else 0,
            "last_updated_at": row["last_updated_at"].isoformat() if row and row["last_updated_at"] else None,
            "vector_available": bool(vector_available),
            "vector_installed": bool(vector_installed),
        }
    finally:
        await connection.close()


async def collect_status() -> dict[str, Any]:
    return {
        "markdown": markdown_status(),
        "embedding_json": embedding_json_status(),
        "database": await database_status(),
    }


def print_status(status: dict[str, Any]) -> None:
    markdown = status["markdown"]
    embedding_json = status["embedding_json"]
    database = status["database"]

    print("AI catalog index status")
    print(f"- Markdown: {markdown['documents']} files at {markdown['path']}")
    print(
        "- Embedding JSON: "
        f"{embedding_json['documents']} docs, "
        f"complete={embedding_json.get('complete')}, "
        f"model={embedding_json.get('model')}, "
        f"dim={embedding_json.get('output_dimensionality')}"
    )
    if not database.get("connected"):
        print(f"- Database: not connected ({database.get('error')})")
        return
    print(
        "- Database: "
        f"table_exists={database.get('table_exists')}, "
        f"docs={database.get('documents')}, "
        f"models={database.get('models')}, "
        f"dim={database.get('min_dim')}..{database.get('max_dim')}, "
        f"last_updated={database.get('last_updated_at')}"
    )
    print(
        "- pgvector: "
        f"available={database.get('vector_available')}, "
        f"installed={database.get('vector_installed')}"
    )


async def main() -> None:
    print_status(await collect_status())


if __name__ == "__main__":
    asyncio.run(main())
