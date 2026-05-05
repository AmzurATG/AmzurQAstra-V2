"""
Signup Endpoints

Multi-step signup flow with OTP email verification.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.schemas.signup import (
    CheckEmailRequest,
    CheckEmailResponse,
    ResendOTPRequest,
    SignupRequest,
    SignupResponse,
    VerifyOTPRequest,
    OTPVerifyResponse,
)
from common.services import signup_service, otp_service
from common.services.smtp_mailer import SmtpSendError


router = APIRouter()


@router.post("/check-email", response_model=CheckEmailResponse)
async def check_email(
    data: CheckEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check if an email address is already registered."""
    exists = await signup_service.check_email_exists(db, data.email)
    return CheckEmailResponse(exists=exists, email=data.email)


@router.post("/signup", response_model=SignupResponse)
async def signup(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user (Step 2 submission).
    Validates data, stores pending registration, and sends OTP email.
    """
    try:
        result = await signup_service.initiate_signup(db, data)
        return SignupResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except SmtpSendError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send verification email: {e.message}",
        )


@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(
    data: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify the 6-digit OTP to complete signup.
    On success, creates the user account.
    """
    result_status, user, verification = await signup_service.complete_signup(
        db, data.email, data.otp
    )

    if result_status == "success":
        return OTPVerifyResponse(detail="Email verified successfully", success=True)

    if result_status == "not_found":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending registration found. Please sign up again.",
        )

    if result_status == "expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one.",
        )

    if result_status == "locked":
        # Calculate remaining lockout time
        remaining_seconds = 0
        if verification and verification.locked_until:
            delta = verification.locked_until - datetime.now(timezone.utc)
            remaining_seconds = max(0, int(delta.total_seconds()))
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Too many incorrect attempts. Please wait before trying again."},
            headers={"X-Lockout-Seconds": str(remaining_seconds)},
        )

    if result_status == "invalid":
        # Calculate remaining attempts
        remaining = otp_service.MAX_OTP_ATTEMPTS - (verification.attempts if verification else 0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Verification failed.",
    )


@router.post("/resend-otp", response_model=SignupResponse)
async def resend_otp(
    data: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resend OTP for a pending signup."""
    result = await otp_service.resend_otp(db, data.email)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending registration found or account is temporarily locked.",
        )
    return SignupResponse(
        message="New verification code sent.",
        email=data.email,
    )
