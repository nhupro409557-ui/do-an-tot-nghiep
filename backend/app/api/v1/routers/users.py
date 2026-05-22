from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
from app.application.users.schemas import DeleteAccountRequest, DeleteAccountResponse
from app.application.users.use_cases import DeleteAccountUseCase
from app.infrastructure.database.repositories.users import (
    SqlAlchemyLoyaltyRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.database.session import get_session
from app.shared.exceptions import LoyaltyWalletClosedError, UserNotFoundError


router = APIRouter(prefix="/users", tags=["Users"])


@router.delete("/me", response_model=DeleteAccountResponse, status_code=status.HTTP_200_OK)
async def delete_my_account(
    _: DeleteAccountRequest,
    request: Request,
    response: Response,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> DeleteAccountResponse:
    use_case = DeleteAccountUseCase(
        session=session,
        user_repository=SqlAlchemyUserRepository(session),
        loyalty_repository=SqlAlchemyLoyaltyRepository(session),
    )

    try:
        result = await use_case.execute(current_user_id)
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('emv_auth_security_tables'))"))
        await session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS auth_session_revocations (
                    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    revoked_after TIMESTAMPTZ NOT NULL,
                    reason VARCHAR(120) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS security_audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    event_type VARCHAR(80) NOT NULL,
                    email VARCHAR(255),
                    ip_address VARCHAR(80),
                    user_agent TEXT,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS refresh_token_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    family_id UUID NOT NULL,
                    user_agent TEXT,
                    ip_address VARCHAR(80),
                    expires_at TIMESTAMPTZ NOT NULL,
                    revoked_at TIMESTAMPTZ,
                    replaced_by UUID,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    rotated_at TIMESTAMPTZ
                )
                """
            )
        )
        await session.execute(
            text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"),
            {"user_id": current_user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
                VALUES (:user_id, NOW(), 'account_deleted')
                ON CONFLICT (user_id)
                DO UPDATE SET revoked_after = EXCLUDED.revoked_after, reason = EXCLUDED.reason, created_at = NOW()
                """
            ),
            {"user_id": current_user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO security_audit_logs
                    (user_id, event_type, ip_address, user_agent, metadata)
                VALUES
                    (:user_id, 'account_deleted', :ip_address, :user_agent, '{}'::jsonb)
                """
            ),
            {
                "user_id": current_user_id,
                "ip_address": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent"),
            },
        )
        await session.commit()
        response.delete_cookie(key="emv_refresh_token", path="/api/v1/auth")
        return result
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except LoyaltyWalletClosedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
