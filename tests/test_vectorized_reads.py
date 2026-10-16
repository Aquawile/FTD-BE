"""Request-scoped reads of vectorized SEC data (app.services.vectorized_gcs).

Each function must issue one scoped query against sec_vectorized_chunks and
never list or download the whole GCS bucket.
"""
from datetime import date
from unittest.mock import patch

import pytest

from app.services import vectorized_gcs as v

pytestmark = pytest.mark.unit

NVDA_10K = "SEC/10-K/0001045810/000104581026000021/nvda-20260125.htm"


@pytest.fixture(autouse=True)
def _no_gcs():
    """Any GCS client use in these paths is a bug."""
    with patch.object(v, "_get_client", side_effect=AssertionError("GCS must not be touched")):
        yield


def test_resolve_ticker_to_cik_uses_one_mirror_query():
    with patch.object(v, "query_dict", return_value=[{"cik": "0001045810"}]) as q:
        assert v._resolve_ticker_to_cik("NVDA") == "0001045810"
    q.assert_called_once()
    sql, params = q.call_args.args
    assert "sec_vectorized_chunks" in sql and "chunk_index = 0" in sql
    assert params == ("SEC/%", "nvda")


def test_resolve_ticker_to_cik_unknown_returns_none():
    with patch.object(v, "query_dict", return_value=[]):
        assert v._resolve_ticker_to_cik("ZZZZ") is None


def test_list_filings_scoped_to_company_and_mapped():
    rows = [{"source_object": NVDA_10K, "accession_number": "0001045810-26-000021",
             "form_type": "10-K", "filing_date": date(2026, 2, 25), "chunk_count": 54},
            {"source_object": "SEC/8-K/0001045810/x/y.htm", "accession_number": None,
             "form_type": None, "filing_date": None, "chunk_count": 3}]
    with patch.object(v, "query_dict", side_effect=[[{"cik": "0001045810"}], rows]) as q:
        out = v.list_filings_for_ticker("nvda")
    assert q.call_args_list[1].args[1] == ("SEC/8-K/0001045810/%", "SEC/10-K/0001045810/%")
    assert [f.accession_number for f in out] == ["0001045810-26-000021", ""]
    assert out[0].target_ticker == "NVDA" and out[0].element_count == 54
    assert out[1].form_type == "UNKNOWN"


def test_list_filings_unknown_ticker_skips_filings_query():
    with patch.object(v, "query_dict", return_value=[]) as q:
        assert v.list_filings_for_ticker("ZZZZ") == []
    assert q.call_count == 1


@pytest.mark.parametrize("acc", ["0001045810-26-000021", "000104581026000021"])
def test_filing_elements_matches_dashed_accession(acc):
    rows = [{"accession_number": "0001045810-26-000021", "filing_date": date(2026, 2, 25),
             "chunk_index": i, "text_preview": f"chunk {i}"} for i in range(3)]
    with patch.object(v, "query_dict", return_value=rows) as q:
        out = v.get_filing_elements_by_accession(acc)
    assert q.call_args.args[1][0] == "0001045810-26-000021"
    assert [e.element_id for e in out] == [f"0001045810-26-000021-chunk-{i}" for i in range(3)]
    assert out[2].content_body == "chunk 2"


def test_search_escapes_wildcards_and_orders_recent_first():
    rows = [{"source_object": NVDA_10K, "cik": "0001045810", "accession_number": "0001045810-26-000021",
             "filing_date": date(2026, 2, 25), "chunk_index": 7, "preview": "net revenue grew"},
            {"source_object": "SEC/8-K/0000008670/a/eh_8k.htm", "cik": "0000008670", "accession_number": None,
             "filing_date": None, "chunk_index": 0, "preview": "revenue"}]
    with patch.object(v, "query_dict", return_value=rows) as q:
        out = v.search_vectorized_content("50%_off", limit=5)
    sql, params = q.call_args.args
    assert "ORDER BY filing_date DESC" in sql
    assert params == ("SEC/%", "%50\\%\\_off%", 5)
    assert out[0].target_ticker == "NVDA" and out[0].element_id == "0001045810-26-000021-chunk-7"
    assert out[1].target_ticker == "0000008670"  # no ticker in filename -> CIK, as before


def test_count_vectorized_content_is_single_count():
    with patch.object(v, "query_dict", return_value=[{"count": 26918}]) as q:
        assert v.count_vectorized_content() == 26918
    assert "COUNT(*)" in q.call_args.args[0]


def test_timeline_maps_form_from_path_and_passes_window():
    rows = [{"source_object": NVDA_10K, "filing_date": date(2026, 2, 25), "preview": "Annual report"}]
    with patch.object(v, "query_dict", side_effect=[[{"cik": "0001045810"}], rows]) as q:
        out = v.get_timeline_from_gcs("NVDA", date(2026, 1, 1), date(2026, 10, 16), limit=10, offset=0)
    assert q.call_args_list[1].args[1][2:] == (date(2026, 1, 1), date(2026, 10, 16), 10, 0)
    assert out[0].form_type == "10-K" and out[0].source == "sec"
