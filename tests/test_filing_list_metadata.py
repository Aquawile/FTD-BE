from datetime import date
from unittest.mock import patch

import pytest

from app.services import vectorized_gcs as v

pytestmark = pytest.mark.unit

PATH = "SEC/10-K/0000001800/000162828026010185/abt-20251231.htm"


def _rows(**over):
    row = {"source_object": PATH, "accession_number": None, "form_type": None, "filing_date": None, "chunk_count": 53}
    row.update(over)
    return [row]


def _list(rows):
    with patch.object(v, "_resolve_ticker_to_cik", return_value="0000001800"), patch.object(v, "query_dict", return_value=rows):
        return v.list_filings_for_ticker("ABT")


def test_missing_metadata_is_filled_from_the_stored_path():
    f = _list(_rows())[0]
    assert (f.form_type, f.accession_number) == ("10-K", "0001628280-26-010185")
    assert f.filing_date is None and f.period_of_report == date(2025, 12, 31)
    assert f.url == "https://www.sec.gov/Archives/edgar/data/1800/000162828026010185/0001628280-26-010185-index.htm"


def test_recorded_metadata_wins_over_the_path():
    f = _list(_rows(accession_number="0000000000-00-000001", form_type="10-K/A", filing_date=date(2026, 2, 1)))[0]
    assert (f.form_type, f.accession_number, f.filing_date) == ("10-K/A", "0000000000-00-000001", date(2026, 2, 1))


def test_8k_path_and_undated_files_sort_by_period_after_dated_ones():
    rows = _rows(source_object="SEC/8-K/0000001800/000162828026000001/abt-20260105.htm") + _rows(filing_date=date(2026, 2, 20)) + _rows(source_object="SEC/10-K/0000001800/000162828024000002/abt-20231231.htm")
    out = _list(rows)
    assert [f.form_type for f in out] == ["10-K", "8-K", "10-K"]
    assert out[0].filing_date == date(2026, 2, 20)


def test_path_without_an_accession_gives_no_broken_link():
    f = _list(_rows(source_object="SEC/10-K/0000001800/weird.htm"))[0]
    assert f.accession_number == "" and f.url == ""
