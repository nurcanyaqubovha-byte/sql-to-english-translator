"""Rule-based, offline SQL -> natural language translator.

This engine handles common SELECT-style queries without any network access or
API key. It splits a query into its clauses (SELECT / FROM / JOIN / WHERE /
GROUP BY / HAVING / ORDER BY) and builds a plain-language explanation from
templates. For anything it cannot fully parse it falls back gracefully,
explaining the parts it did recognise.

For complex queries (subqueries, CTEs, window functions) the AI engine in
``ai_engine.py`` produces better results -- that is the point of the hybrid
design.
"""

import re

import sqlparse

# --- Language packs ----------------------------------------------------------
# Each supported language provides the words used to stitch the explanation
# together. Keeping them in dictionaries makes adding a new language a matter of
# adding one more entry.

OPERATORS = {
    "en": {
        ">": "is greater than",
        "<": "is less than",
        ">=": "is greater than or equal to",
        "<=": "is less than or equal to",
        "=": "equals",
        "!=": "is not equal to",
        "<>": "is not equal to",
        "like": "matches the pattern",
        "in": "is one of",
        "between": "is between",
        "is": "is",
    },
    "az": {
        ">": "böyükdür",
        "<": "kiçikdir",
        ">=": "böyük və ya bərabərdir",
        "<=": "kiçik və ya bərabərdir",
        "=": "bərabərdir",
        "!=": "bərabər deyil",
        "<>": "bərabər deyil",
        "like": "nümunəyə uyğundur",
        "in": "bunlardan biridir",
        "between": "aralığındadır",
        "is": "-dir",
    },
}

PHRASES = {
    "en": {
        "show": "Show",
        "all_columns": "all columns",
        "from": "from",
        "the_table": "the table",
        "joined_with": "joined with",
        "where": "where",
        "grouped_by": "grouped by",
        "having": "keeping only groups where",
        "ordered_by": "ordered by",
        "ascending": "ascending",
        "descending": "descending",
        "count_all": "the number of rows",
        "and": "and",
        "for_each": "For each",
        "show_count": "show the number of rows",
        "could_not_parse": (
            "This query could not be fully analysed by the offline engine. "
            "Try the AI engine (set ANTHROPIC_API_KEY) for a detailed explanation."
        ),
        "not_select": (
            "This is a {kind} statement. The offline engine explains SELECT "
            "queries; use the AI engine for a full explanation."
        ),
    },
    "az": {
        "show": "Göstər",
        "all_columns": "bütün sütunları",
        "from": "buradan:",
        "the_table": "cədvəlindən",
        "joined_with": "ilə birləşdirilmiş",
        "where": "şərti ilə:",
        "grouped_by": "buna görə qruplaşdırılmış:",
        "having": "yalnız bu şərtə uyğun qruplar:",
        "ordered_by": "buna görə sıralanmış:",
        "ascending": "artan",
        "descending": "azalan",
        "count_all": "sətirlərin sayını",
        "and": "və",
        "for_each": "Hər",
        "show_count": "üçün sətirlərin sayını göstər",
        "could_not_parse": (
            "Bu sorğunu offline motor tam təhlil edə bilmədi. "
            "Ətraflı izah üçün AI motorunu sınayın (ANTHROPIC_API_KEY təyin edin)."
        ),
        "not_select": (
            "Bu, {kind} əmridir. Offline motor SELECT sorğularını izah edir; "
            "tam izah üçün AI motorundan istifadə edin."
        ),
    },
}

# Clause keywords used to split a query, in the order they appear.
_CLAUSE_KEYWORDS = ["select", "from", "where", "group by", "having", "order by"]


def _normalise(sql):
    """Collapse whitespace and strip a trailing semicolon."""
    sql = sql.strip().rstrip(";").strip()
    sql = re.sub(r"\s+", " ", sql)
    return sql


