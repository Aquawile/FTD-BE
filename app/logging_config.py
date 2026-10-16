"""Logging configuration for structured audit logging.

Configures:
1. Root logger — application logging (stdout, standard format)
2. Audit logger — SEC proxy access, structured JSON to file and stdout

File handler writes to /var/log/ftd-api/sec-content-proxy.log
(if directory does not exist, falls back to stdout-only).
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format audit log records as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "user_key"):
            entry["user_key"] = record.user_key
        if hasattr(record, "method"):
            entry["method"] = record.method
        if hasattr(record, "path"):
            entry["path"] = record.path
        if hasattr(record, "status"):
            entry["status"] = record.status
        if hasattr(record, "duration_ms"):
            entry["duration_ms"] = record.duration_ms
        if hasattr(record, "details"):
            entry["details"] = record.details
        return json.dumps(entry)


def setup_logging() -> None:
    """Configure root and audit loggers."""

    # Root logger — stdout, standard format
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    root_logger.addHandler(root_handler)

    # Audit logger — structured JSON to file and stdout
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    json_formatter = JSONFormatter()

    # File handler (best-effort)
    log_dir = "/var/log/ftd-api"
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "sec-content-proxy.log"))
        file_handler.setFormatter(json_formatter)
        audit_logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # Fallback: stdout only if we can't write to file
        pass

    # Stdout handler for audit logger
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(json_formatter)
    audit_logger.addHandler(stdout_handler)
