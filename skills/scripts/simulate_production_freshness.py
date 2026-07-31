"""Simulate production freshness: carry-forward + daily jitter up to TARGET_DATE.

Safety:
 - Writes a rollback SQL script BEFORE any insert.
 - sl323 tables: only inserts rows with tm > original MAX(tm) -> rollback = DELETE WHERE tm > orig_max (cannot touch real rows).
 - wq_pcp_d: tags generated rows bak1='SIMGEN' -> rollback = DELETE WHERE bak1='SIMGEN'.
 - Never modifies or deletes existing rows.
 - Excludes forecast (slztk) tables per user's choice.
"""
import os, sys, random
from datetime import datetime, timedelta, date
import pymysql

random.seed(20260731)  # deterministic
TARGET = date(2026, 7, 31)
ROLLBACK_PATH = '/opt/git/water-resources-skills/skills/scripts/rollback_simgen.sql'

cfg = {
    'host': os.environ.get('SL323_DB_HOST', '192.168.100.103'),
    'port': int(os.environ.get('SL323_DB_PORT', '3306')),
    'user': os.environ.get('SL323_DB_USER', 'root'),
    'password': os.environ.get('SL323_DB_PASSWORD', ''),
    'charset': 'utf8mb4',
}
if not cfg['password']:
    for p in ('/opt/git/water-resources-skills/.env', '/opt/git/water-resources-skills/skills/.env'):
        if os.path.isfile(p):
            for raw in open(p, encoding='utf-8'):
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                v = v.split('#', 1)[0].strip().strip('"').strip("'")
                if k.strip() == 'SL323_DB_PASSWORD' and v:
                    cfg['password'] = v

DRY_RUN = '--apply' not in sys.argv

def connect(db):
    return pymysql.connect(host=cfg['host'], port=cfg['port'], user=cfg['user'],
                           password=cfg['password'], database=db, charset=cfg['charset'],
                           connect_timeout=10, read_timeout=180, autocommit=False)

def col_meta(conn, db, table):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_SCALE, COLUMN_KEY "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s "
            "ORDER BY ORDINAL_POSITION", (db, table))
        return cur.fetchall()

def jitter(v, scale):
    if v is None:
        return None
    f = float(v) * (1 + random.uniform(-0.03, 0.03))
    return round(f, scale if scale else 0) if scale else int(round(f))

# (db, table, time_col, tag_col_or_None)
SL323 = [
    ('sl323', 'st_river_r', 'tm', None),
    ('sl323', 'st_pptn_r',  'tm', None),
    ('sl323', 'st_pump_r',  'tm', None),
    ('sl323', 'st_pump_pa', 'tm', None),
    ('sl323', 'st_gate_r',  'tm', None),
    ('sl323', 'st_was_r',   'tm', None),
]
WQ = ('sl325', 'wq_pcp_d', 'spt', 'bak1')

def gen_sl323(conn, db, table, tcol):
    meta = col_meta(conn, db, table)
    cols = [m['COLUMN_NAME'] for m in meta]
    scale = {m['COLUMN_NAME']: m['NUMERIC_SCALE'] for m in meta}
    dtype = {m['COLUMN_NAME']: m['DATA_TYPE'] for m in meta}
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(f"SELECT MAX({tcol}) mx FROM {table}")
        orig_max = cur.fetchone()['mx']
        cur.execute(f"SELECT * FROM {table} WHERE {tcol}=%s", (orig_max,))
        templates = cur.fetchall()
    start = orig_max.date() + timedelta(days=1)
    days = [start + timedelta(days=i) for i in range((TARGET - start).days + 1)]
    rows = []
    for tmpl in templates:
        for d in days:
            row = dict(tmpl)
            row[tcol] = datetime(d.year, d.month, d.day, 0, 0, 0)
            for c in cols:
                if c == tcol:
                    continue
                if dtype[c] == 'decimal':
                    row[c] = jitter(tmpl[c], scale[c])
            rows.append([row[c] for c in cols])
    return orig_max, cols, rows

