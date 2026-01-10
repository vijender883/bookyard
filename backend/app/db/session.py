from sqlalchemy import text
from sqlmodel import create_engine, Session, SQLModel
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """
    Initializes the database schema using SQLModel and then runs the 
    post-initialization SQL for Supabase-specific features (Enums, Realtime, RLS).
    """
    # 1. Create tables defined in SQLModel
    SQLModel.metadata.create_all(engine)
    
    # 2. Run Supabase-specific SQL (Enums, Realtime, RLS)
    migration_file = "/Users/rahulpandey187/Documents/bookyard/backend/supabase/migrations/20260110_initial_schema.sql"
    if os.path.exists(migration_file):
        with open(migration_file, "r") as f:
            sql = f.read()
            with Session(engine) as session:
                try:
                    # Execute the SQL script. Note: This assumes the script 
                    # uses CREATE TABLE IF NOT EXISTS and other idempotent commands.
                    session.execute(text(sql))
                    session.commit()
                except Exception as e:
                    print(f"Error running migration: {e}")
                    session.rollback()

def get_session():
    with Session(engine) as session:
        yield session
