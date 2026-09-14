from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass



PASSWORD_SCHEME = "pbkdf2_sha256"
DEFAULT_PBKDF2_ITERATIONS = 390_000
ADMIN_SESSION_KEY = "altitude_admin_identity"


@dataclass(frozen=True)
class AdminIdentity:
    """Authenticated administrator stored in the Streamlit session."""

    username: str


def _encode_base64(value: bytes) -> str:
    """Encode bytes for safe storage in an environment variable."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_base64(value: str) -> bytes:
    """Decode URL-safe base64 values with optional missing padding."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_password_hash(
    password: str,
    *,
    iterations: int = DEFAULT_PBKDF2_ITERATIONS,
) -> str:
    """
    Create a salted PBKDF2 password hash for ALTITUDE_ADMIN_PASSWORD_HASH.

    The plaintext password is never stored by the application.
    """
    if len(password) < 12:
        raise ValueError("The administrator password must be at least 12 characters.")

    if iterations < 200_000:
        raise ValueError("PBKDF2 iterations must be at least 200,000.")

    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return "$".join(
        (
            PASSWORD_SCHEME,
            str(iterations),
            _encode_base64(salt),
            _encode_base64(derived_key),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password against an Altitude PBKDF2 hash."""
    try:
        scheme, iterations_text, salt_text, expected_text = encoded_hash.split(
            "$",
            maxsplit=3,
        )
        iterations = int(iterations_text)
        salt = _decode_base64(salt_text)
        expected = _decode_base64(expected_text)
    except (TypeError, ValueError):
        return False

    if scheme != PASSWORD_SCHEME or iterations < 200_000:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return hmac.compare_digest(candidate, expected)


def get_configured_admin_username() -> str:
    """Return the configured administrator username."""
    return os.getenv("ALTITUDE_ADMIN_USERNAME", "techhelp").strip() or "techhelp"


def get_admin_auth_fingerprint() -> str:
    """Return a non-secret fingerprint that invalidates stale login cookies."""
    configured_username = get_configured_admin_username().casefold()
    encoded_hash = os.getenv("ALTITUDE_ADMIN_PASSWORD_HASH", "").strip()
    session_version = os.getenv("ALTITUDE_ADMIN_SESSION_VERSION", "1").strip() or "1"
    material = f"{configured_username}\0{encoded_hash}\0{session_version}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def get_admin_configuration_error() -> str | None:
    """Return a user-safe setup error when authentication is not configured."""
    encoded_hash = os.getenv("ALTITUDE_ADMIN_PASSWORD_HASH", "").strip()

    if not encoded_hash:
        return (
            "Administrator authentication has not been configured. "
            "Generate a password hash and add ALTITUDE_ADMIN_PASSWORD_HASH "
            "to the project .env file."
        )

    if not encoded_hash.startswith(f"{PASSWORD_SCHEME}$"):
        return (
            "ALTITUDE_ADMIN_PASSWORD_HASH is not a supported Altitude "
            "PBKDF2 password hash."
        )

    return None


def authenticate_admin(username: str, password: str) -> bool:
    """Validate administrator credentials from environment configuration."""
    configured_username = get_configured_admin_username()
    encoded_hash = os.getenv("ALTITUDE_ADMIN_PASSWORD_HASH", "").strip()

    if not encoded_hash:
        return False

    username_matches = hmac.compare_digest(
        username.strip().casefold(),
        configured_username.casefold(),
    )

    # Always run password verification when a hash exists so timing does not
    # reveal whether the username was correct.
    password_matches = verify_password(password, encoded_hash)

    return username_matches and password_matches


def set_admin_authenticated(username: str) -> None:
    """Mark the current Streamlit browser session as authenticated."""
    import streamlit as st

    st.session_state[ADMIN_SESSION_KEY] = {
        "username": username.strip(),
    }


def get_admin_identity() -> AdminIdentity | None:
    """Return the current authenticated identity, if present."""
    import streamlit as st

    raw_identity = st.session_state.get(ADMIN_SESSION_KEY)

    if not isinstance(raw_identity, dict):
        return None

    username = str(raw_identity.get("username", "")).strip()

    if not username:
        return None

    return AdminIdentity(username=username)


def is_admin_authenticated() -> bool:
    """Return whether this Streamlit browser session is authenticated."""
    return get_admin_identity() is not None


def logout_admin() -> None:
    """Clear administrator authentication and dashboard state."""
    import streamlit as st

    st.session_state.pop(ADMIN_SESSION_KEY, None)
    st.session_state.pop("admin_active_section", None)
    st.session_state.pop("admin_failed_login_attempts", None)
    st.session_state.pop("admin_locked_until", None)
