"""Symmetric encryption service for storing API credentials securely.

Uses Fernet (AES-128-CBC) from the `cryptography` library.
The encryption key is derived from the application's SECRET_KEY.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a 32-byte URL-safe base64-encoded key from the app secret."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    key_source = settings.FIELD_ENCRYPTION_KEY.strip() or settings.SECRET_KEY
    return Fernet(_derive_fernet_key(key_source))


def encrypt_value(plain_text: str) -> str:
    if not plain_text:
        return ""
    return _get_fernet().encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_value(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    return _get_fernet().decrypt(cipher_text.encode("utf-8")).decode("utf-8")
