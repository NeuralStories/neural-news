"""Diagnóstico: estado de las versiones de guion y las aprobaciones."""
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "storage/neural-news.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=== últimas historias con versiones de guion ===")
for s in conn.execute(
    "select id, title, status from stories order by id desc limit 3"
):
    print(f"historia #{s['id']} [{s['status']}] {s['title'][:50]}")
    for v in conn.execute(
        "select id, version, length(content) n, created_at from script_versions "
        "where story_id=? order by version desc limit 4",
        (s["id"],),
    ):
        print(f"   version {v['version']} (id {v['id']}, {v['n']} chars, {v['created_at']})")
    for a in conn.execute(
        "select * from approvals where story_id=? order by id desc limit 3", (s["id"],)
    ):
        print(f"   aprobación: {dict(a)}")

print("\n=== últimos trabajos (job) con error ===")
for j in conn.execute(
    "select id, type, status, error_kind, substr(coalesce(error,''),1,90) e, created_at "
    "from jobs order by id desc limit 8"
):
    print(f"  #{j['id']} {j['type']:<18} {j['status']:<18} kind={j['error_kind']} {j['e']}")
