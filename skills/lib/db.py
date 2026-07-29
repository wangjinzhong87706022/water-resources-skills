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

# Functions that break partition pruning on a RANGE-partitioned tm column.
# YEAR(tm), DATE(tm), MONTH(tm), LEFT(tm, ...) etc. force a full partition scan.
_PARTITION_BREAKING_FUNCS = (
    "year", "date", "month", "left", "right", "substring",
    "date_format", "str_to_date", "extract",
)


def _check_partition_prune(sql):
    import re
    lower = sql.lower()
    # A range predicate on tm enables pruning regardless of functions elsewhere
    # (e.g. GROUP BY DATE(tm) with WHERE tm >= ... AND tm < ... is fine).
    if re.search(r'\btm[`"]?\s*(>=|<=|>|<|between)', lower):
        return
    for fn in _PARTITION_BREAKING_FUNCS:
        # Match e.g. year(tm), YEAR(tm), year(`tm`), year(r.tm)
        if re.search(rf'\b{fn}\s*\(\s*(?:\w+\.)?[`"]?tm[`"]?\s*\)', lower):
            raise ValueError(
                f"{fn.upper()}(tm) without a tm range disables partition pruning and will scan "
                "ALL partitions (may take 10-60s or time out).\n"
                "Fix: add a range condition:\n"
                "  OK   tm >= '2024-01-01' AND tm < '2025-01-01'  -- year 2024\n"
                "  BAD  YEAR(tm) = 2024  -- scans all partitions\n"
                f"Your SQL: {sql[:300]}"
            )


def _check_sql(sql, allow_full_scan=False):
    s = sql.strip().upper()
    if not any(s.startswith(p) for p in _ALLOWED):
        raise ValueError(f"只允许 SELECT/SHOW/DESCRIBE，收到: {s[:30]}")
    if not allow_full_scan:
        _check_partition_prune(sql)


def _schema_hint(sql, error_msg, db):
    """On unknown column/table errors, return the real schema so the caller
    can self-correct in one round. Returns '' when not applicable."""
    import re
    if not ("Unknown column" in error_msg or "doesn't exist" in error_msg or "Unknown table" in error_msg):
        return ""
    m = re.search(r'\b(st_\w+)\b', sql)
    if not m:
        return ""
    table = m.group(1)
    try:
        conn = _connect(db="information_schema", timeout=10)
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY "
                    "FROM COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                    "ORDER BY ORDINAL_POSITION",
                    (db, table),
                )
                cols = cur.fetchall()
        finally:
            conn.close()
        if not cols:
            return ""
        lines = [f"[schema] Table `{table}` real columns (INFORMATION_SCHEMA):"]
        for c in cols:
            nn = "NULL" if c["IS_NULLABLE"] == "YES" else "NOT NULL"
            lines.append(f"  {c['COLUMN_NAME']}  {c['COLUMN_TYPE']}  {nn}  {c.get('COLUMN_KEY', '')}")
        lines.append("Fix the SQL using the correct column names above.")
        return "\n".join(lines)
    except Exception:
        return ""


def query(sql, db=DEFAULT_DB, timeout=DEFAULT_TIMEOUT, allow_full_scan=False):
    """Execute a SELECT query and return list of dicts.

    Args:
        sql: SQL statement (SELECT/SHOW/DESCRIBE only).
        db: Database name (default: sl323).
        timeout: Per-query timeout in seconds (default: 30).
        allow_full_scan: Skip the partition-prune guard (trusted callers only,
            e.g. eval replay of gold SQL).

    Returns:
        list[dict]: Rows as dicts with column names as keys. Empty list if no results.

    Raises:
        ValueError: Non-SELECT SQL, or partition-scan SQL without allow_full_scan.
        TimeoutError: Query exceeded timeout.
    """
    import sys
    _check_sql(sql, allow_full_scan=allow_full_scan)
    conn = _connect(db, timeout=timeout)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            if not rows:
                print(
                    f"[db hint] Query returned 0 rows. SQL: {sql[:200]}\n"
                    "[db hint] Check get_date_range(table) for time coverage, "
                    "or column names / filter values via the schema.",
                    file=sys.stderr,
                )
            return rows
    except pymysql.err.OperationalError as e:
        if e.args[0] == 3024:  # ER_QUERY_TIMEOUT
            raise TimeoutError(f"Query timeout after {timeout}s") from None
        hint = _schema_hint(sql, str(e), db)
        if hint:
            raise pymysql.err.OperationalError(e.args[0], f"{e.args[1]}\n\n{hint}") from None
        raise
    except pymysql.err.ProgrammingError as e:
        hint = _schema_hint(sql, str(e), db)
        if hint:
            raise pymysql.err.ProgrammingError(e.args[0], f"{e.args[1]}\n\n{hint}") from None
        raise
    finally:
        conn.close()


def get_date_range(table, db=DEFAULT_DB):
    """Return approximate min/max tm for a table as a human-readable string.

    Reads partition boundaries from INFORMATION_SCHEMA.PARTITIONS (zero row
    scan); falls back to a full MIN/MAX scan only when no partitions exist.
    """
    import re
    from datetime import date, timedelta
    conn = _connect(db, timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT PARTITION_NAME, PARTITION_DESCRIPTION "
                "FROM INFORMATION_SCHEMA.PARTITIONS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                "ORDER BY PARTITION_DESCRIPTION",
                (db, table),
            )
            part_rows = [r for r in cur.fetchall() if r[0] is not None]
            if part_rows:
                def _strip(val):
                    m = re.match(r"'(.+)'", str(val))
                    return m.group(1) if m else str(val)

                first_desc = _strip(part_rows[0][1])
                last_desc = _strip(part_rows[-1][1])
                try:
                    upper = date.fromisoformat(first_desc)
                    est_min = date(upper.year - 1, 1, 1)
                    est_max = date.fromisoformat(last_desc) - timedelta(days=1)
                    return f"`{table}`: ~{est_min} ~ {est_max} (partition bounds: {first_desc} ~ {last_desc})"
                except (ValueError, TypeError):
                    return f"`{table}`: < {first_desc} ~ < {last_desc} (partition upper bounds)"

            cur.execute(f"SELECT MIN(tm), MAX(tm) FROM `{table}`")
            row = cur.fetchone()
            if row and row[0] and row[1]:
                return f"`{table}`: {row[0]} ~ {row[1]}"
            return f"`{table}`: no data or no `tm` column."
    except Exception as e:
        return f"`{table}`: query failed ({e})"
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
