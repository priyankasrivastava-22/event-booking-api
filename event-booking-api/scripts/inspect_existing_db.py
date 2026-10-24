"""Read-only audit of an EXISTING PostgreSQL/Aiven schema against Eventora models.

Prints schema metadata only, never application rows, user secrets or DATABASE_URL.
No CREATE/ALTER/DROP, no Alembic stamp, and no migration is executed.
"""
from sqlalchemy import inspect, text
from database import engine, Base
import models  # noqa: F401  populate the SQLAlchemy model metadata


def main():
    with engine.connect() as connection:
        if connection.dialect.name != "postgresql":
            raise RuntimeError("Audit requires an explicit PostgreSQL DATABASE_URL (Aiven).")
        inspector = inspect(connection)
        database_name = connection.execute(text("SELECT current_database()" )).scalar_one()
        print("Connected PostgreSQL database:", database_name)
        table_names = set(inspector.get_table_names(schema="public"))
        print("Existing public tables:", ", ".join(sorted(table_names)) or "none")
        if "alembic_version" in table_names:
            versions = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all()
            print("Existing Alembic revision(s):", ", ".join(versions) or "none")
        else:
            print("Existing Alembic revision(s): NO alembic_version table")
        expected = {name: table for name, table in Base.metadata.tables.items() if table.schema in (None, "public")}
        missing_tables = sorted(set(expected) - table_names)
        print("Model tables MISSING on Aiven:", ", ".join(missing_tables) or "none")
        extra_tables = sorted(table_names - set(expected) - {"alembic_version"})
        print("Aiven tables not in current models (do NOT drop):", ", ".join(extra_tables) or "none")
        missing_columns = {}
        for name in sorted(set(expected) & table_names):
            live_columns = {col["name"] for col in inspector.get_columns(name, schema="public")}
            absent = sorted({col.name for col in expected[name].columns} - live_columns)
            if absent:
                missing_columns[name] = absent
        if missing_columns:
            print("Missing model columns (review migration, do NOT auto-add blindly):")
            for name, columns in missing_columns.items():
                print(" -", name + ":", ", ".join(columns))
        else:
            print("Missing model columns: none")
        print("Read-only audit finished. No changes were made.")


if __name__ == "__main__":
    main()
