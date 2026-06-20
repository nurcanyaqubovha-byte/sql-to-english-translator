"""Lightweight SQL error detection.

Catches common beginner mistakes and reports them in plain English or
Azerbaijani. This is a heuristic checker -- it does not fully validate SQL
against a grammar, but it flags the issues people hit most often:

* empty input
* unbalanced parentheses
* unbalanced single quotes
* a trailing comma before FROM
* ``= NULL`` / ``!= NULL`` (should be ``IS NULL`` / ``IS NOT NULL``)
* a statement that does not start with a known SQL keyword

Use ``check_sql(sql, lang)`` -> list of human-readable problem strings (empty
list means no problems were detected).
"""

import re

import sqlparse

MESSAGES = {
    "en": {
        "empty": "The query is empty.",
        "unbalanced_parens": (
            "Unbalanced parentheses: {opened} '(' and {closed} ')'."
        ),
        "unbalanced_quotes": (
            "Unbalanced single quotes -- a string literal is not closed."
        ),
        "trailing_comma": (
            "There is a comma right before FROM. Remove the trailing comma in "
            "the column list."
        ),
        "eq_null": (
            "Using '{op} NULL' does not work in SQL. Use 'IS NULL' or "
            "'IS NOT NULL' instead."
        ),
        "unknown_start": (
            "The statement does not start with a known SQL keyword "
            "(SELECT, INSERT, UPDATE, DELETE, CREATE, ...). Check for a typo."
        ),
        "select_no_from": (
            "This looks like a SELECT with column names but no FROM clause. "
            "Did you forget 'FROM <table>'?"
        ),
    },
    "az": {
        "empty": "Sorğu boşdur.",
        "unbalanced_parens": (
            "Mötərizələr balanssızdır: {opened} ədəd '(' və {closed} ədəd ')'."
        ),
        "unbalanced_quotes": (
            "Tək dırnaqlar balanssızdır -- mətn dəyəri bağlanmayıb."
        ),
        "trailing_comma": (
            "FROM-dan dərhal əvvəl vergül var. Sütun siyahısındakı artıq vergülü "
            "silin."
        ),
        "eq_null": (
            "SQL-də '{op} NULL' işləmir. Əvəzində 'IS NULL' və ya 'IS NOT NULL' "
            "istifadə edin."
        ),
        "unknown_start": (
            "İfadə tanınan SQL açar sözü ilə başlamır "
            "(SELECT, INSERT, UPDATE, DELETE, CREATE, ...). Yazı səhvini yoxlayın."
        ),
        "select_no_from": (
            "Bu, sütun adları olan, amma FROM hissəsi olmayan SELECT-ə oxşayır. "
            "'FROM <cədvəl>' yazmağı unutmusunuz?"
        ),
    },
}

_KNOWN_STARTS = (
    "select", "insert", "update", "delete", "create", "drop", "alter",
    "with", "truncate", "merge", "explain", "grant", "revoke",
)


def _strip_strings(sql):
    """Return ``sql`` with single-quoted string literals blanked out.

    Keeps the same length so character positions are preserved, and treats the
    SQL escape ``''`` (a doubled quote inside a string) correctly.
    """
    out = []
    in_string = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            if in_string and i + 1 < len(sql) and sql[i + 1] == "'":
                # Escaped quote inside a string -> consume both, stay inside.
                out.append("  ")
                i += 2
                continue
            in_string = not in_string
            out.append("'")
        elif in_string:
            out.append(" ")
        else:
            out.append(ch)
        i += 1
    return "".join(out), in_string


def check_sql(sql, lang="en"):
    """Return a list of detected problems (empty list = looks OK)."""
    if lang not in MESSAGES:
        lang = "en"
    msg = MESSAGES[lang]
    issues = []

    if not sql or not sql.strip():
        return [msg["empty"]]

    stripped, unclosed_string = _strip_strings(sql)

    # Unbalanced single quotes.
    if unclosed_string:
        issues.append(msg["unbalanced_quotes"])

    # Unbalanced parentheses (ignoring those inside string literals).
    opened = stripped.count("(")
    closed = stripped.count(")")
    if opened != closed:
        issues.append(msg["unbalanced_parens"].format(opened=opened, closed=closed))

    # Trailing comma before FROM, e.g. "SELECT a, b, FROM t".
    if re.search(r",\s*\bfrom\b", stripped, re.IGNORECASE):
        issues.append(msg["trailing_comma"])

    # "= NULL" / "!= NULL" / "<> NULL".
    eq_null = re.search(r"(=|!=|<>)\s*null\b", stripped, re.IGNORECASE)
    if eq_null:
        issues.append(msg["eq_null"].format(op=eq_null.group(1)))

    # Statement should start with a known keyword.
    first_word = re.match(r"\s*([A-Za-z_]+)", stripped)
    if first_word and first_word.group(1).lower() not in _KNOWN_STARTS:
        issues.append(msg["unknown_start"])

    # SELECT with apparent column names but no FROM.
    if _is_select_without_from(stripped):
        issues.append(msg["select_no_from"])

    return issues


def _is_select_without_from(stripped):
    """Heuristic: a SELECT that references a column-like name but has no FROM.

    Avoids false positives on ``SELECT 1`` or ``SELECT NOW()`` by requiring a
    bare identifier that is not a number, function call, or string.
    """
    parsed = sqlparse.parse(stripped)
    if not parsed or parsed[0].get_type() != "SELECT":
        return False
    if re.search(r"\bfrom\b", stripped, re.IGNORECASE):
        return False
    # Extract the SELECT list (between SELECT and end / first clause keyword).
    m = re.search(r"\bselect\b\s+(.*)$", stripped, re.IGNORECASE | re.DOTALL)
    if not m:
        return False
    body = m.group(1)
    body = re.sub(r"^distinct\s+", "", body, flags=re.IGNORECASE)
    # A bare identifier not immediately followed by '(' (function call).
    for token in re.split(r"[,\s]+", body):
        token = token.strip()
        if not token:
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token) and "(" not in token:
            return True
    return False
