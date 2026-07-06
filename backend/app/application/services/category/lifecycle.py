from .common import *

async def restore_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    affected_root_ids = await find_root_ids_for_categories(session, [category_id])
    if await category_repo.restore_category(session, category_id) == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục.")
    await category_repo.restore_hidden_children(session, category_id)
    await category_repo.restore_products_hidden_by_category(session, category_id)
    await audit_category_event(session, category_id, "CATEGORY_RESTORED", new_value={"status": "ACTIVE"}, actor_id=actor_id)
    await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_RESTORED")
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids)
    return {"ok": True}


async def deactivate_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    affected_root_ids = await find_root_ids_for_categories(session, [category_id])
    await ensure_categories_not_migrating(session, [category_id])
    delete_blockers = await category_repo.get_category_delete_blockers(session, category_id)
    if not delete_blockers.get("exists"):
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục.")
    if delete_blockers.get("can_hard_delete"):
        if await category_repo.hard_delete_category(session, category_id) == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy danh mục.")
        await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_HARD_DELETED")
        await session.commit()
        enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids, removed_root_ids=affected_root_ids)
        return {"ok": True, "action": "hard_deleted", "affectedProducts": 0}

    raise HTTPException(
        status_code=409,
        detail="Không thể xóa danh mục đang có dữ liệu liên quan. Hãy ẩn danh mục nếu cần ngừng hiển thị.",
    )


async def list_category_audit_logs(category_id: UUID, session: AsyncSession) -> list[dict]:
    return await category_repo.list_category_audit_logs(session, category_id)

async def list_category_migration_jobs(category_id: UUID, session: AsyncSession) -> list[dict]:
    await recover_stale_category_migrations(session)
    await session.commit()
    return await category_repo.list_category_migration_jobs(session, category_id)

async def category_operational_metrics(session: AsyncSession, redis: Redis) -> dict:
    recovered_jobs = await recover_stale_category_migrations(session)
    if recovered_jobs:
        await session.commit()
    try:
        hits = int(await redis.get("metrics:catalog_categories:cache_hit") or 0)
        misses = int(await redis.get("metrics:catalog_categories:cache_miss") or 0)
        samples = [int(item) for item in await redis.lrange("metrics:catalog_categories:latency_ms", 0, 499)]
    except Exception:
        hits = 0
        misses = 0
        samples = []
    total = hits + misses
    sorted_samples = sorted(samples)
    p99_index = max(0, min(len(sorted_samples) - 1, int(len(sorted_samples) * 0.99) - 1)) if sorted_samples else 0
    job_metrics = await category_repo.get_category_migration_job_metrics(
        session,
        stale_after_minutes=CATEGORY_MIGRATION_STALE_MINUTES,
    )
    business_metrics = await category_repo.get_category_business_metrics(session)
    return {
        "cacheHits": hits,
        "cacheMisses": misses,
        "cacheHitRatio": hits / total if total else 0,
        "latencyP99Ms": sorted_samples[p99_index] if sorted_samples else 0,
        "sampleSize": len(samples),
        "migrationFailedJobs": int(job_metrics["failed_jobs"] or 0),
        "migrationRunningJobs": int(job_metrics["running_jobs"] or 0),
        "migrationStaleJobs": int(job_metrics["stale_jobs"] or 0),
        "migrationWatchdogRecoveredJobs": len(recovered_jobs),
        "migrationAverageDurationSeconds": float(job_metrics["avg_duration_seconds"] or 0),
        "activeCategories": int(business_metrics["active_categories"] or 0),
        "emptyActiveCategories": int(business_metrics["empty_active_categories"] or 0),
        "averageProductsPerActiveCategory": float(business_metrics["avg_products_per_active_category"] or 0),
    }
