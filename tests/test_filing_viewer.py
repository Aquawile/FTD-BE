from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.unit

URL = "/tickers/NVDA/filings/000104581026000021/content?cik=0001045810"
DOC = b"<?xml version='1.0' encoding='ASCII'?><html><body><script>alert(1)</script><p>Item 1. Business</p></body></html>"


def _get(stored_type, found=True, sec_type="text/html"):
    with patch("app.services.vectorized_gcs.get_filing_content_from_gcs", return_value=(DOC if found else b"", stored_type, found)), \
         patch("app.routes.tickers._get_sec_primary_doc", return_value="d.htm"), \
         patch("app.routes.tickers._fetch_sec_content", return_value=(DOC, sec_type)), \
         patch("app.services.audit.log_sec_content_proxy"):
        return TestClient(app).get(URL)  # public path: no token


def test_text_plain_object_is_served_as_a_rendered_page():
    res = _get("text/plain")
    assert res.status_code == 200 and res.content == DOC
    assert res.headers["content-type"].startswith("text/html")


def test_filing_is_locked_in_a_sandbox_and_stays_anonymous():
    csp = _get("text/plain").headers["content-security-policy"]
    assert csp.split(";")[0] == "sandbox"            # no allow-* flags: no scripts, opaque origin
    assert "allow-" not in csp and "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp and "form-action 'none'" in csp
    res = _get("text/plain")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["referrer-policy"] == "no-referrer"


def test_sec_gov_fallback_gets_the_same_protection():
    res = _get("", found=False, sec_type="text/html; charset=ISO-8859-1")
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/html; charset=ISO-8859-1"
    assert res.headers["content-security-policy"].startswith("sandbox")
