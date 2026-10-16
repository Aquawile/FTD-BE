"""GNews queries search by company name and ticker (gnews/queries.py)."""
import importlib.util
import os

import pytest

pytestmark = pytest.mark.unit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


q = _load("gnews_queries", ("gnews", "queries.py"))
srr = _load("sync_recent_relational", ("scripts", "sync_recent_relational.py"))


def test_ticker_terms_use_name_and_ticker():
    assert q.ticker_terms("NVDA", {"NVDA": "NVIDIA"}) == ['"NVIDIA"', '"NVDA"']
    assert q.ticker_terms("XYZ", {}) == ['"XYZ"']
    assert q.ticker_terms("IBM", {"IBM": "IBM"}) == ['"IBM"']           # name equal to ticker: once
    assert q.ticker_terms("ACME", {"ACME": 'Acme "Labs"'}) == ['"Acme Labs"', '"ACME"']


def _roster(n=500, name=lambda i: f"Company {i}"):
    """n tickers; 9 in 10 have a name (real names average ~14 chars)."""
    tickers = [f"T{i:03d}" for i in range(n)]
    names = {t: name(i) for i, t in enumerate(tickers) if i % 10}
    return tickers, names


def test_spreads_over_budget_within_length_and_covers_every_ticker():
    tickers, names = _roster()
    batches, dropped = q.build_batches(tickers, names, max_query_length=200, max_requests=100)
    assert len(batches) <= 100 and not dropped
    assert all(len(b["query"]) <= 200 for b in batches)
    assert sorted(t for b in batches for t in b["tickers"]) == sorted(tickers)
    first = batches[0]
    assert first["tickers"] == ["T000", "T001", "T002", "T003", "T004"]
    assert first["query"] == '"T000" OR "Company 1" OR "T001" OR "Company 2" OR "T002" OR "Company 3" OR "T003" OR "Company 4" OR "T004"'


def test_tighter_budget_packs_more_then_drops_longest_names():
    tickers, names = _roster(60, name=lambda i: f"Company Number {i} Holdings Worldwide")
    batches, dropped = q.build_batches(tickers, names, max_query_length=200, max_requests=12)
    assert len(batches) <= 12
    assert sorted(t for b in batches for t in b["tickers"]) == sorted(tickers)
    for t in dropped:
        assert all(f'"{names[t]}"' not in b["query"] for b in batches)


def test_impossible_budget_raises():
    with pytest.raises(ValueError):
        q.build_batches([f"T{i}" for i in range(50)], {}, max_query_length=20, max_requests=3)


def test_sync_reads_tickers_from_new_and_old_batch_files():
    symbols = {"NVDA", "AAPL", "MMM"}
    assert srr.batch_tickers({"query": '"NVIDIA" OR "NVDA" OR "Apple" OR "AAPL"', "tickers": ["NVDA", "AAPL", "ZZZ"]}, symbols) == ["NVDA", "AAPL"]
    assert srr.batch_tickers({"query": '"$MMM" OR "$AOS"'}, symbols) == ["MMM"]
