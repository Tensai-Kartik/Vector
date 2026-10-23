import pytest
from app.adapters.router import ExecutionRouter
from app.adapters.github_adapter import GitHubAPIAdapter

def test_github_api_routing_detection():
    # Should detect repository metadata request
    match_repo = ExecutionRouter.can_route_to_github_api("Search GitHub for octocat/Hello-World repo metadata")
    assert match_repo is not None
    assert match_repo[0] == "get_repository"
    assert match_repo[1] == "octocat"
    assert match_repo[2] == "Hello-World"

    # Should detect release request
    match_rel = ExecutionRouter.can_route_to_github_api("Get releases for owner/repo on github")
    assert match_rel is not None
    assert match_rel[0] == "get_releases"

    # Should return None for generic browser tasks
    match_browser = ExecutionRouter.can_route_to_github_api("Download latest invoice from accounts portal")
    assert match_browser is None

@pytest.mark.asyncio
async def test_route_and_execute_fallback_when_not_github():
    route = await ExecutionRouter.route_and_execute("Fill out procurement form and click submit")
    assert route["executed_via"] == "browser"
    assert "DOM interaction" in route["reason"]
