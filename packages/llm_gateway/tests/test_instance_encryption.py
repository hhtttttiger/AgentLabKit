from __future__ import annotations

import base64

import pytest

from llm_gateway.model_catalog.instance_encryption import (
    decrypt_instance_api_key,
    encrypt_instance_api_key,
    parse_encryption_key,
)


class TestInstanceEncryption:
    def test_round_trip_matches_dotnet_payload_shape(self):
        key = bytes.fromhex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
        cipher_text = encrypt_instance_api_key("secret-api-key", key)

        assert decrypt_instance_api_key(cipher_text, key) == "secret-api-key"

    def test_parse_encryption_key_accepts_base64(self):
        raw_key = bytes(range(32))
        encoded_key = base64.b64encode(raw_key).decode("ascii")

        assert parse_encryption_key(encoded_key) == raw_key

    def test_parse_encryption_key_rejects_invalid_lengths(self):
        encoded_key = base64.b64encode(b"short").decode("ascii")
        with pytest.raises(ValueError, match="16, 24, or 32 bytes"):
            parse_encryption_key(encoded_key)

    def test_decrypt_returns_none_for_invalid_cipher_text(self):
        key = bytes(range(32))
        assert decrypt_instance_api_key("not-base64", key) is None
