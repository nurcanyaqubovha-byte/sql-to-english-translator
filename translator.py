"""Hybrid SQL -> natural language translator.

Picks between the offline rule-based engine and the Claude-powered AI engine:

* ``engine="auto"`` (default): use the AI engine when ``ANTHROPIC_API_KEY`` is
  set, otherwise fall back to the offline rule-based engine.
* ``engine="ai"``: force the AI engine. If it fails, fall back to rules with a
  warning so the user always gets *some* explanation.
* ``engine="rule"``: force the offline engine.
"""

import sys

import ai_engine
import rule_engine

VALID_ENGINES = ("auto", "ai", "rule")
VALID_LANGS = ("en", "az")


def translate(sql, lang="en", engine="auto"):
    """Translate ``sql`` into natural language.

    Args:
        sql: the SQL query text.
        lang: 'en' (English) or 'az' (Azerbaijani).
        engine: 'auto', 'ai', or 'rule'.

    Returns:
        The explanation string.
    """
    if lang not in VALID_LANGS:
        lang = "en"
    if engine not in VALID_ENGINES:
        engine = "auto"

    if engine == "rule":
        return rule_engine.translate_rule_based(sql, lang)

    if engine == "auto":
        if ai_engine.is_available():
            engine = "ai"
        else:
            return rule_engine.translate_rule_based(sql, lang)

    # engine == "ai" (either chosen explicitly or selected by auto)
    try:
        return ai_engine.translate_ai(sql, lang)
    except ai_engine.AIEngineError as exc:
        print(f"[warning] AI engine unavailable ({exc}). "
              f"Falling back to the offline engine.", file=sys.stderr)
        return rule_engine.translate_rule_based(sql, lang)
