from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")
# Fallback local (desarrollo): SQLite si no hay DATABASE_URL
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./dev.db"

# Para Neon/Render usa la cadena pooled con ?sslmode=require
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
