"""SEC EDGAR HTTP client with compliance headers, throttling, and retries."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

from src.config import Settings
from src.error_logger import ErrorLogger


class SecClient:
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

    XBRL_PATH_FRAGMENTS = (
        "xbrl/companyfacts",
        "xbrl/companyconcept",
    )

    def __init__(self, settings: Settings, error_logger: ErrorLogger) -> None:
        self.settings = settings
        self.error_logger = error_logger
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": settings.sec_user_agent,
                "Accept-Encoding": "gzip, deflate",
            }
        )
        self._last_request_at = 0.0
        self.bytes_transferred = 0

    def _throttle(self) -> None:
        """Enforce max requests_per_second between any two HTTP calls."""
        elapsed = time.monotonic() - self._last_request_at
        wait = self.settings.min_request_interval - elapsed
        if wait > 0:
            time.sleep(wait)

    def _mark_request_sent(self) -> None:
        self._last_request_at = time.monotonic()

    def _paced_wait_before_attempt(self, attempt: int) -> None:
        """Wait before an HTTP attempt — backoff on retries, then rate-limit slot."""
        if attempt > 1:
            # Exponential backoff between retries; never shorter than the SEC rate floor.
            retry_delay = max(2 ** (attempt - 1), self.settings.min_request_interval)
            time.sleep(retry_delay)
        self._throttle()

    def _retry_after_seconds(self, response: requests.Response | None) -> float | None:
        if response is None or response.status_code != 429:
            return None
        header = response.headers.get("Retry-After")
        if header is None:
            return None
        try:
            return max(float(header), self.settings.min_request_interval)
        except ValueError:
            return None

    def _track_bytes(self, count: int) -> bool:
        self.bytes_transferred += count
        return self.bytes_transferred <= self.settings.max_ingest_bytes

    def _request(
        self,
        method: str,
        url: str,
        *,
        cik: str,
        stream: bool = False,
        timeout: int = 60,
    ) -> requests.Response | None:
        for attempt in range(1, self.settings.max_retries + 1):
            self._paced_wait_before_attempt(attempt)
            try:
                response = self._session.request(
                    method,
                    url,
                    timeout=timeout,
                    stream=stream,
                )
                self._mark_request_sent()
                if response.status_code == 200:
                    return response
                body_preview = ""
                if not stream:
                    body_preview = response.text[:500]
                self.error_logger.log_http_failure(
                    cik=cik,
                    url=url,
                    status_code=response.status_code,
                    message=body_preview,
                    attempt=attempt,
                )
                retry_after = self._retry_after_seconds(response)
                if retry_after is not None and attempt < self.settings.max_retries:
                    time.sleep(retry_after)
                    continue
            except requests.RequestException as exc:
                self._mark_request_sent()
                self.error_logger.log_http_failure(
                    cik=cik,
                    url=url,
                    status_code=None,
                    message=str(exc),
                    attempt=attempt,
                )

        return None

    def fetch_url(self, url: str, *, cik: str) -> requests.Response | None:
        response = self._request("GET", url, cik=cik)
        if response is None:
            return None
        content = response.content
        if not self._track_bytes(len(content)):
            self.error_logger.log_http_failure(
                cik=cik,
                url=url,
                status_code=None,
                message=(
                    f"Ingest byte budget exceeded ({self.settings.max_ingest_gb} GB)"
                ),
                attempt=self.settings.max_retries,
            )
            return None
        return response

    def download_to_file(
        self,
        url: str,
        destination: Path,
        *,
        cik: str,
        max_bytes: int,
        timeout: int = 600,
    ) -> bool:
        for attempt in range(1, self.settings.max_retries + 1):
            self._paced_wait_before_attempt(attempt)
            try:
                with self._session.get(url, stream=True, timeout=timeout) as response:
                    self._mark_request_sent()
                    if response.status_code != 200:
                        self.error_logger.log_http_failure(
                            cik=cik,
                            url=url,
                            status_code=response.status_code,
                            message="Bulk archive download failed",
                            attempt=attempt,
                        )
                        retry_after = self._retry_after_seconds(response)
                        if retry_after is not None and attempt < self.settings.max_retries:
                            time.sleep(retry_after)
                        continue

                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > max_bytes:
                        self.error_logger.log_http_failure(
                            cik=cik,
                            url=url,
                            status_code=None,
                            message=(
                                f"Archive size {content_length} bytes exceeds limit "
                                f"{max_bytes} bytes"
                            ),
                            attempt=attempt,
                        )
                        return False

                    total = 0
                    with destination.open("wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if not chunk:
                                continue
                            total += len(chunk)
                            if total > max_bytes:
                                self.error_logger.log_http_failure(
                                    cik=cik,
                                    url=url,
                                    status_code=None,
                                    message=(
                                        f"Download exceeded {max_bytes} bytes; "
                                        "terminating to protect free-tier credits"
                                    ),
                                    attempt=attempt,
                                )
                                return False
                            handle.write(chunk)
                            if not self._track_bytes(len(chunk)):
                                return False

                return True
            except requests.RequestException as exc:
                self._mark_request_sent()
                self.error_logger.log_http_failure(
                    cik=cik,
                    url=url,
                    status_code=None,
                    message=str(exc),
                    attempt=attempt,
                )

        return False

    @staticmethod
    def normalize_cik(cik: str) -> str:
        digits = "".join(ch for ch in cik if ch.isdigit())
        if not digits:
            raise ValueError(f"Invalid CIK: {cik!r}")
        return digits.zfill(10)

    @staticmethod
    def cik_for_url(cik: str) -> str:
        return str(int(SecClient.normalize_cik(cik)))

    def get_submissions(self, cik: str) -> dict[str, Any] | None:
        normalized = self.normalize_cik(cik)
        url = self.SUBMISSIONS_URL.format(cik=normalized)
        response = self.fetch_url(url, cik=normalized)
        if response is None:
            return None
        return response.json()

    def download_document(self, cik: str, accession_number: str, document: str) -> bytes | None:
        normalized = self.normalize_cik(cik)
        accession_path = accession_number.replace("-", "")
        cik_path = self.cik_for_url(normalized)
        url = f"{self.ARCHIVES_BASE}/{cik_path}/{accession_path}/{document}"

        if self._is_xbrl_url(url) or self._is_xbrl_filename(document):
            return None

        response = self.fetch_url(url, cik=normalized)
        if response is None:
            return None
        return response.content

    @classmethod
    def _is_xbrl_url(cls, url: str) -> bool:
        lowered = url.lower()
        return any(fragment in lowered for fragment in cls.XBRL_PATH_FRAGMENTS)

    @staticmethod
    def _is_xbrl_filename(filename: str) -> bool:
        lowered = filename.lower()
        return lowered.endswith(".xml") or lowered.endswith("-xbrl.htm")
