from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path


DEFAULT_INDEX_DIR = Path("var/cocoindex/catalog_markdown")
MAX_EXCERPT_CHARS = 700
TITLE_WEIGHT = 3.0

IGNORED_TOKENS = {
    "anh",
    "ban",
    "can",
    "cho",
    "co",
    "cua",
    "duoc",
    "gia",
    "hang",
    "khong",
    "la",
    "minh",
    "mua",
    "nao",
    "pham",
    "san",
    "toi",
    "tu",
    "van",
}

QUERY_EXPANSIONS = {
    "dien": ["smartphone", "phone"],
    "thoai": ["smartphone", "phone"],
    "smartphone": ["dien", "thoai", "phone"],
    "phone": ["dien", "thoai", "smartphone"],
    "laptop": ["may", "tinh", "notebook"],
    "may": ["laptop"],
    "tinh": ["laptop"],
    "pin": ["battery"],
    "battery": ["pin"],
    "camera": ["chup", "anh"],
    "anh": ["camera"],
    "ram": ["memory"],
    "ssd": ["storage"],
    "gaming": ["game"],
    "game": ["gaming"],
}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower()).replace("\u0111", "d")
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def query_tokens(query: str) -> list[str]:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(query))
        if len(token) > 2 and token not in IGNORED_TOKENS
    ]
    return list(dict.fromkeys(tokens))[:12]


def expanded_query_tokens(query: str) -> list[str]:
    tokens = query_tokens(query)
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(QUERY_EXPANSIONS.get(token, []))
    return list(dict.fromkeys(expanded))[:24]


def title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def excerpt_from_markdown(text: str, tokens: list[str]) -> str:
    fallback = ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("```"):
            continue
        if not fallback:
            fallback = stripped
        normalized = normalize_text(stripped)
        if any(token in normalized for token in tokens):
            return stripped[:MAX_EXCERPT_CHARS]
    return fallback[:MAX_EXCERPT_CHARS]


def token_stream(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(value))
        if len(token) > 2 and token not in IGNORED_TOKENS
    ]


def term_vector(text: str, *, title: str = "", filename: str = "") -> Counter[str]:
    vector: Counter[str] = Counter(token_stream(text))
    for token in token_stream(title):
        vector[token] += TITLE_WEIGHT
    for token in token_stream(filename):
        vector[token] += 1.5
    return vector


def query_vector(query: str) -> Counter[str]:
    vector: Counter[str] = Counter()
    for token in expanded_query_tokens(query):
        vector[token] += 1.0
    return vector


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    if dot <= 0:
        return 0.0
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def search_catalog_index(
    query: str,
    *,
    index_dir: Path = DEFAULT_INDEX_DIR,
    limit: int = 3,
) -> list[dict]:
    excerpt_tokens = query_tokens(query)
    vector = query_vector(query)
    if not vector or limit <= 0 or not index_dir.exists():
        return []

    ranked: list[tuple[float, str, dict]] = []
    for path in index_dir.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        title = title_from_markdown(text, path.stem)
        score = cosine_similarity(vector, term_vector(text, title=title, filename=path.name))
        if score <= 0:
            continue

        ranked.append(
            (
                score,
                title.lower(),
                {
                    "title": title,
                    "excerpt": excerpt_from_markdown(text, excerpt_tokens),
                    "file": path.name,
                    "score": round(score, 4),
                    "source": "cocoindex_catalog_vector",
                },
            )
        )

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item for _, _, item in ranked[:limit]]
