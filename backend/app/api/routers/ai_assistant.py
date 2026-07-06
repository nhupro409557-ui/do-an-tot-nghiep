from uuid import UUID

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_optional_current_user_id
from app.application.ai.schemas import AIAssistantRequest, AIAssistantResponse
from app.application.ai.use_cases import AIAssistantUseCase
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session


router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


@router.post(
    "/chat",
    response_model=AIAssistantResponse,
    responses={
        400: {"description": "Invalid AI assistant payload."},
        403: {"description": "The request is outside the sales assistant scope."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def chat_with_ai_assistant(
    payload: AIAssistantRequest,
    current_user_id: UUID | None = Depends(get_optional_current_user_id),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> AIAssistantResponse:
    use_case = AIAssistantUseCase(session=session, redis=redis)
    return await use_case.execute(user_id=str(current_user_id) if current_user_id else None, request=payload)
