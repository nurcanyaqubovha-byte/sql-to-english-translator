"""Command-line interface for the SQL -> English/Azerbaijani translator.

Examples:
    python main.py "SELECT name FROM users WHERE age > 18;"
    python main.py "SELECT * FROM orders;" --lang az
    python main.py --file examples/sample_queries.sql --engine rule
"""

import argparse
import sys

import sqlparse

import optimizer
import translator
import validator

_ISSUES_LABEL = {"en": "Possible issues:", "az": "Mümkün problemlər:"}
_SUGGEST_LABEL = {"en": "Optimization suggestions:", "az": "Optimallaşdırma təklifləri:"}


def _read_queries(args):
    """Return a list of SQL statements from the positional arg or a file."""
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            print(f"Error: could not read file '{args.file}': {exc}", file=sys.stderr)
            sys.exit(1)
        statements = [s.strip() for s in sqlparse.split(text) if s.strip()]
        return statements

    if args.query:
        return [args.query.strip()]

    return []


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sql-translator",
        description="Translate SQL queries into plain English or Azerbaijani.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="The SQL query to translate (quote it). Omit when using --file.",
    )
    parser.add_argument(
        "-f", "--file",
        help="Read one or more SQL statements from a file.",
    )
    parser.add_argument(
        "-l", "--lang",
        choices=translator.VALID_LANGS,
        default="en",
        help="Output language: 'en' (English, default) or 'az' (Azerbaijani).",
    )
    parser.add_argument(
        "-e", "--engine",
        choices=translator.VALID_ENGINES,
        default="auto",
        help="Translation engine: 'auto' (default), 'ai', or 'rule'.",
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="Skip the SQL error check (only show the explanation).",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Skip the optimization suggestions.",
    )
    return parser


def _force_utf8_output():
    """Ensure non-ASCII output (e.g. Azerbaijani 'ə') prints on any console.

    Windows consoles default to a legacy code page (cp1252) that cannot encode
    these characters, which would otherwise crash on Azerbaijani output.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _force_utf8_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    queries = _read_queries(args)
    if not queries:
        parser.print_help()
        print("\nError: provide a SQL query or use --file.", file=sys.stderr)
        return 1

    multiple = len(queries) > 1
    for i, sql in enumerate(queries, start=1):
        if multiple:
            print(f"--- Query {i} ---")
            print(sql)
            print()

        if not args.no_check:
            issues = validator.check_sql(sql, args.lang)
            if issues:
                print(_ISSUES_LABEL[args.lang])
                for issue in issues:
                    print(f"  - {issue}")
                print()

        explanation = translator.translate(sql, lang=args.lang, engine=args.engine)
        print(explanation)

        if not args.no_optimize:
            suggestions = optimizer.suggest(sql, args.lang)
            if suggestions:
                print()
                print(_SUGGEST_LABEL[args.lang])
                for s in suggestions:
                    print(f"  - {s}")

        if multiple and i < len(queries):
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
