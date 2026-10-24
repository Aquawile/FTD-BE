"""Fiscal year end from the newest 10-K (scripts/update_fiscal_parameters.py)."""

from __future__ import annotations

import importlib.util
import pathlib
from datetime import date

import pytest

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location(
    "update_fiscal_parameters", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "update_fiscal_parameters.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
period_end = _mod.period_end
plan_updates = _mod.plan_updates
plausible = _mod.plausible
verify_period = _mod.verify_period
xbrl_period_end = _mod.xbrl_period_end


def _header(period_text: str) -> str:
    """A minimal inline XBRL header carrying dei:DocumentPeriodEndDate."""
    return ('<ix:header><ix:hidden><ix:nonNumeric contextRef="c-1" name="dei:DocumentPeriodEndDate" '
            f'format="ixt:date-monthname-day-year-en">{period_text}</ix:nonNumeric></ix:hidden></ix:header>')


@pytest.mark.parametrize("source_object,expected", [
    ("SEC/10-K/0000320193/000032019325000079/aapl-20250927.htm", "2025-09-27"),
    ("SEC/10-K/0000002488/000000248826000018/amd-20251227.htm", "2025-12-27"),
    ("SEC/10-K/0000072971/000007297126000133/wfc-20251231_d2.htm", "2025-12-31"),   # suffix after the date
    ("SEC/10-K/0000009389/000110465926017410/ball-20251231x10k.htm", "2025-12-31"),
    ("SEC/10-K/0001280452/000143774926006113/mpwr20251231_10k.htm", "2025-12-31"),  # no dash before the date
    ("SEC/10-K/0001000697/000119312526062604/d778470d10k.htm", None),             # no date at all
    ("SEC/10-K/0000320193/000032019325000079/aapl-20250927.html", "2025-09-27"),
    ("SEC/10-K/0000320193/000032019325000079/aapl-20250231.htm", None),           # not a date
    ("SEC/10-K/0000320193/000032019325000079/aapl.htm", None),                    # no date in the name
    ("", None),
    (None, None),
])
def test_period_end_reads_the_date_in_the_document_name(source_object, expected):
    assert period_end(source_object) == expected


def test_missing_cik_gets_a_row():
    assert plan_updates({"0000001800": ("0000001800-26-000001", "2025-12-31")}, {}) == [
        ("0000001800", "2025-12-31", "0000001800-26-000001")]


def test_unchanged_date_gets_no_row_even_for_a_new_accession():
    newest = {"0000320193": ("0000320193-26-000101", "2025-09-27")}
    assert plan_updates(newest, {"0000320193": "2025-09-27"}) == []


def test_changed_date_gets_a_row():
    newest = {"0000320193": ("0000320193-26-000101", "2026-06-22")}
    assert plan_updates(newest, {"0000320193": "2025-09-27"}) == [
        ("0000320193", "2026-06-22", "0000320193-26-000101")]


def test_cik_without_a_10k_is_left_alone():
    assert plan_updates({}, {"0000320193": "2025-09-27"}) == []


def test_plan_is_sorted_by_cik():
    newest = {"0000002": ("A-1", "2025-01-01"), "0000001": ("B-1", "2025-02-02")}
    assert [cik for cik, _, _ in plan_updates(newest, {})] == ["0000001", "0000002"]


@pytest.mark.parametrize("html,want", [
    (_header("December&#160;27, 2025"), "2025-12-27"),        # the usual cover-page form
    (_header("December 31, 2025"), "2025-12-31"),
    (_header("12/28/2025"), "2025-12-28"),                    # numeric form
    (_header("<span>October</span>&#160;3, 2025"), "2025-10-03"),  # tags inside the value
])
def test_agree_when_cover_page_matches_the_name(html, want):
    assert verify_period(html, want)[0] == "agree"


def test_disagree_when_cover_page_differs_from_the_name():
    status, text = verify_period(_header("June 22, 2026"), "2025-09-27")
    assert (status, text) == ("disagree", "June 22, 2026")


def test_unreadable_when_the_tag_is_missing():
    assert verify_period("<html><body>no inline XBRL here</body></html>", "2025-09-27") == ("unreadable", "")


def test_month_and_day_only_agrees_with_the_name_using_the_name_year():
    # the usual form: the tag has "December 31" and the year comes from the name
    assert verify_period(_header("December 31"), "2025-12-31") == ("agree", "December 31")


def test_month_and_day_only_disagreeing_day_is_a_disagreement():
    assert verify_period(_header("December 27"), "2025-12-31") == ("disagree", "December 27")


def test_unreadable_when_the_month_and_day_are_not_a_date():
    assert verify_period(_header("Sometime in December"), "2025-12-31") == ("unreadable", "Sometime in December")


def test_unreadable_when_the_file_could_not_be_read():
    assert verify_period(None, "2025-09-27") == ("unreadable", "")


@pytest.mark.parametrize("text,expected", [
    ("December 27, 2025", "2025-12-27"),
    ("12/28/2025", "2025-12-28"),
    ("Feb 30, 2025", None),                                   # not a real day
    ("sometime in 2025", None),
])
def test_xbrl_text_formats(text, expected):
    assert xbrl_period_end(text) == expected


def test_future_date_is_implausible():
    assert plausible("2099-01-01", date(2026, 10, 24)) is False


def test_date_before_2000_is_implausible():
    assert plausible("1999-12-31", date(2026, 10, 24)) is False


def test_today_and_2000_are_plausible():
    assert plausible("2000-01-01", date(2026, 10, 24)) is True
    assert plausible("2026-10-24", date(2026, 10, 24)) is True
