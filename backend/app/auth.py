"""Keycloak access-token verification for protected API routes."""
from __future__ import annotations

from typing import Any, TypedDict

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    MissingRequiredClaimError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)

from .config import get_settings


class AuthenticatedUser(TypedDict):
    user_id: str
    email: str | None
    preferred_username: str | None


_bearer = HTTPBearer(auto_error=False)
_settings = get_settings()
_jwks = PyJWKClient(_settings.keycloak_jwks_url, cache_keys=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        signing_key = _jwks.get_signing_key_from_jwt(credentials.credentials)
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=_settings.keycloak_audience,
            issuer=_settings.keycloak_issuer,
            # exp, issuer, audience, and subject are required for this API.
            # iat is useful metadata but is not needed to validate the token.
            options={"require": ["exp", "sub"]},
        )
        user_id = claims.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise jwt.InvalidTokenError("Token subject is missing.")
        return {
            "user_id": user_id,
            "email": claims.get("email"),
            "preferred_username": claims.get("preferred_username"),
        }
    except InvalidAudienceError as exc:
        raise HTTPException(
            status_code=401,
            detail="Sign-in token is missing the Querydesk API audience. Check the Keycloak API audience client scope.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidIssuerError as exc:
        raise HTTPException(
            status_code=401,
            detail="Sign-in issuer does not match the API configuration. Check the Keycloak public URL.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="The sign-in service is temporarily unavailable. Check API-to-Keycloak connectivity.",
        ) from exc
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Your sign-in token has expired. Sign out and sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except MissingRequiredClaimError as exc:
        claim = exc.claim
        # Report claim names only. Never include token contents or claim values
        # in an API response; the names help distinguish token-profile issues.
        try:
            unverified_claims = jwt.decode(
                credentials.credentials,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
            claim_names = ", ".join(sorted(unverified_claims.keys())) or "none"
        except Exception:
            claim_names = "unavailable"
        raise HTTPException(
            status_code=401,
            detail=f"Keycloak token is missing required claim '{claim}'. Token claim names: {claim_names}. Keycloak user access tokens normally include 'sub'; check that the API receives the browser's access token for the Querydesk realm.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="The token signature does not match the current Keycloak signing key. Restart the API after confirming it uses the correct realm JWKS URL.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except PyJWKClientError as exc:
        raise HTTPException(
            status_code=401,
            detail="Keycloak did not provide a signing key matching this token. Check that the API JWKS URL points to the same realm that issued the token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Keycloak rejected the sign-in token ({type(exc).__name__}). Sign out and sign in again; if it persists, check API and Keycloak realm configuration.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
