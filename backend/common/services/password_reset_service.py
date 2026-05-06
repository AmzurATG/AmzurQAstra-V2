"""
Password Reset Service

Handles the forgot-password flow:
1. Retrieve security questions for an email
2. Verify security answers
3. Generate + email a reset token
4. Validate token and reset password
"""
from __future__ import annotations

import logging
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, format_datetime
from typing import Optional

import bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.user import User
from common.db.models.security_question import SecurityQuestion
from common.db.models.password_reset_token import PasswordResetToken
from common.services.smtp_mailer import is_smtp_configured, SmtpSendError
from common.utils.security import hash_password
from config import settings

logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRY_MINUTES = 10


async def get_security_questions_for_email(
    db: AsyncSession, email: str
) -> list[dict] | None:
    """
    Return security questions (id + question_text) for a user.
    Returns None if user not found.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None

    sq_result = await db.execute(
        select(SecurityQuestion).where(SecurityQuestion.user_id == user.id)
    )
    questions = sq_result.scalars().all()

    if not questions:
        return None

    return [{"id": q.id, "question": q.question_text} for q in questions]


async def verify_security_answers(
    db: AsyncSession, email: str, answers: list[dict]
) -> tuple[bool, dict]:
    """
    Verify security question answers.
    Returns: (all_correct, field_errors)
    field_errors is a dict of {question_id: error_message} for incorrect answers.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return False, {"general": "Account not found"}

    field_errors = {}
    for answer_input in answers:
        q_id = answer_input["id"]
        provided_answer = answer_input["answer"].strip().lower()

        sq_result = await db.execute(
            select(SecurityQuestion).where(
                SecurityQuestion.id == q_id,
                SecurityQuestion.user_id == user.id,
            )
        )
        sq = sq_result.scalar_one_or_none()

        if not sq:
            field_errors[str(q_id)] = "Question not found"
            continue

        if not bcrypt.checkpw(provided_answer.encode(), sq.answer_hash.encode()):
            field_errors[str(q_id)] = "Incorrect answer"

    all_correct = len(field_errors) == 0
    return all_correct, field_errors


async def create_and_send_reset_token(db: AsyncSession, email: str) -> str:
    """
    Generate a reset token, store its hash, and email it to the user.
    Returns the plain token (for dev/testing response).
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    # Invalidate any existing unused tokens for this user
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,  # noqa: E712
        )
        .values(used=True)
    )
    await db.flush()

    # Generate a 6-character alphanumeric token (easy to type from email)
    token = secrets.token_hex(3).upper()  # 6 hex chars e.g. "A3F2B1"
    token_hash = bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_record)
    await db.flush()

    # Send email
    _send_reset_token_email(email, token)

    logger.info(f"Password reset token created for {email}, expires at {expires_at}")
    return token


async def verify_token_and_reset_password(
    db: AsyncSession, email: str, token: str, new_password: str
) -> tuple[bool, str]:
    """
    Verify the reset token and update the password.
    Returns: (success, message)
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return False, "Account not found"

    # Find valid (unused, not expired) tokens for this user
    now = datetime.now(timezone.utc)
    tokens_result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,  # noqa: E712
            PasswordResetToken.expires_at > now,
        )
    )
    valid_tokens = tokens_result.scalars().all()

    # Check if any token matches
    matched_token: Optional[PasswordResetToken] = None
    for t in valid_tokens:
        if bcrypt.checkpw(token.encode(), t.token_hash.encode()):
            matched_token = t
            break

    if not matched_token:
        return False, "Invalid or expired reset token"

    # Mark token as used
    matched_token.used = True

    # Update password
    user.hashed_password = hash_password(new_password)
    await db.flush()

    logger.info(f"Password reset completed for {email}")
    return True, "Password reset successfully"


def _send_reset_token_email(to_email: str, token: str) -> None:
    """Send password reset token email."""
    if not is_smtp_configured():
        logger.warning("SMTP not configured — reset token email not sent")
        raise SmtpSendError("Email is not configured (set SMTP_HOST and EMAIL_FROM_ADDRESS).")

    from_email = settings.EMAIL_FROM_ADDRESS
    from_name = (settings.EMAIL_FROM_NAME or "QAstra").strip()

    subject = "QAstra Password Reset"

    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;padding:20px;">
<h2 style="color:#2563eb;">Password Reset Request</h2>
<p>You've requested to reset your password for your QAstra account.</p>
<p>Use the following token to complete the password reset process:</p>
<div style="background-color:#f3f4f6;border-radius:8px;padding:20px;text-align:center;margin:24px 0;">
  <span style="font-family:monospace;font-size:32px;font-weight:bold;letter-spacing:6px;color:#1f2937;">{token}</span>
</div>
<p>This token will expire in <strong>{RESET_TOKEN_EXPIRY_MINUTES} minutes</strong>.</p>
<p style="color:#6b7280;font-size:13px;">If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
<p style="margin-top:2em;">Kind regards,<br><strong>QAstra</strong></p>
</body></html>"""

    text_body = f"""Password Reset Request

Your password reset token is: {token}

This token will expire in {RESET_TOKEN_EXPIRY_MINUTES} minutes.

If you didn't request a password reset, please ignore this email.
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_email
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    timeout = max(5, int(settings.SMTP_TIMEOUT_SECONDS or 30))
    user_smtp = (settings.SMTP_USER or "").strip()
    password = settings.SMTP_PASSWORD or ""
    host = settings.SMTP_HOST
    port = int(settings.SMTP_PORT or (465 if settings.SMTP_USE_SSL else 587))

    try:
        if settings.SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
                if user_smtp or password:
                    smtp.login(user_smtp, password)
                smtp.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if settings.SMTP_USE_TLS:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if user_smtp or password:
                    smtp.login(user_smtp, password)
                smtp.sendmail(from_email, [to_email], msg.as_string())

        logger.info(f"Password reset email sent to {to_email}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP auth failed: {e}")
        raise SmtpSendError(f"SMTP authentication failed: {e}") from e
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending reset token: {e}")
        raise SmtpSendError(f"SMTP error: {e}") from e
    except OSError as e:
        logger.error(f"Could not reach mail server: {e}")
        raise SmtpSendError(f"Could not reach mail server: {e}") from e
