"""Tests for the Flask web interface.

These use Flask's test client (no real server needed). If Flask is not
installed, the whole module is skipped so the core tests still run.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import app as web_app
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@unittest.skipUnless(HAS_FLASK, "Flask is not installed")
class TestWebApp(unittest.TestCase):
    def setUp(self):
        web_app.app.config["TESTING"] = True
        self.client = web_app.app.test_client()

    def test_index_get(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"SQL", resp.data)

    def test_post_returns_explanation(self):
        resp = self.client.post("/", data={
            "query": "SELECT name FROM users WHERE age > 18;",
            "lang": "en",
            "engine": "rule",
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.data.decode("utf-8")
        self.assertIn("greater than", body)

    def test_post_shows_issues(self):
        resp = self.client.post("/", data={
            "query": "SELECT a, b, FROM t;",
            "lang": "en",
            "engine": "rule",
        })
        body = resp.data.decode("utf-8")
        self.assertIn("comma", body.lower())

    def test_azerbaijani_page(self):
        resp = self.client.get("/?lang=az")
        body = resp.data.decode("utf-8")
        self.assertIn("Tərcümə", body)

    def test_empty_query_shows_error(self):
        resp = self.client.post("/", data={"query": "", "lang": "en", "engine": "rule"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("enter a SQL", resp.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
