from email.message import EmailMessage
import smtplib

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.config import settings


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
    if not settings.smtp_username or not settings.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SMTP is not configured.",
        )

    sender = settings.smtp_from_email or settings.smtp_username
    brand_name = "ElectroMart VietNam"
    is_password_reset = payload.purpose == "password_reset"
    action_name = "Đặt lại mật khẩu" if is_password_reset else "Xác nhận tài khoản"
    intro = (
        f"Bạn vừa yêu cầu đặt lại mật khẩu tài khoản {brand_name}."
        if is_password_reset
        else f"Bạn vừa đăng ký tài khoản {brand_name}."
    )

    message = EmailMessage()
    message["Subject"] = f"{action_name} {brand_name}"
    message["From"] = sender
    message["To"] = payload.email
    message.set_content(
        "\n".join(
            [
                f"Xin chào {payload.name},",
                "",
                intro,
                f"Mã xác nhận của bạn là: {payload.code}",
                "",
                f"Hoặc bấm vào liên kết này để xác nhận tự động: {payload.link}",
                "",
                "Mã xác nhận có hiệu lực trong 15 phút.",
            ]
        )
    )
    message.add_alternative(
        f"""
        <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
          <h2 style="color:#d70018">{action_name} {brand_name}</h2>
          <p>Xin chào <strong>{payload.name}</strong>,</p>
          <p>{intro}</p>
          <p>Mã xác nhận của bạn:</p>
          <div style="font-size:28px;font-weight:700;letter-spacing:6px;color:#d70018">{payload.code}</div>
          <p>Hoặc bấm nút bên dưới để xác nhận tự động:</p>
          <p>
            <a href="{payload.link}" style="background:#d70018;color:#fff;text-decoration:none;padding:12px 18px;border-radius:8px;display:inline-block">
              {action_name}
            </a>
          </p>
          <p style="color:#6b7280;font-size:13px">Mã xác nhận có hiệu lực trong 15 phút.</p>
        </div>
        """,
        subtype="html",
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Không gửi được email xác nhận.",
        ) from exc

    return VerificationEmailResponse(ok=True)
