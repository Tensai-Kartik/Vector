from typing import Dict, Any, Tuple, Optional
import re
from app.adapters.github_adapter import GitHubAPIAdapter

class ExecutionRouter:
    """
    Evaluates whether an incoming task or step should be routed to an
    authorized direct API adapter (API-first) or to the Playwright browser engine.
    """

    GITHUB_REPO_REGEX = re.compile(r"(?:github\.com/|repo(?:sitory)?\s+)?([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)", re.IGNORECASE)

    @classmethod
    def can_route_to_github_api(cls, task_or_intent: str) -> Optional[Tuple[str, str, str]]:
        """
        Detects if task matches GitHub API read operations:
        Returns (operation_type, owner, repo) or None
        """
        lower = task_or_intent.lower()
        if "github" in lower:
            # Check for releases
            match = cls.GITHUB_REPO_REGEX.search(task_or_intent)
            if match:
                owner, repo = match.group(1), match.group(2)
                # Filter out obvious false positives like 'blob/main'
                if owner.lower() in ["https:", "http:", "github.com"]:
                    return None
                if "release" in lower:
                    return ("get_releases", owner, repo)
                if any(w in lower for w in ["star", "repo", "lookup", "info", "metadata", "search"]):
                    return ("get_repository", owner, repo)
        return None

    @classmethod
    async def route_and_execute(
        cls,
        task_or_intent: str,
        step_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Attempts execution via authorized API adapters.
        Returns execution result dictionary or indicates fallback to browser.
        """
        github_match = cls.can_route_to_github_api(task_or_intent)

        if github_match:
            op_type, owner, repo = github_match
            adapter = GitHubAPIAdapter()

            if op_type == "get_repository":
                res = await adapter.get_repository(owner, repo)
                if "error" not in res:
                    return {
                        "executed_via": "api",
                        "adapter": "GitHub REST API",
                        "operation": f"repos/{owner}/{repo}",
                        "reason": f"Safe read operation for repository metadata routed API-first to official GitHub REST endpoint.",
                        "success": True,
                        "data": res
                    }
                else:
                    return {
                        "executed_via": "fallback_needed",
                        "reason": f"API adapter returned: {res['error']}. Re-routing to browser automation.",
                        "success": False
                    }

            elif op_type == "get_releases":
                res = await adapter.get_releases(owner, repo)
                if res and "error" not in res[0]:
                    return {
                        "executed_via": "api",
                        "adapter": "GitHub REST API",
                        "operation": f"repos/{owner}/{repo}/releases",
                        "reason": f"Release listing routed API-first for optimal reliability and structured payload extraction.",
                        "success": True,
                        "data": res
                    }
                else:
                    return {
                        "executed_via": "fallback_needed",
                        "reason": "Releases API query failed or rate limited. Re-routing to browser automation.",
                        "success": False
                    }

        return {
            "executed_via": "browser",
            "reason": "Operation requires DOM interaction, visual validation, or has no direct API adapter available.",
            "success": True
        }
