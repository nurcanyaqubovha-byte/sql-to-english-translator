-- Sample SQL queries for the translator.
-- Run with: python main.py --file examples/sample_queries.sql

SELECT first_name, salary
FROM employees
WHERE salary > 5000;

SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id;

SELECT *
FROM products
WHERE price <= 100
ORDER BY price DESC;

SELECT customers.name, orders.total
FROM customers
JOIN orders ON customers.id = orders.customer_id
WHERE orders.total > 250;

SELECT department_id, AVG(salary)
FROM employees
GROUP BY department_id
HAVING AVG(salary) > 4000
ORDER BY department_id ASC;
