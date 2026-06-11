import sqlite3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# LOCAL SQLITE FILE
SQLITE_DB = "events.db"

# RENDER POSTGRES URL
POSTGRES_URL = os.getenv("DATABASE_URL")
# CONNECT SQLITE
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row

# CONNECT POSTGRES
engine = create_engine(POSTGRES_URL)

# TABLES TO MIGRATE
# Order matters because of foreign keys
tables = [
    "users",
    "categories",
    "events",
    "bookings",
    "notifications",
    "audit_logs",
    "blacklisted_tokens",
    "password_resets",
    "email_verifications",
    "payments"
]

# START MIGRATION
with engine.begin() as conn:
    for table in tables:
        try:
            rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
            print(f"{table}: {len(rows)} rows")

            for row in rows:
                data = dict(row)

                # Convert SQLite integer booleans
                # PostgreSQL expects True / False
                if table == "users":
                    if "is_active" in data:
                        data["is_active"] = bool(data["is_active"])

                    if "is_verified" in data:
                        data["is_verified"] = bool(data["is_verified"])

                # Dynamic column + values creation
                cols = ", ".join(data.keys())
                vals = ", ".join([f":{k}" for k in data.keys()])

                query = text(f"""
                    INSERT INTO {table} ({cols})
                    VALUES ({vals})
                    ON CONFLICT DO NOTHING
                """)

                conn.execute(query, data)

        except Exception as e:
            print(f"Skipped {table}: {e}")

print("Migration completed.")

print("DB URL =", POSTGRES_URL)