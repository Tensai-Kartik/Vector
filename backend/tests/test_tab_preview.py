import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.preview import (
    _check_iframe_embeddable,
    extract_youtube_video_id,
    is_safe_public_http_url,
)


def test_extract_youtube_video_id():
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=tg2MwT5FPdY") == "tg2MwT5FPdY"
    assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ?t=10") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://www.youtube.com/shorts/abcDEF12345") == "abcDEF12345"
    assert extract_youtube_video_id("https://web.whatsapp.com/") is None


def test_is_safe_public_http_url():
    assert is_safe_public_http_url("https://www.youtube.com/watch?v=tg2MwT5FPdY") is True
    assert is_safe_public_http_url("http://127.0.0.1:8000/api") is False
    assert is_safe_public_http_url("http://localhost:3000") is False
    assert is_safe_public_http_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_public_http_url("http://192.168.1.10/") is False
    assert is_safe_public_http_url("file:///C:/Windows/System32") is False


def test_check_iframe_embeddable():
    h_ok = httpx.Headers({"content-type": "text/html"})
    assert _check_iframe_embeddable(h_ok) == (True, None)

    h_xfo = httpx.Headers({"x-frame-options": "SAMEORIGIN"})
    can_embed, reason = _check_iframe_embeddable(h_xfo)
    assert can_embed is False
    assert "X-Frame-Options" in reason

    h_csp = httpx.Headers({"content-security-policy": "default-src 'self'; frame-ancestors 'none'"})
    can_embed_csp, reason_csp = _check_iframe_embeddable(h_csp)
    assert can_embed_csp is False
    assert "frame-ancestors" in reason_csp


def test_resolve_launch_includes_youtube_embed_metadata(monkeypatch):
    async def fake_yt(query: str, timeout: float = 5.0):
        return {
            "video_id": "tg2MwT5FPdY",
            "url": "https://www.youtube.com/watch?v=tg2MwT5FPdY",
            "search_url": "https://www.youtube.com/results?search_query=carryminati",
            "title": "CARRYMINATI",
            "resolved_direct": "true",
        }

    monkeypatch.setattr("app.api.routes.resolve_youtube_top_video", fake_yt)
    client = TestClient(app)
    res = client.post("/api/resolve-launch", json={"task": "play carryminati video on youtube"})
    assert res.status_code == 200
    data = res.json()
    assert data["should_open_tab"] is True
    assert data["video_id"] == "tg2MwT5FPdY"
    assert data["embed_url"] == "https://www.youtube.com/embed/tg2MwT5FPdY?autoplay=1&mute=1&playsinline=1&rel=0"
    assert data["thumbnail_url"] == "https://i.ytimg.com/vi/tg2MwT5FPdY/hqdefault.jpg"


def test_tab_preview_endpoint_and_validation(monkeypatch):
    client = TestClient(app)

    bad_res = client.post("/api/tab-preview", json={"url": ""})
    assert bad_res.status_code == 400

    local_res = client.post("/api/tab-preview", json={"url": "http://127.0.0.1:8000"})
    assert local_res.status_code == 200
    assert local_res.json()["embeddable"] is False

    async def fake_fetch_preview(url: str, title_hint=None, timeout: float = 3.5):
        return {
            "url": url,
            "final_url": url,
            "domain": "example.com",
            "site_name": "Example Domain",
            "title": "Example Title",
            "description": "Sample page preview",
            "image_url": "https://example.com/preview.png",
            "favicon_url": "https://example.com/favicon.ico",
            "embeddable": True,
            "embed_url": url,
            "embed_blocked_reason": None,
            "status_code": 200,
            "response_ms": 42,
            "video_id": None,
        }

    monkeypatch.setattr("app.api.routes.fetch_tab_preview", fake_fetch_preview)
    ok_res = client.post("/api/tab-preview", json={"url": "https://example.com", "title_hint": "Example"})
    assert ok_res.status_code == 200
    payload = ok_res.json()
    assert payload["embeddable"] is True
    assert payload["title"] == "Example Title"
    assert payload["status_code"] == 200

