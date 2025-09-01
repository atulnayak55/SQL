import re
from bedrock_client import nl_to_sql as generate_sql, fix_sql

FROM_RE = re.compile(r'\bFROM\b', re.IGNORECASE)

def ensure_from_clause(sql: str, schema_hint: str) -> str:
    """If SQL has no FROM, ask the model to fix it once."""
    if FROM_RE.search(sql):
        return sql
    hint = 'Query is missing the FROM clause. It must select from "onlineretail_cleaned".'
    fixed = fix_sql(sql, hint, schema_hint=schema_hint).strip()
    return fixed or sql
