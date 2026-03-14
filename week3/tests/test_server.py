"""
Tests for week3/server/main.py

All HTTP calls are intercepted by httpx's MockTransport — no real network
requests are made.  Each test builds a fake GitHub API response and asserts
the tool function returns the expected shape.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from week3.server.main import (
    _handle_response,
    get_repository,
    list_issues,
    search_repositories,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_REQUEST = httpx.Request("GET", "https://api.github.com/test")


def _mock_response(status_code: int, body: object) -> httpx.Response:
    """Build a fake httpx.Response with the given status code and JSON body."""
    content = json.dumps(body).encode()
    return httpx.Response(status_code, content=content, request=_FAKE_REQUEST)


def _make_client(response: httpx.Response):
    """Return a context-manager mock whose .get() returns *response*."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = response
    return mock_client


# ---------------------------------------------------------------------------
# _handle_response
# ---------------------------------------------------------------------------

class TestHandleResponse:
    def test_ok_returns_json(self):
        resp = _mock_response(200, {"key": "value"})
        assert _handle_response(resp) == {"key": "value"}

    def test_404_raises_value_error(self):
        resp = _mock_response(404, {"message": "Not Found"})
        with pytest.raises(ValueError, match="404"):
            _handle_response(resp)

    def test_rate_limit_raises_runtime_error(self):
        resp = httpx.Response(403, content=b'{"message":"rate limit exceeded"}', request=_FAKE_REQUEST)
        with pytest.raises(RuntimeError, match="rate limit"):
            _handle_response(resp)

    def test_other_4xx_raises_http_status_error(self):
        resp = _mock_response(422, {"message": "Validation Failed"})
        with pytest.raises(httpx.HTTPStatusError):
            _handle_response(resp)


# ---------------------------------------------------------------------------
# search_repositories
# ---------------------------------------------------------------------------

REPO_ITEM = {
    "full_name": "tiangolo/fastapi",
    "description": "FastAPI framework",
    "stargazers_count": 80000,
    "language": "Python",
    "html_url": "https://github.com/tiangolo/fastapi",
    "open_issues_count": 500,
}


class TestSearchRepositories:
    def test_returns_formatted_results(self):
        fake_resp = _mock_response(200, {"items": [REPO_ITEM]})
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            results = search_repositories("fastapi")
        assert len(results) == 1
        assert results[0]["full_name"] == "tiangolo/fastapi"
        assert results[0]["stars"] == 80000
        assert results[0]["language"] == "Python"

    def test_empty_items_returns_message(self):
        fake_resp = _mock_response(200, {"items": []})
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            results = search_repositories("xyznonexistent123")
        assert len(results) == 1
        assert "message" in results[0]

    def test_max_results_clamped_to_30(self):
        fake_resp = _mock_response(200, {"items": [REPO_ITEM]})
        client_mock = _make_client(fake_resp)
        with patch("week3.server.main._client", return_value=client_mock):
            search_repositories("python", max_results=999)
        _, kwargs = client_mock.get.call_args
        assert kwargs["params"]["per_page"] == 30

    def test_max_results_clamped_to_1(self):
        fake_resp = _mock_response(200, {"items": [REPO_ITEM]})
        client_mock = _make_client(fake_resp)
        with patch("week3.server.main._client", return_value=client_mock):
            search_repositories("python", max_results=0)
        _, kwargs = client_mock.get.call_args
        assert kwargs["params"]["per_page"] == 1

    def test_no_description_falls_back(self):
        item = {**REPO_ITEM, "description": None}
        fake_resp = _mock_response(200, {"items": [item]})
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            results = search_repositories("fastapi")
        assert results[0]["description"] == "(no description)"

    def test_timeout_raises_runtime_error(self):
        client_mock = MagicMock()
        client_mock.__enter__ = MagicMock(return_value=client_mock)
        client_mock.__exit__ = MagicMock(return_value=False)
        client_mock.get.side_effect = httpx.TimeoutException("timed out")
        with patch("week3.server.main._client", return_value=client_mock):
            with pytest.raises(RuntimeError, match="Network error"):
                search_repositories("fastapi")


# ---------------------------------------------------------------------------
# get_repository
# ---------------------------------------------------------------------------

REPO_DETAIL = {
    "full_name": "anthropics/anthropic-sdk-python",
    "description": "The official Python library for the Anthropic API",
    "stargazers_count": 2100,
    "forks_count": 310,
    "open_issues_count": 28,
    "language": "Python",
    "license": {"spdx_id": "MIT"},
    "default_branch": "main",
    "homepage": "https://docs.anthropic.com",
    "html_url": "https://github.com/anthropics/anthropic-sdk-python",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z",
}


