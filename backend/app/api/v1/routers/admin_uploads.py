import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_user_permissions
from app.config import settings


router = APIRouter(prefix="/uploads")

ALLOWED_UPLOAD_FOLDERS = {"products", "brands", "categories", "content"}
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 200 * 1024 * 1024
UPLOAD_FOLDER_PERMISSIONS = {
    "products": "product:create",
    "brands": "brand:create",
    "categories": "category:create",
    "content": "content:create",
}


class PresignedUploadPayload(BaseModel):
    folder: str = "products"
    contentType: str
    size: int = Field(gt=0)


def require_upload_permission(folder: str, permissions: set[str]) -> None:
    required_permission = UPLOAD_FOLDER_PERMISSIONS.get(folder)
    if not required_permission or required_permission not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tải file cho khu vực này.")


@router.post("/presigned-url")
async def create_presigned_upload(
    payload: PresignedUploadPayload,
    request: Request,
    permissions: set[str] = Depends(get_user_permissions),
) -> dict:
    if payload.folder not in ALLOWED_UPLOAD_FOLDERS:
        raise HTTPException(status_code=400, detail="Invalid upload folder.")
    require_upload_permission(payload.folder, permissions)
    allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_VIDEO_TYPES}
    extension = allowed_types.get(payload.contentType)
    if not extension:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    if payload.folder == "content":
        if payload.contentType in ALLOWED_VIDEO_TYPES:
            max_size = min(MAX_VIDEO_UPLOAD_BYTES, 500 * 1024 * 1024)
        else:
            max_size = min(MAX_IMAGE_UPLOAD_BYTES, 5 * 1024 * 1024)
        if payload.contentType not in {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"}:
            raise HTTPException(status_code=400, detail="Content module only accepts JPG, PNG, WEBP, MP4, WEBM.")
    else:
        max_size = MAX_VIDEO_UPLOAD_BYTES if payload.contentType in ALLOWED_VIDEO_TYPES else MAX_IMAGE_UPLOAD_BYTES
    if payload.size > max_size:
        raise HTTPException(status_code=400, detail="File is too large.")
    file_key = f"{payload.folder}/{uuid4().hex}{extension}"
    if not all([settings.s3_bucket, settings.s3_access_key_id, settings.s3_secret_access_key, settings.s3_public_base_url]):
        base_url = str(request.base_url).rstrip("/")
        return {
            "uploadUrl": f"{base_url}/api/admin/uploads/local/{file_key}",
            "fileKey": file_key,
            "publicUrl": f"{base_url}/uploads/{file_key}",
            "expiresIn": settings.s3_presign_expires_seconds,
            "storage": "local",
        }

    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": file_key, "ContentType": payload.contentType},
        ExpiresIn=settings.s3_presign_expires_seconds,
        HttpMethod="PUT",
    )
    return {
        "uploadUrl": upload_url,
        "fileKey": file_key,
        "publicUrl": f"{settings.s3_public_base_url.rstrip('/')}/{file_key}",
        "expiresIn": settings.s3_presign_expires_seconds,
    }


@router.put("/local/{folder}/{filename}")
async def upload_local_file(
    folder: str,
    filename: str,
    request: Request,
    permissions: set[str] = Depends(get_user_permissions),
) -> dict:
    if folder not in ALLOWED_UPLOAD_FOLDERS:
        raise HTTPException(status_code=400, detail="Invalid upload folder.")
    require_upload_permission(folder, permissions)
    safe_filename = Path(filename).name
    if safe_filename != filename or not re.fullmatch(r"[a-f0-9]{32}\.(jpg|png|webp|gif|mp4|webm)", safe_filename):
        raise HTTPException(status_code=400, detail="Invalid upload filename.")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_VIDEO_TYPES}
    expected_extension = allowed_types.get(content_type)
    if not expected_extension or not safe_filename.endswith(expected_extension):
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    body = await request.body()
    max_size = MAX_VIDEO_UPLOAD_BYTES if content_type in ALLOWED_VIDEO_TYPES else MAX_IMAGE_UPLOAD_BYTES
    if folder == "content" and content_type not in {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"}:
        raise HTTPException(status_code=400, detail="Content module only accepts JPG, PNG, WEBP, MP4, WEBM.")
    if len(body) > max_size:
        raise HTTPException(status_code=400, detail="File is too large.")
    upload_dir = Path("uploads") / folder
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / safe_filename).write_bytes(body)
    return {"ok": True, "fileKey": f"{folder}/{safe_filename}"}
