import httpx
from typing import Dict, Any, List, Optional
from app.config import settings

class GitHubAPIAdapter:
    """
    Authorized Direct REST API Adapter for GitHub.
    Performs safe, read-oriented operations with rate-limit handling
    and confidential token protection.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "VECTOR-Autonomous-Web-Operator"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 404:
                return {"error": f"Repository '{owner}/{repo}' not found on GitHub."}
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                return {"error": "GitHub API rate limit reached. Fallback to browser automation recommended."}
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": data.get("id"),
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "open_issues": data.get("open_issues_count"),
                "language": data.get("language"),
                "default_branch": data.get("default_branch"),
                "html_url": data.get("html_url")
            }

    async def get_releases(self, owner: str, repo: str, limit: int = 5) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/releases"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 404:
                return [{"error": f"Releases not found for '{owner}/{repo}'"}]
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                return [{"error": "GitHub API rate limit reached."}]
            resp.raise_for_status()
            releases = resp.json()
            formatted = []
            for r in releases[:limit]:
                assets = [
                    {"name": a.get("name"), "size_bytes": a.get("size"), "download_url": a.get("browser_download_url")}
                    for a in r.get("assets", [])
                ]
                formatted.append({
                    "id": r.get("id"),
                    "tag_name": r.get("tag_name"),
                    "name": r.get("name"),
                    "published_at": r.get("published_at"),
                    "html_url": r.get("html_url"),
                    "assets": assets
                })
            return formatted
