"""SMTP delivery for formal report emails with PDF attachments."""

from __future__ import annotations

import html
import smtplib
import ssl
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, format_datetime
from datetime import datetime, timezone
from typing import Tuple

from config import settings


class SmtpSendError(Exception):
    """SMTP or configuration error surfaced to the API layer."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.EMAIL_FROM_ADDRESS)


def _from_display_name() -> str:
    return (settings.EMAIL_FROM_NAME or settings.APP_NAME or "QAstra").strip()


def _requirement_display_label(
    requirement_title: str | None,
    requirement_file_name: str | None,
    requirement_id: int,
) -> str:
    if requirement_title and requirement_title.strip():
        return requirement_title.strip()
    if requirement_file_name and requirement_file_name.strip():
        return requirement_file_name.strip()
    return f"Requirement #{requirement_id}"


def build_report_email_envelope(
    *,
    report_title_phrase: str,
    requirement_title: str | None,
    requirement_file_name: str | None,
    requirement_id: int,
    run_id: int,
    run_created_at: datetime | None,
) -> Tuple[str, str, str]:
    """
    Return (subject, plain_text, html_fragment_for_body).

    report_title_phrase examples:
    - "Requirements gap analysis"
    - "Testing recommendations"
    """
    app = html.escape(settings.APP_NAME or "QAstra")
    label = html.escape(
        _requirement_display_label(
            requirement_title, requirement_file_name, requirement_id
        )
    )
    phrase = html.escape(report_title_phrase)
    run_id_s = str(run_id)

    if run_created_at is not None:
        if run_created_at.tzinfo is None:
            dt_utc = run_created_at.replace(tzinfo=timezone.utc)
        else:
            dt_utc = run_created_at.astimezone(timezone.utc)
        gen_line = dt_utc.strftime("%Y-%m-%d %H:%M UTC")
        gen_line_plain = gen_line
    else:
        gen_line = "See timestamp in your QAstra workspace"
        gen_line_plain = gen_line

    subject = f"{settings.APP_NAME} — {report_title_phrase} report (run #{run_id})"

    text_body = f"""Dear colleague,

Please find attached the {report_title_phrase} report for the requirement document:

  { _requirement_display_label(requirement_title, requirement_file_name, requirement_id) }

Reference: run #{run_id}
Report generated: {gen_line_plain}

This report was produced by {settings.APP_NAME} from the requirement text and user stories associated with the project at the time the run was executed. The PDF attachment is the same document available for download in the application.

If you did not expect this message, you may disregard it.

Kind regards,
{settings.APP_NAME}
"""

    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#1a1a1a;">
<p>Dear colleague,</p>
<p>Please find attached the <strong>{phrase}</strong> report for the requirement document <strong>{label}</strong>.</p>
<ul style="margin:0 0 1em 1.2em;padding:0;">
<li>Reference: run <strong>#{run_id_s}</strong></li>
<li>Report generated: <strong>{html.escape(gen_line)}</strong></li>
</ul>
<p>This report was produced by <strong>{app}</strong> from the requirement text and user stories associated with the project at the time the run was executed. The PDF attachment is the same document available for download in the application.</p>
<p>If you did not expect this message, you may disregard it.</p>
<p style="margin-top:1.5em;">Kind regards,<br><strong>{app}</strong></p>
</body></html>"""

    return subject, text_body, html_body


def _safe_attachment_filename(name: str) -> str:
    out = []
    for c in name:
        if 32 <= ord(c) < 127 and c not in '\\/"*:?<>|':
            out.append(c)
        else:
            out.append("_")
    s = "".join(out).strip("._") or "report.pdf"
    if not s.lower().endswith(".pdf"):
        s += ".pdf"
    return s


def send_email_with_pdf_attachment(
    *,
    to_addr: str,
    subject: str,
    text_body: str,
    html_body: str,
    pdf_bytes: bytes,
    attachment_filename: str,
) -> None:
    if not is_smtp_configured():
        raise SmtpSendError(
            "Email is not configured (set SMTP_HOST and EMAIL_FROM_ADDRESS)."
        )

    to_addr = to_addr.strip()
    if not to_addr:
        raise SmtpSendError("Recipient address is empty.")

    from_email = settings.EMAIL_FROM_ADDRESS
    assert from_email  # guarded by is_smtp_configured
    from_name = _from_display_name()

    msg = MIMEMultipart("mixed")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_addr
    msg["Date"] = format_datetime(datetime.now(timezone.utc))

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    safe_name = _safe_attachment_filename(attachment_filename)
    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header(
        "Content-Disposition",
        "attachment",
        filename=safe_name,
    )
    msg.attach(pdf_part)

    timeout = max(5, int(settings.SMTP_TIMEOUT_SECONDS or 30))
    user = (settings.SMTP_USER or "").strip()
    password = settings.SMTP_PASSWORD or ""
    host = settings.SMTP_HOST
    assert host
    port = int(settings.SMTP_PORT or (465 if settings.SMTP_USE_SSL else 587))

    try:
        if settings.SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
                if user or password:
                    smtp.login(user, password)
                smtp.sendmail(from_email, [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if settings.SMTP_USE_TLS:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if user or password:
                    smtp.login(user, password)
                smtp.sendmail(from_email, [to_addr], msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        raise SmtpSendError(f"SMTP authentication failed: {e}") from e
    except smtplib.SMTPException as e:
        raise SmtpSendError(f"SMTP error: {e}") from e
    except OSError as e:
        raise SmtpSendError(f"Could not reach mail server: {e}") from e
