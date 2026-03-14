# Week 3 — GitHub MCP Server

A Model Context Protocol (MCP) server that wraps the **GitHub REST API**, exposing three tools for searching repositories, fetching repository metadata, and listing issues. Runs locally over **STDIO transport** and integrates with Claude Desktop or any MCP-compatible client.

## Prerequisites

- Python 3.10+, Conda environment `cs146s`
- `mcp[cli]` installed: `pip install "mcp[cli]"`
- _(Optional)_ A [GitHub personal access token](https://github.com/settings/tokens) for higher rate limits

## Environment Setup

Add to `.env` at the **repo root** (optional but recommended):

```
GITHUB_TOKEN=ghp_your_token_here
```

Without a token, GitHub allows **60 requests/hour**. With a token, the limit is **5 000 requests/hour**.

## Running the Server

### MCP Inspector (development / testing)

```bash
conda activate cs146s
mcp dev week3/server/main.py
```

Opens the MCP Inspector UI at `http://localhost:5173` where you can call tools interactively.

### Direct STDIO run

```bash
conda activate cs146s
python -m week3.server.main
```

## Claude Desktop Integration

Add the following to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "/path/to/conda/envs/cs146s/bin/python",
      "args": ["-m", "week3.server.main"],
      "cwd": "/path/to/modern-software-dev-assignments",
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

Replace paths with your actual conda env and repo locations. Restart Claude Desktop after saving.

## Tool Reference

### `search_repositories`

Search GitHub repositories by keyword or advanced query syntax.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search terms, e.g. `"fastapi async"` or `"language:python stars:>1000"` |
| `max_results` | integer | 10 | Number of results (1–30) |

**Example input:**
```
query: "model context protocol python"
max_results: 5
```

**Example output:**
```json
[
  {
    "full_name": "modelcontextprotocol/python-sdk",
    "description": "The official Python SDK for Model Context Protocol servers and clients",
    "stars": 3821,
    "language": "Python",
    "url": "https://github.com/modelcontextprotocol/python-sdk",
    "open_issues": 42
  }
]
```

---

### `get_repository`

Fetch detailed metadata for a specific repository.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `owner` | string | required | GitHub username or org, e.g. `"anthropics"` |
| `repo` | string | required | Repository name, e.g. `"anthropic-sdk-python"` |

**Example input:**
```
owner: "anthropics"
repo: "anthropic-sdk-python"
```

**Example output:**
```json
{
  "full_name": "anthropics/anthropic-sdk-python",
  "description": "The official Python library for the Anthropic API",
  "stars": 2100,
  "forks": 310,
  "open_issues": 28,
  "language": "Python",
  "license": "MIT",
  "default_branch": "main",
  "url": "https://github.com/anthropics/anthropic-sdk-python"
}
```

Returns `404` error if the repository does not exist.

---

### `list_issues`

List issues for a repository, optionally filtered by state.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `owner` | string | required | GitHub username or org |
| `repo` | string | required | Repository name |
| `state` | string | `"open"` | `"open"`, `"closed"`, or `"all"` |
| `max_results` | integer | 10 | Number of results (1–30) |

**Example input:**
```
owner: "tiangolo"
repo: "fastapi"
state: "open"
max_results: 5
```

**Example output:**
```json
[
  {
    "number": 12345,
    "title": "Add support for async lifespan in testing",
    "state": "open",
    "author": "someuser",
    "labels": ["feature", "help wanted"],
    "comments": 3,
    "created_at": "2025-01-10T08:22:00Z",
    "url": "https://github.com/tiangolo/fastapi/issues/12345"
  }
]
```

Pull requests are automatically excluded from results.

## Error Handling

| Condition | Behaviour |
|-----------|-----------|
| Repository not found | Raises `ValueError` with a descriptive message |
| Rate limit exceeded | Raises `RuntimeError` advising to set `GITHUB_TOKEN` |
| Network timeout / unreachable | Raises `RuntimeError` with the underlying error |
| Invalid `state` parameter | Raises `ValueError` immediately, before any API call |
| No results found | Returns a single-element list with a `"message"` key |

## Project Structure

```
week3/
├── server/
│   └── main.py   # MCP server — tools, GitHub client, logging
└── README.md
```
