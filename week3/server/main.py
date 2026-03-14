"""
Week 3 — GitHub MCP Server (STDIO transport)

Wraps the GitHub REST API and exposes three tools:
  • search_repositories  — full-text repo search
  • get_repository       — fetch metadata for owner/repo
  • list_issues          — list open (or closed) issues for a repo

Run:
    python -m week3.server.main          (via poetry)
    mcp dev week3/server/main.py         (MCP inspector)

Environment variables:
    GITHUB_TOKEN   Optional personal-access token; raises rate limit
                   from 60 → 5000 requests/hour.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — write to stderr only; stdout is reserved for STDIO transport.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("github-mcp")

# ---------------------------------------------------------------------------
# GitHub HTTP client
# ---------------------------------------------------------------------------
_GITHUB_API = "https://api.github.com"
_TOKEN = os.getenv("GITHUB_TOKEN")

_headers: dict[str, str] = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if _TOKEN:
    _headers["Authorization"] = f"Bearer {_TOKEN}"
    log.info("GitHub token loaded — using authenticated requests (5 000 req/h).")
else:
    log.warning("GITHUB_TOKEN not set — unauthenticated requests limited to 60 req/h.")


def _client() -> httpx.Client:
    return httpx.Client(base_url=_GITHUB_API, headers=_headers, timeout=10.0)


def _handle_response(resp: httpx.Response) -> Any:
    """Raise a descriptive error for non-2xx responses."""
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RuntimeError(
            "GitHub rate limit exceeded. Set GITHUB_TOKEN for 5 000 req/h, "
            "or wait until the limit resets."
        )
    if resp.status_code == 404:
        raise ValueError("Resource not found (404). Check the owner/repo name.")
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("GitHub MCP Server")


@mcp.tool()
def search_repositories(query: str, max_results: int = 10) -> list[dict]:
    """
    Search GitHub repositories by keyword.

    Args:
        query:       Search terms (e.g. "fastapi async", "language:python stars:>1000").
        max_results: Maximum number of results to return (1–30, default 10).

    Returns:
        A list of repository summaries with name, description, stars, URL, and language.
    """
    max_results = max(1, min(max_results, 30))
    log.info("search_repositories: query=%r max=%d", query, max_results)

    with _client() as c:
        try:
            data = _handle_response(
                c.get("/search/repositories", params={"q": query, "per_page": max_results})
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RuntimeError(f"Network error contacting GitHub: {exc}") from exc

    items = data.get("items", [])
    if not items:
        return [{"message": f"No repositories found for query: {query!r}"}]

    return [
        {
            "full_name": r["full_name"],
            "description": r.get("description") or "(no description)",
            "stars": r["stargazers_count"],
            "language": r.get("language") or "unknown",
            "url": r["html_url"],
            "open_issues": r["open_issues_count"],
        }
        for r in items
    ]


@mcp.tool()
def get_repository(owner: str, repo: str) -> dict:
    """
    Fetch detailed metadata for a specific GitHub repository.

    Args:
        owner: GitHub username or organisation (e.g. "anthropics").
        repo:  Repository name (e.g. "anthropic-sdk-python").

    Returns:
        Repository details: description, stars, forks, language, license,
        open issues, default branch, and homepage.
    """
    log.info("get_repository: %s/%s", owner, repo)

    with _client() as c:
        try:
            r = _handle_response(c.get(f"/repos/{owner}/{repo}"))
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RuntimeError(f"Network error contacting GitHub: {exc}") from exc

    return {
        "full_name": r["full_name"],
        "description": r.get("description") or "(no description)",
        "stars": r["stargazers_count"],
        "forks": r["forks_count"],
        "open_issues": r["open_issues_count"],
        "language": r.get("language") or "unknown",
        "license": (r.get("license") or {}).get("spdx_id") or "none",
        "default_branch": r["default_branch"],
        "homepage": r.get("homepage") or "",
        "url": r["html_url"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


@mcp.tool()
def list_issues(owner: str, repo: str, state: str = "open", max_results: int = 10) -> list[dict]:
    """
    List issues for a GitHub repository.

    Args:
        owner:       GitHub username or organisation.
        repo:        Repository name.
        state:       "open", "closed", or "all" (default "open").
        max_results: Maximum number of issues to return (1–30, default 10).

    Returns:
        A list of issues with number, title, state, author, labels, and URL.
    """
    if state not in ("open", "closed", "all"):
        raise ValueError("state must be 'open', 'closed', or 'all'.")
    max_results = max(1, min(max_results, 30))
    log.info("list_issues: %s/%s state=%s max=%d", owner, repo, state, max_results)

    with _client() as c:
        try:
            issues = _handle_response(
                c.get(
                    f"/repos/{owner}/{repo}/issues",
                    params={"state": state, "per_page": max_results},
                )
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RuntimeError(f"Network error contacting GitHub: {exc}") from exc

    # GitHub's /issues endpoint includes pull requests; filter them out.
    issues = [i for i in issues if "pull_request" not in i]

    if not issues:
        return [{"message": f"No {state} issues found for {owner}/{repo}."}]

    return [
        {
            "number": i["number"],
            "title": i["title"],
            "state": i["state"],
            "author": i["user"]["login"],
            "labels": [lbl["name"] for lbl in i.get("labels", [])],
            "comments": i["comments"],
            "created_at": i["created_at"],
            "url": i["html_url"],
        }
        for i in issues
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
