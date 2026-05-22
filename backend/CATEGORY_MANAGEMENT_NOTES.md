# Category Management Notes

This file records the non-obvious decisions added while hardening category management.

## Files to review first

- `backend/app/api/v1/routers/admin.py`
- `backend/app/api/v1/routers/catalog.py`

## What was added

1. Migration branch lock

- Helper: `ensure_categories_not_migrating(...)`
- Purpose: blocks write actions when a category branch has a running migration job.
- Coverage:
  - category create/update/delete/reorder/bulk update
  - product create/update
  - product status changes
  - product delete/archive

2. Workflow lock marker

- Category `workflow_status` is temporarily set to `MIGRATING` when parent changes create a migration job.
- Reset happens in `process_category_migration_job(...)` on both success and failure.

3. Redirect chain flattening

- Helper: `record_category_redirect(...)`
- Purpose: when slug changes from `C` to `D`, older redirects pointing to `C` are updated to point directly to `D`.
- This avoids long SEO redirect chains.

4. Product behavior on category soft delete

- Helper: `deactivate_products_in_category_branch(...)`
- Rule: products inside the deleted category branch are automatically moved to `INACTIVE`, and variants are disabled.
- Reason: prevents "active product / hidden taxonomy" mismatch on storefront.

5. Partial category cache refresh

- Cache is now split by root branch.
- Keys:
  - `catalog:categories:roots:active`
  - `catalog:categories:roots:stale`
  - `catalog:categories:branch:{rootId}:active`
  - `catalog:categories:branch:{rootId}:stale`
- Public catalog reads branch caches first, then falls back to old full-tree fallback.

6. Migration watchdog / stale job recovery

- Constant: `CATEGORY_MIGRATION_STALE_MINUTES = 30`
- Helper: `recover_stale_category_migrations(...)`
- Purpose: detect migration jobs stuck in `PENDING/RUNNING/IN_PROGRESS` beyond the timeout window.
- Behavior:
  - mark stale jobs as `FAILED`
  - release category `workflow_status` from `MIGRATING`
  - expose stale/recovered counts through category ops metrics
- This is an in-process self-healing fallback, not a full DLQ implementation.

7. Restore UX safety notice

- Frontend restore action now warns admins that category restore does not automatically reactivate products.
- File: `frontend/src/pages/AdminDashboard.tsx`

8. Frontend concurrency message

- Frontend now translates version mismatch / `409 Conflict` style responses into a clearer admin message.
- File: `frontend/src/pages/AdminDashboard.tsx`

9. Category-only refresh path in Admin Dashboard

- Frontend now has a dedicated `loadCategoryWorkspace(...)` flow instead of forcing a full dashboard reload after every category mutation.
- Coverage:
  - create/update/reorder/restore category
  - category edit side data refresh
- Reason:
  - reduces the perceived delay after category edits
  - avoids re-fetching unrelated tabs such as vouchers, reviews, permissions on every category save

10. Category operational telemetry surfaced in UI

- Frontend now consumes:
  - `GET /admin/categories/ops/metrics`
  - `GET /admin/categories/{id}/audit-logs`
  - `GET /admin/categories/{id}/migration-jobs`
- Purpose:
  - show cache hit ratio / P99 latency / running migration jobs
  - expose audit history and migration progress for the category being edited
- File: `frontend/src/pages/AdminDashboard.tsx`

11. Migration job auto-polling while editing category

- When the selected category has `PENDING/RUNNING/IN_PROGRESS` migration jobs, the category workspace now auto-refreshes on an interval.
- Purpose:
  - helps admins observe long-running parent-change migrations without manually reloading the whole dashboard
- File: `frontend/src/pages/AdminDashboard.tsx`

## Maintenance guidance

1. If you add a new product write endpoint, also call `ensure_categories_not_migrating(...)`.
2. If you add a new category mutation endpoint, also refresh affected root caches via `enqueue_category_cache_refresh(...)`.
3. If category tree depth or inheritance rules change, review:
   - `ensure_no_category_cycle(...)`
   - `ensure_category_depth(...)`
   - `ensure_spec_inheritance_safe(...)`
4. If storefront starts needing full nested trees beyond one child level, update both:
   - `fetch_visible_category_branch(...)`
   - `read_category_tree_from_branch_cache(...)`
5. If the app later gets a scheduler/worker platform, move `recover_stale_category_migrations(...)` to a proper cron or DLQ workflow instead of relying on opportunistic request-time cleanup.
6. If category admin grows further, keep new diagnostics under the category-only refresh path instead of reusing the full `loadData()` dashboard fetch.

## Business assumptions introduced in this pass

1. During category migration, branch writes are blocked instead of allowed with eventual reconciliation.
2. Soft deleting a category branch unlists products instead of moving them to an "uncategorized" bucket.
3. Restoring a category does not auto-reactivate products that were inactivated by the delete flow.
4. Stale migration jobs older than 30 minutes are treated as failed and their category workflow lock is released automatically.
5. Category operators benefit from seeing operational telemetry in the same screen as category edits, not only through backend logs.
