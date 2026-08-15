from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.storage import media_storage
from app.shared.exceptions import BusinessException


def managed_media_keys(references: list[str]) -> list[str]:
    keys: list[str] = []
    for reference in references:
        file_key = media_storage.file_key_from_reference(reference) if reference else None
        if file_key and file_key not in keys:
            keys.append(file_key)
    return keys


async def list_assets_by_file_keys(session: AsyncSession, file_keys: list[str]) -> list[dict]:
    if not file_keys:
        return []
    result = await session.execute(
        text("SELECT id, public_url, file_key, folder, associated_entity_id FROM media_assets WHERE file_key = ANY(:file_keys)"),
        {"file_keys": file_keys}
    )
    return [dict(r) for r in result.mappings().all()]

async def associate_assets_with_entity(session: AsyncSession, urls: list[str], entity_type: str, entity_id: UUID) -> None:
    file_keys = managed_media_keys(urls)
    if file_keys:
        await session.execute(
            text(
                """
                UPDATE media_assets
                SET associated_entity_type = :entity_type,
                    associated_entity_id = :entity_id
                WHERE file_key = ANY(:file_keys)
                """
            ),
            {"file_keys": file_keys, "entity_type": entity_type, "entity_id": entity_id}
        )
    await session.execute(
        text(
            """
            UPDATE media_assets
            SET associated_entity_type = NULL,
                associated_entity_id = NULL
            WHERE associated_entity_id = :entity_id
              AND associated_entity_type = :entity_type
              AND NOT (file_key = ANY(:file_keys))
            """
        ),
        {"file_keys": file_keys or [""], "entity_type": entity_type, "entity_id": entity_id}
    )

async def validate_media_assets(session: AsyncSession, *, entity_id: UUID, urls: list[str], allowed_folder: str, parent_id: UUID | None = None) -> None:
    uploaded_keys = managed_media_keys(urls)
    if not uploaded_keys:
        return

    assets = await list_assets_by_file_keys(session, uploaded_keys)
    assets_by_key = {asset["file_key"]: asset for asset in assets}

    for file_key in uploaded_keys:
        asset = assets_by_key.get(file_key)
        if not asset:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "MEDIA_ASSET_NOT_FOUND",
                    "message": f"Tệp media {file_key} chưa được upload hợp lệ.",
                }
            )
        if asset["folder"] != allowed_folder:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "MEDIA_SCOPE_INVALID",
                    "message": f"Media phải thuộc thư mục {allowed_folder}.",
                }
            )
        if asset["associated_entity_id"] and asset["associated_entity_id"] not in {entity_id, parent_id}:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "MEDIA_ASSET_ALREADY_ASSOCIATED",
                    "message": f"Tệp media {file_key} đã được sử dụng bởi thực thể khác.",
                }
            )

async def claim_media_assets(
    session: AsyncSession,
    *,
    urls: list[str],
    entity_type: str,
    entity_id: UUID,
    allowed_folder: str,
    parent_id: UUID | None = None,
) -> None:
    uploaded_keys = managed_media_keys(urls)
    if uploaded_keys:
        rows = (
            await session.execute(
                text(
                    """
                    UPDATE media_assets
                    SET associated_entity_type = :entity_type,
                        associated_entity_id = :entity_id
                    WHERE file_key = ANY(:file_keys)
                      AND folder = :allowed_folder
                      AND (
                          associated_entity_id IS NULL
                          OR associated_entity_id = :entity_id
                          OR (CAST(:parent_id AS UUID) IS NOT NULL AND associated_entity_id = CAST(:parent_id AS UUID))
                      )
                    RETURNING file_key
                    """
                ),
                {
                    "file_keys": uploaded_keys,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "parent_id": parent_id,
                    "allowed_folder": allowed_folder,
                },
            )
        ).scalars().all()

        if set(rows) != set(uploaded_keys):
            raise BusinessException(
                409,
                "MEDIA_ASSET_CLAIM_FAILED",
                "Media không tồn tại, sai phạm vi hoặc đã được thực thể khác sử dụng.",
            )

    # Disassociate old assets
    await session.execute(
        text(
            """
            UPDATE media_assets
            SET associated_entity_type = NULL,
                associated_entity_id = NULL
            WHERE associated_entity_id = :entity_id
              AND associated_entity_type = :entity_type
              AND NOT (file_key = ANY(:file_keys))
            """
        ),
        {"file_keys": uploaded_keys or [""], "entity_type": entity_type, "entity_id": entity_id},
    )


async def assert_all_product_media_claimed(
    session: AsyncSession,
    *,
    urls: list[str],
    entity_id: UUID,
    parent_id: UUID | None = None,
) -> None:
    external = [
        url
        for url in urls
        if url and not url.startswith("/images/") and not media_storage.file_key_from_reference(url)
    ]
    if external:
        raise BusinessException(400, "MEDIA_EXTERNAL_NOT_ALLOWED", "Media sản phẩm phải được upload qua hệ thống.")

    await claim_media_assets(
        session,
        urls=urls,
        entity_type="PRODUCT",
        entity_id=entity_id,
        allowed_folder="products",
        parent_id=parent_id,
    )
