import psycopg2
from tabulate import tabulate # You might need to: pip install tabulate

def get_daily_report():
    conn = psycopg2.connect(host="localhost", database="face_recognition", user="admin", password="password123")
    cur = conn.cursor()
    
    query = """
    SELECT s.name, TO_CHAR(a.log_time AT TIME ZONE 'Asia/Kolkata', 'HH12:MI AM') 
    FROM attendance_logs a 
    JOIN students s ON a.student_id = s.id 
    WHERE a.log_time::date = CURRENT_DATE
    ORDER BY a.log_time ASC;
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    print(f"\n--- Attendance Report for {rows[0][1] if rows else 'Today'} ---")
    print(tabulate(rows, headers=['Student Name', 'Time In'], tablefmt='grid'))
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    get_daily_report()