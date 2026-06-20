"""Heuristic SQL query-optimization suggestions.

Scans a query for common performance anti-patterns and returns plain-language
advice in English or Azerbaijani. Like ``validator``, this is heuristic: it does
not run the query or read a real schema, so suggestions are hints to review --
not guarantees. It deliberately errs toward few, high-signal suggestions.

Use ``suggest(sql, lang)`` -> list of suggestion strings (empty list = nothing
obvious to improve).
"""

import re

import rule_engine
import validator

MESSAGES = {
    "en": {
        "select_star": (
            "Avoid SELECT * -- list only the columns you need so the database "
            "reads and transfers less data."
        ),
        "leading_wildcard": (
            "A LIKE pattern that starts with '%' cannot use an index, forcing a "
            "full scan. Avoid a leading wildcard where possible."
        ),
        "func_on_column": (
            "Wrapping a column in a function inside WHERE (e.g. UPPER(col) or "
            "YEAR(col)) prevents index use. Compare the bare column instead, or "
            "use a computed/functional index."
        ),
        "or_condition": (
            "OR conditions can stop the database from using indexes. If they "
            "test the same column, IN (...) is often faster; otherwise consider "
            "UNION."
        ),
        "not_in": (
            "NOT IN can be slow and behaves unexpectedly with NULLs. NOT EXISTS "
            "or a LEFT JOIN ... IS NULL is usually better."
        ),
        "implicit_join": (
            "This uses the old comma-style join. Use an explicit JOIN ... ON to "
            "make the join condition clear and avoid accidental cross joins."
        ),
        "order_no_limit": (
            "ORDER BY without LIMIT sorts the entire result. Add LIMIT if you "
            "only need the top rows."
        ),
        "distinct": (
            "DISTINCT can be expensive. Check whether a JOIN is creating "
            "duplicate rows that DISTINCT is hiding."
        ),
        "no_where": (
            "There is no WHERE clause, so this reads the whole table. Add a "
            "filter (and/or LIMIT) if you do not need every row."
        ),
    },
    "az": {
        "select_star": (
            "SELECT * istifadə etməyin -- yalnız lazım olan sütunları yazın ki, "
            "baza daha az məlumat oxusun və ötürsün."
        ),
        "leading_wildcard": (
            "'%' ilə başlayan LIKE nümunəsi indeksdən istifadə edə bilmir və tam "
            "skan tələb edir. Mümkünsə, əvvəldəki '%'-dən qaçın."
        ),
        "func_on_column": (
            "WHERE içində sütunu funksiyaya salmaq (məs. UPPER(sütun) və ya "
            "YEAR(sütun)) indeksdən istifadəni dayandırır. Bunun yerinə sütunu "
            "olduğu kimi müqayisə edin və ya funksional indeks qurun."
        ),
        "or_condition": (
            "OR şərtləri bazanın indeksdən istifadəsini dayandıra bilər. Eyni "
            "sütunu yoxlayırlarsa, çox vaxt IN (...) daha sürətlidir; əks halda "
            "UNION düşünün."
        ),
        "not_in": (
            "NOT IN yavaş ola bilər və NULL dəyərlərlə gözlənilməz davranır. "
            "Adətən NOT EXISTS və ya LEFT JOIN ... IS NULL daha yaxşıdır."
        ),
        "implicit_join": (
            "Bu, köhnə vergüllü birləşmə üsulundan istifadə edir. Birləşmə şərtini "
            "aydın etmək və təsadüfi cross join-dən qaçmaq üçün açıq JOIN ... ON "
            "istifadə edin."
        ),
        "order_no_limit": (
            "LIMIT-siz ORDER BY bütün nəticəni sıralayır. Yalnız yuxarı sətirlər "
            "lazımdırsa, LIMIT əlavə edin."
        ),
        "distinct": (
            "DISTINCT bahalı ola bilər. JOIN-in DISTINCT-in gizlətdiyi təkrar "
            "sətirlər yaratmadığını yoxlayın."
        ),
        "no_where": (
            "WHERE hissəsi yoxdur, ona görə bu, bütün cədvəli oxuyur. Hər sətir "
            "lazım deyilsə, filtr (və/və ya LIMIT) əlavə edin."
        ),
    },
}


def suggest(sql, lang="en"):
    """Return a list of optimization suggestions (empty list = nothing obvious)."""
    if lang not in MESSAGES:
        lang = "en"
    msg = MESSAGES[lang]
    out = []

    if not sql or not sql.strip():
        return out

    normalised = rule_engine._normalise(sql)
    # Blank out string literals so their contents never trigger keyword matches.
    stripped, _ = validator._strip_strings(normalised)

    # Only analyse SELECT statements; other statements have different concerns.
    if rule_engine._statement_kind(normalised) not in ("SELECT", "UNKNOWN"):
        return out

    clauses = rule_engine._split_clauses(stripped)
    select_body = clauses.get("select", "")
    from_body = clauses.get("from", "")
    where_body = clauses.get("where", "")

    # SELECT *
    if re.search(r"select\s+\*", "select " + select_body, re.IGNORECASE) or \
            select_body.strip() == "*":
        out.append(msg["select_star"])

    # Leading wildcard in LIKE -- check the ORIGINAL sql (needs string content).
    if re.search(r"\blike\s+n?'%", normalised, re.IGNORECASE):
        out.append(msg["leading_wildcard"])

    # Function applied to a column inside WHERE (non-sargable).
    if where_body and re.search(
            r"\b[A-Za-z_]+\s*\([^)]*\)\s*(=|!=|<>|>=|<=|>|<|\blike\b)",
            where_body, re.IGNORECASE):
        out.append(msg["func_on_column"])

    # OR in WHERE.
    if where_body and re.search(r"\bor\b", where_body, re.IGNORECASE):
        out.append(msg["or_condition"])

    # NOT IN anywhere.
    if re.search(r"\bnot\s+in\b", stripped, re.IGNORECASE):
        out.append(msg["not_in"])

    # Implicit (comma-style) join: top-level comma in FROM.
    if from_body and len(rule_engine._split_top_level(from_body)) > 1:
        out.append(msg["implicit_join"])

    # ORDER BY without LIMIT.
    if "order by" in clauses and not re.search(r"\blimit\b", stripped, re.IGNORECASE):
        out.append(msg["order_no_limit"])

    # DISTINCT.
    if re.search(r"select\s+distinct\b", "select " + select_body, re.IGNORECASE):
        out.append(msg["distinct"])

    # No WHERE clause at all (full table read).
    if "select" in clauses and "where" not in clauses:
        out.append(msg["no_where"])

    return out
