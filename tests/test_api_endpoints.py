"""Unit tests for FastAPI route endpoints.

These tests mock authentication (Firebase token validation) and CRUD layer functions so they can run without a database.
They verify HTTP-level concerns: status codes, response shapes, query parameter
validation, and auth/permission enforcement.
"""

from __future__ import annotations

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, AsyncMock

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.auth.models import User
from app.auth.dependencies import get_current_application_user, get_current_permissions
from app.models import (
    TrackedTicker,
    WorkspaceResponse,
    AlertResponse,
    TickerResult,
    PriceRow,
    NewsRow,
    TimelineEvent,
    FilingSummary,
    FilingElement,
    FiscalYearEnd,
    SearchResult,
)
from app.services.exceptions import (
    TickerNotFoundError,
    FilingNotFoundError,
)

client = TestClient(app)

_FAKE_USER = User(
    id=4,
    firebase_uid="test-firebase-uid",
    email="test@example.com",
    is_active=True,
    created_at="2026-01-01T00:00:00",
    updated_at="2026-01-01T00:00:00",
)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake-valid-token"}


@pytest.fixture(autouse=True)
def _mock_firebase_auth():
    """Patch Firebase token validation so the middleware always succeeds,
    and mock DB writes so tests don't need a database connection.
    """
    with patch(
        "app.auth.middleware.validate_firebase_token_with_reason",
        return_value=({"firebase_uid": "test-firebase-uid", "email": "test@example.com"}, None),
    ), patch("app.db.execute"):
        yield


@pytest.fixture
def _mock_user():
    """Override get_current_application_user for routes using it directly."""
    async def _fake_current_application_user(request=None) -> User:
        return _FAKE_USER
    original = app.dependency_overrides.get
    app.dependency_overrides[get_current_application_user] = _fake_current_application_user
    yield
    if get_current_application_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_application_user]


@pytest.fixture
def _mock_permissions():
    """Override auth dependencies for routes using require_permission."""
    async def _fake_current_user(request=None) -> User:
        return _FAKE_USER
    async def _fake_permissions() -> set[str]:
        return {
            "tickers.search", "tickers.prices", "tickers.news",
            "tickers.filings", "tickers.timeline", "tickers.fiscal_year_end",
            "filings.read", "search.read", "dashboard.read", "admin",
        }
    app.dependency_overrides[get_current_application_user] = _fake_current_user
    app.dependency_overrides[get_current_permissions] = _fake_permissions
    yield
    app.dependency_overrides.pop(get_current_application_user, None)
    app.dependency_overrides.pop(get_current_permissions, None)


@pytest.fixture
def _mock_no_permissions():
    """Override auth dependencies so no permissions are granted (403 tests)."""
    async def _fake_current_user(request=None) -> User:
        return _FAKE_USER
    async def _fake_permissions() -> set[str]:
        return set()
    app.dependency_overrides[get_current_application_user] = _fake_current_user
    app.dependency_overrides[get_current_permissions] = _fake_permissions
    yield
    app.dependency_overrides.pop(get_current_application_user, None)
    app.dependency_overrides.pop(get_current_permissions, None)


# ---------------------------------------------------------------------------
# Dashboard endpoint (public — no auth required)
# ---------------------------------------------------------------------------

