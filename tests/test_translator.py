"""Tests for the offline rule-based engine.

These tests are deterministic and require no API key or network access. The AI
engine is intentionally not tested here because it depends on a live API call.

Run with:
    python -m pytest tests/
    # or
    python -m unittest discover -s tests
"""

import os
import sys
import unittest

# Make the project root importable when running from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rule_engine  # noqa: E402
import translator  # noqa: E402
import validator  # noqa: E402


class TestRuleEngineEnglish(unittest.TestCase):
    def test_simple_select_where(self):
        sql = "SELECT first_name, salary FROM employees WHERE salary > 5000;"
        out = rule_engine.translate_rule_based(sql, "en")
        self.assertIn("first_name", out)
        self.assertIn("salary", out)
        self.assertIn("employees", out)
        self.assertIn("greater than", out)
        self.assertTrue(out.endswith("."))

    def test_select_star(self):
        out = rule_engine.translate_rule_based("SELECT * FROM products;", "en")
        self.assertIn("all columns", out)
        self.assertIn("products", out)

    def test_count_group_by(self):
        sql = "SELECT department_id, COUNT(*) FROM employees GROUP BY department_id;"
        out = rule_engine.translate_rule_based(sql, "en")
        self.assertIn("For each", out)
        self.assertIn("department_id", out)
        self.assertIn("number of rows", out)

    def test_order_by_desc(self):
        sql = "SELECT name FROM products ORDER BY price DESC;"
        out = rule_engine.translate_rule_based(sql, "en")
        self.assertIn("ordered by", out)
        self.assertIn("descending", out)

    def test_join(self):
        sql = ("SELECT customers.name FROM customers "
               "JOIN orders ON customers.id = orders.customer_id;")
        out = rule_engine.translate_rule_based(sql, "en")
        self.assertIn("joined with", out)
        self.assertIn("orders", out)

    def test_having(self):
        sql = ("SELECT department_id, AVG(salary) FROM employees "
               "GROUP BY department_id HAVING AVG(salary) > 4000;")
        out = rule_engine.translate_rule_based(sql, "en")
        self.assertIn("groups where", out)

    def test_non_select_statement(self):
        out = rule_engine.translate_rule_based("DELETE FROM users WHERE id = 1;", "en")
        self.assertIn("DELETE", out)

    def test_empty_query(self):
        out = rule_engine.translate_rule_based("", "en")
        self.assertIn("could not", out.lower())


class TestRuleEngineAzerbaijani(unittest.TestCase):
    def test_simple_select_az(self):
        sql = "SELECT first_name, salary FROM employees WHERE salary > 5000;"
        out = rule_engine.translate_rule_based(sql, "az")
        self.assertIn("employees", out)
        self.assertIn("böyükdür", out)
        self.assertTrue(out.endswith("."))

    def test_select_star_az(self):
        out = rule_engine.translate_rule_based("SELECT * FROM products;", "az")
        self.assertIn("bütün sütunları", out)


class TestHybridSelection(unittest.TestCase):
    def test_rule_engine_forced(self):
        out = translator.translate("SELECT * FROM t;", lang="en", engine="rule")
        self.assertIn("all columns", out)

    def test_auto_without_key_uses_rules(self):
        # Ensure no key is present for this test.
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            out = translator.translate("SELECT * FROM t;", lang="en", engine="auto")
            self.assertIn("all columns", out)
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved

    def test_invalid_lang_falls_back_to_en(self):
        out = translator.translate("SELECT * FROM t;", lang="xx", engine="rule")
        self.assertIn("all columns", out)


class TestValidator(unittest.TestCase):
    def test_valid_query_has_no_issues(self):
        sql = "SELECT name FROM users WHERE age > 18;"
        self.assertEqual(validator.check_sql(sql, "en"), [])

    def test_empty(self):
        issues = validator.check_sql("", "en")
        self.assertEqual(len(issues), 1)
        self.assertIn("empty", issues[0].lower())

    def test_unbalanced_parentheses(self):
        issues = validator.check_sql("SELECT * FROM t WHERE (a > 1;", "en")
        self.assertTrue(any("parenthes" in m.lower() for m in issues))

    def test_unbalanced_quote(self):
        issues = validator.check_sql("SELECT * FROM t WHERE name = 'bob;", "en")
        self.assertTrue(any("quote" in m.lower() for m in issues))

    def test_trailing_comma_before_from(self):
        issues = validator.check_sql("SELECT a, b, FROM t;", "en")
        self.assertTrue(any("comma" in m.lower() for m in issues))

    def test_equals_null(self):
        issues = validator.check_sql("SELECT * FROM t WHERE x = NULL;", "en")
        self.assertTrue(any("NULL" in m for m in issues))

    def test_unknown_start(self):
        issues = validator.check_sql("SELCT * FROM t;", "en")
        self.assertTrue(any("keyword" in m.lower() for m in issues))

    def test_select_without_from(self):
        issues = validator.check_sql("SELECT name, age;", "en")
        self.assertTrue(any("from" in m.lower() for m in issues))

    def test_select_literal_no_false_positive(self):
        # "SELECT 1" and "SELECT NOW()" are valid and need no FROM.
        self.assertEqual(validator.check_sql("SELECT 1;", "en"), [])
        self.assertEqual(validator.check_sql("SELECT NOW();", "en"), [])

    def test_string_with_parenthesis_not_flagged(self):
        # A '(' inside a string literal must not count as unbalanced.
        sql = "SELECT * FROM t WHERE note = 'hi (there)';"
        self.assertEqual(validator.check_sql(sql, "en"), [])

    def test_azerbaijani_messages(self):
        issues = validator.check_sql("", "az")
        self.assertIn("boş", issues[0].lower())


if __name__ == "__main__":
    unittest.main()
