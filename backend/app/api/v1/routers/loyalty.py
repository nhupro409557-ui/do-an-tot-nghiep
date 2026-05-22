from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
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
        400: {"description": "Insufficient points or invalid request."},
        401: {"description": "Missing or invalid authentication context."},
        403: {"description": "The user is not allowed to redeem points."},
        404: {"description": "Active user not found."},
        409: {"description": "Loyalty wallet is not active."},
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
