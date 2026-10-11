import pytest
from jose import jwt

from core import security


def test_hash_and_verify_password_roundtrip():
    hashed = security.hash_password("MySecurePass123")
    assert hashed != "MySecurePass123"
    assert security.verify_password("MySecurePass123", hashed)
    assert not security.verify_password("WrongPassword", hashed)


def test_hash_password_rejects_empty_string():
    with pytest.raises(ValueError):
        security.hash_password("")


def test_verify_password_fails_closed_on_invalid_input():
    assert security.verify_password("", "somehash") is False
    assert security.verify_password("something", "") is False


def test_encrypt_decrypt_phone_roundtrip():
    original = "+919876543210"
    encrypted = security.encrypt_phone(original)
    assert encrypted != original
    assert security.decrypt_phone(encrypted) == original


def test_normalize_phone_requires_country_code():
    with pytest.raises(ValueError):
        security.normalize_phone("9876543210")


def test_normalize_phone_rejects_non_numeric():
    with pytest.raises(ValueError):
        security.normalize_phone("+91abc4567890")


def test_phone_lookup_hmac_is_deterministic():
    phone = "+919876543210"
    assert security.phone_lookup_hmac(phone) == security.phone_lookup_hmac(phone)


def test_phone_lookup_hmac_differs_for_different_numbers():
    assert security.phone_lookup_hmac("+919876543210") != security.phone_lookup_hmac("+919876543211")


def test_create_token_roundtrip():
    token = security.create_token({"sub": "testuser", "role": "user"})
    payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
    assert payload["sub"] == "testuser"
    assert payload["role"] == "user"
    assert "exp" in payload


def test_create_token_with_expiry_uses_custom_lifetime():
    from datetime import timedelta

    token = security.create_token_with_expiry({"sub": "testuser"}, timedelta(minutes=5))
    payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
    assert payload["sub"] == "testuser"