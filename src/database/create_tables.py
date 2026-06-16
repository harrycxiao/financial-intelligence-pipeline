# src/database/create_tables.py

from src.database.connection import Base, engine
from src.database import models


def create_tables() -> None:
    """Create all database tables registered on Base.metadata."""

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    create_tables()