from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from app.services.store import connect, create_token, hash_password, iso_now, row_to_dict, verify_password, verify_token


router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    with connect() as conn:
        user = row_to_dict(conn.execute("SELECT id, full_name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone())

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register")
def register(payload: RegisterRequest):
    with connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (payload.email.lower(),)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = payload.email.lower()
        conn.execute(
            """
            INSERT INTO users (id, full_name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, payload.full_name, payload.email.lower(), hash_password(payload.password), iso_now()),
        )

    return {"access_token": create_token(user_id), "token_type": "bearer"}


@router.post("/login")
def login(payload: LoginRequest):
    with connect() as conn:
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE email = ?", (payload.email.lower(),)).fetchone())

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {"access_token": create_token(user["id"]), "token_type": "bearer"}


@router.get("/me")
def me(user=Depends(current_user)):
    return user
