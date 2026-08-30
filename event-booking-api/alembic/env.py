from logging.config import fileConfig  # Configure Alembic logging
from sqlalchemy import engine_from_config, pool  # Create SQLAlchemy engine
from alembic import context  # Alembic migration context
from dotenv import load_dotenv  # Load environment variables
import os  # Access environment variables
import sys  # Add project root to Python path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root so models can be imported

load_dotenv()  # Load .env variables

import models  # Import SQLAlchemy models
from database import Base  # Import shared SQLAlchemy metadata

config = context.config  # Get Alembic configuration

database_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_POSTGRES")  # Read PostgreSQL URL from environment

if not database_url:  # Stop if database URL is missing
    raise RuntimeError("DATABASE_URL is not configured in .env")  # Clear configuration error

config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))  # Provide database URL to Alembic safely

if config.config_file_name is not None:  # Check whether Alembic config exists
    fileConfig(config.config_file_name)  # Configure logging

target_metadata = Base.metadata  # Tell Alembic to compare models.py metadata with PostgreSQL schema


def run_migrations_offline():  # Run migrations without opening a database connection
    url = config.get_main_option("sqlalchemy.url")  # Read database URL
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})  # Configure offline migration
    with context.begin_transaction():  # Start migration transaction
        context.run_migrations()  # Execute migrations


def run_migrations_online():  # Run migrations using a database connection
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)  # Create database engine

    with connectable.connect() as connection:  # Open database connection
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)  # Configure Alembic with model metadata

        with context.begin_transaction():  # Start migration transaction
            context.run_migrations()  # Execute migrations


if context.is_offline_mode():  # Check migration mode
    run_migrations_offline()  # Run offline migration
else:  # Otherwise use online mode
    run_migrations_online()  # Run online migration