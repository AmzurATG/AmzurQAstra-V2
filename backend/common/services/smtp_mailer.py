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
from common.services.report_email_enrichment import RichReportEmailParts


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


def _parts_have_body(parts: RichReportEmailParts | None) -> bool:
    if not parts:
        return False
    return bool(parts.executive_summary or parts.highlights or parts.metrics)


def _executive_summary_html(text: str) -> str:
    """Escape and preserve line breaks for email HTML."""
    lines = text.splitlines() or [text]
    return "<br />\n".join(html.escape(line) for line in lines if line is not None)


def _rich_blocks_plain(parts: RichReportEmailParts) -> str:
    blocks: list[str] = []

    if parts.executive_summary:
        blocks.append(
            "Executive summary\n"
            + "-----------------\n"
            + parts.executive_summary.strip()
        )

    if parts.metrics:
        blocks.append(
            "At a glance\n"
            + "-----------\n"
            + "\n".join(f"• {m}" for m in parts.metrics)
        )

    if parts.highlights:
        blocks.append(
            "Key points\n"
            + "----------\n"
            + "\n".join(f"• {h}" for h in parts.highlights)
        )

    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n\n"


def _rich_blocks_html(parts: RichReportEmailParts) -> str:
    out: list[str] = []

    if parts.executive_summary:
        summ = parts.executive_summary.strip()
        out.append(
            '<h2 style="font-size:16px;font-weight:600;color:#111827;margin:1.25em 0 0.5em;">'
            "Executive summary</h2>"
            '<div style="border-left:4px solid #6366f1;padding:12px 16px;background:#f9fafb;'
            'margin:0 0 1em 0;font-size:14px;line-height:1.55;color:#374151;">'
            f"{_executive_summary_html(summ)}</div>"
        )

    if parts.metrics:
        items = "".join(f"<li>{html.escape(m)}</li>" for m in parts.metrics)
        out.append(
            '<h2 style="font-size:16px;font-weight:600;color:#111827;margin:1.25em 0 0.5em;">'
            "At a glance</h2>"
            f'<ul style="margin:0 0 1em 1.1em;padding:0;line-height:1.5;color:#374151;">{items}</ul>'
        )

    if parts.highlights:
        items = "".join(f"<li>{html.escape(h)}</li>" for h in parts.highlights)
        out.append(
            '<h2 style="font-size:16px;font-weight:600;color:#111827;margin:1.25em 0 0.5em;">'
            "Key points</h2>"
            f'<ul style="margin:0 0 1em 1.1em;padding:0;line-height:1.5;color:#374151;">{items}</ul>'
        )

    if not out:
        return ""
    return "\n".join(out) + "\n"


