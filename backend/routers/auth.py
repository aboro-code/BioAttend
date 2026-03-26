from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor

from dependencies import get_db_connection
from auth_dependencies import get_current_user
from models.schemas import LoginRequest, LoginResponse, MeResponse
from security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT id, username, password_hash, role, is_active
        FROM app_users
        WHERE username = %s
    """,
        (request.username,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=user["username"], role=user["role"])
    return LoginResponse(
        success=True,
        access_token=token,
        token_type="bearer",
        role=user["role"],
        username=user["username"],
    )


@router.get("/me", response_model=MeResponse)
async def me(user=Depends(get_current_user)):
    return MeResponse(username=user["username"], role=user["role"])
