import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# =========================================================
# PATH CONFIGURATION
# =========================================================

API_DIR = Path(__file__).resolve().parent
PROJECT_DIR = API_DIR.parent


# =========================================================
# LOAD .ENV
# =========================================================

load_dotenv(API_DIR / ".env")
load_dotenv(PROJECT_DIR / ".env")


# =========================================================
# DATABASE URL
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. "
        "Configure the existing Aiven PostgreSQL database "
        "in your .env file."
    )


# SQLAlchemy expects postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


# =========================================================
# ENGINE OPTIONS
# =========================================================

connect_args = {}

if DATABASE_URL.startswith("postgresql"):
    connect_args = {
        "connect_timeout": 10
    }

elif DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }


# =========================================================
# SQLALCHEMY ENGINE
# =========================================================

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300
)


# =========================================================
# SESSION
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =========================================================
# BASE MODEL
# =========================================================

Base = declarative_base()