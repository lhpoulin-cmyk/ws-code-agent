from docwriter_web.ui_state import DEVELOPER, NORMAL, mode_cookie, mode_from_cookie
from test_web_app import app, request


def test_mode_preference_is_signed_and_contains_no_content():
    secret = b"g" * 32
    cookie = mode_cookie(DEVELOPER, secret)
    assert mode_from_cookie(cookie, secret) == DEVELOPER
    assert mode_from_cookie(cookie.replace("developer", "normal"), secret) == NORMAL
    assert "source" not in cookie and "proposal" not in cookie and "steering" not in cookie


def test_system_status_is_probe_based_and_refresh_is_csrf_protected(tmp_path):
    application = app(tmp_path)
    page = request(application, "/system")
    assert "Source:" in page["body"] and "UNKNOWN" in page["body"]
    assert "127.0.0.1:11434" not in page["body"]
    assert request(application, "/system/refresh", "POST", {"csrf": "wrong"})["status"].startswith("403")
    assert request(application, "/system/refresh", "POST", {"csrf": "x"})["status"].startswith("303")


def test_local_static_assets_are_available_without_editorial_data(tmp_path):
    application = app(tmp_path)
    css = request(application, "/static/docwriter.css")
    js = request(application, "/static/docwriter.js")
    assert css["status"].startswith("200") and "skip-link" in css["body"]
    assert js["status"].startswith("200") and "DOMContentLoaded" in js["body"]
