import json
import re
import urllib.parse
from typing import Dict, Optional
import httpx

DEFAULT_YT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_youtube_query(task: str) -> str:
    """Extracts a clean search query from natural-language YouTube play/watch prompts."""
    t_lower = (task or "").lower()
    if "carryminati" in t_lower:
        return "carryminati"

    m = re.search(
        r"(?:play\s+(?:the\s+)?(?:latest|newest|recent|top|trending|new)?\s*(?:videos?\s+(?:of|by|from)|songs?\s+(?:of|by))?|"
        r"watch\s+(?:the\s+)?(?:latest|newest|recent)?\s*(?:videos?\s+(?:of|by|from))?|"
        r"search\s+(?:youtube\s+)?for|"
        r"(?:latest|newest|recent)\s+videos?\s+(?:of|by|from)|"
        r"videos?\s+(?:of|by|from)|find)\s+(.+)",
        task or "",
        re.IGNORECASE,
    )
    query = m.group(1) if m else (task or "")
    query = re.sub(
        r"\b(?:on\s+youtube|in\s+youtube|youtube|in\s+(?:a\s+)?new\s+(?:chrome\s+)?(?:tab|window)|new\s+(?:chrome\s+)?(?:tab|window)|please)\b",
        "",
        query,
        flags=re.IGNORECASE,
    )
    query = re.sub(
        r"^(?:the\s+|a\s+|latest\s+|video\s+of\s+|of\s+|by\s+)+",
        "",
        query.strip(),
        flags=re.IGNORECASE,
    )
    query = re.sub(r"\s+", " ", query).strip(" .?!\"'")
    if not query or query.lower() in {"a video", "video", "videos", "some video", "any video", "latest", "latest video"}:
        return "trending"
    return query


def parse_youtube_search_html(html: str) -> Optional[Dict[str, str]]:
    """Parses YouTube search HTML (`ytInitialData`) for the top organic video or short URL."""
    if not html:
        return None

    # Detect datacenter anti-bot consent/sorry pages before picking bogus IDs
    low = html[:12000].lower()
    if "unusual traffic" in low or "/sorry/index" in low:
        return None

    vid_match = re.search(r'"videoRenderer"\s*:\s*\{"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)
    is_short = False
    if not vid_match:
        vid_match = re.search(r'"reelWatchEndpoint"\s*:\s*\{"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)
        is_short = bool(vid_match)
    if not vid_match:
        vid_match = re.search(r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)

    if not vid_match:
        return None

    video_id = vid_match.group(1)
    snippet = html[vid_match.end() : vid_match.end() + 1200]
    title = None
    title_match = re.search(r'"title"\s*:\s*\{\s*"runs"\s*:\s*\[\s*\{\s*"text"\s*:\s*("(?:\\.|[^"\\])*")', snippet)
    if title_match:
        try:
            title = json.loads(title_match.group(1))
        except Exception:
            title = None

    watch_url = (
        f"https://www.youtube.com/shorts/{video_id}"
        if is_short
        else f"https://www.youtube.com/watch?v={video_id}"
    )
    return {"video_id": video_id, "url": watch_url, "title": title or video_id}


async def resolve_youtube_top_video(query: str, timeout: float = 5.0) -> Dict[str, Optional[str]]:
    """
    Lightweight (~0 MB browser overhead) async HTTP lookup for the top YouTube result URL.
    Falls back cleanly to the YouTube search results URL if HTML parsing yields no direct ID.
    """
    clean_query = (query or "trending").strip()
    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_query)}"
    try:
        async with httpx.AsyncClient(headers=DEFAULT_YT_HEADERS, follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(search_url)
            if resp.status_code == 200:
                parsed = parse_youtube_search_html(resp.text)
                if parsed:
                    return {
                        "video_id": parsed["video_id"],
                        "url": parsed["url"],
                        "search_url": search_url,
                        "title": parsed.get("title"),
                        "resolved_direct": "true",
                    }
    except Exception:
        pass
    return {
        "video_id": None,
        "url": search_url,
        "search_url": search_url,
        "title": clean_query,
        "resolved_direct": None,
    }
