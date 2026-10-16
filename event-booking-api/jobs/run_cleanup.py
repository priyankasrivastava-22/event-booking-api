"""One-shot expired-hold cleanup. Schedule every minute with your host/cron.

From event-booking-api/: python -m jobs.run_cleanup
Set DATABASE_URL before running. Do not run the script itself in a loop.
"""
import logging
from database import SessionLocal
from jobs.inventory_cleanup import release_expired_inventory


def main():
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        total = release_expired_inventory(db)
        logging.info("Released %s expired bookings", total)
    except Exception:
        db.rollback()
        logging.exception("Expired hold cleanup failed")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
