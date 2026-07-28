from __future__ import annotations

from app.auth.models import normalize_email
from app.db import query_dict


def get_user_by_email(email: str) -> dict | None:
    normalized = normalize_email(email)
    rows = query_dict(
        "SELECT id, email, password_hash, is_active FROM users WHERE email = %s",
        (normalized,),
    )
    if rows:
        return rows[0]
    return None