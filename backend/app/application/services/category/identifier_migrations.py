from .common import *

async def preview_identifier_policy_migration(
    category_id: UUID,
    identifier_type: str,
    session: AsyncSession,
) -> dict:
    if identifier_type not in {"IMEI", "SERIAL"}:
        raise HTTPException(status_code=422, detail="Loại mã định danh không hợp lệ.")
    if not await category_repo.get_category_for_update(session, category_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục.")
    lines = await category_repo.preview_identifier_policy_change(
        session,
        category_id=category_id,
        identifier_type=identifier_type,
    )
    return identifier_preview_summary(identifier_type, lines)


async def create_identifier_policy_migration(
    category_id: UUID,
    payload: CategoryIdentifierMigrationCreatePayload,
    session: AsyncSession,
    actor_id: UUID,
) -> dict:
    try:
        if not await category_repo.get_category_for_update(session, category_id):
            raise HTTPException(status_code=404, detail="Không tìm thấy danh mục.")
        active = await category_repo.find_active_identifier_policy_migration(
            session,
            category_id=category_id,
            identifier_type=payload.identifierType,
        )
        if active:
            raise HTTPException(status_code=409, detail="Danh mục đã có tác vụ bổ sung mã đang xử lý.")
        target_inventory_policy = normalize_identifier_inventory_policy(payload.targetInventoryPolicy)
        target_enabled = (
            bool(target_inventory_policy.get("trackImei"))
            if payload.identifierType == "IMEI"
            else bool(target_inventory_policy.get("trackSerialNumber"))
        )
        if not target_enabled:
            raise HTTPException(status_code=422, detail="Chính sách đích phải bật loại mã định danh đã chọn.")
        lines = await category_repo.preview_identifier_policy_change(
            session,
            category_id=category_id,
            identifier_type=payload.identifierType,
        )
        summary = identifier_preview_summary(payload.identifierType, lines)
        if summary["requiredIdentifiers"] <= 0:
            raise HTTPException(status_code=409, detail="Tồn kho hiện tại không cần bổ sung mã định danh.")
        migration_id = uuid4()
        await category_repo.create_identifier_policy_migration(
            session,
            migration_id=migration_id,
            category_id=category_id,
            identifier_type=payload.identifierType,
            target_inventory_policy=target_inventory_policy,
            lines=summary["lines"],
            actor_id=actor_id,
        )
        await audit_category_event(
            session,
            category_id,
            "IDENTIFIER_POLICY_MIGRATION_CREATED",
            new_value={
                "migrationId": str(migration_id),
                "identifierType": payload.identifierType,
                "requiredIdentifiers": summary["requiredIdentifiers"],
            },
            actor_id=actor_id,
        )
        await session.commit()
        return {"id": str(migration_id), **summary}
    except Exception as exc:
        await session.rollback()
        raise exc


async def list_identifier_policy_migrations(category_id: UUID, session: AsyncSession) -> list[dict]:
    migrations = await category_repo.list_identifier_policy_migrations(session, category_id)
    for migration in migrations:
        migration["lines"] = await category_repo.list_identifier_policy_migration_lines(session, UUID(migration["id"]))
    return migrations


async def scan_identifier_policy_migration(
    migration_id: UUID,
    payload: CategoryIdentifierMigrationScanPayload,
    session: AsyncSession,
    actor_id: UUID,
) -> dict:
    try:
        migration = await category_repo.get_identifier_policy_migration(session, migration_id, for_update=True)
        if not migration:
            raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ bổ sung mã.")
        if migration["status"] not in {"PENDING", "IN_PROGRESS"}:
            raise HTTPException(status_code=409, detail="Tác vụ này không còn nhận thêm mã.")
        line = await category_repo.get_identifier_policy_migration_line(session, migration_id, payload.lineId)
        if not line:
            raise HTTPException(status_code=404, detail="Không tìm thấy dòng sản phẩm trong tác vụ.")
        values = list(dict.fromkeys(str(value).strip().upper() for value in payload.identifiers if str(value).strip()))
        pattern = IMEI_PATTERN if migration["identifierType"] == "IMEI" else SERIAL_PATTERN
        invalid = [value for value in values if not pattern.match(value)]
        if invalid:
            label = "IMEI phải có đúng 15 chữ số" if migration["identifierType"] == "IMEI" else "Serial number không đúng định dạng"
            raise HTTPException(status_code=400, detail=f"{label}: {', '.join(invalid[:5])}")
        remaining = int(line["requiredIdentifierCount"]) - int(line["stagedIdentifierCount"])
        if len(values) > remaining:
            raise HTTPException(status_code=400, detail=f"Dòng này chỉ còn thiếu {remaining} mã.")
        existing_values = await category_repo.list_existing_identifier_values(session, migration["identifierType"], values)
        if existing_values:
            raise HTTPException(status_code=409, detail=f"Mã đã tồn tại trong hệ thống: {', '.join(sorted(existing_values)[:5])}")
        staged_values = await category_repo.list_staged_identifier_values(session, values)
        if staged_values:
            raise HTTPException(status_code=409, detail=f"Mã đang nằm trong tác vụ khác: {', '.join(sorted(staged_values)[:5])}")
        inserted = await category_repo.stage_identifier_policy_values(
            session,
            migration_id=migration_id,
            line_id=payload.lineId,
            values=values,
            actor_id=actor_id,
        )
        await session.commit()
        return {"inserted": inserted, "remaining": remaining - inserted}
    except Exception as exc:
        await session.rollback()
        raise exc


async def complete_identifier_policy_migration(
    migration_id: UUID,
    session: AsyncSession,
    actor_id: UUID,
) -> dict:
    try:
        migration = await category_repo.get_identifier_policy_migration(session, migration_id, for_update=True)
        if not migration:
            raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ bổ sung mã.")
        if migration["status"] not in {"PENDING", "IN_PROGRESS"}:
            raise HTTPException(status_code=409, detail="Tác vụ này không thể hoàn tất.")
        lines = await category_repo.list_identifier_policy_migration_lines(session, migration_id)
        if any(int(line["stagedIdentifierCount"]) != int(line["requiredIdentifierCount"]) for line in lines):
            raise HTTPException(status_code=409, detail="Chưa bổ sung đủ mã cho tất cả sản phẩm.")
        current_lines = await category_repo.preview_identifier_policy_change(
            session,
            category_id=UUID(migration["categoryId"]),
            identifier_type=migration["identifierType"],
        )
        current_required = {
            (line["productId"], line["variantId"]): int(line["requiredIdentifierCount"])
            for line in current_lines
            if int(line["requiredIdentifierCount"]) > 0
        }
        stored_required = {
            (line["productId"], line["variantId"]): int(line["requiredIdentifierCount"])
            for line in lines
        }
        if current_required != stored_required:
            raise HTTPException(
                status_code=409,
                detail="Tồn kho đã thay đổi trong lúc bổ sung mã. Hãy hủy tác vụ và tạo lại để đối soát chính xác.",
            )
        await category_repo.activate_identifier_policy_migration_values(
            session,
            migration_id=migration_id,
            identifier_type=migration["identifierType"],
        )
        await category_repo.complete_identifier_policy_migration(
            session,
            migration_id=migration_id,
            category_id=UUID(migration["categoryId"]),
            target_inventory_policy=migration["targetInventoryPolicy"],
            identifier_type=migration["identifierType"],
            actor_id=actor_id,
        )
        await audit_category_event(
            session,
            UUID(migration["categoryId"]),
            "IDENTIFIER_POLICY_MIGRATION_COMPLETED",
            new_value={"migrationId": str(migration_id), "identifierType": migration["identifierType"]},
            actor_id=actor_id,
        )
        await session.commit()
        return {"ok": True}
    except Exception as exc:
        await session.rollback()
        raise exc


async def cancel_identifier_policy_migration(
    migration_id: UUID,
    payload: CategoryIdentifierMigrationCancelPayload,
    session: AsyncSession,
    actor_id: UUID,
) -> dict:
    try:
        migration = await category_repo.get_identifier_policy_migration(session, migration_id, for_update=True)
        if not migration:
            raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ bổ sung mã.")
        if migration["status"] not in {"PENDING", "IN_PROGRESS"}:
            raise HTTPException(status_code=409, detail="Tác vụ này không thể hủy.")
        await category_repo.cancel_identifier_policy_migration(
            session,
            migration_id=migration_id,
            actor_id=actor_id,
            reason=payload.reason,
        )
        await audit_category_event(
            session,
            UUID(migration["categoryId"]),
            "IDENTIFIER_POLICY_MIGRATION_CANCELLED",
            new_value={"migrationId": str(migration_id), "reason": payload.reason},
            actor_id=actor_id,
        )
        await session.commit()
        return {"ok": True}
    except Exception as exc:
        await session.rollback()
        raise exc
