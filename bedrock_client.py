import re

def _clean_sql(raw: str) -> str:
    sql = raw.strip()
    # remove code fences like ```sql ... ```
    if sql.startswith("```"):
        sql = re.sub(r"^```[a-zA-Z]*", "", sql, flags=re.IGNORECASE | re.MULTILINE)
        sql = sql.replace("```", "")
    return sql.strip()
def answer_from_rows(question: str, sql: str, columns: list, rows: list) -> str:
    """
    Produce a short, precise, single-sentence answer from columns/rows.
    Never invent data; if rows empty, say no result.
    """
    sample = {"columns": columns, "rows": rows[:5]}  # cap to 5 rows
    prompt = (
        "You are given a user question, the SQL that was executed, and the first rows returned.\n"
        "Answer with one short factual sentence. If results are empty, say so.\n\n"
        f"Question: {question}\nSQL: {sql}\nPreview: {json.dumps(sample)}"
    )
    messages = [{"role":"user","content":[{"type":"text","text": prompt}]}]
    return _invoke(messages)

import os, json, time, boto3
from botocore.exceptions import ClientError

_REGION = os.getenv("AWS_REGION", "eu-north-1")
_MODEL_OR_PROFILE = (
    os.getenv("BEDROCK_INFERENCE_PROFILE_ID")
    or os.getenv("BEDROCK_INFERENCE_PROFILE_ARN")
    or os.getenv("BEDROCK_MODEL_ID")
)
_brt = boto3.client("bedrock-runtime", region_name=_REGION)

BASE_INSTRUCTIONS = """
You translate natural language into **PostgreSQL** for the schema shown.

Rules (follow exactly):
- Always query the table "onlineretail_cleaned".
- Use identifiers exactly as in the schema (case-sensitive). Prefer double quotes.
- Columns are TEXT; when doing math, **cast** (e.g., "TotalPrice"::numeric, "Quantity"::int, "Year"::int).
- You may use **CTEs**, subqueries, and window functions.
- **SELECT-only** (no INSERT/UPDATE/DELETE/DDL). Return exactly one SQL statement.
- If the request implies a superlative (“highest/top/most”), include ORDER BY … DESC and add LIMIT (1 or 10).
- If user didn’t give a LIMIT, add `LIMIT 100`.
- Never omit the FROM clause. Return only SQL, no commentary.
"""

def _invoke(messages: list) -> str:
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 400,
        "messages": messages,
    }
    for attempt in range(3):
        try:
            resp = _brt.invoke_model(
                modelId=_MODEL_OR_PROFILE,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(resp["body"].read())
            for part in data.get("content", []):
                if part.get("type") == "text":
                    return part.get("text", "").strip()
            return ""
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ThrottlingException" and attempt < 2:
                time.sleep(0.6 * (2 ** attempt))  # 0.6s, 1.2s backoff
                continue
            raise

def nl_to_sql(message: str, schema_hint: str = "") -> str:
    system = BASE_INSTRUCTIONS + (f"\n\nSchema:\n{schema_hint}" if schema_hint else "")
    prompt = f"{system}\n\nRequest: {message}\n\nReturn only the SQL."
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    raw = _invoke(messages)
    return _clean_sql(raw)

def fix_sql(sql: str, db_error: str, schema_hint: str = "") -> str:
    system = BASE_INSTRUCTIONS + "\nYou are given a SQL query and the exact PostgreSQL error it produced. Return a corrected SQL that fixes the error. Keep it SELECT-only."
    if schema_hint:
        system += f"\n\nSchema:\n{schema_hint}"
    prompt = f"{system}\n\nOriginal SQL:\n{sql}\n\nError:\n{db_error}\n\nReturn corrected SQL only:"
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    raw = _invoke(messages)
    return _clean_sql(raw)

def answer_from_rows(question: str, sql: str, columns: list, rows: list) -> str:
    """
    Produce a short, precise, single-sentence answer from columns/rows.
    Never invent data; if rows empty, say 'No results found.'
    """
    sample = {"columns": columns, "rows": rows[:5]}
    prompt = (
        "You are a careful data analyst. Given the user's question, the SQL executed, and a preview of rows, "
        "reply with ONE short, factual sentence. If the question implies a superlative, name the winner and value. "
        "If the result set is empty, say 'No results found.'\n\n"
        f"Question: {question}\nSQL: {sql}\nPreview JSON: {json.dumps(sample, ensure_ascii=False)}"
    )
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    return _invoke(messages)
    if schema_hint:
        system += f"\n\nSchema:\n{schema_hint}"
    prompt = f"{system}\n\nOriginal SQL:\n{sql}\n\nError:\n{db_error}\n\nReturn corrected SQL only:"
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    return _invoke(messages)
