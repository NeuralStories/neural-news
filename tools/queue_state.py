"""Estado de la cola: trabajos recientes."""
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "storage/neural-news.db"
with sqlite3.connect(DB) as conn:
    filas = conn.execute(
        "select id, type, status, attempt, substr(coalesce(error,''),1,60), created_at "
        "from jobs order by id desc limit 12"
    ).fetchall()
    for f in filas:
        print(f)
    print("--- totales por estado ---")
    for f in conn.execute("select status, count(*) from jobs group by status").fetchall():
        print(f)
