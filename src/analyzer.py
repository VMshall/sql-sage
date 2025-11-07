"""
SQL query analyzer powered by Claude.
Detects dialect, explains queries in plain English, identifies inefficiencies,
produces optimized versions, and flags edge cases.
"""

import json
import os
import re
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ANALYZER_SYSTEM_PROMPT = """You are a database expert and SQL performance engineer with deep expertise in:
- PostgreSQL, MySQL, SQLite, BigQuery, Snowflake, SQL Server, Oracle dialects
- Query optimization: indexes, execution plans, join strategies, partition pruning
- Common anti-patterns: N+1 queries, SELECT *, missing indexes, implicit type casts
- Window functions, CTEs, lateral joins, recursive queries
- Complexity analysis for SQL (data scan scope, join cardinality, sort operations)

Your explanations are clear enough for junior developers but deep enough for seniors.
You always provide concrete, runnable optimized SQL — not vague suggestions.
You never fabricate table structures; you work with what's in the query."""

# Dialect signature patterns for auto-detection
DIALECT_SIGNATURES = {
    "PostgreSQL": [
        r"\$\d+",           # Parameter placeholders $1, $2
        r"ILIKE",           # Case-insensitive LIKE
        r"::[\w]+",         # Type casting ::text, ::integer
        r"RETURNING",       # RETURNING clause
        r"ON CONFLICT",     # Upsert syntax
        r"ARRAY\[",         # Array literals
        r"jsonb?_",         # JSON functions
    ],
    "MySQL": [
        r"LIMIT \d+,\s*\d+", # LIMIT offset, count syntax
        r"AUTO_INCREMENT",
        r"ENGINE\s*=",
        r"TINYINT|MEDIUMINT",
        r"GROUP_CONCAT",
        r"IFNULL\(",
        r"`\w+`",           # Backtick identifiers
    ],
    "BigQuery": [
        r"ARRAY_AGG",
        r"STRUCT\(",
        r"UNNEST\(",
        r"`[\w-]+\.[\w-]+`", # Project.dataset backtick refs
        r"PARTITION BY\s+DATE",
        r"EXCEPT\s+DISTINCT",
        r"QUALIFY",
    ],
    "SQLite": [
        r"AUTOINCREMENT",
        r"PRAGMA",
        r"WITHOUT ROWID",
    ],
    "SQL Server": [
        r"TOP \d+",
        r"NOLOCK",
        r"GETDATE\(\)",
        r"ISNULL\(",
        r"\[[\w\s]+\]",     # Square bracket identifiers
        r"DECLARE @",
        r"NVARCHAR",
    ],
    "Snowflake": [
        r"QUALIFY",
        r"FLATTEN\(",
        r"PARSE_JSON",
        r"VARIANT",
        r"COPY INTO",
    ],
}


def detect_sql_dialect(query: str) -> str:
    """Detect SQL dialect from query syntax patterns."""
    scores: dict[str, int] = {}
    query_upper = query.upper()

    for dialect, patterns in DIALECT_SIGNATURES.items():
        score = sum(1 for p in patterns if re.search(p, query, re.IGNORECASE))
        scores[dialect] = score

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "Standard SQL"


def analyze_query(query: str, dialect: str | None = None) -> dict[str, Any]:
    """
    Analyze a SQL query for readability, performance, and correctness.

    Args:
        query: The SQL query to analyze
        dialect: Override dialect detection ('PostgreSQL', 'MySQL', etc.)

    Returns:
        Structured analysis with explanation, optimized query, and insights
    """
    if not query or len(query.strip()) < 10:
        raise ValueError("Query is too short for analysis")

    detected_dialect = dialect if dialect and dialect != "auto" else detect_sql_dialect(query)

    prompt = f"""Analyze this SQL query thoroughly.

Detected/Specified Dialect: {detected_dialect}

SQL QUERY:
```sql
{query}
```

Return ONLY valid JSON with this exact structure:
{{
  "dialect": "string - confirmed SQL dialect",
  "query_type": "string - e.g., SELECT with JOINs, CTE, Window Function, Aggregation, etc.",
  "complexity": "string - one of: simple, moderate, complex, very_complex",
  "estimated_complexity": "string - e.g., 'O(n log n) for the sort, O(n*m) for the nested loop join'",
  "plain_english_explanation": "string - clear step-by-step explanation of what this query does, written for a developer who didn't write it",
  "step_by_step": [
    "string - each logical step of query execution in plain English"
  ],
  "inefficiencies": [
    {{
      "issue": "string - issue title",
      "description": "string - specific explanation referencing the query",
      "impact": "string - one of: low, medium, high, critical",
      "fix_hint": "string - brief fix description"
    }}
  ],
  "optimized_query": "string - the full rewritten optimized SQL query",
  "optimization_notes": ["string - list of changes made and why"],
  "edge_cases": [
    {{
      "scenario": "string - edge case description",
      "risk": "string - what could go wrong",
      "mitigation": "string - how to handle it"
    }}
  ],
  "index_suggestions": ["string - specific index recommendations with syntax"],
  "overall_score": number between 1 and 10
}}

For optimized_query: if the query is already optimal, return it unchanged.
Be specific — reference actual table/column names from the query.
index_suggestions should include actual CREATE INDEX statements where possible."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        system=ANALYZER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    result = json.loads(response_text)

    return {
        "dialect": result.get("dialect", detected_dialect),
        "query_type": result.get("query_type", "SELECT"),
        "complexity": result.get("complexity", "moderate"),
        "estimated_complexity": result.get("estimated_complexity", ""),
        "plain_english_explanation": result.get("plain_english_explanation", ""),
        "step_by_step": result.get("step_by_step", []),
        "inefficiencies": [
            {
                "issue": i.get("issue", ""),
                "description": i.get("description", ""),
                "impact": i.get("impact", "medium"),
                "fix_hint": i.get("fix_hint", "")
            }
            for i in result.get("inefficiencies", [])
        ],
        "optimized_query": result.get("optimized_query", query),
        "optimization_notes": result.get("optimization_notes", []),
        "edge_cases": [
            {
                "scenario": e.get("scenario", ""),
                "risk": e.get("risk", ""),
                "mitigation": e.get("mitigation", "")
            }
            for e in result.get("edge_cases", [])
        ],
        "index_suggestions": result.get("index_suggestions", []),
        "overall_score": float(result.get("overall_score", 5))
    }
