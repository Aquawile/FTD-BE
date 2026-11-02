from __future__ import annotations

import os

FIREBASE_PROJECT_ID: str = os.environ.get("FIREBASE_PROJECT_ID", "ftd-2026")
# Public by design (also embedded in the web app); identifies the project, grants no access.
FIREBASE_WEB_API_KEY: str = os.environ.get("FIREBASE_WEB_API_KEY", "AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8")
FIREBASE_CREDENTIALS_PATH: str = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
FIREBASE_AUTH_ENABLED: bool = os.environ.get("FIREBASE_AUTH_ENABLED", "false").lower() == "true"


def get_firebase_config() -> dict[str, object]:
    return {
        "project_id": FIREBASE_PROJECT_ID,
        "credentials_path": FIREBASE_CREDENTIALS_PATH,
        "auth_enabled": FIREBASE_AUTH_ENABLED,
    }