"""Tests del SecurityHeadersMiddleware (Plan 04, item 7 - endurecer CSP)."""
from django.http import HttpResponse

from agrimIT.middleware import SecurityHeadersMiddleware


def _csp():
    mw = SecurityHeadersMiddleware(lambda request: HttpResponse("ok"))
    resp = mw(object())  # el middleware no usa el request para los headers
    return resp["Content-Security-Policy"]


def test_csp_incluye_directivas_endurecidas():
    csp = _csp()
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "frame-ancestors 'self'" in csp
    assert "form-action 'self'" in csp


def test_csp_mantiene_default_src_self():
    assert "default-src 'self'" in _csp()


def test_otros_headers_de_seguridad_presentes():
    mw = SecurityHeadersMiddleware(lambda request: HttpResponse("ok"))
    resp = mw(object())
    assert resp["X-Frame-Options"] == "DENY"
    assert resp["X-Content-Type-Options"] == "nosniff"
    assert resp["Referrer-Policy"] == "strict-origin-when-cross-origin"
