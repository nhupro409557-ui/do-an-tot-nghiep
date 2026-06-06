from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.schemas import DeleteAccountResponse
from app.application.users.use_cases import DeleteAccountUseCase
from app.infrastructure.database.repositories.users import (
    SqlAlchemyLoyaltyRepository,
    SqlAlchemyUserRepository,
    insert_account_deleted_security_audit,
    prepare_account_deletion_security_tables,
    revoke_user_refresh_sessions,
    upsert_account_deletion_revocation,
)
from app.shared.exceptions import LoyaltyWalletClosedError, UserNotFoundError


async def delete_user_account(
    session: AsyncSession,
    current_user_id: UUID,
    ip_address: str,
    user_agent: str | None,
) -> DeleteAccountResponse:
    use_case = DeleteAccountUseCase(
        session=session,
        user_repository=SqlAlchemyUserRepository(session),
        loyalty_repository=SqlAlchemyLoyaltyRepository(session),
    )

    try:
        result = await use_case.execute(current_user_id)
        await prepare_account_deletion_security_tables(session)
        await revoke_user_refresh_sessions(session, current_user_id)
        await upsert_account_deletion_revocation(session, current_user_id)
        await insert_account_deleted_security_audit(
            session,
            user_id=current_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await session.commit()
        return result
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except LoyaltyWalletClosedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
