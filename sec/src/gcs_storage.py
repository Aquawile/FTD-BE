"""Upload SEC filing artifacts to Google Cloud Storage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage

from src.config import Settings
from src.filing_fetcher import EightKFiling


class GcsStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = storage.Client(project=settings.gcp_project or None)
        self._bucket = self._client.bucket(settings.gcs_bucket)

    def _object_path(self, relative_path: str) -> str:
        return f"{self.settings.gcs_sec_prefix}/{relative_path.lstrip('/')}"

    def filing_exists(self, filing: EightKFiling) -> bool:
        blob = self._bucket.blob(self._object_path(filing.blob_name))
        return blob.exists()

    def upload_filing(self, filing: EightKFiling, content: bytes) -> str:
        object_name = self._object_path(filing.blob_name)
        blob = self._bucket.blob(object_name)
        blob.upload_from_string(content)
        return f"gs://{self.settings.gcs_bucket}/{object_name}"

    def upload_metadata(self, filing: EightKFiling) -> str:
        metadata = (
            f"cik={filing.cik}\n"
            f"accession_number={filing.accession_number}\n"
            f"filing_date={filing.filing_date.isoformat()}\n"
            f"form={filing.form}\n"
            f"primary_document={filing.primary_document}\n"
        )
        object_name = self._object_path(f"{filing.gcs_folder_name}/metadata.txt")
        blob = self._bucket.blob(object_name)
        blob.upload_from_string(metadata, content_type="text/plain")
        return f"gs://{self.settings.gcs_bucket}/{object_name}"

    def download_config_blob(self, relative_path: str) -> bytes | None:
        object_name = self._object_path(relative_path)
        blob = self._bucket.blob(object_name)
        if not blob.exists():
            return None
        return blob.download_as_bytes()

    def upload_config_blob(
        self,
        relative_path: str,
        content: bytes,
        *,
        content_type: str = "application/json",
    ) -> str:
        object_name = self._object_path(relative_path)
        blob = self._bucket.blob(object_name)
        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{self.settings.gcs_bucket}/{object_name}"

    def load_roster_manifest(self) -> set[str] | None:
        blob = self._bucket.blob(self._object_path(self.settings.roster_manifest_blob))
        if not blob.exists():
            return None
        payload = json.loads(blob.download_as_text(encoding="utf-8"))
        tickers = payload.get("tickers", [])
        return {str(ticker).upper() for ticker in tickers}

    def save_roster_manifest(self, tickers: list[str]) -> str:
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tickers": tickers,
        }
        object_name = self._object_path(self.settings.roster_manifest_blob)
        blob = self._bucket.blob(object_name)
        blob.upload_from_string(
            json.dumps(payload, indent=2),
            content_type="application/json",
        )
        return f"gs://{self.settings.gcs_bucket}/{object_name}"

    def upload_error_log(self, local_log_path: Path) -> str | None:
        if not local_log_path.exists() or local_log_path.stat().st_size == 0:
            return None
        object_name = self._object_path(f"logs/{local_log_path.name}")
        blob = self._bucket.blob(object_name)
        blob.upload_from_filename(str(local_log_path), content_type="text/plain")
        return f"gs://{self.settings.gcs_bucket}/{object_name}"

    def has_completed_initial_run(self) -> bool:
        blob = self._bucket.blob(self._object_path(self.settings.run_manifest_blob))
        return blob.exists()

    def mark_initial_run_complete(self, *, uploaded: int, skipped: int) -> str:
        payload = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "uploaded": uploaded,
            "skipped_existing": skipped,
        }
        object_name = self._object_path(self.settings.run_manifest_blob)
        blob = self._bucket.blob(object_name)
        blob.upload_from_string(
            json.dumps(payload, indent=2),
            content_type="application/json",
        )
        return f"gs://{self.settings.gcs_bucket}/{object_name}"
