"""
audit_redaction.py — PII and secret redaction helper for audit before/after.

C-05: Design decision D7.
    Before persisting before/after JSONB fields, replace values for known
    sensitive keys with "[REDACTED]".  Applied recursively on nested dicts
    so that PII and secrets are NEVER stored in the audit trail in plain text.

Sensitive key list (extensible):
    password, cbu, dni, alias_cbu, token, secret, hash

Case-insensitive key comparison so that 'Password', 'PASSWORD', etc. are
also redacted.
"""
from typing import Any, Dict, Optional, Set


# ---------------------------------------------------------------------------
# Sensitive key catalog (task 6.4: extracted to a constant)
# ---------------------------------------------------------------------------

SENSITIVE_KEYS: Set[str] = {
    "password",
    "cbu",
    "dni",
    "alias_cbu",
    "token",
    "secret",
    "hash",
}


# ---------------------------------------------------------------------------
# redact_pii — recursive dict sanitiser
# ---------------------------------------------------------------------------

def redact_pii(
    data: Optional[Dict[str, Any]],
    *,
    sensitive_keys: Set[str] = SENSITIVE_KEYS,
) -> Optional[Dict[str, Any]]:
    """
    Recursively redact values of sensitive keys in *data*.

    Returns None if *data* is None (passthrough).
    Returns a new dict with sensitive values replaced by "[REDACTED]".

    The original dict is NOT mutated.

    Rules:
    - Key comparison is case-insensitive.
    - Only dict values are recursed into.
    - Non-dict values (lists, scalars) for sensitive keys are fully replaced.
    - Non-sensitive list items are left as-is (no list recursion needed for
      current threat model; can be extended if required).

    Examples::

        redact_pii({"password": "secret123"})
        # → {"password": "[REDACTED]"}

        redact_pii({"user": {"cbu": "0000111122223333444455556666"}})
        # → {"user": {"cbu": "[REDACTED]"}}

        redact_pii(None)
        # → None
    """
    if data is None:
        return None

    result: Dict[str, Any] = {}
    lower_sensitive = {k.lower() for k in sensitive_keys}

    for key, value in data.items():
        if key.lower() in lower_sensitive:
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = redact_pii(value, sensitive_keys=sensitive_keys)
        else:
            result[key] = value

    return result
