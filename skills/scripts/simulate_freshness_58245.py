"""Supplement: add station 58245 (扬州) to st_pptn_r so Q26/Q41 golden SQL
(hardcoded stcd='58245', anchored on CURDATE()) returns rows.

58245 went inactive 2025-11-26, before the main generator's active-station
cutoff, so it was skipped. We fill 2026-06-12..2026-07-31 (tm > 2026-06-11),
which the EXISTING rollback rule `DELETE FROM st_pptn_r WHERE tm > '2026-06-11'`
already covers -- no rollback change needed.
"""
import os, random
from datetime import datetime, date, timedelta
import pymysql

random.seed(58245)
TARGET = date(2026, 7, 31)
START = date(2026, 6, 12)  # > existing st_pptn_r max 2026-06-11

cfg = {'host': os.environ.get('SL323_DB_HOST','192.168.100.103'),
       'port': int(os.environ.get('SL323_DB_PORT','3306')),
       'user': os.environ.get('SL323_DB_USER','root'),
       'password': os.environ.get('SL323_DB_PASSWORD',''), 'charset':'utf8mb4'}
if not cfg['password']:
    for p in ('/opt/git/water-resources-skills/.env','/opt/git/water-resources-skills/skills/.env'):
        if os.path.isfile(p):
            for raw in open(p, encoding='utf-8'):
                line=raw.strip()
                if not line or line.startswith('#') or '=' not in line: continue
                k,_,v=line.partition('='); v=v.split('#',1)[0].strip().strip('"').strip("'")
                if k.strip()=='SL323_DB_PASSWORD' and v: cfg['password']=v

import sys
DRY = '--apply' not in sys.argv
conn = pymysql.connect(database='sl323', **cfg, connect_timeout=10, read_timeout=60, autocommit=False)
try:
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("SELECT * FROM st_pptn_r WHERE stcd='58245' ORDER BY tm DESC LIMIT 1")
        tmpl = cur.fetchone()
        cur.execute("SHOW COLUMNS FROM st_pptn_r")
        cols = [r['Field'] for r in cur.fetchall()]
    days = [START + timedelta(days=i) for i in range((TARGET - START).days + 1)]
    rows = []
    for d in days:
        row = dict(tmpl)
        row['tm'] = datetime(d.year, d.month, d.day, 0, 0, 0)
        # realistic daily rainfall: 60% dry, else 0.5..15mm
        row['drp'] = 0.0 if random.random() < 0.6 else round(random.uniform(0.5, 15.0), 1)
        rows.append([row[c] for c in cols])
    print(f"58245 rows to insert: {len(rows)}  (from {START} to {TARGET})")
    if DRY:
        print("[DRY-RUN] use --apply to insert. Rollback covered by existing tm>'2026-06-11'.")
    else:
        ph = ','.join(['%s']*len(cols)); collist=','.join(f'`{c}`' for c in cols)
        with conn.cursor() as cur:
            cur.executemany(f"INSERT INTO st_pptn_r ({collist}) VALUES ({ph})", rows)
        conn.commit()
        print(f"[DONE] inserted {len(rows)} rows for 58245.")
except Exception:
    conn.rollback(); raise
finally:
    conn.close()
