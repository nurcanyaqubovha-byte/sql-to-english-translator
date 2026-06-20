"""Flask web interface for the SQL -> English/Azerbaijani translator.

Run locally:
    pip install -r requirements.txt
    python app.py
    # then open http://127.0.0.1:5000/

This reuses the same engines as the CLI: ``validator.check_sql`` for error
detection and ``translator.translate`` for the explanation.
"""

from flask import Flask, render_template, request

import ai_engine
import translator
import validator

app = Flask(__name__)

# UI text per language so the page itself can be shown in either language.
UI = {
    "en": {
        "title": "SQL to English Translator",
        "subtitle": "Explain any SQL query in plain language.",
        "query_label": "SQL query",
        "placeholder": "SELECT first_name, salary FROM employees WHERE salary > 5000;",
        "lang_label": "Explanation language",
        "engine_label": "Engine",
        "submit": "Translate",
        "issues_title": "Possible issues",
        "result_title": "Explanation",
        "ai_note": "AI engine active (ANTHROPIC_API_KEY found).",
        "rule_note": "Offline engine (set ANTHROPIC_API_KEY for AI explanations).",
        "empty_error": "Please enter a SQL query.",
    },
    "az": {
        "title": "SQL Tərcüməçisi",
        "subtitle": "İstənilən SQL sorğusunu sadə dildə izah edin.",
        "query_label": "SQL sorğusu",
        "placeholder": "SELECT first_name, salary FROM employees WHERE salary > 5000;",
        "lang_label": "İzah dili",
        "engine_label": "Motor",
        "submit": "Tərcümə et",
        "issues_title": "Mümkün problemlər",
        "result_title": "İzah",
        "ai_note": "AI motoru aktivdir (ANTHROPIC_API_KEY tapıldı).",
        "rule_note": "Offline motor (AI izahları üçün ANTHROPIC_API_KEY təyin edin).",
        "empty_error": "Zəhmət olmasa bir SQL sorğusu daxil edin.",
    },
}

ENGINES = ("auto", "ai", "rule")


@app.route("/", methods=["GET", "POST"])
def index():
    lang = request.values.get("lang", "en")
    if lang not in UI:
        lang = "en"
    engine = request.values.get("engine", "auto")
    if engine not in ENGINES:
        engine = "auto"

    query = ""
    issues = []
    explanation = None
    error = None

    if request.method == "POST":
        query = (request.form.get("query") or "").strip()
        if not query:
            error = UI[lang]["empty_error"]
        else:
            issues = validator.check_sql(query, lang)
            explanation = translator.translate(query, lang=lang, engine=engine)

    return render_template(
        "index.html",
        ui=UI[lang],
        lang=lang,
        engine=engine,
        engines=ENGINES,
        query=query,
        issues=issues,
        explanation=explanation,
        error=error,
        ai_available=ai_engine.is_available(),
    )


if __name__ == "__main__":
    # debug=False by default; set FLASK_DEBUG=1 to develop with auto-reload.
    app.run(host="127.0.0.1", port=5000)
