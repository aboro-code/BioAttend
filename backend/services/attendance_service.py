"""
Attendance logging service
"""

from datetime import datetime
from dependencies import get_db_connection


def log_attendance(student_name: str):
    """Log attendance for a student"""
    now = datetime.now()
    today = now.date()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get student ID
        cur.execute("SELECT id FROM students WHERE name = %s", (student_name,))
        res = cur.fetchone()

        if res:
            student_id = res[0]

            # Check if already logged today
            cur.execute(
                """
                SELECT id FROM attendance_logs 
                WHERE student_id = %s AND log_time::date = %s
            """,
                (student_id, today),
            )
            existing = cur.fetchone()

            if existing:
                # Update existing log
                cur.execute(
                    "UPDATE attendance_logs SET log_time = %s WHERE id = %s",
                    (now, existing[0]),
                )
            else:
                # Insert new log
                cur.execute(
                    "INSERT INTO attendance_logs (student_id, status, log_time) VALUES (%s, 'Present', %s)",
                    (student_id, now),
                )

            conn.commit()

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Attendance DB Error: {e}")
