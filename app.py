def clean_sql_output(raw: str) -> str:
    sql = raw.strip()
    # remove code fences
    if sql.startswith("```"):
        sql = re.sub(r"^```[a-zA-Z]*", "", sql)
        sql = sql.replace("```", "")
    return sql.strip()
# app.py

from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os



from db import get_connection, ensure_readonly_query
from bedrock_client import nl_to_sql as generate_sql, fix_sql, answer_from_rows

import re
FROM_RE = re.compile(r'\bFROM\b', re.IGNORECASE)
def ensure_from_clause(sql: str, schema_hint: str) -> str:
    if FROM_RE.search(sql):
        return sql
    hint = 'Query is missing the FROM clause. It must select from "onlineretail_cleaned".'
    fixed = fix_sql(sql, hint, schema_hint=schema_hint).strip()
    return fixed or sql



app = FastAPI(title="SQL Chatbot (Read-only + Precise Answers)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)



SCHEMA_HINT = """Tables:
"onlineretail_cleaned"(
    "InvoiceNo","StockCode","Description","Quantity","InvoiceDate",
    "UnitPrice","CustomerID","Country","TotalPrice","Year","Month"
)

Notes:
- Numeric-like columns are TEXT; cast when aggregating or comparing:
    "TotalPrice"::numeric, "UnitPrice"::numeric, "Quantity"::int, "Year"::int, "Month"::int.

Examples:
-- highest spending customer
WITH totals AS (
    SELECT "CustomerID", SUM("TotalPrice"::numeric) AS "TotalSpent"
    FROM "onlineretail_cleaned"
    GROUP BY "CustomerID"
)
SELECT "CustomerID","TotalSpent"
FROM totals
ORDER BY "TotalSpent" DESC
LIMIT 1;

-- total sales by country
SELECT "Country", SUM("TotalPrice"::numeric) AS "TotalSales"
FROM "onlineretail_cleaned"
GROUP BY "Country"
ORDER BY "TotalSales" DESC
LIMIT 100;
"""


@app.get("/")
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))






@app.post("/chat")
def chat(message: str = Form(...)):

    raw = generate_sql(message, schema_hint=SCHEMA_HINT)
    sql = clean_sql_output(raw)

    # 2) Ensure FROM exists
    sql = ensure_from_clause(sql, SCHEMA_HINT)

    # 3) Read-only guard
    try:
        sql = ensure_readonly_query(sql)
    except Exception as e:
        return {"sql": sql, "error": str(e)}

    # (rest of function unchanged…)
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close(); conn.close()

        answer = answer_from_rows(message, sql, cols, rows) if rows else "No results found."
        return {"sql": sql, "columns": cols, "rows": rows, "answer": answer}
    except Exception as e:
        try:
            repaired = fix_sql(sql, str(e), schema_hint=SCHEMA_HINT).strip()
            repaired = ensure_readonly_query(repaired)
            conn = get_connection(); cur = conn.cursor()
            cur.execute(repaired)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            cur.close(); conn.close()
            answer = answer_from_rows(message, repaired, cols, rows) if rows else "No results found."
            return {"sql": repaired, "columns": cols, "rows": rows, "answer": answer, "note": "Auto-repaired from DB error."}
        except Exception as e2:
            return {"sql": sql, "error": f"{e}\n(Repair attempt failed: {e2})"}
