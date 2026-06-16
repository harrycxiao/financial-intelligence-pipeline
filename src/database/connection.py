# src/database/connection.py

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Load database credentials from .env.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError(
        "DATABASE_URL not found. Make sure your .env file contains DATABASE_URL."
    )


# Engine manages the connection pool to Postgres.
engine = create_engine(
    DATABASE_URL,
    echo=True,
)


# SessionLocal creates database sessions for queries/inserts/updates.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# Base is inherited by every SQLAlchemy model/table.
Base = declarative_base()