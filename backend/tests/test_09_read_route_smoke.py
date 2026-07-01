import pytest


def _has_required_non_auth_parameter(operation: dict) -> bool:
    for parameter in operation.get("parameters", []):
        if not parameter.get("required"):
            continue
        if parameter.get("in") == "header" and parameter.get("name", "").lower() in {
            "authorization",
            "x-user-id",
        }:
            continue
        return True
    return False


@pytest.mark.integration
async def test_all_parameterless_read_routes_avoid_server_errors(
    api_client,
    admin_headers,
    customer_headers,
):
    from app.main import app

    failures: list[str] = []
    checked = 0
    for path, path_item in app.openapi()["paths"].items():
        operation = path_item.get("get")
        if operation is None or "{" in path or _has_required_non_auth_parameter(operation):
            continue

        headers: dict[str, str] = {}
        if path.startswith("/api/admin/"):
            headers = admin_headers
        elif path.startswith("/api/me/") or path.startswith("/api/auth/"):
            headers = customer_headers

        response = await api_client.get(path, headers=headers)
        checked += 1
        if response.status_code >= 500:
            failures.append(f"GET {path}: {response.status_code}")

    assert checked >= 50, f"Số route đọc được kiểm tra quá thấp: {checked}"
    assert not failures, "Route đọc trả lỗi server:\n" + "\n".join(failures)
