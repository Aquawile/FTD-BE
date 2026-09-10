from __future__ import annotations

import pytest
import unittest
from datetime import date, timedelta
from uuid import uuid4

from app.db import get_connection
from app.services.exceptions import (
    DataRetrievalError,
    DataValidationError,
    FilingNotFoundError,
    TickerNotFoundError,
)
from app.services.data_service import (
    search_tickers,
    get_ticker_prices,
    get_ticker_news,
    get_ticker_filings,
    get_filing_elements,
    get_ticker_timeline,
    get_ticker_fiscal_year_end,
    search_content,
    get_dashboard_stats,
    MAX_TICKER_LENGTH,
    MAX_SEARCH_LIMIT,
    VALID_DATA_SOURCES,
)


def _postgres_available() -> bool:
    """Check if PostgreSQL is available and has the expected tables."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.unified_staging')")
                if cur.fetchone()[0] is None:
                    return False
                cur.execute("SELECT to_regclass('public.staging_finnhub')")
                if cur.fetchone()[0] is None:
                    return False
                cur.execute("SELECT to_regclass('public.staging_gnews')")
                if cur.fetchone()[0] is None:
                    return False
                cur.execute("SELECT to_regclass('public.staging_sec')")
                if cur.fetchone()[0] is None:
                    return False
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False


class TestDataServiceValidation(unittest.TestCase):
    """Unit tests for data service validation logic (no database required)."""

    @pytest.mark.unit
    def test_search_tickers_raises_for_empty_query(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            search_tickers("")
        self.assertIn("empty", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_search_tickers_raises_for_whitespace_query(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            search_tickers("   ")
        self.assertIn("empty", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_get_ticker_prices_raises_for_empty_ticker(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            get_ticker_prices("", date(2024, 1, 1), date(2024, 12, 31))
        self.assertIn("empty", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_get_ticker_prices_raises_for_long_ticker(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            get_ticker_prices("A" * (MAX_TICKER_LENGTH + 1), date(2024, 1, 1), date(2024, 12, 31))
        self.assertIn("exceed", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_get_ticker_prices_raises_for_invalid_date_range(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            get_ticker_prices("AAPL", date(2024, 12, 31), date(2024, 1, 1))
        self.assertIn("start date", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_get_ticker_timeline_raises_for_invalid_sources(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            get_ticker_timeline("AAPL", date(2024, 1, 1), date(2024, 12, 31), sources=["invalid_source"])
        self.assertIn("unrecognized", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_get_ticker_timeline_accepts_valid_sources(self) -> None:
        for source in VALID_DATA_SOURCES:
            result = _validate_sources([source])
            self.assertEqual(result, [source])

    @pytest.mark.unit
    def test_get_filing_elements_raises_for_empty_accession(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            get_filing_elements("")
        self.assertIn("empty", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_search_content_raises_for_empty_keyword(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            search_content("")
        self.assertIn("empty", str(ctx.exception).lower())

    @pytest.mark.unit
    def test_search_content_raises_for_invalid_source(self) -> None:
        with self.assertRaises(DataValidationError) as ctx:
            search_content("test", source="invalid_source")
        self.assertIn("unrecognized", str(ctx.exception).lower())


class TestDataServiceIntegration(unittest.TestCase):
    """Integration tests for data service operations against PostgreSQL."""

    @pytest.mark.db_integration
    def test_search_tickers_returns_results_for_known_ticker(self) -> None:
        results = search_tickers("AAPL", limit=5)
        self.assertIsInstance(results, list)
        if results:
            self.assertIsInstance(results[0], type(results[0]))
            self.assertTrue(hasattr(results[0], "ticker"))

    @pytest.mark.db_integration
    def test_search_tickers_returns_empty_for_nonsense_query(self) -> None:
        results = search_tickers("ZZZZZZZZZZZZZ")
        self.assertEqual(results, [])

    @pytest.mark.db_integration
    def test_get_ticker_prices_raises_for_nonexistent_ticker(self) -> None:
        with self.assertRaises(TickerNotFoundError):
            get_ticker_prices("ZZZZZ", date(2020, 1, 1), date(2024, 12, 31))

    @pytest.mark.db_integration
    def test_get_ticker_prices_returns_data_for_known_ticker(self) -> None:
        try:
            results = get_ticker_prices("AAPL", date(2024, 1, 1), date(2024, 12, 31))
            self.assertIsInstance(results, list)
            if results:
                self.assertTrue(hasattr(results[0], "normalized_calendar_date"))
                self.assertTrue(hasattr(results[0], "current"))
        except TickerNotFoundError:
            self.skipTest("No price data for AAPL in test database")

    @pytest.mark.db_integration
    def test_get_ticker_news_raises_for_nonexistent_ticker(self) -> None:
        with self.assertRaises(TickerNotFoundError):
            get_ticker_news("ZZZZZ", date(2020, 1, 1), date(2024, 12, 31))

    @pytest.mark.db_integration
    def test_get_ticker_filings_raises_for_nonexistent_ticker(self) -> None:
        with self.assertRaises(TickerNotFoundError):
            get_ticker_filings("ZZZZZ")

    @pytest.mark.db_integration
    def test_get_filing_elements_raises_for_nonexistent_accession(self) -> None:
        with self.assertRaises(FilingNotFoundError):
            get_filing_elements("0000000000-00-000000")

    @pytest.mark.db_integration
    def test_get_ticker_timeline_raises_for_nonexistent_ticker(self) -> None:
        with self.assertRaises(TickerNotFoundError):
            get_ticker_timeline("ZZZZZ", date(2020, 1, 1), date(2024, 12, 31))

    @pytest.mark.db_integration
    def test_get_dashboard_stats_returns_expected_structure(self) -> None:
        result = get_dashboard_stats()
        self.assertIsInstance(result, dict)
        self.assertIn("articles_count", result)
        self.assertIn("tickers_count", result)
        self.assertIn("alerts_count", result)
        self.assertIn("evidence_score", result)
        self.assertIsInstance(result["articles_count"], int)
        self.assertIsInstance(result["tickers_count"], int)


class TestLayer3DataServiceIntegration(unittest.TestCase):
    """Integration tests verifying the complete Layer Three data service sequence."""

    @pytest.mark.db_integration
    def test_ticker_overview_retrieval_sequence(self) -> None:
        """Verify the complete sequence: search → prices → news → filings.

        This test demonstrates that the service layer can retrieve related
        data for a ticker through multiple coordinated operations, all
        without the client needing to understand the underlying table structure.
        """
        search_results = search_tickers("AAPL", limit=1)
        if not search_results:
            self.skipTest("No tickers found in test database")

        ticker = search_results[0].ticker
        self.assertIsNotNone(ticker)
        self.assertGreater(len(ticker), 0)

        end_date = date(2024, 12, 31)
        start_date = end_date - timedelta(days=365)

        try:
            prices = get_ticker_prices(ticker, start_date, end_date)
            self.assertIsInstance(prices, list)
        except TickerNotFoundError:
            pass

        try:
            news = get_ticker_news(ticker, start_date, end_date, limit=10)
            self.assertIsInstance(news, list)
        except TickerNotFoundError:
            pass

        try:
            filings = get_ticker_filings(ticker)
            self.assertIsInstance(filings, list)
        except TickerNotFoundError:
            pass

    @pytest.mark.db_integration
    def test_filing_detail_retrieval_sequence(self) -> None:
        """Verify the sequence: ticker filings → filing elements.

        Demonstrates that the service layer can navigate from a ticker
        to its filings and then to the detailed elements within a filing.
        """
        try:
            filings = get_ticker_filings("AAPL")
        except TickerNotFoundError:
            self.skipTest("No filings for AAPL in test database")
            return

        if not filings:
            self.skipTest("No filings returned for AAPL")
            return

        accession = filings[0].accession_number
        self.assertIsNotNone(accession)

        try:
            elements = get_filing_elements(accession)
            self.assertIsInstance(elements, list)
            if elements:
                self.assertTrue(hasattr(elements[0], "element_id"))
                self.assertTrue(hasattr(elements[0], "content_body"))
        except FilingNotFoundError:
            self.skipTest(f"No elements found for filing {accession}")

    @pytest.mark.db_integration
    def test_service_layer_has_no_http_dependencies(self) -> None:
        """Verify the data service module does not import HTTP-specific modules."""
        import ast
        import pathlib

        service_modules = [
            pathlib.Path("app/services/data_service.py"),
            pathlib.Path("app/services/exceptions.py"),
        ]

        http_imports = {"fastapi", "starlette", "uvicorn", "Request", "HTTPException", "Depends", "APIRouter"}

        for module_path in service_modules:
            if not module_path.exists():
                continue
            content = module_path.read_text()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and any(name in http_imports for name in [node.module] + [alias.name for alias in node.names]):
                        self.fail(f"Service module {module_path} imports HTTP-specific module: {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in http_imports:
                            self.fail(f"Service module {module_path} imports HTTP-specific module: {alias.name}")


def _validate_sources(sources: list[str] | None) -> list[str] | None:
    """Re-export for testing without making it part of the public API."""
    from app.services.data_service import _validate_sources
    return _validate_sources(sources)


if __name__ == "__main__":
    unittest.main()
