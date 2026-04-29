# import os
# from sqlalchemy import create_engine
# from sqlalchemy.orm import declarative_base, sessionmaker
#
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#
# DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'events.db')}"
#
# engine = create_engine(
#     DATABASE_URL,
#     connect_args={"check_same_thread": False}
# )
#
# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
#
# Base = declarative_base()
#
# print("Database path:", DATABASE_URL)



#
# import os
# from sqlalchemy import create_engine
# from sqlalchemy.orm import declarative_base, sessionmaker
#
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#
# DATABASE_URL = os.getenv(
#     "DATABASE_URL",
#     f"sqlite:///{os.path.join(BASE_DIR, 'events.db')}"
# )
#
# if DATABASE_URL.startswith("postgres://"):
#     DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
#
# connect_args = {}
#
# if DATABASE_URL.startswith("sqlite"):
#     connect_args = {"check_same_thread": False}
#
# engine = create_engine(DATABASE_URL, connect_args=connect_args)
#
# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
#
# Base = declarative_base()
#
# print("Connected DB:", DATABASE_URL)



import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'events.db')}"
)

# Fix old postgres:// format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}

# Only for SQLite
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

print("Connected DB:", DATABASE_URL)