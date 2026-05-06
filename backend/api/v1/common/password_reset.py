"""
Forgot Password / Password Reset Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.schemas.password_reset import (
    ForgotPasswordInitiateRequest,
    ForgotPasswordInitiateResponse,
    ForgotPasswordVerifyRequest,
    ForgotPasswordVerifyResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SecurityQuestionOut,
)
from common.services import password_reset_service
from common.services.smtp_mailer import SmtpSendError


router = APIRouter()


@router.post("/forgot-password/initiate", response_model=ForgotPasswordInitiateResponse)
async def initiate_password_reset(
    data: ForgotPasswordInitiateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start the password reset flow.
    Returns the user's security questions (without answers).
    """
    questions = await password_reset_service.get_security_questions_for_email(db, data.email)

    if questions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that email address.",
        )

    return ForgotPasswordInitiateResponse(
        email=data.email,
        security_questions=[SecurityQuestionOut(**q) for q in questions],
    )


@router.post("/forgot-password/verify-security", response_model=ForgotPasswordVerifyResponse)
async def verify_security_answers(
    data: ForgotPasswordVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify security question answers.
    On success, generates and emails a reset token.
    """
    answers = [{"id": a.id, "answer": a.answer} for a in data.answers]
    all_correct, field_errors = await password_reset_service.verify_security_answers(
        db, data.email, answers
    )

    if not all_correct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Some security answers are incorrect",
                "field_errors": field_errors,
            },
        )

    # Answers correct — generate and send reset token
    try:
        token = await password_reset_service.create_and_send_reset_token(db, data.email)
    except SmtpSendError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send reset email: {e.message}",
        )

    return ForgotPasswordVerifyResponse(
        message="Security answers verified. A password reset token has been sent to your email.",
        reset_token=token,  # Include for dev convenience; remove in production
    )


@router.post("/forgot-password/reset", response_model=ResetPasswordResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using the emailed token.
    """
    success, message = await password_reset_service.verify_token_and_reset_password(
        db, data.email, data.reset_token, data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return ResetPasswordResponse(message=message)
