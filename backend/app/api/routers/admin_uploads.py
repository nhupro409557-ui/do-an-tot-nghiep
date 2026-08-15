import math
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.dependencies import get_user_permissions
from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_session
from app.infrastructure.storage import StorageReadOnlyError, media_storage


router = APIRouter(prefix="/uploads")

ALLOWED_UPLOAD_FOLDERS = {"products", "brands", "categories", "content", "inventory", "used-products"}
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}
MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_VIDEO_DURATION_SECONDS = 300
MAX_DOCUMENT_UPLOAD_BYTES = 20 * 1024 * 1024
UPLOAD_FOLDER_PERMISSIONS = {
    "products": "product:create",
    "brands": "brand:create",
    "categories": "category:create",
    "content": "content:create",
    "inventory": "inventory:adjust",
    "used-products": "used_product:manage",
}


class PresignedUploadPayload(BaseModel):
    folder: str = "products"
    contentType: str
    size: int = Field(gt=0)
    durationSeconds: float | None = Field(default=None, ge=0)


def require_upload_permission(folder: str, permissions: set[str]) -> None:
    required_permission = UPLOAD_FOLDER_PERMISSIONS.get(folder)
    if not required_permission or required_permission not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tải file cho khu vực này.")


def validate_video_duration(content_type: str, duration_seconds: float | None) -> None:
    if content_type not in ALLOWED_VIDEO_TYPES:
        return
    if duration_seconds is None or not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="Không đọc được thời lượng video.")
    if duration_seconds > MAX_VIDEO_DURATION_SECONDS:
        raise HTTPException(status_code=400, detail="Video không được dài quá 5 phút.")


@router.post("/presigned-url")
async def create_presigned_upload(
    payload: PresignedUploadPayload,
    request: Request,
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if payload.folder not in ALLOWED_UPLOAD_FOLDERS:
        raise HTTPException(status_code=400, detail="Invalid upload folder.")
    require_upload_permission(payload.folder, permissions)
    allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_VIDEO_TYPES}
    if payload.folder == "inventory":
        allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_DOCUMENT_TYPES}
    extension = allowed_types.get(payload.contentType)
    if not extension:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    validate_video_duration(payload.contentType, payload.durationSeconds)
    if payload.folder == "content":
        if payload.contentType in ALLOWED_VIDEO_TYPES:
            max_size = min(MAX_VIDEO_UPLOAD_BYTES, 500 * 1024 * 1024)
        else:
            max_size = min(MAX_IMAGE_UPLOAD_BYTES, 5 * 1024 * 1024)
        if payload.contentType not in {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"}:
            raise HTTPException(status_code=400, detail="Content module only accepts JPG, PNG, WEBP, MP4, WEBM.")
    elif payload.folder == "inventory":
        max_size = MAX_DOCUMENT_UPLOAD_BYTES if payload.contentType in ALLOWED_DOCUMENT_TYPES else MAX_IMAGE_UPLOAD_BYTES
    else:
        max_size = MAX_VIDEO_UPLOAD_BYTES if payload.contentType in ALLOWED_VIDEO_TYPES else MAX_IMAGE_UPLOAD_BYTES
    if payload.size > max_size:
        raise HTTPException(status_code=400, detail="File is too large.")
    file_key = f"{payload.folder}/{uuid4().hex}{extension}"
    if not media_storage.supports_runtime_upload:
        raise HTTPException(
            status_code=409,
            detail="Kho bundled chỉ đọc; hãy thêm tệp vào Git rồi triển khai lại.",
        )

    base_url = str(request.base_url).rstrip("/")
    public_url = media_storage.public_url(file_key, base_url)
    await session.execute(
        text(
            """
            INSERT INTO media_assets (id, public_url, file_key, folder, content_type, size_bytes, created_at)
            VALUES (:id, :public_url, :file_key, :folder, :content_type, :size_bytes, NOW())
            """
        ),
        {
            "id": uuid4(),
            "public_url": public_url,
            "file_key": file_key,
            "folder": payload.folder,
            "content_type": payload.contentType,
            "size_bytes": payload.size,
        }
    )
    await session.commit()
    if media_storage.driver == "s3":
        return {
            "uploadUrl": media_storage.create_presigned_put_url(file_key, payload.contentType),
            "fileKey": file_key,
            "publicUrl": public_url,
            "expiresIn": settings.s3_presign_expires_seconds,
            "storage": "s3",
        }
    return {
        "uploadUrl": f"{base_url}/api/admin/uploads/local/{file_key}",
        "fileKey": file_key,
        "publicUrl": public_url,
        "expiresIn": settings.s3_presign_expires_seconds,
        "storage": "local",
    }


@router.put("/local/{folder}/{filename}")
async def upload_local_file(
    folder: str,
    filename: str,
    request: Request,
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if folder not in ALLOWED_UPLOAD_FOLDERS:
        raise HTTPException(status_code=400, detail="Invalid upload folder.")
    require_upload_permission(folder, permissions)
    if media_storage.driver != "local":
        raise HTTPException(
            status_code=409,
            detail="Endpoint upload local không khả dụng với kho lưu trữ hiện tại.",
        )
    safe_filename = Path(filename).name
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_VIDEO_TYPES}
    if folder == "inventory":
        allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_DOCUMENT_TYPES}
    expected_extension = allowed_types.get(content_type)
    allowed_extensions = "|".join(re.escape(ext.lstrip(".")) for ext in set(allowed_types.values()))
    if safe_filename != filename or not re.fullmatch(rf"[a-f0-9]{{32}}\.({allowed_extensions})", safe_filename):
        raise HTTPException(status_code=400, detail="Invalid upload filename.")
    if not expected_extension or not safe_filename.endswith(expected_extension):
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    if content_type in ALLOWED_VIDEO_TYPES:
        try:
            duration_seconds = float(request.headers.get("x-media-duration-seconds", ""))
        except ValueError:
            duration_seconds = None
        validate_video_duration(content_type, duration_seconds)
    body = await request.body()
    if folder == "inventory":
        max_size = MAX_DOCUMENT_UPLOAD_BYTES if content_type in ALLOWED_DOCUMENT_TYPES else MAX_IMAGE_UPLOAD_BYTES
    else:
        max_size = MAX_VIDEO_UPLOAD_BYTES if content_type in ALLOWED_VIDEO_TYPES else MAX_IMAGE_UPLOAD_BYTES
    if folder == "content" and content_type not in {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"}:
        raise HTTPException(status_code=400, detail="Content module only accepts JPG, PNG, WEBP, MP4, WEBM.")
    if len(body) > max_size:
        raise HTTPException(status_code=400, detail="File is too large.")
    base_url = str(request.base_url).rstrip("/")
    file_key = f"{folder}/{safe_filename}"
    try:
        media_storage.write_bytes(file_key, body, content_type)
    except StorageReadOnlyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    public_url = media_storage.public_url(file_key, base_url)
    exists = await session.scalar(
        text("SELECT EXISTS(SELECT 1 FROM media_assets WHERE public_url = :public_url)"),
        {"public_url": public_url}
    )
    if not exists:
        await session.execute(
            text(
                """
                INSERT INTO media_assets (id, public_url, file_key, folder, content_type, size_bytes, created_at)
                VALUES (:id, :public_url, :file_key, :folder, :content_type, :size_bytes, NOW())
                """
            ),
            {
                "id": uuid4(),
                "public_url": public_url,
                "file_key": file_key,
                "folder": folder,
                "content_type": content_type,
                "size_bytes": len(body),
            }
        )
        await session.commit()
    return {"ok": True, "fileKey": f"{folder}/{safe_filename}"}
