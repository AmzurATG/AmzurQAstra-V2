"""
Signup Service

Orchestrates the multi-step signup flow:
1. check_email_exists — pre-check
2. initiate_signup — validate, store pending data, send OTP
3. complete_signup — verify OTP, create user, store security questions
"""
from __future__ import annotations

import logging
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.user import User, UserRole
from common.db.models.email_verification import EmailVerification
from common.db.models.security_question import SecurityQuestion
from common.schemas.signup import SignupRequest
from common.services import otp_service
from common.utils.security import hash_password

logger = logging.getLogger(__name__)


async def check_email_exists(db: AsyncSession, email: str) -> bool:
    """Check if an email is already registered."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none() is not None


async def initiate_signup(db: AsyncSession, data: SignupRequest) -> dict:
    """
    Validate signup data, store pending registration, and send OTP.
    Returns a response dict with message and email.
    Raises ValueError on validation failures.
    """
    # Check if email is already registered
    if await check_email_exists(db, data.email):
        raise ValueError("Email already registered")

    # Prepare user data for storage (without password confirmation)
    user_data = {
        "first_name": data.first_name,
        "last_name": data.last_name,
        "company_name": data.company_name,
        "email": data.email,
        "country_code": data.country_code,
        "phone_number": data.phone_number,
        "password": data.password,  # Will be hashed when user is actually created
    }

    # Prepare security questions (hash answers for storage)
    security_questions = []
    for sq in data.security_questions:
        answer_hash = bcrypt.hashpw(
            sq.answer.strip().lower().encode(), bcrypt.gensalt()
        ).decode()
        security_questions.append({
            "question": sq.question,
            "answer_hash": answer_hash,
        })

    # Create verification record + send OTP
    await otp_service.create_verification(
        db=db,
        email=data.email,
        user_data=user_data,
        security_questions=security_questions,
    )

    return {
        "message": "Verification code sent. Please check your email to complete registration.",
        "email": data.email,
    }


async def complete_signup(
    db: AsyncSession, email: str, otp: str
) -> tuple[str, Optional[User], Optional[EmailVerification]]:
    """
    Verify OTP and create the user.
    Returns: (status, user_or_none, verification_record)
    Status: "success", "invalid", "expired", "locked", "not_found"
    """
    status, verification = await otp_service.verify_otp(db, email, otp)

    if status != "valid" or verification is None:
        return status, None, verification

    # OTP verified — create the real user
    user_data = verification.user_data
    security_questions_data = verification.security_questions or []

    # Create user
    user = User(
        email=user_data["email"],
        hashed_password=hash_password(user_data["password"]),
        full_name=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
        role=UserRole.tester,
        is_active=True,
        is_verified=True,
        company_name=user_data.get("company_name"),
        country_code=user_data.get("country_code"),
        phone_number=user_data.get("phone_number"),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Store security questions
    for sq_data in security_questions_data:
        sq = SecurityQuestion(
            user_id=user.id,
            question_text=sq_data["question"],
            answer_hash=sq_data["answer_hash"],
        )
        db.add(sq)

    # Clean up the verification record
    await db.delete(verification)
    await db.flush()

    logger.info(f"Signup completed for {email}, user_id={user.id}")
    return "success", user, verification
