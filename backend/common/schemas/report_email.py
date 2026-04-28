"""Request body for emailing a stored PDF report."""

from pydantic import BaseModel, EmailStr, Field


class SendReportEmailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
