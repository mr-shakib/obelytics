from uuid import uuid4
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_and_verify():
    raw = "MySecretPass123"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_round_trip():
    user_id = uuid4()
    org_id = uuid4()
    token = create_access_token(user_id, org_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["org"] == str(org_id)
    assert payload["type"] == "access"


def test_refresh_token_hash_is_deterministic():
    raw = "some-raw-token"
    h1 = hash_refresh_token(raw)
    h2 = hash_refresh_token(raw)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest
