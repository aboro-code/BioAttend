from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg2.extras import RealDictCursor

from dependencies import get_db_connection
from security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT id, username, role, is_active
        FROM app_users
        WHERE username = %s
    """,
        (username,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User inactive or missing")

    return user


def require_role(required_role: str):
    def _role_checker(user=Depends(get_current_user)):
        if user["role"] != required_role:
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        return user

    return _role_checker
