"""Add signup tables: email_verifications, security_questions, password_reset_tokens
and add signup fields to users table.

Revision ID: s1g2n3u4p5v1
Revises: m7n8o9p0q1r2
Create Date: 2026-05-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s1g2n3u4p5v1"
down_revision: Union[str, None] = "m7n8o9p0q1r2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Add signup fields to users table ---
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("users", sa.Column("company_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("country_code", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.String(20), nullable=True))

    # --- Create email_verifications table ---
    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("otp_hash", sa.String(255), nullable=False),
        sa.Column("user_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("security_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_email_verifications_expires", "email_verifications", ["expires_at"])

    # --- Create security_questions table ---
    op.create_table(
        "security_questions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("question_text", sa.String(500), nullable=False),
        sa.Column("answer_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Create password_reset_tokens table ---
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("security_questions")
    op.drop_index("idx_email_verifications_expires", table_name="email_verifications")
    op.drop_table("email_verifications")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "country_code")
    op.drop_column("users", "company_name")
    op.drop_column("users", "is_verified")
