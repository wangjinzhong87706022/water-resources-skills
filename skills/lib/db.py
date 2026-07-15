"""Shared DB helper for water-resources skills.

Usage (LLM-generated runtime script — __file__ unreliable, use the
ROOT env-var snippet documented in SKILL.md "标准导入片段"):

    import os, sys
    sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
    from db import query, query_multi

Usage (offline scripts under scripts/, run from real path — uses bootstrap
resolver which adds env-var override + candidate fallback):

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib'))
    from bootstrap import locate_lib, locate_shared
    from db import query

    rows = query("SELECT stcd, stnm FROM sl323.st_stbprp_b LIMIT 10")
    for row in rows:
        print(row['stnm'], row['stcd'])
"""

import os
from pathlib import Path

import pymysql

# DeerFlow runs skill scripts in a sandbox subprocess whose environment is
# scrubbed by env_policy.build_sandbox_env() — any var matching *PASSWORD* /
# *KEY* / *SECRET* / *TOKEN* / *PASSWD* / *CREDENTIAL* / *DSN* is stripped
# (issue #3861). Consequently SL323_DB_PASSWORD is NOT visible to db.py when
# it runs inside the sandbox, and a plain os.environ.get() returns ''. We fall
# back to reading the gitignored repo-root .env, located relative to this file
# so resolution works regardless of cwd or env vars.
_ENV_FILE_CANDIDATES = (
    Path(__file__).resolve().parent.parent.parent / ".env",  # <repo-root>/.env
    Path(__file__).resolve().parent.parent / ".env",         # <skills>/.env
)


def _parse_env_file(path):
    """Minimal KEY=VALUE parser (no python-dotenv dependency)."""
    values = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                val = val.split("#", 1)[0].strip()  # strip inline comments
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                values[key.strip()] = val
    except OSError:
        pass
    return values


def _load_file_env():
    merged = {}
    for candidate in _ENV_FILE_CANDIDATES:
        if candidate.is_file():
            merged.update(_parse_env_file(candidate))
    return merged


_FILE_ENV = _load_file_env()


def _cfg(key, default=""):
    """Resolve a DB config value: os.environ wins; .env file fills the gap
    (e.g. the scrubbed PASSWORD); built-in default is the last resort."""
    return os.environ.get(key) or _FILE_ENV.get(key) or default


DB_CONFIG = {
    'host': _cfg('SL323_DB_HOST', '192.168.100.103'),
    'port': int(_cfg('SL323_DB_PORT', '3306')),
    'user': _cfg('SL323_DB_USER', 'root'),
    'password': _cfg('SL323_DB_PASSWORD', ''),
    'charset': 'utf8mb4',
}

DEFAULT_DB = 'sl323'
DEFAULT_TIMEOUT = 30  # seconds per query

_ALLOWED = ('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')


def _check_sql(sql):
    s = sql.strip().upper()
    if not any(s.startswith(p) for p in _ALLOWED):
        raise ValueError(f"只允许 SELECT/SHOW/DESCRIBE，收到: {s[:30]}")


def query(sql, db=DEFAULT_DB, timeout=DEFAULT_TIMEOUT):
    """Execute a SELECT query and return list of dicts.

    Args:
        sql: SQL statement (SELECT/SHOW/DESCRIBE only).
        db: Database name (default: sl323).
        timeout: Per-query timeout in seconds (default: 30).

    Returns:
        list[dict]: Rows as dicts with column names as keys. Empty list if no results.

    Raises:
        ValueError: Non-SELECT SQL.
        TimeoutError: Query exceeded timeout.
    """
    _check_sql(sql)
    conn = _connect(db, timeout=timeout)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()
    except pymysql.err.OperationalError as e:
        if e.args[0] == 3024:  # ER_QUERY_TIMEOUT
            raise TimeoutError(f"Query timeout after {timeout}s") from None
        raise
    finally:
        conn.close()


def query_multi(sqls, db=DEFAULT_DB, timeout=DEFAULT_TIMEOUT):
    """Execute multiple SELECT queries sequentially, return list of results."""
    return [query(sql, db=db, timeout=timeout) for sql in sqls]


def _connect(db=DEFAULT_DB, timeout=DEFAULT_TIMEOUT):
    return pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=db,
        charset=DB_CONFIG['charset'],
        connect_timeout=10,
        read_timeout=timeout,
    )
