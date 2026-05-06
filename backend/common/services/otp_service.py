"""
OTP Service for signup email verification.

Generates, stores (in DB), and verifies 6-digit OTPs.
Sends verification emails via the existing SMTP infrastructure.
"""
from __future__ import annotations

import logging
import random
import smtplib
import ssl
import string
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, format_datetime

import bcrypt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.email_verification import EmailVerification
from common.services.smtp_mailer import is_smtp_configured, SmtpSendError
from config import settings

logger = logging.getLogger(__name__)

# Constants
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3
LOCKOUT_DURATION_MINUTES = 5


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def _hash_otp(otp: str) -> str:
    """Hash OTP with bcrypt for secure storage."""
    return bcrypt.hashpw(otp.encode(), bcrypt.gensalt()).decode()


def _verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """Verify an OTP against its bcrypt hash."""
    return bcrypt.checkpw(otp.encode(), otp_hash.encode())


async def create_verification(
    db: AsyncSession,
    email: str,
    user_data: dict,
    security_questions: list[dict],
) -> str:
    """
    Create or replace a pending email verification.
    Generates OTP, stores hashed OTP + pending data in DB, sends email.
    Returns the OTP (for logging in dev only).
    """
    otp = generate_otp()
    otp_hash = _hash_otp(otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Upsert: delete existing verification for this email, then insert new
    await db.execute(
        delete(EmailVerification).where(EmailVerification.email == email)
    )
    await db.flush()

    verification = EmailVerification(
        email=email,
        otp_hash=otp_hash,
        user_data=user_data,
        security_questions=security_questions,
        expires_at=expires_at,
        attempts=0,
        locked_until=None,
    )
    db.add(verification)
    await db.flush()

    # Send OTP email
    _send_otp_email(email, otp)

    logger.info(f"OTP verification created for {email}, expires at {expires_at}")
    return otp


async def verify_otp(
    db: AsyncSession,
    email: str,
    otp: str,
) -> tuple[str, EmailVerification | None]:
    """
    Verify OTP for an email.
    Returns: (status, verification_record)
    Status is one of: "valid", "invalid", "expired", "locked", "not_found"
    """
    result = await db.execute(
        select(EmailVerification).where(EmailVerification.email == email)
    )
    verification = result.scalar_one_or_none()

    if not verification:
        return "not_found", None

    now = datetime.now(timezone.utc)

    # Check lockout
    if verification.locked_until and now < verification.locked_until:
        return "locked", verification

    # Check expiry
    if now > verification.expires_at:
        return "expired", verification

    # Verify OTP hash
    if not _verify_otp_hash(otp, verification.otp_hash):
        # Increment attempts
        verification.attempts += 1
        if verification.attempts >= MAX_OTP_ATTEMPTS:
            verification.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        await db.flush()
        return "invalid", verification

    # OTP is valid
    return "valid", verification


async def resend_otp(db: AsyncSession, email: str) -> str | None:
    """
    Generate a new OTP for an existing pending verification.
    Returns the new OTP or None if not found / locked.
    """
    result = await db.execute(
        select(EmailVerification).where(EmailVerification.email == email)
    )
    verification = result.scalar_one_or_none()

    if not verification:
        return None

    now = datetime.now(timezone.utc)

    # Check lockout
    if verification.locked_until and now < verification.locked_until:
        return None

    # Generate new OTP
    otp = generate_otp()
    verification.otp_hash = _hash_otp(otp)
    verification.expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    verification.attempts = 0
    verification.locked_until = None
    await db.flush()

    # Send new OTP email
    _send_otp_email(email, otp)

    logger.info(f"OTP resent for {email}")
    return otp


async def cleanup_expired(db: AsyncSession) -> int:
    """Delete expired verification records. Returns count deleted."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(EmailVerification).where(EmailVerification.expires_at < now)
    )
    await db.flush()
    count = result.rowcount  # type: ignore[attr-defined]
    if count:
        logger.info(f"Cleaned up {count} expired email verifications")
    return count


def _send_otp_email(to_email: str, otp: str) -> None:
    """Send OTP verification email using existing SMTP config."""
    if not is_smtp_configured():
        logger.warning("SMTP not configured — OTP email not sent")
        raise SmtpSendError("Email is not configured (set SMTP_HOST and EMAIL_FROM_ADDRESS).")

    from_email = settings.EMAIL_FROM_ADDRESS
    from_name = (settings.EMAIL_FROM_NAME or "QAstra").strip()

    subject = "Your QAstra Verification Code"

    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;padding:20px;">
<h2 style="color:#2563eb;">Welcome to QAstra!</h2>
<p>Thank you for signing up. Please use the verification code below to complete your registration:</p>
<div style="background-color:#f3f4f6;border-radius:8px;padding:20px;text-align:center;margin:24px 0;">
  <span style="font-family:monospace;font-size:32px;font-weight:bold;letter-spacing:8px;color:#1f2937;">{otp}</span>
</div>
<p>This code will expire in <strong>{OTP_EXPIRY_MINUTES} minutes</strong>.</p>
<p style="color:#6b7280;font-size:13px;">If you didn't request this code, please ignore this email.</p>
<p style="margin-top:2em;">Kind regards,<br><strong>QAstra</strong></p>
</body></html>"""

    text_body = f"""Welcome to QAstra!

Your verification code is: {otp}

This code will expire in {OTP_EXPIRY_MINUTES} minutes.

If you didn't request this code, please ignore this email.
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_email
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    timeout = max(5, int(settings.SMTP_TIMEOUT_SECONDS or 30))
    user = (settings.SMTP_USER or "").strip()
    password = settings.SMTP_PASSWORD or ""
    host = settings.SMTP_HOST
    port = int(settings.SMTP_PORT or (465 if settings.SMTP_USE_SSL else 587))

    try:
        if settings.SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
                if user or password:
                    smtp.login(user, password)
                smtp.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if settings.SMTP_USE_TLS:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if user or password:
                    smtp.login(user, password)
                smtp.sendmail(from_email, [to_email], msg.as_string())

        logger.info(f"OTP email sent to {to_email}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP auth failed: {e}")
        raise SmtpSendError(f"SMTP authentication failed: {e}") from e
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending OTP: {e}")
        raise SmtpSendError(f"SMTP error: {e}") from e
    except OSError as e:
        logger.error(f"Could not reach mail server: {e}")
        raise SmtpSendError(f"Could not reach mail server: {e}") from e
