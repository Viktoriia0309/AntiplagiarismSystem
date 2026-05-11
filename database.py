import psycopg2

DB_CONFIG = {
    "dbname": "antiplagiarism_db",
    "user": "postgres",
    "password": "123",
    "host": "localhost",
    "port": "5432"
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_all_documents():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT filename, content FROM documents")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    filenames = [row[0] for row in rows]
    texts = [row[1] for row in rows]

    return texts, filenames