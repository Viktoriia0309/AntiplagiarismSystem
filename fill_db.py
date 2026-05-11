import os
from database import get_connection

conn = get_connection()
cur = conn.cursor()

for filename in os.listdir("texts"):
    if filename.endswith(".txt"):
        with open(f"texts/{filename}", "r", encoding="utf-8") as f:
            content = f.read()

        cur.execute(
            "INSERT INTO documents (filename, content) VALUES (%s, %s)",
            (filename, content)
        )

conn.commit()
cur.close()
conn.close()

print("Готово")