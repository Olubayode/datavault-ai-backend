import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(os.getenv("DATAVAULT_DB_PATH", "storage/datavault.db"))
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage/uploads"))
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 7)))


def utc_now() -> int:
    return int(time.time())


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}:{base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_text, digest_text = stored_hash.split(":", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
    except ValueError:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(actual, expected)


def _b64_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _unb64_json(value: str) -> dict[str, Any]:
    padded = value + "=" * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")))


def create_token(user_id: str) -> str:
    payload = _b64_json({"sub": user_id, "exp": utc_now() + TOKEN_TTL_SECONDS})
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    signature_text = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload}.{signature_text}"


def verify_token(token: str) -> str | None:
    try:
        payload, signature_text = token.split(".", 1)
        expected = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode((signature_text + "=" * (-len(signature_text) % 4)).encode("utf-8"))
        data = _unb64_json(payload)
    except Exception:
        return None

    if not hmac.compare_digest(actual, expected):
        return None
    if int(data.get("exp", 0)) < utc_now():
        return None
    return str(data.get("sub"))


def ensure_default_project(user_id: str) -> dict[str, Any]:
    with connect() as conn:
        existing = conn.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at ASC LIMIT 1",
            (user_id,),
        ).fetchone()
        if existing:
            return dict(existing)

        project_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO projects (id, user_id, title, description, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                project_id,
                user_id,
                "Datavault Workspace",
                "Upload datasets and ask AI analytics questions.",
                iso_now(),
            ),
        )
        created = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(created)


def save_uploaded_file(project_id: str, file_name: str, content_type: str, purpose: str, content: bytes) -> dict[str, Any]:
    suffix = Path(file_name).suffix.lower()
    allowed = {".csv", ".xlsx", ".xls"} if purpose == "dataset" else {".pdf"}
    if suffix not in allowed:
        readable = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported file type. Use: {readable}")

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_name = f"{purpose}_{file_id}{suffix}"
    path = STORAGE_DIR / safe_name
    path.write_bytes(content)

    uploaded = {
        "id": file_id,
        "project_id": project_id,
        "file_name": file_name,
        "file_path": str(path),
        "file_type": content_type,
        "file_size": len(content),
        "purpose": purpose,
        "uploaded_at": iso_now(),
    }

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO files (id, project_id, file_name, file_path, file_type, file_size, purpose, uploaded_at)
            VALUES (:id, :project_id, :file_name, :file_path, :file_type, :file_size, :purpose, :uploaded_at)
            """,
            uploaded,
        )

    return uploaded
