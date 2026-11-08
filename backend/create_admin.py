
from pwdlib import PasswordHash

from backend.database import get_connection

# Initial development account
USERNAME = "admin"
PASSWORD = "pass1234"
FULL_NAME = "System Administrator"
ROLE = "admin"

password_hasher = PasswordHash.recommended()


def create_admin():
    with get_connection() as conn:

        # Check whether the admin username already exists
        existing_user = conn.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (USERNAME,)
        ).fetchone()

        if existing_user:
            print("Admin account already exists. No changes made.")
            return

        # Hash password before saving
        hashed_password = password_hasher.hash(PASSWORD)

        # Insert the new administrator
        conn.execute(
            """
            INSERT INTO users
                (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                USERNAME,
                hashed_password,
                FULL_NAME,
                ROLE,
                1
            )
        )

        print("Admin account created successfully!")


if __name__ == "__main__":
    create_admin()
