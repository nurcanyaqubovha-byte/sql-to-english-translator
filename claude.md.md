# SQL to English Translator

An AI-powered tool that translates SQL queries into clear and simple English explanations.

## Features

- Translate SQL queries into natural language
- Explain SELECT statements
- Explain WHERE conditions
- Explain ORDER BY clauses
- Explain GROUP BY and HAVING clauses
- Explain JOIN operations
- Beginner-friendly explanations
- Command Line Interface (CLI)
- AI-powered query interpretation

## Example

### SQL Query

```sql
SELECT first_name, salary
FROM employees
WHERE salary > 5000;
```

### English Translation

```text
Show the first name and salary of all employees whose salary is greater than 5000.
```

### SQL Query

```sql
SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id;
```

### English Translation

```text
Display each department and the number of employees working in that department.
```

## Project Structure

```text
sql-to-english-translator/
│
├── main.py
├── translator.py
├── prompts/
│   └── sql_prompt.txt
├── examples/
│   └── sample_queries.sql
├── tests/
│   └── test_translator.py
├── requirements.txt
└── README.md
```

## Future Enhancements

- SQL to Azerbaijani translation
- SQL error detection
- Query optimization suggestions
- Web application interface
- Interactive learning mode
- Voice input support

## Author

Developed as a portfolio project for learning SQL, AI integration, and natural language processing.
