"""AES-GCM encryption utilities for sensitive data (e.g. API keys).

Uses AES-256-GCM with random 12-byte nonce. The key must be base64-encoded
and decode to 16, 24, or 32 bytes (AES-128/192/256).

Usage:
    from alkit_infra.encryption import encrypt_text, decrypt_text, parse_key

    key = parse_key(base64_key)
    cipher = encrypt_text("my-secret", key)
    plain = decrypt_text(cipher, key)
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_BYTES = 12
_TAG_BYTES = 16


def parse_key(encryption_key: str | None) -> bytes | None:
    """Parse a base64-encoded encryption key. Returns None if empty."""
    if not encryption_key:
        return None
    key = base64.b64decode(encryption_key)
    if len(key) not in {16, 24, 32}:
        raise ValueError(
            f"Encryption key must decode to 16, 24, or 32 bytes; got {len(key)} bytes."
        )
    return key


def encrypt_text(plain_text: str, key: bytes) -> str:
    """Encrypt plaintext string with AES-GCM. Returns base64-encoded ciphertext."""
    if not plain_text:
        return ""
    nonce = os.urandom(_NONCE_BYTES)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
    ciphertext = ciphertext_with_tag[:-_TAG_BYTES]
    tag = ciphertext_with_tag[-_TAG_BYTES:]
    return base64.b64encode(nonce + tag + ciphertext).decode("ascii")


def decrypt_text(cipher_text: str | None, key: bytes) -> str | None:
    """Decrypt AES-GCM ciphertext. Returns None if input is empty or decryption fails."""
    if not cipher_text:
        return None
    try:
        payload = base64.b64decode(cipher_text)
        if len(payload) < _NONCE_BYTES + _TAG_BYTES:
            return None
        nonce = payload[:_NONCE_BYTES]
        tag = payload[_NONCE_BYTES:_NONCE_BYTES + _TAG_BYTES]
        ciphertext = payload[_NONCE_BYTES + _TAG_BYTES:]
        aesgcm = AESGCM(key)
        plain_text = aesgcm.decrypt(nonce, ciphertext + tag, None)
        return plain_text.decode("utf-8")
    except Exception:
        return None
