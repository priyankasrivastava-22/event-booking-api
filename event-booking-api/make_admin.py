"""Local operator-only CLI to promote an EXISTING Eventora user.

Run inside the API container after signing up at the frontend:
    python make_admin.py --username YOUR_REGISTERED_USERNAME

Never expose this command as an HTTP endpoint, or run it for an unknown user.
"""
import argparse
from database import SessionLocal
from models import User


def main():
    parser = argparse.ArgumentParser(description="Promote one existing account to admin")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--username", help="Exact registered username")
    group.add_argument("--email", help="Registered email address")
    args = parser.parse_args()

    with SessionLocal() as db:
        query = db.query(User)
        user = query.filter(User.username == args.username.strip()).first() if args.username else query.filter(User.email == args.email.strip().lower()).first()
        if not user:
            parser.error("No registered user found; register through the frontend first")
        if not user.is_active:
            parser.error("Inactive account cannot be promoted")
        if user.role == "admin":
            print(f"Account {user.username} already has admin privileges")
            return
        user.role = "admin"
        db.commit()
        print(f"Promoted registered user {user.username} to admin; sign out and sign back in")


if __name__ == "__main__":
    main()
