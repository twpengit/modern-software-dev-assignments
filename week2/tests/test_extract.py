import pytest
from unittest.mock import MagicMock, patch

from ..app.services.extract import extract_action_items


def _mock_llm_response(json_text: str):
    """Build a fake Anthropic message response returning the given text."""
    block = MagicMock()
    block.type = "text"
    block.text = json_text
    msg = MagicMock()
    msg.content = [block]
    return msg


@pytest.fixture(autouse=True)
def mock_client():
    with patch("week2.app.services.extract._client") as m:
        yield m


# ---------------------------------------------------------------------------
# Bullet list
# ---------------------------------------------------------------------------

def test_llm_bullet_list(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response(
        '["Fix login bug", "Write tests", "Deploy to production"]'
    )
    result = extract_action_items("- Fix login bug\n- Write tests\n- Deploy to production")
    assert result == ["Fix login bug", "Write tests", "Deploy to production"]


# ---------------------------------------------------------------------------
# Keyword-prefixed lines (todo:, action:, next:)
# ---------------------------------------------------------------------------

def test_llm_keyword_prefixed_lines(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response(
        '["Call the client", "Send invoice", "Schedule follow-up"]'
    )
    text = "todo: Call the client\naction: Send invoice\nnext: Schedule follow-up"
    result = extract_action_items(text)
    assert result == ["Call the client", "Send invoice", "Schedule follow-up"]


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_llm_empty_input(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response("[]")
    result = extract_action_items("")
    assert result == []


# ---------------------------------------------------------------------------
# Numbered list
# ---------------------------------------------------------------------------

def test_llm_numbered_list(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response(
        '["Set up database", "Implement API", "Write documentation"]'
    )
    text = "1. Set up database\n2. Implement API\n3. Write documentation"
    result = extract_action_items(text)
    assert result == ["Set up database", "Implement API", "Write documentation"]


# ---------------------------------------------------------------------------
# Plain narrative — no action items
# ---------------------------------------------------------------------------

def test_llm_no_action_items(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response("[]")
    result = extract_action_items("The meeting went well. Everyone seemed happy.")
    assert result == []


# ---------------------------------------------------------------------------
# LLM returns response wrapped in markdown code fences
# ---------------------------------------------------------------------------

def test_llm_strips_markdown_fences(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response(
        '```json\n["Review PR", "Merge branch"]\n```'
    )
    result = extract_action_items("Review PR and merge branch.")
    assert result == ["Review PR", "Merge branch"]


# ---------------------------------------------------------------------------
# LLM returns a wrapper object like {"items": [...]}
# ---------------------------------------------------------------------------

def test_llm_wrapper_object(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response(
        '{"items": ["Update dependencies", "Run tests"]}'
    )
    result = extract_action_items("Update dependencies and run tests.")
    assert result == ["Update dependencies", "Run tests"]


# ---------------------------------------------------------------------------
# Mixed: checkboxes + keyword prefixes in one block of text
# ---------------------------------------------------------------------------

def test_llm_mixed_input(mock_client):
    mock_client.messages.create.return_value = _mock_llm_response(
        '["Set up database", "Implement API endpoint", "Write tests"]'
    )
    text = (
        "Notes from meeting:\n"
        "- [ ] Set up database\n"
        "* implement API endpoint\n"
        "1. Write tests\n"
        "Some narrative sentence."
    )
    result = extract_action_items(text)
    assert "Set up database" in result
    assert "Implement API endpoint" in result
    assert "Write tests" in result
