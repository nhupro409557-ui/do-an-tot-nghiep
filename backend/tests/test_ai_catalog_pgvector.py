from __future__ import annotations

import math

import pytest

from app.application.ai.catalog_embedding_index import (
    PGVECTOR_DIMENSION,
    embedding_task_type,
    pgvector_literal,
    should_use_pgvector,
)


def test_pgvector_literal_requires_configured_dimension() -> None:
    with pytest.raises(ValueError, match="768 chiều"):
        pgvector_literal([0.1, 0.2])


def test_pgvector_literal_rejects_non_finite_values() -> None:
    embedding = [0.0] * PGVECTOR_DIMENSION
    embedding[-1] = math.nan

    with pytest.raises(ValueError, match="không hữu hạn"):
        pgvector_literal(embedding)


def test_pgvector_rollout_is_stable_for_the_same_query() -> None:
    query = "điện thoại pin tốt dưới 15 triệu"

    first = should_use_pgvector(query, 35)
    second = should_use_pgvector(query, 35)

    assert first is second
    assert should_use_pgvector(query, 0) is False
    assert should_use_pgvector(query, 100) is True


def test_embedding_task_type_is_only_used_for_legacy_model() -> None:
    assert embedding_task_type("gemini-embedding-001", query=True) == "RETRIEVAL_QUERY"
    assert embedding_task_type("gemini-embedding-001", query=False) == "RETRIEVAL_DOCUMENT"
    assert embedding_task_type("gemini-embedding-2", query=True) is None
