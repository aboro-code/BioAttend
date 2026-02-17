import json
import numpy as np
from psycopg2.extras import RealDictCursor
from dependencies import get_db_connection


def load_all_students():
    """Load all students with embeddings from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT name, embedding FROM students")
        rows = cur.fetchall()

        students = []
        for row in rows:
            emb_str = row["embedding"]
            if isinstance(emb_str, str):
                clean_str = emb_str.replace("np.str_('", "").replace("')", "")
                emb_list = json.loads(clean_str)
                embedding = np.array(emb_list).astype(np.float32)
            else:
                embedding = np.array(emb_str).astype(np.float32)
            print(f"Student: {row['name']}, Embedding Shape: {embedding.shape}")

            students.append({"name": row["name"], "embedding": embedding})

        cur.close()
        conn.close()
        print(f"✅ Loaded {len(students)} students from database")
        return students
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return []
