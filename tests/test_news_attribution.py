"""Article -> ticker attribution rules (PRD-6, CLAUDE.md known issue #10)."""
import importlib.util
import os

import pytest

pytestmark = pytest.mark.unit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("sync_recent_relational", os.path.join(ROOT, "scripts", "sync_recent_relational.py"))
srr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srr)


@pytest.mark.parametrize("raw, expected", [
    ("NVIDIA CORP", "NVIDIA"),
    ("Apple Inc.", "Apple"),
    ("Agilent Technologies, Inc.", "Agilent Technologies"),
    ("The Walt Disney Company", "Walt Disney"),
    ("3M COMPANY", "3M"),
    ("Co", None),
    ("NORTHROP GRUMMAN CORP /DE/", "NORTHROP GRUMMAN"),
    ("WALT DISNEY CO/", "WALT DISNEY"),
    ("VERTEX PHARMACEUTICALS INC / MA", "VERTEX PHARMACEUTICALS"),
])
def test_normalize_company_name(raw, expected):
    assert srr.normalize_company_name(raw) == expected


@pytest.mark.parametrize("text, ticker, names, rule", [
    ("Buy $NVDA before earnings", "NVDA", [], "dollar"),
    ("A. O. Smith (NYSE: AOS) reported results", "AOS", [], "exchange"),
    ("Apple (AAPL) and Microsoft rallied", "AAPL", [], "paren"),
    ("Shares of NVIDIA rose 3%", "NVDA", ["NVIDIA"], "name"),
    ("3M cuts its guidance", "MMM", ["3M"], "name"),
    ("STEPX Neo phone ships with Step AOS", "AOS", [], None),
    ("pineapple prices climb", "AAPL", ["Apple"], None),
    ("Apple and NVDA rallied", "NVDA", [], None),
])
def test_article_mentions(text, ticker, names, rule):
    assert srr.article_mentions(text, ticker, names) == rule
