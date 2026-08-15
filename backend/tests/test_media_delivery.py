from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.api.routers import media as media_router
from app.infrastructure.storage.media_storage import MediaStorage


def make_settings(tmp_path, driver="local"):
    return SimpleNamespace(
        media_storage_driver=driver,
        media_local_directory=str(tmp_path / "uploads"),
        media_public_path="/media",
        s3_endpoint_url="https://storage.example.com" if driver == "s3" else "",
        s3_bucket="media" if driver == "s3" else "",
        s3_access_key_id="key" if driver == "s3" else "",
        s3_secret_access_key="secret" if driver == "s3" else "",
        s3_public_base_url="https://cdn.example.com" if driver == "s3" else "",
        s3_region="auto",
        s3_presign_expires_seconds=900,
    )


@pytest.mark.asyncio
async def test_delivers_local_media_from_configured_directory(tmp_path, monkeypatch):
    storage = MediaStorage(make_settings(tmp_path))
    storage.write_bytes("content/banner.webp", b"image", "image/webp")
    monkeypatch.setattr(media_router, "media_storage", storage)

    response = await media_router.deliver_media("content/banner.webp")

    assert isinstance(response, FileResponse)
    assert response.path == str(tmp_path / "uploads" / "content" / "banner.webp")


@pytest.mark.asyncio
async def test_redirects_s3_media_to_current_public_base_url(tmp_path, monkeypatch):
    storage = MediaStorage(make_settings(tmp_path, driver="s3"))
    monkeypatch.setattr(media_router, "media_storage", storage)

    response = await media_router.deliver_media("content/video.mp4")

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "https://cdn.example.com/content/video.mp4"


@pytest.mark.asyncio
async def test_returns_not_found_for_missing_local_media(tmp_path, monkeypatch):
    storage = MediaStorage(make_settings(tmp_path))
    monkeypatch.setattr(media_router, "media_storage", storage)

    with pytest.raises(HTTPException) as exc_info:
        await media_router.deliver_media("content/missing.webp")

    assert exc_info.value.status_code == 404
