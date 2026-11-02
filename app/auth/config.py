from __future__ import annotations

import os

BCRYPT_ROUNDS: int = int(os.environ.get("BCRYPT_ROUNDS", "12"))
