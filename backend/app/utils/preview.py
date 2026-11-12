import html
import ipaddress
import re
import time
import urllib.parse
from typing import Any, Dict, Optional
import httpx

DEFAULT_PREVIEW_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extracts an 11-char YouTube video ID from watch, shorts, youtu.be, or embed URLs."""
    if not url:
        return None
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return None
    host = (parsed.hostname or "").lower()
    if not ("youtube.com" in host or "youtu.be" in host):
        return None

    if "youtu.be" in host:
        vid = parsed.path.strip("/").split("/")[0]
        return vid if re.fullmatch(r"[a-zA-Z0-9_-]{11}", vid or "") else None

    if parsed.path.startswith("/watch"):
        qs = urllib.parse.parse_qs(parsed.query)
        vid = (qs.get("v") or [None])[0]
        return vid if re.fullmatch(r"[a-zA-Z0-9_-]{11}", vid or "") else None

    for prefix in ("/shorts/", "/embed/", "/live/"):
        if parsed.path.startswith(prefix):
            vid = parsed.path[len(prefix):].split("/")[0]
            return vid if re.fullmatch(r"[a-zA-Z0-9_-]{11}", vid or "") else None

    return None


def is_safe_public_http_url(url: str) -> bool:
    """Rejects non-HTTP(S) schemes and loopback/private/link-local IP targets."""
    if not url or len(url) > 2048:
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower().strip("[]")
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local") or host.endswith(".internal"):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
    except ValueError:
        pass
    return True


def _extract_meta(head_html: str, *names: str) -> Optional[str]:
    """Finds the content attribute for any matching meta property or name inside HTML head."""
    for name in names:
        esc = re.escape(name)
        patterns = [
            rf'<meta[^>]+(?:property|name)\s*=\s*["\']{esc}["\'][^>]+content\s*=\s*["\']([^"\']*)["\']',
            rf'<meta[^>]+content\s*=\s*["\']([^"\']*)["\'][^>]+(?:property|name)\s*=\s*["\']{esc}["\']',
        ]
        for pat in patterns:
            m = re.search(pat, head_html, re.IGNORECASE)
            if m and m.group(1).strip():
                return html.unescape(m.group(1).strip())
    return None


def _check_iframe_embeddable(headers: httpx.Headers) -> tuple[bool, Optional[str]]:
    """Checks X-Frame-Options and CSP frame-ancestors headers for cross-origin embed support."""
    xfo = (headers.get("x-frame-options") or "").lower()
    if "deny" in xfo or "sameorigin" in xfo or "allow-from" in xfo:
        return False, f"Restricted by X-Frame-Options ({xfo.upper()})"

    csp = headers.get("content-security-policy") or ""
    fa_match = re.search(r"frame-ancestors\s+([^;]+)", csp, re.IGNORECASE)
    if fa_match:
        ancestors = fa_match.group(1).strip().lower()
        tokens = ancestors.split()
        if "*" not in tokens and "https:" not in tokens:
            return False, "Restricted by Content-Security-Policy (frame-ancestors)"

    return True, None


async def fetch_tab_preview(url: str, title_hint: Optional[str] = None, timeout: float = 3.5) -> Dict[str, Any]:
    """
    Fetches lightweight page metadata and iframe-embeddability headers for a URL
    without launching a Chromium browser process.
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or url
    favicon_fallback = f"https://www.google.com/s2/favicons?domain={urllib.parse.quote(host)}&sz=64"
    yt_id = extract_youtube_video_id(url)

    result: Dict[str, Any] = {
        "url": url,
        "final_url": url,
        "domain": host,
        "site_name": "YouTube" if yt_id else host,
        "title": title_hint or host,
        "description": None,
        "image_url": f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg" if yt_id else None,
        "favicon_url": favicon_fallback,
        "embeddable": bool(yt_id),
        "embed_url": (
            f"https://www.youtube.com/embed/{yt_id}?autoplay=1&mute=1&playsinline=1&rel=0"
            if yt_id
            else None
        ),
        "embed_blocked_reason": None,
        "status_code": None,
        "response_ms": None,
        "video_id": yt_id,
    }

    if not is_safe_public_http_url(url):
        result["embeddable"] = False
        result["embed_blocked_reason"] = "Non-public URL cannot be framed"
        return result

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            headers=DEFAULT_PREVIEW_HEADERS,
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            resp = await client.get(url)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            final_url = str(resp.url)
            final_host = urllib.parse.urlparse(final_url).hostname or host

            result["final_url"] = final_url
            result["domain"] = final_host
            result["status_code"] = resp.status_code
            result["response_ms"] = elapsed_ms

            if resp.status_code < 400:
                text_body = resp.text or ""
                head_end = text_body.lower().find("</head>")
                head_chunk = text_body[: min(max(head_end + 7, 120000), 350000)] if head_end > 0 else text_body[:250000]
                title_tag = re.search(r"<title[^>]*>(.*?)</title>", head_chunk, re.IGNORECASE | re.DOTALL)
                raw_title = (
                    _extract_meta(head_chunk, "og:title", "twitter:title")
                    or (html.unescape(re.sub(r"\s+", " ", title_tag.group(1)).strip()) if title_tag else None)
                )
                if raw_title and raw_title.lower() not in (
                    "error", "just a moment...", "attention required!", "access denied", "403 forbidden"
                ):
                    result["title"] = raw_title

                site_name = _extract_meta(head_chunk, "og:site_name", "application-name")
                if site_name:
                    result["site_name"] = site_name

                desc = _extract_meta(head_chunk, "og:description", "twitter:description", "description")
                if desc:
                    result["description"] = desc[:280]

                og_img = _extract_meta(head_chunk, "og:image", "twitter:image", "twitter:image:src")
                if og_img:
                    resolved_img = urllib.parse.urljoin(final_url, og_img)
                    if resolved_img.startswith(("http://", "https://")):
                        result["image_url"] = resolved_img

                icon_match = re.search(
                    r'<link[^>]+rel\s*=\s*["\'][^"\']*\bicon\b[^"\']*["\'][^>]+href\s*=\s*["\']([^"\']+)["\']',
                    head_chunk,
                    re.IGNORECASE,
                ) or re.search(
                    r'<link[^>]+href\s*=\s*["\']([^"\']+)["\'][^>]+rel\s*=\s*["\'][^"\']*\bicon\b[^"\']*["\']',
                    head_chunk,
                    re.IGNORECASE,
                )
                if icon_match and icon_match.group(1).strip():
                    result["favicon_url"] = urllib.parse.urljoin(final_url, html.unescape(icon_match.group(1).strip()))

            # YouTube watch/shorts always embeds cleanly via /embed/{video_id}
            if yt_id:
                result["embeddable"] = True
                result["embed_url"] = f"https://www.youtube.com/embed/{yt_id}?autoplay=1&mute=1&playsinline=1&rel=0"
                result["embed_blocked_reason"] = None
            elif resp.status_code < 400:
                can_embed, reason = _check_iframe_embeddable(resp.headers)
                result["embeddable"] = can_embed
                result["embed_url"] = final_url if can_embed else None
                result["embed_blocked_reason"] = reason
            else:
                result["embeddable"] = False
                result["embed_blocked_reason"] = f"HTTP {resp.status_code} · Live session active in Chrome tab"
    except Exception as exc:
        result["response_ms"] = int((time.perf_counter() - started) * 1000)
        if not yt_id:
            result["embeddable"] = False
            result["embed_blocked_reason"] = f"Preview fetch fallback ({type(exc).__name__})"

    return result
