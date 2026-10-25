from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from app.auth.oidc import JWTValidator
from app.conf.settings import Settings


def _token_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_jwk = json.loads(
        RSAAlgorithm.to_jwk(private_key.public_key())
    )
    public_jwk["kid"] = "test-key"
    public_jwk["use"] = "sig"
    return private_pem, public_jwk


def _settings() -> Settings:
    return Settings(
        environment="production",
        dev_auth_enabled=False,
        oidc_issuer="https://issuer.example",
        oidc_audience="agent-api",
        oidc_jwks_url="https://issuer.example/jwks.json",
        trusted_hosts="testserver",
    )


async def test_valid_oidc_token_maps_identity() -> None:
    private_key, public_jwk = _token_material()
    claims = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "roles": ["agent:user", "agent:approver"],
        "iss": "https://issuer.example",
        "aud": "agent-api",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"keys": [public_jwk]})
    )
    client = httpx.AsyncClient(transport=transport)
    validator = JWTValidator(_settings(), http_client=client)
    identity = await validator.validate(token)
    assert identity.user_id == "user-1"
    assert identity.tenant_id == "tenant-1"
    assert "agent:approver" in identity.roles
    await client.aclose()


async def test_wrong_audience_is_rejected() -> None:
    private_key, public_jwk = _token_material()
    claims = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "roles": ["agent:user"],
        "iss": "https://issuer.example",
        "aud": "other-api",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"keys": [public_jwk]})
    )
    client = httpx.AsyncClient(transport=transport)
    validator = JWTValidator(_settings(), http_client=client)
    with pytest.raises(HTTPException) as error:
        await validator.validate(token)
    assert error.value.status_code == 401
    await client.aclose()
