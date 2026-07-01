import pytest


@pytest.mark.integration
@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/api/catalog/categories",
        "/api/catalog/brands",
        "/api/catalog/products",
        "/api/catalog/rankings",
        "/api/catalog/images",
        "/api/banners",
        "/api/videos",
        "/api/payment-methods",
        "/api/shipping-config",
        "/api/store/info",
        "/api/vouchers",
    ],
)
async def test_public_database_to_api_read_paths(api_client, path):
    response = await api_client.get(path)

    assert response.status_code == 200, f"{path}: {response.status_code} {response.text}"
    assert response.headers["content-type"].startswith("application/json")
