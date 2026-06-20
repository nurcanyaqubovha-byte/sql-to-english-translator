"""Claude-powered SQL -> natural language translator.

This engine sends the query to Anthropic's Claude model and returns its
explanation. It requires the ``ANTHROPIC_API_KEY`` environment variable and the
``anthropic`` package (``pip install -r requirements.txt``).
"""

import os

MODEL = "claude-opus-4-8"
MAX_TOKENS = 1024

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


class AIEngineError(Exception):
    """Raised when the AI engine cannot produce a translation."""


def _load_system_prompt(lang):
    path = os.path.join(_PROMPTS_DIR, f"sql_prompt_{lang}.txt")
    if not os.path.exists(path):
        path = os.path.join(_PROMPTS_DIR, "sql_prompt_en.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def is_available():
    """Return True if the AI engine can run (API key present)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def translate_ai(sql, lang="en"):
    """Translate a SQL query using the Claude API.

    Raises:
        AIEngineError: if the SDK is missing, the key is invalid, or the API
            call fails.
    """
    if lang not in ("en", "az"):
        lang = "en"

    try:
        import anthropic
    except ImportError as exc:
        raise AIEngineError(
            "The 'anthropic' package is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc

    if not is_available():
        raise AIEngineError(
            "ANTHROPIC_API_KEY is not set. Set it in your environment to use "
            "the AI engine, or use --engine rule for the offline engine."
        )

    system_prompt = _load_system_prompt(lang)

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": sql}],
        )
    except anthropic.AuthenticationError as exc:
        raise AIEngineError("Invalid API key. Check ANTHROPIC_API_KEY.") from exc
    except anthropic.RateLimitError as exc:
        raise AIEngineError("Rate limited by the API. Please retry shortly.") from exc
    except anthropic.APIError as exc:
        raise AIEngineError(f"API request failed: {exc}") from exc

    text_parts = [block.text for block in response.content if block.type == "text"]
    explanation = "".join(text_parts).strip()
    if not explanation:
        raise AIEngineError("The model returned an empty response.")
    return explanation
