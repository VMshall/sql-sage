# SQL Sage

SQL Sage — AI SQL explainer and optimizer with dialect detection and performance analysis.

## Problem

SQL queries are hard to understand, optimize, and debug — especially complex ones with JOINs, CTEs, subqueries, and window functions. Developers waste hours deciphering poorly documented queries.

## Solution

Paste any SQL query and get instant structured analysis:
- **Plain-English Explanation** — what the query actually does, step by step
- **Dialect Detection** — auto-identifies PostgreSQL, MySQL, BigQuery, SQLite, etc.
- **Performance Inefficiencies** — missing indexes, N+1 patterns, expensive operations
- **Optimized Version** — rewritten query with explanations of changes
- **Complexity Assessment** — time/space complexity estimate
- **Edge Cases** — nulls, empty sets, overflow risks, and other gotchas

## Stack

- **Backend**: FastAPI + Anthropic Claude claude-opus-4-6
- **Frontend**: Single-file HTML/JS with Tailwind CSS, side-by-side SQL comparison

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
uvicorn src.api:app --reload
```

Then open http://localhost:8000

## API

`POST /api/analyze` — Analyze a SQL query

```json
{
  "query": "SELECT * FROM orders o JOIN ...",
  "dialect": "auto"
}
```

Returns explanation, dialect, inefficiencies, optimized query, complexity, and edge cases.
