from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.application.loyalty.schemas import RedeemPointsRequest, RedeemPointsResponse
from app.application.loyalty.use_cases import RedeemPointsUseCase
from app.infrastructure.database.session import get_session
from app.shared.exceptions import (
    InsufficientPointsError,
    LoyaltyWalletClosedError,
    UserNotFoundError,
)


router = APIRouter(prefix="/loyalty", tags=["Loyalty"])


@router.post(
    "/redeem",
    response_model=RedeemPointsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Không đủ điểm hoặc yêu cầu không hợp lệ."},
        401: {"description": "Thiếu hoặc sai ngữ cảnh xác thực."},
        403: {"description": "Người dùng không được phép đổi điểm."},
        404: {"description": "Không tìm thấy tài khoản đang hoạt động."},
        409: {"description": "Ví điểm thưởng không ở trạng thái hoạt động."},
    },
)
async def redeem_points(
    payload: RedeemPointsRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> RedeemPointsResponse:
    try:
        return await RedeemPointsUseCase(session=session).execute(
            user_id=current_user_id,
            order_id=payload.order_id,
            points=payload.points,
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except LoyaltyWalletClosedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except InsufficientPointsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
