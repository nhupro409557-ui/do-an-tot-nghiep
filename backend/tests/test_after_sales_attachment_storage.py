from app.application.after_sales.attachments import attachment_url


def test_attachment_url_uses_stable_media_path_for_new_storage_keys():
    assert attachment_url("after-sales/return/request/photo.webp") == (
        "/media/after-sales/return/request/photo.webp"
    )


def test_attachment_url_keeps_legacy_upload_keys_compatible():
    assert attachment_url("uploads/after-sales/warranty/request/video.mp4") == (
        "/media/after-sales/warranty/request/video.mp4"
    )
