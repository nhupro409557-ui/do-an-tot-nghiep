from collections import Counter

import pytest


@pytest.mark.contract
def test_openapi_operations_have_unique_ids_and_tags():
    from app.main import app

    schema = app.openapi()
    operation_ids: list[str] = []
    untagged: list[str] = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            operation_ids.append(operation["operationId"])
            if not operation.get("tags"):
                untagged.append(f"{method.upper()} {path}")

    duplicates = [key for key, count in Counter(operation_ids).items() if count > 1]
    assert not duplicates, f"operationId bị trùng: {duplicates}"
    assert not untagged, f"API chưa phân nhóm: {untagged}"


@pytest.mark.contract
async def test_protected_mutations_reject_anonymous_requests_without_server_error(api_client):
    from app.main import app

    schema = app.openapi()
    failures: list[str] = []
    skipped_public_callbacks = {
        "/api/payments/momo/ipn",
        "/api/payments/sepay/ipn",
        "/api/payments/zalopay/callback",
    }
    for path, path_item in schema["paths"].items():
        if path in skipped_public_callbacks:
            continue
        if not path.startswith(("/api/admin/", "/api/me/")):
            continue
        concrete_path = (
            path.replace("{brand_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{category_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{content_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{user_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{sale_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{product_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{variant_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{location_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{request_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{service_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{review_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{supplier_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{voucher_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{method_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{identifier_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{notification_id}", "00000000-0000-0000-0000-000000000001")
            .replace("{reference_code}", "TEST-NOT-FOUND")
            .replace("{document_no}", "TEST-NOT-FOUND")
            .replace("{filename}", "test.txt")
            .replace("{folder}", "test")
        )
        for method in set(path_item) & {"post", "put", "patch", "delete"}:
            response = await api_client.request(method, concrete_path, json={})
            if response.status_code >= 500:
                failures.append(f"{method.upper()} {path}: {response.status_code}")

    assert not failures, "Endpoint bảo vệ trả lỗi server khi chưa đăng nhập:\n" + "\n".join(failures)
