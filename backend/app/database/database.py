from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use /app/db directory in Docker, or local directory for development
DB_DIR = os.getenv("DB_DIR", ".")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIR}/sql_app.db"

print(f"[database] Using database path: {SQLALCHEMY_DATABASE_URL}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 