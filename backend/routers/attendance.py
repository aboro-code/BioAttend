from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import List
from psycopg2.extras import RealDictCursor
from dependencies import get_db_connection
from models.schemas import AttendanceLog
from services.export_service import generate_csv_export, generate_excel_export

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/today", response_model=List[AttendanceLog])
async def get_today_attendance():
    """Get today's attendance logs"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT s.name, a.status, TO_CHAR(a.log_time, 'HH12:MI AM') as time 
        FROM attendance_logs a 
        JOIN students s ON a.student_id = s.id 
        WHERE a.log_time::date = CURRENT_DATE 
        ORDER BY a.log_time DESC
    """
    )
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res


@router.get("/export/csv")
async def export_csv():
    """Export attendance as CSV"""
    try:
        content, filename = generate_csv_export()
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/export/excel")
async def export_excel():
    """Export attendance as Excel"""
    try:
        excel_file, filename = generate_excel_export()
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return {"error": str(e)}
