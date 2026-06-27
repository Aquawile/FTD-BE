"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    gcp_project: str
    gce_instance_name: str
    gce_zone: str
    gcs_bucket: str
    gcs_sec_prefix: str
    sec_user_agent: str
    company_tickers_url: str
    initial_lookback_days: int
    steady_lookback_days: int
    allow_local_execution: bool
    use_bulk_submissions: bool
    max_download_gb: float
    max_ingest_gb: float
    max_retries: int = 3
    requests_per_second: float = 10.0
    error_log_filename: str = "error_log.txt"
    run_manifest_blob: str = "logs/last_successful_run.json"
    roster_manifest_blob: str = "logs/fortune500_roster.json"
    fortune_500_gcs_path: str = "config/fortune500.json"
    fortune_500_fallback_url: str = (
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
        "master/data/constituents.csv"
    )
    target_company_limit: int = 500

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> Settings:
        return cls(
            gcp_project=os.getenv("GCP_PROJECT", "ftd2026").strip(),
            gce_instance_name=os.getenv("GCE_INSTANCE_NAME", "data-ingest-vm").strip(),
            gce_zone=os.getenv("GCE_ZONE", "us-west2-a").strip(),
            gcs_bucket=os.getenv("GCS_BUCKET", "raw-data-strg").strip(),
            gcs_sec_prefix=os.getenv("GCS_SEC_PREFIX", "SEC").strip().strip("/"),
            sec_user_agent=os.getenv(
                "SEC_USER_AGENT",
                "FinanceTrackerDashboard izzybutera11@gmail.com",
            ).strip(),
            company_tickers_url=os.getenv(
                "COMPANY_TICKERS_URL",
                "https://www.sec.gov/files/company_tickers.json",
            ).strip(),
            fortune_500_gcs_path=os.getenv(
                "FORTUNE_500_GCS_PATH",
                "config/fortune500.json",
            ).strip(),
            fortune_500_fallback_url=os.getenv(
                "FORTUNE_500_FALLBACK_URL",
                "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
                "master/data/constituents.csv",
            ).strip(),
            target_company_limit=max(
                1, int(os.getenv("TARGET_COMPANY_LIMIT", "500"))
            ),
            initial_lookback_days=max(1, int(os.getenv("INITIAL_LOOKBACK_DAYS", "7"))),
            steady_lookback_days=max(1, int(os.getenv("STEADY_LOOKBACK_DAYS", "1"))),
            allow_local_execution=_env_bool("ALLOW_LOCAL_EXECUTION", False),
            use_bulk_submissions=_env_bool("USE_BULK_SUBMISSIONS", False),
            max_download_gb=_env_float("MAX_DOWNLOAD_GB", 2.0),
            max_ingest_gb=_env_float("MAX_INGEST_GB", 5.0),
        )

    def validate(self) -> None:
        missing = []
        if not self.sec_user_agent:
            missing.append("SEC_USER_AGENT")
        if not self.gcp_project:
            missing.append("GCP_PROJECT")
        if not self.gce_instance_name:
            missing.append("GCE_INSTANCE_NAME")
        if not self.gce_zone:
            missing.append("GCE_ZONE")
        if not self.company_tickers_url:
            missing.append("COMPANY_TICKERS_URL")
        if missing:
            raise ValueError(
                "Missing or invalid configuration: " + ", ".join(missing)
            )

    @property
    def min_request_interval(self) -> float:
        return 1.0 / self.requests_per_second

    @property
    def max_download_bytes(self) -> int:
        return int(self.max_download_gb * (1024 ** 3))

    @property
    def max_ingest_bytes(self) -> int:
        return int(self.max_ingest_gb * (1024 ** 3))

    def resolve_lookback_days(self, initial_run_complete: bool) -> int:
        if initial_run_complete:
            return self.steady_lookback_days
        return self.initial_lookback_days
