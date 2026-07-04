"""Instance-level API key encryption (thin wrapper around alkit_infra.encryption)."""

from __future__ import annotations

from alkit_infra.encryption import decrypt_text as decrypt_instance_api_key
from alkit_infra.encryption import encrypt_text as encrypt_instance_api_key
from alkit_infra.encryption import parse_key as parse_encryption_key

__all__ = [
    "decrypt_instance_api_key",
    "encrypt_instance_api_key",
    "parse_encryption_key",
]
