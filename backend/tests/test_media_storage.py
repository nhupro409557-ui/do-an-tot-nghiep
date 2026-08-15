from types import SimpleNamespace

import pytest

from app.infrastructure.storage.media_storage import MediaStorage, StorageConfigurationError


def make_settings(tmp_path, **overrides):
    values = {
        "media_storage_driver": "auto",
        "media_local_directory": str(tmp_path / "uploads"),
        "media_public_path": "/media",
        "s3_endpoint_url": "",
        "s3_bucket": "",
        "s3_access_key_id": "",
        "s3_secret_access_key": "",
        "s3_public_base_url": "",
        "s3_region": "ap-southeast-1",
        "s3_presign_expires_seconds": 900,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_auto_driver_keeps_local_storage_when_s3_is_not_configured(tmp_path):
    storage = MediaStorage(make_settings(tmp_path))

    assert storage.driver == "local"
    assert storage.public_url("content/banner.webp", "https://api.example.com") == (
        "https://api.example.com/media/content/banner.webp"
    )


def test_auto_driver_uses_s3_only_when_required_credentials_are_complete(tmp_path):
    storage = MediaStorage(
        make_settings(
            tmp_path,
            s3_bucket="media-bucket",
            s3_access_key_id="access-key",
            s3_secret_access_key="secret-key",
            s3_public_base_url="https://cdn.example.com",
        )
    )

    assert storage.driver == "s3"


def test_explicit_s3_driver_rejects_incomplete_configuration(tmp_path):
    with pytest.raises(StorageConfigurationError, match="S3"):
        MediaStorage(make_settings(tmp_path, media_storage_driver="s3"))


def test_bundled_storage_is_read_only_but_can_resolve_existing_files(tmp_path):
    storage = MediaStorage(make_settings(tmp_path, media_storage_driver="bundled"))

    assert storage.driver == "bundled"
    assert storage.supports_runtime_upload is False
    assert storage.resolve_local_path("content/banner.webp") == (
        tmp_path / "uploads" / "content" / "banner.webp"
    )


def test_local_storage_writes_counts_and_deletes_files(tmp_path):
    storage = MediaStorage(make_settings(tmp_path, media_storage_driver="local"))

    storage.write_bytes("reviews/user/product/photo.webp", b"image", "image/webp")

    assert storage.count("reviews/user/product") == 1
    assert storage.resolve_local_path("reviews/user/product/photo.webp").read_bytes() == b"image"
    storage.delete("reviews/user/product/photo.webp")
    assert storage.count("reviews/user/product") == 0


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://api.example.com/media/content/video.mp4", "content/video.mp4"),
        ("https://api.example.com/uploads/content/video.mp4", "content/video.mp4"),
        ("/media/products/photo.webp", "products/photo.webp"),
        ("/uploads/products/photo.webp", "products/photo.webp"),
    ],
)
def test_extracts_file_key_from_stable_and_legacy_urls(tmp_path, url, expected):
    storage = MediaStorage(make_settings(tmp_path))

    assert storage.file_key_from_url(url) == expected


@pytest.mark.parametrize("file_key", ["../secret.txt", "/absolute.jpg", "content/../../secret.txt"])
def test_rejects_unsafe_file_keys(tmp_path, file_key):
    storage = MediaStorage(make_settings(tmp_path))

    with pytest.raises(ValueError, match="không hợp lệ"):
        storage.resolve_local_path(file_key)
