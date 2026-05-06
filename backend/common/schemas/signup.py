"""
Pydantic schemas for the signup flow.
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
import re


# --- Security Question Schemas ---

class SecurityQuestionInput(BaseModel):
    """A single security question + answer pair from the user."""
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1, max_length=255)


# --- Signup Request ---

class SignupRequest(BaseModel):
    """Step 2 submission: full user data + security questions → triggers OTP email."""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    company_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    country_code: Optional[str] = Field(None, max_length=10)
    phone_number: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)
    security_questions: List[SecurityQuestionInput] = Field(..., min_length=2, max_length=2)

    @validator("email")
    def validate_business_email(cls, v):
        free_providers = [
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
            "aol.com", "icloud.com", "mail.com", "protonmail.com",
            "zoho.com", "yandex.com", "gmx.com", "live.com"
            #-- , "mailinator.com", Allowing mailinator for testing purposes, but can be blocked in production
        ]
        domain = v.split("@")[1].lower()
        if domain in free_providers:
            raise ValueError("Please use a business email address (you@company.com)")
        return v

    @validator("password")
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
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

    @validator("security_questions")
    def questions_must_be_different(cls, v):
        if len(v) == 2 and v[0].question == v[1].question:
            raise ValueError("Security questions must be different")
        return v


# --- Check Email ---

class CheckEmailRequest(BaseModel):
    """Check if an email is already registered."""
    email: EmailStr


class CheckEmailResponse(BaseModel):
    exists: bool
    email: str


# --- OTP Verification ---

class VerifyOTPRequest(BaseModel):
    """Verify the 6-digit OTP to complete signup."""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

    @validator("otp")
    def validate_otp_format(cls, v):
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v


# --- Resend OTP ---

class ResendOTPRequest(BaseModel):
    """Request a new OTP for a pending signup."""
    email: EmailStr


# --- Responses ---

class SignupResponse(BaseModel):
    message: str
    email: str


class OTPVerifyResponse(BaseModel):
    detail: str
    success: bool
