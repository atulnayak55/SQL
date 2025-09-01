import os, psycopg2, re

def get_connection():
	return psycopg2.connect(
		host=os.getenv("POSTGRES_HOST"),
		port=os.getenv("POSTGRES_PORT", "5432"),
		dbname=os.getenv("POSTGRES_DB"),
		user=os.getenv("POSTGRES_USER"),
		password=os.getenv("POSTGRES_PASSWORD"),
		sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
	)

# --- helpers & regexes ---

# Disallow anything obviously dangerous anywhere in the text
WRITE_VERBS = re.compile(
	r'\b(INSERT|UPDATE|DELETE|MERGE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|COPY|VACUUM|ANALYZE)\b',
	re.IGNORECASE
)

# Allowed starters after stripping comments/whitespace
ALLOWED_START = re.compile(
	r'^\s*(WITH\b|SELECT\b|VALUES\b|TABLE\b)',
	re.IGNORECASE | re.DOTALL
)

_LIMIT_RE = re.compile(r'\bLIMIT\b\s+\d+', re.IGNORECASE)
_SEMI_RE  = re.compile(r';\s*$')

def _strip_leading_comments(sql: str) -> str:
	"""
	Remove leading SQL comments:
	  -- line comments
	  /* block comments */
	…so the starter check isn't fooled.
	"""
	s = sql.lstrip()
	# Remove any number of leading comments
	while True:
		if s.startswith('--'):
			nl = s.find('\n')
			s = s[nl+1:] if nl != -1 else ''
			s = s.lstrip()
			continue
		if s.startswith('/*'):
			end = s.find('*/')
			if end == -1:
				# Unclosed comment -> treat as empty
				return ''
			s = s[end+2:].lstrip()
			continue
		break
	return s

def _single_statement_only(sql: str) -> bool:
	"""
	Ensure there is at most one statement.
	We normalize one trailing semicolon later; here we reject
	anything with another semicolon before the end.
	"""
	# Remove trailing semicolon(s) and whitespace, then check if any ; remain
	core = _SEMI_RE.sub('', sql).strip()
	return ';' not in core

def ensure_readonly_query(sql: str) -> str:
	"""
	Accepts common read-only statements:
	  - SELECT …
	  - WITH … SELECT …
	  - TABLE <name>
	  - VALUES (…)
	Adds LIMIT 100 if missing (works for SELECT/WITH/TABLE/VALUES).
	Normalizes to a single trailing semicolon.
	Rejects writes/DDL/multiple statements.
	"""
	raw = sql.strip()
	if not raw:
		raise ValueError("Empty query.")

	# Block obvious write/DDL verbs anywhere
	if WRITE_VERBS.search(raw):
		raise ValueError("Only read-only queries are allowed.")

	# Enforce single statement
	if not _single_statement_only(raw):
		raise ValueError("Multiple statements are not allowed.")

	# Check allowed starters after stripping comments
	starter_scan = _strip_leading_comments(raw)
	if not ALLOWED_START.match(starter_scan):
		raise ValueError("Only SELECT/WITH/TABLE/VALUES queries are allowed.")

	# Add LIMIT if missing (idempotent). This is fine for SELECT/WITH/TABLE/VALUES.
	q = raw
	if not _LIMIT_RE.search(q):
		q = _SEMI_RE.sub('', q) + " LIMIT 100"

	# Normalize to exactly one trailing semicolon
	q = _SEMI_RE.sub('', q).rstrip() + ";"
	return q
