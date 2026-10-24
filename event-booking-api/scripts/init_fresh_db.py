"""Create the Eventora model schema in an EMPTY local development database only.

The legacy Alembic base revision assumes pre-existing app tables, so a fresh
PostgreSQL instance cannot safely run the old migration chain from zero.
Run this ONCE on a completely empty development DB, then `alembic stamp head`.
For an existing database, back up data and follow its recorded migration path.
"""
from sqlalchemy import inspect
import models
from database import engine, Base


def main():
    current = inspect(engine).get_table_names()
    if current:
        raise RuntimeError(f"Refusing to bootstrap: database already contains tables: {current}")
    Base.metadata.create_all(bind=engine)
    print("Created Eventora tables in empty development database. Next: alembic stamp head")


if __name__ == "__main__":
    main()