class TestDashboardEndpoint:
    @pytest.mark.unit
    def test_dashboard_stats_returns_expected_fields(self) -> None:
        with patch("app.services.vectorized_gcs.count_vectorized_content", return_value=15000), \
             patch("app.crud.count_articles", return_value=(21959, 704, 758054)):
            with patch("app.db.query_dict") as mock_qd:
                mock_qd.side_effect = [
                    [{"count": 500}],
                ]
                response = client.get("/dashboard/stats")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["articles_count"] == 758054 + 21959
            assert data["sec_elements_count"] == 758054
            assert data["news_articles_count"] == 21959
            assert data["sec_filings_count"] == 704
            assert data["tickers_count"] == 500
            assert "alerts_count" not in data and "evidence_score" not in data
            assert data["vectorized_sec_count"] == 15000

    @pytest.mark.unit
    def test_dashboard_stats_returns_zeros_on_empty(self) -> None:
        with patch("app.services.vectorized_gcs.count_vectorized_content", return_value=0), \
             patch("app.crud.count_articles", return_value=(0, 0, 0)):
            with patch("app.db.query_dict") as mock_qd:
                mock_qd.side_effect = [
                    [{"count": 0}],
                ]
                response = client.get("/dashboard/stats")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["articles_count"] == 0
            assert data["tickers_count"] == 0
            assert "evidence_score" not in data
            assert data["vectorized_sec_count"] == 0

    @pytest.mark.unit
    def test_dashboard_stats_no_auth_required(self) -> None:
        with patch("app.services.vectorized_gcs.count_vectorized_content", return_value=0), \
             patch("app.crud.count_articles", return_value=(0, 0, 0)):
            with patch("app.db.query_dict") as mock_qd:
                mock_qd.side_effect = [
                    [{"count": 0}],
                ]
                response = client.get("/dashboard/stats")
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Tracked tickers endpoint
# ---------------------------------------------------------------------------

class TestTrackedTickersEndpoint:
    @pytest.mark.unit
    def test_get_tracked_tickers_returns_list(self) -> None:
        fake = [
            TrackedTicker(
                symbol="AAPL",
                name="Apple Inc.",
                sector="Technology",
                current_price=Decimal("200.50"),
                change_percent=Decimal("1.2"),
            ),
        ]
        with patch("app.routes.tickers.get_tracked_tickers", return_value=fake):
            response = client.get("/tickers/tracked")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["symbol"] == "AAPL"
        assert data[0]["name"] == "Apple Inc."
        assert data[0]["sector"] == "Technology"

    @pytest.mark.unit
    def test_get_tracked_tickers_empty_list(self) -> None:
        with patch("app.routes.tickers.get_tracked_tickers", return_value=[]):
            response = client.get("/tickers/tracked")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.unit
    def test_get_tracked_tickers_respects_limit_param(self) -> None:
        with patch("app.routes.tickers.get_tracked_tickers") as mock_fn:
            mock_fn.return_value = []
            client.get("/tickers/tracked?limit=5")
            mock_fn.assert_called_once_with(limit=5, symbol=None)

    @pytest.mark.unit
    def test_get_tracked_tickers_single_symbol_is_public_and_normalized(self) -> None:
        with patch("app.routes.tickers.get_tracked_tickers") as mock_fn:
            mock_fn.return_value = []
            response = client.get("/tickers/tracked?symbol=nvda&limit=1")
            assert response.status_code == 200
            mock_fn.assert_called_once_with(limit=1, symbol="NVDA")

    @pytest.mark.unit
    def test_get_tracked_tickers_limit_rejected_when_too_large(self) -> None:
        with patch("app.routes.tickers.get_tracked_tickers") as mock_fn:
            mock_fn.return_value = []
            response = client.get("/tickers/tracked?limit=99999")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            mock_fn.assert_not_called()

    @pytest.mark.unit
    def test_get_tracked_tickers_is_public(self) -> None:
        with patch("app.routes.tickers.get_tracked_tickers", return_value=[]):
            response = client.get("/tickers/tracked")
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Ticker search endpoint
# ---------------------------------------------------------------------------

