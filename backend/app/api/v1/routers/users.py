from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
from app.application.users.schemas import DeleteAccountRequest, DeleteAccountResponse
from app.infrastructure.database.session import get_session
from app.application.services import user_service


router = APIRouter(prefix="/users", tags=["Users"])


@router.delete("/me", response_model=DeleteAccountResponse, status_code=status.HTTP_200_OK)
async def delete_my_account(
    _: DeleteAccountRequest,
    request: Request,
    response: Response,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> DeleteAccountResponse:
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    
    result = await user_service.delete_user_account(
        session=session,
        current_user_id=current_user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    response.delete_cookie(key="emv_refresh_token", path="/api/auth")
    return result
