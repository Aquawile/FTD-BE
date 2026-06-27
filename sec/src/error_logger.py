"""Local error log writer for failed SEC requests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


class ErrorLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._lock = Lock()

    def log_http_failure(
        self,
        *,
        cik: str,
        url: str,
        status_code: int | None,
        message: str,
        attempt: int,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        status = status_code if status_code is not None else "N/A"
        line = (
            f"[{timestamp}] CIK={cik} HTTP={status} "
            f"attempt={attempt} url={url} error={message.strip()}\n"
        )
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def has_entries(self) -> bool:
        return self.log_path.exists() and self.log_path.stat().st_size > 0
