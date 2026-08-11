import sqlite3


def get_connection():
    return sqlite3.connect("chat.db", check_same_thread=False)


def init_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            page_count INTEGER NOT NULL,
            chunk_count INTEGER NOT NULL
        )
        """)

        conn.commit()
        conn.close()

        print("✅ Database initialized")

    except Exception as e:
        print("❌ DB Init Error:", e)
