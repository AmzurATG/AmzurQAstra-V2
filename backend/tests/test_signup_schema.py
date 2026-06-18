"""Signup schema validation tests."""

import pytest
from pydantic import ValidationError

from common.schemas.signup import SignupRequest


def _base_payload(**overrides):
    data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "company_name": "Acme Corp",
        "email": "jane@acmecorp.com",
        "country_code": "+1",
        "phone_number": "5551234567",
        "password": "Secure1!",
        "confirm_password": "Secure1!",
        "security_questions": [
            {"question": "What city were you born in?", "answer": "Boston"},
            {"question": "What was the name of your first pet?", "answer": "Rex"},
        ],
    }
    data.update(overrides)
    return data


def test_phone_number_required():
    with pytest.raises(ValidationError) as exc:
        SignupRequest(**_base_payload(phone_number="   "))
    msg = str(exc.value).lower()
    assert "phone number is required" in msg or "7 and 15 digits" in msg


def test_phone_number_normalized():
    req = SignupRequest(**_base_payload(phone_number="(555) 123-4567"))
    assert req.phone_number == "5551234567"


def test_phone_number_length_validation():
    with pytest.raises(ValidationError) as exc:
        SignupRequest(**_base_payload(phone_number="12345"))
    assert "7 and 15 digits" in str(exc.value)
