from .common import *

async def get_product_inventory(session: AsyncSession, product_id: UUID) -> dict:
    product_data = await inventory_repo.get_product_inventory_summary(session, product_id)
    if not product_data:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    variants = await inventory_repo.list_product_inventory_variants(session, product_id)
    logs = await inventory_repo.list_inventory_adjustment_logs(session, product_id)
    sales_config = product_data.get("salesConfig") if isinstance(product_data.get("salesConfig"), dict) else {}
    minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
    product_data.update(
        {
            "minimumStock": minimum_stock,
            "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
            "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
            "stockAlert": "LOW" if int(product_data.get("stockQuantity") or 0) <= minimum_stock else "OK",
        }
    )
    return {**product_data, "variants": variants, "logs": logs}

async def update_product_inventory_settings(
    session: AsyncSession,
    product_id: UUID,
    payload: InventorySettingsPayload,
) -> dict:
    row = await inventory_repo.get_product_sales_config_for_update(session, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    sales_config = row.get("sales_config") if isinstance(row.get("sales_config"), dict) else {}
    merged = persisted_sales_config(
        {
            **sales_config,
            "minimumStock": payload.minimumStock,
            "blockSaleWhenOutOfStock": payload.blockSaleWhenOutOfStock,
            "cycleCountDays": payload.cycleCountDays or sales_config.get("cycleCountDays") or 30,
        }
    )
    await inventory_repo.update_product_sales_config(session, product_id=product_id, sales_config=merged)
    await session.commit()
    return {"ok": True, **merged}

async def export_inventory_snapshot(session: AsyncSession, search: str = "") -> Response:
    rows = await inventory_repo.list_inventory_snapshot_rows(session, search)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "productId",
            "productName",
            "productSku",
            "variantId",
            "variantSku",
            "variantConfiguration",
            "variantColor",
            "physicalStock",
            "reservedStock",
            "availableStock",
            "displayPrice",
            "averageUnitCost",
            "locations",
            "minimumStock",
            "stockAlert",
            "stockState",
            "tracksImei",
            "tracksSerialNumber",
            "primaryImei",
            "supplementalImei",
            "inStockImei",
            "reservedImei",
            "soldImei",
            "warrantyImei",
            "scrapImei",
            "inStockSerialNumber",
            "reservedSerialNumber",
            "soldSerialNumber",
            "warrantySerialNumber",
            "scrapSerialNumber",
            "productStatus",
            "blockSaleWhenOutOfStock",
        ],
    )
    writer.writeheader()
    for row in rows:
        shaped = _shape_inventory_level_row(row)
        writer.writerow(
            {
                "productId": shaped["productId"],
                "productName": shaped["productName"],
                "productSku": shaped["productSku"],
                "variantId": shaped["variantId"] or "",
                "variantSku": shaped["variantSku"] or "",
                "variantConfiguration": shaped["variantConfiguration"] or "",
                "variantColor": shaped["variantColor"] or "",
                "physicalStock": shaped["physicalStock"],
                "reservedStock": shaped["reservedStock"],
                "availableStock": shaped["availableStock"],
                "displayPrice": shaped["displayPrice"],
                "averageUnitCost": shaped["averageUnitCost"],
                "locations": "; ".join(
                    f"{item.get('code') or '-'} - {item.get('name') or '-'} ({int(item.get('onHandQuantity') or 0)})"
                    for item in shaped.get("locations") or []
                ),
                "minimumStock": shaped["minimumStock"],
                "stockAlert": "Cần nhập thêm" if shaped["stockAlert"] == "LOW" else "Ổn định",
                "stockState": shaped["stockState"],
                "tracksImei": "Có" if shaped["tracksImei"] else "Không",
                "tracksSerialNumber": "Có" if shaped["tracksSerialNumber"] else "Không",
                "primaryImei": shaped["primaryImei"] or "",
                "supplementalImei": shaped["supplementalImei"],
                "inStockImei": shaped["imeiSummary"]["inStock"],
                "reservedImei": shaped["imeiSummary"]["reserved"],
                "soldImei": shaped["imeiSummary"]["sold"],
                "warrantyImei": shaped["imeiSummary"]["warranty"],
                "scrapImei": shaped["imeiSummary"]["scrap"],
                "inStockSerialNumber": shaped["serialNumberSummary"]["inStock"],
                "reservedSerialNumber": shaped["serialNumberSummary"]["reserved"],
                "soldSerialNumber": shaped["serialNumberSummary"]["sold"],
                "warrantySerialNumber": shaped["serialNumberSummary"]["warranty"],
                "scrapSerialNumber": shaped["serialNumberSummary"]["scrap"],
                "productStatus": shaped["productStatus"],
                "blockSaleWhenOutOfStock": "Có" if shaped["blockSaleWhenOutOfStock"] else "Không",
            }
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inventory-export.csv"'},
    )


