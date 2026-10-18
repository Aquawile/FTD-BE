"""Display names shown under each ticker (scripts/load_company_names.py)."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location(
    "load_company_names", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "load_company_names.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
display_name = _mod.display_name


@pytest.mark.parametrize("raw,expected", [
    ("Apple", "Apple"),                                    # already mixed case: unchanged
    ("Meta Platforms", "Meta Platforms"),
    ("MICROSOFT", "Microsoft"),
    ("JPMorgan Chase &", "JPMorgan Chase"),                # trailing connector from suffix stripping
    ("ELI LILLY AND", "Eli Lilly"),
    ("BECTON, DICKINSON AND", "Becton, Dickinson"),
    ("SERVICENOW, I", "Servicenow"),
    ("US BANCORP \\DE\\", "US Bancorp"),                   # state tag
    ("KKR\xa0&", "KKR"),                                   # non-breaking space
    ("CMS\xa0ENERGY", "CMS Energy"),
    ("BANK OF NEW YORK MELLON", "Bank of New York Mellon"),
    ("ARCHER-DANIELS-MIDLAND", "Archer-Daniels-Midland"),
    ("PG&E", "PG&E"),
    ("3M", "3M"),
    ("CME", "CME"),                                        # single-word acronym stays upper
    ("NVR", "NVR"),
    ("MOODY’S", "Moody’s"),
])
def test_display_name(raw, expected):
    assert display_name(raw) == expected


@pytest.mark.parametrize("sec_title,expected", [
    ("AMPHENOL CORP /DE/", "Amphenol"),
    ("AUTOZONE INC", "Autozone"),
    ("Blackstone Inc.", "Blackstone"),
    ("CONAGRA BRANDS INC.", "Conagra Brands"),
    ("WELLS FARGO & COMPANY/MN", "Wells Fargo"),
    ("Deere & Co", "Deere"),
    ("TE Connectivity plc", "TE Connectivity"),
    ("NEWS CORP", "News Corp"),          # one short word left: keep the suffix
    ("Fox Corp", "Fox Corp"),
])
def test_sec_title_fallback(sec_title, expected):
    assert display_name(_mod.strip_corporate_suffix(sec_title)) == expected
