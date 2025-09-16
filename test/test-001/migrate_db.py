import sqlite3
from db.database import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")
cols = [r[1] for r in cur.fetchall()]

if "created_at" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN created_at INTEGER")
    print("Colonna 'created_at' aggiunta con successo ✅")
else:
    print("Colonna 'created_at' già presente")

conn.commit()
conn.close()
print("Migrazione completata.")
