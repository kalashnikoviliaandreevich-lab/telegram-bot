import sqlite3

conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS docs (
    user_id INTEGER,
    chunk TEXT,
    embedding BLOB
)
""")

conn.commit()


def save_chunk(user_id, chunk, embedding):
    cur.execute(
        "INSERT INTO docs VALUES (?, ?, ?)",
        (user_id, chunk, embedding.tobytes())
    )
    conn.commit()


def get_all(user_id):
    cur.execute("SELECT chunk, embedding FROM docs WHERE user_id=?", (user_id,))
    return cur.fetchall()


def clear(user_id):
    cur.execute("DELETE FROM docs WHERE user_id=?", (user_id,))
    conn.commit() 