class TestTickerSearchEndpoint:
    @pytest.mark.unit
    def test_search_tickers_returns_results(self, _mock_permissions) -> None:
        fake = [
            TickerResult(ticker="AAPL", cik="0000320193", sector="Technology"),
        ]
        with patch("app.routes.tickers.search_tickers", return_value=fake):
            response = client.get("/tickers/search?q=aapl", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["cik"] == "0000320193"

    @pytest.mark.unit
    def test_search_tickers_missing_query_returns_422(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.search_tickers", return_value=[]):
            response = client.get("/tickers/search", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_search_tickers_empty_query_returns_422(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.search_tickers", return_value=[]):
            response = client.get("/tickers/search?q=", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_search_tickers_empty_list(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.search_tickers", return_value=[]):
            response = client.get("/tickers/search?q=ZZZZ", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.unit
    def test_search_tickers_requires_permission(self, _mock_no_permissions) -> None:
        response = client.get("/tickers/search?q=aapl", headers=_auth_headers())
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Ticker prices endpoint
# ---------------------------------------------------------------------------

class TestTickerPricesEndpoint:
    @pytest.mark.unit
    def test_get_prices_returns_rows(self, _mock_permissions) -> None:
        fake = [
            PriceRow(
                normalized_calendar_date=date(2024, 1, 15),
                current=Decimal("190.50"),
                change=Decimal("2.50"),
                percent_change=Decimal("1.33"),
                open=Decimal("188.00"),
                high=Decimal("191.00"),
                low=Decimal("187.50"),
                previous_close=Decimal("188.00"),
            ),
        ]
        with patch("app.routes.tickers.get_ticker_prices", return_value=fake):
            response = client.get(
                "/tickers/AAPL/prices?start=2024-01-01&end=2024-12-31",
                headers=_auth_headers(),
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["current"] == 190.5
        assert data[0]["open"] == 188.0
        assert data[0]["high"] == 191.0
        assert data[0]["low"] == 187.5
        assert data[0]["previous_close"] == 188.0

    @pytest.mark.unit
    def test_get_prices_missing_dates_returns_422(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.get_ticker_prices", return_value=[]):
            response = client.get("/tickers/AAPL/prices", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_prices_nonexistent_ticker_raises_404(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.get_ticker_prices", side_effect=TickerNotFoundError("not found")):
            response = client.get(
                "/tickers/ZZZZZ/prices?start=2024-01-01&end=2024-12-31",
                headers=_auth_headers(),
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Ticker news endpoint
# ---------------------------------------------------------------------------

class TestTickerNewsEndpoint:
    @pytest.mark.unit
    def test_get_news_returns_rows(self, _mock_permissions) -> None:
        fake = [
            NewsRow(
                target_ticker="AAPL",
                normalized_calendar_date=date(2024, 6, 1),
                content_body="Apple announces new product",
            ),
        ]
        with patch("app.routes.tickers.get_ticker_news", return_value=fake), \
             patch("app.routes.tickers.get_ticker_news_bounds", return_value=(1, date(2024, 6, 1))):
            response = client.get(
                "/tickers/AAPL/news?start=2024-01-01&end=2024-12-31",
                headers=_auth_headers(),
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["target_ticker"] == "AAPL"
        assert "Apple announces" in data[0]["content_body"]

    @pytest.mark.unit
    def test_get_news_pages_with_offset_and_reports_totals(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.get_ticker_news", return_value=[]) as rows, \
             patch("app.routes.tickers.get_ticker_news_bounds", return_value=(137, date(2026, 6, 29))):
            response = client.get(
                "/tickers/AAPL/news?start=2026-01-01&end=2026-10-16&limit=20&offset=40",
                headers=_auth_headers(),
            )
        assert response.status_code == status.HTTP_200_OK
        assert rows.call_args.args == ("AAPL", date(2026, 1, 1), date(2026, 10, 16), 20, 40)
        assert response.headers["X-Total-Count"] == "137"
        assert response.headers["X-Earliest-Date"] == "2026-06-29"

    @pytest.mark.unit
    def test_get_news_negative_offset_returns_422(self, _mock_permissions) -> None:
        response = client.get("/tickers/AAPL/news?start=2026-01-01&end=2026-10-16&offset=-1", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_news_missing_dates_returns_422(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.get_ticker_news", return_value=[]):
            response = client.get("/tickers/AAPL/news", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_news_nonexistent_ticker_raises_404(self, _mock_permissions) -> None:
        with patch("app.routes.tickers.get_ticker_news", side_effect=TickerNotFoundError("not found")):
            response = client.get(
                "/tickers/ZZZZZ/news?start=2024-01-01&end=2024-12-31",
                headers=_auth_headers(),
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Ticker timeline endpoint
# ---------------------------------------------------------------------------

class TestTickerTimelineEndpoint:
    @pytest.mark.unit
    def test_get_timeline_returns_rows(self, _mock_permissions) -> None:
        fake = [
            TimelineEvent(
                normalized_calendar_date=date(2024, 1, 15),
                source="sec",
                content_body="10-K filing",
                form_type="10-K",
            ),
        ]
        with patch("app.services.vectorized_gcs.get_timeline_from_gcs", return_value=fake):
            response = client.get(
                "/tickers/AAPL/timeline?start=2024-01-01&end=2024-12-31&sources=sec",
                headers=_auth_headers(),
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "sec"

    @pytest.mark.unit
    def test_get_timeline_with_non_sec_sources_uses_crud(self, _mock_permissions) -> None:
        fake = [
            TimelineEvent(
                normalized_calendar_date=date(2024, 1, 15),
                source="gnews",
                content_body="News article",
            ),
        ]
        with patch("app.crud.get_ticker_timeline", return_value=fake):
            response = client.get(
                "/tickers/AAPL/timeline?start=2024-01-01&end=2024-12-31&sources=gnews",
                headers=_auth_headers(),
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "gnews"

    @pytest.mark.unit
    def test_get_timeline_missing_dates_returns_422(self, _mock_permissions) -> None:
        response = client.get("/tickers/AAPL/timeline", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Ticker filings endpoint
# ---------------------------------------------------------------------------

class TestTickerFilingsEndpoint:
    @pytest.mark.unit
    def test_get_filings_returns_summaries(self, _mock_permissions) -> None:
        fake = [
            FilingSummary(
                target_ticker="AAPL",
                target_cik="0000320193",
                form_type="10-K",
                accession_number="0000320193-24-000011",
                filing_date=date(2024, 1, 1),
                element_count=45,
            ),
        ]
        with patch("app.services.vectorized_gcs.list_filings_for_ticker", return_value=fake):
            response = client.get("/tickers/AAPL/filings", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["form_type"] == "10-K"
        assert data[0]["element_count"] == 45

    @pytest.mark.unit
    def test_get_filings_nonexistent_ticker_returns_empty(self, _mock_permissions) -> None:
        with patch("app.services.vectorized_gcs.list_filings_for_ticker", return_value=[]):
            response = client.get("/tickers/ZZZZZ/filings", headers=_auth_headers())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.unit
    def test_get_filings_empty_list(self, _mock_permissions) -> None:
        with patch("app.services.vectorized_gcs.list_filings_for_ticker", return_value=[]):
            response = client.get("/tickers/AAPL/filings", headers=_auth_headers())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


# ---------------------------------------------------------------------------
# Fiscal year end endpoint
# ---------------------------------------------------------------------------

class TestFiscalYearEndEndpoint:
    @pytest.mark.unit
    def test_get_fiscal_year_end_returns_data(self, _mock_permissions) -> None:
        fake = FiscalYearEnd(
            target_ticker="AAPL",
            target_cik="0000320193",
            fiscal_year_end_date=date(2024, 9, 28),
            source_accession="0000320193-24-000011",
        )
        with patch("app.services.vectorized_gcs.get_fiscal_year_end_from_gcs", return_value=fake):
            response = client.get("/tickers/AAPL/fiscal-year-end", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["target_ticker"] == "AAPL"
        assert data["fiscal_year_end_date"] == "2024-09-28"

    @pytest.mark.unit
    def test_get_fiscal_year_end_not_found_returns_404(self, _mock_permissions) -> None:
        with patch("app.services.vectorized_gcs.get_fiscal_year_end_from_gcs", return_value=None):
            response = client.get("/tickers/ZZZZZ/fiscal-year-end", headers=_auth_headers())
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Filing elements endpoint
# ---------------------------------------------------------------------------

class TestFilingElementsEndpoint:
    @pytest.mark.unit
    def test_get_filing_elements_returns_list(self, _mock_permissions) -> None:
        fake = [
            FilingElement(
                element_id="element-1",
                accession_number="0000320193-24-000011",
                item_number="1A",
                content_type="risk_factors",
                element_type="narrative",
                content_body="Risk factor content",
            ),
        ]
        with patch("app.services.vectorized_gcs.get_filing_elements_by_accession", return_value=fake):
            response = client.get(
                "/filings/0000320193-24-000011/elements",
                headers=_auth_headers(),
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["element_id"] == "element-1"
        assert data[0]["item_number"] == "1A"

    @pytest.mark.unit
    def test_get_filing_elements_not_found_returns_empty(self, _mock_permissions) -> None:
        with patch("app.services.vectorized_gcs.get_filing_elements_by_accession", return_value=[]):
            response = client.get(
                "/filings/0000000000-00-000000/elements",
                headers=_auth_headers(),
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


# ---------------------------------------------------------------------------
# Workspaces endpoint
# ---------------------------------------------------------------------------

class TestWorkspacesEndpoint:
    @pytest.mark.unit
    def test_get_workspaces_returns_list(self, _mock_user) -> None:
        fake = [
            WorkspaceResponse(
                id=1, name="My Portfolio", tickers=["AAPL", "NVDA"],
                alerts=3, created_at="2024-01-01T00:00:00",
            ),
            WorkspaceResponse(
                id=2, name="Watchlist", tickers=["GOOGL"],
                alerts=0, created_at="2024-02-01T00:00:00",
            ),
        ]
        with patch("app.routes.workspaces.get_user_workspaces", return_value=fake):
            response = client.get("/workspaces", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "My Portfolio"
        assert data[0]["tickers"] == ["AAPL", "NVDA"]

    @pytest.mark.unit
    def test_get_workspaces_empty_list(self, _mock_user) -> None:
        with patch("app.routes.workspaces.get_user_workspaces", return_value=[]):
            response = client.get("/workspaces", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.unit
    def test_get_workspaces_requires_auth(self) -> None:
        response = client.get("/workspaces")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Alerts endpoint
# ---------------------------------------------------------------------------

class TestAlertsEndpoint:
    @pytest.mark.unit
    def test_get_alerts_returns_list(self, _mock_user) -> None:
        fake = [
            AlertResponse(
                id=1, ticker="AAPL", type="price",
                message="Price dropped below $190",
                read=False, severity="high",
                time="2024-06-15T10:30:00",
            ),
        ]
        with patch("app.routes.alerts.get_user_alerts", return_value=fake):
            response = client.get("/alerts?limit=10", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["type"] == "price"
        assert data[0]["severity"] == "high"

    @pytest.mark.unit
    def test_get_alerts_empty_list(self, _mock_user) -> None:
        with patch("app.routes.alerts.get_user_alerts", return_value=[]):
            response = client.get("/alerts", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.unit
    def test_get_alerts_requires_auth(self) -> None:
        response = client.get("/alerts")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Search (content) endpoint
# ---------------------------------------------------------------------------

class TestSearchContentEndpoint:
    @pytest.mark.unit
    def test_search_content_returns_results(self, _mock_permissions) -> None:
        fake = [
            SearchResult(
                target_ticker="AAPL",
                normalized_calendar_date=date(2024, 6, 1),
                source="gnews",
                content_preview="Apple announces new AI features",
                element_id="elem-1",
            ),
        ]
        with patch("app.routes.search.search_content", return_value=fake):
            response = client.get("/search?q=Apple&source=gnews", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["target_ticker"] == "AAPL"

    @pytest.mark.unit
    def test_search_sec_content_uses_gcs(self, _mock_permissions) -> None:
        fake = [
            SearchResult(
                target_ticker="AAPL",
                normalized_calendar_date=date(2024, 6, 1),
                source="sec",
                content_preview="SEC filing content",
                element_id="elem-2",
            ),
        ]
        with patch("app.services.vectorized_gcs.search_vectorized_content", return_value=fake):
            response = client.get("/search?q=revenue&source=sec", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "sec"

    @pytest.mark.unit
    def test_search_no_source_defaults_to_sec_gcs(self, _mock_permissions) -> None:
        fake = [
            SearchResult(
                target_ticker="AAPL",
                normalized_calendar_date=date(2024, 6, 1),
                source="sec",
                content_preview="SEC filing content",
                element_id="elem-2",
            ),
        ]
        with patch("app.services.vectorized_gcs.search_vectorized_content", return_value=fake):
            response = client.get("/search?q=revenue", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "sec"

    @pytest.mark.unit
    def test_search_content_missing_query_returns_422(self, _mock_permissions) -> None:
        response = client.get("/search", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_search_content_empty_query_returns_422(self, _mock_permissions) -> None:
        response = client.get("/search?q=", headers=_auth_headers())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_search_content_requires_permission(self, _mock_no_permissions) -> None:
        response = client.get("/search?q=test", headers=_auth_headers())
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Admin endpoints (Layer 11 — Counter Monitoring)
# ---------------------------------------------------------------------------

class TestAdminEndpoints:
    @pytest.mark.unit
    def test_db_access_counters_returns_empty(self, _mock_permissions) -> None:
        with patch("app.services.db_access_counter.get_counters", return_value={}):
            response = client.get("/admin/db-access-counters", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["counters"] == {}
        assert data["total_hits"] == 0
        assert data["all_clear"] is True
        assert data["db_access_detected"] is False

    @pytest.mark.unit
    def test_db_access_counters_shows_hits_when_present(self, _mock_permissions) -> None:
        from app.services.db_access_counter import increment_counter, reset_counters
        reset_counters()
        increment_counter("endpoint:get_ticker_filings")

        response = client.get("/admin/db-access-counters", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["counters"]["endpoint:get_ticker_filings"] == 1
        assert data["db_access_detected"] is True
        assert data["all_clear"] is False

        reset_counters()

    @pytest.mark.unit
    def test_db_access_counters_reset(self, _mock_permissions) -> None:
        from app.services.db_access_counter import increment_counter, reset_counters
        reset_counters()
        increment_counter("endpoint:test")

        response = client.post("/admin/db-access-counters/reset", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "reset"

    @pytest.mark.unit
    def test_db_access_counters_requires_admin_permission(self, _mock_no_permissions) -> None:
        response = client.get("/admin/db-access-counters", headers=_auth_headers())
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.unit
    def test_migration_status_returns_summary(self, _mock_permissions) -> None:
        with patch("app.services.db_access_counter.get_counters", return_value={}), \
             patch("app.services.vectorized_gcs.count_vectorized_content", return_value=707):
            response = client.get("/admin/migration-status", headers=_auth_headers())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["migration_complete"] is True
        assert data["vectorized_content_elements_in_gcs"] == 707
        assert "sec_endpoints_using_gcs" in data

    @pytest.mark.unit
    def test_migration_status_requires_admin_permission(self, _mock_no_permissions) -> None:
        response = client.get("/admin/migration-status", headers=_auth_headers())
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Health endpoint validation (Layer 10)
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    @pytest.mark.unit
    def test_health_returns_db_access_counters(self) -> None:
        with patch("app.services.db_access_counter.get_counters", return_value={}):
            response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "db_access_counters" in data
        assert "db_access_detected" in data
        assert data["db_access_detected"] is False