def gen_wq(conn, db, table, tcol, tag):
    meta = col_meta(conn, db, table)
    cols = [m['COLUMN_NAME'] for m in meta]
    scale = {m['COLUMN_NAME']: m['NUMERIC_SCALE'] for m in meta}
    dtype = {m['COLUMN_NAME']: m['DATA_TYPE'] for m in meta}
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        # active stations: latest data in 2026-03..2026-07 window
        cur.execute(
            "SELECT d.* FROM wq_pcp_d d JOIN "
            "(SELECT stcd, MAX(spt) mx FROM wq_pcp_d "
            " WHERE spt >= '2026-03-01' AND spt < '2026-08-01' GROUP BY stcd) m "
            "ON d.stcd=m.stcd AND d.spt=m.mx")
        templates = cur.fetchall()
    rows = []
    for tmpl in templates:
        smax = tmpl[tcol]
        start = smax.date() + timedelta(days=1)
        if start > TARGET:
            continue
        days = [start + timedelta(days=i) for i in range((TARGET - start).days + 1)]
        for d in days:
            row = dict(tmpl)
            row[tcol] = datetime(d.year, d.month, d.day, 0, 0, 0)
            row[tag] = 'SIMGEN'
            for c in cols:
                if c in (tcol, tag):
                    continue
                if dtype[c] == 'decimal':
                    row[c] = jitter(tmpl[c], scale[c])
            rows.append([row[c] for c in cols])
    return cols, rows

def insert(conn, table, cols, rows):
    ph = ','.join(['%s'] * len(cols))
    collist = ','.join(f'`{c}`' for c in cols)
    sql = f"INSERT INTO {table} ({collist}) VALUES ({ph})"
    with conn.cursor() as cur:
        for i in range(0, len(rows), 1000):
            cur.execute("SELECT 1")  # keep-alive noop
            cur.executemany(sql, rows[i:i+1000])

def main():
    rollback_lines = ["-- Rollback for SIMGEN production-freshness data (generated).",
                      "-- Deletes ONLY generated rows. Run against the noted DB.", ""]
    plan = []
    # sl323
    conn = connect('sl323')
    try:
        prepared = []
        for db, table, tcol, tag in SL323:
            orig_max, cols, rows = gen_sl323(conn, db, table, tcol)
            prepared.append((db, table, tcol, cols, rows))
            plan.append((f'{db}.{table}', len(rows), f"tm > '{orig_max}'"))
            rollback_lines.append(f"USE {db};")
            rollback_lines.append(f"DELETE FROM {table} WHERE {tcol} > '{orig_max}';")
        # wq
        wconn = connect('sl325')
        wdb, wtable, wtcol, wtag = WQ
        wcols, wrows = gen_wq(wconn, wdb, wtable, wtcol, wtag)
        plan.append((f'{wdb}.{wtable}', len(wrows), f"{wtag}='SIMGEN'"))
        rollback_lines.append(f"USE {wdb};")
        rollback_lines.append(f"DELETE FROM {wtable} WHERE {wtag}='SIMGEN';")

        # write rollback file FIRST
        with open(ROLLBACK_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rollback_lines) + '\n')
        print(f"[rollback] written -> {ROLLBACK_PATH}\n")

        print("=== PLAN ===")
        total = 0
        for name, n, cond in plan:
            print(f"  {name:22} +{n:6} rows   (rollback: {cond})")
            total += n
        print(f"  {'TOTAL':22} +{total:6} rows")

        if DRY_RUN:
            print("\n[DRY-RUN] no rows inserted. Re-run with --apply to insert.")
            return

        print("\n[APPLY] inserting...")
        for db, table, tcol, cols, rows in prepared:
            if rows:
                insert(conn, table, cols, rows)
                print(f"  inserted {len(rows):6} -> {db}.{table}")
        conn.commit()
        if wrows:
            insert(wconn, wtable, wcols, wrows)
            print(f"  inserted {len(wrows):6} -> {wdb}.{wtable}")
        wconn.commit()
        print("\n[DONE] committed.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
