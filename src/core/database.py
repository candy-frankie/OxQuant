"""
OxQuant Database Module

Database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import asyncpg
import asyncio

from src.core.config import settings


# Synchronous SQLAlchemy setup (for ORM)
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Async database setup (for raw SQL queries)
async def get_async_connection():
    """Get async PostgreSQL connection."""
    return await asyncpg.connect(settings.DATABASE_URL)


async def init_db():
    """Initialize database tables."""
    from src.core import models
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create async connection for initialization
    conn = await get_async_connection()
    try:
        # Create extensions if needed
        await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        
        # Create custom functions
        await conn.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """)
        
        print("Database initialized successfully")
    finally:
        await conn.close()


# Database models will be imported here to ensure they're registered
from src.core.models import *  # noqa