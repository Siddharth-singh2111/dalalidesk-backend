"""
Set the password hash for user 'admin' in PostgreSQL (uses .env DB_* vars).

Usage from repository root:
    python API_Database/reset_admin_password.py
    python API_Database/reset_admin_password.py your_new_password

Default password if omitted: admin5555
"""
import os
import sys

import bcrypt
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else "admin5555"
    required = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing env: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE username = %s",
                    (pw_hash, "admin"),
                )
                if cur.rowcount == 0:
                    print("No user with username 'admin' found.", file=sys.stderr)
                    sys.exit(1)
        print("Password updated for user 'admin'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
