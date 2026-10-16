"""Ticker -> CIK mapping (CLAUDE.md known issue #9).

The lakehouse loader zipped the full ticker list against resolve_target_ciks()'s
CIK list, which skips unresolved tickers and repeated CIKs, shifting every later
ticker onto a neighbour's CIK. These tests pin the fix.
"""
import importlib.util
import os
import sys
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sec"))
from src.company_roster import build_ticker_cik_map, resolve_target_ciks  # noqa: E402

_spec = importlib.util.spec_from_file_location("sync_recent_relational", os.path.join(ROOT, "scripts", "sync_recent_relational.py"))
srr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srr)

TICKERS = ["AAPL", "XYZQ", "GOOG", "GOOGL", "NVDA"]  # XYZQ unresolved; GOOG/GOOGL share a CIK
SEC_MAP = {"AAPL": "0000320193", "GOOG": "0001652044", "GOOGL": "0001652044", "NVDA": "0001045810"}


def test_old_zip_pairing_shifts_ciks():
    ciks, _ = resolve_target_ciks(TICKERS, SEC_MAP)
    zipped = dict(zip(TICKERS, ciks))
    assert zipped["XYZQ"] == "0001652044"  # GOOG's CIK on the unresolved ticker
    assert zipped["GOOG"] == "0001045810"  # NVDA's CIK on GOOG
    assert "NVDA" not in zipped            # last ticker dropped entirely


def test_build_ticker_cik_map_looks_up_each_ticker():
    assert build_ticker_cik_map(TICKERS, SEC_MAP) == {
        "AAPL": "0000320193",
        "GOOG": "0001652044",
        "GOOGL": "0001652044",
        "NVDA": "0001045810",
    }


def _bucket(names):
    return SimpleNamespace(list_blobs=lambda prefix: [SimpleNamespace(name=n) for n in names if n.startswith(prefix)])


def test_gcs_map_uses_cik_folder_of_ticker_named_filings():
    names = [
        "SEC/10-K/0000320193/000032019325000079/aapl-20250927.htm",
        "SEC/10-K/0001045810/000104581026000021/nvda-20260125.htm",
        "SEC/8-K/0000008670/000095014226001884/eh260799361_8k.htm",  # no ticker in filename
        "SEC/10-K/0000111111/000011111126000001/dup-20260101.htm",
        "SEC/10-K/0000222222/000022222226000001/dup-20260101.htm",   # same ticker, two CIKs
        "SEC/logs/error_log_10k.txt",
    ]
    assert srr.load_gcs_ticker_cik_map(_bucket(names)) == {"AAPL": "0000320193", "NVDA": "0001045810"}
