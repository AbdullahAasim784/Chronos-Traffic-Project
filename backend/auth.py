
import sqlite3
from pwdlib import PasswordHash

from backend.database import get_connection

password_hasher = PasswordHash.recommended()


def verify_login(username, password):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        user = conn.execute(
            """
            SELECT user_id, username, password_hash,
                   full_name, role, is_active
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    if user is None or not user["is_active"]:
        return None

    if not password_hasher.verify(password, user["password_hash"]):
        return None

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"]
    }