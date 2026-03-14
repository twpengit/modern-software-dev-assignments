from __future__ import annotations

import json
import os
import re
from typing import List

from dotenv import load_dotenv
import anthropic

load_dotenv()

_client = anthropic.Anthropic(
    api_key=os.environ["MINIMAX_API_KEY"],
    base_url="https://api.minimaxi.com/anthropic",
)


def extract_action_items_llm(text: str) -> List[str]:
    """LLM-powered extraction using MiniMax API via Anthropic SDK."""
    message = _client.messages.create(
        model="MiniMax-M2.5",
        max_tokens=1024,
        system=(
            "You are an assistant that extracts action items from notes. "
            "Return ONLY a JSON array of strings, one action item per element. "
            "Return [] if there are no action items. "
            "Do not include any explanation or markdown formatting."
        ),
        messages=[{"role": "user", "content": text}],
    )
    raw = next((block.text for block in message.content if block.type == "text"), "[]").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n?", "", raw)
        raw = raw.rstrip("`").strip()
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    for v in parsed.values():
        if isinstance(v, list):
            return [str(item) for item in v]
    return []


def extract_action_items(text: str) -> List[str]:
    message = _client.messages.create(
        model="MiniMax-M2.5",
        max_tokens=1024,
        system=(
            "Extract all action items from the user's text. "
            "Return ONLY a JSON array of strings, one item per element. "
            "Return [] if there are no action items. "
            "Do not include any explanation or markdown formatting."
        ),
        messages=[{"role": "user", "content": text}],
    )
    raw = next((block.text for block in message.content if block.type == "text"), "[]").strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n?", "", raw)
        raw = raw.rstrip("`").strip()
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    # Handle {"items": [...]} or similar wrapper object
    for v in parsed.values():
        if isinstance(v, list):
            return [str(item) for item in v]
    return []
