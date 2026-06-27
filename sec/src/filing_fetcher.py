"""Parse SEC submissions JSON and extract eligible 8-K filings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from src.sec_client import SecClient


@dataclass(frozen=True)
class EightKFiling:
    cik: str
    accession_number: str
    filing_date: date
    primary_document: str
    form: str

    @property
    def gcs_folder_name(self) -> str:
        return (
            f"8-K/{self.cik}/{self.accession_number.replace('-', '')}"
        )

    @property
    def blob_name(self) -> str:
        return f"{self.gcs_folder_name}/{self.primary_document}"


def _parse_filing_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def extract_recent_8k_filings(
    submissions: dict,
    *,
    cik: str,
    lookback_days: int,
) -> list[EightKFiling]:
    filings = submissions.get("filings", {})
    recent = filings.get("recent")
    if not recent:
        return []

    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_documents = recent.get("primaryDocument", [])
    is_xbrl_flags = recent.get("isXBRL", [])
    is_inline_xbrl_flags = recent.get("isInlineXBRL", [])

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=lookback_days)
    results: list[EightKFiling] = []

    for index, form in enumerate(forms):
        if form != "8-K":
            continue

        primary_document = primary_documents[index]
        if SecClient._is_xbrl_filename(primary_document):
            continue

        if _flag_is_true(is_xbrl_flags, index) or _flag_is_true(is_inline_xbrl_flags, index):
            continue

        filing_date = _parse_filing_date(filing_dates[index])
        if filing_date < cutoff:
            continue

        results.append(
            EightKFiling(
                cik=SecClient.normalize_cik(cik),
                accession_number=accession_numbers[index],
                filing_date=filing_date,
                primary_document=primary_document,
                form=form,
            )
        )

    return results


def _flag_is_true(flags: list, index: int) -> bool:
    if index >= len(flags):
        return False
    value = flags[index]
    return value in (1, "1", True, "true")
