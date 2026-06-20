# SQL to English/Azerbaijani Translator

An AI-powered tool that translates SQL queries into clear, simple explanations
in **English** or **Azerbaijani**. It uses a **hybrid** approach: a rule-based
offline engine works without any API key, and — when an Anthropic API key is
available — it upgrades to a Claude-powered engine for richer explanations.

## Features

- Translate SQL queries into natural language (English and Azerbaijani)
- Explain SELECT, WHERE, ORDER BY, GROUP BY, HAVING, and JOIN clauses
- **SQL error detection** — flags common mistakes (unbalanced parentheses,
  trailing commas, `= NULL`, typos) in clear language before translating
- **Optimization suggestions** — points out performance anti-patterns
  (`SELECT *`, leading `LIKE '%...'`, functions on columns, implicit joins, ...)
- **Offline rule-based engine** — no API key, no internet required
- **AI engine** — Anthropic Claude for complex queries (subqueries, etc.)
- **Hybrid auto mode** — picks the AI engine when a key is set, otherwise rules
- Command-line interface with single-query or file input
- **Web interface** — a simple Flask page (English/Azerbaijani UI)

## Project Structure

```text
SQL terceme/
├── main.py                 # CLI entry point
├── app.py                  # Flask web interface
├── translator.py           # Engine selection (hybrid logic)
├── rule_engine.py          # Offline rule-based engine
├── ai_engine.py            # Claude API engine
├── validator.py            # SQL error detection
├── optimizer.py            # Query optimization suggestions
├── templates/
│   └── index.html          # Web page template
├── static/
│   └── style.css           # Web page styling
├── prompts/
│   ├── sql_prompt_en.txt
│   └── sql_prompt_az.txt
├── examples/
│   └── sample_queries.sql
├── tests/
│   ├── test_translator.py
│   └── test_web.py
├── requirements.txt
└── README.md
```

## Installation

```bash
# 1. (recommended) create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt
```

## Setting up the AI engine (optional)

The offline engine works out of the box. To enable the Claude-powered engine,
set your Anthropic API key (get one at <https://console.anthropic.com/>):

```bash
# Windows (PowerShell, persistent — open a new terminal afterwards)
setx ANTHROPIC_API_KEY "sk-ant-..."

# macOS/Linux (current session)
export ANTHROPIC_API_KEY="sk-ant-..."
```

Never commit your real key. Copy `.env.example` to `.env` if you keep it in a
file — `.env` is gitignored.

## Usage

```bash
# Auto engine (AI if a key is set, otherwise the offline engine)
python main.py "SELECT first_name, salary FROM employees WHERE salary > 5000;"

# Azerbaijani output
python main.py "SELECT * FROM orders;" --lang az

# Force the offline rule-based engine
python main.py "SELECT department_id, COUNT(*) FROM employees GROUP BY department_id;" --engine rule

# Force the AI engine
python main.py "SELECT * FROM users;" --engine ai

# Translate every statement in a file
python main.py --file examples/sample_queries.sql --engine rule
```

### Options

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `query` | text | – | The SQL query to translate (quote it) |
| `-f`, `--file` | path | – | Read one or more statements from a file |
| `-l`, `--lang` | `en`, `az` | `en` | Output language |
| `-e`, `--engine` | `auto`, `ai`, `rule` | `auto` | Translation engine |
| `--no-check` | flag | off | Skip the SQL error check |
| `--no-optimize` | flag | off | Skip the optimization suggestions |

### Error detection

Before translating, the tool checks for common mistakes and prints them:

```bash
python main.py "SELECT a, b, FROM t WHERE (x > 1;" --engine rule
```

```text
Possible issues:
  - Unbalanced parentheses: 1 '(' and 0 ')'.
  - There is a comma right before FROM. Remove the trailing comma in the column list.

Show a and b, from t, where (x is greater than 1.
```

Use `--no-check` to skip this step.

### Optimization suggestions

The tool also points out common performance anti-patterns:

```bash
python main.py "SELECT * FROM users WHERE name LIKE '%son' ORDER BY name;" --engine rule
```

```text
Show all columns, from users, where name matches the pattern '%son', ordered by name.

Optimization suggestions:
  - Avoid SELECT * -- list only the columns you need...
  - A LIKE pattern that starts with '%' cannot use an index...
  - ORDER BY without LIMIT sorts the entire result...
```

Use `--no-optimize` to skip this step.

## Examples

### SQL Query

```sql
SELECT first_name, salary
FROM employees
WHERE salary > 5000;
```

### English (offline engine)

```text
Show first_name and salary, from employees, where salary is greater than 5000.
```

### SQL Query

```sql
SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id;
```

### English (offline engine)

```text
For each department_id, show department_id and the number of rows, from employees.
```

## Web interface

Start the local server and open it in a browser:

```bash
python app.py
# then open http://127.0.0.1:5000/
```

Enter a SQL query, choose the engine, and switch between English (`EN`) and
Azerbaijani (`AZ`) in the top-right corner. Validation issues and the
explanation appear below the form.

## Running the tests

```bash
python -m pytest tests/
# or, without pytest installed:
python -m unittest discover -s tests
```

## How the hybrid engine works

1. `--engine rule` always uses the offline engine.
2. `--engine ai` uses Claude; if it fails (no key, network error) it warns and
   falls back to the offline engine so you always get an answer.
3. `--engine auto` (default) uses Claude when `ANTHROPIC_API_KEY` is set,
   otherwise the offline engine.

## Future Enhancements

- Interactive learning mode

## Author

Developed as a portfolio project for learning SQL, AI integration, and natural
language processing.