def _split_clauses(sql):
    """Return a dict mapping clause name -> clause body text.

    Splitting is done on top-level keywords. We avoid splitting inside
    parentheses so that things like ``IN (1, 2, 3)`` stay intact.
    """
    # Build a regex that matches any clause keyword as a whole word.
    pattern = re.compile(
        r"\b(" + "|".join(k.replace(" ", r"\s+") for k in _CLAUSE_KEYWORDS) + r")\b",
        re.IGNORECASE,
    )

    matches = []
    depth = 0
    # Track parenthesis depth so we only accept keywords at the top level.
    for m in pattern.finditer(sql):
        depth = sql.count("(", 0, m.start()) - sql.count(")", 0, m.start())
        if depth == 0:
            matches.append(m)

    clauses = {}
    for i, m in enumerate(matches):
        name = re.sub(r"\s+", " ", m.group(1).lower())
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(sql)
        clauses[name] = sql[start:end].strip()
    return clauses


def _split_top_level(text, sep=","):
    """Split ``text`` on ``sep`` but ignore separators inside parentheses."""
    parts = []
    depth = 0
    current = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _humanise_column(col, lang):
    """Turn a single SELECT item into readable text."""
    col = col.strip()
    phrases = PHRASES[lang]

    # COUNT(*) -> "the number of rows"
    if re.fullmatch(r"count\s*\(\s*\*\s*\)", col, re.IGNORECASE):
        return phrases["count_all"]

    # Aggregate functions: COUNT(x), SUM(x), AVG(x), MIN(x), MAX(x)
    agg = re.fullmatch(r"(count|sum|avg|min|max)\s*\(\s*(.+?)\s*\)", col, re.IGNORECASE)
    if agg:
        func = agg.group(1).lower()
        inner = agg.group(2)
        names = {
            "en": {
                "count": "the count of",
                "sum": "the total of",
                "avg": "the average of",
                "min": "the minimum of",
                "max": "the maximum of",
            },
            "az": {
                "count": "sayını",
                "sum": "cəmini",
                "avg": "ortalamasını",
                "min": "minimumunu",
                "max": "maksimumunu",
            },
        }
        if lang == "az":
            return f"{inner} {names['az'][func]}"
        return f"{names['en'][func]} {inner}"

    # Drop an "AS alias" for readability.
    col = re.sub(r"\s+as\s+\w+$", "", col, flags=re.IGNORECASE)
    return col


def _humanise_columns(select_body, lang):
    phrases = PHRASES[lang]
    body = select_body.strip()
    # Ignore DISTINCT for the basic explanation.
    body = re.sub(r"^distinct\s+", "", body, flags=re.IGNORECASE)
    if body.strip() == "*":
        return phrases["all_columns"]
    items = [_humanise_column(c, lang) for c in _split_top_level(body)]
    return _join_list(items, lang)


def _join_list(items, lang):
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    sep = PHRASES[lang]["and"]
    return ", ".join(items[:-1]) + f" {sep} " + items[-1]


def _humanise_from(from_body, lang):
    """Explain the FROM clause, including any JOINs."""
    phrases = PHRASES[lang]
    # Separate the first table from any JOINed tables.
    join_split = re.split(r"\b((?:inner|left|right|full|cross)?\s*join)\b",
                          from_body, flags=re.IGNORECASE)
    base_table = join_split[0].strip()
    text = base_table

    # join_split alternates: [table, join_kw, table, join_kw, table, ...]
    joined = []
    for i in range(1, len(join_split), 2):
        target = join_split[i + 1] if i + 1 < len(join_split) else ""
        # Trim the ON condition for the high-level summary.
        target = re.split(r"\bon\b", target, flags=re.IGNORECASE)[0].strip()
        if target:
            joined.append(target)
    if joined:
        text += f" {phrases['joined_with']} " + _join_list(joined, lang)
    return text


