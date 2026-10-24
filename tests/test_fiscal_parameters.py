"""Fiscal year end from the newest 10-K (scripts/update_fiscal_parameters.py)."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location(
    "update_fiscal_parameters", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "update_fiscal_parameters.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
period_end = _mod.period_end
plan_updates = _mod.plan_updates


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
