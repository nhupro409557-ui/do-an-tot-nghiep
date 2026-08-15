from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.config import settings
from app.infrastructure.storage import media_storage


router = APIRouter(prefix=f"/{settings.media_public_path.strip('/')}", tags=["Media"])


@router.get("/{file_key:path}", response_model=None)
async def deliver_media(file_key: str) -> Response:
    try:
        if media_storage.driver == "s3":
            return RedirectResponse(media_storage.external_url(file_key), status_code=307)
        path = media_storage.resolve_local_path(file_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp media.") from exc

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp media.")
    return FileResponse(str(path))
