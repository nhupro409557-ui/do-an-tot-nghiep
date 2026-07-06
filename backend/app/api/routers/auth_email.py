from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr


router = APIRouter(prefix="/auth", tags=["Auth"])


class VerificationEmailRequest(BaseModel):
    email: EmailStr
    name: str
    code: str
    link: str
    purpose: str = "registration"


class VerificationEmailResponse(BaseModel):
    ok: bool


@router.post("/send-verification-email", response_model=VerificationEmailResponse)
async def send_verification_email(payload: VerificationEmailRequest) -> VerificationEmailResponse:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Endpoint gửi email trực tiếp đã tắt. Hãy dùng /auth/register/start hoặc /auth/forgot-password.",
    )