class TestGetRepository:
    def test_returns_all_fields(self):
        fake_resp = _mock_response(200, REPO_DETAIL)
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            result = get_repository("anthropics", "anthropic-sdk-python")
        assert result["full_name"] == "anthropics/anthropic-sdk-python"
        assert result["stars"] == 2100
        assert result["license"] == "MIT"
        assert result["default_branch"] == "main"

    def test_missing_license_falls_back(self):
        detail = {**REPO_DETAIL, "license": None}
        fake_resp = _mock_response(200, detail)
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            result = get_repository("anthropics", "anthropic-sdk-python")
        assert result["license"] == "none"

    def test_missing_language_falls_back(self):
        detail = {**REPO_DETAIL, "language": None}
        fake_resp = _mock_response(200, detail)
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            result = get_repository("anthropics", "anthropic-sdk-python")
        assert result["language"] == "unknown"

    def test_404_propagates(self):
        fake_resp = _mock_response(404, {"message": "Not Found"})
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            with pytest.raises(ValueError, match="404"):
                get_repository("nobody", "nonexistent-repo-xyz")

    def test_network_error_raises_runtime_error(self):
        client_mock = MagicMock()
        client_mock.__enter__ = MagicMock(return_value=client_mock)
        client_mock.__exit__ = MagicMock(return_value=False)
        client_mock.get.side_effect = httpx.NetworkError("connection refused")
        with patch("week3.server.main._client", return_value=client_mock):
            with pytest.raises(RuntimeError, match="Network error"):
                get_repository("anthropics", "anthropic-sdk-python")


# ---------------------------------------------------------------------------
# list_issues
# ---------------------------------------------------------------------------

ISSUE = {
    "number": 42,
    "title": "Fix async lifespan support",
    "state": "open",
    "user": {"login": "octocat"},
    "labels": [{"name": "bug"}, {"name": "help wanted"}],
    "comments": 3,
    "created_at": "2025-01-10T08:22:00Z",
    "html_url": "https://github.com/tiangolo/fastapi/issues/42",
}

PULL_REQUEST = {**ISSUE, "number": 99, "pull_request": {"url": "..."}}


class TestListIssues:
    def test_returns_formatted_issues(self):
        fake_resp = _mock_response(200, [ISSUE])
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            results = list_issues("tiangolo", "fastapi")
        assert len(results) == 1
        assert results[0]["number"] == 42
        assert results[0]["labels"] == ["bug", "help wanted"]
        assert results[0]["author"] == "octocat"

    def test_pull_requests_are_excluded(self):
        fake_resp = _mock_response(200, [ISSUE, PULL_REQUEST])
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            results = list_issues("tiangolo", "fastapi")
        assert all(r.get("number") != 99 for r in results)
        assert len(results) == 1

    def test_empty_results_returns_message(self):
        fake_resp = _mock_response(200, [])
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            results = list_issues("tiangolo", "fastapi", state="closed")
        assert "message" in results[0]

    def test_only_pull_requests_returns_message(self):
        fake_resp = _mock_response(200, [PULL_REQUEST])
        with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
            results = list_issues("tiangolo", "fastapi")
        assert "message" in results[0]

    def test_invalid_state_raises_value_error(self):
        with pytest.raises(ValueError, match="state must be"):
            list_issues("tiangolo", "fastapi", state="invalid")

    def test_valid_states_accepted(self):
        for state in ("open", "closed", "all"):
            fake_resp = _mock_response(200, [ISSUE])
            with patch("week3.server.main._client", return_value=_make_client(fake_resp)):
                results = list_issues("tiangolo", "fastapi", state=state)
            assert isinstance(results, list)

    def test_max_results_clamped(self):
        fake_resp = _mock_response(200, [ISSUE])
        client_mock = _make_client(fake_resp)
        with patch("week3.server.main._client", return_value=client_mock):
            list_issues("tiangolo", "fastapi", max_results=100)
        _, kwargs = client_mock.get.call_args
        assert kwargs["params"]["per_page"] == 30

    def test_timeout_raises_runtime_error(self):
        client_mock = MagicMock()
        client_mock.__enter__ = MagicMock(return_value=client_mock)
        client_mock.__exit__ = MagicMock(return_value=False)
        client_mock.get.side_effect = httpx.TimeoutException("timed out")
        with patch("week3.server.main._client", return_value=client_mock):
            with pytest.raises(RuntimeError, match="Network error"):
                list_issues("tiangolo", "fastapi")
