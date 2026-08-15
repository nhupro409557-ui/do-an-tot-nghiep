from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.application.services.review_media_service import delete_owned_review_images, validate_review_image


@pytest.mark.parametrize(
    ("content_type", "data", "expected_extension"),
    [
        ("image/jpeg", b"\xff\xd8\xffreview-image", ".jpg"),
        ("image/png", b"\x89PNG\r\n\x1a\nreview-image", ".png"),
        ("image/webp", b"RIFF\x10\x00\x00\x00WEBPreview-image", ".webp"),
    ],
)
def test_accepts_supported_review_images(content_type, data, expected_extension):
    assert validate_review_image(content_type, data) == expected_extension


def test_rejects_image_with_mismatched_file_signature():
    with pytest.raises(HTTPException) as exc_info:
        validate_review_image("image/png", b"not-a-real-png")

    assert exc_info.value.status_code == 400
    assert "không hợp lệ" in str(exc_info.value.detail)


def test_rejects_unsupported_review_image_type():
    with pytest.raises(HTTPException) as exc_info:
        validate_review_image("image/gif", b"GIF89a")

    assert exc_info.value.status_code == 400
    assert "JPG, PNG hoặc WEBP" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_deletes_only_owned_review_images(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    user_id = uuid4()
    product_id = uuid4()
    upload_dir = tmp_path / "uploads" / "reviews" / str(user_id) / str(product_id)
    upload_dir.mkdir(parents=True)
    owned_image = upload_dir / "owned.jpg"
    owned_image.write_bytes(b"review-image")
    stable_image = upload_dir / "stable.webp"
    stable_image.write_bytes(b"review-image")
    unrelated_image = tmp_path / "outside.jpg"
    unrelated_image.write_bytes(b"outside-image")

    await delete_owned_review_images(
        urls=[
            f"http://localhost:8000/uploads/reviews/{user_id}/{product_id}/owned.jpg",
            f"http://localhost:8000/media/reviews/{user_id}/{product_id}/stable.webp",
            "http://localhost:8000/outside.jpg",
        ],
        user_id=user_id,
        product_id=product_id,
    )

    assert not owned_image.exists()
    assert not stable_image.exists()
    assert unrelated_image.exists()