def build_report_email_envelope(
    *,
    report_title_phrase: str,
    requirement_title: str | None,
    requirement_file_name: str | None,
    requirement_id: int,
    run_id: int,
    run_created_at: datetime | None,
    rich: RichReportEmailParts | None = None,
) -> Tuple[str, str, str]:
    """
    Return (subject, plain_text, html_fragment_for_body).

    report_title_phrase examples:
    - "Requirements gap analysis"
    - "Testing recommendations"

    When ``rich`` is provided and non-empty, the body includes an executive summary,
    optional metrics, and optional key-point bullets suitable for client-facing email.
    """
    app = html.escape(settings.APP_NAME or "QAstra")
    label_plain = _requirement_display_label(
        requirement_title, requirement_file_name, requirement_id
    )
    label = html.escape(label_plain)
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

    has_rich = _parts_have_body(rich)

    intro_plain = (
        f"Hello,\n\n"
        f"We are sharing the {report_title_phrase} report for the following requirement document:\n\n"
        f"  {label_plain}\n\n"
    )
    if has_rich:
        intro_plain += (
            "Below you will find a concise summary and key details from this run. "
            "The complete, print-ready report is attached as a PDF for your records.\n\n"
        )
    else:
        intro_plain += (
            "The complete report is attached as a PDF. "
            f"It reflects the requirement text and user stories in your project at the time this run was executed.\n\n"
        )

    intro_html = (
        "<p>Hello,</p>"
        f"<p>We are sharing the <strong>{phrase}</strong> report for the requirement document "
        f"<strong>{label}</strong>.</p>"
    )
    if has_rich:
        intro_html += (
            "<p>Below you will find a concise summary and key details from this run. "
            "The <strong>complete, print-ready report is attached as a PDF</strong> for your records.</p>"
        )
    else:
        intro_html += (
            "<p>The <strong>complete report is attached as a PDF</strong>. "
            f"It reflects the requirement text and user stories in your project at the time this run was executed.</p>"
        )

    ref_plain = (
        f"Reference: run #{run_id}\n"
        f"Report generated: {gen_line_plain}\n\n"
    )
    ref_html = (
        "<ul style=\"margin:0 0 1em 1.2em;padding:0;line-height:1.5;\">"
        f"<li>Reference: run <strong>#{run_id_s}</strong></li>"
        f"<li>Report generated: <strong>{html.escape(gen_line)}</strong></li>"
        "</ul>"
    )

    rich_plain = _rich_blocks_plain(rich) if rich and has_rich else ""
    rich_html = _rich_blocks_html(rich) if rich and has_rich else ""

    closing_plain = (
        f"The PDF attachment is the same formal document available for download within {settings.APP_NAME}. "
        "If you did not expect this message, you may disregard it.\n\n"
        f"Kind regards,\n{settings.APP_NAME}\n"
    )
    closing_html = (
        f"<p style=\"color:#4b5563;font-size:14px;\">The PDF attachment is the same formal document "
        f"available for download within <strong>{app}</strong>. "
        "If you did not expect this message, you may disregard it.</p>"
        f"<p style=\"margin-top:1.5em;\">Kind regards,<br><strong>{app}</strong></p>"
    )

    text_body = intro_plain + ref_plain + rich_plain + closing_plain

    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#1a1a1a;">
{intro_html}
{ref_html}
{rich_html}
{closing_html}
</body></html>"""

    return subject, text_body, html_body


def build_integrity_check_report_email_envelope(
    *,
    run_id: str,
    project_id: int,
    app_url: str | None,
    run_completed_at: datetime | None,
    rich: RichReportEmailParts | None = None,
) -> Tuple[str, str, str]:
    """
    Return (subject, plain_text, html) for BIC / integrity check PDF emails.

    When ``rich`` is provided with content, the body includes the run narrative summary
    and step / outcome metrics ahead of the closing lines.
    """
    app = html.escape(settings.APP_NAME or "QAstra")
    rid = html.escape((run_id or "").strip() or "unknown")
    url_plain = (app_url or "").strip() or "—"
    url_h = html.escape(url_plain)

    if run_completed_at is not None:
        if run_completed_at.tzinfo is None:
            dt_utc = run_completed_at.replace(tzinfo=timezone.utc)
        else:
            dt_utc = run_completed_at.astimezone(timezone.utc)
        gen_line = dt_utc.strftime("%Y-%m-%d %H:%M UTC")
        gen_line_plain = gen_line
    else:
        gen_line = "See timestamp in your QAstra workspace"
        gen_line_plain = gen_line

    if len(run_id) > 8:
        subject = (
            f"{settings.APP_NAME} — Build integrity check report "
            f"(project #{project_id}, run {run_id[:8]}…)"
        )
    else:
        subject = (
            f"{settings.APP_NAME} — Build integrity check report "
            f"(project #{project_id}, run {run_id})"
        )

    has_rich = _parts_have_body(rich)

    intro_plain = (
        "Hello,\n\n"
        "We are sharing the Build integrity check (BIC) report for your QAstra project.\n\n"
    )
    if has_rich:
        intro_plain += (
            "Below is a concise summary of the run and key metrics. "
            "The complete report is attached as a PDF; representative screenshots from the run "
            "may be included as additional attachments when available.\n\n"
        )
    else:
        intro_plain += (
            "The complete report is attached as a PDF. "
            "Representative screenshots from the run may be included as additional attachments when available.\n\n"
        )

    intro_html = (
        "<p>Hello,</p>"
        "<p>We are sharing the <strong>Build integrity check</strong> report for your QAstra project.</p>"
    )
    if has_rich:
        intro_html += (
            "<p>Below is a concise summary of the run and key metrics. "
            "The <strong>complete report is attached as a PDF</strong>; representative screenshots "
            "from the run may be included as additional attachments when available.</p>"
        )
    else:
        intro_html += (
            "<p>The <strong>complete report is attached as a PDF</strong>. "
            "Representative screenshots from the run may be included as additional attachments when available.</p>"
        )

    ref_plain = (
        f"Project id: {project_id}\n"
        f"Run id: {run_id}\n"
        f"Application URL: {url_plain}\n"
        f"Run completed: {gen_line_plain}\n\n"
    )
    ref_html = (
        "<ul style=\"margin:0 0 1em 1.2em;padding:0;line-height:1.5;\">"
        f"<li>Project id: <strong>{project_id}</strong></li>"
        f"<li>Run id: <strong>{rid}</strong></li>"
        f"<li>Application URL: <strong>{url_h}</strong></li>"
        f"<li>Run completed: <strong>{html.escape(gen_line)}</strong></li>"
        "</ul>"
    )

    rich_plain = _rich_blocks_plain(rich) if rich and has_rich else ""
    rich_html = _rich_blocks_html(rich) if rich and has_rich else ""

    closing_plain = (
        f"The PDF attachment matches the report you can download from the Build Integrity Check page "
        f"in {settings.APP_NAME}. If you did not expect this message, you may disregard it.\n\n"
        f"Kind regards,\n{settings.APP_NAME}\n"
    )
    closing_html = (
        "<p style=\"color:#4b5563;font-size:14px;\">The PDF attachment matches the report you can download "
        f"from the Build Integrity Check page in <strong>{app}</strong>. "
        "If you did not expect this message, you may disregard it.</p>"
        f"<p style=\"margin-top:1.5em;\">Kind regards,<br><strong>{app}</strong></p>"
    )

    text_body = intro_plain + ref_plain + rich_plain + closing_plain

    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#1a1a1a;">
{intro_html}
{ref_html}
{rich_html}
{closing_html}
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


def _safe_image_filename(name: str) -> str:
    """Sanitise a screenshot filename for use as a MIME attachment name."""
    out = []
    for c in name:
        if 32 <= ord(c) < 127 and c not in '\\/"*:?<>|':
            out.append(c)
        else:
            out.append("_")
    s = "".join(out).strip("._") or "screenshot.png"
    return s


def send_email_with_pdf_attachment(
    *,
    to_addr: str,
    subject: str,
    text_body: str,
    html_body: str,
    pdf_bytes: bytes,
    attachment_filename: str,
    screenshot_attachments: list[tuple[bytes, str]] | None = None,
) -> None:
    """
    Send an email with a PDF report as the primary attachment.

    Args:
        screenshot_attachments: Optional list of ``(image_bytes, filename)``
            tuples that will be appended as inline image attachments after
            the PDF.  Filenames should already be sanitised or will be
            sanitised internally.
    """
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
    pdf_part.add_header("Content-Disposition", "attachment", filename=safe_name)
    msg.attach(pdf_part)

    for img_bytes, img_filename in (screenshot_attachments or []):
        safe_img = _safe_image_filename(img_filename)
        img_part = MIMEApplication(img_bytes, _subtype="octet-stream")
        img_part.add_header("Content-Disposition", "attachment", filename=safe_img)
        msg.attach(img_part)

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
