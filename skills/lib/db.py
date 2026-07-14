"""Shared DB helper for water-resources skills.

Usage (DeerFlow):
    import sys
    sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')
    from db import query, query_multi

    rows = query("SELECT stcd, stnm FROM sl323.st_stbprp_b LIMIT 10")
    for row in rows:
        print(row['stnm'], row['stcd'])
"""

import os

import pymysql

DB_CONFIG = {
    'host': os.environ.get('SL323_DB_HOST', '192.168.100.103'),
    'port': int(os.environ.get('SL323_DB_PORT', '3306')),
    'user': os.environ.get('SL323_DB_USER', 'root'),
    'password': os.environ.get('SL323_DB_PASSWORD', ''),
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
    conn = _connect(db)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, timeout=timeout)
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


def _connect(db=DEFAULT_DB):
    return pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=db,
        charset=DB_CONFIG['charset'],
        connect_timeout=10,
    )
