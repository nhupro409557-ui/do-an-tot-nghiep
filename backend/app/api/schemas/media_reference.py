from typing import Any

from app.infrastructure.storage import media_storage


def normalize_media_reference(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    file_key = media_storage.file_key_from_reference(stripped)
    if file_key:
        return file_key
    if media_storage.is_managed_reference_candidate(stripped):
        raise ValueError("Đường dẫn media không hợp lệ.")
    return stripped


def normalize_media_reference_list(values: Any) -> Any:
    if not isinstance(values, list):
        return values
    return [normalize_media_reference(value) for value in values]


def normalize_media_reference_items(values: Any) -> Any:
    if not isinstance(values, list):
        return values
    normalized: list[Any] = []
    for value in values:
        if isinstance(value, dict) and "url" in value:
            normalized.append({**value, "url": normalize_media_reference(value.get("url"))})
        else:
            normalized.append(normalize_media_reference(value))
    return normalized
