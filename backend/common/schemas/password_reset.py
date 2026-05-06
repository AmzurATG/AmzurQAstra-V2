"""
Pydantic schemas for the forgot password / password reset flow.
"""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, validator
import re


# --- Initiate Password Reset ---

class ForgotPasswordInitiateRequest(BaseModel):
    """Start the password reset flow — returns user's security questions."""
    email: EmailStr


class SecurityQuestionOut(BaseModel):
    """A security question (without the answer) to display to the user."""
    id: int
    question: str


class ForgotPasswordInitiateResponse(BaseModel):
    email: str
    security_questions: List[SecurityQuestionOut]


# --- Verify Security Answers ---

class SecurityAnswerInput(BaseModel):
    """User's answer to a specific security question (by ID)."""
    id: int
    answer: str = Field(..., min_length=1, max_length=255)


class ForgotPasswordVerifyRequest(BaseModel):
    """Submit security question answers to get a password reset token."""
    email: EmailStr
    answers: List[SecurityAnswerInput] = Field(..., min_length=1)


class ForgotPasswordVerifyResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None  # Included in dev; in production, only sent via email


# --- Reset Password ---

class ResetPasswordRequest(BaseModel):
    """Final step: set a new password using the reset token."""
    email: EmailStr
    reset_token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)

    @validator("new_password")
    def validate_password_strength(cls, v):
        errors = []
        if not re.search(r"[A-Z]", v):
            errors.append("one uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("one lowercase letter")
        if not re.search(r"[0-9]", v):
            errors.append("one number")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", v):
            errors.append("one special character")
        if re.search(r"\s", v):
            errors.append("no whitespace")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class ResetPasswordResponse(BaseModel):
    message: str
