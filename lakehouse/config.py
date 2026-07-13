"""Lakehouse staging configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.config import Settings


@dataclass(frozen=True)
class LakehouseSettings:
    """Settings for the lakehouse staging pipeline."""

    project_root: Path
    gcs_bucket: str = "raw-data-strg"
    lakehouse_gcs_prefix: str = "lakehouse"
    staging_path: str = "lakehouse/staging"
    catalog_path: str = "lakehouse/catalog"
    bq_dataset: str = "lakehouse"
    target_company_limit: int = 500

    # Reuse underlying SEC settings for auth and roster loading.
    _sec_settings: Settings = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_sec_settings",
            Settings.from_env(self.project_root),
        )

    @property
    def gcs_staging_prefix(self) -> str:
        return f"{self.lakehouse_gcs_prefix}/staging"

    @property
    def sec_settings(self) -> Settings:
        return object.__getattribute__(self, "_sec_settings")

    @classmethod
    def from_project_root(cls, project_root: Path | str) -> LakehouseSettings:
        return cls(project_root=Path(project_root).resolve())
