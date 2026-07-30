from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_optional_current_user_id
from app.application.ai.contracts import HandoverInfo
from app.application.ai.conversation_token import issue_conversation_token, validate_conversation_token
from app.application.ai.schemas import (
    AIConversationSessionResponse,
    AIAssistantFeedbackRequest,
    AIAssistantFeedbackResponse,
    AIAssistantRequest,
    AIAssistantResponse,
)
from app.application.ai.use_cases import AIAssistantUseCase
from app.config import settings
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session
from app.infrastructure.database.repositories import ai_repo
from app.infrastructure.database.repositories.store_info_repo import get_store_info


router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


def _traffic_origin(client_host: str | None, client_capabilities: list[str]) -> str:
    is_local_client = client_host in {"127.0.0.1", "::1", "testclient"}
    declares_synthetic = "synthetic_evaluation_v1" in client_capabilities
    return "SYNTHETIC" if is_local_client and declares_synthetic else "CUSTOMER"


def _require_valid_conversation_token(
    token: str | None,
    *,
    conversation_id: UUID,
    current_user_id: UUID | None,
) -> None:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu mã xác thực phiên trò chuyện.",
        )
    try:
        validate_conversation_token(
            token,
            conversation_id=conversation_id,
            user_id=current_user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post("/conversations", response_model=AIConversationSessionResponse)
async def create_ai_conversation(
    current_user_id: UUID | None = Depends(get_optional_current_user_id),
) -> AIConversationSessionResponse:
    conversation_id = uuid4()
    token, expires_at = issue_conversation_token(
        conversation_id=conversation_id,
        user_id=current_user_id,
        ttl_minutes=settings.ai_conversation_memory_ttl_minutes,
    )
    return AIConversationSessionResponse(
        conversation_id=conversation_id,
        conversation_token=token,
        expires_at=expires_at,
    )


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
    request: Request,
    current_user_id: UUID | None = Depends(get_optional_current_user_id),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> AIAssistantResponse:
    _require_valid_conversation_token(
        payload.conversation_token,
        conversation_id=payload.conversation_id,
        current_user_id=current_user_id,
    )
    use_case = AIAssistantUseCase(session=session, redis=redis)
    return await use_case.execute(
        user_id=str(current_user_id) if current_user_id else None,
        request=payload,
        traffic_origin=_traffic_origin(
            request.client.host if request.client else None,
            payload.client_capabilities,
        ),
    )


@router.post("/feedback", response_model=AIAssistantFeedbackResponse)
async def submit_ai_assistant_feedback(
    payload: AIAssistantFeedbackRequest,
    current_user_id: UUID | None = Depends(get_optional_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AIAssistantFeedbackResponse:
    _require_valid_conversation_token(
        payload.conversation_token,
        conversation_id=payload.conversation_id,
        current_user_id=current_user_id,
    )
    saved = await ai_repo.save_ai_feedback(
        session,
        response_id=payload.response_id,
        conversation_id=payload.conversation_id,
        user_id=current_user_id,
        helpful=payload.helpful,
        reason=payload.reason.strip() if payload.reason else None,
    )
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phản hồi chatbot thuộc phiên hiện tại.",
        )
    handover = None
    if not payload.helpful:
        unhelpful_count = await ai_repo.get_consecutive_unhelpful_feedback_count(
            session,
            conversation_id=payload.conversation_id,
            user_id=current_user_id,
        )
        if unhelpful_count >= max(1, settings.ai_handover_failure_threshold):
            store = await get_store_info(session)
            phone = getattr(store, "hotline", None)
            email = getattr(store, "email", None)
            contact_text = (
                f"Hotline chăm sóc khách hàng: {phone}."
                if phone
                else (f"Email chăm sóc khách hàng: {email}." if email else "")
            )
            handover = HandoverInfo(
                reason="Khách hàng đánh giá nhiều câu trả lời liên tiếp chưa hữu ích.",
                phone=phone,
                email=email,
                display_text=(
                    "Mình nhận thấy các câu trả lời vừa rồi chưa giúp được bạn. "
                    f"Bạn có muốn liên hệ bộ phận chăm sóc khách hàng không? {contact_text}"
                ).strip(),
                can_create_ticket=current_user_id is not None,
            )
    await session.commit()
    return AIAssistantFeedbackResponse(
        saved=True,
        handover_recommended=handover is not None,
        handover=handover,
    )
