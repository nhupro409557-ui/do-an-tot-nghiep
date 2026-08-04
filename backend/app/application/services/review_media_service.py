from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

ALLOWED_REVIEW_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_REVIEW_IMAGE_BYTES = 5 * 1024 * 1024
MAX_REVIEW_IMAGES_PER_UPLOAD = 5
MAX_STORED_REVIEW_IMAGES_PER_PRODUCT = 20


def delete_owned_review_images(*, urls: list[str], user_id: UUID, product_id: UUID) -> None:
    upload_dir = (Path("uploads") / "reviews" / str(user_id) / str(product_id)).resolve()
    expected_prefix = f"/uploads/reviews/{user_id}/{product_id}/"
    allowed_extensions = set(ALLOWED_REVIEW_IMAGE_TYPES.values())

    for raw_url in urls:
        url_path = unquote(urlparse(str(raw_url)).path).replace("\\", "/")
        if not url_path.startswith(expected_prefix):
            continue
        filename = Path(url_path).name
        if not filename or Path(filename).suffix.lower() not in allowed_extensions:
            continue
        target = (upload_dir / filename).resolve()
        if target.parent != upload_dir:
            continue
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass


def validate_review_image(content_type: str, data: bytes) -> str:
    normalized_type = content_type.lower().strip()
    extension = ALLOWED_REVIEW_IMAGE_TYPES.get(normalized_type)
    if not extension:
        raise HTTPException(status_code=400, detail="Ảnh đánh giá chỉ hỗ trợ JPG, PNG hoặc WEBP.")

    signatures_valid = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    if not data or not signatures_valid[normalized_type]:
        raise HTTPException(status_code=400, detail="Nội dung tệp ảnh không hợp lệ.")
    return extension


async def upload_review_images(
    *,
    product_id: UUID,
    user_id: UUID,
    files: list[UploadFile],
    base_url: str,
    session: AsyncSession,
) -> list[dict]:
    from app.application.services.public_content_service import get_review_eligibility

    if not files or len(files) > MAX_REVIEW_IMAGES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail="Mỗi lần chỉ được tải tối đa 5 ảnh đánh giá.")

    eligibility = await get_review_eligibility(product_id, user_id, session)
    if not eligibility.get("canReview") and not eligibility.get("canEdit"):
        raise HTTPException(status_code=403, detail=eligibility.get("message") or "Bạn chưa đủ điều kiện tải ảnh đánh giá.")

    upload_dir = Path("uploads") / "reviews" / str(user_id) / str(product_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_count = sum(1 for path in upload_dir.iterdir() if path.is_file())
    if stored_count + len(files) > MAX_STORED_REVIEW_IMAGES_PER_PRODUCT:
        raise HTTPException(status_code=400, detail="Bạn đã tải quá nhiều ảnh cho sản phẩm này.")

    created_paths: list[Path] = []
    results: list[dict] = []
    try:
        for upload in files:
            data = await upload.read(MAX_REVIEW_IMAGE_BYTES + 1)
            if len(data) > MAX_REVIEW_IMAGE_BYTES:
                raise HTTPException(status_code=400, detail=f"Ảnh {upload.filename or ''} vượt quá 5 MB.")
            extension = validate_review_image(upload.content_type or "", data)
            path = upload_dir / f"{uuid4().hex}{extension}"
            path.write_bytes(data)
            created_paths.append(path)
            public_url = f"{base_url.rstrip('/')}/{path.as_posix()}"
            results.append({"url": public_url})
    except Exception:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    finally:
        for upload in files:
            await upload.close()

    return results
