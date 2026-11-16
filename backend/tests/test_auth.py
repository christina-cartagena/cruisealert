"""Auth service tests: password hashing + JWT round-trips (no DB required)."""
import pytest
from fastapi import HTTPException

from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("hunter2-correct-horse")
        assert hashed != "hunter2-correct-horse"
        assert hashed.startswith("$2")  # bcrypt prefix

    def test_verify_correct_password(self):
        hashed = hash_password("s3cret-password")
        assert verify_password("s3cret-password", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("s3cret-password")
        assert verify_password("wrong-password", hashed) is False

    def test_distinct_hashes_for_same_password(self):
        assert hash_password("abc12345") != hash_password("abc12345")


class TestJwt:
    def test_access_token_round_trip(self):
        token = create_access_token("user-123", "pro")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["tier"] == "pro"
        assert payload["type"] == "access"

    def test_refresh_token_round_trip(self):
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.real.token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = create_access_token("user-789", "free")
        with pytest.raises(HTTPException):
            decode_token(token + "tampered")
