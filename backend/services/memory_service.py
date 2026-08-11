from db.database import get_connection


def save_message(session_id: str, role: str, content: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO chats (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print("❌ Save Error:", e)


def get_history(session_id: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT role, content FROM chats WHERE session_id=? ORDER BY id ASC",
            (session_id,)
        )

        rows = cursor.fetchall()
        conn.close()

        return [{"role": r[0], "content": r[1]} for r in rows]

    except Exception as e:
        print("❌ Fetch Error:", e)
        return []


def save_document_metadata(doc_id: str, page_count: int, chunk_count: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO documents (doc_id, page_count, chunk_count) VALUES (?, ?, ?)",
        (doc_id, page_count, chunk_count),
    )
    conn.commit()
    conn.close()


def get_document_metadata(doc_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT page_count, chunk_count FROM documents WHERE doc_id = ?",
        (doc_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {"page_count": row[0], "chunk_count": row[1]}
