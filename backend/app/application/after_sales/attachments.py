import hashlib
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import after_sales_repo
from app.infrastructure.storage import StorageReadOnlyError, media_storage


ALLOWED_UPLOAD_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def attachment_url(storage_key: str) -> str:
    file_key = media_storage.normalize_storage_key(storage_key)
    return f"{media_storage.public_path}/{file_key}"


async def add_attachments(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    user_id: UUID,
    files: list[UploadFile],
) -> list[dict]:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request or request["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    if request["status"] not in {"SUBMITTED", "RECEIVED"}:
        raise HTTPException(status_code=409, detail="Không thể bổ sung tệp sau khi QC đã bắt đầu.")
    current = int(await session.scalar(
        text(
            """
            SELECT COUNT(*) FROM after_sales_attachments
            WHERE reference_type=:kind AND reference_id=:id AND status='ACTIVE'
            """
        ),
        {"kind": kind, "id": request_id},
    ) or 0)
    if current + len(files) > 5:
        raise HTTPException(status_code=400, detail="Mỗi yêu cầu chỉ được tối đa 5 tệp.")
    results = []
    created_keys: list[str] = []
    try:
        for upload in files:
            content_type = (upload.content_type or "").lower()
            if content_type not in ALLOWED_UPLOAD_TYPES:
                raise HTTPException(status_code=400, detail=f"Định dạng tệp {upload.filename} không được hỗ trợ.")
            data = await upload.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=400, detail=f"Tệp {upload.filename} vượt quá 20 MB.")
            digest = hashlib.sha256(data).hexdigest()
            attachment_id = uuid4()
            filename = f"{attachment_id}{ALLOWED_UPLOAD_TYPES[content_type]}"
            storage_key = f"after-sales/{kind.lower()}/{request_id}/{filename}"
            media_storage.write_bytes(storage_key, data, content_type)
            created_keys.append(storage_key)
            await session.execute(
                text(
                    """
                    INSERT INTO after_sales_attachments
                        (id, reference_type, reference_id, uploaded_by, original_name,
                         storage_key, content_type, size_bytes, checksum_sha256)
                    VALUES (:id, :kind, :reference_id, :user_id, :name,
                            :key, :content_type, :size, :checksum)
                    """
                ),
                {
                    "id": attachment_id,
                    "kind": kind,
                    "reference_id": request_id,
                    "user_id": user_id,
                    "name": upload.filename or filename,
                    "key": storage_key,
                    "content_type": content_type,
                    "size": len(data),
                    "checksum": digest,
                },
            )
            results.append({"id": str(attachment_id), "url": attachment_url(storage_key)})
        await session.commit()
        return results
    except StorageReadOnlyError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        await session.rollback()
        for storage_key in created_keys:
            try:
                media_storage.delete(storage_key)
            except (OSError, StorageReadOnlyError):
                pass
        raise
    finally:
        for upload in files:
            await upload.close()


async def schedule_attachment_cleanup(session: AsyncSession, kind: str, request_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE after_sales_attachments
            SET status='PENDING_DELETE', delete_after=NOW() + INTERVAL '30 days'
            WHERE reference_type=:kind AND reference_id=:id AND status='ACTIVE'
            """
        ),
        {"kind": kind, "id": request_id},
    )
