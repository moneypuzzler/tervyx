"""Credential validation helpers for external services.

These utilities keep user-facing modules free from repetitive string
sanitisation logic while providing consistent, actionable guidance when
required credentials are missing or malformed.
"""
from __future__ import annotations

from typing import Optional, Tuple


_PLACEHOLDER_VALUES = {
    "your-api-key-here",
    "your-actual-api-key",
    "paste-your-gemini-key",
    "gemini-api-key",
}


def validate_gemini_api_key(value: Optional[str]) -> Tuple[bool, Optional[str], str]:
    """Return whether *value* looks like a valid Gemini API key.

    Parameters
    ----------
    value:
        The raw value supplied by the user or environment. ``None`` or blank
        values are treated as missing credentials.

    Returns
    -------
    tuple
        ``(is_valid, cleaned_value, error_message)`` where ``cleaned_value`` is
        the stripped API key when valid. When the key is invalid, the
        ``error_message`` contains actionable guidance.
    """

    if value is None:
        return False, None, "Gemini API key not provided. Export GEMINI_API_KEY or pass --gemini-key."

    cleaned = value.strip()
    if not cleaned:
        return False, None, "Gemini API key was blank. Confirm your secret does not contain extra whitespace."

    if cleaned.lower() in _PLACEHOLDER_VALUES:
        return False, None, "Gemini API key is still set to a placeholder. Copy the key from Google AI Studio."

    if " " in cleaned:
        return False, None, "Gemini API key contains spaces. Ensure you copied it without surrounding comments."

    if not cleaned.startswith("AIza"):
        return False, cleaned, (
            "Gemini API keys from Google AI Studio currently start with 'AIza'. "
            "Verify that you copied the server API key (not the OAuth client ID)."
        )

    if len(cleaned) < 25:
        return False, cleaned, "Gemini API key looks too short. Copy the full key from the developer console."

    return True, cleaned, ""


def redact_gemini_api_key(value: Optional[str], visible: int = 4) -> str:
    """Return a redacted representation of the Gemini key for logs."""
    if not value:
        return ""

    visible = max(1, visible)
    if len(value) <= visible * 2:
        return value

    return f"{value[:visible]}…{value[-visible:]}"