async def list_inventory_levels(
    session: AsyncSession,
    search: str = "",
    stock_filter: str = "",
    location: str = "",
    category_id: str = "",
    brand_id: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    rows = await inventory_repo.list_inventory_level_rows(session, search.strip())
    category_id = category_id.strip()
    brand_id = brand_id.strip()
    if category_id:
        rows = [
            row for row in rows
            if str(row.get("categoryId") or "") == category_id
            or str(row.get("subcategoryId") or "") == category_id
        ]
    if brand_id:
        rows = [row for row in rows if str(row.get("brandId") or "") == brand_id]
    shaped_rows = [_shape_inventory_level_row(row) for row in rows]
    stock_filter = stock_filter.strip().upper()
    location = location.strip().lower()
    if stock_filter == "LOW":
        shaped_rows = [row for row in shaped_rows if row["stockAlert"] == "LOW"]
    elif stock_filter == "IN_STOCK":
        shaped_rows = [row for row in shaped_rows if row["physicalStock"] > 0]
    elif stock_filter == "RESERVED":
        shaped_rows = [row for row in shaped_rows if row["reservedStock"] > 0]
    if location:
        shaped_rows = [
            row for row in shaped_rows
            if any(
                location in str(item.get("code") or "").lower()
                or location in str(item.get("name") or "").lower()
                for item in row.get("locations") or []
            )
        ]
    total = len(shaped_rows)
    start = (page - 1) * page_size
    return {
        "items": shaped_rows[start:start + page_size],
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


async def list_inventory_locations(
    session: AsyncSession,
    search: str = "",
    include_inactive: bool = True,
    zone: str = "",
    purpose: str = "",
    status: str = "",
    aisle: str = "",
    shelf: str = "",
    bin: str = "",
) -> list[dict]:
    normalized_purpose = str(purpose or "").strip().upper()
    normalized_status = str(status or "").strip().upper()
    normalized_aisle = str(aisle or "").strip().upper()
    normalized_shelf = str(shelf or "").strip()
    normalized_bin = str(bin or "").strip()
    if normalized_purpose and normalized_purpose not in {"STORAGE", "WARRANTY", "QC", "DAMAGED", "RETURN", "USED", "VIRTUAL"}:
        raise HTTPException(status_code=400, detail="Loại kệ hàng không hợp lệ.")
    if normalized_status and normalized_status not in {"ACTIVE", "INACTIVE"}:
        raise HTTPException(status_code=400, detail="Trạng thái kệ hàng không hợp lệ.")
    if normalized_aisle and not re.fullmatch(r"[A-Z]{1,4}", normalized_aisle):
        raise HTTPException(status_code=400, detail="Khu/dãy kệ không hợp lệ.")
    if normalized_shelf and not re.fullmatch(r"\d{1,2}", normalized_shelf):
        raise HTTPException(status_code=400, detail="Số kệ không hợp lệ.")
    if normalized_bin and not re.fullmatch(r"\d{1,2}", normalized_bin):
        raise HTTPException(status_code=400, detail="Số ô không hợp lệ.")
    return await inventory_repo.list_inventory_locations(
        session,
        search,
        include_inactive,
        zone.strip(),
        normalized_purpose,
        normalized_status,
        normalized_aisle,
        normalized_shelf.zfill(2) if normalized_shelf else "",
        normalized_bin.zfill(2) if normalized_bin else "",
    )


async def create_inventory_location(session: AsyncSession, payload: InventoryLocationPayload) -> dict:
    code = _normalize_location_code(payload.code)
    name = payload.name.strip()
    purpose = str(payload.purpose or "STORAGE").strip().upper()
    sort_order = int(payload.sortOrder or 0) or _location_sort_order_from_code(code)
    if not code:
        raise HTTPException(status_code=400, detail="Mã kệ hàng không hợp lệ.")
    existing = await inventory_repo.get_inventory_location_by_code(session, code)
    if existing:
        raise HTTPException(status_code=409, detail="Mã kệ hàng đã tồn tại.")
    location = await inventory_repo.create_inventory_location(
        session,
        location_id=uuid4(),
        code=code,
        name=name,
        zone=(payload.zone or "").strip() or None,
        purpose=purpose,
        sort_order=sort_order,
        allow_mixed_sku=bool(payload.allowMixedSku),
        length_cm=payload.lengthCm,
        width_cm=payload.widthCm,
        height_cm=payload.heightCm,
        usable_ratio=payload.usableRatio,
        description=(payload.description or "").strip() or None,
    )
    await session.commit()
    return location


async def update_inventory_location(session: AsyncSession, location_id: UUID, payload: InventoryLocationPayload) -> dict:
    current = await inventory_repo.get_inventory_location_by_id(session, location_id)
    if not current:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    code = _normalize_location_code(payload.code)
    purpose = str(payload.purpose or "STORAGE").strip().upper()
    sort_order = int(payload.sortOrder or 0) or _location_sort_order_from_code(code)
    if not code:
        raise HTTPException(status_code=400, detail="Mã kệ hàng không hợp lệ.")
    existing = await inventory_repo.get_inventory_location_by_code(session, code)
    if existing and str(existing["id"]) != str(location_id):
        raise HTTPException(status_code=409, detail="Mã kệ hàng đã tồn tại.")

    has_stock = await inventory_repo.inventory_location_has_stock(session, location_id)
    if str(current.get("purpose")).upper() != purpose and has_stock:
        raise HTTPException(
            status_code=400,
            detail="Kệ còn tồn kho, không thể thay đổi mục đích kệ (vui lòng dọn kệ trước).",
        )
    if has_stock:
        usage = await inventory_repo.get_inventory_location_capacity_usage(session, location_id)
        if usage:
            used_vol = float(usage.get("usedVolumeCm3") or 0)
            if used_vol > 0:
                new_usable_vol = float(payload.lengthCm or 0) * float(payload.widthCm or 0) * float(payload.heightCm or 0) * float(payload.usableRatio or 0)
                if new_usable_vol < used_vol:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Dung lượng mới ({new_usable_vol:,.0f} cm³) nhỏ hơn dung lượng đang sử dụng ({used_vol:,.0f} cm³).",
                    )

    location = await inventory_repo.update_inventory_location(
        session,
        location_id=location_id,
        code=code,
        name=payload.name.strip(),
        zone=(payload.zone or "").strip() or None,
        purpose=purpose,
        sort_order=sort_order,
        allow_mixed_sku=bool(payload.allowMixedSku),
        length_cm=payload.lengthCm,
        width_cm=payload.widthCm,
        height_cm=payload.heightCm,
        usable_ratio=payload.usableRatio,
        description=(payload.description or "").strip() or None,
    )
    if not location:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    await session.commit()
    return location


async def update_inventory_location_status(session: AsyncSession, location_id: UUID, payload: InventoryLocationStatusPayload) -> dict:
    current = await inventory_repo.get_inventory_location_by_id(session, location_id)
    if not current:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    if current.get("isDefault") and not payload.isActive:
        raise HTTPException(status_code=400, detail="Không thể khóa kệ mặc định của kho chính.")
    if not payload.isActive and await inventory_repo.inventory_location_has_stock(session, location_id):
        raise HTTPException(status_code=400, detail="Kệ còn tồn kho, cần xử lý hết tồn trước khi khóa.")
    location = await inventory_repo.set_inventory_location_status(
        session,
        location_id=location_id,
        status="ACTIVE" if payload.isActive else "INACTIVE",
    )
    if not location:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    await session.commit()
    return location


async def get_inventory_dashboard(session: AsyncSession, search: str = "") -> dict:
    raw_rows = await inventory_repo.list_inventory_level_rows(session, search.strip())
    rows = [_shape_inventory_level_row(row) for row in raw_rows]
    total_sku = len(rows)
    low_stock_rows = [row for row in rows if row["stockAlert"] == "LOW"]
    inventory_value = sum(float(row["physicalStock"] or 0) * float(row["averageUnitCost"] or 0) for row in rows)
    top_stock = sorted(rows, key=lambda row: int(row["physicalStock"] or 0), reverse=True)[:8]
    top_need_restock = sorted(
        low_stock_rows,
        key=lambda row: int(row["minimumStock"] or 0) - int(row["availableStock"] or 0),
        reverse=True,
    )[:8]
    return {
        "totalSku": total_sku,
        "lowStockCount": len(low_stock_rows),
        "inventoryValue": inventory_value,
        "reservedSkuCount": len([row for row in rows if row["reservedStock"] > 0]),
        "topStock": top_stock,
        "topNeedRestock": top_need_restock,
    }


async def get_inventory_aging_report(session: AsyncSession, search: str = "", bucket: str = "") -> dict:
    bucket = bucket.strip().upper()
    valid_buckets = {"", "0_30", "31_90", "91_180", "180_PLUS"}
    if bucket not in valid_buckets:
        raise HTTPException(status_code=400, detail="Nhóm tuổi tồn kho không hợp lệ.")

    rows = await inventory_repo.list_inventory_aging_rows(session, search.strip(), bucket)
    bucket_labels = {
        "0_30": "0-30 ngày",
        "31_90": "31-90 ngày",
        "91_180": "91-180 ngày",
        "180_PLUS": "Trên 180 ngày",
    }
    buckets = {
        key: {"bucket": key, "label": label, "skuCount": 0, "quantity": 0, "totalCost": 0.0}
        for key, label in bucket_labels.items()
    }
    items = []
    for row in rows:
        key = str(row.get("bucket") or "")
        quantity = int(row.get("quantity") or 0)
        total_cost = float(row.get("totalCost") or 0)
        if key in buckets:
            buckets[key]["skuCount"] += 1
            buckets[key]["quantity"] += quantity
            buckets[key]["totalCost"] += total_cost
        items.append(
            {
                **row,
                "bucketLabel": bucket_labels.get(key, key),
                "quantity": quantity,
                "totalCost": total_cost,
                "averageAgeDays": float(row.get("averageAgeDays") or 0),
                "maxAgeDays": int(row.get("maxAgeDays") or 0),
            }
        )

    return {
        "asOf": datetime.utcnow().isoformat() + "Z",
        "buckets": list(buckets.values()),
        "items": items,
        "totalQuantity": sum(item["quantity"] for item in items),
        "totalCost": sum(item["totalCost"] for item in items),
    }


async def get_inventory_reconciliation_report(session: AsyncSession, search: str = "", issue_type: str = "") -> dict:
    issue_type = issue_type.strip().upper()
    valid_issue_types = {
        "",
        "LEVEL_GT_IDENTIFIERS",
        "IDENTIFIER_IN_STOCK_WITHOUT_LOCATION",
        "IDENTIFIER_LOCATION_WITHOUT_LEVEL",
        "TERMINAL_IDENTIFIER_WITH_LOCATION",
    }
    if issue_type not in valid_issue_types:
        raise HTTPException(status_code=400, detail="Loại sai lệch tồn kho không hợp lệ.")

    rows = await inventory_repo.list_inventory_reconciliation_rows(session, search.strip(), issue_type)
    issue_labels = {
        "LEVEL_GT_IDENTIFIERS": "Tồn kệ lớn hơn số mã",
        "IDENTIFIER_IN_STOCK_WITHOUT_LOCATION": "Mã còn tồn nhưng chưa có kệ",
        "IDENTIFIER_LOCATION_WITHOUT_LEVEL": "Mã có kệ nhưng kệ không có tồn",
        "TERMINAL_IDENTIFIER_WITH_LOCATION": "Mã đã rời kho nhưng còn gắn kệ",
    }
    summary = {
        key: {"issueType": key, "label": label, "count": 0}
        for key, label in issue_labels.items()
    }
    for row in rows:
        key = row.get("issueType")
        if key in summary:
            summary[key]["count"] += 1
    return {
        "asOf": datetime.utcnow().isoformat() + "Z",
        "summary": list(summary.values()),
        "totalIssues": sum(item["count"] for item in summary.values()),
        "items": rows,
    }


async def list_inventory_ledger(
    session: AsyncSession,
    search: str = "",
    product_id: str = "",
    date_from: str = "",
    date_to: str = "",
    transaction_type: str = "",
    reason: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    for label, value in {"Từ ngày": date_from, "Đến ngày": date_to}.items():
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"{label} không hợp lệ.") from exc
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="Từ ngày không được lớn hơn đến ngày.")
    transaction_type = transaction_type.strip().upper()
    if transaction_type and transaction_type not in {"RECEIPT", "ADJUSTMENT", "SALE", "RETURN", "REVERSAL"}:
        raise HTTPException(status_code=400, detail="Loại giao dịch sổ kho không hợp lệ.")
    reason = reason.strip().upper()
    if reason and reason not in {"RTV_COMPLETED", "LIQUIDATED", "SCRAP", "OUT_OF_SYSTEM", "COST_ADJUSTMENT"}:
        raise HTTPException(status_code=400, detail="Lý do sổ kho không hợp lệ.")
    rows = await inventory_repo.list_inventory_ledger_rows(
        session,
        search=search.strip(),
        product_id=product_id.strip(),
        date_from=date_from.strip(),
        date_to=date_to.strip(),
        transaction_type=transaction_type,
        reason=reason,
    )
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "page": page, "pageSize": page_size, "total": total, "totalPages": max(1, (total + page_size - 1) // page_size)}
