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
    ("Apple (AAPL) and Microsoft rallied", "AAPL", [], None),
    ("Apple (AAPL) and Microsoft rallied", "AAPL", ["Apple"], "name"),
    ("Barclays Adjusts Price Target on Camden Property Trust", "TGT", ["Target"], None),
    ("Target (TGT) to Challenge Amazon's Fall Sales Event", "TGT", ["Target"], "name"),
    ("Asus ProArt P16 with Nvidia's RTX Spark steps up", "RTX", ["RTX"], None),
    ("Poke Ball hotel opens in Japan", "BALL", ["Ball"], None),
    ("The Premier League's KMI panel reviewed it", "KMI", ["Kinder Morgan"], None),
    ("Kinder Morgan raises dividend", "KMI", ["Kinder Morgan"], "name"),
    ("HSBC plans HK$100 fund; adviser admits scamming firms for $3.3M and $3M", "MMM", ["3M"], None),
    ("Torrevieja awards a €3m lighting contract", "MMM", ["3M"], None),
    ("3M recalls laminators", "MMM", ["3M"], "name"),
    ("pays no tax on a target of $5", "TGT", ["Target"], None),
    ("Shares of NVIDIA rose 3%", "NVDA", ["NVIDIA"], "name"),
    ("3M cuts its guidance", "MMM", ["3M"], "name"),
    ("STEPX Neo phone ships with Step AOS", "AOS", [], None),
    ("pineapple prices climb", "AAPL", ["Apple"], None),
    ("Apple and NVDA rallied", "NVDA", [], None),
])
def test_article_mentions(text, ticker, names, rule):
    assert srr.article_mentions(text, ticker, names) == rule
