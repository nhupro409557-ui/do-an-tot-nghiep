from app.infrastructure.database.repositories.media_repo import managed_media_keys


def test_managed_media_keys_canonicalize_new_and_legacy_references():
    assert managed_media_keys(
        [
            "products/new.webp",
            "/media/products/stable.webp",
            "https://api.example.com/uploads/products/legacy.webp",
            "/images/placeholder.webp",
        ]
    ) == [
        "products/new.webp",
        "products/stable.webp",
        "products/legacy.webp",
    ]


def test_managed_media_keys_remove_duplicates_without_changing_order():
    assert managed_media_keys(
        [
            "products/photo.webp",
            "/media/products/photo.webp",
            "products/other.webp",
        ]
    ) == ["products/photo.webp", "products/other.webp"]