def _humanise_condition(cond, lang):
    """Replace SQL operators in a condition with words."""
    ops = OPERATORS[lang]
    text = cond.strip()
    # Word operators first (LIKE, IN, BETWEEN, IS) -- case-insensitive.
    for word in ["like", "in", "between", "is"]:
        text = re.sub(rf"\b{word}\b", ops[word], text, flags=re.IGNORECASE)
    # Symbol operators, longest first so >= is handled before >.
    for sym in [">=", "<=", "!=", "<>", ">", "<", "="]:
        text = text.replace(sym, f" {ops[sym]} ")
    # Connectors AND / OR -> words.
    if lang == "az":
        text = re.sub(r"\bAND\b", "və", text, flags=re.IGNORECASE)
        text = re.sub(r"\bOR\b", "və ya", text, flags=re.IGNORECASE)
    else:
        text = re.sub(r"\bAND\b", "and", text, flags=re.IGNORECASE)
        text = re.sub(r"\bOR\b", "or", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _humanise_order(order_body, lang):
    phrases = PHRASES[lang]
    items = []
    for part in _split_top_level(order_body):
        direction = ""
        if re.search(r"\bdesc\b", part, re.IGNORECASE):
            direction = f" ({phrases['descending']})"
        elif re.search(r"\basc\b", part, re.IGNORECASE):
            direction = f" ({phrases['ascending']})"
        name = re.sub(r"\s+(asc|desc)\b", "", part, flags=re.IGNORECASE).strip()
        items.append(name + direction)
    return _join_list(items, lang)


def _statement_kind(sql):
    """Return the leading statement keyword (e.g. INSERT, UPDATE), or None."""
    parsed = sqlparse.parse(sql)
    if not parsed:
        return None
    return parsed[0].get_type()  # 'SELECT', 'INSERT', 'UNKNOWN', ...


def translate_rule_based(sql, lang="en"):
    """Translate a SQL query into a natural-language explanation.

    Args:
        sql: the SQL query text.
        lang: 'en' or 'az'.

    Returns:
        A human-readable explanation string.
    """
    if lang not in PHRASES:
        lang = "en"
    phrases = PHRASES[lang]

    if not sql or not sql.strip():
        return phrases["could_not_parse"]

    sql = _normalise(sql)

    kind = _statement_kind(sql)
    if kind and kind not in ("SELECT", "UNKNOWN"):
        return phrases["not_select"].format(kind=kind)

    clauses = _split_clauses(sql)
    if "select" not in clauses:
        return phrases["could_not_parse"]

    columns = _humanise_columns(clauses["select"], lang)

    parts = []
    group_body = clauses.get("group by")

    if group_body:
        # "For each <group>, show <columns>."
        group_text = _join_list(_split_top_level(group_body), lang)
        if lang == "az":
            parts.append(f"{phrases['for_each']} {group_text} üçün {columns} göstər")
        else:
            parts.append(f"{phrases['for_each']} {group_text}, show {columns}")
    else:
        # "Show <columns>"
        if lang == "az":
            parts.append(f"{phrases['show']} {columns}")
        else:
            parts.append(f"{phrases['show']} {columns}")

    if "from" in clauses:
        from_text = _humanise_from(clauses["from"], lang)
        if lang == "az":
            parts.append(f"{from_text} {phrases['the_table']}")
        else:
            parts.append(f"{phrases['from']} {from_text}")

    if "where" in clauses:
        cond = _humanise_condition(clauses["where"], lang)
        parts.append(f"{phrases['where']} {cond}")

    if "having" in clauses:
        cond = _humanise_condition(clauses["having"], lang)
        parts.append(f"{phrases['having']} {cond}")

    if "order by" in clauses:
        order_text = _humanise_order(clauses["order by"], lang)
        parts.append(f"{phrases['ordered_by']} {order_text}")

    sentence = ", ".join(parts).strip()
    if not sentence.endswith("."):
        sentence += "."
    # Capitalise the first character.
    return sentence[0].upper() + sentence[1:]
