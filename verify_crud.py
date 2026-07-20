"""Verify all CRUD functions return real data from PostgreSQL."""

from datetime import date
from app.crud import (
    search_tickers,
    get_ticker_prices,
    get_ticker_news,
    get_ticker_filings,
    get_filing_elements,
    get_ticker_timeline,
    get_ticker_fiscal_year_end,
    search_content,
)


def check(name, fn, *args, **kwargs):
    print(f"=== {name} ===")
    try:
        result = fn(*args, **kwargs)
        if result:
            print(f"  First: {result[0]}")
        print(f"  Total: {len(result)}\n")
        return result
    except Exception as e:
        print(f"  ERROR: {e}\n")
        return None


check("search_tickers('AAPL', 5)", search_tickers, "AAPL", 5)
check("get_ticker_prices('AAPL', date(2026,1,1), date(2026,7,17))", get_ticker_prices, "AAPL", date(2026, 1, 1), date(2026, 7, 17))
check("get_ticker_news('AAPL', date(2026,1,1), date(2026,7,17), 5)", get_ticker_news, "AAPL", date(2026, 1, 1), date(2026, 7, 17), 5)

filings = check("get_ticker_filings('AAPL')", get_ticker_filings, "AAPL")
check("get_ticker_timeline('AAPL', date(2026,1,1), date(2026,7,17), None, 10, 0)", get_ticker_timeline, "AAPL", date(2026, 1, 1), date(2026, 7, 17), None, 10, 0)
check("get_ticker_fiscal_year_end('AAPL')", get_ticker_fiscal_year_end, "AAPL")
check("search_content('autonomous driving', None, 5)", search_content, "autonomous driving", None, 5)

if filings:
    acc = filings[0].accession_number
    check(f"get_filing_elements('{acc}')", get_filing_elements, acc)

print("=== VERIFICATION COMPLETE ===")
