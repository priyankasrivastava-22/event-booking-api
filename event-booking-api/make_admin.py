import sqlite3

conn = sqlite3.connect("events.db")
cursor = conn.cursor()

cursor.execute(
    "UPDATE users SET role = 'admin' WHERE username = ?",
    ("priya@example.com",)
)

conn.commit()
conn.close()

print("User role updated to admin")