"""
Security utilities for authentication and encryption
"""
from datetime import datetime, timedelta
from typing import Optional, List
import secrets
import bcrypt
from jose import jwt
from cryptography.fernet import Fernet
import base64
import hashlib

from config import settings

# Stable nonce from settings (survives restarts). Falls back to a random
# per-process nonce when JWT_NONCE is not configured in .env.
BOOT_NONCE: str = settings.JWT_NONCE or secrets.token_hex(16)


# =============================================================================
# ENCRYPTION UTILITIES
# =============================================================================

# Fields in integration config that should be encrypted
SENSITIVE_CONFIG_FIELDS = [
    'api_token', 'personal_access_token', 'access_token', 'token',
    'password', 'secret', 'api_key', 'webhook_url', 'bot_token'
]


def _get_fernet() -> Fernet:
    """
    Get a Fernet instance using the encryption key from settings.
    The key is derived from ENCRYPTION_KEY using SHA256 to ensure 32 bytes.
    """
    # Derive a 32-byte key from the settings key using SHA256
    key_bytes = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    # Fernet requires base64-encoded 32-byte key
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value.
    Returns the encrypted value as a base64 string prefixed with 'enc:'.
    """
    if not value:
        return value
    
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return f"enc:{encrypted.decode()}"


def decrypt_value(value: str) -> str:
    """
    Decrypt an encrypted string value.
    If value doesn't start with 'enc:', returns as-is (not encrypted).
    """
    if not value or not isinstance(value, str):
        return value
    
    if not value.startswith("enc:"):
        # Not encrypted, return as-is
        return value
    
    try:
        fernet = _get_fernet()
        encrypted_data = value[4:]  # Remove 'enc:' prefix
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception:
        # If decryption fails, return original (might be corrupted)
        return value


def encrypt_config(config: dict) -> dict:
    """
    Encrypt sensitive fields in an integration config dict.
    Only encrypts fields listed in SENSITIVE_CONFIG_FIELDS.
    """
    if not config:
        return config
    
    encrypted_config = {}
    for key, value in config.items():
        if key.lower() in SENSITIVE_CONFIG_FIELDS and value and isinstance(value, str):
            # Only encrypt if not already encrypted
            if not value.startswith("enc:"):
                encrypted_config[key] = encrypt_value(value)
            else:
                encrypted_config[key] = value
        else:
            encrypted_config[key] = value
    
    return encrypted_config


def decrypt_config(config: dict) -> dict:
    """
    Decrypt sensitive fields in an integration config dict.
    """
    if not config:
        return config
    
    decrypted_config = {}
    for key, value in config.items():
        if isinstance(value, str) and value.startswith("enc:"):
            decrypted_config[key] = decrypt_value(value)
        else:
            decrypted_config[key] = value
    
    return decrypted_config


# =============================================================================
# PASSWORD HASHING
# =============================================================================


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.utcnow()
    to_encode = {"sub": subject, "exp": expire, "iat": now, "type": "access", "nonce": BOOT_NONCE}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.utcnow()
    to_encode = {"sub": subject, "exp": expire, "iat": now, "type": "refresh", "nonce": BOOT_NONCE}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
