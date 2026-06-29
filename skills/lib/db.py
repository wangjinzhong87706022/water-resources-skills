"""Shared DB helper for water-resources skills.

Usage:
    import sys
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')
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
        RuntimeError: MySQL execution error.
    """
    _check_sql(sql)
    conn = pymysql.connect(database=db, read_timeout=timeout, **DB_CONFIG)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SET SESSION max_execution_time = {timeout * 1000}")
        cursor.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        result = [dict(zip(columns, row)) for row in rows]
        if not result:
            print("[db] 查询返回 0 行。建议: 扩大时间范围、模糊匹配名称、或检查分区表是否缺少 tm 条件。")
        return result
    except pymysql.err.OperationalError as e:
        if e.args[0] == 3024:  # ER_QUERY_TIMEOUT
            raise TimeoutError(
                f"查询超时({timeout}s)。建议: 添加 WHERE tm >= ... 时间条件以利用分区裁剪。SQL: {sql[:100]}"
            ) from e
        raise RuntimeError(f"MySQL 执行错误: {e}") from e
    except pymysql.Error as e:
        raise RuntimeError(f"MySQL 错误: {e}") from e
    finally:
        conn.close()


def query_multi(sqls, db=DEFAULT_DB, timeout=DEFAULT_TIMEOUT):
    """Execute multiple SQL statements sequentially.

    Args:
        sqls: List of SQL strings.
        db: Database name (default: sl323).
        timeout: Per-query timeout in seconds (default: 30).

    Returns:
        list[list[dict]]: One element per SQL.
    """
    return [query(sql, db=db, timeout=timeout) for sql in sqls]
